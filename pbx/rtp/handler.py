"""
RTP Media Handler
Handles real-time audio/video streaming
"""

from __future__ import annotations

import socket
import struct
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pbx.utils.audio import (
    WAV_FORMAT_ALAW,
    WAV_FORMAT_G722,
    WAV_FORMAT_PCM,
    WAV_FORMAT_ULAW,
)
from pbx.utils.logger import get_logger

if TYPE_CHECKING:
    from pbx.features.qos_monitoring import QoSMetrics, QoSMonitor
    from pbx.rtp.rfc2833 import RFC2833Receiver

# Type alias for network address tuples
type AddrTuple = tuple[str, int]


class RTPHandler:
    """Handle RTP media streams."""

    def __init__(
        self,
        local_port: int,
        remote_host: str | None = None,
        remote_port: int | None = None,
    ) -> None:
        """
        Initialize RTP handler.

        Args:
            local_port: Local port to bind to.
            remote_host: Remote host to send to.
            remote_port: Remote port to send to.
        """
        self.local_port: int = local_port
        self.remote_host: str | None = remote_host
        self.remote_port: int | None = remote_port
        self.logger = get_logger()
        self.socket: socket.socket | None = None
        self.running: bool = False
        self.sequence_number: int = 0
        self.timestamp: int = 0
        self.ssrc: int = 0x12345678  # Synchronization source identifier

    def start(self) -> bool:
        """
        Start RTP handler.

        Returns:
            True if the handler started successfully, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(
                ("0.0.0.0", self.local_port)  # nosec B104 - RTP needs to bind all interfaces
            )
            self.running = True

            self.logger.info(f"RTP handler started on port {self.local_port}")

            # Start receiving thread
            receive_thread = threading.Thread(target=self._receive_loop)
            receive_thread.daemon = True
            receive_thread.start()

            return True
        except OSError as e:
            self.logger.error(f"Failed to start RTP handler: {e}")
            return False

    def stop(self) -> None:
        """Stop RTP handler."""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info(f"RTP handler stopped on port {self.local_port}")

    def _receive_loop(self) -> None:
        """Receive RTP packets in a loop."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                self._handle_rtp_packet(data, addr)
            except OSError as e:
                if self.running:
                    self.logger.error(f"Error receiving RTP packet: {e}")

    def _handle_rtp_packet(self, data: bytes, addr: AddrTuple) -> None:
        """
        Handle incoming RTP packet.

        Args:
            data: Packet data.
            addr: Source address.
        """
        if len(data) < 12:
            return

        # Parse RTP header (simplified)
        # RTP header: version(2), padding(1), extension(1), CSRC count(4),
        #             marker(1), payload type(7), sequence number(16),
        #             timestamp(32), SSRC(32)

        header = struct.unpack("!BBHII", data[:12])
        (header[0] >> 6) & 0x03
        payload_type = header[1] & 0x7F
        seq_num = header[2]
        header[3]
        header[4]

        payload = data[12:]

        self.logger.debug(
            f"Received RTP packet: seq={seq_num}, pt={payload_type}, size={len(payload)}"
        )

        # In a real implementation, you would:
        # 1. Buffer and reorder packets based on sequence number
        # 2. Decode audio based on payload type (codec)
        # 3. Mix/route audio to other participants
        # 4. Handle packet loss and jitter

    def send_packet(self, payload: bytes, payload_type: int = 0, marker: bool = False) -> bool:
        """
        Send RTP packet.

        Args:
            payload: Audio/video payload data.
            payload_type: RTP payload type (codec identifier).
            marker: Marker bit.

        Returns:
            True if sent successfully.
        """
        if not self.remote_host or not self.remote_port:
            return False

        try:
            # Build RTP header
            version = 2
            padding = 0
            extension = 0
            csrc_count = 0

            byte0 = (version << 6) | (padding << 5) | (extension << 4) | csrc_count
            byte1 = (int(marker) << 7) | (payload_type & 0x7F)

            header = struct.pack(
                "!BBHII", byte0, byte1, self.sequence_number, self.timestamp, self.ssrc
            )

            packet = header + payload

            self.socket.sendto(packet, (self.remote_host, self.remote_port))

            # Update sequence and timestamp
            self.sequence_number = (self.sequence_number + 1) & 0xFFFF
            # Simplified, should be based on sample rate
            self.timestamp += len(payload)

            return True
        except (KeyError, OSError, TypeError, ValueError, struct.error) as e:
            self.logger.error(f"Error sending RTP packet: {e}")
            return False


class RTPRelay:
    """
    RTP relay for connecting two endpoints.

    Used for call forwarding, conferencing, etc.
    """

    def __init__(
        self,
        port_range_start: int = 10000,
        port_range_end: int = 20000,
        qos_monitor: QoSMonitor | None = None,
    ) -> None:
        """
        Initialize RTP relay.

        Args:
            port_range_start: Start of port range for RTP.
            port_range_end: End of port range for RTP.
            qos_monitor: Optional QoS monitor for tracking call quality.
        """
        self.port_range_start: int = port_range_start
        self.port_range_end: int = port_range_end
        self.active_relays: dict[str, dict[str, Any]] = {}
        self.logger = get_logger()
        self.port_pool: list[int] = list(
            range(port_range_start, port_range_end, 2)
        )  # Even ports for RTP
        self.qos_monitor: QoSMonitor | None = qos_monitor

    def allocate_relay(self, call_id: str) -> tuple[int, int] | None:
        """
        Allocate RTP relay for a call.

        Args:
            call_id: Unique call identifier.

        Returns:
            Tuple of (rtp_port, rtcp_port) or None if allocation failed.
        """
        if not self.port_pool:
            self.logger.error("No available ports for RTP relay")
            return None

        rtp_port = self.port_pool.pop(0)
        rtcp_port = rtp_port + 1

        handler = RTPRelayHandler(rtp_port, call_id, qos_monitor=self.qos_monitor)
        if handler.start():
            self.active_relays[call_id] = {
                "rtp_port": rtp_port,
                "rtcp_port": rtcp_port,
                "handler": handler,
            }
            self.logger.info(
                f"Allocated RTP relay for call {call_id}: ports {rtp_port}/{rtcp_port}"
            )
            return (rtp_port, rtcp_port)
        self.port_pool.insert(0, rtp_port)
        return None

    def set_endpoints(self, call_id: str, endpoint_a: AddrTuple, endpoint_b: AddrTuple) -> None:
        """
        Set both endpoints for RTP relay.

        Args:
            call_id: Call identifier.
            endpoint_a: Tuple of (host, port) for first endpoint.
            endpoint_b: Tuple of (host, port) for second endpoint.
        """
        if call_id in self.active_relays:
            handler: RTPRelayHandler = self.active_relays[call_id]["handler"]
            handler.set_endpoints(endpoint_a, endpoint_b)
            self.logger.info(f"RTP relay {call_id}: {endpoint_a} <-> {endpoint_b}")

    def release_relay(self, call_id: str) -> None:
        """
        Release RTP relay for a call.

        Args:
            call_id: Call identifier.
        """
        if call_id in self.active_relays:
            relay = self.active_relays[call_id]
            relay["handler"].stop()
            self.port_pool.append(relay["rtp_port"])
            self.port_pool.sort()
            del self.active_relays[call_id]
            self.logger.info(f"Released RTP relay for call {call_id}")


class RTPRelayHandler:
    """RTP relay handler that forwards packets between two endpoints."""

    def __init__(
        self,
        local_port: int,
        call_id: str,
        qos_monitor: QoSMonitor | None = None,
    ) -> None:
        """
        Initialize RTP relay handler.

        Args:
            local_port: Local port to bind to.
            call_id: Call identifier for logging.
            qos_monitor: Optional QoS monitor for tracking call quality.
        """
        self.local_port: int = local_port
        self.call_id: str = call_id
        self.logger = get_logger()
        self.socket: socket.socket | None = None
        self.running: bool = False
        self.endpoint_a: AddrTuple | None = None  # (host, port) - Expected endpoint from SDP
        self.endpoint_b: AddrTuple | None = None  # (host, port) - Expected endpoint from SDP
        # (host, port) - Actual source learned from first packet
        self.learned_a: AddrTuple | None = None
        # (host, port) - Actual source learned from first packet
        self.learned_b: AddrTuple | None = None
        self.lock: threading.Lock = threading.Lock()
        self.qos_monitor: QoSMonitor | None = qos_monitor
        # Track QoS separately for each direction to avoid mixing sequence
        # numbers
        self.qos_metrics_a_to_b: QoSMetrics | None = None  # Metrics for packets from A to B
        self.qos_metrics_b_to_a: QoSMetrics | None = None  # Metrics for packets from B to A
        self._learning_timeout: float = 10.0  # Seconds to allow endpoint learning
        self._start_time: float | None = None  # Track when relay started for timeout

        # Start QoS monitoring if monitor is available
        # We track each direction separately since they have independent RTP
        # sequence numbers
        if self.qos_monitor:
            self.qos_metrics_a_to_b = self.qos_monitor.start_monitoring(f"{call_id}_a_to_b")
            self.qos_metrics_b_to_a = self.qos_monitor.start_monitoring(f"{call_id}_b_to_a")
            self.logger.debug("QoS monitoring started for call %s (both directions)", call_id)

    def set_endpoints(self, endpoint_a: AddrTuple | None, endpoint_b: AddrTuple | None) -> None:
        """
        Set the two endpoints to relay between.

        Either or both endpoints can be None initially. The relay will learn
        endpoints from actual RTP packets (symmetric RTP) or wait until both
        are explicitly set.

        Args:
            endpoint_a: Tuple of (host, port) or None.
            endpoint_b: Tuple of (host, port) or None.
        """
        with self.lock:
            # Only update if not None, preserving existing values
            if endpoint_a is not None:
                self.endpoint_a = endpoint_a
            if endpoint_b is not None:
                self.endpoint_b = endpoint_b

    def start(self) -> bool:
        """
        Start RTP relay handler.

        Returns:
            True if the handler started successfully, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(
                ("0.0.0.0", self.local_port)  # nosec B104 - RTP needs to bind all interfaces
            )
            self.running = True
            self._start_time = time.time()  # Track start time for learning timeout

            self.logger.info(
                f"RTP relay handler started on port {self.local_port} for call {self.call_id}"
            )

            # Start receiving thread
            receive_thread = threading.Thread(target=self._relay_loop)
            receive_thread.daemon = True
            receive_thread.start()

            return True
        except OSError as e:
            self.logger.error(f"Failed to start RTP relay handler: {e}")
            return False

    def stop(self) -> None:
        """Stop RTP relay handler."""
        self.running = False
        if self.socket:
            self.socket.close()

        # Stop QoS monitoring if active (both directions)
        if self.qos_monitor:
            if self.qos_metrics_a_to_b:
                self.qos_monitor.stop_monitoring(f"{self.call_id}_a_to_b")
            if self.qos_metrics_b_to_a:
                self.qos_monitor.stop_monitoring(f"{self.call_id}_b_to_a")

        self.logger.info(f"RTP relay handler stopped on port {self.local_port}")

    def _relay_loop(self) -> None:
        """Relay RTP packets between endpoints with symmetric RTP support."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)

                # Symmetric RTP: Learn actual source addresses from first packets
                # This handles NAT traversal where actual source differs from
                # SDP
                with self.lock:
                    # Allow learning even if only one endpoint is set (fixes early packet dropping)
                    # This is important because INVITE sets endpoint_a but endpoint_b is only
                    # set after 200 OK. RTP packets may arrive during this
                    # window.

                    # Determine if this packet is from A, B, or unknown
                    is_from_a = False
                    is_from_b = False

                    # Check learned addresses first (most reliable)
                    if self.learned_a and (
                        addr[0] == self.learned_a[0] and addr[1] == self.learned_a[1]
                    ):
                        is_from_a = True
                    elif self.learned_b and (
                        addr[0] == self.learned_b[0] and addr[1] == self.learned_b[1]
                    ):
                        is_from_b = True
                    # Check if packet matches expected SDP address for A
                    elif self.endpoint_a and (
                        addr[0] == self.endpoint_a[0] and addr[1] == self.endpoint_a[1]
                    ):
                        if not self.learned_a:
                            self.learned_a = addr
                            self.logger.info(f"Learned endpoint A: {addr} (matched SDP)")
                        is_from_a = True
                    # Check if packet matches expected SDP address for B
                    elif self.endpoint_b and (
                        addr[0] == self.endpoint_b[0] and addr[1] == self.endpoint_b[1]
                    ):
                        if not self.learned_b:
                            self.learned_b = addr
                            self.logger.info(f"Learned endpoint B: {addr} (matched SDP)")
                        is_from_b = True
                    # Symmetric RTP: Learn from first packet (NAT traversal)
                    # Security: Only learn within timeout window and validate
                    # packet format
                    elif not self.learned_a:
                        # Check if we're still in the learning window
                        elapsed = time.time() - self._start_time if self._start_time else 0
                        if elapsed > self._learning_timeout:
                            self.logger.warning(
                                f"RTP learning timeout expired, rejecting packet from {addr}"
                            )
                            continue

                        # Validate this looks like a real RTP packet (at least
                        # 12 bytes header)
                        if len(data) < 12:
                            self.logger.debug(f"Rejecting too-short packet from {addr}")
                            continue

                        # First packet from unknown source - assume it's
                        # endpoint A
                        self.learned_a = addr
                        is_from_a = True
                        expected_str = (
                            f" (expected {self.endpoint_a})"
                            if self.endpoint_a
                            else " (no SDP endpoint set)"
                        )
                        self.logger.info(
                            f"Learned endpoint A via symmetric RTP: {addr}{expected_str}"
                        )
                    elif not self.learned_b and addr != self.learned_a:
                        # Check if we're still in the learning window
                        elapsed = time.time() - self._start_time if self._start_time else 0
                        if elapsed > self._learning_timeout:
                            self.logger.warning(
                                f"RTP learning timeout expired, rejecting packet from {addr}"
                            )
                            continue

                        # Validate this looks like a real RTP packet
                        if len(data) < 12:
                            self.logger.debug(f"Rejecting too-short packet from {addr}")
                            continue

                        # Second packet from different source - assume it's
                        # endpoint B
                        self.learned_b = addr
                        is_from_b = True
                        expected_str = (
                            f" (expected {self.endpoint_b})"
                            if self.endpoint_b
                            else " (no SDP endpoint set)"
                        )
                        self.logger.info(
                            f"Learned endpoint B via symmetric RTP: {addr}{expected_str}"
                        )
                    else:
                        # Packet from unknown third source or duplicate
                        self.logger.debug(
                            f"RTP packet from unknown source: {addr} (learned A:{self.learned_a}, B:{self.learned_b})"
                        )
                        continue

                    # Forward packet to the other endpoint and update QoS metrics
                    # Parse RTP header once for QoS tracking (only if we have
                    # valid data)
                    seq_num: int | None = None
                    timestamp: int | None = None
                    payload_size: int | None = None
                    if len(data) >= 12:
                        try:
                            header = struct.unpack("!BBHII", data[:12])
                            seq_num = header[2]
                            timestamp = header[3]
                            payload_size = len(data) - 12
                        except (KeyError, TypeError, ValueError, struct.error) as parse_error:
                            self.logger.debug(f"Error parsing RTP header for QoS: {parse_error}")

                    if is_from_a and self.learned_b:
                        # Packet from A, send to B (using learned address)
                        self.socket.sendto(data, self.learned_b)
                        # Track QoS for A->B direction
                        if self.qos_metrics_a_to_b and seq_num is not None:
                            self.qos_metrics_a_to_b.update_packet_received(
                                seq_num, timestamp, payload_size
                            )
                            self.qos_metrics_a_to_b.update_packet_sent()
                        self.logger.debug(f"Relayed {len(data)} bytes: A->B")
                    elif is_from_b and self.learned_a:
                        # Packet from B, send to A (using learned address)
                        self.socket.sendto(data, self.learned_a)
                        # Track QoS for B->A direction
                        if self.qos_metrics_b_to_a and seq_num is not None:
                            self.qos_metrics_b_to_a.update_packet_received(
                                seq_num, timestamp, payload_size
                            )
                            self.qos_metrics_b_to_a.update_packet_sent()
                        self.logger.debug(f"Relayed {len(data)} bytes: B->A")
                    elif is_from_a and self.endpoint_b:
                        # From A but B not learned yet - try sending to
                        # expected B (if known)
                        self.socket.sendto(data, self.endpoint_b)
                        # Track QoS for A->B direction
                        if self.qos_metrics_a_to_b and seq_num is not None:
                            self.qos_metrics_a_to_b.update_packet_received(
                                seq_num, timestamp, payload_size
                            )
                            self.qos_metrics_a_to_b.update_packet_sent()
                        self.logger.debug(
                            f"Relayed {len(data)} bytes: A->B (B not learned, using SDP)"
                        )
                    elif is_from_b and self.endpoint_a:
                        # From B but A not learned yet - try sending to
                        # expected A (if known)
                        self.socket.sendto(data, self.endpoint_a)
                        # Track QoS for B->A direction
                        if self.qos_metrics_b_to_a and seq_num is not None:
                            self.qos_metrics_b_to_a.update_packet_received(
                                seq_num, timestamp, payload_size
                            )
                            self.qos_metrics_b_to_a.update_packet_sent()
                        self.logger.debug(
                            f"Relayed {len(data)} bytes: B->A (A not learned, using SDP)"
                        )
                    elif is_from_a:
                        # From A but B not known at all yet - must drop packet
                        # This is rare since endpoint_b is usually set soon
                        # after endpoint_a
                        self.logger.debug("Packet from A dropped - waiting for B endpoint")
                    elif is_from_b:
                        # From B but A not known at all yet - must drop packet
                        # This is rare since endpoint_a is usually set first
                        self.logger.debug("Packet from B dropped - waiting for A endpoint")

            except (KeyError, OSError, TypeError, ValueError, struct.error) as e:
                if self.running:
                    self.logger.error(f"Error in RTP relay loop: {e}")


class RTPRecorder:
    """
    RTP recorder for voicemail recording.

    Records incoming RTP audio stream.
    Automatically filters out RFC 2833 telephone-event packets (payload type 101).
    """

    def __init__(
        self,
        local_port: int,
        call_id: str,
        rfc2833_handler: RFC2833Receiver | None = None,
    ) -> None:
        """
        Initialize RTP recorder.

        Args:
            local_port: Local port to bind to.
            call_id: Call identifier for logging.
            rfc2833_handler: Optional RFC 2833 receiver for DTMF event handling.
        """
        self.local_port: int = local_port
        self.call_id: str = call_id
        self.logger = get_logger()
        self.socket: socket.socket | None = None
        self.running: bool = False
        self.recorded_data: list[bytes] = []
        self.lock: threading.Lock = threading.Lock()
        self.remote_endpoint: AddrTuple | None = None  # Will be learned from first packet
        self.rfc2833_handler: RFC2833Receiver | None = rfc2833_handler  # Optional RFC 2833 receiver

    def start(self) -> bool:
        """
        Start RTP recorder.

        Returns:
            True if the recorder started successfully, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(
                ("0.0.0.0", self.local_port)  # nosec B104 - RTP needs to bind all interfaces
            )
            self.socket.settimeout(0.5)  # 500ms timeout for recv
            self.running = True

            self.logger.info(
                f"RTP recorder started on port {self.local_port} for call {self.call_id}"
            )

            # Start recording thread
            record_thread = threading.Thread(target=self._record_loop)
            record_thread.daemon = True
            record_thread.start()

            return True
        except OSError as e:
            self.logger.error(f"Failed to start RTP recorder: {e}")
            return False

    def stop(self) -> None:
        """Stop RTP recorder."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except OSError as e:
                self.logger.debug(f"Error closing socket: {e}")
        self.logger.info(f"RTP recorder stopped on port {self.local_port}")

    def _record_loop(self) -> None:
        """Record RTP packets in a loop."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)

                # Learn remote endpoint from first packet
                if not self.remote_endpoint:
                    self.remote_endpoint = addr
                    self.logger.info(f"Learned remote RTP endpoint: {addr}")

                # Extract audio payload from RTP packet
                if len(data) >= 12:
                    # Parse RTP header to get payload
                    header = struct.unpack("!BBHII", data[:12])
                    payload_type = header[1] & 0x7F
                    payload = data[12:]

                    # Filter out RFC 2833 telephone-event packets (payload type 101)
                    # These are DTMF signaling packets, not audio
                    if payload_type == 101:
                        self.logger.debug(
                            "Received RFC 2833 telephone-event packet (filtered from recording)"
                        )
                        # If we have an RFC 2833 handler, delegate event
                        # processing
                        if self.rfc2833_handler:
                            self.rfc2833_handler.handle_rtp_packet(data, addr)
                        continue

                    # Store only audio payloads (not telephone-events)
                    with self.lock:
                        self.recorded_data.append(payload)

                    self.logger.debug(
                        f"Recorded {len(payload)} bytes (PT {payload_type}) from call {self.call_id}"
                    )

            except TimeoutError:
                # Timeout is normal, just continue
                continue
            except (KeyError, OSError, TypeError, ValueError, struct.error) as e:
                if self.running:
                    self.logger.error(f"Error in RTP record loop: {e}")

    def get_recorded_audio(self) -> bytes:
        """
        Get all recorded audio data.

        Returns:
            Combined audio data as bytes.
        """
        with self.lock:
            # Combine all recorded payloads
            return b"".join(self.recorded_data)

    def get_duration(self) -> int:
        """
        Estimate recording duration based on packets received.

        Assumes 20ms per packet (typical for G.711).

        Note: This is an approximation. For accurate duration calculation,
        we would need to track RTP timestamps and account for packet timing
        variations, lost packets, or different packetization intervals.

        Returns:
            Duration in seconds (estimated).
        """
        with self.lock:
            num_packets = len(self.recorded_data)
            # Each packet typically represents 20ms of audio
            duration_ms = num_packets * 20
            return duration_ms // 1000


class RTPPlayer:
    """
    RTP Player - Sends audio to remote endpoint.

    Used for playing tones, announcements, music on hold, etc.
    """

    def __init__(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        call_id: str | None = None,
    ) -> None:
        """
        Initialize RTP player.

        Args:
            local_port: Local UDP port to send from.
            remote_host: Remote host IP address.
            remote_port: Remote UDP port.
            call_id: Optional call identifier for logging.
        """
        self.local_port: int = local_port
        self.remote_host: str = remote_host
        self.remote_port: int = remote_port
        self.call_id: str = call_id or "unknown"
        self.logger = get_logger()
        self.socket: socket.socket | None = None
        self.running: bool = False
        self.sequence_number: int = 0
        self.timestamp: int = 0
        self.ssrc: int = 0x87654321  # Synchronization source identifier
        self.lock: threading.Lock = threading.Lock()

    def start(self) -> bool:
        """
        Start RTP player.

        Returns:
            True if the player started successfully, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces (0.0.0.0) to allow RTP from any network adapter
            # This is intentional for VoIP systems which need to handle
            # multi-homed servers
            self.socket.bind(
                ("0.0.0.0", self.local_port)  # nosec B104 - RTP needs to bind all interfaces
            )
            self.running = True

            self.logger.info(
                f"RTP player started on port {self.local_port} for call {self.call_id}"
            )
            return True
        except OSError as e:
            self.logger.error(f"Failed to start RTP player: {e}")
            return False

    def stop(self) -> None:
        """Stop RTP player."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass  # Socket already closed
            self.socket = None
        self.logger.info(f"RTP player stopped for call {self.call_id}")

    def send_audio(
        self,
        audio_data: bytes,
        payload_type: int = 0,
        samples_per_packet: int = 160,
        bytes_per_sample: int | None = None,
    ) -> bool:
        """
        Send audio data via RTP packets.

        Args:
            audio_data: Raw audio data (format depends on payload_type).
                - For PCMU/PCMA (PT 0/8): 8-bit samples (1 byte per sample).
                - For G.722 (PT 9): 8-bit encoded samples (1 byte per sample).
                - For PCM (PT 10/11): 16-bit samples (2 bytes per sample).
            payload_type: RTP payload type (0 = PCMU, 8 = PCMA, 9 = G.722,
                10 = L16 stereo, 11 = L16 mono).
            samples_per_packet: Number of samples per RTP packet
                (default 160 = 20ms at 8kHz).
            bytes_per_sample: Bytes per sample (None=auto-detect, 1 for
                G.711/G.722, 2 for 16-bit PCM).

        Returns:
            True if successful.
        """
        if not self.running or not self.socket:
            self.logger.warning("Cannot send audio - RTP player not running")
            return False

        try:
            # Determine bytes per sample if not explicitly provided
            if bytes_per_sample is None:
                # G.711 formats (PCMU, PCMA) are 8-bit = 1 byte per sample
                # G.722 is also 8-bit encoded = 1 byte per sample
                # PCM formats are typically 16-bit = 2 bytes per sample
                if payload_type in [0, 8, 9]:  # PCMU, PCMA, or G.722
                    bytes_per_sample = 1
                else:  # PCM or other formats
                    bytes_per_sample = 2

            # Split audio into packets
            bytes_per_packet = samples_per_packet * bytes_per_sample
            num_packets = (len(audio_data) + bytes_per_packet - 1) // bytes_per_packet

            for i in range(num_packets):
                start = i * bytes_per_packet
                end = min(start + bytes_per_packet, len(audio_data))
                payload = audio_data[start:end]

                # Build RTP packet
                rtp_packet = self._build_rtp_packet(payload, payload_type)

                # Send packet
                self.socket.sendto(rtp_packet, (self.remote_host, self.remote_port))

                # Increment sequence and timestamp
                with self.lock:
                    self.sequence_number = (self.sequence_number + 1) & 0xFFFF
                    self.timestamp = (self.timestamp + samples_per_packet) & 0xFFFFFFFF

                # Small delay to pace packets (20ms for 160 samples at 8kHz)
                time.sleep(0.020)

            self.logger.info(f"Sent {num_packets} RTP packets for call {self.call_id}")
            return True

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Error sending audio: {e}")
            return False

    def _build_rtp_packet(self, payload: bytes, payload_type: int = 0) -> bytes:
        """
        Build an RTP packet.

        Args:
            payload: Audio payload bytes.
            payload_type: RTP payload type.

        Returns:
            Complete RTP packet as bytes.
        """
        # RTP header (12 bytes)
        # Byte 0: V(2), P(1), X(1), CC(4)
        # V=2, P=0, X=0, CC=0
        byte0 = 0x80  # Version 2, no padding, no extension, no CSRC

        # Byte 1: M(1), PT(7)
        # M=0 (not first packet), PT=payload_type
        byte1 = payload_type & 0x7F

        with self.lock:
            header = struct.pack(
                ">BBHII", byte0, byte1, self.sequence_number, self.timestamp, self.ssrc
            )

        return header + payload

    def play_beep(self, frequency: int = 1000, duration_ms: int = 500) -> bool:
        """
        Play a beep tone.

        Args:
            frequency: Frequency in Hz.
            duration_ms: Duration in milliseconds.

        Returns:
            True if successful.
        """
        # Note: Import here to avoid circular dependency with audio module
        try:
            from pbx.utils.audio import generate_beep_tone, pcm16_to_ulaw

            # Generate PCM tone (16-bit samples)
            pcm_data = generate_beep_tone(frequency, duration_ms, sample_rate=8000)
            # Convert to u-law for PCMU codec (payload type 0)
            ulaw_data = pcm16_to_ulaw(pcm_data)
            return self.send_audio(ulaw_data, payload_type=0)
        except ImportError:
            self.logger.error("Audio utilities not available")
            return False

    def play_file(self, file_path: str | Path) -> bool:
        """
        Play an audio file from a WAV file.

        Supports WAV files with:
        - G.711 u-law (8-bit, 8kHz) - legacy format
        - G.711 A-law (8-bit, 8kHz) - legacy format
        - PCM (16-bit, 8kHz/16kHz) - converted to G.722 for HD audio

        Args:
            file_path: Path to WAV file.

        Returns:
            True if successful.
        """
        import struct

        if not Path(file_path).exists():
            self.logger.error(f"Audio file not found: {file_path}")
            return False

        try:
            with open(file_path, "rb") as f:
                # Read WAV header
                riff = f.read(4)
                if riff != b"RIFF" or len(riff) < 4:
                    self.logger.error(f"Invalid WAV file (bad RIFF header): {file_path}")
                    return False

                size_bytes = f.read(4)
                if len(size_bytes) < 4:
                    self.logger.error(f"Truncated WAV file (no file size): {file_path}")
                    return False
                struct.unpack("<I", size_bytes)[0]

                wave = f.read(4)
                if wave != b"WAVE" or len(wave) < 4:
                    self.logger.error(f"Invalid WAV file (bad WAVE marker): {file_path}")
                    return False

                # Find fmt chunk
                audio_format: int = 0
                num_channels: int = 0
                sample_rate: int = 0
                payload_type: int = 0
                convert_to_pcmu: bool = False

                while True:
                    chunk_id = f.read(4)
                    if not chunk_id or len(chunk_id) < 4:
                        self.logger.error(f"No format chunk found in WAV file: {file_path}")
                        return False

                    size_bytes = f.read(4)
                    if not size_bytes or len(size_bytes) < 4:
                        self.logger.error(f"Truncated chunk size in WAV file: {file_path}")
                        return False
                    chunk_size = struct.unpack("<I", size_bytes)[0]

                    if chunk_id == b"fmt ":
                        # Validate fmt chunk size (minimum 16 bytes for basic
                        # format)
                        if chunk_size < 16:
                            self.logger.error(f"Invalid fmt chunk size in WAV file: {file_path}")
                            return False

                        # Parse format
                        fmt_data = f.read(16)
                        if len(fmt_data) < 16:
                            self.logger.error(f"Truncated fmt chunk in WAV file: {file_path}")
                            return False

                        audio_format = struct.unpack("<H", fmt_data[0:2])[0]
                        num_channels = struct.unpack("<H", fmt_data[2:4])[0]
                        sample_rate = struct.unpack("<I", fmt_data[4:8])[0]
                        # Skip byte_rate and block_align - not needed for playback
                        struct.unpack("<H", fmt_data[14:16])[0]

                        # Skip any extra format bytes
                        if chunk_size > 16:
                            f.read(chunk_size - 16)

                        # Determine payload type based on format
                        convert_to_pcmu = False
                        if audio_format == WAV_FORMAT_ULAW:
                            payload_type = 0  # PCMU (u-law)
                        elif audio_format == WAV_FORMAT_ALAW:
                            payload_type = 8  # PCMA (A-law)
                        elif audio_format == WAV_FORMAT_G722:
                            # G.722 format - already encoded, no conversion
                            # needed
                            payload_type = 9  # G.722
                            self.logger.info("G.722 format detected - already encoded for VoIP.")
                        elif audio_format == WAV_FORMAT_PCM:
                            # PCM format - convert to PCMU (G.711 u-law) for maximum compatibility
                            # Note: Previously converted to G.722, but G.722
                            # has implementation issues
                            payload_type = 0  # PCMU
                            convert_to_pcmu = True
                            self.logger.info(
                                "PCM format detected - will convert to PCMU (G.711 u-law) "
                                "for maximum compatibility."
                            )
                        else:
                            self.logger.error(f"Unsupported audio format: {audio_format}")
                            return False

                        self.logger.info(
                            f"WAV file: format={audio_format}, channels={num_channels}, "
                            f"rate={sample_rate}Hz, bits={struct.unpack('<H', fmt_data[14:16])[0]}"
                        )
                        break

                    if chunk_id == b"data":
                        # Found data before fmt - invalid
                        self.logger.error("Invalid WAV structure")
                        return False
                    # Skip unknown chunk
                    f.read(chunk_size)

                # Find data chunk
                while True:
                    chunk_id = f.read(4)
                    if not chunk_id or len(chunk_id) < 4:
                        self.logger.error(f"No data chunk found in WAV file: {file_path}")
                        return False

                    size_bytes = f.read(4)
                    if not size_bytes or len(size_bytes) < 4:
                        self.logger.error(f"Truncated data chunk size in WAV file: {file_path}")
                        return False
                    chunk_size = struct.unpack("<I", size_bytes)[0]

                    if chunk_id == b"data":
                        # Validate data size is reasonable
                        if chunk_size == 0:
                            self.logger.error(f"Empty data chunk in WAV file: {file_path}")
                            return False
                        if chunk_size > 100 * 1024 * 1024:  # 100MB limit
                            self.logger.error(
                                f"Data chunk too large ({chunk_size} bytes) in WAV file: {file_path}"
                            )
                            return False

                        # Read audio data
                        audio_data = f.read(chunk_size)
                        if len(audio_data) < chunk_size:
                            self.logger.warning(
                                f"Truncated audio data in WAV file: {file_path} "
                                f"(expected {chunk_size}, got {len(audio_data)})"
                            )
                            # Continue with partial data rather than failing
                            # completely

                        # For mono files, use data as-is
                        # For stereo, we'd need to downmix (take left channel)
                        if num_channels == 2:
                            self.logger.warning(
                                "Stereo audio detected, extracting left channel only"
                            )
                            # Extract left channel (assuming interleaved
                            # samples)
                            if audio_format == WAV_FORMAT_PCM:  # PCM 16-bit
                                # Extract every other 16-bit sample (left channel)
                                # More efficient using slice with step
                                audio_data = audio_data[::4] + audio_data[1::4]
                            else:  # 8-bit formats (G.711, G.722)
                                audio_data = audio_data[::2]

                        # Convert PCM to PCMU if needed
                        if convert_to_pcmu:
                            try:
                                from pbx.utils.audio import pcm16_to_ulaw

                                original_size = len(audio_data)

                                # First, downsample from 16kHz to 8kHz if
                                # needed
                                if sample_rate == 16000:
                                    # Simple decimation: take every other
                                    # sample
                                    downsampled = bytearray()
                                    for i in range(
                                        0, len(audio_data), 4
                                    ):  # Skip every other 16-bit sample
                                        if i + 1 < len(audio_data):
                                            downsampled.extend(audio_data[i : i + 2])
                                    audio_data = bytes(downsampled)
                                    sample_rate = 8000
                                    self.logger.info(
                                        f"Downsampled from 16kHz to 8kHz: {original_size} bytes -> {len(audio_data)} bytes"
                                    )

                                # Convert to u-law
                                audio_data = pcm16_to_ulaw(audio_data)
                                self.logger.info(
                                    f"Converted PCM to PCMU: {len(audio_data)} bytes (u-law)"
                                )
                            except (KeyError, TypeError, ValueError) as e:
                                self.logger.error(f"Failed to convert PCM to PCMU: {e}")
                                return False
                        elif payload_type == 9:
                            # G.722 format - already encoded, ensure correct sample rate for packets
                            # G.722 uses 8kHz clock rate but actual 16kHz
                            # sampling
                            sample_rate = 16000

                        # Calculate samples per packet based on sample rate
                        # 20ms packet = sample_rate * 0.02
                        samples_per_packet = int(sample_rate * 0.02)

                        # Send the audio
                        self.logger.info(
                            f"Playing audio file: {file_path} ({len(audio_data)} bytes)"
                        )
                        return self.send_audio(audio_data, payload_type, samples_per_packet)

                    # Skip this chunk (with size validation)
                    if chunk_size > 100 * 1024 * 1024:  # 100MB limit
                        self.logger.error(
                            f"Chunk size too large ({chunk_size} bytes) in WAV file: {file_path}"
                        )
                        return False
                    f.read(chunk_size)

        except (KeyError, OSError, TypeError, ValueError) as e:
            self.logger.error(f"Error playing audio file {file_path}: {e}")
            import traceback

            traceback.print_exc()
            return False


class RTPDTMFListener:
    """
    RTP DTMF Listener - Receives RTP audio and detects DTMF tones.

    Used for interactive voice response (IVR) and auto attendant systems.
    """

    def __init__(self, local_port: int, call_id: str | None = None) -> None:
        """
        Initialize RTP DTMF listener.

        Args:
            local_port: Local UDP port to receive RTP packets.
            call_id: Optional call identifier for logging.
        """
        self.local_port: int = local_port
        self.call_id: str = call_id or "unknown"
        self.logger = get_logger()
        self.socket: socket.socket | None = None
        self.running: bool = False
        self.detected_digits: list[str] = []
        self.lock: threading.Lock = threading.Lock()
        self.audio_buffer: list[float] = []
        self.sample_rate: int = 8000  # Standard for telephony

        # DTMF detection frame sizes (based on DTMFDetector default of 205 samples per frame)
        # We need ~2x frame size for reliable detection with overlap
        self.dtmf_frame_size: int = 205  # Samples per DTMF detection frame
        # Buffer size for detection (2x frame size)
        self.dtmf_buffer_size: int = 410
        self.dtmf_slide_size: int = 205  # Sliding window size

        # Initialize DTMF detector
        from pbx.utils.dtmf import DTMFDetector

        self.dtmf_detector = DTMFDetector(sample_rate=self.sample_rate)

    def start(self) -> bool:
        """
        Start RTP DTMF listener.

        Returns:
            True if the listener started successfully, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces (0.0.0.0) to allow RTP from any network adapter
            # This is intentional for VoIP systems which need to handle
            # multi-homed servers
            self.socket.bind(
                ("0.0.0.0", self.local_port)  # nosec B104 - RTP needs to bind all interfaces
            )
            self.socket.settimeout(0.1)  # 100ms timeout for recv
            self.running = True

            self.logger.info(
                f"RTP DTMF listener started on port {self.local_port} for call {self.call_id}"
            )

            # Start listening thread
            listen_thread = threading.Thread(target=self._listen_loop)
            listen_thread.daemon = True
            listen_thread.start()

            return True
        except OSError as e:
            self.logger.error(f"Failed to start RTP DTMF listener: {e}")
            return False

    def stop(self) -> None:
        """Stop RTP DTMF listener."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except OSError as e:
                self.logger.debug(f"Error closing socket: {e}")
            self.socket = None
        self.logger.info(f"RTP DTMF listener stopped for call {self.call_id}")

    def _listen_loop(self) -> None:
        """Listen for RTP packets and detect DTMF tones."""

        while self.running:
            try:
                data, _addr = self.socket.recvfrom(2048)

                # Extract audio payload from RTP packet
                if len(data) >= 12:
                    # Parse RTP header
                    header = struct.unpack("!BBHII", data[:12])
                    payload_type = header[1] & 0x7F
                    payload = data[12:]

                    # Convert audio payload to samples for DTMF detection
                    # Assuming G.711 u-law (payload type 0) or A-law (payload
                    # type 8)
                    if payload_type in [0, 8]:
                        # Convert G.711 to linear PCM samples
                        samples = self._decode_g711(payload, payload_type)

                        with self.lock:
                            self.audio_buffer.extend(samples)

                            # Process buffer when we have enough samples
                            if len(self.audio_buffer) >= self.dtmf_buffer_size:
                                # Try to detect DTMF tone
                                digit = self.dtmf_detector.detect_tone(
                                    self.audio_buffer[: self.dtmf_buffer_size]
                                )

                                if digit:
                                    # Check if this is a new digit (not a
                                    # repeat)
                                    if (
                                        not self.detected_digits
                                        or self.detected_digits[-1] != digit
                                    ):
                                        self.detected_digits.append(digit)
                                        self.logger.info(f"DTMF digit detected: {digit}")

                                # Keep a sliding window of audio
                                self.audio_buffer = self.audio_buffer[self.dtmf_slide_size :]

            except TimeoutError:
                # Timeout is normal, just continue
                continue
            except (KeyError, OSError, TypeError, ValueError, struct.error) as e:
                if self.running:
                    self.logger.error(f"Error in RTP DTMF listen loop: {e}")

    def _decode_g711(self, payload: bytes, payload_type: int) -> list[float]:
        """
        Decode G.711 audio to linear PCM samples.

        Args:
            payload: G.711 encoded audio bytes.
            payload_type: 0 for u-law, 8 for A-law.

        Returns:
            Linear PCM samples normalized to [-1.0, 1.0].
        """
        samples: list[float] = []

        for byte in payload:
            if payload_type == 0:  # u-law
                # Simplified u-law decode
                sample = self._ulaw_to_linear(byte)
            else:  # A-law (payload_type == 8)
                # Simplified A-law decode
                sample = self._alaw_to_linear(byte)

            # Normalize to [-1.0, 1.0]
            samples.append(sample / 32768.0)

        return samples

    def _ulaw_to_linear(self, ulaw_byte: int) -> int:
        """
        Convert u-law byte to linear PCM sample.

        Args:
            ulaw_byte: u-law encoded byte.

        Returns:
            Linear PCM sample (-32768 to 32767).
        """
        # u-law decompression algorithm (ITU-T G.711)
        ulaw_byte = ~ulaw_byte & 0xFF
        sign = (ulaw_byte & 0x80) >> 7
        exponent = (ulaw_byte & 0x70) >> 4
        mantissa = ulaw_byte & 0x0F

        # Calculate linear value
        # 0x84 (132) is the bias value added to mantissa in u-law encoding
        linear = ((mantissa << 3) + 0x84) << exponent

        if sign:
            return -linear
        return linear

    def _alaw_to_linear(self, alaw_byte: int) -> int:
        """
        Convert A-law byte to linear PCM sample.

        Args:
            alaw_byte: A-law encoded byte.

        Returns:
            Linear PCM sample (-32768 to 32767).
        """
        # A-law decompression algorithm (ITU-T G.711)
        alaw_byte ^= 0x55  # XOR with 0x55 per A-law spec
        sign = (alaw_byte & 0x80) >> 7
        exponent = (alaw_byte & 0x70) >> 4
        mantissa = alaw_byte & 0x0F

        if exponent == 0:
            linear = (mantissa << 4) + 8
        else:
            # 0x108 (264) is the bias for non-zero exponents in A-law encoding
            linear = ((mantissa << 4) + 0x108) << (exponent - 1)

        if sign:
            return -linear
        return linear

    def get_digit(self, timeout: float = 1.0) -> str | None:
        """
        Get the next detected DTMF digit.

        Args:
            timeout: Maximum time to wait for a digit (seconds).

        Returns:
            Detected digit ('0'-'9', '*', '#', 'A'-'D') or None if timeout.
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            with self.lock:
                if self.detected_digits:
                    return self.detected_digits.pop(0)

            # Small delay to avoid busy waiting
            time.sleep(0.05)

        return None

    def clear_digits(self) -> None:
        """Clear all detected digits from the buffer."""
        with self.lock:
            self.detected_digits.clear()
