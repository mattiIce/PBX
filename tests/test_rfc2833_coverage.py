"""Comprehensive tests for RFC 2833 RTP Event Handler for DTMF Signaling."""

import struct
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestRFC2833Constants:
    """Tests for RFC 2833 module-level constants."""

    def test_event_codes(self) -> None:
        """Test DTMF event codes mapping."""
        from pbx.rtp.rfc2833 import RFC2833_EVENT_CODES

        assert RFC2833_EVENT_CODES["0"] == 0
        assert RFC2833_EVENT_CODES["9"] == 9
        assert RFC2833_EVENT_CODES["*"] == 10
        assert RFC2833_EVENT_CODES["#"] == 11
        assert RFC2833_EVENT_CODES["A"] == 12
        assert RFC2833_EVENT_CODES["D"] == 15

    def test_code_to_digit(self) -> None:
        """Test reverse mapping from code to digit."""
        from pbx.rtp.rfc2833 import RFC2833_CODE_TO_DIGIT

        assert RFC2833_CODE_TO_DIGIT[0] == "0"
        assert RFC2833_CODE_TO_DIGIT[10] == "*"
        assert RFC2833_CODE_TO_DIGIT[11] == "#"
        assert RFC2833_CODE_TO_DIGIT[15] == "D"

    def test_constants(self) -> None:
        """Test constants."""
        from pbx.rtp.rfc2833 import PAYLOAD_TYPE_TELEPHONE_EVENT, SAMPLE_RATE_8KHZ

        assert SAMPLE_RATE_8KHZ == 8000
        assert PAYLOAD_TYPE_TELEPHONE_EVENT == 101


@pytest.mark.unit
class TestRFC2833EventPacket:
    """Tests for RFC2833EventPacket."""

    def test_init_with_string_digit(self) -> None:
        """Test initialization with a string digit."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event="5", end=False, volume=10, duration=160)

        assert pkt.event == 5
        assert pkt.end is False
        assert pkt.volume == 10
        assert pkt.duration == 160

    def test_init_with_string_star(self) -> None:
        """Test initialization with star character."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event="*")

        assert pkt.event == 10

    def test_init_with_string_hash(self) -> None:
        """Test initialization with hash character."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event="#")

        assert pkt.event == 11

    def test_init_with_lowercase_letter(self) -> None:
        """Test initialization with lowercase letter converts to uppercase."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event="a")

        assert pkt.event == 12

    def test_init_with_int_event(self) -> None:
        """Test initialization with integer event code."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event=7)

        assert pkt.event == 7

    def test_init_with_none_event(self) -> None:
        """Test initialization with None event."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event=None)

        assert pkt.event == 0

    def test_init_with_invalid_string(self) -> None:
        """Test initialization with invalid string defaults to 0."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event="Z")

        assert pkt.event == 0

    def test_pack(self) -> None:
        """Test packing into bytes."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event=1, end=False, volume=10, duration=160)
        data = pkt.pack()

        assert len(data) == 4
        event, byte2, duration = struct.unpack("!BBH", data)
        assert event == 1
        assert byte2 == 10  # end=0, volume=10
        assert duration == 160

    def test_pack_with_end_bit(self) -> None:
        """Test packing with end bit set."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event=5, end=True, volume=10, duration=1280)
        data = pkt.pack()

        event, byte2, duration = struct.unpack("!BBH", data)
        assert event == 5
        assert byte2 & 0x80  # end bit set
        assert (byte2 & 0x3F) == 10  # volume
        assert duration == 1280

    def test_unpack_valid(self) -> None:
        """Test unpacking valid data."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        # Event=1, end=True, volume=10, duration=160
        data = struct.pack("!BBH", 1, 0x8A, 160)
        pkt = RFC2833EventPacket.unpack(data)

        assert pkt is not None
        assert pkt.event == 1
        assert pkt.end is True
        assert pkt.volume == 10
        assert pkt.duration == 160

    def test_unpack_too_short(self) -> None:
        """Test unpacking data that is too short."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        result = RFC2833EventPacket.unpack(b"\x00\x00")

        assert result is None

    def test_unpack_longer_data(self) -> None:
        """Test unpacking with extra data (only first 4 bytes used)."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        data = struct.pack("!BBH", 3, 0x0A, 320) + b"\x00\x00"
        pkt = RFC2833EventPacket.unpack(data)

        assert pkt is not None
        assert pkt.event == 3

    def test_pack_unpack_roundtrip(self) -> None:
        """Test pack/unpack roundtrip."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        original = RFC2833EventPacket(event=9, end=True, volume=15, duration=640)
        data = original.pack()
        unpacked = RFC2833EventPacket.unpack(data)

        assert unpacked is not None
        assert unpacked.event == original.event
        assert unpacked.end == original.end
        assert unpacked.volume == original.volume
        assert unpacked.duration == original.duration

    def test_get_digit_valid(self) -> None:
        """Test get_digit with valid event code."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event=5)
        assert pkt.get_digit() == "5"

        pkt = RFC2833EventPacket(event=10)
        assert pkt.get_digit() == "*"

        pkt = RFC2833EventPacket(event=11)
        assert pkt.get_digit() == "#"

    def test_get_digit_invalid(self) -> None:
        """Test get_digit with invalid event code."""
        from pbx.rtp.rfc2833 import RFC2833EventPacket

        pkt = RFC2833EventPacket(event=99)
        assert pkt.get_digit() is None


@pytest.mark.unit
class TestRFC2833Receiver:
    """Tests for RFC2833Receiver."""

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_init(self, mock_get_logger: MagicMock) -> None:
        """Test receiver initialization."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000, call_id="call-1", payload_type=101)

        assert receiver.local_port == 5000
        assert receiver.call_id == "call-1"
        assert receiver.payload_type == 101
        assert receiver.running is False
        assert receiver.last_event is None

    @patch("pbx.rtp.rfc2833.socket.socket")
    @patch("pbx.rtp.rfc2833.get_logger")
    def test_start_success(self, mock_get_logger: MagicMock, mock_socket_class: MagicMock) -> None:
        """Test successful receiver start."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        mock_sock = MagicMock()
        # Make recvfrom block properly so thread doesn't crash
        mock_sock.recvfrom.side_effect = TimeoutError()
        mock_socket_class.return_value = mock_sock

        receiver = RFC2833Receiver(local_port=5000)
        result = receiver.start()

        assert result is True
        assert receiver.running is True
        mock_sock.bind.assert_called_once()

        # Stop receiver to clean up thread
        receiver.stop()

    @patch("pbx.rtp.rfc2833.socket.socket")
    @patch("pbx.rtp.rfc2833.get_logger")
    def test_start_failure(self, mock_get_logger: MagicMock, mock_socket_class: MagicMock) -> None:
        """Test receiver start failure."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError("Port in use")
        mock_socket_class.return_value = mock_sock

        receiver = RFC2833Receiver(local_port=5000)
        result = receiver.start()

        assert result is False

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_stop(self, mock_get_logger: MagicMock) -> None:
        """Test receiver stop."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000)
        receiver.running = True
        receiver.socket = MagicMock()

        receiver.stop()

        assert receiver.running is False
        receiver.socket.close.assert_called_once()

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_stop_no_socket(self, mock_get_logger: MagicMock) -> None:
        """Test stop without socket."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000)
        receiver.running = True
        receiver.socket = None

        receiver.stop()

        assert receiver.running is False

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_handle_rtp_packet_too_short(self, mock_get_logger: MagicMock) -> None:
        """Test handling packet that is too short."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000)
        receiver.handle_rtp_packet(b"\x00" * 10, ("192.168.1.1", 5000))

        # Should return without processing

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_handle_rtp_packet_wrong_payload_type(self, mock_get_logger: MagicMock) -> None:
        """Test handling packet with wrong payload type."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000, payload_type=101)

        # Build RTP header with payload type 0 (not 101)
        header = struct.pack("!BBHII", 0x80, 0, 1, 160, 0x12345678)
        payload = struct.pack("!BBH", 1, 0x00, 160)

        receiver.handle_rtp_packet(header + payload, ("192.168.1.1", 5000))

        # Should not process since payload type doesn't match

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_handle_rtp_packet_dtmf_start(self, mock_get_logger: MagicMock) -> None:
        """Test handling DTMF start event."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000, payload_type=101)

        # RTP header: version=2, payload_type=101, seq=1, timestamp=160, ssrc=0x12345678
        header = struct.pack("!BBHII", 0x80, 101, 1, 160, 0x12345678)
        # RFC 2833 payload: event=5, end=False, volume=10, duration=160
        payload = struct.pack("!BBH", 5, 0x0A, 160)

        receiver.handle_rtp_packet(header + payload, ("192.168.1.1", 5000))

        assert receiver.last_event == "5"
        assert receiver.last_seq == 1

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_handle_rtp_packet_dtmf_end(self, mock_get_logger: MagicMock) -> None:
        """Test handling DTMF end event."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        pbx_core = MagicMock()
        receiver = RFC2833Receiver(
            local_port=5000, pbx_core=pbx_core, call_id="call-1", payload_type=101
        )

        # Simulate start event first
        receiver.last_event = "5"
        receiver.last_seq = 1

        # RTP header with payload_type=101
        header = struct.pack("!BBHII", 0x80, 101, 2, 320, 0x12345678)
        # RFC 2833 payload: event=5, end=True, volume=10, duration=1280
        payload = struct.pack("!BBH", 5, 0x8A, 1280)

        receiver.handle_rtp_packet(header + payload, ("192.168.1.1", 5000))

        # Should deliver DTMF to PBX core
        pbx_core.handle_dtmf_info.assert_called_once_with("call-1", "5")
        assert receiver.last_event is None

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_handle_rtp_packet_dtmf_end_no_pbx(self, mock_get_logger: MagicMock) -> None:
        """Test handling DTMF end without PBX core."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000, payload_type=101)
        receiver.last_event = "5"
        receiver.last_seq = 1

        header = struct.pack("!BBHII", 0x80, 101, 2, 320, 0x12345678)
        payload = struct.pack("!BBH", 5, 0x8A, 1280)

        receiver.handle_rtp_packet(header + payload, ("192.168.1.1", 5000))

        # Should complete without error
        assert receiver.last_event is None

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_handle_rtp_packet_short_payload(self, mock_get_logger: MagicMock) -> None:
        """Test handling packet with short payload."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000, payload_type=101)

        header = struct.pack("!BBHII", 0x80, 101, 1, 160, 0x12345678)
        # Short payload (only 2 bytes instead of 4)
        payload = b"\x00\x00"

        receiver.handle_rtp_packet(header + payload, ("192.168.1.1", 5000))

        # Should return without processing (payload too short)

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_handle_rtp_packet_new_digit_replaces_old(self, mock_get_logger: MagicMock) -> None:
        """Test handling new DTMF digit replaces old one."""
        from pbx.rtp.rfc2833 import RFC2833Receiver

        receiver = RFC2833Receiver(local_port=5000, payload_type=101)
        receiver.last_event = "3"
        receiver.last_seq = 1

        # New digit "7" start event
        header = struct.pack("!BBHII", 0x80, 101, 5, 1600, 0x12345678)
        payload = struct.pack("!BBH", 7, 0x0A, 160)

        receiver.handle_rtp_packet(header + payload, ("192.168.1.1", 5000))

        assert receiver.last_event == "7"


@pytest.mark.unit
class TestRFC2833Sender:
    """Tests for RFC2833Sender."""

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_init(self, mock_get_logger: MagicMock) -> None:
        """Test sender initialization."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        sender = RFC2833Sender(
            local_port=6000, remote_host="192.168.1.1", remote_port=5000, payload_type=101
        )

        assert sender.local_port == 6000
        assert sender.remote_host == "192.168.1.1"
        assert sender.remote_port == 5000
        assert sender.payload_type == 101
        assert sender.sequence_number == 0
        assert sender.timestamp == 0

    @patch("pbx.rtp.rfc2833.socket.socket")
    @patch("pbx.rtp.rfc2833.get_logger")
    def test_start_success(self, mock_get_logger: MagicMock, mock_socket_class: MagicMock) -> None:
        """Test successful sender start."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        sender = RFC2833Sender(local_port=6000, remote_host="192.168.1.1", remote_port=5000)
        result = sender.start()

        assert result is True
        mock_sock.bind.assert_called_once()

    @patch("pbx.rtp.rfc2833.socket.socket")
    @patch("pbx.rtp.rfc2833.get_logger")
    def test_start_failure(self, mock_get_logger: MagicMock, mock_socket_class: MagicMock) -> None:
        """Test sender start failure."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        mock_socket_class.side_effect = OSError("Port in use")

        sender = RFC2833Sender(local_port=6000, remote_host="192.168.1.1", remote_port=5000)
        result = sender.start()

        assert result is False

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_stop(self, mock_get_logger: MagicMock) -> None:
        """Test sender stop."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        sender = RFC2833Sender(local_port=6000, remote_host="192.168.1.1", remote_port=5000)
        sender.socket = MagicMock()

        sender.stop()

        sender.socket.close.assert_called_once()

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_stop_no_socket(self, mock_get_logger: MagicMock) -> None:
        """Test stop without socket."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        sender = RFC2833Sender(local_port=6000, remote_host="192.168.1.1", remote_port=5000)
        sender.socket = None

        sender.stop()
        # Should not raise

    @patch("pbx.rtp.rfc2833.time.sleep")
    @patch("pbx.rtp.rfc2833.get_logger")
    def test_send_dtmf_success(self, mock_get_logger: MagicMock, mock_sleep: MagicMock) -> None:
        """Test successful DTMF sending."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        sender = RFC2833Sender(local_port=6000, remote_host="192.168.1.1", remote_port=5000)
        sender.socket = MagicMock()

        result = sender.send_dtmf("5", duration_ms=160)

        assert result is True
        # 5 packets total: start, continuation, 3x end
        assert sender.socket.sendto.call_count == 5
        assert sender.sequence_number == 5

    @patch("pbx.rtp.rfc2833.time.sleep")
    @patch("pbx.rtp.rfc2833.get_logger")
    def test_send_dtmf_star(self, mock_get_logger: MagicMock, mock_sleep: MagicMock) -> None:
        """Test sending star DTMF digit."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        sender = RFC2833Sender(local_port=6000, remote_host="192.168.1.1", remote_port=5000)
        sender.socket = MagicMock()

        result = sender.send_dtmf("*")

        assert result is True

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_send_dtmf_invalid_digit(self, mock_get_logger: MagicMock) -> None:
        """Test sending invalid DTMF digit."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        sender = RFC2833Sender(local_port=6000, remote_host="192.168.1.1", remote_port=5000)
        sender.socket = MagicMock()

        result = sender.send_dtmf("Z")

        assert result is False

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_send_rtp_packet(self, mock_get_logger: MagicMock) -> None:
        """Test internal RTP packet sending."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        sender = RFC2833Sender(
            local_port=6000, remote_host="192.168.1.1", remote_port=5000, payload_type=101
        )
        sender.socket = MagicMock()

        payload = b"\x01\x0a\x00\xa0"  # event=1, volume=10, duration=160
        sender._send_rtp_packet(payload, payload_type=101, marker=True)

        sender.socket.sendto.assert_called_once()
        sent_data = sender.socket.sendto.call_args[0][0]
        # RTP header (12 bytes) + payload (4 bytes)
        assert len(sent_data) == 16

        # Verify header
        header = struct.unpack("!BBHII", sent_data[:12])
        assert (header[0] >> 6) & 0x03 == 2  # version
        assert header[1] & 0x7F == 101  # payload type
        assert bool(header[1] & 0x80) is True  # marker

    @patch("pbx.rtp.rfc2833.get_logger")
    def test_send_rtp_packet_default_payload_type(self, mock_get_logger: MagicMock) -> None:
        """Test RTP packet with default payload type."""
        from pbx.rtp.rfc2833 import RFC2833Sender

        sender = RFC2833Sender(
            local_port=6000, remote_host="192.168.1.1", remote_port=5000, payload_type=96
        )
        sender.socket = MagicMock()

        sender._send_rtp_packet(b"\x00" * 4)

        sent_data = sender.socket.sendto.call_args[0][0]
        header = struct.unpack("!BBHII", sent_data[:12])
        assert header[1] & 0x7F == 96  # Uses instance payload_type
