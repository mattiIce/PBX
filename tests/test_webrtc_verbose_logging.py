#!/usr/bin/env python3
"""
Test WebRTC verbose logging feature
"""

import logging
from io import StringIO
from typing import Any


from pbx.features.webrtc import WebRTCGateway, WebRTCSignalingServer


def test_verbose_logging_disabled() -> bool:
    """Test that verbose logging is disabled by default"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
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

    return True


def test_verbose_logging_enabled() -> bool:
    """Test that verbose logging can be enabled"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
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

    return True


def test_verbose_logging_in_offer_handling() -> bool:
    """Test verbose logging in SDP offer handling"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
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

    return True


def test_gateway_verbose_logging() -> bool:
    """Test that gateway inherits verbose logging from signaling server"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {"features.webrtc.enabled": True, "features.webrtc.verbose_logging": True}
            return config_map.get(key, default)

    config = MockConfig()
    signaling = WebRTCSignalingServer(config)

    # Create mock PBX core
    class MockPBXCore:
        def __init__(self) -> None:
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

    return True
