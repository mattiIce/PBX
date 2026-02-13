"""
Test suite for RFC 2833 DTMF functionality
Validates RFC 2833 RTP event handling for DTMF signaling with payload type 101
"""

import struct


from pbx.rtp.rfc2833 import (
    RFC2833_CODE_TO_DIGIT,
    RFC2833_EVENT_CODES,
    RFC2833EventPacket,
    RFC2833Receiver,
    RFC2833Sender,
)


class TestRFC2833EventPacket:
    """Test RFC 2833 event packet encoding/decoding"""

    def test_event_codes_mapping(self) -> None:
        """Test that event codes are properly mapped"""
        # Test digit to code mapping
        assert RFC2833_EVENT_CODES["0"] == 0
        assert RFC2833_EVENT_CODES["1"] == 1
        assert RFC2833_EVENT_CODES["5"] == 5
        assert RFC2833_EVENT_CODES["9"] == 9
        assert RFC2833_EVENT_CODES["*"] == 10
        assert RFC2833_EVENT_CODES["#"] == 11
        assert RFC2833_EVENT_CODES["A"] == 12
        assert RFC2833_EVENT_CODES["D"] == 15
        # Test reverse mapping
        assert RFC2833_CODE_TO_DIGIT[0] == "0"
        assert RFC2833_CODE_TO_DIGIT[10] == "*"
        assert RFC2833_CODE_TO_DIGIT[11] == "#"
    def test_packet_creation_with_digit(self) -> None:
        """Test creating packet with DTMF digit"""
        packet = RFC2833EventPacket("5", end=False, volume=10, duration=160)
        assert packet.event == 5
        assert packet.end == False
        assert packet.volume == 10
        assert packet.duration == 160
        assert packet.get_digit() == "5"
    def test_packet_creation_with_star(self) -> None:
        """Test creating packet with * digit"""
        packet = RFC2833EventPacket("*", end=False, volume=10, duration=160)
        assert packet.event == 10
        assert packet.get_digit() == "*"
    def test_packet_creation_with_pound(self) -> None:
        """Test creating packet with # digit"""
        packet = RFC2833EventPacket("#", end=True, volume=10, duration=320)
        assert packet.event == 11
        assert packet.end == True
        assert packet.get_digit() == "#"
    def test_packet_creation_with_event_code(self) -> None:
        """Test creating packet with event code directly"""
        packet = RFC2833EventPacket(event=7, end=False, volume=5, duration=240)
        assert packet.event == 7
        assert packet.get_digit() == "7"
    def test_packet_pack_format(self) -> None:
        """Test that packet packs to correct 4-byte format"""
        packet = RFC2833EventPacket("3", end=False, volume=10, duration=160)
        data = packet.pack()

        # Should be exactly 4 bytes
        assert len(data) == 4
        # Unpack and verify structure
        event, byte2, duration = struct.unpack("!BBH", data)
        assert event == 3
        assert duration == 160
        # Check E bit (should be 0) and volume
        end_bit = bool(byte2 & 0x80)
        volume = byte2 & 0x3F
        assert end_bit == False
        assert volume == 10
    def test_packet_pack_with_end_bit(self) -> None:
        """Test packet packing with end bit set"""
        packet = RFC2833EventPacket("1", end=True, volume=15, duration=320)
        data = packet.pack()

        # Unpack and verify end bit
        event, byte2, duration = struct.unpack("!BBH", data)
        end_bit = bool(byte2 & 0x80)
        assert end_bit == True
        assert event == 1
        assert duration == 320
    def test_packet_unpack(self) -> None:
        """Test unpacking RFC 2833 event packet"""
        # Create a packet with known values
        original = RFC2833EventPacket("8", end=False, volume=12, duration=200)
        packed = original.pack()

        # Unpack it
        unpacked = RFC2833EventPacket.unpack(packed)

        assert unpacked is not None
        assert unpacked.event == 8
        assert unpacked.end == False
        assert unpacked.volume == 12
        assert unpacked.duration == 200
        assert unpacked.get_digit() == "8"
    def test_packet_unpack_with_end_bit(self) -> None:
        """Test unpacking packet with end bit set"""
        original = RFC2833EventPacket("9", end=True, volume=8, duration=480)
        packed = original.pack()

        unpacked = RFC2833EventPacket.unpack(packed)

        assert unpacked is not None
        assert unpacked.end == True
        assert unpacked.get_digit() == "9"
    def test_packet_unpack_invalid_data(self) -> None:
        """Test unpacking with invalid data"""
        # Too short
        result = RFC2833EventPacket.unpack(b"\x00\x00")
        assert result is None
        # Empty
        result = RFC2833EventPacket.unpack(b"")
        assert result is None
    def test_all_dtmf_digits(self) -> None:
        """Test packet creation and packing for all DTMF digits"""
        digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#"]

        for digit in digits:
            packet = RFC2833EventPacket(digit, end=False, volume=10, duration=160)
            data = packet.pack()

            # Verify pack/unpack round-trip
            unpacked = RFC2833EventPacket.unpack(data)
            assert unpacked is not None
            assert unpacked.get_digit() == digit
    def test_volume_range(self) -> None:
        """Test that volume is properly clamped to 6 bits (0-63)"""
        # Volume should be masked to 6 bits (0-63)
        packet = RFC2833EventPacket("1", end=False, volume=70, duration=160)
        data = packet.pack()

        unpacked = RFC2833EventPacket.unpack(data)
        # Volume should be masked: 70 & 0x3F = 6
        assert unpacked.volume == 6
    def test_duration_16bit(self) -> None:
        """Test that duration is properly handled as 16-bit value"""
        # Test maximum duration (65535)
        packet = RFC2833EventPacket("2", end=False, volume=10, duration=65535)
        data = packet.pack()

        unpacked = RFC2833EventPacket.unpack(data)
        assert unpacked.duration == 65535
class TestRFC2833Integration:
    """Integration tests for RFC 2833 components"""

    def test_rfc2833_receiver_initialization(self) -> None:
        """Test RFC 2833 receiver can be initialized"""
        receiver = RFC2833Receiver(local_port=20000)
        assert receiver.local_port == 20000
        assert not receiver.running
        assert receiver.last_event is None
    def test_rfc2833_sender_initialization(self) -> None:
        """Test RFC 2833 sender can be initialized"""
        sender = RFC2833Sender(local_port=20002, remote_host="127.0.0.1", remote_port=20003)
        assert sender.local_port == 20002
        assert sender.remote_host == "127.0.0.1"
        assert sender.remote_port == 20003
    def test_event_packet_roundtrip(self) -> None:
        """Test complete round-trip of event packet creation"""
        # Create event for each digit
        test_cases = [
            ("0", 0),
            ("1", 1),
            ("5", 5),
            ("9", 9),
            ("*", 10),
            ("#", 11),
            ("A", 12),
            ("D", 15),
        ]

        for digit, expected_code in test_cases:
            # Create packet
            packet = RFC2833EventPacket(digit, end=False, volume=10, duration=160)
            assert packet.event == expected_code
            # Pack and unpack
            packed = packet.pack()
            unpacked = RFC2833EventPacket.unpack(packed)

            # Verify
            assert unpacked is not None
            assert unpacked.get_digit() == digit
            assert unpacked.event == expected_code
    def test_rtp_packet_building(self) -> None:
        """Test that RFC 2833 can build valid RTP packet structure"""
        RFC2833Sender(local_port=20004, remote_host="127.0.0.1", remote_port=20005)

        # Create an event packet
        event_packet = RFC2833EventPacket("5", end=False, volume=10, duration=160)
        payload = event_packet.pack()

        # Verify payload is 4 bytes
        assert len(payload) == 4
        # Verify we can extract event from payload
        unpacked = RFC2833EventPacket.unpack(payload)
        assert unpacked.get_digit() == "5"
class TestRFC2833Compliance:
    """Test RFC 2833 compliance and specifications"""

    def test_payload_size_compliance(self) -> None:
        """Test that RFC 2833 payload is exactly 4 bytes per specification"""
        for digit in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#"]:
            packet = RFC2833EventPacket(digit)
            data = packet.pack()
            assert len(data) == 4, f"RFC 2833 payload must be 4 bytes for digit {digit}"
    def test_event_code_range(self) -> None:
        """Test that DTMF event codes are in valid range (0-15)"""
        for digit, code in RFC2833_EVENT_CODES.items():
            assert code >= 0
            assert code <= 15
    def test_end_bit_behavior(self) -> None:
        """Test that end bit is properly set and detected"""
        # Start packet
        start_packet = RFC2833EventPacket("3", end=False)
        start_data = start_packet.pack()
        start_unpacked = RFC2833EventPacket.unpack(start_data)
        assert not start_unpacked.end
        # End packet
        end_packet = RFC2833EventPacket("3", end=True)
        end_data = end_packet.pack()
        end_unpacked = RFC2833EventPacket.unpack(end_data)
        assert end_unpacked.end
    def test_reserved_bit_zero(self) -> None:
        """Test that reserved bit (R) is zero per RFC 2833"""
        packet = RFC2833EventPacket("7", end=False, volume=10)
        data = packet.pack()

        # Extract second byte
        byte2 = data[1]
        # R bit is bit 6 (0x40)
        r_bit = bool(byte2 & 0x40)
        assert not r_bit, "Reserved bit must be 0 per RFC 2833"
    def test_duration_timestamp_units(self) -> None:
        """Test that duration is in timestamp units (8kHz sample rate)"""
        # 20ms at 8kHz = 160 timestamp units
        packet = RFC2833EventPacket("1", duration=160)
        assert packet.duration == 160
        # 40ms at 8kHz = 320 timestamp units
        packet = RFC2833EventPacket("1", duration=320)
        assert packet.duration == 320
