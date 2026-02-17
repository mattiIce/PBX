"""Comprehensive tests for CallQualityPredictionDatabase."""

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.call_quality_prediction_db import CallQualityPredictionDatabase


@pytest.mark.unit
class TestCallQualityPredictionDatabaseInit:
    """Tests for CallQualityPredictionDatabase initialization."""

    def test_init_with_db_backend(self) -> None:
        """Test initialization stores db_backend and logger."""
        mock_db = MagicMock()
        with patch("pbx.features.call_quality_prediction_db.get_logger") as mock_logger:
            db = CallQualityPredictionDatabase(mock_db)
            assert db.db is mock_db
            assert db.logger is mock_logger.return_value

    def test_init_with_none_backend(self) -> None:
        """Test initialization accepts None backend."""
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            db = CallQualityPredictionDatabase(None)
            assert db.db is None


@pytest.mark.unit
class TestCallQualityPredictionDatabaseCreateTables:
    """Tests for create_tables method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

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
        """Test SQLite SQL contains correct syntax."""
        self.mock_db.db_type = "sqlite"
        self.db.create_tables()
        calls = self.mock_cursor.execute.call_args_list
        sql_texts = [call[0][0] for call in calls]
        assert any("quality_metrics" in sql for sql in sql_texts)
        assert any("quality_predictions" in sql for sql in sql_texts)
        assert any("quality_alerts" in sql for sql in sql_texts)
        assert any("quality_trends" in sql for sql in sql_texts)
        assert any("AUTOINCREMENT" in sql for sql in sql_texts)

    def test_create_tables_postgresql_sql_content(self) -> None:
        """Test PostgreSQL SQL contains correct syntax."""
        self.mock_db.db_type = "postgresql"
        self.db.create_tables()
        calls = self.mock_cursor.execute.call_args_list
        sql_texts = [call[0][0] for call in calls]
        assert any("SERIAL PRIMARY KEY" in sql for sql in sql_texts)
        assert any("JSONB" in sql for sql in sql_texts)

    def test_create_tables_error(self) -> None:
        """Test table creation handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("table error")
        result = self.db.create_tables()
        assert result is False
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestCallQualityPredictionDatabaseSaveMetrics:
    """Tests for save_metrics method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

    def test_save_metrics_sqlite(self) -> None:
        """Test saving metrics with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        metrics = {
            "timestamp": "2026-01-01T00:00:00",
            "latency": 20,
            "jitter": 5,
            "packet_loss": 0.01,
            "bandwidth": 64000,
            "mos_score": 4.2,
        }
        self.db.save_metrics("call-001", metrics)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == "call-001"
        assert params[1] == "2026-01-01T00:00:00"
        assert params[2] == 20
        self.mock_db.connection.commit.assert_called_once()

    def test_save_metrics_postgresql(self) -> None:
        """Test saving metrics with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        metrics = {
            "timestamp": "2026-01-01T00:00:00",
            "latency": 20,
            "jitter": 5,
            "packet_loss": 0.01,
            "bandwidth": 64000,
            "mos_score": 4.2,
        }
        self.db.save_metrics("call-001", metrics)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql

    def test_save_metrics_default_timestamp(self) -> None:
        """Test saving metrics uses default timestamp when not provided."""
        self.mock_db.db_type = "sqlite"
        metrics = {"latency": 20}
        self.db.save_metrics("call-001", metrics)
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == "call-001"
        # timestamp should be auto-generated ISO string
        assert params[1] is not None

    def test_save_metrics_missing_optional_fields(self) -> None:
        """Test saving metrics with missing optional fields returns None for missing keys."""
        self.mock_db.db_type = "sqlite"
        metrics = {}
        self.db.save_metrics("call-001", metrics)
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[2] is None  # latency
        assert params[3] is None  # jitter
        assert params[4] is None  # packet_loss
        assert params[5] is None  # bandwidth
        assert params[6] is None  # mos_score

    def test_save_metrics_sqlite_error(self) -> None:
        """Test saving metrics handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        self.db.save_metrics("call-001", {})
        self.db.logger.error.assert_called_once()

    def test_save_metrics_key_error(self) -> None:
        """Test saving metrics handles KeyError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = KeyError("missing key")
        self.db.save_metrics("call-001", {})
        self.db.logger.error.assert_called_once()

    def test_save_metrics_type_error(self) -> None:
        """Test saving metrics handles TypeError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = TypeError("type issue")
        self.db.save_metrics("call-001", {})
        self.db.logger.error.assert_called_once()

    def test_save_metrics_value_error(self) -> None:
        """Test saving metrics handles ValueError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = ValueError("value issue")
        self.db.save_metrics("call-001", {})
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestCallQualityPredictionDatabaseSavePrediction:
    """Tests for save_prediction method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

    def test_save_prediction_sqlite(self) -> None:
        """Test saving prediction with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        prediction = {
            "current_mos": 4.0,
            "predicted_mos": 3.5,
            "predicted_quality_level": "good",
            "current_packet_loss": 0.01,
            "predicted_packet_loss": 0.05,
            "alert": True,
            "alert_reasons": ["high_jitter"],
            "recommendations": ["reduce_bandwidth"],
            "timestamp": "2026-01-01T00:00:00",
        }
        self.db.save_prediction("call-001", prediction)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == "call-001"
        assert params[1] == 4.0
        assert params[6] == 1  # alert True -> 1 for SQLite
        assert params[7] == json.dumps(["high_jitter"])
        self.mock_db.connection.commit.assert_called_once()

    def test_save_prediction_sqlite_alert_false(self) -> None:
        """Test saving prediction with alert=False converts to 0 for SQLite."""
        self.mock_db.db_type = "sqlite"
        prediction = {"alert": False}
        self.db.save_prediction("call-001", prediction)
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[6] == 0

    def test_save_prediction_sqlite_defaults(self) -> None:
        """Test saving prediction uses defaults for missing keys."""
        self.mock_db.db_type = "sqlite"
        prediction = {}
        self.db.save_prediction("call-001", prediction)
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[6] == 0  # default alert False -> 0
        assert params[7] == json.dumps([])  # default alert_reasons
        assert params[8] == json.dumps([])  # default recommendations

    def test_save_prediction_postgresql(self) -> None:
        """Test saving prediction with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        prediction = {
            "current_mos": 4.0,
            "predicted_mos": 3.5,
            "predicted_quality_level": "good",
            "current_packet_loss": 0.01,
            "predicted_packet_loss": 0.05,
            "alert": True,
            "alert_reasons": ["high_jitter"],
            "recommendations": ["reduce_bandwidth"],
            "timestamp": datetime.now(UTC),
        }
        self.db.save_prediction("call-001", prediction)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[6] is True  # PostgreSQL keeps bool

    def test_save_prediction_postgresql_defaults(self) -> None:
        """Test saving prediction with PostgreSQL uses defaults for missing keys."""
        self.mock_db.db_type = "postgresql"
        prediction = {}
        self.db.save_prediction("call-001", prediction)
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[6] is False  # default alert
        assert params[7] == json.dumps([])
        assert params[8] == json.dumps([])

    def test_save_prediction_sqlite_error(self) -> None:
        """Test saving prediction handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        self.db.save_prediction("call-001", {})
        self.db.logger.error.assert_called_once()

    def test_save_prediction_json_error(self) -> None:
        """Test saving prediction handles json.JSONDecodeError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = json.JSONDecodeError("err", "doc", 0)
        self.db.save_prediction("call-001", {})
        self.db.logger.error.assert_called_once()

    def test_save_prediction_key_error(self) -> None:
        """Test saving prediction handles KeyError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = KeyError("missing")
        self.db.save_prediction("call-001", {})
        self.db.logger.error.assert_called_once()

    def test_save_prediction_type_error(self) -> None:
        """Test saving prediction handles TypeError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = TypeError("type issue")
        self.db.save_prediction("call-001", {})
        self.db.logger.error.assert_called_once()

    def test_save_prediction_value_error(self) -> None:
        """Test saving prediction handles ValueError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = ValueError("val issue")
        self.db.save_prediction("call-001", {})
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestCallQualityPredictionDatabaseSaveAlert:
    """Tests for save_alert method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

    def test_save_alert_sqlite(self) -> None:
        """Test saving alert with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.db.save_alert(
            call_id="call-001",
            alert_type="high_jitter",
            severity="warning",
            message="Jitter exceeded threshold",
            metric_value=50.0,
            threshold_value=30.0,
        )
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == "call-001"
        assert params[1] == "high_jitter"
        assert params[2] == "warning"
        assert params[3] == "Jitter exceeded threshold"
        assert params[4] == 50.0
        assert params[5] == 30.0
        self.mock_db.connection.commit.assert_called_once()

    def test_save_alert_postgresql(self) -> None:
        """Test saving alert with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.db.save_alert(
            call_id="call-001",
            alert_type="packet_loss",
            severity="critical",
            message="Packet loss high",
            metric_value=10.0,
            threshold_value=5.0,
        )
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql

    def test_save_alert_error(self) -> None:
        """Test saving alert handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        self.db.save_alert("call-001", "type", "sev", "msg", 1.0, 2.0)
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestCallQualityPredictionDatabaseGetRecentPredictions:
    """Tests for get_recent_predictions method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

    def test_get_recent_predictions_sqlite(self) -> None:
        """Test getting recent predictions with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.description = [("id",), ("call_id",), ("current_mos",)]
        self.mock_cursor.fetchall.return_value = [
            (1, "call-001", 4.0),
            (2, "call-002", 3.5),
        ]
        result = self.db.get_recent_predictions(limit=50)
        assert len(result) == 2
        assert result[0]["call_id"] == "call-001"
        assert result[1]["current_mos"] == 3.5
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "?" in sql

    def test_get_recent_predictions_postgresql(self) -> None:
        """Test getting recent predictions with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.description = [("id",), ("call_id",)]
        self.mock_cursor.fetchall.return_value = [(1, "call-001")]
        result = self.db.get_recent_predictions(limit=10)
        assert len(result) == 1
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "%s" in sql

    def test_get_recent_predictions_default_limit(self) -> None:
        """Test getting recent predictions uses default limit of 100."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.description = [("id",)]
        self.mock_cursor.fetchall.return_value = []
        self.db.get_recent_predictions()
        params = self.mock_cursor.execute.call_args[0][1]
        assert params == (100,)

    def test_get_recent_predictions_empty(self) -> None:
        """Test getting recent predictions when none exist."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.description = [("id",)]
        self.mock_cursor.fetchall.return_value = []
        result = self.db.get_recent_predictions()
        assert result == []

    def test_get_recent_predictions_error(self) -> None:
        """Test getting recent predictions handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("query error")
        result = self.db.get_recent_predictions()
        assert result == []
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestCallQualityPredictionDatabaseGetActiveAlerts:
    """Tests for get_active_alerts method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

    def test_get_active_alerts_sqlite(self) -> None:
        """Test getting active alerts with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.description = [("id",), ("call_id",), ("alert_type",)]
        self.mock_cursor.fetchall.return_value = [
            (1, "call-001", "high_jitter"),
        ]
        result = self.db.get_active_alerts()
        assert len(result) == 1
        assert result[0]["alert_type"] == "high_jitter"
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "acknowledged = 0" in sql

    def test_get_active_alerts_postgresql(self) -> None:
        """Test getting active alerts with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.description = [("id",), ("call_id",)]
        self.mock_cursor.fetchall.return_value = []
        result = self.db.get_active_alerts()
        assert result == []
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "acknowledged = FALSE" in sql

    def test_get_active_alerts_error(self) -> None:
        """Test getting active alerts handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("query error")
        result = self.db.get_active_alerts()
        assert result == []
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestCallQualityPredictionDatabaseAcknowledgeAlert:
    """Tests for acknowledge_alert method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

    def test_acknowledge_alert_sqlite(self) -> None:
        """Test acknowledging alert with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.db.acknowledge_alert(42)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "acknowledged = 1" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params == (42,)
        self.mock_db.connection.commit.assert_called_once()

    def test_acknowledge_alert_postgresql(self) -> None:
        """Test acknowledging alert with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.db.acknowledge_alert(10)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "acknowledged = TRUE" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params == (10,)

    def test_acknowledge_alert_error(self) -> None:
        """Test acknowledging alert handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("update error")
        self.db.acknowledge_alert(1)
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestCallQualityPredictionDatabaseUpdateDailyTrends:
    """Tests for update_daily_trends method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

    def test_update_daily_trends_sqlite(self) -> None:
        """Test updating daily trends with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        metrics = {
            "avg_mos": 4.0,
            "avg_latency": 20,
            "avg_jitter": 5,
            "avg_packet_loss": 0.01,
            "call_count": 10,
            "alert_count": 2,
        }
        self.db.update_daily_trends("sip:1001@pbx.local", metrics)
        self.mock_cursor.execute.assert_called_once()
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "INSERT OR REPLACE" in sql
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[0] == "sip:1001@pbx.local"
        assert params[2] == 4.0
        assert params[6] == 10
        self.mock_db.connection.commit.assert_called_once()

    def test_update_daily_trends_postgresql(self) -> None:
        """Test updating daily trends with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        metrics = {
            "avg_mos": 3.8,
            "avg_latency": 25,
            "avg_jitter": 8,
            "avg_packet_loss": 0.02,
        }
        self.db.update_daily_trends("sip:1002@pbx.local", metrics)
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql

    def test_update_daily_trends_defaults(self) -> None:
        """Test updating daily trends uses defaults for missing keys."""
        self.mock_db.db_type = "sqlite"
        self.db.update_daily_trends("endpoint", {})
        params = self.mock_cursor.execute.call_args[0][1]
        assert params[6] == 1  # default call_count
        assert params[7] == 0  # default alert_count

    def test_update_daily_trends_error(self) -> None:
        """Test updating daily trends handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("insert error")
        self.db.update_daily_trends("endpoint", {})
        self.db.logger.error.assert_called_once()

    def test_update_daily_trends_key_error(self) -> None:
        """Test updating daily trends handles KeyError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = KeyError("key")
        self.db.update_daily_trends("endpoint", {})
        self.db.logger.error.assert_called_once()

    def test_update_daily_trends_type_error(self) -> None:
        """Test updating daily trends handles TypeError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = TypeError("type")
        self.db.update_daily_trends("endpoint", {})
        self.db.logger.error.assert_called_once()

    def test_update_daily_trends_value_error(self) -> None:
        """Test updating daily trends handles ValueError."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = ValueError("value")
        self.db.update_daily_trends("endpoint", {})
        self.db.logger.error.assert_called_once()


@pytest.mark.unit
class TestCallQualityPredictionDatabaseGetStatistics:
    """Tests for get_statistics method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.connection.cursor.return_value = self.mock_cursor
        with patch("pbx.features.call_quality_prediction_db.get_logger"):
            self.db = CallQualityPredictionDatabase(self.mock_db)

    def test_get_statistics_sqlite(self) -> None:
        """Test getting statistics with SQLite backend."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.side_effect = [
            (100,),  # total_predictions
            (15,),  # alerts_generated
            (5,),  # active_alerts
            (4.1,),  # avg_mos_24h
        ]
        result = self.db.get_statistics()
        assert result["total_predictions"] == 100
        assert result["alerts_generated"] == 15
        assert result["active_alerts"] == 5
        assert result["avg_mos_24h"] == 4.1

    def test_get_statistics_postgresql(self) -> None:
        """Test getting statistics with PostgreSQL backend."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.side_effect = [
            (200,),
            (30,),
            (10,),
            (3.9,),
        ]
        result = self.db.get_statistics()
        assert result["total_predictions"] == 200
        assert result["alerts_generated"] == 30
        assert result["active_alerts"] == 10
        assert result["avg_mos_24h"] == 3.9

    def test_get_statistics_sqlite_queries(self) -> None:
        """Test statistics uses correct SQLite queries."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.side_effect = [(0,), (0,), (0,), (None,)]
        self.db.get_statistics()
        calls = self.mock_cursor.execute.call_args_list
        sql_texts = [call[0][0] for call in calls]
        assert any("alert = 1" in sql for sql in sql_texts)
        assert any("acknowledged = 0" in sql for sql in sql_texts)
        assert any("datetime('now', '-24 hours')" in sql for sql in sql_texts)

    def test_get_statistics_postgresql_queries(self) -> None:
        """Test statistics uses correct PostgreSQL queries."""
        self.mock_db.db_type = "postgresql"
        self.mock_cursor.fetchone.side_effect = [(0,), (0,), (0,), (None,)]
        self.db.get_statistics()
        calls = self.mock_cursor.execute.call_args_list
        sql_texts = [call[0][0] for call in calls]
        assert any("alert = TRUE" in sql for sql in sql_texts)
        assert any("acknowledged = FALSE" in sql for sql in sql_texts)
        assert any("INTERVAL" in sql for sql in sql_texts)

    def test_get_statistics_null_avg_mos(self) -> None:
        """Test statistics handles NULL avg_mos gracefully."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.side_effect = [
            (50,),
            (5,),
            (2,),
            (None,),  # NULL mos
        ]
        result = self.db.get_statistics()
        assert result["avg_mos_24h"] == 0.0

    def test_get_statistics_none_row(self) -> None:
        """Test statistics handles None row for avg_mos."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.side_effect = [
            (50,),
            (5,),
            (2,),
            None,  # None row
        ]
        # This would raise TypeError since None[0] fails, but code checks row and row[0]
        # Actually the code does: row[0] if row and row[0] else 0.0
        # If row is None, `row and row[0]` is falsy, so returns 0.0
        # But fetchone returns None, so row is None, and row[0] would fail
        # but the `and` short-circuits, so it returns 0.0
        result = self.db.get_statistics()
        assert result["avg_mos_24h"] == 0.0

    def test_get_statistics_error(self) -> None:
        """Test statistics handles sqlite3.Error."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.execute.side_effect = sqlite3.Error("query error")
        result = self.db.get_statistics()
        assert result == {}
        self.db.logger.error.assert_called_once()

    def test_get_statistics_zero_avg_mos(self) -> None:
        """Test statistics handles zero avg_mos (falsy but valid)."""
        self.mock_db.db_type = "sqlite"
        self.mock_cursor.fetchone.side_effect = [
            (0,),
            (0,),
            (0,),
            (0,),  # 0 is falsy, so avg_mos_24h will be 0.0
        ]
        result = self.db.get_statistics()
        # 0 is falsy, so the code returns 0.0
        assert result["avg_mos_24h"] == 0.0
