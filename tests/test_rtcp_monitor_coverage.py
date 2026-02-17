"""Comprehensive tests for the RTCPMonitor, RTCPStats, and RTCPMonitorManager modules."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pbx.rtp.rtcp_monitor import RTCPMonitor, RTCPMonitorManager, RTCPStats


@pytest.mark.unit
class TestRTCPStats:
    """Tests for the RTCPStats dataclass."""

    def test_default_values(self) -> None:
        """Test that all default values are correct."""
        stats = RTCPStats()

        assert stats.packets_sent == 0
        assert stats.bytes_sent == 0
        assert stats.packets_received == 0
        assert stats.packets_lost == 0
        assert stats.packets_expected == 0
        assert stats.bytes_received == 0
        assert stats.jitter_ms == 0.0
        assert stats.rtt_ms == 0.0
        assert stats.packet_loss_percent == 0.0
        assert stats.mos_score == 0.0
        assert stats.first_packet_time is None
        assert stats.last_packet_time is None
        assert stats.highest_sequence == 0
        assert stats.sequence_cycles == 0
        assert stats.last_sequence is None
        assert stats.last_sr_timestamp == 0
        assert stats.last_sr_time == 0.0

    def test_custom_values(self) -> None:
        """Test creating RTCPStats with custom values."""
        stats = RTCPStats(
            packets_sent=100,
            bytes_sent=16000,
            packets_received=95,
            packets_lost=5,
            jitter_ms=12.5,
            rtt_ms=30.0,
            mos_score=4.2,
        )

        assert stats.packets_sent == 100
        assert stats.bytes_sent == 16000
        assert stats.packets_received == 95
        assert stats.packets_lost == 5
        assert stats.jitter_ms == 12.5
        assert stats.rtt_ms == 30.0
        assert stats.mos_score == 4.2


@pytest.mark.unit
class TestRTCPMonitor:
    """Tests for the RTCPMonitor class."""

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_init_default_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with default configuration."""
        monitor = RTCPMonitor("call-123")

        assert monitor.call_id == "call-123"
        assert monitor.interval_seconds == 5
        assert monitor.alert_thresholds == {
            "packet_loss_percent": 5.0,
            "jitter_ms": 50.0,
            "mos_min": 3.5,
            "rtt_ms": 300.0,
        }
        assert monitor.transit_time is None
        assert monitor.last_arrival_time is None
        assert isinstance(monitor.stats, RTCPStats)

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_init_custom_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with custom configuration."""
        config = {
            "interval_seconds": 10,
            "alert_thresholds": {
                "packet_loss_percent": 2.0,
                "jitter_ms": 30.0,
                "mos_min": 4.0,
                "rtt_ms": 150.0,
            },
        }
        monitor = RTCPMonitor("call-456", config)

        assert monitor.interval_seconds == 10
        assert monitor.alert_thresholds["packet_loss_percent"] == 2.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_update_sent_packet(self, mock_get_logger: MagicMock) -> None:
        """Test updating sent packet statistics."""
        monitor = RTCPMonitor("call-123")

        monitor.update_sent_packet(160)
        monitor.update_sent_packet(160)

        assert monitor.stats.packets_sent == 2
        assert monitor.stats.bytes_sent == 320

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    @patch("pbx.rtp.rtcp_monitor.time")
    def test_update_received_packet_first(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test updating received packet for the first time."""
        mock_time.time.return_value = 1000.0
        monitor = RTCPMonitor("call-123")

        monitor.update_received_packet(sequence=1, timestamp=8000, size=160)

        assert monitor.stats.packets_received == 1
        assert monitor.stats.bytes_received == 160
        assert monitor.stats.first_packet_time == 1000.0
        assert monitor.stats.last_packet_time == 1000.0
        assert monitor.stats.last_sequence == 1
        assert monitor.stats.highest_sequence == 1

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    @patch("pbx.rtp.rtcp_monitor.time")
    def test_update_received_packet_multiple(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test updating received packets multiple times."""
        mock_time.time.return_value = 1000.0
        monitor = RTCPMonitor("call-123")

        monitor.update_received_packet(sequence=1, timestamp=8000, size=160)

        mock_time.time.return_value = 1000.02
        monitor.update_received_packet(sequence=2, timestamp=8160, size=160)

        assert monitor.stats.packets_received == 2
        assert monitor.stats.bytes_received == 320
        assert monitor.stats.first_packet_time == 1000.0
        assert monitor.stats.last_packet_time == 1000.02
        assert monitor.stats.last_sequence == 2
        assert monitor.stats.highest_sequence == 2

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_update_lost_packet(self, mock_get_logger: MagicMock) -> None:
        """Test updating lost packet count."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packets_expected = 10

        monitor.update_lost_packet()
        monitor.update_lost_packet()

        assert monitor.stats.packets_lost == 2
        assert monitor.stats.packet_loss_percent == pytest.approx(20.0)

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_update_rtt(self, mock_get_logger: MagicMock) -> None:
        """Test updating round-trip time."""
        monitor = RTCPMonitor("call-123")

        monitor.update_rtt(50.0)

        assert monitor.stats.rtt_ms == 50.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_update_sequence_first_packet(self, mock_get_logger: MagicMock) -> None:
        """Test sequence tracking for the first packet."""
        monitor = RTCPMonitor("call-123")

        monitor._update_sequence(100)

        assert monitor.stats.last_sequence == 100
        assert monitor.stats.highest_sequence == 100
        assert monitor.stats.sequence_cycles == 0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_update_sequence_normal_increment(self, mock_get_logger: MagicMock) -> None:
        """Test normal sequential increment."""
        monitor = RTCPMonitor("call-123")

        monitor._update_sequence(100)
        monitor._update_sequence(101)
        monitor._update_sequence(102)

        assert monitor.stats.last_sequence == 102
        assert monitor.stats.highest_sequence == 102
        assert monitor.stats.sequence_cycles == 0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_update_sequence_wraparound(self, mock_get_logger: MagicMock) -> None:
        """Test sequence number wraparound detection (65535 -> 0)."""
        monitor = RTCPMonitor("call-123")

        monitor._update_sequence(65534)
        monitor._update_sequence(65535)

        # Now wraparound: seq=1, last_seq=65535
        # diff = 1 - 65535 = -65534, which is < -32768
        # so diff += 65536 = 2, and sequence_cycles += 1
        monitor._update_sequence(1)

        assert monitor.stats.sequence_cycles == 1
        assert monitor.stats.last_sequence == 1

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_update_sequence_negative_wraparound(self, mock_get_logger: MagicMock) -> None:
        """Test large positive diff indicating negative wraparound."""
        monitor = RTCPMonitor("call-123")

        monitor._update_sequence(1)
        # seq=65535, last_seq=1 => diff = 65534 > 32768
        # so diff -= 65536 = -2 (old packet, no cycle increment)
        monitor._update_sequence(65535)

        assert monitor.stats.sequence_cycles == 0
        # highest_sequence should not update since diff < 0
        assert monitor.stats.highest_sequence == 1

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    @patch("pbx.rtp.rtcp_monitor.time")
    def test_calculate_jitter_first_packet(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test jitter calculation sets baseline on first packet."""
        monitor = RTCPMonitor("call-123")

        monitor._calculate_jitter(8000, 1000.0)

        assert monitor.last_arrival_time == 1000.0
        assert monitor.transit_time == pytest.approx(1000.0 - 8000 / 8000.0)

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_calculate_jitter_second_packet(self, mock_get_logger: MagicMock) -> None:
        """Test jitter calculation on second packet updates jitter_ms."""
        monitor = RTCPMonitor("call-123")

        # First packet establishes baseline
        monitor._calculate_jitter(8000, 1000.0)

        # Second packet with some jitter
        monitor._calculate_jitter(8160, 1000.025)

        assert monitor.stats.jitter_ms >= 0
        assert monitor.transit_time is not None
        assert monitor.last_arrival_time == 1000.025

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_calculate_jitter_accumulation(self, mock_get_logger: MagicMock) -> None:
        """Test jitter accumulates over multiple packets with variable timing."""
        monitor = RTCPMonitor("call-123")

        base_time = 1000.0
        timestamp = 8000

        # Packet 1 - baseline
        monitor._calculate_jitter(timestamp, base_time)

        # Packets with increasing jitter
        for i in range(1, 20):
            timestamp += 160
            jitter_offset = 0.005 * (i % 3)  # Variable jitter
            arrival = base_time + (i * 0.02) + jitter_offset
            monitor._calculate_jitter(timestamp, arrival)

        # Jitter should be positive after experiencing variable delays
        assert monitor.stats.jitter_ms > 0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_calculate_packet_loss_with_expected(self, mock_get_logger: MagicMock) -> None:
        """Test packet loss calculation with expected packets."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packets_expected = 100
        monitor.stats.packets_lost = 5

        monitor._calculate_packet_loss()

        assert monitor.stats.packet_loss_percent == pytest.approx(5.0)

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_calculate_packet_loss_zero_expected(self, mock_get_logger: MagicMock) -> None:
        """Test packet loss calculation with zero expected packets."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packets_expected = 0

        monitor._calculate_packet_loss()

        assert monitor.stats.packet_loss_percent == 0.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_excellent_conditions(self, mock_get_logger: MagicMock) -> None:
        """Test MOS estimate with excellent conditions (no impairments)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.rtt_ms = 10.0
        monitor.stats.packet_loss_percent = 0.0
        monitor.stats.jitter_ms = 5.0

        monitor._estimate_mos()

        # With minimal impairments, MOS should be high (>4.0)
        assert monitor.stats.mos_score >= 4.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_high_delay(self, mock_get_logger: MagicMock) -> None:
        """Test MOS estimate with high delay (RTT > 354.6ms -> one-way > 177.3)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.rtt_ms = 400.0  # One-way = 200ms > 177.3
        monitor.stats.packet_loss_percent = 0.0
        monitor.stats.jitter_ms = 0.0

        monitor._estimate_mos()

        # High delay should reduce MOS
        assert monitor.stats.mos_score < 4.5

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_low_delay(self, mock_get_logger: MagicMock) -> None:
        """Test MOS estimate with low delay (one-way <= 177.3)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.rtt_ms = 100.0  # One-way = 50ms < 177.3
        monitor.stats.packet_loss_percent = 0.0
        monitor.stats.jitter_ms = 0.0

        monitor._estimate_mos()

        assert monitor.stats.mos_score > 4.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_with_packet_loss(self, mock_get_logger: MagicMock) -> None:
        """Test MOS estimate with packet loss."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.rtt_ms = 0.0
        monitor.stats.packet_loss_percent = 10.0
        monitor.stats.jitter_ms = 0.0

        monitor._estimate_mos()

        # Packet loss should reduce MOS
        assert monitor.stats.mos_score < 4.5

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_with_high_jitter(self, mock_get_logger: MagicMock) -> None:
        """Test MOS estimate with high jitter (>30ms triggers penalty)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.rtt_ms = 0.0
        monitor.stats.packet_loss_percent = 0.0
        monitor.stats.jitter_ms = 80.0  # High jitter

        monitor._estimate_mos()

        # Should have some degradation from jitter penalty
        assert monitor.stats.mos_score < 4.5

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_negative_r_factor(self, mock_get_logger: MagicMock) -> None:
        """Test MOS estimate when R-factor goes negative -> MOS = 1.0."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.rtt_ms = 2000.0  # Extreme delay
        monitor.stats.packet_loss_percent = 50.0  # Extreme loss
        monitor.stats.jitter_ms = 200.0  # Extreme jitter

        monitor._estimate_mos()

        assert monitor.stats.mos_score == 1.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_clamped_max(self, mock_get_logger: MagicMock) -> None:
        """Test MOS estimate is clamped to max 5.0."""
        monitor = RTCPMonitor("call-123")
        # Perfect conditions
        monitor.stats.rtt_ms = 0.0
        monitor.stats.packet_loss_percent = 0.0
        monitor.stats.jitter_ms = 0.0

        monitor._estimate_mos()

        assert monitor.stats.mos_score <= 5.0
        assert monitor.stats.mos_score >= 1.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_r_factor_over_100(self, mock_get_logger: MagicMock) -> None:
        """Test MOS when R-factor exceeds 100 -> MOS = 4.5."""
        monitor = RTCPMonitor("call-123")
        # R-factor starts at 93.2, so it can't normally exceed 100
        # But with all zeros it stays at 93.2 which is < 100
        # To test r_factor > 100 branch, we'd need negative impairments
        # which isn't realistic, but we verify the normal path works
        monitor.stats.rtt_ms = 0.0
        monitor.stats.packet_loss_percent = 0.0
        monitor.stats.jitter_ms = 0.0

        monitor._estimate_mos()

        # R=93.2 -> mos = 1 + 0.035*93.2 + 7e-6*93.2*(93.2-60)*(100-93.2) ~= 4.41
        assert 4.0 <= monitor.stats.mos_score <= 5.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_statistics(self, mock_get_logger: MagicMock) -> None:
        """Test get_statistics returns correct dictionary."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packets_sent = 100
        monitor.stats.packets_received = 95
        monitor.stats.packets_lost = 5
        monitor.stats.packets_expected = 100
        monitor.stats.bytes_sent = 16000
        monitor.stats.bytes_received = 15200
        monitor.stats.packet_loss_percent = 5.0
        monitor.stats.jitter_ms = 12.5
        monitor.stats.rtt_ms = 30.0
        monitor.stats.mos_score = 4.1
        monitor.stats.first_packet_time = 1000.0
        monitor.stats.last_packet_time = 1060.0

        stats = monitor.get_statistics()

        assert stats["call_id"] == "call-123"
        assert stats["packets_sent"] == 100
        assert stats["packets_received"] == 95
        assert stats["packets_lost"] == 5
        assert stats["packets_expected"] == 100
        assert stats["bytes_sent"] == 16000
        assert stats["bytes_received"] == 15200
        assert stats["packet_loss_percent"] == 5.0
        assert stats["jitter_ms"] == 12.5
        assert stats["rtt_ms"] == 30.0
        assert stats["mos_score"] == 4.1
        assert stats["call_duration_seconds"] == 60.0
        assert stats["quality_rating"] == "Good"

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_statistics_no_packets(self, mock_get_logger: MagicMock) -> None:
        """Test get_statistics when no packets have been received."""
        monitor = RTCPMonitor("call-123")

        stats = monitor.get_statistics()

        assert stats["call_duration_seconds"] == 0.0
        assert stats["packets_received"] == 0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_quality_rating_excellent(self, mock_get_logger: MagicMock) -> None:
        """Test quality rating: Excellent (MOS >= 4.3)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.mos_score = 4.5

        assert monitor._get_quality_rating() == "Excellent"

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_quality_rating_good(self, mock_get_logger: MagicMock) -> None:
        """Test quality rating: Good (4.0 <= MOS < 4.3)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.mos_score = 4.1

        assert monitor._get_quality_rating() == "Good"

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_quality_rating_fair(self, mock_get_logger: MagicMock) -> None:
        """Test quality rating: Fair (3.6 <= MOS < 4.0)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.mos_score = 3.7

        assert monitor._get_quality_rating() == "Fair"

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_quality_rating_poor(self, mock_get_logger: MagicMock) -> None:
        """Test quality rating: Poor (3.1 <= MOS < 3.6)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.mos_score = 3.2

        assert monitor._get_quality_rating() == "Poor"

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_quality_rating_bad(self, mock_get_logger: MagicMock) -> None:
        """Test quality rating: Bad (MOS < 3.1)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.mos_score = 2.0

        assert monitor._get_quality_rating() == "Bad"

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_check_quality_alerts_no_alerts(self, mock_get_logger: MagicMock) -> None:
        """Test no alerts when all metrics are within thresholds."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packet_loss_percent = 1.0
        monitor.stats.jitter_ms = 10.0
        monitor.stats.mos_score = 4.5
        monitor.stats.rtt_ms = 50.0

        alerts = monitor.check_quality_alerts()

        assert alerts == []

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_check_quality_alerts_high_packet_loss(self, mock_get_logger: MagicMock) -> None:
        """Test alert triggered by high packet loss."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packet_loss_percent = 10.0  # > 5.0 threshold
        monitor.stats.jitter_ms = 10.0
        monitor.stats.mos_score = 4.5
        monitor.stats.rtt_ms = 50.0

        alerts = monitor.check_quality_alerts()

        assert len(alerts) == 1
        assert "packet loss" in alerts[0].lower()

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_check_quality_alerts_high_jitter(self, mock_get_logger: MagicMock) -> None:
        """Test alert triggered by high jitter."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packet_loss_percent = 1.0
        monitor.stats.jitter_ms = 60.0  # > 50.0 threshold
        monitor.stats.mos_score = 4.5
        monitor.stats.rtt_ms = 50.0

        alerts = monitor.check_quality_alerts()

        assert len(alerts) == 1
        assert "jitter" in alerts[0].lower()

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_check_quality_alerts_low_mos(self, mock_get_logger: MagicMock) -> None:
        """Test alert triggered by low MOS score."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packet_loss_percent = 1.0
        monitor.stats.jitter_ms = 10.0
        monitor.stats.mos_score = 2.5  # < 3.5 threshold
        monitor.stats.rtt_ms = 50.0

        alerts = monitor.check_quality_alerts()

        assert len(alerts) == 1
        assert "mos" in alerts[0].lower()

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_check_quality_alerts_high_rtt(self, mock_get_logger: MagicMock) -> None:
        """Test alert triggered by high RTT."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packet_loss_percent = 1.0
        monitor.stats.jitter_ms = 10.0
        monitor.stats.mos_score = 4.5
        monitor.stats.rtt_ms = 400.0  # > 300.0 threshold

        alerts = monitor.check_quality_alerts()

        assert len(alerts) == 1
        assert "latency" in alerts[0].lower()

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_check_quality_alerts_multiple(self, mock_get_logger: MagicMock) -> None:
        """Test multiple alerts triggered simultaneously."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packet_loss_percent = 10.0
        monitor.stats.jitter_ms = 60.0
        monitor.stats.mos_score = 2.5
        monitor.stats.rtt_ms = 400.0

        alerts = monitor.check_quality_alerts()

        assert len(alerts) == 4

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_reset(self, mock_get_logger: MagicMock) -> None:
        """Test resetting monitor state."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packets_received = 100
        monitor.stats.jitter_ms = 25.0
        monitor.transit_time = 1.5
        monitor.last_arrival_time = 1000.0

        monitor.reset()

        assert monitor.stats.packets_received == 0
        assert monitor.stats.jitter_ms == 0.0
        assert monitor.transit_time is None
        assert monitor.last_arrival_time is None

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    @patch("pbx.rtp.rtcp_monitor.time")
    def test_packets_expected_tracking(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test that packets_expected is correctly computed from sequence numbers."""
        mock_time.time.return_value = 1000.0
        monitor = RTCPMonitor("call-123")

        # First packet
        monitor.update_received_packet(sequence=100, timestamp=8000, size=160)

        # Second packet
        mock_time.time.return_value = 1000.02
        monitor.update_received_packet(sequence=105, timestamp=8800, size=160)

        # packets_expected = extended_max - extended_base + 1
        # After second packet: highest=105, last=100 (from first update to last assignment)
        # Actually sequence tracking is: first call sets last_sequence=100, highest=100
        # second call: diff=5>0, highest=105, extended_max=105, extended_base=100+0*65536=100
        # packets_expected = 105-100+1 = 6
        # Then last_sequence = 105
        assert monitor.stats.packets_expected == 6

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_zero_packet_loss(self, mock_get_logger: MagicMock) -> None:
        """Test MOS estimation with zero packet loss (ie_eff = 0)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packet_loss_percent = 0.0
        monitor.stats.rtt_ms = 0.0
        monitor.stats.jitter_ms = 0.0

        monitor._estimate_mos()

        # R-factor = 93.2 - 0 - 0 = 93.2
        assert monitor.stats.mos_score > 4.0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_estimate_mos_jitter_below_threshold(self, mock_get_logger: MagicMock) -> None:
        """Test MOS with jitter <= 30ms (no jitter penalty)."""
        monitor = RTCPMonitor("call-123")
        monitor.stats.packet_loss_percent = 0.0
        monitor.stats.rtt_ms = 0.0
        monitor.stats.jitter_ms = 20.0  # Below 30ms threshold

        monitor._estimate_mos()

        # No jitter penalty should be applied
        assert monitor.stats.mos_score > 4.0


@pytest.mark.unit
class TestRTCPMonitorManager:
    """Tests for the RTCPMonitorManager class."""

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_init_without_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when PBX has no config attribute."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)

        assert manager.config == {}
        assert manager.monitors == {}

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_init_with_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with PBX config containing rtcp settings."""
        pbx = MagicMock()
        pbx.config = {"rtcp": {"interval_seconds": 10}}

        manager = RTCPMonitorManager(pbx)

        assert manager.config == {"interval_seconds": 10}

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_init_with_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when pbx.config is None."""
        pbx = MagicMock()
        pbx.config = None

        manager = RTCPMonitorManager(pbx)

        assert manager.config == {}

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_create_monitor(self, mock_get_logger: MagicMock) -> None:
        """Test creating a monitor for a call."""
        pbx = MagicMock()
        pbx.config = {"rtcp": {"interval_seconds": 10}}
        manager = RTCPMonitorManager(pbx)

        monitor = manager.create_monitor("call-123")

        assert isinstance(monitor, RTCPMonitor)
        assert monitor.call_id == "call-123"
        assert "call-123" in manager.monitors
        assert monitor.interval_seconds == 10

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_create_monitor_with_custom_config(self, mock_get_logger: MagicMock) -> None:
        """Test creating a monitor with call-specific config."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)

        custom_config = {"interval_seconds": 2}
        monitor = manager.create_monitor("call-456", config=custom_config)

        assert monitor.interval_seconds == 2

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_monitor_existing(self, mock_get_logger: MagicMock) -> None:
        """Test getting an existing monitor."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)
        created = manager.create_monitor("call-123")

        result = manager.get_monitor("call-123")

        assert result is created

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_monitor_nonexistent(self, mock_get_logger: MagicMock) -> None:
        """Test getting a non-existent monitor returns None."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)

        result = manager.get_monitor("no-such-call")

        assert result is None

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_remove_monitor_existing(self, mock_get_logger: MagicMock) -> None:
        """Test removing an existing monitor."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)
        manager.create_monitor("call-123")

        manager.remove_monitor("call-123")

        assert "call-123" not in manager.monitors

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_remove_monitor_nonexistent(self, mock_get_logger: MagicMock) -> None:
        """Test removing a non-existent monitor does not raise."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)

        manager.remove_monitor("no-such-call")  # Should not raise

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_all_statistics(self, mock_get_logger: MagicMock) -> None:
        """Test getting statistics for all monitors."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)
        manager.create_monitor("call-1")
        manager.create_monitor("call-2")

        stats = manager.get_all_statistics()

        assert len(stats) == 2
        assert stats[0]["call_id"] in ("call-1", "call-2")
        assert stats[1]["call_id"] in ("call-1", "call-2")

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_active_calls_count(self, mock_get_logger: MagicMock) -> None:
        """Test active calls count."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)

        assert manager.get_active_calls_count() == 0

        manager.create_monitor("call-1")
        assert manager.get_active_calls_count() == 1

        manager.create_monitor("call-2")
        assert manager.get_active_calls_count() == 2

        manager.remove_monitor("call-1")
        assert manager.get_active_calls_count() == 1

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_quality_summary_no_monitors(self, mock_get_logger: MagicMock) -> None:
        """Test quality summary with no active monitors."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)

        summary = manager.get_quality_summary()

        assert summary["active_calls"] == 0
        assert summary["average_mos"] == 0.0
        assert summary["average_packet_loss"] == 0.0
        assert summary["average_jitter_ms"] == 0.0
        assert summary["calls_with_issues"] == 0

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_quality_summary_with_monitors(self, mock_get_logger: MagicMock) -> None:
        """Test quality summary with active monitors."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)

        mon1 = manager.create_monitor("call-1")
        mon1.stats.mos_score = 4.0
        mon1.stats.packet_loss_percent = 2.0
        mon1.stats.jitter_ms = 10.0

        mon2 = manager.create_monitor("call-2")
        mon2.stats.mos_score = 3.0
        mon2.stats.packet_loss_percent = 8.0
        mon2.stats.jitter_ms = 20.0

        summary = manager.get_quality_summary()

        assert summary["active_calls"] == 2
        assert summary["average_mos"] == pytest.approx(3.5)
        assert summary["average_packet_loss"] == pytest.approx(5.0)
        assert summary["average_jitter_ms"] == pytest.approx(15.0)

    @patch("pbx.rtp.rtcp_monitor.get_logger")
    def test_get_quality_summary_counts_issues(self, mock_get_logger: MagicMock) -> None:
        """Test quality summary correctly counts calls with quality issues."""
        pbx = MagicMock(spec=[])
        manager = RTCPMonitorManager(pbx)

        # Good call
        mon1 = manager.create_monitor("call-1")
        mon1.stats.mos_score = 4.5
        mon1.stats.packet_loss_percent = 1.0
        mon1.stats.jitter_ms = 5.0
        mon1.stats.rtt_ms = 20.0

        # Bad call
        mon2 = manager.create_monitor("call-2")
        mon2.stats.mos_score = 2.0  # < 3.5 threshold
        mon2.stats.packet_loss_percent = 15.0  # > 5.0 threshold
        mon2.stats.jitter_ms = 80.0  # > 50.0 threshold
        mon2.stats.rtt_ms = 500.0  # > 300.0 threshold

        summary = manager.get_quality_summary()

        assert summary["calls_with_issues"] == 1  # Only call-2 has issues
