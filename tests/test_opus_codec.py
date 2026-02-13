"""
Tests for Opus Codec Support
"""

from typing import Any


from pbx.features.opus_codec import OpusCodec, OpusCodecManager


class MockPBX:
    """Mock PBX for testing"""

    def __init__(self) -> None:
        self.config = MockConfig()


class MockConfig:
    """Mock config for testing"""

    def get(self, key: str, default: Any = None) -> Any:
        return default


class TestOpusCodec:
    """Test OpusCodec class"""

    def test_codec_initialization_default(self) -> None:
        """Test codec initialization with default parameters"""
        codec = OpusCodec()

        assert codec.sample_rate == OpusCodec.DEFAULT_SAMPLE_RATE
        assert codec.bitrate == OpusCodec.DEFAULT_BITRATE
        assert codec.frame_size == OpusCodec.DEFAULT_FRAME_SIZE
        assert codec.channels == OpusCodec.DEFAULT_CHANNELS
        assert codec.fec_enabled
        assert not codec.dtx_enabled

    def test_codec_initialization_custom(self) -> None:
        """Test codec initialization with custom parameters"""
        config = {
            "sample_rate": 16000,
            "bitrate": 24000,
            "frame_size": 40,
            "channels": 2,
            "complexity": 8,
            "application": "audio",
            "fec": False,
            "dtx": True,
        }

        codec = OpusCodec(config)

        assert codec.sample_rate == 16000
        assert codec.bitrate == 24000
        assert codec.frame_size == 40
        assert codec.channels == 2
        assert codec.complexity == 8
        assert codec.application == OpusCodec.APP_AUDIO
        assert not codec.fec_enabled
        assert codec.dtx_enabled

    def test_codec_validation_sample_rate(self) -> None:
        """Test sample rate validation"""
        config = {"sample_rate": 99999}  # Invalid sample rate
        codec = OpusCodec(config)

        # Should fall back to default
        assert codec.sample_rate == OpusCodec.DEFAULT_SAMPLE_RATE

    def test_codec_validation_bitrate(self) -> None:
        """Test bitrate validation"""
        # Too low
        codec1 = OpusCodec({"bitrate": 1000})
        assert codec1.bitrate == OpusCodec.DEFAULT_BITRATE
        # Too high
        codec2 = OpusCodec({"bitrate": 999999})
        assert codec2.bitrate == OpusCodec.DEFAULT_BITRATE
        # Valid
        codec3 = OpusCodec({"bitrate": 64000})
        assert codec3.bitrate == 64000

    def test_codec_validation_complexity(self) -> None:
        """Test complexity validation"""
        # Too low
        codec1 = OpusCodec({"complexity": -1})
        assert codec1.complexity == OpusCodec.DEFAULT_COMPLEXITY
        # Too high
        codec2 = OpusCodec({"complexity": 11})
        assert codec2.complexity == OpusCodec.DEFAULT_COMPLEXITY
        # Valid
        codec3 = OpusCodec({"complexity": 7})
        assert codec3.complexity == 7

    def test_application_types(self) -> None:
        """Test application type configuration"""
        # VoIP (default)
        codec1 = OpusCodec()
        assert codec1.application == OpusCodec.APP_VOIP
        # Audio
        codec2 = OpusCodec({"application": "audio"})
        assert codec2.application == OpusCodec.APP_AUDIO
        # Low delay
        codec3 = OpusCodec({"application": "lowdelay"})
        assert codec3.application == OpusCodec.APP_LOWDELAY

    def test_sdp_parameters(self) -> None:
        """Test SDP parameter generation"""
        codec = OpusCodec({"bitrate": 32000, "frame_size": 20, "fec": True, "dtx": False})

        sdp = codec.get_sdp_parameters()

        assert sdp["payload_type"] == OpusCodec.PAYLOAD_TYPE
        assert sdp["encoding_name"] == "opus"
        assert sdp["clock_rate"] == 48000  # Always 48kHz for Opus RTP
        assert "fmtp" in sdp
        assert isinstance(sdp["fmtp"], str)

    def test_fmtp_string_generation(self) -> None:
        """Test format parameters string generation"""
        codec = OpusCodec({"bitrate": 32000, "frame_size": 20, "fec": True, "dtx": False})

        fmtp = codec._build_fmtp_string()

        # Should contain required parameters
        assert "minptime=20" in fmtp
        assert "useinbandfec=1" in fmtp
        assert "maxaveragebitrate=32000" in fmtp
        assert "usedtx=1" not in fmtp  # DTX is disabled

    def test_fmtp_with_dtx(self) -> None:
        """Test format parameters with DTX enabled"""
        codec = OpusCodec({"dtx": True})

        fmtp = codec._build_fmtp_string()
        assert "usedtx=1" in fmtp

    def test_is_available(self) -> None:
        """Test availability check"""
        codec = OpusCodec()

        # Should return boolean
        assert isinstance(codec.is_available(), bool)

    def test_get_info(self) -> None:
        """Test codec information retrieval"""
        codec = OpusCodec()

        info = codec.get_info()

        # Check structure
        assert "name" in info
        assert "rfc" in info
        assert "available" in info
        assert "configuration" in info
        assert "sdp" in info
        assert "encoder_ready" in info
        assert "decoder_ready" in info
        # Check values
        assert info["name"] == "Opus"
        assert "RFC 6716" in info["rfc"]
        assert isinstance(info["available"], bool)
        assert isinstance(info["configuration"], dict)
        assert not info["encoder_ready"]  # Not created yet
        assert not info["decoder_ready"]  # Not created yet

    def test_encoder_creation_without_library(self) -> None:
        """Test encoder creation when library is not available"""
        codec = OpusCodec()

        # If library is not available, should return None
        if not codec.opus_available:
            encoder = codec.create_encoder()
            assert encoder is None

    def test_decoder_creation_without_library(self) -> None:
        """Test decoder creation when library is not available"""
        codec = OpusCodec()

        # If library is not available, should return None
        if not codec.opus_available:
            decoder = codec.create_decoder()
            assert decoder is None

    def test_encode_without_library(self) -> None:
        """Test encoding when library is not available"""
        codec = OpusCodec()

        if not codec.opus_available:
            # Should return None when library not available
            result = codec.encode(b"\x00" * 1920)  # 20ms @ 48kHz
            assert result is None

    def test_decode_without_library(self) -> None:
        """Test decoding when library is not available"""
        codec = OpusCodec()

        if not codec.opus_available:
            # Should return None when library not available
            result = codec.decode(b"\x00" * 100)
            assert result is None

    def test_packet_loss_concealment_without_library(self) -> None:
        """Test PLC when library is not available"""
        codec = OpusCodec()

        if not codec.opus_available:
            # Should return None when library not available
            result = codec.handle_packet_loss()
            assert result is None

    def test_reset_encoder(self) -> None:
        """Test encoder reset"""
        codec = OpusCodec()

        # Should not crash even if encoder not created
        codec.reset_encoder()

    def test_reset_decoder(self) -> None:
        """Test decoder reset"""
        codec = OpusCodec()

        # Should not crash even if decoder not created
        codec.reset_decoder()

    def test_all_sample_rates(self) -> None:
        """Test all supported sample rates"""
        for rate in OpusCodec.SAMPLE_RATES:
            codec = OpusCodec({"sample_rate": rate})
            assert codec.sample_rate == rate

    def test_bitrate_range(self) -> None:
        """Test various bitrate values"""
        # Valid bitrates
        valid_bitrates = [6000, 8000, 16000, 24000, 32000, 64000, 128000]

        for bitrate in valid_bitrates:
            codec = OpusCodec({"bitrate": bitrate})
            assert codec.bitrate == bitrate

    def test_frame_sizes(self) -> None:
        """Test various frame sizes"""
        frame_sizes = [10, 20, 40, 60]

        for size in frame_sizes:
            codec = OpusCodec({"frame_size": size})
            assert codec.frame_size == size

class TestOpusCodecManager:
    """Test OpusCodecManager class"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.pbx = MockPBX()
        self.manager = OpusCodecManager(self.pbx)

    def test_manager_initialization(self) -> None:
        """Test manager initialization"""
        assert self.manager is not None
        assert len(self.manager.codecs) == 0

    def test_create_codec(self) -> None:
        """Test creating codec for a call"""
        codec = self.manager.create_codec("call-001")

        assert codec is not None
        assert isinstance(codec, OpusCodec)
        assert "call-001" in self.manager.codecs

    def test_create_codec_with_config(self) -> None:
        """Test creating codec with custom config"""
        config = {"sample_rate": 16000, "bitrate": 24000}

        codec = self.manager.create_codec("call-002", config)

        assert codec.sample_rate == 16000
        assert codec.bitrate == 24000

    def test_get_codec(self) -> None:
        """Test retrieving codec for a call"""
        self.manager.create_codec("call-001")

        codec = self.manager.get_codec("call-001")
        assert codec is not None
        assert isinstance(codec, OpusCodec)

    def test_get_nonexistent_codec(self) -> None:
        """Test retrieving codec that doesn't exist"""
        codec = self.manager.get_codec("call-999")
        assert codec is None

    def test_remove_codec(self) -> None:
        """Test removing codec for a call"""
        self.manager.create_codec("call-001")
        assert "call-001" in self.manager.codecs
        self.manager.remove_codec("call-001")
        assert "call-001" not in self.manager.codecs

    def test_remove_nonexistent_codec(self) -> None:
        """Test removing codec that doesn't exist"""
        # Should not crash
        self.manager.remove_codec("call-999")

    def test_get_all_codecs(self) -> None:
        """Test retrieving all active codecs"""
        self.manager.create_codec("call-001")
        self.manager.create_codec("call-002")
        self.manager.create_codec("call-003")

        all_codecs = self.manager.get_all_codecs()

        assert len(all_codecs) == 3
        assert "call-001" in all_codecs
        assert "call-002" in all_codecs
        assert "call-003" in all_codecs

    def test_is_opus_available(self) -> None:
        """Test Opus library availability check"""
        available = self.manager.is_opus_available()
        assert isinstance(available, bool)

    def test_multiple_calls(self) -> None:
        """Test managing codecs for multiple calls"""
        # Create codecs for 10 calls
        for i in range(10):
            call_id = f"call-{i:03d}"
            codec = self.manager.create_codec(call_id)
            assert codec is not None
        # Verify all created
        assert len(self.manager.codecs) == 10
        # Remove half
        for i in range(5):
            call_id = f"call-{i:03d}"
            self.manager.remove_codec(call_id)

        # Verify half remaining
        assert len(self.manager.codecs) == 5

class TestOpusCodecWithLibrary:
    """Test Opus codec with actual library (if available)"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.codec = OpusCodec()

        # Skip tests if library not available
        if not self.codec.opus_available:
            self.skipTest("opuslib not available")

    def test_encoder_creation(self) -> None:
        """Test actual encoder creation"""
        encoder = self.codec.create_encoder()

        assert encoder is not None
        assert self.codec.encoder is not None
        info = self.codec.get_info()
        assert info["encoder_ready"]

    def test_decoder_creation(self) -> None:
        """Test actual decoder creation"""
        decoder = self.codec.create_decoder()

        assert decoder is not None
        assert self.codec.decoder is not None
        info = self.codec.get_info()
        assert info["decoder_ready"]

    def test_encode_decode_cycle(self) -> None:
        """Test encoding and decoding audio"""
        # Create encoder and decoder
        self.codec.create_encoder()
        self.codec.create_decoder()

        # Generate test PCM data (20ms @ 48kHz, mono, 16-bit)
        frame_samples = int(48000 * 20 / 1000)  # 960 samples
        pcm_data = b"\x00\x01" * frame_samples  # Simple test pattern

        # Encode
        encoded = self.codec.encode(pcm_data)
        assert encoded is not None
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0
        # Decode
        decoded = self.codec.decode(encoded)
        assert decoded is not None
        assert isinstance(decoded, bytes)
        assert len(decoded) == len(pcm_data)

    def test_packet_loss_concealment(self) -> None:
        """Test packet loss concealment"""
        # Create decoder
        self.codec.create_decoder()

        # First, decode a normal packet to initialize
        frame_samples = int(48000 * 20 / 1000)
        pcm_data = b"\x00\x01" * frame_samples

        # Encode first to get valid opus data
        self.codec.create_encoder()
        encoded = self.codec.encode(pcm_data)
        self.codec.decode(encoded)

        # Now test PLC for lost packet
        plc_audio = self.codec.handle_packet_loss()
        assert plc_audio is not None
        assert isinstance(plc_audio, bytes)
