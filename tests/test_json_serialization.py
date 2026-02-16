#!/usr/bin/env python3
"""
Tests for JSON serialization of datetime objects in API responses
"""

import json
from datetime import UTC, datetime

from pbx.api.rest_api import DateTimeEncoder
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB


def test_datetime_encoder() -> None:
    """Test that DateTimeEncoder correctly serializes datetime objects"""

    # Create test data with datetime objects
    test_data = {
        "id": 1,
        "name": "Test",
        "created_at": datetime(2025, 12, 5, 14, 30, 0, tzinfo=UTC),
        "updated_at": datetime(2025, 12, 5, 15, 45, 30, tzinfo=UTC),
    }

    # Serialize with custom encoder
    json_str = json.dumps(test_data, cls=DateTimeEncoder)

    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed["id"] == 1, "ID should match"
    assert parsed["name"] == "Test", "Name should match"
    assert parsed["created_at"] == "2025-12-05T14:30:00+00:00", "Created timestamp should be ISO format"
    assert parsed["updated_at"] == "2025-12-05T15:45:30+00:00", "Updated timestamp should be ISO format"


def test_registered_phones_json_serialization() -> None:
    """Test JSON serialization of registered phones with datetime objects"""

    # Simulate what PostgreSQL returns with datetime objects
    phones = [
        {
            "id": 1,
            "mac_address": "001565123456",
            "extension_number": "1001",
            "user_agent": "Yealink SIP-T46S",
            "ip_address": "192.168.1.100",
            "first_registered": datetime(2025, 12, 5, 14, 0, 0, tzinfo=UTC),
            "last_registered": datetime(2025, 12, 5, 14, 30, 0, tzinfo=UTC),
            "contact_uri": "<sip:1001@192.168.1.100:5060>",
        },
        {
            "id": 2,
            "mac_address": "001565123457",
            "extension_number": "1002",
            "user_agent": "Cisco SPA504G",
            "ip_address": "192.168.1.101",
            "first_registered": datetime(2025, 12, 5, 13, 0, 0, tzinfo=UTC),
            "last_registered": datetime(2025, 12, 5, 14, 15, 0, tzinfo=UTC),
            "contact_uri": "<sip:1002@192.168.1.101:5060>",
        },
    ]

    # Serialize with custom encoder
    json_str = json.dumps(phones, cls=DateTimeEncoder)

    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert len(parsed) == 2, "Should have 2 phones"
    assert parsed[0]["extension_number"] == "1001", "First phone extension should match"
    assert parsed[0]["first_registered"] == "2025-12-05T14:00:00+00:00", (
        "First phone timestamp should be ISO format"
    )
    assert parsed[1]["extension_number"] == "1002", "Second phone extension should match"


def test_registered_phones_db_with_encoder() -> None:
    """Test that registered phones from database can be serialized"""

    # Create database backend (using SQLite for tests)
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

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

    # Serialize with custom encoder (should work even if datetime objects are
    # present)
    json_str = json.dumps(phones, cls=DateTimeEncoder)

    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert len(parsed) >= 2, "Should have at least 2 phones"
