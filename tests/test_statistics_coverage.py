"""Comprehensive tests for Enhanced Statistics and Analytics module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pbx.features.statistics import StatisticsEngine


def _make_cdr_system(records_by_date=None, default_records=None):
    """Helper to create a mock CDR system."""
    mock_cdr = MagicMock()
    if records_by_date is not None:

        def get_records(date, limit=10000):
            return records_by_date.get(date, [])

        mock_cdr.get_records.side_effect = get_records
    elif default_records is not None:
        mock_cdr.get_records.return_value = default_records
    else:
        mock_cdr.get_records.return_value = []
    return mock_cdr


@pytest.mark.unit
class TestStatisticsEngineInit:
    """Tests for StatisticsEngine initialization."""

    @patch("pbx.features.statistics.get_logger")
    def test_init(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        assert engine.cdr_system is mock_cdr


@pytest.mark.unit
class TestStatisticsEngineOverviewStats:
    """Tests for overview statistics."""

    @patch("pbx.features.statistics.get_logger")
    def test_overview_stats_no_records(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_overview_stats(7)
        assert result["total_calls"] == 0
        assert result["answered_calls"] == 0
        assert result["missed_calls"] == 0
        assert result["answer_rate"] == 0
        assert result["avg_call_duration"] == 0

    @patch("pbx.features.statistics.get_logger")
    def test_overview_stats_with_records(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120},
            {"disposition": "answered", "duration": 60},
            {"disposition": "no_answer", "duration": 0},
            {"disposition": "busy", "duration": 0},
            {"disposition": "failed", "duration": 0},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_overview_stats(1)
        assert result["total_calls"] == 5
        assert result["answered_calls"] == 2
        assert result["missed_calls"] == 2
        assert result["answer_rate"] == 40.0
        assert result["avg_call_duration"] == 90.0


@pytest.mark.unit
class TestStatisticsEngineDailyTrends:
    """Tests for daily trends."""

    @patch("pbx.features.statistics.get_logger")
    def test_daily_trends_empty(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_daily_trends(3)
        assert len(result) == 3
        assert all(t["total_calls"] == 0 for t in result)

    @patch("pbx.features.statistics.get_logger")
    def test_daily_trends_with_records(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 60},
            {"disposition": "no_answer", "duration": 0},
            {"disposition": "failed", "duration": 0},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_daily_trends(2)
        assert len(result) == 2
        assert result[0]["answered"] == 1
        assert result[0]["missed"] == 1
        assert result[0]["failed"] == 1


@pytest.mark.unit
class TestStatisticsEngineHourlyDistribution:
    """Tests for hourly distribution."""

    @patch("pbx.features.statistics.get_logger")
    def test_hourly_distribution_empty(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_hourly_distribution(1)
        assert len(result) == 24
        assert all(h["calls"] == 0 for h in result)

    @patch("pbx.features.statistics.get_logger")
    def test_hourly_distribution_with_records(self, mock_get_logger) -> None:
        records = [
            {"start_time": "2024-01-01T10:00:00"},
            {"start_time": "2024-01-01T10:30:00"},
            {"start_time": "2024-01-01T14:00:00"},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_hourly_distribution(1)
        # Hour 10 should have 2 calls
        hour_10 = next(h for h in result if h["hour"] == 10)
        assert hour_10["calls"] == 2
        hour_14 = next(h for h in result if h["hour"] == 14)
        assert hour_14["calls"] == 1

    @patch("pbx.features.statistics.get_logger")
    def test_hourly_distribution_invalid_timestamp(self, mock_get_logger) -> None:
        records = [
            {"start_time": "not-a-date"},
            {"start_time": None},
            {},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_hourly_distribution(1)
        assert all(h["calls"] == 0 for h in result)


@pytest.mark.unit
class TestStatisticsEngineTopCallers:
    """Tests for top callers."""

    @patch("pbx.features.statistics.get_logger")
    def test_top_callers_empty(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_top_callers(1)
        assert result == []

    @patch("pbx.features.statistics.get_logger")
    def test_top_callers_with_records(self, mock_get_logger) -> None:
        records = [
            {"from_extension": "1001", "duration": 60},
            {"from_extension": "1001", "duration": 120},
            {"from_extension": "1002", "duration": 30},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_top_callers(1, limit=10)
        assert len(result) == 2
        assert result[0]["extension"] == "1001"
        assert result[0]["calls"] == 2
        assert result[0]["total_duration"] == 180.0
        assert result[0]["avg_duration"] == 90.0

    @patch("pbx.features.statistics.get_logger")
    def test_top_callers_limit(self, mock_get_logger) -> None:
        records = [{"from_extension": f"100{i}", "duration": 60} for i in range(20)]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_top_callers(1, limit=5)
        assert len(result) == 5

    @patch("pbx.features.statistics.get_logger")
    def test_top_callers_missing_extension(self, mock_get_logger) -> None:
        records = [{"duration": 60}]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_top_callers(1)
        assert len(result) == 1
        assert result[0]["extension"] == "Unknown"


@pytest.mark.unit
class TestStatisticsEngineCallDisposition:
    """Tests for call disposition breakdown."""

    @patch("pbx.features.statistics.get_logger")
    def test_call_disposition_empty(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_call_disposition(1)
        assert result == []

    @patch("pbx.features.statistics.get_logger")
    def test_call_disposition_with_records(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered"},
            {"disposition": "answered"},
            {"disposition": "no_answer"},
            {"disposition": "busy"},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_call_disposition(1)
        assert len(result) == 3  # answered, no_answer, busy
        total_pct = sum(d["percentage"] for d in result)
        assert abs(total_pct - 100.0) < 0.1

    @patch("pbx.features.statistics.get_logger")
    def test_call_disposition_missing_field(self, mock_get_logger) -> None:
        records = [{}]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_call_disposition(1)
        assert len(result) == 1
        assert result[0]["disposition"] == "unknown"


@pytest.mark.unit
class TestStatisticsEnginePeakHours:
    """Tests for peak hours."""

    @patch("pbx.features.statistics.get_logger")
    def test_peak_hours_empty(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_peak_hours(1)
        assert result == []

    @patch("pbx.features.statistics.get_logger")
    def test_peak_hours_with_records(self, mock_get_logger) -> None:
        records = [
            {"start_time": "2024-01-01T10:00:00"},
            {"start_time": "2024-01-01T10:30:00"},
            {"start_time": "2024-01-01T10:45:00"},
            {"start_time": "2024-01-01T14:00:00"},
            {"start_time": "2024-01-01T14:30:00"},
            {"start_time": "2024-01-01T09:00:00"},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_peak_hours(1)
        assert len(result) <= 3
        assert result[0]["hour"] == "10:00"
        assert result[0]["calls"] == 3

    @patch("pbx.features.statistics.get_logger")
    def test_peak_hours_invalid_timestamps(self, mock_get_logger) -> None:
        records = [{"start_time": "invalid"}, {}]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_peak_hours(1)
        assert result == []


@pytest.mark.unit
class TestStatisticsEngineAverageMetrics:
    """Tests for average metrics."""

    @patch("pbx.features.statistics.get_logger")
    def test_average_metrics_no_data(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_average_metrics(7)
        assert result["avg_calls_per_day"] == 0.0
        assert result["avg_answered_per_day"] == 0.0
        assert result["avg_duration_per_day"] == 0.0

    @patch("pbx.features.statistics.get_logger")
    def test_average_metrics_with_data(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120},
            {"disposition": "answered", "duration": 60},
            {"disposition": "no_answer", "duration": 0},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine._get_average_metrics(1)
        assert result["avg_calls_per_day"] == 3.0
        assert result["avg_answered_per_day"] == 2.0
        # Total duration = 180, / 1 day / 60 = 3.0 minutes
        assert result["avg_duration_per_day"] == 3.0


@pytest.mark.unit
class TestStatisticsEngineDashboard:
    """Tests for dashboard statistics."""

    @patch("pbx.features.statistics.get_logger")
    def test_get_dashboard_statistics(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_dashboard_statistics(days=3)
        assert "overview" in result
        assert "daily_trends" in result
        assert "hourly_distribution" in result
        assert "top_callers" in result
        assert "call_disposition" in result
        assert "peak_hours" in result
        assert "average_metrics" in result

    @patch("pbx.features.statistics.get_logger")
    def test_get_dashboard_statistics_default_days(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_dashboard_statistics()
        assert "overview" in result


@pytest.mark.unit
class TestStatisticsEngineCallQualityMetrics:
    """Tests for call quality metrics integration."""

    @patch("pbx.features.statistics.get_logger")
    def test_quality_metrics_no_pbx_core(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_call_quality_metrics()
        assert result["average_mos"] == 0.0
        assert "note" in result

    @patch("pbx.features.statistics.get_logger")
    def test_quality_metrics_no_qos_monitor(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        pbx_core = MagicMock(spec=[])  # No qos_monitor attribute
        result = engine.get_call_quality_metrics(pbx_core=pbx_core)
        assert result["average_mos"] == 0.0

    @patch("pbx.features.statistics.get_logger")
    def test_quality_metrics_with_qos_data(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        pbx_core = MagicMock()
        pbx_core.qos_monitor.get_statistics.return_value = {
            "total_calls": 100,
            "active_calls": 5,
            "calls_with_issues": 10,
        }
        pbx_core.qos_monitor.get_historical_metrics.return_value = [
            {
                "mos_score": 4.5,
                "jitter_avg_ms": 10.0,
                "packet_loss_percentage": 0.5,
                "latency_avg_ms": 30.0,
            },
            {
                "mos_score": 4.1,
                "jitter_avg_ms": 20.0,
                "packet_loss_percentage": 1.0,
                "latency_avg_ms": 50.0,
            },
            {
                "mos_score": 3.8,
                "jitter_avg_ms": 30.0,
                "packet_loss_percentage": 2.0,
                "latency_avg_ms": 80.0,
            },
            {
                "mos_score": 3.3,
                "jitter_avg_ms": 40.0,
                "packet_loss_percentage": 3.0,
                "latency_avg_ms": 120.0,
            },
            {
                "mos_score": 2.5,
                "jitter_avg_ms": 60.0,
                "packet_loss_percentage": 5.0,
                "latency_avg_ms": 200.0,
            },
        ]

        result = engine.get_call_quality_metrics(pbx_core=pbx_core)
        assert result["average_mos"] > 0
        assert result["average_jitter"] > 0
        assert result["average_packet_loss"] > 0
        assert result["average_latency"] > 0
        assert "quality_distribution" in result
        assert result["quality_distribution"]["excellent"] > 0
        assert result["total_calls_monitored"] == 100
        assert result["active_monitored_calls"] == 5

    @patch("pbx.features.statistics.get_logger")
    def test_quality_metrics_empty_historical(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        pbx_core = MagicMock()
        pbx_core.qos_monitor.get_statistics.return_value = {
            "total_calls": 0,
            "active_calls": 0,
            "calls_with_issues": 0,
        }
        pbx_core.qos_monitor.get_historical_metrics.return_value = []

        result = engine.get_call_quality_metrics(pbx_core=pbx_core)
        # Empty historical -> fallback
        assert result["average_mos"] == 0.0
        assert "note" in result


@pytest.mark.unit
class TestStatisticsEngineRealTimeMetrics:
    """Tests for real-time metrics."""

    @patch("pbx.features.statistics.get_logger")
    def test_real_time_metrics_with_data(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        pbx_core = MagicMock()
        pbx_core.calls = {"call1": MagicMock(), "call2": MagicMock()}
        pbx_core.extensions = {
            "1001": {"registered": True},
            "1002": {"registered": False},
            "1003": {"registered": True},
        }
        pbx_core.start_time = datetime.now(UTC) - timedelta(hours=2)

        result = engine.get_real_time_metrics(pbx_core)
        assert result["active_calls"] == 2
        assert result["registered_extensions"] == 2
        assert result["system_uptime"] > 0
        assert "timestamp" in result

    @patch("pbx.features.statistics.get_logger")
    def test_real_time_metrics_no_calls_attr(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        pbx_core = MagicMock(spec=[])  # No calls or extensions attributes
        result = engine.get_real_time_metrics(pbx_core)
        assert result["active_calls"] == 0
        assert result["registered_extensions"] == 0

    @patch("pbx.features.statistics.get_logger")
    def test_system_uptime_no_start_time(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        pbx_core = MagicMock(spec=[])
        result = engine._get_system_uptime(pbx_core)
        assert result == 0

    @patch("pbx.features.statistics.get_logger")
    def test_system_uptime_with_start_time(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        pbx_core = MagicMock()
        pbx_core.start_time = datetime.now(UTC) - timedelta(seconds=3600)
        result = engine._get_system_uptime(pbx_core)
        assert result >= 3599.0


@pytest.mark.unit
class TestStatisticsEngineAdvancedAnalytics:
    """Tests for advanced analytics."""

    @patch("pbx.features.statistics.get_logger")
    def test_advanced_analytics_no_records(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_advanced_analytics("2024-01-01", "2024-01-03")
        assert result["date_range"]["start"] == "2024-01-01"
        assert result["date_range"]["end"] == "2024-01-03"
        assert result["date_range"]["days"] == 3
        assert result["summary"]["total_calls"] == 0

    @patch("pbx.features.statistics.get_logger")
    def test_advanced_analytics_with_records(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120, "from_ext": "1001", "to_ext": "1002"},
            {"disposition": "no_answer", "duration": 0, "from_ext": "1001", "to_ext": "1003"},
            {"disposition": "failed", "duration": 0, "from_ext": "1002", "to_ext": "1001"},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_advanced_analytics("2024-01-01", "2024-01-01")
        assert result["summary"]["total_calls"] == 3
        assert result["summary"]["answered"] == 1
        assert result["summary"]["missed"] == 1
        assert result["summary"]["failed"] == 1

    @patch("pbx.features.statistics.get_logger")
    def test_advanced_analytics_with_extension_filter(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120, "from_ext": "1001", "to_ext": "1002"},
            {"disposition": "answered", "duration": 60, "from_ext": "1002", "to_ext": "1003"},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_advanced_analytics(
            "2024-01-01", "2024-01-01", filters={"extension": "1001"}
        )
        assert result["summary"]["total_calls"] == 1

    @patch("pbx.features.statistics.get_logger")
    def test_advanced_analytics_with_disposition_filter(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120},
            {"disposition": "no_answer", "duration": 0},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_advanced_analytics(
            "2024-01-01", "2024-01-01", filters={"disposition": "answered"}
        )
        assert result["summary"]["total_calls"] == 1
        assert result["summary"]["answered"] == 1

    @patch("pbx.features.statistics.get_logger")
    def test_advanced_analytics_with_min_duration_filter(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120},
            {"disposition": "answered", "duration": 30},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_advanced_analytics(
            "2024-01-01", "2024-01-01", filters={"min_duration": 60}
        )
        assert result["summary"]["total_calls"] == 1

    @patch("pbx.features.statistics.get_logger")
    def test_advanced_analytics_no_filters(self, mock_get_logger) -> None:
        records = [{"disposition": "answered", "duration": 60}]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_advanced_analytics("2024-01-01", "2024-01-01", filters=None)
        assert result["filters_applied"] == {}


@pytest.mark.unit
class TestStatisticsEngineCallCenterMetrics:
    """Tests for call center metrics."""

    @patch("pbx.features.statistics.get_logger")
    def test_call_center_metrics_empty(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_call_center_metrics(days=1)
        assert result["total_calls"] == 0
        assert result["answered"] == 0
        assert result["abandoned"] == 0
        assert result["queue"] == "All Queues"

    @patch("pbx.features.statistics.get_logger")
    def test_call_center_metrics_with_records(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120, "wait_time": 10, "queue": "sales"},
            {"disposition": "answered", "duration": 60, "wait_time": 25, "queue": "sales"},
            {"disposition": "no_answer", "duration": 0, "wait_time": 30, "queue": "sales"},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_call_center_metrics(days=1)
        assert result["total_calls"] == 3
        assert result["answered"] == 2
        assert result["abandoned"] == 1
        assert result["average_handle_time"] == 90.0
        assert result["average_speed_of_answer"] == 17.5
        # 1 of 2 answered within 20s threshold
        assert result["service_level_20s"] == 50.0

    @patch("pbx.features.statistics.get_logger")
    def test_call_center_metrics_with_queue_filter(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120, "wait_time": 10, "queue": "sales"},
            {"disposition": "answered", "duration": 60, "wait_time": 5, "queue": "support"},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_call_center_metrics(days=1, queue_name="sales")
        assert result["total_calls"] == 1
        assert result["queue"] == "sales"

    @patch("pbx.features.statistics.get_logger")
    def test_call_center_metrics_abandonment_rate(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 120, "wait_time": 10},
            {"disposition": "busy", "duration": 0, "wait_time": 0},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.get_call_center_metrics(days=1)
        assert result["abandonment_rate"] == 50.0


@pytest.mark.unit
class TestStatisticsEngineExportCSV:
    """Tests for CSV export."""

    @patch("pbx.features.statistics.get_logger")
    def test_export_csv_empty_records(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        result = engine.export_to_csv([], "test.csv")
        assert result is False

    @patch("pbx.features.statistics.get_logger")
    @patch("pbx.features.statistics.Path")
    def test_export_csv_success(self, mock_path_cls, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_path_cls.return_value.open.return_value = mock_file

        records = [
            {
                "timestamp": "2024-01-01",
                "from_ext": "1001",
                "to_ext": "1002",
                "caller_id": "Test",
                "called_number": "1002",
                "disposition": "answered",
                "duration": 60,
                "wait_time": 5,
                "queue": "sales",
            },
        ]
        result = engine.export_to_csv(records, "/tmp/test.csv")
        assert result is True

    @patch("pbx.features.statistics.get_logger")
    @patch("pbx.features.statistics.Path")
    def test_export_csv_io_error(self, mock_path_cls, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        mock_path_cls.return_value.open.side_effect = OSError("Write error")
        records = [{"from_ext": "1001"}]
        result = engine.export_to_csv(records, "/invalid/path.csv")
        assert result is False


@pytest.mark.unit
class TestStatisticsEngineGenerateReport:
    """Tests for report generation."""

    @patch("pbx.features.statistics.get_logger")
    def test_generate_daily_report(self, mock_get_logger) -> None:
        records = [
            {"disposition": "answered", "duration": 60},
        ]
        mock_cdr = _make_cdr_system(default_records=records)
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report("daily", {"date": "2024-01-01"})
        assert result["report_type"] == "Daily Report"
        assert result["date"] == "2024-01-01"
        assert result["total_calls"] == 1

    @patch("pbx.features.statistics.get_logger")
    def test_generate_daily_report_default_date(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report("daily", {})
        assert result["report_type"] == "Daily Report"
        # Date should be today
        assert result["date"] == datetime.now(UTC).strftime("%Y-%m-%d")

    @patch("pbx.features.statistics.get_logger")
    def test_generate_weekly_report(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report("weekly", {})
        assert "date_range" in result

    @patch("pbx.features.statistics.get_logger")
    def test_generate_monthly_report(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report("monthly", {})
        assert "date_range" in result

    @patch("pbx.features.statistics.get_logger")
    def test_generate_custom_report(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report(
            "custom", {"start_date": "2024-01-01", "end_date": "2024-01-15"}
        )
        assert result["date_range"]["start"] == "2024-01-01"
        assert result["date_range"]["end"] == "2024-01-15"

    @patch("pbx.features.statistics.get_logger")
    def test_generate_invalid_report(self, mock_get_logger) -> None:
        mock_cdr = MagicMock()
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report("unknown_type", {})
        assert result == {"error": "Invalid report type"}

    @patch("pbx.features.statistics.get_logger")
    def test_generate_weekly_report_with_filters(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report("weekly", {"filters": {"extension": "1001"}})
        assert "date_range" in result

    @patch("pbx.features.statistics.get_logger")
    def test_generate_monthly_report_with_filters(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report("monthly", {"filters": {"disposition": "answered"}})
        assert "date_range" in result

    @patch("pbx.features.statistics.get_logger")
    def test_generate_custom_report_with_filters(self, mock_get_logger) -> None:
        mock_cdr = _make_cdr_system(default_records=[])
        engine = StatisticsEngine(mock_cdr)
        result = engine.generate_report(
            "custom",
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-15",
                "filters": {"extension": "1001"},
            },
        )
        assert result["filters_applied"] == {"extension": "1001"}
