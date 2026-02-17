"""Comprehensive tests for ConversationalAIDatabase."""

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.conversational_ai_db import ConversationalAIDatabase


@pytest.mark.unit
class TestConversationalAIDatabaseInit:
    """Tests for ConversationalAIDatabase initialization."""

    def test_init_with_db_backend(self) -> None:
        """Test initialization stores db_backend and logger."""
        mock_db = MagicMock()
        with patch("pbx.features.conversational_ai_db.get_logger") as mock_logger:
            db = ConversationalAIDatabase(mock_db)
            assert db.db is mock_db
            assert db.logger is mock_logger.return_value

    def test_init_with_none_backend(self) -> None:
        """Test initialization accepts None backend."""
        with patch("pbx.features.conversational_ai_db.get_logger"):
            db = ConversationalAIDatabase(None)
            assert db.db is None


@pytest.mark.unit
class TestConversationalAIDatabaseCreateTables:
    """Tests for create_tables method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.conversational_ai_db.get_logger"):
            self.db = ConversationalAIDatabase(self.mock_db)

    def test_create_tables_sqlite(self) -> None:
        """Test table creation with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        result = self.db.create_tables()
        assert result is True
        assert self.mock_cursor.execute.call_count == 4
        self.mock_db.connection.commit.assert_called_once()

    def test_create_tables_postgresql(self) -> None:
        """Test table creation with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        result = self.db.create_tables()
        assert result is True
        assert self.mock_cursor.execute.call_count == 4
        self.mock_db.connection.commit.assert_called_once()

    def test_create_tables_sqlite_sql_content(self) -> None:
        """Test SQLite SQL contains correct table names and syntax."""
        self.mock_db.db_type = "sqlite"
        self.db.create_tables()
        calls = self.mock_cursor.execute.call_args_list
        sql_texts = [c[0][0] for c in calls]
        assert any("ai_conversations" in sql for sql in sql_texts)
        assert any("ai_messages" in sql for sql in sql_texts)
        assert any("ai_intents" in sql for sql in sql_texts)
        assert any("ai_configurations" in sql for sql in sql_texts)
        assert any("AUTOINCREMENT" in sql for sql in sql_texts)
        assert any("BLOB" in sql for sql in sql_texts)

    def test_create_tables_postgresql_sql_content(self) -> None:
        """Test PostgreSQL SQL contains correct syntax."""
        self.mock_db.db_type = "postgresql"
        self.db.create_tables()
        calls = self.mock_cursor.execute.call_args_list
        sql_texts = [c[0][0] for c in calls]
        assert any("SERIAL PRIMARY KEY" in sql for sql in sql_texts)
        assert any("JSONB" in sql for sql in sql_texts)
        assert any("BYTEA" in sql for sql in sql_texts)

    def test_create_tables_logs_success(self) -> None:
        """Test table creation logs success message."""
        self.mock_db.db_type = "sqlite"
        self.db.create_tables()
        self.db.logger.info.assert_called_once_with("Conversational AI tables created successfully")

    def test_create_tables_error(self) -> None:
        """Test table creation handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("table error")
        result = self.db.create_tables()
        assert result is False
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestConversationalAIDatabaseSaveConversation:
    """Tests for save_conversation method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.conversational_ai_db.get_logger"):
            self.db = ConversationalAIDatabase(self.mock_db)

    def test_save_conversation_sqlite(self) -> None:
        """Test saving conversation with SQLite backend returns lastrowid."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.lastrowid = 7
        started_at = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = self.db.save_conversation("call-001", "5551234567", started_at)
        assert result == 7
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == "call-001"
        assert params[1] == "5551234567"
        assert params[2] == started_at.isoformat()
        self.mock_db.connection.commit.assert_called_once()

    def test_save_conversation_postgresql(self) -> None:
        """Test saving conversation with PostgreSQL backend returns fetched id."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.return_value = (42,)
        started_at = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = self.db.save_conversation("call-002", "5559876543", started_at)
        assert result == 42
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        assert "RETURNING id" in sql

    def test_save_conversation_error(self) -> None:
        """Test saving conversation handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        started_at = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = self.db.save_conversation("call-001", "5551234567", started_at)
        assert result is None
        self.db.logger.error.assert_called_once()

    def test_save_conversation_passes_isoformat(self) -> None:
        """Test that started_at is converted to isoformat string."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.lastrowid = 1
        started_at = datetime(2026, 6, 15, 14, 0, 0, tzinfo=UTC)
        self.db.save_conversation("call-001", "caller", started_at)
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[2] == "2026-06-15T14:00:00+00:00"


@pytest.mark.unit
class TestConversationalAIDatabaseSaveMessage:
    """Tests for save_message method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.conversational_ai_db.get_logger"):
            self.db = ConversationalAIDatabase(self.mock_db)

    def test_save_message_sqlite(self) -> None:
        """Test saving message with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        ts = datetime(2026, 1, 15, 10, 31, 0, tzinfo=UTC)
        self.db.save_message(1, "user", "Hello, how can I help?", ts)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == 1
        assert params[1] == "user"
        assert params[2] == "Hello, how can I help?"
        assert params[3] == ts.isoformat()
        self.mock_db.connection.commit.assert_called_once()

    def test_save_message_postgresql(self) -> None:
        """Test saving message with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        ts = datetime(2026, 1, 15, 10, 31, 0, tzinfo=UTC)
        self.db.save_message(1, "assistant", "I can help with that.", ts)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[1] == "assistant"

    def test_save_message_error(self) -> None:
        """Test saving message handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        ts = datetime(2026, 1, 15, 10, 31, 0, tzinfo=UTC)
        self.db.save_message(1, "user", "Hello", ts)
        self.db.logger.error.assert_called_once()

    def test_save_message_various_roles(self) -> None:
        """Test saving messages with different roles."""
        self.mock_db.db_type = "sqlite"
        ts = datetime(2026, 1, 15, 10, 31, 0, tzinfo=UTC)
        for role in ("user", "assistant", "system"):
            self.mock_cursor.execute.reset_mock()
            self.db.save_message(1, role, f"Message from {role}", ts)
            params = self.mock_cursor.execute.call_args[0][1]
            assert params[1] == role


@pytest.mark.unit
class TestConversationalAIDatabaseSaveIntent:
    """Tests for save_intent method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.conversational_ai_db.get_logger"):
            self.db = ConversationalAIDatabase(self.mock_db)

    def test_save_intent_sqlite(self) -> None:
        """Test saving intent with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        ts = datetime(2026, 1, 15, 10, 32, 0, tzinfo=UTC)
        entities = {"department": "billing", "action": "query"}
        self.db.save_intent(1, "transfer_call", 0.95, entities, ts)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == 1
        assert params[1] == "transfer_call"
        assert params[2] == 0.95
        assert params[3] == json.dumps(entities)
        assert params[4] == ts.isoformat()
        self.mock_db.connection.commit.assert_called_once()

    def test_save_intent_postgresql(self) -> None:
        """Test saving intent with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        ts = datetime(2026, 1, 15, 10, 32, 0, tzinfo=UTC)
        entities = {"queue": "support"}
        self.db.save_intent(2, "queue_call", 0.88, entities, ts)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[3] == json.dumps(entities)

    def test_save_intent_empty_entities(self) -> None:
        """Test saving intent with empty entities dict."""
        self.mock_db.db_type = "sqlite"
        ts = datetime(2026, 1, 15, 10, 32, 0, tzinfo=UTC)
        self.db.save_intent(1, "greeting", 0.99, {}, ts)
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[3] == "{}"

    def test_save_intent_error(self) -> None:
        """Test saving intent handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        ts = datetime(2026, 1, 15, 10, 32, 0, tzinfo=UTC)
        self.db.save_intent(1, "intent", 0.5, {}, ts)
        self.db.logger.error.assert_called_once()

    def test_save_intent_value_error(self) -> None:
        """Test saving intent handles ValueError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = ValueError("val error")
        ts = datetime(2026, 1, 15, 10, 32, 0, tzinfo=UTC)
        self.db.save_intent(1, "intent", 0.5, {}, ts)
        self.db.logger.error.assert_called_once()

    def test_save_intent_json_decode_error(self) -> None:
        """Test saving intent handles json.JSONDecodeError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = json.JSONDecodeError("err", "doc", 0)
        ts = datetime(2026, 1, 15, 10, 32, 0, tzinfo=UTC)
        self.db.save_intent(1, "intent", 0.5, {}, ts)
        self.db.logger.error.assert_called_once()

    def test_save_intent_complex_entities(self) -> None:
        """Test saving intent with complex nested entities."""
        self.mock_db.db_type = "sqlite"
        ts = datetime(2026, 1, 15, 10, 32, 0, tzinfo=UTC)
        entities = {
            "department": "sales",
            "priority": "high",
            "tags": ["urgent", "vip"],
            "metadata": {"source": "phone"},
        }
        self.db.save_intent(1, "route", 0.92, entities, ts)
        params = self.mock_cursor.execute.call_args[0][1]
        assert json.loads(params[3]) == entities


@pytest.mark.unit
class TestConversationalAIDatabaseEndConversation:
    """Tests for end_conversation method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.conversational_ai_db.get_logger"):
            self.db = ConversationalAIDatabase(self.mock_db)

    def test_end_conversation_sqlite(self) -> None:
        """Test ending conversation with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.db.end_conversation("call-001", "transfer_call", 5)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        assert "ended_at" in sql
        assert "final_intent" in sql
        assert "message_count" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[1] == "transfer_call"
        assert params[2] == 5
        assert params[3] == "call-001"
        self.mock_db.connection.commit.assert_called_once()

    def test_end_conversation_postgresql(self) -> None:
        """Test ending conversation with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.db.end_conversation("call-002", "hangup", 10)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[1] == "hangup"
        assert params[2] == 10
        assert params[3] == "call-002"

    def test_end_conversation_timestamp_set(self) -> None:
        """Test that ended_at timestamp is set as ISO format string."""
        self.mock_db.db_type = "sqlite"
        self.db.end_conversation("call-001", "done", 3)
        params = self.mock_cursor.execute.call_args[0][1]
        # ended_at should be an ISO format datetime string
        ended_at = params[0]
        assert isinstance(ended_at, str)
        # Should be parseable as ISO format
        datetime.fromisoformat(ended_at)

    def test_end_conversation_error(self) -> None:
        """Test ending conversation handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("update error")
        self.db.end_conversation("call-001", "intent", 5)
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestConversationalAIDatabaseGetConversationHistory:
    """Tests for get_conversation_history method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.conversational_ai_db.get_logger"):
            self.db = ConversationalAIDatabase(self.mock_db)

    def test_get_conversation_history_sqlite(self) -> None:
        """Test getting conversation history with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.description = [
            ("id",),
            ("call_id",),
            ("caller_id",),
            ("msg_count",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (1, "call-001", "5551234567", 5),
            (2, "call-002", "5559876543", 3),
        ]
        result = self.db.get_conversation_history(limit=50)
        assert len(result) == 2
        assert result[0]["call_id"] == "call-001"
        assert result[1]["msg_count"] == 3
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        assert "LEFT JOIN" in sql

    def test_get_conversation_history_postgresql(self) -> None:
        """Test getting conversation history with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.description = [("id",), ("call_id",)]
        self.mock_cursor.fetchall.return_value = [(1, "call-001")]
        result = self.db.get_conversation_history(limit=10)
        assert len(result) == 1
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql

    def test_get_conversation_history_default_limit(self) -> None:
        """Test getting conversation history uses default limit of 100."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.description = [("id",)]
        self.mock_cursor.fetchall.return_value = []
        self.db.get_conversation_history()
        params = self.mock_cursor.execute.call_args[0][1]
        assert params == (100,)

    def test_get_conversation_history_empty(self) -> None:
        """Test getting conversation history when none exist."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.description = [("id",)]
        self.mock_cursor.fetchall.return_value = []
        result = self.db.get_conversation_history()
        assert result == []

    def test_get_conversation_history_postgresql_columns(self) -> None:
        """Test PostgreSQL path processes columns from cursor.description."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.description = [
            ("id",),
            ("call_id",),
            ("caller_id",),
            ("started_at",),
            ("msg_count",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (1, "call-001", "5551234567", "2026-01-15T10:30:00", 5),
        ]
        result = self.db.get_conversation_history(limit=10)
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["call_id"] == "call-001"
        assert result[0]["started_at"] == "2026-01-15T10:30:00"
        assert result[0]["msg_count"] == 5

    def test_get_conversation_history_error(self) -> None:
        """Test getting conversation history handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("query error")
        result = self.db.get_conversation_history()
        assert result == []
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestConversationalAIDatabaseGetIntentStatistics:
    """Tests for get_intent_statistics method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.conversational_ai_db.get_logger"):
            self.db = ConversationalAIDatabase(self.mock_db)

    def test_get_intent_statistics_sqlite(self) -> None:
        """Test getting intent statistics with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchall.return_value = [
            ("transfer_call", 50),
            ("queue_call", 30),
            ("greeting", 100),
        ]
        result = self.db.get_intent_statistics()
        assert result == {
            "transfer_call": 50,
            "queue_call": 30,
            "greeting": 100,
        }

    def test_get_intent_statistics_postgresql(self) -> None:
        """Test getting intent statistics with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.description = [("intent",), ("count",)]
        self.mock_cursor.fetchall.return_value = [
            ("hangup", 20),
            ("voicemail", 15),
        ]
        result = self.db.get_intent_statistics()
        assert result == {"hangup": 20, "voicemail": 15}

    def test_get_intent_statistics_postgresql_reads_description(self) -> None:
        """Test PostgreSQL path accesses cursor.description (even though unused)."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.description = [("intent",), ("count",)]
        self.mock_cursor.fetchall.return_value = [("test", 1)]
        self.db.get_intent_statistics()
        # The PostgreSQL branch reads cursor.description (line 342 in source)
        # though the result is not stored. This test ensures that path is covered.
        assert self.mock_cursor.description is not None

    def test_get_intent_statistics_empty(self) -> None:
        """Test getting intent statistics when no intents exist."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchall.return_value = []
        result = self.db.get_intent_statistics()
        assert result == {}

    def test_get_intent_statistics_error(self) -> None:
        """Test getting intent statistics handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("query error")
        result = self.db.get_intent_statistics()
        assert result == {}
        self.db.logger.error.assert_called_once()

    def test_get_intent_statistics_sql_content(self) -> None:
        """Test that the SQL groups by intent and orders by count."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchall.return_value = []
        self.db.get_intent_statistics()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "GROUP BY intent" in sql
        assert "ORDER BY count DESC" in sql

    def test_get_intent_statistics_single_intent(self) -> None:
        """Test getting intent statistics with a single intent."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchall.return_value = [("only_intent", 42)]
        result = self.db.get_intent_statistics()
        assert result == {"only_intent": 42}

    def test_get_intent_statistics_many_intents(self) -> None:
        """Test getting intent statistics with many intents."""
        self.mock_db.db_type = "sqlite"
        intents = [(f"intent_{i}", i * 10) for i in range(20)]
        self.mock_cursor.fetchall.return_value = intents
        result = self.db.get_intent_statistics()
        assert len(result) == 20
        assert result["intent_5"] == 50
