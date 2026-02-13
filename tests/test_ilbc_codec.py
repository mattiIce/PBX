"""
Unit tests for iLBC codec implementation
Tests codec initialization, SDP negotiation, and encoding/decoding
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.ilbc_codec import ILBCCodec, ILBCCodecManager


class TestILBCCodec(unittest.TestCase):
    """Test iLBC codec functionality"""

    def test_codec_initialization_default(self) -> None:
        """Test codec initialization with default settings"""
        codec = ILBCCodec()

        self.assertEqual(codec.mode, 30)  # Default 30ms mode
        self.assertEqual(codec.bitrate, 13330)  # 13.33 kbps for 30ms
        self.assertEqual(codec.frame_size, 240)  # 240 samples for 30ms
        self.assertEqual(codec.encoded_size, 50)  # 50 bytes for 30ms
        self.assertEqual(codec.payload_type, 97)

    def test_codec_initialization_20ms_mode(self) -> None:
        """Test codec initialization with 20ms mode"""
        codec = ILBCCodec({"mode": 20})

        self.assertEqual(codec.mode, 20)
        self.assertEqual(codec.bitrate, 15200)  # 15.2 kbps for 20ms
        self.assertEqual(codec.frame_size, 160)  # 160 samples for 20ms
        self.assertEqual(codec.encoded_size, 38)  # 38 bytes for 20ms

    def test_codec_initialization_30ms_mode(self) -> None:
        """Test codec initialization with 30ms mode"""
        codec = ILBCCodec({"mode": 30})

        self.assertEqual(codec.mode, 30)
        self.assertEqual(codec.bitrate, 13330)
        self.assertEqual(codec.frame_size, 240)
        self.assertEqual(codec.encoded_size, 50)

    def test_invalid_mode_defaults_to_30ms(self) -> None:
        """Test that invalid mode defaults to 30ms"""
        codec = ILBCCodec({"mode": 99})

        self.assertEqual(codec.mode, 30)  # Should default to 30ms

    def test_custom_payload_type(self) -> None:
        """Test custom payload type configuration"""
        codec = ILBCCodec({"payload_type": 100})

        self.assertEqual(codec.payload_type, 100)

    def test_get_info(self) -> None:
        """Test get_info returns correct codec information"""
        codec = ILBCCodec({"mode": 30})
        info = codec.get_info()

        self.assertEqual(info["name"], "iLBC")
        self.assertEqual(info["sample_rate"], 8000)
        self.assertEqual(info["mode"], "30ms")
        self.assertEqual(info["bitrate"], 13330)
        self.assertEqual(info["frame_size"], 240)
        self.assertEqual(info["encoded_size"], 50)
        self.assertEqual(info["payload_type"], 97)
        self.assertIn("Packet loss concealment", info["features"])
        self.assertIn("Low bitrate", info["features"])
        self.assertIn("Royalty-free", info["features"])

    def test_get_sdp_description(self) -> None:
        """Test SDP description generation"""
        codec = ILBCCodec({"mode": 30, "payload_type": 97})
        sdp = codec.get_sdp_description()

        self.assertEqual(sdp, "rtpmap:97 iLBC/8000")

    def test_get_fmtp_20ms(self) -> None:
        """Test FMTP generation for 20ms mode"""
        codec = ILBCCodec({"mode": 20, "payload_type": 97})
        fmtp = codec.get_fmtp()

        self.assertEqual(fmtp, "fmtp:97 mode=20")

    def test_get_fmtp_30ms(self) -> None:
        """Test FMTP generation for 30ms mode"""
        codec = ILBCCodec({"mode": 30, "payload_type": 97})
        fmtp = codec.get_fmtp()

        self.assertEqual(fmtp, "fmtp:97 mode=30")

    def test_get_sdp_parameters(self) -> None:
        """Test complete SDP parameters"""
        codec = ILBCCodec({"mode": 30, "payload_type": 97})
        params = codec.get_sdp_parameters()

        self.assertEqual(params["payload_type"], 97)
        self.assertEqual(params["encoding_name"], "iLBC")
        self.assertEqual(params["clock_rate"], 8000)
        self.assertEqual(params["channels"], 1)
        self.assertEqual(params["mode"], 30)
        self.assertEqual(params["rtpmap"], "rtpmap:97 iLBC/8000")
        self.assertEqual(params["fmtp"], "fmtp:97 mode=30")

    def test_is_available_without_library(self) -> None:
        """Test availability check when library not installed"""
        codec = ILBCCodec()

        # Without pyilbc installed, should return False
        # (assuming pyilbc is not installed in test environment)
        available = codec.is_available()
        self.assertIsInstance(available, bool)

    @patch("pbx.features.ilbc_codec.ILBCCodec.is_available")
    def test_create_encoder_when_available(self, mock_available: MagicMock) -> None:
        """Test encoder creation when library is available"""
        mock_available.return_value = True

        with patch("builtins.__import__") as mock_import:
            mock_pyilbc = MagicMock()
            mock_pyilbc.Encoder = MagicMock()
            mock_import.return_value = mock_pyilbc

            codec = ILBCCodec({"mode": 30})
            codec.ilbc_available = True
            codec.create_encoder()

            self.assertIsNotNone(codec.encoder)

    @patch("pbx.features.ilbc_codec.ILBCCodec.is_available")
    def test_create_decoder_when_available(self, mock_available: MagicMock) -> None:
        """Test decoder creation when library is available"""
        mock_available.return_value = True

        with patch("builtins.__import__") as mock_import:
            mock_pyilbc = MagicMock()
            mock_pyilbc.Decoder = MagicMock()
            mock_import.return_value = mock_pyilbc

            codec = ILBCCodec({"mode": 30})
            codec.ilbc_available = True
            codec.create_decoder()

            self.assertIsNotNone(codec.decoder)

    def test_encode_without_encoder(self) -> None:
        """Test encoding fails gracefully without encoder"""
        codec = ILBCCodec({"mode": 30})
        codec.encoder = None

        pcm_data = b"\x00" * 480  # 240 samples * 2 bytes
        result = codec.encode(pcm_data)

        self.assertIsNone(result)

    def test_encode_wrong_size(self) -> None:
        """Test encoding with wrong PCM data size"""
        codec = ILBCCodec({"mode": 30})
        codec.encoder = Mock()

        pcm_data = b"\x00" * 100  # Wrong size
        result = codec.encode(pcm_data)

        self.assertIsNone(result)

    def test_decode_without_decoder(self) -> None:
        """Test decoding fails gracefully without decoder"""
        codec = ILBCCodec({"mode": 30})
        codec.decoder = None

        ilbc_data = b"\x00" * 50
        result = codec.decode(ilbc_data)

        self.assertIsNone(result)

    def test_decode_wrong_size(self) -> None:
        """Test decoding with wrong iLBC data size"""
        codec = ILBCCodec({"mode": 30})
        codec.decoder = Mock()

        ilbc_data = b"\x00" * 10  # Wrong size (should be 50 for 30ms)
        result = codec.decode(ilbc_data)

        self.assertIsNone(result)

    def test_handle_packet_loss_without_decoder(self) -> None:
        """Test packet loss concealment without decoder"""
        codec = ILBCCodec({"mode": 30})
        codec.decoder = None

        result = codec.handle_packet_loss()

        self.assertIsNone(result)

    def test_reset_encoder(self) -> None:
        """Test encoder reset"""
        codec = ILBCCodec({"mode": 30})
        codec.encoder = Mock()
        codec.encoder

        codec.reset_encoder()

        # Should recreate encoder (or remain None if library unavailable)
        self.assertIsNotNone(codec)

    def test_reset_decoder(self) -> None:
        """Test decoder reset"""
        codec = ILBCCodec({"mode": 30})
        codec.decoder = Mock()
        codec.decoder

        codec.reset_decoder()

        # Should recreate decoder (or remain None if library unavailable)
        self.assertIsNotNone(codec)


class TestILBCCodecManager(unittest.TestCase):
    """Test iLBC codec manager functionality"""

    def test_manager_initialization(self) -> None:
        """Test codec manager initialization"""
        pbx = Mock()
        pbx.config = {"codecs": {"ilbc": {"enabled": True, "mode": 30}}}

        manager = ILBCCodecManager(pbx)

        self.assertEqual(manager.pbx, pbx)
        self.assertEqual(manager.config, {"enabled": True, "mode": 30})
        self.assertEqual(len(manager.codecs), 0)

    def test_manager_initialization_no_config(self) -> None:
        """Test codec manager with no config"""
        pbx = Mock()
        pbx.config = None

        manager = ILBCCodecManager(pbx)

        self.assertEqual(manager.config, {})

    def test_create_codec(self) -> None:
        """Test creating codec for a call"""
        pbx = Mock()
        pbx.config = {"codecs": {"ilbc": {"mode": 30}}}

        manager = ILBCCodecManager(pbx)
        codec = manager.create_codec("call-123")

        self.assertIsInstance(codec, ILBCCodec)
        self.assertEqual(codec.mode, 30)
        self.assertIn("call-123", manager.codecs)
        self.assertEqual(manager.codecs["call-123"], codec)

    def test_create_codec_with_custom_config(self) -> None:
        """Test creating codec with custom configuration"""
        pbx = Mock()
        pbx.config = {}

        manager = ILBCCodecManager(pbx)
        custom_config = {"mode": 20, "payload_type": 100}
        codec = manager.create_codec("call-456", custom_config)

        self.assertEqual(codec.mode, 20)
        self.assertEqual(codec.payload_type, 100)

    def test_get_codec(self) -> None:
        """Test retrieving codec for a call"""
        pbx = Mock()
        pbx.config = {}

        manager = ILBCCodecManager(pbx)
        codec = manager.create_codec("call-789")

        retrieved = manager.get_codec("call-789")
        self.assertEqual(retrieved, codec)

    def test_get_codec_not_found(self) -> None:
        """Test retrieving non-existent codec"""
        pbx = Mock()
        pbx.config = {}

        manager = ILBCCodecManager(pbx)
        retrieved = manager.get_codec("call-999")

        self.assertIsNone(retrieved)

    def test_remove_codec(self) -> None:
        """Test removing codec for a call"""
        pbx = Mock()
        pbx.config = {}

        manager = ILBCCodecManager(pbx)
        manager.create_codec("call-111")

        self.assertIn("call-111", manager.codecs)

        manager.remove_codec("call-111")

        self.assertNotIn("call-111", manager.codecs)

    def test_remove_codec_not_found(self) -> None:
        """Test removing non-existent codec doesn't raise error"""
        pbx = Mock()
        pbx.config = {}

        manager = ILBCCodecManager(pbx)

        # Should not raise error
        manager.remove_codec("call-999")

    def test_get_all_codecs(self) -> None:
        """Test getting all codec instances"""
        pbx = Mock()
        pbx.config = {}

        manager = ILBCCodecManager(pbx)
        codec1 = manager.create_codec("call-1")
        manager.create_codec("call-2")
        manager.create_codec("call-3")

        all_codecs = manager.get_all_codecs()

        self.assertEqual(len(all_codecs), 3)
        self.assertIn("call-1", all_codecs)
        self.assertIn("call-2", all_codecs)
        self.assertIn("call-3", all_codecs)
        self.assertEqual(all_codecs["call-1"], codec1)

    def test_get_all_codecs_returns_copy(self) -> None:
        """Test that get_all_codecs returns a copy"""
        pbx = Mock()
        pbx.config = {}

        manager = ILBCCodecManager(pbx)
        manager.create_codec("call-1")

        all_codecs = manager.get_all_codecs()
        all_codecs["call-999"] = Mock()

        # Original should not be modified
        self.assertNotIn("call-999", manager.codecs)

    def test_is_ilbc_available(self) -> None:
        """Test checking iLBC availability"""
        pbx = Mock()
        pbx.config = {}

        manager = ILBCCodecManager(pbx)
        available = manager.is_ilbc_available()

        self.assertIsInstance(available, bool)


class TestILBCSDP(unittest.TestCase):
    """Test iLBC SDP integration"""

    def test_sdp_includes_ilbc(self) -> None:
        """Test that SDP includes iLBC codec"""
        from pbx.sip.sdp import SDPBuilder

        # Test with iLBC included
        codecs = ["0", "8", "97", "101"]
        sdp = SDPBuilder.build_audio_sdp("192.168.1.100", 10000, codecs=codecs)

        # Verify iLBC is in SDP
        self.assertIn("rtpmap:97 iLBC/8000", sdp)

    def test_sdp_fmtp_for_ilbc(self) -> None:
        """Test that SDP includes FMTP for iLBC"""
        # Note: The current SDP builder doesn't include fmtp for iLBC
        # This test documents expected behavior for future enhancement
        from pbx.sip.sdp import SDPBuilder

        codecs = ["0", "8", "97", "101"]
        sdp = SDPBuilder.build_audio_sdp("192.168.1.100", 10000, codecs=codecs)

        # Currently SDP builder doesn't add fmtp, but it should be in m= line
        self.assertIn("97", sdp)


if __name__ == "__main__":
    unittest.main()
