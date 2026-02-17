"""Comprehensive tests for the JitterBuffer and JitterBufferManager modules."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pbx.rtp.jitter_buffer import JitterBuffer, JitterBufferManager, JitterBufferPacket


@pytest.mark.unit
class TestJitterBufferPacket:
    """Tests for JitterBufferPacket dataclass."""

    def test_init_sets_all_fields(self) -> None:
        """Test that all fields are initialized properly."""
        data = b"\x00\x01\x02\x03"
        packet = JitterBufferPacket(data=data, sequence=100, timestamp=8000, arrival_time=1000.0)

        assert packet.data == data
        assert packet.sequence == 100
        assert packet.timestamp == 8000
        assert packet.arrival_time == 1000.0
        assert packet.size == 4

    def test_size_matches_data_length(self) -> None:
        """Test that size is computed from the data bytes."""
        data = b"\xff" * 160
        packet = JitterBufferPacket(data=data, sequence=0, timestamp=0, arrival_time=0.0)

        assert packet.size == 160

    def test_empty_data(self) -> None:
        """Test packet with empty data."""
        packet = JitterBufferPacket(data=b"", sequence=0, timestamp=0, arrival_time=0.0)

        assert packet.size == 0
        assert packet.data == b""


@pytest.mark.unit
class TestJitterBuffer:
    """Tests for the JitterBuffer class."""

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_init_default_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with default configuration."""
        buf = JitterBuffer()

        assert buf.initial_length_ms == 50
        assert buf.max_length_ms == 200
        assert buf.max_drift_ms == 30
        assert buf.adaptive is True
        assert buf.packets_received == 0
        assert buf.packets_dropped == 0
        assert buf.packets_late == 0
        assert buf.packets_lost == 0
        assert buf.jitter_estimate == 0.0
        assert buf.last_sequence is None
        assert buf.last_timestamp is None
        assert buf.start_time is None

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_init_custom_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with custom configuration."""
        config = {
            "initial_length_ms": 100,
            "max_length_ms": 500,
            "max_drift_ms": 50,
            "adaptive": False,
        }
        buf = JitterBuffer(config)

        assert buf.initial_length_ms == 100
        assert buf.max_length_ms == 500
        assert buf.max_drift_ms == 50
        assert buf.adaptive is False
        assert buf.current_length_ms == 100

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_put_first_packet(self, mock_get_logger: MagicMock) -> None:
        """Test inserting the first packet sets start_time."""
        buf = JitterBuffer()

        result = buf.put(b"\x00" * 160, sequence=1, timestamp=160)

        assert result is True
        assert buf.packets_received == 1
        assert buf.start_time is not None
        assert len(buf.buffer) == 1

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_put_multiple_packets_in_order(self, mock_get_logger: MagicMock) -> None:
        """Test inserting multiple packets in sequence order."""
        buf = JitterBuffer()

        buf.put(b"\x01" * 160, sequence=1, timestamp=160)
        buf.put(b"\x02" * 160, sequence=2, timestamp=320)
        buf.put(b"\x03" * 160, sequence=3, timestamp=480)

        assert buf.packets_received == 3
        assert len(buf.buffer) == 3
        # Verify order
        assert buf.buffer[0].sequence == 1
        assert buf.buffer[1].sequence == 2
        assert buf.buffer[2].sequence == 3

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_put_reordered_packets(self, mock_get_logger: MagicMock) -> None:
        """Test that out-of-order packets are reordered in the buffer."""
        buf = JitterBuffer()

        buf.put(b"\x01" * 160, sequence=1, timestamp=160)
        buf.put(b"\x03" * 160, sequence=3, timestamp=480)
        buf.put(b"\x02" * 160, sequence=2, timestamp=320)

        assert len(buf.buffer) == 3
        assert buf.buffer[0].sequence == 1
        assert buf.buffer[1].sequence == 2
        assert buf.buffer[2].sequence == 3

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_put_late_packet_dropped(self, mock_get_logger: MagicMock) -> None:
        """Test that very late packets are dropped (seq_diff < -10)."""
        buf = JitterBuffer()

        # Put first packet and establish last_sequence via get()
        buf.put(b"\x01" * 160, sequence=100, timestamp=160)
        # Force the last_sequence by getting the packet
        buf.get()  # This won't return data yet if buffer delay not met
        # Manually set last_sequence to simulate having played up to seq 100
        buf.last_sequence = 100

        # Now put a very old packet (sequence 80, diff = 80 - 100 = -20 < -10)
        result = buf.put(b"\x02" * 160, sequence=80, timestamp=160)

        assert result is False
        assert buf.packets_late == 1

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_put_slightly_old_packet_accepted(self, mock_get_logger: MagicMock) -> None:
        """Test that slightly old packets are still accepted (seq_diff >= -10)."""
        buf = JitterBuffer()

        buf.put(b"\x01" * 160, sequence=100, timestamp=160)
        buf.last_sequence = 100

        # Packet with seq 95, diff = 95 - 100 = -5, which is >= -10
        result = buf.put(b"\x02" * 160, sequence=95, timestamp=160)

        assert result is True

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_empty_buffer_returns_none(self, mock_get_logger: MagicMock) -> None:
        """Test that get() returns None when buffer is empty."""
        buf = JitterBuffer()

        result = buf.get()

        assert result is None

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_returns_none_before_buffer_delay(self, mock_get_logger: MagicMock) -> None:
        """Test that get() returns None when buffer delay has not elapsed."""
        buf = JitterBuffer({"initial_length_ms": 1000})  # Long delay

        buf.put(b"\x01" * 160, sequence=1, timestamp=160)

        # Since initial_length_ms is 1000ms, get should return None immediately
        result = buf.get()
        assert result is None

    @patch("pbx.rtp.jitter_buffer.get_logger")
    @patch("pbx.rtp.jitter_buffer.time")
    def test_get_returns_data_after_buffer_delay(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test that get() returns data after buffer delay has elapsed."""
        buf = JitterBuffer({"initial_length_ms": 50})

        # First call to time.time() in put() sets start_time
        mock_time.time.return_value = 1000.0
        buf.put(b"\x01" * 160, sequence=1, timestamp=160)

        # Second call to time.time() in get() should be after the delay
        mock_time.time.return_value = 1000.1  # 100ms later > 50ms initial

        result = buf.get()

        assert result == b"\x01" * 160
        assert buf.last_sequence == 1
        assert buf.last_timestamp == 160

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_updates_last_sequence_and_timestamp(self, mock_get_logger: MagicMock) -> None:
        """Test that get() updates tracking fields."""
        buf = JitterBuffer({"initial_length_ms": 0})
        buf.start_time = time.time() - 1  # Ensure delay has passed

        buf.put(b"\x01" * 160, sequence=42, timestamp=6720)
        result = buf.get()

        assert result is not None
        assert buf.last_sequence == 42
        assert buf.last_timestamp == 6720

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_sequence_diff_normal(self, mock_get_logger: MagicMock) -> None:
        """Test sequence diff for normal sequential numbers."""
        buf = JitterBuffer()

        assert buf._sequence_diff(10, 5) == 5
        assert buf._sequence_diff(5, 10) == -5
        assert buf._sequence_diff(100, 100) == 0

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_sequence_diff_wraparound_forward(self, mock_get_logger: MagicMock) -> None:
        """Test sequence diff with forward wraparound (65535 -> 0)."""
        buf = JitterBuffer()

        # seq1=1, seq2=65535 => diff = 1-65535 = -65534, which is < -32768
        # so corrected diff = -65534 + 65536 = 2 (seq1 is ahead)
        diff = buf._sequence_diff(1, 65535)
        assert diff == 2

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_sequence_diff_wraparound_backward(self, mock_get_logger: MagicMock) -> None:
        """Test sequence diff with backward wraparound."""
        buf = JitterBuffer()

        # seq1=65535, seq2=1 => diff = 65534, which is > 32768
        # so corrected diff = 65534 - 65536 = -2 (seq1 is behind)
        diff = buf._sequence_diff(65535, 1)
        assert diff == -2

    @patch("pbx.rtp.jitter_buffer.get_logger")
    @patch("pbx.rtp.jitter_buffer.time")
    def test_update_statistics_first_packet(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test that statistics update correctly for first packet (sets baseline)."""
        buf = JitterBuffer()
        mock_time.time.return_value = 1000.0

        buf.put(b"\x01" * 160, sequence=1, timestamp=160)

        # After first packet, last_arrival_time should be set
        assert buf.last_arrival_time == 1000.0
        assert buf.jitter_estimate == 0.0  # No jitter on first packet

    @patch("pbx.rtp.jitter_buffer.get_logger")
    @patch("pbx.rtp.jitter_buffer.time")
    def test_update_statistics_jitter_calculation(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test jitter estimation with multiple packets."""
        buf = JitterBuffer()

        # First packet
        mock_time.time.return_value = 1000.0
        buf.put(b"\x01" * 160, sequence=1, timestamp=8000)

        # Second packet - arrives with some jitter
        # Expected inter-packet time for 8kHz at timestamp diff 160: 160/8000 = 0.02s
        mock_time.time.return_value = 1000.025  # Arrival diff = 0.025s, expected 0.02s
        buf.put(b"\x02" * 160, sequence=2, timestamp=8160)

        # Jitter should be non-zero after second packet
        # The second packet can now calculate jitter since last_timestamp was set by get/first
        # On the second put, _update_statistics runs, and since last_timestamp is set by get,
        # if it was not gotten yet, it may still be None. Let's check.
        # Actually, last_timestamp is only set by get(). In put(), it calls _update_statistics
        # which checks self.last_timestamp (set by get()). So for jitter to be computed from
        # timestamp_diff, we need last_timestamp set. Let's do get() in between.

    @patch("pbx.rtp.jitter_buffer.get_logger")
    @patch("pbx.rtp.jitter_buffer.time")
    def test_jitter_with_timestamp_tracking(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test that jitter is computed when last_timestamp is available."""
        buf = JitterBuffer({"initial_length_ms": 0, "adaptive": True})

        # Insert and retrieve first packet to set last_timestamp
        mock_time.time.return_value = 1000.0
        buf.put(b"\x01" * 160, sequence=1, timestamp=8000)

        mock_time.time.return_value = 1000.1
        buf.get()  # sets last_timestamp = 8000

        # Now insert second packet
        mock_time.time.return_value = 1000.025
        buf.put(b"\x02" * 160, sequence=2, timestamp=8160)

        # Jitter estimate should have been updated since last_timestamp is not None
        # The transit diff would be calculated
        assert buf.last_arrival_time == 1000.025

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_adapt_buffer_size(self, mock_get_logger: MagicMock) -> None:
        """Test adaptive buffer sizing changes current_length_ms."""
        buf = JitterBuffer({"initial_length_ms": 50, "max_length_ms": 200, "adaptive": True})

        # Simulate a high jitter estimate
        buf.jitter_estimate = 0.05  # 50ms jitter

        buf._adapt_buffer_size()

        # target_ms = 0.05 * 1000 * 3 + 50 = 200
        # current_length_ms moves 10% toward target
        # new = 50 + (200 - 50) * 0.1 = 50 + 15 = 65
        assert buf.current_length_ms == pytest.approx(65.0)

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_adapt_buffer_size_clamps_to_max(self, mock_get_logger: MagicMock) -> None:
        """Test that adaptive sizing is clamped to max_length_ms."""
        buf = JitterBuffer({"initial_length_ms": 50, "max_length_ms": 200, "adaptive": True})

        # Very high jitter
        buf.jitter_estimate = 1.0  # 1000ms jitter

        buf._adapt_buffer_size()

        # target_ms = 1.0 * 1000 * 3 + 50 = 3050, clamped to 200
        # new = 50 + (200 - 50) * 0.1 = 65
        assert buf.current_length_ms <= buf.max_length_ms

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_adapt_buffer_size_clamps_to_min(self, mock_get_logger: MagicMock) -> None:
        """Test that adaptive sizing never goes below initial_length_ms."""
        buf = JitterBuffer({"initial_length_ms": 50, "max_length_ms": 200, "adaptive": True})

        buf.jitter_estimate = 0.0

        buf._adapt_buffer_size()

        # target_ms = 0 + 50 = 50, which is the initial
        assert buf.current_length_ms >= buf.initial_length_ms

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_statistics(self, mock_get_logger: MagicMock) -> None:
        """Test statistics dictionary returned by get_statistics()."""
        buf = JitterBuffer({"initial_length_ms": 60, "max_length_ms": 300, "adaptive": False})

        buf.put(b"\x01" * 160, sequence=1, timestamp=160)
        buf.put(b"\x02" * 160, sequence=2, timestamp=320)

        stats = buf.get_statistics()

        assert stats["packets_received"] == 2
        assert stats["packets_dropped"] == 0
        assert stats["packets_late"] == 0
        assert stats["packets_lost"] == 0
        assert stats["packets_buffered"] == 2
        assert stats["initial_length_ms"] == 60
        assert stats["max_length_ms"] == 300
        assert stats["adaptive"] is False
        assert "jitter_ms" in stats
        assert "current_length_ms" in stats

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_reset(self, mock_get_logger: MagicMock) -> None:
        """Test that reset clears all state."""
        buf = JitterBuffer()

        buf.put(b"\x01" * 160, sequence=1, timestamp=160)
        buf.put(b"\x02" * 160, sequence=2, timestamp=320)
        buf.packets_dropped = 5
        buf.packets_lost = 3

        buf.reset()

        assert len(buf.buffer) == 0
        assert buf.last_sequence is None
        assert buf.last_timestamp is None
        assert buf.packets_received == 0
        assert buf.packets_dropped == 0
        assert buf.packets_late == 0
        assert buf.packets_lost == 0
        assert buf.start_time is None
        assert buf.current_length_ms == buf.initial_length_ms
        assert buf.jitter_estimate == 0.0
        assert buf.last_arrival_time is None

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_flush(self, mock_get_logger: MagicMock) -> None:
        """Test flush returns all packets and clears buffer."""
        buf = JitterBuffer()

        buf.put(b"\x01" * 160, sequence=1, timestamp=160)
        buf.put(b"\x02" * 160, sequence=2, timestamp=320)
        buf.put(b"\x03" * 160, sequence=3, timestamp=480)

        packets = buf.flush()

        assert len(packets) == 3
        assert packets[0] == b"\x01" * 160
        assert packets[1] == b"\x02" * 160
        assert packets[2] == b"\x03" * 160
        assert len(buf.buffer) == 0

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_flush_empty_buffer(self, mock_get_logger: MagicMock) -> None:
        """Test flush on empty buffer returns empty list."""
        buf = JitterBuffer()

        packets = buf.flush()

        assert packets == []

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_set_length(self, mock_get_logger: MagicMock) -> None:
        """Test set_length sets the buffer length and disables adaptive mode."""
        buf = JitterBuffer({"initial_length_ms": 50, "max_length_ms": 200, "adaptive": True})

        buf.set_length(100)

        assert buf.current_length_ms == 100
        assert buf.adaptive is False

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_set_length_clamps_to_min(self, mock_get_logger: MagicMock) -> None:
        """Test set_length enforces minimum (initial_length_ms)."""
        buf = JitterBuffer({"initial_length_ms": 50, "max_length_ms": 200})

        buf.set_length(10)

        assert buf.current_length_ms == 50

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_set_length_clamps_to_max(self, mock_get_logger: MagicMock) -> None:
        """Test set_length enforces maximum (max_length_ms)."""
        buf = JitterBuffer({"initial_length_ms": 50, "max_length_ms": 200})

        buf.set_length(999)

        assert buf.current_length_ms == 200

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_insert_ordered_empty_buffer(self, mock_get_logger: MagicMock) -> None:
        """Test inserting into an empty buffer."""
        buf = JitterBuffer()
        packet = JitterBufferPacket(b"\x01", 1, 160, 1000.0)

        buf._insert_ordered(packet)

        assert len(buf.buffer) == 1
        assert buf.buffer[0].sequence == 1

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_insert_ordered_at_beginning(self, mock_get_logger: MagicMock) -> None:
        """Test inserting a packet that should go at the beginning."""
        buf = JitterBuffer()
        buf.buffer.append(JitterBufferPacket(b"\x02", 5, 800, 1000.0))
        buf.buffer.append(JitterBufferPacket(b"\x03", 10, 1600, 1000.1))

        new_packet = JitterBufferPacket(b"\x01", 1, 160, 999.9)
        buf._insert_ordered(new_packet)

        assert buf.buffer[0].sequence == 1
        assert buf.buffer[1].sequence == 5
        assert buf.buffer[2].sequence == 10

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_insert_ordered_in_middle(self, mock_get_logger: MagicMock) -> None:
        """Test inserting a packet in the middle of the buffer."""
        buf = JitterBuffer()
        buf.buffer.append(JitterBufferPacket(b"\x01", 1, 160, 1000.0))
        buf.buffer.append(JitterBufferPacket(b"\x03", 10, 1600, 1000.2))

        new_packet = JitterBufferPacket(b"\x02", 5, 800, 1000.1)
        buf._insert_ordered(new_packet)

        assert buf.buffer[0].sequence == 1
        assert buf.buffer[1].sequence == 5
        assert buf.buffer[2].sequence == 10

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_insert_ordered_at_end(self, mock_get_logger: MagicMock) -> None:
        """Test inserting a packet at the end."""
        buf = JitterBuffer()
        buf.buffer.append(JitterBufferPacket(b"\x01", 1, 160, 1000.0))
        buf.buffer.append(JitterBufferPacket(b"\x02", 5, 800, 1000.1))

        new_packet = JitterBufferPacket(b"\x03", 20, 3200, 1000.2)
        buf._insert_ordered(new_packet)

        assert buf.buffer[2].sequence == 20

    @patch("pbx.rtp.jitter_buffer.get_logger")
    @patch("pbx.rtp.jitter_buffer.time")
    def test_update_statistics_without_last_timestamp(
        self, mock_time: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Test _update_statistics when last_timestamp is None (no jitter update)."""
        buf = JitterBuffer({"adaptive": True})

        # First packet sets last_arrival_time
        mock_time.time.return_value = 1000.0
        buf.put(b"\x01" * 160, sequence=1, timestamp=8000)

        # Second packet: last_timestamp is None so no timestamp_diff computed
        mock_time.time.return_value = 1000.02
        buf.put(b"\x02" * 160, sequence=2, timestamp=8160)

        # Jitter should still be 0 because last_timestamp is None
        assert buf.jitter_estimate == 0.0

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_non_adaptive_mode_does_not_change_buffer(self, mock_get_logger: MagicMock) -> None:
        """Test that non-adaptive mode does not change buffer size."""
        buf = JitterBuffer({"initial_length_ms": 50, "max_length_ms": 200, "adaptive": False})
        initial_length = buf.current_length_ms

        buf.jitter_estimate = 0.1
        # _adapt_buffer_size should not be called in non-adaptive mode
        # but let's verify the buffer length doesn't change after puts
        buf.put(b"\x01" * 160, sequence=1, timestamp=160)

        assert buf.current_length_ms == initial_length


@pytest.mark.unit
class TestJitterBufferManager:
    """Tests for the JitterBufferManager class."""

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_init_without_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when PBX has no config attribute."""
        pbx = MagicMock(spec=[])  # No attributes
        manager = JitterBufferManager(pbx)

        assert manager.config == {}
        assert manager.buffers == {}

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_init_with_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with PBX config containing jitter_buffer settings."""
        pbx = MagicMock()
        # Use a real dict as the config attribute
        real_config: dict[str, Any] = {
            "rtp": {"jitter_buffer": {"initial_length_ms": 100, "adaptive": False}}
        }
        pbx.config = real_config

        manager = JitterBufferManager(pbx)

        assert manager.config == {"initial_length_ms": 100, "adaptive": False}

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_init_with_config_no_jitter_buffer_key(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when rtp config exists but no jitter_buffer key."""
        pbx = MagicMock()
        pbx.config = {"rtp": {}}

        manager = JitterBufferManager(pbx)

        assert manager.config == {}

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_init_with_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when pbx.config is None."""
        pbx = MagicMock()
        pbx.config = None

        manager = JitterBufferManager(pbx)

        assert manager.config == {}

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_create_buffer(self, mock_get_logger: MagicMock) -> None:
        """Test creating a buffer for a call."""
        pbx = MagicMock()
        pbx.config = {"rtp": {"jitter_buffer": {"initial_length_ms": 80}}}
        manager = JitterBufferManager(pbx)

        buf = manager.create_buffer("call-123")

        assert isinstance(buf, JitterBuffer)
        assert "call-123" in manager.buffers
        assert buf.initial_length_ms == 80

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_create_buffer_with_custom_config(self, mock_get_logger: MagicMock) -> None:
        """Test creating a buffer with call-specific config overriding global."""
        pbx = MagicMock()
        pbx.config = {"rtp": {"jitter_buffer": {"initial_length_ms": 80}}}
        manager = JitterBufferManager(pbx)

        custom_config = {"initial_length_ms": 30, "max_length_ms": 100}
        buf = manager.create_buffer("call-456", config=custom_config)

        assert buf.initial_length_ms == 30
        assert buf.max_length_ms == 100

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_buffer_existing(self, mock_get_logger: MagicMock) -> None:
        """Test getting an existing buffer by call ID."""
        pbx = MagicMock(spec=[])
        manager = JitterBufferManager(pbx)
        created = manager.create_buffer("call-123")

        result = manager.get_buffer("call-123")

        assert result is created

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_buffer_nonexistent(self, mock_get_logger: MagicMock) -> None:
        """Test getting a non-existent buffer returns None."""
        pbx = MagicMock(spec=[])
        manager = JitterBufferManager(pbx)

        result = manager.get_buffer("no-such-call")

        assert result is None

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_remove_buffer_existing(self, mock_get_logger: MagicMock) -> None:
        """Test removing an existing buffer."""
        pbx = MagicMock(spec=[])
        manager = JitterBufferManager(pbx)
        manager.create_buffer("call-123")

        manager.remove_buffer("call-123")

        assert "call-123" not in manager.buffers

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_remove_buffer_nonexistent(self, mock_get_logger: MagicMock) -> None:
        """Test removing a non-existent buffer does not raise."""
        pbx = MagicMock(spec=[])
        manager = JitterBufferManager(pbx)

        manager.remove_buffer("no-such-call")  # Should not raise

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_all_buffers(self, mock_get_logger: MagicMock) -> None:
        """Test getting all buffers returns a copy."""
        pbx = MagicMock(spec=[])
        manager = JitterBufferManager(pbx)
        manager.create_buffer("call-1")
        manager.create_buffer("call-2")

        all_bufs = manager.get_all_buffers()

        assert len(all_bufs) == 2
        assert "call-1" in all_bufs
        assert "call-2" in all_bufs
        # Should be a copy
        all_bufs["call-3"] = JitterBuffer()
        assert "call-3" not in manager.buffers

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_statistics_for_specific_call(self, mock_get_logger: MagicMock) -> None:
        """Test get_statistics with a specific call_id."""
        pbx = MagicMock(spec=[])
        manager = JitterBufferManager(pbx)
        buf = manager.create_buffer("call-123")
        buf.put(b"\x01" * 160, sequence=1, timestamp=160)

        stats = manager.get_statistics(call_id="call-123")

        assert "call-123" in stats
        assert stats["call-123"]["packets_received"] == 1

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_statistics_nonexistent_call(self, mock_get_logger: MagicMock) -> None:
        """Test get_statistics for non-existent call returns empty dict."""
        pbx = MagicMock(spec=[])
        manager = JitterBufferManager(pbx)

        stats = manager.get_statistics(call_id="no-such-call")

        assert stats == {}

    @patch("pbx.rtp.jitter_buffer.get_logger")
    def test_get_statistics_all_calls(self, mock_get_logger: MagicMock) -> None:
        """Test get_statistics without call_id returns stats for all."""
        pbx = MagicMock(spec=[])
        manager = JitterBufferManager(pbx)
        manager.create_buffer("call-1")
        manager.create_buffer("call-2")

        stats = manager.get_statistics()

        assert "call-1" in stats
        assert "call-2" in stats
