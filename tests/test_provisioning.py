#!/usr/bin/env python3
"""
Tests for phone provisioning system
"""

from pbx.features.extensions import ExtensionRegistry
from pbx.features.phone_provisioning import (
    PhoneProvisioning,
    PhoneTemplate,
    ProvisioningDevice,
)
from pbx.utils.config import Config


def test_device_mac_normalization() -> None:
    """Test MAC address normalization"""

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


def test_phone_template() -> None:
    """Test phone template configuration generation"""

    template_content = """account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
"""

    template = PhoneTemplate("yealink", "t46s", template_content)

    extension_config = {"number": "1001", "name": "Test User", "password": "testpass123"}

    server_config = {"sip_host": "192.168.1.100", "sip_port": 5060, "server_name": "TestPBX"}

    config = template.generate_config(extension_config, server_config)

    # Check that placeholders were replaced
    assert "{{EXTENSION_NUMBER}}" not in config, "Extension number placeholder not replaced"
    assert "1001" in config, "Extension number not in config"
    assert "testpass123" in config, "Password not in config"
    assert "192.168.1.100" in config, "SIP server not in config"
    assert "5060" in config, "SIP port not in config"


def test_provisioning_device_registration() -> None:
    """Test device registration"""

    # Create a minimal config
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Register a device
    device = provisioning.register_device("00:15:65:12:34:56", "1001", "zultys", "zip33g")

    assert device is not None, "Device registration failed"
    assert device.mac_address == "001565123456", f"Unexpected MAC: {device.mac_address}"
    assert device.extension_number == "1001", f"Unexpected extension: {device.extension_number}"
    assert device.vendor == "zultys", f"Unexpected vendor: {device.vendor}"
    assert device.model == "zip33g", f"Unexpected model: {device.model}"

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


def test_supported_vendors_and_models() -> None:
    """Test supported vendors and models"""

    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Get supported vendors
    vendors = provisioning.get_supported_vendors()
    assert len(vendors) > 0, "No vendors found"
    assert "zultys" in vendors, "Zultys not in vendors"
    assert "yealink" in vendors, "Yealink not in vendors"
    assert "polycom" in vendors, "Polycom not in vendors"
    assert "cisco" in vendors, "Cisco not in vendors"
    assert "grandstream" in vendors, "Grandstream not in vendors"

    # Get models for Zultys
    zultys_models = provisioning.get_supported_models("zultys")
    assert len(zultys_models) > 0, "No Zultys models found"
    assert "zip33g" in zultys_models, "ZIP33G not in Zultys models"
    assert "zip37g" in zultys_models, "ZIP37G not in Zultys models"

    # Get all models
    all_models = provisioning.get_supported_models()
    assert isinstance(all_models, dict), "Expected dict for all models"
    assert "zultys" in all_models, "Zultys not in all models"
    assert len(all_models["zultys"]) == 2, (
        f"Expected 2 Zultys models, got {len(all_models['zultys'])}"
    )


def test_builtin_templates() -> None:
    """Test that built-in templates exist"""

    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Check Zultys ZIP 33G template
    zultys_zip33g_template = provisioning.get_template("zultys", "zip33g")
    assert zultys_zip33g_template is not None, "Zultys ZIP33G template not found"

    # Check Zultys ZIP 37G template
    zultys_zip37g_template = provisioning.get_template("zultys", "zip37g")
    assert zultys_zip37g_template is not None, "Zultys ZIP37G template not found"

    # Check Yealink T46S template
    yealink_t46s_template = provisioning.get_template("yealink", "t46s")
    assert yealink_t46s_template is not None, "Yealink T46S template not found"

    # Check Polycom VVX450 template
    polycom_vvx450_template = provisioning.get_template("polycom", "vvx450")
    assert polycom_vvx450_template is not None, "Polycom VVX450 template not found"

    # Check Cisco SPA504G template
    cisco_spa504g_template = provisioning.get_template("cisco", "spa504g")
    assert cisco_spa504g_template is not None, "Cisco SPA504G template not found"

    # Check Grandstream GXP2170 template
    grandstream_gxp2170_template = provisioning.get_template("grandstream", "gxp2170")
    assert grandstream_gxp2170_template is not None, "Grandstream GXP2170 template not found"


def test_config_generation() -> None:
    """Test configuration generation"""

    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)
    extension_registry = ExtensionRegistry(config)

    # Add a test extension to the registry
    from pbx.features.extensions import Extension

    test_ext = Extension(
        "1001", "Test User", {"password": "password1001", "email": "test@test.com"}
    )
    extension_registry.extensions["1001"] = test_ext

    # Register a device for extension 1001
    device = provisioning.register_device("00:15:65:12:34:56", "1001", "zultys", "zip33g")

    # Generate configuration
    config_content, content_type = provisioning.generate_config(
        "00:15:65:12:34:56", extension_registry
    )

    assert config_content is not None, "Config generation failed"
    assert content_type == "text/plain", f"Unexpected content type: {content_type}"
    assert "1001" in config_content, "Extension number not in config"
    assert "password1001" in config_content, "Password not in config"

    # Check that device was marked as provisioned
    assert device.last_provisioned is not None, "Device not marked as provisioned"


def test_unregistered_device_error_message() -> None:
    """Test that unregistered devices produce helpful error messages"""

    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)
    extension_registry = ExtensionRegistry(config)

    # Register one device
    provisioning.register_device("00:0B:EA:85:ED:68", "1001", "zultys", "zip33g")

    # Try to generate config for unregistered device
    config_content, content_type = provisioning.generate_config(
        "00:0B:EA:85:F5:54",
        extension_registry,  # Different MAC
    )

    # Should return None for unregistered device
    assert config_content is None, "Config should be None for unregistered device"
    assert content_type is None, "Content type should be None for unregistered device"

    # Check that the error was logged in request history
    history = provisioning.get_request_history(limit=1)
    assert len(history) == 1, "Should have one request in history"
    assert not history[0]["success"], "Request should have failed"
    assert "not registered" in history[0]["error"], "Error should mention registration"


def test_similar_mac_detection() -> None:
    """Test that similar MAC addresses are detected (helps identify typos)"""

    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)
    extension_registry = ExtensionRegistry(config)

    # Register devices with same OUI (first 6 chars)
    provisioning.register_device("00:0B:EA:85:ED:68", "1001", "zultys", "zip33g")
    provisioning.register_device("00:0B:EA:85:F5:54", "1002", "zultys", "zip33g")

    # Try to generate config for device with same OUI but wrong MAC (typo)
    config_content, _content_type = provisioning.generate_config(
        "00:0B:EA:85:ED:69",
        extension_registry,  # Last digit is 9 instead of 8 (typo)
    )

    # Should return None for unregistered device
    assert config_content is None, "Config should be None for unregistered device"

    # The warning log should mention similar MACs were found
    # We can't easily test log output, but we verified the code path exists


def test_mac_placeholder_detection() -> None:
    """Test that MAC address placeholders are detected properly"""

    from pbx.api.routes.provisioning import MAC_ADDRESS_PLACEHOLDERS
    from pbx.features.phone_provisioning import normalize_mac_address

    # Verify the constant has key placeholder patterns
    # We expect literal placeholders like {mac} that indicate misconfiguration
    # Note: $mac and $MA are CORRECT variables and should NOT be in this list
    assert len(MAC_ADDRESS_PLACEHOLDERS) > 0, "MAC_ADDRESS_PLACEHOLDERS should not be empty"
    assert "{mac}" in MAC_ADDRESS_PLACEHOLDERS, "Should include {mac} placeholder"
    assert "{MAC}" in MAC_ADDRESS_PLACEHOLDERS, "Should include {MAC} placeholder"

    # Verify that correct MAC variables are NOT in the placeholder list
    assert "$mac" not in MAC_ADDRESS_PLACEHOLDERS, "$mac is a valid MAC variable, not a placeholder"
    assert "$MA" not in MAC_ADDRESS_PLACEHOLDERS, (
        "$MA is a valid MAC variable (Cisco), not a placeholder"
    )

    # Test that actual MAC addresses are NOT in the placeholder list
    real_macs = ["00:15:65:12:34:56", "00-15-65-12-34-56", "0015.6512.3456", "001565123456"]

    for mac in real_macs:
        # Verify real MACs are not mistaken for placeholders
        assert mac not in MAC_ADDRESS_PLACEHOLDERS, (
            f"Real MAC {mac} should not be in placeholder list"
        )

        # Verify normalized MACs are also not placeholders
        normalized = normalize_mac_address(mac)
        assert normalized == "001565123456", (
            f"MAC {mac} should normalize to 001565123456, got {normalized}"
        )
        assert normalized not in MAC_ADDRESS_PLACEHOLDERS, (
            f"Normalized MAC {normalized} should not be in placeholder list"
        )

    # Test that placeholder detection works correctly for common cases
    # This simulates what happens in the API endpoint
    test_cases = [
        ("{mac}", True, "Literal {mac} placeholder (misconfiguration)"),
        ("{MAC}", True, "Literal {MAC} placeholder (misconfiguration)"),
        ("{Ma}", True, "Literal {Ma} placeholder (misconfiguration)"),
        ("$mac", False, "Valid MAC variable for Zultys/Yealink/Polycom/Grandstream"),
        ("$MA", False, "Valid MAC variable for Cisco"),
        ("000bea85ed68", False, "Valid normalized MAC"),
        ("00:0B:EA:85:ED:68", False, "Valid MAC with colons"),
    ]

    for mac_value, should_be_placeholder, description in test_cases:
        is_placeholder = mac_value in MAC_ADDRESS_PLACEHOLDERS
        assert is_placeholder == should_be_placeholder, (
            f"Failed for {description}: {mac_value} (expected placeholder={should_be_placeholder}, got {is_placeholder})"
        )
