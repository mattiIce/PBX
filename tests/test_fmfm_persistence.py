"""
Test Find Me/Follow Me database persistence
"""
import os
import sys
import unittest
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.find_me_follow_me import FindMeFollowMe
from pbx.utils.database import DatabaseBackend


class TestFMFMPersistence(unittest.TestCase):
    """Test FMFM configuration persistence"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.config = {
            'database.type': 'sqlite',
            'database.path': self.temp_db.name,
            'features': {
                'find_me_follow_me': {
                    'enabled': True
                }
            }
        }
        
        self.database = DatabaseBackend(self.config)
        self.database.connect()
    
    def tearDown(self):
        """Clean up test database"""
        if hasattr(self, 'database') and self.database.connection:
            self.database.connection.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_persistence(self):
        """Test that FMFM configs are saved and loaded from database"""
        # Create first instance and add config
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)
        
        config = {
            'mode': 'sequential',
            'destinations': [
                {'number': '1001', 'ring_time': 20},
                {'number': '1002', 'ring_time': 15}
            ],
            'enabled': True,
            'no_answer_destination': '2000'
        }
        
        success = fmfm1.set_config('1000', config)
        self.assertTrue(success, "Config should be saved successfully")
        
        # Create second instance to verify persistence
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)
        
        loaded_config = fmfm2.get_config('1000')
        self.assertIsNotNone(loaded_config, "Config should be loaded from database")
        self.assertEqual(loaded_config['mode'], 'sequential')
        self.assertEqual(len(loaded_config['destinations']), 2)
        self.assertEqual(loaded_config['destinations'][0]['number'], '1001')
        self.assertEqual(loaded_config['no_answer_destination'], '2000')
    
    def test_add_destination_persistence(self):
        """Test that adding destinations persists to database"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)
        
        fmfm1.add_destination('1000', '1001', 20)
        fmfm1.add_destination('1000', '1002', 15)
        
        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)
        
        config = fmfm2.get_config('1000')
        self.assertIsNotNone(config)
        self.assertEqual(len(config['destinations']), 2)
    
    def test_remove_destination_persistence(self):
        """Test that removing destinations persists to database"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)
        
        config = {
            'mode': 'sequential',
            'destinations': [
                {'number': '1001', 'ring_time': 20},
                {'number': '1002', 'ring_time': 15}
            ],
            'enabled': True
        }
        fmfm1.set_config('1000', config)
        
        # Remove a destination
        fmfm1.remove_destination('1000', '1001')
        
        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)
        
        loaded_config = fmfm2.get_config('1000')
        self.assertIsNotNone(loaded_config)
        self.assertEqual(len(loaded_config['destinations']), 1)
        self.assertEqual(loaded_config['destinations'][0]['number'], '1002')
    
    def test_enable_disable_persistence(self):
        """Test that enable/disable persists to database"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)
        
        config = {
            'mode': 'sequential',
            'destinations': [{'number': '1001', 'ring_time': 20}],
            'enabled': True
        }
        fmfm1.set_config('1000', config)
        
        # Disable
        fmfm1.disable_fmfm('1000')
        
        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)
        
        loaded_config = fmfm2.get_config('1000')
        self.assertIsNotNone(loaded_config)
        self.assertFalse(loaded_config['enabled'])
        
        # Enable again
        fmfm2.enable_fmfm('1000')
        
        # Create third instance
        fmfm3 = FindMeFollowMe(config=self.config, database=self.database)
        
        loaded_config = fmfm3.get_config('1000')
        self.assertTrue(loaded_config['enabled'])
    
    def test_delete_config_persistence(self):
        """Test that delete removes config from database"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)
        
        config = {
            'mode': 'sequential',
            'destinations': [{'number': '1001', 'ring_time': 20}],
            'enabled': True
        }
        fmfm1.set_config('1000', config)
        
        # Verify it exists
        self.assertIsNotNone(fmfm1.get_config('1000'))
        
        # Delete
        fmfm1.delete_config('1000')
        
        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)
        
        loaded_config = fmfm2.get_config('1000')
        self.assertIsNone(loaded_config, "Config should be deleted from database")
    
    def test_simultaneous_mode_persistence(self):
        """Test that simultaneous mode configs persist correctly"""
        fmfm1 = FindMeFollowMe(config=self.config, database=self.database)
        
        config = {
            'mode': 'simultaneous',
            'destinations': [
                {'number': '1001', 'ring_time': 30},
                {'number': '1002', 'ring_time': 30},
                {'number': '1003', 'ring_time': 30}
            ],
            'enabled': True
        }
        fmfm1.set_config('1000', config)
        
        # Create new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)
        
        loaded_config = fmfm2.get_config('1000')
        self.assertIsNotNone(loaded_config)
        self.assertEqual(loaded_config['mode'], 'simultaneous')
        self.assertEqual(len(loaded_config['destinations']), 3)


if __name__ == '__main__':
    unittest.main()
