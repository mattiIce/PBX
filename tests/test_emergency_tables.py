#!/usr/bin/env python3
"""
Tests for emergency tables in database
"""

import os
import tempfile


from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend
from pathlib import Path


def test_emergency_contacts_table_creation() -> None:
    """Test that emergency_contacts table is created"""

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables
        assert db.create_tables() is True

        # Verify emergency_contacts table exists
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='emergency_contacts'"
        )
        result = cursor.fetchone()
        assert result is not None, "emergency_contacts table not found"

        # Verify table structure
        cursor.execute("PRAGMA table_info(emergency_contacts)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        required_columns = [
            "id",
            "name",
            "extension",
            "phone",
            "email",
            "priority",
            "notification_methods",
            "active",
        ]
        for col in required_columns:
            assert col in columns, f"Column {col} not found in emergency_contacts table"

        cursor.close()
        db.disconnect()

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_emergency_notifications_table_creation() -> None:
    """Test that emergency_notifications table is created"""

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables
        assert db.create_tables() is True

        # Verify emergency_notifications table exists
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='emergency_notifications'"
        )
        result = cursor.fetchone()
        assert result is not None, "emergency_notifications table not found"

        # Verify table structure
        cursor.execute("PRAGMA table_info(emergency_notifications)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        required_columns = [
            "id",
            "timestamp",
            "trigger_type",
            "details",
            "contacts_notified",
            "methods_used",
        ]
        for col in required_columns:
            assert col in columns, f"Column {col} not found in emergency_notifications table"

        cursor.close()
        db.disconnect()

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_emergency_indexes_creation() -> None:
    """Test that emergency table indexes are created"""

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables
        assert db.create_tables() is True

        # Verify indexes exist
        cursor = db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        expected_indexes = [
            "idx_emergency_contacts_active",
            "idx_emergency_contacts_priority",
            "idx_emergency_notifications_timestamp",
            "idx_emergency_notifications_trigger_type",
        ]

        for idx in expected_indexes:
            assert idx in indexes, f"Index {idx} not found"

        cursor.close()
        db.disconnect()

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)
