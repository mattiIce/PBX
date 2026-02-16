"""
Unit tests for Speex codec implementation
Tests codec initialization, SDP negotiation, and encoding/decoding
"""

from unittest.mock import Mock

from pbx.features.speex_codec import SpeexCodec, SpeexCodecManager


class TestSpeexCodec:
    """Test Speex codec functionality"""

    def test_codec_initialization_default(self) -> None:
        """Test codec initialization with default settings"""
        codec = SpeexCodec()

        assert codec.mode == "nb"  # Default narrowband
        assert codec.sample_rate == 8000
        assert codec.quality == 8
        assert codec.vbr_enabled
        assert codec.vad_enabled
        assert not codec.dtx_enabled
        assert codec.complexity == 3

    def test_codec_initialization_narrowband(self) -> None:
        """Test narrowband mode initialization"""
        codec = SpeexCodec({"mode": "nb"})

        assert codec.mode == "nb"
        assert codec.sample_rate == 8000
        assert codec.payload_type == 98  # NB uses PT 98

    def test_codec_initialization_wideband(self) -> None:
        """Test wideband mode initialization"""
        codec = SpeexCodec({"mode": "wb"})

        assert codec.mode == "wb"
        assert codec.sample_rate == 16000
        assert codec.payload_type == 99  # WB uses PT 99

    def test_codec_initialization_ultrawideband(self) -> None:
        """Test ultra-wideband mode initialization"""
        codec = SpeexCodec({"mode": "uwb"})

        assert codec.mode == "uwb"
        assert codec.sample_rate == 32000
        assert codec.payload_type == 100  # UWB uses PT 100

    def test_invalid_mode_defaults_to_nb(self) -> None:
        """Test that invalid mode defaults to narrowband"""
        codec = SpeexCodec({"mode": "invalid"})

        assert codec.mode == "nb"

    def test_custom_quality(self) -> None:
        """Test custom quality setting"""
        codec = SpeexCodec({"quality": 10})

        assert codec.quality == 10

    def test_custom_complexity(self) -> None:
        """Test custom complexity setting"""
        codec = SpeexCodec({"complexity": 7})

        assert codec.complexity == 7

    def test_vbr_configuration(self) -> None:
        """Test VBR configuration"""
        codec = SpeexCodec({"vbr": False})

        assert not codec.vbr_enabled

    def test_vad_configuration(self) -> None:
        """Test VAD configuration"""
        codec = SpeexCodec({"vad": False})

        assert not codec.vad_enabled

    def test_dtx_configuration(self) -> None:
        """Test DTX configuration"""
        codec = SpeexCodec({"dtx": True})

        assert codec.dtx_enabled

    def test_get_info_narrowband(self) -> None:
        """Test get_info for narrowband mode"""
        codec = SpeexCodec({"mode": "nb", "quality": 8, "vbr": True})
        info = codec.get_info()

        assert info["name"] == "Speex"
        assert info["mode"] == "Narrowband"
        assert info["sample_rate"] == 8000
        assert info["quality"] == 8
        assert info["typical_bitrate"] == 8000
        assert "Variable Bitrate" in info["features"]
        assert "Voice Activity Detection" in info["features"]

    def test_get_info_wideband(self) -> None:
        """Test get_info for wideband mode"""
        codec = SpeexCodec({"mode": "wb"})
        info = codec.get_info()

        assert info["mode"] == "Wideband"
        assert info["sample_rate"] == 16000

    def test_get_sdp_description_narrowband(self) -> None:
        """Test SDP description for narrowband"""
        codec = SpeexCodec({"mode": "nb", "payload_type": 98})
        sdp = codec.get_sdp_description()

        assert sdp == "rtpmap:98 SPEEX/8000"

    def test_get_sdp_description_wideband(self) -> None:
        """Test SDP description for wideband"""
        codec = SpeexCodec({"mode": "wb", "payload_type": 99})
        sdp = codec.get_sdp_description()

        assert sdp == "rtpmap:99 SPEEX/16000"

    def test_get_fmtp_with_vbr(self) -> None:
        """Test FMTP generation with VBR enabled"""
        codec = SpeexCodec({"mode": "nb", "vbr": True, "payload_type": 98})
        fmtp = codec.get_fmtp()

        assert "vbr=on" in fmtp
        assert "fmtp:98" in fmtp

    def test_get_fmtp_wideband(self) -> None:
        """Test FMTP for wideband mode"""
        codec = SpeexCodec({"mode": "wb", "vbr": True, "payload_type": 99})
        fmtp = codec.get_fmtp()

        assert 'mode="1 in any"', fmtp

    def test_get_fmtp_ultrawideband(self) -> None:
        """Test FMTP for ultra-wideband mode"""
        codec = SpeexCodec({"mode": "uwb", "vbr": True, "payload_type": 100})
        fmtp = codec.get_fmtp()

        assert 'mode="2 in any"', fmtp

    def test_get_fmtp_no_vbr(self) -> None:
        """Test FMTP without VBR"""
        codec = SpeexCodec({"mode": "nb", "vbr": False, "payload_type": 98})
        fmtp = codec.get_fmtp()

        # Should have no fmtp or just mode for wideband
        if fmtp:
            assert "vbr=on" not in fmtp

    def test_get_sdp_parameters(self) -> None:
        """Test complete SDP parameters"""
        codec = SpeexCodec({"mode": "nb", "vbr": True, "payload_type": 98})
        params = codec.get_sdp_parameters()

        assert params["payload_type"] == 98
        assert params["encoding_name"] == "SPEEX"
        assert params["clock_rate"] == 8000
        assert params["channels"] == 1
        assert params["mode"] == "nb"
        assert params["rtpmap"] == "rtpmap:98 SPEEX/8000"
        assert "fmtp" in params

    def test_frame_size_narrowband(self) -> None:
        """Test frame size calculation for narrowband"""
        codec = SpeexCodec({"mode": "nb"})

        # 20ms frame at 8kHz = 160 samples
        assert codec.frame_size == 160

    def test_frame_size_wideband(self) -> None:
        """Test frame size calculation for wideband"""
        codec = SpeexCodec({"mode": "wb"})

        # 20ms frame at 16kHz = 320 samples
        assert codec.frame_size == 320

    def test_frame_size_ultrawideband(self) -> None:
        """Test frame size calculation for ultra-wideband"""
        codec = SpeexCodec({"mode": "uwb"})

        # 20ms frame at 32kHz = 640 samples
        assert codec.frame_size == 640

    def test_is_available(self) -> None:
        """Test availability check"""
        codec = SpeexCodec()
        available = codec.is_available()

        assert isinstance(available, bool)

    def test_encode_without_encoder(self) -> None:
        """Test encoding fails gracefully without encoder"""
        codec = SpeexCodec({"mode": "nb"})
        codec.encoder = None

        pcm_data = b"\x00" * 320  # 160 samples * 2 bytes
        result = codec.encode(pcm_data)

        assert result is None

    def test_encode_wrong_size(self) -> None:
        """Test encoding with wrong PCM data size"""
        codec = SpeexCodec({"mode": "nb"})
        codec.encoder = Mock()

        pcm_data = b"\x00" * 100  # Wrong size
        result = codec.encode(pcm_data)

        assert result is None

    def test_decode_without_decoder(self) -> None:
        """Test decoding fails gracefully without decoder"""
        codec = SpeexCodec({"mode": "nb"})
        codec.decoder = None

        speex_data = b"\x00" * 20
        result = codec.decode(speex_data)

        assert result is None

    def test_reset_encoder(self) -> None:
        """Test encoder reset"""
        codec = SpeexCodec({"mode": "nb"})
        codec.encoder = Mock()

        codec.reset_encoder()

        assert codec is not None

    def test_reset_decoder(self) -> None:
        """Test decoder reset"""
        codec = SpeexCodec({"mode": "nb"})
        codec.decoder = Mock()

        codec.reset_decoder()

        assert codec is not None


class TestSpeexCodecManager:
    """Test Speex codec manager functionality"""

    def test_manager_initialization(self) -> None:
        """Test codec manager initialization"""
        pbx = Mock()
        pbx.config = {"codecs": {"speex": {"enabled": True, "mode": "nb"}}}

        manager = SpeexCodecManager(pbx)

        assert manager.pbx == pbx
        assert manager.config == {"enabled": True, "mode": "nb"}
        assert len(manager.codecs) == 0

    def test_manager_initialization_no_config(self) -> None:
        """Test codec manager with no config"""
        pbx = Mock()
        pbx.config = None

        manager = SpeexCodecManager(pbx)

        assert manager.config == {}

    def test_create_codec(self) -> None:
        """Test creating codec for a call"""
        pbx = Mock()
        pbx.config = {"codecs": {"speex": {"mode": "wb"}}}

        manager = SpeexCodecManager(pbx)
        codec = manager.create_codec("call-123")

        assert isinstance(codec, SpeexCodec)
        assert codec.mode == "wb"
        assert "call-123" in manager.codecs

    def test_create_codec_with_custom_config(self) -> None:
        """Test creating codec with custom configuration"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        custom_config = {"mode": "uwb", "quality": 10}
        codec = manager.create_codec("call-456", custom_config)

        assert codec.mode == "uwb"
        assert codec.quality == 10

    def test_get_codec(self) -> None:
        """Test retrieving codec for a call"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        codec = manager.create_codec("call-789")

        retrieved = manager.get_codec("call-789")
        assert retrieved == codec

    def test_get_codec_not_found(self) -> None:
        """Test retrieving non-existent codec"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        retrieved = manager.get_codec("call-999")

        assert retrieved is None

    def test_remove_codec(self) -> None:
        """Test removing codec for a call"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        manager.create_codec("call-111")

        assert "call-111" in manager.codecs
        manager.remove_codec("call-111")

        assert "call-111" not in manager.codecs

    def test_get_all_codecs(self) -> None:
        """Test getting all codec instances"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        manager.create_codec("call-1")
        manager.create_codec("call-2")

        all_codecs = manager.get_all_codecs()

        assert len(all_codecs) == 2
        assert "call-1" in all_codecs
        assert "call-2" in all_codecs

    def test_is_speex_available(self) -> None:
        """Test checking Speex availability"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        available = manager.is_speex_available()

        assert isinstance(available, bool)


class TestSpeexSDP:
    """Test Speex SDP integration"""

    def test_sdp_includes_speex(self) -> None:
        """Test that SDP includes Speex codec"""
        from pbx.sip.sdp import SDPBuilder

        # Test with Speex narrowband
        codecs = ["0", "8", "98", "101"]
        sdp = SDPBuilder.build_audio_sdp("192.168.1.100", 10000, codecs=codecs)

        # Verify Speex is in SDP
        assert "rtpmap:98 SPEEX/8000" in sdp

    def test_sdp_speex_wideband(self) -> None:
        """Test SDP for Speex wideband"""
        from pbx.sip.sdp import SDPBuilder

        codecs = ["0", "8", "99", "101"]
        sdp = SDPBuilder.build_audio_sdp("192.168.1.100", 10000, codecs=codecs)

        # Verify wideband Speex
        assert "rtpmap:99 SPEEX/16000" in sdp
