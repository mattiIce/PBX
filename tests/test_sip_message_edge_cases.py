#!/usr/bin/env python3
"""
Test edge cases for SIP message parsing to prevent list index out of range errors
"""


from pbx.sip.message import SIPMessage


def test_empty_message() -> None:
    """Test parsing an empty message"""

    msg = SIPMessage("")

    # Should not crash, fields should remain None/empty
    assert msg.method is None
    assert msg.status_code is None
    assert msg.uri is None


def test_single_newline_message() -> None:
    """Test parsing a message with just newlines"""

    msg = SIPMessage("\r\n")

    # Should not crash
    assert msg.method is None
    assert msg.status_code is None


def test_malformed_request_no_uri() -> None:
    """Test parsing a request with no URI"""

    raw_message = "INVITE\r\n"
    msg = SIPMessage(raw_message)

    # Should not crash, method should remain None
    assert msg.method is None
    assert msg.uri is None


def test_malformed_response_no_status_code() -> None:
    """Test parsing a response with no status code"""

    raw_message = "SIP/2.0\r\n"
    msg = SIPMessage(raw_message)

    # Should not crash, status_code should remain None
    assert msg.status_code is None


def test_malformed_response_invalid_status_code() -> None:
    """Test parsing a response with invalid status code"""

    raw_message = "SIP/2.0 INVALID OK\r\n"
    msg = SIPMessage(raw_message)

    # Should not crash, status_code should remain None
    assert msg.status_code is None


def test_valid_request() -> None:
    """Test parsing a valid request still works"""

    raw_message = (
        "INVITE sip:1002@pbx.local SIP/2.0\r\n"
        "Via: SIP/2.0/UDP 192.168.1.100:5060\r\n"
        'From: "Alice" <sip:1001@pbx.local>\r\n'
        "To: <sip:1002@pbx.local>\r\n"
        "Call-ID: test-call-123\r\n"
        "CSeq: 1 INVITE\r\n"
        "Content-Length: 0\r\n"
        "\r\n"
    )

    msg = SIPMessage(raw_message)

    assert msg.method == "INVITE"
    assert msg.uri == "sip:1002@pbx.local"
    assert msg.version == "SIP/2.0"
    assert msg.get_header("Call-ID") == "test-call-123"


def test_valid_response() -> None:
    """Test parsing a valid response still works"""

    raw_message = (
        "SIP/2.0 200 OK\r\n"
        "Via: SIP/2.0/UDP 192.168.1.100:5060\r\n"
        'From: "Alice" <sip:1001@pbx.local>\r\n'
        "To: <sip:1002@pbx.local>\r\n"
        "Call-ID: test-call-123\r\n"
        "CSeq: 1 INVITE\r\n"
        "Content-Length: 0\r\n"
        "\r\n"
    )

    msg = SIPMessage(raw_message)

    assert msg.status_code == 200
    assert msg.status_text == "OK"
    assert msg.version == "SIP/2.0"
    assert msg.get_header("Call-ID") == "test-call-123"
