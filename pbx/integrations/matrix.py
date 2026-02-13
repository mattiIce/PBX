"""
Matrix Integration (Free, Open-Source Alternative to Slack/Teams Chat)
Enables team messaging, file sharing, and real-time notifications
"""

import os
import re
import time
from datetime import datetime
from typing import Any

from pbx.utils.logger import get_logger

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class MatrixIntegration:
    """Matrix integration handler (100% Free & Open Source)"""

    def __init__(self, config: dict):
        """
        Initialize Matrix integration

        Args:
            config: Integration configuration from config.yml
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = config.get("integrations.matrix.enabled", False)

        # Matrix homeserver details
        self.homeserver_url = config.get("integrations.matrix.homeserver_url", "https://matrix.org")

        # Bot account for sending notifications
        self.bot_username = config.get("integrations.matrix.bot_username")
        self.bot_password = config.get("integrations.matrix.bot_password")
        self.bot_access_token = None

        # Notification settings
        self.notification_room = config.get("integrations.matrix.notification_room")
        self.voicemail_room = config.get("integrations.matrix.voicemail_room")
        self.missed_call_notifications = config.get(
            "integrations.matrix.missed_call_notifications", True
        )

        if self.enabled:
            if not REQUESTS_AVAILABLE:
                self.logger.error(
                    "Matrix integration requires 'requests' library. "
                    "Install with: pip install requests"
                )
                self.enabled = False
            elif not all([self.homeserver_url, self.bot_username, self.bot_password]):
                self.logger.error(
                    "Matrix integration requires homeserver_url, " "bot_username, and bot_password"
                )
                self.enabled = False
            else:
                self.logger.info(f"Matrix integration enabled (Server: {self.homeserver_url})")
                # Authenticate bot
                self._authenticate()

    def _authenticate(self) -> bool:
        """
        Authenticate bot account and get access token

        Returns:
            bool: Success status
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return False

        try:
            url = f"{self.homeserver_url}/_matrix/client/r0/login"

            data = {
                "type": "m.login.password",
                "user": self.bot_username,
                "password": self.bot_password,
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                self.bot_access_token = result.get("access_token")
                self.logger.info("Matrix bot authenticated successfully")
                return True
            else:
                self.logger.error(f"Matrix authentication failed: {response.status_code}")
                return False

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Matrix authentication error: {e}")
            return False

    def _make_request(
        self, method: str, endpoint: str, data: dict = None, params: dict = None
    ) -> dict | None:
        """
        Make authenticated API request to Matrix

        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint
            data: Request body data
            params: URL parameters

        Returns:
            Response data or None on error
        """
        if not self.enabled or not REQUESTS_AVAILABLE or not self.bot_access_token:
            return None

        try:
            url = f"{self.homeserver_url}/_matrix/client/r0/{endpoint}"

            headers = {
                "Authorization": f"Bearer {self.bot_access_token}",
                "Content-type": "application/json",
            }

            response = requests.request(
                method=method, url=url, json=data, params=params, headers=headers, timeout=10
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                self.logger.error(f"Matrix API error: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            self.logger.error(f"Matrix API request failed: {e}")
            return None

    def send_message(self, room_id: str, message: str, msg_type: str = "m.text") -> str | None:
        """
        Send message to Matrix room

        Args:
            room_id: Matrix room ID
            message: Message text (supports markdown)
            msg_type: Message type (m.text, m.notice, m.emote)

        Returns:
            Event ID or None on error
        """
        if not self.enabled:
            return None

        try:
            # Generate transaction ID
            txn_id = f"pbx_{int(time.time() * 1000)}"

            data = {
                "msgtype": msg_type,
                "body": message,
                "format": "org.matrix.custom.html",
                "formatted_body": self._markdown_to_html(message),
            }

            result = self._make_request(
                "PUT", f"rooms/{room_id}/send/m.room.message/{txn_id}", data=data
            )

            if result:
                return result.get("event_id")

            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to send Matrix message: {e}")
            return None

    def send_notification(self, message: str, room_id: str = None) -> bool:
        """
        Send notification to default room

        Args:
            message: Notification message
            room_id: Specific room ID (uses default if not provided)

        Returns:
            bool: Success status
        """
        room = room_id or self.notification_room

        if not room:
            self.logger.warning("No notification room configured")
            return False

        event_id = self.send_message(room, message, msg_type="m.notice")
        return event_id is not None

    def send_missed_call_alert(self, extension: str, caller_id: str, timestamp: datetime) -> bool:
        """
        Send missed call notification

        Args:
            extension: Extension that missed the call
            caller_id: Caller phone number
            timestamp: When call occurred

        Returns:
            bool: Success status
        """
        if not self.enabled or not self.missed_call_notifications:
            return False

        message = (
            "📞 **Missed Call**\n\n"
            f"Extension: {extension}\n"
            f"From: {caller_id}\n"
            f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return self.send_notification(message)

    def send_voicemail_notification(
        self, extension: str, caller_id: str, duration: int, transcription: str = None
    ) -> bool:
        """
        Send voicemail notification to Matrix

        Args:
            extension: Extension receiving voicemail
            caller_id: Caller phone number
            duration: Voicemail duration in seconds
            transcription: Optional transcription text

        Returns:
            bool: Success status
        """
        if not self.enabled:
            return False

        room = self.voicemail_room or self.notification_room

        if not room:
            return False

        message = (
            "📬 **New Voicemail**\n\n"
            f"Extension: {extension}\n"
            f"From: {caller_id}\n"
            f"Duration: {duration}s"
        )

        if transcription:
            message += f"\n\n**Transcription:**\n{transcription}"

        return self.send_notification(message, room_id=room)

    def create_room(
        self, name: str, topic: str = None, invite_users: list[str] = None
    ) -> str | None:
        """
        Create new Matrix room

        Args:
            name: Room name
            topic: Room topic/description
            invite_users: list of user IDs to invite

        Returns:
            Room ID or None on error
        """
        if not self.enabled:
            return None

        try:
            data: dict[str, Any] = {"name": name, "preset": "private_chat", "visibility": "private"}

            if topic:
                data["topic"] = topic

            if invite_users:
                data["invite"] = invite_users

            result = self._make_request("POST", "createRoom", data=data)

            if result:
                room_id = result.get("room_id")
                self.logger.info(f"Created Matrix room: {room_id}")
                return room_id

            return None

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to create room: {e}")
            return None

    def invite_to_room(self, room_id: str, user_id: str) -> bool:
        """
        Invite user to room

        Args:
            room_id: Matrix room ID
            user_id: User Matrix ID (@user:server.com)

        Returns:
            bool: Success status
        """
        if not self.enabled:
            return False

        try:
            data = {"user_id": user_id}

            result = self._make_request("POST", f"rooms/{room_id}/invite", data=data)

            return result is not None

        except requests.RequestException as e:
            self.logger.error(f"Failed to invite user: {e}")
            return False

    def upload_file(
        self, file_path: str, content_type: str = "application/octet-stream"
    ) -> str | None:
        """
        Upload file to Matrix homeserver

        Args:
            file_path: Path to file
            content_type: MIME type

        Returns:
            MXC URI or None on error
        """
        if not self.enabled or not REQUESTS_AVAILABLE or not self.bot_access_token:
            return None

        try:

            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None

            url = f"{self.homeserver_url}/_matrix/media/r0/upload"

            headers = {
                "Authorization": f"Bearer {self.bot_access_token}",
                "Content-type": content_type,
            }

            with open(file_path, "rb") as f:
                response = requests.post(url, data=f.read(), headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result.get("content_uri")
            else:
                self.logger.error(f"File upload failed: {response.status_code}")
                return None

        except (KeyError, OSError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to upload file: {e}")
            return None

    def send_file(
        self,
        room_id: str,
        file_path: str,
        filename: str = None,
        content_type: str = "application/octet-stream",
    ) -> str | None:
        """
        Send file to room

        Args:
            room_id: Matrix room ID
            file_path: Path to file
            filename: Display filename (uses actual filename if not provided)
            content_type: MIME type

        Returns:
            Event ID or None on error
        """
        if not self.enabled:
            return None

        try:

            # Upload file
            mxc_uri = self.upload_file(file_path, content_type)

            if not mxc_uri:
                return None

            # Send file message
            txn_id = f"pbx_{int(time.time() * 1000)}"

            if not filename:
                filename = os.path.basename(file_path)

            data = {
                "msgtype": "m.file",
                "body": filename,
                "url": mxc_uri,
                "info": {"size": os.path.getsize(file_path), "mimetype": content_type},
            }

            result = self._make_request(
                "PUT", f"rooms/{room_id}/send/m.room.message/{txn_id}", data=data
            )

            if result:
                return result.get("event_id")

            return None

        except (KeyError, OSError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to send file: {e}")
            return None

    def _markdown_to_html(self, markdown: str) -> str:
        """
        Convert simple markdown to HTML for Matrix

        Args:
            markdown: Markdown text

        Returns:
            HTML formatted text
        """
        html = markdown

        # Bold
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        # Italic
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # Code
        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)

        # Line breaks
        html = html.replace("\n", "<br/>")

        return html

    def get_room_members(self, room_id: str) -> list[str]:
        """
        Get list of room members

        Args:
            room_id: Matrix room ID

        Returns:
            list of user IDs
        """
        if not self.enabled:
            return []

        try:
            result = self._make_request("GET", f"rooms/{room_id}/members")

            if result and result.get("chunk"):
                members = []
                for event in result["chunk"]:
                    if event.get("type") == "m.room.member":
                        if event.get("membership") == "join":
                            members.append(event.get("state_key"))
                return members

            return []

        except (KeyError, TypeError, ValueError, requests.RequestException) as e:
            self.logger.error(f"Failed to get room members: {e}")
            return []


# Export class
__all__ = ["MatrixIntegration"]
