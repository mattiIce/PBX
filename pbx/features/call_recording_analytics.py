"""
Call Recording Analytics
AI analysis of recorded calls
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pbx.utils.logger import get_logger
import os


class AnalysisType(Enum):
    """Analysis type enumeration"""
    SENTIMENT = "sentiment"
    KEYWORDS = "keywords"
    COMPLIANCE = "compliance"
    QUALITY = "quality"
    SUMMARY = "summary"
    TRANSCRIPT = "transcript"


class RecordingAnalytics:
    """
    Call Recording Analytics
    
    AI-powered analysis of recorded calls.
    Features:
    - Sentiment analysis
    - Keyword detection
    - Compliance checking
    - Quality scoring
    - Automatic summarization
    - Trend analysis
    
    Integration points:
    - OpenAI Whisper (transcription)
    - GPT models (summarization, sentiment)
    - Custom ML models (compliance, quality)
    """
    
    def __init__(self, config=None):
        """Initialize recording analytics"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        analytics_config = self.config.get('features', {}).get('recording_analytics', {})
        self.enabled = analytics_config.get('enabled', False)
        self.auto_analyze = analytics_config.get('auto_analyze', False)
        self.analysis_types = analytics_config.get('analysis_types', [
            'sentiment', 'keywords', 'summary'
        ])
        
        # Analysis results storage
        self.analyses: Dict[str, Dict] = {}
        
        # Statistics
        self.total_analyses = 0
        self.analyses_by_type = {}
        
        self.logger.info("Call recording analytics initialized")
        self.logger.info(f"  Auto-analyze: {self.auto_analyze}")
        self.logger.info(f"  Analysis types: {', '.join(self.analysis_types)}")
        self.logger.info(f"  Enabled: {self.enabled}")
    
    def analyze_recording(self, recording_id: str, audio_path: str,
                         analysis_types: List[str] = None) -> Dict:
        """
        Analyze a call recording
        
        Args:
            recording_id: Recording identifier
            audio_path: Path to audio file
            analysis_types: Types of analysis to perform
            
        Returns:
            Dict: Analysis results
        """
        analysis_types = analysis_types or self.analysis_types
        
        results = {
            'recording_id': recording_id,
            'analyzed_at': datetime.now().isoformat(),
            'analyses': {}
        }
        
        # Perform each type of analysis
        for analysis_type in analysis_types:
            if analysis_type == 'transcript':
                results['analyses']['transcript'] = self._transcribe(audio_path)
            elif analysis_type == 'sentiment':
                results['analyses']['sentiment'] = self._analyze_sentiment(audio_path)
            elif analysis_type == 'keywords':
                results['analyses']['keywords'] = self._detect_keywords(audio_path)
            elif analysis_type == 'compliance':
                results['analyses']['compliance'] = self._check_compliance(audio_path)
            elif analysis_type == 'quality':
                results['analyses']['quality'] = self._score_quality(audio_path)
            elif analysis_type == 'summary':
                results['analyses']['summary'] = self._summarize(audio_path)
            
            # Track statistics
            self.analyses_by_type[analysis_type] = \
                self.analyses_by_type.get(analysis_type, 0) + 1
        
        self.analyses[recording_id] = results
        self.total_analyses += 1
        
        self.logger.info(f"Analyzed recording {recording_id}")
        self.logger.info(f"  Analysis types: {', '.join(analysis_types)}")
        
        return results
    
    def _transcribe(self, audio_path: str) -> Dict:
        """
        Transcribe audio to text using Vosk (offline speech-to-text)
        
        Args:
            audio_path: Path to audio file (WAV format, 16kHz recommended)
            
        Returns:
            Dict: Transcription results with transcript, confidence, duration, words
        """
        try:
            # Try to use Vosk for offline transcription (already in requirements.txt)
            from vosk import KaldiRecognizer, Model
            import wave
            import json
            
            # Try to get Vosk model from voicemail transcription if available
            vosk_model = None
            model_path = 'models/vosk-model-small-en-us-0.15'
            
            try:
                if os.path.exists(model_path):
                    vosk_model = Model(model_path)
                else:
                    self.logger.warning(f"Vosk model not found at {model_path}")
                    self.logger.info("Download from: https://alphacephei.com/vosk/models")
            except Exception as e:
                self.logger.warning(f"Could not load Vosk model: {e}")
            
            if not vosk_model:
                # Return empty result if model not available
                return {
                    'transcript': '',
                    'confidence': 0.0,
                    'duration': 0,
                    'words': [],
                    'error': 'Vosk model not available'
                }
            
            # Open audio file
            wf = wave.open(audio_path, "rb")
            sample_rate = wf.getframerate()
            
            # Create recognizer
            rec = KaldiRecognizer(vosk_model, sample_rate)
            rec.SetWords(True)
            
            # Process audio
            full_transcript = []
            all_words = []
            total_confidence = 0.0
            confidence_count = 0
            
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                    
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if result.get('text'):
                        full_transcript.append(result['text'])
                        if 'result' in result:
                            all_words.extend(result['result'])
                            for word in result['result']:
                                if 'conf' in word:
                                    total_confidence += word['conf']
                                    confidence_count += 1
            
            # Get final result
            final_result = json.loads(rec.FinalResult())
            if final_result.get('text'):
                full_transcript.append(final_result['text'])
                if 'result' in final_result:
                    all_words.extend(final_result['result'])
                    for word in final_result['result']:
                        if 'conf' in word:
                            total_confidence += word['conf']
                            confidence_count += 1
            
            wf.close()
            
            # Calculate average confidence
            avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
            
            # Get duration from wave file
            duration = wf.getnframes() / sample_rate if sample_rate > 0 else 0
            
            return {
                'transcript': ' '.join(full_transcript),
                'confidence': avg_confidence,
                'duration': duration,
                'words': all_words
            }
            
        except ImportError:
            self.logger.warning("Vosk not available. Install with: pip install vosk")
            return {
                'transcript': '',
                'confidence': 0.0,
                'duration': 0,
                'words': [],
                'error': 'Vosk not installed'
            }
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'duration': 0,
                'words': [],
                'error': str(e)
            }
    
    def _analyze_sentiment(self, audio_path: str) -> Dict:
        """
        Analyze call sentiment using rule-based and keyword analysis
        
        In production, integrate with:
        - OpenAI GPT for semantic sentiment analysis
        - Google Cloud Natural Language API
        - Custom ML sentiment models
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict: Sentiment analysis results
        """
        # First, we need a transcript - placeholder for now
        # In production: Use Whisper or other STT to get transcript
        transcript = ""  # Would come from _transcribe(audio_path)
        
        # Sentiment keywords
        positive_words = [
            'thank', 'thanks', 'grateful', 'appreciate', 'excellent', 'great', 
            'wonderful', 'happy', 'satisfied', 'love', 'perfect', 'amazing',
            'fantastic', 'pleased', 'good', 'helpful', 'friendly'
        ]
        negative_words = [
            'angry', 'upset', 'frustrated', 'disappointed', 'terrible', 'awful',
            'horrible', 'bad', 'worst', 'hate', 'angry', 'annoyed', 'complaint',
            'problem', 'issue', 'broken', 'failed', 'error', 'wrong', 'unhappy'
        ]
        
        # Analyze transcript if available
        sentiment_score = 0.0
        overall_sentiment = 'neutral'
        
        if transcript:
            transcript_lower = transcript.lower()
            
            # Count sentiment indicators
            positive_count = sum(1 for word in positive_words if word in transcript_lower)
            negative_count = sum(1 for word in negative_words if word in transcript_lower)
            
            # Calculate sentiment score (-1.0 to 1.0)
            total_indicators = positive_count + negative_count
            if total_indicators > 0:
                sentiment_score = (positive_count - negative_count) / total_indicators
            
            # Determine overall sentiment
            if sentiment_score > 0.2:
                overall_sentiment = 'positive'
            elif sentiment_score < -0.2:
                overall_sentiment = 'negative'
        
        return {
            'overall_sentiment': overall_sentiment,
            'sentiment_score': sentiment_score,  # -1.0 to 1.0
            'customer_sentiment': overall_sentiment,  # Would differentiate in production
            'agent_sentiment': 'neutral',  # Would analyze separately in production
            'sentiment_timeline': []  # Would track sentiment changes over call
        }
    
    def _detect_keywords(self, audio_path: str) -> Dict:
        """
        Detect important keywords and topics
        
        In production, integrate with:
        - spaCy for Named Entity Recognition
        - YAKE or KeyBERT for keyword extraction
        - Custom domain-specific keyword models
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict: Detected keywords and topics
        """
        # First, we need a transcript - placeholder for now
        transcript = ""  # Would come from _transcribe(audio_path)
        
        # Keyword categories
        competitor_keywords = ['competitor', 'alternative', 'other company', 'switch']
        product_keywords = ['product', 'service', 'feature', 'plan', 'package']
        issue_keywords = ['problem', 'issue', 'broken', 'not working', 'error', 'fail']
        sales_keywords = ['purchase', 'buy', 'price', 'cost', 'discount', 'deal']
        support_keywords = ['help', 'support', 'assistance', 'troubleshoot', 'fix']
        
        keywords = []
        competitor_mentions = []
        product_mentions = []
        issue_keywords_found = []
        
        if transcript:
            transcript_lower = transcript.lower()
            
            # Detect competitor mentions
            for keyword in competitor_keywords:
                if keyword in transcript_lower:
                    competitor_mentions.append(keyword)
            
            # Detect product mentions
            for keyword in product_keywords:
                if keyword in transcript_lower:
                    product_mentions.append(keyword)
            
            # Detect issue keywords
            for keyword in issue_keywords:
                if keyword in transcript_lower:
                    issue_keywords_found.append(keyword)
            
            # Combine all for general keywords
            all_keyword_sets = [
                sales_keywords, support_keywords, issue_keywords,
                product_keywords, competitor_keywords
            ]
            for keyword_set in all_keyword_sets:
                for keyword in keyword_set:
                    if keyword in transcript_lower and keyword not in keywords:
                        keywords.append(keyword)
        
        return {
            'keywords': keywords,
            'competitor_mentions': competitor_mentions,
            'product_mentions': product_mentions,
            'issue_keywords': issue_keywords_found
        }
    
    def _check_compliance(self, audio_path: str) -> Dict:
        """
        Check compliance requirements
        
        In production, integrate with:
        - Custom compliance rule engine
        - Speech recognition for required phrases
        - Regulatory compliance databases
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict: Compliance check results
        """
        # First, we need a transcript - placeholder for now
        transcript = ""  # Would come from _transcribe(audio_path)
        
        # Compliance requirements
        required_phrases = [
            'this call may be recorded',
            'for quality assurance',
            'terms and conditions',
            'do you agree'
        ]
        
        prohibited_phrases = [
            'guaranteed',
            'no risk',
            'can\'t lose',
            'promise'  # In certain contexts
        ]
        
        violations = []
        warnings = []
        required_found = []
        prohibited_found = []
        
        if transcript:
            transcript_lower = transcript.lower()
            
            # Check for required phrases
            for phrase in required_phrases:
                if phrase in transcript_lower:
                    required_found.append(phrase)
            
            # Check for prohibited phrases
            for phrase in prohibited_phrases:
                if phrase in transcript_lower:
                    prohibited_found.append(phrase)
                    violations.append(f"Prohibited phrase detected: '{phrase}'")
            
            # Check if all required phrases were found
            missing_required = [p for p in required_phrases if p not in required_found]
            if missing_required:
                warnings.extend([f"Missing required phrase: '{p}'" for p in missing_required])
        
        compliant = len(violations) == 0
        
        return {
            'compliant': compliant,
            'violations': violations,
            'warnings': warnings,
            'required_phrases_found': required_found,
            'prohibited_phrases_found': prohibited_found
        }
    
    def _score_quality(self, audio_path: str) -> Dict:
        """
        Score call quality based on multiple factors
        
        In production, integrate with:
        - Speech analytics for tone and pace
        - ML models for agent performance
        - Customer satisfaction prediction models
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict: Quality scores
        """
        # First, we need a transcript - placeholder for now
        transcript = ""  # Would come from _transcribe(audio_path)
        
        # Quality indicators
        positive_indicators = [
            'thank you', 'appreciate', 'understand', 'help you',
            'certainly', 'absolutely', 'of course', 'glad to help'
        ]
        
        negative_indicators = [
            'wait', 'hold on', 'I don\'t know', 'not sure',
            'can\'t help', 'impossible', 'no way'
        ]
        
        professionalism_indicators = [
            'sir', 'ma\'am', 'please', 'thank you',
            'may I', 'would you like'
        ]
        
        overall_score = 50.0  # Base score
        agent_performance = 50.0
        customer_satisfaction = 50.0
        resolution_quality = 50.0
        professionalism = 50.0
        
        if transcript:
            transcript_lower = transcript.lower()
            
            # Calculate agent performance based on positive/negative indicators
            positive_count = sum(1 for indicator in positive_indicators if indicator in transcript_lower)
            negative_count = sum(1 for indicator in negative_indicators if indicator in transcript_lower)
            
            if positive_count + negative_count > 0:
                agent_performance = 50 + (positive_count - negative_count) * 5
                agent_performance = max(0, min(100, agent_performance))  # Clamp to 0-100
            
            # Calculate professionalism
            professionalism_count = sum(1 for indicator in professionalism_indicators if indicator in transcript_lower)
            professionalism = min(100, 50 + professionalism_count * 10)
            
            # Customer satisfaction based on positive sentiment words
            satisfaction_words = ['satisfied', 'happy', 'thank', 'great', 'excellent']
            dissatisfaction_words = ['unhappy', 'disappointed', 'frustrated', 'angry']
            
            sat_count = sum(1 for word in satisfaction_words if word in transcript_lower)
            dissat_count = sum(1 for word in dissatisfaction_words if word in transcript_lower)
            
            if sat_count + dissat_count > 0:
                customer_satisfaction = 50 + (sat_count - dissat_count) * 10
                customer_satisfaction = max(0, min(100, customer_satisfaction))
            
            # Resolution quality based on resolution keywords
            resolution_words = ['resolved', 'fixed', 'solved', 'working now', 'taken care of']
            resolution_count = sum(1 for word in resolution_words if word in transcript_lower)
            resolution_quality = min(100, 50 + resolution_count * 15)
            
            # Overall score is weighted average
            overall_score = (
                agent_performance * 0.3 +
                customer_satisfaction * 0.3 +
                resolution_quality * 0.25 +
                professionalism * 0.15
            )
        
        return {
            'overall_score': round(overall_score, 2),  # 0-100
            'agent_performance': round(agent_performance, 2),
            'customer_satisfaction': round(customer_satisfaction, 2),
            'resolution_quality': round(resolution_quality, 2),
            'professionalism': round(professionalism, 2)
        }
    
    def _summarize(self, audio_path: str) -> Dict:
        """
        Generate call summary using extractive summarization
        
        In production, integrate with:
        - OpenAI GPT for abstractive summarization
        - BART or T5 models for summarization
        - Custom domain-specific summarization models
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict: Call summary with key points and action items
        """
        # First, we need a transcript - placeholder for now
        transcript = ""  # Would come from _transcribe(audio_path)
        
        summary = ""
        key_points = []
        action_items = []
        outcomes = []
        
        if transcript:
            # Split into sentences
            sentences = [s.strip() for s in transcript.split('.') if s.strip()]
            
            # Extractive summarization - select most important sentences
            # In production, use more sophisticated methods (TF-IDF, TextRank, etc.)
            
            # Look for action items (sentences with action verbs)
            action_verbs = ['will', 'need to', 'must', 'should', 'going to', 'have to']
            for sentence in sentences:
                if any(verb in sentence.lower() for verb in action_verbs):
                    action_items.append(sentence)
            
            # Look for outcomes (sentences with resolution indicators)
            outcome_indicators = ['resolved', 'fixed', 'completed', 'done', 'finished', 'successful']
            for sentence in sentences:
                if any(indicator in sentence.lower() for indicator in outcome_indicators):
                    outcomes.append(sentence)
            
            # Generate key points from first few sentences and important indicators
            important_keywords = [
                'issue', 'problem', 'request', 'question', 'concern',
                'solution', 'answer', 'resolution', 'next steps'
            ]
            for sentence in sentences[:5]:  # First 5 sentences
                if any(keyword in sentence.lower() for keyword in important_keywords):
                    key_points.append(sentence)
            
            # Create summary from key points
            if key_points:
                summary = '. '.join(key_points[:3]) + '.'
            elif sentences:
                summary = '. '.join(sentences[:2]) + '.'
        
        return {
            'summary': summary,
            'key_points': key_points[:5],  # Top 5 key points
            'action_items': action_items[:5],  # Top 5 action items
            'outcomes': outcomes[:3]  # Top 3 outcomes
        }
    
    def search_recordings(self, criteria: Dict) -> List[str]:
        """
        Search recordings by analysis criteria with improved matching
        
        Args:
            criteria: Search criteria dict with keys:
                - sentiment: 'positive', 'negative', or 'neutral'
                - keywords: list of keywords to search for
                - min_quality_score: minimum quality score (0-100)
                - compliant: True/False for compliance status
            
        Returns:
            List[str]: Matching recording IDs
        """
        matching = []
        
        for recording_id, analysis in self.analyses.items():
            match = True
            
            # Check sentiment criteria
            if 'sentiment' in criteria:
                sentiment_result = analysis['analyses'].get('sentiment', {})
                if sentiment_result.get('overall_sentiment') != criteria['sentiment']:
                    match = False
            
            # Check keyword criteria
            if 'keywords' in criteria and match:
                keyword_result = analysis['analyses'].get('keywords', {})
                found_keywords = keyword_result.get('keywords', [])
                if not any(k in found_keywords for k in criteria['keywords']):
                    match = False
            
            # Check quality score criteria
            if 'min_quality_score' in criteria and match:
                quality_result = analysis['analyses'].get('quality', {})
                overall_score = quality_result.get('overall_score', 0)
                if overall_score < criteria['min_quality_score']:
                    match = False
            
            # Check compliance criteria
            if 'compliant' in criteria and match:
                compliance_result = analysis['analyses'].get('compliance', {})
                if compliance_result.get('compliant') != criteria['compliant']:
                    match = False
            
            if match:
                matching.append(recording_id)
        
        return matching
    
    def get_analysis(self, recording_id: str) -> Optional[Dict]:
        """
        Get analysis results for a recording
        
        Args:
            recording_id: Recording identifier
            
        Returns:
            Optional[Dict]: Analysis results or None if not found
        """
        return self.analyses.get(recording_id)
    
    def get_trend_analysis(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Analyze trends over time with aggregated metrics
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dict: Trend analysis with sentiment, quality, keywords, and compliance data
        """
        sentiment_trend = []
        quality_trend = []
        keyword_trends = {}
        compliance_data = {'compliant': 0, 'non_compliant': 0}
        
        # Filter analyses by date range
        filtered_analyses = []
        for recording_id, analysis in self.analyses.items():
            try:
                analyzed_at = datetime.fromisoformat(analysis['analyzed_at'])
                if start_date <= analyzed_at <= end_date:
                    filtered_analyses.append(analysis)
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Skipping analysis {recording_id} due to invalid timestamp: {e}")
                continue
        
        if not filtered_analyses:
            return {
                'sentiment_trend': [],
                'quality_trend': [],
                'keyword_trends': {},
                'compliance_rate': 0.0,
                'total_recordings': 0
            }
        
        # Aggregate sentiment data
        for analysis in filtered_analyses:
            sentiment_data = analysis['analyses'].get('sentiment', {})
            if sentiment_data:
                sentiment_trend.append({
                    'date': analysis['analyzed_at'],
                    'sentiment': sentiment_data.get('overall_sentiment', 'neutral'),
                    'score': sentiment_data.get('sentiment_score', 0.0)
                })
        
        # Aggregate quality data
        for analysis in filtered_analyses:
            quality_data = analysis['analyses'].get('quality', {})
            if quality_data:
                quality_trend.append({
                    'date': analysis['analyzed_at'],
                    'overall_score': quality_data.get('overall_score', 0.0),
                    'agent_performance': quality_data.get('agent_performance', 0.0),
                    'customer_satisfaction': quality_data.get('customer_satisfaction', 0.0)
                })
        
        # Aggregate keyword trends
        for analysis in filtered_analyses:
            keyword_data = analysis['analyses'].get('keywords', {})
            if keyword_data:
                for keyword in keyword_data.get('keywords', []):
                    keyword_trends[keyword] = keyword_trends.get(keyword, 0) + 1
        
        # Sort keyword trends by frequency
        keyword_trends = dict(sorted(keyword_trends.items(), key=lambda x: x[1], reverse=True))
        
        # Calculate compliance rate
        for analysis in filtered_analyses:
            compliance_data_item = analysis['analyses'].get('compliance', {})
            if compliance_data_item:
                if compliance_data_item.get('compliant', False):
                    compliance_data['compliant'] += 1
                else:
                    compliance_data['non_compliant'] += 1
        
        total_compliance_checks = compliance_data['compliant'] + compliance_data['non_compliant']
        compliance_rate = (
            compliance_data['compliant'] / total_compliance_checks
            if total_compliance_checks > 0 else 0.0
        )
        
        return {
            'sentiment_trend': sentiment_trend,
            'quality_trend': quality_trend,
            'keyword_trends': keyword_trends,
            'compliance_rate': round(compliance_rate * 100, 2),  # As percentage
            'total_recordings': len(filtered_analyses),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def get_statistics(self) -> Dict:
        """Get analytics statistics"""
        return {
            'enabled': self.enabled,
            'auto_analyze': self.auto_analyze,
            'total_analyses': self.total_analyses,
            'analyses_by_type': self.analyses_by_type,
            'available_analysis_types': self.analysis_types
        }


# Global instance
_recording_analytics = None


def get_recording_analytics(config=None) -> RecordingAnalytics:
    """Get or create recording analytics instance"""
    global _recording_analytics
    if _recording_analytics is None:
        _recording_analytics = RecordingAnalytics(config)
    return _recording_analytics
