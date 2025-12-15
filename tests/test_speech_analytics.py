"""
Tests for Speech Analytics Framework
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.features.speech_analytics import SpeechAnalyticsEngine


class TestSpeechAnalytics(unittest.TestCase):
    """Test Speech Analytics functionality"""

    def setUp(self):
        """Set up test database"""
        import sqlite3
        
        class MockDB:
            def __init__(self):
                self.db_type = 'sqlite'
                self.conn = sqlite3.connect(':memory:')
                self.enabled = True
                
            def execute(self, query, params=None):
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor.fetchall()
                
            def disconnect(self):
                self.conn.close()
        
        self.db = MockDB()
        
        # Create tables
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS speech_analytics_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extension TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                transcription_enabled INTEGER DEFAULT 1,
                sentiment_enabled INTEGER DEFAULT 1,
                summarization_enabled INTEGER DEFAULT 1,
                keywords TEXT,
                alert_threshold REAL DEFAULT 0.7,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS call_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id TEXT NOT NULL,
                transcript TEXT,
                summary TEXT,
                sentiment TEXT,
                sentiment_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.config = {
            'speech_analytics.enabled': True,
            'speech_analytics.vosk_model_path': '/tmp/vosk-model'
        }
        self.engine = SpeechAnalyticsEngine(self.db, self.config)

    def tearDown(self):
        """Clean up test database"""
        self.db.disconnect()

    def test_initialization(self):
        """Test engine initialization"""
        self.assertIsNotNone(self.engine)
        # Enabled based on config key 'speech_analytics.enabled'
        self.assertTrue(self.engine.enabled)

    def test_update_config(self):
        """Test updating configuration"""
        config = {
            'enabled': True,
            'transcription_enabled': True,
            'sentiment_enabled': True,
            'keywords': 'urgent,complaint,refund'
        }
        
        result = self.engine.update_config('1001', config)
        self.assertTrue(result)

    def test_get_config(self):
        """Test retrieving configuration"""
        # First create a config
        config = {
            'enabled': True,
            'transcription_enabled': True,
            'keywords': 'test,keywords'
        }
        self.engine.update_config('1001', config)
        
        # Now retrieve it
        retrieved = self.engine.get_config('1001')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['extension'], '1001')
        self.assertTrue(retrieved['enabled'])

    def test_sentiment_analysis_positive(self):
        """Test positive sentiment analysis"""
        text = "This is excellent service! I'm very happy and satisfied with the great support."
        result = self.engine.analyze_sentiment(text)
        
        self.assertEqual(result['sentiment'], 'positive')
        self.assertGreater(result['score'], 0)
        self.assertGreater(result['confidence'], 0)

    def test_sentiment_analysis_negative(self):
        """Test negative sentiment analysis"""
        text = "This is terrible service. I'm very frustrated and disappointed with the poor support."
        result = self.engine.analyze_sentiment(text)
        
        self.assertEqual(result['sentiment'], 'negative')
        self.assertLess(result['score'], 0)
        self.assertGreater(result['confidence'], 0)

    def test_sentiment_analysis_neutral(self):
        """Test neutral sentiment analysis"""
        text = "This is a regular phone call about account information."
        result = self.engine.analyze_sentiment(text)
        
        self.assertEqual(result['sentiment'], 'neutral')
        self.assertAlmostEqual(result['score'], 0.0, delta=0.1)

    def test_sentiment_analysis_empty(self):
        """Test sentiment analysis with empty text"""
        result = self.engine.analyze_sentiment("")
        
        self.assertEqual(result['sentiment'], 'neutral')
        self.assertEqual(result['score'], 0.0)

    def test_keyword_detection(self):
        """Test keyword detection"""
        text = "I have an urgent complaint about my refund"
        keywords = ['urgent', 'complaint', 'refund', 'cancel']
        
        detected = self.engine.detect_keywords(text, keywords)
        self.assertIn('urgent', detected)
        self.assertIn('complaint', detected)
        self.assertIn('refund', detected)
        self.assertNotIn('cancel', detected)

    def test_keyword_detection_case_insensitive(self):
        """Test case-insensitive keyword detection"""
        text = "URGENT: This is an IMPORTANT issue"
        keywords = ['urgent', 'important']
        
        detected = self.engine.detect_keywords(text, keywords)
        self.assertIn('urgent', detected)
        self.assertIn('important', detected)

    def test_generate_summary(self):
        """Test call summary generation"""
        transcript = """
        Hello, I'm calling about a problem with my order.
        I placed an order last week but haven't received it yet.
        This is very important because I need it urgently.
        Can you please help me track the order?
        Thank you for your assistance.
        """
        
        summary = self.engine.generate_summary('call-123', transcript)
        self.assertIsNotNone(summary)
        self.assertGreater(len(summary), 0)
        # Summary should be shorter than original
        self.assertLess(len(summary), len(transcript))

    def test_generate_summary_short_text(self):
        """Test summary generation with short text"""
        transcript = "Hello, thanks."
        summary = self.engine.generate_summary('call-124', transcript)
        
        self.assertEqual(summary, "Call too short to summarize")

    def test_generate_summary_stores_in_db(self):
        """Test that summary is stored in database"""
        transcript = """
        I need help with my account. There is a billing problem.
        The charges are incorrect and I need a refund.
        This is urgent please help me resolve this issue.
        """
        
        call_id = 'call-125'
        summary = self.engine.generate_summary(call_id, transcript)
        
        # Retrieve from database
        retrieved = self.engine.get_call_summary(call_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['call_id'], call_id)
        self.assertIn('summary', retrieved)

    def test_get_call_summary_not_found(self):
        """Test retrieving non-existent summary"""
        summary = self.engine.get_call_summary('nonexistent')
        self.assertIsNone(summary)

    def test_get_all_configs(self):
        """Test retrieving all configurations"""
        # Create multiple configs
        for ext in ['1001', '1002', '1003']:
            self.engine.update_config(ext, {'enabled': True})
        
        configs = self.engine.get_all_configs()
        self.assertEqual(len(configs), 3)

    def test_analyze_audio_stream_without_vosk(self):
        """Test audio analysis without Vosk library"""
        # Should not crash even without Vosk
        result = self.engine.analyze_audio_stream('call-126', b'dummy_audio_data')
        
        self.assertIsNotNone(result)
        self.assertIn('call_id', result)
        self.assertEqual(result['call_id'], 'call-126')

    def test_analyze_call_recording(self):
        """Test full call recording analysis"""
        result = self.engine.analyze_call_recording('call-127', '/tmp/test.wav')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['call_id'], 'call-127')
        self.assertIn('status', result)

    def test_sentiment_scoring(self):
        """Test sentiment score calculation"""
        # Mixed sentiment
        text = "The service was good but I had some problems with billing"
        result = self.engine.analyze_sentiment(text)
        
        # Should be close to neutral or slightly negative
        self.assertLess(abs(result['score']), 0.5)

    def test_summary_preserves_important_info(self):
        """Test that summary preserves important information"""
        transcript = """
        Good morning, this is about order number 12345.
        I need urgent help because the delivery is late.
        I was promised delivery yesterday but nothing arrived.
        This is causing major problems for our business.
        Please expedite the order immediately.
        """
        
        summary = self.engine.generate_summary('call-128', transcript)
        
        # Summary should contain key information
        summary_lower = summary.lower()
        # Should contain at least one important keyword
        important_keywords = ['order', 'urgent', 'delivery', 'problem']
        has_important = any(kw in summary_lower for kw in important_keywords)
        self.assertTrue(has_important)


if __name__ == '__main__':
    unittest.main()
