"""
Microsoft Teams Integration
Enables SIP Direct Routing, presence sync, and collaboration features with Microsoft Teams
"""
from pbx.utils.logger import get_logger
from typing import Optional, Dict, List

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


class TeamsIntegration:
    """Microsoft Teams integration handler"""

    def __init__(self, config: dict):
        """
        Initialize Teams integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get('integrations.microsoft_teams.enabled', 
                                  config.get('integrations.teams.enabled', False))
        self.tenant_id = config.get('integrations.microsoft_teams.tenant_id',
                                    config.get('integrations.teams.tenant_id'))
        self.client_id = config.get('integrations.microsoft_teams.client_id',
                                    config.get('integrations.teams.client_id'))
        self.client_secret = config.get('integrations.microsoft_teams.client_secret',
                                        config.get('integrations.teams.client_secret'))
        self.direct_routing_domain = config.get('integrations.microsoft_teams.direct_routing_domain',
                                                config.get('integrations.teams.sip_domain'))
        self.graph_endpoint = 'https://graph.microsoft.com/v1.0'
        self.scopes = ['https://graph.microsoft.com/.default']
        self.access_token = None
        self.msal_app = None

        if self.enabled:
            if not REQUESTS_AVAILABLE:
                self.logger.error("Teams integration requires 'requests' library. Install with: pip install requests")
                self.enabled = False
            elif not MSAL_AVAILABLE:
                self.logger.error("Teams integration requires 'msal' library. Install with: pip install msal")
                self.enabled = False
            else:
                self.logger.info("Microsoft Teams integration enabled")
                self._initialize_msal()

    def _initialize_msal(self):
        """Initialize MSAL confidential client application"""
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            self.logger.error("Teams credentials not configured properly")
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
        Authenticate with Microsoft Teams using OAuth 2.0

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
            self.logger.info("Authenticating with Microsoft Teams...")
            
            # Acquire token using client credentials flow
            result = self.msal_app.acquire_token_for_client(scopes=self.scopes)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.logger.info("Microsoft Teams authentication successful")
                return True
            else:
                error = result.get("error", "Unknown error")
                error_desc = result.get("error_description", "")
                self.logger.error(f"Authentication failed: {error} - {error_desc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error authenticating with Microsoft Teams: {e}")
            return False

    def sync_presence(self, user_id: str, pbx_status: str) -> bool:
        """
        Sync presence status to Microsoft Teams

        Args:
            user_id: Teams user ID or UPN
            pbx_status: PBX presence status (available, busy, away, dnd, etc.)

        Returns:
            bool: True if successful
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return False

        if not self.authenticate():
            return False

        # Map PBX status to Teams presence
        status_map = {
            'available': 'Available',
            'busy': 'Busy',
            'away': 'Away',
            'dnd': 'DoNotDisturb',
            'offline': 'Offline',
            'in_call': 'Busy',
            'in_meeting': 'InAMeeting'
        }
        
        teams_status = status_map.get(pbx_status.lower(), 'Available')

        try:
            self.logger.info(f"Syncing presence for {user_id}: {pbx_status} -> {teams_status}")
            
            url = f"{self.graph_endpoint}/users/{user_id}/presence/setPresence"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'sessionId': f'pbx-{user_id}',
                'availability': teams_status,
                'activity': teams_status
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                self.logger.info(f"Presence synced successfully for {user_id}")
                return True
            else:
                self.logger.error(f"Failed to sync presence: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error syncing presence: {e}")
            return False

    def route_call_to_teams(self, from_number: str, to_teams_user: str):
        """
        Route a call from PBX to Microsoft Teams user

        Args:
            from_number: Caller's number
            to_teams_user: Teams user ID or UPN

        Returns:
            bool: True if call routed successfully
        """
        if not self.enabled:
            return False

        self.logger.info(f"Routing call from {from_number} to Teams user {to_teams_user}")
        # TODO: Use SIP Direct Routing to send INVITE to Teams
        # SIP URI: {user}@{direct_routing_domain}

        return False

    def send_chat_message(self, to_user: str, message: str):
        """
        Send a chat message to Teams user

        Args:
            to_user: Teams user ID or UPN
            message: Message text

        Returns:
            bool: True if successful
        """
        if not self.enabled or not REQUESTS_AVAILABLE or not MSAL_AVAILABLE:
            return False

        # Authenticate first
        if not self.authenticate():
            return False

        try:
            # First, we need to create or get a 1:1 chat with the user
            # Create a chat endpoint
            chat_url = f"{self.graph_endpoint}/chats"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Create a 1:1 chat
            chat_body = {
                'chatType': 'oneOnOne',
                'members': [
                    {
                        '@odata.type': '#microsoft.graph.aadUserConversationMember',
                        'user@odata.bind': f"https://graph.microsoft.com/v1.0/users('{to_user}')",
                        'roles': ['owner']
                    }
                ]
            }
            
            self.logger.info(f"Creating/getting chat with {to_user}")
            chat_response = requests.post(chat_url, headers=headers, json=chat_body, timeout=10)
            
            # Note: If chat already exists, API may return 201 or we need to get existing chat
            # For simplicity, we'll handle both cases
            chat_id = None
            if chat_response.status_code in [200, 201]:
                chat_id = chat_response.json().get('id')
            else:
                # Try to find existing chat
                search_url = f"{self.graph_endpoint}/me/chats"
                search_response = requests.get(search_url, headers=headers, timeout=10)
                if search_response.status_code == 200:
                    chats = search_response.json().get('value', [])
                    for chat in chats:
                        if chat.get('chatType') == 'oneOnOne':
                            # Check if this chat is with the target user
                            members = chat.get('members', [])
                            for member in members:
                                if member.get('userId') == to_user or member.get('email') == to_user:
                                    chat_id = chat.get('id')
                                    break
                        if chat_id:
                            break
            
            if not chat_id:
                self.logger.error(f"Failed to create or find chat with {to_user}")
                return False
            
            # Send message to the chat
            message_url = f"{self.graph_endpoint}/chats/{chat_id}/messages"
            message_body = {
                'body': {
                    'content': message,
                    'contentType': 'text'
                }
            }
            
            self.logger.info(f"Sending message to chat {chat_id}")
            message_response = requests.post(message_url, headers=headers, json=message_body, timeout=10)
            
            if message_response.status_code == 201:
                self.logger.info(f"Successfully sent Teams chat message to {to_user}")
                return True
            else:
                self.logger.warning(f"Failed to send Teams chat message: {message_response.status_code} - {message_response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Teams chat message: {e}")
            return False

    def create_meeting_from_call(self, call_id: str, subject: str = None, participants: List[str] = None) -> Optional[Dict]:
        """
        Escalate a phone call to a Teams meeting

        Args:
            call_id: PBX call identifier
            subject: Meeting subject
            participants: List of participant email addresses

        Returns:
            dict: Meeting details (join URL, etc.) or None
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return None

        if not self.authenticate():
            return None

        try:
            self.logger.info(f"Creating Teams meeting for call {call_id}")
            
            url = f"{self.graph_endpoint}/users/me/onlineMeetings"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'subject': subject or f'Escalated Call {call_id}',
                'participants': {
                    'attendees': [
                        {'identity': {'user': {'id': email}}}
                        for email in (participants or [])
                    ]
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                meeting_data = response.json()
                self.logger.info(f"Teams meeting created: {meeting_data.get('id')}")
                
                return {
                    'meeting_id': meeting_data.get('id'),
                    'join_url': meeting_data.get('joinWebUrl'),
                    'subject': meeting_data.get('subject'),
                    'start_time': meeting_data.get('startDateTime'),
                    'end_time': meeting_data.get('endDateTime')
                }
            else:
                self.logger.error(f"Failed to create Teams meeting: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating Teams meeting: {e}")
            return None
