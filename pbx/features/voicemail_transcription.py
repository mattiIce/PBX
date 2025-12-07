"""
Voicemail transcription service using speech-to-text APIs
"""
import os
from datetime import datetime
from pbx.utils.logger import get_logger

# Try importing optional transcription libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from google.cloud import speech
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_AVAILABLE = False


class VoicemailTranscriptionService:
    """Service for transcribing voicemail messages to text"""

    def __init__(self, config=None):
        """
        Initialize transcription service

        Args:
            config: Config object with transcription settings
        """
        self.logger = get_logger()
        self.config = config
        self.enabled = False
        self.provider = None
        self.api_key = None

        # Load configuration
        if config:
            transcription_config = config.get('features', {}).get('voicemail_transcription', {})
            self.enabled = transcription_config.get('enabled', False)
            self.provider = transcription_config.get('provider', 'openai')
            self.api_key = transcription_config.get('api_key')

            if self.enabled:
                self.logger.info(f"Voicemail transcription service initialized")
                self.logger.info(f"  Provider: {self.provider}")
                self.logger.info(f"  API key configured: {bool(self.api_key)}")
            else:
                self.logger.debug("Voicemail transcription service disabled in configuration")

    def transcribe(self, audio_file_path, language='en-US'):
        """
        Transcribe voicemail audio file to text

        Args:
            audio_file_path: Path to audio file (WAV format)
            language: Language code (default: en-US)

        Returns:
            Dictionary with transcription results:
            {
                'success': bool,
                'text': str,
                'confidence': float,
                'language': str,
                'provider': str,
                'timestamp': datetime,
                'error': str (if success is False)
            }
        """
        if not self.enabled:
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': None,
                'timestamp': datetime.now(),
                'error': 'Transcription service is disabled'
            }

        if not os.path.exists(audio_file_path):
            self.logger.error(f"Audio file not found: {audio_file_path}")
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': self.provider,
                'timestamp': datetime.now(),
                'error': f'Audio file not found: {audio_file_path}'
            }

        self.logger.info(f"Transcribing voicemail: {audio_file_path}")
        self.logger.info(f"  Provider: {self.provider}")
        self.logger.info(f"  Language: {language}")

        try:
            if self.provider == 'openai':
                return self._transcribe_openai(audio_file_path, language)
            elif self.provider == 'google':
                return self._transcribe_google(audio_file_path, language)
            else:
                error_msg = f"Unsupported transcription provider: {self.provider}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'text': None,
                    'confidence': 0.0,
                    'language': language,
                    'provider': self.provider,
                    'timestamp': datetime.now(),
                    'error': error_msg
                }
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': self.provider,
                'timestamp': datetime.now(),
                'error': str(e)
            }

    def _transcribe_openai(self, audio_file_path, language='en-US'):
        """
        Transcribe using OpenAI Whisper API

        Args:
            audio_file_path: Path to audio file
            language: Language code

        Returns:
            Transcription result dictionary
        """
        if not OPENAI_AVAILABLE:
            error_msg = "OpenAI library not installed. Install with: pip install openai"
            self.logger.error(error_msg)
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': 'openai',
                'timestamp': datetime.now(),
                'error': error_msg
            }

        if not self.api_key:
            error_msg = "OpenAI API key not configured"
            self.logger.error(error_msg)
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': 'openai',
                'timestamp': datetime.now(),
                'error': error_msg
            }

        try:
            # Set API key
            openai.api_key = self.api_key

            # Open audio file
            with open(audio_file_path, 'rb') as audio_file:
                # Extract language code (e.g., 'en' from 'en-US')
                lang_code = language.split('-')[0] if '-' in language else language

                # Call Whisper API
                self.logger.info(f"Calling OpenAI Whisper API...")
                response = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    language=lang_code
                )

                # Extract text
                text = response.get('text', '').strip()

                if text:
                    self.logger.info(f"✓ Transcription successful")
                    self.logger.info(f"  Text length: {len(text)} characters")
                    self.logger.debug(f"  Text: {text[:100]}...")
                    return {
                        'success': True,
                        'text': text,
                        'confidence': 1.0,  # Whisper doesn't provide confidence
                        'language': language,
                        'provider': 'openai',
                        'timestamp': datetime.now(),
                        'error': None
                    }
                else:
                    self.logger.warning("Transcription returned empty text")
                    return {
                        'success': False,
                        'text': None,
                        'confidence': 0.0,
                        'language': language,
                        'provider': 'openai',
                        'timestamp': datetime.now(),
                        'error': 'Transcription returned empty text'
                    }

        except Exception as e:
            self.logger.error(f"OpenAI transcription error: {e}")
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': 'openai',
                'timestamp': datetime.now(),
                'error': str(e)
            }

    def _transcribe_google(self, audio_file_path, language='en-US'):
        """
        Transcribe using Google Cloud Speech-to-Text API

        Args:
            audio_file_path: Path to audio file
            language: Language code

        Returns:
            Transcription result dictionary
        """
        if not GOOGLE_SPEECH_AVAILABLE:
            error_msg = "Google Cloud Speech library not installed. Install with: pip install google-cloud-speech"
            self.logger.error(error_msg)
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': 'google',
                'timestamp': datetime.now(),
                'error': error_msg
            }

        try:
            # Initialize Google Speech client
            client = speech.SpeechClient()

            # Read audio file
            with open(audio_file_path, 'rb') as audio_file:
                content = audio_file.read()

            # Configure audio and recognition settings
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=8000,  # Standard phone audio sample rate
                language_code=language,
                enable_automatic_punctuation=True,
                model='phone_call'  # Optimized for phone call audio
            )

            # Perform transcription
            self.logger.info(f"Calling Google Cloud Speech-to-Text API...")
            response = client.recognize(config=config, audio=audio)

            # Extract best result
            if response.results:
                result = response.results[0]
                if result.alternatives:
                    alternative = result.alternatives[0]
                    text = alternative.transcript.strip()
                    confidence = alternative.confidence

                    if text:
                        self.logger.info(f"✓ Transcription successful")
                        self.logger.info(f"  Text length: {len(text)} characters")
                        self.logger.info(f"  Confidence: {confidence:.2%}")
                        self.logger.debug(f"  Text: {text[:100]}...")
                        return {
                            'success': True,
                            'text': text,
                            'confidence': confidence,
                            'language': language,
                            'provider': 'google',
                            'timestamp': datetime.now(),
                            'error': None
                        }

            # No results found
            self.logger.warning("Transcription returned no results")
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': 'google',
                'timestamp': datetime.now(),
                'error': 'Transcription returned no results'
            }

        except Exception as e:
            self.logger.error(f"Google transcription error: {e}")
            return {
                'success': False,
                'text': None,
                'confidence': 0.0,
                'language': language,
                'provider': 'google',
                'timestamp': datetime.now(),
                'error': str(e)
            }
