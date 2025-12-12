#!/usr/bin/env python3
"""
Integration test for phone registration tracking
Tests the full flow from SIP REGISTER to database storage
"""
import os
import re
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.core.pbx import PBXCore
from pbx.sip.message import SIPMessage



def test_mac_extraction():
    """Test MAC address extraction from various SIP header formats"""
    print("Testing MAC address extraction from SIP headers...")

    # Create a minimal config
    pbx = PBXCore("config.yml")

    # Test 1: MAC in Contact header
    contact1 = "<sip:1001@192.168.1.100:5060;mac=00:15:65:12:34:56>"
    user_agent1 = "Yealink SIP-T46S 66.85.0.5"
    mac1 = pbx._extract_mac_address(contact1, user_agent1)
    assert mac1 == "001565123456", f"Expected 001565123456, got {mac1}"
    print(f"  ✓ Extracted MAC from Contact: {mac1}")

    # Test 2: MAC in User-Agent
    contact2 = "<sip:1002@192.168.1.101:5060>"
    user_agent2 = "Yealink SIP-T46S 66.85.0.5 00:15:65:AA:BB:CC"
    mac2 = pbx._extract_mac_address(contact2, user_agent2)
    assert mac2 == "001565aabbcc", f"Expected 001565aabbcc, got {mac2}"
    print(f"  ✓ Extracted MAC from User-Agent: {mac2}")

    # Test 3: No MAC available
    contact3 = "<sip:1003@192.168.1.102:5060>"
    user_agent3 = "Generic SIP Phone"
    mac3 = pbx._extract_mac_address(contact3, user_agent3)
    assert mac3 is None, f"Expected None, got {mac3}"
    print(f"  ✓ Correctly handled no MAC: {mac3}")

    # Test 4: MAC with hyphens
    contact4 = "<sip:1004@192.168.1.103:5060;mac=00-15-65-11-22-33>"
    user_agent4 = "Polycom VVX 450"
    mac4 = pbx._extract_mac_address(contact4, user_agent4)
    assert mac4 == "001565112233", f"Expected 001565112233, got {mac4}"
    print(f"  ✓ Extracted MAC with hyphens: {mac4}")

    print("✓ MAC address extraction works")


def test_registration_storage():
    """Test that phone registration is stored in database"""
    print("Testing phone registration storage...")

    # Create PBX with in-memory database
    pbx = PBXCore("config.yml")

    # Override to use in-memory database for testing
    if pbx.database:
        pbx.database.disconnect()

    from pbx.utils.config import Config
    from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB

    config = Config("config.yml")
    config.config['database'] = {
        'type': 'sqlite',
        'path': ':memory:'
    }

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to test database"
    assert db.create_tables(), "Failed to create tables"

    pbx.database = db
    pbx.registered_phones_db = RegisteredPhonesDB(db)

    # Add a test extension to the in-memory database
    from pbx.utils.database import ExtensionDB
    pbx.extension_db = ExtensionDB(db)

    # Add extension to database with a simple hash for testing
    import hashlib
    password_hash = hashlib.sha256("testpass".encode()).hexdigest()
    pbx.extension_db.add(
        number="1001",
        name="Test User",
        email="test@test.com",
        password_hash=password_hash
    )

    # Simulate a SIP REGISTER
    from_header = '"Test Phone" <sip:1001@192.168.1.100>'
    addr = ('192.168.1.100', 5060)
    user_agent = "Yealink SIP-T46S 66.85.0.5 00:15:65:12:34:56"
    contact = "<sip:1001@192.168.1.100:5060>"

    # Call register_extension
    success = pbx.register_extension(from_header, addr, user_agent, contact)
    assert success, "Registration failed"

    # Verify it was stored in database
    phones = pbx.registered_phones_db.get_by_extension("1001")
    assert len(phones) >= 1, "Phone not found in database"

    phone = phones[0]
    assert phone['extension_number'] == "1001", "Wrong extension"
    assert phone['ip_address'] == "192.168.1.100", "Wrong IP"
    assert phone['mac_address'] == "001565123456", "Wrong MAC"
    assert phone['user_agent'] == user_agent, "Wrong User-Agent"

    print("  ✓ Phone stored in database with all details")
    print(f"    Extension: {phone['extension_number']}")
    print(f"    IP: {phone['ip_address']}")
    print(f"    MAC: {phone['mac_address']}")
    print(f"    User-Agent: {phone['user_agent']}")

    # Test re-registration (should update, not create new)
    user_agent2 = "Yealink SIP-T46S 66.85.0.10 00:15:65:12:34:56"
    success = pbx.register_extension(from_header, addr, user_agent2, contact)
    assert success, "Re-registration failed"

    phones = pbx.registered_phones_db.get_by_extension("1001")
    assert len(phones) == 1, "Should only have one record after re-registration"
    assert phones[0]['user_agent'] == user_agent2, "User-Agent not updated"

    print("  ✓ Re-registration updates existing record")

    print("✓ Phone registration storage works")


def test_ip_based_tracking():
    """Test tracking phones by IP when MAC is not available"""
    print("Testing IP-based tracking (no MAC)...")

    # Create PBX with in-memory database
    from pbx.utils.config import Config
    from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB

    config = Config("config.yml")
    config.config['database'] = {
        'type': 'sqlite',
        'path': ':memory:'
    }

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to test database"
    assert db.create_tables(), "Failed to create tables"

    pbx = PBXCore("config.yml")
    pbx.database = db
    pbx.registered_phones_db = RegisteredPhonesDB(db)

    # Add a test extension to the database
    from pbx.utils.database import ExtensionDB
    pbx.extension_db = ExtensionDB(db)
    import hashlib
    password_hash = hashlib.sha256("testpass".encode()).hexdigest()
    pbx.extension_db.add(
        number="1002",
        name="Generic User",
        email="test2@test.com",
        password_hash=password_hash
    )

    # Simulate registration without MAC
    from_header = '"Generic Phone" <sip:1002@192.168.1.101>'
    addr = ('192.168.1.101', 5060)
    user_agent = "Generic SIP Phone"
    contact = "<sip:1002@192.168.1.101:5060>"

    success = pbx.register_extension(from_header, addr, user_agent, contact)
    assert success, "Registration failed"

    # Verify stored with IP but no MAC
    phones = pbx.registered_phones_db.get_by_extension("1002")
    assert len(phones) >= 1, "Phone not found"

    phone = phones[0]
    assert phone['ip_address'] == "192.168.1.101", "Wrong IP"
    assert phone['mac_address'] is None, "MAC should be None"

    print(f"  ✓ Phone tracked by IP: {phone['ip_address']}")
    print(f"  ✓ MAC correctly stored as None")

    print("✓ IP-based tracking works")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Phone Registration Integration Tests")
    print("=" * 60)

    try:
        test_mac_extraction()
        test_registration_storage()
        test_ip_based_tracking()

        print("=" * 60)
        print("Results: 3 passed, 0 failed")
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
