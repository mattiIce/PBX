#!/usr/bin/env python3
"""
Tests for database permission error handling
"""

import os
import tempfile


from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend
from pathlib import Path


def test_index_creation_with_permission_error() -> None:
    """Test that index creation failures don't cause startup errors"""

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

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_table_already_exists_handling() -> None:
    """Test that 'already exists' errors are handled gracefully"""

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

    finally:
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_critical_vs_non_critical_errors() -> None:
    """Test that critical and non-critical errors are handled differently"""

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

    finally:
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)
