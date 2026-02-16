#!/usr/bin/env python3
"""
Tests for Phone Book and Paging features
"""

from pbx.features.paging import PagingSystem
from pbx.features.phone_book import PhoneBook


def test_phone_book_basic() -> None:
    """Test basic phone book operations"""

    # Create a phone book with minimal config
    config = {"features.phone_book.enabled": True, "features.phone_book.auto_sync_from_ad": False}

    phone_book = PhoneBook(config, database=None)

    # Test add entry
    success = phone_book.add_entry(
        extension="1001", name="John Doe", department="Sales", email="john@example.com"
    )
    assert success, "Failed to add phone book entry"

    # Test get entry
    entry = phone_book.get_entry("1001")
    assert entry is not None, "Failed to get phone book entry"
    assert entry["name"] == "John Doe", "Name mismatch"
    assert entry["department"] == "Sales", "Department mismatch"

    # Test get all entries
    entries = phone_book.get_all_entries()
    assert len(entries) == 1, "Should have one entry"

    # Test search
    results = phone_book.search("John")
    assert len(results) == 1, "Search should find one result"
    assert results[0]["name"] == "John Doe", "Search result mismatch"

    # Test remove entry
    success = phone_book.remove_entry("1001")
    assert success, "Failed to remove phone book entry"

    entry = phone_book.get_entry("1001")
    assert entry is None, "Entry should be removed"


def test_phone_book_export() -> None:
    """Test phone book export formats"""

    config = {"features.phone_book.enabled": True, "features.phone_book.auto_sync_from_ad": False}

    phone_book = PhoneBook(config, database=None)

    # Add some entries
    phone_book.add_entry("1001", "Alice Smith", email="alice@example.com")
    phone_book.add_entry("1002", "Bob Johnson", email="bob@example.com")
    phone_book.add_entry("1003", "Charlie Brown", email="charlie@example.com")

    # Test XML export (Yealink)
    xml_output = phone_book.export_xml()
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_output, "XML header missing"
    assert "<YealinkIPPhoneDirectory>" in xml_output, "Yealink root element missing"
    assert "<Name>Alice Smith</Name>" in xml_output, "Entry not in XML"
    assert "<Telephone>1001</Telephone>" in xml_output, "Extension not in XML"

    # Test Cisco XML export
    cisco_xml = phone_book.export_cisco_xml()
    assert "<CiscoIPPhoneDirectory>" in cisco_xml, "Cisco root element missing"
    assert "<Name>Bob Johnson</Name>" in cisco_xml, "Entry not in Cisco XML"

    # Test JSON export
    json_output = phone_book.export_json()
    assert '"extension": "1001"' in json_output or '"extension":"1001"' in json_output, (
        "Extension not in JSON"
    )
    assert '"name": "Alice Smith"' in json_output or '"name":"Alice Smith"' in json_output, (
        "Name not in JSON"
    )


def test_paging_system_basic() -> None:
    """Test basic paging system operations"""

    config = {
        "features.paging.enabled": True,
        "features.paging.prefix": "7",
        "features.paging.all_call_extension": "700",
        "features.paging.zones": [],
    }

    paging_system = PagingSystem(config, database=None)

    # Test is_paging_extension
    assert paging_system.is_paging_extension("700"), "All-call should be paging extension"
    assert paging_system.is_paging_extension("701"), "7xx should be paging extension"
    assert not paging_system.is_paging_extension("1001"), "1001 should not be paging extension"

    # Test add zone
    success = paging_system.add_zone(
        extension="701", name="Zone 1 - Office", description="Main office area"
    )
    assert success, "Failed to add paging zone"

    # Test get zone
    zone = paging_system.get_zone_for_extension("701")
    assert zone is not None, "Failed to get zone"
    assert zone["name"] == "Zone 1 - Office", "Zone name mismatch"

    # Test get all zones
    zones = paging_system.get_zones()
    assert len(zones) == 1, "Should have one zone"

    # Test remove zone
    success = paging_system.remove_zone("701")
    assert success, "Failed to remove zone"

    zones = paging_system.get_zones()
    assert len(zones) == 0, "Should have no zones"


def test_paging_system_devices() -> None:
    """Test paging system DAC device configuration"""

    config = {
        "features.paging.enabled": True,
        "features.paging.prefix": "7",
        "features.paging.all_call_extension": "700",
        "features.paging.zones": [],
        "features.paging.dac_devices": [],
    }

    paging_system = PagingSystem(config, database=None)

    # Test configure DAC device
    success = paging_system.configure_dac_device(
        device_id="paging-gateway-1",
        device_type="cisco_vg224",
        sip_uri="sip:paging@192.168.1.100:5060",
        ip_address="192.168.1.100",
        port=5060,
    )
    assert success, "Failed to configure DAC device"

    # Test get DAC devices
    devices = paging_system.get_dac_devices()
    assert len(devices) == 1, "Should have one device"
    assert devices[0]["device_id"] == "paging-gateway-1", "Device ID mismatch"
    assert devices[0]["device_type"] == "cisco_vg224", "Device type mismatch"


def test_phone_book_disabled() -> None:
    """Test phone book when disabled"""

    config = {"features.phone_book.enabled": False}

    phone_book = PhoneBook(config, database=None)

    # All operations should return False/empty when disabled
    assert not phone_book.add_entry("1001", "Test"), "Should fail when disabled"
    assert phone_book.get_entry("1001") is None, "Should return None when disabled"
    assert phone_book.get_all_entries() == [], "Should return empty list when disabled"


def test_paging_system_disabled() -> None:
    """Test paging system when disabled"""

    config = {"features.paging.enabled": False}

    paging_system = PagingSystem(config, database=None)

    # All operations should return False/empty when disabled
    assert not paging_system.is_paging_extension("700"), "Should return False when disabled"
    assert not paging_system.add_zone("701", "Test"), "Should fail when disabled"
    assert paging_system.get_zones() == [], "Should return empty list when disabled"
