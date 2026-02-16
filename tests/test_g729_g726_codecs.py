"""
Tests for G.729 and G.726 codec support
Validates codec initialization, SDP generation, and framework functionality
"""

import pytest

from pbx.features.g726_codec import G726Codec, G726CodecManager
from pbx.features.g729_codec import G729Codec, G729CodecManager
from pbx.sip.sdp import SDPBuilder, SDPSession


class TestG729Codec:
    """Test G.729 codec functionality"""

    def test_g729_initialization(self) -> None:
        """Test G.729 codec initialization"""
        codec = G729Codec(variant="G729AB")
        assert codec.variant == "G729AB"
        assert codec.SAMPLE_RATE == 8000
        assert codec.PAYLOAD_TYPE == 18
        assert codec.BITRATE == 8000

    def test_g729_info(self) -> None:
        """Test G.729 codec info retrieval"""
        codec = G729Codec(variant="G729A")
        info = codec.get_info()

        assert info["name"] == "G.729"
        assert info["variant"] == "G729A"
        assert info["sample_rate"] == 8000
        assert info["bitrate"] == 8000
        assert info["payload_type"] == 18
        assert info["license_required"]

    def test_g729_sdp_description(self) -> None:
        """Test G.729 SDP format string"""
        codec = G729Codec()
        sdp_desc = codec.get_sdp_description()

        assert "rtpmap:18" in sdp_desc
        assert "G729/8000" in sdp_desc

    def test_g729_fmtp_params(self) -> None:
        """Test G.729 FMTP parameters"""
        # Base variant should disable Annex B
        codec_base = G729Codec(variant="G729")
        fmtp = codec_base.get_fmtp_params()
        assert fmtp is not None
        assert "annexb=no" in fmtp
        # AB variant should not have fmtp
        codec_ab = G729Codec(variant="G729AB")
        fmtp_ab = codec_ab.get_fmtp_params()
        assert fmtp_ab is None

    def test_g729_capabilities(self) -> None:
        """Test G.729 capabilities"""
        caps = G729Codec.get_capabilities()

        assert "G729AB" in caps["variants"]
        assert caps["sample_rate"] == 8000
        assert caps["bitrate"] == 8000
        assert caps["channels"] == 1


class TestG729CodecManager:
    """Test G.729 codec manager"""

    def test_manager_initialization(self) -> None:
        """Test codec manager initialization"""
        config = {"codecs.g729.enabled": True, "codecs.g729.variant": "G729A"}
        manager = G729CodecManager(config)

        assert manager.enabled
        assert manager.variant == "G729A"

    def test_manager_create_encoder(self) -> None:
        """Test creating encoder"""
        config = {"codecs.g729.enabled": True}
        manager = G729CodecManager(config)

        encoder = manager.create_encoder("call123")
        assert encoder is not None
        assert isinstance(encoder, G729Codec)
        # Should be retrievable
        retrieved = manager.get_encoder("call123")
        assert encoder == retrieved

    def test_manager_disabled(self) -> None:
        """Test manager when disabled"""
        config = {"codecs.g729.enabled": False}
        manager = G729CodecManager(config)

        encoder = manager.create_encoder("call123")
        assert encoder is None

    def test_manager_release_codec(self) -> None:
        """Test releasing codec resources"""
        config = {"codecs.g729.enabled": True}
        manager = G729CodecManager(config)

        manager.create_encoder("call123")
        manager.create_decoder("call123")

        manager.release_codec("call123")

        assert manager.get_encoder("call123") is None
        assert manager.get_decoder("call123") is None

    def test_manager_sdp_capabilities(self) -> None:
        """Test SDP capabilities"""
        config = {"codecs.g729.enabled": True}
        manager = G729CodecManager(config)

        caps = manager.get_sdp_capabilities()
        assert len(caps) > 0
        assert any("rtpmap:18" in cap for cap in caps)


class TestG726Codec:
    """Test G.726 codec functionality"""

    def test_g726_initialization_32k(self) -> None:
        """Test G.726-32 initialization"""
        codec = G726Codec(bitrate=32000)
        assert codec.bitrate == 32000
        assert codec.bitrate_kbps == 32
        assert codec.bits_per_sample == 4
        assert codec.payload_type == 2  # Static type for G.726-32

    def test_g726_initialization_40k(self) -> None:
        """Test G.726-40 initialization"""
        codec = G726Codec(bitrate=40000)
        assert codec.bitrate == 40000
        assert codec.bitrate_kbps == 40
        assert codec.bits_per_sample == 5
        assert codec.payload_type == 114  # Dynamic type

    def test_g726_invalid_bitrate(self) -> None:
        """Test invalid bitrate raises error"""
        with pytest.raises(ValueError):
            G726Codec(bitrate=48000)

    def test_g726_info(self) -> None:
        """Test G.726 codec info"""
        codec = G726Codec(bitrate=32000)
        info = codec.get_info()

        assert info["name"] == "G.726-32"
        assert info["sample_rate"] == 8000
        assert info["bitrate"] == 32000
        assert info["bits_per_sample"] == 4
        assert info["payload_type"] == 2

    def test_g726_sdp_description(self) -> None:
        """Test G.726 SDP format strings"""
        codec_32 = G726Codec(bitrate=32000)
        sdp_32 = codec_32.get_sdp_description()
        assert "rtpmap:2" in sdp_32
        assert "G726-32/8000" in sdp_32
        codec_24 = G726Codec(bitrate=24000)
        sdp_24 = codec_24.get_sdp_description()
        assert "G726-24/8000" in sdp_24

    def test_g726_capabilities(self) -> None:
        """Test G.726 capabilities"""
        caps = G726Codec.get_capabilities()

        assert 32000 in caps["bitrates"]
        assert 24000 in caps["bitrates"]
        assert 16000 in caps["bitrates"]
        assert 40000 in caps["bitrates"]
        assert caps["sample_rate"] == 8000

    def test_g726_is_supported(self) -> None:
        """Test G.726 support detection"""
        # G.726-32 should be supported via audioop
        # Other bitrates need specialized library
        supported_32 = G726Codec.is_supported(32000)
        # We can't guarantee audioop is available in all environments
        # but we can check the method works
        assert isinstance(supported_32, bool)


class TestG726CodecManager:
    """Test G.726 codec manager"""

    def test_manager_initialization(self) -> None:
        """Test codec manager initialization"""
        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        assert manager.enabled
        assert manager.default_bitrate == 32000

    def test_manager_invalid_bitrate(self) -> None:
        """Test manager handles invalid bitrate"""
        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 99999}
        manager = G726CodecManager(config)

        # Should default to 32000
        assert manager.default_bitrate == 32000

    def test_manager_create_encoder(self) -> None:
        """Test creating encoder"""
        config = {"codecs.g726.enabled": True}
        manager = G726CodecManager(config)

        encoder = manager.create_encoder("call456", bitrate=24000)
        assert encoder is not None
        assert isinstance(encoder, G726Codec)
        assert encoder.bitrate == 24000

    def test_manager_statistics(self) -> None:
        """Test manager statistics"""
        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        manager.create_encoder("call1")
        manager.create_decoder("call2")

        stats = manager.get_statistics()
        assert stats["enabled"]
        assert stats["default_bitrate"] == 32000
        assert stats["active_encoders"] == 1
        assert stats["active_decoders"] == 1


class TestSDPWithNewCodecs:
    """Test SDP generation with G.729 and G.726"""

    def test_sdp_with_g729(self) -> None:
        """Test SDP includes G.729"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100",
            local_port=10000,
            codecs=["0", "18", "101"],  # PCMU, G.729, telephone-event
        )

        assert "m=audio 10000" in sdp
        assert "0 18 101" in sdp  # Payload types in m= line
        assert "a=rtpmap:0 PCMU/8000" in sdp
        assert "a=rtpmap:18 G729/8000" in sdp
        assert "a=rtpmap:101 telephone-event/8000" in sdp

    def test_sdp_with_g726_32(self) -> None:
        """Test SDP includes G.726-32"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100",
            local_port=10000,
            codecs=["0", "2", "101"],  # PCMU, G.726-32, telephone-event
        )

        assert "0 2 101" in sdp
        assert "a=rtpmap:2 G726-32/8000" in sdp

    def test_sdp_with_g726_variants(self) -> None:
        """Test SDP includes G.726 variants"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100",
            local_port=10000,
            codecs=["0", "112", "113", "114", "101"],  # PCMU, G.726 variants, DTMF
        )

        assert "a=rtpmap:112 G726-16/8000" in sdp
        assert "a=rtpmap:113 G726-24/8000" in sdp
        assert "a=rtpmap:114 G726-40/8000" in sdp

    def test_sdp_default_includes_new_codecs(self) -> None:
        """Test default SDP includes G.729 and G.726-32"""
        sdp = SDPBuilder.build_audio_sdp(
            local_ip="192.168.1.100",
            local_port=10000,
            # Using default codecs
        )

        # Default should now include: 0, 8, 9, 18, 2, 101
        assert "a=rtpmap:0 PCMU/8000" in sdp
        assert "a=rtpmap:8 PCMA/8000" in sdp
        assert "a=rtpmap:9 G722/8000" in sdp
        assert "a=rtpmap:18 G729/8000" in sdp
        assert "a=rtpmap:2 G726-32/8000" in sdp
        assert "a=rtpmap:101 telephone-event/8000" in sdp

    def test_sdp_parsing_preserves_new_codecs(self) -> None:
        """Test SDP parser handles new codecs"""
        sdp_text = """v=0
o=pbx 12345 0 IN IP4 192.168.1.100
s=PBX Call
c=IN IP4 192.168.1.100
t=0 0
m=audio 10000 RTP/AVP 0 18 2 101
a=rtpmap:0 PCMU/8000
a=rtpmap:18 G729/8000
a=rtpmap:2 G726-32/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=sendrecv
"""

        session = SDPSession()
        session.parse(sdp_text)

        audio_info = session.get_audio_info()
        assert audio_info is not None
        assert audio_info["port"] == 10000
        assert "0" in audio_info["formats"]
        assert "18" in audio_info["formats"]
        assert "2" in audio_info["formats"]
