"""Comprehensive tests for VoiceBiometricsDatabase."""

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock, call, patch

import pytest

from pbx.features.voice_biometrics_db import VoiceBiometricsDatabase


@pytest.mark.unit
class TestVoiceBiometricsDatabaseInit:
    """Tests for VoiceBiometricsDatabase initialization."""

    def test_init_with_db_backend(self) -> None:
        """Test initialization stores db_backend and logger."""
        mock_db = MagicMock()
        with patch("pbx.features.voice_biometrics_db.get_logger") as mock_logger:
            db = VoiceBiometricsDatabase(mock_db)
            assert db.db is mock_db
            assert db.logger is mock_logger.return_value

    def test_init_with_none_backend(self) -> None:
        """Test initialization accepts None backend."""
        with patch("pbx.features.voice_biometrics_db.get_logger"):
            db = VoiceBiometricsDatabase(None)
            assert db.db is None


@pytest.mark.unit
class TestVoiceBiometricsDatabaseCreateTables:
    """Tests for create_tables method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.voice_biometrics_db.get_logger"):
            self.db = VoiceBiometricsDatabase(self.mock_db)

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
        assert any("voice_profiles" in sql for sql in sql_texts)
        assert any("voice_enrollments" in sql for sql in sql_texts)
        assert any("voice_verifications" in sql for sql in sql_texts)
        assert any("voice_fraud_detections" in sql for sql in sql_texts)
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
        self.db.logger.info.assert_called_once_with("Voice biometrics tables created successfully")

    def test_create_tables_error(self) -> None:
        """Test table creation handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("table error")
        result = self.db.create_tables()
        assert result is False
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestVoiceBiometricsDatabaseSaveProfile:
    """Tests for save_profile method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.voice_biometrics_db.get_logger"):
            self.db = VoiceBiometricsDatabase(self.mock_db)

    def test_save_profile_sqlite(self) -> None:
        """Test saving profile with SQLite backend returns lastrowid."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.lastrowid = 42
        result = self.db.save_profile("user-001", "1001", "enrolling")
        assert result == 42
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "INSERT OR REPLACE" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params == ("user-001", "1001", "enrolling")
        self.mock_db.connection.commit.assert_called_once()

    def test_save_profile_postgresql(self) -> None:
        """Test saving profile with PostgreSQL backend returns fetched id."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.return_value = (99,)
        result = self.db.save_profile("user-002", "1002", "enrolled")
        assert result == 99
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql
        assert "RETURNING id" in sql

    def test_save_profile_error(self) -> None:
        """Test saving profile handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        result = self.db.save_profile("user-001", "1001", "enrolling")
        assert result is None
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestVoiceBiometricsDatabaseGetProfile:
    """Tests for get_profile method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.voice_biometrics_db.get_logger"):
            self.db = VoiceBiometricsDatabase(self.mock_db)

    def test_get_profile_found_sqlite(self) -> None:
        """Test getting profile that exists with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.return_value = (1, "user-001", "1001", "enrolled", 3, 3)
        self.mock_cursor.description = [
            ("id",),
            ("user_id",),
            ("extension",),
            ("status",),
            ("enrollment_samples",),
            ("required_samples",),
        ]
        result = self.db.get_profile("user-001")
        assert result is not None
        assert result["user_id"] == "user-001"
        assert result["status"] == "enrolled"
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql

    def test_get_profile_found_postgresql(self) -> None:
        """Test getting profile that exists with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.return_value = (1, "user-001", "1001", "enrolled")
        self.mock_cursor.description = [
            ("id",),
            ("user_id",),
            ("extension",),
            ("status",),
        ]
        result = self.db.get_profile("user-001")
        assert result is not None
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql

    def test_get_profile_not_found(self) -> None:
        """Test getting profile that does not exist."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.return_value = None
        result = self.db.get_profile("nonexistent")
        assert result is None

    def test_get_profile_error(self) -> None:
        """Test getting profile handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("query error")
        result = self.db.get_profile("user-001")
        assert result is None
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestVoiceBiometricsDatabaseUpdateEnrollmentProgress:
    """Tests for update_enrollment_progress method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.voice_biometrics_db.get_logger"):
            self.db = VoiceBiometricsDatabase(self.mock_db)

    def test_update_enrollment_progress_sqlite(self) -> None:
        """Test updating enrollment progress with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.db.update_enrollment_progress("user-001", 2)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        assert "enrollment_samples" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params == (2, "user-001")
        self.mock_db.connection.commit.assert_called_once()

    def test_update_enrollment_progress_postgresql(self) -> None:
        """Test updating enrollment progress with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.db.update_enrollment_progress("user-001", 3)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params == (3, "user-001")

    def test_update_enrollment_progress_error(self) -> None:
        """Test updating enrollment progress handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("update error")
        self.db.update_enrollment_progress("user-001", 1)
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestVoiceBiometricsDatabaseSaveVerification:
    """Tests for save_verification method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.voice_biometrics_db.get_logger"):
            self.db = VoiceBiometricsDatabase(self.mock_db)

    def test_save_verification_sqlite_verified(self) -> None:
        """Test saving successful verification with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        # Mock get_profile to return a profile
        self.mock_cursor.fetchone.return_value = (
            1,
            "user-001",
            "1001",
            "enrolled",
            3,
            3,
            None,
            5,
            1,
        )
        self.mock_cursor.description = [
            ("id",),
            ("user_id",),
            ("extension",),
            ("status",),
            ("enrollment_samples",),
            ("required_samples",),
            ("voiceprint_data",),
            ("successful_verifications",),
            ("failed_verifications",),
        ]
        self.db.save_verification("user-001", "call-001", True, 0.95)
        # First call is get_profile SELECT, second is INSERT verification,
        # third is UPDATE profile stats
        assert self.mock_cursor.execute.call_count == 3
        # Check the INSERT for verification
        insert_call = self.mock_cursor.execute.call_args_list[1]
        insert_sql = insert_call[0][0]
        assert "voice_verifications" in insert_sql
        insert_params = insert_call[0][1]
        assert insert_params[0] == 1  # profile_id
        assert insert_params[1] == "call-001"
        assert insert_params[2] == 1  # verified True -> 1 for SQLite
        assert insert_params[3] == 0.95
        # Check the UPDATE for stats
        update_call = self.mock_cursor.execute.call_args_list[2]
        update_sql = update_call[0][0]
        assert "successful_verifications" in update_sql

    def test_save_verification_sqlite_failed(self) -> None:
        """Test saving failed verification with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.return_value = (
            1,
            "user-001",
            "1001",
            "enrolled",
            3,
            3,
            None,
            5,
            1,
        )
        self.mock_cursor.description = [
            ("id",),
            ("user_id",),
            ("extension",),
            ("status",),
            ("enrollment_samples",),
            ("required_samples",),
            ("voiceprint_data",),
            ("successful_verifications",),
            ("failed_verifications",),
        ]
        self.db.save_verification("user-001", "call-001", False, 0.3)
        insert_call = self.mock_cursor.execute.call_args_list[1]
        insert_params = insert_call[0][1]
        assert insert_params[2] == 0  # verified False -> 0 for SQLite
        update_call = self.mock_cursor.execute.call_args_list[2]
        update_sql = update_call[0][0]
        assert "failed_verifications" in update_sql

    def test_save_verification_postgresql_verified(self) -> None:
        """Test saving successful verification with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.return_value = (
            1,
            "user-001",
            "1001",
            "enrolled",
            3,
            3,
            None,
            5,
            1,
        )
        self.mock_cursor.description = [
            ("id",),
            ("user_id",),
            ("extension",),
            ("status",),
            ("enrollment_samples",),
            ("required_samples",),
            ("voiceprint_data",),
            ("successful_verifications",),
            ("failed_verifications",),
        ]
        self.db.save_verification("user-001", "call-001", True, 0.92)
        assert self.mock_cursor.execute.call_count == 3
        insert_call = self.mock_cursor.execute.call_args_list[1]
        insert_params = insert_call[0][1]
        assert insert_params[2] is True  # PostgreSQL keeps bool
        update_call = self.mock_cursor.execute.call_args_list[2]
        update_sql = update_call[0][0]
        assert "successful_verifications" in update_sql
        assert "%s" in update_sql

    def test_save_verification_postgresql_failed(self) -> None:
        """Test saving failed verification with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.return_value = (
            1,
            "user-001",
            "1001",
            "enrolled",
            3,
            3,
            None,
            5,
            1,
        )
        self.mock_cursor.description = [
            ("id",),
            ("user_id",),
            ("extension",),
            ("status",),
            ("enrollment_samples",),
            ("required_samples",),
            ("voiceprint_data",),
            ("successful_verifications",),
            ("failed_verifications",),
        ]
        self.db.save_verification("user-001", "call-001", False, 0.2)
        update_call = self.mock_cursor.execute.call_args_list[2]
        update_sql = update_call[0][0]
        assert "failed_verifications" in update_sql
        assert "%s" in update_sql

    def test_save_verification_no_profile(self) -> None:
        """Test saving verification when profile does not exist returns early."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.return_value = None
        self.db.save_verification("nonexistent", "call-001", True, 0.9)
        # Only 1 call for get_profile SELECT, no INSERT or UPDATE
        assert self.mock_cursor.execute.call_count == 1

    def test_save_verification_error(self) -> None:
        """Test saving verification handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("query error")
        self.db.save_verification("user-001", "call-001", True, 0.9)
        self.db.logger.error.assert_called_once()

    def test_save_verification_key_error(self) -> None:
        """Test saving verification handles KeyError."""
        self.mock_db.db_type = "sqlite"
        # Return a row but with description that won't have "id" key
        self.mock_cursor.fetchone.return_value = (1,)
        self.mock_cursor.description = [("wrong_key",)]
        self.db.save_verification("user-001", "call-001", True, 0.9)
        self.db.logger.error.assert_called_once()

    def test_save_verification_type_error(self) -> None:
        """Test saving verification handles TypeError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.return_value = (1, "user-001", "1001", "enrolled")
        self.mock_cursor.description = [
            ("id",),
            ("user_id",),
            ("extension",),
            ("status",),
        ]
        # Make the second execute raise TypeError
        self.mock_cursor.execute.side_effect = [
            None,  # get_profile SELECT
            TypeError("type issue"),  # INSERT verification
        ]
        self.db.save_verification("user-001", "call-001", True, 0.9)
        self.db.logger.error.assert_called_once()

    def test_save_verification_value_error(self) -> None:
        """Test saving verification handles ValueError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.return_value = (1, "user-001", "1001", "enrolled")
        self.mock_cursor.description = [
            ("id",),
            ("user_id",),
            ("extension",),
            ("status",),
        ]
        self.mock_cursor.execute.side_effect = [
            None,
            ValueError("val issue"),
        ]
        self.db.save_verification("user-001", "call-001", True, 0.9)
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestVoiceBiometricsDatabaseSaveFraudDetection:
    """Tests for save_fraud_detection method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.voice_biometrics_db.get_logger"):
            self.db = VoiceBiometricsDatabase(self.mock_db)

    def test_save_fraud_detection_sqlite_fraud_true(self) -> None:
        """Test saving fraud detection with fraud=True using SQLite."""
        self.mock_db.db_type = "sqlite"
        indicators = ["voice_mismatch", "unusual_pattern"]
        self.db.save_fraud_detection("call-001", "5551234567", True, 0.85, indicators)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == "call-001"
        assert params[1] == "5551234567"
        assert params[2] == 1  # fraud_detected True -> 1
        assert params[3] == 0.85
        assert params[4] == json.dumps(indicators)
        self.mock_db.connection.commit.assert_called_once()

    def test_save_fraud_detection_sqlite_fraud_false(self) -> None:
        """Test saving fraud detection with fraud=False using SQLite."""
        self.mock_db.db_type = "sqlite"
        self.db.save_fraud_detection("call-002", "5559876543", False, 0.1, [])
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[2] == 0  # fraud_detected False -> 0

    def test_save_fraud_detection_postgresql(self) -> None:
        """Test saving fraud detection with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        indicators = ["spoofed_caller_id"]
        self.db.save_fraud_detection("call-001", "5551234567", True, 0.9, indicators)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[2] is True  # PostgreSQL keeps bool

    def test_save_fraud_detection_empty_indicators(self) -> None:
        """Test saving fraud detection with empty indicators list."""
        self.mock_db.db_type = "sqlite"
        self.db.save_fraud_detection("call-001", "5551234567", False, 0.0, [])
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[4] == "[]"

    def test_save_fraud_detection_error(self) -> None:
        """Test saving fraud detection handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        self.db.save_fraud_detection("call-001", "caller", True, 0.5, [])
        self.db.logger.error.assert_called_once()

    def test_save_fraud_detection_value_error(self) -> None:
        """Test saving fraud detection handles ValueError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = ValueError("val error")
        self.db.save_fraud_detection("call-001", "caller", True, 0.5, [])
        self.db.logger.error.assert_called_once()

    def test_save_fraud_detection_json_error(self) -> None:
        """Test saving fraud detection handles json.JSONDecodeError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = json.JSONDecodeError("err", "doc", 0)
        self.db.save_fraud_detection("call-001", "caller", True, 0.5, [])
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestVoiceBiometricsDatabaseGetStatistics:
    """Tests for get_statistics method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.voice_biometrics_db.get_logger"):
            self.db = VoiceBiometricsDatabase(self.mock_db)

    def test_get_statistics_sqlite(self) -> None:
        """Test getting statistics with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.side_effect = [
            (50,),  # total_profiles
            (30,),  # enrolled
            (200,),  # total_verifications
            (180,),  # successful
            (5,),  # fraud_detected
        ]
        result = self.db.get_statistics()
        assert result["total_profiles"] == 50
        assert result["enrolled_profiles"] == 30
        assert result["total_verifications"] == 200
        assert result["successful_verifications"] == 180
        assert result["failed_verifications"] == 20  # 200 - 180
        assert result["fraud_attempts_detected"] == 5

    def test_get_statistics_postgresql(self) -> None:
        """Test getting statistics with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.side_effect = [
            (100,),
            (75,),
            (500,),
            (450,),
            (10,),
        ]
        result = self.db.get_statistics()
        assert result["total_profiles"] == 100
        assert result["enrolled_profiles"] == 75
        assert result["failed_verifications"] == 50  # 500 - 450

    def test_get_statistics_sqlite_queries(self) -> None:
        """Test statistics uses correct SQLite queries."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.side_effect = [(0,), (0,), (0,), (0,), (0,)]
        self.db.get_statistics()
        calls = self.mock_cursor.execute.call_args_list
        sql_texts = [c[0][0] for c in calls]
        assert any("verified = 1" in sql for sql in sql_texts)
        assert any("fraud_detected = 1" in sql for sql in sql_texts)

    def test_get_statistics_postgresql_queries(self) -> None:
        """Test statistics uses correct PostgreSQL queries."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.side_effect = [(0,), (0,), (0,), (0,), (0,)]
        self.db.get_statistics()
        calls = self.mock_cursor.execute.call_args_list
        sql_texts = [c[0][0] for c in calls]
        assert any("verified = TRUE" in sql for sql in sql_texts)
        assert any("fraud_detected = TRUE" in sql for sql in sql_texts)

    def test_get_statistics_zero_verifications(self) -> None:
        """Test statistics with zero verifications produces zero failed."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.side_effect = [(0,), (0,), (0,), (0,), (0,)]
        result = self.db.get_statistics()
        assert result["total_verifications"] == 0
        assert result["successful_verifications"] == 0
        assert result["failed_verifications"] == 0

    def test_get_statistics_error(self) -> None:
        """Test statistics handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("query error")
        result = self.db.get_statistics()
        assert result == {}
        self.db.logger.error.assert_called_once()

    def test_get_statistics_all_enrolled_query(self) -> None:
        """Test that enrolled query is the same for both backends."""
        for db_type in ("sqlite", "postgresql"):
            self.mock_db.db_type = db_type
            self.mock_cursor.fetchone.side_effect = [(0,), (0,), (0,), (0,), (0,)]
            self.mock_cursor.execute.reset_mock()
            self.db.get_statistics()
            calls = self.mock_cursor.execute.call_args_list
            # Second query should be about enrolled status
            enrolled_sql = calls[1][0][0]
            assert "status = 'enrolled'" in enrolled_sql
