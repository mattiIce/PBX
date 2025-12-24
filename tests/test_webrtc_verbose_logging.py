#!/usr/bin/env python3
"""
Test WebRTC verbose logging feature
"""
import logging
import os
import sys
from io import StringIO

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.webrtc import WebRTCGateway, WebRTCSignalingServer


def test_verbose_logging_disabled():
    """Test that verbose logging is disabled by default"""
    print("\nTesting verbose logging disabled by default...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                "features.webrtc.enabled": True,
                "features.webrtc.verbose_logging": False,  # Disabled
                "features.webrtc.session_timeout": 300,
            }
            return config_map.get(key, default)

    config = MockConfig()
    signaling = WebRTCSignalingServer(config)

    assert signaling.enabled, "Should be enabled"
    assert signaling.verbose_logging is False, "Verbose logging should be disabled"

    signaling.stop()

    print("✓ Verbose logging disabled by default works")
    return True


def test_verbose_logging_enabled():
    """Test that verbose logging can be enabled"""
    print("\nTesting verbose logging enabled...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                "features.webrtc.enabled": True,
                "features.webrtc.verbose_logging": True,  # Enabled
                "features.webrtc.session_timeout": 300,
                "features.webrtc.stun_servers": ["stun:stun.example.com:19302"],
            }
            return config_map.get(key, default)

    config = MockConfig()

    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)

    from pbx.utils.logger import get_logger

    logger = get_logger()
    logger.addHandler(handler)

    signaling = WebRTCSignalingServer(config)

    assert signaling.enabled, "Should be enabled"
    assert signaling.verbose_logging, "Verbose logging should be enabled"

    # Create a session to test verbose logging
    signaling.create_session("1001")

    # Get log output
    log_output = log_stream.getvalue()

    # Verify verbose logging output exists
    assert (
        "[VERBOSE]" in log_output or "verbose logging ENABLED" in log_output.lower()
    ), f"Should have verbose log messages. Log output: {log_output}"

    signaling.stop()
    logger.removeHandler(handler)

    print("✓ Verbose logging enabled works")
    print(f"  Captured verbose logs: {'[VERBOSE]' in log_output}")
    return True


def test_verbose_logging_in_offer_handling():
    """Test verbose logging in SDP offer handling"""
    print("\nTesting verbose logging in offer handling...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                "features.webrtc.enabled": True,
                "features.webrtc.verbose_logging": True,
                "features.webrtc.session_timeout": 300,
            }
            return config_map.get(key, default)

    config = MockConfig()

    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)

    from pbx.utils.logger import get_logger

    logger = get_logger()
    logger.addHandler(handler)

    signaling = WebRTCSignalingServer(config)

    # Create session
    session = signaling.create_session("1001")

    # Handle an offer
    test_sdp = """v=0
o=- 123456 123456 IN IP4 192.168.1.1
s=WebRTC Session
t=0 0
m=audio 50000 RTP/AVP 0
c=IN IP4 192.168.1.1
a=rtpmap:0 PCMU/8000
"""

    signaling.handle_offer(session.session_id, test_sdp)

    # Get log output
    log_output = log_stream.getvalue()

    # Verify verbose logging output includes SDP details
    assert "[VERBOSE]" in log_output, f"Should have [VERBOSE] tag in logs. Log output: {log_output}"
    assert (
        "SDP offer received" in log_output or "Full SDP offer" in log_output
    ), f"Should have SDP offer details in logs. Log output: {log_output}"

    signaling.stop()
    logger.removeHandler(handler)

    print("✓ Verbose logging in offer handling works")
    return True


def test_gateway_verbose_logging():
    """Test that gateway inherits verbose logging from signaling server"""
    print("\nTesting gateway verbose logging...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {"features.webrtc.enabled": True, "features.webrtc.verbose_logging": True}
            return config_map.get(key, default)

    config = MockConfig()
    signaling = WebRTCSignalingServer(config)

    # Create mock PBX core
    class MockPBXCore:
        def __init__(self):
            self.webrtc_signaling = signaling

    pbx_core = MockPBXCore()

    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)

    from pbx.utils.logger import get_logger

    logger = get_logger()
    logger.addHandler(handler)

    gateway = WebRTCGateway(pbx_core)

    # Verify gateway has verbose logging enabled
    assert gateway.verbose_logging, "Gateway should have verbose logging enabled"

    # Get log output
    log_output = log_stream.getvalue()

    # Verify gateway initialization logged correctly
    assert (
        "[VERBOSE]" in log_output or "verbose logging ENABLED" in log_output.lower()
    ), f"Gateway should log verbose mode. Log output: {log_output}"

    signaling.stop()
    logger.removeHandler(handler)

    print("✓ Gateway verbose logging works")
    return True


if __name__ == "__main__":
    print("======================================================================")
    print("Testing WebRTC Verbose Logging Feature")
    print("======================================================================")

    tests = [
        test_verbose_logging_disabled,
        test_verbose_logging_enabled,
        test_verbose_logging_in_offer_handling,
        test_gateway_verbose_logging,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n======================================================================")
    if failed == 0:
        print(f"✅ All verbose logging tests passed! ({passed}/{len(tests)})")
        sys.exit(0)
    else:
        print(f"❌ Some tests failed: {passed} passed, {failed} failed")
        sys.exit(1)
