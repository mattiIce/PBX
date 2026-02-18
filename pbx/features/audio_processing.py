"""
Advanced Audio Processing
Noise suppression and echo cancellation using free libraries
"""

from typing import Any

import numpy as np

from pbx.utils.logger import get_logger

# Try to import WebRTC Audio Processing (free)
try:
    WEBRTC_AUDIO_AVAILABLE = True
except ImportError:
    WEBRTC_AUDIO_AVAILABLE = False


class AudioProcessor:
    """Advanced audio processing for noise suppression and echo cancellation"""

    def __init__(self, config: Any | None = None) -> None:
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

            # Apply spectral subtraction noise suppression
            if self.noise_suppression_enabled:
                audio_array = self._suppress_noise(audio_array)

            # Apply NLMS adaptive echo cancellation
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
        """
        Apply spectral subtraction noise suppression.

        Uses a frequency-domain approach: estimates the noise spectrum from
        low-energy frames and subtracts it from the signal spectrum.
        """
        frame_len = len(audio)
        if frame_len == 0:
            return audio

        # Compute FFT
        spectrum = np.fft.rfft(audio.astype(np.float64))
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)

        # Estimate noise floor from running average
        current_rms = np.sqrt(np.mean(audio.astype(np.float64) ** 2))

        if not hasattr(self, "_noise_spectrum"):
            self._noise_spectrum = magnitude.copy()
            self._noise_frame_count = 0

        # Update noise estimate during silence (low energy frames)
        silence_threshold = 500  # Threshold for silence detection
        if current_rms < silence_threshold:
            alpha = 0.95  # Smoothing factor for noise estimate
            self._noise_spectrum = alpha * self._noise_spectrum + (1 - alpha) * magnitude
            self._noise_frame_count += 1

        # Spectral subtraction with over-subtraction factor
        over_subtraction = 2.0
        spectral_floor = 0.01  # Prevent musical noise

        cleaned_magnitude = magnitude - over_subtraction * self._noise_spectrum
        cleaned_magnitude = np.maximum(cleaned_magnitude, spectral_floor * magnitude)

        # Reconstruct signal
        cleaned_spectrum = cleaned_magnitude * np.exp(1j * phase)
        result = np.fft.irfft(cleaned_spectrum, n=frame_len)
        return np.clip(result, -32768, 32767).astype(np.int16)

    def _cancel_echo(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply echo cancellation using NLMS (Normalized Least Mean Squares)
        adaptive filter.

        Maintains an adaptive filter that models the echo path and subtracts
        the estimated echo from the near-end signal.
        """
        frame_len = len(audio)
        if frame_len == 0:
            return audio

        # Initialize adaptive filter state
        filter_length = 128  # Adaptive filter taps
        if not hasattr(self, "_echo_filter"):
            self._echo_filter = np.zeros(filter_length)
            self._far_end_buffer = np.zeros(filter_length)
            self._echo_mu = 0.01  # Step size for NLMS

        # If we have far-end reference audio, use it
        if hasattr(self, "_last_far_end") and self._last_far_end is not None:
            far_end = self._last_far_end.astype(np.float64)

            # Ensure matching lengths
            process_len = min(frame_len, len(far_end))
            near_end = audio[:process_len].astype(np.float64)

            output = np.zeros(process_len)
            for i in range(process_len):
                # Shift far-end buffer
                self._far_end_buffer = np.roll(self._far_end_buffer, 1)
                self._far_end_buffer[0] = far_end[i] if i < len(far_end) else 0

                # Estimate echo
                echo_estimate = np.dot(self._echo_filter, self._far_end_buffer)

                # Subtract estimated echo
                error = near_end[i] - echo_estimate
                output[i] = error

                # Update filter (NLMS)
                power = np.dot(self._far_end_buffer, self._far_end_buffer) + 1e-6
                self._echo_filter += self._echo_mu * error * self._far_end_buffer / power

            result = np.zeros(frame_len)
            result[:process_len] = output
            if process_len < frame_len:
                result[process_len:] = audio[process_len:]
            return np.clip(result, -32768, 32767).astype(np.int16)

        return audio

    def set_far_end_reference(self, far_end_audio: bytes) -> None:
        """
        Provide far-end audio reference for echo cancellation.

        Args:
            far_end_audio: Raw PCM 16-bit audio from the far end
        """
        self._last_far_end = np.frombuffer(far_end_audio, dtype=np.int16)

    def _apply_agc(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply automatic gain control with attack/release dynamics.

        Uses a digital compressor/expander with configurable target level,
        attack time, and release time to smoothly normalize audio levels.
        """
        if len(audio) == 0:
            return audio

        # AGC parameters
        target_level_db = -20.0  # Target output level in dBFS
        attack_time = 0.005  # Attack time in seconds (fast)
        release_time = 0.05  # Release time in seconds (slower)
        max_gain_db = 30.0  # Maximum gain in dB

        # Initialize state
        if not hasattr(self, "_agc_gain_db"):
            self._agc_gain_db = 0.0

        # Compute frame level in dB
        audio_float = audio.astype(np.float64)
        rms = np.sqrt(np.mean(audio_float**2))
        if rms < 1.0:
            return audio  # Signal too quiet, pass through

        level_db = 20.0 * np.log10(rms / 32768.0 + 1e-10)

        # Compute desired gain
        desired_gain_db = target_level_db - level_db
        desired_gain_db = np.clip(desired_gain_db, -20.0, max_gain_db)

        # Smooth gain changes (attack/release)
        samples_per_sec = self.sample_rate
        frame_duration = len(audio) / samples_per_sec

        if desired_gain_db > self._agc_gain_db:
            # Increasing gain (release)
            coeff = 1.0 - np.exp(-frame_duration / release_time)
        else:
            # Decreasing gain (attack)
            coeff = 1.0 - np.exp(-frame_duration / attack_time)

        self._agc_gain_db += coeff * (desired_gain_db - self._agc_gain_db)

        # Apply gain
        gain_linear = 10.0 ** (self._agc_gain_db / 20.0)
        audio_gained = audio_float * gain_linear
        return np.clip(audio_gained, -32768, 32767).astype(np.int16)

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

    def reset_statistics(self) -> None:
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
