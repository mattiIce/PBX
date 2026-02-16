"""
RFC 2833 RTP Event Handler for DTMF Signaling

Implements RFC 2833 (RTP Payload for DTMF Digits, Telephony Tones and Signals)
using configurable payload type (default 101) for out-of-band DTMF transmission over RTP.
"""

from __future__ import annotations

import contextlib
import socket
import struct
import threading
import time
from typing import TYPE_CHECKING

from pbx.utils.logger import get_logger

if TYPE_CHECKING:
    from pbx.core.pbx import PBXCore

# Type alias for network address tuples
type AddrTuple = tuple[str, int]

# Constants
SAMPLE_RATE_8KHZ: int = 8000  # Standard sample rate for telephony
PAYLOAD_TYPE_TELEPHONE_EVENT: int = 101  # RFC 2833 default payload type (can be configured)

# RFC 2833 Event Codes for DTMF digits
RFC2833_EVENT_CODES: dict[str, int] = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "*": 10,
    "#": 11,
    "A": 12,
    "B": 13,
    "C": 14,
    "D": 15,
}

# Reverse mapping
RFC2833_CODE_TO_DIGIT: dict[int, str] = {v: k for k, v in RFC2833_EVENT_CODES.items()}


class RFC2833EventPacket:
    """
    RFC 2833 RTP Event Packet.

    Packet format (4 bytes payload):
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |     event     |E|R| volume    |          duration             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    event: Event code (0-15 for DTMF, see RFC2833_EVENT_CODES)
    E: End bit (1 = final packet for this event)
    R: Reserved (must be 0)
    volume: Power level (0 = loudest, 63 = silence)
    duration: Duration in timestamp units (160 for 20ms at 8kHz)
    """

    def __init__(
        self,
        event: int | str | None = None,
        end: bool = False,
        volume: int = 10,
        duration: int = 160,
    ) -> None:
        """
        Initialize RFC 2833 event packet.

        Args:
            event: Event code (0-15) or DTMF digit ('0'-'9', '*', '#', 'A'-'D').
            end: End bit (True for final packet).
            volume: Power level (0-63, default 10).
            duration: Duration in timestamp units (default 160 = 20ms at 8kHz).
        """
        # Convert digit to event code if string
        if isinstance(event, str):
            self.event: int = RFC2833_EVENT_CODES.get(event.upper(), 0)
        else:
            self.event = event if event is not None else 0

        self.end: bool = end
        self.volume: int = volume
        self.duration: int = duration

    def pack(self) -> bytes:
        """
        Pack event into 4-byte payload.

        Returns:
            4-byte RFC 2833 event payload.
        """
        # Build second byte: E(1) R(1) volume(6)
        byte2 = (int(self.end) << 7) | (self.volume & 0x3F)

        # Pack: event(8), E|R|volume(8), duration(16)
        return struct.pack("!BBH", self.event, byte2, self.duration)

    @staticmethod
    def unpack(data: bytes) -> RFC2833EventPacket | None:
        """
        Unpack 4-byte payload into RFC2833EventPacket.

        Args:
            data: 4-byte payload data.

        Returns:
            RFC2833EventPacket or None if invalid.
        """
        if len(data) < 4:
            return None

        try:
            event, byte2, duration = struct.unpack("!BBH", data[:4])
            end = bool(byte2 & 0x80)
            volume = byte2 & 0x3F

            packet = RFC2833EventPacket(event, end, volume, duration)
            return packet
        except (KeyError, TypeError, ValueError, struct.error):
            return None

    def get_digit(self) -> str | None:
        """
        Get DTMF digit from event code.

        Returns:
            DTMF digit or None if not a valid DTMF event.
        """
        return RFC2833_CODE_TO_DIGIT.get(self.event)


class RFC2833Receiver:
    """
    RFC 2833 RTP Event Receiver.

    Listens for RTP packets with configurable payload type (default 101) and extracts DTMF events.
    """

    def __init__(
        self,
        local_port: int,
        pbx_core: PBXCore | None = None,
        call_id: str | None = None,
        payload_type: int = 101,
    ) -> None:
        """
        Initialize RFC 2833 receiver.

        Args:
            local_port: Local UDP port to listen on.
            pbx_core: Reference to PBX core for DTMF delivery.
            call_id: Call identifier for this receiver.
            payload_type: RTP payload type for telephone-event (default: 101).
        """
        self.local_port: int = local_port
        self.pbx_core: PBXCore | None = pbx_core
        self.call_id: str | None = call_id
        self.payload_type: int = payload_type
        self.logger = get_logger()
        self.socket: socket.socket | None = None
        self.running: bool = False
        self.last_event: str | None = None
        self.last_seq: int | None = None
        self.event_start_time: float | None = None

    def start(self) -> bool:
        """
        Start RFC 2833 receiver.

        Returns:
            True if started successfully, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(
                ("0.0.0.0", self.local_port)  # nosec B104 - RTP needs to bind all interfaces
            )
            self.socket.settimeout(0.1)  # Non-blocking with timeout
            self.running = True

            self.logger.info(f"RFC 2833 receiver started on port {self.local_port}")

            # Start receiving thread
            receive_thread = threading.Thread(target=self._receive_loop)
            receive_thread.daemon = True
            receive_thread.start()

            return True
        except OSError as e:
            self.logger.error(f"Failed to start RFC 2833 receiver: {e}")
            return False

    def stop(self) -> None:
        """Stop RFC 2833 receiver."""
        self.running = False
        if self.socket:
            with contextlib.suppress(BaseException):
                self.socket.close()
        self.logger.info(f"RFC 2833 receiver stopped on port {self.local_port}")

    def _receive_loop(self) -> None:
        """Main receive loop for RFC 2833 events."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                self.handle_rtp_packet(data, addr)
            except TimeoutError:
                continue
            except OSError as e:
                if self.running:
                    self.logger.error(f"Error receiving RFC 2833 packet: {e}")

    def handle_rtp_packet(self, data: bytes, addr: AddrTuple) -> None:
        """
        Handle incoming RTP packet (public interface).

        This is the public method that should be called by external code
        to process RTP packets for RFC 2833 events.

        Args:
            data: Packet data.
            addr: Source address.
        """
        if len(data) < 12:
            return

        # Parse RTP header
        try:
            header = struct.unpack("!BBHII", data[:12])
            (header[0] >> 6) & 0x03
            payload_type = header[1] & 0x7F
            bool(header[1] & 0x80)
            seq_num = header[2]
            header[3]
            header[4]

            # Only process configured payload type for telephone-event
            if payload_type != self.payload_type:
                return

            # Extract payload (RFC 2833 event)
            payload = data[12:]
            if len(payload) < 4:
                return

            # Parse RFC 2833 event
            event_packet = RFC2833EventPacket.unpack(payload)
            if not event_packet:
                return

            digit = event_packet.get_digit()
            if not digit:
                return

            # Handle event based on end bit and sequence
            if event_packet.end:
                # End of DTMF event
                if self.last_event == digit:
                    # This is the end of the current event
                    self.logger.info(
                        f"RFC 2833 DTMF event completed: {digit} (duration: {event_packet.duration})"
                    )

                    # Deliver DTMF to PBX core
                    if self.pbx_core and self.call_id:
                        self.pbx_core.handle_dtmf_info(self.call_id, digit)

                    # Reset state
                    self.last_event = None
                    self.last_seq = None
                    self.event_start_time = None
            else:
                # Start or continuation of DTMF event
                if self.last_event != digit or self.last_seq is None:
                    # New event started
                    self.logger.debug(f"RFC 2833 DTMF event started: {digit}")
                    self.last_event = digit
                    self.event_start_time = time.time()

                self.last_seq = seq_num

        except (KeyError, TypeError, ValueError, struct.error) as e:
            self.logger.error(f"Error parsing RFC 2833 packet: {e}")


class RFC2833Sender:
    """
    RFC 2833 RTP Event Sender.

    Sends DTMF digits as RFC 2833 RTP events with configurable payload type (default 101).
    """

    def __init__(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        payload_type: int = 101,
    ) -> None:
        """
        Initialize RFC 2833 sender.

        Args:
            local_port: Local UDP port to send from.
            remote_host: Remote host to send to.
            remote_port: Remote port to send to.
            payload_type: RTP payload type for telephone-event (default: 101).
        """
        self.local_port: int = local_port
        self.remote_host: str = remote_host
        self.remote_port: int = remote_port
        self.payload_type: int = payload_type
        self.logger = get_logger()
        self.socket: socket.socket | None = None
        self.sequence_number: int = 0
        self.timestamp: int = 0
        self.ssrc: int = 0x87654321  # Synchronization source identifier

    def start(self) -> bool:
        """
        Start RFC 2833 sender.

        Returns:
            True if started successfully, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(
                ("0.0.0.0", self.local_port)  # nosec B104 - RTP needs to bind all interfaces
            )

            self.logger.info(f"RFC 2833 sender started on port {self.local_port}")
            return True
        except OSError as e:
            self.logger.error(f"Failed to start RFC 2833 sender: {e}")
            return False

    def stop(self) -> None:
        """Stop RFC 2833 sender."""
        if self.socket:
            with contextlib.suppress(BaseException):
                self.socket.close()
        self.logger.info(f"RFC 2833 sender stopped on port {self.local_port}")

    def send_dtmf(self, digit: str, duration_ms: int = 160) -> bool:
        """
        Send DTMF digit as RFC 2833 event.

        Args:
            digit: DTMF digit ('0'-'9', '*', '#', 'A'-'D').
            duration_ms: Duration in milliseconds (default 160ms).

        Returns:
            True if sent successfully.
        """
        if digit not in RFC2833_EVENT_CODES:
            self.logger.warning(f"Invalid DTMF digit for RFC 2833: {digit}")
            return False

        try:
            # Duration in timestamp units (SAMPLE_RATE_8KHZ)
            # 160ms = 1280 timestamp units at 8kHz
            duration_units = int((duration_ms / 1000.0) * SAMPLE_RATE_8KHZ)

            # Send event packet stream (3 packets: start, continuation, end)
            # This follows RFC 2833 recommendation to send multiple packets

            event_code = RFC2833_EVENT_CODES[digit]
            volume = 10  # Medium volume

            # Packet 1: Start (marker bit set in RTP header)
            event_packet = RFC2833EventPacket(event_code, end=False, volume=volume, duration=160)
            self._send_rtp_packet(event_packet.pack(), payload_type=self.payload_type, marker=True)
            time.sleep(0.02)  # 20ms

            # Packet 2: Continuation
            event_packet = RFC2833EventPacket(event_code, end=False, volume=volume, duration=320)
            self._send_rtp_packet(event_packet.pack(), payload_type=self.payload_type, marker=False)
            time.sleep(0.02)  # 20ms

            # Packet 3: End (end bit set, send 3 times for reliability)
            event_packet = RFC2833EventPacket(
                event_code, end=True, volume=volume, duration=duration_units
            )
            for _ in range(3):
                self._send_rtp_packet(
                    event_packet.pack(), payload_type=self.payload_type, marker=False
                )
                time.sleep(0.01)  # 10ms between end packets

            self.logger.info(f"Sent RFC 2833 DTMF digit: {digit}")
            return True

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error sending RFC 2833 DTMF: {e}")
            return False

    def _send_rtp_packet(
        self, payload: bytes, payload_type: int | None = None, marker: bool = False
    ) -> None:
        """
        Send RTP packet with RFC 2833 payload.

        Args:
            payload: RFC 2833 event payload.
            payload_type: RTP payload type (defaults to instance payload_type).
            marker: Marker bit.
        """
        # Use instance payload_type if not specified
        pt = payload_type if payload_type is not None else self.payload_type

        # Build RTP header
        version = 2
        padding = 0
        extension = 0
        csrc_count = 0

        byte0 = (version << 6) | (padding << 5) | (extension << 4) | csrc_count
        byte1 = (int(marker) << 7) | (pt & 0x7F)

        header = struct.pack(
            "!BBHII", byte0, byte1, self.sequence_number, self.timestamp, self.ssrc
        )

        packet = header + payload

        self.socket.sendto(packet, (self.remote_host, self.remote_port))

        # Update sequence number (timestamp stays same for event duration)
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
