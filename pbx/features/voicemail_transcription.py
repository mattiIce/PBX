"""
Voicemail transcription service using speech-to-text
"""
import os
import wave
import json
from datetime import datetime
from pbx.utils.logger import get_logger

# Constants for Vosk transcription
VOSK_FRAME_SIZE = 4000  # Number of frames to read per chunk
VOSK_DEFAULT_CONFIDENCE = 0.95  # Default confidence when Vosk doesn't provide one

# Import Vosk (free, offline speech recognition)
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

# Optional: Google Cloud Speech (kept for backward compatibility)
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
        self.vosk_model = None
        self.vosk_model_path = None

        # Load configuration
        if config:
            transcription_config = config.get('features', {}).get('voicemail_transcription', {})
            self.enabled = transcription_config.get('enabled', False)
            self.provider = transcription_config.get('provider', 'vosk')  # Default to vosk (free)
            self.api_key = transcription_config.get('api_key')
            self.vosk_model_path = transcription_config.get('vosk_model_path', 'models/vosk-model-small-en-us-0.15')

            if self.enabled:
                self.logger.info(f"Voicemail transcription service initialized")
                self.logger.info(f"  Provider: {self.provider}")
                if self.provider == 'vosk':
                    self.logger.info(f"  Model path: {self.vosk_model_path}")
                    # Initialize Vosk model
                    if VOSK_AVAILABLE:
                        try:
                            if os.path.exists(self.vosk_model_path):
                                self.vosk_model = Model(self.vosk_model_path)
                                self.logger.info("  Vosk model loaded successfully (offline transcription ready)")
                            else:
                                self.logger.warning(f"  Vosk model not found at {self.vosk_model_path}")
                                self.logger.info("  Download model from: https://alphacephei.com/vosk/models")
                        except Exception as e:
                            self.logger.error(f"  Failed to load Vosk model: {e}")
                    else:
                        self.logger.warning("  Vosk library not installed. Install with: pip install vosk")
                else:
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
            if self.provider == 'vosk':
                return self._transcribe_vosk(audio_file_path, language)
            elif self.provider == 'google':
                return self._transcribe_google(audio_file_path, language)
            else:
                error_msg = f"Unsupported transcription provider: {self.provider}. Use 'vosk' (recommended, free) or 'google'"
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

    def _create_error_response(self, error_msg, language, provider=None):
        """
        Helper method to create error response structure
        
        Args:
            error_msg: Error message string
            language: Language code
            provider: Provider name (optional)
            
        Returns:
            Dictionary with error response structure
        """
        return {
            'success': False,
            'text': None,
            'confidence': 0.0,
            'language': language,
            'provider': provider or self.provider,
            'timestamp': datetime.now(),
            'error': error_msg
        }

    def _transcribe_vosk(self, audio_file_path, language='en-US'):
        """
        Transcribe using Vosk (offline, free speech recognition)

        Args:
            audio_file_path: Path to audio file
            language: Language code

        Returns:
            Transcription result dictionary
        """
        if not VOSK_AVAILABLE:
            error_msg = "Vosk library not installed. Install with: pip install vosk"
            self.logger.error(error_msg)
            return self._create_error_response(error_msg, language, 'vosk')

        if not self.vosk_model:
            error_msg = f"Vosk model not loaded. Check model path: {self.vosk_model_path}"
            self.logger.error(error_msg)
            self.logger.info("Download models from: https://alphacephei.com/vosk/models")
            return self._create_error_response(error_msg, language, 'vosk')

        try:
            # Open WAV file
            wf = wave.open(audio_file_path, "rb")
            
            # Validate audio format
            if wf.getnchannels() != 1:
                wf.close()
                error_msg = "Audio must be mono channel"
                self.logger.error(error_msg)
                return self._create_error_response(error_msg, language, 'vosk')
            
            # Check sample rate - Vosk works best with 8kHz or 16kHz
            sample_rate = wf.getframerate()
            if sample_rate not in [8000, 16000, 32000, 44100, 48000]:
                wf.close()
                error_msg = f"Unsupported sample rate: {sample_rate}. Use 8000, 16000, 32000, 44100, or 48000 Hz"
                self.logger.error(error_msg)
                return self._create_error_response(error_msg, language, 'vosk')
            
            # Create recognizer
            rec = KaldiRecognizer(self.vosk_model, sample_rate)
            rec.SetWords(True)  # Enable word-level timestamps
            
            # Process audio in chunks
            self.logger.info(f"Processing audio with Vosk (offline)...")
            results = []
            
            while True:
                data = wf.readframes(VOSK_FRAME_SIZE)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if 'text' in result and result['text']:
                        results.append(result['text'])
            
            # Get final result
            final_result = json.loads(rec.FinalResult())
            if 'text' in final_result and final_result['text']:
                results.append(final_result['text'])
            
            wf.close()
            
            # Combine all text
            text = ' '.join(results).strip()
            
            if text:
                self.logger.info(f"✓ Transcription successful (offline)")
                self.logger.info(f"  Text length: {len(text)} characters")
                self.logger.debug(f"  Text: {text[:100]}...")
                return {
                    'success': True,
                    'text': text,
                    'confidence': VOSK_DEFAULT_CONFIDENCE,  # Vosk doesn't provide confidence
                    'language': language,
                    'provider': 'vosk',
                    'timestamp': datetime.now(),
                    'error': None
                }
            else:
                self.logger.warning("Transcription returned empty text")
                return self._create_error_response('Transcription returned empty text', language, 'vosk')

        except Exception as e:
            self.logger.error(f"Vosk transcription error: {e}")
            return self._create_error_response(str(e), language, 'vosk')

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
