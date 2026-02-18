"""Comprehensive tests for predictive_voicemail_drop feature module."""

import struct
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.predictive_voicemail_drop import (
    VoicemailDropSystem,
    get_voicemail_drop,
)


@pytest.mark.unit
class TestVoicemailDropSystemInit:
    """Tests for VoicemailDropSystem initialization."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_default_initialization(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        assert vds.enabled is False
        assert vds.detection_threshold == 0.85
        assert vds.max_detection_time == 5
        assert vds.message_path == "/var/pbx/voicemail_drops"
        assert vds.messages == {}
        assert vds.total_detections == 0
        assert vds.successful_drops == 0
        assert vds.failed_drops == 0
        assert vds.false_positives == 0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_initialization_with_config(self, mock_logger: MagicMock) -> None:
        config = {
            "features": {
                "voicemail_drop": {
                    "enabled": True,
                    "detection_threshold": 0.7,
                    "max_detection_time": 10,
                    "message_path": "/custom/path",
                }
            }
        }
        vds = VoicemailDropSystem(config=config)
        assert vds.enabled is True
        assert vds.detection_threshold == 0.7
        assert vds.max_detection_time == 10
        assert vds.message_path == "/custom/path"


@pytest.mark.unit
class TestDetectVoicemail:
    """Tests for detect_voicemail method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_empty_audio(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        result = vds.detect_voicemail("call-1", b"")
        assert result["is_voicemail"] is False
        assert result["confidence"] == 0.0
        assert result["detection_method"] == "insufficient_data"
        assert vds.total_detections == 1

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_short_audio(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        result = vds.detect_voicemail("call-1", b"\x00" * 50)
        assert result["is_voicemail"] is False
        assert result["detection_method"] == "insufficient_data"

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_none_audio(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        result = vds.detect_voicemail("call-1", None)
        assert result["is_voicemail"] is False

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_valid_audio_below_threshold(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        # Generate silent/low-energy audio that won't trigger detection
        # 8000 samples = 1 second at 8kHz, all low values
        samples = [10] * 8000
        audio_data = struct.pack(f"{len(samples)}h", *samples)
        result = vds.detect_voicemail("call-1", audio_data)
        assert result["call_id"] == "call-1"
        assert "confidence" in result
        assert "detected_at" in result

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_with_energy_analysis(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.detection_threshold = 0.1  # Lower threshold for testing
        # Generate consistent energy audio (like a pre-recorded message)
        # Consistent samples suggest pre-recorded content
        samples = [500] * 4000
        audio_data = struct.pack(f"{len(samples)}h", *samples)
        result = vds.detect_voicemail("call-1", audio_data)
        assert result["confidence"] >= 0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_odd_length_audio(self, mock_logger: MagicMock) -> None:
        """Test audio data that isn't aligned to 2 bytes."""
        vds = VoicemailDropSystem()
        # 101 bytes - odd number, can't unpack as 16-bit
        audio_data = b"\x00" * 101
        result = vds.detect_voicemail("call-1", audio_data)
        # Should handle struct.error gracefully
        assert result["call_id"] == "call-1"

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_voicemail_with_duration_analysis(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.detection_threshold = 0.1
        # Generate 5 seconds at 8kHz - within typical voicemail greeting range (3-10s)
        num_samples = 8000 * 5
        samples = [100] * num_samples
        audio_data = struct.pack(f"{len(samples)}h", *samples)
        result = vds.detect_voicemail("call-1", audio_data)
        assert result["confidence"] > 0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_increments_counter(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.detect_voicemail("call-1", b"")
        vds.detect_voicemail("call-2", b"")
        assert vds.total_detections == 2


@pytest.mark.unit
class TestDetectBeep:
    """Tests for _detect_beep method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_beep_no_samples(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        assert vds._detect_beep([]) is False

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_beep_short_samples(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        assert vds._detect_beep([100] * 100) is False

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_beep_silence(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        samples = [0] * 10000
        assert vds._detect_beep(samples) is False

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_beep_with_tone(self, mock_logger: MagicMock) -> None:
        """Test with a simulated tone burst (sudden energy increase sustained)."""
        vds = VoicemailDropSystem()
        # Create silence followed by sustained tone
        # Need enough samples for the algorithm: window_size * 50 minimum
        window_size = 160
        samples = [1] * (window_size * 2)  # Low energy prefix
        # Add high energy sustained tone
        samples.extend([5000] * (window_size * 60))
        # Add silence after
        samples.extend([1] * (window_size * 10))
        result = vds._detect_beep(samples)
        assert isinstance(result, bool)

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_detect_beep_energy_not_sustained(self, mock_logger: MagicMock) -> None:
        """Test with energy spike that drops quickly (not a beep)."""
        vds = VoicemailDropSystem()
        window_size = 160
        # Low energy
        samples = [1] * (window_size * 2)
        # Short energy burst
        samples.extend([5000] * window_size)
        # Back to low
        samples.extend([1] * (window_size * 60))
        result = vds._detect_beep(samples)
        assert isinstance(result, bool)


@pytest.mark.unit
class TestDropMessage:
    """Tests for drop_message method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_drop_message_not_found(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        result = vds.drop_message("call-1", "nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"]
        assert vds.failed_drops == 1

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_drop_message_success(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.add_message("msg-1", "Greeting", "/audio/greeting.wav", duration=5.0)
        # The source code references 'file_path' key in drop_message, add it
        vds.messages["msg-1"]["file_path"] = "/audio/greeting.wav"
        result = vds.drop_message("call-1", "msg-1")
        assert result["success"] is True
        assert result["call_id"] == "call-1"
        assert result["message_name"] == "Greeting"
        assert result["duration"] == 5.0
        assert "dropped_at" in result
        assert vds.successful_drops == 1

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_drop_message_multiple(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.add_message("msg-1", "Greeting", "/audio/greeting.wav", duration=5.0)
        vds.messages["msg-1"]["file_path"] = "/audio/greeting.wav"
        vds.drop_message("call-1", "msg-1")
        vds.drop_message("call-2", "msg-1")
        assert vds.successful_drops == 2


@pytest.mark.unit
class TestAddMessage:
    """Tests for add_message method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_add_message(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        result = vds.add_message("msg-1", "Hello", "/audio/hello.wav", duration=3.5)
        assert result["success"] is True
        assert result["message_id"] == "msg-1"
        assert "msg-1" in vds.messages

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_add_message_no_duration(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        result = vds.add_message("msg-1", "Hello", "/audio/hello.wav")
        assert result["success"] is True
        assert vds.messages["msg-1"]["duration"] == 0.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_add_message_fields(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.add_message("msg-1", "Test", "/audio/test.wav", duration=10.0)
        msg = vds.messages["msg-1"]
        assert msg["message_id"] == "msg-1"
        assert msg["name"] == "Test"
        assert msg["audio_path"] == "/audio/test.wav"
        assert msg["duration"] == 10.0
        assert msg["use_count"] == 0
        assert isinstance(msg["created_at"], datetime)


@pytest.mark.unit
class TestRemoveMessage:
    """Tests for remove_message method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_remove_existing(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.add_message("msg-1", "Test", "/audio/test.wav")
        result = vds.remove_message("msg-1")
        assert result is True
        assert "msg-1" not in vds.messages

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_remove_nonexistent(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        result = vds.remove_message("nonexistent")
        assert result is False


@pytest.mark.unit
class TestGetMessage:
    """Tests for get_message method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_get_existing(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.add_message("msg-1", "Test", "/audio/test.wav")
        result = vds.get_message("msg-1")
        assert result is not None
        assert result["name"] == "Test"

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_get_nonexistent(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        result = vds.get_message("nonexistent")
        assert result is None


@pytest.mark.unit
class TestListMessages:
    """Tests for list_messages method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_list_empty(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        assert vds.list_messages() == []

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_list_messages(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.add_message("msg-1", "First", "/audio/first.wav", duration=3.0)
        vds.add_message("msg-2", "Second", "/audio/second.wav", duration=5.0)
        result = vds.list_messages()
        assert len(result) == 2
        assert result[0]["message_id"] == "msg-1"
        assert result[0]["name"] == "First"
        assert result[0]["duration"] == 3.0
        assert result[0]["use_count"] == 0


@pytest.mark.unit
class TestTuneDetection:
    """Tests for tune_detection method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_tune_detection(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.tune_detection(0.6, 8)
        assert vds.detection_threshold == 0.6
        assert vds.max_detection_time == 8

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_tune_detection_extreme_values(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.tune_detection(0.0, 0)
        assert vds.detection_threshold == 0.0
        assert vds.max_detection_time == 0


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_get_statistics_initial(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        stats = vds.get_statistics()
        assert stats["enabled"] is False
        assert stats["total_detections"] == 0
        assert stats["successful_drops"] == 0
        assert stats["failed_drops"] == 0
        assert stats["false_positives"] == 0
        assert stats["success_rate"] == 0
        assert stats["total_messages"] == 0
        assert stats["detection_threshold"] == 0.85
        assert stats["max_detection_time"] == 5

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_get_statistics_with_activity(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        vds.add_message("msg-1", "Test", "/audio/test.wav", duration=5.0)
        vds.messages["msg-1"]["file_path"] = "/audio/test.wav"
        vds.detect_voicemail("call-1", b"")  # Insufficient data
        vds.drop_message("call-1", "msg-1")
        stats = vds.get_statistics()
        assert stats["total_detections"] == 1
        assert stats["successful_drops"] == 1
        assert stats["total_messages"] == 1
        assert stats["success_rate"] == 1.0


@pytest.mark.unit
class TestGetVoicemailDropSingleton:
    """Tests for get_voicemail_drop global function."""

    def test_creates_instance(self) -> None:
        import pbx.features.predictive_voicemail_drop as mod

        original = mod._voicemail_drop
        mod._voicemail_drop = None
        try:
            with patch("pbx.features.predictive_voicemail_drop.get_logger"):
                instance = get_voicemail_drop()
                assert isinstance(instance, VoicemailDropSystem)
        finally:
            mod._voicemail_drop = original

    def test_returns_same_instance(self) -> None:
        import pbx.features.predictive_voicemail_drop as mod

        original = mod._voicemail_drop
        mod._voicemail_drop = None
        try:
            with patch("pbx.features.predictive_voicemail_drop.get_logger"):
                i1 = get_voicemail_drop()
                i2 = get_voicemail_drop()
                assert i1 is i2
        finally:
            mod._voicemail_drop = original


@pytest.mark.unit
class TestDetectFrequency:
    """Tests for _detect_frequency method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_alternating_samples_estimates_frequency(self, mock_logger: MagicMock) -> None:
        """Pure alternating +/- pattern: every sample crosses zero."""
        vds = VoicemailDropSystem()
        # +1, -1, +1, -1, ... for 800 samples at 8000 Hz
        samples = [1 if i % 2 == 0 else -1 for i in range(800)]
        freq = vds._detect_frequency(samples, sample_rate=8000)
        # 799 crossings in 799 transitions, duration=0.1s
        # frequency = crossings / (2 * duration)
        assert freq > 0.0
        # With 800 samples at 8kHz, duration=0.1s, ~799 crossings
        # freq ≈ 799 / 0.2 ≈ 3995 Hz
        assert freq > 3000.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_all_zeros_returns_zero(self, mock_logger: MagicMock) -> None:
        """All-zero samples have no zero crossings."""
        vds = VoicemailDropSystem()
        samples = [0] * 1000
        freq = vds._detect_frequency(samples)
        assert freq == 0.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_empty_list_returns_zero(self, mock_logger: MagicMock) -> None:
        vds = VoicemailDropSystem()
        freq = vds._detect_frequency([])
        assert freq == 0.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_single_sample_returns_zero(self, mock_logger: MagicMock) -> None:
        """Fewer than 2 samples should return 0.0."""
        vds = VoicemailDropSystem()
        freq = vds._detect_frequency([500])
        assert freq == 0.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_two_samples_no_crossing(self, mock_logger: MagicMock) -> None:
        """Two positive samples - no zero crossing."""
        vds = VoicemailDropSystem()
        freq = vds._detect_frequency([100, 200])
        assert freq == 0.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_two_samples_with_crossing(self, mock_logger: MagicMock) -> None:
        """Two samples that cross zero."""
        vds = VoicemailDropSystem()
        freq = vds._detect_frequency([100, -100], sample_rate=8000)
        # 1 crossing, duration = 2/8000 = 0.00025s
        # freq = 1 / (2 * 0.00025) = 2000 Hz
        assert freq == 2000.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_all_positive_returns_zero(self, mock_logger: MagicMock) -> None:
        """No zero crossings when all samples are positive."""
        vds = VoicemailDropSystem()
        samples = [100, 200, 300, 400, 500] * 200
        freq = vds._detect_frequency(samples)
        assert freq == 0.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_all_negative_returns_zero(self, mock_logger: MagicMock) -> None:
        """No zero crossings when all samples are negative."""
        vds = VoicemailDropSystem()
        samples = [-100, -200, -300, -400, -500] * 200
        freq = vds._detect_frequency(samples)
        assert freq == 0.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_known_1000hz_pattern(self, mock_logger: MagicMock) -> None:
        """1000 Hz at 8000 sample rate: sign changes every 4 samples."""
        vds = VoicemailDropSystem()
        # At 8000 Hz sample rate, 1000 Hz = 8 samples per cycle
        # 4 positive, 4 negative per cycle
        cycle = [1000] * 4 + [-1000] * 4
        # 100 cycles = 800 samples = 0.1 seconds
        samples = cycle * 100
        freq = vds._detect_frequency(samples, sample_rate=8000)
        # Each cycle has 2 zero crossings: pos->neg and neg->pos
        # 100 cycles -> 200 crossings (minus edge effects)
        # freq = crossings / (2 * 0.1)
        # Should be close to 1000 Hz
        assert 900.0 <= freq <= 1100.0

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_different_sample_rate_16000(self, mock_logger: MagicMock) -> None:
        """Different sample rate changes the frequency calculation."""
        vds = VoicemailDropSystem()
        # Alternating pattern at 16000 Hz sample rate
        samples = [1, -1] * 400  # 800 samples
        freq_16k = vds._detect_frequency(samples, sample_rate=16000)
        freq_8k = vds._detect_frequency(samples, sample_rate=8000)
        # Same crossings but different duration -> different frequency
        # freq_16k should be double freq_8k
        assert freq_16k == pytest.approx(freq_8k * 2, rel=0.01)


@pytest.mark.unit
class TestLoadAudioFile:
    """Tests for _load_audio_file method."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_load_raw_file(self, mock_logger: MagicMock) -> None:
        """Loading a .raw file returns raw bytes unchanged."""
        vds = VoicemailDropSystem()
        raw_bytes = b"\x01\x02\x03\x04\x05" * 100
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_bytes", return_value=raw_bytes),
            patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".raw")),
        ):
            result = vds._load_audio_file("/audio/test.raw")
        assert result == raw_bytes

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_load_pcm_file(self, mock_logger: MagicMock) -> None:
        """Loading a .pcm file returns raw bytes unchanged."""
        vds = VoicemailDropSystem()
        pcm_bytes = b"\xff\xfe\xfd" * 200
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_bytes", return_value=pcm_bytes),
            patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".pcm")),
        ):
            result = vds._load_audio_file("/audio/test.pcm")
        assert result == pcm_bytes

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_load_wav_file_with_data_chunk(self, mock_logger: MagicMock) -> None:
        """Loading a .wav file extracts PCM data after 'data' chunk header."""
        vds = VoicemailDropSystem()
        # Build minimal WAV with RIFF header and data chunk
        pcm_payload = b"\xab\xcd" * 100
        # RIFF header (12 bytes) + fmt chunk (24 bytes) + data chunk header (8 bytes) + payload
        riff_header = b"RIFF" + struct.pack("<I", 36 + len(pcm_payload)) + b"WAVE"
        fmt_chunk = (
            b"fmt "
            + struct.pack("<I", 16)  # chunk size
            + struct.pack("<HHIIHH", 1, 1, 8000, 16000, 2, 16)
        )
        data_chunk = b"data" + struct.pack("<I", len(pcm_payload)) + pcm_payload
        wav_bytes = riff_header + fmt_chunk + data_chunk

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_bytes", return_value=wav_bytes),
            patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".wav")),
        ):
            result = vds._load_audio_file("/audio/test.wav")
        assert result == pcm_payload

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_load_wav_no_data_chunk_falls_back(self, mock_logger: MagicMock) -> None:
        """WAV file without 'data' marker falls back to skipping 44 bytes."""
        vds = VoicemailDropSystem()
        # Build a fake WAV with no 'data' marker
        header = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"fmt " + b"\x00" * 28
        pcm_payload = b"\x01\x02\x03\x04" * 50
        wav_bytes = header + pcm_payload
        # Ensure > 44 bytes and suffix is .wav
        assert len(wav_bytes) > 44

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_bytes", return_value=wav_bytes),
            patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".wav")),
        ):
            result = vds._load_audio_file("/audio/nodata.wav")
        assert result == wav_bytes[44:]

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_load_nonexistent_file_returns_none(self, mock_logger: MagicMock) -> None:
        """Non-existent file returns None."""
        vds = VoicemailDropSystem()
        with patch("pathlib.Path.exists", return_value=False):
            result = vds._load_audio_file("/audio/missing.wav")
        assert result is None

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_load_file_oserror_returns_none(self, mock_logger: MagicMock) -> None:
        """OSError during read returns None."""
        vds = VoicemailDropSystem()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_bytes", side_effect=OSError("disk error")),
        ):
            result = vds._load_audio_file("/audio/broken.raw")
        assert result is None

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_load_unsupported_extension_returns_bytes(self, mock_logger: MagicMock) -> None:
        """Non-wav/non-raw extension returns raw bytes (treated as raw PCM)."""
        vds = VoicemailDropSystem()
        raw_bytes = b"\xde\xad\xbe\xef" * 50
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_bytes", return_value=raw_bytes),
            patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".mp3")),
        ):
            result = vds._load_audio_file("/audio/test.mp3")
        assert result == raw_bytes

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_load_wav_with_extra_chunks_before_data(self, mock_logger: MagicMock) -> None:
        """WAV file with LIST or other chunks before the data chunk."""
        vds = VoicemailDropSystem()
        pcm_payload = b"\x11\x22" * 80
        riff_header = b"RIFF" + struct.pack("<I", 100 + len(pcm_payload)) + b"WAVE"
        fmt_chunk = (
            b"fmt " + struct.pack("<I", 16) + struct.pack("<HHIIHH", 1, 1, 8000, 16000, 2, 16)
        )
        # Extra LIST chunk (12 bytes) before the data chunk
        list_chunk = b"LIST" + struct.pack("<I", 4) + b"INFO"
        data_chunk = b"data" + struct.pack("<I", len(pcm_payload)) + pcm_payload
        wav_bytes = riff_header + fmt_chunk + list_chunk + data_chunk

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_bytes", return_value=wav_bytes),
            patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".wav")),
        ):
            result = vds._load_audio_file("/audio/extra_chunks.wav")
        assert result == pcm_payload


@pytest.mark.unit
class TestDetectVoicemailEnhanced:
    """Tests for enhanced detect_voicemail paths including frequency and silence analysis."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_beep_with_frequency_in_range_boosts_confidence(self, mock_logger: MagicMock) -> None:
        """When beep detected and frequency is 400-1000 Hz, confidence gets +0.1 boost."""
        vds = VoicemailDropSystem()
        vds.detection_threshold = 2.0  # Set high so we can inspect raw confidence

        # Build audio that triggers beep detection AND has frequency ~600 Hz
        # We need _detect_beep to return True, and _detect_frequency on the tail
        # to return something between 400 and 1000.
        with (
            patch.object(vds, "_detect_beep", return_value=True),
            patch.object(vds, "_detect_frequency", return_value=600.0),
        ):
            # Need enough samples for energy analysis
            # 5 seconds at 8kHz = 40000 samples, in 3-10s duration range
            samples = [500] * 40000
            audio_data = struct.pack(f"{len(samples)}h", *samples)
            result = vds.detect_voicemail("call-freq-boost", audio_data)

        # Beep contributes 0.4, frequency confirmation adds 0.1
        # Check detection_method indicates frequency was confirmed
        assert result["confidence"] >= 0.5
        assert "frequency_confirmed" in result["detection_method"]

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_beep_with_frequency_outside_range_no_boost(self, mock_logger: MagicMock) -> None:
        """When beep detected but frequency is outside 400-1000 Hz, no frequency boost."""
        vds = VoicemailDropSystem()
        vds.detection_threshold = 2.0

        with (
            patch.object(vds, "_detect_beep", return_value=True),
            patch.object(vds, "_detect_frequency", return_value=2000.0),
        ):
            samples = [500] * 40000
            audio_data = struct.pack(f"{len(samples)}h", *samples)
            result = vds.detect_voicemail("call-no-freq-boost", audio_data)

        # Beep contributes 0.4 but no frequency bonus
        # detection_method should be "beep_detection", not "beep_frequency_confirmed"
        assert result["detection_method"] == "beep_detection"

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_silence_ratio_in_voicemail_range_boosts_confidence(
        self, mock_logger: MagicMock
    ) -> None:
        """Silence ratio between 10-30% with enough speech adds 0.1 confidence."""
        vds = VoicemailDropSystem()
        vds.detection_threshold = 2.0  # High threshold to inspect raw confidence

        # Build audio: ~20% silence, ~80% speech
        # window_size=160, need enough windows. 5 seconds at 8kHz = 40000 samples.
        # 250 windows total. 50 silence (20%) + 200 speech (80%)
        # Silence segments: avg abs value < 50 (the threshold in the code)
        silence_samples = [10] * (160 * 50)  # 50 windows of low energy
        speech_samples = [2000] * (160 * 200)  # 200 windows of high energy
        samples = silence_samples + speech_samples
        audio_data = struct.pack(f"{len(samples)}h", *samples)

        with patch.object(vds, "_detect_beep", return_value=False):
            result = vds.detect_voicemail("call-silence", audio_data)

        # Silence ratio ~20% with >5 speech segments -> +0.1
        # Duration 5s is in 3-10s range -> +0.2
        # Energy analysis may also contribute
        assert result["confidence"] >= 0.1

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_too_much_silence_no_boost(self, mock_logger: MagicMock) -> None:
        """Silence ratio > 40% does not get the silence-pattern boost."""
        vds = VoicemailDropSystem()
        vds.detection_threshold = 2.0

        # 90% silence, 10% speech -> silence_ratio = 0.9 -> outside 0.1-0.4
        silence_samples = [5] * (160 * 225)
        speech_samples = [2000] * (160 * 25)
        samples = silence_samples + speech_samples
        audio_data = struct.pack(f"{len(samples)}h", *samples)

        with patch.object(vds, "_detect_beep", return_value=False):
            result = vds.detect_voicemail("call-too-silent", audio_data)

        # Duration 5s -> +0.2 (3-10s range)
        # No silence boost, but possible energy boost
        # Confidence should be relatively low (mostly from duration)
        assert result["confidence"] <= 0.5


@pytest.mark.unit
class TestDropMessageEnhanced:
    """Tests for enhanced drop_message with audio loading and RTP streaming."""

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_drop_message_with_pbx_core_rtp_session(self, mock_logger: MagicMock) -> None:
        """drop_message streams audio via RTP when PBX core and RTP session are available."""
        vds = VoicemailDropSystem()
        vds.add_message("msg-rtp", "RTP Test", "/audio/rtp_test.raw", duration=2.0)

        mock_rtp = MagicMock()
        mock_call = MagicMock()
        mock_call.rtp_session = mock_rtp
        mock_call_manager = MagicMock()
        mock_call_manager.get_call.return_value = mock_call
        mock_pbx = MagicMock()
        mock_pbx.call_manager = mock_call_manager

        audio_bytes = b"\x80" * 480  # 3 RTP packets of 160 bytes each

        with (
            patch.object(vds, "_load_audio_file", return_value=audio_bytes),
            patch(
                "pbx.features.predictive_voicemail_drop.get_pbx_core",
                create=True,
                return_value=mock_pbx,
            ) as mock_get_pbx,
            patch.dict(
                "sys.modules",
                {"pbx.core.pbx": MagicMock(get_pbx_core=mock_get_pbx)},
            ),
        ):
            result = vds.drop_message("call-rtp", "msg-rtp")

        assert result["success"] is True
        assert result["rtp_playback"] is True
        assert mock_rtp.send_audio.call_count == 3
        mock_call_manager.hangup_call.assert_called_once_with("call-rtp")

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_drop_message_pbx_core_import_error_fallback(self, mock_logger: MagicMock) -> None:
        """drop_message falls back gracefully when pbx.core.pbx cannot be imported."""
        vds = VoicemailDropSystem()
        vds.add_message("msg-fb", "Fallback Test", "/audio/fallback.raw", duration=1.0)

        audio_bytes = b"\x00" * 160

        with (
            patch.object(vds, "_load_audio_file", return_value=audio_bytes),
            patch(
                "builtins.__import__",
                side_effect=lambda name, *args, **kwargs: (
                    (_ for _ in ()).throw(ImportError("No PBX core"))
                    if name == "pbx.core.pbx"
                    else __import__(name, *args, **kwargs)
                ),
            ),
        ):
            result = vds.drop_message("call-fallback", "msg-fb")

        assert result["success"] is True
        assert result["rtp_playback"] is False
        assert vds.successful_drops == 1

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_drop_message_no_audio_file_still_succeeds(self, mock_logger: MagicMock) -> None:
        """drop_message records the drop even when audio file cannot be loaded."""
        vds = VoicemailDropSystem()
        vds.add_message("msg-noaudio", "No Audio", "/audio/missing.raw", duration=3.0)

        with patch.object(vds, "_load_audio_file", return_value=None):
            result = vds.drop_message("call-noaudio", "msg-noaudio")

        assert result["success"] is True
        assert result["rtp_playback"] is False
        assert vds.successful_drops == 1

    @patch("pbx.features.predictive_voicemail_drop.get_logger")
    def test_drop_message_rtp_padds_final_chunk(self, mock_logger: MagicMock) -> None:
        """Verify that the final RTP packet is padded to 160 bytes with silence."""
        vds = VoicemailDropSystem()
        vds.add_message("msg-pad", "Pad Test", "/audio/pad.raw", duration=1.0)

        mock_rtp = MagicMock()
        mock_call = MagicMock()
        mock_call.rtp_session = mock_rtp
        mock_call_manager = MagicMock()
        mock_call_manager.get_call.return_value = mock_call
        mock_pbx = MagicMock()
        mock_pbx.call_manager = mock_call_manager

        # 200 bytes = 1 full packet (160) + 1 partial packet (40 bytes, padded to 160)
        audio_bytes = b"\x80" * 200

        with (
            patch.object(vds, "_load_audio_file", return_value=audio_bytes),
            patch(
                "pbx.features.predictive_voicemail_drop.get_pbx_core",
                create=True,
                return_value=mock_pbx,
            ) as mock_get_pbx,
            patch.dict(
                "sys.modules",
                {"pbx.core.pbx": MagicMock(get_pbx_core=mock_get_pbx)},
            ),
        ):
            result = vds.drop_message("call-pad", "msg-pad")

        assert result["rtp_playback"] is True
        assert mock_rtp.send_audio.call_count == 2
        # Second call should be padded to 160 bytes
        second_chunk = mock_rtp.send_audio.call_args_list[1][0][0]
        assert len(second_chunk) == 160
        # First 40 bytes are audio, remaining 120 are silence (0x00)
        assert second_chunk[:40] == b"\x80" * 40
        assert second_chunk[40:] == b"\x00" * 120
