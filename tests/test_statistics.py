"""
Tests for Statistics and Analytics System
"""
import unittest
import tempfile
import os
import sys
import json
import shutil
from datetime import datetime, timedelta
from pbx.features.cdr import CDRSystem, CDRRecord, CallDisposition
from pbx.features.statistics import StatisticsEngine


class MockPBXCore:
    """Mock PBX core for testing"""
    def __init__(self):
        self.calls = []
        self.extensions = {}
        self.start_time = datetime.now() - timedelta(hours=5)


class TestStatisticsEngine(unittest.TestCase):
    """Test statistics engine functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cdr_system = CDRSystem(storage_path=self.temp_dir)
        self.stats_engine = StatisticsEngine(self.cdr_system)
        self.pbx_core = MockPBXCore()
        
        # Create sample call data
        self._create_sample_cdr_data()
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_sample_cdr_data(self):
        """Create sample CDR records for testing"""
        today = datetime.now()
        
        # Create CDR records for the last 3 days
        for day_offset in range(3):
            date = (today - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            filename = os.path.join(self.temp_dir, f"cdr_{date}.jsonl")
            
            with open(filename, 'w') as f:
                # Create 10 sample records per day
                for i in range(10):
                    record = {
                        'call_id': f'call-{day_offset}-{i}',
                        'from_extension': f'100{i % 5}',
                        'to_extension': f'200{i % 3}',
                        'start_time': (today - timedelta(days=day_offset, hours=i)).isoformat(),
                        'answer_time': (today - timedelta(days=day_offset, hours=i, minutes=1)).isoformat() if i % 4 != 0 else None,
                        'end_time': (today - timedelta(days=day_offset, hours=i, minutes=3)).isoformat(),
                        'disposition': 'answered' if i % 4 != 0 else 'no_answer',
                        'duration': 180.0 if i % 4 != 0 else 60.0,
                        'billsec': 120.0 if i % 4 != 0 else 0.0,
                        'recording_file': None,
                        'hangup_cause': None,
                        'user_agent': 'TestPhone'
                    }
                    json.dump(record, f)
                    f.write('\n')
    
    def test_dashboard_statistics(self):
        """Test getting dashboard statistics"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        
        # Check that all expected keys are present
        self.assertIn('overview', stats)
        self.assertIn('daily_trends', stats)
        self.assertIn('hourly_distribution', stats)
        self.assertIn('top_callers', stats)
        self.assertIn('call_disposition', stats)
        self.assertIn('peak_hours', stats)
        self.assertIn('average_metrics', stats)
        
        # Check overview stats
        overview = stats['overview']
        self.assertEqual(overview['total_calls'], 30)  # 10 calls per day * 3 days
        self.assertTrue(overview['answered_calls'] > 0)
        self.assertTrue(overview['answer_rate'] > 0)
    
    def test_daily_trends(self):
        """Test daily trends calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        trends = stats['daily_trends']
        
        # Should have 3 days of data
        self.assertEqual(len(trends), 3)
        
        # Each day should have the expected fields
        for trend in trends:
            self.assertIn('date', trend)
            self.assertIn('total_calls', trend)
            self.assertIn('answered', trend)
            self.assertIn('missed', trend)
            self.assertIn('failed', trend)
    
    def test_hourly_distribution(self):
        """Test hourly distribution calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        distribution = stats['hourly_distribution']
        
        # Should have 24 hours
        self.assertEqual(len(distribution), 24)
        
        # Check that hours are in order
        for i, dist in enumerate(distribution):
            self.assertEqual(dist['hour'], i)
            self.assertIn('calls', dist)
    
    def test_top_callers(self):
        """Test top callers calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        top_callers = stats['top_callers']
        
        # Should have some top callers
        self.assertTrue(len(top_callers) > 0)
        
        # Check that callers are sorted by call count
        for i in range(len(top_callers) - 1):
            self.assertGreaterEqual(
                top_callers[i]['calls'],
                top_callers[i + 1]['calls']
            )
    
    def test_call_disposition(self):
        """Test call disposition breakdown"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        disposition = stats['call_disposition']
        
        # Should have disposition data
        self.assertTrue(len(disposition) > 0)
        
        # Check that percentages add up to approximately 100
        total_percentage = sum(d['percentage'] for d in disposition)
        self.assertAlmostEqual(total_percentage, 100.0, delta=0.1)
    
    def test_peak_hours(self):
        """Test peak hours calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        peak_hours = stats['peak_hours']
        
        # Should have up to 3 peak hours
        self.assertTrue(len(peak_hours) <= 3)
        
        # Each peak hour should have hour and calls
        for peak in peak_hours:
            self.assertIn('hour', peak)
            self.assertIn('calls', peak)
    
    def test_average_metrics(self):
        """Test average metrics calculation"""
        stats = self.stats_engine.get_dashboard_statistics(days=3)
        avg_metrics = stats['average_metrics']
        
        # Should have average metrics
        self.assertIn('avg_calls_per_day', avg_metrics)
        self.assertIn('avg_answered_per_day', avg_metrics)
        self.assertIn('avg_duration_per_day', avg_metrics)
        
        # Averages should be positive
        self.assertGreater(avg_metrics['avg_calls_per_day'], 0)
    
    def test_call_quality_metrics(self):
        """Test call quality metrics (placeholder)"""
        quality = self.stats_engine.get_call_quality_metrics()
        
        # Should have quality metrics
        self.assertIn('average_mos', quality)
        self.assertIn('average_jitter', quality)
        self.assertIn('average_packet_loss', quality)
        self.assertIn('average_latency', quality)
        self.assertIn('quality_distribution', quality)
    
    def test_real_time_metrics(self):
        """Test real-time metrics"""
        metrics = self.stats_engine.get_real_time_metrics(self.pbx_core)
        
        # Should have real-time metrics
        self.assertIn('active_calls', metrics)
        self.assertIn('registered_extensions', metrics)
        self.assertIn('system_uptime', metrics)
        self.assertIn('timestamp', metrics)
        
        # Uptime should be greater than 0
        self.assertGreater(metrics['system_uptime'], 0)
    
    def test_empty_data(self):
        """Test statistics with empty data"""
        # Create a new statistics engine with empty CDR
        temp_dir = tempfile.mkdtemp()
        cdr_system = CDRSystem(storage_path=temp_dir)
        stats_engine = StatisticsEngine(cdr_system)
        
        try:
            stats = stats_engine.get_dashboard_statistics(days=7)
            
            # Should not raise errors with empty data
            self.assertEqual(stats['overview']['total_calls'], 0)
            self.assertEqual(len(stats['daily_trends']), 7)
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


class TestCDRSystem(unittest.TestCase):
    """Test CDR system functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cdr_system = CDRSystem(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_record_lifecycle(self):
        """Test CDR record lifecycle"""
        # Start a record
        record = self.cdr_system.start_record('test-call', '1001', '2001')
        self.assertEqual(record.call_id, 'test-call')
        self.assertEqual(record.from_extension, '1001')
        self.assertEqual(record.to_extension, '2001')
        
        # Mark as answered
        self.cdr_system.mark_answered('test-call')
        self.assertEqual(record.disposition, CallDisposition.ANSWERED)
        
        # End the record
        self.cdr_system.end_record('test-call', 'normal_clearing')
        
        # Record should be saved and removed from active records
        self.assertNotIn('test-call', self.cdr_system.active_records)
    
    def test_get_statistics(self):
        """Test getting CDR statistics"""
        # Create a sample record
        self.cdr_system.start_record('test-call', '1001', '2001')
        self.cdr_system.mark_answered('test-call')
        self.cdr_system.end_record('test-call')
        
        # Get statistics
        stats = self.cdr_system.get_statistics()
        
        self.assertEqual(stats['total_calls'], 1)
        self.assertEqual(stats['answered_calls'], 1)
        self.assertEqual(stats['answer_rate'], 100.0)


def run_all_tests():
    """Run all tests in this module"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    unittest.main()
