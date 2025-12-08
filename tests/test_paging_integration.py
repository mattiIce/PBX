#!/usr/bin/env python3
"""
Test paging system integration with PBX core
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.paging import PagingSystem
from pbx.utils.config import Config


def test_paging_system_initialization():
    """Test paging system initialization"""
    print("Testing paging system initialization...")
    
    # Create a mock config object with proper structure
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.paging.enabled': True,
                'features.paging.prefix': '7',
                'features.paging.all_call_extension': '700',
                'features.paging.zones': [
                    {
                        'extension': '701',
                        'name': 'Zone 1 - Office',
                        'description': 'Main office area',
                        'dac_device': 'test-device-1'
                    },
                    {
                        'extension': '702',
                        'name': 'Zone 2 - Warehouse',
                        'description': 'Warehouse area',
                        'dac_device': 'test-device-1'
                    }
                ],
                'features.paging.dac_type': 'sip_gateway',
                'features.paging.dac_devices': [
                    {
                        'device_id': 'test-device-1',
                        'device_type': 'cisco_vg224',
                        'sip_uri': 'sip:paging@192.168.1.100:5060',
                        'ip_address': '192.168.1.100',
                        'port': 5060
                    }
                ]
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    paging = PagingSystem(config)
    
    assert paging.enabled == True, "Paging should be enabled"
    assert paging.paging_prefix == '7', "Paging prefix should be '7'"
    assert paging.all_call_extension == '700', "All-call extension should be '700'"
    assert len(paging.zones) == 2, "Should have 2 zones"
    assert len(paging.dac_devices) == 1, "Should have 1 DAC device"
    
    print("✓ Paging system initialization works")
    return True


def test_paging_extension_detection():
    """Test paging extension detection"""
    print("\nTesting paging extension detection...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.paging.enabled': True,
                'features.paging.prefix': '7',
                'features.paging.all_call_extension': '700',
                'features.paging.zones': [
                    {'extension': '701', 'name': 'Zone 1'}
                ],
                'features.paging.dac_type': 'sip_gateway',
                'features.paging.dac_devices': []
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    paging = PagingSystem(config)
    
    # Test paging extensions
    assert paging.is_paging_extension('700') == True, "700 should be paging extension"
    assert paging.is_paging_extension('701') == True, "701 should be paging extension"
    assert paging.is_paging_extension('702') == True, "702 should be paging extension"
    
    # Test non-paging extensions
    assert paging.is_paging_extension('1001') == False, "1001 should not be paging extension"
    assert paging.is_paging_extension('8001') == False, "8001 should not be paging extension"
    
    print("✓ Paging extension detection works")
    return True


def test_zone_management():
    """Test zone management"""
    print("\nTesting zone management...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.paging.enabled': True,
                'features.paging.prefix': '7',
                'features.paging.all_call_extension': '700',
                'features.paging.zones': [],
                'features.paging.dac_type': 'sip_gateway',
                'features.paging.dac_devices': []
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    paging = PagingSystem(config)
    
    # Add a zone
    success = paging.add_zone(
        extension='701',
        name='Test Zone',
        description='Test zone description',
        dac_device='test-device'
    )
    assert success == True, "Should successfully add zone"
    assert len(paging.zones) == 1, "Should have 1 zone"
    
    # Get zone by extension
    zone = paging.get_zone_for_extension('701')
    assert zone is not None, "Should find zone"
    assert zone['name'] == 'Test Zone', "Zone name should match"
    
    # Try to add duplicate zone
    success = paging.add_zone(
        extension='701',
        name='Duplicate Zone',
        description='Should fail'
    )
    assert success == False, "Should not add duplicate zone"
    
    # Remove zone
    success = paging.remove_zone('701')
    assert success == True, "Should successfully remove zone"
    assert len(paging.zones) == 0, "Should have 0 zones"
    
    # Try to remove non-existent zone
    success = paging.remove_zone('999')
    assert success == False, "Should not remove non-existent zone"
    
    print("✓ Zone management works")
    return True


def test_page_initiation():
    """Test page initiation"""
    print("\nTesting page initiation...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.paging.enabled': True,
                'features.paging.prefix': '7',
                'features.paging.all_call_extension': '700',
                'features.paging.zones': [
                    {
                        'extension': '701',
                        'name': 'Zone 1',
                        'dac_device': 'test-device'
                    }
                ],
                'features.paging.dac_type': 'sip_gateway',
                'features.paging.dac_devices': []
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    paging = PagingSystem(config)
    
    # Initiate a page to specific zone
    page_id = paging.initiate_page('1001', '701')
    assert page_id is not None, "Should return page ID"
    assert page_id.startswith('page-'), "Page ID should start with 'page-'"
    
    # Check active pages
    active_pages = paging.get_active_pages()
    assert len(active_pages) == 1, "Should have 1 active page"
    assert active_pages[0]['from_extension'] == '1001', "From extension should match"
    assert active_pages[0]['to_extension'] == '701', "To extension should match"
    
    # Get page info
    page_info = paging.get_page_info(page_id)
    assert page_info is not None, "Should get page info"
    assert page_info['zone_names'] == 'Zone 1', "Zone name should match"
    
    # End the page
    success = paging.end_page(page_id)
    assert success == True, "Should successfully end page"
    assert len(paging.get_active_pages()) == 0, "Should have 0 active pages"
    
    print("✓ Page initiation works")
    return True


def test_all_call_paging():
    """Test all-call paging"""
    print("\nTesting all-call paging...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.paging.enabled': True,
                'features.paging.prefix': '7',
                'features.paging.all_call_extension': '700',
                'features.paging.zones': [
                    {'extension': '701', 'name': 'Zone 1'},
                    {'extension': '702', 'name': 'Zone 2'},
                    {'extension': '703', 'name': 'Zone 3'}
                ],
                'features.paging.dac_type': 'sip_gateway',
                'features.paging.dac_devices': []
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    paging = PagingSystem(config)
    
    # Initiate all-call page
    page_id = paging.initiate_page('1001', '700')
    assert page_id is not None, "Should return page ID for all-call"
    
    # Get page info
    page_info = paging.get_page_info(page_id)
    assert page_info is not None, "Should get page info"
    assert page_info['zone_names'] == 'All Zones', "Should be all zones"
    assert len(page_info['zones']) == 3, "Should include all 3 zones"
    
    # End the page
    paging.end_page(page_id)
    
    print("✓ All-call paging works")
    return True


def test_dac_device_configuration():
    """Test DAC device configuration"""
    print("\nTesting DAC device configuration...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.paging.enabled': True,
                'features.paging.prefix': '7',
                'features.paging.all_call_extension': '700',
                'features.paging.zones': [],
                'features.paging.dac_type': 'sip_gateway',
                'features.paging.dac_devices': []
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    paging = PagingSystem(config)
    
    # Configure a DAC device
    success = paging.configure_dac_device(
        device_id='gateway-1',
        device_type='cisco_vg224',
        sip_uri='sip:paging@192.168.1.100',
        ip_address='192.168.1.100',
        port=5060
    )
    assert success == True, "Should successfully configure device"
    assert len(paging.dac_devices) == 1, "Should have 1 device"
    
    # Get devices
    devices = paging.get_dac_devices()
    assert len(devices) == 1, "Should return 1 device"
    assert devices[0]['device_id'] == 'gateway-1', "Device ID should match"
    assert devices[0]['device_type'] == 'cisco_vg224', "Device type should match"
    
    # Try to add duplicate device
    success = paging.configure_dac_device(
        device_id='gateway-1',
        device_type='grandstream_ht802',
        ip_address='192.168.1.101'
    )
    assert success == False, "Should not add duplicate device"
    
    print("✓ DAC device configuration works")
    return True


def test_paging_disabled():
    """Test paging system when disabled"""
    print("\nTesting paging system when disabled...")
    
    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.paging.enabled': False
            }
            return config_map.get(key, default)
    
    config = MockConfig()
    paging = PagingSystem(config)
    
    assert paging.enabled == False, "Paging should be disabled"
    assert paging.is_paging_extension('700') == False, "Should not detect paging extensions"
    assert paging.initiate_page('1001', '700') is None, "Should not initiate page"
    assert len(paging.get_zones()) == 0, "Should return empty zones"
    
    print("✓ Paging disabled state works")
    return True


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Testing Paging System Integration")
    print("=" * 70)
    
    results = []
    results.append(test_paging_system_initialization())
    results.append(test_paging_extension_detection())
    results.append(test_zone_management())
    results.append(test_page_initiation())
    results.append(test_all_call_paging())
    results.append(test_dac_device_configuration())
    results.append(test_paging_disabled())
    
    print("\n" + "=" * 70)
    if all(results):
        print(f"✅ All paging tests passed! ({len(results)}/{len(results)})")
        return True
    else:
        print(f"❌ Some tests failed ({sum(results)}/{len(results)} passed)")
        return False



if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
