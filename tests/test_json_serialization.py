#!/usr/bin/env python3
"""
Tests for JSON serialization of datetime objects in API responses
"""
import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.api.rest_api import DateTimeEncoder
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB
from pbx.utils.config import Config


def test_datetime_encoder():
    """Test that DateTimeEncoder correctly serializes datetime objects"""
    print("Testing DateTimeEncoder...")
    
    # Create test data with datetime objects
    test_data = {
        'id': 1,
        'name': 'Test',
        'created_at': datetime(2025, 12, 5, 14, 30, 0),
        'updated_at': datetime(2025, 12, 5, 15, 45, 30)
    }
    
    # Serialize with custom encoder
    json_str = json.dumps(test_data, cls=DateTimeEncoder)
    print(f"  Serialized JSON: {json_str}")
    
    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed['id'] == 1, "ID should match"
    assert parsed['name'] == 'Test', "Name should match"
    assert parsed['created_at'] == '2025-12-05T14:30:00', "Created timestamp should be ISO format"
    assert parsed['updated_at'] == '2025-12-05T15:45:30', "Updated timestamp should be ISO format"
    
    print("✓ DateTimeEncoder works correctly")


def test_registered_phones_json_serialization():
    """Test JSON serialization of registered phones with datetime objects"""
    print("Testing registered phones JSON serialization...")
    
    # Simulate what PostgreSQL returns with datetime objects
    phones = [
        {
            'id': 1,
            'mac_address': '001565123456',
            'extension_number': '1001',
            'user_agent': 'Yealink SIP-T46S',
            'ip_address': '192.168.1.100',
            'first_registered': datetime(2025, 12, 5, 14, 0, 0),
            'last_registered': datetime(2025, 12, 5, 14, 30, 0),
            'contact_uri': '<sip:1001@192.168.1.100:5060>'
        },
        {
            'id': 2,
            'mac_address': '001565123457',
            'extension_number': '1002',
            'user_agent': 'Cisco SPA504G',
            'ip_address': '192.168.1.101',
            'first_registered': datetime(2025, 12, 5, 13, 0, 0),
            'last_registered': datetime(2025, 12, 5, 14, 15, 0),
            'contact_uri': '<sip:1002@192.168.1.101:5060>'
        }
    ]
    
    # Serialize with custom encoder
    json_str = json.dumps(phones, cls=DateTimeEncoder)
    print(f"  Serialized {len(phones)} phones successfully")
    
    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert len(parsed) == 2, "Should have 2 phones"
    assert parsed[0]['extension_number'] == '1001', "First phone extension should match"
    assert parsed[0]['first_registered'] == '2025-12-05T14:00:00', "First phone timestamp should be ISO format"
    assert parsed[1]['extension_number'] == '1002', "Second phone extension should match"
    
    print("✓ Registered phones JSON serialization works correctly")


def test_registered_phones_db_with_encoder():
    """Test that registered phones from database can be serialized"""
    print("Testing registered phones from database with JSON encoder...")
    
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
    
    # Register phones
    _ = phones_db.register_phone("1001", "192.168.1.100", "001565123456", "Yealink SIP-T46S")
    _ = phones_db.register_phone("1002", "192.168.1.101", "001565123457", "Cisco SPA504G")
    
    # Get all phones
    phones = phones_db.list_all()
    
    # Serialize with custom encoder (should work even if datetime objects are present)
    json_str = json.dumps(phones, cls=DateTimeEncoder)
    
    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert len(parsed) >= 2, "Should have at least 2 phones"
    
    print("✓ Database registered phones can be serialized to JSON")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)    print("Running JSON Serialization Tests")    print("=" * 60)        try:        test_datetime_encoder()        test_registered_phones_json_serialization()        test_registered_phones_db_with_encoder()                print("=" * 60)        print("Results: 3 passed, 0 failed")        print("=" * 60)    except AssertionError as e:        print(f"\n✗ Test failed: {e}")        return False    except Exception as e:        print(f"\n✗ Unexpected error: {e}")        import traceback        traceback.print_exc()        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
