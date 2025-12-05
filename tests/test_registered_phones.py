#!/usr/bin/env python3
"""
Tests for registered phones database tracking
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB
from pbx.utils.config import Config


def test_phone_registration():
    """Test phone registration in database"""
    print("Testing phone registration...")
    
    # Create database backend (using SQLite for tests)
    config = Config("config.yml")
    # Override to use in-memory SQLite for testing
    config.config['database'] = {
        'type': 'sqlite',
        'path': ':memory:'
    }
    
    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"
    
    # Create registered phones DB
    phones_db = RegisteredPhonesDB(db)
    
    # Register a phone with MAC address
    success = phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address="001565123456",
        user_agent="Yealink SIP-T46S",
        contact_uri="<sip:1001@192.168.1.100:5060>"
    )
    assert success, "Phone registration failed"
    
    # Retrieve by MAC
    phone = phones_db.get_by_mac("001565123456", "1001")
    assert phone is not None, "Failed to retrieve phone by MAC"
    assert phone['extension_number'] == "1001", "Wrong extension number"
    assert phone['ip_address'] == "192.168.1.100", "Wrong IP address"
    assert phone['mac_address'] == "001565123456", "Wrong MAC address"
    
    # Retrieve by IP
    phone = phones_db.get_by_ip("192.168.1.100", "1001")
    assert phone is not None, "Failed to retrieve phone by IP"
    assert phone['extension_number'] == "1001", "Wrong extension number"
    
    print("✓ Phone registration with MAC works")


def test_phone_registration_without_mac():
    """Test phone registration without MAC address (IP-based fallback)"""
    print("Testing phone registration without MAC (IP-based)...")
    
    # Create database backend (using SQLite for tests)
    config = Config("config.yml")
    config.config['database'] = {
        'type': 'sqlite',
        'path': ':memory:'
    }
    
    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"
    
    # Create registered phones DB
    phones_db = RegisteredPhonesDB(db)
    
    # Register a phone without MAC address
    success = phones_db.register_phone(
        extension_number="1002",
        ip_address="192.168.1.101",
        mac_address=None,  # No MAC available
        user_agent="Generic SIP Phone",
        contact_uri="<sip:1002@192.168.1.101:5060>"
    )
    assert success, "Phone registration without MAC failed"
    
    # Retrieve by IP
    phone = phones_db.get_by_ip("192.168.1.101", "1002")
    assert phone is not None, "Failed to retrieve phone by IP"
    assert phone['extension_number'] == "1002", "Wrong extension number"
    assert phone['ip_address'] == "192.168.1.101", "Wrong IP address"
    assert phone['mac_address'] is None, "MAC should be None"
    
    print("✓ Phone registration without MAC (IP-based) works")


def test_phone_update_registration():
    """Test updating phone registration"""
    print("Testing phone registration update...")
    
    # Create database backend
    config = Config("config.yml")
    config.config['database'] = {
        'type': 'sqlite',
        'path': ':memory:'
    }
    
    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"
    
    phones_db = RegisteredPhonesDB(db)
    
    # Initial registration
    phones_db.register_phone(
        extension_number="1003",
        ip_address="192.168.1.102",
        mac_address="001565123457",
        user_agent="Yealink SIP-T46S v1"
    )
    
    # Re-register with updated info (simulating phone reboot/re-registration)
    phones_db.register_phone(
        extension_number="1003",
        ip_address="192.168.1.102",
        mac_address="001565123457",
        user_agent="Yealink SIP-T46S v2"
    )
    
    # Should only have one entry
    phones = phones_db.get_by_extension("1003")
    assert len(phones) == 1, f"Expected 1 phone, got {len(phones)}"
    assert phones[0]['user_agent'] == "Yealink SIP-T46S v2", "User agent not updated"
    
    print("✓ Phone registration update works")


def test_list_phones_by_extension():
    """Test listing all phones for an extension"""
    print("Testing listing phones by extension...")
    
    # Create database backend
    config = Config("config.yml")
    config.config['database'] = {
        'type': 'sqlite',
        'path': ':memory:'
    }
    
    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"
    
    phones_db = RegisteredPhonesDB(db)
    
    # Register multiple phones for same extension (different IPs, like desk and softphone)
    phones_db.register_phone(
        extension_number="1004",
        ip_address="192.168.1.103",
        mac_address="001565123458"
    )
    
    # Get phones for extension
    phones = phones_db.get_by_extension("1004")
    assert len(phones) >= 1, "No phones found for extension"
    assert phones[0]['extension_number'] == "1004", "Wrong extension"
    
    print("✓ Listing phones by extension works")


def test_list_all_phones():
    """Test listing all registered phones"""
    print("Testing listing all phones...")
    
    # Create database backend
    config = Config("config.yml")
    config.config['database'] = {
        'type': 'sqlite',
        'path': ':memory:'
    }
    
    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"
    
    phones_db = RegisteredPhonesDB(db)
    
    # Register multiple phones
    phones_db.register_phone("1001", "192.168.1.100", "001565123456")
    phones_db.register_phone("1002", "192.168.1.101", "001565123457")
    phones_db.register_phone("1003", "192.168.1.102", None)  # No MAC
    
    # List all
    all_phones = phones_db.list_all()
    assert len(all_phones) >= 3, f"Expected at least 3 phones, got {len(all_phones)}"
    
    print("✓ Listing all phones works")


if __name__ == "__main__":
    print("=" * 60)
    print("Running Registered Phones Tests")
    print("=" * 60)
    
    try:
        test_phone_registration()
        test_phone_registration_without_mac()
        test_phone_update_registration()
        test_list_phones_by_extension()
        test_list_all_phones()
        
        print("=" * 60)
        print("Results: 5 passed, 0 failed")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
