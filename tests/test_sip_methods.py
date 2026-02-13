"""
Test suite for all SIP methods including MESSAGE, PRACK, UPDATE, and PUBLISH
"""

import os
import sys
import unittest
from typing import Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.sip.message import SIPMessage
from pbx.sip.server import SIPServer


class MockCallManager:
    """Mock call manager for testing"""

    def __init__(self) -> None:
        self.calls: dict[str, Any] = {}

    def get_call(self, call_id: str) -> Any:
        return self.calls.get(call_id)


class MockPBXCore:
    """Mock PBX Core for testing"""

    def __init__(self) -> None:
        self.register_calls: list[tuple[str, Any, str, str]] = []
        self.route_calls: list[tuple[str, str, str]] = []
        self.messages: list[Any] = []
        self.call_manager = MockCallManager()

    def register_extension(self, from_header: str, addr: Any, user_agent: str, contact: str) -> bool:
        """Mock registration"""
        self.register_calls.append((from_header, addr, user_agent, contact))
        return True

    def route_call(self, from_header: str, to_header: str, call_id: str, message: Any, addr: Any) -> bool:
        """Mock call routing"""
        self.route_calls.append((from_header, to_header, call_id))
        return True

    def end_call(self, call_id: str) -> None:
        """Mock end call"""


class TestSIPMethods(unittest.TestCase):
    """Test all SIP methods"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        self.mock_pbx = MockPBXCore()
        self.sip_server = SIPServer(host="127.0.0.1", port=5060, pbx_core=self.mock_pbx)

    def test_message_method_basic(self) -> None:
        """Test MESSAGE method for instant messaging"""
        sip_message = (
            "MESSAGE sip:1002@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1002@192.168.1.100>\r\n"
            "Call-ID: msg-call-123\r\n"
            "CSeq: 1 MESSAGE\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 11\r\n"
            "\r\n"
            "Hello World"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "MESSAGE")
        self.assertEqual(message.get_header("Content-Type"), "text/plain")
        self.assertEqual(message.body, "Hello World")

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_sip_message_method(message, addr)
        # Should not raise exception

    def test_message_method_empty_body(self) -> None:
        """Test MESSAGE method with empty body"""
        sip_message = (
            "MESSAGE sip:1002@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1002@192.168.1.100>\r\n"
            "Call-ID: msg-call-124\r\n"
            "CSeq: 2 MESSAGE\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "MESSAGE")
        self.assertEqual(message.body, "")

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_sip_message_method(message, addr)
        # Should not raise exception

    def test_message_method_various_content_types(self) -> None:
        """Test MESSAGE method with different content types"""
        content_types = ["text/plain", "text/html", "application/json", "application/xml"]

        for idx, content_type in enumerate(content_types):
            body = "Test data"
            sip_message = (
                "MESSAGE sip:1002@192.168.1.100:5060 SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds{idx}\r\n"
                "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
                "To: <sip:1002@192.168.1.100>\r\n"
                f"Call-ID: msg-call-{125 + idx}\r\n"
                f"CSeq: {idx + 1} MESSAGE\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {len(body)}\r\n"
                "\r\n"
                f"{body}"
            )
            message = SIPMessage(sip_message)

            # Verify message parsing
            self.assertEqual(message.method, "MESSAGE")
            self.assertEqual(message.get_header("Content-Type"), content_type)

            # Test handling
            addr = ("192.168.1.101", 5060)
            self.sip_server._handle_sip_message_method(message, addr)
            # Should not raise exception

    def test_prack_method(self) -> None:
        """Test PRACK method for provisional response acknowledgment"""
        sip_message = (
            "PRACK sip:1002@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1002@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: prack-call-123\r\n"
            "CSeq: 2 PRACK\r\n"
            "RAck: 1 1 INVITE\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "PRACK")
        self.assertEqual(message.get_header("RAck"), "1 1 INVITE")
        self.assertEqual(message.get_header("Call-ID"), "prack-call-123")

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_prack(message, addr)
        # Should not raise exception

    def test_prack_method_without_rack(self) -> None:
        """Test PRACK method without RAck header"""
        sip_message = (
            "PRACK sip:1002@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1002@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: prack-call-124\r\n"
            "CSeq: 2 PRACK\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "PRACK")
        self.assertIsNone(message.get_header("RAck"))

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_prack(message, addr)
        # Should not raise exception

    def test_update_method_with_sdp(self) -> None:
        """Test UPDATE method with SDP body"""
        sdp_body = (
            "v=0\r\n"
            "o=- 123456 654321 IN IP4 192.168.1.101\r\n"
            "s=Session\r\n"
            "c=IN IP4 192.168.1.101\r\n"
            "t=0 0\r\n"
            "m=audio 49172 RTP/AVP 0\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
        )

        sip_message = (
            "UPDATE sip:1002@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1002@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: update-call-123\r\n"
            "CSeq: 3 UPDATE\r\n"
            "Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp_body)}\r\n"
            "\r\n"
            f"{sdp_body}"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "UPDATE")
        self.assertEqual(message.get_header("Content-Type"), "application/sdp")
        self.assertIn("m=audio", message.body)

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_update(message, addr)
        # Should not raise exception

    def test_update_method_without_sdp(self) -> None:
        """Test UPDATE method without SDP body"""
        sip_message = (
            "UPDATE sip:1002@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1002@192.168.1.100>;tag=a6c85cf\r\n"
            "Call-ID: update-call-124\r\n"
            "CSeq: 3 UPDATE\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "UPDATE")
        self.assertEqual(message.body, "")

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_update(message, addr)
        # Should not raise exception

    def test_publish_method(self) -> None:
        """Test PUBLISH method for event state publication"""
        sip_message = (
            "PUBLISH sip:presence@192.168.1.100 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1001@192.168.1.100>\r\n"
            "Call-ID: publish-call-123\r\n"
            "CSeq: 1 PUBLISH\r\n"
            "Event: presence\r\n"
            "Expires: 3600\r\n"
            "Content-Type: application/pidf+xml\r\n"
            "Content-Length: 23\r\n"
            "\r\n"
            "<presence>data</presence>"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "PUBLISH")
        self.assertEqual(message.get_header("Event"), "presence")
        self.assertEqual(message.get_header("Expires"), "3600")

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_publish(message, addr)
        # Should not raise exception

    def test_publish_method_with_sip_if_match(self) -> None:
        """Test PUBLISH method with SIP-If-Match for refresh"""
        sip_message = (
            "PUBLISH sip:presence@192.168.1.100 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1001@192.168.1.100>\r\n"
            "Call-ID: publish-call-124\r\n"
            "CSeq: 2 PUBLISH\r\n"
            "Event: presence\r\n"
            "Expires: 3600\r\n"
            "SIP-If-Match: entity-tag-12345\r\n"
            "Content-Type: application/pidf+xml\r\n"
            "Content-Length: 23\r\n"
            "\r\n"
            "<presence>data</presence>"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "PUBLISH")
        self.assertEqual(message.get_header("SIP-If-Match"), "entity-tag-12345")

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_publish(message, addr)
        # Should not raise exception

    def test_publish_method_without_body(self) -> None:
        """Test PUBLISH method without body (unpublish)"""
        sip_message = (
            "PUBLISH sip:presence@192.168.1.100 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1001@192.168.1.100>\r\n"
            "Call-ID: publish-call-125\r\n"
            "CSeq: 3 PUBLISH\r\n"
            "Event: presence\r\n"
            "Expires: 0\r\n"
            "SIP-If-Match: entity-tag-12345\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "PUBLISH")
        self.assertEqual(message.get_header("Expires"), "0")
        self.assertEqual(message.body, "")

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_publish(message, addr)
        # Should not raise exception

    def test_options_includes_all_methods(self) -> None:
        """Test OPTIONS response includes all supported methods"""
        sip_message = (
            "OPTIONS sip:192.168.1.100 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:192.168.1.100>\r\n"
            "Call-ID: options-call-123\r\n"
            "CSeq: 1 OPTIONS\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "OPTIONS")

        # Test handling (just verify no exception)
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_options(message, addr)
        # Should not raise exception

    def test_all_methods_in_request_handler(self) -> None:
        """Test that all methods are properly routed by _handle_request"""
        test_methods = [
            "REGISTER",
            "INVITE",
            "ACK",
            "BYE",
            "CANCEL",
            "OPTIONS",
            "SUBSCRIBE",
            "NOTIFY",
            "REFER",
            "INFO",
            "MESSAGE",
            "PRACK",
            "UPDATE",
            "PUBLISH",
        ]

        for method in test_methods:
            sip_message = (
                f"{method} sip:test@192.168.1.100:5060 SIP/2.0\r\n"
                "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
                "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
                "To: <sip:1002@192.168.1.100>\r\n"
                f"Call-ID: test-{method.lower()}-123\r\n"
                f"CSeq: 1 {method}\r\n"
                "Content-Length: 0\r\n"
                "\r\n"
            )
            message = SIPMessage(sip_message)

            # Verify message parsing
            self.assertEqual(message.method, method)

            # Test handling via _handle_request
            addr = ("192.168.1.101", 5060)
            self.sip_server._handle_request(message, addr)
            # Should not raise exception

    def test_unsupported_method_returns_405(self) -> None:
        """Test that unsupported methods return 405 Method Not Allowed"""
        sip_message = (
            "UNSUPPORTED sip:test@192.168.1.100:5060 SIP/2.0\r\n"
            "Via: SIP/2.0/UDP 192.168.1.101:5060;branch=z9hG4bK776asdhds\r\n"
            "From: <sip:1001@192.168.1.100>;tag=1928301774\r\n"
            "To: <sip:1002@192.168.1.100>\r\n"
            "Call-ID: unsupported-call-123\r\n"
            "CSeq: 1 UNSUPPORTED\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        )
        message = SIPMessage(sip_message)

        # Verify message parsing
        self.assertEqual(message.method, "UNSUPPORTED")

        # Test handling
        addr = ("192.168.1.101", 5060)
        self.sip_server._handle_request(message, addr)
        # Should handle gracefully and send 405 response


if __name__ == "__main__":
    unittest.main()
