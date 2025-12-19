"""
Tests for Opus Codec Support
"""

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.opus_codec import OpusCodec, OpusCodecManager


class MockPBX:
    """Mock PBX for testing"""

    def __init__(self):
        self.config = MockConfig()


class MockConfig:
    """Mock config for testing"""

    def get(self, key, default=None):
        return default


class TestOpusCodec(unittest.TestCase):
    """Test OpusCodec class"""

    def test_codec_initialization_default(self):
        """Test codec initialization with default parameters"""
        codec = OpusCodec()

        self.assertEqual(codec.sample_rate, OpusCodec.DEFAULT_SAMPLE_RATE)
        self.assertEqual(codec.bitrate, OpusCodec.DEFAULT_BITRATE)
        self.assertEqual(codec.frame_size, OpusCodec.DEFAULT_FRAME_SIZE)
        self.assertEqual(codec.channels, OpusCodec.DEFAULT_CHANNELS)
        self.assertTrue(codec.fec_enabled)
        self.assertFalse(codec.dtx_enabled)

    def test_codec_initialization_custom(self):
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

        self.assertEqual(codec.sample_rate, 16000)
        self.assertEqual(codec.bitrate, 24000)
        self.assertEqual(codec.frame_size, 40)
        self.assertEqual(codec.channels, 2)
        self.assertEqual(codec.complexity, 8)
        self.assertEqual(codec.application, OpusCodec.APP_AUDIO)
        self.assertFalse(codec.fec_enabled)
        self.assertTrue(codec.dtx_enabled)

    def test_codec_validation_sample_rate(self):
        """Test sample rate validation"""
        config = {"sample_rate": 99999}  # Invalid sample rate
        codec = OpusCodec(config)

        # Should fall back to default
        self.assertEqual(codec.sample_rate, OpusCodec.DEFAULT_SAMPLE_RATE)

    def test_codec_validation_bitrate(self):
        """Test bitrate validation"""
        # Too low
        codec1 = OpusCodec({"bitrate": 1000})
        self.assertEqual(codec1.bitrate, OpusCodec.DEFAULT_BITRATE)

        # Too high
        codec2 = OpusCodec({"bitrate": 999999})
        self.assertEqual(codec2.bitrate, OpusCodec.DEFAULT_BITRATE)

        # Valid
        codec3 = OpusCodec({"bitrate": 64000})
        self.assertEqual(codec3.bitrate, 64000)

    def test_codec_validation_complexity(self):
        """Test complexity validation"""
        # Too low
        codec1 = OpusCodec({"complexity": -1})
        self.assertEqual(codec1.complexity, OpusCodec.DEFAULT_COMPLEXITY)

        # Too high
        codec2 = OpusCodec({"complexity": 11})
        self.assertEqual(codec2.complexity, OpusCodec.DEFAULT_COMPLEXITY)

        # Valid
        codec3 = OpusCodec({"complexity": 7})
        self.assertEqual(codec3.complexity, 7)

    def test_application_types(self):
        """Test application type configuration"""
        # VoIP (default)
        codec1 = OpusCodec()
        self.assertEqual(codec1.application, OpusCodec.APP_VOIP)

        # Audio
        codec2 = OpusCodec({"application": "audio"})
        self.assertEqual(codec2.application, OpusCodec.APP_AUDIO)

        # Low delay
        codec3 = OpusCodec({"application": "lowdelay"})
        self.assertEqual(codec3.application, OpusCodec.APP_LOWDELAY)

    def test_sdp_parameters(self):
        """Test SDP parameter generation"""
        codec = OpusCodec({"bitrate": 32000, "frame_size": 20, "fec": True, "dtx": False})

        sdp = codec.get_sdp_parameters()

        self.assertEqual(sdp["payload_type"], OpusCodec.PAYLOAD_TYPE)
        self.assertEqual(sdp["encoding_name"], "opus")
        self.assertEqual(sdp["clock_rate"], 48000)  # Always 48kHz for Opus RTP
        self.assertIn("fmtp", sdp)
        self.assertIsInstance(sdp["fmtp"], str)

    def test_fmtp_string_generation(self):
        """Test format parameters string generation"""
        codec = OpusCodec({"bitrate": 32000, "frame_size": 20, "fec": True, "dtx": False})

        fmtp = codec._build_fmtp_string()

        # Should contain required parameters
        self.assertIn("minptime=20", fmtp)
        self.assertIn("useinbandfec=1", fmtp)
        self.assertIn("maxaveragebitrate=32000", fmtp)
        self.assertNotIn("usedtx=1", fmtp)  # DTX is disabled

    def test_fmtp_with_dtx(self):
        """Test format parameters with DTX enabled"""
        codec = OpusCodec({"dtx": True})

        fmtp = codec._build_fmtp_string()
        self.assertIn("usedtx=1", fmtp)

    def test_is_available(self):
        """Test availability check"""
        codec = OpusCodec()

        # Should return boolean
        self.assertIsInstance(codec.is_available(), bool)

    def test_get_info(self):
        """Test codec information retrieval"""
        codec = OpusCodec()

        info = codec.get_info()

        # Check structure
        self.assertIn("name", info)
        self.assertIn("rfc", info)
        self.assertIn("available", info)
        self.assertIn("configuration", info)
        self.assertIn("sdp", info)
        self.assertIn("encoder_ready", info)
        self.assertIn("decoder_ready", info)

        # Check values
        self.assertEqual(info["name"], "Opus")
        self.assertIn("RFC 6716", info["rfc"])
        self.assertIsInstance(info["available"], bool)
        self.assertIsInstance(info["configuration"], dict)
        self.assertFalse(info["encoder_ready"])  # Not created yet
        self.assertFalse(info["decoder_ready"])  # Not created yet

    def test_encoder_creation_without_library(self):
        """Test encoder creation when library is not available"""
        codec = OpusCodec()

        # If library is not available, should return None
        if not codec.opus_available:
            encoder = codec.create_encoder()
            self.assertIsNone(encoder)

    def test_decoder_creation_without_library(self):
        """Test decoder creation when library is not available"""
        codec = OpusCodec()

        # If library is not available, should return None
        if not codec.opus_available:
            decoder = codec.create_decoder()
            self.assertIsNone(decoder)

    def test_encode_without_library(self):
        """Test encoding when library is not available"""
        codec = OpusCodec()

        if not codec.opus_available:
            # Should return None when library not available
            result = codec.encode(b"\x00" * 1920)  # 20ms @ 48kHz
            self.assertIsNone(result)

    def test_decode_without_library(self):
        """Test decoding when library is not available"""
        codec = OpusCodec()

        if not codec.opus_available:
            # Should return None when library not available
            result = codec.decode(b"\x00" * 100)
            self.assertIsNone(result)

    def test_packet_loss_concealment_without_library(self):
        """Test PLC when library is not available"""
        codec = OpusCodec()

        if not codec.opus_available:
            # Should return None when library not available
            result = codec.handle_packet_loss()
            self.assertIsNone(result)

    def test_reset_encoder(self):
        """Test encoder reset"""
        codec = OpusCodec()

        # Should not crash even if encoder not created
        codec.reset_encoder()

    def test_reset_decoder(self):
        """Test decoder reset"""
        codec = OpusCodec()

        # Should not crash even if decoder not created
        codec.reset_decoder()

    def test_all_sample_rates(self):
        """Test all supported sample rates"""
        for rate in OpusCodec.SAMPLE_RATES:
            codec = OpusCodec({"sample_rate": rate})
            self.assertEqual(codec.sample_rate, rate)

    def test_bitrate_range(self):
        """Test various bitrate values"""
        # Valid bitrates
        valid_bitrates = [6000, 8000, 16000, 24000, 32000, 64000, 128000]

        for bitrate in valid_bitrates:
            codec = OpusCodec({"bitrate": bitrate})
            self.assertEqual(codec.bitrate, bitrate)

    def test_frame_sizes(self):
        """Test various frame sizes"""
        frame_sizes = [10, 20, 40, 60]

        for size in frame_sizes:
            codec = OpusCodec({"frame_size": size})
            self.assertEqual(codec.frame_size, size)


class TestOpusCodecManager(unittest.TestCase):
    """Test OpusCodecManager class"""

    def setUp(self):
        """Set up test fixtures"""
        self.pbx = MockPBX()
        self.manager = OpusCodecManager(self.pbx)

    def test_manager_initialization(self):
        """Test manager initialization"""
        self.assertIsNotNone(self.manager)
        self.assertEqual(len(self.manager.codecs), 0)

    def test_create_codec(self):
        """Test creating codec for a call"""
        codec = self.manager.create_codec("call-001")

        self.assertIsNotNone(codec)
        self.assertIsInstance(codec, OpusCodec)
        self.assertIn("call-001", self.manager.codecs)

    def test_create_codec_with_config(self):
        """Test creating codec with custom config"""
        config = {"sample_rate": 16000, "bitrate": 24000}

        codec = self.manager.create_codec("call-002", config)

        self.assertEqual(codec.sample_rate, 16000)
        self.assertEqual(codec.bitrate, 24000)

    def test_get_codec(self):
        """Test retrieving codec for a call"""
        self.manager.create_codec("call-001")

        codec = self.manager.get_codec("call-001")
        self.assertIsNotNone(codec)
        self.assertIsInstance(codec, OpusCodec)

    def test_get_nonexistent_codec(self):
        """Test retrieving codec that doesn't exist"""
        codec = self.manager.get_codec("call-999")
        self.assertIsNone(codec)

    def test_remove_codec(self):
        """Test removing codec for a call"""
        self.manager.create_codec("call-001")
        self.assertIn("call-001", self.manager.codecs)

        self.manager.remove_codec("call-001")
        self.assertNotIn("call-001", self.manager.codecs)

    def test_remove_nonexistent_codec(self):
        """Test removing codec that doesn't exist"""
        # Should not crash
        self.manager.remove_codec("call-999")

    def test_get_all_codecs(self):
        """Test retrieving all active codecs"""
        self.manager.create_codec("call-001")
        self.manager.create_codec("call-002")
        self.manager.create_codec("call-003")

        all_codecs = self.manager.get_all_codecs()

        self.assertEqual(len(all_codecs), 3)
        self.assertIn("call-001", all_codecs)
        self.assertIn("call-002", all_codecs)
        self.assertIn("call-003", all_codecs)

    def test_is_opus_available(self):
        """Test Opus library availability check"""
        available = self.manager.is_opus_available()
        self.assertIsInstance(available, bool)

    def test_multiple_calls(self):
        """Test managing codecs for multiple calls"""
        # Create codecs for 10 calls
        for i in range(10):
            call_id = f"call-{i:03d}"
            codec = self.manager.create_codec(call_id)
            self.assertIsNotNone(codec)

        # Verify all created
        self.assertEqual(len(self.manager.codecs), 10)

        # Remove half
        for i in range(5):
            call_id = f"call-{i:03d}"
            self.manager.remove_codec(call_id)

        # Verify half remaining
        self.assertEqual(len(self.manager.codecs), 5)


class TestOpusCodecWithLibrary(unittest.TestCase):
    """Test Opus codec with actual library (if available)"""

    def setUp(self):
        """Set up test fixtures"""
        self.codec = OpusCodec()

        # Skip tests if library not available
        if not self.codec.opus_available:
            self.skipTest("opuslib not available")

    def test_encoder_creation(self):
        """Test actual encoder creation"""
        encoder = self.codec.create_encoder()

        self.assertIsNotNone(encoder)
        self.assertIsNotNone(self.codec.encoder)

        info = self.codec.get_info()
        self.assertTrue(info["encoder_ready"])

    def test_decoder_creation(self):
        """Test actual decoder creation"""
        decoder = self.codec.create_decoder()

        self.assertIsNotNone(decoder)
        self.assertIsNotNone(self.codec.decoder)

        info = self.codec.get_info()
        self.assertTrue(info["decoder_ready"])

    def test_encode_decode_cycle(self):
        """Test encoding and decoding audio"""
        # Create encoder and decoder
        self.codec.create_encoder()
        self.codec.create_decoder()

        # Generate test PCM data (20ms @ 48kHz, mono, 16-bit)
        frame_samples = int(48000 * 20 / 1000)  # 960 samples
        pcm_data = b"\x00\x01" * frame_samples  # Simple test pattern

        # Encode
        encoded = self.codec.encode(pcm_data)
        self.assertIsNotNone(encoded)
        self.assertIsInstance(encoded, bytes)
        self.assertGreater(len(encoded), 0)

        # Decode
        decoded = self.codec.decode(encoded)
        self.assertIsNotNone(decoded)
        self.assertIsInstance(decoded, bytes)
        self.assertEqual(len(decoded), len(pcm_data))

    def test_packet_loss_concealment(self):
        """Test packet loss concealment"""
        # Create decoder
        self.codec.create_decoder()

        # First, decode a normal packet to initialize
        frame_samples = int(48000 * 20 / 1000)
        pcm_data = b"\x00\x01" * frame_samples

        # Encode first to get valid opus data
        self.codec.create_encoder()
        encoded = self.codec.encode(pcm_data)
        decoded1 = self.codec.decode(encoded)

        # Now test PLC for lost packet
        plc_audio = self.codec.handle_packet_loss()
        self.assertIsNotNone(plc_audio)
        self.assertIsInstance(plc_audio, bytes)


if __name__ == "__main__":
    unittest.main()
