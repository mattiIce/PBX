#!/usr/bin/env python3
"""
Comprehensive tests for Conversational AI Assistant (pbx/features/conversational_ai.py).

Covers:
- ConversationContext dataclass
- ConversationalAI initialization with various configs
- NLTK initialization (available / unavailable / error paths)
- Conversation lifecycle (start, process, end)
- Intent detection (NLTK-enhanced and pattern-based fallback)
- Confidence scoring
- Entity extraction (phones, emails, extensions, departments, times, numbers)
- Tokenization (NLTK and fallback)
- Response generation and context-aware branching
- Provider configuration
- Statistics and history retrieval
- Global singleton accessor
- Database integration paths
"""

import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: since NLTK may not be installed, the module-level names
# (nltk, WordNetLemmatizer, stopwords, word_tokenize) will not exist as
# attributes on the conversational_ai module.  We must use create=True
# when patching them so the mock creates the attribute if absent.
# ---------------------------------------------------------------------------

MODULE = "pbx.features.conversational_ai"


@pytest.mark.unit
class TestConversationContext:
    """Tests for the ConversationContext class."""

    def test_init_sets_fields(self) -> None:
        from pbx.features.conversational_ai import ConversationContext

        ctx = ConversationContext("call-1", "555-0001")

        assert ctx.call_id == "call-1"
        assert ctx.caller_id == "555-0001"
        assert ctx.messages == []
        assert ctx.intent is None
        assert ctx.entities == {}
        assert isinstance(ctx.started_at, datetime)
        assert ctx.started_at.tzinfo is not None

    def test_add_message_appends(self) -> None:
        from pbx.features.conversational_ai import ConversationContext

        ctx = ConversationContext("call-2", "555-0002")
        ctx.add_message("user", "hello")

        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "user"
        assert ctx.messages[0]["content"] == "hello"
        assert "timestamp" in ctx.messages[0]

    def test_add_multiple_messages(self) -> None:
        from pbx.features.conversational_ai import ConversationContext

        ctx = ConversationContext("call-3", "555-0003")
        ctx.add_message("user", "hello")
        ctx.add_message("assistant", "hi there")
        ctx.add_message("user", "help me")

        assert len(ctx.messages) == 3
        assert ctx.messages[0]["role"] == "user"
        assert ctx.messages[1]["role"] == "assistant"
        assert ctx.messages[2]["content"] == "help me"

    def test_started_at_is_utc(self) -> None:
        from pbx.features.conversational_ai import ConversationContext

        ctx = ConversationContext("call-4", "555-0004")
        assert ctx.started_at.tzinfo == UTC


@pytest.mark.unit
class TestConversationalAIInit:
    """Tests for ConversationalAI initialization."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_init_default_config(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()

        assert ai.config == {}
        assert ai.db_backend is None
        assert ai.db is None
        assert ai.enabled is False
        assert ai.provider == "nltk"
        assert ai.model == "gpt-4"
        assert ai.max_tokens == 150
        assert ai.temperature == 0.7
        assert ai.active_conversations == {}
        assert ai.conversation_ids == {}
        assert ai.total_conversations == 0
        assert ai.total_messages_processed == 0
        assert ai.intents_detected == {}

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_init_with_custom_config(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {
            "features": {
                "conversational_ai": {
                    "enabled": True,
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 200,
                    "temperature": 0.5,
                }
            }
        }
        ai = ConversationalAI(config=config)

        assert ai.enabled is True
        assert ai.provider == "openai"
        assert ai.model == "gpt-3.5-turbo"
        assert ai.max_tokens == 200
        assert ai.temperature == 0.5

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_init_with_none_config_uses_empty_dict(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI(config=None)
        assert ai.config == {}

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_init_with_db_backend_enabled(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_db_backend = MagicMock()
        mock_db_backend.enabled = True

        mock_db_instance = MagicMock()

        with patch(
            "pbx.features.conversational_ai_db.ConversationalAIDatabase",
            return_value=mock_db_instance,
        ):
            ai = ConversationalAI(db_backend=mock_db_backend)

        assert ai.db is not None
        mock_db_instance.create_tables.assert_called_once()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_init_with_db_backend_disabled(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_db_backend = MagicMock()
        mock_db_backend.enabled = False

        ai = ConversationalAI(db_backend=mock_db_backend)
        assert ai.db is None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_init_db_backend_sqlite_error(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_db_backend = MagicMock()
        mock_db_backend.enabled = True

        with patch(
            "pbx.features.conversational_ai_db.ConversationalAIDatabase",
            side_effect=sqlite3.Error("db error"),
        ):
            ai = ConversationalAI(db_backend=mock_db_backend)

        assert ai.db is None


@pytest.mark.unit
class TestNLTKInitialization:
    """Tests for NLTK initialization paths."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_nltk_not_available(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.lemmatizer is None
        assert ai.stop_words is None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_nltk_available_all_data_present(
        self, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_stopwords.words.return_value = ["the", "is", "a"]
        mock_lemmatizer_instance = MagicMock()
        mock_lemmatizer_cls.return_value = mock_lemmatizer_instance

        # nltk.data.find succeeds (data already present)
        mock_nltk.data.find.return_value = True

        ai = ConversationalAI()

        assert ai.lemmatizer is mock_lemmatizer_instance
        assert ai.stop_words == {"the", "is", "a"}
        # Should not download anything since data.find succeeds
        mock_nltk.download.assert_not_called()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_nltk_download_punkt_on_lookup_error(
        self, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_stopwords.words.return_value = ["the"]
        mock_lemmatizer_cls.return_value = MagicMock()

        # First call (punkt) raises LookupError; others succeed
        mock_nltk.data.find.side_effect = [
            LookupError("punkt not found"),
            True,
            True,
        ]

        ai = ConversationalAI()

        mock_nltk.download.assert_called_once_with("punkt", quiet=True)
        assert ai.lemmatizer is not None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_nltk_download_stopwords_on_lookup_error(
        self, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_stopwords.words.return_value = ["the"]
        mock_lemmatizer_cls.return_value = MagicMock()

        # Second call (stopwords) raises LookupError
        mock_nltk.data.find.side_effect = [
            True,
            LookupError("stopwords not found"),
            True,
        ]

        ai = ConversationalAI()

        mock_nltk.download.assert_called_once_with("stopwords", quiet=True)

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_nltk_download_wordnet_on_lookup_error(
        self, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_stopwords.words.return_value = ["the"]
        mock_lemmatizer_cls.return_value = MagicMock()

        # Third call (wordnet) raises LookupError
        mock_nltk.data.find.side_effect = [
            True,
            True,
            LookupError("wordnet not found"),
        ]

        ai = ConversationalAI()

        mock_nltk.download.assert_called_once_with("wordnet", quiet=True)

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_nltk_all_three_downloads_needed(
        self, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_stopwords.words.return_value = ["the"]
        mock_lemmatizer_cls.return_value = MagicMock()

        mock_nltk.data.find.side_effect = [
            LookupError("punkt"),
            LookupError("stopwords"),
            LookupError("wordnet"),
        ]

        ai = ConversationalAI()

        assert mock_nltk.download.call_count == 3

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True, side_effect=Exception("init fail"))
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_nltk_init_exception_falls_back(
        self, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_nltk.data.find.return_value = True

        ai = ConversationalAI()

        assert ai.lemmatizer is None
        assert ai.stop_words is None


@pytest.mark.unit
class TestStartConversation:
    """Tests for starting conversations."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_start_conversation_creates_context(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ctx = ai.start_conversation("call-100", "555-9999")

        assert ctx.call_id == "call-100"
        assert ctx.caller_id == "555-9999"
        assert "call-100" in ai.active_conversations
        assert ai.total_conversations == 1

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_start_multiple_conversations(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.start_conversation("call-2", "555-0002")

        assert ai.total_conversations == 2
        assert len(ai.active_conversations) == 2

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_start_conversation_with_db(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.save_conversation.return_value = 42

        ai.start_conversation("call-db", "555-1111")

        ai.db.save_conversation.assert_called_once()
        assert ai.conversation_ids["call-db"] == 42

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_start_conversation_db_returns_none(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.save_conversation.return_value = None

        ai.start_conversation("call-db-none", "555-2222")

        assert "call-db-none" not in ai.conversation_ids


@pytest.mark.unit
class TestProcessUserInput:
    """Tests for processing user input."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_process_unknown_call_id(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        result = ai.process_user_input("nonexistent", "hello")

        assert result["intent"] == "unknown"
        assert "don't have context" in result["response"]
        assert result["entities"] == {}

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_process_valid_input(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "I want to purchase something")

        assert "response" in result
        assert "intent" in result
        assert "entities" in result
        assert "confidence" in result
        assert ai.total_messages_processed == 1

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_process_input_updates_context(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "billing question")

        ctx = ai.active_conversations["call-1"]
        # Two messages: user + assistant
        assert len(ctx.messages) == 2
        assert ctx.messages[0]["role"] == "user"
        assert ctx.messages[1]["role"] == "assistant"
        assert ctx.intent is not None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_process_input_tracks_intents(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "emergency help now")

        assert "emergency_request" in ai.intents_detected
        assert ai.intents_detected["emergency_request"] == 1

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_process_input_with_db_saves_messages_and_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.save_conversation.return_value = 10

        ai.start_conversation("call-db", "555-0001")
        ai.process_user_input("call-db", "emergency help now")

        # Should save 2 messages (user + assistant)
        assert ai.db.save_message.call_count == 2
        # Emergency should trigger save_intent
        ai.db.save_intent.assert_called_once()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_process_input_general_inquiry_skips_intent_save(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.save_conversation.return_value = 10

        ai.start_conversation("call-db", "555-0001")
        # "foo bar" does not match any intent pattern -> general_inquiry
        ai.process_user_input("call-db", "foo bar baz")

        ai.db.save_intent.assert_not_called()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_process_input_without_conversation_id_in_mapping(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        # No conversation_id mapping (db.save_conversation not called)
        ai.start_conversation("call-no-id", "555-0001")
        # Remove the conversation_id mapping to simulate missing ID
        ai.conversation_ids.pop("call-no-id", None)

        ai.process_user_input("call-no-id", "hello")

        ai.db.save_message.assert_not_called()


@pytest.mark.unit
class TestEndConversation:
    """Tests for ending conversations."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_end_conversation_removes_from_active(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.end_conversation("call-1")

        assert "call-1" not in ai.active_conversations

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_end_conversation_nonexistent_call_id(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        # Should not raise
        ai.end_conversation("nonexistent")

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_end_conversation_with_db(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.save_conversation.return_value = 7

        ai.start_conversation("call-db-end", "555-0001")
        ai.process_user_input("call-db-end", "billing question")
        ai.end_conversation("call-db-end")

        ai.db.end_conversation.assert_called_once()
        assert "call-db-end" not in ai.conversation_ids

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_end_conversation_with_no_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()

        ai.start_conversation("call-no-intent", "555-0001")
        # End without processing any input (intent is None)
        ai.end_conversation("call-no-intent")

        ai.db.end_conversation.assert_called_once_with("call-no-intent", "unknown", 0)

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_end_conversation_cleans_conversation_ids(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.save_conversation.return_value = 55

        ai.start_conversation("call-clean", "555-0001")
        assert "call-clean" in ai.conversation_ids

        ai.end_conversation("call-clean")
        assert "call-clean" not in ai.conversation_ids


@pytest.mark.unit
class TestDetectIntent:
    """Tests for intent detection via pattern matching (non-NLTK fallback)."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_emergency_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("This is an emergency") == "emergency_request"
        assert ai.detect_intent("Call 911 right now") == "emergency_request"
        assert ai.detect_intent("I need urgent help") == "emergency_request"
        assert ai.detect_intent("Help now please") == "emergency_request"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_transfer_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("Please transfer me") == "transfer_request"
        assert ai.detect_intent("I want to speak to someone") == "transfer_request"
        assert ai.detect_intent("Connect me to the right person") == "transfer_request"
        assert ai.detect_intent("Put me through to a rep") == "transfer_request"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_sales_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        # Use inputs that only hit sales keywords, not transfer keywords
        assert ai.detect_intent("sales department") == "sales_department"
        assert ai.detect_intent("I'd like to purchase something") == "sales_department"
        assert ai.detect_intent("I want to buy a product") == "sales_department"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_support_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("I need support") == "support_department"
        assert ai.detect_intent("I have a technical issue") == "support_department"
        assert ai.detect_intent("tech support please") == "support_department"
        assert ai.detect_intent("help desk please") == "support_department"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_billing_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("I have a billing question") == "billing_department"
        assert ai.detect_intent("What about my payment") == "billing_department"
        assert ai.detect_intent("I need to check my invoice") == "billing_department"
        assert ai.detect_intent("My account has an issue") == "billing_department"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_business_hours_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("What are your hours") == "business_hours_inquiry"
        assert ai.detect_intent("Are you open today") == "business_hours_inquiry"
        assert ai.detect_intent("When are you available") == "business_hours_inquiry"
        assert ai.detect_intent("What is the schedule") == "business_hours_inquiry"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_location_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("What is your location") == "location_inquiry"
        assert ai.detect_intent("What is the address") == "location_inquiry"
        assert ai.detect_intent("Can I get directions") == "location_inquiry"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_pricing_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("What is the price") == "pricing_inquiry"
        assert ai.detect_intent("How much does it cost") == "pricing_inquiry"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_voicemail_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("Send me to voicemail") == "voicemail_request"
        assert ai.detect_intent("Leave a message") == "voicemail_request"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_callback_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("Please call back later") == "callback_request"
        assert ai.detect_intent("I need a callback") == "callback_request"
        assert ai.detect_intent("Can you call me back") == "callback_request"
        assert ai.detect_intent("Return call please") == "callback_request"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_complaint_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("I have a complaint") == "complaint"
        assert ai.detect_intent("I am unhappy with the service") == "complaint"
        assert ai.detect_intent("I am dissatisfied") == "complaint"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_cancel_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("Cancel the request") == "cancel_request"
        assert ai.detect_intent("Nevermind") == "cancel_request"
        assert ai.detect_intent("Just forget it") == "cancel_request"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_gratitude_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("Thank you very much") == "gratitude"
        assert ai.detect_intent("Thanks a lot") == "gratitude"
        assert ai.detect_intent("I appreciate your effort") == "gratitude"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_affirmation_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("Yes please") == "affirmation"
        assert ai.detect_intent("Yeah that works") == "affirmation"
        assert ai.detect_intent("Sure thing") == "affirmation"
        assert ai.detect_intent("That is correct") == "affirmation"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_negation_intent(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        # "no" alone triggers negation; "no thanks" triggers gratitude first
        # because "thanks" matches before "no" in the pattern list.
        # "incorrect" contains "correct" which matches affirmation first.
        assert ai.detect_intent("Nope") == "negation"
        assert ai.detect_intent("That is not what I wanted") == "negation"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_negation_intent_no_keyword(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        # "no" by itself triggers negation
        assert ai.detect_intent("no") == "negation"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_general_inquiry_fallback(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("lorem ipsum dolor sit amet") == "general_inquiry"
        assert ai.detect_intent("xyzzy") == "general_inquiry"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.word_tokenize", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_detect_intent_nltk_enhanced_path(
        self, mock_word_tokenize, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_nltk.data.find.return_value = True
        mock_stopwords.words.return_value = ["the", "is", "a", "to", "i", "an"]
        mock_lemmatizer = MagicMock()
        mock_lemmatizer_cls.return_value = mock_lemmatizer
        mock_lemmatizer.lemmatize.side_effect = lambda w: w

        ai = ConversationalAI()

        # word_tokenize returns tokens including emergency keyword
        mock_word_tokenize.return_value = ["this", "is", "an", "emergency"]
        result = ai.detect_intent("This is an emergency")

        assert result == "emergency_request"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.word_tokenize", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_detect_intent_nltk_error_falls_back_to_patterns(
        self, mock_word_tokenize, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_nltk.data.find.return_value = True
        mock_stopwords.words.return_value = ["the"]
        mock_lemmatizer = MagicMock()
        mock_lemmatizer_cls.return_value = mock_lemmatizer

        ai = ConversationalAI()

        # word_tokenize raises an error -> falls back to pattern matching
        mock_word_tokenize.side_effect = ValueError("tokenize error")
        result = ai.detect_intent("I need support")

        # Should fall through to standard patterns
        assert result == "support_department"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.word_tokenize", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_detect_intent_nltk_no_match_falls_to_patterns(
        self, mock_word_tokenize, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_nltk.data.find.return_value = True
        mock_stopwords.words.return_value = []
        mock_lemmatizer = MagicMock()
        mock_lemmatizer_cls.return_value = mock_lemmatizer
        mock_lemmatizer.lemmatize.side_effect = lambda w: w

        ai = ConversationalAI()

        # Returns tokens that do NOT match any NLTK patterns but DO match standard patterns
        mock_word_tokenize.return_value = ["dissatisfied"]
        # "dissatisfied" is not in NLTK intent patterns, but IS in standard patterns
        result = ai.detect_intent("I am dissatisfied")

        assert result == "complaint"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_priority_emergency_over_all(self, mock_get_logger) -> None:
        """Emergency patterns should match first due to priority ordering."""
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        # "emergency" + "support" - emergency comes first in the list
        assert ai.detect_intent("emergency support needed") == "emergency_request"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_priority_transfer_over_sales(self, mock_get_logger) -> None:
        """Transfer patterns should match before sales when both are present."""
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        # "speak to" triggers transfer before "sales"
        assert ai.detect_intent("I want to speak to sales") == "transfer_request"


@pytest.mark.unit
class TestDetectIntentWithConfidence:
    """Tests for intent detection with confidence scoring."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_base_confidence_for_non_strong_indicator(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("what are your hours")

        assert intent == "business_hours_inquiry"
        assert confidence == 0.75

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_high_confidence_for_strong_indicator_emergency(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("this is an emergency")

        assert intent == "emergency_request"
        assert confidence == 0.95

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_high_confidence_for_strong_indicator_911(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("call 911")

        assert intent == "emergency_request"
        assert confidence == 0.95

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_high_confidence_transfer_request(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("transfer to accounting")

        assert intent == "transfer_request"
        assert confidence == 0.95

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_high_confidence_sales(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("I want to purchase a product")

        assert intent == "sales_department"
        assert confidence == 0.95

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_high_confidence_support(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("I need tech support")

        assert intent == "support_department"
        assert confidence == 0.95

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_high_confidence_billing(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("about my billing")

        assert intent == "billing_department"
        assert confidence == 0.95

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_high_confidence_callback(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("please call me back")

        assert intent == "callback_request"
        assert confidence == 0.95

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_high_confidence_complaint(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("I have a complaint")

        assert intent == "complaint"
        assert confidence == 0.95

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_base_confidence_general_inquiry(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        intent, confidence = ai._detect_intent_with_confidence("lorem ipsum dolor")

        assert intent == "general_inquiry"
        assert confidence == 0.75


@pytest.mark.unit
class TestExtractEntities:
    """Tests for entity extraction."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_phone_number_dashed(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Call me at 555-123-4567")

        assert "phone_numbers" in entities
        assert "555-123-4567" in entities["phone_numbers"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_phone_number_dots(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Call me at 555.123.4567")

        assert "phone_numbers" in entities
        assert "555.123.4567" in entities["phone_numbers"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_phone_number_no_separators(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Call me at 5551234567")

        assert "phone_numbers" in entities
        assert "5551234567" in entities["phone_numbers"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_short_phone_number(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Call me at 555-1234")

        assert "phone_numbers" in entities
        assert "555-1234" in entities["phone_numbers"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_phone_number_with_country_code(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Call me at 1-555-123-4567")

        assert "phone_numbers" in entities
        assert "1-555-123-4567" in entities["phone_numbers"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_email(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Send it to user@example.com please")

        assert "emails" in entities
        assert "user@example.com" in entities["emails"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_extension(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Transfer to ext 1001")

        assert "extensions" in entities
        assert "1001" in entities["extensions"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_extension_full_word(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Transfer to extension 2005")

        assert "extensions" in entities
        assert "2005" in entities["extensions"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_extension_x_prefix(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Transfer to x1001")

        assert "extensions" in entities
        assert "1001" in entities["extensions"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_departments(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()

        assert "sales" in ai.extract_entities("Talk to sales")["departments"]
        assert "support" in ai.extract_entities("I need tech support")["departments"]
        assert "billing" in ai.extract_entities("About my billing")["departments"]
        assert "hr" in ai.extract_entities("human resources department")["departments"]
        assert "management" in ai.extract_entities("I want a manager")["departments"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_multiple_departments(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("I need sales and support")

        assert "sales" in entities["departments"]
        assert "support" in entities["departments"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_time_with_am_pm(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("Call me at 3:30 PM")

        assert "times" in entities
        assert "3:30 PM" in entities["times"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_time_without_am_pm(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("The meeting is at 14:30 sharp")

        assert "times" in entities
        # Without am/pm, the third group is empty string, so result is "14:30 "
        assert any("14:30" in t for t in entities["times"])

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_numbers(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("My order number is 12345")

        assert "numbers" in entities
        assert "12345" in entities["numbers"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_no_entities(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("hello there")

        assert entities == {}

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_multiple_entity_types(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities(
            "Call me at 555-123-4567 or email user@example.com about my sales order 98765"
        )

        assert "phone_numbers" in entities
        assert "emails" in entities
        assert "departments" in entities
        assert "numbers" in entities


@pytest.mark.unit
class TestGenerateResponse:
    """Tests for response generation with context-aware branching."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_emergency_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "This is an emergency")

        assert "emergency" in result["response"].lower()
        assert result["confidence"] == 1.0

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_transfer_request_response_with_department(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "Transfer me to billing please")

        assert "transfer" in result["response"].lower() or "billing" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_sales_department_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "sales department please")

        assert "sales" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_support_department_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "tech support please")

        assert "support" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_billing_department_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "billing question")

        assert "billing" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_business_hours_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "What are your hours?")

        assert "hours" in result["response"].lower() or "monday" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_location_inquiry_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "Where is your location?")

        assert "office" in result["response"].lower() or "address" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_pricing_inquiry_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "How much does it cost?")

        assert "pricing" in result["response"].lower() or "sales" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_voicemail_request_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "Send me to voicemail")

        assert "voicemail" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_callback_request_with_phone_number(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "Call me back at 555-123-4567")

        assert "callback" in result["response"].lower() or "call" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_callback_request_without_phone_number(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "Can you call me back?")

        assert "callback" in result["response"].lower() or "call" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_complaint_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "I have a complaint")

        assert "sorry" in result["response"].lower() or "supervisor" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_cancel_request_response(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "Cancel that please")

        assert result["intent"] == "cancel_request"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_gratitude_short_conversation(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "Thank you")

        assert "welcome" in result["response"].lower()
        assert result["intent"] == "gratitude"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_gratitude_long_conversation(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        # Add messages to make message_count > 3
        ctx = ai.active_conversations["call-1"]
        ctx.add_message("user", "hello")
        ctx.add_message("assistant", "hi")
        ctx.add_message("user", "question")
        ctx.add_message("assistant", "answer")

        result = ai.process_user_input("call-1", "Thank you so much")

        assert "welcome" in result["response"].lower()
        assert "happy" in result["response"].lower() or "anything" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_affirmation_after_callback_request(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "Can you call me back?")

        result = ai.process_user_input("call-1", "Yes please")

        assert result["intent"] == "affirmation"
        assert "call you back" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_affirmation_after_transfer_request(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "Transfer me please")

        result = ai.process_user_input("call-1", "Yes")

        assert result["intent"] == "affirmation"
        assert "transfer" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_affirmation_after_sales_department(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "sales department")

        result = ai.process_user_input("call-1", "Yeah sure")

        assert result["intent"] == "affirmation"
        assert "transfer" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_affirmation_after_support_department(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "tech support please")

        result = ai.process_user_input("call-1", "Sure thing")

        assert result["intent"] == "affirmation"
        assert "transfer" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_affirmation_generic(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        # Process something that is not callback/transfer/sales/support
        ai.process_user_input("call-1", "What are your hours?")

        result = ai.process_user_input("call-1", "Okay sure")

        assert result["intent"] == "affirmation"
        assert "help" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_negation_after_callback_request(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "Can you call me back?")

        # Use "nope" which cleanly triggers negation (no conflicting keywords)
        result = ai.process_user_input("call-1", "Nope")

        assert result["intent"] == "negation"
        assert "prefer" in result["response"].lower() or "instead" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_negation_after_location_inquiry(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "What is your location?")

        result = ai.process_user_input("call-1", "No")

        assert result["intent"] == "negation"
        assert (
            "information" in result["response"].lower()
            or "provide" in result["response"].lower()
        )

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_negation_after_business_hours(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "What are your hours?")

        result = ai.process_user_input("call-1", "Nope")

        assert result["intent"] == "negation"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_negation_generic(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        # Set a non-special previous intent
        ai.process_user_input("call-1", "I have a complaint")

        result = ai.process_user_input("call-1", "No")

        assert result["intent"] == "negation"
        assert "instead" in result["response"].lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_general_inquiry_early_conversation(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "lorem ipsum dolor")

        assert "help" in result["response"].lower()
        assert result["intent"] == "general_inquiry"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_general_inquiry_late_conversation(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        # Add messages to make message_count > 2
        ctx = ai.active_conversations["call-1"]
        ctx.add_message("user", "first")
        ctx.add_message("assistant", "reply")
        ctx.add_message("user", "second")

        result = ai.process_user_input("call-1", "xyzzy foobar")

        assert "assist" in result["response"].lower()


@pytest.mark.unit
class TestBuildResponseHandlers:
    """Tests for the response handler mapping."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_handlers_return_dict(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()

        assert isinstance(handlers, dict)
        expected_keys = [
            "emergency_request",
            "transfer_request",
            "sales_department",
            "support_department",
            "billing_department",
            "business_hours_inquiry",
            "location_inquiry",
            "pricing_inquiry",
            "voicemail_request",
            "callback_request",
            "complaint",
            "cancel_request",
        ]
        for key in expected_keys:
            assert key in handlers

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_emergency_handler_returns_confidence_1(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()
        response, confidence = handlers["emergency_request"]({})

        assert "emergency" in response.lower()
        assert confidence == 1.0

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_transfer_handler_with_department(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()
        response, confidence = handlers["transfer_request"]({"departments": ["billing"]})

        assert "billing" in response.lower()
        assert confidence is None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_transfer_handler_without_department(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()
        response, confidence = handlers["transfer_request"]({})

        assert "general" in response.lower()
        assert confidence is None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_transfer_handler_with_empty_departments_list(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()
        response, confidence = handlers["transfer_request"]({"departments": []})

        assert "general" in response.lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_callback_handler_with_phone(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()
        response, confidence = handlers["callback_request"](
            {"phone_numbers": ["555-123-4567"]}
        )

        assert "555-123-4567" in response
        assert confidence is None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_callback_handler_without_phone(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()
        response, confidence = handlers["callback_request"]({})

        assert "best number" in response.lower()
        assert confidence is None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_callback_handler_with_empty_phone_list(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()
        response, confidence = handlers["callback_request"]({"phone_numbers": [None]})

        assert "best number" in response.lower()

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_all_handlers_return_tuples(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        handlers = ai._build_response_handlers()

        for intent_name, handler in handlers.items():
            result = handler({})
            assert isinstance(result, tuple), f"Handler for {intent_name} should return tuple"
            assert len(result) == 2, f"Handler for {intent_name} should return 2-element tuple"
            assert isinstance(result[0], str), f"Response for {intent_name} should be a string"


@pytest.mark.unit
class TestTokenizeWithNLTK:
    """Tests for NLTK tokenization."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_tokenize_fallback_without_nltk(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        result = ai.tokenize_with_nltk("Hello World Test")

        assert result == ["hello", "world", "test"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.word_tokenize", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_tokenize_with_nltk_available(
        self, mock_word_tokenize, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_nltk.data.find.return_value = True
        mock_stopwords.words.return_value = ["the", "is"]
        mock_lemmatizer = MagicMock()
        mock_lemmatizer_cls.return_value = mock_lemmatizer
        mock_lemmatizer.lemmatize.side_effect = lambda w: w

        ai = ConversationalAI()

        mock_word_tokenize.return_value = ["hello", "world", "the", ".", "test"]
        result = ai.tokenize_with_nltk("hello world the . test")

        # Should exclude "the" (stop word) and "." (not alpha)
        assert "the" not in result
        assert "." not in result
        assert "hello" in result
        assert "world" in result
        assert "test" in result

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.word_tokenize", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_tokenize_nltk_error_falls_back(
        self, mock_word_tokenize, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_nltk.data.find.return_value = True
        mock_stopwords.words.return_value = []
        mock_lemmatizer = MagicMock()
        mock_lemmatizer_cls.return_value = mock_lemmatizer

        ai = ConversationalAI()

        mock_word_tokenize.side_effect = RuntimeError("tokenize error")
        result = ai.tokenize_with_nltk("Hello World")

        assert result == ["hello", "world"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_tokenize_fallback_with_no_lemmatizer(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.lemmatizer = None
        ai.stop_words = None

        result = ai.tokenize_with_nltk("Testing Fallback Tokenization")
        assert result == ["testing", "fallback", "tokenization"]


@pytest.mark.unit
class TestGetStatistics:
    """Tests for statistics retrieval."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_statistics_default(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        stats = ai.get_statistics()

        assert stats["total_conversations"] == 0
        assert stats["active_conversations"] == 0
        assert stats["total_messages_processed"] == 0
        assert stats["intents_detected"] == {}
        assert stats["provider"] == "nltk"
        assert stats["model"] == "gpt-4"
        assert stats["enabled"] is False
        assert stats["nltk_available"] is False

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_statistics_after_conversations(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ai.process_user_input("call-1", "emergency help")

        stats = ai.get_statistics()

        assert stats["total_conversations"] == 1
        assert stats["active_conversations"] == 1
        assert stats["total_messages_processed"] == 1
        assert "emergency_request" in stats["intents_detected"]

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_statistics_with_db(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.get_intent_statistics.return_value = {"sales_department": 5}

        stats = ai.get_statistics()

        assert "intent_statistics_db" in stats
        assert stats["intent_statistics_db"] == {"sales_department": 5}

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_statistics_with_db_no_stats(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.get_intent_statistics.return_value = None

        stats = ai.get_statistics()

        assert "intent_statistics_db" not in stats

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.nltk", create=True)
    @patch(f"{MODULE}.stopwords", create=True)
    @patch(f"{MODULE}.WordNetLemmatizer", create=True)
    @patch(f"{MODULE}.NLTK_AVAILABLE", True)
    def test_statistics_nltk_available_true(
        self, mock_lemmatizer_cls, mock_stopwords, mock_nltk, mock_get_logger
    ) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        mock_nltk.data.find.return_value = True
        mock_stopwords.words.return_value = ["the"]
        mock_lemmatizer_cls.return_value = MagicMock()

        ai = ConversationalAI()
        stats = ai.get_statistics()

        assert stats["nltk_available"] is True


@pytest.mark.unit
class TestGetConversationHistory:
    """Tests for conversation history retrieval."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_history_without_db(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        history = ai.get_conversation_history()

        assert history == []

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_history_with_db(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.get_conversation_history.return_value = [{"id": 1, "call_id": "call-1"}]

        history = ai.get_conversation_history(limit=50)

        ai.db.get_conversation_history.assert_called_once_with(50)
        assert len(history) == 1

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_history_default_limit(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.get_conversation_history.return_value = []

        ai.get_conversation_history()

        ai.db.get_conversation_history.assert_called_once_with(100)


@pytest.mark.unit
class TestConfigureProvider:
    """Tests for provider configuration."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_provider_when_disabled(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        result = ai.configure_provider("openai", api_key="test-key")

        assert result is False

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_openai_provider(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        with patch("pbx.utils.encryption.encrypt_data", create=True, return_value=b"encrypted"):
            result = ai.configure_provider("openai", api_key="sk-test123", model="gpt-4")

        assert result is True
        assert ai.provider == "openai"
        assert ai.model == "gpt-4"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_dialogflow_provider(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        with patch("pbx.utils.encryption.encrypt_data", create=True, return_value=b"encrypted"):
            result = ai.configure_provider(
                "dialogflow", api_key="df-key", project_id="my-project"
            )

        assert result is True
        assert ai.provider == "dialogflow"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_lex_provider(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        with patch("pbx.utils.encryption.encrypt_data", create=True, return_value=b"encrypted"):
            result = ai.configure_provider(
                "lex", api_key="lex-key", region="us-west-2"
            )

        assert result is True
        assert ai.provider == "lex"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_azure_provider(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        with patch("pbx.utils.encryption.encrypt_data", create=True, return_value=b"encrypted"):
            result = ai.configure_provider(
                "azure", api_key="az-key", endpoint="https://azure.example.com"
            )

        assert result is True
        assert ai.provider == "azure"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_provider_no_api_key(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        result = ai.configure_provider("openai")

        assert result is True
        assert ai.provider == "openai"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_provider_encryption_unavailable(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        # Simulate ImportError for encryption module
        with patch.dict("sys.modules", {"pbx.utils.encryption": None}):
            result = ai.configure_provider("openai", api_key="key123")

        assert result is True
        assert hasattr(ai, "_api_key")
        assert ai._api_key == "key123"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_provider_updates_temperature(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        result = ai.configure_provider("openai", temperature=0.3)

        assert result is True
        assert ai.temperature == 0.3

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_provider_updates_max_tokens(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        result = ai.configure_provider("openai", max_tokens=300)

        assert result is True
        assert ai.max_tokens == 300

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_configure_provider_lowercases_name(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"conversational_ai": {"enabled": True}}}
        ai = ConversationalAI(config=config)

        result = ai.configure_provider("OPENAI")

        assert result is True
        assert ai.provider == "openai"


@pytest.mark.unit
class TestGetConversationalAISingleton:
    """Tests for the global singleton accessor."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_get_conversational_ai_creates_instance(self, mock_get_logger) -> None:
        import pbx.features.conversational_ai as module

        module._conversational_ai = None

        instance = module.get_conversational_ai()
        assert isinstance(instance, module.ConversationalAI)

        # Reset global state
        module._conversational_ai = None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_get_conversational_ai_returns_same_instance(self, mock_get_logger) -> None:
        import pbx.features.conversational_ai as module

        module._conversational_ai = None

        instance1 = module.get_conversational_ai()
        instance2 = module.get_conversational_ai()

        assert instance1 is instance2

        # Reset global state
        module._conversational_ai = None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_get_conversational_ai_with_config(self, mock_get_logger) -> None:
        import pbx.features.conversational_ai as module

        module._conversational_ai = None

        config = {"features": {"conversational_ai": {"enabled": True, "provider": "openai"}}}
        instance = module.get_conversational_ai(config=config)

        assert instance.enabled is True
        assert instance.provider == "openai"

        # Reset global state
        module._conversational_ai = None

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_get_conversational_ai_with_db_backend(self, mock_get_logger) -> None:
        import pbx.features.conversational_ai as module

        module._conversational_ai = None

        mock_db = MagicMock()
        mock_db.enabled = False

        instance = module.get_conversational_ai(db_backend=mock_db)
        assert instance.db_backend is mock_db

        # Reset global state
        module._conversational_ai = None


@pytest.mark.unit
class TestFullConversationFlow:
    """Integration-style tests for complete conversation flows."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_complete_conversation_lifecycle(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()

        # Start
        ctx = ai.start_conversation("call-flow", "555-0001")
        assert ctx is not None
        assert ai.total_conversations == 1

        # First message
        r1 = ai.process_user_input("call-flow", "Hello")
        assert r1["intent"] == "general_inquiry"

        # Second message
        r2 = ai.process_user_input("call-flow", "billing question")
        assert r2["intent"] == "billing_department"

        # Third message
        r3 = ai.process_user_input("call-flow", "Thank you")
        assert r3["intent"] == "gratitude"

        # End
        ai.end_conversation("call-flow")
        assert "call-flow" not in ai.active_conversations

        # Stats
        stats = ai.get_statistics()
        assert stats["total_conversations"] == 1
        assert stats["active_conversations"] == 0
        assert stats["total_messages_processed"] == 3

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_multiple_concurrent_conversations(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()

        ai.start_conversation("call-a", "555-0001")
        ai.start_conversation("call-b", "555-0002")

        r_a = ai.process_user_input("call-a", "I need support")
        r_b = ai.process_user_input("call-b", "What is the price?")

        assert r_a["intent"] == "support_department"
        assert r_b["intent"] == "pricing_inquiry"

        assert ai.get_statistics()["total_conversations"] == 2
        assert ai.get_statistics()["active_conversations"] == 2

        ai.end_conversation("call-a")

        assert ai.get_statistics()["active_conversations"] == 1

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_full_flow_with_db(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.db = MagicMock()
        ai.db.save_conversation.return_value = 99

        ai.start_conversation("call-db-flow", "555-0001")
        ai.process_user_input("call-db-flow", "I need support")
        ai.end_conversation("call-db-flow")

        ai.db.save_conversation.assert_called_once()
        assert ai.db.save_message.call_count == 2
        ai.db.save_intent.assert_called_once()
        ai.db.end_conversation.assert_called_once()


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_empty_string_input(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "")

        assert "response" in result
        assert result["intent"] == "general_inquiry"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_very_long_input(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        long_input = "hello " * 1000
        result = ai.process_user_input("call-1", long_input)

        assert "response" in result

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_special_characters_in_input(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        result = ai.process_user_input("call-1", "!@#$%^&*()")

        assert "response" in result

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_extract_entities_empty_string(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        entities = ai.extract_entities("")

        assert entities == {}

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_detect_intent_case_insensitive(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("EMERGENCY") == "emergency_request"
        assert ai.detect_intent("Sales") == "sales_department"
        assert ai.detect_intent("BILLING") == "billing_department"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_overwrite_conversation_same_call_id(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        ai.start_conversation("call-1", "555-0001")
        ctx2 = ai.start_conversation("call-1", "555-0002")

        assert ai.active_conversations["call-1"] is ctx2
        assert ctx2.caller_id == "555-0002"
        assert ai.total_conversations == 2

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_config_missing_features_key(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"other_key": "value"}
        ai = ConversationalAI(config=config)

        assert ai.enabled is False
        assert ai.provider == "nltk"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_config_missing_conversational_ai_key(self, mock_get_logger) -> None:
        from pbx.features.conversational_ai import ConversationalAI

        config = {"features": {"other_feature": True}}
        ai = ConversationalAI(config=config)

        assert ai.enabled is False
        assert ai.provider == "nltk"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_when_keyword_triggers_business_hours(self, mock_get_logger) -> None:
        """The 'when' keyword triggers business_hours_inquiry."""
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("when do you close") == "business_hours_inquiry"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_where_keyword_triggers_location(self, mock_get_logger) -> None:
        """The 'where' keyword triggers location_inquiry."""
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("where are you") == "location_inquiry"

    @patch(f"{MODULE}.get_logger")
    @patch(f"{MODULE}.NLTK_AVAILABLE", False)
    def test_how_much_triggers_pricing(self, mock_get_logger) -> None:
        """The 'how much' keyword triggers pricing_inquiry."""
        from pbx.features.conversational_ai import ConversationalAI

        ai = ConversationalAI()
        assert ai.detect_intent("how much is it") == "pricing_inquiry"
