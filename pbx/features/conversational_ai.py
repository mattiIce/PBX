"""
Conversational AI Assistant
Auto-responses and smart call handling using AI
"""
from typing import Dict, List, Optional
from datetime import datetime
from pbx.utils.logger import get_logger


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
        self.started_at = datetime.now()
        self.messages = []
        self.intent = None
        self.entities = {}
        
    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })


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
    
    def __init__(self, config=None):
        """Initialize conversational AI system"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        ai_config = self.config.get('features', {}).get('conversational_ai', {})
        self.enabled = ai_config.get('enabled', False)
        self.provider = ai_config.get('provider', 'openai')  # openai, dialogflow, lex, azure
        self.model = ai_config.get('model', 'gpt-4')
        self.max_tokens = ai_config.get('max_tokens', 150)
        self.temperature = ai_config.get('temperature', 0.7)
        
        # Active conversations
        self.active_conversations: Dict[str, ConversationContext] = {}
        
        # Statistics
        self.total_conversations = 0
        self.total_messages_processed = 0
        self.intents_detected = {}
        
        self.logger.info("Conversational AI assistant initialized")
        self.logger.info(f"  Provider: {self.provider}")
        self.logger.info(f"  Model: {self.model}")
        self.logger.info(f"  Enabled: {self.enabled}")
    
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
        
        self.logger.info(f"Started conversation for call {call_id} from {caller_id}")
        return context
    
    def process_user_input(self, call_id: str, user_input: str) -> Dict:
        """
        Process user input and generate AI response
        
        Args:
            call_id: Call identifier
            user_input: User's speech converted to text
            
        Returns:
            Dict containing response, intent, and entities
        """
        if call_id not in self.active_conversations:
            self.logger.warning(f"No active conversation for call {call_id}")
            return {
                'response': "I'm sorry, I don't have context for this conversation.",
                'intent': 'unknown',
                'entities': {}
            }
        
        context = self.active_conversations[call_id]
        context.add_message('user', user_input)
        self.total_messages_processed += 1
        
        # TODO: Integrate with AI provider
        # This is where you would call OpenAI, Dialogflow, etc.
        response = self._generate_response(context, user_input)
        
        context.add_message('assistant', response['response'])
        context.intent = response['intent']
        context.entities = response['entities']
        
        # Track intents
        intent = response['intent']
        self.intents_detected[intent] = self.intents_detected.get(intent, 0) + 1
        
        return response
    
    def _generate_response(self, context: ConversationContext, user_input: str) -> Dict:
        """
        Generate AI response using enhanced intent detection and entity extraction
        
        In production, integrate with:
        - OpenAI GPT-4 for natural responses
        - Dialogflow for conversation management
        - AWS Lex for conversational AI
        
        Args:
            context: Conversation context
            user_input: User's input
            
        Returns:
            Dict with response, intent, and entities
        """
        # Detect intent using enhanced method
        intent = self.detect_intent(user_input)
        
        # Extract entities using enhanced method
        entities = self.extract_entities(user_input)
        
        # Generate response based on intent
        if intent == 'emergency_request':
            response = "I'm connecting you to emergency services immediately."
        elif intent == 'transfer_request':
            dept = entities.get('departments', ['general'])[0] if entities.get('departments') else 'general'
            response = f"I'll transfer you to the {dept} department right away."
        elif intent == 'sales_department':
            response = "Let me connect you with our sales team."
        elif intent == 'support_department':
            response = "I'll transfer you to technical support."
        elif intent == 'billing_department':
            response = "Connecting you to our billing department."
        elif intent == 'business_hours_inquiry':
            response = "Our business hours are Monday through Friday, 9 AM to 5 PM."
        elif intent == 'location_inquiry':
            response = "We're located at our main office. Would you like me to provide the address?"
        elif intent == 'pricing_inquiry':
            response = "I can help you with pricing information. Let me connect you with sales."
        elif intent == 'voicemail_request':
            response = "I'll direct you to voicemail where you can leave a message."
        elif intent == 'callback_request':
            phone = entities.get('phone_numbers', [None])[0]
            if phone:
                response = f"I'll arrange a callback to {phone}. Is that correct?"
            else:
                response = "I can arrange a callback. What number should we call?"
        elif intent == 'complaint':
            response = "I'm sorry to hear about your experience. Let me connect you with a supervisor."
        elif intent == 'cancel_request':
            response = "No problem. Is there anything else I can help you with?"
        elif intent == 'gratitude':
            response = "You're welcome! Is there anything else I can assist you with?"
        elif intent == 'affirmation':
            response = "Great! How can I help you further?"
        elif intent == 'negation':
            response = "I understand. What would you like me to do instead?"
        else:  # general_inquiry
            response = "I understand. How else can I help you?"
        
        return {
            'response': response,
            'intent': intent,
            'entities': entities
        }
    
    def detect_intent(self, text: str) -> str:
        """
        Detect user intent from text using pattern matching and keyword analysis
        
        In production, this should integrate with:
        - OpenAI GPT for semantic understanding
        - Dialogflow for intent classification
        - AWS Lex for conversational AI
        
        Args:
            text: User's input text
            
        Returns:
            str: Detected intent
        """
        text_lower = text.lower()
        
        # Intent patterns with priority (most specific first)
        intent_patterns = [
            # Emergency/urgent
            (['emergency', 'urgent', '911', 'help now'], 'emergency_request'),
            
            # Transfer requests
            (['transfer', 'speak to', 'talk to', 'connect me', 'put me through'], 'transfer_request'),
            
            # Department routing
            (['sales', 'purchase', 'buy'], 'sales_department'),
            (['support', 'technical', 'tech support', 'help desk'], 'support_department'),
            (['billing', 'payment', 'invoice', 'account'], 'billing_department'),
            
            # Information requests
            (['hours', 'open', 'available', 'when', 'schedule'], 'business_hours_inquiry'),
            (['location', 'address', 'where', 'directions'], 'location_inquiry'),
            (['price', 'cost', 'how much'], 'pricing_inquiry'),
            
            # Voicemail
            (['voicemail', 'message', 'leave message'], 'voicemail_request'),
            
            # Call back
            (['call back', 'callback', 'call me back', 'return call'], 'callback_request'),
            
            # Complaint
            (['complaint', 'complain', 'unhappy', 'dissatisfied'], 'complaint'),
            
            # General
            (['cancel', 'nevermind', 'forget it'], 'cancel_request'),
            (['thank', 'thanks', 'appreciate'], 'gratitude'),
            (['yes', 'yeah', 'sure', 'okay', 'correct'], 'affirmation'),
            (['no', 'nope', 'not', 'incorrect'], 'negation'),
        ]
        
        # Check patterns
        for keywords, intent in intent_patterns:
            if any(keyword in text_lower for keyword in keywords):
                return intent
        
        # Default intent
        return 'general_inquiry'
    
    def extract_entities(self, text: str) -> Dict:
        """
        Extract entities from text using pattern matching
        
        In production, this should integrate with:
        - spaCy for Named Entity Recognition
        - OpenAI GPT for semantic entity extraction
        - Custom ML models for domain-specific entities
        
        Args:
            text: User's input text
            
        Returns:
            Dict: Extracted entities (phone numbers, names, departments, dates, times, etc.)
        """
        import re
        
        entities = {}
        
        # Extract phone numbers (various formats)
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 555-123-4567 or 5551234567
            r'\b\d{3}[-.]?\d{4}\b',             # 555-1234
            r'\b1[-.]?\d{3}[-.]?\d{3}[-.]?\d{4}\b'  # 1-555-123-4567
        ]
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        if phones:
            entities['phone_numbers'] = phones
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            entities['emails'] = emails
        
        # Extract extension numbers
        ext_pattern = r'\b(?:ext|extension|x)\s*(\d{3,5})\b'
        extensions = re.findall(ext_pattern, text.lower())
        if extensions:
            entities['extensions'] = extensions
        
        # Extract department mentions
        departments = []
        dept_keywords = {
            'sales': ['sales', 'selling', 'purchase'],
            'support': ['support', 'tech support', 'technical', 'help'],
            'billing': ['billing', 'payment', 'invoice', 'accounting'],
            'hr': ['hr', 'human resources', 'personnel'],
            'management': ['manager', 'management', 'supervisor']
        }
        text_lower = text.lower()
        for dept, keywords in dept_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                departments.append(dept)
        if departments:
            entities['departments'] = departments
        
        # Extract times (simple patterns)
        time_pattern = r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?\b'
        times = re.findall(time_pattern, text)
        if times:
            entities['times'] = [f"{h}:{m} {ap}" if ap else f"{h}:{m}" for h, m, ap in times]
        
        # Extract numbers (could be order numbers, account numbers, etc.)
        number_pattern = r'\b\d{4,}\b'
        numbers = re.findall(number_pattern, text)
        if numbers:
            entities['numbers'] = numbers
        
        return entities
    
    def end_conversation(self, call_id: str):
        """
        End a conversation
        
        Args:
            call_id: Call identifier
        """
        if call_id in self.active_conversations:
            context = self.active_conversations[call_id]
            duration = (datetime.now() - context.started_at).total_seconds()
            
            self.logger.info(f"Ended conversation for call {call_id}")
            self.logger.info(f"  Duration: {duration:.1f}s")
            self.logger.info(f"  Messages: {len(context.messages)}")
            self.logger.info(f"  Final intent: {context.intent}")
            
            del self.active_conversations[call_id]
    
    def get_statistics(self) -> Dict:
        """Get AI assistant statistics"""
        return {
            'total_conversations': self.total_conversations,
            'active_conversations': len(self.active_conversations),
            'total_messages_processed': self.total_messages_processed,
            'intents_detected': self.intents_detected,
            'provider': self.provider,
            'model': self.model,
            'enabled': self.enabled
        }
    
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
                self.logger.warning("Encryption module not available, API key stored in memory only")
                self._api_key = api_key
        
        # Update configuration from kwargs
        if 'model' in kwargs:
            self.model = kwargs['model']
        if 'temperature' in kwargs:
            self.temperature = kwargs['temperature']
        if 'max_tokens' in kwargs:
            self.max_tokens = kwargs['max_tokens']
        
        # Provider-specific initialization
        if self.provider == 'openai':
            self.logger.info(f"  OpenAI model: {self.model}")
            # In production: Initialize OpenAI client
            # import openai
            # openai.api_key = api_key
            
        elif self.provider == 'dialogflow':
            project_id = kwargs.get('project_id')
            self.logger.info(f"  Dialogflow project: {project_id}")
            # In production: Initialize Dialogflow client
            # from google.cloud import dialogflow
            
        elif self.provider == 'lex':
            region = kwargs.get('region', 'us-east-1')
            self.logger.info(f"  Amazon Lex region: {region}")
            # In production: Initialize Lex client
            # import boto3
            # lex_client = boto3.client('lex-runtime', region_name=region)
            
        elif self.provider == 'azure':
            endpoint = kwargs.get('endpoint')
            self.logger.info(f"  Azure endpoint: {endpoint}")
            # In production: Initialize Azure Bot Service client
        
        self.logger.info(f"AI provider configured: {provider}")


# Global instance
_conversational_ai = None


def get_conversational_ai(config=None) -> ConversationalAI:
    """Get or create conversational AI instance"""
    global _conversational_ai
    if _conversational_ai is None:
        _conversational_ai = ConversationalAI(config)
    return _conversational_ai
