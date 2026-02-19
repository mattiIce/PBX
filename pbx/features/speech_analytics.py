"""
Real-Time Speech Analytics Framework
Provides live transcription, sentiment analysis, and call summarization
"""

from datetime import UTC, datetime
from typing import Any

from pbx.utils.logger import get_logger


class SpeechAnalyticsEngine:
    """
    Real-time speech analytics engine
    Framework for transcription, sentiment, and summarization
    """

    def __init__(self, db_backend: Any | None, config: dict) -> None:
        """
        Initialize speech analytics engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = config.get("speech_analytics.enabled", False)

        self.logger.info("Speech Analytics Framework initialized")

    def get_config(self, extension: str) -> dict | None:
        """
        Get speech analytics configuration for extension

        Args:
            extension: Extension number

        Returns:
            Configuration dict or None
        """
        try:
            result = self.db.execute(
                (
                    "SELECT id, extension, enabled, transcription_enabled, sentiment_enabled, summarization_enabled, keywords, alert_threshold, created_at, updated_at FROM speech_analytics_configs WHERE extension = ?"
                    if self.db.db_type == "sqlite"
                    else "SELECT id, extension, enabled, transcription_enabled, sentiment_enabled, summarization_enabled, keywords, alert_threshold, created_at, updated_at FROM speech_analytics_configs WHERE extension = %s"
                ),
                (extension,),
            )

            if result and result[0]:
                row = result[0]
                return {
                    "extension": row[1],
                    "enabled": bool(row[2]),
                    "transcription_enabled": bool(row[3]),
                    "sentiment_enabled": bool(row[4]),
                    "summarization_enabled": bool(row[5]),
                    "keywords": row[6],
                    "alert_threshold": float(row[7]) if row[7] else 0.7,
                }
            return None
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to get speech analytics config: {e}")
            return None

    def update_config(self, extension: str, config: dict) -> bool:
        """
        Update speech analytics configuration

        Args:
            extension: Extension number
            config: Configuration dictionary

        Returns:
            bool: True if successful
        """
        try:
            # Check if config exists
            existing = self.get_config(extension)

            if existing:
                # Update
                self.db.execute(
                    (
                        """UPDATE speech_analytics_configs
                       SET enabled = ?, transcription_enabled = ?,
                           sentiment_enabled = ?, summarization_enabled = ?,
                           keywords = ?, alert_threshold = ?, updated_at = ?
                       WHERE extension = ?"""
                        if self.db.db_type == "sqlite"
                        else """UPDATE speech_analytics_configs
                       SET enabled = %s, transcription_enabled = %s,
                           sentiment_enabled = %s, summarization_enabled = %s,
                           keywords = %s, alert_threshold = %s, updated_at = %s
                       WHERE extension = %s"""
                    ),
                    (
                        config.get("enabled", True),
                        config.get("transcription_enabled", True),
                        config.get("sentiment_enabled", True),
                        config.get("summarization_enabled", True),
                        config.get("keywords", ""),
                        config.get("alert_threshold", 0.7),
                        datetime.now(UTC),
                        extension,
                    ),
                )
            else:
                # Insert
                self.db.execute(
                    (
                        """INSERT INTO speech_analytics_configs
                       (extension, enabled, transcription_enabled, sentiment_enabled,
                        summarization_enabled, keywords, alert_threshold)
                       VALUES (?, ?, ?, ?, ?, ?, ?)"""
                        if self.db.db_type == "sqlite"
                        else """INSERT INTO speech_analytics_configs
                       (extension, enabled, transcription_enabled, sentiment_enabled,
                        summarization_enabled, keywords, alert_threshold)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                    ),
                    (
                        extension,
                        config.get("enabled", True),
                        config.get("transcription_enabled", True),
                        config.get("sentiment_enabled", True),
                        config.get("summarization_enabled", True),
                        config.get("keywords", ""),
                        config.get("alert_threshold", 0.7),
                    ),
                )

            self.logger.info(f"Updated speech analytics config for {extension}")
            return True

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to update speech analytics config: {e}")
            return False

    def analyze_audio_stream(self, call_id: str, audio_chunk: bytes) -> dict:
        """
        Analyze audio stream in real-time
        Uses Vosk for offline speech recognition

        Args:
            call_id: Call identifier
            audio_chunk: Audio data chunk (16kHz, 16-bit PCM)

        Returns:
            Analysis results dictionary
        """
        result = {
            "call_id": call_id,
            "transcription": "",
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "keywords_detected": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Get configuration for this call
        # Would need to map call_id to extension in real implementation
        try:
            # Transcribe audio using Vosk (offline)
            transcription = self._transcribe_audio_vosk(audio_chunk)
            result["transcription"] = transcription

            if transcription:
                # Analyze sentiment
                sentiment_result = self.analyze_sentiment(transcription)
                result["sentiment"] = sentiment_result["sentiment"]
                result["sentiment_score"] = sentiment_result["score"]

                # Build keyword list from stored call-extension mapping or defaults
                default_keywords = ["urgent", "complaint", "cancel", "refund", "problem"]
                keywords = list(default_keywords)
                try:
                    # Try to get custom keywords from the extension config
                    # call_id format may contain extension info (e.g., "ext-100-...")
                    extension = getattr(self, "_call_extensions", {}).get(call_id)
                    if extension:
                        ext_config = self.get_config(extension)
                        if ext_config and ext_config.get("keywords"):
                            custom_kw = ext_config["keywords"]
                            if isinstance(custom_kw, str) and custom_kw.strip():
                                keywords = [k.strip() for k in custom_kw.split(",") if k.strip()]
                except (KeyError, TypeError, ValueError):
                    pass  # Use default keywords
                result["keywords_detected"] = self.detect_keywords(transcription, keywords)

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error analyzing audio stream: {e}")

        return result

    def _transcribe_audio_vosk(self, audio_chunk: bytes) -> str:
        """
        Transcribe audio using Vosk offline speech recognition

        Args:
            audio_chunk: Audio data (16kHz, 16-bit PCM)

        Returns:
            Transcribed text
        """
        try:
            # Import vosk only when needed
            import json

            import vosk

            # Check if we have a Vosk model initialized
            if not hasattr(self, "_vosk_model"):
                # Initialize Vosk model (requires model to be downloaded)
                # Default path: /var/pbx/vosk-models/
                model_path = self.config.get(
                    "speech_analytics.vosk_model_path",
                    "/var/pbx/vosk-models/vosk-model-small-en-us-0.15",
                )

                try:
                    self._vosk_model = vosk.Model(model_path)
                    self._vosk_recognizer = vosk.KaldiRecognizer(self._vosk_model, 16000)
                    self.logger.info(f"Vosk model loaded from {model_path}")
                except Exception as e:
                    self.logger.warning(f"Vosk model not available: {e}")
                    return ""

            # Process audio chunk
            if self._vosk_recognizer.AcceptWaveform(audio_chunk):
                result = json.loads(self._vosk_recognizer.Result())
                return result.get("text", "")
            # Partial result
            result = json.loads(self._vosk_recognizer.PartialResult())
            return result.get("partial", "")

        except ImportError:
            self.logger.warning("Vosk library not available, transcription disabled")
            return ""
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Error in Vosk transcription: {e}")
            return ""

    def analyze_sentiment(self, text: str) -> dict:
        """
        Analyze sentiment of text using rule-based approach
        Simple but effective for real-time analysis

        Args:
            text: Text to analyze

        Returns:
            Sentiment analysis results
        """
        if not text:
            return {"sentiment": "neutral", "score": 0.0, "confidence": 0.0}

        text_lower = text.lower()

        # Positive and negative word lists
        positive_words = [
            "great",
            "excellent",
            "good",
            "happy",
            "satisfied",
            "wonderful",
            "fantastic",
            "amazing",
            "perfect",
            "love",
            "best",
            "helpful",
            "thank",
            "thanks",
            "appreciate",
            "pleased",
            "glad",
            "delighted",
        ]

        negative_words = [
            "bad",
            "terrible",
            "awful",
            "horrible",
            "poor",
            "worst",
            "hate",
            "angry",
            "frustrated",
            "disappointed",
            "upset",
            "annoyed",
            "useless",
            "broken",
            "problem",
            "issue",
            "complaint",
            "refund",
            "cancel",
            "wrong",
            "error",
            "failed",
            "unhappy",
            "dissatisfied",
        ]

        # Count positive and negative words
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        # Calculate sentiment score (-1.0 to 1.0)
        total_words = len(text.split())
        if total_words == 0:
            return {"sentiment": "neutral", "score": 0.0, "confidence": 0.0}

        # Normalize scores
        positive_score = positive_count / max(total_words, 1)
        negative_score = negative_count / max(total_words, 1)

        # Calculate final score
        score = positive_score - negative_score

        # Determine sentiment category
        if score > 0.1:
            sentiment = "positive"
        elif score < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Calculate confidence based on word count
        # Confidence scales linearly: 10 sentiment words = 100% confidence
        # This provides a reasonable threshold for reliable sentiment detection
        confidence_scaling_factor = 10.0
        confidence = min(1.0, (positive_count + negative_count) / confidence_scaling_factor)

        return {
            "sentiment": sentiment,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
        }

    def generate_summary(self, call_id: str, transcript: str) -> str:
        """
        Generate call summary from transcript
        Uses extractive summarization (key sentence extraction)

        Args:
            call_id: Call identifier
            transcript: Full call transcript

        Returns:
            Summary text
        """
        if not transcript or len(transcript.strip()) < 50:
            return "Call too short to summarize"

        try:
            # Split into sentences
            sentences = [
                s.strip()
                for s in transcript.replace("!", ".").replace("?", ".").split(".")
                if s.strip()
            ]

            if len(sentences) <= 2:
                return transcript

            # Simple extractive summarization
            # Score sentences by: length, keyword presence, position
            keywords = [
                "problem",
                "issue",
                "help",
                "need",
                "want",
                "order",
                "account",
                "payment",
                "service",
                "question",
                "urgent",
                "important",
            ]

            scored_sentences = []
            for i, sentence in enumerate(sentences):
                score = 0
                sentence_lower = sentence.lower()

                # Length score (prefer moderate length)
                word_count = len(sentence.split())
                if 5 <= word_count <= 20:
                    score += 2
                elif word_count > 3:
                    score += 1

                # Keyword score
                keyword_count = sum(1 for kw in keywords if kw in sentence_lower)
                score += keyword_count * 2

                # Position score (beginning and end are more important)
                if i == 0 or i == len(sentences) - 1:
                    score += 3
                elif i == 1 or i == len(sentences) - 2:
                    score += 1

                scored_sentences.append((score, sentence))

            # Sort by score and take top sentences
            scored_sentences.sort(reverse=True, key=lambda x: x[0])
            summary_count = min(3, max(1, len(sentences) // 3))
            top_sentences = [s[1] for s in scored_sentences[:summary_count]]

            # Preserve original order
            summary = ". ".join([s for s in sentences if s in top_sentences])

            # Store summary in database
            self._store_summary(call_id, transcript, summary)

            return summary

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return "Unable to generate summary"

    def _store_summary(self, call_id: str, transcript: str, summary: str) -> bool:
        """
        Store call summary in database

        Args:
            call_id: Call identifier
            transcript: Full transcript
            summary: Generated summary

        Returns:
            bool: True if successful
        """
        try:
            # Get sentiment of full transcript
            sentiment = self.analyze_sentiment(transcript)

            self.db.execute(
                (
                    """INSERT INTO call_summaries
                   (call_id, transcript, summary, sentiment, sentiment_score)
                   VALUES (?, ?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO call_summaries
                   (call_id, transcript, summary, sentiment, sentiment_score)
                   VALUES (%s, %s, %s, %s, %s)"""
                ),
                (call_id, transcript, summary, sentiment["sentiment"], sentiment["score"]),
            )
            return True
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error storing summary: {e}")
            return False

    def detect_keywords(self, text: str, keywords: list[str]) -> list[str]:
        """
        Detect keywords in text

        Args:
            text: Text to search
            keywords: Keywords to detect

        Returns:
            list of detected keywords
        """
        detected = [keyword for keyword in keywords if keyword.lower() in text.lower()]

        return detected

    def get_all_configs(self) -> list[dict]:
        """
        Get all speech analytics configurations

        Returns:
            list of configuration dictionaries
        """
        try:
            result = self.db.execute("SELECT id, extension, enabled, transcription_enabled, sentiment_enabled, summarization_enabled, keywords, alert_threshold, created_at, updated_at FROM speech_analytics_configs ORDER BY extension")

            configs = [
                {
                    "extension": row[1],
                    "enabled": bool(row[2]),
                    "transcription_enabled": bool(row[3]),
                    "sentiment_enabled": bool(row[4]),
                    "summarization_enabled": bool(row[5]),
                    "keywords": row[6],
                    "alert_threshold": float(row[7]) if row[7] else 0.7,
                }
                for row in result or []
            ]

            return configs

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to get all speech analytics configs: {e}")
            return []

    def get_call_summary(self, call_id: str) -> dict | None:
        """
        Get stored call summary

        Args:
            call_id: Call identifier

        Returns:
            Summary dict or None
        """
        try:
            result = self.db.execute(
                (
                    "SELECT * FROM call_summaries WHERE call_id = ?"
                    if self.db.db_type == "sqlite"
                    else "SELECT * FROM call_summaries WHERE call_id = %s"
                ),
                (call_id,),
            )

            if result and result[0]:
                row = result[0]
                return {
                    "call_id": row[1],
                    "transcript": row[2],
                    "summary": row[3],
                    "sentiment": row[4],
                    "sentiment_score": float(row[5]) if row[5] else 0.0,
                    "created_at": row[6],
                }
            return None
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error getting call summary: {e}")
            return None

    def analyze_call_recording(self, call_id: str, audio_file_path: str) -> dict:
        """
        Analyze a complete call recording

        Args:
            call_id: Call identifier
            audio_file_path: Path to audio file

        Returns:
            Complete analysis dict
        """
        try:
            import wave

            chunk_results = []
            duration = 0.0

            # 1. Load audio file and read PCM data
            try:
                with wave.open(audio_file_path, "rb") as wf:
                    sample_rate = wf.getframerate()
                    n_frames = wf.getnframes()
                    duration = n_frames / sample_rate if sample_rate > 0 else 0.0

                    # 2. Read and process in chunks (4000 frames per chunk)
                    chunk_frame_size = 4000
                    while True:
                        audio_chunk = wf.readframes(chunk_frame_size)
                        if len(audio_chunk) == 0:
                            break

                        # 3. Transcribe each chunk
                        chunk_text = self._transcribe_audio_vosk(audio_chunk)
                        if chunk_text:
                            chunk_results.append(chunk_text)

            except (FileNotFoundError, wave.Error) as e:
                self.logger.error(f"Could not open audio file {audio_file_path}: {e}")
                return {"call_id": call_id, "status": "error", "error": str(e)}

            # 4. Generate full transcript from all chunks
            full_transcript = " ".join(chunk_results).strip()

            # 5. Analyze sentiment of the full transcript
            sentiment_result = self.analyze_sentiment(full_transcript)

            # 6. Generate summary
            summary = self.generate_summary(call_id, full_transcript)

            # 7. Detect keywords
            default_keywords = [
                "urgent",
                "complaint",
                "cancel",
                "refund",
                "problem",
                "help",
                "issue",
                "billing",
                "account",
                "service",
            ]
            keywords_detected = self.detect_keywords(full_transcript, default_keywords)

            return {
                "call_id": call_id,
                "status": "completed",
                "duration": duration,
                "transcript": full_transcript,
                "sentiment": sentiment_result["sentiment"],
                "sentiment_score": sentiment_result["score"],
                "sentiment_confidence": sentiment_result["confidence"],
                "summary": summary,
                "keywords_detected": keywords_detected,
                "chunks_processed": len(chunk_results),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except ImportError:
            self.logger.warning("wave module not available for audio file processing")
            return {"call_id": call_id, "status": "error", "error": "wave module not available"}
        except Exception as e:
            self.logger.error(f"Error analyzing call recording: {e}")
            return {"call_id": call_id, "status": "error", "error": str(e)}
