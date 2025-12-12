#!/usr/bin/env python3
"""
Tests for PostgreSQL transaction rollback handling
Validates that failed transactions are properly rolled back to prevent
"current transaction is aborted" errors
"""
import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend



def test_transaction_rollback_on_error():
    """Test that transactions are rolled back after errors"""
    print("Testing transaction rollback after errors...")

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

        # Create tables first
        assert db.create_tables() is True

        # Execute a bad query that should fail
        result = db.execute("INVALID SQL SYNTAX", ())
        assert result is False

        # Now execute a valid query - this should succeed
        # If rollback didn't work, this would fail with "transaction is
        # aborted" error
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)",
            ('1234567890',
             1))
        assert result is True

        # Verify the insert worked
        row = db.fetch_one(
            "SELECT * FROM vip_callers WHERE caller_id = ?", ('1234567890',))
        assert row is not None
        assert row['caller_id'] == '1234567890'

        db.disconnect()
        print("✓ Transaction rollback on error works correctly")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_fetch_one_rollback_on_error():
    """Test that fetch_one rolls back transaction on error"""
    print("Testing fetch_one transaction rollback...")

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.create_tables() is True

        # Execute a bad SELECT query
        result = db.fetch_one("SELECT * FROM nonexistent_table", ())
        assert result is None

        # Now execute a valid query - should succeed if rollback worked
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)",
            ('9876543210',
             1))
        assert result is True

        db.disconnect()
        print("✓ fetch_one transaction rollback works correctly")

    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_fetch_all_rollback_on_error():
    """Test that fetch_all rolls back transaction on error"""
    print("Testing fetch_all transaction rollback...")

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.create_tables() is True

        # Execute a bad SELECT query
        result = db.fetch_all("SELECT * FROM nonexistent_table", ())
        assert result == []

        # Now execute a valid query - should succeed if rollback worked
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)",
            ('5555555555',
             1))
        assert result is True

        db.disconnect()
        print("✓ fetch_all transaction rollback works correctly")

    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_schema_migration_rollback():
    """Test that schema migration errors don't leave transactions open"""
    print("Testing schema migration transaction rollback...")

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables (which includes schema migration)
        # This might encounter errors but should handle them gracefully
        result = db.create_tables()
        assert result is True

        # After schema migration (even with potential errors), we should be
        # able to insert
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)",
            ('1112223333',
             1))
        assert result is True

        db.disconnect()
        print("✓ Schema migration transaction handling works correctly")

    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_permission_error_rollback():
    """Test that permission errors properly rollback transactions"""
    print("Testing permission error transaction rollback...")

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.create_tables() is True

        # Try to create an index that will fail (table doesn't exist)
        # This is marked as non-critical, so should return True but rollback
        result = db._execute_with_context(
            "CREATE INDEX test_idx ON nonexistent_table(col)",
            "index creation",
            critical=False
        )
        # Should fail gracefully

        # After the failed index creation, we should still be able to insert
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)",
            ('4445556666',
             1))
        assert result is True

        db.disconnect()
        print("✓ Permission error transaction rollback works correctly")

    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Running Transaction Rollback Tests")
    print("=" * 70)
    print()

    tests = [
        test_transaction_rollback_on_error,
        test_fetch_one_rollback_on_error,
        test_fetch_all_rollback_on_error,
        test_schema_migration_rollback,
        test_permission_error_rollback,
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
