#!/usr/bin/env python3
"""
Tests for voicemail database integration
"""

import shutil
import tempfile
from pathlib import Path

from pbx.features.voicemail import VoicemailSystem
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_database_configuration() -> None:
    """Test database configuration loading"""

    config = Config("config.yml")

    # Check database settings (values come from .env on server)
    assert config.get("database.type") == "postgresql"
    assert config.get("database.host") is not None, "Database host should be set"
    # Port should be an integer after env variable resolution
    db_port = config.get("database.port")
    assert db_port == 5432 or db_port == "5432", (
        f"Expected port 5432, got {db_port} (type: {type(db_port)})"
    )
    assert config.get("database.name") is not None, "Database name should be set"
    assert config.get("database.user") is not None, "Database user should be set"


def test_database_backend_initialization() -> None:
    """Test database backend initialization with SQLite fallback"""

    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_db:
        pass

    try:
        # Create a test config for SQLite
        test_config = Config("config.yml")
        # Override database settings for testing
        test_config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.enabled is True

        # Create tables
        assert db.create_tables() is True

        # Test table existence with a simple query
        result = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [row["name"] for row in result]
        assert "voicemail_messages" in table_names
        assert "call_records" in table_names
        assert "vip_callers" in table_names

        db.disconnect()

    finally:
        # Cleanup
        if Path(temp_db.name).exists():
            Path(temp_db.name).unlink(missing_ok=True)


def test_voicemail_database_integration() -> None:
    """Test voicemail saving to database"""

    # Create temporary directories for test
    temp_dir = tempfile.mkdtemp()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_db:
        pass

    try:
        # Create test config with SQLite
        config = Config("config.yml")
        config.config["database"] = {"type": "sqlite", "path": temp_db.name}

        # Initialize database
        db = DatabaseBackend(config)
        assert db.connect() is True
        assert db.create_tables() is True

        # Create voicemail system with database
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config, database=db)

        # Save a test message
        test_audio = b"RIFF" + b"\x00" * 100
        message_id = vm_system.save_message(
            extension_number="1001", caller_id="1002", audio_data=test_audio, duration=30
        )

        assert message_id is not None

        # Verify message was saved to database
        query = "SELECT * FROM voicemail_messages WHERE message_id = ?"
        result = db.fetch_one(query, (message_id,))

        assert result is not None
        assert result["extension_number"] == "1001"
        assert result["caller_id"] == "1002"
        assert result["duration"] == 30
        assert result["listened"] is False or result["listened"] == 0

        # Mark message as listened
        mailbox = vm_system.get_mailbox("1001")
        mailbox.mark_listened(message_id)

        # Verify listened status updated in database
        result = db.fetch_one(query, (message_id,))
        assert result["listened"] is True or result["listened"] == 1

        # Delete message
        mailbox.delete_message(message_id)

        # Verify message deleted from database
        result = db.fetch_one(query, (message_id,))
        assert result is None

        db.disconnect()

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        if Path(temp_db.name).exists():
            Path(temp_db.name).unlink(missing_ok=True)


def test_voicemail_without_database() -> None:
    """Test voicemail system works without database"""

    temp_dir = tempfile.mkdtemp()

    try:
        config = Config("config.yml")

        # Create voicemail system without database
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config, database=None)

        # Save a test message
        test_audio = b"RIFF" + b"\x00" * 100
        message_id = vm_system.save_message(
            extension_number="1001", caller_id="1002", audio_data=test_audio, duration=30
        )

        assert message_id is not None
        assert len(vm_system.get_mailbox("1001").messages) == 1

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
