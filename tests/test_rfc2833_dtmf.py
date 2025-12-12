"""
Test suite for RFC 2833 DTMF functionality
Validates RFC 2833 RTP event handling for DTMF signaling with payload type 101
"""
import os
import struct
import sys
import time
import unittest

from pbx.rtp.rfc2833 import (
    RFC2833_CODE_TO_DIGIT,
    RFC2833_EVENT_CODES,
    RFC2833EventPacket,
    RFC2833Receiver,
    RFC2833Sender,
)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRFC2833EventPacket(unittest.TestCase):
    """Test RFC 2833 event packet encoding/decoding"""

    def test_event_codes_mapping(self):
        """Test that event codes are properly mapped"""
        # Test digit to code mapping
        self.assertEqual(RFC2833_EVENT_CODES['0'], 0)
        self.assertEqual(RFC2833_EVENT_CODES['1'], 1)
        self.assertEqual(RFC2833_EVENT_CODES['5'], 5)
        self.assertEqual(RFC2833_EVENT_CODES['9'], 9)
        self.assertEqual(RFC2833_EVENT_CODES['*'], 10)
        self.assertEqual(RFC2833_EVENT_CODES['#'], 11)
        self.assertEqual(RFC2833_EVENT_CODES['A'], 12)
        self.assertEqual(RFC2833_EVENT_CODES['D'], 15)

        # Test reverse mapping
        self.assertEqual(RFC2833_CODE_TO_DIGIT[0], '0')
        self.assertEqual(RFC2833_CODE_TO_DIGIT[10], '*')
        self.assertEqual(RFC2833_CODE_TO_DIGIT[11], '#')

    def test_packet_creation_with_digit(self):
        """Test creating packet with DTMF digit"""
        packet = RFC2833EventPacket('5', end=False, volume=10, duration=160)
        self.assertEqual(packet.event, 5)
        self.assertEqual(packet.end, False)
        self.assertEqual(packet.volume, 10)
        self.assertEqual(packet.duration, 160)
        self.assertEqual(packet.get_digit(), '5')

    def test_packet_creation_with_star(self):
        """Test creating packet with * digit"""
        packet = RFC2833EventPacket('*', end=False, volume=10, duration=160)
        self.assertEqual(packet.event, 10)
        self.assertEqual(packet.get_digit(), '*')

    def test_packet_creation_with_pound(self):
        """Test creating packet with # digit"""
        packet = RFC2833EventPacket('#', end=True, volume=10, duration=320)
        self.assertEqual(packet.event, 11)
        self.assertEqual(packet.end, True)
        self.assertEqual(packet.get_digit(), '#')

    def test_packet_creation_with_event_code(self):
        """Test creating packet with event code directly"""
        packet = RFC2833EventPacket(event=7, end=False, volume=5, duration=240)
        self.assertEqual(packet.event, 7)
        self.assertEqual(packet.get_digit(), '7')

    def test_packet_pack_format(self):
        """Test that packet packs to correct 4-byte format"""
        packet = RFC2833EventPacket('3', end=False, volume=10, duration=160)
        data = packet.pack()

        # Should be exactly 4 bytes
        self.assertEqual(len(data), 4)

        # Unpack and verify structure
        event, byte2, duration = struct.unpack('!BBH', data)
        self.assertEqual(event, 3)
        self.assertEqual(duration, 160)

        # Check E bit (should be 0) and volume
        end_bit = bool(byte2 & 0x80)
        volume = byte2 & 0x3F
        self.assertEqual(end_bit, False)
        self.assertEqual(volume, 10)

    def test_packet_pack_with_end_bit(self):
        """Test packet packing with end bit set"""
        packet = RFC2833EventPacket('1', end=True, volume=15, duration=320)
        data = packet.pack()

        # Unpack and verify end bit
        event, byte2, duration = struct.unpack('!BBH', data)
        end_bit = bool(byte2 & 0x80)
        self.assertEqual(end_bit, True)
        self.assertEqual(event, 1)
        self.assertEqual(duration, 320)

    def test_packet_unpack(self):
        """Test unpacking RFC 2833 event packet"""
        # Create a packet with known values
        original = RFC2833EventPacket('8', end=False, volume=12, duration=200)
        packed = original.pack()

        # Unpack it
        unpacked = RFC2833EventPacket.unpack(packed)

        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked.event, 8)
        self.assertEqual(unpacked.end, False)
        self.assertEqual(unpacked.volume, 12)
        self.assertEqual(unpacked.duration, 200)
        self.assertEqual(unpacked.get_digit(), '8')

    def test_packet_unpack_with_end_bit(self):
        """Test unpacking packet with end bit set"""
        original = RFC2833EventPacket('9', end=True, volume=8, duration=480)
        packed = original.pack()

        unpacked = RFC2833EventPacket.unpack(packed)

        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked.end, True)
        self.assertEqual(unpacked.get_digit(), '9')

    def test_packet_unpack_invalid_data(self):
        """Test unpacking with invalid data"""
        # Too short
        result = RFC2833EventPacket.unpack(b'\x00\x00')
        self.assertIsNone(result)

        # Empty
        result = RFC2833EventPacket.unpack(b'')
        self.assertIsNone(result)

    def test_all_dtmf_digits(self):
        """Test packet creation and packing for all DTMF digits"""
        digits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '#']

        for digit in digits:
            packet = RFC2833EventPacket(
                digit, end=False, volume=10, duration=160)
            data = packet.pack()

            # Verify pack/unpack round-trip
            unpacked = RFC2833EventPacket.unpack(data)
            self.assertIsNotNone(unpacked)
            self.assertEqual(unpacked.get_digit(), digit)

    def test_volume_range(self):
        """Test that volume is properly clamped to 6 bits (0-63)"""
        # Volume should be masked to 6 bits (0-63)
        packet = RFC2833EventPacket('1', end=False, volume=70, duration=160)
        data = packet.pack()

        unpacked = RFC2833EventPacket.unpack(data)
        # Volume should be masked: 70 & 0x3F = 6
        self.assertEqual(unpacked.volume, 6)

    def test_duration_16bit(self):
        """Test that duration is properly handled as 16-bit value"""
        # Test maximum duration (65535)
        packet = RFC2833EventPacket('2', end=False, volume=10, duration=65535)
        data = packet.pack()

        unpacked = RFC2833EventPacket.unpack(data)
        self.assertEqual(unpacked.duration, 65535)


class TestRFC2833Integration(unittest.TestCase):
    """Integration tests for RFC 2833 components"""

    def test_rfc2833_receiver_initialization(self):
        """Test RFC 2833 receiver can be initialized"""
        receiver = RFC2833Receiver(local_port=20000)
        self.assertEqual(receiver.local_port, 20000)
        self.assertFalse(receiver.running)
        self.assertIsNone(receiver.last_event)

    def test_rfc2833_sender_initialization(self):
        """Test RFC 2833 sender can be initialized"""
        sender = RFC2833Sender(
            local_port=20002,
            remote_host='127.0.0.1',
            remote_port=20003
        )
        self.assertEqual(sender.local_port, 20002)
        self.assertEqual(sender.remote_host, '127.0.0.1')
        self.assertEqual(sender.remote_port, 20003)

    def test_event_packet_roundtrip(self):
        """Test complete round-trip of event packet creation"""
        # Create event for each digit
        test_cases = [
            ('0', 0), ('1', 1), ('5', 5), ('9', 9),
            ('*', 10), ('#', 11), ('A', 12), ('D', 15)
        ]

        for digit, expected_code in test_cases:
            # Create packet
            packet = RFC2833EventPacket(
                digit, end=False, volume=10, duration=160)
            self.assertEqual(packet.event, expected_code)

            # Pack and unpack
            packed = packet.pack()
            unpacked = RFC2833EventPacket.unpack(packed)

            # Verify
            self.assertIsNotNone(unpacked)
            self.assertEqual(unpacked.get_digit(), digit)
            self.assertEqual(unpacked.event, expected_code)

    def test_rtp_packet_building(self):
        """Test that RFC 2833 can build valid RTP packet structure"""
        sender = RFC2833Sender(
            local_port=20004,
            remote_host='127.0.0.1',
            remote_port=20005
        )

        # Create an event packet
        event_packet = RFC2833EventPacket(
            '5', end=False, volume=10, duration=160)
        payload = event_packet.pack()

        # Verify payload is 4 bytes
        self.assertEqual(len(payload), 4)

        # Verify we can extract event from payload
        unpacked = RFC2833EventPacket.unpack(payload)
        self.assertEqual(unpacked.get_digit(), '5')


class TestRFC2833Compliance(unittest.TestCase):
    """Test RFC 2833 compliance and specifications"""

    def test_payload_size_compliance(self):
        """Test that RFC 2833 payload is exactly 4 bytes per specification"""
        for digit in [
            '0',
            '1',
            '2',
            '3',
            '4',
            '5',
            '6',
            '7',
            '8',
            '9',
            '*',
                '#']:
            packet = RFC2833EventPacket(digit)
            data = packet.pack()
            self.assertEqual(
                len(data),
                4,
                f"RFC 2833 payload must be 4 bytes for digit {digit}")

    def test_event_code_range(self):
        """Test that DTMF event codes are in valid range (0-15)"""
        for digit, code in RFC2833_EVENT_CODES.items():
            self.assertGreaterEqual(code, 0)
            self.assertLessEqual(code, 15)

    def test_end_bit_behavior(self):
        """Test that end bit is properly set and detected"""
        # Start packet
        start_packet = RFC2833EventPacket('3', end=False)
        start_data = start_packet.pack()
        start_unpacked = RFC2833EventPacket.unpack(start_data)
        self.assertFalse(start_unpacked.end)

        # End packet
        end_packet = RFC2833EventPacket('3', end=True)
        end_data = end_packet.pack()
        end_unpacked = RFC2833EventPacket.unpack(end_data)
        self.assertTrue(end_unpacked.end)

    def test_reserved_bit_zero(self):
        """Test that reserved bit (R) is zero per RFC 2833"""
        packet = RFC2833EventPacket('7', end=False, volume=10)
        data = packet.pack()

        # Extract second byte
        byte2 = data[1]
        # R bit is bit 6 (0x40)
        r_bit = bool(byte2 & 0x40)
        self.assertFalse(r_bit, "Reserved bit must be 0 per RFC 2833")

    def test_duration_timestamp_units(self):
        """Test that duration is in timestamp units (8kHz sample rate)"""
        # 20ms at 8kHz = 160 timestamp units
        packet = RFC2833EventPacket('1', duration=160)
        self.assertEqual(packet.duration, 160)

        # 40ms at 8kHz = 320 timestamp units
        packet = RFC2833EventPacket('1', duration=320)
        self.assertEqual(packet.duration, 320)


if __name__ == '__main__':
    unittest.main()
