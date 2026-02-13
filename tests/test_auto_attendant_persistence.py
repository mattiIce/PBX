"""
Tests for Auto Attendant Database Persistence
Ensures configuration and menu options persist across restarts
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from typing import Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.auto_attendant import AutoAttendant


class MockConfig:
    """Mock configuration for testing"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def get(self, key: str, default: Any = None) -> Any:
        if key == "database":
            return {"path": self.db_path}
        elif key == "auto_attendant":
            return {
                "enabled": True,
                "extension": "0",
                "timeout": 10,
                "max_retries": 3,
                "audio_path": "auto_attendant",
                "menu_options": [
                    {"digit": "1", "destination": "1001", "description": "Sales"},
                    {"digit": "2", "destination": "1002", "description": "Support"},
                ],
            }
        return default


class TestAutoAttendantPersistence(unittest.TestCase):
    """Test auto attendant database persistence"""

    def setUp(self) -> None:
        """Set up test environment"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.config = MockConfig(self.db_path)

    def tearDown(self) -> None:
        """Clean up test environment"""
        # Close and remove temporary database
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_initial_config_saved_to_db(self) -> None:
        """Test that initial configuration is saved to database"""
        # Create auto attendant
        AutoAttendant(config=self.config)

        # Verify configuration was saved to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT enabled, extension, timeout, max_retries FROM auto_attendant_config WHERE id = 1"
        )
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)  # enabled
        self.assertEqual(row[1], "0")  # extension
        self.assertEqual(row[2], 10)  # timeout
        self.assertEqual(row[3], 3)  # max_retries

    def test_initial_menu_options_saved_to_db(self) -> None:
        """Test that initial menu options are saved to database"""
        # Create auto attendant
        AutoAttendant(config=self.config)

        # Verify menu options were saved to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT digit, destination, description FROM auto_attendant_menu_options ORDER BY digit"
        )
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "1")
        self.assertEqual(rows[0][1], "1001")
        self.assertEqual(rows[0][2], "Sales")
        self.assertEqual(rows[1][0], "2")
        self.assertEqual(rows[1][1], "1002")
        self.assertEqual(rows[1][2], "Support")

    def test_config_persists_across_restarts(self) -> None:
        """Test that configuration persists across restarts"""
        # Create auto attendant and update config
        aa1 = AutoAttendant(config=self.config)
        aa1.update_config(enabled=False, extension="9", timeout=20, max_retries=5)

        # Create new instance (simulating restart)
        aa2 = AutoAttendant(config=self.config)

        # Verify configuration persisted
        self.assertEqual(aa2.enabled, False)
        self.assertEqual(aa2.extension, "9")
        self.assertEqual(aa2.timeout, 20)
        self.assertEqual(aa2.max_retries, 5)

    def test_menu_options_persist_across_restarts(self) -> None:
        """Test that menu options persist across restarts"""
        # Create auto attendant and add menu option
        aa1 = AutoAttendant(config=self.config)
        aa1.add_menu_option("3", "1003", "Billing")

        # Create new instance (simulating restart)
        aa2 = AutoAttendant(config=self.config)

        # Verify menu option persisted
        self.assertIn("3", aa2.menu_options)
        self.assertEqual(aa2.menu_options["3"]["destination"], "1003")
        self.assertEqual(aa2.menu_options["3"]["description"], "Billing")

    def test_menu_option_update_persists(self) -> None:
        """Test that menu option updates persist"""
        # Create auto attendant
        aa1 = AutoAttendant(config=self.config)

        # Update menu option
        aa1.add_menu_option("1", "1005", "New Sales")

        # Create new instance (simulating restart)
        aa2 = AutoAttendant(config=self.config)

        # Verify update persisted
        self.assertEqual(aa2.menu_options["1"]["destination"], "1005")
        self.assertEqual(aa2.menu_options["1"]["description"], "New Sales")

    def test_menu_option_deletion_persists(self) -> None:
        """Test that menu option deletion persists"""
        # Create auto attendant
        aa1 = AutoAttendant(config=self.config)

        # Delete menu option
        aa1.remove_menu_option("1")

        # Create new instance (simulating restart)
        aa2 = AutoAttendant(config=self.config)

        # Verify deletion persisted
        self.assertNotIn("1", aa2.menu_options)
        self.assertIn("2", aa2.menu_options)  # Other option still exists

    def test_database_tables_created(self) -> None:
        """Test that database tables are created"""
        # Create auto attendant
        AutoAttendant(config=self.config)

        # Verify tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check config table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='auto_attendant_config'"
        )
        self.assertIsNotNone(cursor.fetchone())

        # Check menu options table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='auto_attendant_menu_options'"
        )
        self.assertIsNotNone(cursor.fetchone())

        conn.close()

    def test_multiple_updates_persist(self) -> None:
        """Test that multiple sequential updates persist"""
        # Create auto attendant
        aa1 = AutoAttendant(config=self.config)

        # Make multiple changes
        aa1.update_config(timeout=15)
        aa1.add_menu_option("3", "1003", "Billing")
        aa1.add_menu_option("4", "1004", "HR")
        aa1.remove_menu_option("2")
        aa1.update_config(max_retries=7)

        # Create new instance (simulating restart)
        aa2 = AutoAttendant(config=self.config)

        # Verify all changes persisted
        self.assertEqual(aa2.timeout, 15)
        self.assertEqual(aa2.max_retries, 7)
        self.assertIn("1", aa2.menu_options)
        self.assertNotIn("2", aa2.menu_options)
        self.assertIn("3", aa2.menu_options)
        self.assertIn("4", aa2.menu_options)


if __name__ == "__main__":
    unittest.main()
