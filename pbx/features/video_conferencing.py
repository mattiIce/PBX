"""
Video Conferencing Framework
HD video calls, screen sharing, and 4K video support
"""

import hashlib
import sqlite3
from datetime import UTC, datetime
from typing import Any

from pbx.utils.logger import get_logger


class VideoConferencingEngine:
    """
    Video conferencing framework
    Supports HD/4K video, screen sharing, and multi-party conferences
    """

    def __init__(self, db_backend: Any | None, config: dict) -> None:
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

    def create_room(self, room_data: dict) -> int | None:
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

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to create video conference room: {e}")
            return None

    def join_room(self, room_id: int, participant_data: dict) -> bool:
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

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
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
                (datetime.now(UTC), room_id, extension),
            )

            self.logger.info(f"Participant {extension} left room {room_id}")
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Failed to remove participant from room: {e}")
            return False

    def get_room(self, room_id: int) -> dict | None:
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
                    "SELECT id, room_name, owner_extension, max_participants, enable_4k, enable_screen_share, recording_enabled, password_hash, created_at FROM video_conference_rooms WHERE id = ?"
                    if self.db.db_type == "sqlite"
                    else "SELECT id, room_name, owner_extension, max_participants, enable_4k, enable_screen_share, recording_enabled, password_hash, created_at FROM video_conference_rooms WHERE id = %s"
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

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get video conference room: {e}")
            return None

    def get_room_participants(self, room_id: int) -> list[dict]:
        """
        Get active participants in room

        Args:
            room_id: Room ID

        Returns:
            list of participant dictionaries
        """
        try:
            result = self.db.execute(
                (
                    """SELECT id, room_id, extension, display_name, joined_at, left_at, video_enabled, audio_enabled, screen_sharing FROM video_conference_participants
                   WHERE room_id = ? AND left_at IS NULL"""
                    if self.db.db_type == "sqlite"
                    else """SELECT id, room_id, extension, display_name, joined_at, left_at, video_enabled, audio_enabled, screen_sharing FROM video_conference_participants
                   WHERE room_id = %s AND left_at IS NULL"""
                ),
                (room_id,),
            )

            participants = [
                {
                    "extension": row[2],
                    "display_name": row[3],
                    "joined_at": row[4],
                    "video_enabled": bool(row[6]),
                    "audio_enabled": bool(row[7]),
                    "screen_sharing": bool(row[8]),
                }
                for row in result or []
            ]

            return participants

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get room participants: {e}")
            return []

    def update_codec_config(self, codec_data: dict) -> bool:
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

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to update video codec config: {e}")
            return False

    def get_all_rooms(self) -> list[dict]:
        """
        Get all video conference rooms

        Returns:
            list of room dictionaries
        """
        try:
            result = self.db.execute(
                "SELECT id, room_name, owner_extension, max_participants, enable_4k, enable_screen_share, recording_enabled, password_hash, created_at FROM video_conference_rooms ORDER BY created_at DESC"
            )

            rooms = [
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
                for row in result or []
            ]

            return rooms

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get all video conference rooms: {e}")
            return []

    def enable_screen_share(self, room_id: int, extension: str) -> bool:
        """
        Enable screen sharing for a participant using WebRTC signaling.

        Updates the database state and generates a WebRTC SDP renegotiation
        offer to add a screen-share media track to the participant's session.
        The SDP offer is stored and can be retrieved by the client to complete
        the WebRTC renegotiation handshake.

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

            self.logger.info(f"Screen sharing flag enabled for {extension} in room {room_id}")

            # Initiate WebRTC renegotiation to add the screen-share track.
            # This is best-effort; signaling failures do not affect the
            # database state update above.
            try:
                sdp_offer = self._generate_screen_share_sdp(room_id, extension)
                if sdp_offer:
                    participants = self.get_room_participants(room_id)
                    for participant in participants:
                        if participant["extension"] != extension:
                            self._send_signaling_message(
                                room_id,
                                participant["extension"],
                                {
                                    "type": "screen_share_offer",
                                    "from": extension,
                                    "sdp": sdp_offer,
                                },
                            )
                    self.logger.info(
                        f"WebRTC renegotiation initiated for screen share "
                        f"by {extension} in room {room_id}"
                    )
            except Exception as e:
                self.logger.warning(
                    f"WebRTC signaling for screen share failed (DB state updated successfully): {e}"
                )

            return True

        except sqlite3.Error as e:
            self.logger.error(f"Failed to enable screen sharing: {e}")
            return False

    def disable_screen_share(self, room_id: int, extension: str) -> bool:
        """
        Disable screen sharing for a participant.

        Updates database state and sends a WebRTC renegotiation signal
        to remove the screen-share track.

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
                (False, room_id, extension),
            )

            # Notify participants to remove the screen-share stream
            participants = self.get_room_participants(room_id)
            for participant in participants:
                if participant["extension"] != extension:
                    self._send_signaling_message(
                        room_id,
                        participant["extension"],
                        {
                            "type": "screen_share_stop",
                            "from": extension,
                        },
                    )

            self.logger.info(f"Screen sharing disabled for {extension} in room {room_id}")
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Failed to disable screen sharing: {e}")
            return False

    def handle_webrtc_offer(self, room_id: int, from_extension: str, sdp_offer: str) -> dict | None:
        """
        Handle an incoming WebRTC SDP offer from a participant.

        Processes the SDP offer, generates an SDP answer with the server's
        media capabilities, and returns it for the client to apply.

        Args:
            room_id: Room ID
            from_extension: Extension of the participant sending the offer
            sdp_offer: SDP offer string

        Returns:
            dict | None: SDP answer and ICE candidates, or None on failure
        """
        try:
            # Parse the offered SDP to extract media descriptions
            media_lines = self._parse_sdp_media(sdp_offer)

            # Generate an SDP answer matching the offered media
            sdp_answer = self._generate_sdp_answer(room_id, from_extension, media_lines)

            # Generate ICE candidates for the server's media relay
            ice_candidates = self._generate_ice_candidates(room_id)

            self.logger.info(
                f"Generated WebRTC answer for {from_extension} in room {room_id} "
                f"({len(media_lines)} media lines)"
            )

            return {
                "type": "answer",
                "sdp": sdp_answer,
                "ice_candidates": ice_candidates,
            }

        except Exception as e:
            self.logger.error(f"Failed to handle WebRTC offer: {e}")
            return None

    def handle_ice_candidate(self, room_id: int, from_extension: str, candidate: dict) -> bool:
        """
        Handle an incoming ICE candidate from a participant.

        Relays ICE candidates to other participants in the room for
        peer-to-peer or server-relayed connectivity.

        Args:
            room_id: Room ID
            from_extension: Extension of the participant sending the candidate
            candidate: ICE candidate dictionary

        Returns:
            bool: True if candidate was relayed successfully
        """
        try:
            participants = self.get_room_participants(room_id)
            for participant in participants:
                if participant["extension"] != from_extension:
                    self._send_signaling_message(
                        room_id,
                        participant["extension"],
                        {
                            "type": "ice_candidate",
                            "from": from_extension,
                            "candidate": candidate,
                        },
                    )

            self.logger.debug(f"Relayed ICE candidate from {from_extension} in room {room_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to relay ICE candidate: {e}")
            return False

    def _generate_screen_share_sdp(self, room_id: int, extension: str) -> str | None:
        """
        Generate an SDP offer for screen sharing renegotiation.

        Creates an SDP media description for a new video track designated
        for screen sharing content, using VP8/VP9/H.264 codecs.

        Args:
            room_id: Room ID
            extension: Participant extension

        Returns:
            str | None: SDP offer string or None on failure
        """
        import time

        try:
            room = self.get_room(room_id)
            if not room:
                return None

            # Determine codec and resolution based on room configuration
            max_resolution = "1920x1080"
            if room.get("enable_4k"):
                max_resolution = "3840x2160"

            session_id = int(time.time())
            sdp_lines = [
                "v=0",
                f"o=pbx-video {session_id} {session_id} IN IP4 0.0.0.0",
                "s=PBX Screen Share",
                "t=0 0",
                # Screen share video media line
                "m=video 0 UDP/TLS/RTP/SAVPF 96 97 98",
                "c=IN IP4 0.0.0.0",
                "a=mid:screen",
                "a=sendonly",
                "a=content:slides",
                f"a=label:screen-{extension}",
                # VP8 codec (widely supported)
                "a=rtpmap:96 VP8/90000",
                "a=fmtp:96 max-fs=8160;max-fr=30",
                # VP9 codec (better compression)
                "a=rtpmap:97 VP9/90000",
                "a=fmtp:97 max-fs=8160;max-fr=30",
                # H.264 codec (hardware acceleration)
                "a=rtpmap:98 H264/90000",
                "a=fmtp:98 profile-level-id=42e01f;level-asymmetry-allowed=1",
                "a=rtcp-mux",
                "a=rtcp-rsize",
                # ICE and DTLS attributes (placeholders for actual negotiation)
                "a=ice-ufrag:screen",
                "a=ice-pwd:screensharepassword",
                "a=setup:actpass",
                f"a=max-message-size={max_resolution}",
            ]

            return "\r\n".join(sdp_lines) + "\r\n"

        except Exception as e:
            self.logger.error(f"Failed to generate screen share SDP: {e}")
            return None

    def _generate_sdp_answer(self, room_id: int, extension: str, offered_media: list[dict]) -> str:
        """
        Generate an SDP answer matching the offered media descriptions.

        Args:
            room_id: Room ID
            extension: Participant extension
            offered_media: Parsed media descriptions from the offer

        Returns:
            str: SDP answer string
        """
        import time

        session_id = int(time.time())
        sdp_lines = [
            "v=0",
            f"o=pbx-video {session_id} {session_id} IN IP4 0.0.0.0",
            "s=PBX Video Conference",
            "t=0 0",
            "a=group:BUNDLE " + " ".join(m.get("mid", str(i)) for i, m in enumerate(offered_media)),
        ]

        for media in offered_media:
            media_type = media.get("type", "video")
            codecs = media.get("codecs", [96])
            codec_str = " ".join(str(c) for c in codecs)
            sdp_lines.extend(
                [
                    f"m={media_type} 0 UDP/TLS/RTP/SAVPF {codec_str}",
                    "c=IN IP4 0.0.0.0",
                    f"a=mid:{media.get('mid', '0')}",
                    f"a={media.get('direction', 'recvonly')}",
                    "a=rtcp-mux",
                    "a=rtcp-rsize",
                    "a=ice-ufrag:answer",
                    "a=ice-pwd:answerpassword",
                    "a=setup:active",
                ]
            )

            # Add codec descriptions from the offer
            sdp_lines.extend(media.get("codec_lines", []))

        return "\r\n".join(sdp_lines) + "\r\n"

    def _parse_sdp_media(self, sdp: str) -> list[dict]:
        """
        Parse SDP to extract media descriptions.

        Args:
            sdp: SDP string

        Returns:
            list[dict]: Parsed media descriptions
        """
        media_sections = []
        current_media = None

        for raw_line in sdp.strip().split("\n"):
            sdp_line = raw_line.strip().rstrip("\r")
            if sdp_line.startswith("m="):
                if current_media:
                    media_sections.append(current_media)
                parts = sdp_line[2:].split()
                current_media = {
                    "type": parts[0] if parts else "video",
                    "port": int(parts[1]) if len(parts) > 1 else 0,
                    "codecs": [int(c) for c in parts[3:] if c.isdigit()] if len(parts) > 3 else [],
                    "mid": "0",
                    "direction": "sendrecv",
                    "codec_lines": [],
                }
            elif current_media:
                if sdp_line.startswith("a=mid:"):
                    current_media["mid"] = sdp_line[6:]
                elif sdp_line.startswith("a=sendonly"):
                    current_media["direction"] = "recvonly"
                elif sdp_line.startswith("a=recvonly"):
                    current_media["direction"] = "sendonly"
                elif sdp_line.startswith("a=sendrecv"):
                    current_media["direction"] = "sendrecv"
                elif sdp_line.startswith(("a=rtpmap:", "a=fmtp:")):
                    current_media["codec_lines"].append(sdp_line)

        if current_media:
            media_sections.append(current_media)

        return media_sections

    def _generate_ice_candidates(self, room_id: int) -> list[dict]:
        """
        Generate ICE candidates for the server's media relay.

        In a production deployment, these would come from the actual STUN/TURN
        server configuration. This generates host candidates based on the
        server's configured addresses.

        Args:
            room_id: Room ID

        Returns:
            list[dict]: ICE candidate dictionaries
        """
        candidates = []

        # Generate host candidate from configured SIP/RTP bind address
        bind_address = self.config.get("sip.bind_address", "0.0.0.0")
        rtp_port_start = self.config.get("rtp.port_start", 10000)

        # Host candidate for RTP
        candidates.append(
            {
                "candidate": (
                    f"candidate:1 1 udp 2130706431 {bind_address} "
                    f"{rtp_port_start + (room_id * 2)} typ host"
                ),
                "sdpMid": "0",
                "sdpMLineIndex": 0,
            }
        )

        # STUN server relay candidate if configured
        stun_server = self.config.get("webrtc.stun_server", "")
        if stun_server:
            candidates.append(
                {
                    "candidate": (
                        f"candidate:2 1 udp 1694498815 {bind_address} "
                        f"{rtp_port_start + (room_id * 2) + 1} typ srflx "
                        f"raddr {bind_address} rport {rtp_port_start + (room_id * 2)}"
                    ),
                    "sdpMid": "0",
                    "sdpMLineIndex": 0,
                }
            )

        return candidates

    def _send_signaling_message(self, room_id: int, to_extension: str, message: dict) -> bool:
        """
        Send a WebRTC signaling message to a participant.

        Stores the signaling message in the database for the target participant
        to poll/retrieve. In production with WebSocket support, this would push
        the message directly to the client's WebSocket connection.

        Args:
            room_id: Room ID
            to_extension: Target participant extension
            message: Signaling message dictionary

        Returns:
            bool: True if message was queued successfully
        """
        import json

        try:
            self.db.execute(
                (
                    """INSERT INTO video_conference_signals
                   (room_id, to_extension, message_type, message_data, created_at)
                   VALUES (?, ?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO video_conference_signals
                   (room_id, to_extension, message_type, message_data, created_at)
                   VALUES (%s, %s, %s, %s, %s)"""
                ),
                (
                    room_id,
                    to_extension,
                    message.get("type", "unknown"),
                    json.dumps(message),
                    datetime.now(UTC),
                ),
            )

            self.logger.debug(
                f"Queued signaling message ({message.get('type')}) "
                f"for {to_extension} in room {room_id}"
            )
            return True

        except sqlite3.Error as e:
            self.logger.warning(f"Failed to queue signaling message: {e}")
            return False

    def get_signaling_messages(self, room_id: int, extension: str) -> list[dict]:
        """
        Retrieve pending WebRTC signaling messages for a participant.

        Clients should poll this endpoint (or use WebSocket push) to receive
        SDP offers/answers and ICE candidates from other participants.

        Args:
            room_id: Room ID
            extension: Participant extension

        Returns:
            list[dict]: Pending signaling messages
        """
        import json

        try:
            result = self.db.execute(
                (
                    """SELECT id, message_type, message_data, created_at
                   FROM video_conference_signals
                   WHERE room_id = ? AND to_extension = ?
                   ORDER BY created_at ASC"""
                    if self.db.db_type == "sqlite"
                    else """SELECT id, message_type, message_data, created_at
                   FROM video_conference_signals
                   WHERE room_id = %s AND to_extension = %s
                   ORDER BY created_at ASC"""
                ),
                (room_id, extension),
            )

            messages = []
            signal_ids = []
            for row in result or []:
                signal_ids.append(row[0])
                messages.append(
                    {
                        "id": row[0],
                        "type": row[1],
                        "data": json.loads(row[2]) if row[2] else {},
                        "created_at": str(row[3]),
                    }
                )

            # Clean up retrieved messages
            if signal_ids:
                placeholders = ", ".join(
                    "?" * len(signal_ids) if self.db.db_type == "sqlite" else "%s" * len(signal_ids)
                )
                self.db.execute(
                    f"DELETE FROM video_conference_signals WHERE id IN ({placeholders})",
                    tuple(signal_ids),
                )

            return messages

        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to retrieve signaling messages: {e}")
            return []
