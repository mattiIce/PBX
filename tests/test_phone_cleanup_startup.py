"""
Tests for phone registration cleanup at startup
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB


class TestPhoneCleanupStartup(unittest.TestCase):
    """Test cleanup of incomplete phone registrations"""

    def setUp(self):
        """Set up test fixtures"""
        self.db = Mock(spec=DatabaseBackend)
        self.db.db_type = 'sqlite'
        self.db.enabled = True
        self.phones_db = RegisteredPhonesDB(self.db)

    def test_cleanup_no_incomplete_registrations(self):
        """Test cleanup when there are no incomplete registrations"""
        # Mock fetch_one to return 0 count
        self.db.fetch_one.return_value = {'count': 0}

        success, count = self.phones_db.cleanup_incomplete_registrations()

        self.assertTrue(success)
        self.assertEqual(count, 0)
        # Execute should not be called since count is 0
        self.db.execute.assert_not_called()

    def test_cleanup_with_incomplete_registrations(self):
        """Test cleanup when there are incomplete registrations"""
        # Mock fetch_one to return 3 incomplete registrations
        self.db.fetch_one.return_value = {'count': 3}
        self.db.execute.return_value = True

        success, count = self.phones_db.cleanup_incomplete_registrations()

        self.assertTrue(success)
        self.assertEqual(count, 3)
        # Verify the DELETE query was executed
        self.db.execute.assert_called_once()
        call_args = self.db.execute.call_args[0][0]
        self.assertIn("DELETE FROM registered_phones", call_args)
        self.assertIn("mac_address IS NULL", call_args)
        self.assertIn("ip_address IS NULL", call_args)
        self.assertIn("extension_number IS NULL", call_args)

    def test_cleanup_database_error(self):
        """Test cleanup handles database errors gracefully"""
        # Mock fetch_one to raise an exception
        self.db.fetch_one.side_effect = Exception("Database error")

        success, count = self.phones_db.cleanup_incomplete_registrations()

        self.assertFalse(success)
        self.assertEqual(count, 0)

    def test_cleanup_delete_failure(self):
        """Test cleanup when delete operation fails"""
        # Mock fetch_one to return 2 incomplete registrations
        self.db.fetch_one.return_value = {'count': 2}
        # Mock execute to return False (failure)
        self.db.execute.return_value = False

        success, count = self.phones_db.cleanup_incomplete_registrations()

        self.assertFalse(success)
        self.assertEqual(count, 2)
        # Verify DELETE was attempted
        self.db.execute.assert_called_once()

    def test_cleanup_query_structure(self):
        """Test that cleanup query checks all required fields"""
        self.db.fetch_one.return_value = {'count': 5}
        self.db.execute.return_value = True

        self.phones_db.cleanup_incomplete_registrations()

        # Get the DELETE query
        delete_query = self.db.execute.call_args[0][0]

        # Verify it checks for NULL or empty string for all three fields
        self.assertIn("mac_address IS NULL OR mac_address = ''", delete_query)
        self.assertIn("ip_address IS NULL OR ip_address = ''", delete_query)
        self.assertIn(
            "extension_number IS NULL OR extension_number = ''",
            delete_query)

        # Verify it uses OR between conditions (any missing field triggers
        # deletion)
        self.assertIn("OR", delete_query)


class TestPhoneCleanupIntegration(unittest.TestCase):
    """Integration tests for phone cleanup (requires actual database)"""

    def test_cleanup_removes_only_incomplete_registrations(self):
        """Test that cleanup only removes incomplete registrations"""
        # This is a documentation test showing expected behavior
        # In a real database scenario:
        #
        # BEFORE cleanup:
        # - Phone 1: MAC='00:11:22:33:44:55', IP='192.168.1.10', Ext='1001' -> KEPT
        # - Phone 2: MAC=NULL, IP='192.168.1.11', Ext='1002' -> REMOVED (no MAC)
        # - Phone 3: MAC='00:11:22:33:44:56', IP=NULL, Ext='1003' -> REMOVED (no IP)
        # - Phone 4: MAC='00:11:22:33:44:57', IP='192.168.1.12', Ext=NULL -> REMOVED (no Ext)
        # - Phone 5: MAC='00:11:22:33:44:58', IP='192.168.1.13', Ext='1005' -> KEPT
        #
        # AFTER cleanup:
        # - Phone 1: MAC='00:11:22:33:44:55', IP='192.168.1.10', Ext='1001' -> KEPT
        # - Phone 5: MAC='00:11:22:33:44:58', IP='192.168.1.13', Ext='1005' -> KEPT
        #
        # Result: 3 incomplete registrations removed, 2 complete registrations
        # retained
        pass


if __name__ == '__main__':
    unittest.main()
