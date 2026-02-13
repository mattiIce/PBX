"""
Test SIP Send Line and Send MAC functionality
Tests P-Asserted-Identity, Remote-Party-ID, and X-MAC-Address headers
"""

import unittest

from pbx.sip.message import SIPMessage, SIPMessageBuilder


class TestSIPCallerIDHeaders(unittest.TestCase):
    """Test SIP caller ID header functionality"""

    def test_add_caller_id_headers(self) -> None:
        """Test adding P-Asserted-Identity and Remote-Party-ID headers"""
        message = SIPMessage()
        message.method = "INVITE"
        message.uri = "sip:1002@192.168.1.100"

        # Add caller ID headers
        SIPMessageBuilder.add_caller_id_headers(
            message, extension_number="1001", display_name="John Doe", server_ip="192.168.1.100"
        )

        # Verify P-Asserted-Identity header
        pai = message.get_header("P-Asserted-Identity")
        self.assertIsNotNone(pai)
        self.assertIn("John Doe", pai)
        self.assertIn("sip:1001@192.168.1.100", pai)

        # Verify Remote-Party-ID header
        rpid = message.get_header("Remote-Party-ID")
        self.assertIsNotNone(rpid)
        self.assertIn("John Doe", rpid)
        self.assertIn("sip:1001@192.168.1.100", rpid)
        self.assertIn("party=calling", rpid)
        self.assertIn("privacy=of", rpid)
        self.assertIn("screen=no", rpid)

    def test_caller_id_headers_format(self) -> None:
        """Test caller ID headers are properly formatted"""
        message = SIPMessage()
        message.method = "INVITE"

        SIPMessageBuilder.add_caller_id_headers(
            message, extension_number="2001", display_name="Sales Department", server_ip="10.0.0.1"
        )

        pai = message.get_header("P-Asserted-Identity")
        # Should be in format: "Display Name" <sip:ext@server>
        self.assertEqual(pai, '"Sales Department" <sip:2001@10.0.0.1>')

        rpid = message.get_header("Remote-Party-ID")
        # Should have proper parameters
        self.assertIn('"Sales Department" <sip:2001@10.0.0.1>', rpid)


class TestSIPMACAddressHeader(unittest.TestCase):
    """Test SIP MAC address header functionality"""

    def test_add_mac_address_header_colon_format(self) -> None:
        """Test adding MAC address header with colon format"""
        message = SIPMessage()
        message.method = "INVITE"

        # Test with colon-separated MAC
        SIPMessageBuilder.add_mac_address_header(message, mac_address="00:11:22:33:44:55")

        x_mac = message.get_header("X-MAC-Address")
        self.assertIsNotNone(x_mac)
        self.assertEqual(x_mac, "00:11:22:33:44:55")

    def test_add_mac_address_header_dash_format(self) -> None:
        """Test adding MAC address header with dash format"""
        message = SIPMessage()
        message.method = "INVITE"

        # Test with dash-separated MAC
        SIPMessageBuilder.add_mac_address_header(message, mac_address="AA-BB-CC-DD-EE-FF")

        x_mac = message.get_header("X-MAC-Address")
        self.assertIsNotNone(x_mac)
        # Should be normalized to colon format and lowercase
        self.assertEqual(x_mac, "aa:bb:cc:dd:ee:ff")

    def test_add_mac_address_header_no_separator(self) -> None:
        """Test adding MAC address header without separators"""
        message = SIPMessage()
        message.method = "INVITE"

        # Test with no separators
        SIPMessageBuilder.add_mac_address_header(message, mac_address="001122334455")

        x_mac = message.get_header("X-MAC-Address")
        self.assertIsNotNone(x_mac)
        # Should be formatted with colons
        self.assertEqual(x_mac, "00:11:22:33:44:55")

    def test_add_mac_address_header_invalid(self) -> None:
        """Test adding invalid MAC address doesn't add header"""
        message = SIPMessage()
        message.method = "INVITE"

        # Test with invalid MAC (too short)
        SIPMessageBuilder.add_mac_address_header(message, mac_address="00:11:22")

        x_mac = message.get_header("X-MAC-Address")
        # Should not add header for invalid MAC
        self.assertIsNone(x_mac)

    def test_add_mac_address_header_none(self) -> None:
        """Test adding None MAC address doesn't crash"""
        message = SIPMessage()
        message.method = "INVITE"

        # Test with None
        SIPMessageBuilder.add_mac_address_header(message, mac_address=None)

        x_mac = message.get_header("X-MAC-Address")
        self.assertIsNone(x_mac)

    def test_add_mac_address_header_invalid_chars(self) -> None:
        """Test adding MAC with invalid characters doesn't add header"""
        message = SIPMessage()
        message.method = "INVITE"

        # Test with invalid characters (G is not hex)
        SIPMessageBuilder.add_mac_address_header(message, mac_address="GG:11:22:33:44:55")

        x_mac = message.get_header("X-MAC-Address")
        # Should not add header for invalid MAC
        self.assertIsNone(x_mac)


class TestSIPMessageParsing(unittest.TestCase):
    """Test parsing SIP messages with new headers"""

    def test_parse_invite_with_caller_id_headers(self) -> None:
        """Test parsing INVITE with P-Asserted-Identity and Remote-Party-ID"""
        raw_message = (
            "INVITE sip:1002@192.168.1.100 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.50:5060\r\n"
            "From: <sip:1001@192.168.1.100>\r\n"
            "To: <sip:1002@192.168.1.100>\r\n"
            "Call-ID: test-call-123\r\n"
            "CSeq: 1 INVITE\r\n"
            'P-Asserted-Identity: "John Doe" <sip:1001@192.168.1.100>\r\n'
            'Remote-Party-ID: "John Doe" <sip:1001@192.168.1.100>;party=calling\r\n'
            "Content-Length: 0\r\n"
            "\r\n"
        )

        message = SIPMessage(raw_message)

        self.assertEqual(message.method, "INVITE")

        pai = message.get_header("P-Asserted-Identity")
        self.assertIsNotNone(pai)
        self.assertIn("John Doe", pai)

        rpid = message.get_header("Remote-Party-ID")
        self.assertIsNotNone(rpid)
        self.assertIn("John Doe", rpid)

    def test_parse_invite_with_mac_header(self) -> None:
        """Test parsing INVITE with X-MAC-Address header"""
        raw_message = (
            "INVITE sip:1002@192.168.1.100 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.50:5060\r\n"
            "From: <sip:1001@192.168.1.100>\r\n"
            "To: <sip:1002@192.168.1.100>\r\n"
            "Call-ID: test-call-456\r\n"
            "CSeq: 1 INVITE\r\n"
            "X-MAC-Address: 00:11:22:33:44:55\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )

        message = SIPMessage(raw_message)

        self.assertEqual(message.method, "INVITE")

        x_mac = message.get_header("X-MAC-Address")
        self.assertIsNotNone(x_mac)
        self.assertEqual(x_mac, "00:11:22:33:44:55")


class TestSIPMessageBuilding(unittest.TestCase):
    """Test building complete SIP messages with all headers"""

    def test_build_invite_with_all_headers(self) -> None:
        """Test building INVITE with caller ID and MAC headers"""
        message = SIPMessageBuilder.build_request(
            method="INVITE",
            uri="sip:1002@192.168.1.100",
            from_addr="<sip:1001@192.168.1.100>",
            to_addr="<sip:1002@192.168.1.100>",
            call_id="test-call-789",
            cseq=1,
            body="",
        )

        # Add caller ID headers
        SIPMessageBuilder.add_caller_id_headers(
            message, extension_number="1001", display_name="Alice Smith", server_ip="192.168.1.100"
        )

        # Add MAC address header
        SIPMessageBuilder.add_mac_address_header(message, mac_address="AA:BB:CC:DD:EE:FF")

        # Build the message
        raw_message = message.build()

        # Verify all headers are present
        self.assertIn("P-Asserted-Identity", raw_message)
        self.assertIn("Remote-Party-ID", raw_message)
        self.assertIn("X-MAC-Address", raw_message)
        self.assertIn("Alice Smith", raw_message)
        self.assertIn("aa:bb:cc:dd:ee:f", raw_message)

        # Verify it can be parsed back
        parsed = SIPMessage(raw_message)
        self.assertEqual(parsed.method, "INVITE")
        self.assertIsNotNone(parsed.get_header("P-Asserted-Identity"))
        self.assertIsNotNone(parsed.get_header("Remote-Party-ID"))
        self.assertIsNotNone(parsed.get_header("X-MAC-Address"))


if __name__ == "__main__":
    unittest.main()
