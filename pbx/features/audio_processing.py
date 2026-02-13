"""
Advanced Audio Processing
Noise suppression and echo cancellation using free libraries
"""


import numpy as np

from pbx.utils.logger import get_logger

# Try to import WebRTC Audio Processing (free)
try:
    pass

    WEBRTC_AUDIO_AVAILABLE = True
except ImportError:
    WEBRTC_AUDIO_AVAILABLE = False


class AudioProcessor:
    """Advanced audio processing for noise suppression and echo cancellation"""

    def __init__(self, config=None):
        """Initialize audio processor"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        audio_config = self.config.get("features", {}).get("audio_processing", {})
        self.noise_suppression_enabled = audio_config.get("noise_suppression", True)
        self.echo_cancellation_enabled = audio_config.get("echo_cancellation", True)
        self.auto_gain_enabled = audio_config.get("auto_gain", True)

        # Sample rate and frame size
        self.sample_rate = audio_config.get("sample_rate", 16000)
        self.frame_size = audio_config.get("frame_size", 160)  # 10ms at 16kHz

        # Statistics
        self.frames_processed = 0
        self.noise_level_history = []

        if WEBRTC_AUDIO_AVAILABLE:
            self.logger.info("Audio processor initialized with WebRTC Audio Processing")
            self.logger.info(f"  Noise suppression: {self.noise_suppression_enabled}")
            self.logger.info(f"  Echo cancellation: {self.echo_cancellation_enabled}")
            self.logger.info(f"  Auto gain control: {self.auto_gain_enabled}")
        else:
            self.logger.warning(
                "WebRTC Audio Processing not available. Install with: pip install webrtc-audio-processing"
            )

    def process_frame(self, audio_data: bytes, is_far_end: bool = False) -> bytes:
        """
        Process audio frame with noise suppression and echo cancellation

        Args:
            audio_data: Raw audio frame data (PCM 16-bit)
            is_far_end: True if this is far-end audio (for echo cancellation)

        Returns:
            Processed audio data
        """
        if not WEBRTC_AUDIO_AVAILABLE:
            return audio_data  # Pass through if library not available

        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Apply noise suppression (stub - would use WebRTC APM)
            if self.noise_suppression_enabled:
                audio_array = self._suppress_noise(audio_array)

            # Apply echo cancellation (stub - would use WebRTC APM)
            if self.echo_cancellation_enabled and not is_far_end:
                audio_array = self._cancel_echo(audio_array)

            # Apply auto gain control
            if self.auto_gain_enabled:
                audio_array = self._apply_agc(audio_array)

            self.frames_processed += 1

            # Convert back to bytes
            return audio_array.tobytes()

        except Exception as e:
            self.logger.error(f"Error processing audio frame: {e}")
            return audio_data

    def _suppress_noise(self, audio: np.ndarray) -> np.ndarray:
        """Apply noise suppression to audio signal"""
        # Stub implementation - in production would use WebRTC's NS module
        # For now, apply simple threshold-based noise gate
        threshold = np.mean(np.abs(audio)) * 0.1
        mask = np.abs(audio) > threshold
        return audio * mask

    def _cancel_echo(self, audio: np.ndarray) -> np.ndarray:
        """Apply echo cancellation to audio signal"""
        # Stub implementation - in production would use WebRTC's AEC module
        # This requires both near-end and far-end audio streams
        return audio

    def _apply_agc(self, audio: np.ndarray) -> np.ndarray:
        """Apply automatic gain control"""
        # Stub implementation - in production would use WebRTC's AGC module
        # Simple normalization for now
        if len(audio) == 0:
            return audio

        target_level = 0.7  # Target RMS level (0-1)
        current_rms = np.sqrt(np.mean(audio.astype(float) ** 2)) / 32768.0

        if current_rms > 0:
            gain = target_level / current_rms
            gain = min(gain, 10.0)  # Limit maximum gain
            # Prevent overflow by clamping to int16 range
            audio = np.clip(audio * gain, -32768, 32767).astype(np.int16)

        return audio

    def estimate_noise_level(self, audio_data: bytes) -> float:
        """
        Estimate current noise level in audio

        Args:
            audio_data: Raw audio data

        Returns:
            Noise level (0.0 to 1.0)
        """
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            # Calculate RMS as noise estimate
            rms = np.sqrt(np.mean(audio_array.astype(float) ** 2)) / 32768.0

            # Store in history
            self.noise_level_history.append(rms)
            if len(self.noise_level_history) > 100:
                self.noise_level_history.pop(0)

            return float(rms)
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error estimating noise level: {e}")
            return 0.0

    def get_average_noise_level(self) -> float:
        """Get average noise level over recent history"""
        if not self.noise_level_history:
            return 0.0
        return sum(self.noise_level_history) / len(self.noise_level_history)

    def reset_statistics(self):
        """Reset processing statistics"""
        self.frames_processed = 0
        self.noise_level_history = []

    def get_statistics(self) -> dict:
        """Get audio processing statistics"""
        return {
            "frames_processed": self.frames_processed,
            "average_noise_level": self.get_average_noise_level(),
            "noise_suppression_enabled": self.noise_suppression_enabled,
            "echo_cancellation_enabled": self.echo_cancellation_enabled,
            "auto_gain_enabled": self.auto_gain_enabled,
            "webrtc_available": WEBRTC_AUDIO_AVAILABLE,
        }
