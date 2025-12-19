"""
Test Find Me/Follow Me database save failure handling
"""

import os
import sys
import tempfile
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.find_me_follow_me import FindMeFollowMe
from pbx.utils.database import DatabaseBackend


class TestFMFMSaveFailure(unittest.TestCase):
    """Test FMFM configuration save failure handling"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.config = {
            "database.type": "sqlite",
            "database.path": self.temp_db.name,
            "features": {"find_me_follow_me": {"enabled": True}},
        }

        self.database = DatabaseBackend(self.config)
        self.database.connect()

    def tearDown(self):
        """Clean up test database"""
        if hasattr(self, "database") and self.database.connection:
            self.database.connection.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_set_config_with_database_failure(self):
        """Test that set_config returns False if database save fails"""
        fmfm = FindMeFollowMe(config=self.config, database=self.database)

        # Close the database connection to simulate a failure
        self.database.connection.close()

        config = {
            "mode": "sequential",
            "destinations": [
                {"number": "1001", "ring_time": 20},
            ],
            "enabled": True,
        }

        # This should fail because database connection is closed
        success = fmfm.set_config("1000", config)
        self.assertFalse(success, "set_config should return False when database save fails")

        # Config should not be in memory if database save failed
        loaded_config = fmfm.get_config("1000")
        self.assertIsNone(
            loaded_config, "Config should not be saved to memory if database save fails"
        )

    def test_set_config_without_database(self):
        """Test that set_config works without a database"""
        config = {"features": {"find_me_follow_me": {"enabled": True}}}

        # Create FMFM without database
        fmfm = FindMeFollowMe(config=config, database=None)

        fmfm_config = {
            "mode": "sequential",
            "destinations": [
                {"number": "1001", "ring_time": 20},
            ],
            "enabled": True,
        }

        # This should succeed even without a database
        success = fmfm.set_config("1000", fmfm_config)
        self.assertTrue(success, "set_config should work without a database")

        # Config should be in memory
        loaded_config = fmfm.get_config("1000")
        self.assertIsNotNone(loaded_config, "Config should be saved to memory")
        self.assertEqual(loaded_config["mode"], "sequential")

    def test_set_config_with_working_database(self):
        """Test that set_config succeeds with a working database"""
        fmfm = FindMeFollowMe(config=self.config, database=self.database)

        config = {
            "mode": "simultaneous",
            "destinations": [
                {"number": "1001", "ring_time": 20},
                {"number": "1002", "ring_time": 20},
            ],
            "enabled": True,
        }

        # This should succeed
        success = fmfm.set_config("1000", config)
        self.assertTrue(success, "set_config should succeed with working database")

        # Config should be in memory and database
        loaded_config = fmfm.get_config("1000")
        self.assertIsNotNone(loaded_config, "Config should be saved")
        self.assertEqual(loaded_config["mode"], "simultaneous")

        # Verify it persists by creating a new instance
        fmfm2 = FindMeFollowMe(config=self.config, database=self.database)
        loaded_config2 = fmfm2.get_config("1000")
        self.assertIsNotNone(loaded_config2, "Config should persist to database")
        self.assertEqual(loaded_config2["mode"], "simultaneous")

    def test_set_config_with_fmfm_disabled_globally(self):
        """Test that set_config returns False and logs error when FMFM is disabled globally"""
        config = {"features": {"find_me_follow_me": {"enabled": False}}}  # Disabled globally

        # Create FMFM with feature disabled
        fmfm = FindMeFollowMe(config=config, database=None)

        fmfm_config = {
            "mode": "simultaneous",
            "destinations": [
                {"number": "1537", "ring_time": 10},
                {"number": "1519", "ring_time": 10},
                {"number": "1501", "ring_time": 10},
            ],
            "enabled": True,
            "no_answer_destination": "1537",
        }

        # This should fail because FMFM is disabled globally
        success = fmfm.set_config("8001", fmfm_config)
        self.assertFalse(success, "set_config should return False when FMFM is disabled globally")

        # Config should not be saved
        loaded_config = fmfm.get_config("8001")
        self.assertIsNone(
            loaded_config, "Config should not be saved when FMFM is disabled globally"
        )


if __name__ == "__main__":
    unittest.main()
