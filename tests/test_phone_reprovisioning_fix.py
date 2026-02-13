#!/usr/bin/env python3
"""
Test for phone reprovisioning bug fix

Tests that when a phone (IP/MAC) is reprovisioned to a different extension,
the old extension-IP-MAC mapping is properly removed from the registered_phones table.

Bug: If an IP/MAC has been reprovisioned to a different extension, the old extension,
IP and MAC mapping persists in the table, causing duplicate entries.
"""


from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB


def test_phone_reprovisioning_removes_old_mapping() -> None:
    """
    Test that reprovisioning a phone to a new extension removes the old mapping

    Scenario:
    1. Phone with MAC 001122334455 and IP 192.168.1.100 registers to extension 1001
    2. Same phone (same MAC/IP) registers to extension 1002
    3. Old mapping (ext 1001 -> MAC/IP) should be deleted
    4. Only new mapping (ext 1002 -> MAC/IP) should exist
    """

    # Create database backend (using SQLite for tests)
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Step 1: Register phone to extension 1001
    success, _ = phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address="001122334455",
        user_agent="Yealink SIP-T46S",
    )
    assert success, "Initial registration failed"

    # Verify phone is registered to extension 1001
    phone = phones_db.get_by_mac("001122334455")
    assert phone is not None, "Phone not found after initial registration"
    assert phone["extension_number"] == "1001", "Phone should be on extension 1001"

    phones_ext_1001 = phones_db.get_by_extension("1001")
    assert len(phones_ext_1001) == 1, "Extension 1001 should have 1 phone"

    # Step 2: Reprovision same phone to extension 1002
    success, _ = phones_db.register_phone(
        extension_number="1002",
        ip_address="192.168.1.100",  # Same IP
        mac_address="001122334455",  # Same MAC
        user_agent="Yealink SIP-T46S",
    )
    assert success, "Reprovisioning registration failed"

    # Step 3: Verify old mapping is removed
    phones_ext_1001 = phones_db.get_by_extension("1001")
    assert (
        len(phones_ext_1001) == 0
    ), f"Extension 1001 should have 0 phones, but has {len(phones_ext_1001)}"

    # Step 4: Verify new mapping exists
    phones_ext_1002 = phones_db.get_by_extension("1002")
    assert (
        len(phones_ext_1002) == 1
    ), f"Extension 1002 should have 1 phone, but has {len(phones_ext_1002)}"
    assert phones_ext_1002[0]["mac_address"] == "001122334455", "Wrong MAC on extension 1002"
    assert phones_ext_1002[0]["ip_address"] == "192.168.1.100", "Wrong IP on extension 1002"

    # Step 5: Verify no duplicate entries for this MAC/IP
    all_phones = phones_db.list_all()
    mac_count = sum(1 for p in all_phones if p["mac_address"] == "001122334455")
    assert mac_count == 1, f"Expected 1 entry for MAC, found {mac_count} (duplicate entries exist!)"

    ip_count = sum(1 for p in all_phones if p["ip_address"] == "192.168.1.100")
    assert ip_count == 1, f"Expected 1 entry for IP, found {ip_count} (duplicate entries exist!)"


def test_phone_reprovisioning_by_ip_only() -> None:
    """
    Test reprovisioning when phone has no MAC address (IP-based tracking)
    """

    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Register phone without MAC to extension 1003
    success, _ = phones_db.register_phone(
        extension_number="1003",
        ip_address="192.168.1.103",
        mac_address=None,  # No MAC
        user_agent="Generic SIP Phone",
    )
    assert success, "Initial registration failed"

    # Verify registration
    phones_ext_1003 = phones_db.get_by_extension("1003")
    assert len(phones_ext_1003) == 1, "Extension 1003 should have 1 phone"

    # Reprovision same IP to extension 1004
    success, _ = phones_db.register_phone(
        extension_number="1004",
        ip_address="192.168.1.103",  # Same IP
        mac_address=None,  # Still no MAC
        user_agent="Generic SIP Phone",
    )
    assert success, "Reprovisioning failed"

    # Verify old mapping removed
    phones_ext_1003 = phones_db.get_by_extension("1003")
    assert len(phones_ext_1003) == 0, "Extension 1003 should have 0 phones after reprovisioning"

    # Verify new mapping exists
    phones_ext_1004 = phones_db.get_by_extension("1004")
    assert len(phones_ext_1004) == 1, "Extension 1004 should have 1 phone"
    assert phones_ext_1004[0]["ip_address"] == "192.168.1.103", "Wrong IP on extension 1004"

    # No duplicates
    all_phones = phones_db.list_all()
    ip_count = sum(1 for p in all_phones if p["ip_address"] == "192.168.1.103")
    assert ip_count == 1, f"Expected 1 entry for IP, found {ip_count}"


def test_phone_reprovisioning_with_mac_then_ip() -> None:
    """
    Test reprovisioning when phone has MAC initially but then registers with IP only
    """

    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Register phone with MAC to extension 1005
    success, _ = phones_db.register_phone(
        extension_number="1005",
        ip_address="192.168.1.105",
        mac_address="AABBCCDDEE11",
        user_agent="Yealink Phone",
    )
    assert success, "Initial registration failed"

    # Reprovision to extension 1006, but this time without MAC (phone didn't
    # send it)
    success, _ = phones_db.register_phone(
        extension_number="1006",
        ip_address="192.168.1.105",  # Same IP
        mac_address=None,  # No MAC this time
        user_agent="Yealink Phone",
    )
    assert success, "Reprovisioning failed"

    # Old extension should have no phones
    phones_ext_1005 = phones_db.get_by_extension("1005")
    assert len(phones_ext_1005) == 0, "Extension 1005 should have 0 phones"

    # New extension should have the phone
    phones_ext_1006 = phones_db.get_by_extension("1006")
    assert len(phones_ext_1006) == 1, "Extension 1006 should have 1 phone"

    # No duplicates
    all_phones = phones_db.list_all()
    ip_count = sum(1 for p in all_phones if p["ip_address"] == "192.168.1.105")
    assert ip_count == 1, f"Expected 1 entry for IP, found {ip_count}"


def test_multiple_phones_different_extensions() -> None:
    """
    Test that different phones can still register to different extensions (normal case)
    """

    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Register three different phones to three different extensions
    phones_db.register_phone("2001", "192.168.1.201", "AAAAAAAAAAAA")
    phones_db.register_phone("2002", "192.168.1.202", "BBBBBBBBBBBB")
    phones_db.register_phone("2003", "192.168.1.203", "CCCCCCCCCCCC")

    # All should exist independently
    all_phones = phones_db.list_all()
    assert len(all_phones) == 3, f"Expected 3 phones, got {len(all_phones)}"

    # Each extension should have exactly one phone
    assert len(phones_db.get_by_extension("2001")) == 1, "Extension 2001 should have 1 phone"
    assert len(phones_db.get_by_extension("2002")) == 1, "Extension 2002 should have 1 phone"
    assert len(phones_db.get_by_extension("2003")) == 1, "Extension 2003 should have 1 phone"
