#!/usr/bin/env python3
"""
Tests for emergency tables in database
"""
import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend



def test_emergency_contacts_table_creation():
    """Test that emergency_contacts table is created"""
    print("Testing emergency_contacts table creation...")

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables
        assert db.create_tables() is True

        # Verify emergency_contacts table exists
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='emergency_contacts'")
        result = cursor.fetchone()
        assert result is not None, "emergency_contacts table not found"

        # Verify table structure
        cursor.execute("PRAGMA table_info(emergency_contacts)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        required_columns = [
            'id',
            'name',
            'extension',
            'phone',
            'email',
            'priority',
            'notification_methods',
            'active']
        for col in required_columns:
            assert col in columns, f"Column {col} not found in emergency_contacts table"

        cursor.close()
        db.disconnect()
        print("✓ emergency_contacts table created successfully")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_emergency_notifications_table_creation():
    """Test that emergency_notifications table is created"""
    print("Testing emergency_notifications table creation...")

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables
        assert db.create_tables() is True

        # Verify emergency_notifications table exists
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='emergency_notifications'")
        result = cursor.fetchone()
        assert result is not None, "emergency_notifications table not found"

        # Verify table structure
        cursor.execute("PRAGMA table_info(emergency_notifications)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        required_columns = [
            'id',
            'timestamp',
            'trigger_type',
            'details',
            'contacts_notified',
            'methods_used']
        for col in required_columns:
            assert col in columns, f"Column {col} not found in emergency_notifications table"

        cursor.close()
        db.disconnect()
        print("✓ emergency_notifications table created successfully")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_emergency_indexes_creation():
    """Test that emergency table indexes are created"""
    print("Testing emergency table indexes creation...")

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables
        assert db.create_tables() is True

        # Verify indexes exist
        cursor = db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        expected_indexes = [
            'idx_emergency_contacts_active',
            'idx_emergency_contacts_priority',
            'idx_emergency_notifications_timestamp',
            'idx_emergency_notifications_trigger_type'
        ]

        for idx in expected_indexes:
            assert idx in indexes, f"Index {idx} not found"

        cursor.close()
        db.disconnect()
        print("✓ Emergency table indexes created successfully")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Running Emergency Tables Tests")
    print("=" * 70)
    print()

    tests = [
        test_emergency_contacts_table_creation,
        test_emergency_notifications_table_creation,
        test_emergency_indexes_creation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
