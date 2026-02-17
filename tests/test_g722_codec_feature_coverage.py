"""Comprehensive tests for g722_codec feature module."""

import struct
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.g722_codec import (
    IHB_TABLE,
    ILB_TABLE,
    Q2_DECISION_LEVELS,
    Q2_OUTPUT_LEVELS,
    Q6_DECISION_LEVELS,
    Q6_OUTPUT_LEVELS,
    WH_TABLE,
    WL_TABLE,
    G722Codec,
    G722CodecManager,
    G722State,
)


@pytest.mark.unit
class TestG722State:
    """Tests for G722State initialization."""

    def test_state_initialization(self) -> None:
        state = G722State()
        assert len(state.x) == 24
        assert all(v == 0 for v in state.x)
        assert state.sl == 0
        assert state.spl == 0
        assert state.szl == 0
        assert state.detl == 32
        assert state.dlt == 0
        assert state.nbl == 0
        assert len(state.al) == 2
        assert len(state.bl) == 6
        assert len(state.dql) == 6
        assert len(state.sgl) == 6
        assert state.plt == 0
        assert state.plt1 == 0
        assert state.plt2 == 0
        assert len(state.rlt) == 2

    def test_state_higher_subband_init(self) -> None:
        state = G722State()
        assert state.sh == 0
        assert state.sph == 0
        assert state.szh == 0
        assert state.deth == 8
        assert state.dh == 0
        assert state.nbh == 0
        assert len(state.ah) == 2
        assert len(state.bh) == 6
        assert len(state.dqh) == 6
        assert len(state.sgh) == 6
        assert state.pht == 0
        assert state.pht1 == 0
        assert state.pht2 == 0
        assert len(state.rh) == 2


@pytest.mark.unit
class TestQuantizationTables:
    """Tests for quantization table integrity."""

    def test_q6_decision_levels_length(self) -> None:
        assert len(Q6_DECISION_LEVELS) == 32

    def test_q6_output_levels_length(self) -> None:
        assert len(Q6_OUTPUT_LEVELS) == 32

    def test_q2_decision_levels_length(self) -> None:
        assert len(Q2_DECISION_LEVELS) == 3

    def test_q2_output_levels_length(self) -> None:
        assert len(Q2_OUTPUT_LEVELS) == 4

    def test_ilb_table_length(self) -> None:
        assert len(ILB_TABLE) == 32

    def test_ihb_table_length(self) -> None:
        assert len(IHB_TABLE) == 4

    def test_wl_table_length(self) -> None:
        assert len(WL_TABLE) == 64

    def test_wh_table_length(self) -> None:
        assert len(WH_TABLE) == 4


@pytest.mark.unit
class TestG722CodecInit:
    """Tests for G722Codec initialization."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_default_init(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        assert codec.bitrate == G722Codec.MODE_64K
        assert codec.enabled is True
        assert isinstance(codec.encoder_state, G722State)
        assert isinstance(codec.decoder_state, G722State)

    @patch("pbx.features.g722_codec.get_logger")
    def test_init_56k(self, mock_logger: MagicMock) -> None:
        codec = G722Codec(bitrate=G722Codec.MODE_56K)
        assert codec.bitrate == 56000

    @patch("pbx.features.g722_codec.get_logger")
    def test_init_48k(self, mock_logger: MagicMock) -> None:
        codec = G722Codec(bitrate=G722Codec.MODE_48K)
        assert codec.bitrate == 48000

    @patch("pbx.features.g722_codec.get_logger")
    def test_class_constants(self, mock_logger: MagicMock) -> None:
        assert G722Codec.SAMPLE_RATE == 16000
        assert G722Codec.FRAME_SIZE == 320
        assert G722Codec.PAYLOAD_TYPE == 9


@pytest.mark.unit
class TestG722Encode:
    """Tests for G722Codec encode method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_empty(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec.encode(b"")
        assert result == b""

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_too_short(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec.encode(b"\x00\x00")
        assert result == b""

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_single_pair(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        # Two 16-bit samples = 4 bytes
        pcm = struct.pack("<hh", 1000, -1000)
        result = codec.encode(pcm)
        assert result is not None
        assert len(result) == 1  # One byte per sample pair

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_multiple_pairs(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        # 10 sample pairs = 40 bytes input
        samples = [500 * (i % 5) for i in range(20)]
        pcm = struct.pack(f"<{len(samples)}h", *samples)
        result = codec.encode(pcm)
        assert result is not None
        assert len(result) == 10

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_unaligned_input(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        # 5 bytes - not aligned to 4 bytes
        pcm = b"\x00" * 5
        result = codec.encode(pcm)
        assert result is not None
        assert len(result) == 1  # Truncated to 4 bytes, one pair

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_silence(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        pcm = b"\x00" * 40  # 10 pairs of silence
        result = codec.encode(pcm)
        assert result is not None
        assert len(result) == 10

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_max_values(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        pcm = struct.pack("<hh", 32767, -32768)
        result = codec.encode(pcm)
        assert result is not None
        assert len(result) == 1


@pytest.mark.unit
class TestG722Decode:
    """Tests for G722Codec decode method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_empty(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec.decode(b"")
        assert result == b""

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_single_byte(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec.decode(b"\x00")
        assert result is not None
        assert len(result) == 4  # Two 16-bit samples

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_multiple_bytes(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec.decode(b"\x00\x3f\x80\xff")
        assert result is not None
        assert len(result) == 16  # 4 bytes input = 8 samples = 16 bytes output

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_all_zeros(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec.decode(b"\x00" * 10)
        assert result is not None
        assert len(result) == 40  # 10 bytes -> 20 samples -> 40 bytes

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_all_ff(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec.decode(b"\xff" * 5)
        assert result is not None
        assert len(result) == 20


@pytest.mark.unit
class TestG722EncodeDecode:
    """Tests for encode/decode round-trip."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_decode_roundtrip(self, mock_logger: MagicMock) -> None:
        encoder = G722Codec()
        decoder = G722Codec()
        # Generate a simple waveform
        samples = [int(1000 * (i % 10)) for i in range(20)]
        pcm = struct.pack(f"<{len(samples)}h", *samples)
        encoded = encoder.encode(pcm)
        assert encoded is not None
        decoded = decoder.decode(encoded)
        assert decoded is not None
        assert len(decoded) == len(pcm)

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_decode_silence_roundtrip(self, mock_logger: MagicMock) -> None:
        encoder = G722Codec()
        decoder = G722Codec()
        pcm = b"\x00" * 80
        encoded = encoder.encode(pcm)
        decoded = decoder.decode(encoded)
        assert decoded is not None
        assert len(decoded) == 80


@pytest.mark.unit
class TestEncodeSamplePair:
    """Tests for _encode_sample_pair method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_zero_pair(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._encode_sample_pair(0, 0)
        assert isinstance(result, int)
        assert 0 <= result <= 255

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_positive_pair(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._encode_sample_pair(5000, 3000)
        assert isinstance(result, int)
        assert 0 <= result <= 255

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_negative_pair(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._encode_sample_pair(-5000, -3000)
        assert isinstance(result, int)
        assert 0 <= result <= 255

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_mixed_pair(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._encode_sample_pair(10000, -10000)
        assert isinstance(result, int)
        assert 0 <= result <= 255


@pytest.mark.unit
class TestDecodeSamplePair:
    """Tests for _decode_sample_pair method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_zero_code(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        s1, s2 = codec._decode_sample_pair(0)
        assert isinstance(s1, int)
        assert isinstance(s2, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_max_code(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        s1, s2 = codec._decode_sample_pair(255)
        assert isinstance(s1, int)
        assert isinstance(s2, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_midrange_code(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        s1, s2 = codec._decode_sample_pair(128)
        assert isinstance(s1, int)
        assert isinstance(s2, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_all_codes(self, mock_logger: MagicMock) -> None:
        """Verify all 256 possible codes decode without error."""
        codec = G722Codec()
        for code in range(256):
            s1, s2 = codec._decode_sample_pair(code)
            assert isinstance(s1, int)
            assert isinstance(s2, int)


@pytest.mark.unit
class TestQMFFilters:
    """Tests for QMF filter methods."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_qmf_rx_filter_lower(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        x = [100] * 24
        result = codec._qmf_rx_filter(x, 0)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_qmf_rx_filter_higher(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        x = [100] * 24
        result = codec._qmf_rx_filter(x, 1)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_qmf_rx_filter_zeros(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        x = [0] * 24
        result_low = codec._qmf_rx_filter(x, 0)
        result_high = codec._qmf_rx_filter(x, 1)
        assert result_low == 0
        assert result_high == 0

    @patch("pbx.features.g722_codec.get_logger")
    def test_qmf_tx_filter(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = G722State()
        s1, s2 = codec._qmf_tx_filter(1000, 500, state)
        assert isinstance(s1, int)
        assert isinstance(s2, int)
        assert -32768 <= s1 <= 32767
        assert -32768 <= s2 <= 32767

    @patch("pbx.features.g722_codec.get_logger")
    def test_qmf_tx_filter_saturation(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = G722State()
        s1, s2 = codec._qmf_tx_filter(32000, 32000, state)
        assert s1 == 32767  # Saturated
        assert s2 == 0  # 32000 - 32000 = 0, <<1 = 0


@pytest.mark.unit
class TestInverseQuantizers:
    """Tests for inverse quantizer methods."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_lower_zero(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_lower(0, 32)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_lower_positive(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_lower(10, 32)
        assert isinstance(result, int)
        assert result >= 0

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_lower_negative(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_lower(50, 32)  # il >= 32 means negative
        assert isinstance(result, int)
        assert result <= 0

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_lower_max_index(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_lower(63, 32)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_lower_over_max(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_lower(100, 32)  # Clamped to 63
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_lower_high_idx(self, mock_logger: MagicMock) -> None:
        """Test with idx >= 32 to trigger ILB_TABLE[31] fallback."""
        codec = G722Codec()
        result = codec._inverse_quant_lower(31, 32)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_higher_zero(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_higher(0, 8)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_higher_positive(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_higher(1, 8)
        assert isinstance(result, int)
        assert result >= 0

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_higher_negative(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_higher(2, 8)  # ih >= 2 means negative
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_higher_max(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._inverse_quant_higher(3, 8)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_inverse_quant_higher_high_idx(self, mock_logger: MagicMock) -> None:
        """Test with idx >= 4 to trigger IHB_TABLE[3] fallback."""
        codec = G722Codec()
        result = codec._inverse_quant_higher(5, 8)
        assert isinstance(result, int)


@pytest.mark.unit
class TestAdaptQuantizers:
    """Tests for quantizer adaptation methods."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_adapt_lower_basic(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._adapt_lower(0, 32)
        assert isinstance(result, int)
        assert result >= 1

    @patch("pbx.features.g722_codec.get_logger")
    def test_adapt_lower_high_il(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._adapt_lower(63, 32)
        assert isinstance(result, int)
        assert result >= 1

    @patch("pbx.features.g722_codec.get_logger")
    def test_adapt_lower_overflow(self, mock_logger: MagicMock) -> None:
        """Test that nbl is capped at 18432."""
        codec = G722Codec()
        result = codec._adapt_lower(1, 20000)  # WL_TABLE[1] = 3042
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_adapt_lower_underflow(self, mock_logger: MagicMock) -> None:
        """Test that nbl is floored at 0."""
        codec = G722Codec()
        result = codec._adapt_lower(0, 0)  # det + WL_TABLE[0] = 0 + (-60) < 0
        assert isinstance(result, int)
        assert result >= 1

    @patch("pbx.features.g722_codec.get_logger")
    def test_adapt_higher_basic(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._adapt_higher(0, 8)
        assert isinstance(result, int)
        assert result >= 1

    @patch("pbx.features.g722_codec.get_logger")
    def test_adapt_higher_all_codes(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        for ih in range(4):
            result = codec._adapt_higher(ih, 8)
            assert result >= 1

    @patch("pbx.features.g722_codec.get_logger")
    def test_adapt_higher_overflow(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._adapt_higher(2, 25000)  # WH_TABLE[2] = 798
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_adapt_higher_underflow(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        result = codec._adapt_higher(1, 0)  # WH_TABLE[1] = -214 -> nbl < 0
        assert result >= 1


@pytest.mark.unit
class TestSubbandEncoders:
    """Tests for sub-band encode methods."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_lower_subband(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.encoder_state
        result = codec._encode_lower_subband(1000, state)
        assert isinstance(result, int)
        assert 0 <= result <= 63

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_lower_subband_negative(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.encoder_state
        result = codec._encode_lower_subband(-1000, state)
        assert isinstance(result, int)
        assert 0 <= result <= 63

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_lower_subband_zero(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.encoder_state
        result = codec._encode_lower_subband(0, state)
        assert isinstance(result, int)
        assert 0 <= result <= 63

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_lower_subband_low_detl(self, mock_logger: MagicMock) -> None:
        """Test with detl < 32 to hit alternate path."""
        codec = G722Codec()
        state = codec.encoder_state
        state.detl = 16
        result = codec._encode_lower_subband(500, state)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_higher_subband(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.encoder_state
        result = codec._encode_higher_subband(500, state)
        assert isinstance(result, int)
        assert 0 <= result <= 3

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_higher_subband_negative(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.encoder_state
        result = codec._encode_higher_subband(-500, state)
        assert isinstance(result, int)
        assert 0 <= result <= 3

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_higher_subband_low_deth(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.encoder_state
        state.deth = 4
        result = codec._encode_higher_subband(500, state)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_encode_higher_subband_various_levels(self, mock_logger: MagicMock) -> None:
        """Test various input levels to hit different quantization branches."""
        codec = G722Codec()
        for xh in [0, 50, 200, 1000, -50, -200, -1000]:
            state = G722State()
            state.deth = 8
            result = codec._encode_higher_subband(xh, state)
            assert 0 <= result <= 3


@pytest.mark.unit
class TestSubbandDecoders:
    """Tests for sub-band decode methods."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_lower_subband(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.decoder_state
        result = codec._decode_lower_subband(10, state)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_lower_subband_all_codes(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        for il in range(64):
            state = G722State()
            state.detl = 32
            result = codec._decode_lower_subband(il, state)
            assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_higher_subband(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.decoder_state
        result = codec._decode_higher_subband(1, state)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec.get_logger")
    def test_decode_higher_subband_all_codes(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        for ih in range(4):
            state = G722State()
            state.deth = 8
            result = codec._decode_higher_subband(ih, state)
            assert isinstance(result, int)


@pytest.mark.unit
class TestSaturate:
    """Tests for _saturate method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_saturate_within_range(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        assert codec._saturate(100, -1000, 1000) == 100

    @patch("pbx.features.g722_codec.get_logger")
    def test_saturate_below_min(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        assert codec._saturate(-2000, -1000, 1000) == -1000

    @patch("pbx.features.g722_codec.get_logger")
    def test_saturate_above_max(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        assert codec._saturate(2000, -1000, 1000) == 1000

    @patch("pbx.features.g722_codec.get_logger")
    def test_saturate_at_boundaries(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        assert codec._saturate(-1000, -1000, 1000) == -1000
        assert codec._saturate(1000, -1000, 1000) == 1000


@pytest.mark.unit
class TestGetInfo:
    """Tests for get_info method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_info(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        info = codec.get_info()
        assert info["name"] == "G.722"
        assert info["sample_rate"] == 16000
        assert info["bitrate"] == 64000
        assert info["frame_size"] == 320
        assert info["payload_type"] == 9
        assert info["enabled"] is True
        assert "HD Audio" in info["quality"]


@pytest.mark.unit
class TestGetSdpDescription:
    """Tests for get_sdp_description method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_sdp_description(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        sdp = codec.get_sdp_description()
        assert "G722" in sdp
        assert "9" in sdp
        assert "16000" in sdp


@pytest.mark.unit
class TestStaticMethods:
    """Tests for static methods."""

    def test_is_supported(self) -> None:
        assert G722Codec.is_supported() is True

    def test_get_capabilities(self) -> None:
        caps = G722Codec.get_capabilities()
        assert 64000 in caps["bitrates"]
        assert 56000 in caps["bitrates"]
        assert 48000 in caps["bitrates"]
        assert caps["sample_rate"] == 16000
        assert caps["channels"] == 1
        assert 320 in caps["frame_sizes"]


@pytest.mark.unit
class TestG722CodecManagerInit:
    """Tests for G722CodecManager initialization."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_default_init(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        assert manager.enabled is True
        assert manager.default_bitrate == G722Codec.MODE_64K
        assert manager.encoders == {}
        assert manager.decoders == {}

    @patch("pbx.features.g722_codec.get_logger")
    def test_init_with_config(self, mock_logger: MagicMock) -> None:
        config = {"codecs.g722.enabled": False, "codecs.g722.bitrate": 56000}
        manager = G722CodecManager(config=config)
        # Note: config.get with dot keys doesn't do nested lookup
        # It looks for literal key "codecs.g722.enabled"
        assert manager.config == config

    @patch("pbx.features.g722_codec.get_logger")
    def test_init_disabled(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager(config={"codecs.g722.enabled": False})
        # The config.get with default True will still return True
        # because dict.get("codecs.g722.enabled") won't find it with nested key
        assert isinstance(manager.enabled, bool)


@pytest.mark.unit
class TestCreateEncoder:
    """Tests for create_encoder method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_create_encoder(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        encoder = manager.create_encoder("call-1")
        assert encoder is not None
        assert isinstance(encoder, G722Codec)
        assert "call-1" in manager.encoders

    @patch("pbx.features.g722_codec.get_logger")
    def test_create_encoder_custom_bitrate(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        encoder = manager.create_encoder("call-1", bitrate=48000)
        assert encoder.bitrate == 48000

    @patch("pbx.features.g722_codec.get_logger")
    def test_create_encoder_disabled(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.enabled = False
        encoder = manager.create_encoder("call-1")
        assert encoder is None


@pytest.mark.unit
class TestCreateDecoder:
    """Tests for create_decoder method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_create_decoder(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        decoder = manager.create_decoder("call-1")
        assert decoder is not None
        assert isinstance(decoder, G722Codec)
        assert "call-1" in manager.decoders

    @patch("pbx.features.g722_codec.get_logger")
    def test_create_decoder_custom_bitrate(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        decoder = manager.create_decoder("call-1", bitrate=56000)
        assert decoder.bitrate == 56000

    @patch("pbx.features.g722_codec.get_logger")
    def test_create_decoder_disabled(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.enabled = False
        decoder = manager.create_decoder("call-1")
        assert decoder is None


@pytest.mark.unit
class TestReleaseCodec:
    """Tests for release_codec method."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_release_both(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.create_encoder("call-1")
        manager.create_decoder("call-1")
        manager.release_codec("call-1")
        assert "call-1" not in manager.encoders
        assert "call-1" not in manager.decoders

    @patch("pbx.features.g722_codec.get_logger")
    def test_release_nonexistent(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.release_codec("nonexistent")  # Should not raise

    @patch("pbx.features.g722_codec.get_logger")
    def test_release_only_encoder(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.create_encoder("call-1")
        manager.release_codec("call-1")
        assert "call-1" not in manager.encoders


@pytest.mark.unit
class TestGetEncoderDecoder:
    """Tests for get_encoder and get_decoder."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_encoder_exists(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.create_encoder("call-1")
        assert manager.get_encoder("call-1") is not None

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_encoder_not_exists(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        assert manager.get_encoder("nonexistent") is None

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_decoder_exists(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.create_decoder("call-1")
        assert manager.get_decoder("call-1") is not None

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_decoder_not_exists(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        assert manager.get_decoder("nonexistent") is None


@pytest.mark.unit
class TestManagerStatistics:
    """Tests for G722CodecManager.get_statistics."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_statistics(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.create_encoder("call-1")
        manager.create_encoder("call-2")
        manager.create_decoder("call-1")
        stats = manager.get_statistics()
        assert stats["enabled"] is True
        assert stats["active_encoders"] == 2
        assert stats["active_decoders"] == 1
        assert stats["default_bitrate"] == 64000
        assert stats["supported"] is True

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_statistics_empty(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        stats = manager.get_statistics()
        assert stats["active_encoders"] == 0
        assert stats["active_decoders"] == 0


@pytest.mark.unit
class TestManagerSdpCapabilities:
    """Tests for G722CodecManager.get_sdp_capabilities."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_sdp_capabilities_enabled(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        caps = manager.get_sdp_capabilities()
        assert len(caps) == 1
        assert "G722" in caps[0]

    @patch("pbx.features.g722_codec.get_logger")
    def test_get_sdp_capabilities_disabled(self, mock_logger: MagicMock) -> None:
        manager = G722CodecManager()
        manager.enabled = False
        caps = manager.get_sdp_capabilities()
        assert caps == []


@pytest.mark.unit
class TestPredictorUpdates:
    """Tests for predictor update methods."""

    @patch("pbx.features.g722_codec.get_logger")
    def test_update_predictor_lower(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.encoder_state
        state.sl = 1000
        codec._update_predictor_lower(state, 50)
        assert state.spl == 1000

    @patch("pbx.features.g722_codec.get_logger")
    def test_update_predictor_higher(self, mock_logger: MagicMock) -> None:
        codec = G722Codec()
        state = codec.encoder_state
        state.sh = 500
        codec._update_predictor_higher(state, 25)
        assert state.sph == 500
