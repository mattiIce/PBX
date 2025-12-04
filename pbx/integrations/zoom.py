"""
Zoom Integration
Enables Zoom Phone, video meetings, and collaboration features
"""
from pbx.utils.logger import get_logger
from datetime import datetime, timedelta
from typing import Optional, Dict

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Token expiry buffer in seconds (refresh 5 minutes before expiry)
TOKEN_EXPIRY_BUFFER_SECONDS = 300


class ZoomIntegration:
    """Zoom integration handler"""

    def __init__(self, config: dict):
        """
        Initialize Zoom integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get('integrations.zoom.enabled', False)
        self.account_id = config.get('integrations.zoom.account_id')
        self.client_id = config.get('integrations.zoom.client_id')
        self.client_secret = config.get('integrations.zoom.client_secret')
        self.phone_enabled = config.get('integrations.zoom.phone_enabled', False)
        self.api_base_url = config.get('integrations.zoom.api_base_url', 'https://api.zoom.us/v2')
        self.access_token = None
        self.token_expiry = None

        if self.enabled:
            if not REQUESTS_AVAILABLE:
                self.logger.error("Zoom integration requires 'requests' library. Install with: pip install requests")
                self.enabled = False
            else:
                self.logger.info("Zoom integration enabled")

    def authenticate(self) -> bool:
        """
        Authenticate with Zoom using Server-to-Server OAuth

        Returns:
            bool: True if authentication successful
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return False

        # Check if token is still valid
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return True

        if not all([self.account_id, self.client_id, self.client_secret]):
            self.logger.error("Zoom credentials not configured properly")
            return False

        try:
            # Server-to-Server OAuth token endpoint
            token_url = "https://zoom.us/oauth/token"
            
            params = {
                'grant_type': 'account_credentials',
                'account_id': self.account_id
            }
            
            auth = (self.client_id, self.client_secret)
            
            self.logger.info("Authenticating with Zoom API...")
            response = requests.post(token_url, params=params, auth=auth, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                expires_in = data.get('expires_in', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - TOKEN_EXPIRY_BUFFER_SECONDS)
                
                self.logger.info("Zoom authentication successful")
                return True
            else:
                self.logger.error(f"Zoom authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Zoom authentication error: {e}")
            return False

    def create_meeting(self, topic: str, start_time: str = None, duration_minutes: int = 60, **kwargs) -> Optional[Dict]:
        """
        Create a Zoom meeting

        Args:
            topic: Meeting topic
            start_time: Start time (ISO format, optional)
            duration_minutes: Duration in minutes
            **kwargs: Additional meeting settings

        Returns:
            dict: Meeting details (join URL, meeting ID, etc.) or None
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return None

        # Authenticate first
        if not self.authenticate():
            return None

        try:
            url = f"{self.api_base_url}/users/me/meetings"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Build meeting payload
            payload = {
                'topic': topic,
                'type': 2 if start_time else 1,  # 1=instant, 2=scheduled
                'duration': duration_minutes,
                'settings': {
                    'host_video': kwargs.get('host_video', True),
                    'participant_video': kwargs.get('participant_video', True),
                    'join_before_host': kwargs.get('join_before_host', False),
                    'mute_upon_entry': kwargs.get('mute_upon_entry', False),
                    'auto_recording': kwargs.get('auto_recording', 'none')
                }
            }
            
            if start_time:
                payload['start_time'] = start_time
                payload['timezone'] = kwargs.get('timezone', 'America/New_York')
            
            self.logger.info(f"Creating Zoom meeting: {topic}")
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                meeting_data = response.json()
                self.logger.info(f"Zoom meeting created: {meeting_data.get('id')}")
                
                return {
                    'meeting_id': meeting_data.get('id'),
                    'join_url': meeting_data.get('join_url'),
                    'start_url': meeting_data.get('start_url'),
                    'password': meeting_data.get('password'),
                    'topic': meeting_data.get('topic'),
                    'start_time': meeting_data.get('start_time'),
                    'duration': meeting_data.get('duration')
                }
            else:
                self.logger.error(f"Failed to create Zoom meeting: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating Zoom meeting: {e}")
            return None

    def start_instant_meeting(self, host_extension: str) -> Optional[Dict]:
        """
        Start an instant Zoom meeting from desk phone

        Args:
            host_extension: PBX extension starting the meeting

        Returns:
            dict: Meeting details or None
        """
        if not self.enabled or not self.phone_enabled:
            return None

        self.logger.info(f"Starting instant Zoom meeting for {host_extension}")
        
        # Create an instant meeting (type=1, no start_time)
        topic = f"Instant Meeting - Extension {host_extension}"
        return self.create_meeting(topic=topic, duration_minutes=60)

    def route_to_zoom_phone(self, from_number: str, to_number: str):
        """
        Route call through Zoom Phone

        Args:
            from_number: Caller's number
            to_number: Destination number

        Returns:
            bool: True if routed successfully
        """
        if not self.enabled or not self.phone_enabled:
            return False

        self.logger.info(f"Routing call from {from_number} to {to_number} via Zoom Phone")
        # TODO: Use SIP trunking to route to Zoom Phone
        # SIP URI: {number}@pbx.zoom.us

        return False

    def get_phone_user_status(self, user_id: str):
        """
        Get Zoom Phone user status

        Args:
            user_id: Zoom user ID

        Returns:
            dict: User status (available, busy, etc.) or None
        """
        if not self.enabled or not self.phone_enabled:
            return None

        # TODO: Query Zoom Phone API
        # GET https://api.zoom.us/v2/phone/users/{userId}/settings

        return None
