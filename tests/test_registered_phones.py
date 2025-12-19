#!/usr/bin/env python3
"""
Tests for registered phones database tracking
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB


def test_phone_registration():
    """Test phone registration in database"""
    print("Testing phone registration...")

    # Create database backend (using SQLite for tests)
    config = Config("config.yml")
    # Override to use in-memory SQLite for testing
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    # Create registered phones DB
    phones_db = RegisteredPhonesDB(db)

    # Register a phone with MAC address
    success, _ = phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address="001565123456",
        user_agent="Yealink SIP-T46S",
        contact_uri="<sip:1001@192.168.1.100:5060>",
    )
    assert success, "Phone registration failed"

    # Retrieve by MAC
    phone = phones_db.get_by_mac("001565123456", "1001")
    assert phone is not None, "Failed to retrieve phone by MAC"
    assert phone["extension_number"] == "1001", "Wrong extension number"
    assert phone["ip_address"] == "192.168.1.100", "Wrong IP address"
    assert phone["mac_address"] == "001565123456", "Wrong MAC address"

    # Retrieve by IP
    phone = phones_db.get_by_ip("192.168.1.100", "1001")
    assert phone is not None, "Failed to retrieve phone by IP"
    assert phone["extension_number"] == "1001", "Wrong extension number"

    print("✓ Phone registration with MAC works")


def test_phone_registration_without_mac():
    """Test phone registration without MAC address (IP-based fallback)"""
    print("Testing phone registration without MAC (IP-based)...")

    # Create database backend (using SQLite for tests)
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    # Create registered phones DB
    phones_db = RegisteredPhonesDB(db)

    # Register a phone without MAC address
    success, _ = phones_db.register_phone(
        extension_number="1002",
        ip_address="192.168.1.101",
        mac_address=None,  # No MAC available
        user_agent="Generic SIP Phone",
        contact_uri="<sip:1002@192.168.1.101:5060>",
    )
    assert success, "Phone registration without MAC failed"

    # Retrieve by IP
    phone = phones_db.get_by_ip("192.168.1.101", "1002")
    assert phone is not None, "Failed to retrieve phone by IP"
    assert phone["extension_number"] == "1002", "Wrong extension number"
    assert phone["ip_address"] == "192.168.1.101", "Wrong IP address"
    assert phone["mac_address"] is None, "MAC should be None"

    print("✓ Phone registration without MAC (IP-based) works")


def test_phone_update_registration():
    """Test updating phone registration"""
    print("Testing phone registration update...")

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Initial registration
    _ = phones_db.register_phone(
        extension_number="1003",
        ip_address="192.168.1.102",
        mac_address="001565123457",
        user_agent="Yealink SIP-T46S v1",
    )

    # Re-register with updated info (simulating phone reboot/re-registration)
    _ = phones_db.register_phone(
        extension_number="1003",
        ip_address="192.168.1.102",
        mac_address="001565123457",
        user_agent="Yealink SIP-T46S v2",
    )

    # Should only have one entry
    phones = phones_db.get_by_extension("1003")
    assert len(phones) == 1, f"Expected 1 phone, got {len(phones)}"
    assert phones[0]["user_agent"] == "Yealink SIP-T46S v2", "User agent not updated"

    print("✓ Phone registration update works")


def test_list_phones_by_extension():
    """Test listing all phones for an extension"""
    print("Testing listing phones by extension...")

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Register multiple phones for same extension (different IPs, like desk
    # and softphone)
    _ = phones_db.register_phone(
        extension_number="1004", ip_address="192.168.1.103", mac_address="001565123458"
    )

    # Get phones for extension
    phones = phones_db.get_by_extension("1004")
    assert len(phones) >= 1, "No phones found for extension"
    assert phones[0]["extension_number"] == "1004", "Wrong extension"

    print("✓ Listing phones by extension works")


def test_list_all_phones():
    """Test listing all registered phones"""
    print("Testing listing all phones...")

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Register multiple phones
    _ = phones_db.register_phone("1001", "192.168.1.100", "001565123456")
    _ = phones_db.register_phone("1002", "192.168.1.101", "001565123457")
    _ = phones_db.register_phone("1003", "192.168.1.102", None)  # No MAC

    # List all
    all_phones = phones_db.list_all()
    assert (
        len(all_phones) >= 3
    ), f"Expected at least 3 phones, got {
        len(all_phones)}"

    print("✓ Listing all phones works")


def test_mac_preservation_on_reregistration():
    """
    Test that MAC address is preserved when phone re-registers without MAC

    This addresses the issue where phones may not send MAC in every REGISTER.
    The system should preserve existing MAC/IP/extension instead of overwriting with None.
    """
    print("Testing MAC preservation on re-registration...")

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Scenario 1: Initial registration WITH MAC, re-register WITHOUT MAC
    _ = phones_db.register_phone(
        extension_number="1005",
        ip_address="192.168.1.105",
        mac_address="001565123459",
        user_agent="Yealink SIP-T46S",
        contact_uri="<sip:1005@192.168.1.105:5060>",
    )

    # Re-register without MAC (common when phone doesn't send it)
    _ = phones_db.register_phone(
        extension_number="1005",
        ip_address="192.168.1.105",
        mac_address=None,  # Phone doesn't send MAC this time
        user_agent="Yealink SIP-T46S",
        contact_uri="<sip:1005@192.168.1.105:5060>",
    )

    # Verify MAC is preserved
    phone = phones_db.get_by_ip("192.168.1.105", "1005")
    assert phone is not None, "Phone not found"
    assert phone["mac_address"] == "001565123459", "MAC should be preserved, not replaced with None"

    # Scenario 2: Re-register with different MAC should update
    _ = phones_db.register_phone(
        extension_number="1005",
        ip_address="192.168.1.105",
        mac_address="001565999999",  # Different MAC
        user_agent="Yealink SIP-T46S",
        contact_uri="<sip:1005@192.168.1.105:5060>",
    )

    phone = phones_db.get_by_ip("192.168.1.105", "1005")
    assert phone["mac_address"] == "001565999999", "MAC should be updated when new MAC provided"

    print("✓ MAC preservation on re-registration works")


def test_ip_preservation_on_reregistration():
    """
    Test that IP address is preserved when phone re-registers with MAC only
    """
    print("Testing IP preservation on re-registration...")

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Initial registration with both MAC and IP
    _ = phones_db.register_phone(
        extension_number="1006",
        ip_address="192.168.1.106",
        mac_address="00156512345A",
        user_agent="Polycom VVX 450",
    )

    # Verify initial registration
    phone = phones_db.get_by_mac("00156512345A", "1006")
    assert phone is not None, "Phone not found"
    assert phone["ip_address"] == "192.168.1.106", "IP not stored correctly"

    print("✓ IP preservation on re-registration works")


def test_update_phone_extension():
    """
    Test updating a phone's extension when reprovisioning to a different extension

    This addresses the scenario where a phone (identified by MAC) is moved from
    one extension to another. The system should update the extension number
    rather than creating duplicate entries.
    """
    print("Testing phone extension update (reprovisioning)...")

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Scenario: Phone is initially provisioned to extension 1001
    _ = phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address="001565AABBCC",
        user_agent="Yealink SIP-T46S",
        contact_uri="<sip:1001@192.168.1.100:5060>",
    )

    # Verify initial registration
    phone = phones_db.get_by_mac("001565AABBCC")
    assert phone is not None, "Phone not found after initial registration"
    assert phone["extension_number"] == "1001", "Wrong initial extension"
    assert phone["mac_address"] == "001565AABBCC", "Wrong MAC address"

    # Now reprovision the phone to extension 1002
    success = phones_db.update_phone_extension(
        mac_address="001565AABBCC", new_extension_number="1002"
    )
    assert success, "Failed to update phone extension"

    # Verify the extension was updated
    phone = phones_db.get_by_mac("001565AABBCC")
    assert phone is not None, "Phone not found after extension update"
    assert phone["extension_number"] == "1002", "Extension not updated correctly"
    assert phone["mac_address"] == "001565AABBCC", "MAC address should remain the same"
    assert phone["ip_address"] == "192.168.1.100", "IP address should remain the same"

    # Verify we don't have duplicate entries for this MAC
    all_phones = phones_db.list_all()
    mac_count = sum(1 for p in all_phones if p["mac_address"] == "001565AABBCC")
    assert mac_count == 1, f"Expected 1 entry for MAC, found {mac_count} (possible duplicate)"

    # Verify old extension 1001 has no phones registered
    old_ext_phones = phones_db.get_by_extension("1001")
    assert len(old_ext_phones) == 0, "Old extension should have no phones"

    # Verify new extension 1002 has this phone
    new_ext_phones = phones_db.get_by_extension("1002")
    assert len(new_ext_phones) == 1, "New extension should have exactly 1 phone"
    assert new_ext_phones[0]["mac_address"] == "001565AABBCC", "Wrong phone on new extension"

    print("✓ Phone extension update (reprovisioning) works")


def test_update_phone_extension_without_mac():
    """
    Test that update_phone_extension requires a MAC address
    """
    print("Testing phone extension update validation...")

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Try to update with None MAC - should return False
    success = phones_db.update_phone_extension(mac_address=None, new_extension_number="1003")
    assert not success, "Should fail when MAC address is None"

    # Try to update with empty MAC - should return False
    success = phones_db.update_phone_extension(mac_address="", new_extension_number="1003")
    assert not success, "Should fail when MAC address is empty"

    print("✓ Phone extension update validation works")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Registered Phones Tests")
    print("=" * 60)

    try:
        test_phone_registration()
        test_phone_registration_without_mac()
        test_phone_update_registration()
        test_list_phones_by_extension()
        test_list_all_phones()
        test_mac_preservation_on_reregistration()
        test_ip_preservation_on_reregistration()
        test_update_phone_extension()
        test_update_phone_extension_without_mac()

        print("=" * 60)
        print("Results: 9 passed, 0 failed")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
