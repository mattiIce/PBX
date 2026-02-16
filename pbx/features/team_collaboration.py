"""
Team Messaging Framework
Built-in chat platform for team collaboration
"""

import sqlite3

from pbx.utils.logger import get_logger
from typing import Any


class TeamMessagingEngine:
    """
    Team messaging framework
    Provides chat channels and direct messaging
    """

    def __init__(self, db_backend: Any | None, config: dict) -> None:
        """
        Initialize team messaging engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = config.get("team_messaging.enabled", False)

        self.logger.info("Team Messaging Framework initialized")

    def create_channel(self, channel_data: dict) -> int | None:
        """
        Create messaging channel

        Args:
            channel_data: Channel configuration

        Returns:
            Channel ID or None
        """
        try:
            self.db.execute(
                (
                    """INSERT INTO team_messaging_channels
                   (channel_name, description, is_private, created_by)
                   VALUES (?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO team_messaging_channels
                   (channel_name, description, is_private, created_by)
                   VALUES (%s, %s, %s, %s)"""
                ),
                (
                    channel_data["channel_name"],
                    channel_data.get("description", ""),
                    channel_data.get("is_private", False),
                    channel_data.get("created_by"),
                ),
            )

            # Get created channel ID
            result = self.db.execute(
                (
                    "SELECT id FROM team_messaging_channels WHERE channel_name = ?"
                    if self.db.db_type == "sqlite"
                    else "SELECT id FROM team_messaging_channels WHERE channel_name = %s"
                ),
                (channel_data["channel_name"],),
            )

            if result and result[0]:
                channel_id = result[0][0]

                # Add creator as admin
                if channel_data.get("created_by"):
                    self.add_member(channel_id, channel_data["created_by"], "admin")

                self.logger.info(f"Created messaging channel: {channel_data['channel_name']}")
                return channel_id

            return None

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to create messaging channel: {e}")
            return None

    def add_member(self, channel_id: int, extension: str, role: str = "member") -> bool:
        """
        Add member to channel

        Args:
            channel_id: Channel ID
            extension: Extension number
            role: Member role (admin, member)

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                (
                    """INSERT INTO team_messaging_members
                   (channel_id, extension, role)
                   VALUES (?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO team_messaging_members
                   (channel_id, extension, role)
                   VALUES (%s, %s, %s)"""
                ),
                (channel_id, extension, role),
            )

            self.logger.info(f"Added {extension} to channel {channel_id}")
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Failed to add member to channel: {e}")
            return False

    def send_message(self, message_data: dict) -> int | None:
        """
        Send message to channel

        Args:
            message_data: Message information

        Returns:
            Message ID or None
        """
        try:
            self.db.execute(
                (
                    """INSERT INTO team_messages
                   (channel_id, sender_extension, message_text, message_type)
                   VALUES (?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO team_messages
                   (channel_id, sender_extension, message_text, message_type)
                   VALUES (%s, %s, %s, %s)"""
                ),
                (
                    message_data["channel_id"],
                    message_data["sender_extension"],
                    message_data["message_text"],
                    message_data.get("message_type", "text"),
                ),
            )

            # Get message ID
            result = self.db.execute(
                (
                    """SELECT id FROM team_messages
                   WHERE channel_id = ? AND sender_extension = ?
                   ORDER BY sent_at DESC LIMIT 1"""
                    if self.db.db_type == "sqlite"
                    else """SELECT id FROM team_messages
                   WHERE channel_id = %s AND sender_extension = %s
                   ORDER BY sent_at DESC LIMIT 1"""
                ),
                (message_data["channel_id"], message_data["sender_extension"]),
            )

            if result and result[0]:
                return result[0][0]

            return None

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to send message: {e}")
            return None

    def get_channel_messages(self, channel_id: int, limit: int = 100) -> list[dict]:
        """
        Get messages from channel

        Args:
            channel_id: Channel ID
            limit: Maximum number of messages

        Returns:
            list of message dictionaries
        """
        try:
            result = self.db.execute(
                (
                    """SELECT * FROM team_messages
                   WHERE channel_id = ?
                   ORDER BY sent_at DESC LIMIT ?"""
                    if self.db.db_type == "sqlite"
                    else """SELECT * FROM team_messages
                   WHERE channel_id = %s
                   ORDER BY sent_at DESC LIMIT %s"""
                ),
                (channel_id, limit),
            )

            messages = []
            for row in result or []:
                messages.append(
                    {
                        "id": row[0],
                        "sender_extension": row[2],
                        "message_text": row[3],
                        "message_type": row[4],
                        "sent_at": row[5],
                    }
                )

            return list(reversed(messages))  # Return in chronological order

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get channel messages: {e}")
            return []

    def get_user_channels(self, extension: str) -> list[dict]:
        """
        Get channels for user

        Args:
            extension: Extension number

        Returns:
            list of channel dictionaries
        """
        try:
            result = self.db.execute(
                (
                    """SELECT c.* FROM team_messaging_channels c
                   INNER JOIN team_messaging_members m ON c.id = m.channel_id
                   WHERE m.extension = ?
                   ORDER BY c.channel_name"""
                    if self.db.db_type == "sqlite"
                    else """SELECT c.* FROM team_messaging_channels c
                   INNER JOIN team_messaging_members m ON c.id = m.channel_id
                   WHERE m.extension = %s
                   ORDER BY c.channel_name"""
                ),
                (extension,),
            )

            channels = []
            for row in result or []:
                channels.append(
                    {
                        "id": row[0],
                        "channel_name": row[1],
                        "description": row[2],
                        "is_private": bool(row[3]),
                        "created_by": row[4],
                        "created_at": row[5],
                    }
                )

            return channels

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get user channels: {e}")
            return []

    def get_all_channels(self) -> list[dict]:
        """
        Get all public channels

        Returns:
            list of channel dictionaries
        """
        try:
            result = self.db.execute(
                (
                    """SELECT * FROM team_messaging_channels
                   WHERE is_private = ? ORDER BY channel_name"""
                    if self.db.db_type == "sqlite"
                    else """SELECT * FROM team_messaging_channels
                   WHERE is_private = %s ORDER BY channel_name"""
                ),
                (False,),
            )

            channels = []
            for row in result or []:
                channels.append(
                    {
                        "id": row[0],
                        "channel_name": row[1],
                        "description": row[2],
                        "created_by": row[4],
                        "created_at": row[5],
                    }
                )

            return channels

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get all channels: {e}")
            return []


class FileShareEngine:
    """
    File sharing framework
    Secure document collaboration
    """

    def __init__(self, db_backend: Any | None, config: dict) -> None:
        """
        Initialize file share engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.storage_path = config.get("file_sharing.storage_path", "/var/pbx/shared_files")

        self.logger.info("File Sharing Framework initialized")

    def upload_file(self, file_data: dict) -> int | None:
        """
        Upload and share file
        Framework method - handles file storage

        Args:
            file_data: File information

        Returns:
            File ID or None
        """
        try:
            self.db.execute(
                (
                    """INSERT INTO shared_files
                   (file_name, file_path, file_size, mime_type, uploaded_by,
                    shared_with, description, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO shared_files
                   (file_name, file_path, file_size, mime_type, uploaded_by,
                    shared_with, description, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                ),
                (
                    file_data["file_name"],
                    file_data["file_path"],
                    file_data.get("file_size", 0),
                    file_data.get("mime_type"),
                    file_data["uploaded_by"],
                    file_data.get("shared_with", ""),
                    file_data.get("description", ""),
                    file_data.get("expires_at"),
                ),
            )

            # Get file ID
            result = self.db.execute(
                (
                    """SELECT id FROM shared_files
                   WHERE file_path = ? ORDER BY uploaded_at DESC LIMIT 1"""
                    if self.db.db_type == "sqlite"
                    else """SELECT id FROM shared_files
                   WHERE file_path = %s ORDER BY uploaded_at DESC LIMIT 1"""
                ),
                (file_data["file_path"],),
            )

            if result and result[0]:
                self.logger.info(f"File uploaded: {file_data['file_name']}")
                return result[0][0]

            return None

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to upload file: {e}")
            return None

    def get_shared_files(self, extension: str) -> list[dict]:
        """
        Get files shared with user

        Args:
            extension: Extension number

        Returns:
            list of file dictionaries
        """
        try:
            # Files uploaded by user or shared with them
            result = self.db.execute(
                (
                    """SELECT * FROM shared_files
                   WHERE uploaded_by = ? OR shared_with LIKE ?
                   ORDER BY uploaded_at DESC"""
                    if self.db.db_type == "sqlite"
                    else """SELECT * FROM shared_files
                   WHERE uploaded_by = %s OR shared_with LIKE %s
                   ORDER BY uploaded_at DESC"""
                ),
                (extension, f"%{extension}%"),
            )

            files = []
            for row in result or []:
                files.append(
                    {
                        "id": row[0],
                        "file_name": row[1],
                        "file_size": row[3],
                        "mime_type": row[4],
                        "uploaded_by": row[5],
                        "description": row[7],
                        "uploaded_at": row[8],
                        "expires_at": row[9],
                    }
                )

            return files

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get shared files: {e}")
            return []
