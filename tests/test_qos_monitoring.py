"""
Tests for QoS (Quality of Service) Monitoring System
"""

import time


from pbx.features.qos_monitoring import QoSMetrics, QoSMonitor


class MockPBX:
    """Mock PBX for testing"""

    def __init__(self) -> None:
        self.db = None


class TestQoSMetrics:
    """Test QoSMetrics class"""

    def test_metrics_initialization(self) -> None:
        """Test that metrics are properly initialized"""
        metrics = QoSMetrics("test-call-123")

        assert metrics.call_id == "test-call-123"
        assert metrics.packets_sent == 0
        assert metrics.packets_received == 0
        assert metrics.packets_lost == 0
        assert metrics.mos_score == 0.0
        assert metrics.end_time is None
    def test_packet_sent_tracking(self) -> None:
        """Test packet sent counter"""
        metrics = QoSMetrics("test-call-123")

        for i in range(10):
            metrics.update_packet_sent()

        assert metrics.packets_sent == 10
    def test_packet_received_no_loss(self) -> None:
        """Test packet reception with no packet loss"""
        metrics = QoSMetrics("test-call-123")

        # Simulate receiving 10 packets in sequence
        for seq in range(100, 110):
            metrics.update_packet_received(seq, seq * 160, 160)

        assert metrics.packets_received == 10
        assert metrics.packets_lost == 0
    def test_packet_loss_detection(self) -> None:
        """Test packet loss detection"""
        metrics = QoSMetrics("test-call-123")

        # Receive packet 100
        metrics.update_packet_received(100, 16000, 160)

        # Skip packets 101-103, receive 104 (3 packets lost)
        metrics.update_packet_received(104, 16640, 160)

        assert metrics.packets_received == 2
        assert metrics.packets_lost == 3
    def test_out_of_order_detection(self) -> None:
        """Test out-of-order packet detection"""
        metrics = QoSMetrics("test-call-123")

        # Receive packets in order: 100, 101, 102
        metrics.update_packet_received(100, 16000, 160)
        metrics.update_packet_received(101, 16160, 160)
        metrics.update_packet_received(102, 16320, 160)

        # Receive packet 99 (out of order)
        metrics.update_packet_received(99, 15840, 160)

        assert metrics.packets_out_of_order == 1
    def test_jitter_calculation(self) -> None:
        """Test jitter calculation"""
        metrics = QoSMetrics("test-call-123")

        # Simulate regular packet arrival
        base_time = time.time()
        for i in range(10):
            # Packets arriving every 20ms with small variations
            arrival_time = base_time + (i * 0.02) + (i % 2) * 0.005
            timestamp = i * 160  # 20ms at 8kHz sample rate

            # Manually set arrival time for testing
            if i == 0:
                metrics.last_arrival_time = arrival_time
                metrics.last_packet_timestamp = timestamp
            else:
                metrics.last_arrival_time
                metrics.last_arrival_time = arrival_time
                metrics.update_packet_received(100 + i, timestamp, 160)

        # Jitter should be calculated and stored
        assert len(metrics.jitter_samples) > 0
        assert metrics.avg_jitter > 0.0
    def test_mos_score_perfect_conditions(self) -> None:
        """Test MOS score with perfect network conditions"""
        metrics = QoSMetrics("test-call-123")

        # Simulate perfect packet reception (no loss, low jitter, low latency)
        for seq in range(100, 200):
            metrics.update_packet_received(seq, seq * 160, 160)

        # Add low latency samples
        for _ in range(10):
            metrics.add_latency_sample(50.0)  # 50ms RTT

        # MOS should be high (>= 4.0) with perfect conditions
        summary = metrics.get_summary()
        assert summary["mos_score"] >= 4.0
        assert summary["quality_rating"] == "Excellent"
    def test_mos_score_poor_conditions(self) -> None:
        """Test MOS score with poor network conditions"""
        metrics = QoSMetrics("test-call-123")

        # Simulate packet loss (every 3rd packet lost)
        for seq in range(100, 200):
            if seq % 3 == 0:
                # Skip this packet (simulate loss)
                pass
            else:
                metrics.update_packet_received(seq, seq * 160, 160)

        # Add high latency samples
        for _ in range(10):
            metrics.add_latency_sample(400.0)  # 400ms RTT (very high)

        # MOS should be low (< 3.5) with poor conditions
        summary = metrics.get_summary()
        assert summary["mos_score"] < 3.5
        assert summary["quality_rating"] in ["Poor", "Bad"]
    def test_summary_generation(self) -> None:
        """Test summary data generation"""
        metrics = QoSMetrics("test-call-123")

        # Add some test data
        for seq in range(100, 110):
            metrics.update_packet_received(seq, seq * 160, 160)

        metrics.add_latency_sample(100.0)
        metrics.end_call()

        summary = metrics.get_summary()

        # Verify all expected fields are present
        assert "call_id" in summary
        assert "start_time" in summary
        assert "end_time" in summary
        assert "duration_seconds" in summary
        assert "packets_received" in summary
        assert "packets_lost" in summary
        assert "packet_loss_percentage" in summary
        assert "jitter_avg_ms" in summary
        assert "latency_avg_ms" in summary
        assert "mos_score" in summary
        assert "quality_rating" in summary
        assert summary["call_id"] == "test-call-123"
        assert summary["packets_received"] == 10
class TestQoSMonitor:
    """Test QoSMonitor class"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.pbx = MockPBX()
        self.monitor = QoSMonitor(self.pbx)

    def test_monitor_initialization(self) -> None:
        """Test monitor initialization"""
        assert self.monitor is not None
        assert len(self.monitor.active_calls) == 0
        assert len(self.monitor.historical_data) == 0
        assert len(self.monitor.alerts) == 0
    def test_start_monitoring(self) -> None:
        """Test starting QoS monitoring for a call"""
        metrics = self.monitor.start_monitoring("call-001")

        assert metrics is not None
        assert metrics.call_id == "call-001"
        assert "call-001" in self.monitor.active_calls
        assert len(self.monitor.active_calls) == 1
    def test_stop_monitoring(self) -> None:
        """Test stopping QoS monitoring"""
        # Start monitoring
        self.monitor.start_monitoring("call-001")

        # Stop monitoring
        summary = self.monitor.stop_monitoring("call-001")

        assert summary is not None
        assert summary["call_id"] == "call-001"
        assert "call-001" not in self.monitor.active_calls
        assert len(self.monitor.historical_data) == 1
    def test_get_metrics(self) -> None:
        """Test getting current metrics for active call"""
        self.monitor.start_monitoring("call-001")

        metrics = self.monitor.get_metrics("call-001")

        assert metrics is not None
        assert metrics["call_id"] == "call-001"
    def test_get_all_active_metrics(self) -> None:
        """Test getting metrics for all active calls"""
        self.monitor.start_monitoring("call-001")
        self.monitor.start_monitoring("call-002")
        self.monitor.start_monitoring("call-003")

        all_metrics = self.monitor.get_all_active_metrics()

        assert len(all_metrics) == 3
        call_ids = [m["call_id"] for m in all_metrics]
        assert "call-001" in call_ids
        assert "call-002" in call_ids
        assert "call-003" in call_ids
    def test_historical_metrics(self) -> None:
        """Test historical metrics storage"""
        # Monitor and complete 5 calls
        for i in range(5):
            call_id = f"call-{i:03d}"
            self.monitor.start_monitoring(call_id)
            self.monitor.stop_monitoring(call_id)

        history = self.monitor.get_historical_metrics(limit=10)

        assert len(history) == 5
    def test_historical_metrics_filtering(self) -> None:
        """Test filtering historical metrics by MOS score"""
        # Create calls with different quality
        for i in range(10):
            call_id = f"call-{i:03d}"
            metrics = self.monitor.start_monitoring(call_id)

            # Simulate different quality levels
            if i < 5:
                # Good quality - lots of packets, low loss
                for seq in range(100, 200):
                    metrics.update_packet_received(seq, seq * 160, 160)
                metrics.add_latency_sample(50.0)
            else:
                # Poor quality - high loss
                for seq in range(100, 200):
                    if seq % 5 != 0:  # 20% packet loss
                        metrics.update_packet_received(seq, seq * 160, 160)
                metrics.add_latency_sample(400.0)

            self.monitor.stop_monitoring(call_id)

        # Get only high-quality calls (MOS >= 4.0)
        high_quality = self.monitor.get_historical_metrics(limit=100, min_mos=4.0)

        # Should have approximately 5 high-quality calls
        assert len(high_quality) > 0
        for call in high_quality:
            assert call["mos_score"] >= 4.0
    def test_alert_generation_low_mos(self) -> None:
        """Test alert generation for low MOS score"""
        call_id = "bad-quality-call"
        metrics = self.monitor.start_monitoring(call_id)

        # Simulate very poor quality (high packet loss)
        for seq in range(100, 200):
            if seq % 2 == 0:  # 50% packet loss
                metrics.update_packet_received(seq, seq * 160, 160)

        # Stop monitoring (triggers alert check)
        self.monitor.stop_monitoring(call_id)

        # Should have generated at least one alert
        assert len(self.monitor.alerts) > 0
        # Check for low MOS alert
        alert_types = [a["type"] for a in self.monitor.alerts]
        assert "low_mos" in alert_types
    def test_alert_generation_packet_loss(self) -> None:
        """Test alert generation for high packet loss"""
        call_id = "packet-loss-call"
        metrics = self.monitor.start_monitoring(call_id)

        # Simulate 10% packet loss (exceeds default threshold of 2%)
        for seq in range(100, 200):
            if seq % 10 != 0:  # 10% loss
                metrics.update_packet_received(seq, seq * 160, 160)

        self.monitor.stop_monitoring(call_id)

        alerts = self.monitor.get_alerts()
        alert_types = [a["type"] for a in alerts]
        assert "high_packet_loss" in alert_types
    def test_clear_alerts(self) -> None:
        """Test clearing alerts"""
        # Generate some alerts
        call_id = "bad-call"
        metrics = self.monitor.start_monitoring(call_id)

        # Simulate poor quality
        for seq in range(100, 150):
            if seq % 3 == 0:
                metrics.update_packet_received(seq, seq * 160, 160)

        self.monitor.stop_monitoring(call_id)

        # Verify alerts exist
        assert len(self.monitor.alerts) > 0
        # Clear alerts
        count = self.monitor.clear_alerts()

        assert count > 0
        assert len(self.monitor.alerts) == 0
    def test_get_statistics(self) -> None:
        """Test overall statistics generation"""
        # Monitor several calls with varying quality
        for i in range(20):
            call_id = f"call-{i:03d}"
            metrics = self.monitor.start_monitoring(call_id)

            # Good quality for first 15, poor for last 5
            if i < 15:
                for seq in range(100, 150):
                    metrics.update_packet_received(seq, seq * 160, 160)
                metrics.add_latency_sample(50.0)
            else:
                for seq in range(100, 150):
                    if seq % 4 != 0:
                        metrics.update_packet_received(seq, seq * 160, 160)
                metrics.add_latency_sample(350.0)

            self.monitor.stop_monitoring(call_id)

        stats = self.monitor.get_statistics()

        assert stats["total_calls"] == 20
        assert stats["average_mos"] > 0.0
        assert stats["calls_with_issues"] > 0
        assert stats["issue_percentage"] > 0.0
    def test_update_thresholds(self) -> None:
        """Test updating alert thresholds"""
        # Set custom thresholds
        new_thresholds = {
            "mos_min": 4.0,
            "packet_loss_max": 1.0,
            "jitter_max": 30.0,
            "latency_max": 200.0,
        }

        self.monitor.update_alert_thresholds(new_thresholds)

        assert self.monitor.alert_thresholds["mos_min"] == 4.0
        assert self.monitor.alert_thresholds["packet_loss_max"] == 1.0
        assert self.monitor.alert_thresholds["jitter_max"] == 30.0
        assert self.monitor.alert_thresholds["latency_max"] == 200.0
    def test_max_historical_records_limit(self) -> None:
        """Test that historical data doesn't exceed maximum"""
        # Set a small limit for testing
        self.monitor.max_historical_records = 100

        # Generate more calls than the limit
        for i in range(150):
            call_id = f"call-{i:04d}"
            self.monitor.start_monitoring(call_id)
            self.monitor.stop_monitoring(call_id)

        # Historical data should not exceed the limit
        assert len(self.monitor.historical_data) <= 100
