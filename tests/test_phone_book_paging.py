#!/usr/bin/env python3
"""
Tests for Phone Book and Paging features
"""
import os
import sys

from pbx.features.paging import PagingSystem
from pbx.features.phone_book import PhoneBook

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_phone_book_basic():
    """Test basic phone book operations"""
    print("Testing phone book basic operations...")

    # Create a phone book with minimal config
    config = {
        'features.phone_book.enabled': True,
        'features.phone_book.auto_sync_from_ad': False
    }

    phone_book = PhoneBook(config, database=None)

    # Test add entry
    success = phone_book.add_entry(
        extension="1001",
        name="John Doe",
        department="Sales",
        email="john@example.com"
    )
    assert success, "Failed to add phone book entry"

    # Test get entry
    entry = phone_book.get_entry("1001")
    assert entry is not None, "Failed to get phone book entry"
    assert entry['name'] == "John Doe", "Name mismatch"
    assert entry['department'] == "Sales", "Department mismatch"

    # Test get all entries
    entries = phone_book.get_all_entries()
    assert len(entries) == 1, "Should have one entry"

    # Test search
    results = phone_book.search("John")
    assert len(results) == 1, "Search should find one result"
    assert results[0]['name'] == "John Doe", "Search result mismatch"

    # Test remove entry
    success = phone_book.remove_entry("1001")
    assert success, "Failed to remove phone book entry"

    entry = phone_book.get_entry("1001")
    assert entry is None, "Entry should be removed"

    print("✓ Phone book basic operations passed")


def test_phone_book_export():
    """Test phone book export formats"""
    print("Testing phone book export formats...")

    config = {
        'features.phone_book.enabled': True,
        'features.phone_book.auto_sync_from_ad': False
    }

    phone_book = PhoneBook(config, database=None)

    # Add some entries
    phone_book.add_entry("1001", "Alice Smith", email="alice@example.com")
    phone_book.add_entry("1002", "Bob Johnson", email="bob@example.com")
    phone_book.add_entry("1003", "Charlie Brown", email="charlie@example.com")

    # Test XML export (Yealink)
    xml_output = phone_book.export_xml()
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_output, "XML header missing"
    assert '<YealinkIPPhoneDirectory>' in xml_output, "Yealink root element missing"
    assert '<Name>Alice Smith</Name>' in xml_output, "Entry not in XML"
    assert '<Telephone>1001</Telephone>' in xml_output, "Extension not in XML"

    # Test Cisco XML export
    cisco_xml = phone_book.export_cisco_xml()
    assert '<CiscoIPPhoneDirectory>' in cisco_xml, "Cisco root element missing"
    assert '<Name>Bob Johnson</Name>' in cisco_xml, "Entry not in Cisco XML"

    # Test JSON export
    json_output = phone_book.export_json()
    assert '"extension": "1001"' in json_output or '"extension":"1001"' in json_output, "Extension not in JSON"
    assert '"name": "Alice Smith"' in json_output or '"name":"Alice Smith"' in json_output, "Name not in JSON"

    print("✓ Phone book export formats passed")


def test_paging_system_basic():
    """Test basic paging system operations"""
    print("Testing paging system basic operations...")

    config = {
        'features.paging.enabled': True,
        'features.paging.prefix': '7',
        'features.paging.all_call_extension': '700',
        'features.paging.zones': []
    }

    paging_system = PagingSystem(config, database=None)

    # Test is_paging_extension
    assert paging_system.is_paging_extension(
        '700'), "All-call should be paging extension"
    assert paging_system.is_paging_extension(
        '701'), "7xx should be paging extension"
    assert not paging_system.is_paging_extension(
        '1001'), "1001 should not be paging extension"

    # Test add zone
    success = paging_system.add_zone(
        extension="701",
        name="Zone 1 - Office",
        description="Main office area"
    )
    assert success, "Failed to add paging zone"

    # Test get zone
    zone = paging_system.get_zone_for_extension("701")
    assert zone is not None, "Failed to get zone"
    assert zone['name'] == "Zone 1 - Office", "Zone name mismatch"

    # Test get all zones
    zones = paging_system.get_zones()
    assert len(zones) == 1, "Should have one zone"

    # Test remove zone
    success = paging_system.remove_zone("701")
    assert success, "Failed to remove zone"

    zones = paging_system.get_zones()
    assert len(zones) == 0, "Should have no zones"

    print("✓ Paging system basic operations passed")


def test_paging_system_devices():
    """Test paging system DAC device configuration"""
    print("Testing paging system DAC device configuration...")

    config = {
        'features.paging.enabled': True,
        'features.paging.prefix': '7',
        'features.paging.all_call_extension': '700',
        'features.paging.zones': [],
        'features.paging.dac_devices': []
    }

    paging_system = PagingSystem(config, database=None)

    # Test configure DAC device
    success = paging_system.configure_dac_device(
        device_id="paging-gateway-1",
        device_type="cisco_vg224",
        sip_uri="sip:paging@192.168.1.100:5060",
        ip_address="192.168.1.100",
        port=5060
    )
    assert success, "Failed to configure DAC device"

    # Test get DAC devices
    devices = paging_system.get_dac_devices()
    assert len(devices) == 1, "Should have one device"
    assert devices[0]['device_id'] == "paging-gateway-1", "Device ID mismatch"
    assert devices[0]['device_type'] == "cisco_vg224", "Device type mismatch"

    print("✓ Paging system DAC device configuration passed")


def test_phone_book_disabled():
    """Test phone book when disabled"""
    print("Testing phone book when disabled...")

    config = {
        'features.phone_book.enabled': False
    }

    phone_book = PhoneBook(config, database=None)

    # All operations should return False/empty when disabled
    assert not phone_book.add_entry(
        "1001", "Test"), "Should fail when disabled"
    assert phone_book.get_entry(
        "1001") is None, "Should return None when disabled"
    assert phone_book.get_all_entries() == [], "Should return empty list when disabled"

    print("✓ Phone book disabled test passed")


def test_paging_system_disabled():
    """Test paging system when disabled"""
    print("Testing paging system when disabled...")

    config = {
        'features.paging.enabled': False
    }

    paging_system = PagingSystem(config, database=None)

    # All operations should return False/empty when disabled
    assert not paging_system.is_paging_extension(
        '700'), "Should return False when disabled"
    assert not paging_system.add_zone(
        "701", "Test"), "Should fail when disabled"
    assert paging_system.get_zones() == [], "Should return empty list when disabled"

    print("✓ Paging system disabled test passed")


def run_all_tests():
    """Run all tests in this module"""
    print("\nRunning Phone Book and Paging Tests")
    print("=" * 60)

    try:
        test_phone_book_basic()
        test_phone_book_export()
        test_paging_system_basic()
        test_paging_system_devices()
        test_phone_book_disabled()
        test_paging_system_disabled()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
