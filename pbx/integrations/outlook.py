"""
Microsoft Outlook Integration
Provides calendar sync, contact sync, and presence integration
"""

from datetime import UTC, datetime, timedelta

from pbx.utils.logger import get_logger

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
        self.enabled = config.get("integrations.outlook.enabled", False)
        self.tenant_id = config.get("integrations.outlook.tenant_id")
        self.client_id = config.get("integrations.outlook.client_id")
        self.client_secret = config.get("integrations.outlook.client_secret")
        self.sync_interval = config.get("integrations.outlook.sync_interval", 300)  # 5 minutes
        self.auto_dnd_in_meetings = config.get("integrations.outlook.auto_dnd_in_meetings", True)
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        self.scopes = config.get(
            "integrations.outlook.scopes", ["https://graph.microsoft.com/.default"]
        )
        self.access_token = None
        self.msal_app = None

        if self.enabled:
            if not REQUESTS_AVAILABLE:
                self.logger.error(
                    "Outlook integration requires 'requests' library. Install with: pip install requests"
                )
                self.enabled = False
            elif not MSAL_AVAILABLE:
                self.logger.error(
                    "Outlook integration requires 'msal' library. Install with: pip install msal"
                )
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
                self.client_id, authority=authority, client_credential=self.client_secret
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
            error = result.get("error", "Unknown error")
            error_desc = result.get("error_description", "")
            self.logger.error(f"Authentication failed: {error} - {error_desc}")
            return False

        except (requests.RequestException, KeyError, ValueError) as e:
            self.logger.error(f"Error authenticating with Microsoft Graph: {e}")
            return False

    def get_calendar_events(
        self, user_email: str, start_time: str | None = None, end_time: str | None = None
    ) -> list[dict]:
        """
        Get calendar events for a user

        Args:
            user_email: User's email address
            start_time: Start time (ISO format, optional)
            end_time: End time (ISO format, optional)

        Returns:
            list: list of calendar events
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return []

        if not self.authenticate():
            return []

        # Default to today's events if not specified
        if not start_time:
            start_time = datetime.now(UTC).replace(hour=0, minute=0, second=0).isoformat() + "Z"
        if not end_time:
            end_time = (datetime.now(UTC) + timedelta(days=1)).replace(
                hour=0, minute=0, second=0
            ).isoformat() + "Z"

        try:
            self.logger.info(f"Fetching calendar events for {user_email}")

            url = f"{self.graph_endpoint}/users/{user_email}/calendar/calendarView"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-type": "application/json",
            }
            params = {
                "startDateTime": start_time,
                "endDateTime": end_time,
                "$select": "subject,start,end,location,organizer,isAllDay,isCancelled",
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                events = []
                for event in data.get("value", []):
                    events.append(
                        {
                            "subject": event.get("subject"),
                            "start": event.get("start", {}).get("dateTime"),
                            "end": event.get("end", {}).get("dateTime"),
                            "location": event.get("location", {}).get("displayName"),
                            "organizer": event.get("organizer", {})
                            .get("emailAddress", {})
                            .get("name"),
                            "is_all_day": event.get("isAllDay", False),
                            "is_cancelled": event.get("isCancelled", False),
                        }
                    )

                self.logger.info(f"Found {len(events)} calendar events for {user_email}")
                return events
            self.logger.error(
                f"Failed to fetch calendar events: {response.status_code} - {response.text}"
            )
            return []

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
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
        now = datetime.now(UTC)
        start_time = now.isoformat()
        end_time = (now + timedelta(hours=1)).isoformat()

        # Check current calendar events
        events = self.get_calendar_events(user_email, start_time, end_time)

        if events:
            # User has active or upcoming meeting
            for event in events:
                if not event.get("is_cancelled"):
                    # Parse event times as timezone-aware
                    event_start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
                    event_end = datetime.fromisoformat(event["end"].replace("Z", "+00:00"))

                    if event_start <= now <= event_end:
                        return "busy"

        # Check out of office status
        ooo = self.get_out_of_office_status(user_email)
        if ooo and ooo.get("status") == "scheduled":
            return "out_of_office"

        return "available"

    def sync_contacts(self, user_email: str) -> list[dict]:
        """
        Synchronize Outlook contacts with PBX

        Args:
            user_email: User's email address

        Returns:
            list: list of contacts
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return []

        if not self.authenticate():
            return []

        try:
            self.logger.info(f"Syncing contacts for {user_email}")

            url = f"{self.graph_endpoint}/users/{user_email}/contacts"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-type": "application/json",
            }
            params = {"$select": "displayName,emailAddresses,businessPhones,mobilePhone,homePhones"}

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                contacts = []
                for contact in data.get("value", []):
                    # Extract primary email
                    emails = contact.get("emailAddresses", [])
                    primary_email = emails[0].get("address") if emails else None

                    # Extract phone numbers
                    business_phones = contact.get("businessPhones", [])
                    mobile_phone = contact.get("mobilePhone")
                    home_phones = contact.get("homePhones", [])

                    contacts.append(
                        {
                            "name": contact.get("displayName"),
                            "email": primary_email,
                            "business_phone": business_phones[0] if business_phones else None,
                            "mobile_phone": mobile_phone,
                            "home_phone": home_phones[0] if home_phones else None,
                        }
                    )

                self.logger.info(f"Synced {len(contacts)} contacts for {user_email}")
                return contacts
            self.logger.error(f"Failed to sync contacts: {response.status_code} - {response.text}")
            return []

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
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
        if not self.enabled or not REQUESTS_AVAILABLE or not MSAL_AVAILABLE:
            return False

        # Authenticate first
        if not self.authenticate():
            return False

        try:
            url = f"{self.graph_endpoint}/users/{user_email}/calendar/events"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-type": "application/json",
            }

            # Extract call details
            from_number = call_details.get("from", "Unknown")
            to_number = call_details.get("to", "Unknown")
            duration = call_details.get("duration", 0)
            timestamp = call_details.get("timestamp", datetime.now(UTC).isoformat())
            direction = call_details.get("direction", "inbound")

            # Parse timestamp
            if isinstance(timestamp, str):
                start_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                start_time = datetime.now(UTC)

            # Calculate end time based on duration
            end_time = start_time + timedelta(seconds=duration)

            # Create event body
            event_body = {
                "subject": f"Phone Call - {from_number if direction == 'inbound' else to_number}",
                "body": {
                    "contentType": "text",
                    "content": "Phone call details:\n"
                    f"Direction: {direction}\n"
                    f"From: {from_number}\n"
                    f"To: {to_number}\n"
                    f"Duration: {duration} seconds",
                },
                "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
                "categories": ["Phone Call"],
                "isReminderOn": False,
            }

            self.logger.info(f"Logging call to calendar for {user_email}")
            response = requests.post(url, headers=headers, json=event_body, timeout=10)

            if response.status_code == 201:
                self.logger.info(f"Successfully logged call to calendar for {user_email}")
                return True
            self.logger.warning(
                f"Failed to log call to calendar: {response.status_code} - {response.text}"
            )
            return False

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Error logging call to calendar: {e}")
            return False

    def get_out_of_office_status(self, user_email: str) -> dict | None:
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
            url = (
                f"{self.graph_endpoint}/users/{user_email}/mailboxSettings/automaticRepliesSetting"
            )
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    # disabled, alwaysEnabled, scheduled
                    "status": data.get("status"),
                    "external_reply": data.get("externalReplyMessage"),
                    "internal_reply": data.get("internalReplyMessage"),
                    "scheduled_start": data.get("scheduledStartDateTime", {}).get("dateTime"),
                    "scheduled_end": data.get("scheduledEndDateTime", {}).get("dateTime"),
                }
            self.logger.error(f"Failed to get OOO status: {response.status_code}")
            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Error getting OOO status: {e}")
            return None

    def send_meeting_reminder(
        self,
        user_email: str,
        meeting_id: str,
        minutes_before: int = 5,
        pbx_core=None,
        extension_number: str | None = None,
    ):
        """
        Send a phone notification for upcoming meeting

        Args:
            user_email: User's email address
            meeting_id: Meeting identifier
            minutes_before: Minutes before meeting to notify
            pbx_core: Optional PBXCore instance for call origination
            extension_number: Optional extension to call (if not provided, looked up by email)

        Returns:
            bool: True if notification scheduled

        Notes:
            This implementation uses a scheduling approach to call the user's extension
            and play a meeting reminder message. In production, you might use:
            - Threading/async tasks for scheduling
            - External scheduler (cron, celery, APScheduler)
            - Message queue for deferred execution
        """
        if not self.enabled:
            self.logger.warning("Outlook integration is not enabled")
            return False

        self.logger.info(
            f"Scheduling meeting reminder for {user_email} ({minutes_before} min before)"
        )

        # Get meeting details if needed
        try:
            if not self.authenticate():
                return False

            # Fetch meeting details
            url = f"{self.graph_endpoint}/users/{user_email}/calendar/events/{meeting_id}"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                self.logger.warning(f"Failed to fetch meeting details: {response.status_code}")
                return False

            meeting = response.json()
            subject = meeting.get("subject", "Upcoming Meeting")
            start_time_str = meeting.get("start", {}).get("dateTime", "")

            if not start_time_str:
                self.logger.error("Meeting has no start time")
                return False

            # Parse meeting start time - handle various ISO formats
            try:
                # Try with 'Z' suffix (Zulu time)
                if start_time_str.endswith("Z"):
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                # Try direct ISO format parsing
                elif "+" in start_time_str or start_time_str.endswith("+00:00"):
                    start_time = datetime.fromisoformat(start_time_str)
                else:
                    # Assume UTC if no timezone specified
                    start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=UTC)
            except ValueError as e:
                self.logger.error(f"Failed to parse meeting start time '{start_time_str}': {e}")
                return False

            reminder_time = start_time - timedelta(minutes=minutes_before)
            now = datetime.now(UTC)

            # Calculate delay until reminder should be sent
            delay_seconds = (reminder_time - now).total_seconds()

            if delay_seconds < 0:
                self.logger.warning("Meeting reminder time has already passed")
                return False

            self.logger.info(
                f"Meeting '{subject}' reminder scheduled for {reminder_time} (in {delay_seconds:.0f} seconds)"
            )

            # If PBX core provided, schedule the reminder
            # NOTE: This uses threading.Timer which is lost on application restart.
            # For production use, consider:
            # - APScheduler (https://apscheduler.readthedocs.io/)
            # - Celery with Redis/RabbitMQ (https://docs.celeryproject.org/)
            # - Database-backed task queue
            # - Cron jobs for scheduled tasks
            if pbx_core:
                # Find extension by email if not provided
                if not extension_number and hasattr(pbx_core, "extension_registry"):
                    for ext_num, ext in pbx_core.extension_registry.extensions.items():
                        if hasattr(ext, "config") and ext.config.get("email") == user_email:
                            extension_number = ext_num
                            break

                if not extension_number:
                    self.logger.error(f"Could not find extension for email {user_email}")
                    return False

                self.logger.info(f"Will call extension {extension_number} at reminder time")

                # Schedule the reminder using threading
                import threading

                def send_reminder():
                    """Execute the reminder call"""
                    try:
                        self.logger.info(
                            f"Sending meeting reminder to extension {extension_number}"
                        )

                        # In production, this would:
                        # 1. Originate a call to the extension
                        # 2. Play a TTS or pre-recorded message:
                        #    "You have a meeting in {minutes_before} minutes: {subject}"
                        # 3. Optionally provide options:
                        #    "Press 1 to join now, press 2 to snooze, press 3 to dismiss"
                        # 4. Handle DTMF responses

                        # For now, log the reminder action
                        self.logger.info(
                            f"REMINDER: Extension {extension_number} has meeting '{subject}' "
                            f"starting at {start_time.strftime('%H:%M')}"
                        )

                        # If trunk system available, could originate call here
                        if hasattr(pbx_core, "call_manager"):
                            self.logger.info(
                                f"Call reminder system ready for extension {extension_number}"
                            )
                            # In production:
                            # pbx_core.originate_call(extension_number,
                            # 'reminder', message)

                    except Exception as e:
                        self.logger.error(f"Error sending meeting reminder: {e}")

                # Schedule the timer
                timer = threading.Timer(delay_seconds, send_reminder)
                timer.daemon = True  # Don't block shutdown
                timer.start()

                self.logger.info(f"Meeting reminder scheduled successfully for {extension_number}")
                return True
            # No PBX core - just log the intent
            self.logger.warning(
                "Meeting reminder scheduling requires PBX core for call origination.\n"
                "To enable reminders:\n"
                "1. Pass pbx_core parameter to this method\n"
                "2. Ensure extension has email configured in database/config\n"
                "3. PBX will call extension and play reminder message\n"
                f"Meeting: '{subject}' at {start_time.strftime('%Y-%m-%d %H:%M %Z')}"
            )
            return False

        except Exception as e:
            self.logger.error(f"Error scheduling meeting reminder: {e}")
            import traceback

            traceback.print_exc()
            return False
