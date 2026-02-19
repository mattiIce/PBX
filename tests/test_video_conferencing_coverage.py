"""
Tests for Video Conferencing Framework
Comprehensive coverage of VideoConferencingEngine
"""

import hashlib
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.video_conferencing import VideoConferencingEngine


@pytest.mark.unit
class TestVideoConferencingEngineInit:
    """Test VideoConferencingEngine initialization"""

    @patch("pbx.features.video_conferencing.get_logger")
    def test_init_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with enabled config"""
        config = {"video_conferencing.enabled": True}
        db = MagicMock()
        engine = VideoConferencingEngine(db, config)

        assert engine.enabled is True
        assert engine.db is db
        assert engine.config is config
        mock_get_logger.return_value.info.assert_called()

    @patch("pbx.features.video_conferencing.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with disabled config"""
        config = {"video_conferencing.enabled": False}
        db = MagicMock()
        engine = VideoConferencingEngine(db, config)

        assert engine.enabled is False

    @patch("pbx.features.video_conferencing.get_logger")
    def test_init_default_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization defaults to disabled when key missing"""
        config = {}
        db = MagicMock()
        engine = VideoConferencingEngine(db, config)

        assert engine.enabled is False

    @patch("pbx.features.video_conferencing.get_logger")
    def test_init_none_db(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with None db_backend"""
        config = {"video_conferencing.enabled": False}
        engine = VideoConferencingEngine(None, config)

        assert engine.db is None


@pytest.mark.unit
class TestVideoConferencingCreateRoom:
    """Test VideoConferencingEngine.create_room"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_create_room_basic(self) -> None:
        """Test basic room creation without password"""
        self.db.execute.side_effect = [None, [(42,)]]
        room_data = {"room_name": "Test Room"}

        result = self.engine.create_room(room_data)

        assert result == 42
        assert self.db.execute.call_count == 2

    def test_create_room_with_password(self) -> None:
        """Test room creation with password hashing"""
        self.db.execute.side_effect = [None, [(1,)]]
        room_data = {"room_name": "Secure Room", "password": "secret123"}

        result = self.engine.create_room(room_data)

        assert result == 1
        # Verify password was hashed
        insert_call_args = self.db.execute.call_args_list[0]
        params = insert_call_args[0][1]
        expected_hash = hashlib.sha256(b"secret123").hexdigest()
        assert params[-1] == expected_hash

    def test_create_room_with_all_options(self) -> None:
        """Test room creation with all options specified"""
        self.db.execute.side_effect = [None, [(5,)]]
        room_data = {
            "room_name": "Full Room",
            "owner_extension": "1001",
            "max_participants": 25,
            "enable_4k": True,
            "enable_screen_share": False,
            "recording_enabled": True,
            "password": "pass",
        }

        result = self.engine.create_room(room_data)

        assert result == 5
        insert_call_args = self.db.execute.call_args_list[0]
        params = insert_call_args[0][1]
        assert params[0] == "Full Room"
        assert params[1] == "1001"
        assert params[2] == 25
        assert params[3] is True
        assert params[4] is False
        assert params[5] is True

    def test_create_room_default_values(self) -> None:
        """Test room creation uses correct defaults"""
        self.db.execute.side_effect = [None, [(1,)]]
        room_data = {"room_name": "Defaults Room"}

        self.engine.create_room(room_data)

        insert_call_args = self.db.execute.call_args_list[0]
        params = insert_call_args[0][1]
        assert params[1] is None  # owner_extension default
        assert params[2] == 10  # max_participants default
        assert params[3] is False  # enable_4k default
        assert params[4] is True  # enable_screen_share default
        assert params[5] is False  # recording_enabled default
        assert params[6] is None  # no password

    def test_create_room_no_result(self) -> None:
        """Test room creation when SELECT returns no result"""
        self.db.execute.side_effect = [None, []]

        result = self.engine.create_room({"room_name": "Ghost Room"})

        assert result is None

    def test_create_room_none_result(self) -> None:
        """Test room creation when SELECT returns None"""
        self.db.execute.side_effect = [None, None]

        result = self.engine.create_room({"room_name": "Ghost Room"})

        assert result is None

    def test_create_room_result_first_row_none(self) -> None:
        """Test room creation when result has None first element"""
        self.db.execute.side_effect = [None, [None]]

        result = self.engine.create_room({"room_name": "Ghost Room"})

        assert result is None

    def test_create_room_key_error(self) -> None:
        """Test room creation with missing required key"""
        result = self.engine.create_room({})  # missing room_name

        assert result is None

    def test_create_room_db_error(self) -> None:
        """Test room creation with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.create_room({"room_name": "Error Room"})

        assert result is None

    def test_create_room_type_error(self) -> None:
        """Test room creation with TypeError"""
        self.db.execute.side_effect = TypeError("type error")

        result = self.engine.create_room({"room_name": "Error Room"})

        assert result is None

    def test_create_room_value_error(self) -> None:
        """Test room creation with ValueError"""
        self.db.execute.side_effect = ValueError("value error")

        result = self.engine.create_room({"room_name": "Error Room"})

        assert result is None

    def test_create_room_postgresql_query(self) -> None:
        """Test room creation uses PostgreSQL placeholder syntax"""
        self.db.db_type = "postgresql"
        self.db.execute.side_effect = [None, [(1,)]]

        self.engine.create_room({"room_name": "PG Room"})

        insert_query = self.db.execute.call_args_list[0][0][0]
        assert "%s" in insert_query
        assert "?" not in insert_query

    def test_create_room_empty_password(self) -> None:
        """Test room creation with empty password string"""
        self.db.execute.side_effect = [None, [(1,)]]
        room_data = {"room_name": "Room", "password": ""}

        self.engine.create_room(room_data)

        insert_call_args = self.db.execute.call_args_list[0]
        params = insert_call_args[0][1]
        # Empty string is falsy, so password_hash should be None
        assert params[-1] is None


@pytest.mark.unit
class TestVideoConferencingJoinRoom:
    """Test VideoConferencingEngine.join_room"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_join_room_success(self) -> None:
        """Test successfully joining a room"""
        participant_data = {
            "extension": "1001",
            "display_name": "Alice",
            "video_enabled": True,
            "audio_enabled": True,
        }

        result = self.engine.join_room(1, participant_data)

        assert result is True
        self.db.execute.assert_called_once()

    def test_join_room_minimal_data(self) -> None:
        """Test joining with minimal participant data"""
        result = self.engine.join_room(1, {})

        assert result is True
        call_args = self.db.execute.call_args[0][1]
        assert call_args[1] is None  # extension
        assert call_args[2] is None  # display_name
        assert call_args[3] is True  # video_enabled default
        assert call_args[4] is True  # audio_enabled default

    def test_join_room_video_disabled(self) -> None:
        """Test joining with video disabled"""
        participant_data = {
            "extension": "1002",
            "display_name": "Bob",
            "video_enabled": False,
            "audio_enabled": True,
        }

        result = self.engine.join_room(1, participant_data)

        assert result is True
        call_args = self.db.execute.call_args[0][1]
        assert call_args[3] is False

    def test_join_room_db_error(self) -> None:
        """Test joining room with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.join_room(1, {"extension": "1001"})

        assert result is False

    def test_join_room_key_error(self) -> None:
        """Test joining room with KeyError"""
        self.db.execute.side_effect = KeyError("key")

        result = self.engine.join_room(1, {"extension": "1001"})

        assert result is False

    def test_join_room_type_error(self) -> None:
        """Test joining room with TypeError"""
        self.db.execute.side_effect = TypeError("type")

        result = self.engine.join_room(1, {"extension": "1001"})

        assert result is False

    def test_join_room_postgresql(self) -> None:
        """Test join room uses PostgreSQL placeholders"""
        self.db.db_type = "postgresql"

        self.engine.join_room(1, {"extension": "1001"})

        query = self.db.execute.call_args[0][0]
        assert "%s" in query
        assert "?" not in query


@pytest.mark.unit
class TestVideoConferencingLeaveRoom:
    """Test VideoConferencingEngine.leave_room"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_leave_room_success(self) -> None:
        """Test successfully leaving a room"""
        result = self.engine.leave_room(1, "1001")

        assert result is True
        self.db.execute.assert_called_once()
        call_args = self.db.execute.call_args[0][1]
        # First param is datetime, then room_id, then extension
        assert call_args[1] == 1
        assert call_args[2] == "1001"

    def test_leave_room_db_error(self) -> None:
        """Test leaving room with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.leave_room(1, "1001")

        assert result is False

    def test_leave_room_postgresql(self) -> None:
        """Test leave room uses PostgreSQL placeholders"""
        self.db.db_type = "postgresql"

        self.engine.leave_room(1, "1001")

        query = self.db.execute.call_args[0][0]
        assert "%s" in query
        assert "?" not in query

    def test_leave_room_sets_timestamp(self) -> None:
        """Test that leave_room sets a timestamp"""
        self.engine.leave_room(1, "1001")

        call_args = self.db.execute.call_args[0][1]
        from datetime import datetime

        assert isinstance(call_args[0], datetime)


@pytest.mark.unit
class TestVideoConferencingGetRoom:
    """Test VideoConferencingEngine.get_room"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_get_room_success(self) -> None:
        """Test getting room details"""
        row = (1, "Room1", "1001", 10, 1, 1, 0, "hash", "2024-01-01")
        self.db.execute.return_value = [row]

        result = self.engine.get_room(1)

        assert result is not None
        assert result["id"] == 1
        assert result["room_name"] == "Room1"
        assert result["owner_extension"] == "1001"
        assert result["max_participants"] == 10
        assert result["enable_4k"] is True
        assert result["enable_screen_share"] is True
        assert result["recording_enabled"] is False
        assert result["created_at"] == "2024-01-01"

    def test_get_room_not_found_empty(self) -> None:
        """Test getting room that does not exist (empty list)"""
        self.db.execute.return_value = []

        result = self.engine.get_room(999)

        assert result is None

    def test_get_room_not_found_none(self) -> None:
        """Test getting room when result is None"""
        self.db.execute.return_value = None

        result = self.engine.get_room(999)

        assert result is None

    def test_get_room_first_row_none(self) -> None:
        """Test getting room when first row is None"""
        self.db.execute.return_value = [None]

        result = self.engine.get_room(999)

        assert result is None

    def test_get_room_db_error(self) -> None:
        """Test getting room with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.get_room(1)

        assert result is None

    def test_get_room_key_error(self) -> None:
        """Test getting room with KeyError"""
        self.db.execute.side_effect = KeyError("key")

        result = self.engine.get_room(1)

        assert result is None

    def test_get_room_type_error(self) -> None:
        """Test getting room with TypeError"""
        self.db.execute.side_effect = TypeError("type")

        result = self.engine.get_room(1)

        assert result is None

    def test_get_room_postgresql(self) -> None:
        """Test get room uses PostgreSQL placeholders"""
        self.db.db_type = "postgresql"
        self.db.execute.return_value = []

        self.engine.get_room(1)

        query = self.db.execute.call_args[0][0]
        assert "%s" in query

    def test_get_room_boolean_conversion(self) -> None:
        """Test boolean fields are properly converted"""
        row = (1, "Room", "1001", 10, 0, 0, 1, "hash", "2024-01-01")
        self.db.execute.return_value = [row]

        result = self.engine.get_room(1)

        assert result["enable_4k"] is False
        assert result["enable_screen_share"] is False
        assert result["recording_enabled"] is True


@pytest.mark.unit
class TestVideoConferencingGetRoomParticipants:
    """Test VideoConferencingEngine.get_room_participants"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_get_participants_success(self) -> None:
        """Test getting active participants"""
        rows = [
            (1, 1, "1001", "Alice", "2024-01-01", None, 1, 1, 0),
            (2, 1, "1002", "Bob", "2024-01-01", None, 1, 1, 1),
        ]
        self.db.execute.return_value = rows

        result = self.engine.get_room_participants(1)

        assert len(result) == 2
        assert result[0]["extension"] == "1001"
        assert result[0]["display_name"] == "Alice"
        assert result[0]["video_enabled"] is True
        assert result[0]["audio_enabled"] is True
        assert result[0]["screen_sharing"] is False
        assert result[1]["screen_sharing"] is True

    def test_get_participants_empty(self) -> None:
        """Test getting participants when none in room"""
        self.db.execute.return_value = []

        result = self.engine.get_room_participants(1)

        assert result == []

    def test_get_participants_none_result(self) -> None:
        """Test getting participants when result is None"""
        self.db.execute.return_value = None

        result = self.engine.get_room_participants(1)

        assert result == []

    def test_get_participants_db_error(self) -> None:
        """Test getting participants with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.get_room_participants(1)

        assert result == []

    def test_get_participants_key_error(self) -> None:
        """Test getting participants with KeyError"""
        self.db.execute.side_effect = KeyError("key")

        result = self.engine.get_room_participants(1)

        assert result == []

    def test_get_participants_postgresql(self) -> None:
        """Test get participants uses PostgreSQL placeholders"""
        self.db.db_type = "postgresql"
        self.db.execute.return_value = []

        self.engine.get_room_participants(1)

        query = self.db.execute.call_args[0][0]
        assert "%s" in query


@pytest.mark.unit
class TestVideoConferencingUpdateCodecConfig:
    """Test VideoConferencingEngine.update_codec_config"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_update_codec_existing(self) -> None:
        """Test updating an existing codec config"""
        self.db.execute.side_effect = [[(1,)], None]
        codec_data = {
            "codec_name": "H264",
            "enabled": True,
            "priority": 50,
            "max_resolution": "3840x2160",
            "max_bitrate": 4000,
            "min_bitrate": 1000,
        }

        result = self.engine.update_codec_config(codec_data)

        assert result is True
        assert self.db.execute.call_count == 2

    def test_update_codec_insert_new(self) -> None:
        """Test inserting a new codec config"""
        self.db.execute.side_effect = [[], None]
        codec_data = {"codec_name": "VP9"}

        result = self.engine.update_codec_config(codec_data)

        assert result is True
        assert self.db.execute.call_count == 2

    def test_update_codec_insert_when_none_result(self) -> None:
        """Test inserting codec when SELECT returns None"""
        self.db.execute.side_effect = [None, None]
        codec_data = {"codec_name": "AV1"}

        result = self.engine.update_codec_config(codec_data)

        assert result is True

    def test_update_codec_insert_when_first_row_none(self) -> None:
        """Test inserting codec when first row of result is None/falsy"""
        self.db.execute.side_effect = [[None], None]
        codec_data = {"codec_name": "AV1"}

        result = self.engine.update_codec_config(codec_data)

        assert result is True

    def test_update_codec_default_values(self) -> None:
        """Test codec update uses correct defaults"""
        self.db.execute.side_effect = [[], None]
        codec_data = {"codec_name": "H265"}

        self.engine.update_codec_config(codec_data)

        insert_args = self.db.execute.call_args_list[1][0][1]
        assert insert_args[0] == "H265"
        assert insert_args[1] is True  # enabled default
        assert insert_args[2] == 100  # priority default
        assert insert_args[3] == "1920x1080"  # max_resolution default
        assert insert_args[4] == 2000  # max_bitrate default
        assert insert_args[5] == 500  # min_bitrate default

    def test_update_codec_missing_codec_name(self) -> None:
        """Test codec update with missing codec_name key"""
        result = self.engine.update_codec_config({})

        assert result is False

    def test_update_codec_db_error(self) -> None:
        """Test codec update with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.update_codec_config({"codec_name": "H264"})

        assert result is False

    def test_update_codec_postgresql_existing(self) -> None:
        """Test codec update uses PostgreSQL syntax when updating"""
        self.db.db_type = "postgresql"
        self.db.execute.side_effect = [[(1,)], None]

        self.engine.update_codec_config({"codec_name": "H264"})

        for call in self.db.execute.call_args_list:
            query = call[0][0]
            assert "%s" in query

    def test_update_codec_postgresql_insert(self) -> None:
        """Test codec insert uses PostgreSQL syntax"""
        self.db.db_type = "postgresql"
        self.db.execute.side_effect = [[], None]

        self.engine.update_codec_config({"codec_name": "VP9"})

        insert_query = self.db.execute.call_args_list[1][0][0]
        assert "%s" in insert_query


@pytest.mark.unit
class TestVideoConferencingGetAllRooms:
    """Test VideoConferencingEngine.get_all_rooms"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_get_all_rooms_success(self) -> None:
        """Test getting all rooms"""
        rows = [
            (1, "Room1", "1001", 10, 1, 1, 0, "hash1", "2024-01-02"),
            (2, "Room2", "1002", 20, 0, 1, 1, "hash2", "2024-01-01"),
        ]
        self.db.execute.return_value = rows

        result = self.engine.get_all_rooms()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["room_name"] == "Room1"
        assert result[0]["enable_4k"] is True
        assert result[1]["id"] == 2
        assert result[1]["enable_4k"] is False
        assert result[1]["recording_enabled"] is True

    def test_get_all_rooms_empty(self) -> None:
        """Test getting all rooms when none exist"""
        self.db.execute.return_value = []

        result = self.engine.get_all_rooms()

        assert result == []

    def test_get_all_rooms_none(self) -> None:
        """Test getting all rooms when result is None"""
        self.db.execute.return_value = None

        result = self.engine.get_all_rooms()

        assert result == []

    def test_get_all_rooms_db_error(self) -> None:
        """Test getting all rooms with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.get_all_rooms()

        assert result == []

    def test_get_all_rooms_query_no_params(self) -> None:
        """Test that get_all_rooms query has no parameters"""
        self.db.execute.return_value = []

        self.engine.get_all_rooms()

        self.db.execute.assert_called_once_with(
            "SELECT * FROM video_conference_rooms ORDER BY created_at DESC"
        )


@pytest.mark.unit
class TestVideoConferencingEnableScreenShare:
    """Test VideoConferencingEngine.enable_screen_share"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_enable_screen_share_success(self) -> None:
        """Test enabling screen sharing"""
        result = self.engine.enable_screen_share(1, "1001")

        assert result is True
        self.db.execute.assert_called_once()
        call_args = self.db.execute.call_args[0][1]
        assert call_args[0] is True
        assert call_args[1] == 1
        assert call_args[2] == "1001"

    def test_enable_screen_share_db_error(self) -> None:
        """Test enabling screen sharing with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.enable_screen_share(1, "1001")

        assert result is False

    def test_enable_screen_share_postgresql(self) -> None:
        """Test enable screen share uses PostgreSQL placeholders"""
        self.db.db_type = "postgresql"

        self.engine.enable_screen_share(1, "1001")

        query = self.db.execute.call_args[0][0]
        assert "%s" in query
        assert "?" not in query


@pytest.mark.unit
class TestVideoConferencingDisableScreenShare:
    """Test VideoConferencingEngine.disable_screen_share"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_disable_screen_share_success(self) -> None:
        """Test disabling screen sharing updates DB and notifies participants"""
        # get_room_participants returns two other participants
        self.db.execute.side_effect = [
            None,  # UPDATE screen_sharing = False
            [
                (1, 1, "1002", "User2", None, None, True, True, False),
                (2, 1, "1003", "User3", None, None, True, True, False),
            ],  # SELECT participants
            None,  # INSERT signaling for 1002
            None,  # INSERT signaling for 1003
        ]

        result = self.engine.disable_screen_share(1, "1001")

        assert result is True
        # First call is the UPDATE
        first_call = self.db.execute.call_args_list[0]
        assert first_call[0][1] == (False, 1, "1001")

    def test_disable_screen_share_db_error(self) -> None:
        """Test disabling screen sharing with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.disable_screen_share(1, "1001")

        assert result is False

    def test_disable_screen_share_postgresql(self) -> None:
        """Test disable screen share uses PostgreSQL placeholders"""
        self.db.db_type = "postgresql"

        self.engine.disable_screen_share(1, "1001")

        query = self.db.execute.call_args_list[0][0][0]
        assert "%s" in query
        assert "?" not in query

    def test_disable_screen_share_no_other_participants(self) -> None:
        """Test disabling screen sharing when no other participants exist"""
        self.db.execute.side_effect = [
            None,  # UPDATE
            [],  # empty participants
        ]

        result = self.engine.disable_screen_share(1, "1001")

        assert result is True
        # Only 2 DB calls: UPDATE + SELECT participants
        assert self.db.execute.call_count == 2


@pytest.mark.unit
class TestVideoConferencingHandleWebrtcOffer:
    """Test VideoConferencingEngine.handle_webrtc_offer"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

        self.sample_sdp_offer = (
            "v=0\r\n"
            "o=- 123456 2 IN IP4 127.0.0.1\r\n"
            "s=-\r\n"
            "t=0 0\r\n"
            "m=audio 49170 UDP/TLS/RTP/SAVPF 111\r\n"
            "a=mid:audio0\r\n"
            "a=sendrecv\r\n"
            "a=rtpmap:111 opus/48000/2\r\n"
            "m=video 51372 UDP/TLS/RTP/SAVPF 96 97\r\n"
            "a=mid:video0\r\n"
            "a=sendrecv\r\n"
            "a=rtpmap:96 VP8/90000\r\n"
            "a=rtpmap:97 VP9/90000\r\n"
        )

    def test_handle_webrtc_offer_success(self) -> None:
        """Test handling a valid WebRTC SDP offer"""
        result = self.engine.handle_webrtc_offer(1, "1001", self.sample_sdp_offer)

        assert result is not None
        assert result["type"] == "answer"
        assert "sdp" in result
        assert "ice_candidates" in result
        assert isinstance(result["ice_candidates"], list)

    def test_handle_webrtc_offer_sdp_answer_contains_bundle(self) -> None:
        """Test that the generated SDP answer contains BUNDLE grouping"""
        result = self.engine.handle_webrtc_offer(1, "1001", self.sample_sdp_offer)

        assert result is not None
        assert "a=group:BUNDLE" in result["sdp"]
        assert "audio0" in result["sdp"]
        assert "video0" in result["sdp"]

    def test_handle_webrtc_offer_empty_sdp(self) -> None:
        """Test handling an empty SDP offer"""
        result = self.engine.handle_webrtc_offer(1, "1001", "")

        # Empty SDP should still produce a result (just with no media)
        assert result is not None
        assert result["type"] == "answer"

    def test_handle_webrtc_offer_malformed_sdp(self) -> None:
        """Test handling a malformed SDP offer"""
        result = self.engine.handle_webrtc_offer(1, "1001", "not a valid sdp")

        # Should not crash, returns answer with no media sections
        assert result is not None
        assert result["type"] == "answer"

    def test_handle_webrtc_offer_returns_ice_candidates(self) -> None:
        """Test that ICE candidates are returned in the offer response"""
        self.config["sip.bind_address"] = "192.168.1.100"
        self.config["rtp.port_start"] = 20000

        result = self.engine.handle_webrtc_offer(1, "1001", self.sample_sdp_offer)

        assert result is not None
        assert len(result["ice_candidates"]) >= 1
        assert "192.168.1.100" in result["ice_candidates"][0]["candidate"]


@pytest.mark.unit
class TestVideoConferencingHandleIceCandidate:
    """Test VideoConferencingEngine.handle_ice_candidate"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_handle_ice_candidate_relays_to_others(self) -> None:
        """Test ICE candidate is relayed to other participants"""
        self.db.execute.side_effect = [
            [
                (1, 1, "1001", "User1", None, None, True, True, False),
                (2, 1, "1002", "User2", None, None, True, True, False),
                (3, 1, "1003", "User3", None, None, True, True, False),
            ],  # SELECT participants
            None,  # INSERT signal for 1002
            None,  # INSERT signal for 1003
        ]
        candidate = {"candidate": "candidate:1 1 udp 2130706431 10.0.0.1 5000 typ host"}

        result = self.engine.handle_ice_candidate(1, "1001", candidate)

        assert result is True
        # 1 SELECT + 2 INSERTs (to 1002 and 1003, not back to 1001)
        assert self.db.execute.call_count == 3

    def test_handle_ice_candidate_no_other_participants(self) -> None:
        """Test ICE candidate when sender is the only participant"""
        self.db.execute.return_value = [
            (1, 1, "1001", "User1", None, None, True, True, False),
        ]
        candidate = {"candidate": "candidate:1 1 udp 2130706431 10.0.0.1 5000 typ host"}

        result = self.engine.handle_ice_candidate(1, "1001", candidate)

        assert result is True

    def test_handle_ice_candidate_exception(self) -> None:
        """Test ICE candidate relay with unexpected exception"""
        self.db.execute.side_effect = RuntimeError("Unexpected error")
        candidate = {"candidate": "candidate:1 1 udp 2130706431 10.0.0.1 5000 typ host"}

        result = self.engine.handle_ice_candidate(1, "1001", candidate)

        assert result is False

    def test_handle_ice_candidate_empty_room(self) -> None:
        """Test ICE candidate when room has no participants"""
        self.db.execute.return_value = []
        candidate = {"candidate": "candidate:1 1 udp 2130706431 10.0.0.1 5000 typ host"}

        result = self.engine.handle_ice_candidate(1, "1001", candidate)

        assert result is True


@pytest.mark.unit
class TestVideoConferencingGenerateScreenShareSdp:
    """Test VideoConferencingEngine._generate_screen_share_sdp"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_generate_screen_share_sdp_success(self) -> None:
        """Test generating screen share SDP for a standard room"""
        self.db.execute.return_value = [
            (1, "TestRoom", "1001", 10, False, True, False, None, "2025-01-01"),
        ]

        result = self.engine._generate_screen_share_sdp(1, "1001")

        assert result is not None
        assert "v=0" in result
        assert "m=video" in result
        assert "VP8" in result
        assert "VP9" in result
        assert "H264" in result
        assert "a=sendonly" in result
        assert "a=content:slides" in result
        assert "screen-1001" in result

    def test_generate_screen_share_sdp_4k_enabled(self) -> None:
        """Test screen share SDP with 4K enabled room"""
        self.db.execute.return_value = [
            (1, "TestRoom", "1001", 10, True, True, False, None, "2025-01-01"),
        ]

        result = self.engine._generate_screen_share_sdp(1, "1001")

        assert result is not None
        assert "3840x2160" in result

    def test_generate_screen_share_sdp_4k_disabled(self) -> None:
        """Test screen share SDP with 4K disabled room"""
        self.db.execute.return_value = [
            (1, "TestRoom", "1001", 10, False, True, False, None, "2025-01-01"),
        ]

        result = self.engine._generate_screen_share_sdp(1, "1001")

        assert result is not None
        assert "1920x1080" in result

    def test_generate_screen_share_sdp_room_not_found(self) -> None:
        """Test screen share SDP when room does not exist"""
        self.db.execute.return_value = []

        result = self.engine._generate_screen_share_sdp(1, "1001")

        assert result is None

    def test_generate_screen_share_sdp_contains_codecs(self) -> None:
        """Test screen share SDP contains all expected codec descriptions"""
        self.db.execute.return_value = [
            (1, "TestRoom", "1001", 10, False, True, False, None, "2025-01-01"),
        ]

        result = self.engine._generate_screen_share_sdp(1, "1001")

        assert "a=rtpmap:96 VP8/90000" in result
        assert "a=rtpmap:97 VP9/90000" in result
        assert "a=rtpmap:98 H264/90000" in result

    def test_generate_screen_share_sdp_contains_ice_attributes(self) -> None:
        """Test screen share SDP contains ICE attributes"""
        self.db.execute.return_value = [
            (1, "TestRoom", "1001", 10, False, True, False, None, "2025-01-01"),
        ]

        result = self.engine._generate_screen_share_sdp(1, "1001")

        assert "a=ice-ufrag:" in result
        assert "a=ice-pwd:" in result
        assert "a=setup:actpass" in result


@pytest.mark.unit
class TestVideoConferencingGenerateSdpAnswer:
    """Test VideoConferencingEngine._generate_sdp_answer"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_generate_sdp_answer_bundle_grouping(self) -> None:
        """Test SDP answer includes BUNDLE grouping with correct MIDs"""
        offered_media = [
            {
                "type": "audio",
                "codecs": [111],
                "mid": "a0",
                "direction": "sendrecv",
                "codec_lines": [],
            },
            {
                "type": "video",
                "codecs": [96],
                "mid": "v0",
                "direction": "sendrecv",
                "codec_lines": [],
            },
        ]

        result = self.engine._generate_sdp_answer(1, "1001", offered_media)

        assert "a=group:BUNDLE a0 v0" in result

    def test_generate_sdp_answer_direction_sendrecv(self) -> None:
        """Test direction negotiation: sendrecv stays sendrecv"""
        offered_media = [
            {
                "type": "audio",
                "codecs": [111],
                "mid": "a0",
                "direction": "sendrecv",
                "codec_lines": [],
            },
        ]

        result = self.engine._generate_sdp_answer(1, "1001", offered_media)

        assert "a=sendrecv" in result

    def test_generate_sdp_answer_direction_recvonly(self) -> None:
        """Test direction negotiation: recvonly in answer when offer parsed as recvonly"""
        offered_media = [
            {
                "type": "video",
                "codecs": [96],
                "mid": "v0",
                "direction": "recvonly",
                "codec_lines": [],
            },
        ]

        result = self.engine._generate_sdp_answer(1, "1001", offered_media)

        assert "a=recvonly" in result

    def test_generate_sdp_answer_direction_sendonly(self) -> None:
        """Test direction negotiation: sendonly in answer"""
        offered_media = [
            {
                "type": "video",
                "codecs": [96],
                "mid": "v0",
                "direction": "sendonly",
                "codec_lines": [],
            },
        ]

        result = self.engine._generate_sdp_answer(1, "1001", offered_media)

        assert "a=sendonly" in result

    def test_generate_sdp_answer_includes_codec_lines(self) -> None:
        """Test SDP answer includes offered codec descriptions"""
        offered_media = [
            {
                "type": "video",
                "codecs": [96, 97],
                "mid": "v0",
                "direction": "sendrecv",
                "codec_lines": [
                    "a=rtpmap:96 VP8/90000",
                    "a=rtpmap:97 VP9/90000",
                ],
            },
        ]

        result = self.engine._generate_sdp_answer(1, "1001", offered_media)

        assert "a=rtpmap:96 VP8/90000" in result
        assert "a=rtpmap:97 VP9/90000" in result

    def test_generate_sdp_answer_empty_media(self) -> None:
        """Test SDP answer with no offered media"""
        result = self.engine._generate_sdp_answer(1, "1001", [])

        assert "v=0" in result
        assert "a=group:BUNDLE " in result
        # No m= lines
        assert "m=" not in result

    def test_generate_sdp_answer_uses_mid_default(self) -> None:
        """Test SDP answer uses default MID when not specified"""
        offered_media = [
            {"type": "video", "codecs": [96], "direction": "sendrecv", "codec_lines": []},
        ]

        result = self.engine._generate_sdp_answer(1, "1001", offered_media)

        # Default mid from enumerate index
        assert "a=mid:0" in result


@pytest.mark.unit
class TestVideoConferencingParseSdpMedia:
    """Test VideoConferencingEngine._parse_sdp_media"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_parse_sdp_media_single_audio(self) -> None:
        """Test parsing SDP with a single audio media section"""
        sdp = (
            "v=0\r\n"
            "o=- 123 2 IN IP4 0.0.0.0\r\n"
            "s=-\r\n"
            "m=audio 49170 UDP/TLS/RTP/SAVPF 111\r\n"
            "a=mid:audio0\r\n"
            "a=sendrecv\r\n"
            "a=rtpmap:111 opus/48000/2\r\n"
        )

        result = self.engine._parse_sdp_media(sdp)

        assert len(result) == 1
        assert result[0]["type"] == "audio"
        assert result[0]["port"] == 49170
        assert result[0]["mid"] == "audio0"
        assert result[0]["direction"] == "sendrecv"
        assert 111 in result[0]["codecs"]
        assert "a=rtpmap:111 opus/48000/2" in result[0]["codec_lines"]

    def test_parse_sdp_media_multiple_sections(self) -> None:
        """Test parsing SDP with audio and video media sections"""
        sdp = (
            "v=0\r\n"
            "m=audio 49170 UDP/TLS/RTP/SAVPF 111\r\n"
            "a=mid:a0\r\n"
            "a=sendrecv\r\n"
            "m=video 51372 UDP/TLS/RTP/SAVPF 96 97\r\n"
            "a=mid:v0\r\n"
            "a=sendonly\r\n"
            "a=rtpmap:96 VP8/90000\r\n"
        )

        result = self.engine._parse_sdp_media(sdp)

        assert len(result) == 2
        assert result[0]["type"] == "audio"
        assert result[0]["mid"] == "a0"
        assert result[1]["type"] == "video"
        assert result[1]["mid"] == "v0"
        # sendonly in offer -> direction set to recvonly in parser
        assert result[1]["direction"] == "recvonly"

    def test_parse_sdp_media_direction_sendonly_maps_to_recvonly(self) -> None:
        """Test that sendonly in SDP is parsed as recvonly (answer perspective)"""
        sdp = "m=video 0 UDP/TLS/RTP/SAVPF 96\r\na=sendonly\r\n"

        result = self.engine._parse_sdp_media(sdp)

        assert len(result) == 1
        assert result[0]["direction"] == "recvonly"

    def test_parse_sdp_media_direction_recvonly_maps_to_sendonly(self) -> None:
        """Test that recvonly in SDP is parsed as sendonly (answer perspective)"""
        sdp = "m=video 0 UDP/TLS/RTP/SAVPF 96\r\na=recvonly\r\n"

        result = self.engine._parse_sdp_media(sdp)

        assert len(result) == 1
        assert result[0]["direction"] == "sendonly"

    def test_parse_sdp_media_direction_sendrecv(self) -> None:
        """Test that sendrecv stays as sendrecv"""
        sdp = "m=audio 0 UDP/TLS/RTP/SAVPF 111\r\na=sendrecv\r\n"

        result = self.engine._parse_sdp_media(sdp)

        assert result[0]["direction"] == "sendrecv"

    def test_parse_sdp_media_empty_string(self) -> None:
        """Test parsing an empty SDP string"""
        result = self.engine._parse_sdp_media("")

        assert result == []

    def test_parse_sdp_media_no_media_lines(self) -> None:
        """Test parsing SDP with no media lines"""
        sdp = "v=0\r\no=- 123 2 IN IP4 0.0.0.0\r\ns=-\r\nt=0 0\r\n"

        result = self.engine._parse_sdp_media(sdp)

        assert result == []

    def test_parse_sdp_media_codec_fmtp_lines(self) -> None:
        """Test parsing SDP captures fmtp lines"""
        sdp = (
            "m=video 0 UDP/TLS/RTP/SAVPF 96\r\n"
            "a=rtpmap:96 VP8/90000\r\n"
            "a=fmtp:96 max-fs=8160;max-fr=30\r\n"
        )

        result = self.engine._parse_sdp_media(sdp)

        assert len(result) == 1
        assert "a=rtpmap:96 VP8/90000" in result[0]["codec_lines"]
        assert "a=fmtp:96 max-fs=8160;max-fr=30" in result[0]["codec_lines"]

    def test_parse_sdp_media_malformed_no_crash(self) -> None:
        """Test parsing malformed SDP does not crash"""
        sdp = "m=\r\ngarbage line\r\na=mid:test\r\n"

        result = self.engine._parse_sdp_media(sdp)

        # Should parse the m= line without crashing
        assert isinstance(result, list)


@pytest.mark.unit
class TestVideoConferencingGenerateIceCandidates:
    """Test VideoConferencingEngine._generate_ice_candidates"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_generate_ice_candidates_default_config(self) -> None:
        """Test ICE candidate generation with default config"""
        result = self.engine._generate_ice_candidates(1)

        assert len(result) == 1  # only host, no STUN
        assert "candidate:1" in result[0]["candidate"]
        assert "0.0.0.0" in result[0]["candidate"]
        assert "10002" in result[0]["candidate"]  # 10000 + (1 * 2)
        assert result[0]["sdpMid"] == "0"
        assert result[0]["sdpMLineIndex"] == 0

    def test_generate_ice_candidates_custom_bind_address(self) -> None:
        """Test ICE candidate generation with custom bind address"""
        self.config["sip.bind_address"] = "192.168.1.50"

        result = self.engine._generate_ice_candidates(1)

        assert "192.168.1.50" in result[0]["candidate"]

    def test_generate_ice_candidates_custom_rtp_port(self) -> None:
        """Test ICE candidate generation with custom RTP port start"""
        self.config["rtp.port_start"] = 30000

        result = self.engine._generate_ice_candidates(5)

        # 30000 + (5 * 2) = 30010
        assert "30010" in result[0]["candidate"]

    def test_generate_ice_candidates_with_stun_server(self) -> None:
        """Test ICE candidate generation includes srflx when STUN configured"""
        self.config["webrtc.stun_server"] = "stun:stun.example.com:3478"

        result = self.engine._generate_ice_candidates(1)

        assert len(result) == 2
        assert "typ host" in result[0]["candidate"]
        assert "typ srflx" in result[1]["candidate"]

    def test_generate_ice_candidates_stun_srflx_port_offset(self) -> None:
        """Test STUN srflx candidate uses correct port offset"""
        self.config["webrtc.stun_server"] = "stun:stun.example.com:3478"
        self.config["rtp.port_start"] = 20000

        result = self.engine._generate_ice_candidates(3)

        # host port = 20000 + (3 * 2) = 20006
        # srflx port = 20000 + (3 * 2) + 1 = 20007
        assert "20006" in result[0]["candidate"]
        assert "20007" in result[1]["candidate"]

    def test_generate_ice_candidates_room_id_zero(self) -> None:
        """Test ICE candidates for room ID 0"""
        result = self.engine._generate_ice_candidates(0)

        # 10000 + (0 * 2) = 10000
        assert "10000" in result[0]["candidate"]


@pytest.mark.unit
class TestVideoConferencingSendSignalingMessage:
    """Test VideoConferencingEngine._send_signaling_message"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_send_signaling_message_success(self) -> None:
        """Test sending a signaling message stores it in the DB"""
        message = {"type": "offer", "sdp": "v=0..."}

        result = self.engine._send_signaling_message(1, "1002", message)

        assert result is True
        self.db.execute.assert_called_once()
        call_args = self.db.execute.call_args[0][1]
        assert call_args[0] == 1  # room_id
        assert call_args[1] == "1002"  # to_extension
        assert call_args[2] == "offer"  # message_type

    def test_send_signaling_message_db_error(self) -> None:
        """Test sending signaling message with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine._send_signaling_message(1, "1002", {"type": "offer"})

        assert result is False

    def test_send_signaling_message_postgresql(self) -> None:
        """Test send signaling message uses PostgreSQL placeholders"""
        self.db.db_type = "postgresql"

        self.engine._send_signaling_message(1, "1002", {"type": "offer"})

        query = self.db.execute.call_args[0][0]
        assert "%s" in query
        assert "?" not in query

    def test_send_signaling_message_unknown_type(self) -> None:
        """Test sending message without type key defaults to 'unknown'"""
        message = {"data": "some_data"}

        result = self.engine._send_signaling_message(1, "1002", message)

        assert result is True
        call_args = self.db.execute.call_args[0][1]
        assert call_args[2] == "unknown"

    def test_send_signaling_message_json_serialization(self) -> None:
        """Test that the message is JSON-serialized in the DB call"""
        import json

        message = {"type": "ice_candidate", "candidate": {"sdp": "test"}}

        self.engine._send_signaling_message(1, "1002", message)

        call_args = self.db.execute.call_args[0][1]
        stored_json = call_args[3]
        parsed = json.loads(stored_json)
        assert parsed["type"] == "ice_candidate"
        assert parsed["candidate"]["sdp"] == "test"


@pytest.mark.unit
class TestVideoConferencingGetSignalingMessages:
    """Test VideoConferencingEngine.get_signaling_messages"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = MagicMock()
        self.db.db_type = "sqlite"
        self.config = {"video_conferencing.enabled": True}
        with patch("pbx.features.video_conferencing.get_logger"):
            self.engine = VideoConferencingEngine(self.db, self.config)

    def test_get_signaling_messages_success(self) -> None:
        """Test retrieving signaling messages"""
        import json

        self.db.execute.side_effect = [
            [
                (1, "offer", json.dumps({"type": "offer", "sdp": "v=0..."}), "2025-01-01 00:00:00"),
                (2, "ice_candidate", json.dumps({"type": "ice_candidate"}), "2025-01-01 00:00:01"),
            ],  # SELECT
            None,  # DELETE
        ]

        result = self.engine.get_signaling_messages(1, "1001")

        assert len(result) == 2
        assert result[0]["type"] == "offer"
        assert result[0]["data"]["sdp"] == "v=0..."
        assert result[1]["type"] == "ice_candidate"

    def test_get_signaling_messages_deletes_after_retrieval(self) -> None:
        """Test that messages are deleted after retrieval"""
        import json

        self.db.execute.side_effect = [
            [
                (10, "offer", json.dumps({"type": "offer"}), "2025-01-01"),
                (11, "answer", json.dumps({"type": "answer"}), "2025-01-01"),
            ],
            None,
        ]

        self.engine.get_signaling_messages(1, "1001")

        # Second call should be DELETE with the IDs
        delete_call = self.db.execute.call_args_list[1]
        assert "DELETE" in delete_call[0][0]
        assert delete_call[0][1] == (10, 11)

    def test_get_signaling_messages_empty(self) -> None:
        """Test retrieving when no messages exist"""
        self.db.execute.return_value = []

        result = self.engine.get_signaling_messages(1, "1001")

        assert result == []
        # Only one DB call (SELECT), no DELETE since no IDs
        assert self.db.execute.call_count == 1

    def test_get_signaling_messages_none_result(self) -> None:
        """Test retrieving when DB returns None"""
        self.db.execute.return_value = None

        result = self.engine.get_signaling_messages(1, "1001")

        assert result == []

    def test_get_signaling_messages_db_error(self) -> None:
        """Test retrieving messages with database error"""
        self.db.execute.side_effect = Exception("DB error")

        result = self.engine.get_signaling_messages(1, "1001")

        assert result == []

    def test_get_signaling_messages_postgresql(self) -> None:
        """Test get signaling messages uses PostgreSQL placeholders"""
        self.db.db_type = "postgresql"
        self.db.execute.return_value = []

        self.engine.get_signaling_messages(1, "1001")

        query = self.db.execute.call_args[0][0]
        assert "%s" in query
        assert "?" not in query

    def test_get_signaling_messages_null_message_data(self) -> None:
        """Test handling of null message_data in a row"""
        self.db.execute.side_effect = [
            [
                (1, "offer", None, "2025-01-01"),
            ],
            None,  # DELETE
        ]

        result = self.engine.get_signaling_messages(1, "1001")

        assert len(result) == 1
        assert result[0]["data"] == {}

    def test_get_signaling_messages_json_decode_error(self) -> None:
        """Test handling of invalid JSON in message_data"""
        self.db.execute.side_effect = [
            [
                (1, "offer", "not valid json{{{", "2025-01-01"),
            ],
        ]

        result = self.engine.get_signaling_messages(1, "1001")

        # JSONDecodeError is caught, returns empty list
        assert result == []
