"""
Test DTMF Payload Type Configuration
Tests configurable DTMF payload type functionality
"""

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pbx.features.phone_provisioning import PhoneTemplate
from pbx.rtp.rfc2833 import RFC2833EventPacket, RFC2833Receiver, RFC2833Sender
from pbx.sip.sdp import SDPBuilder, SDPSession


class TestDTMFPayloadTypeConfiguration(unittest.TestCase):
    """Test DTMF payload type configuration"""

    def test_sdp_builder_default_payload_type(self) -> None:
        """Test SDP builder uses default payload type 101"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100", local_port=10000, session_id="12345"
        )

        # Should include payload type 101
        self.assertIn("101", sdp)
        self.assertIn("rtpmap:101 telephone-event/8000", sdp)
        self.assertIn("fmtp:101 0-16", sdp)

    def test_sdp_builder_custom_payload_type_100(self) -> None:
        """Test SDP builder with custom payload type 100"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100", local_port=10000, session_id="12345", dtmf_payload_type=100
        )

        # Should include payload type 100 instead of 101
        self.assertIn("100", sdp)
        self.assertIn("rtpmap:100 telephone-event/8000", sdp)
        self.assertIn("fmtp:100 0-16", sdp)

        # Should NOT include 101
        self.assertNotIn("rtpmap:101", sdp)

    def test_sdp_builder_custom_payload_type_102(self) -> None:
        """Test SDP builder with custom payload type 102"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100", local_port=10000, session_id="12345", dtmf_payload_type=102
        )

        # Should include payload type 102
        self.assertIn("102", sdp)
        self.assertIn("rtpmap:102 telephone-event/8000", sdp)
        self.assertIn("fmtp:102 0-16", sdp)

    def test_sdp_builder_with_custom_codecs_and_payload_type(self) -> None:
        """Test SDP builder with custom codecs and payload type"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100",
            local_port=10000,
            session_id="12345",
            codecs=["0", "8", "100"],  # PCMU, PCMA, telephone-event on 100
            dtmf_payload_type=100,
        )

        # Should include custom codecs
        self.assertIn("m=audio 10000 RTP/AVP 0 8 100", sdp)
        self.assertIn("rtpmap:0 PCMU/8000", sdp)
        self.assertIn("rtpmap:8 PCMA/8000", sdp)
        self.assertIn("rtpmap:100 telephone-event/8000", sdp)

    def test_rfc2833_receiver_default_payload_type(self) -> None:
        """Test RFC2833 receiver with default payload type"""
        receiver = RFC2833Receiver(local_port=10000)
        self.assertEqual(receiver.payload_type, 101)

    def test_rfc2833_receiver_custom_payload_type(self) -> None:
        """Test RFC2833 receiver with custom payload type"""
        receiver = RFC2833Receiver(local_port=10000, payload_type=100)
        self.assertEqual(receiver.payload_type, 100)

    def test_rfc2833_sender_default_payload_type(self) -> None:
        """Test RFC2833 sender with default payload type"""
        sender = RFC2833Sender(local_port=10000, remote_host="192.168.1.200", remote_port=20000)
        self.assertEqual(sender.payload_type, 101)

    def test_rfc2833_sender_custom_payload_type(self) -> None:
        """Test RFC2833 sender with custom payload type"""
        sender = RFC2833Sender(
            local_port=10000, remote_host="192.168.1.200", remote_port=20000, payload_type=102
        )
        self.assertEqual(sender.payload_type, 102)

    def test_phone_template_dtmf_payload_replacement(self) -> None:
        """Test phone template replaces DTMF payload type placeholder"""
        template_content = """
# DTMF Configuration
account.1.dtmf.type = 2
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}
"""
        template = PhoneTemplate("zultys", "zip33g", template_content)

        # Test with payload type 100
        config = template.generate_config(
            extension_config={"number": "1501", "name": "Test User", "password": "secret"},
            server_config={
                "sip_host": "192.168.1.1",
                "sip_port": 5060,
                "server_name": "Test PBX",
                "dtmf": {"payload_type": 100},
            },
        )

        self.assertIn("account.1.dtmf.dtmf_payload = 100", config)
        self.assertNotIn("{{DTMF_PAYLOAD_TYPE}}", config)

    def test_phone_template_dtmf_payload_default(self) -> None:
        """Test phone template uses default 101 when not configured"""
        template_content = """
# DTMF Configuration
account.1.dtmf.type = 2
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}
"""
        template = PhoneTemplate("zultys", "zip33g", template_content)

        # Test without dtmf config (should default to 101)
        config = template.generate_config(
            extension_config={"number": "1501", "name": "Test User", "password": "secret"},
            server_config={"sip_host": "192.168.1.1", "sip_port": 5060, "server_name": "Test PBX"},
        )

        self.assertIn("account.1.dtmf.dtmf_payload = 101", config)

    def test_rfc2833_event_packet_independence(self) -> None:
        """Test RFC2833 event packet is independent of payload type"""
        # Event packet structure should be same regardless of payload type
        event1 = RFC2833EventPacket(event="5", end=False, volume=10, duration=160)
        event2 = RFC2833EventPacket(event="5", end=False, volume=10, duration=160)

        # Both should pack to same payload
        self.assertEqual(event1.pack(), event2.pack())

        # Payload type only affects RTP header, not RFC2833 payload
        self.assertEqual(len(event1.pack()), 4)  # Always 4 bytes

    def test_sdp_parser_with_alternative_payload_type(self) -> None:
        """Test SDP parser handles alternative DTMF payload types"""
        sdp_body = """v=0
o=test 123456 0 IN IP4 192.168.1.100
s=Test
c=IN IP4 192.168.1.100
t=0 0
m=audio 10000 RTP/AVP 0 8 100
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:100 telephone-event/8000
a=fmtp:100 0-16
"""
        session = SDPSession()
        session.parse(sdp_body)

        # Should parse payload type 100
        audio_info = session.get_audio_info()
        self.assertIsNotNone(audio_info)
        self.assertIn("100", audio_info["formats"])


class TestDTMFPayloadTypeValidation(unittest.TestCase):
    """Test DTMF payload type validation"""

    def test_valid_payload_type_range(self) -> None:
        """Test valid dynamic payload type range (96-127)"""
        valid_types = [96, 100, 101, 102, 127]

        for pt in valid_types:
            # Should not raise exception
            sdp = SDPBuilder.build_audio_sdp(
                local_ip="192.168.1.100", local_port=10000, dtmf_payload_type=pt
            )
            self.assertIn(str(pt), sdp)

    def test_standard_payload_type_101(self) -> None:
        """Test standard RFC2833 payload type 101"""
        # 101 is the RFC standard for telephone-event
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100", local_port=10000, dtmf_payload_type=101
        )

        self.assertIn("rtpmap:101 telephone-event/8000", sdp)


if __name__ == "__main__":
    unittest.main()
