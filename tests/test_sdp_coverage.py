"""Comprehensive tests for pbx/sip/sdp.py - SDP negotiation."""

from unittest.mock import MagicMock, patch

import pytest

from pbx.sip.sdp import SDPBuilder, SDPSession


@pytest.mark.unit
class TestSDPSessionInit:
    """Tests for SDPSession.__init__."""

    def test_default_version(self) -> None:
        sdp = SDPSession()
        assert sdp.version == 0

    def test_default_origin_empty(self) -> None:
        sdp = SDPSession()
        assert sdp.origin == {}

    def test_default_session_name(self) -> None:
        sdp = SDPSession()
        assert sdp.session_name == "-"

    def test_default_connection_empty(self) -> None:
        sdp = SDPSession()
        assert sdp.connection == {}

    def test_default_media_empty(self) -> None:
        sdp = SDPSession()
        assert sdp.media == []


@pytest.mark.unit
class TestSDPSessionParse:
    """Tests for SDPSession.parse."""

    def test_parse_version(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\n")
        assert sdp.version == 0

    def test_parse_origin(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\no=user1 123 456 IN IP4 192.168.1.100\n")
        assert sdp.origin["username"] == "user1"
        assert sdp.origin["session_id"] == "123"
        assert sdp.origin["version"] == "456"
        assert sdp.origin["network_type"] == "IN"
        assert sdp.origin["address_type"] == "IP4"
        assert sdp.origin["address"] == "192.168.1.100"

    def test_parse_session_name(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\ns=Test Session\n")
        assert sdp.session_name == "Test Session"

    def test_parse_session_level_connection(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nc=IN IP4 192.168.1.100\n")
        assert sdp.connection["network_type"] == "IN"
        assert sdp.connection["address_type"] == "IP4"
        assert sdp.connection["address"] == "192.168.1.100"

    def test_parse_media_line(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nm=audio 10000 RTP/AVP 0 8\n")
        assert len(sdp.media) == 1
        media = sdp.media[0]
        assert media["type"] == "audio"
        assert media["port"] == 10000
        assert media["protocol"] == "RTP/AVP"
        assert media["formats"] == ["0", "8"]
        assert media["attributes"] == []

    def test_parse_media_attributes(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nm=audio 10000 RTP/AVP 0\na=rtpmap:0 PCMU/8000\na=sendrecv\n")
        assert len(sdp.media) == 1
        assert "rtpmap:0 PCMU/8000" in sdp.media[0]["attributes"]
        assert "sendrecv" in sdp.media[0]["attributes"]

    def test_parse_media_level_connection(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nc=IN IP4 10.0.0.1\nm=audio 10000 RTP/AVP 0\nc=IN IP4 192.168.1.200\n")
        assert sdp.connection["address"] == "10.0.0.1"
        assert sdp.media[0]["connection"]["address"] == "192.168.1.200"

    def test_parse_multiple_media(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nm=audio 10000 RTP/AVP 0\nm=video 20000 RTP/AVP 96\n")
        assert len(sdp.media) == 2
        assert sdp.media[0]["type"] == "audio"
        assert sdp.media[1]["type"] == "video"

    def test_parse_empty_lines_skipped(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\n\n\nm=audio 10000 RTP/AVP 0\n")
        assert sdp.version == 0
        assert len(sdp.media) == 1

    def test_parse_lines_without_equals_skipped(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nsome random text\nm=audio 10000 RTP/AVP 0\n")
        assert sdp.version == 0
        assert len(sdp.media) == 1

    def test_parse_attribute_outside_media_ignored(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\na=tool:TestTool\nm=audio 10000 RTP/AVP 0\n")
        # Attribute before any media line: current_media is None, so it's skipped
        assert len(sdp.media) == 1
        assert sdp.media[0]["attributes"] == []

    def test_parse_origin_too_few_parts(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\no=short\n")
        assert sdp.origin == {}

    def test_parse_connection_too_few_parts(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nc=IN\n")
        assert sdp.connection == {}

    def test_parse_media_too_few_parts(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nm=audio 10000\n")
        assert sdp.media == []

    def test_parse_full_sdp(self) -> None:
        sdp_body = (
            "v=0\n"
            "o=pbx 12345 0 IN IP4 192.168.1.1\n"
            "s=PBX Call\n"
            "c=IN IP4 192.168.1.1\n"
            "t=0 0\n"
            "m=audio 20000 RTP/AVP 0 8 101\n"
            "a=rtpmap:0 PCMU/8000\n"
            "a=rtpmap:8 PCMA/8000\n"
            "a=rtpmap:101 telephone-event/8000\n"
            "a=fmtp:101 0-16\n"
            "a=sendrecv\n"
        )
        sdp = SDPSession()
        sdp.parse(sdp_body)
        assert sdp.version == 0
        assert sdp.origin["username"] == "pbx"
        assert sdp.session_name == "PBX Call"
        assert sdp.connection["address"] == "192.168.1.1"
        assert len(sdp.media) == 1
        assert sdp.media[0]["port"] == 20000
        assert len(sdp.media[0]["attributes"]) == 5

    def test_parse_with_crlf(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\r\nm=audio 10000 RTP/AVP 0\r\n")
        assert sdp.version == 0
        assert len(sdp.media) == 1


@pytest.mark.unit
class TestSDPSessionGetAudioInfo:
    """Tests for SDPSession.get_audio_info."""

    def test_get_audio_info_returns_none_when_no_media(self) -> None:
        sdp = SDPSession()
        assert sdp.get_audio_info() is None

    def test_get_audio_info_returns_none_for_video_only(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nc=IN IP4 10.0.0.1\nm=video 20000 RTP/AVP 96\n")
        assert sdp.get_audio_info() is None

    def test_get_audio_info_with_session_level_connection(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nc=IN IP4 192.168.1.100\nm=audio 10000 RTP/AVP 0 8\n")
        info = sdp.get_audio_info()
        assert info is not None
        assert info["address"] == "192.168.1.100"
        assert info["port"] == 10000
        assert info["formats"] == ["0", "8"]

    def test_get_audio_info_with_media_level_connection(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nc=IN IP4 10.0.0.1\nm=audio 10000 RTP/AVP 0\nc=IN IP4 192.168.1.200\n")
        info = sdp.get_audio_info()
        assert info is not None
        # Media-level connection takes precedence
        assert info["address"] == "192.168.1.200"

    def test_get_audio_info_first_audio_media(self) -> None:
        sdp = SDPSession()
        sdp.parse("v=0\nc=IN IP4 10.0.0.1\nm=audio 10000 RTP/AVP 0\nm=audio 20000 RTP/AVP 8\n")
        info = sdp.get_audio_info()
        assert info is not None
        assert info["port"] == 10000


@pytest.mark.unit
class TestSDPSessionBuild:
    """Tests for SDPSession.build."""

    def test_build_minimal(self) -> None:
        sdp = SDPSession()
        result = sdp.build()
        assert "v=0\r\n" in result
        assert "s=-\r\n" in result
        assert "t=0 0\r\n" in result

    def test_build_with_origin(self) -> None:
        sdp = SDPSession()
        sdp.origin = {
            "username": "pbx",
            "session_id": "123",
            "version": "0",
            "network_type": "IN",
            "address_type": "IP4",
            "address": "192.168.1.1",
        }
        result = sdp.build()
        assert "o=pbx 123 0 IN IP4 192.168.1.1\r\n" in result

    def test_build_without_origin(self) -> None:
        sdp = SDPSession()
        sdp.origin = {}
        result = sdp.build()
        assert "o=" not in result

    def test_build_with_connection(self) -> None:
        sdp = SDPSession()
        sdp.connection = {
            "network_type": "IN",
            "address_type": "IP4",
            "address": "192.168.1.1",
        }
        result = sdp.build()
        assert "c=IN IP4 192.168.1.1\r\n" in result

    def test_build_without_connection(self) -> None:
        sdp = SDPSession()
        sdp.connection = {}
        result = sdp.build()
        assert "c=" not in result

    def test_build_with_media(self) -> None:
        sdp = SDPSession()
        sdp.media.append(
            {
                "type": "audio",
                "port": 10000,
                "protocol": "RTP/AVP",
                "formats": ["0", "8"],
                "attributes": ["rtpmap:0 PCMU/8000", "sendrecv"],
            }
        )
        result = sdp.build()
        assert "m=audio 10000 RTP/AVP 0 8\r\n" in result
        assert "a=rtpmap:0 PCMU/8000\r\n" in result
        assert "a=sendrecv\r\n" in result

    def test_build_with_media_level_connection(self) -> None:
        sdp = SDPSession()
        sdp.media.append(
            {
                "type": "audio",
                "port": 10000,
                "protocol": "RTP/AVP",
                "formats": ["0"],
                "attributes": [],
                "connection": {
                    "network_type": "IN",
                    "address_type": "IP4",
                    "address": "192.168.1.200",
                },
            }
        )
        result = sdp.build()
        assert "c=IN IP4 192.168.1.200\r\n" in result

    def test_build_ends_with_crlf(self) -> None:
        sdp = SDPSession()
        result = sdp.build()
        assert result.endswith("\r\n")

    def test_build_multiple_media(self) -> None:
        sdp = SDPSession()
        sdp.media.append(
            {
                "type": "audio",
                "port": 10000,
                "protocol": "RTP/AVP",
                "formats": ["0"],
                "attributes": [],
            }
        )
        sdp.media.append(
            {
                "type": "video",
                "port": 20000,
                "protocol": "RTP/AVP",
                "formats": ["96"],
                "attributes": [],
            }
        )
        result = sdp.build()
        assert "m=audio 10000 RTP/AVP 0" in result
        assert "m=video 20000 RTP/AVP 96" in result


@pytest.mark.unit
class TestSDPSessionRoundTrip:
    """Test parse->build round trip."""

    def test_parse_and_rebuild(self) -> None:
        original = (
            "v=0\n"
            "o=pbx 123 0 IN IP4 192.168.1.1\n"
            "s=PBX Call\n"
            "c=IN IP4 192.168.1.1\n"
            "m=audio 10000 RTP/AVP 0 8\n"
            "a=rtpmap:0 PCMU/8000\n"
            "a=sendrecv\n"
        )
        sdp = SDPSession()
        sdp.parse(original)
        built = sdp.build()
        assert "v=0" in built
        assert "o=pbx 123 0 IN IP4 192.168.1.1" in built
        assert "s=PBX Call" in built
        assert "c=IN IP4 192.168.1.1" in built
        assert "m=audio 10000 RTP/AVP 0 8" in built
        assert "a=rtpmap:0 PCMU/8000" in built
        assert "a=sendrecv" in built


@pytest.mark.unit
class TestSDPBuilderBuildAudioSdp:
    """Tests for SDPBuilder.build_audio_sdp."""

    def test_basic_audio_sdp(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000)
        assert "v=0" in result
        assert "o=pbx" in result
        assert "s=PBX Call" in result
        assert "c=IN IP4 192.168.1.1" in result
        assert "m=audio 10000 RTP/AVP" in result

    def test_default_codecs(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000)
        assert "rtpmap:0 PCMU/8000" in result
        assert "rtpmap:8 PCMA/8000" in result
        assert "rtpmap:9 G722/8000" in result
        assert "rtpmap:18 G729/8000" in result
        assert "rtpmap:2 G726-32/8000" in result
        assert "rtpmap:101 telephone-event/8000" in result
        assert "fmtp:101 0-16" in result

    def test_sendrecv_attribute(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000)
        assert "a=sendrecv" in result

    def test_custom_codecs(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["0", "101"])
        assert "rtpmap:0 PCMU/8000" in result
        assert "rtpmap:101 telephone-event/8000" in result
        # These should NOT be present since we only requested 0 and 101
        assert "rtpmap:8 PCMA/8000" not in result
        assert "rtpmap:9 G722/8000" not in result

    def test_custom_session_id(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, session_id="99999")
        assert "99999" in result

    def test_custom_dtmf_payload_type(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, dtmf_payload_type=96)
        assert "rtpmap:96 telephone-event/8000" in result
        assert "fmtp:96 0-16" in result

    def test_g726_40_dynamic_codec(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["114"])
        assert "rtpmap:114 G726-40/8000" in result

    def test_g726_24_dynamic_codec(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["113"])
        assert "rtpmap:113 G726-24/8000" in result

    def test_g726_16_dynamic_codec(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["112"])
        assert "rtpmap:112 G726-16/8000" in result

    def test_ilbc_codec(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["97"])
        assert "rtpmap:97 iLBC/8000" in result
        assert "fmtp:97 mode=30" in result

    def test_ilbc_codec_custom_mode(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["97"], ilbc_mode=20)
        assert "fmtp:97 mode=20" in result

    def test_speex_narrowband_codec(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["98"])
        assert "rtpmap:98 SPEEX/8000" in result

    def test_speex_wideband_codec(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["99"])
        assert "rtpmap:99 SPEEX/16000" in result
        assert 'fmtp:99 vbr=on;mode="1,any"' in result

    def test_speex_ultra_wideband_codec(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["100"])
        assert "rtpmap:100 SPEEX/32000" in result
        assert 'fmtp:100 vbr=on;mode="2,any"' in result

    def test_all_codecs_together(self) -> None:
        codecs = ["0", "8", "9", "18", "2", "114", "113", "112", "97", "98", "99", "100", "101"]
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=codecs)
        assert "rtpmap:0 PCMU/8000" in result
        assert "rtpmap:8 PCMA/8000" in result
        assert "rtpmap:9 G722/8000" in result
        assert "rtpmap:18 G729/8000" in result
        assert "rtpmap:2 G726-32/8000" in result
        assert "rtpmap:114 G726-40/8000" in result
        assert "rtpmap:113 G726-24/8000" in result
        assert "rtpmap:112 G726-16/8000" in result
        assert "rtpmap:97 iLBC/8000" in result
        assert "rtpmap:98 SPEEX/8000" in result
        assert "rtpmap:99 SPEEX/16000" in result
        assert "rtpmap:100 SPEEX/32000" in result
        assert "rtpmap:101 telephone-event/8000" in result

    def test_output_is_valid_sdp_parsable(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000)
        sdp = SDPSession()
        sdp.parse(result)
        assert sdp.version == 0
        info = sdp.get_audio_info()
        assert info is not None
        assert info["address"] == "192.168.1.1"
        assert info["port"] == 10000

    def test_codecs_without_dtmf(self) -> None:
        result = SDPBuilder.build_audio_sdp("192.168.1.1", 10000, codecs=["0", "8"])
        assert "telephone-event" not in result

    def test_origin_address_matches_local_ip(self) -> None:
        result = SDPBuilder.build_audio_sdp("10.0.0.5", 20000)
        sdp = SDPSession()
        sdp.parse(result)
        assert sdp.origin["address"] == "10.0.0.5"
        assert sdp.connection["address"] == "10.0.0.5"
