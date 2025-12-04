"""
Microsoft Outlook Integration
Provides calendar sync, contact sync, and presence integration
"""
from pbx.utils.logger import get_logger
from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False


class OutlookIntegration:
    """Microsoft Outlook / Office 365 integration handler"""

    def __init__(self, config: dict):
        """
        Initialize Outlook integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get('integrations.outlook.enabled', False)
        self.tenant_id = config.get('integrations.outlook.tenant_id')
        self.client_id = config.get('integrations.outlook.client_id')
        self.client_secret = config.get('integrations.outlook.client_secret')
        self.sync_interval = config.get('integrations.outlook.sync_interval', 300)  # 5 minutes
        self.auto_dnd_in_meetings = config.get('integrations.outlook.auto_dnd_in_meetings', True)
        self.graph_endpoint = 'https://graph.microsoft.com/v1.0'
        self.scopes = config.get('integrations.outlook.scopes', [
            'https://graph.microsoft.com/.default'
        ])
        self.access_token = None
        self.msal_app = None

        if self.enabled:
            if not REQUESTS_AVAILABLE:
                self.logger.error("Outlook integration requires 'requests' library. Install with: pip install requests")
                self.enabled = False
            elif not MSAL_AVAILABLE:
                self.logger.error("Outlook integration requires 'msal' library. Install with: pip install msal")
                self.enabled = False
            else:
                self.logger.info("Outlook integration enabled")
                self._initialize_msal()

    def _initialize_msal(self):
        """Initialize MSAL confidential client application"""
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            self.logger.error("Outlook credentials not configured properly")
            return
        
        try:
            authority = f"https://login.microsoftonline.com/{self.tenant_id}"
            self.msal_app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=authority,
                client_credential=self.client_secret
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize MSAL: {e}")

    def authenticate(self) -> bool:
        """
        Authenticate with Microsoft Graph API using client credentials flow

        Returns:
            bool: True if authentication successful
        """
        if not self.enabled or not MSAL_AVAILABLE:
            return False

        if not self.msal_app:
            self._initialize_msal()
            if not self.msal_app:
                return False

        try:
            self.logger.info("Authenticating with Microsoft Graph...")
            
            # Acquire token using client credentials flow
            result = self.msal_app.acquire_token_for_client(scopes=self.scopes)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.logger.info("Microsoft Graph authentication successful")
                return True
            else:
                error = result.get("error", "Unknown error")
                error_desc = result.get("error_description", "")
                self.logger.error(f"Authentication failed: {error} - {error_desc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error authenticating with Microsoft Graph: {e}")
            return False

    def get_calendar_events(self, user_email: str, start_time: str = None, end_time: str = None) -> List[Dict]:
        """
        Get calendar events for a user

        Args:
            user_email: User's email address
            start_time: Start time (ISO format, optional)
            end_time: End time (ISO format, optional)

        Returns:
            list: List of calendar events
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return []

        if not self.authenticate():
            return []

        # Default to today's events if not specified
        if not start_time:
            start_time = datetime.now().replace(hour=0, minute=0, second=0).isoformat() + 'Z'
        if not end_time:
            end_time = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'

        try:
            self.logger.info(f"Fetching calendar events for {user_email}")
            
            url = f"{self.graph_endpoint}/users/{user_email}/calendar/calendarView"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            params = {
                'startDateTime': start_time,
                'endDateTime': end_time,
                '$select': 'subject,start,end,location,organizer,isAllDay,isCancelled'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                events = []
                for event in data.get('value', []):
                    events.append({
                        'subject': event.get('subject'),
                        'start': event.get('start', {}).get('dateTime'),
                        'end': event.get('end', {}).get('dateTime'),
                        'location': event.get('location', {}).get('displayName'),
                        'organizer': event.get('organizer', {}).get('emailAddress', {}).get('name'),
                        'is_all_day': event.get('isAllDay', False),
                        'is_cancelled': event.get('isCancelled', False)
                    })
                
                self.logger.info(f"Found {len(events)} calendar events for {user_email}")
                return events
            else:
                self.logger.error(f"Failed to fetch calendar events: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching calendar events: {e}")
            return []

    def check_user_availability(self, user_email: str) -> str:
        """
        Check if user is available based on calendar

        Args:
            user_email: User's email address

        Returns:
            str: Status (available, busy, tentative, out_of_office)
        """
        if not self.enabled:
            return "unknown"

        # Use timezone-aware datetime
        now = datetime.now(timezone.utc)
        start_time = now.isoformat()
        end_time = (now + timedelta(hours=1)).isoformat()
        
        # Check current calendar events
        events = self.get_calendar_events(user_email, start_time, end_time)
        
        if events:
            # User has active or upcoming meeting
            for event in events:
                if not event.get('is_cancelled'):
                    # Parse event times as timezone-aware
                    event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                    event_end = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
                    
                    if event_start <= now <= event_end:
                        return "busy"
        
        # Check out of office status
        ooo = self.get_out_of_office_status(user_email)
        if ooo and ooo.get('status') == 'scheduled':
            return "out_of_office"
        
        return "available"

    def sync_contacts(self, user_email: str) -> List[Dict]:
        """
        Synchronize Outlook contacts with PBX

        Args:
            user_email: User's email address

        Returns:
            list: List of contacts
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return []

        if not self.authenticate():
            return []

        try:
            self.logger.info(f"Syncing contacts for {user_email}")
            
            url = f"{self.graph_endpoint}/users/{user_email}/contacts"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            params = {
                '$select': 'displayName,emailAddresses,businessPhones,mobilePhone,homePhones'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                contacts = []
                for contact in data.get('value', []):
                    # Extract primary email
                    emails = contact.get('emailAddresses', [])
                    primary_email = emails[0].get('address') if emails else None
                    
                    # Extract phone numbers
                    business_phones = contact.get('businessPhones', [])
                    mobile_phone = contact.get('mobilePhone')
                    home_phones = contact.get('homePhones', [])
                    
                    contacts.append({
                        'name': contact.get('displayName'),
                        'email': primary_email,
                        'business_phone': business_phones[0] if business_phones else None,
                        'mobile_phone': mobile_phone,
                        'home_phone': home_phones[0] if home_phones else None
                    })
                
                self.logger.info(f"Synced {len(contacts)} contacts for {user_email}")
                return contacts
            else:
                self.logger.error(f"Failed to sync contacts: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error syncing contacts: {e}")
            return []

    def log_call_to_calendar(self, user_email: str, call_details: dict):
        """
        Log a phone call to user's Outlook calendar

        Args:
            user_email: User's email address
            call_details: Call details (from, to, duration, etc.)

        Returns:
            bool: True if logged successfully
        """
        if not self.enabled:
            return False

        self.logger.info(f"Logging call to calendar for {user_email}")
        # TODO: Create calendar event
        # POST https://graph.microsoft.com/v1.0/users/{userPrincipalName}/calendar/events

        return False

    def get_out_of_office_status(self, user_email: str) -> Optional[Dict]:
        """
        Get user's out-of-office status

        Args:
            user_email: User's email address

        Returns:
            dict: OOO status and message, or None
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return None

        if not self.authenticate():
            return None

        try:
            url = f"{self.graph_endpoint}/users/{user_email}/mailboxSettings/automaticRepliesSetting"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': data.get('status'),  # disabled, alwaysEnabled, scheduled
                    'external_reply': data.get('externalReplyMessage'),
                    'internal_reply': data.get('internalReplyMessage'),
                    'scheduled_start': data.get('scheduledStartDateTime', {}).get('dateTime'),
                    'scheduled_end': data.get('scheduledEndDateTime', {}).get('dateTime')
                }
            else:
                self.logger.error(f"Failed to get OOO status: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting OOO status: {e}")
            return None

    def send_meeting_reminder(self, user_email: str, meeting_id: str, minutes_before: int = 5):
        """
        Send a phone notification for upcoming meeting

        Args:
            user_email: User's email address
            meeting_id: Meeting identifier
            minutes_before: Minutes before meeting to notify

        Returns:
            bool: True if notification scheduled
        """
        if not self.enabled:
            return False

        self.logger.info(f"Scheduling meeting reminder for {user_email}")
        # TODO: Schedule notification to user's extension

        return False
