"""
Tests for voicemail transcription functionality
"""
import unittest
import os
import sys
import tempfile
import wave
import struct
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Mock the optional dependencies before importing the module
sys.modules['openai'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.speech'] = MagicMock()

from pbx.features.voicemail_transcription import VoicemailTranscriptionService


class TestVoicemailTranscription(unittest.TestCase):
    """Test voicemail transcription service"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test audio file (simple WAV)
        self.test_audio_path = os.path.join(self.temp_dir, "test_voicemail.wav")
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
            value = int(32767.0 * 0.5 * (1 + (i % 100) / 100))  # Simple varying amplitude
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
        config.get = Mock(return_value={'voicemail_transcription': {'enabled': False}})
        
        service = VoicemailTranscriptionService(config)
        
        self.assertFalse(service.enabled)
        
        result = service.transcribe(self.test_audio_path)
        
        self.assertFalse(result['success'])
        self.assertIsNone(result['text'])
        self.assertEqual(result['error'], 'Transcription service is disabled')

    @patch('pbx.features.voicemail_transcription.OPENAI_AVAILABLE', True)
    def test_transcription_service_enabled_no_api_key(self):
        """Test transcription service when enabled but no API key"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'openai',
                'api_key': None
            }
        })
        
        service = VoicemailTranscriptionService(config)
        
        self.assertTrue(service.enabled)
        self.assertEqual(service.provider, 'openai')
        
        result = service.transcribe(self.test_audio_path)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'OpenAI API key not configured')

    def test_transcription_file_not_found(self):
        """Test transcription with non-existent file"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'openai',
                'api_key': 'test-key'
            }
        })
        
        service = VoicemailTranscriptionService(config)
        
        result = service.transcribe('/nonexistent/file.wav')
        
        self.assertFalse(result['success'])
        self.assertIn('Audio file not found', result['error'])

    @patch('pbx.features.voicemail_transcription.OPENAI_AVAILABLE', True)
    def test_transcription_openai_success(self):
        """Test successful OpenAI transcription"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'openai',
                'api_key': 'test-key'
            }
        })
        
        # Mock OpenAI response
        import openai
        mock_response = {
            'text': 'This is a test voicemail transcription.'
        }
        openai.Audio.transcribe = Mock(return_value=mock_response)
        
        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['text'], 'This is a test voicemail transcription.')
        self.assertEqual(result['confidence'], 1.0)  # Whisper doesn't provide confidence
        self.assertEqual(result['provider'], 'openai')
        self.assertIsNone(result['error'])

    @patch('pbx.features.voicemail_transcription.OPENAI_AVAILABLE', True)
    def test_transcription_openai_empty_text(self):
        """Test OpenAI transcription with empty result"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'openai',
                'api_key': 'test-key'
            }
        })
        
        # Mock OpenAI response with empty text
        import openai
        mock_response = {'text': ''}
        openai.Audio.transcribe = Mock(return_value=mock_response)
        
        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)
        
        self.assertFalse(result['success'])
        self.assertIsNone(result['text'])
        self.assertEqual(result['error'], 'Transcription returned empty text')

    @patch('pbx.features.voicemail_transcription.OPENAI_AVAILABLE', True)
    def test_transcription_openai_api_error(self):
        """Test OpenAI transcription with API error"""
        config = Mock()
        config.get = Mock(return_value={
            'voicemail_transcription': {
                'enabled': True,
                'provider': 'openai',
                'api_key': 'test-key'
            }
        })
        
        # Mock OpenAI API error
        import openai
        openai.Audio.transcribe = Mock(side_effect=Exception('API rate limit exceeded'))
        
        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)
        
        self.assertFalse(result['success'])
        self.assertIn('API rate limit exceeded', result['error'])

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
    def test_transcription_google_success(self):
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
        from google.cloud import speech
        mock_client = MagicMock()
        speech.SpeechClient = Mock(return_value=mock_client)
        
        # Mock recognition response
        mock_alternative = MagicMock()
        mock_alternative.transcript = 'This is a Google transcription test.'
        mock_alternative.confidence = 0.95
        
        mock_result = MagicMock()
        mock_result.alternatives = [mock_alternative]
        
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        
        mock_client.recognize = Mock(return_value=mock_response)
        
        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['text'], 'This is a Google transcription test.')
        self.assertEqual(result['confidence'], 0.95)
        self.assertEqual(result['provider'], 'google')
        self.assertIsNone(result['error'])

    @patch('pbx.features.voicemail_transcription.GOOGLE_SPEECH_AVAILABLE', True)
    def test_transcription_google_no_results(self):
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
        from google.cloud import speech
        mock_client = MagicMock()
        speech.SpeechClient = Mock(return_value=mock_client)
        
        # Mock empty response
        mock_response = MagicMock()
        mock_response.results = []
        
        mock_client.recognize = Mock(return_value=mock_response)
        
        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Transcription returned no results')

    def test_transcription_result_structure(self):
        """Test that transcription result has correct structure"""
        config = Mock()
        config.get = Mock(return_value={'voicemail_transcription': {'enabled': False}})
        
        service = VoicemailTranscriptionService(config)
        result = service.transcribe(self.test_audio_path)
        
        # Verify all required keys are present
        required_keys = ['success', 'text', 'confidence', 'language', 'provider', 'timestamp', 'error']
        for key in required_keys:
            self.assertIn(key, result)
        
        # Verify types
        self.assertIsInstance(result['success'], bool)
        self.assertIsInstance(result['confidence'], float)
        self.assertIsInstance(result['timestamp'], datetime)


if __name__ == '__main__':
    unittest.main()
