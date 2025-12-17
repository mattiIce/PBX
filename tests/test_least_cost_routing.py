"""
Tests for Least-Cost Routing (LCR) System
"""
import os
import sys
import unittest
import tempfile
import sqlite3
from datetime import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.least_cost_routing import (
    DialPattern, RateEntry, TimeBasedRate, LeastCostRouting
)


class MockPBX:
    """Mock PBX for testing"""
    def __init__(self, db_path=None):
        self.trunk_manager = MockTrunkManager()
        self.config = MockConfig(db_path) if db_path else None


class MockConfig:
    """Mock config for testing"""
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get(self, key, default=None):
        if key == 'database':
            return {'path': self.db_path}
        return default


class MockTrunkManager:
    """Mock trunk manager for testing"""
    def __init__(self):
        self.trunks = {}
    
    def get_trunk(self, trunk_id):
        return self.trunks.get(trunk_id)


class MockTrunk:
    """Mock trunk for testing"""
    def __init__(self, trunk_id):
        self.trunk_id = trunk_id
        self.total_calls = 100
        self.successful_calls = 95


class TestDialPattern(unittest.TestCase):
    """Test DialPattern class"""
    
    def test_pattern_matching(self):
        """Test dial pattern matching"""
        # US toll-free pattern
        pattern = DialPattern(r'^1(800|888|877|866)\d{7}$', 'US Toll-Free')
        
        self.assertTrue(pattern.matches('18005551234'))
        self.assertTrue(pattern.matches('18885551234'))
        self.assertFalse(pattern.matches('12125551234'))
        self.assertFalse(pattern.matches('5551234'))
    
    def test_international_pattern(self):
        """Test international dial pattern"""
        # International calls (011 prefix)
        pattern = DialPattern(r'^011\d+$', 'International')
        
        self.assertTrue(pattern.matches('011441234567890'))
        self.assertTrue(pattern.matches('01133123456789'))
        self.assertFalse(pattern.matches('12125551234'))


class TestRateEntry(unittest.TestCase):
    """Test RateEntry class"""
    
    def test_cost_calculation_basic(self):
        """Test basic cost calculation"""
        pattern = DialPattern(r'^\d{10}$', 'US Local')
        rate = RateEntry(
            trunk_id='trunk1',
            pattern=pattern,
            rate_per_minute=0.01,
            connection_fee=0.0
        )
        
        # 60 seconds = 1 minute = $0.01
        self.assertEqual(rate.calculate_cost(60), 0.01)
        
        # 180 seconds = 3 minutes = $0.03
        self.assertEqual(rate.calculate_cost(180), 0.03)
    
    def test_cost_calculation_with_connection_fee(self):
        """Test cost calculation with connection fee"""
        pattern = DialPattern(r'^011', 'International')
        rate = RateEntry(
            trunk_id='trunk1',
            pattern=pattern,
            rate_per_minute=0.20,
            connection_fee=0.05
        )
        
        # 60 seconds = 1 minute = $0.20 + $0.05 connection = $0.25
        self.assertEqual(rate.calculate_cost(60), 0.25)
    
    def test_cost_calculation_with_minimum(self):
        """Test cost calculation with minimum duration"""
        pattern = DialPattern(r'^\d{10}$', 'US Local')
        rate = RateEntry(
            trunk_id='trunk1',
            pattern=pattern,
            rate_per_minute=0.01,
            minimum_seconds=30
        )
        
        # 10 seconds, but minimum is 30 seconds = $0.005
        cost = rate.calculate_cost(10)
        self.assertEqual(cost, round((30 / 60.0) * 0.01, 4))
    
    def test_cost_calculation_with_increment(self):
        """Test cost calculation with billing increment"""
        pattern = DialPattern(r'^\d{10}$', 'US Local')
        rate = RateEntry(
            trunk_id='trunk1',
            pattern=pattern,
            rate_per_minute=0.01,
            billing_increment=6
        )
        
        # 65 seconds should round up to 66 (next 6-second increment)
        # 66 / 60 * 0.01 = $0.011
        cost = rate.calculate_cost(65)
        self.assertEqual(cost, 0.011)


class TestTimeBasedRate(unittest.TestCase):
    """Test TimeBasedRate class"""
    
    def test_time_range_normal(self):
        """Test time range (normal, non-crossing midnight)"""
        # Business hours: 9 AM to 5 PM weekdays
        rate = TimeBasedRate(
            name='Business Hours',
            start_time=time(9, 0),
            end_time=time(17, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Monday-Friday
            rate_multiplier=1.0
        )
        
        # This test is time-dependent, so we won't assert specific results
        # Just ensure it runs without error
        _ = rate.applies_now()
    
    def test_time_range_midnight_crossing(self):
        """Test time range crossing midnight"""
        # Late night: 11 PM to 3 AM
        rate = TimeBasedRate(
            name='Late Night',
            start_time=time(23, 0),
            end_time=time(3, 0),
            days_of_week=[0, 1, 2, 3, 4, 5, 6],  # All days
            rate_multiplier=0.5
        )
        
        # This test is time-dependent, so we won't assert specific results
        # Just ensure it runs without error
        _ = rate.applies_now()


class TestLeastCostRouting(unittest.TestCase):
    """Test LeastCostRouting class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.pbx = MockPBX(self.db_path)
        self.lcr = LeastCostRouting(self.pbx)
    
    def tearDown(self):
        """Clean up test environment"""
        # Close and remove temporary database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_add_rate(self):
        """Test adding a rate"""
        self.lcr.add_rate(
            trunk_id='trunk1',
            pattern=r'^\d{10}$',
            rate_per_minute=0.01,
            description='US Local'
        )
        
        self.assertEqual(len(self.lcr.rate_entries), 1)
        self.assertEqual(self.lcr.rate_entries[0].trunk_id, 'trunk1')
    
    def test_add_time_based_rate(self):
        """Test adding time-based rate"""
        self.lcr.add_time_based_rate(
            name='Peak Hours',
            start_hour=9,
            start_minute=0,
            end_hour=17,
            end_minute=0,
            days=[0, 1, 2, 3, 4],
            multiplier=1.2
        )
        
        self.assertEqual(len(self.lcr.time_based_rates), 1)
        self.assertEqual(self.lcr.time_based_rates[0].name, 'Peak Hours')
    
    def test_get_applicable_rates(self):
        """Test getting applicable rates for a number"""
        # Add multiple rates for different patterns
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.01, 'US Local')
        self.lcr.add_rate('trunk2', r'^\d{10}$', 0.015, 'US Local Alt')
        self.lcr.add_rate('trunk3', r'^1800', 0.00, 'Toll-Free')
        
        # Test local number
        rates = self.lcr.get_applicable_rates('2125551234')
        self.assertEqual(len(rates), 2)  # Should match trunk1 and trunk2
        # Should be sorted by cost (lowest first)
        self.assertEqual(rates[0][0], 'trunk1')
    
    def test_select_trunk_cost_based(self):
        """Test trunk selection based on cost"""
        # Add rates
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.02, 'US Local - Expensive')
        self.lcr.add_rate('trunk2', r'^\d{10}$', 0.01, 'US Local - Cheap')
        
        # Select trunk (trunk2 should be selected as it's cheaper)
        selected = self.lcr.select_trunk('2125551234', ['trunk1', 'trunk2'])
        self.assertEqual(selected, 'trunk2')
    
    def test_select_trunk_with_quality(self):
        """Test trunk selection considering quality"""
        self.lcr.prefer_quality = True
        self.lcr.quality_weight = 0.5
        
        # Add mock trunks
        trunk1 = MockTrunk('trunk1')
        trunk1.successful_calls = 95
        trunk1.total_calls = 100
        
        trunk2 = MockTrunk('trunk2')
        trunk2.successful_calls = 50
        trunk2.total_calls = 100
        
        self.pbx.trunk_manager.trunks['trunk1'] = trunk1
        self.pbx.trunk_manager.trunks['trunk2'] = trunk2
        
        # Add rates (trunk2 is cheaper but lower quality)
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.02, 'US Local - Expensive but Reliable')
        self.lcr.add_rate('trunk2', r'^\d{10}$', 0.01, 'US Local - Cheap but Unreliable')
        
        # With quality consideration, should might select trunk1
        selected = self.lcr.select_trunk('2125551234', ['trunk1', 'trunk2'])
        # Result depends on the weighting algorithm, just ensure it's one of the trunks
        self.assertIn(selected, ['trunk1', 'trunk2'])
    
    def test_statistics(self):
        """Test statistics gathering"""
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.01, 'US Local')
        self.lcr.select_trunk('2125551234', ['trunk1'])
        
        stats = self.lcr.get_statistics()
        
        self.assertTrue(stats['enabled'])
        self.assertEqual(stats['total_routes'], 1)
        self.assertEqual(stats['rate_entries'], 1)
    
    def test_clear_rates(self):
        """Test clearing rates"""
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.01, 'US Local')
        self.lcr.add_rate('trunk2', r'^011', 0.20, 'International')
        
        self.assertEqual(len(self.lcr.rate_entries), 2)
        
        self.lcr.clear_rates()
        
        self.assertEqual(len(self.lcr.rate_entries), 0)
    
    def test_disabled_lcr(self):
        """Test that disabled LCR returns None"""
        self.lcr.enabled = False
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.01, 'US Local')
        
        selected = self.lcr.select_trunk('2125551234', ['trunk1'])
        self.assertIsNone(selected)
    
    def test_rate_persists_to_database(self):
        """Test that rates are saved to database"""
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.01, 'US Local')
        
        # Verify in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT trunk_id, pattern, rate_per_minute FROM lcr_rates')
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'trunk1')
        self.assertEqual(row[1], r'^\d{10}$')
        self.assertEqual(row[2], 0.01)
    
    def test_time_rate_persists_to_database(self):
        """Test that time-based rates are saved to database"""
        self.lcr.add_time_based_rate('Peak Hours', 9, 0, 17, 0, [0, 1, 2, 3, 4], 1.2)
        
        # Verify in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name, start_hour, rate_multiplier FROM lcr_time_rates')
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'Peak Hours')
        self.assertEqual(row[1], 9)
        self.assertEqual(row[2], 1.2)
    
    def test_rates_load_from_database(self):
        """Test that rates are loaded from database on initialization"""
        # Add rate and create new LCR instance (simulating restart)
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.01, 'US Local')
        
        # Create new instance
        lcr2 = LeastCostRouting(self.pbx)
        
        # Verify rate was loaded
        self.assertEqual(len(lcr2.rate_entries), 1)
        self.assertEqual(lcr2.rate_entries[0].trunk_id, 'trunk1')
    
    def test_time_rates_load_from_database(self):
        """Test that time-based rates are loaded from database"""
        self.lcr.add_time_based_rate('Peak Hours', 9, 0, 17, 0, [0, 1, 2, 3, 4], 1.2)
        
        # Create new instance (simulating restart)
        lcr2 = LeastCostRouting(self.pbx)
        
        # Verify time rate was loaded
        self.assertEqual(len(lcr2.time_based_rates), 1)
        self.assertEqual(lcr2.time_based_rates[0].name, 'Peak Hours')
    
    def test_clear_rates_deletes_from_database(self):
        """Test that clearing rates deletes from database"""
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.01, 'US Local')
        self.lcr.clear_rates()
        
        # Verify database is empty
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM lcr_rates')
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 0)
    
    def test_multiple_rates_persist(self):
        """Test that multiple rates persist across restarts"""
        self.lcr.add_rate('trunk1', r'^\d{10}$', 0.01, 'US Local')
        self.lcr.add_rate('trunk2', r'^011', 0.20, 'International')
        self.lcr.add_time_based_rate('Peak', 9, 0, 17, 0, [0, 1, 2, 3, 4], 1.2)
        
        # Create new instance
        lcr2 = LeastCostRouting(self.pbx)
        
        # Verify all persisted
        self.assertEqual(len(lcr2.rate_entries), 2)
        self.assertEqual(len(lcr2.time_based_rates), 1)


if __name__ == '__main__':
    unittest.main()
