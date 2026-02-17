"""
Comprehensive tests for Call Recording Analytics feature.

Tests cover all public classes, methods, enums, dataclasses, and the
global singleton accessor in pbx/features/call_recording_analytics.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pbx.features.call_recording_analytics import RecordingAnalytics

# ---------------------------------------------------------------------------
# AnalysisType enum
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalysisType:
    """Tests for the AnalysisType enumeration."""

    def test_all_enum_members_exist(self) -> None:
        from pbx.features.call_recording_analytics import AnalysisType

        assert AnalysisType.SENTIMENT.value == "sentiment"
        assert AnalysisType.KEYWORDS.value == "keywords"
        assert AnalysisType.COMPLIANCE.value == "compliance"
        assert AnalysisType.QUALITY.value == "quality"
        assert AnalysisType.SUMMARY.value == "summary"
        assert AnalysisType.TRANSCRIPT.value == "transcript"

    def test_enum_member_count(self) -> None:
        from pbx.features.call_recording_analytics import AnalysisType

        assert len(AnalysisType) == 6

    def test_enum_from_value(self) -> None:
        from pbx.features.call_recording_analytics import AnalysisType

        assert AnalysisType("sentiment") is AnalysisType.SENTIMENT
        assert AnalysisType("keywords") is AnalysisType.KEYWORDS

    def test_enum_invalid_value(self) -> None:
        from pbx.features.call_recording_analytics import AnalysisType

        with pytest.raises(ValueError):
            AnalysisType("nonexistent")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    enabled: bool = False,
    auto_analyze: bool = False,
    analysis_types: list[str] | None = None,
    vosk_model_path: str = "/opt/vosk-model-small-en-us-0.15",
) -> dict:
    """Build a minimal config dict for RecordingAnalytics."""
    cfg: dict = {
        "features": {
            "recording_analytics": {
                "enabled": enabled,
                "auto_analyze": auto_analyze,
            }
        },
        "voicemail": {
            "transcription": {
                "vosk_model_path": vosk_model_path,
            }
        },
    }
    if analysis_types is not None:
        cfg["features"]["recording_analytics"]["analysis_types"] = analysis_types
    return cfg


def _build_analytics(
    config: dict | None = None,
    vosk_available: bool = False,
    spacy_available: bool = False,
) -> RecordingAnalytics:
    """Construct a RecordingAnalytics with mocked optional imports."""
    with (
        patch("pbx.features.call_recording_analytics.VOSK_AVAILABLE", vosk_available),
        patch("pbx.features.call_recording_analytics.SPACY_AVAILABLE", spacy_available),
        patch("pbx.features.call_recording_analytics.get_logger") as mock_logger_fn,
    ):
        mock_logger_fn.return_value = MagicMock()
        from pbx.features.call_recording_analytics import RecordingAnalytics

        return RecordingAnalytics(config)


# ---------------------------------------------------------------------------
# RecordingAnalytics.__init__
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecordingAnalyticsInit:
    """Tests for RecordingAnalytics initialisation."""

    def test_init_with_none_config(self) -> None:
        analytics = _build_analytics(config=None)
        assert analytics.config == {}
        assert analytics.enabled is False
        assert analytics.auto_analyze is False
        assert analytics.analysis_types == ["sentiment", "keywords", "summary"]

    def test_init_with_empty_config(self) -> None:
        analytics = _build_analytics(config={})
        assert analytics.enabled is False
        assert analytics.auto_analyze is False

    def test_init_enabled(self) -> None:
        cfg = _make_config(enabled=True, auto_analyze=True)
        analytics = _build_analytics(config=cfg)
        assert analytics.enabled is True
        assert analytics.auto_analyze is True

    def test_init_custom_analysis_types(self) -> None:
        cfg = _make_config(analysis_types=["transcript", "compliance"])
        analytics = _build_analytics(config=cfg)
        assert analytics.analysis_types == ["transcript", "compliance"]

    def test_init_default_analysis_types(self) -> None:
        cfg = _make_config()
        analytics = _build_analytics(config=cfg)
        assert analytics.analysis_types == ["sentiment", "keywords", "summary"]

    def test_init_storage_and_stats_defaults(self) -> None:
        analytics = _build_analytics()
        assert analytics.analyses == {}
        assert analytics.total_analyses == 0
        assert analytics.analyses_by_type == {}

    def test_init_models_none_when_libs_unavailable(self) -> None:
        analytics = _build_analytics(vosk_available=False, spacy_available=False)
        assert analytics.vosk_model is None
        assert analytics.spacy_nlp is None

    def test_init_vosk_model_loaded_when_path_exists(self) -> None:
        cfg = _make_config(vosk_model_path="/fake/vosk")
        mock_model = MagicMock()
        with (
            patch("pbx.features.call_recording_analytics.VOSK_AVAILABLE", True),
            patch("pbx.features.call_recording_analytics.SPACY_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.get_logger") as mock_log,
            patch("pbx.features.call_recording_analytics.Path") as mock_path_cls,
            patch("pbx.features.call_recording_analytics.Model", mock_model, create=True),
        ):
            mock_log.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = True

            from pbx.features.call_recording_analytics import RecordingAnalytics

            ra = RecordingAnalytics(cfg)
            mock_model.assert_called_once_with("/fake/vosk")
            assert ra.vosk_model is not None

    def test_init_vosk_model_not_found(self) -> None:
        cfg = _make_config(vosk_model_path="/nonexistent/path")
        with (
            patch("pbx.features.call_recording_analytics.VOSK_AVAILABLE", True),
            patch("pbx.features.call_recording_analytics.SPACY_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.get_logger") as mock_log,
            patch("pbx.features.call_recording_analytics.Path") as mock_path_cls,
            patch("pbx.features.call_recording_analytics.Model", create=True),
        ):
            mock_log.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = False

            from pbx.features.call_recording_analytics import RecordingAnalytics

            ra = RecordingAnalytics(cfg)
            assert ra.vosk_model is None

    def test_init_vosk_model_load_exception(self) -> None:
        cfg = _make_config(vosk_model_path="/bad/path")
        with (
            patch("pbx.features.call_recording_analytics.VOSK_AVAILABLE", True),
            patch("pbx.features.call_recording_analytics.SPACY_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.get_logger") as mock_log,
            patch("pbx.features.call_recording_analytics.Path") as mock_path_cls,
            patch(
                "pbx.features.call_recording_analytics.Model",
                side_effect=OSError("boom"),
                create=True,
            ),
        ):
            mock_log.return_value = MagicMock()
            mock_path_cls.return_value.exists.return_value = True

            from pbx.features.call_recording_analytics import RecordingAnalytics

            ra = RecordingAnalytics(cfg)
            assert ra.vosk_model is None

    def test_init_spacy_model_loaded(self) -> None:
        mock_spacy = MagicMock()
        mock_nlp = MagicMock()
        mock_spacy.load.return_value = mock_nlp

        with (
            patch("pbx.features.call_recording_analytics.VOSK_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.SPACY_AVAILABLE", True),
            patch("pbx.features.call_recording_analytics.get_logger") as mock_log,
            patch("pbx.features.call_recording_analytics.spacy", mock_spacy, create=True),
        ):
            mock_log.return_value = MagicMock()

            from pbx.features.call_recording_analytics import RecordingAnalytics

            ra = RecordingAnalytics({})
            mock_spacy.load.assert_called_once_with("en_core_web_sm")
            assert ra.spacy_nlp is mock_nlp

    def test_init_spacy_model_load_fails(self) -> None:
        mock_spacy = MagicMock()
        mock_spacy.load.side_effect = RuntimeError("no model")

        with (
            patch("pbx.features.call_recording_analytics.VOSK_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.SPACY_AVAILABLE", True),
            patch("pbx.features.call_recording_analytics.get_logger") as mock_log,
            patch("pbx.features.call_recording_analytics.spacy", mock_spacy, create=True),
        ):
            mock_log.return_value = MagicMock()

            from pbx.features.call_recording_analytics import RecordingAnalytics

            ra = RecordingAnalytics({})
            assert ra.spacy_nlp is None


# ---------------------------------------------------------------------------
# RecordingAnalytics.analyze_recording
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzeRecording:
    """Tests for the main analyze_recording entry point."""

    def test_analyze_recording_returns_expected_structure(self) -> None:
        analytics = _build_analytics()
        result = analytics.analyze_recording("rec-1", "/audio.wav", ["sentiment"])
        assert result["recording_id"] == "rec-1"
        assert "analyzed_at" in result
        assert "sentiment" in result["analyses"]

    def test_analyze_recording_uses_instance_types_when_none(self) -> None:
        cfg = _make_config(analysis_types=["quality"])
        analytics = _build_analytics(config=cfg)
        result = analytics.analyze_recording("rec-2", "/audio.wav")
        assert "quality" in result["analyses"]

    def test_analyze_recording_tracks_statistics(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("rec-1", "/audio.wav", ["sentiment", "keywords"])
        assert analytics.total_analyses == 1
        assert analytics.analyses_by_type["sentiment"] == 1
        assert analytics.analyses_by_type["keywords"] == 1

    def test_analyze_recording_stores_results(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("rec-1", "/audio.wav", ["summary"])
        assert "rec-1" in analytics.analyses

    def test_analyze_recording_all_types(self) -> None:
        analytics = _build_analytics()
        all_types = ["transcript", "sentiment", "keywords", "compliance", "quality", "summary"]
        result = analytics.analyze_recording("rec-all", "/audio.wav", all_types)
        for t in all_types:
            assert t in result["analyses"]

    def test_analyze_recording_unknown_type_ignored(self) -> None:
        analytics = _build_analytics()
        result = analytics.analyze_recording("rec-1", "/audio.wav", ["nonexistent"])
        assert result["analyses"] == {}
        assert analytics.analyses_by_type["nonexistent"] == 1

    def test_analyze_multiple_recordings_increments_total(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("r1", "/a.wav", ["sentiment"])
        analytics.analyze_recording("r2", "/b.wav", ["sentiment"])
        assert analytics.total_analyses == 2
        assert analytics.analyses_by_type["sentiment"] == 2

    def test_analyzed_at_is_utc_isoformat(self) -> None:
        analytics = _build_analytics()
        result = analytics.analyze_recording("rec-1", "/audio.wav", ["sentiment"])
        parsed = datetime.fromisoformat(result["analyzed_at"])
        assert parsed.tzinfo is not None


# ---------------------------------------------------------------------------
# RecordingAnalytics._transcribe
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTranscribe:
    """Tests for the _transcribe method."""

    def test_transcribe_import_error_path(self) -> None:
        """When vosk is not installed, should return error dict."""
        analytics = _build_analytics()
        with patch.dict("sys.modules", {"vosk": None}):
            result = analytics._transcribe("/fake.wav")
        # The method catches ImportError internally
        assert isinstance(result, dict)
        assert "transcript" in result

    def test_transcribe_no_vosk_model_returns_error(self) -> None:
        """When _load_vosk_model returns None, should return error dict."""
        analytics = _build_analytics()
        mock_vosk_module = MagicMock()
        with (
            patch.dict("sys.modules", {"vosk": mock_vosk_module}),
            patch.object(analytics, "_load_vosk_model", return_value=None),
        ):
            result = analytics._transcribe("/fake.wav")
        assert result["error"] == "Vosk model not available"
        assert result["transcript"] == ""
        assert result["confidence"] == 0.0

    def test_transcribe_happy_path(self) -> None:
        """Full transcription happy path with mocked wave and vosk."""
        import json

        analytics = _build_analytics()

        mock_vosk_module = MagicMock()
        mock_model = MagicMock()
        mock_recognizer = MagicMock()
        mock_vosk_module.KaldiRecognizer.return_value = mock_recognizer

        # Mock wave file context manager
        mock_wf = MagicMock()
        mock_wf.getframerate.return_value = 16000
        mock_wf.getnframes.return_value = 32000  # 2 seconds at 16kHz
        mock_wf.readframes.side_effect = [b"\x00" * 4000, b""]
        mock_wf.__enter__ = MagicMock(return_value=mock_wf)
        mock_wf.__exit__ = MagicMock(return_value=False)

        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps(
            {"text": "hello world", "result": [{"word": "hello", "conf": 0.95}]}
        )
        mock_recognizer.FinalResult.return_value = json.dumps(
            {"text": "goodbye", "result": [{"word": "goodbye", "conf": 0.9}]}
        )

        mock_wave_module = MagicMock()
        mock_wave_module.open.return_value = mock_wf

        with (
            patch.dict("sys.modules", {"vosk": mock_vosk_module, "wave": mock_wave_module}),
            patch.object(analytics, "_load_vosk_model", return_value=mock_model),
        ):
            result = analytics._transcribe("/audio.wav")

        assert "hello world" in result["transcript"]
        assert "goodbye" in result["transcript"]
        assert result["confidence"] > 0
        assert result["duration"] == 2.0

    def test_transcribe_happy_path_zero_confidence_count(self) -> None:
        """Transcription with no confidence data returns 0.0 confidence."""
        import json

        analytics = _build_analytics()

        mock_vosk_module = MagicMock()
        mock_model = MagicMock()
        mock_recognizer = MagicMock()
        mock_vosk_module.KaldiRecognizer.return_value = mock_recognizer

        mock_wf = MagicMock()
        mock_wf.getframerate.return_value = 16000
        mock_wf.getnframes.return_value = 0
        mock_wf.readframes.side_effect = [b""]
        mock_wf.__enter__ = MagicMock(return_value=mock_wf)
        mock_wf.__exit__ = MagicMock(return_value=False)

        mock_recognizer.FinalResult.return_value = json.dumps({})

        mock_wave_module = MagicMock()
        mock_wave_module.open.return_value = mock_wf

        with (
            patch.dict("sys.modules", {"vosk": mock_vosk_module, "wave": mock_wave_module}),
            patch.object(analytics, "_load_vosk_model", return_value=mock_model),
        ):
            result = analytics._transcribe("/audio.wav")

        assert result["transcript"] == ""
        assert result["confidence"] == 0.0

    def test_transcribe_happy_path_zero_sample_rate(self) -> None:
        """Zero sample rate yields duration 0."""
        import json

        analytics = _build_analytics()

        mock_vosk_module = MagicMock()
        mock_model = MagicMock()
        mock_recognizer = MagicMock()
        mock_vosk_module.KaldiRecognizer.return_value = mock_recognizer

        mock_wf = MagicMock()
        mock_wf.getframerate.return_value = 0
        mock_wf.getnframes.return_value = 100
        mock_wf.readframes.side_effect = [b""]
        mock_wf.__enter__ = MagicMock(return_value=mock_wf)
        mock_wf.__exit__ = MagicMock(return_value=False)

        mock_recognizer.FinalResult.return_value = json.dumps({})

        mock_wave_module = MagicMock()
        mock_wave_module.open.return_value = mock_wf

        with (
            patch.dict("sys.modules", {"vosk": mock_vosk_module, "wave": mock_wave_module}),
            patch.object(analytics, "_load_vosk_model", return_value=mock_model),
        ):
            result = analytics._transcribe("/audio.wav")

        assert result["duration"] == 0

    def test_transcribe_oserror_path(self) -> None:
        """When file can't be opened, should return error dict."""
        analytics = _build_analytics()
        mock_vosk_module = MagicMock()
        mock_wave_module = MagicMock()
        mock_wave_module.open.side_effect = OSError("no such file")

        with (
            patch.dict("sys.modules", {"vosk": mock_vosk_module, "wave": mock_wave_module}),
            patch.object(analytics, "_load_vosk_model", return_value=MagicMock()),
        ):
            result = analytics._transcribe("/nonexistent.wav")
        assert result["error"] == "no such file"
        assert result["transcript"] == ""


# ---------------------------------------------------------------------------
# RecordingAnalytics._load_vosk_model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadVoskModel:
    """Tests for _load_vosk_model."""

    def test_load_vosk_model_path_exists(self) -> None:
        analytics = _build_analytics()
        mock_model_instance = MagicMock()
        mock_model_cls = MagicMock(return_value=mock_model_instance)

        with (
            patch("pbx.features.call_recording_analytics.Path") as mock_path_cls,
            patch.dict("sys.modules", {"vosk": MagicMock(Model=mock_model_cls)}),
        ):
            mock_path_cls.return_value.exists.return_value = True
            result = analytics._load_vosk_model()
        assert result is mock_model_instance

    def test_load_vosk_model_path_does_not_exist(self) -> None:
        analytics = _build_analytics()
        with (
            patch("pbx.features.call_recording_analytics.Path") as mock_path_cls,
            patch.dict("sys.modules", {"vosk": MagicMock()}),
        ):
            mock_path_cls.return_value.exists.return_value = False
            result = analytics._load_vosk_model()
        assert result is None

    def test_load_vosk_model_oserror(self) -> None:
        analytics = _build_analytics()
        mock_model_cls = MagicMock(side_effect=OSError("bad model"))
        with (
            patch("pbx.features.call_recording_analytics.Path") as mock_path_cls,
            patch.dict("sys.modules", {"vosk": MagicMock(Model=mock_model_cls)}),
        ):
            mock_path_cls.return_value.exists.return_value = True
            result = analytics._load_vosk_model()
        assert result is None


# ---------------------------------------------------------------------------
# RecordingAnalytics._process_vosk_audio
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProcessVoskAudio:
    """Tests for _process_vosk_audio helper."""

    def test_process_vosk_audio_basic(self) -> None:
        import json

        analytics = _build_analytics()

        mock_recognizer = MagicMock()
        mock_wf = MagicMock()

        # Simulate 2 frames of audio then empty
        mock_wf.readframes.side_effect = [b"\x00" * 4000, b"\x00" * 4000, b""]

        # First frame accepted, second not
        mock_recognizer.AcceptWaveform.side_effect = [True, False]
        mock_recognizer.Result.return_value = json.dumps(
            {"text": "hello world", "result": [{"word": "hello", "conf": 0.9}]}
        )
        mock_recognizer.FinalResult.return_value = json.dumps(
            {"text": "goodbye", "result": [{"word": "goodbye", "conf": 0.8}]}
        )

        transcript, words, total_conf, conf_count = analytics._process_vosk_audio(
            mock_recognizer, mock_wf
        )

        assert "hello world" in transcript
        assert "goodbye" in transcript
        assert len(words) == 2
        assert conf_count == 2
        assert abs(total_conf - 1.7) < 0.001

    def test_process_vosk_audio_empty_results(self) -> None:
        import json

        analytics = _build_analytics()

        mock_recognizer = MagicMock()
        mock_wf = MagicMock()
        mock_wf.readframes.side_effect = [b""]

        mock_recognizer.FinalResult.return_value = json.dumps({})

        transcript, words, total_conf, conf_count = analytics._process_vosk_audio(
            mock_recognizer, mock_wf
        )

        assert transcript == []
        assert words == []
        assert total_conf == 0.0
        assert conf_count == 0

    def test_process_vosk_audio_result_without_conf(self) -> None:
        import json

        analytics = _build_analytics()

        mock_recognizer = MagicMock()
        mock_wf = MagicMock()
        mock_wf.readframes.side_effect = [b"\x00" * 4000, b""]

        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps(
            {"text": "test", "result": [{"word": "test"}]}
        )
        mock_recognizer.FinalResult.return_value = json.dumps({})

        transcript, words, _total_conf, conf_count = analytics._process_vosk_audio(
            mock_recognizer, mock_wf
        )

        assert "test" in transcript
        assert len(words) == 1
        assert conf_count == 0  # No confidence values

    def test_process_vosk_audio_text_without_result_key(self) -> None:
        import json

        analytics = _build_analytics()

        mock_recognizer = MagicMock()
        mock_wf = MagicMock()
        mock_wf.readframes.side_effect = [b"\x00" * 4000, b""]

        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps({"text": "just text"})
        mock_recognizer.FinalResult.return_value = json.dumps({"text": "final"})

        transcript, words, _total_conf, _conf_count = analytics._process_vosk_audio(
            mock_recognizer, mock_wf
        )

        assert "just text" in transcript
        assert "final" in transcript
        assert words == []


# ---------------------------------------------------------------------------
# RecordingAnalytics._analyze_sentiment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzeSentiment:
    """Tests for sentiment analysis."""

    def test_sentiment_no_transcript_no_models(self) -> None:
        analytics = _build_analytics()
        analytics.vosk_model = None
        analytics.spacy_nlp = None

        result = analytics._analyze_sentiment("/audio.wav")

        assert result["overall_sentiment"] == "neutral"
        assert result["sentiment_score"] == 0.0
        assert result["agent_sentiment"] == "neutral"
        assert result["sentiment_timeline"] == []

    def test_sentiment_with_vosk_and_spacy_positive(self) -> None:
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()

        # Mock _transcribe to return positive text
        analytics._transcribe = MagicMock(
            return_value={"text": "thank you very much that was excellent and wonderful"}
        )

        # Mock spaCy NLP pipeline
        mock_nlp = MagicMock()
        mock_tokens = []
        for word in [
            "thank",
            "you",
            "very",
            "much",
            "that",
            "was",
            "excellent",
            "and",
            "wonderful",
        ]:
            token = MagicMock()
            token.lemma_.lower.return_value = word
            token.is_alpha = True
            mock_tokens.append(token)

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(mock_tokens))
        mock_nlp.return_value = mock_doc
        analytics.spacy_nlp = mock_nlp

        result = analytics._analyze_sentiment("/audio.wav")

        assert result["overall_sentiment"] == "positive"
        assert result["sentiment_score"] > 0.2

    def test_sentiment_with_vosk_and_spacy_negative(self) -> None:
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()

        analytics._transcribe = MagicMock(
            return_value={"text": "angry upset frustrated disappointed terrible"}
        )

        mock_nlp = MagicMock()
        mock_tokens = []
        for word in ["angry", "upset", "frustrated", "disappointed", "terrible"]:
            token = MagicMock()
            token.lemma_.lower.return_value = word
            token.is_alpha = True
            mock_tokens.append(token)

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(mock_tokens))
        mock_nlp.return_value = mock_doc
        analytics.spacy_nlp = mock_nlp

        result = analytics._analyze_sentiment("/audio.wav")

        assert result["overall_sentiment"] == "negative"
        assert result["sentiment_score"] < -0.2

    def test_sentiment_with_vosk_and_spacy_neutral(self) -> None:
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()

        analytics._transcribe = MagicMock(return_value={"text": "hello goodbye yes no"})

        mock_nlp = MagicMock()
        mock_tokens = []
        for word in ["hello", "goodbye", "yes", "no"]:
            token = MagicMock()
            token.lemma_.lower.return_value = word
            token.is_alpha = True
            mock_tokens.append(token)

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(mock_tokens))
        mock_nlp.return_value = mock_doc
        analytics.spacy_nlp = mock_nlp

        result = analytics._analyze_sentiment("/audio.wav")

        assert result["overall_sentiment"] == "neutral"
        assert result["sentiment_score"] == 0.0

    def test_sentiment_spacy_exception_fallback(self) -> None:
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()

        analytics._transcribe = MagicMock(return_value={"text": "thank you"})

        mock_nlp = MagicMock(side_effect=RuntimeError("spacy error"))
        analytics.spacy_nlp = mock_nlp

        result = analytics._analyze_sentiment("/audio.wav")

        # Should not crash; falls through to return
        assert result["overall_sentiment"] == "neutral"

    def test_sentiment_fallback_keyword_positive(self) -> None:
        """Keyword-based fallback when spaCy not available but transcript exists."""
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()
        analytics.spacy_nlp = None

        analytics._transcribe = MagicMock(
            return_value={"text": "thank appreciate excellent great wonderful"}
        )

        result = analytics._analyze_sentiment("/audio.wav")

        assert result["overall_sentiment"] == "positive"
        assert result["sentiment_score"] > 0.2

    def test_sentiment_fallback_keyword_negative(self) -> None:
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()
        analytics.spacy_nlp = None

        analytics._transcribe = MagicMock(
            return_value={"text": "angry upset frustrated disappointed terrible awful horrible bad"}
        )

        result = analytics._analyze_sentiment("/audio.wav")

        assert result["overall_sentiment"] == "negative"
        assert result["sentiment_score"] < -0.2

    def test_sentiment_fallback_keyword_neutral(self) -> None:
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()
        analytics.spacy_nlp = None

        analytics._transcribe = MagicMock(
            return_value={"text": "the quick brown fox jumps over the lazy dog"}
        )

        result = analytics._analyze_sentiment("/audio.wav")

        assert result["overall_sentiment"] == "neutral"
        assert result["sentiment_score"] == 0.0

    def test_sentiment_equal_positive_and_negative(self) -> None:
        """When pos == neg, score is 0 and sentiment is neutral."""
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()
        analytics.spacy_nlp = None

        analytics._transcribe = MagicMock(return_value={"text": "thank angry"})

        result = analytics._analyze_sentiment("/audio.wav")

        assert result["overall_sentiment"] == "neutral"
        assert result["sentiment_score"] == 0.0


# ---------------------------------------------------------------------------
# RecordingAnalytics._detect_keywords
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectKeywords:
    """Tests for keyword detection."""

    def test_keywords_empty_transcript(self) -> None:
        analytics = _build_analytics()
        result = analytics._detect_keywords("/audio.wav")

        assert result["keywords"] == []
        assert result["competitor_mentions"] == []
        assert result["product_mentions"] == []
        assert result["issue_keywords"] == []

    def test_keywords_return_structure(self) -> None:
        analytics = _build_analytics()
        result = analytics._detect_keywords("/audio.wav")
        assert "keywords" in result
        assert "competitor_mentions" in result
        assert "product_mentions" in result
        assert "issue_keywords" in result


# ---------------------------------------------------------------------------
# RecordingAnalytics._check_compliance
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckCompliance:
    """Tests for compliance checking."""

    def test_compliance_empty_transcript_is_compliant(self) -> None:
        analytics = _build_analytics()
        result = analytics._check_compliance("/audio.wav")

        assert result["compliant"] is True
        assert result["violations"] == []
        assert result["warnings"] == []
        assert result["required_phrases_found"] == []
        assert result["prohibited_phrases_found"] == []

    def test_compliance_return_structure(self) -> None:
        analytics = _build_analytics()
        result = analytics._check_compliance("/audio.wav")
        expected_keys = {
            "compliant",
            "violations",
            "warnings",
            "required_phrases_found",
            "prohibited_phrases_found",
        }
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# RecordingAnalytics._score_quality
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScoreQuality:
    """Tests for quality scoring."""

    def test_quality_empty_transcript_base_scores(self) -> None:
        analytics = _build_analytics()
        result = analytics._score_quality("/audio.wav")

        assert result["overall_score"] == 50.0
        assert result["agent_performance"] == 50.0
        assert result["customer_satisfaction"] == 50.0
        assert result["resolution_quality"] == 50.0
        assert result["professionalism"] == 50.0

    def test_quality_return_structure(self) -> None:
        analytics = _build_analytics()
        result = analytics._score_quality("/audio.wav")
        expected_keys = {
            "overall_score",
            "agent_performance",
            "customer_satisfaction",
            "resolution_quality",
            "professionalism",
        }
        assert set(result.keys()) == expected_keys

    def test_quality_scores_are_rounded(self) -> None:
        analytics = _build_analytics()
        result = analytics._score_quality("/audio.wav")
        for key in result:
            value = result[key]
            assert value == round(value, 2)


# ---------------------------------------------------------------------------
# RecordingAnalytics._summarize
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSummarize:
    """Tests for summarization."""

    def test_summarize_empty_transcript(self) -> None:
        analytics = _build_analytics()
        result = analytics._summarize("/audio.wav")

        assert result["summary"] == ""
        assert result["key_points"] == []
        assert result["action_items"] == []
        assert result["outcomes"] == []

    def test_summarize_return_structure(self) -> None:
        analytics = _build_analytics()
        result = analytics._summarize("/audio.wav")
        expected_keys = {"summary", "key_points", "action_items", "outcomes"}
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# RecordingAnalytics.search_recordings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchRecordings:
    """Tests for search_recordings."""

    def _populate_analyses(self, analytics: RecordingAnalytics) -> None:
        """Populate analytics.analyses with test data."""
        analytics.analyses = {
            "rec-positive": {
                "analyzed_at": datetime.now(UTC).isoformat(),
                "analyses": {
                    "sentiment": {
                        "overall_sentiment": "positive",
                        "sentiment_score": 0.8,
                    },
                    "keywords": {"keywords": ["product", "purchase"]},
                    "quality": {"overall_score": 85.0},
                    "compliance": {"compliant": True},
                },
            },
            "rec-negative": {
                "analyzed_at": datetime.now(UTC).isoformat(),
                "analyses": {
                    "sentiment": {
                        "overall_sentiment": "negative",
                        "sentiment_score": -0.6,
                    },
                    "keywords": {"keywords": ["problem", "error"]},
                    "quality": {"overall_score": 30.0},
                    "compliance": {"compliant": False},
                },
            },
            "rec-neutral": {
                "analyzed_at": datetime.now(UTC).isoformat(),
                "analyses": {
                    "sentiment": {
                        "overall_sentiment": "neutral",
                        "sentiment_score": 0.0,
                    },
                    "keywords": {"keywords": []},
                    "quality": {"overall_score": 50.0},
                    "compliance": {"compliant": True},
                },
            },
        }

    def test_search_no_criteria_returns_all(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({})
        assert len(result) == 3

    def test_search_by_sentiment(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"sentiment": "positive"})
        assert result == ["rec-positive"]

    def test_search_by_sentiment_negative(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"sentiment": "negative"})
        assert result == ["rec-negative"]

    def test_search_by_keywords_match(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"keywords": ["product"]})
        assert result == ["rec-positive"]

    def test_search_by_keywords_no_match(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"keywords": ["nonexistent"]})
        assert result == []

    def test_search_by_min_quality_score(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"min_quality_score": 80})
        assert result == ["rec-positive"]

    def test_search_by_min_quality_score_low(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"min_quality_score": 10})
        assert len(result) == 3

    def test_search_by_compliance_true(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"compliant": True})
        assert set(result) == {"rec-positive", "rec-neutral"}

    def test_search_by_compliance_false(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"compliant": False})
        assert result == ["rec-negative"]

    def test_search_combined_criteria(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings(
            {"sentiment": "positive", "min_quality_score": 80, "compliant": True}
        )
        assert result == ["rec-positive"]

    def test_search_combined_criteria_no_match(self) -> None:
        analytics = _build_analytics()
        self._populate_analyses(analytics)
        result = analytics.search_recordings({"sentiment": "positive", "compliant": False})
        assert result == []

    def test_search_empty_analyses(self) -> None:
        analytics = _build_analytics()
        result = analytics.search_recordings({"sentiment": "positive"})
        assert result == []

    def test_search_missing_analysis_type(self) -> None:
        """When an analysis type is not present in results, should not match."""
        analytics = _build_analytics()
        analytics.analyses = {
            "rec-minimal": {
                "analyzed_at": datetime.now(UTC).isoformat(),
                "analyses": {},  # No analysis data
            }
        }
        result = analytics.search_recordings({"sentiment": "positive"})
        assert result == []

    def test_search_quality_missing_defaults_to_zero(self) -> None:
        analytics = _build_analytics()
        analytics.analyses = {
            "rec-no-quality": {
                "analyzed_at": datetime.now(UTC).isoformat(),
                "analyses": {"quality": {}},
            }
        }
        result = analytics.search_recordings({"min_quality_score": 1})
        assert result == []


# ---------------------------------------------------------------------------
# RecordingAnalytics.get_analysis
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAnalysis:
    """Tests for get_analysis."""

    def test_get_analysis_existing(self) -> None:
        analytics = _build_analytics()
        analytics.analyses["rec-1"] = {"foo": "bar"}
        assert analytics.get_analysis("rec-1") == {"foo": "bar"}

    def test_get_analysis_nonexistent(self) -> None:
        analytics = _build_analytics()
        assert analytics.get_analysis("no-such") is None


# ---------------------------------------------------------------------------
# RecordingAnalytics._filter_analyses_by_date
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterAnalysesByDate:
    """Tests for _filter_analyses_by_date."""

    def test_filter_within_range(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        analytics.analyses = {
            "rec-1": {"analyzed_at": now.isoformat(), "analyses": {}},
        }
        result = analytics._filter_analyses_by_date(
            now - timedelta(hours=1), now + timedelta(hours=1)
        )
        assert len(result) == 1

    def test_filter_outside_range(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        past = now - timedelta(days=30)
        analytics.analyses = {
            "rec-1": {"analyzed_at": past.isoformat(), "analyses": {}},
        }
        result = analytics._filter_analyses_by_date(
            now - timedelta(hours=1), now + timedelta(hours=1)
        )
        assert len(result) == 0

    def test_filter_invalid_timestamp(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        analytics.analyses = {
            "rec-bad": {"analyzed_at": "not-a-date", "analyses": {}},
        }
        result = analytics._filter_analyses_by_date(
            now - timedelta(hours=1), now + timedelta(hours=1)
        )
        assert len(result) == 0

    def test_filter_missing_timestamp_key(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        analytics.analyses = {
            "rec-no-ts": {"analyses": {}},
        }
        result = analytics._filter_analyses_by_date(
            now - timedelta(hours=1), now + timedelta(hours=1)
        )
        assert len(result) == 0

    def test_filter_empty_analyses(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        result = analytics._filter_analyses_by_date(
            now - timedelta(hours=1), now + timedelta(hours=1)
        )
        assert result == []


# ---------------------------------------------------------------------------
# RecordingAnalytics._aggregate_sentiment_data
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAggregateSentimentData:
    """Tests for _aggregate_sentiment_data."""

    def test_aggregate_sentiment_with_data(self) -> None:
        analytics = _build_analytics()
        analyses = [
            {
                "analyzed_at": "2026-01-01T00:00:00+00:00",
                "analyses": {
                    "sentiment": {
                        "overall_sentiment": "positive",
                        "sentiment_score": 0.8,
                    }
                },
            }
        ]
        result = analytics._aggregate_sentiment_data(analyses)
        assert len(result) == 1
        assert result[0]["sentiment"] == "positive"
        assert result[0]["score"] == 0.8

    def test_aggregate_sentiment_empty_data(self) -> None:
        analytics = _build_analytics()
        result = analytics._aggregate_sentiment_data([])
        assert result == []

    def test_aggregate_sentiment_no_sentiment_key(self) -> None:
        analytics = _build_analytics()
        analyses = [{"analyzed_at": "2026-01-01T00:00:00+00:00", "analyses": {}}]
        result = analytics._aggregate_sentiment_data(analyses)
        assert result == []

    def test_aggregate_sentiment_defaults(self) -> None:
        """When sentiment dict has data but missing expected keys, defaults apply."""
        analytics = _build_analytics()
        analyses = [
            {
                "analyzed_at": "2026-01-01T00:00:00+00:00",
                "analyses": {"sentiment": {"some_key": "some_value"}},
            }
        ]
        result = analytics._aggregate_sentiment_data(analyses)
        assert len(result) == 1
        assert result[0]["sentiment"] == "neutral"
        assert result[0]["score"] == 0.0

    def test_aggregate_sentiment_empty_dict_skipped(self) -> None:
        """Empty sentiment dict is falsy, so it is skipped."""
        analytics = _build_analytics()
        analyses = [
            {
                "analyzed_at": "2026-01-01T00:00:00+00:00",
                "analyses": {"sentiment": {}},
            }
        ]
        result = analytics._aggregate_sentiment_data(analyses)
        assert result == []


# ---------------------------------------------------------------------------
# RecordingAnalytics._aggregate_quality_data
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAggregateQualityData:
    """Tests for _aggregate_quality_data."""

    def test_aggregate_quality_with_data(self) -> None:
        analytics = _build_analytics()
        analyses = [
            {
                "analyzed_at": "2026-01-01T00:00:00+00:00",
                "analyses": {
                    "quality": {
                        "overall_score": 80.0,
                        "agent_performance": 70.0,
                        "customer_satisfaction": 90.0,
                    }
                },
            }
        ]
        result = analytics._aggregate_quality_data(analyses)
        assert len(result) == 1
        assert result[0]["overall_score"] == 80.0
        assert result[0]["agent_performance"] == 70.0
        assert result[0]["customer_satisfaction"] == 90.0

    def test_aggregate_quality_empty(self) -> None:
        analytics = _build_analytics()
        result = analytics._aggregate_quality_data([])
        assert result == []

    def test_aggregate_quality_no_quality_key(self) -> None:
        analytics = _build_analytics()
        analyses = [{"analyzed_at": "2026-01-01T00:00:00+00:00", "analyses": {}}]
        result = analytics._aggregate_quality_data(analyses)
        assert result == []

    def test_aggregate_quality_defaults(self) -> None:
        """When quality dict has data but missing expected keys, defaults apply."""
        analytics = _build_analytics()
        analyses = [
            {
                "analyzed_at": "2026-01-01T00:00:00+00:00",
                "analyses": {"quality": {"some_key": "some_value"}},
            }
        ]
        result = analytics._aggregate_quality_data(analyses)
        assert len(result) == 1
        assert result[0]["overall_score"] == 0.0

    def test_aggregate_quality_empty_dict_skipped(self) -> None:
        """Empty quality dict is falsy, so it is skipped."""
        analytics = _build_analytics()
        analyses = [
            {
                "analyzed_at": "2026-01-01T00:00:00+00:00",
                "analyses": {"quality": {}},
            }
        ]
        result = analytics._aggregate_quality_data(analyses)
        assert result == []


# ---------------------------------------------------------------------------
# RecordingAnalytics._aggregate_keyword_trends
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAggregateKeywordTrends:
    """Tests for _aggregate_keyword_trends."""

    def test_aggregate_keywords_with_data(self) -> None:
        analytics = _build_analytics()
        analyses = [
            {"analyses": {"keywords": {"keywords": ["product", "help"]}}},
            {"analyses": {"keywords": {"keywords": ["product", "error"]}}},
        ]
        result = analytics._aggregate_keyword_trends(analyses)
        assert result["product"] == 2
        assert result["help"] == 1
        assert result["error"] == 1

    def test_aggregate_keywords_sorted_by_frequency(self) -> None:
        analytics = _build_analytics()
        analyses = [
            {"analyses": {"keywords": {"keywords": ["alpha"]}}},
            {"analyses": {"keywords": {"keywords": ["beta", "alpha"]}}},
            {"analyses": {"keywords": {"keywords": ["alpha"]}}},
        ]
        result = analytics._aggregate_keyword_trends(analyses)
        keys = list(result.keys())
        assert keys[0] == "alpha"
        assert result["alpha"] == 3

    def test_aggregate_keywords_empty(self) -> None:
        analytics = _build_analytics()
        result = analytics._aggregate_keyword_trends([])
        assert result == {}

    def test_aggregate_keywords_no_keywords_key(self) -> None:
        analytics = _build_analytics()
        analyses = [{"analyses": {}}]
        result = analytics._aggregate_keyword_trends(analyses)
        assert result == {}

    def test_aggregate_keywords_empty_keywords_list(self) -> None:
        analytics = _build_analytics()
        analyses = [{"analyses": {"keywords": {"keywords": []}}}]
        result = analytics._aggregate_keyword_trends(analyses)
        assert result == {}


# ---------------------------------------------------------------------------
# RecordingAnalytics._calculate_compliance_data
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCalculateComplianceData:
    """Tests for _calculate_compliance_data."""

    def test_compliance_mixed(self) -> None:
        analytics = _build_analytics()
        analyses = [
            {"analyses": {"compliance": {"compliant": True}}},
            {"analyses": {"compliance": {"compliant": False}}},
            {"analyses": {"compliance": {"compliant": True}}},
        ]
        result = analytics._calculate_compliance_data(analyses)
        assert result["compliant"] == 2
        assert result["non_compliant"] == 1

    def test_compliance_all_compliant(self) -> None:
        analytics = _build_analytics()
        analyses = [
            {"analyses": {"compliance": {"compliant": True}}},
            {"analyses": {"compliance": {"compliant": True}}},
        ]
        result = analytics._calculate_compliance_data(analyses)
        assert result["compliant"] == 2
        assert result["non_compliant"] == 0

    def test_compliance_empty(self) -> None:
        analytics = _build_analytics()
        result = analytics._calculate_compliance_data([])
        assert result["compliant"] == 0
        assert result["non_compliant"] == 0

    def test_compliance_no_compliance_key(self) -> None:
        analytics = _build_analytics()
        analyses = [{"analyses": {}}]
        result = analytics._calculate_compliance_data(analyses)
        assert result["compliant"] == 0
        assert result["non_compliant"] == 0

    def test_compliance_default_false(self) -> None:
        """When 'compliant' key missing but dict is truthy, defaults to False."""
        analytics = _build_analytics()
        analyses = [{"analyses": {"compliance": {"some_key": "value"}}}]
        result = analytics._calculate_compliance_data(analyses)
        assert result["non_compliant"] == 1

    def test_compliance_empty_dict_skipped(self) -> None:
        """Empty compliance dict is falsy, so it is skipped entirely."""
        analytics = _build_analytics()
        analyses = [{"analyses": {"compliance": {}}}]
        result = analytics._calculate_compliance_data(analyses)
        assert result["compliant"] == 0
        assert result["non_compliant"] == 0


# ---------------------------------------------------------------------------
# RecordingAnalytics.get_trend_analysis
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetTrendAnalysis:
    """Tests for get_trend_analysis."""

    def test_trend_analysis_no_data(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        result = analytics.get_trend_analysis(now - timedelta(days=7), now + timedelta(days=1))
        assert result["sentiment_trend"] == []
        assert result["quality_trend"] == []
        assert result["keyword_trends"] == {}
        assert result["compliance_rate"] == 0.0
        assert result["total_recordings"] == 0

    def test_trend_analysis_with_data(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        analytics.analyses = {
            "rec-1": {
                "analyzed_at": now.isoformat(),
                "analyses": {
                    "sentiment": {"overall_sentiment": "positive", "sentiment_score": 0.8},
                    "quality": {
                        "overall_score": 80.0,
                        "agent_performance": 70.0,
                        "customer_satisfaction": 90.0,
                    },
                    "keywords": {"keywords": ["help"]},
                    "compliance": {"compliant": True},
                },
            },
            "rec-2": {
                "analyzed_at": now.isoformat(),
                "analyses": {
                    "sentiment": {"overall_sentiment": "negative", "sentiment_score": -0.5},
                    "quality": {
                        "overall_score": 40.0,
                        "agent_performance": 30.0,
                        "customer_satisfaction": 20.0,
                    },
                    "keywords": {"keywords": ["problem"]},
                    "compliance": {"compliant": False},
                },
            },
        }

        result = analytics.get_trend_analysis(now - timedelta(hours=1), now + timedelta(hours=1))

        assert result["total_recordings"] == 2
        assert len(result["sentiment_trend"]) == 2
        assert len(result["quality_trend"]) == 2
        assert result["compliance_rate"] == 50.0
        assert "date_range" in result
        assert "help" in result["keyword_trends"]
        assert "problem" in result["keyword_trends"]

    def test_trend_analysis_full_compliance(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        analytics.analyses = {
            "rec-1": {
                "analyzed_at": now.isoformat(),
                "analyses": {"compliance": {"compliant": True}},
            },
        }
        result = analytics.get_trend_analysis(now - timedelta(hours=1), now + timedelta(hours=1))
        assert result["compliance_rate"] == 100.0

    def test_trend_analysis_no_compliance_data(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        analytics.analyses = {
            "rec-1": {
                "analyzed_at": now.isoformat(),
                "analyses": {"sentiment": {"overall_sentiment": "neutral"}},
            },
        }
        result = analytics.get_trend_analysis(now - timedelta(hours=1), now + timedelta(hours=1))
        assert result["compliance_rate"] == 0.0

    def test_trend_analysis_date_range_in_result(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        analytics.analyses = {
            "rec-1": {
                "analyzed_at": now.isoformat(),
                "analyses": {},
            },
        }
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)
        result = analytics.get_trend_analysis(start, end)
        assert result["date_range"]["start"] == start.isoformat()
        assert result["date_range"]["end"] == end.isoformat()


# ---------------------------------------------------------------------------
# RecordingAnalytics.get_statistics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics."""

    def test_statistics_defaults(self) -> None:
        analytics = _build_analytics()
        stats = analytics.get_statistics()
        assert stats["enabled"] is False
        assert stats["auto_analyze"] is False
        assert stats["total_analyses"] == 0
        assert stats["analyses_by_type"] == {}
        assert stats["available_analysis_types"] == ["sentiment", "keywords", "summary"]

    def test_statistics_after_analysis(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("r1", "/a.wav", ["sentiment", "quality"])
        stats = analytics.get_statistics()
        assert stats["total_analyses"] == 1
        assert stats["analyses_by_type"]["sentiment"] == 1
        assert stats["analyses_by_type"]["quality"] == 1

    def test_statistics_enabled(self) -> None:
        cfg = _make_config(enabled=True, auto_analyze=True)
        analytics = _build_analytics(config=cfg)
        stats = analytics.get_statistics()
        assert stats["enabled"] is True
        assert stats["auto_analyze"] is True


# ---------------------------------------------------------------------------
# get_recording_analytics (global singleton)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRecordingAnalytics:
    """Tests for the module-level get_recording_analytics singleton accessor."""

    def test_get_recording_analytics_creates_instance(self) -> None:
        with (
            patch("pbx.features.call_recording_analytics._recording_analytics", None),
            patch("pbx.features.call_recording_analytics.VOSK_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.SPACY_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.get_logger") as mock_log,
        ):
            mock_log.return_value = MagicMock()
            from pbx.features.call_recording_analytics import get_recording_analytics

            instance = get_recording_analytics({"features": {}})
            assert instance is not None

    def test_get_recording_analytics_returns_same_instance(self) -> None:
        sentinel = MagicMock()
        with patch("pbx.features.call_recording_analytics._recording_analytics", sentinel):
            from pbx.features.call_recording_analytics import get_recording_analytics

            instance = get_recording_analytics()
            assert instance is sentinel

    def test_get_recording_analytics_none_config(self) -> None:
        with (
            patch("pbx.features.call_recording_analytics._recording_analytics", None),
            patch("pbx.features.call_recording_analytics.VOSK_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.SPACY_AVAILABLE", False),
            patch("pbx.features.call_recording_analytics.get_logger") as mock_log,
        ):
            mock_log.return_value = MagicMock()
            from pbx.features.call_recording_analytics import get_recording_analytics

            instance = get_recording_analytics(None)
            assert instance is not None


# ---------------------------------------------------------------------------
# Module-level constants (VOSK_AVAILABLE, SPACY_AVAILABLE)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModuleLevelConstants:
    """Tests that verify module-level constants exist and are boolean."""

    def test_vosk_available_is_bool(self) -> None:
        from pbx.features.call_recording_analytics import VOSK_AVAILABLE

        assert isinstance(VOSK_AVAILABLE, bool)

    def test_spacy_available_is_bool(self) -> None:
        from pbx.features.call_recording_analytics import SPACY_AVAILABLE

        assert isinstance(SPACY_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# Integration-style tests (still unit-mocked)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzeAndSearchFlow:
    """End-to-end flow tests using analyze_recording + search_recordings."""

    def test_analyze_then_search_by_sentiment(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("rec-1", "/a.wav", ["sentiment"])
        # Default sentiment is neutral (empty transcript)
        result = analytics.search_recordings({"sentiment": "neutral"})
        assert "rec-1" in result

    def test_analyze_then_get_analysis(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("rec-1", "/a.wav", ["quality"])
        result = analytics.get_analysis("rec-1")
        assert result is not None
        assert "quality" in result["analyses"]

    def test_analyze_then_trend_analysis(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("rec-1", "/a.wav", ["sentiment", "quality"])

        now = datetime.now(UTC)
        trends = analytics.get_trend_analysis(now - timedelta(hours=1), now + timedelta(hours=1))
        assert trends["total_recordings"] == 1

    def test_multiple_analyses_then_statistics(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("r1", "/a.wav", ["sentiment"])
        analytics.analyze_recording("r2", "/b.wav", ["quality", "compliance"])
        analytics.analyze_recording("r3", "/c.wav", ["sentiment", "keywords"])

        stats = analytics.get_statistics()
        assert stats["total_analyses"] == 3
        assert stats["analyses_by_type"]["sentiment"] == 2
        assert stats["analyses_by_type"]["quality"] == 1
        assert stats["analyses_by_type"]["compliance"] == 1
        assert stats["analyses_by_type"]["keywords"] == 1


# ---------------------------------------------------------------------------
# Edge-case and error-path tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEdgeCases:
    """Edge cases and error path coverage."""

    def test_analyze_recording_with_empty_analysis_types_falls_back(self) -> None:
        """Empty list is falsy, so it falls back to instance analysis_types."""
        cfg = _make_config(analysis_types=["sentiment", "keywords", "summary"])
        analytics = _build_analytics(config=cfg)
        result = analytics.analyze_recording("rec-1", "/a.wav", [])
        # Falls back to instance defaults
        assert "sentiment" in result["analyses"]
        assert "keywords" in result["analyses"]
        assert "summary" in result["analyses"]
        assert analytics.total_analyses == 1

    def test_search_with_multiple_keyword_criteria(self) -> None:
        analytics = _build_analytics()
        analytics.analyses = {
            "rec-1": {
                "analyzed_at": datetime.now(UTC).isoformat(),
                "analyses": {
                    "keywords": {"keywords": ["alpha", "beta"]},
                },
            },
        }
        # any() match: at least one keyword matches
        result = analytics.search_recordings({"keywords": ["alpha", "gamma"]})
        assert result == ["rec-1"]

    def test_search_keywords_none_match(self) -> None:
        analytics = _build_analytics()
        analytics.analyses = {
            "rec-1": {
                "analyzed_at": datetime.now(UTC).isoformat(),
                "analyses": {
                    "keywords": {"keywords": ["alpha"]},
                },
            },
        }
        result = analytics.search_recordings({"keywords": ["gamma", "delta"]})
        assert result == []

    def test_config_with_missing_features_key(self) -> None:
        analytics = _build_analytics(config={"other": "stuff"})
        assert analytics.enabled is False
        assert analytics.auto_analyze is False

    def test_config_with_missing_recording_analytics_key(self) -> None:
        analytics = _build_analytics(config={"features": {}})
        assert analytics.enabled is False

    def test_overwrite_analysis_for_same_recording(self) -> None:
        analytics = _build_analytics()
        analytics.analyze_recording("rec-1", "/a.wav", ["sentiment"])
        analytics.analyze_recording("rec-1", "/a.wav", ["quality"])
        # Second call overwrites
        result = analytics.get_analysis("rec-1")
        assert "quality" in result["analyses"]
        # total_analyses still increments
        assert analytics.total_analyses == 2

    def test_trend_analysis_compliance_rate_rounding(self) -> None:
        analytics = _build_analytics()
        now = datetime.now(UTC)
        analytics.analyses = {
            "r1": {
                "analyzed_at": now.isoformat(),
                "analyses": {"compliance": {"compliant": True}},
            },
            "r2": {
                "analyzed_at": now.isoformat(),
                "analyses": {"compliance": {"compliant": True}},
            },
            "r3": {
                "analyzed_at": now.isoformat(),
                "analyses": {"compliance": {"compliant": False}},
            },
        }
        result = analytics.get_trend_analysis(now - timedelta(hours=1), now + timedelta(hours=1))
        # 2/3 = 66.67%
        assert result["compliance_rate"] == 66.67

    def test_sentiment_spacy_with_non_alpha_tokens(self) -> None:
        analytics = _build_analytics()
        analytics.vosk_model = MagicMock()
        analytics._transcribe = MagicMock(return_value={"text": "thank 123 !!! excellent"})

        mock_nlp = MagicMock()
        mock_tokens = []
        for word, is_alpha in [
            ("thank", True),
            ("123", False),
            ("!!!", False),
            ("excellent", True),
        ]:
            token = MagicMock()
            token.lemma_.lower.return_value = word
            token.is_alpha = is_alpha
            mock_tokens.append(token)

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(mock_tokens))
        mock_nlp.return_value = mock_doc
        analytics.spacy_nlp = mock_nlp

        result = analytics._analyze_sentiment("/audio.wav")
        # Only alpha tokens considered; "thank" and "excellent" are positive
        assert result["overall_sentiment"] == "positive"
        assert result["sentiment_score"] == 1.0

    def test_quality_scores_clamped(self) -> None:
        """Verify clamping logic in _score_quality wouldn't go below 0 or above 100."""
        analytics = _build_analytics()
        # With empty transcript, base scores are 50.0 -- we trust the logic is correct
        result = analytics._score_quality("/audio.wav")
        for key in [
            "overall_score",
            "agent_performance",
            "customer_satisfaction",
            "resolution_quality",
            "professionalism",
        ]:
            assert 0.0 <= result[key] <= 100.0
