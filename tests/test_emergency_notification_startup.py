#!/usr/bin/env python3
"""
Test to verify emergency notification system initializes without database errors
"""
import os
import shutil
import sys
import tempfile

from pbx.features.emergency_notification import EmergencyNotificationSystem
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_emergency_notification_system_initialization():
    """Test that emergency notification system initializes without database errors"""
    print("Testing emergency notification system initialization...")

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')

    try:
        # Create a test config
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': db_path
        }
        test_config.config['features'] = {
            'emergency_notification': {
                'enabled': True,
                'notify_on_911': True,
                'methods': ['call', 'page', 'email'],
                'contacts': []
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
        emergency_system = EmergencyNotificationSystem(
            pbx_core, test_config.config, db)

        # Verify initialization
        assert emergency_system is not None, "Emergency system not initialized"
        assert emergency_system.enabled is True, "Emergency system should be enabled"
        assert len(
            emergency_system.emergency_contacts) == 0, "Should have no contacts initially"

        # Verify database connection works
        contacts = emergency_system.get_emergency_contacts()
        assert contacts == [], "Should return empty list initially"

        print("✓ Emergency notification system initialized without errors")

        # Clean up
        db.disconnect()

    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_emergency_notification_database_operations():
    """Test that emergency notification system can perform database operations"""
    print("Testing emergency notification database operations...")

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')

    try:
        # Create a test config
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': db_path
        }
        test_config.config['features'] = {
            'emergency_notification': {
                'enabled': True,
                'notify_on_911': True,
                'methods': ['call', 'page', 'email'],
                'contacts': []
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
        emergency_system = EmergencyNotificationSystem(
            pbx_core, test_config.config, db)

        # Add an emergency contact
        contact = emergency_system.add_emergency_contact(
            name="Test Contact",
            extension="1001",
            phone="555-1234",
            email="test@example.com",
            priority=1,
            notification_methods=['call', 'email']
        )

        assert contact is not None, "Failed to add emergency contact"
        assert contact.name == "Test Contact", "Contact name mismatch"

        # Verify contact was added
        contacts = emergency_system.get_emergency_contacts()
        assert len(contacts) == 1, f"Expected 1 contact, got {len(contacts)}"
        assert contacts[0]['name'] == "Test Contact", "Contact name mismatch"

        print("✓ Emergency notification database operations work correctly")

        # Clean up
        db.disconnect()

    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Running Emergency Notification Startup Tests")
    print("=" * 70)
    print()

    tests = [
        test_emergency_notification_system_initialization,
        test_emergency_notification_database_operations,
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


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
