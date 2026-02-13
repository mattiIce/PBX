"""
Conversational AI Assistant
Auto-responses and smart call handling using AI
"""

from datetime import datetime, timezone

from pbx.utils.logger import get_logger

# NLTK for natural language processing
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize

    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


class ConversationContext:
    """Represents a conversation context for AI processing"""

    def __init__(self, call_id: str, caller_id: str):
        """
        Initialize conversation context

        Args:
            call_id: Unique call identifier
            caller_id: Caller's phone number
        """
        self.call_id = call_id
        self.caller_id = caller_id
        self.started_at = datetime.now(timezone.utc)
        self.messages = []
        self.intent = None
        self.entities = {}

    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append(
            {"role": role, "content": content, "timestamp": datetime.now(timezone.utc).isoformat()}
        )


class ConversationalAI:
    """
    Conversational AI Assistant

    Provides intelligent auto-responses and call handling using AI.
    This framework is ready for integration with AI services like:
    - OpenAI GPT models
    - Google Dialogflow
    - Amazon Lex
    - Microsoft Azure Bot Service
    """

    def __init__(self, config=None, db_backend=None):
        """Initialize conversational AI system"""
        self.logger = get_logger()
        self.config = config or {}
        self.db_backend = db_backend
        self.db = None

        # Configuration
        ai_config = self.config.get("features", {}).get("conversational_ai", {})
        self.enabled = ai_config.get("enabled", False)
        self.provider = ai_config.get(
            "provider", "nltk"
        )  # nltk (free), openai, dialogflow, lex, azure
        self.model = ai_config.get("model", "gpt-4")
        self.max_tokens = ai_config.get("max_tokens", 150)
        self.temperature = ai_config.get("temperature", 0.7)

        # Active conversations
        self.active_conversations: dict[str, ConversationContext] = {}

        # Active conversation ID mapping (call_id -> conversation_id)
        self.conversation_ids: dict[str, int] = {}

        # Statistics
        self.total_conversations = 0
        self.total_messages_processed = 0
        self.intents_detected = {}

        # NLTK components
        self.lemmatizer = None
        self.stop_words = None
        self._initialize_nltk()

        # Initialize database if available
        if self.db_backend and self.db_backend.enabled:
            try:
                from pbx.features.conversational_ai_db import ConversationalAIDatabase

                self.db = ConversationalAIDatabase(self.db_backend)
                self.db.create_tables()
                self.logger.info("Conversational AI database layer initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize database layer: {e}")

        self.logger.info("Conversational AI assistant initialized")
        self.logger.info(f"  Provider: {self.provider}")
        self.logger.info(f"  Model: {self.model}")
        self.logger.info(f"  NLTK available: {NLTK_AVAILABLE}")
        self.logger.info(f"  Enabled: {self.enabled}")

    def _initialize_nltk(self):
        """Initialize NLTK components for NLP processing"""
        if not NLTK_AVAILABLE:
            self.logger.info("NLTK not available - install with: pip install nltk")
            return

        try:
            # Download required resources if not already present
            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                self.logger.info("Downloading NLTK punkt tokenizer...")
                nltk.download("punkt", quiet=True)

            try:
                nltk.data.find("corpora/stopwords")
            except LookupError:
                self.logger.info("Downloading NLTK stopwords...")
                nltk.download("stopwords", quiet=True)

            try:
                nltk.data.find("corpora/wordnet")
            except LookupError:
                self.logger.info("Downloading NLTK wordnet...")
                nltk.download("wordnet", quiet=True)

            # Initialize components
            self.lemmatizer = WordNetLemmatizer()
            self.stop_words = set(stopwords.words("english"))

            self.logger.info("NLTK components initialized successfully")

        except Exception as e:
            self.logger.warning(f"Could not initialize NLTK: {e}")
            self.lemmatizer = None
            self.stop_words = None

    def start_conversation(self, call_id: str, caller_id: str) -> ConversationContext:
        """
        Start a new conversation

        Args:
            call_id: Unique call identifier
            caller_id: Caller's phone number

        Returns:
            ConversationContext: New conversation context
        """
        context = ConversationContext(call_id, caller_id)
        self.active_conversations[call_id] = context
        self.total_conversations += 1

        # Save to database
        if self.db:
            conversation_id = self.db.save_conversation(call_id, caller_id, context.started_at)
            if conversation_id:
                self.conversation_ids[call_id] = conversation_id

        self.logger.info(f"Started conversation for call {call_id} from {caller_id}")
        return context

    def process_user_input(self, call_id: str, user_input: str) -> dict:
        """
        Process user input and generate AI response

        Args:
            call_id: Call identifier
            user_input: User's speech converted to text

        Returns:
            dict containing response, intent, and entities
        """
        if call_id not in self.active_conversations:
            self.logger.warning(f"No active conversation for call {call_id}")
            return {
                "response": "I'm sorry, I don't have context for this conversation.",
                "intent": "unknown",
                "entities": {},
            }

        context = self.active_conversations[call_id]
        context.add_message("user", user_input)
        self.total_messages_processed += 1

        # Integrate with AI provider (rule-based with ML-style confidence scoring)
        # This provides intelligent responses without requiring external API keys
        response = self._generate_response(context, user_input)

        context.add_message("assistant", response["response"])
        context.intent = response["intent"]
        context.entities = response["entities"]

        # Save to database
        if self.db and call_id in self.conversation_ids:
            conversation_id = self.conversation_ids[call_id]
            # Save messages
            self.db.save_message(conversation_id, "user", user_input, datetime.now(timezone.utc))
            self.db.save_message(conversation_id, "assistant", response["response"], datetime.now(timezone.utc))
            # Save intent
            if response["intent"] and response["intent"] != "general_inquiry":
                confidence = response.get("confidence", 0.9)
                self.db.save_intent(
                    conversation_id,
                    response["intent"],
                    confidence,
                    response["entities"],
                    datetime.now(timezone.utc),
                )

        # Track intents
        intent = response["intent"]
        self.intents_detected[intent] = self.intents_detected.get(intent, 0) + 1

        return response

    def _build_response_handlers(self):
        """Build intent-to-response handler mapping"""
        return {
            "emergency_request": lambda entities: (
                "I'm connecting you to emergency services immediately.",
                1.0,
            ),
            "transfer_request": lambda entities: (
                f"I'll transfer you to the {entities.get('departments', ['general'])[0] if entities.get('departments') else 'general'} department right away.",
                None,
            ),
            "sales_department": lambda entities: (
                "Let me connect you with our sales team. They'll be happy to help you.",
                None,
            ),
            "support_department": lambda entities: (
                "I'll transfer you to technical support. They're ready to assist you.",
                None,
            ),
            "billing_department": lambda entities: (
                "Connecting you to our billing department now.",
                None,
            ),
            "business_hours_inquiry": lambda entities: (
                "Our business hours are Monday through Friday, 9 AM to 5 PM. Is there anything else you'd like to know?",
                None,
            ),
            "location_inquiry": lambda entities: (
                "We're located at our main office. Would you like me to provide the full address?",
                None,
            ),
            "pricing_inquiry": lambda entities: (
                "I can help you with pricing information. Let me connect you with our sales team who can provide detailed quotes.",
                None,
            ),
            "voicemail_request": lambda entities: (
                "I'll direct you to voicemail where you can leave a detailed message.",
                None,
            ),
            "callback_request": lambda entities: (
                (
                    f"I'll arrange a callback to {entities.get('phone_numbers', [None])[0]}. Is that the best number to reach you?"
                    if entities.get("phone_numbers", [None])[0]
                    else "I can arrange a callback for you. What's the best number to reach you at?"
                ),
                None,
            ),
            "complaint": lambda entities: (
                "I'm sorry to hear about your experience. Let me connect you with a supervisor who can help resolve this.",
                None,
            ),
            "cancel_request": lambda entities: (
                "No problem at all. Is there anything else I can help you with today?",
                None,
            ),
        }

    def _generate_response(self, context: ConversationContext, user_input: str) -> dict:
        """
        Generate AI response using enhanced intent detection and entity extraction

        Implements intelligent conversational AI with:
        - Context-aware responses
        - Intent confidence scoring
        - Entity-based personalization
        - Multi-turn conversation handling

        For external AI providers, configure:
        - OpenAI GPT-4 for natural responses
        - Dialogflow for conversation management
        - AWS Lex for conversational AI

        Args:
            context: Conversation context
            user_input: User's input

        Returns:
            dict with response, intent, entities, and confidence
        """
        # Detect intent using enhanced method with confidence scoring
        intent, confidence = self._detect_intent_with_confidence(user_input)

        # Extract entities using enhanced method
        entities = self.extract_entities(user_input)

        # Check conversation history for context
        previous_intent = context.intent  # ConversationContext has intent attribute
        message_count = len(context.messages)

        # Build response handlers
        handlers = self._build_response_handlers()

        # Generate contextual response based on intent and conversation flow
        if intent in handlers:
            response, override_confidence = handlers[intent](entities)
            if override_confidence is not None:
                confidence = override_confidence

        elif intent == "gratitude":
            if message_count > 3:
                response = "You're very welcome! Happy to help. Anything else?"
            else:
                response = "You're welcome! Is there anything else I can assist you with?"

        elif intent == "affirmation":
            # Context-aware affirmation handling
            if previous_intent == "callback_request":
                response = "Perfect! We'll call you back shortly."
            elif previous_intent in ["transfer_request", "sales_department", "support_department"]:
                response = "Great! Transferring you now."
            else:
                response = "Excellent! How can I help you further?"

        elif intent == "negation":
            # Context-aware negation handling
            if previous_intent == "callback_request":
                response = "Understood. What would you prefer instead?"
            elif previous_intent in ["location_inquiry", "business_hours_inquiry"]:
                response = "No problem. What other information can I provide?"
            else:
                response = "I understand. What would you like me to do instead?"

        else:  # general_inquiry
            # Provide helpful fallback based on conversation stage
            if message_count <= 2:
                response = "I'm here to help! You can ask about our hours, location, or I can connect you with sales, support, or billing."
            else:
                response = "I understand. How else can I assist you today?"

        return {
            "response": response,
            "intent": intent,
            "entities": entities,
            "confidence": confidence,
        }

    def _detect_intent_with_confidence(self, text: str) -> tuple:
        """
        Detect intent with confidence scoring

        Args:
            text: User input

        Returns:
            tuple of (intent, confidence)
        """
        # Use existing detect_intent method
        intent = self.detect_intent(text)

        # Calculate confidence based on keyword matches
        text_lower = text.lower()

        # Define strong indicators for each intent
        strong_indicators = {
            "emergency_request": ["emergency", "911", "urgent help"],
            "transfer_request": ["transfer to", "connect me to", "speak to"],
            "sales_department": ["sales", "purchase", "buy"],
            "support_department": ["support", "technical help", "tech support"],
            "billing_department": ["billing", "invoice", "payment"],
            "callback_request": ["call me back", "callback", "return my call"],
            "complaint": ["complaint", "complain", "unhappy"],
        }

        # Check for strong indicators
        confidence = 0.75  # Base confidence
        if intent in strong_indicators:
            for indicator in strong_indicators[intent]:
                if indicator in text_lower:
                    confidence = 0.95
                    break

        return (intent, confidence)

    def detect_intent(self, text: str) -> str:
        """
        Detect user intent from text using NLTK and pattern matching

        Uses free/open-source NLTK for NLP processing, with fallback to pattern matching.
        In production, can also integrate with:
        - Rasa for open-source intent classification
        - OpenAI GPT for semantic understanding
        - Dialogflow for intent classification

        Args:
            text: User's input text

        Returns:
            str: Detected intent
        """
        text_lower = text.lower()

        # Use NLTK for enhanced intent detection if available
        if NLTK_AVAILABLE and self.lemmatizer and self.stop_words:
            try:
                # Tokenize and lemmatize
                tokens = word_tokenize(text_lower)
                lemmatized = [
                    self.lemmatizer.lemmatize(token)
                    for token in tokens
                    if token.isalpha() and token not in self.stop_words
                ]

                # Enhanced intent patterns with lemmatized keywords
                nltk_intent_patterns = [
                    (["emergency", "urgent", "help"], "emergency_request"),
                    (["transfer", "speak", "talk", "connect"], "transfer_request"),
                    (["sale", "purchase", "buy", "order"], "sales_department"),
                    (["support", "technical", "help", "problem"], "support_department"),
                    (["billing", "payment", "invoice", "account"], "billing_department"),
                    (["hour", "open", "available", "schedule"], "business_hours_inquiry"),
                    (["location", "address", "direction"], "location_inquiry"),
                    (["price", "cost"], "pricing_inquiry"),
                    (["voicemail", "message"], "voicemail_request"),
                    (["call", "callback"], "callback_request"),
                    (["complaint", "complain", "unhappy"], "complaint"),
                    (["cancel", "nevermind", "forget"], "cancel_request"),
                    (["thank", "appreciate"], "gratitude"),
                    (["yes", "yeah", "sure", "okay"], "affirmation"),
                    (["no", "nope"], "negation"),
                ]

                # Check NLTK-enhanced patterns
                for keywords, intent in nltk_intent_patterns:
                    if any(keyword in lemmatized for keyword in keywords):
                        return intent
            except Exception as e:
                self.logger.debug(f"NLTK intent detection failed: {e}, falling back to patterns")

        # Standard intent patterns with priority (most specific first)
        intent_patterns = [
            # Emergency/urgent
            (["emergency", "urgent", "911", "help now"], "emergency_request"),
            # Transfer requests
            (
                ["transfer", "speak to", "talk to", "connect me", "put me through"],
                "transfer_request",
            ),
            # Department routing
            (["sales", "purchase", "buy"], "sales_department"),
            (["support", "technical", "tech support", "help desk"], "support_department"),
            (["billing", "payment", "invoice", "account"], "billing_department"),
            # Information requests
            (["hours", "open", "available", "when", "schedule"], "business_hours_inquiry"),
            (["location", "address", "where", "directions"], "location_inquiry"),
            (["price", "cost", "how much"], "pricing_inquiry"),
            # Voicemail
            (["voicemail", "message", "leave message"], "voicemail_request"),
            # Call back
            (["call back", "callback", "call me back", "return call"], "callback_request"),
            # Complaint
            (["complaint", "complain", "unhappy", "dissatisfied"], "complaint"),
            # General
            (["cancel", "nevermind", "forget it"], "cancel_request"),
            (["thank", "thanks", "appreciate"], "gratitude"),
            (["yes", "yeah", "sure", "okay", "correct"], "affirmation"),
            (["no", "nope", "not", "incorrect"], "negation"),
        ]

        # Check patterns
        for keywords, intent in intent_patterns:
            if any(keyword in text_lower for keyword in keywords):
                return intent

        # Default intent
        return "general_inquiry"

    def extract_entities(self, text: str) -> dict:
        """
        Extract entities from text using pattern matching

        In production, this should integrate with:
        - spaCy for Named Entity Recognition
        - OpenAI GPT for semantic entity extraction
        - Custom ML models for domain-specific entities

        Args:
            text: User's input text

        Returns:
            dict: Extracted entities (phone numbers, names, departments, dates, times, etc.)
        """
        import re

        entities = {}

        # Extract phone numbers (various formats)
        phone_patterns = [
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # 555-123-4567 or 5551234567
            r"\b\d{3}[-.]?\d{4}\b",  # 555-1234
            r"\b1[-.]?\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # 1-555-123-4567
        ]
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        if phones:
            entities["phone_numbers"] = phones

        # Extract email addresses
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, text)
        if emails:
            entities["emails"] = emails

        # Extract extension numbers
        ext_pattern = r"\b(?:ext|extension|x)\s*(\d{3,5})\b"
        extensions = re.findall(ext_pattern, text.lower())
        if extensions:
            entities["extensions"] = extensions

        # Extract department mentions
        departments = []
        dept_keywords = {
            "sales": ["sales", "selling", "purchase"],
            "support": ["support", "tech support", "technical", "help"],
            "billing": ["billing", "payment", "invoice", "accounting"],
            "hr": ["hr", "human resources", "personnel"],
            "management": ["manager", "management", "supervisor"],
        }
        text_lower = text.lower()
        for dept, keywords in dept_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                departments.append(dept)
        if departments:
            entities["departments"] = departments

        # Extract times (simple patterns)
        time_pattern = r"\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?\b"
        times = re.findall(time_pattern, text)
        if times:
            entities["times"] = [f"{h}:{m} {ap}" if ap else f"{h}:{m}" for h, m, ap in times]

        # Extract numbers (could be order numbers, account numbers, etc.)
        number_pattern = r"\b\d{4,}\b"
        numbers = re.findall(number_pattern, text)
        if numbers:
            entities["numbers"] = numbers

        return entities

    def tokenize_with_nltk(self, text: str) -> list[str]:
        """
        Tokenize text using NLTK with lemmatization and stop word removal

        Args:
            text: Text to tokenize

        Returns:
            list[str]: Processed tokens
        """
        if not NLTK_AVAILABLE or not self.lemmatizer or not self.stop_words:
            # Fallback to simple tokenization
            return text.lower().split()

        try:
            # Tokenize
            tokens = word_tokenize(text.lower())

            # Remove punctuation and stopwords, then lemmatize
            processed = [
                self.lemmatizer.lemmatize(token)
                for token in tokens
                if token.isalpha() and token not in self.stop_words
            ]

            return processed
        except Exception as e:
            self.logger.error(f"NLTK tokenization error: {e}")
            return text.lower().split()

    def end_conversation(self, call_id: str):
        """
        End a conversation

        Args:
            call_id: Call identifier
        """
        if call_id in self.active_conversations:
            context = self.active_conversations[call_id]
            duration = (datetime.now(timezone.utc) - context.started_at).total_seconds()

            # Save to database
            if self.db:
                self.db.end_conversation(
                    call_id, context.intent or "unknown", len(context.messages)
                )

            self.logger.info(f"Ended conversation for call {call_id}")
            self.logger.info(f"  Duration: {duration:.1f}s")
            self.logger.info(f"  Messages: {len(context.messages)}")
            self.logger.info(f"  Final intent: {context.intent}")

            del self.active_conversations[call_id]
            if call_id in self.conversation_ids:
                del self.conversation_ids[call_id]

    def get_statistics(self) -> dict:
        """Get AI assistant statistics"""
        stats = {
            "total_conversations": self.total_conversations,
            "active_conversations": len(self.active_conversations),
            "total_messages_processed": self.total_messages_processed,
            "intents_detected": self.intents_detected,
            "provider": self.provider,
            "model": self.model,
            "enabled": self.enabled,
            "nltk_available": NLTK_AVAILABLE and self.lemmatizer is not None,
        }

        # Add database statistics if available
        if self.db:
            db_stats = self.db.get_intent_statistics()
            if db_stats:
                stats["intent_statistics_db"] = db_stats

        return stats

    def get_conversation_history(self, limit: int = 100) -> list[dict]:
        """
        Get conversation history from database

        Args:
            limit: Maximum number of conversations to return

        Returns:
            list of conversation dictionaries
        """
        if self.db:
            return self.db.get_conversation_history(limit)
        return []

    def configure_provider(self, provider: str, api_key: str = None, **kwargs):
        """
        Configure AI provider with secure API key storage

        Supports:
        - OpenAI (GPT-4, GPT-3.5)
        - Google Dialogflow
        - Amazon Lex
        - Microsoft Azure Bot Service

        Args:
            provider: Provider name (openai, dialogflow, lex, azure)
            api_key: API key for the provider (will be stored securely)
            **kwargs: Additional provider-specific configuration
                - model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
                - region: AWS region for Lex
                - project_id: Google Cloud project ID for Dialogflow
                - endpoint: Custom API endpoint
        """
        if not self.enabled:
            self.logger.error("Cannot configure provider: Conversational AI feature is not enabled")
            return False

        self.provider = provider.lower()

        # Store API key securely using encryption utilities
        if api_key:
            try:
                from pbx.utils.encryption import encrypt_data

                # In production, store encrypted API key in database or secure vault
                encrypted_key = encrypt_data(api_key.encode())
                self.logger.info(f"Configured AI provider: {provider} (API key encrypted)")

                # Store for this session (in production, save to database)
                self._api_key_encrypted = encrypted_key
            except ImportError:
                # Fallback if encryption not available
                self.logger.warning(
                    "Encryption module not available, API key stored in memory only"
                )
                self._api_key = api_key

        # Update configuration from kwargs
        if "model" in kwargs:
            self.model = kwargs["model"]
        if "temperature" in kwargs:
            self.temperature = kwargs["temperature"]
        if "max_tokens" in kwargs:
            self.max_tokens = kwargs["max_tokens"]

        # Provider-specific initialization
        if self.provider == "openai":
            self.logger.info(f"  OpenAI model: {self.model}")
            # In production: Initialize OpenAI client
            # import openai
            # openai.api_key = api_key

        elif self.provider == "dialogflow":
            project_id = kwargs.get("project_id")
            self.logger.info(f"  Dialogflow project: {project_id}")
            # In production: Initialize Dialogflow client
            # from google.cloud import dialogflow

        elif self.provider == "lex":
            region = kwargs.get("region", "us-east-1")
            self.logger.info(f"  Amazon Lex region: {region}")
            # In production: Initialize Lex client
            # import boto3
            # lex_client = boto3.client('lex-runtime', region_name=region)

        elif self.provider == "azure":
            endpoint = kwargs.get("endpoint")
            self.logger.info(f"  Azure endpoint: {endpoint}")
            # In production: Initialize Azure Bot Service client

        self.logger.info(f"AI provider configured: {provider}")
        return True


# Global instance
_conversational_ai = None


def get_conversational_ai(config=None, db_backend=None) -> ConversationalAI:
    """Get or create conversational AI instance"""
    global _conversational_ai
    if _conversational_ai is None:
        _conversational_ai = ConversationalAI(config, db_backend)
    return _conversational_ai
