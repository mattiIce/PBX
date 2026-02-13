#!/usr/bin/env python3
"""
Test for periodic device re-registration scenario

This test simulates the real-world issue where phones re-register
every X amount of time (e.g., every 60 seconds), and may not always
send the MAC address in every REGISTER message.

Tests that the system properly checks the table first and preserves
existing MAC, IP, and extension information instead of stripping/losing it.
"""


from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB


def test_periodic_reregistration_preserves_data() -> None:
    """
    Test that periodic re-registration preserves data

    Simulates a phone that:
    1. Registers initially with full information (MAC, IP, extension)
    2. Re-registers after 60 seconds without MAC
    3. Re-registers again with MAC
    4. Re-registers without MAC again

    The system should preserve all information throughout.
    """

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Simulate initial registration at time T=0
    _ = phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address="001565123456",
        user_agent="Yealink SIP-T46S 66.85.0.5",
        contact_uri="<sip:1001@192.168.1.100:5060;mac=00:15:65:12:34:56>",
    )

    # Verify initial registration
    phone = phones_db.get_by_ip("192.168.1.100", "1001")
    assert phone is not None, "Phone not found after initial registration"
    assert phone["mac_address"] == "001565123456", "MAC not stored"
    assert phone["extension_number"] == "1001", "Extension not stored"
    assert phone["ip_address"] == "192.168.1.100", "IP not stored"

    # Simulate re-registration at T=60s (phone doesn't send MAC this time)
    _ = phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address=None,  # Phone doesn't include MAC in this REGISTER
        user_agent="Yealink SIP-T46S 66.85.0.5",
        contact_uri="<sip:1001@192.168.1.100:5060>",  # No MAC in Contact
    )

    # Verify MAC was preserved
    phone = phones_db.get_by_ip("192.168.1.100", "1001")
    assert phone is not None, "Phone not found after re-registration"
    assert phone["mac_address"] == "001565123456", "MAC was lost! Should be preserved"
    assert phone["extension_number"] == "1001", "Extension changed"
    assert phone["ip_address"] == "192.168.1.100", "IP changed"

    # Simulate re-registration at T=120s (phone sends MAC again)
    _ = phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address="001565123456",
        user_agent="Yealink SIP-T46S 66.85.0.5",
        contact_uri="<sip:1001@192.168.1.100:5060;mac=00:15:65:12:34:56>",
    )

    # Verify all data is still correct
    phone = phones_db.get_by_ip("192.168.1.100", "1001")
    assert phone is not None, "Phone not found"
    assert phone["mac_address"] == "001565123456", "MAC incorrect"

    # Simulate re-registration at T=180s (no MAC again)
    _ = phones_db.register_phone(
        extension_number="1001",
        ip_address="192.168.1.100",
        mac_address=None,
        user_agent="Yealink SIP-T46S 66.85.0.5",
        contact_uri="<sip:1001@192.168.1.100:5060>",
    )

    # Verify MAC still preserved
    phone = phones_db.get_by_ip("192.168.1.100", "1001")
    assert phone is not None, "Phone not found"
    assert phone["mac_address"] == "001565123456", "MAC was lost again!"

    # Verify we only have ONE record (not multiple duplicate entries)
    all_phones = phones_db.get_by_extension("1001")
    assert (
        len(all_phones) == 1
    ), f"Expected 1 phone record, got {len(all_phones)}"


def test_multiple_phones_reregistering() -> None:
    """
    Test multiple phones re-registering with varying MAC availability
    """

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Register three phones initially
    _ = phones_db.register_phone("1001", "192.168.1.100", "001565111111", "Yealink T46S")
    _ = phones_db.register_phone("1002", "192.168.1.101", "001565222222", "Polycom VVX")
    _ = phones_db.register_phone("1003", "192.168.1.102", "001565333333", "Cisco SPA")

    # Phone 1 re-registers with MAC
    _ = phones_db.register_phone("1001", "192.168.1.100", "001565111111", "Yealink T46S")
    # Phone 2 re-registers without MAC
    _ = phones_db.register_phone("1002", "192.168.1.101", None, "Polycom VVX")
    # Phone 3 re-registers without MAC
    _ = phones_db.register_phone("1003", "192.168.1.102", None, "Cisco SPA")


    # Verify all MACs preserved
    phone1 = phones_db.get_by_ip("192.168.1.100", "1001")
    phone2 = phones_db.get_by_ip("192.168.1.101", "1002")
    phone3 = phones_db.get_by_ip("192.168.1.102", "1003")

    assert phone1["mac_address"] == "001565111111", "Phone 1 MAC lost"
    assert phone2["mac_address"] == "001565222222", "Phone 2 MAC lost"
    assert phone3["mac_address"] == "001565333333", "Phone 3 MAC lost"
