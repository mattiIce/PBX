"""
Integration test for SIP Send Line and Send MAC in PBX Core
Tests that headers are properly added during call routing
"""

import unittest
from unittest.mock import MagicMock, Mock, patch

from pbx.core.pbx import PBXCore
from pbx.sip.message import SIPMessage


class TestSIPSendLineIntegration(unittest.TestCase):
    """Integration tests for SIP send line and MAC in call routing"""

    def setUp(self):
        """Set up test environment"""
        import os
        import tempfile

        # Create a unique temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        self.temp_config_path = self.temp_config.name

        # Create a minimal test config
        self.temp_config.write(
            """
server:
  sip_host: 0.0.0.0
  sip_port: 5060
  external_ip: 192.168.1.100
  rtp_port_range_start: 10000
  rtp_port_range_end: 20000

sip:
  caller_id:
    send_p_asserted_identity: true
    send_remote_party_id: true
  device:
    send_mac_address: true
    accept_mac_in_invite: true

database:
  type: sqlite
  path: ":memory:"

features:
  voicemail: false
  call_recording: false

logging:
  level: ERROR
  console: false
"""
        )
        self.temp_config.close()

    def tearDown(self):
        """Clean up test environment"""
        import os

        if os.path.exists(self.temp_config_path):
            os.remove(self.temp_config_path)

    def test_invite_includes_caller_id_headers(self):
        """Test that INVITE messages include P-Asserted-Identity and Remote-Party-ID"""
        # This is a simplified test that verifies the header generation logic
        # Full integration would require a running PBX instance

        from pbx.sip.message import SIPMessageBuilder

        # Simulate what PBX does when routing a call
        invite = SIPMessageBuilder.build_request(
            method="INVITE",
            uri="sip:1002@192.168.1.100",
            from_addr="<sip:1001@192.168.1.100>",
            to_addr="<sip:1002@192.168.1.100>",
            call_id="test-call-123",
            cseq=1,
            body="",
        )

        # Add caller ID headers (as PBX would)
        SIPMessageBuilder.add_caller_id_headers(
            invite, extension_number="1001", display_name="John Doe", server_ip="192.168.1.100"
        )

        # Verify headers are present
        self.assertIsNotNone(invite.get_header("P-Asserted-Identity"))
        self.assertIsNotNone(invite.get_header("Remote-Party-ID"))

        # Verify header content
        pai = invite.get_header("P-Asserted-Identity")
        self.assertIn("John Doe", pai)
        self.assertIn("sip:1001@192.168.1.100", pai)

        rpid = invite.get_header("Remote-Party-ID")
        self.assertIn("John Doe", rpid)
        self.assertIn("party=calling", rpid)

    def test_invite_includes_mac_address_header(self):
        """Test that INVITE messages include X-MAC-Address when available"""
        from pbx.sip.message import SIPMessageBuilder

        invite = SIPMessageBuilder.build_request(
            method="INVITE",
            uri="sip:1002@192.168.1.100",
            from_addr="<sip:1001@192.168.1.100>",
            to_addr="<sip:1002@192.168.1.100>",
            call_id="test-call-456",
            cseq=1,
            body="",
        )

        # Add MAC address header (as PBX would if MAC is known)
        SIPMessageBuilder.add_mac_address_header(invite, mac_address="00:11:22:33:44:55")

        # Verify header is present
        self.assertIsNotNone(invite.get_header("X-MAC-Address"))
        self.assertEqual(invite.get_header("X-MAC-Address"), "00:11:22:33:44:55")

    def test_config_defaults_enable_features(self):
        """Test that features are enabled by default"""
        from pbx.utils.config import Config

        config = Config(self.temp_config_path)

        # Verify defaults
        self.assertTrue(config.get("sip.caller_id.send_p_asserted_identity", True))
        self.assertTrue(config.get("sip.caller_id.send_remote_party_id", True))
        self.assertTrue(config.get("sip.device.send_mac_address", True))
        self.assertTrue(config.get("sip.device.accept_mac_in_invite", True))

    def test_mac_address_accepted_from_invite(self):
        """Test that MAC address can be read from incoming INVITE"""
        raw_invite = (
            "INVITE sip:1002@192.168.1.100 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.50:5060\r\n"
            "From: <sip:1001@192.168.1.100>\r\n"
            "To: <sip:1002@192.168.1.100>\r\n"
            "Call-ID: test-789\r\n"
            "CSeq: 1 INVITE\r\n"
            "X-MAC-Address: aa:bb:cc:dd:ee:ff\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        message = SIPMessage(raw_invite)

        # Verify MAC can be extracted
        mac = message.get_header("X-MAC-Address")
        self.assertEqual(mac, "aa:bb:cc:dd:ee:ff")

    def test_complete_invite_with_all_headers(self):
        """Test building a complete INVITE with all SIP send line/MAC headers"""
        from pbx.sip.message import SIPMessageBuilder

        # Build complete INVITE
        invite = SIPMessageBuilder.build_request(
            method="INVITE",
            uri="sip:2001@10.0.0.1",
            from_addr="<sip:1001@10.0.0.1>",
            to_addr="<sip:2001@10.0.0.1>",
            call_id="complete-test-call",
            cseq=1,
            body="v=0\r\no=- 1234 5678 IN IP4 10.0.0.50\r\n",
        )

        # Add all headers
        invite.set_header("Via", "SIP/2.0/UDP 10.0.0.50:5060")
        invite.set_header("Contact", "<sip:1001@10.0.0.50:5060>")
        invite.set_header("Content-Type", "application/sdp")

        SIPMessageBuilder.add_caller_id_headers(
            invite, extension_number="1001", display_name="Sales Department", server_ip="10.0.0.1"
        )

        SIPMessageBuilder.add_mac_address_header(invite, mac_address="DE:AD:BE:EF:CA:FE")

        # Build and verify
        raw_message = invite.build()

        # Parse it back to verify all headers survive round-trip
        parsed = SIPMessage(raw_message)

        self.assertEqual(parsed.method, "INVITE")
        self.assertIsNotNone(parsed.get_header("P-Asserted-Identity"))
        self.assertIsNotNone(parsed.get_header("Remote-Party-ID"))
        self.assertIsNotNone(parsed.get_header("X-MAC-Address"))
        self.assertEqual(parsed.get_header("X-MAC-Address"), "de:ad:be:ef:ca:fe")


if __name__ == "__main__":
    unittest.main()
