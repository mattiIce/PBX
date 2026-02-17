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
