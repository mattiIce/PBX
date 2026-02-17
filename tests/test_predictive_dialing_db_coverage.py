"""
Comprehensive tests for Predictive Dialing Database layer.
Tests all public methods, SQL paths (PostgreSQL and SQLite), and error handling.
"""

import json
import sqlite3
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pbx.features.predictive_dialing_db import PredictiveDialingDatabase


@pytest.mark.unit
class TestPredictiveDialingDatabaseInit:
    """Tests for PredictiveDialingDatabase initialization."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_init_with_db_backend(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        mock_db = MagicMock()
        db = PredictiveDialingDatabase(mock_db)
        assert db.db is mock_db
        assert db.logger is not None

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_init_with_none_backend(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()
        db = PredictiveDialingDatabase(None)
        assert db.db is None


@pytest.mark.unit
class TestCreateTablesSQLite:
    """Tests for create_tables with SQLite backend."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_create_tables_sqlite_success(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        result = db.create_tables()

        assert result is True
        assert mock_cursor.execute.call_count == 4
        mock_db.connection.commit.assert_called_once()
        mock_logger.info.assert_called_with("Predictive dialing tables created successfully")

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_create_tables_sqlite_sql_contains_autoincrement(
        self, mock_get_logger: MagicMock
    ) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        # Verify SQLite-specific SQL was used (AUTOINCREMENT, not SERIAL)
        first_call_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "AUTOINCREMENT" in first_call_sql
        assert "SERIAL" not in first_call_sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_create_tables_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = sqlite3.Error("table creation failed")

        db = PredictiveDialingDatabase(mock_db)
        result = db.create_tables()

        assert result is False
        mock_logger.error.assert_called_once()
        assert "table creation failed" in mock_logger.error.call_args[0][0]


@pytest.mark.unit
class TestCreateTablesPostgreSQL:
    """Tests for create_tables with PostgreSQL backend."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_create_tables_postgresql_success(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        result = db.create_tables()

        assert result is True
        assert mock_cursor.execute.call_count == 4
        mock_db.connection.commit.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_create_tables_postgresql_sql_contains_serial(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        # Verify PostgreSQL-specific SQL was used (SERIAL, JSONB, REFERENCES)
        first_call_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "SERIAL" in first_call_sql
        assert "AUTOINCREMENT" not in first_call_sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_create_tables_postgresql_contacts_has_jsonb(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        # Second call is contacts table
        contacts_sql = mock_cursor.execute.call_args_list[1][0][0]
        assert "JSONB" in contacts_sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_create_tables_postgresql_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("pg error")

        db = PredictiveDialingDatabase(mock_db)
        result = db.create_tables()

        assert result is False
        mock_logger.error.assert_called_once()


@pytest.mark.unit
class TestSaveCampaign:
    """Tests for save_campaign."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_campaign_sqlite_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        campaign_data = {
            "campaign_id": "camp-1",
            "name": "Test Campaign",
            "dialing_mode": "predictive",
            "status": "active",
            "max_attempts": 5,
            "retry_interval": 1800,
        }
        result = db.save_campaign(campaign_data)

        assert result is True
        mock_cursor.execute.assert_called_once()
        call_sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT OR REPLACE" in call_sql
        params = mock_cursor.execute.call_args[0][1]
        assert params == ("camp-1", "Test Campaign", "predictive", "active", 5, 1800)
        mock_db.connection.commit.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_campaign_postgresql_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        campaign_data = {
            "campaign_id": "camp-1",
            "name": "Test Campaign",
            "dialing_mode": "predictive",
            "status": "active",
        }
        result = db.save_campaign(campaign_data)

        assert result is True
        call_sql = mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in call_sql
        assert "%s" in call_sql
        params = mock_cursor.execute.call_args[0][1]
        assert params[0] == "camp-1"
        # Defaults for max_attempts and retry_interval
        assert params[4] == 3
        assert params[5] == 3600

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_campaign_default_max_attempts(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        campaign_data = {
            "campaign_id": "camp-1",
            "name": "Test",
            "dialing_mode": "power",
            "status": "new",
        }
        result = db.save_campaign(campaign_data)

        assert result is True
        params = mock_cursor.execute.call_args[0][1]
        assert params[4] == 3  # default max_attempts
        assert params[5] == 3600  # default retry_interval

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_campaign_missing_key(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        # Missing required key 'campaign_id'
        campaign_data = {"name": "Test"}
        result = db.save_campaign(campaign_data)

        assert result is False
        mock_logger.error.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_campaign_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("insert failed")

        db = PredictiveDialingDatabase(mock_db)
        campaign_data = {
            "campaign_id": "camp-1",
            "name": "Test",
            "dialing_mode": "predictive",
            "status": "active",
        }
        result = db.save_campaign(campaign_data)

        assert result is False
        mock_logger.error.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_campaign_type_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = TypeError("bad type")

        db = PredictiveDialingDatabase(mock_db)
        result = db.save_campaign(
            {"campaign_id": "c1", "name": "t", "dialing_mode": "p", "status": "a"}
        )

        assert result is False


@pytest.mark.unit
class TestSaveContact:
    """Tests for save_contact."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_contact_sqlite_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        contact_data = {
            "contact_id": "contact-1",
            "phone_number": "5551234567",
            "data": {"name": "John Doe"},
        }
        result = db.save_contact("camp-1", contact_data)

        assert result is True
        mock_cursor.execute.assert_called_once()
        call_sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT OR REPLACE" in call_sql
        params = mock_cursor.execute.call_args[0][1]
        assert params[0] == "camp-1"
        assert params[1] == "contact-1"
        assert params[2] == "5551234567"
        assert json.loads(params[3]) == {"name": "John Doe"}
        mock_db.connection.commit.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_contact_postgresql_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        contact_data = {
            "contact_id": "contact-1",
            "phone_number": "5551234567",
            "data": {"email": "test@test.com"},
        }
        result = db.save_contact("camp-1", contact_data)

        assert result is True
        call_sql = mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in call_sql
        assert "%s" in call_sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_contact_no_data_field(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        contact_data = {
            "contact_id": "contact-1",
            "phone_number": "5551234567",
        }
        result = db.save_contact("camp-1", contact_data)

        assert result is True
        params = mock_cursor.execute.call_args[0][1]
        assert json.loads(params[3]) == {}

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_contact_missing_key(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        # Missing contact_id
        contact_data = {"phone_number": "5551234567"}
        result = db.save_contact("camp-1", contact_data)

        assert result is False
        mock_logger.error.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_contact_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("insert failed")

        db = PredictiveDialingDatabase(mock_db)
        contact_data = {"contact_id": "c1", "phone_number": "555"}
        result = db.save_contact("camp-1", contact_data)

        assert result is False

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_contact_missing_phone_number(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        # Missing phone_number
        contact_data = {"contact_id": "contact-1"}
        result = db.save_contact("camp-1", contact_data)

        assert result is False


@pytest.mark.unit
class TestSaveAttempt:
    """Tests for save_attempt."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_attempt_sqlite_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        attempt_data = {
            "call_id": "call-123",
            "attempt_number": 1,
            "timestamp": "2026-01-01T00:00:00",
            "result": "answered",
            "duration": 120,
            "agent_id": "agent-1",
            "status": "completed",
        }
        db.save_attempt("camp-1", "contact-1", attempt_data)

        assert mock_cursor.execute.call_count == 2
        # First call: INSERT into dialing_attempts
        insert_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "INSERT INTO dialing_attempts" in insert_sql
        assert "?" in insert_sql
        insert_params = mock_cursor.execute.call_args_list[0][0][1]
        assert insert_params[0] == "camp-1"
        assert insert_params[1] == "contact-1"
        assert insert_params[2] == "call-123"
        assert insert_params[3] == 1
        assert insert_params[5] == "answered"
        assert insert_params[6] == 120
        assert insert_params[7] == "agent-1"

        # Second call: UPDATE dialing_contacts
        update_sql = mock_cursor.execute.call_args_list[1][0][0]
        assert "UPDATE dialing_contacts" in update_sql
        update_params = mock_cursor.execute.call_args_list[1][0][1]
        assert update_params[1] == "completed"
        assert update_params[2] == "answered"
        assert update_params[3] == "camp-1"
        assert update_params[4] == "contact-1"

        mock_db.connection.commit.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_attempt_postgresql_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        attempt_data = {
            "call_id": "call-123",
            "attempt_number": 2,
            "timestamp": "2026-01-01T12:00:00",
            "result": "no_answer",
            "duration": 0,
            "agent_id": "agent-2",
            "status": "attempted",
        }
        db.save_attempt("camp-1", "contact-1", attempt_data)

        assert mock_cursor.execute.call_count == 2
        insert_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "%s" in insert_sql
        update_sql = mock_cursor.execute.call_args_list[1][0][0]
        assert "%s" in update_sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_attempt_default_values(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        # Minimal attempt_data -- missing optional fields
        attempt_data = {}
        db.save_attempt("camp-1", "contact-1", attempt_data)

        insert_params = mock_cursor.execute.call_args_list[0][0][1]
        assert insert_params[2] is None  # call_id
        assert insert_params[3] is None  # attempt_number
        # timestamp gets a default datetime value
        assert insert_params[4] is not None
        assert insert_params[5] is None  # result
        assert insert_params[6] is None  # duration
        assert insert_params[7] is None  # agent_id

        update_params = mock_cursor.execute.call_args_list[1][0][1]
        assert update_params[1] == "attempted"  # default status

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_attempt_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("insert failed")

        db = PredictiveDialingDatabase(mock_db)
        db.save_attempt("camp-1", "contact-1", {"call_id": "c1"})

        mock_logger.error.assert_called_once()
        assert "insert failed" in mock_logger.error.call_args[0][0]

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_attempt_cursor_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = sqlite3.Error("cursor error")

        db = PredictiveDialingDatabase(mock_db)
        db.save_attempt("camp-1", "contact-1", {})

        mock_logger.error.assert_called_once()


@pytest.mark.unit
class TestUpdateCampaignStats:
    """Tests for update_campaign_stats."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_update_stats_sqlite_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        stats = {
            "total_contacts": 100,
            "contacts_completed": 50,
            "successful_calls": 40,
            "failed_calls": 10,
        }
        db.update_campaign_stats("camp-1", stats)

        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "UPDATE dialing_campaigns" in sql
        assert "?" in sql
        params = mock_cursor.execute.call_args[0][1]
        assert params == (100, 50, 40, 10, "camp-1")
        mock_db.connection.commit.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_update_stats_postgresql_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        stats = {
            "total_contacts": 200,
            "contacts_completed": 150,
            "successful_calls": 100,
            "failed_calls": 50,
        }
        db.update_campaign_stats("camp-2", stats)

        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        params = mock_cursor.execute.call_args[0][1]
        assert params == (200, 150, 100, 50, "camp-2")

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_update_stats_default_values(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        # Empty stats dict -> uses defaults of 0
        db.update_campaign_stats("camp-1", {})

        params = mock_cursor.execute.call_args[0][1]
        assert params == (0, 0, 0, 0, "camp-1")

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_update_stats_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("update failed")

        db = PredictiveDialingDatabase(mock_db)
        db.update_campaign_stats("camp-1", {"total_contacts": 10})

        mock_logger.error.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_update_stats_partial_stats(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor

        db = PredictiveDialingDatabase(mock_db)
        stats = {"total_contacts": 50, "successful_calls": 20}
        db.update_campaign_stats("camp-1", stats)

        params = mock_cursor.execute.call_args[0][1]
        assert params == (50, 0, 20, 0, "camp-1")


@pytest.mark.unit
class TestGetCampaign:
    """Tests for get_campaign."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_campaign_sqlite_found(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            1,
            "camp-1",
            "Test Campaign",
            "predictive",
            "active",
            3,
            3600,
            "2026-01-01",
            None,
            None,
            100,
            50,
            40,
            10,
        )
        mock_cursor.description = [
            ("id",),
            ("campaign_id",),
            ("name",),
            ("dialing_mode",),
            ("status",),
            ("max_attempts",),
            ("retry_interval",),
            ("created_at",),
            ("started_at",),
            ("ended_at",),
            ("total_contacts",),
            ("contacts_completed",),
            ("successful_calls",),
            ("failed_calls",),
        ]

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_campaign("camp-1")

        assert result is not None
        assert result["campaign_id"] == "camp-1"
        assert result["name"] == "Test Campaign"
        assert result["status"] == "active"
        assert result["total_contacts"] == 100

        sql = mock_cursor.execute.call_args[0][0]
        assert "?" in sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_campaign_postgresql_found(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, "camp-1", "PG Campaign", "power", "running")
        mock_cursor.description = [
            ("id",),
            ("campaign_id",),
            ("name",),
            ("dialing_mode",),
            ("status",),
        ]

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_campaign("camp-1")

        assert result is not None
        assert result["name"] == "PG Campaign"
        sql = mock_cursor.execute.call_args[0][0]
        assert "%s" in sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_campaign_not_found(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_campaign("nonexistent")

        assert result is None

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_campaign_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = sqlite3.Error("query failed")

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_campaign("camp-1")

        assert result is None
        mock_logger.error.assert_called_once()


@pytest.mark.unit
class TestGetAllCampaigns:
    """Tests for get_all_campaigns."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_all_campaigns_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",), ("campaign_id",), ("name",)]
        mock_cursor.fetchall.return_value = [
            (1, "camp-1", "Campaign 1"),
            (2, "camp-2", "Campaign 2"),
        ]

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_all_campaigns()

        assert len(result) == 2
        assert result[0]["campaign_id"] == "camp-1"
        assert result[1]["campaign_id"] == "camp-2"

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_all_campaigns_empty(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",), ("campaign_id",), ("name",)]
        mock_cursor.fetchall.return_value = []

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_all_campaigns()

        assert result == []

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_all_campaigns_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = sqlite3.Error("query failed")

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_all_campaigns()

        assert result == []
        mock_logger.error.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_all_campaigns_sql_order(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = []

        db = PredictiveDialingDatabase(mock_db)
        db.get_all_campaigns()

        sql = mock_cursor.execute.call_args[0][0]
        assert "ORDER BY created_at DESC" in sql


@pytest.mark.unit
class TestGetCampaignContacts:
    """Tests for get_campaign_contacts."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_contacts_sqlite_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.description = [
            ("id",),
            ("campaign_id",),
            ("contact_id",),
            ("phone_number",),
            ("status",),
        ]
        mock_cursor.fetchall.return_value = [
            (1, "camp-1", "c1", "5551111", "pending"),
            (2, "camp-1", "c2", "5552222", "completed"),
        ]

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_campaign_contacts("camp-1")

        assert len(result) == 2
        assert result[0]["contact_id"] == "c1"
        assert result[1]["status"] == "completed"
        sql = mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        assert "ORDER BY created_at" in sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_contacts_postgresql_success(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",), ("contact_id",)]
        mock_cursor.fetchall.return_value = [(1, "c1")]

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_campaign_contacts("camp-1")

        assert len(result) == 1
        sql = mock_cursor.execute.call_args[0][0]
        assert "%s" in sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_contacts_empty(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = []

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_campaign_contacts("camp-1")

        assert result == []

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_contacts_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = sqlite3.Error("query failed")

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_campaign_contacts("camp-1")

        assert result == []
        mock_logger.error.assert_called_once()


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_campaign_specific_sqlite_found(
        self, mock_get_logger: MagicMock
    ) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            1,
            "camp-1",
            "Campaign",
            "predictive",
            "active",
        )
        mock_cursor.description = [
            ("id",),
            ("campaign_id",),
            ("name",),
            ("dialing_mode",),
            ("status",),
        ]

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics(campaign_id="camp-1")

        assert result is not None
        assert result["campaign_id"] == "camp-1"
        sql = mock_cursor.execute.call_args[0][0]
        assert "?" in sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_campaign_specific_postgresql_found(
        self, mock_get_logger: MagicMock
    ) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "postgresql"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, "camp-1", "PG Camp")
        mock_cursor.description = [("id",), ("campaign_id",), ("name",)]

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics(campaign_id="camp-1")

        assert result["campaign_id"] == "camp-1"
        sql = mock_cursor.execute.call_args[0][0]
        assert "%s" in sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_campaign_specific_not_found(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics(campaign_id="nonexistent")

        assert result == {}

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_global_with_data(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (5, 500, 300, 100)

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics()

        assert result["total_campaigns"] == 5
        assert result["total_contacts"] == 500
        assert result["successful_calls"] == 300
        assert result["failed_calls"] == 100

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_global_with_nulls(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        # SUM returns None when no rows exist
        mock_cursor.fetchone.return_value = (0, None, None, None)

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics()

        assert result["total_campaigns"] == 0
        assert result["total_contacts"] == 0
        assert result["successful_calls"] == 0
        assert result["failed_calls"] == 0

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_global_no_row(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics()

        assert result == {}

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_global_none_campaign_id(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (2, 100, 80, 20)

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics(campaign_id=None)

        assert result["total_campaigns"] == 2
        # Verify it executed the global aggregation query
        sql = mock_cursor.execute.call_args[0][0]
        assert "COUNT(*)" in sql
        assert "SUM" in sql

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = sqlite3.Error("stats failed")

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics()

        assert result == {}
        mock_logger.error.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_campaign_specific_error(self, mock_get_logger: MagicMock) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection.cursor.side_effect = sqlite3.Error("query error")

        db = PredictiveDialingDatabase(mock_db)
        result = db.get_statistics(campaign_id="camp-1")

        assert result == {}
        mock_logger.error.assert_called_once()

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_global_sql_content(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, 10, 5, 3)

        db = PredictiveDialingDatabase(mock_db)
        db.get_statistics()

        sql = mock_cursor.execute.call_args[0][0]
        assert "total_campaigns" in sql
        assert "total_contacts" in sql
        assert "successful_calls" in sql
        assert "failed_calls" in sql
        assert "FROM dialing_campaigns" in sql


@pytest.mark.unit
class TestGetStatisticsEmptyString:
    """Test get_statistics with empty string campaign_id (falsy but not None)."""

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_statistics_empty_string_campaign_id(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, 10, 5, 3)

        db = PredictiveDialingDatabase(mock_db)
        # Empty string is falsy, so should take global stats path
        result = db.get_statistics(campaign_id="")

        assert "total_campaigns" in result


@pytest.mark.unit
class TestDatabaseIntegrationWithRealSQLite:
    """Integration-style tests using a real in-memory SQLite database."""

    def _make_db_backend(self) -> MagicMock:
        """Create a mock db_backend wrapping a real SQLite connection."""
        import sqlite3 as sqlite3_mod

        conn = sqlite3_mod.connect(":memory:")
        mock_db = MagicMock()
        mock_db.db_type = "sqlite"
        mock_db.connection = conn
        return mock_db

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_create_tables_and_save_campaign_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)

        result = db.create_tables()
        assert result is True

        campaign_data = {
            "campaign_id": "camp-1",
            "name": "Real Test Campaign",
            "dialing_mode": "predictive",
            "status": "active",
            "max_attempts": 5,
            "retry_interval": 1800,
        }
        result = db.save_campaign(campaign_data)
        assert result is True

        retrieved = db.get_campaign("camp-1")
        assert retrieved is not None
        assert retrieved["name"] == "Real Test Campaign"
        assert retrieved["dialing_mode"] == "predictive"

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_and_get_contacts_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        db.save_campaign(
            {
                "campaign_id": "camp-1",
                "name": "Test",
                "dialing_mode": "power",
                "status": "active",
            }
        )

        db.save_contact(
            "camp-1",
            {
                "contact_id": "c1",
                "phone_number": "5551111",
                "data": {"name": "Alice"},
            },
        )
        db.save_contact(
            "camp-1",
            {
                "contact_id": "c2",
                "phone_number": "5552222",
                "data": {"name": "Bob"},
            },
        )

        contacts = db.get_campaign_contacts("camp-1")
        assert len(contacts) == 2

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_attempt_and_verify_contact_update_real_db(
        self, mock_get_logger: MagicMock
    ) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        db.save_campaign(
            {
                "campaign_id": "camp-1",
                "name": "Test",
                "dialing_mode": "power",
                "status": "active",
            }
        )
        db.save_contact(
            "camp-1",
            {
                "contact_id": "c1",
                "phone_number": "5551111",
            },
        )

        db.save_attempt(
            "camp-1",
            "c1",
            {
                "call_id": "call-1",
                "attempt_number": 1,
                "timestamp": "2026-01-15T10:00:00",
                "result": "answered",
                "duration": 60,
                "agent_id": "agent-1",
                "status": "completed",
            },
        )

        contacts = db.get_campaign_contacts("camp-1")
        assert len(contacts) == 1
        assert contacts[0]["attempts"] == 1
        assert contacts[0]["call_result"] == "answered"
        assert contacts[0]["status"] == "completed"

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_update_campaign_stats_and_get_stats_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        db.save_campaign(
            {
                "campaign_id": "camp-1",
                "name": "Test",
                "dialing_mode": "power",
                "status": "active",
            }
        )

        db.update_campaign_stats(
            "camp-1",
            {
                "total_contacts": 100,
                "contacts_completed": 75,
                "successful_calls": 60,
                "failed_calls": 15,
            },
        )

        stats = db.get_statistics(campaign_id="camp-1")
        assert stats["total_contacts"] == 100
        assert stats["contacts_completed"] == 75
        assert stats["successful_calls"] == 60
        assert stats["failed_calls"] == 15

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_all_campaigns_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        for i in range(3):
            db.save_campaign(
                {
                    "campaign_id": f"camp-{i}",
                    "name": f"Campaign {i}",
                    "dialing_mode": "predictive",
                    "status": "active",
                }
            )

        campaigns = db.get_all_campaigns()
        assert len(campaigns) == 3

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_global_statistics_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        db.save_campaign(
            {
                "campaign_id": "camp-1",
                "name": "Campaign 1",
                "dialing_mode": "predictive",
                "status": "active",
            }
        )
        db.save_campaign(
            {
                "campaign_id": "camp-2",
                "name": "Campaign 2",
                "dialing_mode": "power",
                "status": "active",
            }
        )

        db.update_campaign_stats(
            "camp-1",
            {
                "total_contacts": 50,
                "successful_calls": 30,
                "failed_calls": 10,
            },
        )
        db.update_campaign_stats(
            "camp-2",
            {
                "total_contacts": 100,
                "successful_calls": 60,
                "failed_calls": 20,
            },
        )

        stats = db.get_statistics()
        assert stats["total_campaigns"] == 2
        assert stats["total_contacts"] == 150
        assert stats["successful_calls"] == 90
        assert stats["failed_calls"] == 30

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_get_campaign_not_found_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        result = db.get_campaign("nonexistent")
        assert result is None

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_campaign_upsert_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        db.save_campaign(
            {
                "campaign_id": "camp-1",
                "name": "Original Name",
                "dialing_mode": "predictive",
                "status": "active",
            }
        )

        db.save_campaign(
            {
                "campaign_id": "camp-1",
                "name": "Updated Name",
                "dialing_mode": "power",
                "status": "paused",
            }
        )

        result = db.get_campaign("camp-1")
        assert result is not None
        assert result["name"] == "Updated Name"
        assert result["dialing_mode"] == "power"
        assert result["status"] == "paused"

        all_campaigns = db.get_all_campaigns()
        assert len(all_campaigns) == 1

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_save_contact_upsert_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        db.save_campaign(
            {
                "campaign_id": "camp-1",
                "name": "Test",
                "dialing_mode": "power",
                "status": "active",
            }
        )

        db.save_contact(
            "camp-1",
            {
                "contact_id": "c1",
                "phone_number": "5551111",
            },
        )

        db.save_contact(
            "camp-1",
            {
                "contact_id": "c1",
                "phone_number": "5559999",
            },
        )

        contacts = db.get_campaign_contacts("camp-1")
        assert len(contacts) == 1
        assert contacts[0]["phone_number"] == "5559999"

    @patch("pbx.features.predictive_dialing_db.get_logger")
    def test_multiple_attempts_increment_real_db(self, mock_get_logger: MagicMock) -> None:
        mock_get_logger.return_value = MagicMock()

        mock_db = self._make_db_backend()
        db = PredictiveDialingDatabase(mock_db)
        db.create_tables()

        db.save_campaign(
            {
                "campaign_id": "camp-1",
                "name": "Test",
                "dialing_mode": "power",
                "status": "active",
            }
        )
        db.save_contact(
            "camp-1",
            {
                "contact_id": "c1",
                "phone_number": "5551111",
            },
        )

        # First attempt
        db.save_attempt(
            "camp-1",
            "c1",
            {
                "call_id": "call-1",
                "attempt_number": 1,
                "timestamp": "2026-01-15T10:00:00",
                "result": "no_answer",
                "status": "attempted",
            },
        )

        # Second attempt
        db.save_attempt(
            "camp-1",
            "c1",
            {
                "call_id": "call-2",
                "attempt_number": 2,
                "timestamp": "2026-01-15T11:00:00",
                "result": "answered",
                "status": "completed",
            },
        )

        contacts = db.get_campaign_contacts("camp-1")
        assert contacts[0]["attempts"] == 2
        assert contacts[0]["call_result"] == "answered"
        assert contacts[0]["status"] == "completed"
