#!/usr/bin/env python3
"""
Test to verify emergency contacts persist across restarts
"""

import os
import shutil
import tempfile
from pathlib import Path

from pbx.features.emergency_notification import EmergencyNotificationSystem
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_emergency_contact_persistence_across_restarts() -> None:
    """Test that emergency contacts persist when system restarts"""

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_persistence.db"

    try:
        # ========================================
        # Phase 1: Initial setup and add contacts
        # ========================================

        # Create a test config (no contacts in config)
        test_config = Config("config.yml")
        test_config.config["database"] = {"type": "sqlite", "path": db_path}
        test_config.config["features"] = {
            "emergency_notification": {
                "enabled": True,
                "notify_on_911": True,
                "methods": ["call", "page", "email"],
                "contacts": [],  # Empty - contacts will be added via UI
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

        # Verify no contacts initially
        contacts = emergency_system.get_emergency_contacts()
        assert len(contacts) == 0, f"Expected 0 contacts initially, got {len(contacts)}"

        # Add emergency contacts (simulating admin UI)
        contact1 = emergency_system.add_emergency_contact(
            name="Security Officer",
            extension="1001",
            phone="555-1234",
            email="security@example.com",
            priority=1,
            notification_methods=["call", "page", "email"],
        )

        contact2 = emergency_system.add_emergency_contact(
            name="Manager",
            extension="1002",
            phone="555-5678",
            email="manager@example.com",
            priority=2,
            notification_methods=["call", "email"],
        )

        contact3 = emergency_system.add_emergency_contact(
            name="Receptionist",
            extension="1003",
            email="reception@example.com",
            priority=3,
            notification_methods=["page"],
        )

        assert contact1 is not None, "Failed to add contact 1"
        assert contact2 is not None, "Failed to add contact 2"
        assert contact3 is not None, "Failed to add contact 3"

        # Verify contacts were added
        contacts = emergency_system.get_emergency_contacts()
        assert len(contacts) == 3, f"Expected 3 contacts, got {len(contacts)}"

        # Clean up - disconnect database
        db.disconnect()

        # ========================================
        # Phase 2: Restart system and verify persistence
        # ========================================

        # Create NEW config (simulating restart)
        test_config2 = Config("config.yml")
        test_config2.config["database"] = {"type": "sqlite", "path": db_path}  # Same database file
        test_config2.config["features"] = {
            "emergency_notification": {
                "enabled": True,
                "notify_on_911": True,
                "methods": ["call", "page", "email"],
                "contacts": [],  # Still empty in config
            }
        }

        # Initialize database again
        db2 = DatabaseBackend(test_config2)
        assert db2.connect() is True, "Failed to reconnect to database"

        pbx_core2 = MockPBXCore()

        # Initialize emergency notification system again (simulating restart)
        emergency_system2 = EmergencyNotificationSystem(pbx_core2, test_config2.config, db2)

        # Verify contacts were loaded from database
        contacts = emergency_system2.get_emergency_contacts()
        assert len(contacts) == 3, f"Expected 3 contacts after restart, got {len(contacts)}"

        # Verify contact details
        contact_names = [c["name"] for c in contacts]
        assert "Security Officer" in contact_names, "Security Officer not found"
        assert "Manager" in contact_names, "Manager not found"
        assert "Receptionist" in contact_names, "Receptionist not found"

        # Verify priority ordering
        assert contacts[0]["priority"] == 1, "First contact should have priority 1"
        assert contacts[1]["priority"] == 2, "Second contact should have priority 2"
        assert contacts[2]["priority"] == 3, "Third contact should have priority 3"

        # Verify contact details for Security Officer
        security_contact = next(c for c in contacts if c["name"] == "Security Officer")
        assert security_contact["extension"] == "1001", "Extension mismatch"
        assert security_contact["phone"] == "555-1234", "Phone mismatch"
        assert security_contact["email"] == "security@example.com", "Email mismatch"
        assert "call" in security_contact["notification_methods"], "Call method missing"
        assert "page" in security_contact["notification_methods"], "Page method missing"
        assert "email" in security_contact["notification_methods"], "Email method missing"

        # ========================================
        # Phase 3: Test removal and persistence
        # ========================================

        # Remove one contact
        manager_id = next(c["id"] for c in contacts if c["name"] == "Manager")
        removed = emergency_system2.remove_emergency_contact(manager_id)
        assert removed is True, "Failed to remove contact"

        # Verify removal
        contacts = emergency_system2.get_emergency_contacts()
        assert len(contacts) == 2, f"Expected 2 contacts after removal, got {len(contacts)}"

        # Clean up
        db2.disconnect()

        # ========================================
        # Phase 4: Verify removal persisted
        # ========================================

        # Restart again
        db3 = DatabaseBackend(test_config2)
        assert db3.connect() is True, "Failed to reconnect to database"

        pbx_core3 = MockPBXCore()
        emergency_system3 = EmergencyNotificationSystem(pbx_core3, test_config2.config, db3)

        # Verify only 2 contacts remain
        contacts = emergency_system3.get_emergency_contacts()
        assert len(contacts) == 2, f"Expected 2 contacts after restart, got {len(contacts)}"

        contact_names = [c["name"] for c in contacts]
        assert "Security Officer" in contact_names, "Security Officer should remain"
        assert "Receptionist" in contact_names, "Receptionist should remain"
        assert "Manager" not in contact_names, "Manager should be removed"

        db3.disconnect()

    finally:
        # Clean up
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
