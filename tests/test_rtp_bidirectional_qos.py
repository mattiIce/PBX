"""
Test RTP bidirectional QoS tracking to verify packet loss calculation fix
"""
import unittest
import struct
import time
from unittest.mock import Mock, MagicMock
from pbx.rtp.handler import RTPRelayHandler
from pbx.features.qos_monitoring import QoSMonitor


class TestRTPBidirectionalQoS(unittest.TestCase):
    """Test bidirectional RTP relay QoS tracking"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock PBX
        self.mock_pbx = Mock()
        self.mock_pbx.db = None
        
        # Create QoS monitor
        self.qos_monitor = QoSMonitor(self.mock_pbx)
        
    def test_bidirectional_packet_loss_calculation(self):
        """
        Test that bidirectional RTP traffic doesn't cause false packet loss
        
        This tests the fix for the issue where packets from both endpoints
        were being tracked in a single QoSMetrics object, causing false
        packet loss detection when sequence numbers from different endpoints
        were interleaved.
        """
        # Create relay handler with QoS monitoring
        call_id = "test-call-001"
        handler = RTPRelayHandler(10000, call_id, qos_monitor=self.qos_monitor)
        
        # Verify that two separate QoS metrics were created
        self.assertIsNotNone(handler.qos_metrics_a_to_b)
        self.assertIsNotNone(handler.qos_metrics_b_to_a)
        self.assertIsNot(handler.qos_metrics_a_to_b, handler.qos_metrics_b_to_a)
        
        # Simulate packets from endpoint A (sequence 1000-1049)
        for i in range(50):
            seq_num = 1000 + i
            timestamp = 160000 + (i * 160)
            handler.qos_metrics_a_to_b.update_packet_received(seq_num, timestamp, 160)
            handler.qos_metrics_a_to_b.update_packet_sent()
        
        # Simulate packets from endpoint B (sequence 500-549)
        for i in range(50):
            seq_num = 500 + i
            timestamp = 80000 + (i * 160)
            handler.qos_metrics_b_to_a.update_packet_received(seq_num, timestamp, 160)
            handler.qos_metrics_b_to_a.update_packet_sent()
        
        # Get summaries for both directions
        summary_a_to_b = handler.qos_metrics_a_to_b.get_summary()
        summary_b_to_a = handler.qos_metrics_b_to_a.get_summary()
        
        # Verify A->B direction has no packet loss
        self.assertEqual(summary_a_to_b['packets_received'], 50)
        self.assertEqual(summary_a_to_b['packets_lost'], 0)
        self.assertEqual(summary_a_to_b['packet_loss_percentage'], 0.0)
        self.assertGreater(summary_a_to_b['mos_score'], 4.0, 
                          f"A->B MOS should be > 4.0, got {summary_a_to_b['mos_score']}")
        
        # Verify B->A direction has no packet loss
        self.assertEqual(summary_b_to_a['packets_received'], 50)
        self.assertEqual(summary_b_to_a['packets_lost'], 0)
        self.assertEqual(summary_b_to_a['packet_loss_percentage'], 0.0)
        self.assertGreater(summary_b_to_a['mos_score'], 4.0,
                          f"B->A MOS should be > 4.0, got {summary_b_to_a['mos_score']}")
        
        # Clean up
        handler.stop()
        
    def test_interleaved_packets_no_false_loss(self):
        """
        Test that interleaved packets from both endpoints don't cause false packet loss
        
        This simulates the real-world scenario where packets arrive alternately
        from both endpoints, which was causing ~90% false packet loss before the fix.
        """
        call_id = "test-call-002"
        handler = RTPRelayHandler(10001, call_id, qos_monitor=self.qos_monitor)
        
        # Simulate interleaved packets (alternating A and B)
        # A: seq 1000, 1001, 1002, ...
        # B: seq 500, 501, 502, ...
        for i in range(100):
            if i % 2 == 0:
                # Packet from A
                seq_num = 1000 + (i // 2)
                timestamp = 160000 + (i // 2) * 160
                handler.qos_metrics_a_to_b.update_packet_received(seq_num, timestamp, 160)
                handler.qos_metrics_a_to_b.update_packet_sent()
            else:
                # Packet from B
                seq_num = 500 + (i // 2)
                timestamp = 80000 + (i // 2) * 160
                handler.qos_metrics_b_to_a.update_packet_received(seq_num, timestamp, 160)
                handler.qos_metrics_b_to_a.update_packet_sent()
        
        # Get summaries
        summary_a_to_b = handler.qos_metrics_a_to_b.get_summary()
        summary_b_to_a = handler.qos_metrics_b_to_a.get_summary()
        
        # Both directions should have 50 packets with 0% loss
        self.assertEqual(summary_a_to_b['packets_received'], 50)
        self.assertEqual(summary_a_to_b['packets_lost'], 0)
        self.assertEqual(summary_a_to_b['packet_loss_percentage'], 0.0)
        
        self.assertEqual(summary_b_to_a['packets_received'], 50)
        self.assertEqual(summary_b_to_a['packets_lost'], 0)
        self.assertEqual(summary_b_to_a['packet_loss_percentage'], 0.0)
        
        # Both should have excellent MOS scores
        self.assertGreater(summary_a_to_b['mos_score'], 4.0)
        self.assertGreater(summary_b_to_a['mos_score'], 4.0)
        
        # Clean up
        handler.stop()
        
    def test_actual_packet_loss_detection(self):
        """
        Test that actual packet loss is still detected correctly in each direction
        """
        call_id = "test-call-003"
        handler = RTPRelayHandler(10002, call_id, qos_monitor=self.qos_monitor)
        
        # Simulate A->B with 10% packet loss
        # Send packets with sequence numbers: 1000, 1001, 1002, [skip 1003], 1004, 1005, ...
        seq_nums_a = []
        for i in range(100):
            if i % 10 == 3:  # Skip every 10th packet (10% loss)
                continue
            seq_nums_a.append(1000 + i)
        
        for seq_num in seq_nums_a:
            timestamp = 160000 + (seq_num - 1000) * 160
            handler.qos_metrics_a_to_b.update_packet_received(seq_num, timestamp, 160)
            handler.qos_metrics_a_to_b.update_packet_sent()
        
        # Simulate B->A with no packet loss
        for i in range(100):
            seq_num = 500 + i
            timestamp = 80000 + i * 160
            handler.qos_metrics_b_to_a.update_packet_received(seq_num, timestamp, 160)
            handler.qos_metrics_b_to_a.update_packet_sent()
        
        # Get summaries
        summary_a_to_b = handler.qos_metrics_a_to_b.get_summary()
        summary_b_to_a = handler.qos_metrics_b_to_a.get_summary()
        
        # A->B should show ~10% packet loss
        self.assertEqual(summary_a_to_b['packets_received'], 90)  # 90 packets received
        self.assertEqual(summary_a_to_b['packets_lost'], 10)  # 10 packets lost
        self.assertAlmostEqual(summary_a_to_b['packet_loss_percentage'], 10.0, delta=0.1)
        
        # B->A should have 0% packet loss
        self.assertEqual(summary_b_to_a['packets_received'], 100)
        self.assertEqual(summary_b_to_a['packets_lost'], 0)
        self.assertEqual(summary_b_to_a['packet_loss_percentage'], 0.0)
        
        # MOS scores should reflect the difference in quality
        self.assertLess(summary_a_to_b['mos_score'], summary_b_to_a['mos_score'])
        
        # Clean up
        handler.stop()


if __name__ == '__main__':
    unittest.main()
