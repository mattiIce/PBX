#!/usr/bin/env python3
"""
Test to verify emergency contacts persist across restarts with PostgreSQL
This test requires PostgreSQL to be available and configured
"""

from pbx.features.emergency_notification import EmergencyNotificationSystem
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_emergency_contact_persistence_postgresql() -> bool:
    """Test that emergency contacts persist with PostgreSQL database"""

    try:
        # Create a test config for PostgreSQL
        test_config = Config("config.yml")

        # Check if PostgreSQL is configured in the config
        if test_config.config.get("database", {}).get("type") != "postgresql":
            return True

        test_config.config["features"] = {
            "emergency_notification": {
                "enabled": True,
                "notify_on_911": True,
                "methods": ["call", "page", "email"],
                "contacts": [],  # Empty - contacts will be added via UI
            }
        }

        # ========================================
        # Phase 1: Initial setup and add contacts
        # ========================================

        # Initialize database
        db = DatabaseBackend(test_config)
        if not db.connect():
            return True

        # Verify it's actually PostgreSQL
        if db.db_type != "postgresql":
            db.disconnect()
            return True

        # Create tables if they don't exist
        db.create_tables()

        # Mock PBX core
        class MockPBXCore:
            pass

        pbx_core = MockPBXCore()

        # Initialize emergency notification system
        emergency_system = EmergencyNotificationSystem(pbx_core, test_config.config, db)

        # Get initial count
        initial_contacts = emergency_system.get_emergency_contacts()
        initial_count = len(initial_contacts)

        # Add test emergency contacts (simulating admin UI)
        test_contact_name = "PostgreSQL Test Officer"

        # Check if test contact already exists and remove it
        existing_test = [c for c in initial_contacts if c["name"] == test_contact_name]
        for contact in existing_test:
            emergency_system.remove_emergency_contact(contact["id"])

        contact1 = emergency_system.add_emergency_contact(
            name=test_contact_name,
            extension="9001",
            phone="555-9001",
            email="postgresql-test@example.com",
            priority=1,
            notification_methods=["call", "page", "email"],
        )

        assert contact1 is not None, "Failed to add test contact"

        # Verify contact was added
        contacts = emergency_system.get_emergency_contacts()
        assert len(contacts) == initial_count + 1, (
            f"Expected {initial_count + 1} contacts, got {len(contacts)}"
        )

        # Find the test contact
        test_contact = [c for c in contacts if c["name"] == test_contact_name]
        assert len(test_contact) == 1, f"Expected 1 test contact, found {len(test_contact)}"

        # Clean up - disconnect database
        db.disconnect()

        # ========================================
        # Phase 2: Restart system and verify persistence
        # ========================================

        # Initialize database again
        db2 = DatabaseBackend(test_config)
        assert db2.connect() is True, "Failed to reconnect to database"

        pbx_core2 = MockPBXCore()

        # Initialize emergency notification system again (simulating restart)
        emergency_system2 = EmergencyNotificationSystem(pbx_core2, test_config.config, db2)

        # Verify test contact was loaded from database
        contacts = emergency_system2.get_emergency_contacts()
        test_contact = [c for c in contacts if c["name"] == test_contact_name]
        assert len(test_contact) == 1, "Test contact not found after restart"

        # Verify contact details
        contact = test_contact[0]
        assert contact["extension"] == "9001", "Extension mismatch"
        assert contact["phone"] == "555-9001", "Phone mismatch"
        assert contact["email"] == "postgresql-test@example.com", "Email mismatch"
        assert contact["priority"] == 1, "Priority mismatch"
        assert "call" in contact["notification_methods"], "Call method missing"
        assert "page" in contact["notification_methods"], "Page method missing"
        assert "email" in contact["notification_methods"], "Email method missing"

        # ========================================
        # Phase 3: Clean up test contact
        # ========================================

        # Remove test contact
        removed = emergency_system2.remove_emergency_contact(contact["id"])
        assert removed is True, "Failed to remove test contact"

        # Verify removal
        contacts = emergency_system2.get_emergency_contacts()
        test_contact = [c for c in contacts if c["name"] == test_contact_name]
        assert len(test_contact) == 0, "Test contact still present after removal"

        db2.disconnect()

        return True

    except (KeyError, TypeError, ValueError):
        import traceback

        traceback.print_exc()
        return False
