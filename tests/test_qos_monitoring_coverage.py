"""Comprehensive tests for QoS (Quality of Service) Monitoring module."""

import threading
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.qos_monitoring import QoSMetrics, QoSMonitor


@pytest.mark.unit
class TestQoSMetricsInit:
    """Tests for QoSMetrics initialization."""

    def test_init_defaults(self) -> None:
        metrics = QoSMetrics("call-001")
        assert metrics.call_id == "call-001"
        assert metrics.start_time is not None
        assert metrics.end_time is None
        assert metrics.packets_sent == 0
        assert metrics.packets_received == 0
        assert metrics.packets_lost == 0
        assert metrics.packets_out_of_order == 0
        assert metrics.max_jitter == 0.0
        assert metrics.max_latency == 0.0
        assert metrics.avg_jitter == 0.0
        assert metrics.avg_latency == 0.0
        assert metrics.last_sequence_number is None
        assert metrics.expected_sequence is None
        assert metrics.last_packet_timestamp is None
        assert metrics.last_arrival_time is None
        assert metrics.mos_score == 0.0
        assert isinstance(metrics.lock, type(threading.Lock()))


@pytest.mark.unit
class TestQoSMetricsUpdatePacketReceived:
    """Tests for packet reception tracking."""

    def test_first_packet_initializes_tracking(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_received(100, 1000, 160)
        assert metrics.packets_received == 1
        assert metrics.last_sequence_number == 100
        assert metrics.expected_sequence == 101
        assert metrics.last_packet_timestamp == 1000

    def test_sequential_packets_no_loss(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_received(100, 1000, 160)
        metrics.update_packet_received(101, 1160, 160)
        assert metrics.packets_received == 2
        assert metrics.packets_lost == 0
        assert metrics.expected_sequence == (102 & 0xFFFF)

    def test_packet_loss_detection(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_received(100, 1000, 160)
        metrics.update_packet_received(103, 1480, 160)  # Skipped 101, 102
        assert metrics.packets_lost == 2

    def test_out_of_order_packet(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_received(100, 1000, 160)
        metrics.update_packet_received(101, 1160, 160)
        metrics.update_packet_received(99, 840, 160)  # Out of order
        assert metrics.packets_out_of_order == 1

    def test_jitter_calculation(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_received(100, 1000, 160)
        time.sleep(0.01)
        metrics.update_packet_received(101, 1160, 160)
        assert len(metrics.jitter_samples) > 0
        assert metrics.avg_jitter >= 0.0

    def test_max_jitter_tracked(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_received(100, 1000, 160)
        time.sleep(0.02)
        metrics.update_packet_received(101, 1160, 160)
        assert metrics.max_jitter >= 0.0

    def test_sequence_wrap_around(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_received(65534, 1000, 160)
        metrics.update_packet_received(65535, 1160, 160)
        assert metrics.expected_sequence == 0  # (65535 + 1) & 0xFFFF == 0

    def test_mos_calculated_after_update(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_received(100, 1000, 160)
        metrics.update_packet_received(101, 1160, 160)
        # MOS should be recalculated (may still be 0 with only 2 packets but _calculate_mos runs)
        assert metrics.mos_score >= 0.0


@pytest.mark.unit
class TestQoSMetricsUpdatePacketSent:
    """Tests for packet send tracking."""

    def test_update_packet_sent(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.update_packet_sent()
        assert metrics.packets_sent == 1

    def test_update_packet_sent_multiple(self) -> None:
        metrics = QoSMetrics("call-001")
        for _ in range(10):
            metrics.update_packet_sent()
        assert metrics.packets_sent == 10


@pytest.mark.unit
class TestQoSMetricsLatency:
    """Tests for latency tracking."""

    def test_add_latency_sample(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.add_latency_sample(50.0)
        assert len(metrics.latency_samples) == 1
        assert metrics.avg_latency == 50.0
        assert metrics.max_latency == 50.0

    def test_add_multiple_latency_samples(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.add_latency_sample(50.0)
        metrics.add_latency_sample(100.0)
        assert metrics.avg_latency == 75.0
        assert metrics.max_latency == 100.0

    def test_latency_max_tracked(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.add_latency_sample(200.0)
        metrics.add_latency_sample(100.0)
        assert metrics.max_latency == 200.0


@pytest.mark.unit
class TestQoSMetricsMOSCalculation:
    """Tests for MOS score calculation."""

    def test_mos_no_data(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics._calculate_mos()
        assert metrics.mos_score == 0.0

    def test_mos_perfect_conditions(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 100
        metrics.packets_lost = 0
        metrics.avg_latency = 20.0
        metrics.latency_samples.append(20.0)
        metrics.avg_jitter = 5.0
        metrics.jitter_samples.append(5.0)
        metrics._calculate_mos()
        assert metrics.mos_score >= 4.0

    def test_mos_with_high_packet_loss(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 80
        metrics.packets_lost = 20
        metrics.avg_jitter = 10.0
        metrics.jitter_samples.append(10.0)
        metrics._calculate_mos()
        assert metrics.mos_score < 4.5

    def test_mos_with_high_latency(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 100
        metrics.packets_lost = 0
        metrics.avg_latency = 500.0
        metrics.latency_samples.append(500.0)
        metrics._calculate_mos()
        assert metrics.mos_score < 4.5

    def test_mos_with_high_jitter(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 100
        metrics.packets_lost = 0
        metrics.avg_jitter = 100.0
        metrics.jitter_samples.append(100.0)
        metrics._calculate_mos()
        assert metrics.mos_score < 4.5

    def test_mos_clamp_minimum(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 10
        metrics.packets_lost = 100
        metrics.avg_latency = 1000.0
        metrics.latency_samples.append(1000.0)
        metrics.avg_jitter = 500.0
        metrics.jitter_samples.append(500.0)
        metrics._calculate_mos()
        assert metrics.mos_score >= 1.0

    def test_mos_r_factor_below_zero(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 1
        metrics.packets_lost = 500
        metrics.avg_latency = 5000.0
        metrics.latency_samples.append(5000.0)
        metrics.avg_jitter = 1000.0
        metrics.jitter_samples.append(1000.0)
        metrics._calculate_mos()
        assert metrics.mos_score == 1.0

    def test_mos_latency_below_threshold(self) -> None:
        """Test latency below 160ms threshold has no penalty."""
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 100
        metrics.packets_lost = 0
        metrics.avg_latency = 100.0  # 50ms one-way, below 160
        metrics.latency_samples.append(100.0)
        metrics._calculate_mos()
        assert metrics.mos_score > 4.0

    def test_mos_jitter_below_threshold(self) -> None:
        """Test jitter below 30ms threshold has no penalty."""
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 100
        metrics.packets_lost = 0
        metrics.avg_jitter = 10.0  # Below 30ms threshold
        metrics.jitter_samples.append(10.0)
        metrics._calculate_mos()
        assert metrics.mos_score > 4.0


@pytest.mark.unit
class TestQoSMetricsEndCall:
    """Tests for ending call tracking."""

    def test_end_call_sets_end_time(self) -> None:
        metrics = QoSMetrics("call-001")
        assert metrics.end_time is None
        metrics.end_call()
        assert metrics.end_time is not None

    def test_end_call_recalculates_mos(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 100
        metrics.packets_lost = 0
        metrics.latency_samples.append(20.0)
        metrics.avg_latency = 20.0
        metrics.end_call()
        assert metrics.mos_score > 0.0


@pytest.mark.unit
class TestQoSMetricsGetSummary:
    """Tests for QoS summary generation."""

    def test_get_summary_active_call(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_sent = 50
        metrics.packets_received = 48
        metrics.packets_lost = 2
        summary = metrics.get_summary()
        assert summary["call_id"] == "call-001"
        assert summary["packets_sent"] == 50
        assert summary["packets_received"] == 48
        assert summary["packets_lost"] == 2
        assert summary["end_time"] is None
        assert summary["duration_seconds"] >= 0
        assert "quality_rating" in summary

    def test_get_summary_ended_call(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.end_call()
        summary = metrics.get_summary()
        assert summary["end_time"] is not None
        assert summary["duration_seconds"] >= 0

    def test_get_summary_packet_loss_percentage(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.packets_received = 90
        metrics.packets_lost = 10
        summary = metrics.get_summary()
        assert summary["packet_loss_percentage"] == 10.0

    def test_get_summary_no_packets(self) -> None:
        metrics = QoSMetrics("call-001")
        summary = metrics.get_summary()
        assert summary["packet_loss_percentage"] == 0.0


@pytest.mark.unit
class TestQoSMetricsQualityRating:
    """Tests for quality rating strings."""

    def test_excellent_rating(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.mos_score = 4.5
        assert metrics._get_quality_rating() == "Excellent"

    def test_good_rating(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.mos_score = 4.1
        assert metrics._get_quality_rating() == "Good"

    def test_fair_rating(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.mos_score = 3.7
        assert metrics._get_quality_rating() == "Fair"

    def test_poor_rating(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.mos_score = 3.2
        assert metrics._get_quality_rating() == "Poor"

    def test_bad_rating(self) -> None:
        metrics = QoSMetrics("call-001")
        metrics.mos_score = 2.0
        assert metrics._get_quality_rating() == "Bad"


@pytest.mark.unit
class TestQoSMonitorInit:
    """Tests for QoSMonitor initialization."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_init(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        monitor = QoSMonitor(mock_pbx)
        assert monitor.pbx is mock_pbx
        assert monitor.active_calls == {}
        assert monitor.historical_data == []
        assert len(monitor.alert_thresholds) == 4
        assert monitor.alerts == []
        assert monitor.max_historical_records == 10000


@pytest.mark.unit
class TestQoSMonitorStartMonitoring:
    """Tests for starting call monitoring."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_start_monitoring_new_call(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        metrics = monitor.start_monitoring("call-001")
        assert isinstance(metrics, QoSMetrics)
        assert metrics.call_id == "call-001"
        assert "call-001" in monitor.active_calls

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_start_monitoring_existing_call(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        metrics1 = monitor.start_monitoring("call-001")
        metrics2 = monitor.start_monitoring("call-001")
        assert metrics1 is metrics2


@pytest.mark.unit
class TestQoSMonitorStopMonitoring:
    """Tests for stopping call monitoring."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_stop_monitoring_active_call(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db = None
        monitor = QoSMonitor(mock_pbx)
        monitor.start_monitoring("call-001")
        summary = monitor.stop_monitoring("call-001")
        assert summary is not None
        assert summary["call_id"] == "call-001"
        assert "call-001" not in monitor.active_calls
        assert len(monitor.historical_data) == 1

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_stop_monitoring_nonexistent_call(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        result = monitor.stop_monitoring("nonexistent")
        assert result is None

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_stop_monitoring_trims_historical(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db = None
        monitor = QoSMonitor(mock_pbx)
        monitor.max_historical_records = 2
        for i in range(4):
            monitor.start_monitoring(f"call-{i}")
            monitor.stop_monitoring(f"call-{i}")
        assert len(monitor.historical_data) == 2


@pytest.mark.unit
class TestQoSMonitorGetMetrics:
    """Tests for retrieving metrics."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_metrics_active_call(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        monitor.start_monitoring("call-001")
        result = monitor.get_metrics("call-001")
        assert result is not None
        assert result["call_id"] == "call-001"

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_metrics_nonexistent_call(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        assert monitor.get_metrics("nonexistent") is None

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_all_active_metrics(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        monitor.start_monitoring("call-001")
        monitor.start_monitoring("call-002")
        result = monitor.get_all_active_metrics()
        assert len(result) == 2

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_all_active_metrics_empty(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        result = monitor.get_all_active_metrics()
        assert result == []


@pytest.mark.unit
class TestQoSMonitorHistoricalMetrics:
    """Tests for historical metrics retrieval."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_historical_metrics_default(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db = None
        monitor = QoSMonitor(mock_pbx)
        monitor.start_monitoring("call-001")
        monitor.stop_monitoring("call-001")
        result = monitor.get_historical_metrics()
        assert len(result) == 1

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_historical_metrics_with_limit(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db = None
        monitor = QoSMonitor(mock_pbx)
        for i in range(5):
            monitor.start_monitoring(f"call-{i}")
            monitor.stop_monitoring(f"call-{i}")
        result = monitor.get_historical_metrics(limit=2)
        assert len(result) == 2

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_historical_metrics_with_min_mos(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db = None
        monitor = QoSMonitor(mock_pbx)
        # Create a call with some metrics to get non-zero MOS
        metrics = monitor.start_monitoring("call-001")
        metrics.packets_received = 100
        metrics.packets_lost = 0
        metrics.latency_samples.append(20.0)
        metrics.avg_latency = 20.0
        monitor.stop_monitoring("call-001")

        # This call has default MOS 0
        monitor.start_monitoring("call-002")
        monitor.stop_monitoring("call-002")

        result = monitor.get_historical_metrics(min_mos=1.0)
        # Only call-001 should have MOS >= 1.0
        assert all(d["mos_score"] >= 1.0 for d in result)


@pytest.mark.unit
class TestQoSMonitorAlerts:
    """Tests for quality alerts."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_alerts_empty(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        assert monitor.get_alerts() == []

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_alerts_with_limit(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        monitor.alerts = [{"type": "test", "message": f"alert {i}"} for i in range(10)]
        result = monitor.get_alerts(limit=5)
        assert len(result) == 5

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_clear_alerts(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        monitor.alerts = [{"type": "test"}, {"type": "test"}]
        count = monitor.clear_alerts()
        assert count == 2
        assert monitor.alerts == []

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_check_quality_alerts_low_mos(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        summary = {
            "call_id": "call-001",
            "mos_score": 2.0,
            "packet_loss_percentage": 0.0,
            "jitter_avg_ms": 10.0,
            "latency_avg_ms": 50.0,
        }
        monitor._check_quality_alerts(summary)
        assert len(monitor.alerts) == 1
        assert monitor.alerts[0]["type"] == "low_mos"

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_check_quality_alerts_high_packet_loss(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        summary = {
            "call_id": "call-001",
            "mos_score": 4.5,
            "packet_loss_percentage": 5.0,
            "jitter_avg_ms": 10.0,
            "latency_avg_ms": 50.0,
        }
        monitor._check_quality_alerts(summary)
        assert any(a["type"] == "high_packet_loss" for a in monitor.alerts)

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_check_quality_alerts_high_jitter(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        summary = {
            "call_id": "call-001",
            "mos_score": 4.5,
            "packet_loss_percentage": 0.0,
            "jitter_avg_ms": 100.0,
            "latency_avg_ms": 50.0,
        }
        monitor._check_quality_alerts(summary)
        assert any(a["type"] == "high_jitter" for a in monitor.alerts)

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_check_quality_alerts_high_latency(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        summary = {
            "call_id": "call-001",
            "mos_score": 4.5,
            "packet_loss_percentage": 0.0,
            "jitter_avg_ms": 10.0,
            "latency_avg_ms": 500.0,
        }
        monitor._check_quality_alerts(summary)
        assert any(a["type"] == "high_latency" for a in monitor.alerts)

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_check_quality_alerts_multiple(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        summary = {
            "call_id": "call-001",
            "mos_score": 2.0,
            "packet_loss_percentage": 5.0,
            "jitter_avg_ms": 100.0,
            "latency_avg_ms": 500.0,
        }
        monitor._check_quality_alerts(summary)
        assert len(monitor.alerts) == 4

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_alerts_list_trimmed(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        monitor.alerts = [{"type": "test"}] * 1010
        summary = {
            "call_id": "call-001",
            "mos_score": 2.0,
            "packet_loss_percentage": 0.0,
            "jitter_avg_ms": 10.0,
            "latency_avg_ms": 50.0,
        }
        monitor._check_quality_alerts(summary)
        assert len(monitor.alerts) <= 1000


@pytest.mark.unit
class TestQoSMonitorStatistics:
    """Tests for aggregate statistics."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_statistics_empty(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        stats = monitor.get_statistics()
        assert stats["total_calls"] == 0
        assert stats["average_mos"] == 0.0
        assert stats["calls_with_issues"] == 0

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_get_statistics_with_data(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db = None
        monitor = QoSMonitor(mock_pbx)
        # Add some historical data
        monitor.historical_data = [
            {"mos_score": 4.5, "call_id": "c1"},
            {"mos_score": 3.0, "call_id": "c2"},
            {"mos_score": 4.0, "call_id": "c3"},
        ]
        stats = monitor.get_statistics()
        assert stats["total_calls"] == 3
        assert stats["average_mos"] > 0
        assert stats["calls_with_issues"] == 1  # mos 3.0 < 3.5
        assert "issue_percentage" in stats


@pytest.mark.unit
class TestQoSMonitorStoreMetrics:
    """Tests for database storage of metrics."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_store_metrics_with_db(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db.enabled = True
        monitor = QoSMonitor(mock_pbx)
        summary = {
            "call_id": "call-001",
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-01T00:05:00",
            "duration_seconds": 300,
            "packets_sent": 100,
            "packets_received": 98,
            "packets_lost": 2,
            "packet_loss_percentage": 2.0,
            "jitter_avg_ms": 10.0,
            "jitter_max_ms": 20.0,
            "latency_avg_ms": 50.0,
            "latency_max_ms": 80.0,
            "mos_score": 4.2,
            "quality_rating": "Good",
        }
        monitor._store_metrics(summary)
        mock_pbx.db.execute.assert_called_once()

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_store_metrics_no_db(self, mock_get_logger) -> None:
        mock_pbx = MagicMock(spec=[])  # No db attribute
        monitor = QoSMonitor(mock_pbx)
        # Should not raise
        monitor._store_metrics({"call_id": "call-001"})

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_store_metrics_db_disabled(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db.enabled = False
        monitor = QoSMonitor(mock_pbx)
        monitor._store_metrics({"call_id": "call-001"})
        mock_pbx.db.execute.assert_not_called()

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_store_metrics_db_error(self, mock_get_logger) -> None:
        mock_pbx = MagicMock()
        mock_pbx.db.enabled = True
        mock_pbx.db.execute.side_effect = Exception("DB error")
        monitor = QoSMonitor(mock_pbx)
        summary = {
            "call_id": "call-001",
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-01T00:05:00",
            "duration_seconds": 300,
            "packets_sent": 100,
            "packets_received": 98,
            "packets_lost": 2,
            "packet_loss_percentage": 2.0,
            "jitter_avg_ms": 10.0,
            "jitter_max_ms": 20.0,
            "latency_avg_ms": 50.0,
            "latency_max_ms": 80.0,
            "mos_score": 4.2,
            "quality_rating": "Good",
        }
        # Should not raise
        monitor._store_metrics(summary)


@pytest.mark.unit
class TestQoSMonitorUpdateThresholds:
    """Tests for updating alert thresholds."""

    @patch("pbx.features.qos_monitoring.get_logger")
    def test_update_alert_thresholds(self, mock_get_logger) -> None:
        monitor = QoSMonitor(MagicMock())
        new_thresholds = {"mos_min": 4.0, "jitter_max": 30.0}
        monitor.update_alert_thresholds(new_thresholds)
        assert monitor.alert_thresholds["mos_min"] == 4.0
        assert monitor.alert_thresholds["jitter_max"] == 30.0
        # Original values preserved for keys not updated
        assert monitor.alert_thresholds["packet_loss_max"] == 2.0
        assert monitor.alert_thresholds["latency_max"] == 300.0
