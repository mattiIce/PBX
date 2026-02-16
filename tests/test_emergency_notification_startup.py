#!/usr/bin/env python3
"""
Test to verify emergency notification system initializes without database errors
"""

import shutil
import tempfile
from pathlib import Path

from pbx.features.emergency_notification import EmergencyNotificationSystem
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_emergency_notification_system_initialization() -> None:
    """Test that emergency notification system initializes without database errors"""

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"

    try:
        # Create a test config
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": db_path}
        test_config.config["features"] = {
            "emergency_notification": {
                "enabled": True,
                "notify_on_911": True,
                "methods": ["call", "page", "email"],
                "contacts": [],
            }
        }

        # Initialize database
        db = DatabaseBackend(test_config)
        assert db.connect() is True, "Failed to connect to database"
        assert db.create_tables() is True, "Failed to create tables"

        # Mock PBX core (minimal for this test)
        class MockPBXCore:
            pass

        pbx_core = MockPBXCore()

        # Initialize emergency notification system
        # This should not raise any database errors
        emergency_system = EmergencyNotificationSystem(pbx_core, test_config.config, db)

        # Verify initialization
        assert emergency_system is not None, "Emergency system not initialized"
        assert emergency_system.enabled is True, "Emergency system should be enabled"
        assert len(emergency_system.emergency_contacts) == 0, "Should have no contacts initially"

        # Verify database connection works
        contacts = emergency_system.get_emergency_contacts()
        assert contacts == [], "Should return empty list initially"

        # Clean up
        db.disconnect()

    finally:
        # Clean up
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)


def test_emergency_notification_database_operations() -> None:
    """Test that emergency notification system can perform database operations"""

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"

    try:
        # Create a test config
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": db_path}
        test_config.config["features"] = {
            "emergency_notification": {
                "enabled": True,
                "notify_on_911": True,
                "methods": ["call", "page", "email"],
                "contacts": [],
            }
        }

        # Initialize database
        db = DatabaseBackend(test_config)
        assert db.connect() is True, "Failed to connect to database"
        assert db.create_tables() is True, "Failed to create tables"

        # Mock PBX core
        class MockPBXCore:
            pass

        pbx_core = MockPBXCore()

        # Initialize emergency notification system
        emergency_system = EmergencyNotificationSystem(pbx_core, test_config.config, db)

        # Add an emergency contact
        contact = emergency_system.add_emergency_contact(
            name="Test Contact",
            extension="1001",
            phone="555-1234",
            email="test@example.com",
            priority=1,
            notification_methods=["call", "email"],
        )

        assert contact is not None, "Failed to add emergency contact"
        assert contact.name == "Test Contact", "Contact name mismatch"

        # Verify contact was added
        contacts = emergency_system.get_emergency_contacts()
        assert len(contacts) == 1, f"Expected 1 contact, got {len(contacts)}"
        assert contacts[0]["name"] == "Test Contact", "Contact name mismatch"

        # Clean up
        db.disconnect()

    finally:
        # Clean up
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
