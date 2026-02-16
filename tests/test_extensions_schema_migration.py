#!/usr/bin/env python3
"""
Tests for extensions table schema migration
Tests that voicemail_pin_hash and voicemail_pin_salt columns are added during migration
"""

import os
import sqlite3
import tempfile
from pathlib import Path

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_extensions_columns_migration() -> None:
    """Test that missing voicemail PIN columns are added during migration"""

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        # First, create an old version of the extensions table without
        # voicemail_pin columns
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()

        # Create old schema without voicemail_pin_hash and voicemail_pin_salt
        cursor.execute("""
        CREATE TABLE extensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            password_hash VARCHAR(255) NOT NULL,
            allow_external BOOLEAN DEFAULT 1,
            ad_synced BOOLEAN DEFAULT 0,
            ad_username VARCHAR(100),
            password_changed_at TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            account_locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()

        # Verify columns don't exist yet
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(extensions)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "voicemail_pin_hash" not in columns, "voicemail_pin_hash should not exist initially"
        assert "voicemail_pin_salt" not in columns, "voicemail_pin_salt should not exist initially"
        assert "password_salt" not in columns, "password_salt should not exist initially"

        # Now connect with DatabaseBackend which should trigger migration
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables (this will run migrations)
        assert db.create_tables() is True

        db.disconnect()

        # Verify that the columns were added
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(extensions)")
        columns_after = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "voicemail_pin_hash" in columns_after, (
            "voicemail_pin_hash should exist after migration"
        )
        assert "voicemail_pin_salt" in columns_after, (
            "voicemail_pin_salt should exist after migration"
        )
        assert "password_salt" in columns_after, "password_salt should exist after migration"

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_extensions_columns_already_exist() -> None:
    """Test that migration handles existing columns gracefully"""

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables with all columns
        assert db.create_tables() is True

        # Verify columns exist
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(extensions)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "voicemail_pin_hash" in columns
        assert "voicemail_pin_salt" in columns
        assert "password_salt" in columns

        # Run create_tables again - should not fail (migration runs internally)
        result = db.create_tables()
        assert result is True

        db.disconnect()

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)


def test_insert_with_voicemail_pin() -> None:
    """Test that we can insert extensions with voicemail PIN after migration"""

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    try:
        # First, create old schema without voicemail_pin columns
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE extensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            password_hash VARCHAR(255) NOT NULL,
            allow_external BOOLEAN DEFAULT 1,
            ad_synced BOOLEAN DEFAULT 0,
            ad_username VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()

        # Connect with DatabaseBackend to trigger migration
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.create_tables() is True

        # Now try to insert an extension with voicemail PIN columns
        query = """
        INSERT INTO extensions (number, name, email, password_hash, allow_external,
                              voicemail_pin_hash, voicemail_pin_salt, ad_synced, ad_username)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            "1001",
            "Test User",
            "test@example.com",
            "hash123",
            1,
            "pin_hash",
            "pin_salt",
            0,
            None,
        )

        result = db.execute(query, params)
        assert result is True, "Should be able to insert with voicemail PIN columns"

        # Verify the data was inserted
        verify_query = "SELECT number, name, voicemail_pin_hash, voicemail_pin_salt FROM extensions WHERE number = ?"
        row = db.fetch_one(verify_query, ("1001",))
        assert row is not None, "Extension should be found"
        assert row["number"] == "1001"
        assert row["voicemail_pin_hash"] == "pin_hash"
        assert row["voicemail_pin_salt"] == "pin_salt"

        db.disconnect()

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            os.unlink(temp_db.name)
