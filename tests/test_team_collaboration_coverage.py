#!/usr/bin/env python3
"""
Comprehensive tests for Team Collaboration features (pbx/features/team_collaboration.py)
Covers TeamMessagingEngine and FileShareEngine.
"""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# TeamMessagingEngine tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTeamMessagingEngineInit:
    """Tests for TeamMessagingEngine initialization"""

    def test_init_enabled(self) -> None:
        """Test initialization with enabled flag"""
        mock_db = MagicMock()
        config = {"team_messaging.enabled": True}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(mock_db, config)

        assert engine.enabled is True
        assert engine.db is mock_db
        assert engine.config is config

    def test_init_disabled(self) -> None:
        """Test initialization with disabled flag"""
        mock_db = MagicMock()
        config = {"team_messaging.enabled": False}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(mock_db, config)

        assert engine.enabled is False

    def test_init_default_disabled(self) -> None:
        """Test initialization defaults to disabled"""
        mock_db = MagicMock()
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(mock_db, config)

        assert engine.enabled is False

    def test_init_with_none_db(self) -> None:
        """Test initialization with None database"""
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(None, config)

        assert engine.db is None

    def test_init_logs_message(self) -> None:
        """Test that init logs initialization message"""
        mock_db = MagicMock()
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.team_collaboration import TeamMessagingEngine

            TeamMessagingEngine(mock_db, config)

        mock_logger.info.assert_called_with("Team Messaging Framework initialized")


@pytest.mark.unit
class TestTeamMessagingEngineCreateChannel:
    """Tests for TeamMessagingEngine.create_channel"""

    def _make_engine(self, db_type="sqlite"):
        """Helper to create engine with mock db"""
        mock_db = MagicMock()
        mock_db.db_type = db_type
        config = {"team_messaging.enabled": True}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(mock_db, config)
        return engine

    def test_create_channel_success_sqlite(self) -> None:
        """Test creating a channel with sqlite backend"""
        engine = self._make_engine("sqlite")
        engine.db.execute.side_effect = [
            None,  # INSERT
            [(42,)],  # SELECT returns channel ID
            None,  # INSERT member (add_member call)
        ]
        channel_data = {
            "channel_name": "general",
            "description": "General chat",
            "is_private": False,
            "created_by": "1001",
        }

        result = engine.create_channel(channel_data)

        assert result == 42
        assert engine.db.execute.call_count == 3  # create + select + add_member

    def test_create_channel_success_postgresql(self) -> None:
        """Test creating a channel with postgresql backend"""
        engine = self._make_engine("postgresql")
        engine.db.execute.side_effect = [
            None,  # INSERT
            [(10,)],  # SELECT returns channel ID
            None,  # add_member
        ]
        channel_data = {
            "channel_name": "dev-team",
            "created_by": "1002",
        }

        result = engine.create_channel(channel_data)

        assert result == 10

    def test_create_channel_no_creator(self) -> None:
        """Test creating a channel without created_by"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [
            None,  # INSERT
            [(7,)],  # SELECT returns channel ID
        ]
        channel_data = {
            "channel_name": "announcements",
        }

        result = engine.create_channel(channel_data)

        assert result == 7
        # Should not call add_member since no created_by
        assert engine.db.execute.call_count == 2

    def test_create_channel_no_result(self) -> None:
        """Test creating a channel with no result from query"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [
            None,  # INSERT
            None,  # SELECT returns None
        ]
        channel_data = {"channel_name": "test"}

        result = engine.create_channel(channel_data)

        assert result is None

    def test_create_channel_empty_result(self) -> None:
        """Test creating a channel when result is empty list"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [
            None,  # INSERT
            [],  # SELECT returns empty list
        ]
        channel_data = {"channel_name": "test"}

        result = engine.create_channel(channel_data)

        assert result is None

    def test_create_channel_result_first_item_none(self) -> None:
        """Test creating a channel when first row is None"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [
            None,  # INSERT
            [None],  # SELECT returns list with None
        ]
        channel_data = {"channel_name": "test"}

        result = engine.create_channel(channel_data)

        assert result is None

    def test_create_channel_key_error(self) -> None:
        """Test creating a channel with missing required key"""
        engine = self._make_engine()
        # Missing channel_name key
        channel_data = {"description": "No name"}

        result = engine.create_channel(channel_data)

        assert result is None

    def test_create_channel_db_error(self) -> None:
        """Test creating a channel when db raises error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("database error")
        channel_data = {"channel_name": "test"}

        result = engine.create_channel(channel_data)

        assert result is None

    def test_create_channel_type_error(self) -> None:
        """Test creating a channel with type error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = TypeError("type error")
        channel_data = {"channel_name": "test"}

        result = engine.create_channel(channel_data)

        assert result is None

    def test_create_channel_defaults(self) -> None:
        """Test that channel creation uses default values"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [
            None,  # INSERT
            [(1,)],  # SELECT
        ]
        channel_data = {"channel_name": "minimal"}

        engine.create_channel(channel_data)

        # Verify defaults were used in the INSERT call
        insert_args = engine.db.execute.call_args_list[0]
        params = insert_args[0][1]
        assert params[1] == ""  # description default
        assert params[2] is False  # is_private default
        assert params[3] is None  # created_by default


@pytest.mark.unit
class TestTeamMessagingEngineAddMember:
    """Tests for TeamMessagingEngine.add_member"""

    def _make_engine(self, db_type="sqlite"):
        mock_db = MagicMock()
        mock_db.db_type = db_type
        config = {"team_messaging.enabled": True}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            return TeamMessagingEngine(mock_db, config)

    def test_add_member_success_sqlite(self) -> None:
        """Test adding member with sqlite"""
        engine = self._make_engine("sqlite")

        result = engine.add_member(1, "1001", "member")

        assert result is True
        engine.db.execute.assert_called_once()

    def test_add_member_success_postgresql(self) -> None:
        """Test adding member with postgresql"""
        engine = self._make_engine("postgresql")

        result = engine.add_member(1, "1001", "admin")

        assert result is True

    def test_add_member_default_role(self) -> None:
        """Test adding member with default role"""
        engine = self._make_engine()

        engine.add_member(1, "1001")

        args = engine.db.execute.call_args[0][1]
        assert args[2] == "member"

    def test_add_member_db_error(self) -> None:
        """Test adding member with database error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("constraint violation")

        result = engine.add_member(1, "1001")

        assert result is False


@pytest.mark.unit
class TestTeamMessagingEngineSendMessage:
    """Tests for TeamMessagingEngine.send_message"""

    def _make_engine(self, db_type="sqlite"):
        mock_db = MagicMock()
        mock_db.db_type = db_type
        config = {"team_messaging.enabled": True}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            return TeamMessagingEngine(mock_db, config)

    def test_send_message_success(self) -> None:
        """Test sending a message successfully"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [
            None,  # INSERT
            [(99,)],  # SELECT message ID
        ]
        message_data = {
            "channel_id": 1,
            "sender_extension": "1001",
            "message_text": "Hello world",
            "message_type": "text",
        }

        result = engine.send_message(message_data)

        assert result == 99

    def test_send_message_default_type(self) -> None:
        """Test sending a message with default type"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [None, [(1,)]]
        message_data = {
            "channel_id": 1,
            "sender_extension": "1001",
            "message_text": "Hello",
        }

        engine.send_message(message_data)

        # Verify default message_type is "text"
        insert_args = engine.db.execute.call_args_list[0][0][1]
        assert insert_args[3] == "text"

    def test_send_message_no_result(self) -> None:
        """Test sending message with no result"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [None, None]
        message_data = {
            "channel_id": 1,
            "sender_extension": "1001",
            "message_text": "Hello",
        }

        result = engine.send_message(message_data)

        assert result is None

    def test_send_message_empty_result(self) -> None:
        """Test sending message with empty result"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [None, []]
        message_data = {
            "channel_id": 1,
            "sender_extension": "1001",
            "message_text": "Hello",
        }

        result = engine.send_message(message_data)

        assert result is None

    def test_send_message_result_first_item_none(self) -> None:
        """Test sending message when first row is None"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [None, [None]]
        message_data = {
            "channel_id": 1,
            "sender_extension": "1001",
            "message_text": "Hello",
        }

        result = engine.send_message(message_data)

        assert result is None

    def test_send_message_key_error(self) -> None:
        """Test sending message with missing key"""
        engine = self._make_engine()
        message_data = {"channel_id": 1}  # missing sender_extension and message_text

        result = engine.send_message(message_data)

        assert result is None

    def test_send_message_db_error(self) -> None:
        """Test sending message with db error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("db error")
        message_data = {
            "channel_id": 1,
            "sender_extension": "1001",
            "message_text": "Hello",
        }

        result = engine.send_message(message_data)

        assert result is None

    def test_send_message_postgresql(self) -> None:
        """Test sending message with postgresql"""
        engine = self._make_engine("postgresql")
        engine.db.execute.side_effect = [None, [(50,)]]
        message_data = {
            "channel_id": 2,
            "sender_extension": "1002",
            "message_text": "Test",
        }

        result = engine.send_message(message_data)

        assert result == 50


@pytest.mark.unit
class TestTeamMessagingEngineGetChannelMessages:
    """Tests for TeamMessagingEngine.get_channel_messages"""

    def _make_engine(self, db_type="sqlite"):
        mock_db = MagicMock()
        mock_db.db_type = db_type
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            return TeamMessagingEngine(mock_db, config)

    def test_get_channel_messages_success(self) -> None:
        """Test getting channel messages"""
        engine = self._make_engine()
        # DB returns results in DESC order; method reverses to chronological
        engine.db.execute.return_value = [
            (2, 1, "1002", "Hi there", "text", "2025-01-01 10:01:00"),
            (1, 1, "1001", "Hello", "text", "2025-01-01 10:00:00"),
        ]

        result = engine.get_channel_messages(1, limit=50)

        assert len(result) == 2
        # Reversed to chronological order
        assert result[0]["id"] == 1
        assert result[0]["sender_extension"] == "1001"
        assert result[0]["message_text"] == "Hello"
        assert result[1]["id"] == 2

    def test_get_channel_messages_default_limit(self) -> None:
        """Test getting channel messages with default limit"""
        engine = self._make_engine()
        engine.db.execute.return_value = []

        engine.get_channel_messages(1)

        args = engine.db.execute.call_args[0][1]
        assert args[1] == 100  # default limit

    def test_get_channel_messages_empty(self) -> None:
        """Test getting channel messages with no results"""
        engine = self._make_engine()
        engine.db.execute.return_value = None

        result = engine.get_channel_messages(1)

        assert result == []

    def test_get_channel_messages_db_error(self) -> None:
        """Test getting channel messages with db error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("db error")

        result = engine.get_channel_messages(1)

        assert result == []

    def test_get_channel_messages_postgresql(self) -> None:
        """Test getting messages with postgresql"""
        engine = self._make_engine("postgresql")
        engine.db.execute.return_value = [
            (1, 1, "1001", "msg", "text", "2025-01-01"),
        ]

        result = engine.get_channel_messages(1)

        assert len(result) == 1

    def test_get_channel_messages_reversed_order(self) -> None:
        """Test that messages are returned in chronological order (reversed from DESC)"""
        engine = self._make_engine()
        engine.db.execute.return_value = [
            (3, 1, "1001", "Third", "text", "2025-01-01 10:03:00"),
            (2, 1, "1002", "Second", "text", "2025-01-01 10:02:00"),
            (1, 1, "1001", "First", "text", "2025-01-01 10:01:00"),
        ]

        result = engine.get_channel_messages(1)

        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        assert result[2]["id"] == 3


@pytest.mark.unit
class TestTeamMessagingEngineGetUserChannels:
    """Tests for TeamMessagingEngine.get_user_channels"""

    def _make_engine(self, db_type="sqlite"):
        mock_db = MagicMock()
        mock_db.db_type = db_type
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            return TeamMessagingEngine(mock_db, config)

    def test_get_user_channels_success(self) -> None:
        """Test getting user channels"""
        engine = self._make_engine()
        engine.db.execute.return_value = [
            (1, "general", "General chat", 0, "1001", "2025-01-01"),
            (2, "dev", "Development", 1, "1002", "2025-01-02"),
        ]

        result = engine.get_user_channels("1001")

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["channel_name"] == "general"
        assert result[0]["is_private"] is False
        assert result[1]["is_private"] is True

    def test_get_user_channels_empty(self) -> None:
        """Test getting user channels with no results"""
        engine = self._make_engine()
        engine.db.execute.return_value = None

        result = engine.get_user_channels("1001")

        assert result == []

    def test_get_user_channels_db_error(self) -> None:
        """Test getting user channels with db error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("db error")

        result = engine.get_user_channels("1001")

        assert result == []

    def test_get_user_channels_type_error(self) -> None:
        """Test getting user channels with type error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = TypeError("type error")

        result = engine.get_user_channels("1001")

        assert result == []

    def test_get_user_channels_postgresql(self) -> None:
        """Test getting user channels with postgresql"""
        engine = self._make_engine("postgresql")
        engine.db.execute.return_value = [
            (1, "general", "Chat", 0, "1001", "2025-01-01"),
        ]

        result = engine.get_user_channels("1001")

        assert len(result) == 1


@pytest.mark.unit
class TestTeamMessagingEngineGetAllChannels:
    """Tests for TeamMessagingEngine.get_all_channels"""

    def _make_engine(self, db_type="sqlite"):
        mock_db = MagicMock()
        mock_db.db_type = db_type
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import TeamMessagingEngine

            return TeamMessagingEngine(mock_db, config)

    def test_get_all_channels_success(self) -> None:
        """Test getting all public channels"""
        engine = self._make_engine()
        engine.db.execute.return_value = [
            (1, "general", "General", False, "1001", "2025-01-01"),
            (2, "random", "Random chat", False, "1002", "2025-01-02"),
        ]

        result = engine.get_all_channels()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["channel_name"] == "general"
        assert result[0]["created_by"] == "1001"

    def test_get_all_channels_empty(self) -> None:
        """Test getting all channels with no results"""
        engine = self._make_engine()
        engine.db.execute.return_value = None

        result = engine.get_all_channels()

        assert result == []

    def test_get_all_channels_db_error(self) -> None:
        """Test getting all channels with db error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("db error")

        result = engine.get_all_channels()

        assert result == []

    def test_get_all_channels_postgresql(self) -> None:
        """Test getting all channels with postgresql"""
        engine = self._make_engine("postgresql")
        engine.db.execute.return_value = [
            (1, "general", "Chat", False, "1001", "2025-01-01"),
        ]

        result = engine.get_all_channels()

        assert len(result) == 1

    def test_get_all_channels_passes_false_param(self) -> None:
        """Test that get_all_channels filters with is_private=False"""
        engine = self._make_engine()
        engine.db.execute.return_value = []

        engine.get_all_channels()

        args = engine.db.execute.call_args[0][1]
        assert args == (False,)


# ---------------------------------------------------------------------------
# FileShareEngine tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFileShareEngineInit:
    """Tests for FileShareEngine initialization"""

    def test_init_default_storage_path(self) -> None:
        """Test initialization with default storage path"""
        mock_db = MagicMock()
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import FileShareEngine

            engine = FileShareEngine(mock_db, config)

        assert engine.storage_path == "/var/pbx/shared_files"
        assert engine.db is mock_db

    def test_init_custom_storage_path(self) -> None:
        """Test initialization with custom storage path"""
        mock_db = MagicMock()
        config = {"file_sharing.storage_path": "/custom/path"}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import FileShareEngine

            engine = FileShareEngine(mock_db, config)

        assert engine.storage_path == "/custom/path"

    def test_init_with_none_db(self) -> None:
        """Test initialization with None db"""
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import FileShareEngine

            engine = FileShareEngine(None, config)

        assert engine.db is None

    def test_init_logs_message(self) -> None:
        """Test that init logs initialization message"""
        mock_db = MagicMock()
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.team_collaboration import FileShareEngine

            FileShareEngine(mock_db, config)

        mock_logger.info.assert_called_with("File Sharing Framework initialized")


@pytest.mark.unit
class TestFileShareEngineUploadFile:
    """Tests for FileShareEngine.upload_file"""

    def _make_engine(self, db_type="sqlite"):
        mock_db = MagicMock()
        mock_db.db_type = db_type
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import FileShareEngine

            return FileShareEngine(mock_db, config)

    def test_upload_file_success(self) -> None:
        """Test successful file upload"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [
            None,  # INSERT
            [(101,)],  # SELECT file ID
        ]
        file_data = {
            "file_name": "document.pdf",
            "file_path": "/var/pbx/shared_files/doc.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "uploaded_by": "1001",
            "shared_with": "1002,1003",
            "description": "Important doc",
            "expires_at": "2025-12-31",
        }

        result = engine.upload_file(file_data)

        assert result == 101

    def test_upload_file_defaults(self) -> None:
        """Test file upload with default values"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [None, [(1,)]]
        file_data = {
            "file_name": "test.txt",
            "file_path": "/path/to/test.txt",
            "uploaded_by": "1001",
        }

        engine.upload_file(file_data)

        insert_args = engine.db.execute.call_args_list[0][0][1]
        assert insert_args[2] == 0  # file_size default
        assert insert_args[3] is None  # mime_type default
        assert insert_args[5] == ""  # shared_with default
        assert insert_args[6] == ""  # description default
        assert insert_args[7] is None  # expires_at default

    def test_upload_file_no_result(self) -> None:
        """Test file upload with no result from query"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [None, None]
        file_data = {
            "file_name": "test.txt",
            "file_path": "/path/to/test.txt",
            "uploaded_by": "1001",
        }

        result = engine.upload_file(file_data)

        assert result is None

    def test_upload_file_empty_result(self) -> None:
        """Test file upload with empty result"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [None, []]
        file_data = {
            "file_name": "test.txt",
            "file_path": "/path/to/test.txt",
            "uploaded_by": "1001",
        }

        result = engine.upload_file(file_data)

        assert result is None

    def test_upload_file_result_first_item_none(self) -> None:
        """Test file upload when first row is None"""
        engine = self._make_engine()
        engine.db.execute.side_effect = [None, [None]]
        file_data = {
            "file_name": "test.txt",
            "file_path": "/path/to/test.txt",
            "uploaded_by": "1001",
        }

        result = engine.upload_file(file_data)

        assert result is None

    def test_upload_file_missing_key(self) -> None:
        """Test file upload with missing required key"""
        engine = self._make_engine()
        file_data = {"file_name": "test.txt"}  # missing file_path and uploaded_by

        result = engine.upload_file(file_data)

        assert result is None

    def test_upload_file_db_error(self) -> None:
        """Test file upload with database error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("db error")
        file_data = {
            "file_name": "test.txt",
            "file_path": "/path/to/test.txt",
            "uploaded_by": "1001",
        }

        result = engine.upload_file(file_data)

        assert result is None

    def test_upload_file_postgresql(self) -> None:
        """Test file upload with postgresql"""
        engine = self._make_engine("postgresql")
        engine.db.execute.side_effect = [None, [(200,)]]
        file_data = {
            "file_name": "test.txt",
            "file_path": "/path/to/test.txt",
            "uploaded_by": "1001",
        }

        result = engine.upload_file(file_data)

        assert result == 200


@pytest.mark.unit
class TestFileShareEngineGetSharedFiles:
    """Tests for FileShareEngine.get_shared_files"""

    def _make_engine(self, db_type="sqlite"):
        mock_db = MagicMock()
        mock_db.db_type = db_type
        config = {}

        with patch("pbx.features.team_collaboration.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.team_collaboration import FileShareEngine

            return FileShareEngine(mock_db, config)

    def test_get_shared_files_success(self) -> None:
        """Test getting shared files"""
        engine = self._make_engine()
        engine.db.execute.return_value = [
            (
                1,
                "doc.pdf",
                "/path/doc.pdf",
                1024,
                "application/pdf",
                "1001",
                "1002",
                "A doc",
                "2025-01-01",
                "2025-12-31",
            ),
        ]

        result = engine.get_shared_files("1001")

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["file_name"] == "doc.pdf"
        assert result[0]["file_size"] == 1024
        assert result[0]["mime_type"] == "application/pdf"
        assert result[0]["uploaded_by"] == "1001"
        assert result[0]["description"] == "A doc"

    def test_get_shared_files_uses_like_pattern(self) -> None:
        """Test that get_shared_files uses LIKE pattern for shared_with"""
        engine = self._make_engine()
        engine.db.execute.return_value = []

        engine.get_shared_files("1001")

        args = engine.db.execute.call_args[0][1]
        assert args == ("1001", "%1001%")

    def test_get_shared_files_empty(self) -> None:
        """Test getting shared files with no results"""
        engine = self._make_engine()
        engine.db.execute.return_value = None

        result = engine.get_shared_files("1001")

        assert result == []

    def test_get_shared_files_db_error(self) -> None:
        """Test getting shared files with db error"""
        engine = self._make_engine()
        engine.db.execute.side_effect = sqlite3.Error("db error")

        result = engine.get_shared_files("1001")

        assert result == []

    def test_get_shared_files_postgresql(self) -> None:
        """Test getting shared files with postgresql"""
        engine = self._make_engine("postgresql")
        engine.db.execute.return_value = [
            (
                1,
                "doc.pdf",
                "/path/doc.pdf",
                1024,
                "application/pdf",
                "1001",
                "1002",
                "A doc",
                "2025-01-01",
                None,
            ),
        ]

        result = engine.get_shared_files("1001")

        assert len(result) == 1
