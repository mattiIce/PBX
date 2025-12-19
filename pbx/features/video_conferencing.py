"""
Video Conferencing Framework
HD video calls, screen sharing, and 4K video support
"""

import hashlib
from datetime import datetime
from typing import Dict, List, Optional

from pbx.utils.logger import get_logger


class VideoConferencingEngine:
    """
    Video conferencing framework
    Supports HD/4K video, screen sharing, and multi-party conferences
    """

    def __init__(self, db_backend, config: dict):
        """
        Initialize video conferencing engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = config.get("video_conferencing.enabled", False)

        self.logger.info("Video Conferencing Framework initialized")

    def create_room(self, room_data: Dict) -> Optional[int]:
        """
        Create video conference room

        Args:
            room_data: Room configuration

        Returns:
            Room ID or None
        """
        try:
            password_hash = None
            if room_data.get("password"):
                password_hash = hashlib.sha256(room_data["password"].encode()).hexdigest()

            self.db.execute(
                (
                    """INSERT INTO video_conference_rooms 
                   (room_name, owner_extension, max_participants, enable_4k,
                    enable_screen_share, recording_enabled, password_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO video_conference_rooms 
                   (room_name, owner_extension, max_participants, enable_4k,
                    enable_screen_share, recording_enabled, password_hash)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                ),
                (
                    room_data["room_name"],
                    room_data.get("owner_extension"),
                    room_data.get("max_participants", 10),
                    room_data.get("enable_4k", False),
                    room_data.get("enable_screen_share", True),
                    room_data.get("recording_enabled", False),
                    password_hash,
                ),
            )

            # Get created room ID
            result = self.db.execute(
                (
                    "SELECT id FROM video_conference_rooms WHERE room_name = ?"
                    if self.db.db_type == "sqlite"
                    else "SELECT id FROM video_conference_rooms WHERE room_name = %s"
                ),
                (room_data["room_name"],),
            )

            if result and result[0]:
                room_id = result[0][0]
                self.logger.info(f"Created video conference room: {room_data['room_name']}")
                return room_id

            return None

        except Exception as e:
            self.logger.error(f"Failed to create video conference room: {e}")
            return None

    def join_room(self, room_id: int, participant_data: Dict) -> bool:
        """
        Add participant to video conference room

        Args:
            room_id: Room ID
            participant_data: Participant information

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                (
                    """INSERT INTO video_conference_participants 
                   (room_id, extension, display_name, video_enabled, audio_enabled)
                   VALUES (?, ?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO video_conference_participants 
                   (room_id, extension, display_name, video_enabled, audio_enabled)
                   VALUES (%s, %s, %s, %s, %s)"""
                ),
                (
                    room_id,
                    participant_data.get("extension"),
                    participant_data.get("display_name"),
                    participant_data.get("video_enabled", True),
                    participant_data.get("audio_enabled", True),
                ),
            )

            self.logger.info(
                f"Participant {participant_data.get('extension')} joined room {room_id}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to add participant to room: {e}")
            return False

    def leave_room(self, room_id: int, extension: str) -> bool:
        """
        Remove participant from video conference room

        Args:
            room_id: Room ID
            extension: Participant extension

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                (
                    """UPDATE video_conference_participants 
                   SET left_at = ? 
                   WHERE room_id = ? AND extension = ? AND left_at IS NULL"""
                    if self.db.db_type == "sqlite"
                    else """UPDATE video_conference_participants 
                   SET left_at = %s 
                   WHERE room_id = %s AND extension = %s AND left_at IS NULL"""
                ),
                (datetime.now(), room_id, extension),
            )

            self.logger.info(f"Participant {extension} left room {room_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove participant from room: {e}")
            return False

    def get_room(self, room_id: int) -> Optional[Dict]:
        """
        Get video conference room details

        Args:
            room_id: Room ID

        Returns:
            Room details or None
        """
        try:
            result = self.db.execute(
                (
                    "SELECT * FROM video_conference_rooms WHERE id = ?"
                    if self.db.db_type == "sqlite"
                    else "SELECT * FROM video_conference_rooms WHERE id = %s"
                ),
                (room_id,),
            )

            if result and result[0]:
                row = result[0]
                return {
                    "id": row[0],
                    "room_name": row[1],
                    "owner_extension": row[2],
                    "max_participants": row[3],
                    "enable_4k": bool(row[4]),
                    "enable_screen_share": bool(row[5]),
                    "recording_enabled": bool(row[6]),
                    "created_at": row[8],
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get video conference room: {e}")
            return None

    def get_room_participants(self, room_id: int) -> List[Dict]:
        """
        Get active participants in room

        Args:
            room_id: Room ID

        Returns:
            List of participant dictionaries
        """
        try:
            result = self.db.execute(
                (
                    """SELECT * FROM video_conference_participants 
                   WHERE room_id = ? AND left_at IS NULL"""
                    if self.db.db_type == "sqlite"
                    else """SELECT * FROM video_conference_participants 
                   WHERE room_id = %s AND left_at IS NULL"""
                ),
                (room_id,),
            )

            participants = []
            for row in result or []:
                participants.append(
                    {
                        "extension": row[2],
                        "display_name": row[3],
                        "joined_at": row[4],
                        "video_enabled": bool(row[6]),
                        "audio_enabled": bool(row[7]),
                        "screen_sharing": bool(row[8]),
                    }
                )

            return participants

        except Exception as e:
            self.logger.error(f"Failed to get room participants: {e}")
            return []

    def update_codec_config(self, codec_data: Dict) -> bool:
        """
        Update video codec configuration

        Args:
            codec_data: Codec configuration

        Returns:
            bool: True if successful
        """
        try:
            # Check if codec exists
            result = self.db.execute(
                (
                    "SELECT id FROM video_codec_configs WHERE codec_name = ?"
                    if self.db.db_type == "sqlite"
                    else "SELECT id FROM video_codec_configs WHERE codec_name = %s"
                ),
                (codec_data["codec_name"],),
            )

            if result and result[0]:
                # Update
                self.db.execute(
                    (
                        """UPDATE video_codec_configs 
                       SET enabled = ?, priority = ?, max_resolution = ?,
                           max_bitrate = ?, min_bitrate = ?
                       WHERE codec_name = ?"""
                        if self.db.db_type == "sqlite"
                        else """UPDATE video_codec_configs 
                       SET enabled = %s, priority = %s, max_resolution = %s,
                           max_bitrate = %s, min_bitrate = %s
                       WHERE codec_name = %s"""
                    ),
                    (
                        codec_data.get("enabled", True),
                        codec_data.get("priority", 100),
                        codec_data.get("max_resolution", "1920x1080"),
                        codec_data.get("max_bitrate", 2000),
                        codec_data.get("min_bitrate", 500),
                        codec_data["codec_name"],
                    ),
                )
            else:
                # Insert
                self.db.execute(
                    (
                        """INSERT INTO video_codec_configs 
                       (codec_name, enabled, priority, max_resolution, max_bitrate, min_bitrate)
                       VALUES (?, ?, ?, ?, ?, ?)"""
                        if self.db.db_type == "sqlite"
                        else """INSERT INTO video_codec_configs 
                       (codec_name, enabled, priority, max_resolution, max_bitrate, min_bitrate)
                       VALUES (%s, %s, %s, %s, %s, %s)"""
                    ),
                    (
                        codec_data["codec_name"],
                        codec_data.get("enabled", True),
                        codec_data.get("priority", 100),
                        codec_data.get("max_resolution", "1920x1080"),
                        codec_data.get("max_bitrate", 2000),
                        codec_data.get("min_bitrate", 500),
                    ),
                )

            self.logger.info(f"Updated video codec config: {codec_data['codec_name']}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update video codec config: {e}")
            return False

    def get_all_rooms(self) -> List[Dict]:
        """
        Get all video conference rooms

        Returns:
            List of room dictionaries
        """
        try:
            result = self.db.execute(
                "SELECT * FROM video_conference_rooms ORDER BY created_at DESC"
            )

            rooms = []
            for row in result or []:
                rooms.append(
                    {
                        "id": row[0],
                        "room_name": row[1],
                        "owner_extension": row[2],
                        "max_participants": row[3],
                        "enable_4k": bool(row[4]),
                        "enable_screen_share": bool(row[5]),
                        "recording_enabled": bool(row[6]),
                        "created_at": row[8],
                    }
                )

            return rooms

        except Exception as e:
            self.logger.error(f"Failed to get all video conference rooms: {e}")
            return []

    def enable_screen_share(self, room_id: int, extension: str) -> bool:
        """
        Enable screen sharing for participant
        Framework method - integrates with WebRTC

        Args:
            room_id: Room ID
            extension: Participant extension

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                (
                    """UPDATE video_conference_participants 
                   SET screen_sharing = ?
                   WHERE room_id = ? AND extension = ? AND left_at IS NULL"""
                    if self.db.db_type == "sqlite"
                    else """UPDATE video_conference_participants 
                   SET screen_sharing = %s
                   WHERE room_id = %s AND extension = %s AND left_at IS NULL"""
                ),
                (True, room_id, extension),
            )

            # NOTE: Video conferencing is handled by Zoom/Teams for this deployment
            # This framework provides database tracking only
            # WebRTC video/screen sharing is not implemented as it's redundant with Zoom/Teams

            self.logger.info(f"Screen sharing flag enabled for {extension} in room {room_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to enable screen sharing: {e}")
            return False
