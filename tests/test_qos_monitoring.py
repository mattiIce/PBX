"""
Tests for QoS (Quality of Service) Monitoring System
"""

import os
import sys
import time
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.qos_monitoring import QoSMetrics, QoSMonitor


class MockPBX:
    """Mock PBX for testing"""

    def __init__(self):
        self.db = None


class TestQoSMetrics(unittest.TestCase):
    """Test QoSMetrics class"""

    def test_metrics_initialization(self):
        """Test that metrics are properly initialized"""
        metrics = QoSMetrics("test-call-123")

        self.assertEqual(metrics.call_id, "test-call-123")
        self.assertEqual(metrics.packets_sent, 0)
        self.assertEqual(metrics.packets_received, 0)
        self.assertEqual(metrics.packets_lost, 0)
        self.assertEqual(metrics.mos_score, 0.0)
        self.assertIsNone(metrics.end_time)

    def test_packet_sent_tracking(self):
        """Test packet sent counter"""
        metrics = QoSMetrics("test-call-123")

        for i in range(10):
            metrics.update_packet_sent()

        self.assertEqual(metrics.packets_sent, 10)

    def test_packet_received_no_loss(self):
        """Test packet reception with no packet loss"""
        metrics = QoSMetrics("test-call-123")

        # Simulate receiving 10 packets in sequence
        for seq in range(100, 110):
            metrics.update_packet_received(seq, seq * 160, 160)

        self.assertEqual(metrics.packets_received, 10)
        self.assertEqual(metrics.packets_lost, 0)

    def test_packet_loss_detection(self):
        """Test packet loss detection"""
        metrics = QoSMetrics("test-call-123")

        # Receive packet 100
        metrics.update_packet_received(100, 16000, 160)

        # Skip packets 101-103, receive 104 (3 packets lost)
        metrics.update_packet_received(104, 16640, 160)

        self.assertEqual(metrics.packets_received, 2)
        self.assertEqual(metrics.packets_lost, 3)

    def test_out_of_order_detection(self):
        """Test out-of-order packet detection"""
        metrics = QoSMetrics("test-call-123")

        # Receive packets in order: 100, 101, 102
        metrics.update_packet_received(100, 16000, 160)
        metrics.update_packet_received(101, 16160, 160)
        metrics.update_packet_received(102, 16320, 160)

        # Receive packet 99 (out of order)
        metrics.update_packet_received(99, 15840, 160)

        self.assertEqual(metrics.packets_out_of_order, 1)

    def test_jitter_calculation(self):
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
                old_time = metrics.last_arrival_time
                metrics.last_arrival_time = arrival_time
                metrics.update_packet_received(100 + i, timestamp, 160)

        # Jitter should be calculated and stored
        self.assertGreater(len(metrics.jitter_samples), 0)
        self.assertGreater(metrics.avg_jitter, 0.0)

    def test_mos_score_perfect_conditions(self):
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
        self.assertGreaterEqual(summary["mos_score"], 4.0)
        self.assertEqual(summary["quality_rating"], "Excellent")

    def test_mos_score_poor_conditions(self):
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
        self.assertLess(summary["mos_score"], 3.5)
        self.assertIn(summary["quality_rating"], ["Poor", "Bad"])

    def test_summary_generation(self):
        """Test summary data generation"""
        metrics = QoSMetrics("test-call-123")

        # Add some test data
        for seq in range(100, 110):
            metrics.update_packet_received(seq, seq * 160, 160)

        metrics.add_latency_sample(100.0)
        metrics.end_call()

        summary = metrics.get_summary()

        # Verify all expected fields are present
        self.assertIn("call_id", summary)
        self.assertIn("start_time", summary)
        self.assertIn("end_time", summary)
        self.assertIn("duration_seconds", summary)
        self.assertIn("packets_received", summary)
        self.assertIn("packets_lost", summary)
        self.assertIn("packet_loss_percentage", summary)
        self.assertIn("jitter_avg_ms", summary)
        self.assertIn("latency_avg_ms", summary)
        self.assertIn("mos_score", summary)
        self.assertIn("quality_rating", summary)

        self.assertEqual(summary["call_id"], "test-call-123")
        self.assertEqual(summary["packets_received"], 10)


class TestQoSMonitor(unittest.TestCase):
    """Test QoSMonitor class"""

    def setUp(self):
        """Set up test fixtures"""
        self.pbx = MockPBX()
        self.monitor = QoSMonitor(self.pbx)

    def test_monitor_initialization(self):
        """Test monitor initialization"""
        self.assertIsNotNone(self.monitor)
        self.assertEqual(len(self.monitor.active_calls), 0)
        self.assertEqual(len(self.monitor.historical_data), 0)
        self.assertEqual(len(self.monitor.alerts), 0)

    def test_start_monitoring(self):
        """Test starting QoS monitoring for a call"""
        metrics = self.monitor.start_monitoring("call-001")

        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.call_id, "call-001")
        self.assertIn("call-001", self.monitor.active_calls)
        self.assertEqual(len(self.monitor.active_calls), 1)

    def test_stop_monitoring(self):
        """Test stopping QoS monitoring"""
        # Start monitoring
        self.monitor.start_monitoring("call-001")

        # Stop monitoring
        summary = self.monitor.stop_monitoring("call-001")

        self.assertIsNotNone(summary)
        self.assertEqual(summary["call_id"], "call-001")
        self.assertNotIn("call-001", self.monitor.active_calls)
        self.assertEqual(len(self.monitor.historical_data), 1)

    def test_get_metrics(self):
        """Test getting current metrics for active call"""
        self.monitor.start_monitoring("call-001")

        metrics = self.monitor.get_metrics("call-001")

        self.assertIsNotNone(metrics)
        self.assertEqual(metrics["call_id"], "call-001")

    def test_get_all_active_metrics(self):
        """Test getting metrics for all active calls"""
        self.monitor.start_monitoring("call-001")
        self.monitor.start_monitoring("call-002")
        self.monitor.start_monitoring("call-003")

        all_metrics = self.monitor.get_all_active_metrics()

        self.assertEqual(len(all_metrics), 3)
        call_ids = [m["call_id"] for m in all_metrics]
        self.assertIn("call-001", call_ids)
        self.assertIn("call-002", call_ids)
        self.assertIn("call-003", call_ids)

    def test_historical_metrics(self):
        """Test historical metrics storage"""
        # Monitor and complete 5 calls
        for i in range(5):
            call_id = f"call-{i:03d}"
            self.monitor.start_monitoring(call_id)
            self.monitor.stop_monitoring(call_id)

        history = self.monitor.get_historical_metrics(limit=10)

        self.assertEqual(len(history), 5)

    def test_historical_metrics_filtering(self):
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
        self.assertGreater(len(high_quality), 0)
        for call in high_quality:
            self.assertGreaterEqual(call["mos_score"], 4.0)

    def test_alert_generation_low_mos(self):
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
        self.assertGreater(len(self.monitor.alerts), 0)

        # Check for low MOS alert
        alert_types = [a["type"] for a in self.monitor.alerts]
        self.assertIn("low_mos", alert_types)

    def test_alert_generation_packet_loss(self):
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
        self.assertIn("high_packet_loss", alert_types)

    def test_clear_alerts(self):
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
        self.assertGreater(len(self.monitor.alerts), 0)

        # Clear alerts
        count = self.monitor.clear_alerts()

        self.assertGreater(count, 0)
        self.assertEqual(len(self.monitor.alerts), 0)

    def test_get_statistics(self):
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

        self.assertEqual(stats["total_calls"], 20)
        self.assertGreater(stats["average_mos"], 0.0)
        self.assertGreater(stats["calls_with_issues"], 0)
        self.assertGreater(stats["issue_percentage"], 0.0)

    def test_update_thresholds(self):
        """Test updating alert thresholds"""
        # Set custom thresholds
        new_thresholds = {
            "mos_min": 4.0,
            "packet_loss_max": 1.0,
            "jitter_max": 30.0,
            "latency_max": 200.0,
        }

        self.monitor.update_alert_thresholds(new_thresholds)

        self.assertEqual(self.monitor.alert_thresholds["mos_min"], 4.0)
        self.assertEqual(self.monitor.alert_thresholds["packet_loss_max"], 1.0)
        self.assertEqual(self.monitor.alert_thresholds["jitter_max"], 30.0)
        self.assertEqual(self.monitor.alert_thresholds["latency_max"], 200.0)

    def test_max_historical_records_limit(self):
        """Test that historical data doesn't exceed maximum"""
        # Set a small limit for testing
        self.monitor.max_historical_records = 100

        # Generate more calls than the limit
        for i in range(150):
            call_id = f"call-{i:04d}"
            self.monitor.start_monitoring(call_id)
            self.monitor.stop_monitoring(call_id)

        # Historical data should not exceed the limit
        self.assertLessEqual(len(self.monitor.historical_data), 100)


if __name__ == "__main__":
    unittest.main()
