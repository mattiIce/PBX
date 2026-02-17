#!/usr/bin/env python3
"""
Tests for Callback Queue System
"""

import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.callback_queue import CallbackQueue, CallbackStatus


@pytest.mark.unit
class TestCallbackStatus:
    """Tests for CallbackStatus enum"""

    def test_status_values(self) -> None:
        """Test all callback status enum values exist"""
        assert CallbackStatus.PENDING.value == "pending"
        assert CallbackStatus.SCHEDULED.value == "scheduled"
        assert CallbackStatus.IN_PROGRESS.value == "in_progress"
        assert CallbackStatus.COMPLETED.value == "completed"
        assert CallbackStatus.FAILED.value == "failed"
        assert CallbackStatus.CANCELLED.value == "cancelled"

    def test_status_from_value(self) -> None:
        """Test creating status from string value"""
        assert CallbackStatus("pending") == CallbackStatus.PENDING
        assert CallbackStatus("scheduled") == CallbackStatus.SCHEDULED
        assert CallbackStatus("in_progress") == CallbackStatus.IN_PROGRESS
        assert CallbackStatus("completed") == CallbackStatus.COMPLETED
        assert CallbackStatus("failed") == CallbackStatus.FAILED
        assert CallbackStatus("cancelled") == CallbackStatus.CANCELLED

    def test_invalid_status_raises(self) -> None:
        """Test that invalid status string raises ValueError"""
        with pytest.raises(ValueError):
            CallbackStatus("invalid_status")


@pytest.mark.unit
class TestCallbackQueueInit:
    """Tests for CallbackQueue initialization"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_init_defaults_no_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with no config or database"""
        queue = CallbackQueue()

        assert queue.config == {}
        assert queue.database is None
        assert queue.enabled is False
        assert queue.max_wait_time == 30
        assert queue.retry_attempts == 3
        assert queue.retry_interval == 5
        assert queue.callbacks == {}
        assert queue.queue_callbacks == {}

    @patch("pbx.features.callback_queue.get_logger")
    def test_init_with_config_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with enabled config"""
        config = {
            "features": {
                "callback_queue": {
                    "enabled": True,
                    "max_wait_minutes": 60,
                    "retry_attempts": 5,
                    "retry_interval_minutes": 10,
                }
            }
        }

        queue = CallbackQueue(config=config)

        assert queue.enabled is True
        assert queue.max_wait_time == 60
        assert queue.retry_attempts == 5
        assert queue.retry_interval == 10

    @patch("pbx.features.callback_queue.get_logger")
    def test_init_with_config_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with disabled config"""
        config = {
            "features": {
                "callback_queue": {
                    "enabled": False,
                }
            }
        }

        queue = CallbackQueue(config=config)

        assert queue.enabled is False

    @patch("pbx.features.callback_queue.get_logger")
    def test_init_with_database_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization calls schema and load when database is enabled"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        queue = CallbackQueue(database=mock_db)

        # Verify schema initialization was called
        assert mock_db.connection.cursor.called
        assert mock_db.connection.commit.called

    @patch("pbx.features.callback_queue.get_logger")
    def test_init_with_database_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization skips database when disabled"""
        mock_db = MagicMock()
        mock_db.enabled = False

        queue = CallbackQueue(database=mock_db)

        mock_db.connection.cursor.assert_not_called()

    @patch("pbx.features.callback_queue.get_logger")
    def test_init_logs_when_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization logs info when enabled"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        config = {
            "features": {
                "callback_queue": {
                    "enabled": True,
                    "max_wait_minutes": 30,
                    "retry_attempts": 3,
                }
            }
        }

        queue = CallbackQueue(config=config)

        mock_logger.info.assert_any_call("Callback queue system initialized")

    @patch("pbx.features.callback_queue.get_logger")
    def test_init_empty_features_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with empty features config uses defaults"""
        config = {"features": {}}

        queue = CallbackQueue(config=config)

        assert queue.enabled is False
        assert queue.max_wait_time == 30
        assert queue.retry_attempts == 3
        assert queue.retry_interval == 5


@pytest.mark.unit
class TestInitializeSchema:
    """Tests for _initialize_schema method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_initialize_schema_success(self, mock_get_logger: MagicMock) -> None:
        """Test successful schema initialization"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        queue = CallbackQueue(database=mock_db)

        # 4 execute calls for schema init: 1 CREATE TABLE + 3 CREATE INDEX
        # plus 1 for _load_callbacks_from_database SELECT
        schema_calls = mock_cursor.execute.call_count
        assert schema_calls >= 4

    @patch("pbx.features.callback_queue.get_logger")
    def test_initialize_schema_no_database(self, mock_get_logger: MagicMock) -> None:
        """Test schema initialization with no database"""
        queue = CallbackQueue()
        # Should not raise; just return early
        queue._initialize_schema()

    @patch("pbx.features.callback_queue.get_logger")
    def test_initialize_schema_database_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test schema initialization with disabled database"""
        mock_db = MagicMock()
        mock_db.enabled = False

        queue = CallbackQueue(database=mock_db)

        # Calling it explicitly should return early
        queue._initialize_schema()
        mock_db.connection.cursor.assert_not_called()

    @patch("pbx.features.callback_queue.get_logger")
    def test_initialize_schema_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        """Test schema initialization handles sqlite3 errors"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.connection.cursor.side_effect = sqlite3.Error("connection failed")

        queue = CallbackQueue.__new__(CallbackQueue)
        queue.logger = mock_logger
        queue.config = {}
        queue.database = mock_db
        queue.enabled = False
        queue.max_wait_time = 30
        queue.retry_attempts = 3
        queue.retry_interval = 5
        queue.callbacks = {}
        queue.queue_callbacks = {}

        queue._initialize_schema()

        mock_logger.error.assert_called_once()
        assert "Error initializing callback queue schema" in mock_logger.error.call_args[0][0]


@pytest.mark.unit
class TestLoadCallbacksFromDatabase:
    """Tests for _load_callbacks_from_database method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_load_callbacks_no_database(self, mock_get_logger: MagicMock) -> None:
        """Test loading callbacks without database does nothing"""
        queue = CallbackQueue()
        queue._load_callbacks_from_database()
        assert queue.callbacks == {}

    @patch("pbx.features.callback_queue.get_logger")
    def test_load_callbacks_database_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test loading callbacks with disabled database does nothing"""
        mock_db = MagicMock()
        mock_db.enabled = False

        queue = CallbackQueue(database=mock_db)
        queue._load_callbacks_from_database()
        assert queue.callbacks == {}

    @patch("pbx.features.callback_queue.get_logger")
    def test_load_callbacks_with_active_rows(self, mock_get_logger: MagicMock) -> None:
        """Test loading active callbacks from database"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.enabled = True
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        now = datetime.now(UTC)
        rows = [
            (
                "cb_001", "queue_1", "5551234", "John Doe",
                now, now + timedelta(minutes=10), "scheduled",
                0, 3, None, None,
            ),
            (
                "cb_002", "queue_1", "5555678", "Jane Smith",
                now, now + timedelta(minutes=20), "in_progress",
                1, 3, "agent_1", now,
            ),
        ]
        mock_cursor.fetchall.return_value = rows

        queue = CallbackQueue.__new__(CallbackQueue)
        queue.logger = mock_logger
        queue.config = {}
        queue.database = mock_db
        queue.enabled = False
        queue.max_wait_time = 30
        queue.retry_attempts = 3
        queue.retry_interval = 5
        queue.callbacks = {}
        queue.queue_callbacks = {}

        queue._load_callbacks_from_database()

        assert "cb_001" in queue.callbacks
        assert "cb_002" in queue.callbacks
        assert queue.callbacks["cb_001"]["status"] == CallbackStatus.SCHEDULED
        assert queue.callbacks["cb_002"]["status"] == CallbackStatus.IN_PROGRESS
        assert queue.callbacks["cb_002"]["agent_id"] == "agent_1"
        assert queue.callbacks["cb_002"]["started_at"] == now
        assert "queue_1" in queue.queue_callbacks
        assert len(queue.queue_callbacks["queue_1"]) == 2

    @patch("pbx.features.callback_queue.get_logger")
    def test_load_callbacks_invalid_status_defaults_to_scheduled(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test that invalid status string falls back to SCHEDULED"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.enabled = True
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        now = datetime.now(UTC)
        rows = [
            (
                "cb_bad", "queue_x", "5559999", "Bad Status",
                now, now, "nonexistent_status",
                0, 3, None, None,
            ),
        ]
        mock_cursor.fetchall.return_value = rows

        queue = CallbackQueue.__new__(CallbackQueue)
        queue.logger = mock_logger
        queue.config = {}
        queue.database = mock_db
        queue.enabled = False
        queue.max_wait_time = 30
        queue.retry_attempts = 3
        queue.retry_interval = 5
        queue.callbacks = {}
        queue.queue_callbacks = {}

        queue._load_callbacks_from_database()

        assert queue.callbacks["cb_bad"]["status"] == CallbackStatus.SCHEDULED

    @patch("pbx.features.callback_queue.get_logger")
    def test_load_callbacks_multiple_queues(self, mock_get_logger: MagicMock) -> None:
        """Test loading callbacks populates multiple queues correctly"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.enabled = True
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        now = datetime.now(UTC)
        rows = [
            (
                "cb_a", "queue_alpha", "5551111", "Alice",
                now, now, "scheduled", 0, 3, None, None,
            ),
            (
                "cb_b", "queue_beta", "5552222", "Bob",
                now, now, "pending", 0, 3, None, None,
            ),
        ]
        mock_cursor.fetchall.return_value = rows

        queue = CallbackQueue.__new__(CallbackQueue)
        queue.logger = mock_logger
        queue.config = {}
        queue.database = mock_db
        queue.enabled = False
        queue.max_wait_time = 30
        queue.retry_attempts = 3
        queue.retry_interval = 5
        queue.callbacks = {}
        queue.queue_callbacks = {}

        queue._load_callbacks_from_database()

        assert "queue_alpha" in queue.queue_callbacks
        assert "queue_beta" in queue.queue_callbacks
        assert len(queue.queue_callbacks["queue_alpha"]) == 1
        assert len(queue.queue_callbacks["queue_beta"]) == 1

    @patch("pbx.features.callback_queue.get_logger")
    def test_load_callbacks_database_error(self, mock_get_logger: MagicMock) -> None:
        """Test loading callbacks handles database errors gracefully"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.enabled = True
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = KeyError("some key error")

        queue = CallbackQueue.__new__(CallbackQueue)
        queue.logger = mock_logger
        queue.config = {}
        queue.database = mock_db
        queue.enabled = False
        queue.max_wait_time = 30
        queue.retry_attempts = 3
        queue.retry_interval = 5
        queue.callbacks = {}
        queue.queue_callbacks = {}

        queue._load_callbacks_from_database()

        mock_logger.error.assert_called_once()
        assert "Error loading callbacks from database" in mock_logger.error.call_args[0][0]

    @patch("pbx.features.callback_queue.get_logger")
    def test_load_callbacks_empty_result(self, mock_get_logger: MagicMock) -> None:
        """Test loading callbacks with no active rows"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.enabled = True
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        queue = CallbackQueue.__new__(CallbackQueue)
        queue.logger = mock_logger
        queue.config = {}
        queue.database = mock_db
        queue.enabled = False
        queue.max_wait_time = 30
        queue.retry_attempts = 3
        queue.retry_interval = 5
        queue.callbacks = {}
        queue.queue_callbacks = {}

        queue._load_callbacks_from_database()

        assert queue.callbacks == {}
        assert queue.queue_callbacks == {}


@pytest.mark.unit
class TestSaveCallbackToDatabase:
    """Tests for _save_callback_to_database method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_save_no_database(self, mock_get_logger: MagicMock) -> None:
        """Test save returns False when no database"""
        queue = CallbackQueue()
        result = queue._save_callback_to_database("cb_001")
        assert result is False

    @patch("pbx.features.callback_queue.get_logger")
    def test_save_database_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test save returns False when database disabled"""
        mock_db = MagicMock()
        mock_db.enabled = False

        queue = CallbackQueue(database=mock_db)
        result = queue._save_callback_to_database("cb_001")
        assert result is False

    @patch("pbx.features.callback_queue.get_logger")
    def test_save_nonexistent_callback(self, mock_get_logger: MagicMock) -> None:
        """Test save returns False when callback does not exist"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        queue = CallbackQueue(database=mock_db)
        result = queue._save_callback_to_database("nonexistent_id")
        assert result is False

    @patch("pbx.features.callback_queue.get_logger")
    def test_save_callback_sqlite(self, mock_get_logger: MagicMock) -> None:
        """Test saving callback with SQLite database"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        queue = CallbackQueue(database=mock_db)

        now = datetime.now(UTC)
        queue.callbacks["cb_test"] = {
            "callback_id": "cb_test",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": "Test User",
            "requested_at": now,
            "callback_time": now + timedelta(minutes=10),
            "status": CallbackStatus.SCHEDULED,
            "attempts": 0,
            "max_attempts": 3,
        }

        result = queue._save_callback_to_database("cb_test")
        assert result is True
        mock_db.connection.commit.assert_called()

    @patch("pbx.features.callback_queue.get_logger")
    def test_save_callback_postgresql(self, mock_get_logger: MagicMock) -> None:
        """Test saving callback with PostgreSQL database"""
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        queue = CallbackQueue(database=mock_db)

        now = datetime.now(UTC)
        queue.callbacks["cb_pg"] = {
            "callback_id": "cb_pg",
            "queue_id": "queue_2",
            "caller_number": "5559876",
            "caller_name": "PG User",
            "requested_at": now,
            "callback_time": now + timedelta(minutes=5),
            "status": CallbackStatus.IN_PROGRESS,
            "attempts": 1,
            "max_attempts": 3,
            "agent_id": "agent_1",
            "started_at": now,
        }

        result = queue._save_callback_to_database("cb_pg")
        assert result is True

        # Verify the SQL uses %s placeholders (PostgreSQL style)
        execute_call = mock_cursor.execute.call_args_list[-1]
        sql = execute_call[0][0]
        assert "ON CONFLICT" in sql
        assert "%s" in sql

    @patch("pbx.features.callback_queue.get_logger")
    def test_save_callback_database_error(self, mock_get_logger: MagicMock) -> None:
        """Test save handles database errors gracefully"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        queue = CallbackQueue(database=mock_db)

        now = datetime.now(UTC)
        queue.callbacks["cb_err"] = {
            "callback_id": "cb_err",
            "queue_id": "queue_1",
            "caller_number": "5550000",
            "status": CallbackStatus.SCHEDULED,
            "attempts": 0,
            "max_attempts": 3,
            "requested_at": now,
            "callback_time": now,
        }

        # Make the save cursor execute fail
        save_cursor = MagicMock()
        save_cursor.execute.side_effect = sqlite3.Error("write error")
        # First cursor calls are from __init__; subsequent ones from _save
        call_count = mock_db.connection.cursor.call_count
        mock_db.connection.cursor.return_value = save_cursor

        result = queue._save_callback_to_database("cb_err")
        assert result is False
        mock_logger.error.assert_called()


@pytest.mark.unit
class TestRequestCallback:
    """Tests for request_callback method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_callback_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test requesting callback when queue is disabled"""
        queue = CallbackQueue()
        result = queue.request_callback("queue_1", "5551234")

        assert "error" in result
        assert result["error"] == "Callback queue not enabled"

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_callback_success_asap(self, mock_get_logger: MagicMock) -> None:
        """Test requesting callback ASAP (no preferred time)"""
        config = {"features": {"callback_queue": {"enabled": True, "retry_attempts": 3}}}
        queue = CallbackQueue(config=config)

        result = queue.request_callback("queue_1", "5551234", "John Doe")

        assert "callback_id" in result
        assert result["status"] == "scheduled"
        assert result["queue_position"] == 1
        assert "estimated_time" in result

        # Verify callback was stored
        callback_id = result["callback_id"]
        assert callback_id in queue.callbacks
        assert queue.callbacks[callback_id]["caller_number"] == "5551234"
        assert queue.callbacks[callback_id]["caller_name"] == "John Doe"
        assert queue.callbacks[callback_id]["status"] == CallbackStatus.SCHEDULED

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_callback_with_preferred_time(self, mock_get_logger: MagicMock) -> None:
        """Test requesting callback with preferred time"""
        config = {"features": {"callback_queue": {"enabled": True}}}
        queue = CallbackQueue(config=config)

        preferred = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
        result = queue.request_callback("queue_1", "5551234", preferred_time=preferred)

        callback_id = result["callback_id"]
        assert queue.callbacks[callback_id]["callback_time"] == preferred

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_callback_asap_estimates_from_queue_length(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test ASAP callback time estimation based on queue length"""
        config = {"features": {"callback_queue": {"enabled": True}}}
        queue = CallbackQueue(config=config)

        # Pre-populate queue with existing callbacks
        queue.queue_callbacks["queue_1"] = ["existing_1", "existing_2"]

        before = datetime.now(UTC)
        result = queue.request_callback("queue_1", "5551234")
        after = datetime.now(UTC)

        callback_id = result["callback_id"]
        callback_time = queue.callbacks[callback_id]["callback_time"]

        # Queue had 2 items before, so estimate should be ~10 minutes (2 * 5)
        expected_min = before + timedelta(minutes=10)
        expected_max = after + timedelta(minutes=10)
        assert expected_min <= callback_time <= expected_max

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_callback_adds_to_queue_callbacks(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test that request adds callback to queue_callbacks"""
        config = {"features": {"callback_queue": {"enabled": True}}}
        queue = CallbackQueue(config=config)

        result = queue.request_callback("new_queue", "5551111")

        assert "new_queue" in queue.queue_callbacks
        assert result["callback_id"] in queue.queue_callbacks["new_queue"]

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_callback_no_caller_name(self, mock_get_logger: MagicMock) -> None:
        """Test requesting callback without caller name"""
        config = {"features": {"callback_queue": {"enabled": True}}}
        queue = CallbackQueue(config=config)

        result = queue.request_callback("queue_1", "5551234")

        callback_id = result["callback_id"]
        assert queue.callbacks[callback_id]["caller_name"] is None

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_callback_saves_to_database(self, mock_get_logger: MagicMock) -> None:
        """Test that requesting a callback calls save to database"""
        config = {"features": {"callback_queue": {"enabled": True}}}
        queue = CallbackQueue(config=config)

        with patch.object(queue, "_save_callback_to_database") as mock_save:
            result = queue.request_callback("queue_1", "5551234")
            mock_save.assert_called_once_with(result["callback_id"])

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_multiple_callbacks_unique_ids(self, mock_get_logger: MagicMock) -> None:
        """Test multiple callback requests generate unique IDs"""
        config = {"features": {"callback_queue": {"enabled": True}}}
        queue = CallbackQueue(config=config)

        result1 = queue.request_callback("queue_1", "5551111")
        result2 = queue.request_callback("queue_1", "5552222")

        assert result1["callback_id"] != result2["callback_id"]
        assert result1["queue_position"] == 1
        assert result2["queue_position"] == 2


@pytest.mark.unit
class TestGetNextCallback:
    """Tests for get_next_callback method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_next_nonexistent_queue(self, mock_get_logger: MagicMock) -> None:
        """Test get_next_callback for a queue that does not exist"""
        queue = CallbackQueue()
        result = queue.get_next_callback("nonexistent")
        assert result is None

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_next_empty_queue(self, mock_get_logger: MagicMock) -> None:
        """Test get_next_callback for empty queue"""
        queue = CallbackQueue()
        queue.queue_callbacks["empty_q"] = []
        result = queue.get_next_callback("empty_q")
        assert result is None

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_next_callback_ready(self, mock_get_logger: MagicMock) -> None:
        """Test get_next_callback returns ready callback"""
        queue = CallbackQueue()
        past_time = datetime.now(UTC) - timedelta(minutes=5)
        queue.callbacks["cb_ready"] = {
            "callback_id": "cb_ready",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": past_time,
        }
        queue.queue_callbacks["queue_1"] = ["cb_ready"]

        result = queue.get_next_callback("queue_1")

        assert result is not None
        assert result["callback_id"] == "cb_ready"

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_next_callback_not_yet_ready(self, mock_get_logger: MagicMock) -> None:
        """Test get_next_callback when callback time is in the future"""
        queue = CallbackQueue()
        future_time = datetime.now(UTC) + timedelta(hours=1)
        queue.callbacks["cb_future"] = {
            "callback_id": "cb_future",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": future_time,
        }
        queue.queue_callbacks["queue_1"] = ["cb_future"]

        result = queue.get_next_callback("queue_1")
        assert result is None

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_next_callback_skips_non_scheduled(self, mock_get_logger: MagicMock) -> None:
        """Test get_next_callback skips in-progress or completed callbacks"""
        queue = CallbackQueue()
        past_time = datetime.now(UTC) - timedelta(minutes=5)
        queue.callbacks["cb_in_progress"] = {
            "callback_id": "cb_in_progress",
            "queue_id": "queue_1",
            "caller_number": "5551111",
            "status": CallbackStatus.IN_PROGRESS,
            "callback_time": past_time,
        }
        queue.callbacks["cb_scheduled"] = {
            "callback_id": "cb_scheduled",
            "queue_id": "queue_1",
            "caller_number": "5552222",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": past_time,
        }
        queue.queue_callbacks["queue_1"] = ["cb_in_progress", "cb_scheduled"]

        result = queue.get_next_callback("queue_1")

        assert result is not None
        assert result["callback_id"] == "cb_scheduled"

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_next_callback_missing_callback_data(self, mock_get_logger: MagicMock) -> None:
        """Test get_next_callback skips IDs not in callbacks dict"""
        queue = CallbackQueue()
        queue.queue_callbacks["queue_1"] = ["orphan_id"]

        result = queue.get_next_callback("queue_1")
        assert result is None


@pytest.mark.unit
class TestStartCallback:
    """Tests for start_callback method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_start_callback_not_found(self, mock_get_logger: MagicMock) -> None:
        """Test starting a callback that does not exist"""
        queue = CallbackQueue()
        result = queue.start_callback("nonexistent", "agent_1")

        assert "error" in result
        assert result["error"] == "Callback not found"

    @patch("pbx.features.callback_queue.get_logger")
    def test_start_callback_success(self, mock_get_logger: MagicMock) -> None:
        """Test successfully starting a callback"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_start"] = {
            "callback_id": "cb_start",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": "Test Caller",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }

        with patch.object(queue, "_save_callback_to_database"):
            result = queue.start_callback("cb_start", "agent_42")

        assert result["callback_id"] == "cb_start"
        assert result["caller_number"] == "5551234"
        assert result["caller_name"] == "Test Caller"
        assert result["queue_id"] == "queue_1"

        callback = queue.callbacks["cb_start"]
        assert callback["status"] == CallbackStatus.IN_PROGRESS
        assert callback["agent_id"] == "agent_42"
        assert callback["attempts"] == 1
        assert "started_at" in callback

    @patch("pbx.features.callback_queue.get_logger")
    def test_start_callback_increments_attempts(self, mock_get_logger: MagicMock) -> None:
        """Test that start_callback increments the attempts counter"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_retry"] = {
            "callback_id": "cb_retry",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": "Retry Caller",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 2,
            "max_attempts": 5,
        }

        with patch.object(queue, "_save_callback_to_database"):
            queue.start_callback("cb_retry", "agent_1")

        assert queue.callbacks["cb_retry"]["attempts"] == 3

    @patch("pbx.features.callback_queue.get_logger")
    def test_start_callback_saves_to_database(self, mock_get_logger: MagicMock) -> None:
        """Test that start_callback saves to database"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_db"] = {
            "callback_id": "cb_db",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": None,
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }

        with patch.object(queue, "_save_callback_to_database") as mock_save:
            queue.start_callback("cb_db", "agent_1")
            mock_save.assert_called_once_with("cb_db")


@pytest.mark.unit
class TestCompleteCallback:
    """Tests for complete_callback method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_complete_callback_not_found(self, mock_get_logger: MagicMock) -> None:
        """Test completing a callback that does not exist"""
        queue = CallbackQueue()
        result = queue.complete_callback("nonexistent", True)
        assert result is False

    @patch("pbx.features.callback_queue.get_logger")
    def test_complete_callback_success(self, mock_get_logger: MagicMock) -> None:
        """Test successfully completing a callback"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_done"] = {
            "callback_id": "cb_done",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.IN_PROGRESS,
            "callback_time": now,
            "requested_at": now,
            "attempts": 1,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_done"]

        with patch.object(queue, "_save_callback_to_database"):
            result = queue.complete_callback("cb_done", True, notes="Call resolved")

        assert result is True
        callback = queue.callbacks["cb_done"]
        assert callback["status"] == CallbackStatus.COMPLETED
        assert callback["notes"] == "Call resolved"
        assert "completed_at" in callback
        assert "cb_done" not in queue.queue_callbacks["queue_1"]

    @patch("pbx.features.callback_queue.get_logger")
    def test_complete_callback_failure_with_retries_remaining(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test failing a callback with retries remaining reschedules it"""
        config = {
            "features": {"callback_queue": {"enabled": True, "retry_interval_minutes": 10}}
        }
        queue = CallbackQueue(config=config)
        now = datetime.now(UTC)
        queue.callbacks["cb_retry"] = {
            "callback_id": "cb_retry",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.IN_PROGRESS,
            "callback_time": now,
            "requested_at": now,
            "attempts": 1,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_retry"]

        before = datetime.now(UTC)
        with patch.object(queue, "_save_callback_to_database"):
            result = queue.complete_callback("cb_retry", False)
        after = datetime.now(UTC)

        assert result is True
        callback = queue.callbacks["cb_retry"]
        assert callback["status"] == CallbackStatus.SCHEDULED
        # Callback time should be ~10 minutes from now
        expected_min = before + timedelta(minutes=10)
        expected_max = after + timedelta(minutes=10)
        assert expected_min <= callback["callback_time"] <= expected_max
        # Should still be in the queue
        assert "cb_retry" in queue.queue_callbacks["queue_1"]

    @patch("pbx.features.callback_queue.get_logger")
    def test_complete_callback_failure_max_attempts_reached(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test failing a callback that has reached max attempts marks it as failed"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_final_fail"] = {
            "callback_id": "cb_final_fail",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.IN_PROGRESS,
            "callback_time": now,
            "requested_at": now,
            "attempts": 3,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_final_fail"]

        with patch.object(queue, "_save_callback_to_database"):
            result = queue.complete_callback("cb_final_fail", False, notes="No answer")

        assert result is True
        callback = queue.callbacks["cb_final_fail"]
        assert callback["status"] == CallbackStatus.FAILED
        assert callback["notes"] == "No answer"
        assert "failed_at" in callback
        assert "cb_final_fail" not in queue.queue_callbacks["queue_1"]

    @patch("pbx.features.callback_queue.get_logger")
    def test_complete_callback_success_removes_from_queue(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test completing successfully removes callback from queue"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_rem1"] = {
            "callback_id": "cb_rem1",
            "queue_id": "queue_1",
            "caller_number": "5551111",
            "status": CallbackStatus.IN_PROGRESS,
            "callback_time": now,
            "requested_at": now,
            "attempts": 1,
            "max_attempts": 3,
        }
        queue.callbacks["cb_rem2"] = {
            "callback_id": "cb_rem2",
            "queue_id": "queue_1",
            "caller_number": "5552222",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_rem1", "cb_rem2"]

        with patch.object(queue, "_save_callback_to_database"):
            queue.complete_callback("cb_rem1", True)

        assert "cb_rem1" not in queue.queue_callbacks["queue_1"]
        assert "cb_rem2" in queue.queue_callbacks["queue_1"]

    @patch("pbx.features.callback_queue.get_logger")
    def test_complete_callback_success_no_notes(self, mock_get_logger: MagicMock) -> None:
        """Test completing successfully without notes"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_nonotes"] = {
            "callback_id": "cb_nonotes",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.IN_PROGRESS,
            "callback_time": now,
            "requested_at": now,
            "attempts": 1,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_nonotes"]

        with patch.object(queue, "_save_callback_to_database"):
            queue.complete_callback("cb_nonotes", True)

        assert queue.callbacks["cb_nonotes"]["notes"] is None

    @patch("pbx.features.callback_queue.get_logger")
    def test_complete_callback_queue_id_not_in_queue_callbacks(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test completing callback when queue_id is missing from queue_callbacks"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_orphan"] = {
            "callback_id": "cb_orphan",
            "queue_id": "missing_queue",
            "caller_number": "5559999",
            "status": CallbackStatus.IN_PROGRESS,
            "callback_time": now,
            "requested_at": now,
            "attempts": 3,
            "max_attempts": 3,
        }
        # Do not add "missing_queue" to queue_callbacks

        with patch.object(queue, "_save_callback_to_database"):
            result = queue.complete_callback("cb_orphan", False)

        # Should not raise, just skip the remove step
        assert result is True
        assert queue.callbacks["cb_orphan"]["status"] == CallbackStatus.FAILED


@pytest.mark.unit
class TestCancelCallback:
    """Tests for cancel_callback method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_cancel_callback_not_found(self, mock_get_logger: MagicMock) -> None:
        """Test cancelling a callback that does not exist"""
        queue = CallbackQueue()
        result = queue.cancel_callback("nonexistent")
        assert result is False

    @patch("pbx.features.callback_queue.get_logger")
    def test_cancel_callback_success(self, mock_get_logger: MagicMock) -> None:
        """Test successfully cancelling a callback"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_cancel"] = {
            "callback_id": "cb_cancel",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_cancel"]

        with patch.object(queue, "_save_callback_to_database"):
            result = queue.cancel_callback("cb_cancel")

        assert result is True
        callback = queue.callbacks["cb_cancel"]
        assert callback["status"] == CallbackStatus.CANCELLED
        assert "cancelled_at" in callback
        assert "cb_cancel" not in queue.queue_callbacks["queue_1"]

    @patch("pbx.features.callback_queue.get_logger")
    def test_cancel_callback_removes_from_queue(self, mock_get_logger: MagicMock) -> None:
        """Test cancel removes callback from queue_callbacks"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_c1"] = {
            "callback_id": "cb_c1",
            "queue_id": "queue_1",
            "caller_number": "5551111",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }
        queue.callbacks["cb_c2"] = {
            "callback_id": "cb_c2",
            "queue_id": "queue_1",
            "caller_number": "5552222",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_c1", "cb_c2"]

        with patch.object(queue, "_save_callback_to_database"):
            queue.cancel_callback("cb_c1")

        assert queue.queue_callbacks["queue_1"] == ["cb_c2"]

    @patch("pbx.features.callback_queue.get_logger")
    def test_cancel_callback_queue_not_in_queue_callbacks(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test cancel when queue_id is not in queue_callbacks does not raise"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_orphan"] = {
            "callback_id": "cb_orphan",
            "queue_id": "gone_queue",
            "caller_number": "5550000",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }

        with patch.object(queue, "_save_callback_to_database"):
            result = queue.cancel_callback("cb_orphan")

        assert result is True
        assert queue.callbacks["cb_orphan"]["status"] == CallbackStatus.CANCELLED

    @patch("pbx.features.callback_queue.get_logger")
    def test_cancel_callback_saves_to_database(self, mock_get_logger: MagicMock) -> None:
        """Test that cancel saves callback to database"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_save"] = {
            "callback_id": "cb_save",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_save"]

        with patch.object(queue, "_save_callback_to_database") as mock_save:
            queue.cancel_callback("cb_save")
            mock_save.assert_called_once_with("cb_save")


@pytest.mark.unit
class TestGetCallbackInfo:
    """Tests for get_callback_info method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_info_not_found(self, mock_get_logger: MagicMock) -> None:
        """Test getting info for nonexistent callback"""
        queue = CallbackQueue()
        result = queue.get_callback_info("nonexistent")
        assert result is None

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_info_success(self, mock_get_logger: MagicMock) -> None:
        """Test getting callback info successfully"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_info"] = {
            "callback_id": "cb_info",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": "Info User",
            "status": CallbackStatus.SCHEDULED,
            "requested_at": now,
            "callback_time": now + timedelta(minutes=10),
            "attempts": 0,
        }

        result = queue.get_callback_info("cb_info")

        assert result is not None
        assert result["callback_id"] == "cb_info"
        assert result["queue_id"] == "queue_1"
        assert result["caller_number"] == "5551234"
        assert result["caller_name"] == "Info User"
        assert result["status"] == "scheduled"
        assert result["attempts"] == 0
        assert "requested_at" in result
        assert "callback_time" in result

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_info_returns_serialized_status(self, mock_get_logger: MagicMock) -> None:
        """Test that get_callback_info returns status as string value"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        queue.callbacks["cb_status"] = {
            "callback_id": "cb_status",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": None,
            "status": CallbackStatus.IN_PROGRESS,
            "requested_at": now,
            "callback_time": now,
            "attempts": 2,
        }

        result = queue.get_callback_info("cb_status")
        assert result["status"] == "in_progress"

    @patch("pbx.features.callback_queue.get_logger")
    def test_get_info_returns_iso_formatted_dates(self, mock_get_logger: MagicMock) -> None:
        """Test that dates are returned in ISO format"""
        queue = CallbackQueue()
        now = datetime(2026, 1, 15, 12, 30, 0, tzinfo=UTC)
        later = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
        queue.callbacks["cb_dates"] = {
            "callback_id": "cb_dates",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": None,
            "status": CallbackStatus.SCHEDULED,
            "requested_at": now,
            "callback_time": later,
            "attempts": 0,
        }

        result = queue.get_callback_info("cb_dates")
        assert result["requested_at"] == now.isoformat()
        assert result["callback_time"] == later.isoformat()


@pytest.mark.unit
class TestListQueueCallbacks:
    """Tests for list_queue_callbacks method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_list_empty_queue(self, mock_get_logger: MagicMock) -> None:
        """Test listing callbacks for nonexistent queue"""
        queue = CallbackQueue()
        result = queue.list_queue_callbacks("nonexistent")
        assert result == []

    @patch("pbx.features.callback_queue.get_logger")
    def test_list_all_callbacks(self, mock_get_logger: MagicMock) -> None:
        """Test listing all callbacks in a queue"""
        queue = CallbackQueue()
        now = datetime.now(UTC)
        for i in range(3):
            cb_id = f"cb_list_{i}"
            queue.callbacks[cb_id] = {
                "callback_id": cb_id,
                "queue_id": "queue_1",
                "caller_number": f"555{i:04d}",
                "caller_name": f"User {i}",
                "status": CallbackStatus.SCHEDULED,
                "requested_at": now,
                "callback_time": now + timedelta(minutes=i * 5),
                "attempts": 0,
            }
        queue.queue_callbacks["queue_1"] = ["cb_list_0", "cb_list_1", "cb_list_2"]

        result = queue.list_queue_callbacks("queue_1")
        assert len(result) == 3

    @patch("pbx.features.callback_queue.get_logger")
    def test_list_callbacks_filtered_by_status(self, mock_get_logger: MagicMock) -> None:
        """Test listing callbacks filtered by status"""
        queue = CallbackQueue()
        now = datetime.now(UTC)

        queue.callbacks["cb_sched"] = {
            "callback_id": "cb_sched",
            "queue_id": "queue_1",
            "caller_number": "5551111",
            "caller_name": "Scheduled",
            "status": CallbackStatus.SCHEDULED,
            "requested_at": now,
            "callback_time": now,
            "attempts": 0,
        }
        queue.callbacks["cb_prog"] = {
            "callback_id": "cb_prog",
            "queue_id": "queue_1",
            "caller_number": "5552222",
            "caller_name": "In Progress",
            "status": CallbackStatus.IN_PROGRESS,
            "requested_at": now,
            "callback_time": now,
            "attempts": 1,
        }
        queue.queue_callbacks["queue_1"] = ["cb_sched", "cb_prog"]

        scheduled = queue.list_queue_callbacks("queue_1", status=CallbackStatus.SCHEDULED)
        assert len(scheduled) == 1
        assert scheduled[0]["callback_id"] == "cb_sched"

        in_progress = queue.list_queue_callbacks("queue_1", status=CallbackStatus.IN_PROGRESS)
        assert len(in_progress) == 1
        assert in_progress[0]["callback_id"] == "cb_prog"

    @patch("pbx.features.callback_queue.get_logger")
    def test_list_callbacks_no_match_for_status(self, mock_get_logger: MagicMock) -> None:
        """Test listing callbacks with status filter that matches nothing"""
        queue = CallbackQueue()
        now = datetime.now(UTC)

        queue.callbacks["cb_active"] = {
            "callback_id": "cb_active",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": "Active",
            "status": CallbackStatus.SCHEDULED,
            "requested_at": now,
            "callback_time": now,
            "attempts": 0,
        }
        queue.queue_callbacks["queue_1"] = ["cb_active"]

        result = queue.list_queue_callbacks("queue_1", status=CallbackStatus.FAILED)
        assert result == []

    @patch("pbx.features.callback_queue.get_logger")
    def test_list_callbacks_skips_missing_callback_data(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test listing callbacks skips orphaned IDs"""
        queue = CallbackQueue()
        now = datetime.now(UTC)

        queue.callbacks["cb_real"] = {
            "callback_id": "cb_real",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "caller_name": "Real",
            "status": CallbackStatus.SCHEDULED,
            "requested_at": now,
            "callback_time": now,
            "attempts": 0,
        }
        queue.queue_callbacks["queue_1"] = ["cb_missing", "cb_real"]

        result = queue.list_queue_callbacks("queue_1")
        assert len(result) == 1
        assert result[0]["callback_id"] == "cb_real"


@pytest.mark.unit
class TestGetQueueStatistics:
    """Tests for get_queue_statistics method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_empty_queue_statistics(self, mock_get_logger: MagicMock) -> None:
        """Test statistics for empty/nonexistent queue"""
        queue = CallbackQueue()
        result = queue.get_queue_statistics("empty_queue")

        assert result["queue_id"] == "empty_queue"
        assert result["pending_callbacks"] == 0
        assert result["in_progress_callbacks"] == 0
        assert result["completed_callbacks"] == 0
        assert result["failed_callbacks"] == 0

    @patch("pbx.features.callback_queue.get_logger")
    def test_queue_statistics_with_callbacks(self, mock_get_logger: MagicMock) -> None:
        """Test statistics with various callback statuses"""
        queue = CallbackQueue()
        now = datetime.now(UTC)

        statuses = [
            ("cb_s1", CallbackStatus.SCHEDULED),
            ("cb_s2", CallbackStatus.SCHEDULED),
            ("cb_ip1", CallbackStatus.IN_PROGRESS),
            ("cb_c1", CallbackStatus.COMPLETED),
            ("cb_c2", CallbackStatus.COMPLETED),
            ("cb_c3", CallbackStatus.COMPLETED),
            ("cb_f1", CallbackStatus.FAILED),
        ]

        for cb_id, status in statuses:
            queue.callbacks[cb_id] = {
                "callback_id": cb_id,
                "queue_id": "queue_1",
                "caller_number": "5550000",
                "status": status,
                "callback_time": now,
                "requested_at": now,
                "attempts": 0,
                "max_attempts": 3,
            }

        queue.queue_callbacks["queue_1"] = [cb_id for cb_id, _ in statuses]

        result = queue.get_queue_statistics("queue_1")

        assert result["queue_id"] == "queue_1"
        assert result["pending_callbacks"] == 2
        assert result["in_progress_callbacks"] == 1
        assert result["completed_callbacks"] == 3
        assert result["failed_callbacks"] == 1

    @patch("pbx.features.callback_queue.get_logger")
    def test_queue_statistics_skips_orphaned_ids(self, mock_get_logger: MagicMock) -> None:
        """Test statistics skip callback IDs not in callbacks dict"""
        queue = CallbackQueue()
        now = datetime.now(UTC)

        queue.callbacks["cb_real"] = {
            "callback_id": "cb_real",
            "queue_id": "queue_1",
            "caller_number": "5551234",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
            "requested_at": now,
            "attempts": 0,
            "max_attempts": 3,
        }
        queue.queue_callbacks["queue_1"] = ["cb_real", "orphan_id"]

        result = queue.get_queue_statistics("queue_1")
        assert result["pending_callbacks"] == 1


@pytest.mark.unit
class TestCleanupOldCallbacks:
    """Tests for cleanup_old_callbacks method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_no_callbacks(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup with no callbacks"""
        queue = CallbackQueue()
        queue.cleanup_old_callbacks()
        assert queue.callbacks == {}

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_removes_old_completed(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup removes old completed callbacks"""
        queue = CallbackQueue()
        old_time = datetime.now(UTC) - timedelta(days=31)

        queue.callbacks["cb_old"] = {
            "callback_id": "cb_old",
            "queue_id": "queue_1",
            "status": CallbackStatus.COMPLETED,
            "completed_at": old_time,
        }

        queue.cleanup_old_callbacks(days=30)
        assert "cb_old" not in queue.callbacks

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_removes_old_failed(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup removes old failed callbacks"""
        queue = CallbackQueue()
        old_time = datetime.now(UTC) - timedelta(days=45)

        queue.callbacks["cb_fail"] = {
            "callback_id": "cb_fail",
            "queue_id": "queue_1",
            "status": CallbackStatus.FAILED,
            "failed_at": old_time,
        }

        queue.cleanup_old_callbacks(days=30)
        assert "cb_fail" not in queue.callbacks

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_removes_old_cancelled(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup removes old cancelled callbacks"""
        queue = CallbackQueue()
        old_time = datetime.now(UTC) - timedelta(days=60)

        queue.callbacks["cb_canc"] = {
            "callback_id": "cb_canc",
            "queue_id": "queue_1",
            "status": CallbackStatus.CANCELLED,
            "cancelled_at": old_time,
        }

        queue.cleanup_old_callbacks(days=30)
        assert "cb_canc" not in queue.callbacks

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_keeps_recent_callbacks(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup keeps recent completed callbacks"""
        queue = CallbackQueue()
        recent_time = datetime.now(UTC) - timedelta(days=5)

        queue.callbacks["cb_recent"] = {
            "callback_id": "cb_recent",
            "queue_id": "queue_1",
            "status": CallbackStatus.COMPLETED,
            "completed_at": recent_time,
        }

        queue.cleanup_old_callbacks(days=30)
        assert "cb_recent" in queue.callbacks

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_keeps_active_callbacks(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup keeps scheduled and in-progress callbacks"""
        queue = CallbackQueue()
        now = datetime.now(UTC)

        queue.callbacks["cb_scheduled"] = {
            "callback_id": "cb_scheduled",
            "queue_id": "queue_1",
            "status": CallbackStatus.SCHEDULED,
            "callback_time": now,
        }
        queue.callbacks["cb_in_progress"] = {
            "callback_id": "cb_in_progress",
            "queue_id": "queue_1",
            "status": CallbackStatus.IN_PROGRESS,
            "callback_time": now,
        }
        queue.callbacks["cb_pending"] = {
            "callback_id": "cb_pending",
            "queue_id": "queue_1",
            "status": CallbackStatus.PENDING,
            "callback_time": now,
        }

        queue.cleanup_old_callbacks(days=0)
        assert "cb_scheduled" in queue.callbacks
        assert "cb_in_progress" in queue.callbacks
        assert "cb_pending" in queue.callbacks

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_custom_days(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup with custom days parameter"""
        queue = CallbackQueue()

        queue.callbacks["cb_10d"] = {
            "callback_id": "cb_10d",
            "queue_id": "queue_1",
            "status": CallbackStatus.COMPLETED,
            "completed_at": datetime.now(UTC) - timedelta(days=10),
        }

        # 15 days cutoff should keep the 10-day-old callback
        queue.cleanup_old_callbacks(days=15)
        assert "cb_10d" in queue.callbacks

        # 5 days cutoff should remove the 10-day-old callback
        queue.cleanup_old_callbacks(days=5)
        assert "cb_10d" not in queue.callbacks

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_no_timestamp_keeps_callback(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup keeps callbacks with no completion timestamp"""
        queue = CallbackQueue()

        queue.callbacks["cb_no_ts"] = {
            "callback_id": "cb_no_ts",
            "queue_id": "queue_1",
            "status": CallbackStatus.COMPLETED,
        }

        queue.cleanup_old_callbacks(days=0)
        assert "cb_no_ts" in queue.callbacks

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_logs_when_removed(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup logs when callbacks are removed"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        queue = CallbackQueue()
        old_time = datetime.now(UTC) - timedelta(days=31)

        queue.callbacks["cb_log1"] = {
            "status": CallbackStatus.COMPLETED,
            "completed_at": old_time,
        }
        queue.callbacks["cb_log2"] = {
            "status": CallbackStatus.FAILED,
            "failed_at": old_time,
        }

        queue.cleanup_old_callbacks(days=30)
        mock_logger.info.assert_called_with("Cleaned up 2 old callbacks")

    @patch("pbx.features.callback_queue.get_logger")
    def test_cleanup_mixed_old_and_new(self, mock_get_logger: MagicMock) -> None:
        """Test cleanup with mix of old and new callbacks"""
        queue = CallbackQueue()
        old_time = datetime.now(UTC) - timedelta(days=60)
        recent_time = datetime.now(UTC) - timedelta(days=5)

        queue.callbacks["cb_old_done"] = {
            "status": CallbackStatus.COMPLETED,
            "completed_at": old_time,
        }
        queue.callbacks["cb_old_fail"] = {
            "status": CallbackStatus.FAILED,
            "failed_at": old_time,
        }
        queue.callbacks["cb_recent_done"] = {
            "status": CallbackStatus.COMPLETED,
            "completed_at": recent_time,
        }
        queue.callbacks["cb_active"] = {
            "status": CallbackStatus.SCHEDULED,
        }

        queue.cleanup_old_callbacks(days=30)

        assert "cb_old_done" not in queue.callbacks
        assert "cb_old_fail" not in queue.callbacks
        assert "cb_recent_done" in queue.callbacks
        assert "cb_active" in queue.callbacks


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics method"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_statistics_empty(self, mock_get_logger: MagicMock) -> None:
        """Test overall statistics with no callbacks"""
        queue = CallbackQueue()
        result = queue.get_statistics()

        assert result["enabled"] is False
        assert result["total_callbacks"] == 0
        assert result["active_queues"] == 0
        assert result["status_breakdown"] == {}

    @patch("pbx.features.callback_queue.get_logger")
    def test_statistics_with_data(self, mock_get_logger: MagicMock) -> None:
        """Test overall statistics with various callbacks"""
        config = {"features": {"callback_queue": {"enabled": True}}}
        queue = CallbackQueue(config=config)

        now = datetime.now(UTC)
        queue.callbacks["cb_1"] = {"status": CallbackStatus.SCHEDULED}
        queue.callbacks["cb_2"] = {"status": CallbackStatus.SCHEDULED}
        queue.callbacks["cb_3"] = {"status": CallbackStatus.IN_PROGRESS}
        queue.callbacks["cb_4"] = {"status": CallbackStatus.COMPLETED}
        queue.callbacks["cb_5"] = {"status": CallbackStatus.FAILED}
        queue.callbacks["cb_6"] = {"status": CallbackStatus.CANCELLED}

        queue.queue_callbacks["queue_1"] = ["cb_1", "cb_2", "cb_3"]
        queue.queue_callbacks["queue_2"] = ["cb_4", "cb_5"]

        result = queue.get_statistics()

        assert result["enabled"] is True
        assert result["total_callbacks"] == 6
        assert result["active_queues"] == 2
        assert result["status_breakdown"]["scheduled"] == 2
        assert result["status_breakdown"]["in_progress"] == 1
        assert result["status_breakdown"]["completed"] == 1
        assert result["status_breakdown"]["failed"] == 1
        assert result["status_breakdown"]["cancelled"] == 1

    @patch("pbx.features.callback_queue.get_logger")
    def test_statistics_reflects_enabled_state(self, mock_get_logger: MagicMock) -> None:
        """Test statistics reflects enabled state from config"""
        config = {"features": {"callback_queue": {"enabled": False}}}
        queue = CallbackQueue(config=config)

        result = queue.get_statistics()
        assert result["enabled"] is False

        config_enabled = {"features": {"callback_queue": {"enabled": True}}}
        queue_enabled = CallbackQueue(config=config_enabled)

        result_enabled = queue_enabled.get_statistics()
        assert result_enabled["enabled"] is True


@pytest.mark.unit
class TestEndToEndWorkflow:
    """Tests for complete callback lifecycle workflows"""

    @patch("pbx.features.callback_queue.get_logger")
    def test_full_successful_callback_lifecycle(self, mock_get_logger: MagicMock) -> None:
        """Test full lifecycle: request -> start -> complete"""
        config = {"features": {"callback_queue": {"enabled": True, "retry_attempts": 3}}}
        queue = CallbackQueue(config=config)

        # Request callback
        request_result = queue.request_callback("queue_1", "5551234", "John Doe")
        callback_id = request_result["callback_id"]
        assert request_result["status"] == "scheduled"

        # Manually set callback_time to past so it appears ready
        queue.callbacks[callback_id]["callback_time"] = datetime.now(UTC) - timedelta(minutes=1)

        # Get next callback
        next_cb = queue.get_next_callback("queue_1")
        assert next_cb is not None
        assert next_cb["callback_id"] == callback_id

        # Start callback
        start_result = queue.start_callback(callback_id, "agent_1")
        assert start_result["caller_number"] == "5551234"

        # Complete callback
        complete_result = queue.complete_callback(callback_id, True, notes="Resolved")
        assert complete_result is True

        # Verify final state
        info = queue.get_callback_info(callback_id)
        assert info["status"] == "completed"

        # Queue should be empty
        assert queue.list_queue_callbacks("queue_1") == []

    @patch("pbx.features.callback_queue.get_logger")
    def test_callback_retry_then_success(self, mock_get_logger: MagicMock) -> None:
        """Test callback fails, retries, then succeeds"""
        config = {
            "features": {
                "callback_queue": {
                    "enabled": True,
                    "retry_attempts": 3,
                    "retry_interval_minutes": 5,
                }
            }
        }
        queue = CallbackQueue(config=config)

        # Request
        result = queue.request_callback("queue_1", "5551234")
        callback_id = result["callback_id"]

        # First attempt fails
        queue.start_callback(callback_id, "agent_1")
        queue.complete_callback(callback_id, False)

        # Should be rescheduled
        assert queue.callbacks[callback_id]["status"] == CallbackStatus.SCHEDULED
        assert queue.callbacks[callback_id]["attempts"] == 1

        # Second attempt succeeds
        queue.start_callback(callback_id, "agent_2")
        queue.complete_callback(callback_id, True)

        assert queue.callbacks[callback_id]["status"] == CallbackStatus.COMPLETED

    @patch("pbx.features.callback_queue.get_logger")
    def test_callback_exhausts_retries(self, mock_get_logger: MagicMock) -> None:
        """Test callback fails and exhausts all retry attempts"""
        config = {
            "features": {
                "callback_queue": {
                    "enabled": True,
                    "retry_attempts": 2,
                    "retry_interval_minutes": 1,
                }
            }
        }
        queue = CallbackQueue(config=config)

        result = queue.request_callback("queue_1", "5551234")
        callback_id = result["callback_id"]

        # First attempt fails
        queue.start_callback(callback_id, "agent_1")
        queue.complete_callback(callback_id, False)
        assert queue.callbacks[callback_id]["status"] == CallbackStatus.SCHEDULED

        # Second attempt fails (max reached)
        queue.start_callback(callback_id, "agent_2")
        queue.complete_callback(callback_id, False)
        assert queue.callbacks[callback_id]["status"] == CallbackStatus.FAILED

    @patch("pbx.features.callback_queue.get_logger")
    def test_request_and_cancel(self, mock_get_logger: MagicMock) -> None:
        """Test requesting and then cancelling a callback"""
        config = {"features": {"callback_queue": {"enabled": True}}}
        queue = CallbackQueue(config=config)

        result = queue.request_callback("queue_1", "5551234", "Cancel User")
        callback_id = result["callback_id"]

        cancel_result = queue.cancel_callback(callback_id)
        assert cancel_result is True

        info = queue.get_callback_info(callback_id)
        assert info["status"] == "cancelled"
        assert queue.list_queue_callbacks("queue_1") == []
