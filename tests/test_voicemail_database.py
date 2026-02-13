#!/usr/bin/env python3
"""
Tests for voicemail database integration
"""
import os
import shutil
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.voicemail import VoicemailSystem
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_database_configuration() -> None:
    """Test database configuration loading"""
    print("Testing database configuration...")

    config = Config("config.yml")

    # Check database settings (values come from .env on server)
    assert config.get("database.type") == "postgresql"
    assert config.get("database.host") is not None, "Database host should be set"
    # Port should be an integer after env variable resolution
    db_port = config.get("database.port")
    assert (
        db_port == 5432 or db_port == "5432"
    ), f"Expected port 5432, got {db_port} (type: {type(db_port)})"
    assert config.get("database.name") is not None, "Database name should be set"
    assert config.get("database.user") is not None, "Database user should be set"

    print("✓ Database configuration loads correctly")


def test_database_backend_initialization() -> None:
    """Test database backend initialization with SQLite fallback"""
    print("Testing database backend initialization...")

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

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
        print("✓ Database backend initializes correctly")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_voicemail_database_integration() -> None:
    """Test voicemail saving to database"""
    print("Testing voicemail database integration...")

    # Create temporary directories for test
    temp_dir = tempfile.mkdtemp()
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

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
        print("✓ Voicemail database integration works correctly")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_voicemail_without_database() -> None:
    """Test voicemail system works without database"""
    print("Testing voicemail system without database...")

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

        print("✓ Voicemail system works without database")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def run_all_tests() -> bool:
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Voicemail Database Tests")
    print("=" * 60)
    print()

    tests = [
        test_database_configuration,
        test_database_backend_initialization,
        test_voicemail_database_integration,
        test_voicemail_without_database,
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
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
