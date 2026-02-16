"""
Tests for G.722 HD Audio Codec
"""

import struct

from pbx.features.g722_codec import G722Codec, G722CodecManager


class TestG722Codec:
    """Test G.722 codec functionality"""

    def test_codec_initialization(self) -> None:
        """Test codec initialization"""
        codec = G722Codec()

        assert codec is not None
        assert codec.SAMPLE_RATE == 16000
        assert codec.PAYLOAD_TYPE == 9

    def test_codec_info(self) -> None:
        """Test codec information"""
        codec = G722Codec(bitrate=G722Codec.MODE_64K)
        info = codec.get_info()

        assert info["name"] == "G.722"
        assert info["sample_rate"] == 16000
        assert info["bitrate"] == 64000
        assert info["payload_type"] == 9

    def test_encode_stub(self) -> None:
        """Test encoding"""
        codec = G722Codec()

        # Create fake PCM data (16-bit, 16kHz, 20ms = 320 samples = 640 bytes)
        pcm_data = b"\x00" * 640

        encoded = codec.encode(pcm_data)

        assert encoded is not None
        # G.722 encodes 2 samples (4 bytes) into 1 byte, so 640 bytes -> 160
        # bytes
        assert len(encoded) == len(pcm_data) // 4

    def test_decode_stub(self) -> None:
        """Test decoding"""
        codec = G722Codec()

        # Create fake G.722 data
        g722_data = b"\x00" * 320

        decoded = codec.decode(g722_data)

        assert decoded is not None
        # Each G.722 byte decodes to 2 samples (4 bytes), so 320 bytes -> 1280
        # bytes
        assert len(decoded) == len(g722_data) * 4

    def test_sdp_description(self) -> None:
        """Test SDP description generation"""
        codec = G722Codec()
        sdp = codec.get_sdp_description()

        assert "G722" in sdp
        assert "16000" in sdp
        assert "9" in sdp

    def test_is_supported(self) -> None:
        """Test codec support check"""
        supported = G722Codec.is_supported()
        assert supported

    def test_capabilities(self) -> None:
        """Test codec capabilities"""
        caps = G722Codec.get_capabilities()

        assert "bitrates" in caps
        assert "sample_rate" in caps
        assert caps["sample_rate"] == 16000
        assert 64000 in caps["bitrates"]
        assert 56000 in caps["bitrates"]
        assert 48000 in caps["bitrates"]

    def test_different_bitrates(self) -> None:
        """Test different bitrate modes"""
        codec_64k = G722Codec(bitrate=G722Codec.MODE_64K)
        codec_56k = G722Codec(bitrate=G722Codec.MODE_56K)
        codec_48k = G722Codec(bitrate=G722Codec.MODE_48K)

        assert codec_64k.bitrate == 64000
        assert codec_56k.bitrate == 56000
        assert codec_48k.bitrate == 48000

    def test_encode_decode_roundtrip(self) -> None:
        """Test that encode/decode roundtrip preserves data shape"""
        codec = G722Codec()

        # Create test PCM data with some pattern (sine-like)
        pcm_data = bytearray()
        for i in range(320):  # 320 samples = 640 bytes
            # Create a simple pattern
            value = int((i % 100) * 327 - 16384)
            pcm_data.extend(struct.pack("<h", value))
        pcm_data = bytes(pcm_data)

        # Encode
        encoded = codec.encode(pcm_data)
        assert encoded is not None
        assert len(encoded) == 160  # 640 bytes / 4 = 160 bytes

        # Decode
        decoded = codec.decode(encoded)
        assert decoded is not None
        # 160 bytes * 4 = 640 bytes (same as input)
        assert len(decoded) == 640
        # Verify we can decode what we encoded (sizes should match pattern)
        # Note: Due to quantization, values won't be identical but shape should
        # be preserved


class TestG722CodecManager:
    """Test G.722 codec manager"""

    def test_manager_initialization(self) -> None:
        """Test manager initialization"""
        manager = G722CodecManager()

        assert manager is not None
        assert manager.enabled

    def test_create_encoder(self) -> None:
        """Test encoder creation"""
        manager = G722CodecManager()

        encoder = manager.create_encoder("call-001")

        assert encoder is not None
        assert "call-001" in manager.encoders

    def test_create_decoder(self) -> None:
        """Test decoder creation"""
        manager = G722CodecManager()

        decoder = manager.create_decoder("call-001")

        assert decoder is not None
        assert "call-001" in manager.decoders

    def test_release_codec(self) -> None:
        """Test codec release"""
        manager = G722CodecManager()

        manager.create_encoder("call-001")
        manager.create_decoder("call-001")

        assert len(manager.encoders) == 1
        assert len(manager.decoders) == 1
        manager.release_codec("call-001")

        assert len(manager.encoders) == 0
        assert len(manager.decoders) == 0

    def test_get_statistics(self) -> None:
        """Test statistics retrieval"""
        manager = G722CodecManager()

        manager.create_encoder("call-001")
        manager.create_encoder("call-002")
        manager.create_decoder("call-001")

        stats = manager.get_statistics()

        assert stats["active_encoders"] == 2
        assert stats["active_decoders"] == 1
        assert stats["enabled"]

    def test_sdp_capabilities(self) -> None:
        """Test SDP capabilities"""
        manager = G722CodecManager()

        caps = manager.get_sdp_capabilities()

        assert isinstance(caps, list)
        assert len(caps) > 0

    def test_disabled_manager(self) -> None:
        """Test manager when disabled"""
        config = {"codecs.g722.enabled": False}
        manager = G722CodecManager(config)

        assert not manager.enabled
        encoder = manager.create_encoder("call-001")
        assert encoder is None

    def test_custom_bitrate(self) -> None:
        """Test custom bitrate configuration"""
        config = {"codecs.g722.bitrate": G722Codec.MODE_48K}
        manager = G722CodecManager(config)

        assert manager.default_bitrate == 48000
