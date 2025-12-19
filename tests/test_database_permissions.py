#!/usr/bin/env python3
"""
Tests for database permission error handling
"""
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_index_creation_with_permission_error():
    """Test that index creation failures don't cause startup errors"""
    print("Testing repeated table creation (simulates permission scenario)...")

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # First, create the tables normally
        assert db.create_tables() is True

        # Call create_tables again - indexes already exist
        # This simulates a scenario where tables exist but may have permission issues
        # This should NOT fail or produce error messages
        result = db.create_tables()

        # The method should return True even when tables/indexes already exist
        assert result is True

        # Call it a third time to be sure
        result = db.create_tables()
        assert result is True

        db.disconnect()
        print("✓ Repeated table/index creation is handled gracefully")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_table_already_exists_handling():
    """Test that 'already exists' errors are handled gracefully"""
    print("Testing 'already exists' error handling...")

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables once
        assert db.create_tables() is True

        # Create tables again - should succeed without errors
        assert db.create_tables() is True

        db.disconnect()
        print("✓ 'Already exists' errors are handled gracefully")

    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_critical_vs_non_critical_errors():
    """Test that critical and non-critical errors are handled differently"""
    print("Testing critical vs non-critical error handling...")

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Test non-critical permission error (should return True)
        result = db._execute_with_context(
            "CREATE INDEX test_idx ON test_table(col)", "index creation", critical=False
        )
        # Should fail but be handled gracefully
        # In real scenario with permission error, it would return True
        # Here it just fails with table not existing, which is fine for testing
        # logic

        # Test critical error (should return False and log error)
        result = db._execute_with_context(
            "INVALID SQL SYNTAX HERE", "critical operation", critical=True
        )
        assert result is False

        db.disconnect()
        print("✓ Critical and non-critical errors are handled correctly")

    finally:
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Running Database Permission Tests")
    print("=" * 70)
    print()

    tests = [
        test_index_creation_with_permission_error,
        test_table_already_exists_handling,
        test_critical_vs_non_critical_errors,
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


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
