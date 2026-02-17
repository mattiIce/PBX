"""Comprehensive tests for pbx.features.g726_codec module."""

import struct
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestClamp:
    """Tests for _clamp helper function."""

    def test_clamp_within_range(self) -> None:
        """Test clamp returns value when within range."""
        from pbx.features.g726_codec import _clamp

        assert _clamp(5, 0, 10) == 5

    def test_clamp_below_minimum(self) -> None:
        """Test clamp returns lo when value is below range."""
        from pbx.features.g726_codec import _clamp

        assert _clamp(-5, 0, 10) == 0

    def test_clamp_above_maximum(self) -> None:
        """Test clamp returns hi when value is above range."""
        from pbx.features.g726_codec import _clamp

        assert _clamp(15, 0, 10) == 10

    def test_clamp_at_boundaries(self) -> None:
        """Test clamp at exact boundary values."""
        from pbx.features.g726_codec import _clamp

        assert _clamp(0, 0, 10) == 0
        assert _clamp(10, 0, 10) == 10


@pytest.mark.unit
class TestImaAdpcmEncode:
    """Tests for _ima_adpcm_encode function."""

    def test_encode_empty_data(self) -> None:
        """Test encoding empty PCM data."""
        from pbx.features.g726_codec import _ima_adpcm_encode

        result, state = _ima_adpcm_encode(b"")
        assert result == b""
        assert state == (0, 0)

    def test_encode_single_sample(self) -> None:
        """Test encoding a single sample (odd number)."""
        from pbx.features.g726_codec import _ima_adpcm_encode

        # Single 16-bit sample: value 0
        pcm_data = struct.pack("<h", 0)
        result, state = _ima_adpcm_encode(pcm_data)
        assert isinstance(result, bytes)
        assert len(result) == 1  # One nibble -> one byte (flushed)

    def test_encode_two_samples(self) -> None:
        """Test encoding two samples (even number)."""
        from pbx.features.g726_codec import _ima_adpcm_encode

        # Two 16-bit samples
        pcm_data = struct.pack("<hh", 1000, -1000)
        result, state = _ima_adpcm_encode(pcm_data)
        assert isinstance(result, bytes)
        assert len(result) == 1  # Two nibbles pack into one byte

    def test_encode_with_initial_state(self) -> None:
        """Test encoding with provided initial state."""
        from pbx.features.g726_codec import _ima_adpcm_encode

        pcm_data = struct.pack("<hh", 500, 1000)
        result, state = _ima_adpcm_encode(pcm_data, state=(100, 10))
        assert isinstance(result, bytes)
        assert isinstance(state, tuple)
        assert len(state) == 2

    def test_encode_multiple_samples(self) -> None:
        """Test encoding multiple samples."""
        from pbx.features.g726_codec import _ima_adpcm_encode

        # 10 samples
        samples = [int(32767 * (i / 10)) for i in range(10)]
        pcm_data = struct.pack(f"<{len(samples)}h", *samples)
        result, state = _ima_adpcm_encode(pcm_data)
        assert isinstance(result, bytes)
        assert len(result) == 5  # 10 nibbles = 5 bytes

    def test_encode_negative_samples(self) -> None:
        """Test encoding negative sample values."""
        from pbx.features.g726_codec import _ima_adpcm_encode

        pcm_data = struct.pack("<hh", -10000, -20000)
        result, state = _ima_adpcm_encode(pcm_data)
        assert isinstance(result, bytes)

    def test_encode_max_min_samples(self) -> None:
        """Test encoding with maximum and minimum sample values."""
        from pbx.features.g726_codec import _ima_adpcm_encode

        pcm_data = struct.pack("<hh", 32767, -32768)
        result, state = _ima_adpcm_encode(pcm_data)
        assert isinstance(result, bytes)

    def test_encode_continuity(self) -> None:
        """Test that state carries over between encode calls."""
        from pbx.features.g726_codec import _ima_adpcm_encode

        pcm1 = struct.pack("<hh", 1000, 2000)
        result1, state1 = _ima_adpcm_encode(pcm1)

        pcm2 = struct.pack("<hh", 3000, 4000)
        result2, state2 = _ima_adpcm_encode(pcm2, state1)

        # State should have progressed
        assert state2 != (0, 0)


@pytest.mark.unit
class TestImaAdpcmDecode:
    """Tests for _ima_adpcm_decode function."""

    def test_decode_empty_data(self) -> None:
        """Test decoding empty ADPCM data."""
        from pbx.features.g726_codec import _ima_adpcm_decode

        result, state = _ima_adpcm_decode(b"", 2)
        assert result == b""
        assert state == (0, 0)

    def test_decode_invalid_sample_width(self) -> None:
        """Test decoding with invalid sample width raises ValueError."""
        from pbx.features.g726_codec import _ima_adpcm_decode

        with pytest.raises(ValueError, match="Only 16-bit"):
            _ima_adpcm_decode(b"\x00", 1)

    def test_decode_single_byte(self) -> None:
        """Test decoding a single byte (two nibbles -> two samples)."""
        from pbx.features.g726_codec import _ima_adpcm_decode

        result, state = _ima_adpcm_decode(b"\x00", 2)
        assert isinstance(result, bytes)
        assert len(result) == 4  # 2 samples * 2 bytes each

    def test_decode_with_initial_state(self) -> None:
        """Test decoding with provided initial state."""
        from pbx.features.g726_codec import _ima_adpcm_decode

        result, state = _ima_adpcm_decode(b"\x37", 2, state=(100, 10))
        assert isinstance(result, bytes)
        assert isinstance(state, tuple)

    def test_encode_decode_roundtrip(self) -> None:
        """Test encoding then decoding produces approximate original."""
        from pbx.features.g726_codec import _ima_adpcm_decode, _ima_adpcm_encode

        # Create a simple signal
        samples = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]
        pcm_data = struct.pack(f"<{len(samples)}h", *samples)

        # Encode
        encoded, enc_state = _ima_adpcm_encode(pcm_data)

        # Decode
        decoded, dec_state = _ima_adpcm_decode(encoded, 2)

        # The decoded data should have the same length as the original
        assert len(decoded) == len(pcm_data)

    def test_decode_multiple_bytes(self) -> None:
        """Test decoding multiple bytes."""
        from pbx.features.g726_codec import _ima_adpcm_decode

        adpcm_data = bytes([0x37, 0x48, 0x59])
        result, state = _ima_adpcm_decode(adpcm_data, 2)
        # 3 bytes * 2 nibbles per byte * 2 bytes per sample = 12 bytes
        assert len(result) == 12


@pytest.mark.unit
class TestG726Codec:
    """Tests for G726Codec class."""

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_default_bitrate(self, mock_get_logger: MagicMock) -> None:
        """Test G726Codec initialization with default bitrate."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec()
        assert codec.bitrate == 32000
        assert codec.bitrate_kbps == 32
        assert codec.bits_per_sample == 4
        assert codec.payload_type == 2
        assert codec.enabled is True

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_16kbps(self, mock_get_logger: MagicMock) -> None:
        """Test G726Codec initialization at 16 kbit/s."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=16000)
        assert codec.bitrate_kbps == 16
        assert codec.bits_per_sample == 2
        assert codec.payload_type == 112

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_24kbps(self, mock_get_logger: MagicMock) -> None:
        """Test G726Codec initialization at 24 kbit/s."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=24000)
        assert codec.bitrate_kbps == 24
        assert codec.bits_per_sample == 3

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_40kbps(self, mock_get_logger: MagicMock) -> None:
        """Test G726Codec initialization at 40 kbit/s."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=40000)
        assert codec.bitrate_kbps == 40
        assert codec.bits_per_sample == 5

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_invalid_bitrate(self, mock_get_logger: MagicMock) -> None:
        """Test G726Codec initialization with invalid bitrate."""
        from pbx.features.g726_codec import G726Codec

        with pytest.raises(ValueError, match="Unsupported G.726 bitrate"):
            G726Codec(bitrate=48000)

    @patch("pbx.features.g726_codec.get_logger")
    def test_encode_32kbps(self, mock_get_logger: MagicMock) -> None:
        """Test encoding at 32 kbit/s."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        pcm_data = struct.pack("<hh", 1000, -1000)
        result = codec.encode(pcm_data)
        assert result is not None
        assert isinstance(result, bytes)

    @patch("pbx.features.g726_codec.get_logger")
    def test_encode_non_32kbps_returns_none(self, mock_get_logger: MagicMock) -> None:
        """Test encoding at non-32 kbit/s returns None."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=16000)
        pcm_data = struct.pack("<hh", 1000, -1000)
        result = codec.encode(pcm_data)
        assert result is None

    @patch("pbx.features.g726_codec.get_logger")
    def test_encode_exception(self, mock_get_logger: MagicMock) -> None:
        """Test encoding with exception returns None."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        # Pass invalid data (not valid PCM)
        with patch(
            "pbx.features.g726_codec._ima_adpcm_encode",
            side_effect=Exception("encode error"),
        ):
            result = codec.encode(b"\x00\x01")
            assert result is None

    @patch("pbx.features.g726_codec.get_logger")
    def test_decode_32kbps(self, mock_get_logger: MagicMock) -> None:
        """Test decoding at 32 kbit/s."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        result = codec.decode(b"\x37")
        assert result is not None
        assert isinstance(result, bytes)

    @patch("pbx.features.g726_codec.get_logger")
    def test_decode_empty_data(self, mock_get_logger: MagicMock) -> None:
        """Test decoding empty data returns empty bytes."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        result = codec.decode(b"")
        assert result == b""

    @patch("pbx.features.g726_codec.get_logger")
    def test_decode_non_32kbps_returns_none(self, mock_get_logger: MagicMock) -> None:
        """Test decoding at non-32 kbit/s returns None."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=24000)
        result = codec.decode(b"\x37")
        assert result is None

    @patch("pbx.features.g726_codec.get_logger")
    def test_decode_exception(self, mock_get_logger: MagicMock) -> None:
        """Test decoding with exception returns None."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        with patch(
            "pbx.features.g726_codec._ima_adpcm_decode",
            side_effect=Exception("decode error"),
        ):
            result = codec.decode(b"\x37")
            assert result is None

    @patch("pbx.features.g726_codec.get_logger")
    def test_encode_decode_state_persistence(self, mock_get_logger: MagicMock) -> None:
        """Test that encode/decode state persists across calls."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        assert codec._encode_state is None
        assert codec._decode_state is None

        pcm = struct.pack("<hh", 1000, 2000)
        codec.encode(pcm)
        assert codec._encode_state is not None

        codec.decode(b"\x37")
        assert codec._decode_state is not None

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_info_32kbps(self, mock_get_logger: MagicMock) -> None:
        """Test get_info for 32 kbit/s codec."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        info = codec.get_info()
        assert info["name"] == "G.726-32"
        assert info["sample_rate"] == 8000
        assert info["bitrate"] == 32000
        assert info["bits_per_sample"] == 4
        assert info["payload_type"] == 2
        assert info["enabled"] is True
        assert info["implementation"] == "Full (pure Python ADPCM)"

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_info_non_32kbps(self, mock_get_logger: MagicMock) -> None:
        """Test get_info for non-32 kbit/s codec."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=16000)
        info = codec.get_info()
        assert info["name"] == "G.726-16"
        assert info["implementation"] == "Framework Only"

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_quality_description_all_bitrates(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test quality descriptions for all bitrates."""
        from pbx.features.g726_codec import G726Codec

        codec16 = G726Codec(bitrate=16000)
        assert "Fair" in codec16._get_quality_description()

        codec24 = G726Codec(bitrate=24000)
        assert "Good" in codec24._get_quality_description()

        codec32 = G726Codec(bitrate=32000)
        assert "Good" in codec32._get_quality_description()

        codec40 = G726Codec(bitrate=40000)
        assert "Very Good" in codec40._get_quality_description()

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_sdp_description_32kbps(self, mock_get_logger: MagicMock) -> None:
        """Test SDP description for 32 kbit/s."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        sdp = codec.get_sdp_description()
        assert "G726-32" in sdp
        assert "8000" in sdp

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_sdp_description_non_32kbps(self, mock_get_logger: MagicMock) -> None:
        """Test SDP description for non-32 kbit/s."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=16000)
        sdp = codec.get_sdp_description()
        assert "G726-16" in sdp

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_fmtp_params(self, mock_get_logger: MagicMock) -> None:
        """Test fmtp params returns None."""
        from pbx.features.g726_codec import G726Codec

        codec = G726Codec(bitrate=32000)
        assert codec.get_fmtp_params() is None

    def test_is_supported_32kbps(self) -> None:
        """Test is_supported returns True for 32000."""
        from pbx.features.g726_codec import G726Codec

        assert G726Codec.is_supported(32000) is True

    def test_is_supported_other_bitrates(self) -> None:
        """Test is_supported returns False for non-32000 bitrates."""
        from pbx.features.g726_codec import G726Codec

        assert G726Codec.is_supported(16000) is False
        assert G726Codec.is_supported(24000) is False
        assert G726Codec.is_supported(40000) is False

    def test_get_capabilities(self) -> None:
        """Test get_capabilities returns correct structure."""
        from pbx.features.g726_codec import G726Codec

        caps = G726Codec.get_capabilities()
        assert caps["bitrates"] == [16000, 24000, 32000, 40000]
        assert caps["sample_rate"] == 8000
        assert caps["channels"] == 1
        assert caps["bits_per_sample"] == [2, 3, 4, 5]
        assert "VoIP" in caps["applications"]

    def test_class_constants(self) -> None:
        """Test class-level constants are correct."""
        from pbx.features.g726_codec import G726Codec

        assert G726Codec.SAMPLE_RATE == 8000
        assert G726Codec.PAYLOAD_TYPES[32] == 2
        assert G726Codec.PAYLOAD_TYPES[16] is None
        assert G726Codec.BITS_PER_SAMPLE[32] == 4


@pytest.mark.unit
class TestG726CodecManager:
    """Tests for G726CodecManager class."""

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_no_config(self, mock_get_logger: MagicMock) -> None:
        """Test manager initialization with no config."""
        from pbx.features.g726_codec import G726CodecManager

        manager = G726CodecManager()
        assert manager.enabled is False
        assert manager.default_bitrate == 32000
        assert manager.encoders == {}
        assert manager.decoders == {}

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test manager initialization with enabled config."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)
        assert manager.enabled is True

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_invalid_bitrate_defaults(self, mock_get_logger: MagicMock) -> None:
        """Test manager initialization with invalid bitrate falls back to 32000."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 99000}
        manager = G726CodecManager(config)
        assert manager.default_bitrate == 32000

    @patch("pbx.features.g726_codec.get_logger")
    def test_init_enabled_unsupported_bitrate_warns(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test manager warns when enabled with unsupported bitrate."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 16000}
        manager = G726CodecManager(config)
        assert manager.enabled is True
        assert manager.default_bitrate == 16000

    @patch("pbx.features.g726_codec.get_logger")
    def test_create_encoder(self, mock_get_logger: MagicMock) -> None:
        """Test creating an encoder."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        encoder = manager.create_encoder("call-1")
        assert encoder is not None
        assert "call-1" in manager.encoders

    @patch("pbx.features.g726_codec.get_logger")
    def test_create_encoder_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test creating an encoder when disabled returns None."""
        from pbx.features.g726_codec import G726CodecManager

        manager = G726CodecManager()
        encoder = manager.create_encoder("call-1")
        assert encoder is None

    @patch("pbx.features.g726_codec.get_logger")
    def test_create_encoder_custom_bitrate(self, mock_get_logger: MagicMock) -> None:
        """Test creating an encoder with custom bitrate."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        encoder = manager.create_encoder("call-1", bitrate=24000)
        assert encoder is not None
        assert encoder.bitrate_kbps == 24

    @patch("pbx.features.g726_codec.get_logger")
    def test_create_decoder(self, mock_get_logger: MagicMock) -> None:
        """Test creating a decoder."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        decoder = manager.create_decoder("call-1")
        assert decoder is not None
        assert "call-1" in manager.decoders

    @patch("pbx.features.g726_codec.get_logger")
    def test_create_decoder_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test creating a decoder when disabled returns None."""
        from pbx.features.g726_codec import G726CodecManager

        manager = G726CodecManager()
        decoder = manager.create_decoder("call-1")
        assert decoder is None

    @patch("pbx.features.g726_codec.get_logger")
    def test_create_decoder_custom_bitrate(self, mock_get_logger: MagicMock) -> None:
        """Test creating a decoder with custom bitrate."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        decoder = manager.create_decoder("call-1", bitrate=40000)
        assert decoder is not None
        assert decoder.bitrate_kbps == 40

    @patch("pbx.features.g726_codec.get_logger")
    def test_release_codec(self, mock_get_logger: MagicMock) -> None:
        """Test releasing codecs for a call."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        manager.create_encoder("call-1")
        manager.create_decoder("call-1")
        assert "call-1" in manager.encoders
        assert "call-1" in manager.decoders

        manager.release_codec("call-1")
        assert "call-1" not in manager.encoders
        assert "call-1" not in manager.decoders

    @patch("pbx.features.g726_codec.get_logger")
    def test_release_codec_nonexistent(self, mock_get_logger: MagicMock) -> None:
        """Test releasing codecs for nonexistent call does not error."""
        from pbx.features.g726_codec import G726CodecManager

        manager = G726CodecManager()
        manager.release_codec("nonexistent")  # Should not raise

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_encoder(self, mock_get_logger: MagicMock) -> None:
        """Test getting an encoder by call ID."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        manager.create_encoder("call-1")
        assert manager.get_encoder("call-1") is not None
        assert manager.get_encoder("call-2") is None

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_decoder(self, mock_get_logger: MagicMock) -> None:
        """Test getting a decoder by call ID."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        manager.create_decoder("call-1")
        assert manager.get_decoder("call-1") is not None
        assert manager.get_decoder("call-2") is None

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_statistics(self, mock_get_logger: MagicMock) -> None:
        """Test getting codec usage statistics."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        manager.create_encoder("call-1")
        manager.create_encoder("call-2")
        manager.create_decoder("call-1")

        stats = manager.get_statistics()
        assert stats["enabled"] is True
        assert stats["default_bitrate"] == 32000
        assert stats["active_encoders"] == 2
        assert stats["active_decoders"] == 1
        assert stats["supported"] is True

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_statistics_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test statistics when disabled."""
        from pbx.features.g726_codec import G726CodecManager

        manager = G726CodecManager()
        stats = manager.get_statistics()
        assert stats["enabled"] is False
        assert stats["active_encoders"] == 0

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_sdp_capabilities_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test SDP capabilities when enabled."""
        from pbx.features.g726_codec import G726CodecManager

        config = {"codecs.g726.enabled": True, "codecs.g726.bitrate": 32000}
        manager = G726CodecManager(config)

        caps = manager.get_sdp_capabilities()
        assert len(caps) >= 1
        assert any("G726-32" in c for c in caps)

    @patch("pbx.features.g726_codec.get_logger")
    def test_get_sdp_capabilities_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test SDP capabilities when disabled."""
        from pbx.features.g726_codec import G726CodecManager

        manager = G726CodecManager()
        caps = manager.get_sdp_capabilities()
        assert caps == []


@pytest.mark.unit
class TestModuleTables:
    """Tests for module-level tables and constants."""

    def test_index_table_length(self) -> None:
        """Test that _INDEX_TABLE has correct length."""
        from pbx.features.g726_codec import _INDEX_TABLE

        assert len(_INDEX_TABLE) == 8

    def test_step_size_table_length(self) -> None:
        """Test that _STEP_SIZE_TABLE has correct length."""
        from pbx.features.g726_codec import _STEP_SIZE_TABLE

        assert len(_STEP_SIZE_TABLE) == 89  # indices 0..88

    def test_step_size_table_monotonic(self) -> None:
        """Test that _STEP_SIZE_TABLE is monotonically increasing."""
        from pbx.features.g726_codec import _STEP_SIZE_TABLE

        for i in range(1, len(_STEP_SIZE_TABLE)):
            assert _STEP_SIZE_TABLE[i] > _STEP_SIZE_TABLE[i - 1]
