"""
Call recording system
Records audio from calls for compliance, quality assurance, and training
"""

import wave
from datetime import UTC, datetime
from pathlib import Path

from pbx.utils.logger import get_logger
from typing import Any


class CallRecording:
    """Manages recording for a single call"""

    def __init__(self, call_id: str, recording_path: str ="recordings") -> None:
        """
        Initialize call recording

        Args:
            call_id: Call identifier
            recording_path: Path to store recordings
        """
        self.call_id = call_id
        self.recording_path = recording_path
        self.logger = get_logger()
        self.recording = False
        self.file_path = None
        self.start_time = None
        self.audio_buffer = []

        Path(recording_path).mkdir(parents=True, exist_ok=True)

    def start(self, from_ext: str, to_ext: str) -> Path | None:
        """
        Start recording

        Args:
            from_ext: Calling extension
            to_ext: Called extension

        Returns:
            File path of recording
        """
        if self.recording:
            return None

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{from_ext}_to_{to_ext}_{timestamp}.wav"
        self.file_path = Path(self.recording_path) / filename

        self.recording = True
        self.start_time = datetime.now(UTC)

        self.logger.info(f"Started recording call {self.call_id} to {self.file_path}")
        return self.file_path

    def add_audio(self, audio_data: bytes) -> None:
        """
        Add audio data to recording

        Args:
            audio_data: Audio bytes
        """
        if self.recording:
            self.audio_buffer.append(audio_data)

    def stop(self) -> Path | None:
        """Stop recording and save file"""
        if not self.recording:
            return None

        self.recording = False

        # Save audio buffer to WAV file
        if self.audio_buffer and self.file_path:
            try:
                with wave.open(self.file_path, "wb") as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(8000)  # 8kHz for telephony

                    for audio_data in self.audio_buffer:
                        wav_file.writeframes(audio_data)

                self.logger.info(f"Saved recording to {self.file_path}")
                return self.file_path
            except OSError as e:
                self.logger.error(f"Error saving recording: {e}")
                return None

        return None

    def get_duration(self) -> float:
        """Get recording duration in seconds"""
        if self.start_time:
            end_time = datetime.now(UTC)
            return (end_time - self.start_time).total_seconds()
        return 0


class CallRecordingSystem:
    """Manages call recording for all calls"""

    def __init__(self, recording_path: str ="recordings", auto_record: bool =False) -> None:
        """
        Initialize call recording system

        Args:
            recording_path: Path to store recordings
            auto_record: Automatically record all calls
        """
        self.recording_path = recording_path
        self.auto_record = auto_record
        self.active_recordings = {}
        self.recording_metadata = []
        self.logger = get_logger()

        Path(recording_path).mkdir(parents=True, exist_ok=True)

    def start_recording(self, call_id: str, from_ext: str, to_ext: str) -> bool:
        """
        Start recording a call

        Args:
            call_id: Call identifier
            from_ext: Calling extension
            to_ext: Called extension

        Returns:
            True if recording started
        """
        if call_id in self.active_recordings:
            return False

        recording = CallRecording(call_id, self.recording_path)
        file_path = recording.start(from_ext, to_ext)

        if file_path:
            self.active_recordings[call_id] = recording
            return True
        return False

    def stop_recording(self, call_id: str) -> Any | None:
        """
        Stop recording a call

        Args:
            call_id: Call identifier

        Returns:
            Recording file path or None
        """
        recording = self.active_recordings.get(call_id)
        if recording:
            file_path = recording.stop()

            # Save metadata
            if file_path:
                metadata = {
                    "call_id": call_id,
                    "file_path": file_path,
                    "duration": recording.get_duration(),
                    "timestamp": recording.start_time,
                }
                self.recording_metadata.append(metadata)

            del self.active_recordings[call_id]
            return file_path
        return None

    def add_audio(self, call_id: str, audio_data: bytes) -> None:
        """
        Add audio data to recording

        Args:
            call_id: Call identifier
            audio_data: Audio bytes
        """
        recording = self.active_recordings.get(call_id)
        if recording:
            recording.add_audio(audio_data)

    def is_recording(self, call_id: str) -> bool:
        """Check if call is being recorded"""
        return call_id in self.active_recordings

    def get_recordings(self, limit: int =100) -> list:
        """
        Get recording metadata

        Args:
            limit: Maximum number of recordings to return

        Returns:
            list of recording metadata
        """
        return self.recording_metadata[-limit:]
