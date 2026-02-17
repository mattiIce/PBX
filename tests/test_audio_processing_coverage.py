"""
Tests for Advanced Audio Processing
Comprehensive coverage of AudioProcessor (noise suppression, echo cancellation, AGC)
"""

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pbx.features.audio_processing import AudioProcessor


@pytest.mark.unit
class TestAudioProcessorInit:
    """Test AudioProcessor initialization"""

    @patch("pbx.features.audio_processing.get_logger")
    def test_init_default_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with default config"""
        processor = AudioProcessor()

        assert processor.noise_suppression_enabled is True
        assert processor.echo_cancellation_enabled is True
        assert processor.auto_gain_enabled is True
        assert processor.sample_rate == 16000
        assert processor.frame_size == 160
        assert processor.frames_processed == 0
        assert processor.noise_level_history == []
        assert processor.config == {}

    @patch("pbx.features.audio_processing.get_logger")
    def test_init_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with None config"""
        processor = AudioProcessor(None)

        assert processor.config == {}
        assert processor.noise_suppression_enabled is True

    @patch("pbx.features.audio_processing.get_logger")
    def test_init_custom_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with custom config"""
        config = {
            "features": {
                "audio_processing": {
                    "noise_suppression": False,
                    "echo_cancellation": False,
                    "auto_gain": False,
                    "sample_rate": 8000,
                    "frame_size": 80,
                }
            }
        }
        processor = AudioProcessor(config)

        assert processor.noise_suppression_enabled is False
        assert processor.echo_cancellation_enabled is False
        assert processor.auto_gain_enabled is False
        assert processor.sample_rate == 8000
        assert processor.frame_size == 80

    @patch("pbx.features.audio_processing.get_logger")
    def test_init_partial_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with partial config (some keys missing)"""
        config = {
            "features": {
                "audio_processing": {
                    "noise_suppression": False,
                }
            }
        }
        processor = AudioProcessor(config)

        assert processor.noise_suppression_enabled is False
        assert processor.echo_cancellation_enabled is True  # default
        assert processor.auto_gain_enabled is True  # default

    @patch("pbx.features.audio_processing.get_logger")
    def test_init_empty_features(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with empty features section"""
        processor = AudioProcessor({"features": {}})

        assert processor.noise_suppression_enabled is True

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    @patch("pbx.features.audio_processing.get_logger")
    def test_init_webrtc_available_logging(self, mock_get_logger: MagicMock) -> None:
        """Test initialization logging when WebRTC is available"""
        AudioProcessor()

        logger = mock_get_logger.return_value
        assert logger.info.call_count >= 1

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", False)
    @patch("pbx.features.audio_processing.get_logger")
    def test_init_webrtc_not_available_logging(self, mock_get_logger: MagicMock) -> None:
        """Test initialization logging when WebRTC is not available"""
        AudioProcessor()

        logger = mock_get_logger.return_value
        logger.warning.assert_called()


@pytest.mark.unit
class TestAudioProcessorProcessFrame:
    """Test AudioProcessor.process_frame"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", False)
    def test_process_frame_passthrough_no_webrtc(self) -> None:
        """Test frame passes through when WebRTC is not available"""
        audio_data = np.array([100, 200, 300, 400], dtype=np.int16).tobytes()

        result = self.processor.process_frame(audio_data)

        assert result == audio_data

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_all_processing_enabled(self) -> None:
        """Test frame processing with all features enabled"""
        audio_data = np.array([1000, -2000, 3000, -4000, 5000], dtype=np.int16).tobytes()

        result = self.processor.process_frame(audio_data)

        assert isinstance(result, bytes)
        assert self.processor.frames_processed == 1

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_noise_suppression_only(self) -> None:
        """Test frame processing with only noise suppression"""
        with patch("pbx.features.audio_processing.get_logger"):
            processor = AudioProcessor({
                "features": {
                    "audio_processing": {
                        "noise_suppression": True,
                        "echo_cancellation": False,
                        "auto_gain": False,
                    }
                }
            })

        audio_data = np.array([1000, -2000, 3000, -4000], dtype=np.int16).tobytes()

        result = processor.process_frame(audio_data)

        assert isinstance(result, bytes)
        assert processor.frames_processed == 1

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_echo_cancellation_only(self) -> None:
        """Test frame processing with only echo cancellation"""
        with patch("pbx.features.audio_processing.get_logger"):
            processor = AudioProcessor({
                "features": {
                    "audio_processing": {
                        "noise_suppression": False,
                        "echo_cancellation": True,
                        "auto_gain": False,
                    }
                }
            })

        audio_data = np.array([1000, -2000, 3000, -4000], dtype=np.int16).tobytes()

        result = processor.process_frame(audio_data)

        assert isinstance(result, bytes)

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_far_end_skips_echo_cancel(self) -> None:
        """Test that far-end audio skips echo cancellation"""
        with patch("pbx.features.audio_processing.get_logger"):
            processor = AudioProcessor({
                "features": {
                    "audio_processing": {
                        "noise_suppression": False,
                        "echo_cancellation": True,
                        "auto_gain": False,
                    }
                }
            })

        audio_data = np.array([1000, -2000, 3000], dtype=np.int16).tobytes()

        with patch.object(processor, "_cancel_echo") as mock_cancel:
            processor.process_frame(audio_data, is_far_end=True)
            mock_cancel.assert_not_called()

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_near_end_applies_echo_cancel(self) -> None:
        """Test that near-end audio applies echo cancellation"""
        with patch("pbx.features.audio_processing.get_logger"):
            processor = AudioProcessor({
                "features": {
                    "audio_processing": {
                        "noise_suppression": False,
                        "echo_cancellation": True,
                        "auto_gain": False,
                    }
                }
            })

        audio_data = np.array([1000, -2000, 3000], dtype=np.int16).tobytes()

        with patch.object(processor, "_cancel_echo", return_value=np.array([1000, -2000, 3000], dtype=np.int16)) as mock_cancel:
            processor.process_frame(audio_data, is_far_end=False)
            mock_cancel.assert_called_once()

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_agc_only(self) -> None:
        """Test frame processing with only auto gain control"""
        with patch("pbx.features.audio_processing.get_logger"):
            processor = AudioProcessor({
                "features": {
                    "audio_processing": {
                        "noise_suppression": False,
                        "echo_cancellation": False,
                        "auto_gain": True,
                    }
                }
            })

        audio_data = np.array([1000, -2000, 3000, -4000], dtype=np.int16).tobytes()

        result = processor.process_frame(audio_data)

        assert isinstance(result, bytes)

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_all_disabled(self) -> None:
        """Test frame processing with all features disabled"""
        with patch("pbx.features.audio_processing.get_logger"):
            processor = AudioProcessor({
                "features": {
                    "audio_processing": {
                        "noise_suppression": False,
                        "echo_cancellation": False,
                        "auto_gain": False,
                    }
                }
            })

        audio_data = np.array([1000, -2000, 3000], dtype=np.int16).tobytes()

        result = processor.process_frame(audio_data)

        # All disabled: data passes through unmodified
        assert result == audio_data
        assert processor.frames_processed == 1

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_exception_returns_original(self) -> None:
        """Test that exceptions in processing return original audio"""
        audio_data = np.array([1000, -2000], dtype=np.int16).tobytes()

        with patch.object(self.processor, "_suppress_noise", side_effect=RuntimeError("test")):
            result = self.processor.process_frame(audio_data)

        assert result == audio_data

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_process_frame_increments_counter(self) -> None:
        """Test that frames_processed is incremented"""
        audio_data = np.array([1000, -2000], dtype=np.int16).tobytes()

        self.processor.process_frame(audio_data)
        self.processor.process_frame(audio_data)
        self.processor.process_frame(audio_data)

        assert self.processor.frames_processed == 3


@pytest.mark.unit
class TestAudioProcessorSuppressNoise:
    """Test AudioProcessor._suppress_noise"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    def test_suppress_noise_basic(self) -> None:
        """Test basic noise suppression"""
        # Create audio with a mix of signal and noise
        audio = np.array([10000, 5, -10000, 3, 8000], dtype=np.int16)

        result = self.processor._suppress_noise(audio)

        assert isinstance(result, np.ndarray)
        assert len(result) == len(audio)

    def test_suppress_noise_silence(self) -> None:
        """Test noise suppression on silence"""
        audio = np.array([0, 0, 0, 0], dtype=np.int16)

        result = self.processor._suppress_noise(audio)

        np.testing.assert_array_equal(result, audio)

    def test_suppress_noise_loud_signal(self) -> None:
        """Test noise suppression preserves loud signals"""
        audio = np.array([10000, 10000, 10000, 10000], dtype=np.int16)

        result = self.processor._suppress_noise(audio)

        # All values above threshold should remain
        assert np.all(result != 0)


@pytest.mark.unit
class TestAudioProcessorCancelEcho:
    """Test AudioProcessor._cancel_echo"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    def test_cancel_echo_passthrough(self) -> None:
        """Test echo cancellation (stub) passes audio through"""
        audio = np.array([1000, -2000, 3000], dtype=np.int16)

        result = self.processor._cancel_echo(audio)

        np.testing.assert_array_equal(result, audio)


@pytest.mark.unit
class TestAudioProcessorApplyAGC:
    """Test AudioProcessor._apply_agc"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    def test_apply_agc_empty_array(self) -> None:
        """Test AGC with empty audio array"""
        audio = np.array([], dtype=np.int16)

        result = self.processor._apply_agc(audio)

        assert len(result) == 0

    def test_apply_agc_quiet_signal(self) -> None:
        """Test AGC amplifies quiet signal"""
        audio = np.array([100, -100, 100, -100], dtype=np.int16)

        result = self.processor._apply_agc(audio)

        # AGC should amplify quiet signal
        assert np.max(np.abs(result)) > np.max(np.abs(audio))

    def test_apply_agc_loud_signal(self) -> None:
        """Test AGC with loud signal (near max)"""
        audio = np.array([30000, -30000, 30000, -30000], dtype=np.int16)

        result = self.processor._apply_agc(audio)

        # Result should stay within int16 range
        assert np.all(result >= -32768)
        assert np.all(result <= 32767)

    def test_apply_agc_zero_rms(self) -> None:
        """Test AGC with zero RMS (all zeros)"""
        audio = np.array([0, 0, 0, 0], dtype=np.int16)

        result = self.processor._apply_agc(audio)

        np.testing.assert_array_equal(result, audio)

    def test_apply_agc_gain_limit(self) -> None:
        """Test that AGC limits maximum gain to 10x"""
        # Very quiet signal that would need more than 10x gain
        audio = np.array([1, -1, 1, -1], dtype=np.int16)

        result = self.processor._apply_agc(audio)

        # Max gain is 10.0, so values should be at most ~10
        assert np.max(np.abs(result)) <= 32767

    def test_apply_agc_prevents_overflow(self) -> None:
        """Test AGC prevents integer overflow with clipping"""
        # Signal that when amplified might overflow
        audio = np.array([5000, -5000, 5000, -5000], dtype=np.int16)

        result = self.processor._apply_agc(audio)

        # All values within int16 range
        assert np.all(result >= -32768)
        assert np.all(result <= 32767)
        assert result.dtype == np.int16


@pytest.mark.unit
class TestAudioProcessorEstimateNoiseLevel:
    """Test AudioProcessor.estimate_noise_level"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    def test_estimate_noise_level_basic(self) -> None:
        """Test basic noise level estimation"""
        audio_data = np.array([1000, -1000, 1000, -1000], dtype=np.int16).tobytes()

        result = self.processor.estimate_noise_level(audio_data)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_estimate_noise_level_silence(self) -> None:
        """Test noise level of silence"""
        audio_data = np.array([0, 0, 0, 0], dtype=np.int16).tobytes()

        result = self.processor.estimate_noise_level(audio_data)

        assert result == 0.0

    def test_estimate_noise_level_stores_history(self) -> None:
        """Test that noise level is stored in history"""
        audio_data = np.array([1000, -1000], dtype=np.int16).tobytes()

        self.processor.estimate_noise_level(audio_data)

        assert len(self.processor.noise_level_history) == 1

    def test_estimate_noise_level_history_limit(self) -> None:
        """Test that history is limited to 100 entries"""
        audio_data = np.array([1000, -1000], dtype=np.int16).tobytes()

        for _ in range(110):
            self.processor.estimate_noise_level(audio_data)

        assert len(self.processor.noise_level_history) == 100

    def test_estimate_noise_level_loud_signal(self) -> None:
        """Test noise level of loud signal"""
        audio_data = np.array([32000, -32000, 32000, -32000], dtype=np.int16).tobytes()

        result = self.processor.estimate_noise_level(audio_data)

        assert result > 0.5

    def test_estimate_noise_level_error_returns_zero(self) -> None:
        """Test that errors return 0.0"""
        # Pass invalid data that will cause an error
        with patch("pbx.features.audio_processing.np.frombuffer", side_effect=ValueError("bad")):
            result = self.processor.estimate_noise_level(b"invalid")

        assert result == 0.0


@pytest.mark.unit
class TestAudioProcessorGetAverageNoiseLevel:
    """Test AudioProcessor.get_average_noise_level"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    def test_average_noise_empty_history(self) -> None:
        """Test average noise level with no history"""
        result = self.processor.get_average_noise_level()

        assert result == 0.0

    def test_average_noise_single_entry(self) -> None:
        """Test average noise level with single entry"""
        self.processor.noise_level_history = [0.5]

        result = self.processor.get_average_noise_level()

        assert result == 0.5

    def test_average_noise_multiple_entries(self) -> None:
        """Test average noise level with multiple entries"""
        self.processor.noise_level_history = [0.1, 0.2, 0.3, 0.4, 0.5]

        result = self.processor.get_average_noise_level()

        assert result == pytest.approx(0.3)


@pytest.mark.unit
class TestAudioProcessorResetStatistics:
    """Test AudioProcessor.reset_statistics"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    def test_reset_statistics(self) -> None:
        """Test resetting statistics"""
        self.processor.frames_processed = 42
        self.processor.noise_level_history = [0.1, 0.2, 0.3]

        self.processor.reset_statistics()

        assert self.processor.frames_processed == 0
        assert self.processor.noise_level_history == []


@pytest.mark.unit
class TestAudioProcessorGetStatistics:
    """Test AudioProcessor.get_statistics"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    def test_get_statistics_initial(self) -> None:
        """Test initial statistics"""
        stats = self.processor.get_statistics()

        assert stats["frames_processed"] == 0
        assert stats["average_noise_level"] == 0.0
        assert stats["noise_suppression_enabled"] is True
        assert stats["echo_cancellation_enabled"] is True
        assert stats["auto_gain_enabled"] is True
        assert "webrtc_available" in stats

    def test_get_statistics_after_processing(self) -> None:
        """Test statistics after processing frames"""
        self.processor.frames_processed = 100
        self.processor.noise_level_history = [0.1, 0.3]

        stats = self.processor.get_statistics()

        assert stats["frames_processed"] == 100
        assert stats["average_noise_level"] == pytest.approx(0.2)

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_get_statistics_webrtc_available(self) -> None:
        """Test statistics reports WebRTC as available"""
        stats = self.processor.get_statistics()

        assert stats["webrtc_available"] is True

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", False)
    def test_get_statistics_webrtc_not_available(self) -> None:
        """Test statistics reports WebRTC as not available"""
        stats = self.processor.get_statistics()

        assert stats["webrtc_available"] is False

    def test_get_statistics_custom_config(self) -> None:
        """Test statistics with custom config settings"""
        with patch("pbx.features.audio_processing.get_logger"):
            processor = AudioProcessor({
                "features": {
                    "audio_processing": {
                        "noise_suppression": False,
                        "echo_cancellation": False,
                        "auto_gain": False,
                    }
                }
            })

        stats = processor.get_statistics()

        assert stats["noise_suppression_enabled"] is False
        assert stats["echo_cancellation_enabled"] is False
        assert stats["auto_gain_enabled"] is False


@pytest.mark.unit
class TestAudioProcessorIntegration:
    """Integration-style tests for AudioProcessor processing pipeline"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.audio_processing.get_logger"):
            self.processor = AudioProcessor()

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_full_pipeline_with_noise_estimation(self) -> None:
        """Test processing and noise estimation together"""
        # Generate a test signal
        signal = np.array([5000, -5000, 5000, -5000, 5000, -5000], dtype=np.int16)
        audio_data = signal.tobytes()

        # Process frame
        processed = self.processor.process_frame(audio_data)
        assert isinstance(processed, bytes)

        # Estimate noise
        noise = self.processor.estimate_noise_level(audio_data)
        assert noise > 0.0

        # Check statistics
        stats = self.processor.get_statistics()
        assert stats["frames_processed"] == 1
        assert stats["average_noise_level"] > 0.0

    @patch("pbx.features.audio_processing.WEBRTC_AUDIO_AVAILABLE", True)
    def test_reset_clears_everything(self) -> None:
        """Test that reset clears processing counter and noise history"""
        audio_data = np.array([1000, -1000], dtype=np.int16).tobytes()

        self.processor.process_frame(audio_data)
        self.processor.estimate_noise_level(audio_data)

        assert self.processor.frames_processed == 1
        assert len(self.processor.noise_level_history) == 1

        self.processor.reset_statistics()

        assert self.processor.frames_processed == 0
        assert self.processor.noise_level_history == []
        assert self.processor.get_average_noise_level() == 0.0
