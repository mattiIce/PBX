#!/usr/bin/env python3
"""
Test edge cases for SIP message parsing to prevent list index out of range errors
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.sip.message import SIPMessage, SIPMessageBuilder


def test_empty_message():
    """Test parsing an empty message"""
    print("Testing empty message parsing...")

    msg = SIPMessage("")

    # Should not crash, fields should remain None/empty
    assert msg.method is None
    assert msg.status_code is None
    assert msg.uri is None

    print("✓ Empty message handling works")


def test_single_newline_message():
    """Test parsing a message with just newlines"""
    print("Testing single newline message...")

    msg = SIPMessage("\r\n")

    # Should not crash
    assert msg.method is None
    assert msg.status_code is None

    print("✓ Single newline message handling works")


def test_malformed_request_no_uri():
    """Test parsing a request with no URI"""
    print("Testing malformed request with no URI...")

    raw_message = "INVITE\r\n"
    msg = SIPMessage(raw_message)

    # Should not crash, method should remain None
    assert msg.method is None
    assert msg.uri is None

    print("✓ Malformed request (no URI) handling works")


def test_malformed_response_no_status_code():
    """Test parsing a response with no status code"""
    print("Testing malformed response with no status code...")

    raw_message = "SIP/2.0\r\n"
    msg = SIPMessage(raw_message)

    # Should not crash, status_code should remain None
    assert msg.status_code is None

    print("✓ Malformed response (no status code) handling works")


def test_malformed_response_invalid_status_code():
    """Test parsing a response with invalid status code"""
    print("Testing malformed response with invalid status code...")

    raw_message = "SIP/2.0 INVALID OK\r\n"
    msg = SIPMessage(raw_message)

    # Should not crash, status_code should remain None
    assert msg.status_code is None

    print("✓ Malformed response (invalid status code) handling works")


def test_valid_request():
    """Test parsing a valid request still works"""
    print("Testing valid request parsing...")

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

    print("✓ Valid request parsing still works")


def test_valid_response():
    """Test parsing a valid response still works"""
    print("Testing valid response parsing...")

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

    print("✓ Valid response parsing still works")


def run_all_tests():
    """Run all edge case tests"""
    print("\n" + "=" * 60)
    print("Running SIP Message Edge Case Tests")
    print("=" * 60 + "\n")

    try:
        test_empty_message()
        test_single_newline_message()
        test_malformed_request_no_uri()
        test_malformed_response_no_status_code()
        test_malformed_response_invalid_status_code()
        test_valid_request()
        test_valid_response()

        print("\n" + "=" * 60)
        print("✓ All SIP Message Edge Case Tests Passed!")
        print("=" * 60 + "\n")
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
