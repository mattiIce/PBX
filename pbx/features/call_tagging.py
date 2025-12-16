"""
Call Tagging & Categorization
AI-powered call classification and tagging
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pbx.utils.logger import get_logger


class CallCategory(Enum):
    """Predefined call categories"""
    SALES = "sales"
    SUPPORT = "support"
    BILLING = "billing"
    GENERAL_INQUIRY = "general_inquiry"
    COMPLAINT = "complaint"
    EMERGENCY = "emergency"
    TECHNICAL = "technical"
    OTHER = "other"


class TagSource(Enum):
    """Source of tag"""
    AUTO = "auto"       # AI-generated
    MANUAL = "manual"   # User-added
    RULE = "rule"       # Rule-based


class CallTag:
    """Represents a tag on a call"""
    
    def __init__(self, tag: str, source: TagSource, confidence: float = 1.0):
        """Initialize call tag"""
        self.tag = tag
        self.source = source
        self.confidence = confidence
        self.created_at = datetime.now()


class CallTagging:
    """
    Call Tagging & Categorization System
    
    AI-powered call classification with automatic tagging.
    Features:
    - Automatic categorization based on call content
    - Custom tag creation
    - Rule-based tagging
    - ML-based classification
    - Tag analytics and reporting
    """
    
    def __init__(self, config=None):
        """Initialize call tagging system"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        tagging_config = self.config.get('features', {}).get('call_tagging', {})
        self.enabled = tagging_config.get('enabled', False)
        self.auto_tag_enabled = tagging_config.get('auto_tag', True)
        self.min_confidence = tagging_config.get('min_confidence', 0.7)
        self.max_tags_per_call = tagging_config.get('max_tags', 10)
        
        # Tags storage
        self.call_tags: Dict[str, List[CallTag]] = {}
        
        # Custom tags
        self.custom_tags: set = set()
        
        # Tagging rules
        self.tagging_rules: List[Dict] = []
        self._initialize_default_rules()
        
        # Statistics
        self.total_calls_tagged = 0
        self.total_tags_created = 0
        self.auto_tags_created = 0
        self.manual_tags_created = 0
        
        self.logger.info("Call tagging system initialized")
        self.logger.info(f"  Auto-tagging: {self.auto_tag_enabled}")
        self.logger.info(f"  Min confidence: {self.min_confidence}")
        self.logger.info(f"  Enabled: {self.enabled}")
    
    def _initialize_default_rules(self):
        """Initialize default tagging rules"""
        # Keyword-based rules
        self.tagging_rules.extend([
            {
                'name': 'Sales Call',
                'keywords': ['purchase', 'buy', 'order', 'price', 'quote'],
                'tag': 'sales',
                'category': CallCategory.SALES
            },
            {
                'name': 'Support Call',
                'keywords': ['help', 'issue', 'problem', 'broken', 'not working'],
                'tag': 'support',
                'category': CallCategory.SUPPORT
            },
            {
                'name': 'Billing Call',
                'keywords': ['invoice', 'payment', 'charge', 'bill', 'refund'],
                'tag': 'billing',
                'category': CallCategory.BILLING
            },
            {
                'name': 'Complaint',
                'keywords': ['complaint', 'unhappy', 'disappointed', 'terrible'],
                'tag': 'complaint',
                'category': CallCategory.COMPLAINT
            }
        ])
    
    def tag_call(self, call_id: str, tag: str, source: TagSource = TagSource.MANUAL,
                 confidence: float = 1.0) -> bool:
        """
        Add a tag to a call
        
        Args:
            call_id: Call identifier
            tag: Tag to add
            source: Tag source
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            bool: Success
        """
        if call_id not in self.call_tags:
            self.call_tags[call_id] = []
        
        # Check max tags limit
        if len(self.call_tags[call_id]) >= self.max_tags_per_call:
            self.logger.warning(f"Max tags ({self.max_tags_per_call}) reached for call {call_id}")
            return False
        
        # Add tag
        call_tag = CallTag(tag, source, confidence)
        self.call_tags[call_id].append(call_tag)
        
        # Track custom tags
        if source == TagSource.MANUAL:
            self.custom_tags.add(tag)
            self.manual_tags_created += 1
        elif source == TagSource.AUTO:
            self.auto_tags_created += 1
        
        self.total_tags_created += 1
        
        self.logger.info(f"Tagged call {call_id}: {tag} ({source.value}, conf={confidence:.2f})")
        return True
    
    def auto_tag_call(self, call_id: str, transcript: str = None,
                     metadata: Dict = None) -> List[str]:
        """
        Automatically tag a call based on content
        
        Args:
            call_id: Call identifier
            transcript: Call transcript (optional)
            metadata: Call metadata (optional)
            
        Returns:
            List[str]: Tags added
        """
        if not self.auto_tag_enabled:
            return []
        
        tags_added = []
        
        # Rule-based tagging
        if transcript:
            tags_added.extend(self._apply_rules(call_id, transcript))
        
        # AI-based tagging (placeholder for ML integration)
        if transcript:
            ai_tags = self._classify_with_ai(transcript)
            for tag, confidence in ai_tags:
                if confidence >= self.min_confidence:
                    if self.tag_call(call_id, tag, TagSource.AUTO, confidence):
                        tags_added.append(tag)
        
        # Metadata-based tagging
        if metadata:
            meta_tags = self._tag_from_metadata(metadata)
            for tag in meta_tags:
                if self.tag_call(call_id, tag, TagSource.RULE, 1.0):
                    tags_added.append(tag)
        
        if tags_added:
            self.total_calls_tagged += 1
        
        return tags_added
    
    def _apply_rules(self, call_id: str, transcript: str) -> List[str]:
        """Apply rule-based tagging"""
        tags_added = []
        transcript_lower = transcript.lower()
        
        for rule in self.tagging_rules:
            # Check if any keyword matches
            for keyword in rule['keywords']:
                if keyword in transcript_lower:
                    tag = rule['tag']
                    if self.tag_call(call_id, tag, TagSource.RULE, 0.95):
                        tags_added.append(tag)
                    break
        
        return tags_added
    
    def _classify_with_ai(self, transcript: str) -> List[tuple]:
        """
        Classify call using AI/ML
        
        Args:
            transcript: Call transcript
            
        Returns:
            List[tuple]: List of (tag, confidence) tuples
        """
        # TODO: Integrate with ML classifier
        # This would use scikit-learn, TensorFlow, or call an API like OpenAI
        
        # Placeholder: simple keyword scoring
        results = []
        
        # Example: Use TF-IDF and classification model
        # For now, return empty list
        
        return results
    
    def _tag_from_metadata(self, metadata: Dict) -> List[str]:
        """Extract tags from call metadata"""
        tags = []
        
        # Queue-based tags
        if 'queue' in metadata:
            tags.append(f"queue_{metadata['queue']}")
        
        # Time-based tags
        if 'time_of_day' in metadata:
            hour = metadata['time_of_day']
            if 0 <= hour < 6:
                tags.append('night')
            elif 6 <= hour < 12:
                tags.append('morning')
            elif 12 <= hour < 18:
                tags.append('afternoon')
            else:
                tags.append('evening')
        
        # Duration-based tags
        if 'duration' in metadata:
            duration = metadata['duration']
            if duration < 30:
                tags.append('short_call')
            elif duration < 300:
                tags.append('medium_call')
            else:
                tags.append('long_call')
        
        return tags
    
    def get_call_tags(self, call_id: str) -> List[Dict]:
        """Get all tags for a call"""
        if call_id not in self.call_tags:
            return []
        
        return [
            {
                'tag': tag.tag,
                'source': tag.source.value,
                'confidence': tag.confidence,
                'created_at': tag.created_at.isoformat()
            }
            for tag in self.call_tags[call_id]
        ]
    
    def remove_tag(self, call_id: str, tag: str) -> bool:
        """Remove a tag from a call"""
        if call_id not in self.call_tags:
            return False
        
        self.call_tags[call_id] = [
            t for t in self.call_tags[call_id] if t.tag != tag
        ]
        
        self.logger.info(f"Removed tag '{tag}' from call {call_id}")
        return True
    
    def add_tagging_rule(self, name: str, keywords: List[str], tag: str,
                        category: CallCategory = None):
        """
        Add custom tagging rule
        
        Args:
            name: Rule name
            keywords: Keywords to match
            tag: Tag to apply
            category: Call category (optional)
        """
        rule = {
            'name': name,
            'keywords': keywords,
            'tag': tag,
            'category': category
        }
        self.tagging_rules.append(rule)
        
        self.logger.info(f"Added tagging rule: {name}")
    
    def get_tag_statistics(self) -> Dict:
        """Get tag usage statistics"""
        tag_counts = {}
        
        for tags in self.call_tags.values():
            for tag in tags:
                tag_counts[tag.tag] = tag_counts.get(tag.tag, 0) + 1
        
        return {
            'total_unique_tags': len(tag_counts),
            'tag_counts': tag_counts,
            'most_common': sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def search_by_tag(self, tag: str) -> List[str]:
        """
        Find all calls with a specific tag
        
        Args:
            tag: Tag to search for
            
        Returns:
            List[str]: Call IDs with the tag
        """
        matching_calls = []
        
        for call_id, tags in self.call_tags.items():
            if any(t.tag == tag for t in tags):
                matching_calls.append(call_id)
        
        return matching_calls
    
    def get_all_tags(self) -> List[Dict]:
        """Get all unique tags"""
        all_tags = set()
        for tags_list in self.call_tags.values():
            for tag in tags_list:
                all_tags.add(tag.tag)
        
        # Include custom tags
        all_tags.update(self.custom_tags)
        
        return [{'tag': tag} for tag in sorted(all_tags)]
    
    def get_all_rules(self) -> List[Dict]:
        """Get all tagging rules"""
        return self.tagging_rules.copy()
    
    def create_tag(self, name: str, description: str = '', color: str = '#007bff') -> str:
        """
        Create a new custom tag
        
        Args:
            name: Tag name
            description: Tag description
            color: Tag color (hex)
            
        Returns:
            str: Tag ID
        """
        self.custom_tags.add(name)
        self.logger.info(f"Created custom tag: {name}")
        return name
    
    def create_rule(self, name: str, conditions: List, tag_id: str, priority: int = 100) -> str:
        """
        Create a new tagging rule
        
        Args:
            name: Rule name
            conditions: List of conditions
            tag_id: Tag to apply
            priority: Rule priority
            
        Returns:
            str: Rule ID
        """
        rule_id = f"rule_{len(self.tagging_rules) + 1}"
        rule = {
            'id': rule_id,
            'name': name,
            'conditions': conditions,
            'tag': tag_id,
            'priority': priority
        }
        self.tagging_rules.append(rule)
        self.logger.info(f"Created tagging rule: {name}")
        return rule_id
    
    def classify_call(self, call_id: str) -> List[str]:
        """
        Classify a call and return applicable tags
        
        Args:
            call_id: Call ID
            
        Returns:
            List[str]: List of tags
        """
        # Placeholder for AI classification
        # In production, this would call an ML model
        tags = []
        
        # Apply rule-based tagging
        for rule in self.tagging_rules:
            # Simplified rule evaluation
            # In production, would evaluate actual call data
            tags.append(rule['tag'])
        
        # Store tags
        self.call_tags[call_id] = [CallTag(tag, TagSource.AUTO) for tag in tags[:self.max_tags_per_call]]
        self.total_calls_tagged += 1
        self.auto_tags_created += len(tags)
        
        return tags
    
    def get_statistics(self) -> Dict:
        """Get overall tagging statistics"""
        return {
            'enabled': self.enabled,
            'auto_tag_enabled': self.auto_tag_enabled,
            'total_calls_tagged': self.total_calls_tagged,
            'total_tags_created': self.total_tags_created,
            'auto_tags_created': self.auto_tags_created,
            'manual_tags_created': self.manual_tags_created,
            'custom_tags_count': len(self.custom_tags),
            'tagging_rules_count': len(self.tagging_rules)
        }


# Global instance
_call_tagging = None


def get_call_tagging(config=None) -> CallTagging:
    """Get or create call tagging instance"""
    global _call_tagging
    if _call_tagging is None:
        _call_tagging = CallTagging(config)
    return _call_tagging
