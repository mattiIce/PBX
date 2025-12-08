#!/usr/bin/env python3
"""
Tests for clearing registered phones on server boot
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB
from pbx.utils.config import Config


def test_clear_all_phones():
    """Test clearing all phone registrations"""
    print("Testing clear_all() functionality...")
    
    # Create database backend (using SQLite for tests)
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
    _ = phones_db.register_phone("1001", "192.168.1.100", "001565123456")
    _ = phones_db.register_phone("1002", "192.168.1.101", "001565123457")
    _ = phones_db.register_phone("1003", "192.168.1.102", None)
    
    # Verify phones were registered
    all_phones = phones_db.list_all()
    assert len(all_phones) == 3, f"Expected 3 phones, got {len(all_phones)}"
    
    # Clear all phones
    success = phones_db.clear_all()
    assert success, "Failed to clear phones"
    
    # Verify all phones were cleared
    all_phones = phones_db.list_all()
    assert len(all_phones) == 0, f"Expected 0 phones after clear, got {len(all_phones)}"
    
    print("✓ clear_all() works correctly")


def test_clear_empty_table():
    """Test clearing an already empty table"""
    print("Testing clear_all() on empty table...")
    
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
    
    # Clear empty table (should not fail)
    success = phones_db.clear_all()
    assert success, "Failed to clear empty table"
    
    # Verify still empty
    all_phones = phones_db.list_all()
    assert len(all_phones) == 0, f"Expected 0 phones, got {len(all_phones)}"
    
    print("✓ clear_all() on empty table works")


def test_register_after_clear():
    """Test that phones can be registered after clearing"""
    print("Testing registration after clear_all()...")
    
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
    
    # Register phones
    _ = phones_db.register_phone("1001", "192.168.1.100", "001565123456")
    _ = phones_db.register_phone("1002", "192.168.1.101", "001565123457")
    
    # Clear all
    phones_db.clear_all()
    
    # Verify cleared
    assert len(phones_db.list_all()) == 0, "Phones not cleared"
    
    # Register new phones
    success, _ = phones_db.register_phone("1003", "192.168.1.102", "001565123458")
    assert success, "Failed to register phone after clear"
    
    # Verify new phone is registered
    phones = phones_db.list_all()
    assert len(phones) == 1, f"Expected 1 phone, got {len(phones)}"
    assert phones[0]['extension_number'] == "1003", "Wrong extension registered"
    
    print("✓ Registration after clear_all() works")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Clear Phones on Boot Tests")
    print("=" * 60)
    
    try:
        test_clear_all_phones()
        test_clear_empty_table()
        test_register_after_clear()
        
        print("=" * 60)
        print("Results: 3 passed, 0 failed")
        print("=" * 60)
        return True
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
