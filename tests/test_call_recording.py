"""Unit tests for pbx.features.call_recording — CallRecording and CallRecordingSystem."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("pbx.features.call_recording.get_logger", return_value=MagicMock())
class TestCallRecording:
    """Tests for CallRecording."""

    def test_recording_start(self, _mock_logger, tmp_path):
        """start() returns a Path and sets recording=True with correct filename."""
        from pbx.features.call_recording import CallRecording

        rec = CallRecording("call1", recording_path=str(tmp_path))
        result = rec.start("1001", "1002")

        assert isinstance(result, Path)
        assert rec.recording is True
        assert "1001_to_1002_" in result.name
        assert result.name.endswith(".wav")

    def test_recording_start_already_recording(self, _mock_logger, tmp_path):
        """Second start() returns None when already recording."""
        from pbx.features.call_recording import CallRecording

        rec = CallRecording("call1", recording_path=str(tmp_path))
        rec.start("1001", "1002")
        result = rec.start("1001", "1003")

        assert result is None

    def test_recording_add_audio(self, _mock_logger, tmp_path):
        """add_audio appends to buffer only while recording."""
        from pbx.features.call_recording import CallRecording

        rec = CallRecording("call1", recording_path=str(tmp_path))

        # Not recording yet — buffer stays empty
        rec.add_audio(b"\x00" * 160)
        assert len(rec.audio_buffer) == 0

        rec.start("1001", "1002")
        rec.add_audio(b"\x00" * 160)
        rec.add_audio(b"\x00" * 160)
        assert len(rec.audio_buffer) == 2

    def test_recording_stop_saves_wav(self, _mock_logger, tmp_path):
        """stop() writes a valid WAV file and resets recording state."""
        from pbx.features.call_recording import CallRecording

        rec = CallRecording("call1", recording_path=str(tmp_path))
        rec.start("1001", "1002")

        # 16-bit PCM silence frames (must be even length for 16-bit samples)
        rec.add_audio(b"\x00" * 320)
        rec.add_audio(b"\x00" * 320)

        # wave.open requires str, not Path, on Python <3.14
        rec.file_path = str(rec.file_path)

        result = rec.stop()

        assert result is not None
        assert Path(result).exists()
        assert rec.recording is False

        content = Path(result).read_bytes()
        assert content[:4] == b"RIFF"

    def test_recording_stop_no_recording(self, _mock_logger, tmp_path):
        """stop() without start() returns None."""
        from pbx.features.call_recording import CallRecording

        rec = CallRecording("call1", recording_path=str(tmp_path))
        assert rec.stop() is None


@pytest.mark.unit
@patch("pbx.features.call_recording.get_logger", return_value=MagicMock())
class TestCallRecordingSystem:
    """Tests for CallRecordingSystem."""

    def test_system_start_stop(self, _mock_logger, tmp_path):
        """start_recording/stop_recording lifecycle."""
        from pbx.features.call_recording import CallRecordingSystem

        system = CallRecordingSystem(recording_path=str(tmp_path))

        assert system.start_recording("call1", "1001", "1002") is True
        assert system.is_recording("call1") is True

        # Add audio so the WAV file gets written
        system.add_audio("call1", b"\x00" * 320)

        # wave.open requires str, not Path, on Python <3.14
        recording = system.active_recordings["call1"]
        recording.file_path = str(recording.file_path)

        result = system.stop_recording("call1")

        assert result is not None
        assert system.is_recording("call1") is False

    def test_system_prevents_duplicate(self, _mock_logger, tmp_path):
        """Second start_recording for same call_id returns False."""
        from pbx.features.call_recording import CallRecordingSystem

        system = CallRecordingSystem(recording_path=str(tmp_path))
        assert system.start_recording("call1", "1001", "1002") is True
        assert system.start_recording("call1", "1001", "1002") is False
