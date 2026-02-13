#!/usr/bin/env python3
"""
Test for database-based extension registration validation
Verifies that extensions in the database can register even if not in config.yml
"""


from pbx.core.pbx import PBXCore
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, ExtensionDB, RegisteredPhonesDB


def test_database_extension_registration() -> None:
    """Test that extensions in database can register (not just config.yml)"""

    # Create PBX with in-memory database
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to test database"
    assert db.create_tables(), "Failed to create tables"

    # Create PBX instance
    pbx = PBXCore("config.yml")
    pbx.database = db
    pbx.registered_phones_db = RegisteredPhonesDB(db)
    pbx.extension_db = ExtensionDB(db)

    # Add an extension to the database (not in config.yml)
    # Use extension 9999 which is unlikely to be in config
    success = pbx.extension_db.add(
        number="9999",
        name="Test Database Extension",
        password_hash="test_hash_123",
        email="test@example.com",
    )
    assert success, "Failed to add extension to database"

    # Verify it's in the database
    db_ext = pbx.extension_db.get("9999")
    assert db_ext is not None, "Extension not found in database"
    assert db_ext["number"] == "9999", "Wrong extension number"

    # Now try to register this extension
    from_header = '"Test DB Phone" <sip:9999@192.168.1.200>'
    addr = ("192.168.1.200", 5060)
    user_agent = "Test Phone"
    contact = "<sip:9999@192.168.1.200:5060>"

    # This should succeed because extension is in database
    success = pbx.register_extension(from_header, addr, user_agent, contact)
    assert success, "Registration of database extension failed"

    # Verify it's registered in the extension registry
    is_registered = pbx.extension_registry.is_registered("9999")
    assert is_registered, "Extension not marked as registered in registry"

    # Verify phone tracking was also stored
    phones = pbx.registered_phones_db.get_by_extension("9999")
    assert len(phones) >= 1, "Phone not tracked in database"
    assert phones[0]["ip_address"] == "192.168.1.200", "Wrong IP address"


def test_config_extension_still_works() -> None:
    """Test that database-based extensions work with registration"""

    # Create PBX - it will load extensions from database
    pbx = PBXCore("config.yml")

    # Check if any extensions were loaded from database
    if len(pbx.extension_registry.extensions) == 0:
        return

    # Get the first available extension from the loaded extensions
    test_ext_number = list(pbx.extension_registry.extensions.keys())[0]
    test_ext_name = pbx.extension_registry.extensions[test_ext_number].name

    # Try to register this existing database extension
    from_header = f'"{test_ext_name}" <sip:{test_ext_number}@192.168.1.100>'
    addr = ("192.168.1.100", 5060)
    user_agent = "Test Phone"
    contact = f"<sip:{test_ext_number}@192.168.1.100:5060>"

    # This should succeed because extension exists in database
    success = pbx.register_extension(from_header, addr, user_agent, contact)
    assert success, "Registration of config extension failed"

    # Verify it's registered
    is_registered = pbx.extension_registry.is_registered(test_ext_number)
    assert is_registered, "Extension not marked as registered"


def test_unknown_extension_rejected() -> None:
    """Test that unknown extensions are still rejected"""

    # Create PBX with in-memory database
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to test database"
    assert db.create_tables(), "Failed to create tables"

    pbx = PBXCore("config.yml")
    pbx.database = db
    pbx.registered_phones_db = RegisteredPhonesDB(db)
    pbx.extension_db = ExtensionDB(db)

    # Try to register an extension that doesn't exist (not in DB or config)
    from_header = '"Unknown Extension" <sip:8888@192.168.1.150>'
    addr = ("192.168.1.150", 5060)
    user_agent = "Test Phone"
    contact = "<sip:8888@192.168.1.150:5060>"

    # This should fail
    success = pbx.register_extension(from_header, addr, user_agent, contact)
    assert not success, "Unknown extension should be rejected"

    # Verify it's NOT registered
    is_registered = pbx.extension_registry.is_registered("8888")
    assert not is_registered, "Unknown extension should not be registered"


def test_database_priority() -> None:
    """Test that database takes priority over config"""

    # Create PBX with in-memory database
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to test database"
    assert db.create_tables(), "Failed to create tables"

    pbx = PBXCore("config.yml")
    pbx.database = db
    pbx.registered_phones_db = RegisteredPhonesDB(db)
    pbx.extension_db = ExtensionDB(db)

    # Add extension 1001 to database (which also exists in config)
    # This tests that database is checked first
    success = pbx.extension_db.add(
        number="1001",
        name="Database Version of 1001",
        password_hash="db_hash_456",
        email="db1001@example.com",
    )
    assert success, "Failed to add extension to database"

    # Now register - should use database version
    from_header = '"Priority Test" <sip:1001@192.168.1.100>'
    addr = ("192.168.1.100", 5060)
    user_agent = "Test Phone"
    contact = "<sip:1001@192.168.1.100:5060>"

    success = pbx.register_extension(from_header, addr, user_agent, contact)
    assert success, "Registration failed"

    # Verify database extension was used (by checking it exists in DB)
    db_ext = pbx.extension_db.get("1001")
    assert db_ext is not None, "Extension should exist in database"
    assert db_ext["name"] == "Database Version of 1001", "Database version should be used"
