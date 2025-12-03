#!/usr/bin/env python3
"""
Tests for phone provisioning system
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.phone_provisioning import PhoneProvisioning, ProvisioningDevice, PhoneTemplate
from pbx.features.extensions import ExtensionRegistry
from pbx.utils.config import Config


def test_device_mac_normalization():
    """Test MAC address normalization"""
    print("Testing MAC address normalization...")
    
    # Test various MAC formats
    device1 = ProvisioningDevice("00:15:65:12:34:56", "1001", "yealink", "t46s")
    device2 = ProvisioningDevice("00-15-65-12-34-56", "1001", "yealink", "t46s")
    device3 = ProvisioningDevice("0015.6512.3456", "1001", "yealink", "t46s")
    device4 = ProvisioningDevice("001565123456", "1001", "yealink", "t46s")
    
    # All should normalize to the same format
    expected = "001565123456"
    assert device1.mac_address == expected, f"Expected {expected}, got {device1.mac_address}"
    assert device2.mac_address == expected, f"Expected {expected}, got {device2.mac_address}"
    assert device3.mac_address == expected, f"Expected {expected}, got {device3.mac_address}"
    assert device4.mac_address == expected, f"Expected {expected}, got {device4.mac_address}"
    
    print("✓ MAC address normalization works")


def test_phone_template():
    """Test phone template configuration generation"""
    print("Testing phone template...")
    
    template_content = """account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
"""
    
    template = PhoneTemplate("yealink", "t46s", template_content)
    
    extension_config = {
        'number': '1001',
        'name': 'Test User',
        'password': 'testpass123'
    }
    
    server_config = {
        'sip_host': '192.168.1.100',
        'sip_port': 5060,
        'server_name': 'TestPBX'
    }
    
    config = template.generate_config(extension_config, server_config)
    
    # Check that placeholders were replaced
    assert '{{EXTENSION_NUMBER}}' not in config, "Extension number placeholder not replaced"
    assert '1001' in config, "Extension number not in config"
    assert 'testpass123' in config, "Password not in config"
    assert '192.168.1.100' in config, "SIP server not in config"
    assert '5060' in config, "SIP port not in config"
    
    print("✓ Phone template works")


def test_provisioning_device_registration():
    """Test device registration"""
    print("Testing device registration...")
    
    # Create a minimal config
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)
    
    # Register a device
    device = provisioning.register_device(
        "00:15:65:12:34:56",
        "1001",
        "zip",
        "33g"
    )
    
    assert device is not None, "Device registration failed"
    assert device.mac_address == "001565123456", f"Unexpected MAC: {device.mac_address}"
    assert device.extension_number == "1001", f"Unexpected extension: {device.extension_number}"
    assert device.vendor == "zip", f"Unexpected vendor: {device.vendor}"
    assert device.model == "33g", f"Unexpected model: {device.model}"
    
    # Retrieve the device
    retrieved = provisioning.get_device("00:15:65:12:34:56")
    assert retrieved is not None, "Device retrieval failed"
    assert retrieved.mac_address == device.mac_address
    
    # Unregister the device
    success = provisioning.unregister_device("00:15:65:12:34:56")
    assert success, "Device unregistration failed"
    
    # Verify it's gone
    retrieved = provisioning.get_device("00:15:65:12:34:56")
    assert retrieved is None, "Device still exists after unregistration"
    
    print("✓ Device registration works")


def test_supported_vendors_and_models():
    """Test supported vendors and models"""
    print("Testing supported vendors and models...")
    
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)
    
    # Get supported vendors
    vendors = provisioning.get_supported_vendors()
    assert len(vendors) > 0, "No vendors found"
    assert 'zip' in vendors, "ZIP not in vendors"
    
    # Get models for ZIP
    zip_models = provisioning.get_supported_models('zip')
    assert len(zip_models) > 0, "No ZIP models found"
    assert '33g' in zip_models, "33G not in ZIP models"
    assert '37g' in zip_models, "37G not in ZIP models"
    
    # Get all models
    all_models = provisioning.get_supported_models()
    assert isinstance(all_models, dict), "Expected dict for all models"
    assert 'zip' in all_models, "ZIP not in all models"
    assert len(all_models['zip']) == 2, f"Expected 2 ZIP models, got {len(all_models['zip'])}"
    
    print("✓ Supported vendors and models work")


def test_builtin_templates():
    """Test that built-in templates exist"""
    print("Testing built-in templates...")
    
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)
    
    # Check ZIP 33G template
    zip_33g_template = provisioning.get_template('zip', '33g')
    assert zip_33g_template is not None, "ZIP 33G template not found"
    
    # Check ZIP 37G template
    zip_37g_template = provisioning.get_template('zip', '37g')
    assert zip_37g_template is not None, "ZIP 37G template not found"
    
    print("✓ Built-in templates exist")


def test_config_generation():
    """Test configuration generation"""
    print("Testing configuration generation...")
    
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)
    extension_registry = ExtensionRegistry(config)
    
    # Register a device for extension 1001
    device = provisioning.register_device(
        "00:15:65:12:34:56",
        "1001",
        "zip",
        "33g"
    )
    
    # Generate configuration
    config_content, content_type = provisioning.generate_config(
        "00:15:65:12:34:56",
        extension_registry
    )
    
    assert config_content is not None, "Config generation failed"
    assert content_type == 'text/plain', f"Unexpected content type: {content_type}"
    assert '1001' in config_content, "Extension number not in config"
    assert 'password1001' in config_content, "Password not in config"
    
    # Check that device was marked as provisioned
    assert device.last_provisioned is not None, "Device not marked as provisioned"
    
    print("✓ Configuration generation works")


if __name__ == "__main__":
    print("=" * 60)
    print("Running Phone Provisioning Tests")
    print("=" * 60)
    
    try:
        test_device_mac_normalization()
        test_phone_template()
        test_provisioning_device_registration()
        test_supported_vendors_and_models()
        test_builtin_templates()
        test_config_generation()
        
        print("=" * 60)
        print("Results: 6 passed, 0 failed")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
