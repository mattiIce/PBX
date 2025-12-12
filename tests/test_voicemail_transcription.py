"""
Tests for voicemail transcription functionality
"""
import os
import struct
import sys
import tempfile
import unittest
import wave
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.voicemail_transcription import VoicemailTranscriptionService

# Mock the optional dependencies before importing the module
sys.modules['vosk'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.speech'] = MagicMock()


class TestVoicemailTranscription(unittest.TestCase):
    """Test voicemail transcription service"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

        # Create test audio file (simple WAV)
        self.test_audio_path = os.path.join(
            self.temp_dir, "test_voicemail.wav")
        self._create_test_wav(self.test_audio_path)

    def tearDown(self):
        """Clean up test fixtures"""
        # Remove test files
        if os.path.exists(self.test_audio_path):
            os.remove(self.test_audio_path)
        os.rmdir(self.temp_dir)

    def _create_test_wav(self, filepath, duration=1.0, sample_rate=8000):
        """
        Create a test WAV file with a simple varying amplitude wave

        Args:
            filepath: Path to save WAV file
            duration: Duration in seconds
            sample_rate: Sample rate in Hz
        """
        num_samples = int(duration * sample_rate)

        # Generate samples with varying amplitude
        samples = []
        for i in range(num_samples):
            # Simple varying amplitude
            value = int(32767.0 * 0.5 * (1 + (i % 100) / 100))
            samples.append(struct.pack('<h', value))

        # Write WAV file
        with wave.open(filepath, 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(samples))

    def test_transcription_service_disabled(self):
        """Test transcription service when disabled"""
        config = Mock()
        config.get = Mock(
            return_value={
                'voicemail_transcription': {
                    'enabled': False}})

        service = VoicemailTranscriptionService(config)

        self.assertFalse(service.enabled)

        result = service.transcribe(self.test_audio_path)

        self.assertFalse(result['success'])
        self.assertIsNone(result['text'])
        self.assertEqual(result['error'], 'Transcription service is disabled')

    def test_transcription_file_not_found(self):
        """Test transcription with non-existent file"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'vosk',
                'vosk_model_path': 'models/test'
            }
        })

        service = VoicemailTranscriptionService(config)

        result = service.transcribe('/nonexistent/file.wav')

        self.assertFalse(result['success'])
        self.assertIn('Audio file not found', result['error'])

    def test_transcription_unsupported_provider(self):
        """Test transcription with unsupported provider"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'unsupported_provider',
                'api_key': 'test-key'
            }
        })

        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)

        self.assertFalse(result['success'])
        self.assertIn('Unsupported transcription provider', result['error'])

    @patch('pbx.features.voicemail_transcription.GOOGLE_SPEECH_AVAILABLE', True)
    @patch('pbx.features.voicemail_transcription.speech')
    def test_transcription_google_success(self, mock_speech):
        """Test successful Google Cloud Speech-to-Text transcription"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'google',
                'api_key': None  # Google uses GOOGLE_APPLICATION_CREDENTIALS
            }
        })

        # Mock Google Speech client
        mock_client = MagicMock()
        mock_speech.SpeechClient.return_value = mock_client

        # Mock configuration classes
        mock_speech.RecognitionAudio = MagicMock()
        mock_speech.RecognitionConfig = MagicMock()
        mock_speech.RecognitionConfig.AudioEncoding = MagicMock()

        # Mock recognition response
        mock_alternative = MagicMock()
        mock_alternative.transcript = 'This is a Google transcription test.'
        mock_alternative.confidence = 0.95

        mock_result = MagicMock()
        mock_result.alternatives = [mock_alternative]

        mock_response = MagicMock()
        mock_response.results = [mock_result]

        mock_client.recognize.return_value = mock_response

        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)

        self.assertTrue(result['success'])
        self.assertEqual(
            result['text'],
            'This is a Google transcription test.')
        self.assertEqual(result['confidence'], 0.95)
        self.assertEqual(result['provider'], 'google')
        self.assertIsNone(result['error'])

    @patch('pbx.features.voicemail_transcription.GOOGLE_SPEECH_AVAILABLE', True)
    @patch('pbx.features.voicemail_transcription.speech')
    def test_transcription_google_no_results(self, mock_speech):
        """Test Google transcription with no results"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'google',
                'api_key': None
            }
        })

        # Mock Google Speech client
        mock_client = MagicMock()
        mock_speech.SpeechClient.return_value = mock_client

        # Mock configuration classes
        mock_speech.RecognitionAudio = MagicMock()
        mock_speech.RecognitionConfig = MagicMock()
        mock_speech.RecognitionConfig.AudioEncoding = MagicMock()

        # Mock empty response
        mock_response = MagicMock()
        mock_response.results = []

        mock_client.recognize.return_value = mock_response

        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Transcription returned no results')

    def test_transcription_result_structure(self):
        """Test that transcription result has correct structure"""
        config = Mock()
        config.get = Mock(
            return_value={
                'voicemail_transcription': {
                    'enabled': False}})

        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)

        # Verify all required keys are present
        required_keys = [
            'success',
            'text',
            'confidence',
            'language',
            'provider',
            'timestamp',
            'error']
        for key in required_keys:
            self.assertIn(key, result)

        # Verify types
        self.assertIsInstance(result['success'], bool)
        self.assertIsInstance(result['confidence'], float)
        self.assertIsInstance(result['timestamp'], datetime)


def run_all_tests():
    """Run all tests in this module"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    unittest.main()
