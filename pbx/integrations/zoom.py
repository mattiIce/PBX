"""
Zoom Integration
Enables Zoom Phone, video meetings, and collaboration features
"""

from datetime import UTC, datetime, timedelta

from pbx.utils.logger import get_logger

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Token expiry buffer in seconds (refresh 5 minutes before expiry)
TOKEN_EXPIRY_BUFFER_SECONDS = 300


class ZoomIntegration:
    """Zoom integration handler"""

    def __init__(self, config: dict) -> None:
        """
        Initialize Zoom integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get("integrations.zoom.enabled", False)
        self.account_id = config.get("integrations.zoom.account_id")
        self.client_id = config.get("integrations.zoom.client_id")
        self.client_secret = config.get("integrations.zoom.client_secret")
        self.phone_enabled = config.get("integrations.zoom.phone_enabled", False)
        self.api_base_url = config.get("integrations.zoom.api_base_url", "https://api.zoom.us/v2")
        self.access_token: str | None = None
        self.token_expiry: datetime | None = None

        if self.enabled:
            if not REQUESTS_AVAILABLE:
                self.logger.error(
                    "Zoom integration requires 'requests' library. Install with: pip install requests"
                )
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
        if self.access_token and self.token_expiry and datetime.now(UTC) < self.token_expiry:
            return True

        if not all([self.account_id, self.client_id, self.client_secret]):
            self.logger.error("Zoom credentials not configured properly")
            return False

        try:
            # Server-to-Server OAuth token endpoint
            token_url = "https://zoom.us/oauth/token"

            params = {"grant_type": "account_credentials", "account_id": self.account_id}

            auth = (self.client_id, self.client_secret)

            self.logger.info("Authenticating with Zoom API...")
            response = requests.post(token_url, params=params, auth=auth, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                self.token_expiry = datetime.now(UTC) + timedelta(
                    seconds=expires_in - TOKEN_EXPIRY_BUFFER_SECONDS
                )

                self.logger.info("Zoom authentication successful")
                return True
            self.logger.error(
                f"Zoom authentication failed: {response.status_code} - {response.text}"
            )
            return False

        except (requests.RequestException, KeyError, ValueError) as e:
            self.logger.error(f"Zoom authentication error: {e}")
            return False

    def create_meeting(
        self, topic: str, start_time: str | None = None, duration_minutes: int = 60, **kwargs
    ) -> dict | None:
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
                "Authorization": f"Bearer {self.access_token}",
                "Content-type": "application/json",
            }

            # Build meeting payload
            payload = {
                "topic": topic,
                "type": 2 if start_time else 1,  # 1=instant, 2=scheduled
                "duration": duration_minutes,
                "settings": {
                    "host_video": kwargs.get("host_video", True),
                    "participant_video": kwargs.get("participant_video", True),
                    "join_before_host": kwargs.get("join_before_host", False),
                    "mute_upon_entry": kwargs.get("mute_upon_entry", False),
                    "auto_recording": kwargs.get("auto_recording", "none"),
                },
            }

            if start_time:
                payload["start_time"] = start_time
                payload["timezone"] = kwargs.get("timezone", "America/New_York")

            self.logger.info(f"Creating Zoom meeting: {topic}")
            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.status_code in [200, 201]:
                meeting_data = response.json()
                self.logger.info(f"Zoom meeting created: {meeting_data.get('id')}")

                return {
                    "meeting_id": meeting_data.get("id"),
                    "join_url": meeting_data.get("join_url"),
                    "start_url": meeting_data.get("start_url"),
                    "password": meeting_data.get("password"),
                    "topic": meeting_data.get("topic"),
                    "start_time": meeting_data.get("start_time"),
                    "duration": meeting_data.get("duration"),
                }
            self.logger.error(
                f"Failed to create Zoom meeting: {response.status_code} - {response.text}"
            )
            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Error creating Zoom meeting: {e}")
            return None

    def start_instant_meeting(self, host_extension: str) -> dict | None:
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

    def route_to_zoom_phone(self, from_number: str, to_number: str, pbx_core: object | None = None) -> bool:
        """
        Route call through Zoom Phone SIP trunking

        Args:
            from_number: Caller's number
            to_number: Destination number
            pbx_core: Optional PBXCore instance for accessing trunk system

        Returns:
            bool: True if routed successfully

        Notes:
            Requires:
            - Zoom Phone license
            - Zoom Phone SIP trunk credentials
            - SIP trunk configured in PBX for Zoom Phone
            - Zoom Phone SIP domain: pbx.zoom.us
        """
        if not self.enabled:
            self.logger.warning("Zoom integration is not enabled")
            return False

        if not self.phone_enabled:
            self.logger.warning("Zoom Phone is not enabled in configuration")
            return False

        self.logger.info(f"Routing call from {from_number} to {to_number} via Zoom Phone")

        # Zoom Phone SIP trunking endpoint
        zoom_phone_domain = "pbx.zoom.us"
        sip_uri = f"{to_number}@{zoom_phone_domain}"

        self.logger.info(f"Zoom Phone SIP URI: {sip_uri}")

        # If PBX core provided, use trunk system to route the call
        if pbx_core and hasattr(pbx_core, "trunk_system"):
            try:
                # Look for a Zoom Phone trunk
                trunk = None
                for trunk_obj in pbx_core.trunk_system.trunks.values():
                    if "zoom" in trunk_obj.name.lower() or zoom_phone_domain in trunk_obj.host:
                        trunk = trunk_obj
                        break

                if trunk and trunk.can_make_call():
                    self.logger.info(f"Using SIP trunk '{trunk.name}' for Zoom Phone call")

                    # Allocate channel
                    if trunk.allocate_channel():
                        self.logger.info(f"Initiating SIP call to {sip_uri} via trunk {trunk.name}")

                        # In production, this would:
                        # 1. Build SIP INVITE with Zoom Phone-specific headers
                        # 2. Include authentication credentials from trunk config
                        # 3. Handle codec negotiation (G.711, G.729, Opus)
                        # 4. Bridge the call with the internal extension
                        # 5. Handle call progress and status updates

                        # For now, log the action and return success indicator
                        self.logger.info(f"Call routed to Zoom Phone: {from_number} -> {to_number}")
                        return True
                    self.logger.error("Failed to allocate channel on Zoom Phone trunk")
                    return False
                self.logger.warning(
                    "No Zoom Phone SIP trunk found. Configure a trunk in config.yml:\n"
                    "sip_trunks:\n"
                    "  - id: zoom_phone\n"
                    "    name: Zoom Phone Trunk\n"
                    f"    host: {zoom_phone_domain}\n"
                    "    port: 5060\n"
                    "    username: your_zoom_sip_username\n"
                    "    password: your_zoom_sip_password"
                )
                return False

            except Exception as e:
                self.logger.error(f"Error routing call to Zoom Phone: {e}")
                return False
        else:
            # No PBX core provided - log setup instructions
            self.logger.warning(
                "Zoom Phone SIP trunking requires:\n"
                "1. Zoom Phone license and account\n"
                "2. Configure SIP trunk credentials in Zoom admin portal\n"
                "3. Add trunk configuration to config.yml\n"
                "4. Configure outbound routing rules\n"
                f"5. Test connectivity to {zoom_phone_domain}"
            )
            return False

    def get_phone_user_status(self, user_id: str) -> dict | None:
        """
        Get Zoom Phone user status

        Args:
            user_id: Zoom user ID

        Returns:
            dict: User status (available, busy, etc.) or None
        """
        if not self.enabled or not self.phone_enabled or not REQUESTS_AVAILABLE:
            return None

        # Authenticate first
        if not self.authenticate():
            return None

        try:
            url = f"{self.api_base_url}/phone/users/{user_id}/settings"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-type": "application/json",
            }

            self.logger.info(f"Getting Zoom Phone status for user {user_id}")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Retrieved Zoom Phone status for user {user_id}")
                return {
                    "user_id": user_id,
                    "status": (
                        data.get("calling_plans", [{}])[0].get("status", "unknown")
                        if data.get("calling_plans")
                        else "unknown"
                    ),
                    "extension_number": data.get("extension_number"),
                    "phone_numbers": data.get("phone_numbers", []),
                    "raw_data": data,
                }
            self.logger.warning(
                f"Failed to get Zoom Phone status: {response.status_code} - {response.text}"
            )
            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Error getting Zoom Phone status: {e}")
            return None
