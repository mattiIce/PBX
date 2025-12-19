"""
Unit tests for Speex codec implementation
Tests codec initialization, SDP negotiation, and encoding/decoding
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.speex_codec import SpeexCodec, SpeexCodecManager


class TestSpeexCodec(unittest.TestCase):
    """Test Speex codec functionality"""

    def test_codec_initialization_default(self):
        """Test codec initialization with default settings"""
        codec = SpeexCodec()

        self.assertEqual(codec.mode, "nb")  # Default narrowband
        self.assertEqual(codec.sample_rate, 8000)
        self.assertEqual(codec.quality, 8)
        self.assertTrue(codec.vbr_enabled)
        self.assertTrue(codec.vad_enabled)
        self.assertFalse(codec.dtx_enabled)
        self.assertEqual(codec.complexity, 3)

    def test_codec_initialization_narrowband(self):
        """Test narrowband mode initialization"""
        codec = SpeexCodec({"mode": "nb"})

        self.assertEqual(codec.mode, "nb")
        self.assertEqual(codec.sample_rate, 8000)
        self.assertEqual(codec.payload_type, 98)  # NB uses PT 98

    def test_codec_initialization_wideband(self):
        """Test wideband mode initialization"""
        codec = SpeexCodec({"mode": "wb"})

        self.assertEqual(codec.mode, "wb")
        self.assertEqual(codec.sample_rate, 16000)
        self.assertEqual(codec.payload_type, 99)  # WB uses PT 99

    def test_codec_initialization_ultrawideband(self):
        """Test ultra-wideband mode initialization"""
        codec = SpeexCodec({"mode": "uwb"})

        self.assertEqual(codec.mode, "uwb")
        self.assertEqual(codec.sample_rate, 32000)
        self.assertEqual(codec.payload_type, 100)  # UWB uses PT 100

    def test_invalid_mode_defaults_to_nb(self):
        """Test that invalid mode defaults to narrowband"""
        codec = SpeexCodec({"mode": "invalid"})

        self.assertEqual(codec.mode, "nb")

    def test_custom_quality(self):
        """Test custom quality setting"""
        codec = SpeexCodec({"quality": 10})

        self.assertEqual(codec.quality, 10)

    def test_custom_complexity(self):
        """Test custom complexity setting"""
        codec = SpeexCodec({"complexity": 7})

        self.assertEqual(codec.complexity, 7)

    def test_vbr_configuration(self):
        """Test VBR configuration"""
        codec = SpeexCodec({"vbr": False})

        self.assertFalse(codec.vbr_enabled)

    def test_vad_configuration(self):
        """Test VAD configuration"""
        codec = SpeexCodec({"vad": False})

        self.assertFalse(codec.vad_enabled)

    def test_dtx_configuration(self):
        """Test DTX configuration"""
        codec = SpeexCodec({"dtx": True})

        self.assertTrue(codec.dtx_enabled)

    def test_get_info_narrowband(self):
        """Test get_info for narrowband mode"""
        codec = SpeexCodec({"mode": "nb", "quality": 8, "vbr": True})
        info = codec.get_info()

        self.assertEqual(info["name"], "Speex")
        self.assertEqual(info["mode"], "Narrowband")
        self.assertEqual(info["sample_rate"], 8000)
        self.assertEqual(info["quality"], 8)
        self.assertEqual(info["typical_bitrate"], 8000)
        self.assertIn("Variable Bitrate", info["features"])
        self.assertIn("Voice Activity Detection", info["features"])

    def test_get_info_wideband(self):
        """Test get_info for wideband mode"""
        codec = SpeexCodec({"mode": "wb"})
        info = codec.get_info()

        self.assertEqual(info["mode"], "Wideband")
        self.assertEqual(info["sample_rate"], 16000)

    def test_get_sdp_description_narrowband(self):
        """Test SDP description for narrowband"""
        codec = SpeexCodec({"mode": "nb", "payload_type": 98})
        sdp = codec.get_sdp_description()

        self.assertEqual(sdp, "rtpmap:98 SPEEX/8000")

    def test_get_sdp_description_wideband(self):
        """Test SDP description for wideband"""
        codec = SpeexCodec({"mode": "wb", "payload_type": 99})
        sdp = codec.get_sdp_description()

        self.assertEqual(sdp, "rtpmap:99 SPEEX/16000")

    def test_get_fmtp_with_vbr(self):
        """Test FMTP generation with VBR enabled"""
        codec = SpeexCodec({"mode": "nb", "vbr": True, "payload_type": 98})
        fmtp = codec.get_fmtp()

        self.assertIn("vbr=on", fmtp)
        self.assertIn("fmtp:98", fmtp)

    def test_get_fmtp_wideband(self):
        """Test FMTP for wideband mode"""
        codec = SpeexCodec({"mode": "wb", "vbr": True, "payload_type": 99})
        fmtp = codec.get_fmtp()

        self.assertIn('mode="1,any"', fmtp)

    def test_get_fmtp_ultrawideband(self):
        """Test FMTP for ultra-wideband mode"""
        codec = SpeexCodec({"mode": "uwb", "vbr": True, "payload_type": 100})
        fmtp = codec.get_fmtp()

        self.assertIn('mode="2,any"', fmtp)

    def test_get_fmtp_no_vbr(self):
        """Test FMTP without VBR"""
        codec = SpeexCodec({"mode": "nb", "vbr": False, "payload_type": 98})
        fmtp = codec.get_fmtp()

        # Should have no fmtp or just mode for wideband
        if fmtp:
            self.assertNotIn("vbr=on", fmtp)

    def test_get_sdp_parameters(self):
        """Test complete SDP parameters"""
        codec = SpeexCodec({"mode": "nb", "vbr": True, "payload_type": 98})
        params = codec.get_sdp_parameters()

        self.assertEqual(params["payload_type"], 98)
        self.assertEqual(params["encoding_name"], "SPEEX")
        self.assertEqual(params["clock_rate"], 8000)
        self.assertEqual(params["channels"], 1)
        self.assertEqual(params["mode"], "nb")
        self.assertEqual(params["rtpmap"], "rtpmap:98 SPEEX/8000")
        self.assertIn("fmtp", params)

    def test_frame_size_narrowband(self):
        """Test frame size calculation for narrowband"""
        codec = SpeexCodec({"mode": "nb"})

        # 20ms frame at 8kHz = 160 samples
        self.assertEqual(codec.frame_size, 160)

    def test_frame_size_wideband(self):
        """Test frame size calculation for wideband"""
        codec = SpeexCodec({"mode": "wb"})

        # 20ms frame at 16kHz = 320 samples
        self.assertEqual(codec.frame_size, 320)

    def test_frame_size_ultrawideband(self):
        """Test frame size calculation for ultra-wideband"""
        codec = SpeexCodec({"mode": "uwb"})

        # 20ms frame at 32kHz = 640 samples
        self.assertEqual(codec.frame_size, 640)

    def test_is_available(self):
        """Test availability check"""
        codec = SpeexCodec()
        available = codec.is_available()

        self.assertIsInstance(available, bool)

    def test_encode_without_encoder(self):
        """Test encoding fails gracefully without encoder"""
        codec = SpeexCodec({"mode": "nb"})
        codec.encoder = None

        pcm_data = b"\x00" * 320  # 160 samples * 2 bytes
        result = codec.encode(pcm_data)

        self.assertIsNone(result)

    def test_encode_wrong_size(self):
        """Test encoding with wrong PCM data size"""
        codec = SpeexCodec({"mode": "nb"})
        codec.encoder = Mock()

        pcm_data = b"\x00" * 100  # Wrong size
        result = codec.encode(pcm_data)

        self.assertIsNone(result)

    def test_decode_without_decoder(self):
        """Test decoding fails gracefully without decoder"""
        codec = SpeexCodec({"mode": "nb"})
        codec.decoder = None

        speex_data = b"\x00" * 20
        result = codec.decode(speex_data)

        self.assertIsNone(result)

    def test_reset_encoder(self):
        """Test encoder reset"""
        codec = SpeexCodec({"mode": "nb"})
        codec.encoder = Mock()

        codec.reset_encoder()

        self.assertIsNotNone(codec)

    def test_reset_decoder(self):
        """Test decoder reset"""
        codec = SpeexCodec({"mode": "nb"})
        codec.decoder = Mock()

        codec.reset_decoder()

        self.assertIsNotNone(codec)


class TestSpeexCodecManager(unittest.TestCase):
    """Test Speex codec manager functionality"""

    def test_manager_initialization(self):
        """Test codec manager initialization"""
        pbx = Mock()
        pbx.config = {"codecs": {"speex": {"enabled": True, "mode": "nb"}}}

        manager = SpeexCodecManager(pbx)

        self.assertEqual(manager.pbx, pbx)
        self.assertEqual(manager.config, {"enabled": True, "mode": "nb"})
        self.assertEqual(len(manager.codecs), 0)

    def test_manager_initialization_no_config(self):
        """Test codec manager with no config"""
        pbx = Mock()
        pbx.config = None

        manager = SpeexCodecManager(pbx)

        self.assertEqual(manager.config, {})

    def test_create_codec(self):
        """Test creating codec for a call"""
        pbx = Mock()
        pbx.config = {"codecs": {"speex": {"mode": "wb"}}}

        manager = SpeexCodecManager(pbx)
        codec = manager.create_codec("call-123")

        self.assertIsInstance(codec, SpeexCodec)
        self.assertEqual(codec.mode, "wb")
        self.assertIn("call-123", manager.codecs)

    def test_create_codec_with_custom_config(self):
        """Test creating codec with custom configuration"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        custom_config = {"mode": "uwb", "quality": 10}
        codec = manager.create_codec("call-456", custom_config)

        self.assertEqual(codec.mode, "uwb")
        self.assertEqual(codec.quality, 10)

    def test_get_codec(self):
        """Test retrieving codec for a call"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        codec = manager.create_codec("call-789")

        retrieved = manager.get_codec("call-789")
        self.assertEqual(retrieved, codec)

    def test_get_codec_not_found(self):
        """Test retrieving non-existent codec"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        retrieved = manager.get_codec("call-999")

        self.assertIsNone(retrieved)

    def test_remove_codec(self):
        """Test removing codec for a call"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        manager.create_codec("call-111")

        self.assertIn("call-111", manager.codecs)

        manager.remove_codec("call-111")

        self.assertNotIn("call-111", manager.codecs)

    def test_get_all_codecs(self):
        """Test getting all codec instances"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        codec1 = manager.create_codec("call-1")
        codec2 = manager.create_codec("call-2")

        all_codecs = manager.get_all_codecs()

        self.assertEqual(len(all_codecs), 2)
        self.assertIn("call-1", all_codecs)
        self.assertIn("call-2", all_codecs)

    def test_is_speex_available(self):
        """Test checking Speex availability"""
        pbx = Mock()
        pbx.config = {}

        manager = SpeexCodecManager(pbx)
        available = manager.is_speex_available()

        self.assertIsInstance(available, bool)


class TestSpeexSDP(unittest.TestCase):
    """Test Speex SDP integration"""

    def test_sdp_includes_speex(self):
        """Test that SDP includes Speex codec"""
        from pbx.sip.sdp import SDPBuilder

        # Test with Speex narrowband
        codecs = ["0", "8", "98", "101"]
        sdp = SDPBuilder.build_audio_sdp("192.168.1.100", 10000, codecs=codecs)

        # Verify Speex is in SDP
        self.assertIn("rtpmap:98 SPEEX/8000", sdp)

    def test_sdp_speex_wideband(self):
        """Test SDP for Speex wideband"""
        from pbx.sip.sdp import SDPBuilder

        codecs = ["0", "8", "99", "101"]
        sdp = SDPBuilder.build_audio_sdp("192.168.1.100", 10000, codecs=codecs)

        # Verify wideband Speex
        self.assertIn("rtpmap:99 SPEEX/16000", sdp)


if __name__ == "__main__":
    unittest.main()
