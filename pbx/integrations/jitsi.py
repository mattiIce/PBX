"""
Jitsi Meet Integration (Free, Open-Source Alternative to Zoom)
Enables video conferencing, screen sharing, and recording
"""

import re
import time
from datetime import UTC, datetime

from pbx.utils.logger import get_logger

try:
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


class JitsiIntegration:
    """Jitsi Meet integration handler (100% Free & Open Source)"""

    def __init__(self, config: dict):
        """
        Initialize Jitsi integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get("integrations.jitsi.enabled", False)

        # Can use public server or self-hosted
        self.server_url = config.get("integrations.jitsi.server_url", "https://meet.jit.si")

        # Optional: JWT token for secure rooms (if using Jitsi with auth)
        self.app_id = config.get("integrations.jitsi.app_id")
        self.app_secret = config.get("integrations.jitsi.app_secret")

        # Feature flags
        self.auto_create_rooms = config.get("integrations.jitsi.auto_create_rooms", True)
        self.enable_recording = config.get("integrations.jitsi.enable_recording", False)
        self.enable_lobby = config.get("integrations.jitsi.enable_lobby", False)

        # Room configuration
        self.default_room_config = {
            "startWithAudioMuted": False,
            "startWithVideoMuted": False,
            "enableWelcomePage": False,
            "prejoinPageEnabled": True,
            "requireDisplayName": True,
        }

        if self.enabled:
            if not REQUESTS_AVAILABLE:
                self.logger.warning(
                    "Jitsi integration: 'requests' library recommended. "
                    "Install with: pip install requests"
                )
            self.logger.info(f"Jitsi Meet integration enabled (Server: {self.server_url})")
            if self.server_url == "https://meet.jit.si":
                self.logger.info(
                    "Using public Jitsi server (meet.jit.si). "
                    "For production, consider self-hosting: "
                    "https://jitsi.github.io/handbook/"
                )

    def create_meeting(
        self,
        room_name: str | None = None,
        subject: str | None = None,
        moderator_name: str | None = None,
        participant_names: list[str] | None = None,
        scheduled_time: datetime | None = None,
        duration_minutes: int = 60,
    ) -> dict:
        """
        Create a Jitsi meeting room

        Args:
            room_name: Custom room name (auto-generated if not provided)
            subject: Meeting subject/title
            moderator_name: Name of meeting moderator
            participant_names: list of participant names (optional)
            scheduled_time: When meeting is scheduled (None = instant)
            duration_minutes: Expected duration in minutes

        Returns:
            Dictionary with meeting details:
            {
                'success': bool,
                'room_id': str,
                'room_name': str,
                'url': str,
                'moderator_url': str (with JWT if configured),
                'subject': str,
                'scheduled_time': datetime,
                'duration': int,
                'created_at': datetime
            }
        """
        if not self.enabled:
            return {"success": False, "error": "Jitsi integration is disabled"}

        try:
            # Generate room name if not provided
            if not room_name:
                timestamp = int(time.time())
                room_name = f"pbx-meeting-{timestamp}"

            # Sanitize room name (Jitsi requirements)
            room_name = self._sanitize_room_name(room_name)

            # Generate meeting URL
            meeting_url = f"{self.server_url}/{room_name}"

            # Generate moderator URL with JWT if configured
            moderator_url = meeting_url
            if self.app_id and self.app_secret:
                jwt_token = self._generate_jwt_token(
                    room_name, moderator_name or "Moderator", is_moderator=True
                )
                moderator_url = f"{meeting_url}?jwt={jwt_token}"

            # Store meeting info
            meeting = {
                "success": True,
                "room_id": room_name,
                "room_name": room_name,
                "url": meeting_url,
                "moderator_url": moderator_url,
                "subject": subject or f"Meeting - {room_name}",
                "scheduled_time": scheduled_time or datetime.now(UTC),
                "duration": duration_minutes,
                "created_at": datetime.now(UTC),
                "server": self.server_url,
                "moderator": moderator_name,
                "participants": participant_names or [],
            }

            self.logger.info(f"Jitsi meeting created: {room_name} ({meeting_url})")

            return meeting

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to create Jitsi meeting: {e}")
            return {"success": False, "error": str(e)}

    def get_participant_url(
        self, room_name: str, participant_name: str, is_moderator: bool = False
    ) -> str:
        """
        Generate participant URL for joining a meeting

        Args:
            room_name: Room identifier
            participant_name: Participant display name
            is_moderator: Whether participant is moderator

        Returns:
            Meeting URL with JWT token if configured
        """
        url = f"{self.server_url}/{room_name}"

        # Add display name to URL
        url += f'#userInfo.displayName="{participant_name}"'

        # Add JWT token if configured
        if self.app_id and self.app_secret:
            jwt_token = self._generate_jwt_token(room_name, participant_name, is_moderator)
            url = f"{self.server_url}/{room_name}?jwt={jwt_token}"

        return url

    def create_instant_meeting(self, extension: str, contact_name: str | None = None) -> dict:
        """
        Create instant meeting for call escalation

        Args:
            extension: Extension number creating the meeting
            contact_name: Name of person being invited

        Returns:
            Meeting details dictionary
        """
        room_name = f"call-{extension}-{int(time.time())}"
        subject = f"Video Call with {contact_name or 'Contact'}"

        return self.create_meeting(
            room_name=room_name,
            subject=subject,
            moderator_name=f"Extension {extension}",
            participant_names=[contact_name] if contact_name else [],
        )

    def create_scheduled_meeting(
        self,
        organizer_extension: str,
        scheduled_time: datetime,
        duration_minutes: int = 60,
        subject: str | None = None,
        participants: list[str] | None = None,
    ) -> dict:
        """
        Create scheduled meeting for future time

        Args:
            organizer_extension: Extension organizing the meeting
            scheduled_time: When meeting should start
            duration_minutes: Meeting duration
            subject: Meeting topic
            participants: list of participant names/extensions

        Returns:
            Meeting details dictionary
        """
        timestamp = scheduled_time.strftime("%Y%m%d-%H%M")
        room_name = f"scheduled-{organizer_extension}-{timestamp}"

        return self.create_meeting(
            room_name=room_name,
            subject=subject or "Scheduled Meeting",
            moderator_name=f"Extension {organizer_extension}",
            participant_names=participants,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
        )

    def _sanitize_room_name(self, room_name: str) -> str:
        """
        Sanitize room name for Jitsi compliance

        Args:
            room_name: Original room name

        Returns:
            Sanitized room name (lowercase, alphanumeric, hyphens)
        """
        # Convert to lowercase
        name = room_name.lower()

        # Replace spaces and special chars with hyphens
        name = re.sub(r"[^a-z0-9-]", "-", name)

        # Remove consecutive hyphens
        name = re.sub(r"-+", "-", name)

        # Remove leading/trailing hyphens
        name = name.strip("-")

        return name

    def _generate_jwt_token(
        self, room_name: str, user_name: str, is_moderator: bool = False, expiry_hours: int = 24
    ) -> str:
        """
        Generate JWT token for secure Jitsi rooms

        Args:
            room_name: Room identifier
            user_name: User display name
            is_moderator: Whether user is moderator
            expiry_hours: Token expiry in hours

        Returns:
            JWT token string
        """
        if not JWT_AVAILABLE:
            self.logger.warning("JWT library not available. Install with: pip install PyJWT")
            return ""

        try:
            now = int(time.time())
            payload = {
                "iss": self.app_id,
                "sub": self.server_url.replace("https://", "").replace("http://", ""),
                "aud": self.app_id,
                "room": room_name,
                "exp": now + (expiry_hours * 3600),
                "nb": now - 10,
                "context": {"user": {"name": user_name, "moderator": is_moderator}},
            }

            token = jwt.encode(payload, self.app_secret, algorithm="HS256")

            return token

        except ImportError:
            self.logger.warning("JWT library not available. Install with: pip install PyJWT")
            return ""
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to generate JWT token: {e}")
            return ""

    def get_meeting_info(self, room_name: str) -> dict | None:
        """
        Get information about a meeting room

        Note: Public Jitsi doesn't provide room info API.
        For self-hosted Jitsi, you can query Prosody or Jicofo.

        Args:
            room_name: Room identifier

        Returns:
            Meeting info dict or None
        """
        # This is a placeholder - would need Jitsi server API
        return {
            "room_id": room_name,
            "url": f"{self.server_url}/{room_name}",
            "server": self.server_url,
            "note": "Room info requires self-hosted Jitsi with API access",
        }

    def end_meeting(self, room_name: str) -> bool:
        """
        End a meeting (moderator action)

        Note: Requires self-hosted Jitsi with API access

        Args:
            room_name: Room to end

        Returns:
            bool: Success status
        """
        self.logger.info(
            f"End meeting requested for {room_name}. "
            "Moderator should use 'End meeting' button in Jitsi interface."
        )
        # Would need Jitsi Videobridge API for programmatic control
        return True

    def get_active_participants(self, room_name: str) -> list[str]:
        """
        Get list of active participants in a room

        Note: Requires self-hosted Jitsi with API/WebSocket access

        Args:
            room_name: Room identifier

        Returns:
            list of participant names
        """
        # Would need Jitsi Videobridge API or Prosody query
        self.logger.debug(
            f"Participant list for {room_name} requires self-hosted Jitsi with API access"
        )
        return []

    def create_conference_bridge(self, conference_id: str, participants: list[str]) -> dict:
        """
        Create a Jitsi room for PBX conference bridge

        Args:
            conference_id: Conference/bridge number
            participants: list of extension numbers

        Returns:
            Meeting details with dial-in info
        """
        room_name = f"conference-{conference_id}"

        return self.create_meeting(
            room_name=room_name,
            subject=f"Conference Bridge {conference_id}",
            moderator_name=f"Conference {conference_id}",
            participant_names=[f"Extension {p}" for p in participants],
        )

    def get_embed_code(self, room_name: str, width: int = 800, height: int = 600) -> str:
        """
        Generate HTML embed code for Jitsi meeting

        Args:
            room_name: Room identifier
            width: iFrame width
            height: iFrame height

        Returns:
            HTML embed code
        """
        url = f"{self.server_url}/{room_name}"

        embed = f"""
<iframe
    allow="camera; microphone; fullscreen; display-capture; autoplay"
    src="{url}"
    style="height: {height}px; width: {width}px; border: 0px;">
</iframe>
"""
        return embed.strip()


# Export class
__all__ = ["JitsiIntegration"]
