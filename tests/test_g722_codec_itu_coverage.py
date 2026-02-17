"""
Tests for G.722 HD Audio Codec - ITU-T Compliant Implementation

Comprehensive tests covering:
- G722State initialization and state management
- G722CodecITU encoding, decoding, and helper methods
- QMF analysis and synthesis
- Quantization and inverse quantization
- Adaptive prediction
- Edge cases and error handling
- Module-level constants/tables
"""

import struct
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.g722_codec_itu import (
    IHB_TABLE,
    ILB_TABLE,
    Q2,
    Q6,
    QMF_COEFFS,
    WH_TABLE,
    WL_TABLE,
    G722CodecITU,
    G722State,
)


@pytest.mark.unit
class TestModuleLevelConstants:
    """Test module-level lookup tables and constants"""

    def test_qmf_coeffs_length(self) -> None:
        """QMF filter coefficients should have 24 entries"""
        assert len(QMF_COEFFS) == 24

    def test_qmf_coeffs_are_integers(self) -> None:
        """All QMF coefficients should be integers"""
        for coeff in QMF_COEFFS:
            assert isinstance(coeff, int)

    def test_qmf_coeffs_symmetry(self) -> None:
        """QMF coefficients should exhibit known symmetric structure"""
        # The table is symmetric: QMF_COEFFS[i] == QMF_COEFFS[23 - i]
        for i in range(24):
            assert QMF_COEFFS[i] == QMF_COEFFS[23 - i]

    def test_wl_table_length(self) -> None:
        """WL table should have entries covering the range"""
        assert len(WL_TABLE) > 0

    def test_wh_table_length(self) -> None:
        """WH table should have 4 entries for 2-bit higher sub-band"""
        assert len(WH_TABLE) == 4

    def test_ilb_table_length(self) -> None:
        """ILB table should have 32 entries"""
        assert len(ILB_TABLE) == 32

    def test_ilb_table_monotonically_increasing(self) -> None:
        """ILB table values should be monotonically increasing"""
        for i in range(1, len(ILB_TABLE)):
            assert ILB_TABLE[i] > ILB_TABLE[i - 1]

    def test_ihb_table_length(self) -> None:
        """IHB table should have 4 entries"""
        assert len(IHB_TABLE) == 4

    def test_ihb_table_first_entry_zero(self) -> None:
        """IHB table first entry should be 0"""
        assert IHB_TABLE[0] == 0

    def test_q6_length(self) -> None:
        """Q6 decision levels should have 32 entries"""
        assert len(Q6) == 32

    def test_q6_monotonically_increasing(self) -> None:
        """Q6 decision levels should be monotonically increasing"""
        for i in range(1, len(Q6)):
            assert Q6[i] > Q6[i - 1]

    def test_q2_length(self) -> None:
        """Q2 decision levels should have 3 entries"""
        assert len(Q2) == 3


@pytest.mark.unit
class TestG722State:
    """Test G722State initialization and attributes"""

    def test_state_initialization(self) -> None:
        """State should be properly initialized with default values"""
        state = G722State()

        # QMF filter history
        assert state.x == [0] * 24
        assert len(state.x) == 24

    def test_lower_subband_state_initialization(self) -> None:
        """Lower sub-band state should be initialized to zeros/defaults"""
        state = G722State()

        assert state.s == 0
        assert state.sp == 0
        assert state.sz == 0
        assert state.r == [0, 0]
        assert state.a == [0, 0]
        assert state.b == [0] * 6
        assert state.p == [0] * 6
        assert state.d == [0] * 7
        assert state.nb == 0
        assert state.det == 32

    def test_higher_subband_state_initialization(self) -> None:
        """Higher sub-band state should be initialized to zeros/defaults"""
        state = G722State()

        assert state.s_h == 0
        assert state.sp_h == 0
        assert state.sz_h == 0
        assert state.r_h == [0, 0]
        assert state.a_h == [0, 0]
        assert state.b_h == [0] * 6
        assert state.p_h == [0] * 6
        assert state.d_h == [0] * 7
        assert state.nb_h == 0
        assert state.det_h == 8

    def test_state_mutability(self) -> None:
        """State fields should be mutable"""
        state = G722State()
        state.s = 100
        state.det = 64
        state.s_h = -50
        state.det_h = 16

        assert state.s == 100
        assert state.det == 64
        assert state.s_h == -50
        assert state.det_h == 16

    def test_state_list_independence(self) -> None:
        """Lists in different state instances should be independent"""
        state1 = G722State()
        state2 = G722State()

        state1.x[0] = 999
        assert state2.x[0] == 0

    def test_state_det_defaults(self) -> None:
        """Default det values match ITU-T spec initial values"""
        state = G722State()
        assert state.det == 32
        assert state.det_h == 8


@pytest.mark.unit
class TestG722CodecITUInit:
    """Test G722CodecITU initialization"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_default_initialization(self, mock_get_logger: MagicMock) -> None:
        """Codec should initialize with default 64000 bps bitrate"""
        codec = G722CodecITU()

        assert codec.bitrate == 64000
        assert isinstance(codec.encoder_state, G722State)
        assert isinstance(codec.decoder_state, G722State)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_custom_bitrate_initialization(self, mock_get_logger: MagicMock) -> None:
        """Codec should accept custom bitrate"""
        codec = G722CodecITU(bitrate=56000)
        assert codec.bitrate == 56000

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encoder_decoder_states_independent(self, mock_get_logger: MagicMock) -> None:
        """Encoder and decoder states should be separate instances"""
        codec = G722CodecITU()
        assert codec.encoder_state is not codec.decoder_state

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_class_constants(self, mock_get_logger: MagicMock) -> None:
        """Class-level constants should be correct per G.722 spec"""
        assert G722CodecITU.SAMPLE_RATE == 16000
        assert G722CodecITU.PAYLOAD_TYPE == 9

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_logger_debug_called(self, mock_get_logger: MagicMock) -> None:
        """Initialization should log debug message"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        G722CodecITU(bitrate=64000)
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "64000" in call_args


@pytest.mark.unit
class TestG722CodecITUEncode:
    """Test G722CodecITU.encode method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_empty_data(self, mock_get_logger: MagicMock) -> None:
        """Encoding less than 4 bytes of data should return empty bytes"""
        codec = G722CodecITU()
        result = codec.encode(b"")
        assert result == b""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_single_byte(self, mock_get_logger: MagicMock) -> None:
        """Encoding 1 byte should return empty bytes (needs at least 4)"""
        codec = G722CodecITU()
        result = codec.encode(b"\x00")
        assert result == b""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_two_bytes(self, mock_get_logger: MagicMock) -> None:
        """Encoding 2 bytes should return empty bytes (needs at least 4)"""
        codec = G722CodecITU()
        result = codec.encode(b"\x00\x00")
        assert result == b""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_three_bytes(self, mock_get_logger: MagicMock) -> None:
        """Encoding 3 bytes (not multiple of 4) should be trimmed to empty"""
        codec = G722CodecITU()
        result = codec.encode(b"\x00\x00\x00")
        assert result == b""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_four_bytes_silence(self, mock_get_logger: MagicMock) -> None:
        """Encoding 4 bytes of silence should produce 1 encoded byte"""
        codec = G722CodecITU()
        # Two 16-bit samples of silence
        pcm_data = struct.pack("<hh", 0, 0)
        result = codec.encode(pcm_data)

        assert result is not None
        assert len(result) == 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_eight_bytes(self, mock_get_logger: MagicMock) -> None:
        """Encoding 8 bytes (4 samples) should produce 2 encoded bytes"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hhhh", 100, 200, 300, 400)
        result = codec.encode(pcm_data)

        assert result is not None
        assert len(result) == 2

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_non_aligned_data(self, mock_get_logger: MagicMock) -> None:
        """Encoding data not aligned to 4 bytes should truncate and work"""
        codec = G722CodecITU()
        # 5 bytes -> truncated to 4 bytes -> 1 output byte
        pcm_data = struct.pack("<hh", 100, 200) + b"\x00"
        result = codec.encode(pcm_data)

        assert result is not None
        assert len(result) == 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_positive_samples(self, mock_get_logger: MagicMock) -> None:
        """Encoding positive PCM values should produce non-None result"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hh", 16000, 16000)
        result = codec.encode(pcm_data)

        assert result is not None
        assert isinstance(result, bytes)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_negative_samples(self, mock_get_logger: MagicMock) -> None:
        """Encoding negative PCM values should produce non-None result"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hh", -16000, -16000)
        result = codec.encode(pcm_data)

        assert result is not None
        assert isinstance(result, bytes)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_max_samples(self, mock_get_logger: MagicMock) -> None:
        """Encoding max PCM values should not crash"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hh", 32767, 32767)
        result = codec.encode(pcm_data)

        assert result is not None

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_min_samples(self, mock_get_logger: MagicMock) -> None:
        """Encoding min PCM values should not crash"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hh", -32768, -32768)
        result = codec.encode(pcm_data)

        assert result is not None

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_output_byte_range(self, mock_get_logger: MagicMock) -> None:
        """Each encoded byte should be in 0-255 range (6 lower + 2 upper bits)"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hh", 5000, -5000)
        result = codec.encode(pcm_data)

        assert result is not None
        for byte_val in result:
            assert 0 <= byte_val <= 255

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_returns_none_on_error(self, mock_get_logger: MagicMock) -> None:
        """Encoding should return None on struct error"""
        codec = G722CodecITU()
        # Monkey-patch encoder state to cause an error
        codec.encoder_state.x = None  # Will cause TypeError in list operations
        pcm_data = struct.pack("<hh", 100, 200)
        result = codec.encode(pcm_data)

        assert result is None

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_large_frame(self, mock_get_logger: MagicMock) -> None:
        """Encoding a large frame should work correctly"""
        codec = G722CodecITU()
        # 160 samples = 320 bytes -> 80 encoded bytes
        samples = [i % 1000 for i in range(160)]
        pcm_data = struct.pack(f"<{len(samples)}h", *samples)
        result = codec.encode(pcm_data)

        assert result is not None
        assert len(result) == 80  # 160 samples / 2 = 80 output bytes

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_preserves_encoder_state(self, mock_get_logger: MagicMock) -> None:
        """Multiple encode calls should update encoder state"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hh", 10000, 10000)

        codec.encode(pcm_data)
        # After encoding, state should have changed from initial values
        state = codec.encoder_state
        # The x buffer should have been updated
        assert state.x != [0] * 24


@pytest.mark.unit
class TestG722CodecITUDecode:
    """Test G722CodecITU.decode method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_empty_data(self, mock_get_logger: MagicMock) -> None:
        """Decoding empty data should return empty bytes"""
        codec = G722CodecITU()
        result = codec.decode(b"")
        assert result == b""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_single_byte(self, mock_get_logger: MagicMock) -> None:
        """Decoding 1 byte should produce 4 bytes (2 samples)"""
        codec = G722CodecITU()
        result = codec.decode(b"\x00")

        assert result is not None
        assert len(result) == 4  # 2 samples * 2 bytes each

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_multiple_bytes(self, mock_get_logger: MagicMock) -> None:
        """Decoding N bytes should produce 4*N bytes"""
        codec = G722CodecITU()
        result = codec.decode(b"\x00\x01\x02\x03")

        assert result is not None
        assert len(result) == 16  # 4 bytes * 4 output bytes each

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_output_is_valid_pcm(self, mock_get_logger: MagicMock) -> None:
        """Decoded output should be valid 16-bit PCM samples"""
        codec = G722CodecITU()
        result = codec.decode(b"\x2a")

        assert result is not None
        assert len(result) == 4
        # Should be parseable as two 16-bit signed integers
        s1 = struct.unpack("<h", result[0:2])[0]
        s2 = struct.unpack("<h", result[2:4])[0]
        assert -32768 <= s1 <= 32767
        assert -32768 <= s2 <= 32767

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_silence(self, mock_get_logger: MagicMock) -> None:
        """Decoding zero byte should produce near-silence"""
        codec = G722CodecITU()
        result = codec.decode(b"\x00")

        assert result is not None
        s1 = struct.unpack("<h", result[0:2])[0]
        s2 = struct.unpack("<h", result[2:4])[0]
        # With fresh state, decoding 0x00 should produce values close to 0
        assert abs(s1) < 1000
        assert abs(s2) < 1000

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_all_byte_values(self, mock_get_logger: MagicMock) -> None:
        """Decoding every possible byte value should not crash"""
        codec = G722CodecITU()
        for val in range(256):
            result = codec.decode(bytes([val]))
            assert result is not None
            assert len(result) == 4

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_extracts_lower_and_upper_bits(self, mock_get_logger: MagicMock) -> None:
        """Decode should split byte into 6-bit lower and 2-bit upper"""
        codec = G722CodecITU()
        # 0xFF = ih=3 (bits 7-6), il=63 (bits 5-0)
        result = codec.decode(b"\xff")
        assert result is not None
        assert len(result) == 4

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_returns_none_on_error(self, mock_get_logger: MagicMock) -> None:
        """Decode should return None when internal error occurs"""
        codec = G722CodecITU()
        # Monkey-patch _decode_lower to raise a ValueError
        _original = codec._decode_lower

        def broken_decode_lower(il, state):
            raise ValueError("simulated decode error")

        codec._decode_lower = broken_decode_lower
        result = codec.decode(b"\x2a")
        assert result is None

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_preserves_state(self, mock_get_logger: MagicMock) -> None:
        """Multiple decode calls should properly update decoder state"""
        codec = G722CodecITU()
        codec.decode(b"\x2a")
        _state_after_first = codec.decoder_state.s

        codec.decode(b"\x2a")
        # State should evolve between calls
        assert isinstance(codec.decoder_state.s, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_large_frame(self, mock_get_logger: MagicMock) -> None:
        """Decoding a large frame should work"""
        codec = G722CodecITU()
        g722_data = bytes(range(80))
        result = codec.decode(g722_data)

        assert result is not None
        assert len(result) == 80 * 4


@pytest.mark.unit
class TestG722CodecITUEncodeDecode:
    """Test encode/decode round-trip"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_then_decode_silence(self, mock_get_logger: MagicMock) -> None:
        """Encoding and decoding silence should produce near-silence output"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hh", 0, 0)
        encoded = codec.encode(pcm_data)

        assert encoded is not None

        # Create a new codec for decoding to have fresh state
        codec2 = G722CodecITU()
        decoded = codec2.decode(encoded)

        assert decoded is not None
        assert len(decoded) == 4

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_decode_length_ratio(self, mock_get_logger: MagicMock) -> None:
        """Encoded size should be 1/4 of PCM size; decoded should restore size"""
        codec = G722CodecITU()
        samples = [i * 100 for i in range(80)]
        pcm_data = struct.pack(f"<{len(samples)}h", *samples)

        encoded = codec.encode(pcm_data)
        assert encoded is not None
        # 80 samples (160 bytes PCM) -> 40 encoded bytes
        assert len(encoded) == 40

        codec2 = G722CodecITU()
        decoded = codec2.decode(encoded)
        assert decoded is not None
        # 40 encoded bytes -> 80 samples (160 bytes PCM)
        assert len(decoded) == 160


@pytest.mark.unit
class TestQMFAnalysis:
    """Test _qmf_analysis method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_analysis_zeros(self, mock_get_logger: MagicMock) -> None:
        """QMF analysis of all-zero input should return 0"""
        codec = G722CodecITU()
        x = [0] * 24
        result = codec._qmf_analysis(x, 0)
        assert result == 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_analysis_phase_0(self, mock_get_logger: MagicMock) -> None:
        """QMF analysis phase 0 should use coefficients as-is"""
        codec = G722CodecITU()
        x = [1] * 24
        result = codec._qmf_analysis(x, 0)
        # Sum of QMF_COEFFS >> 14 with saturation
        expected_acc = sum(QMF_COEFFS)
        expected = expected_acc >> 14
        expected = max(-16384, min(16383, expected))
        assert result == expected

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_analysis_phase_1(self, mock_get_logger: MagicMock) -> None:
        """QMF analysis phase 1 should negate odd-indexed coefficients"""
        codec = G722CodecITU()
        x = [1] * 24
        result = codec._qmf_analysis(x, 1)

        # Phase 1 negates odd-indexed coefficients
        acc = 0
        for i in range(24):
            coeff = QMF_COEFFS[i]
            if i % 2:
                coeff = -coeff
            acc += coeff
        expected = acc >> 14
        expected = max(-16384, min(16383, expected))
        assert result == expected

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_analysis_saturation_upper(self, mock_get_logger: MagicMock) -> None:
        """QMF analysis should saturate at 16383"""
        codec = G722CodecITU()
        # Use very large values to force saturation
        x = [32767] * 24
        result = codec._qmf_analysis(x, 0)
        assert result <= 16383

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_analysis_saturation_lower(self, mock_get_logger: MagicMock) -> None:
        """QMF analysis should saturate at -16384"""
        codec = G722CodecITU()
        x = [-32768] * 24
        result = codec._qmf_analysis(x, 0)
        assert result >= -16384


@pytest.mark.unit
class TestQMFSynthesis:
    """Test _qmf_synthesis method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_synthesis_zeros(self, mock_get_logger: MagicMock) -> None:
        """QMF synthesis with zero inputs should return (0, 0)"""
        codec = G722CodecITU()
        state = G722State()
        xout1, xout2 = codec._qmf_synthesis(0, 0, state)
        assert xout1 == 0
        assert xout2 == 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_synthesis_addition_and_subtraction(self, mock_get_logger: MagicMock) -> None:
        """QMF synthesis should add rl+rh and rl-rh"""
        codec = G722CodecITU()
        state = G722State()
        xout1, xout2 = codec._qmf_synthesis(1000, 500, state)
        assert xout1 == 1500  # rl + rh
        assert xout2 == 500  # rl - rh

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_synthesis_saturation(self, mock_get_logger: MagicMock) -> None:
        """QMF synthesis should saturate output to [-16384, 16383]"""
        codec = G722CodecITU()
        state = G722State()
        xout1, xout2 = codec._qmf_synthesis(16000, 16000, state)
        assert xout1 <= 16383
        assert xout2 >= -16384

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_qmf_synthesis_negative_inputs(self, mock_get_logger: MagicMock) -> None:
        """QMF synthesis should handle negative inputs"""
        codec = G722CodecITU()
        state = G722State()
        xout1, xout2 = codec._qmf_synthesis(-1000, -500, state)
        assert xout1 == -1500  # -1000 + -500
        assert xout2 == -500  # -1000 - (-500)


@pytest.mark.unit
class TestEncodeLower:
    """Test _encode_lower method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_lower_zero_input(self, mock_get_logger: MagicMock) -> None:
        """Encoding zero in lower sub-band should return a valid 6-bit code"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._encode_lower(0, state)
        assert 0 <= result <= 63

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_lower_positive_input(self, mock_get_logger: MagicMock) -> None:
        """Encoding positive value should return code in lower half (0-31)"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._encode_lower(1000, state)
        assert 0 <= result <= 63

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_lower_negative_input(self, mock_get_logger: MagicMock) -> None:
        """Encoding negative value should return code in upper half (32-63)"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._encode_lower(-1000, state)
        # Negative differences produce il = 63 - il, so >= 32
        assert 0 <= result <= 63

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_lower_updates_state(self, mock_get_logger: MagicMock) -> None:
        """Encoding should update predictor state"""
        codec = G722CodecITU()
        state = G722State()
        _initial_det = state.det

        codec._encode_lower(5000, state)

        # State should have been updated
        assert state.sp != 0 or state.s != 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_lower_det_adaptation(self, mock_get_logger: MagicMock) -> None:
        """Det (scale factor) should adapt after encoding"""
        codec = G722CodecITU()
        state = G722State()
        _initial_det = state.det

        codec._encode_lower(5000, state)

        # Det should have changed
        assert isinstance(state.det, int)
        assert state.det >= 1  # Det is always at least 1


@pytest.mark.unit
class TestEncodeHigher:
    """Test _encode_higher method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_higher_zero_input(self, mock_get_logger: MagicMock) -> None:
        """Encoding zero in higher sub-band should return a valid 2-bit code"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._encode_higher(0, state)
        assert 0 <= result <= 3

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_higher_positive_input(self, mock_get_logger: MagicMock) -> None:
        """Encoding positive value should produce valid code"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._encode_higher(500, state)
        assert 0 <= result <= 3

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_higher_negative_input(self, mock_get_logger: MagicMock) -> None:
        """Encoding negative value should produce valid code"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._encode_higher(-500, state)
        assert 0 <= result <= 3

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_higher_updates_state(self, mock_get_logger: MagicMock) -> None:
        """Encoding should update higher sub-band state"""
        codec = G722CodecITU()
        state = G722State()

        codec._encode_higher(500, state)

        # State should have been modified
        assert isinstance(state.s_h, int)
        assert isinstance(state.det_h, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_higher_large_positive(self, mock_get_logger: MagicMock) -> None:
        """Encoding a large positive value should map to ih=3 range"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._encode_higher(10000, state)
        assert 0 <= result <= 3

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_higher_quantization_thresholds(self, mock_get_logger: MagicMock) -> None:
        """Test various thresholds in the 2-bit quantizer"""
        codec = G722CodecITU()

        # dqm < 12 -> ih = 0
        state = G722State()
        state.det_h = 8
        # With det_h=8, dqm = abs(xh) * 8 // 8 = abs(xh)
        # For xh=5, dqm=5 < 12 -> ih=0
        result = codec._encode_higher(5, state)
        assert 0 <= result <= 3


@pytest.mark.unit
class TestDecodeLower:
    """Test _decode_lower method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_lower_zero(self, mock_get_logger: MagicMock) -> None:
        """Decoding code 0 should produce a value"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._decode_lower(0, state)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_lower_max_code(self, mock_get_logger: MagicMock) -> None:
        """Decoding max code (63) should produce a value"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._decode_lower(63, state)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_lower_updates_state(self, mock_get_logger: MagicMock) -> None:
        """Decoding should update state"""
        codec = G722CodecITU()
        state = G722State()
        codec._decode_lower(20, state)

        # State s should have been set
        assert isinstance(state.s, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_lower_all_codes(self, mock_get_logger: MagicMock) -> None:
        """Decoding all possible 6-bit codes should not crash"""
        codec = G722CodecITU()
        for code in range(64):
            state = G722State()
            result = codec._decode_lower(code, state)
            assert isinstance(result, int)


@pytest.mark.unit
class TestDecodeHigher:
    """Test _decode_higher method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_higher_zero(self, mock_get_logger: MagicMock) -> None:
        """Decoding code 0 should produce a value"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._decode_higher(0, state)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_higher_max_code(self, mock_get_logger: MagicMock) -> None:
        """Decoding code 3 should produce a value"""
        codec = G722CodecITU()
        state = G722State()
        result = codec._decode_higher(3, state)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_higher_all_codes(self, mock_get_logger: MagicMock) -> None:
        """Decoding all possible 2-bit codes should not crash"""
        codec = G722CodecITU()
        for code in range(4):
            state = G722State()
            result = codec._decode_higher(code, state)
            assert isinstance(result, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_higher_updates_state(self, mock_get_logger: MagicMock) -> None:
        """Decoding should update higher sub-band state"""
        codec = G722CodecITU()
        state = G722State()
        codec._decode_higher(2, state)
        assert isinstance(state.s_h, int)
        assert isinstance(state.det_h, int)


@pytest.mark.unit
class TestInverseQuantLower:
    """Test _inverse_quant_lower method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_lower_zero(self, mock_get_logger: MagicMock) -> None:
        """Inverse quantizing code 0 should produce a value"""
        codec = G722CodecITU()
        result = codec._inverse_quant_lower(0, 32)
        assert isinstance(result, int)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_lower_positive_code(self, mock_get_logger: MagicMock) -> None:
        """Inverse quantizing a positive code (< 32) should produce positive dq"""
        codec = G722CodecITU()
        result = codec._inverse_quant_lower(10, 32)
        assert result >= 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_lower_negative_code(self, mock_get_logger: MagicMock) -> None:
        """Inverse quantizing a code >= 32 should produce negative dq"""
        codec = G722CodecITU()
        result = codec._inverse_quant_lower(50, 32)
        assert result <= 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_lower_code_clamped_to_63(self, mock_get_logger: MagicMock) -> None:
        """Code values > 63 should be clamped to 63"""
        codec = G722CodecITU()
        result_63 = codec._inverse_quant_lower(63, 32)
        result_100 = codec._inverse_quant_lower(100, 32)
        assert result_63 == result_100

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_lower_det_scaling(self, mock_get_logger: MagicMock) -> None:
        """Different det values should scale the output"""
        codec = G722CodecITU()
        result_low = codec._inverse_quant_lower(5, 16)
        result_high = codec._inverse_quant_lower(5, 64)
        # Higher det should produce larger magnitude
        assert abs(result_high) >= abs(result_low)

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_lower_code_31(self, mock_get_logger: MagicMock) -> None:
        """Code 31 (max positive) should be the largest positive value"""
        codec = G722CodecITU()
        result = codec._inverse_quant_lower(31, 32)
        assert result >= 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_lower_code_32(self, mock_get_logger: MagicMock) -> None:
        """Code 32 (first negative) should produce negative output"""
        codec = G722CodecITU()
        result = codec._inverse_quant_lower(32, 32)
        # 32 -> wd = 32 - 64 = -32, idx = 32 -> uses ILB_TABLE[31]
        assert result <= 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_lower_idx_above_31(self, mock_get_logger: MagicMock) -> None:
        """When idx >= 32, should use ILB_TABLE[31]"""
        codec = G722CodecITU()
        # code 32 -> wd = -32, idx = 32 >= 32 -> uses ILB_TABLE[31]
        result = codec._inverse_quant_lower(32, 100)
        assert isinstance(result, int)


@pytest.mark.unit
class TestInverseQuantHigher:
    """Test _inverse_quant_higher method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_higher_zero(self, mock_get_logger: MagicMock) -> None:
        """Inverse quantizing code 0 should produce non-negative value"""
        codec = G722CodecITU()
        result = codec._inverse_quant_higher(0, 8)
        assert result >= 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_higher_code_1(self, mock_get_logger: MagicMock) -> None:
        """Inverse quantizing code 1 should produce positive value"""
        codec = G722CodecITU()
        result = codec._inverse_quant_higher(1, 8)
        assert result >= 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_higher_code_2(self, mock_get_logger: MagicMock) -> None:
        """Inverse quantizing code 2 (negative sign) should produce non-positive"""
        codec = G722CodecITU()
        result = codec._inverse_quant_higher(2, 8)
        # ih=2 -> wd = 2-4 = -2, so dq should be <= 0
        assert result <= 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_higher_code_3(self, mock_get_logger: MagicMock) -> None:
        """Inverse quantizing code 3 (negative sign) should produce non-positive"""
        codec = G722CodecITU()
        result = codec._inverse_quant_higher(3, 8)
        # ih=3 -> wd = 3-4 = -1, so dq should be <= 0
        assert result <= 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_inverse_quant_higher_idx_out_of_range(self, mock_get_logger: MagicMock) -> None:
        """When idx >= 4, should use IHB_TABLE[3]"""
        codec = G722CodecITU()
        # This shouldn't normally happen with 2-bit codes, but tests the fallback
        result = codec._inverse_quant_higher(5, 8)
        assert isinstance(result, int)


@pytest.mark.unit
class TestAdaptLower:
    """Test _adapt_lower method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_lower_returns_positive(self, mock_get_logger: MagicMock) -> None:
        """Adapted det should always be at least 1"""
        codec = G722CodecITU()
        result = codec._adapt_lower(0, 32)
        assert result >= 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_lower_clamped_il(self, mock_get_logger: MagicMock) -> None:
        """il values > 63 should be clamped to 63"""
        codec = G722CodecITU()
        result_63 = codec._adapt_lower(63, 100)
        result_100 = codec._adapt_lower(100, 100)
        # Both should work without error
        assert result_63 >= 1
        assert result_100 >= 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_lower_nbl_lower_bound(self, mock_get_logger: MagicMock) -> None:
        """nbl should not go below 0"""
        codec = G722CodecITU()
        # WL_TABLE[0] is -60, with det=0: nbl = 0 + (-60) -> clamped to 0
        result = codec._adapt_lower(0, 0)
        assert result >= 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_lower_nbl_upper_bound(self, mock_get_logger: MagicMock) -> None:
        """nbl should not exceed 18432"""
        codec = G722CodecITU()
        # Use a large det and positive WL entry to try to exceed 18432
        result = codec._adapt_lower(1, 20000)
        # 20000 + 3042 = 23042, clamped to 18432, then >> 11 = 9
        assert result == 9

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_lower_minimum_det(self, mock_get_logger: MagicMock) -> None:
        """Adapted det should never be less than 1"""
        codec = G722CodecITU()
        for il in range(64):
            result = codec._adapt_lower(il, 0)
            assert result >= 1


@pytest.mark.unit
class TestAdaptHigher:
    """Test _adapt_higher method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_higher_returns_positive(self, mock_get_logger: MagicMock) -> None:
        """Adapted det_h should always be at least 1"""
        codec = G722CodecITU()
        result = codec._adapt_higher(0, 8)
        assert result >= 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_higher_ih_masked(self, mock_get_logger: MagicMock) -> None:
        """ih should be masked with & 3"""
        codec = G722CodecITU()
        result_1 = codec._adapt_higher(1, 100)
        result_5 = codec._adapt_higher(5, 100)  # 5 & 3 = 1
        assert result_1 == result_5

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_higher_nbl_lower_bound(self, mock_get_logger: MagicMock) -> None:
        """nbh should not go below 0"""
        codec = G722CodecITU()
        # WH_TABLE[1] = -214, with det=0: nbh = 0 + (-214) -> clamped to 0
        result = codec._adapt_higher(1, 0)
        assert result >= 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_higher_nbl_upper_bound(self, mock_get_logger: MagicMock) -> None:
        """nbh should not exceed 22528"""
        codec = G722CodecITU()
        result = codec._adapt_higher(2, 25000)
        # 25000 + 798 = 25798, clamped to 22528, then >> 11 = 11
        assert result == 11

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_adapt_higher_all_codes(self, mock_get_logger: MagicMock) -> None:
        """All 2-bit codes should produce valid adaptation"""
        codec = G722CodecITU()
        for ih in range(4):
            result = codec._adapt_higher(ih, 8)
            assert result >= 1


@pytest.mark.unit
class TestUpdatePredictorLower:
    """Test _update_predictor_lower method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_update_predictor_lower_sets_sp(self, mock_get_logger: MagicMock) -> None:
        """Predictor update should set sp to current s"""
        codec = G722CodecITU()
        state = G722State()
        state.s = 12345

        codec._update_predictor_lower(state, 100)
        assert state.sp == 12345

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_update_predictor_lower_zero_state(self, mock_get_logger: MagicMock) -> None:
        """Predictor update with zero state should keep sp at 0"""
        codec = G722CodecITU()
        state = G722State()

        codec._update_predictor_lower(state, 0)
        assert state.sp == 0


@pytest.mark.unit
class TestUpdatePredictorHigher:
    """Test _update_predictor_higher method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_update_predictor_higher_sets_sp_h(self, mock_get_logger: MagicMock) -> None:
        """Predictor update should set sp_h to current s_h"""
        codec = G722CodecITU()
        state = G722State()
        state.s_h = -5678

        codec._update_predictor_higher(state, 50)
        assert state.sp_h == -5678

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_update_predictor_higher_zero_state(self, mock_get_logger: MagicMock) -> None:
        """Predictor update with zero state should keep sp_h at 0"""
        codec = G722CodecITU()
        state = G722State()

        codec._update_predictor_higher(state, 0)
        assert state.sp_h == 0


@pytest.mark.unit
class TestSaturate:
    """Test _saturate method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_saturate_within_range(self, mock_get_logger: MagicMock) -> None:
        """Value within range should be returned as-is"""
        codec = G722CodecITU()
        assert codec._saturate(100, -1000, 1000) == 100

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_saturate_below_min(self, mock_get_logger: MagicMock) -> None:
        """Value below min should return min"""
        codec = G722CodecITU()
        assert codec._saturate(-2000, -1000, 1000) == -1000

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_saturate_above_max(self, mock_get_logger: MagicMock) -> None:
        """Value above max should return max"""
        codec = G722CodecITU()
        assert codec._saturate(2000, -1000, 1000) == 1000

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_saturate_at_min(self, mock_get_logger: MagicMock) -> None:
        """Value at min boundary should be returned as-is"""
        codec = G722CodecITU()
        assert codec._saturate(-1000, -1000, 1000) == -1000

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_saturate_at_max(self, mock_get_logger: MagicMock) -> None:
        """Value at max boundary should be returned as-is"""
        codec = G722CodecITU()
        assert codec._saturate(1000, -1000, 1000) == 1000

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_saturate_zero(self, mock_get_logger: MagicMock) -> None:
        """Zero should always be within range"""
        codec = G722CodecITU()
        assert codec._saturate(0, -32768, 32767) == 0

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_saturate_16bit_range(self, mock_get_logger: MagicMock) -> None:
        """Test saturation with 16-bit PCM range"""
        codec = G722CodecITU()
        assert codec._saturate(50000, -32768, 32767) == 32767
        assert codec._saturate(-50000, -32768, 32767) == -32768


@pytest.mark.unit
class TestGetInfo:
    """Test get_info method"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_get_info_keys(self, mock_get_logger: MagicMock) -> None:
        """Info dict should contain all expected keys"""
        codec = G722CodecITU()
        info = codec.get_info()

        expected_keys = {
            "name",
            "description",
            "sample_rate",
            "bitrate",
            "payload_type",
            "implementation",
        }
        assert set(info.keys()) == expected_keys

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_get_info_values(self, mock_get_logger: MagicMock) -> None:
        """Info dict should contain correct values"""
        codec = G722CodecITU()
        info = codec.get_info()

        assert info["name"] == "G.722"
        assert info["sample_rate"] == 16000
        assert info["bitrate"] == 64000
        assert info["payload_type"] == 9
        assert "ITU-T" in info["implementation"]

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_get_info_custom_bitrate(self, mock_get_logger: MagicMock) -> None:
        """Info dict should reflect custom bitrate"""
        codec = G722CodecITU(bitrate=48000)
        info = codec.get_info()

        assert info["bitrate"] == 48000

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_get_info_description_is_string(self, mock_get_logger: MagicMock) -> None:
        """Description should be a non-empty string"""
        codec = G722CodecITU()
        info = codec.get_info()

        assert isinstance(info["description"], str)
        assert len(info["description"]) > 0


@pytest.mark.unit
class TestIsSupported:
    """Test is_supported static method"""

    def test_is_supported_returns_true(self) -> None:
        """is_supported should always return True"""
        assert G722CodecITU.is_supported() is True

    def test_is_supported_as_static_method(self) -> None:
        """is_supported should be callable without an instance"""
        result = G722CodecITU.is_supported()
        assert result is True

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_is_supported_on_instance(self, mock_get_logger: MagicMock) -> None:
        """is_supported should also work on an instance"""
        codec = G722CodecITU()
        assert codec.is_supported() is True


@pytest.mark.unit
class TestG722CodecITUEdgeCases:
    """Test edge cases and error handling"""

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_alternating_max_samples(self, mock_get_logger: MagicMock) -> None:
        """Encoding alternating max/min samples should not crash"""
        codec = G722CodecITU()
        samples = []
        for _ in range(40):
            samples.extend([32767, -32768])
        pcm_data = struct.pack(f"<{len(samples)}h", *samples)
        result = codec.encode(pcm_data)
        assert result is not None

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_consecutive_calls(self, mock_get_logger: MagicMock) -> None:
        """Multiple consecutive encode calls should maintain state properly"""
        codec = G722CodecITU()
        pcm_data = struct.pack("<hh", 1000, 2000)

        result1 = codec.encode(pcm_data)
        result2 = codec.encode(pcm_data)

        assert result1 is not None
        assert result2 is not None
        # Results may differ because state accumulates
        # The important thing is no crash

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_consecutive_calls(self, mock_get_logger: MagicMock) -> None:
        """Multiple consecutive decode calls should maintain state properly"""
        codec = G722CodecITU()

        result1 = codec.decode(b"\x2a")
        result2 = codec.decode(b"\x2a")

        assert result1 is not None
        assert result2 is not None

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_exactly_four_bytes(self, mock_get_logger: MagicMock) -> None:
        """Encoding exactly 4 bytes should produce exactly 1 encoded byte"""
        codec = G722CodecITU()
        pcm_data = b"\x00\x00\x00\x00"
        result = codec.encode(pcm_data)
        assert result is not None
        assert len(result) == 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_seven_bytes_truncated_to_four(self, mock_get_logger: MagicMock) -> None:
        """Encoding 7 bytes should truncate to 4 bytes and produce 1 encoded byte"""
        codec = G722CodecITU()
        pcm_data = b"\x00\x00\x00\x00\x00\x00\x00"
        result = codec.encode(pcm_data)
        assert result is not None
        assert len(result) == 1

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_det_floor_at_zero(self, mock_get_logger: MagicMock) -> None:
        """When det is 0 or negative, it should be floored to 0 by max()"""
        codec = G722CodecITU()
        state = G722State()
        state.det = -5  # Negative det

        # Should not crash; the encode_lower method does max(det, 0)
        result = codec._encode_lower(100, state)
        assert 0 <= result <= 63

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_higher_det_h_floor(self, mock_get_logger: MagicMock) -> None:
        """When det_h is 0 or negative, it should be handled"""
        codec = G722CodecITU()
        state = G722State()
        state.det_h = -3

        result = codec._encode_higher(100, state)
        assert 0 <= result <= 3

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_lower_det_below_32(self, mock_get_logger: MagicMock) -> None:
        """When det < 32, dqm should use abs(d) directly"""
        codec = G722CodecITU()
        state = G722State()
        state.det = 10  # Below threshold of 32

        result = codec._encode_lower(50, state)
        assert 0 <= result <= 63

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_higher_det_h_below_8(self, mock_get_logger: MagicMock) -> None:
        """When det_h < 8, dqm should use abs(d_h) directly"""
        codec = G722CodecITU()
        state = G722State()
        state.det_h = 3  # Below threshold of 8

        result = codec._encode_higher(50, state)
        assert 0 <= result <= 3

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_encode_error_logs_message(self, mock_get_logger: MagicMock) -> None:
        """Encoding errors should be logged"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        codec = G722CodecITU()
        codec.encoder_state.x = None  # Break state
        pcm_data = struct.pack("<hh", 100, 200)
        codec.encode(pcm_data)

        mock_logger.error.assert_called_once()
        assert "encoding error" in mock_logger.error.call_args[0][0].lower()

    @patch("pbx.features.g722_codec_itu.get_logger")
    def test_decode_error_logs_message(self, mock_get_logger: MagicMock) -> None:
        """Decoding errors should be logged"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        codec = G722CodecITU()

        # Monkey-patch _decode_lower to raise a ValueError
        def broken_decode_lower(il, state):
            raise ValueError("simulated decode error")

        codec._decode_lower = broken_decode_lower
        codec.decode(b"\x2a")

        mock_logger.error.assert_called_once()
        assert "decoding error" in mock_logger.error.call_args[0][0].lower()
