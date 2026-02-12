#!/usr/bin/env python3
"""
Test SDP parsing and building
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.sip.sdp import SDPBuilder, SDPSession


def test_sdp_parsing():
    """Test SDP parsing"""
    print("Testing SDP parsing...")

    sdp_text = """v=0
o=user1 123456 654321 IN IP4 192.168.1.100
s=Test Call
c=IN IP4 192.168.1.100
t=0 0
m=audio 10000 RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=sendrecv
"""

    sdp = SDPSession()
    sdp.parse(sdp_text)

    assert sdp.version == 0, f"Expected version 0, got {sdp.version}"
    assert (
        sdp.origin["username"] == "user1"
    ), f"Expected user1, got {sdp.origin['username']}"
    assert (
        sdp.origin["address"] == "192.168.1.100"
    ), f"Expected 192.168.1.100, got {sdp.origin['address']}"
    assert len(sdp.media) == 1, f"Expected 1 media, got {len(sdp.media)}"
    assert (
        sdp.media[0]["type"] == "audio"
    ), f"Expected audio, got {sdp.media[0]['type']}"
    assert (
        sdp.media[0]["port"] == 10000
    ), f"Expected port 10000, got {sdp.media[0]['port']}"

    print("  ✓ SDP parsing works")


def test_sdp_audio_info():
    """Test extracting audio info from SDP"""
    print("Testing SDP audio info extraction...")

    sdp_text = """v=0
o=user1 123456 654321 IN IP4 192.168.1.100
s=Test Call
c=IN IP4 192.168.1.100
t=0 0
m=audio 10000 RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
"""

    sdp = SDPSession()
    sdp.parse(sdp_text)

    audio_info = sdp.get_audio_info()

    assert audio_info is not None, "Audio info should not be None"
    assert (
        audio_info["address"] == "192.168.1.100"
    ), f"Expected 192.168.1.100, got {audio_info['address']}"
    assert (
        audio_info["port"] == 10000
    ), f"Expected port 10000, got {audio_info['port']}"
    assert "0" in audio_info["formats"], "Expected codec 0 (PCMU) in formats"

    print("  ✓ Audio info extraction works")


def test_sdp_building():
    """Test SDP building"""
    print("Testing SDP building...")

    sdp_body = SDPBuilder.build_audio_sdp(
        local_ip="192.168.1.14", local_port=10000, session_id="test-session-123"
    )

    assert "v=0" in sdp_body, "SDP should contain version"
    assert "192.168.1.14" in sdp_body, "SDP should contain IP address"
    assert "m=audio 10000" in sdp_body, "SDP should contain audio media with port"
    assert "RTP/AVP" in sdp_body, "SDP should contain RTP/AVP protocol"
    assert "PCMU" in sdp_body, "SDP should contain PCMU codec"
    assert "PCMA" in sdp_body, "SDP should contain PCMA codec"

    print("  ✓ SDP building works")

    # Verify the built SDP can be parsed back
    sdp = SDPSession()
    sdp.parse(sdp_body)

    audio_info = sdp.get_audio_info()
    assert audio_info is not None, "Built SDP should be parseable"
    assert audio_info["address"] == "192.168.1.14", "Parsed IP should match"
    assert audio_info["port"] == 10000, "Parsed port should match"

    print("  ✓ Built SDP is valid and parseable")


def test_sdp_media_level_connection():
    """Test SDP with media-level connection info"""
    print("Testing SDP with media-level connection...")

    sdp_text = """v=0
o=user1 123456 654321 IN IP4 192.168.1.100
s=Test Call
t=0 0
m=audio 10000 RTP/AVP 0 8
c=IN IP4 192.168.1.200
a=rtpmap:0 PCMU/8000
"""

    sdp = SDPSession()
    sdp.parse(sdp_text)

    audio_info = sdp.get_audio_info()

    # Should use media-level connection, not session-level
    assert (
        audio_info["address"] == "192.168.1.200"
    ), f"Expected media-level IP 192.168.1.200, got {audio_info['address']}"

    print("  ✓ Media-level connection works")


def test_ilbc_mode_configuration():
    """Test iLBC mode configuration in SDP"""
    print("Testing iLBC mode configuration...")

    # Test with default mode (30ms)
    sdp_body_30 = SDPBuilder.build_audio_sdp(
        local_ip="192.168.1.14",
        local_port=10000,
        session_id="test-ilbc-30",
        codecs=["97"],  # iLBC codec
        ilbc_mode=30,
    )

    assert "rtpmap:97 iLBC/8000" in sdp_body_30, "SDP should contain iLBC codec"
    assert "fmtp:97 mode=30" in sdp_body_30, "SDP should contain mode=30 for iLBC"

    print("  ✓ iLBC mode=30 configuration works")

    # Test with 20ms mode
    sdp_body_20 = SDPBuilder.build_audio_sdp(
        local_ip="192.168.1.14",
        local_port=10000,
        session_id="test-ilbc-20",
        codecs=["97"],  # iLBC codec
        ilbc_mode=20,
    )

    assert "rtpmap:97 iLBC/8000" in sdp_body_20, "SDP should contain iLBC codec"
    assert "fmtp:97 mode=20" in sdp_body_20, "SDP should contain mode=20 for iLBC"

    print("  ✓ iLBC mode=20 configuration works")


def run_all_tests():
    """Run all SDP tests"""
    print("=" * 60)
    print("Running SDP Tests")
    print("=" * 60)
    print()

    tests = [
        test_sdp_parsing,
        test_sdp_audio_info,
        test_sdp_building,
        test_sdp_media_level_connection,
        test_ilbc_mode_configuration,
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
    if failed == 0:
        print("✅ All SDP tests passed!")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
