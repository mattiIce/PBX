#!/usr/bin/env python3
"""
Basic tests for PBX system
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.core.call import Call, CallManager, CallState
from pbx.features.extensions import Extension
from pbx.sip.message import SIPMessage, SIPMessageBuilder



def test_sip_message_parsing():
    """Test SIP message parsing"""
    print("Testing SIP message parsing...")

    raw_message = (
        "INVITE sip:1002@pbx.local SIP/2.0\r\n"
        "Via: SIP/2.0/UDP 192.168.1.100:5060\r\n"
        "From: \"Alice\" <sip:1001@pbx.local>\r\n"
        "To: <sip:1002@pbx.local>\r\n"
        "Call-ID: test-call-123\r\n"
        "CSeq: 1 INVITE\r\n"
        "Content-Length: 0\r\n"
        "\r\n"
    )

    msg = SIPMessage(raw_message)

    assert msg.method == "INVITE", f"Expected INVITE, got {msg.method}"
    assert msg.uri == "sip:1002@pbx.local", f"Expected sip:1002@pbx.local, got {
        msg.uri}"
    assert msg.get_header(
        "Call-ID") == "test-call-123", f"Expected test-call-123, got {msg.get_header('Call-ID')}"
    assert msg.is_request(), "Expected message to be a request"

    print("✓ SIP message parsing works")


def test_sip_message_building():
    """Test SIP message building"""
    print("Testing SIP message building...")

    msg = SIPMessageBuilder.build_request(
        method="REGISTER",
        uri="sip:pbx.local",
        from_addr="<sip:1001@pbx.local>",
        to_addr="<sip:1001@pbx.local>",
        call_id="register-123",
        cseq=1
    )

    msg_str = msg.build()

    assert "REGISTER sip:pbx.local SIP/2.0" in msg_str
    assert "Call-ID: register-123" in msg_str
    assert "CSeq: 1 REGISTER" in msg_str

    print("✓ SIP message building works")


def test_call_management():
    """Test call management"""
    print("Testing call management...")

    manager = CallManager()

    # Create call
    call = manager.create_call("test-123", "1001", "1002")
    assert call.call_id == "test-123"
    assert call.state == CallState.IDLE

    # Start call
    call.start()
    assert call.state == CallState.CALLING
    assert call.start_time is not None

    # Connect call
    call.connect()
    assert call.state == CallState.CONNECTED

    # Hold call
    call.hold()
    assert call.state == CallState.HOLD
    assert call.on_hold is True

    # Resume call
    call.resume()
    assert call.state == CallState.CONNECTED
    assert call.on_hold is False

    # End call
    manager.end_call("test-123")
    assert "test-123" not in manager.active_calls
    assert len(manager.call_history) == 1

    print("✓ Call management works")


def test_extension():
    """Test extension functionality"""
    print("Testing extensions...")

    ext = Extension("1001", "Test Extension", {
        'password': 'testpass',
        'allow_external': True
    })

    assert ext.number == "1001"
    assert ext.name == "Test Extension"
    assert ext.registered is False

    # Register extension
    ext.register(("192.168.1.100", 5060))
    assert ext.registered is True
    assert ext.address == ("192.168.1.100", 5060)

    # Unregister
    ext.unregister()
    assert ext.registered is False
    assert ext.address is None

    print("✓ Extensions work")


def test_config():
    """Test configuration loading"""
    print("Testing configuration...")

    import os

    from pbx.utils.config import Config

    if not os.path.exists("config.yml"):
        print("⚠ Config file not found (skipping test in test environment)")
        return

    config = Config("config.yml")

    # Test basic config access
    sip_port = config.get('server.sip_port')
    assert sip_port == 5060, f"Expected port 5060, got {sip_port}"

    # Note: Extensions are now stored in the database, not in config.yml
    # So we no longer check for extensions in config
    extensions = config.get_extensions()
    assert isinstance(
        extensions, list), "Extensions should be a list (empty if using database)"

    print("✓ Configuration works")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running PBX System Tests")
    print("=" * 60)
    print()

    tests = [
        test_sip_message_parsing,
        test_sip_message_building,
        test_call_management,
        test_extension,
        test_config
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
