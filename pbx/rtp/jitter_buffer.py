"""
Jitter Buffer Implementation
Based on FreeSWITCH STFU library and Asterisk jitter buffer

Handles variable packet arrival times to provide smooth audio playback.
Adapts buffer size based on network conditions.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from pbx.utils.logger import get_logger


class JitterBufferPacket:
    """Represents a packet in the jitter buffer."""

    def __init__(self, data: bytes, sequence: int, timestamp: int, arrival_time: float) -> None:
        """
        Initialize a jitter buffer packet.

        Args:
            data: Raw packet payload bytes.
            sequence: RTP sequence number.
            timestamp: RTP timestamp.
            arrival_time: Time the packet arrived (seconds since epoch).
        """
        self.data: bytes = data
        self.sequence: int = sequence
        self.timestamp: int = timestamp
        self.arrival_time: float = arrival_time
        self.size: int = len(data)


class JitterBuffer:
    """
    Adaptive jitter buffer for RTP packets.

    Smooths out variable packet arrival times caused by network jitter.
    Based on implementations from FreeSWITCH and Asterisk.

    Features:
    - Adaptive buffer sizing
    - Packet reordering
    - Packet loss detection
    - Late packet handling
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize jitter buffer.

        Args:
            config: Configuration dictionary with:
                - initial_length_ms: Initial buffer length (default: 50ms)
                - max_length_ms: Maximum buffer length (default: 200ms)
                - max_drift_ms: Maximum drift tolerance (default: 30ms)
                - adaptive: Enable adaptive mode (default: True)
        """
        self.logger = get_logger()
        self.config: dict[str, Any] = config or {}

        # Configuration parameters
        self.initial_length_ms: int = self.config.get("initial_length_ms", 50)
        self.max_length_ms: int = self.config.get("max_length_ms", 200)
        self.max_drift_ms: int = self.config.get("max_drift_ms", 30)
        self.adaptive: bool = self.config.get("adaptive", True)

        # Buffer state
        self.buffer: deque[JitterBufferPacket] = deque()
        self.lock: threading.Lock = threading.Lock()

        # Packet tracking
        self.last_sequence: int | None = None
        self.last_timestamp: int | None = None
        self.packets_received: int = 0
        self.packets_dropped: int = 0
        self.packets_late: int = 0
        self.packets_lost: int = 0

        # Timing
        self.start_time: float | None = None
        self.current_length_ms: float = self.initial_length_ms

        # Statistics for adaptive behavior
        self.jitter_estimate: float = 0.0
        self.last_arrival_time: float | None = None
        self.transit_time_variance: float = 0.0

        self.logger.info(
            "Jitter buffer initialized: "
            f"initial={self.initial_length_ms}ms, "
            f"max={self.max_length_ms}ms, "
            f"adaptive={self.adaptive}"
        )

    def put(self, data: bytes, sequence: int, timestamp: int) -> bool:
        """
        Add packet to jitter buffer

        Args:
            data: Packet payload
            sequence: RTP sequence number
            timestamp: RTP timestamp

        Returns:
            bool: True if packet accepted, False if dropped
        """
        with self.lock:
            arrival_time = time.time()

            # Track first packet
            if self.start_time is None:
                self.start_time = arrival_time

            # Create packet
            packet = JitterBufferPacket(data, sequence, timestamp, arrival_time)

            # Check if packet is too late
            if self.last_sequence is not None:
                seq_diff = self._sequence_diff(sequence, self.last_sequence)

                if seq_diff < -10:  # Very old packet
                    self.packets_late += 1
                    self.logger.debug(
                        f"Dropping late packet: seq={sequence}, last_seq={self.last_sequence}"
                    )
                    return False

            # Update statistics
            self._update_statistics(packet)

            # Insert packet in order
            self._insert_ordered(packet)

            self.packets_received += 1
            return True

    def get(self) -> bytes | None:
        """
        Get next packet from jitter buffer

        Returns:
            bytes: Packet data, or None if buffer empty or not ready
        """
        with self.lock:
            if len(self.buffer) == 0:
                return None

            # Check if enough time has elapsed to start playback
            if self.start_time is not None:
                elapsed_ms = (time.time() - self.start_time) * 1000

                if elapsed_ms < self.current_length_ms:
                    # Not enough buffered yet
                    return None

            # Get oldest packet
            packet = self.buffer.popleft()

            # Update last timestamp for gap detection
            self.last_timestamp = packet.timestamp
            self.last_sequence = packet.sequence

            return packet.data

    def _insert_ordered(self, packet: JitterBufferPacket) -> None:
        """Insert packet in sequence order."""
        # If buffer empty, just append
        if len(self.buffer) == 0:
            self.buffer.append(packet)
            return

        # Find insertion point
        inserted = False
        for i, buf_packet in enumerate(self.buffer):
            if self._sequence_diff(packet.sequence, buf_packet.sequence) < 0:
                # Insert before this packet
                self.buffer.insert(i, packet)
                inserted = True
                break

        if not inserted:
            # Append at end
            self.buffer.append(packet)

    def _sequence_diff(self, seq1: int, seq2: int) -> int:
        """
        Calculate difference between sequence numbers, handling wraparound

        Returns positive if seq1 > seq2, negative if seq1 < seq2
        """
        diff = seq1 - seq2

        # Handle 16-bit wraparound
        if diff > 32768:
            diff -= 65536
        elif diff < -32768:
            diff += 65536

        return diff

    def _update_statistics(self, packet: JitterBufferPacket) -> None:
        """Update jitter and timing statistics."""
        if self.last_arrival_time is None:
            self.last_arrival_time = packet.arrival_time
            return

        # Calculate inter-arrival jitter (RFC 3550)
        arrival_diff = packet.arrival_time - self.last_arrival_time

        # Expected time based on timestamp (assuming 8kHz sample rate)
        if self.last_timestamp is not None:
            timestamp_diff = abs(packet.timestamp - self.last_timestamp)
            expected_time = timestamp_diff / 8000.0  # Convert to seconds

            # Transit time difference
            transit_diff = abs(arrival_diff - expected_time)

            # Update jitter estimate (RFC 3550 algorithm)
            # J(i) = J(i-1) + (|D(i-1,i)| - J(i-1))/16
            self.jitter_estimate += (transit_diff - self.jitter_estimate) / 16.0

            # Adapt buffer size if enabled
            if self.adaptive:
                self._adapt_buffer_size()

        self.last_arrival_time = packet.arrival_time

    def _adapt_buffer_size(self) -> None:
        """Adapt buffer size based on jitter."""
        # Calculate target buffer size based on jitter
        # Use 3x jitter as buffer size (allows for variance)
        target_ms = self.jitter_estimate * 1000 * 3

        # Add initial length as baseline
        target_ms += self.initial_length_ms

        # Clamp to limits
        target_ms = max(self.initial_length_ms, target_ms)
        target_ms = min(self.max_length_ms, target_ms)

        # Smooth transition (move 10% toward target each update)
        self.current_length_ms += (target_ms - self.current_length_ms) * 0.1

        self.logger.debug(
            f"Adaptive jitter buffer: jitter={self.jitter_estimate * 1000:.1f}ms, "
            f"buffer={self.current_length_ms:.1f}ms"
        )

    def get_statistics(self) -> dict[str, Any]:
        """
        Get jitter buffer statistics

        Returns:
            dict: Statistics including packets received, dropped, jitter, etc.
        """
        with self.lock:
            return {
                "packets_received": self.packets_received,
                "packets_dropped": self.packets_dropped,
                "packets_late": self.packets_late,
                "packets_lost": self.packets_lost,
                "packets_buffered": len(self.buffer),
                "jitter_ms": self.jitter_estimate * 1000,
                "current_length_ms": self.current_length_ms,
                "initial_length_ms": self.initial_length_ms,
                "max_length_ms": self.max_length_ms,
                "adaptive": self.adaptive,
            }

    def reset(self) -> None:
        """Reset jitter buffer state."""
        with self.lock:
            self.buffer.clear()
            self.last_sequence = None
            self.last_timestamp = None
            self.packets_received = 0
            self.packets_dropped = 0
            self.packets_late = 0
            self.packets_lost = 0
            self.start_time = None
            self.current_length_ms = self.initial_length_ms
            self.jitter_estimate = 0.0
            self.last_arrival_time = None

            self.logger.info("Jitter buffer reset")

    def flush(self) -> list[bytes]:
        """
        Flush all packets from buffer

        Returns:
            list: All buffered packets in order
        """
        with self.lock:
            packets = [p.data for p in self.buffer]
            self.buffer.clear()
            return packets

    def set_length(self, length_ms: int) -> None:
        """
        set buffer length manually (disables adaptive mode)

        Args:
            length_ms: Buffer length in milliseconds
        """
        with self.lock:
            self.current_length_ms = max(self.initial_length_ms, min(self.max_length_ms, length_ms))
            self.adaptive = False

            self.logger.info(f"Jitter buffer length set to {self.current_length_ms}ms")


class JitterBufferManager:
    """Manager for multiple jitter buffers (one per call)."""

    def __init__(self, pbx: Any) -> None:
        """
        Initialize jitter buffer manager.

        Args:
            pbx: PBX instance.
        """
        self.pbx = pbx
        self.logger = get_logger()
        self.buffers: dict[str, JitterBuffer] = {}

        # Get global config
        self.config: dict[str, Any] = {}
        if hasattr(pbx, "config") and pbx.config:
            rtp_config = pbx.config.get("rtp", {})
            self.config = rtp_config.get("jitter_buffer", {})

        self.logger.info("Jitter buffer manager initialized")

    def create_buffer(self, call_id: str, config: dict[str, Any] | None = None) -> JitterBuffer:
        """
        Create jitter buffer for a call

        Args:
            call_id: Unique call identifier
            config: Optional buffer configuration (uses global config if not provided)

        Returns:
            JitterBuffer instance
        """
        # Use provided config or global config
        buffer_config = config or self.config

        # Create buffer
        buffer = JitterBuffer(buffer_config)
        self.buffers[call_id] = buffer

        self.logger.debug(f"Created jitter buffer for call {call_id}")
        return buffer

    def get_buffer(self, call_id: str) -> JitterBuffer | None:
        """
        Get jitter buffer for a call

        Args:
            call_id: Call identifier

        Returns:
            JitterBuffer instance or None
        """
        return self.buffers.get(call_id)

    def remove_buffer(self, call_id: str) -> None:
        """
        Remove jitter buffer for a call.

        Args:
            call_id: Call identifier.
        """
        if call_id in self.buffers:
            del self.buffers[call_id]
            self.logger.debug(f"Removed jitter buffer for call {call_id}")

    def get_all_buffers(self) -> dict[str, JitterBuffer]:
        """
        Get all jitter buffer instances

        Returns:
            dict mapping call_id to JitterBuffer
        """
        return self.buffers.copy()

    def get_statistics(self, call_id: str | None = None) -> dict[str, Any]:
        """
        Get statistics for one or all jitter buffers

        Args:
            call_id: Optional call ID (if None, returns stats for all)

        Returns:
            dict: Statistics
        """
        if call_id:
            buffer = self.buffers.get(call_id)
            if buffer:
                return {call_id: buffer.get_statistics()}
            return {}
        return {cid: buf.get_statistics() for cid, buf in self.buffers.items()}
