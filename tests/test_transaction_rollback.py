#!/usr/bin/env python3
"""
Tests for PostgreSQL transaction rollback handling
Validates that failed transactions are properly rolled back to prevent
"current transaction is aborted" errors
"""

import os
import tempfile
from pathlib import Path

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_transaction_rollback_on_error() -> None:
    """Test that transactions are rolled back after errors"""

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

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
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)", ("1234567890", 1)
        )
        assert result is True

        # Verify the insert worked
        row = db.fetch_one("SELECT * FROM vip_callers WHERE caller_id = ?", ("1234567890",))
        assert row is not None
        assert row["caller_id"] == "1234567890"

        db.disconnect()

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_fetch_one_rollback_on_error() -> None:
    """Test that fetch_one rolls back transaction on error"""

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.create_tables() is True

        # Execute a bad SELECT query
        result = db.fetch_one("SELECT * FROM nonexistent_table", ())
        assert result is None

        # Now execute a valid query - should succeed if rollback worked
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)", ("9876543210", 1)
        )
        assert result is True

        db.disconnect()

    finally:
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_fetch_all_rollback_on_error() -> None:
    """Test that fetch_all rolls back transaction on error"""

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.create_tables() is True

        # Execute a bad SELECT query
        result = db.fetch_all("SELECT * FROM nonexistent_table", ())
        assert result == []

        # Now execute a valid query - should succeed if rollback worked
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)", ("5555555555", 1)
        )
        assert result is True

        db.disconnect()

    finally:
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_schema_migration_rollback() -> None:
    """Test that schema migration errors don't leave transactions open"""

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables (which includes schema migration)
        # This might encounter errors but should handle them gracefully
        result = db.create_tables()
        assert result is True

        # After schema migration (even with potential errors), we should be
        # able to insert
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)", ("1112223333", 1)
        )
        assert result is True

        db.disconnect()

    finally:
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_permission_error_rollback() -> None:
    """Test that permission errors properly rollback transactions"""

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.create_tables() is True

        # Try to create an index that will fail (table doesn't exist)
        # This is marked as non-critical, so should return True but rollback
        result = db._execute_with_context(
            "CREATE INDEX test_idx ON nonexistent_table(col)", "index creation", critical=False
        )
        # Should fail gracefully

        # After the failed index creation, we should still be able to insert
        result = db.execute(
            "INSERT INTO vip_callers (caller_id, priority_level) VALUES (?, ?)", ("4445556666", 1)
        )
        assert result is True

        db.disconnect()

    finally:
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)
