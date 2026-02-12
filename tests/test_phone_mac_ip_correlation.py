#!/usr/bin/env python3
"""
Tests for phone MAC-to-IP correlation feature
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.phone_provisioning import PhoneProvisioning, normalize_mac_address
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB


def test_mac_normalization():
    """Test MAC address normalization used in lookups"""
    print("Testing MAC address normalization...")

    test_cases = [
        ("00:15:65:12:34:56", "001565123456"),
        ("00-15-65-12-34-56", "001565123456"),
        ("0015.6512.3456", "001565123456"),
        ("001565123456", "001565123456"),
        ("00:15:65:AB:CD:EF", "001565abcdef"),
    ]

    for input_mac, expected in test_cases:
        result = normalize_mac_address(input_mac)
        assert result == expected, f"MAC {input_mac} normalized to {result}, expected {expected}"

    print("✓ MAC address normalization works correctly")


def test_provisioned_device_structure():
    """Test that provisioned devices have required fields for correlation"""
    print("Testing provisioned device data structure...")

    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Register a test device
    device = provisioning.register_device("00:15:65:12:34:56", "1001", "yealink", "t46s")

    # Verify device has all required fields
    assert device.mac_address == "001565123456", "MAC address should be normalized"
    assert device.extension_number == "1001", "Extension number should match"
    assert device.vendor == "yealink", "Vendor should match"
    assert device.model == "t46s", "Model should match"

    # Test dict conversion
    device_dict = device.to_dict()
    assert "mac_address" in device_dict, "Device dict should have mac_address"
    assert "extension_number" in device_dict, "Device dict should have extension_number"
    assert "vendor" in device_dict, "Device dict should have vendor"
    assert "model" in device_dict, "Device dict should have model"

    print("✓ Provisioned device structure is correct")


def test_registered_phone_lookup_methods():
    """Test RegisteredPhonesDB lookup methods"""
    print("Testing registered phone lookup methods...")

    # Create in-memory SQLite database for testing
    config = {"database.type": "sqlite", "database.path": ":memory:"}

    db = DatabaseBackend(config)
    if not db.connect():
        print("⚠ Skipping test - could not connect to test database")
        return

    db.create_tables()
    registered_phones_db = RegisteredPhonesDB(db)

    # Register a test phone
    success, _ = registered_phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address="001565123456",
        user_agent="Yealink SIP-T46S 66.85.0.5",
        contact_uri="<sip:1001@192.168.1.100:5060>",
    )

    assert success, "Should successfully register phone"

    # Test lookup by MAC
    phone_by_mac = registered_phones_db.get_by_mac("001565123456")
    assert phone_by_mac is not None, "Should find phone by MAC"
    assert phone_by_mac["ip_address"] == "192.168.1.100", "IP should match"
    assert phone_by_mac["extension_number"] == "1001", "Extension should match"

    # Test lookup by IP
    phone_by_ip = registered_phones_db.get_by_ip("192.168.1.100")
    assert phone_by_ip is not None, "Should find phone by IP"
    assert phone_by_ip["mac_address"] == "001565123456", "MAC should match"
    assert phone_by_ip["extension_number"] == "1001", "Extension should match"

    # Test lookup by extension
    phones_by_ext = registered_phones_db.get_by_extension("1001")
    assert len(phones_by_ext) == 1, "Should find one phone for extension"
    assert phones_by_ext[0]["mac_address"] == "001565123456", "MAC should match"
    assert phones_by_ext[0]["ip_address"] == "192.168.1.100", "IP should match"

    print("✓ Registered phone lookup methods work correctly")


def test_correlation_scenario_mac_to_ip():
    """Test correlation: Given MAC, find IP"""
    print("Testing MAC-to-IP correlation scenario...")

    # Setup
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Create in-memory database
    db_config = {"database.type": "sqlite", "database.path": ":memory:"}
    db = DatabaseBackend(db_config)
    if not db.connect():
        print("⚠ Skipping test - could not connect to test database")
        return
    db.create_tables()
    registered_phones_db = RegisteredPhonesDB(db)

    # Scenario: Device is provisioned with MAC
    provisioning.register_device("00:15:65:12:34:56", "1001", "yealink", "t46s")

    # Scenario: Phone registers via SIP (provides IP, may provide MAC)
    _ = registered_phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address="001565123456",  # Some phones provide MAC in SIP headers
        user_agent="Yealink SIP-T46S 66.85.0.5",
    )

    # Given MAC from provisioning, find IP from registration
    normalized_mac = normalize_mac_address("00:15:65:12:34:56")

    # Method 1: Direct MAC lookup
    phone = registered_phones_db.get_by_mac(normalized_mac)
    assert phone is not None, "Should find phone by MAC"
    assert phone["ip_address"] == "192.168.1.100", "Should get correct IP"

    # Method 2: Lookup via extension (if MAC not in registered_phones)
    provisioned_device = provisioning.get_device("00:15:65:12:34:56")
    extension = provisioned_device.extension_number
    phones = registered_phones_db.get_by_extension(extension)
    assert len(phones) > 0, "Should find phones by extension"
    assert phones[0]["ip_address"] == "192.168.1.100", "Should get correct IP"

    print("✓ MAC-to-IP correlation works")


def test_correlation_scenario_ip_to_mac():
    """Test correlation: Given IP, find MAC"""
    print("Testing IP-to-MAC correlation scenario...")

    # Setup
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Create in-memory database
    db_config = {"database.type": "sqlite", "database.path": ":memory:"}
    db = DatabaseBackend(db_config)
    if not db.connect():
        print("⚠ Skipping test - could not connect to test database")
        return
    db.create_tables()
    registered_phones_db = RegisteredPhonesDB(db)

    # Scenario: Device is provisioned with MAC
    provisioning.register_device("00:15:65:AB:CD:EF", "1002", "polycom", "vvx450")

    # Scenario: Phone registers via SIP (provides IP, but NO MAC)
    _ = registered_phones_db.register_phone(
        extension_number="1002",
        ip_address="192.168.1.101",
        mac_address=None,  # Phone didn't provide MAC in SIP
        user_agent="PolycomVVX-VVX_450-UA/5.9.0.9373",
    )

    # Given IP from registration, find MAC from provisioning
    phone = registered_phones_db.get_by_ip("192.168.1.101")
    assert phone is not None, "Should find phone by IP"

    extension = phone["extension_number"]
    assert extension == "1002", "Should get correct extension"

    # Now look up MAC from provisioning system using the extension
    all_devices = provisioning.get_all_devices()
    device_with_mac = None
    for dev in all_devices:
        if dev.extension_number == extension:
            device_with_mac = dev
            break

    assert device_with_mac is not None, "Should find provisioned device for extension"
    assert device_with_mac.mac_address == "001565abcdef", "Should get correct MAC"
    assert device_with_mac.vendor == "polycom", "Should get correct vendor"
    assert device_with_mac.model == "vvx450", "Should get correct model"

    print("✓ IP-to-MAC correlation works")


def test_no_mac_in_sip_registration():
    """Test scenario where phone doesn't provide MAC in SIP REGISTER"""
    print("Testing scenario with no MAC in SIP registration...")

    # Create in-memory database
    db_config = {"database.type": "sqlite", "database.path": ":memory:"}
    db = DatabaseBackend(db_config)
    if not db.connect():
        print("⚠ Skipping test - could not connect to test database")
        return
    db.create_tables()
    registered_phones_db = RegisteredPhonesDB(db)

    # Phone registers WITHOUT MAC
    success, _ = registered_phones_db.register_phone(
        extension_number="1003",
        ip_address="192.168.1.102",
        mac_address=None,  # No MAC provided
        user_agent="Generic SIP Phone",
    )

    assert success, "Should successfully register phone without MAC"

    # Verify phone is in database
    phone = registered_phones_db.get_by_ip("192.168.1.102")
    assert phone is not None, "Should find phone by IP"
    assert phone["mac_address"] is None, "MAC should be None"
    assert phone["ip_address"] == "192.168.1.102", "IP should be correct"

    print("✓ Phone registration without MAC works correctly")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Phone MAC-to-IP Correlation Tests")
    print("=" * 60)
    print()

    tests = [
        test_mac_normalization,
        test_provisioned_device_structure,
        test_registered_phone_lookup_methods,
        test_correlation_scenario_mac_to_ip,
        test_correlation_scenario_ip_to_mac,
        test_no_mac_in_sip_registration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"✗ Test error: {e}")
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
