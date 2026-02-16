#!/usr/bin/env python3
"""
Test SDP parsing and building
"""

from pbx.sip.sdp import SDPBuilder, SDPSession


def test_sdp_parsing() -> None:
    """Test SDP parsing"""

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
    assert sdp.origin["username"] == "user1", f"Expected user1, got {sdp.origin['username']}"
    assert sdp.origin["address"] == "192.168.1.100", (
        f"Expected 192.168.1.100, got {sdp.origin['address']}"
    )
    assert len(sdp.media) == 1, f"Expected 1 media, got {len(sdp.media)}"
    assert sdp.media[0]["type"] == "audio", f"Expected audio, got {sdp.media[0]['type']}"
    assert sdp.media[0]["port"] == 10000, f"Expected port 10000, got {sdp.media[0]['port']}"


def test_sdp_audio_info() -> None:
    """Test extracting audio info from SDP"""

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
    assert audio_info["address"] == "192.168.1.100", (
        f"Expected 192.168.1.100, got {audio_info['address']}"
    )
    assert audio_info["port"] == 10000, f"Expected port 10000, got {audio_info['port']}"
    assert "0" in audio_info["formats"], "Expected codec 0 (PCMU) in formats"


def test_sdp_building() -> None:
    """Test SDP building"""

    sdp_body = SDPBuilder.build_audio_sdp(
        local_ip="192.168.1.14", local_port=10000, session_id="test-session-123"
    )

    assert "v=0" in sdp_body, "SDP should contain version"
    assert "192.168.1.14" in sdp_body, "SDP should contain IP address"
    assert "m=audio 10000" in sdp_body, "SDP should contain audio media with port"
    assert "RTP/AVP" in sdp_body, "SDP should contain RTP/AVP protocol"
    assert "PCMU" in sdp_body, "SDP should contain PCMU codec"
    assert "PCMA" in sdp_body, "SDP should contain PCMA codec"

    # Verify the built SDP can be parsed back
    sdp = SDPSession()
    sdp.parse(sdp_body)

    audio_info = sdp.get_audio_info()
    assert audio_info is not None, "Built SDP should be parseable"
    assert audio_info["address"] == "192.168.1.14", "Parsed IP should match"
    assert audio_info["port"] == 10000, "Parsed port should match"


def test_sdp_media_level_connection() -> None:
    """Test SDP with media-level connection info"""

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
    assert audio_info["address"] == "192.168.1.200", (
        f"Expected media-level IP 192.168.1.200, got {audio_info['address']}"
    )


def test_ilbc_mode_configuration() -> None:
    """Test iLBC mode configuration in SDP"""

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
