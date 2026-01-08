#!/usr/bin/env python3
"""
Tests for provisioning config URL generation
Tests the fix for connection error when API port differs from default
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.utils.config import Config


def test_config_url_uses_correct_port():
    """Test that config URLs use the configured API port, not hardcoded default"""
    print("Testing config URL generation with custom port...")

    # Create a test config with custom port
    class TestConfig:
        def __init__(self, api_port):
            self._api_port = api_port

        def get(self, key, default=None):
            if key == "api.port":
                return self._api_port
            elif key == "server.external_ip":
                return "192.168.1.14"
            elif key == "provisioning.url_format":
                return None  # Force auto-generation
            elif key == "api.ssl.enabled":
                return False
            return default

    # Test with port 9000 (configured in config.yml)
    config_9000 = TestConfig(api_port=9000)
    provisioning_9000 = PhoneProvisioning(config_9000, database=None)

    # Register a device
    device = provisioning_9000.register_device("aa:bb:cc:dd:ee:ff", "1001", "yealink", "t46s")

    # Check that URL uses port 9000
    assert ":9000/" in device.config_url, f"Expected port 9000 in URL, got: {device.config_url}"
    assert ":8080/" not in device.config_url, f"Should not have port 8080, got: {device.config_url}"

    expected_url = "http://192.168.1.14:9000/provision/aabbccddeeff.cfg"
    assert (
        device.config_url == expected_url
    ), f"Expected URL: {expected_url}, got: {device.config_url}"

    print(f"✓ Config URL correctly uses port 9000: {device.config_url}")

    # Test with default port 8080
    config_8080 = TestConfig(api_port=8080)
    provisioning_8080 = PhoneProvisioning(config_8080, database=None)

    device2 = provisioning_8080.register_device("11:22:33:44:55:66", "1002", "yealink", "t46s")

    assert ":8080/" in device2.config_url, f"Expected port 8080 in URL, got: {device2.config_url}"

    print(f"✓ Config URL correctly uses port 8080: {device2.config_url}")


def test_config_url_regenerated_from_database():
    """Test that config URLs are regenerated when loading from database"""
    print("Testing config URL regeneration from database...")

    # Create a mock database that returns old config URL with wrong port
    class MockDevice:
        def __init__(self):
            self.mac_address = "aa:bb:cc:dd:ee:ff"
            self.extension_number = "1001"
            self.vendor = "yealink"
            self.model = "t46s"
            self.device_type = "phone"
            # Old config URL with wrong port (8080)
            self.config_url = "http://192.168.1.14:8080/provision/aabbccddeeff.cfg"
            self.created_at = None
            self.last_provisioned = None

    class MockDevicesDB:
        def list_all(self):
            return [
                {
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                    "extension_number": "1001",
                    "vendor": "yealink",
                    "model": "t46s",
                    "device_type": "phone",
                    "config_url": "http://192.168.1.14:8080/provision/aabbccddeeff.cfg",
                    "created_at": None,
                    "last_provisioned": None,
                }
            ]

    class TestConfig:
        def get(self, key, default=None):
            if key == "api.port":
                return 9000  # New correct port
            elif key == "server.external_ip":
                return "192.168.1.14"
            elif key == "provisioning.url_format":
                return None
            elif key == "api.ssl.enabled":
                return False
            return default

    config = TestConfig()

    # Create provisioning with mock database
    provisioning = PhoneProvisioning(config, database=None)
    provisioning.devices_db = MockDevicesDB()

    # Load devices from database
    provisioning._load_devices_from_database()

    # Get the loaded device
    device = provisioning.get_device("aa:bb:cc:dd:ee:ff")

    assert device is not None, "Device should be loaded from database"

    # Check that config_url was regenerated with correct port
    assert (
        ":9000/" in device.config_url
    ), f"Config URL should use new port 9000, got: {device.config_url}"
    assert (
        ":8080/" not in device.config_url
    ), f"Config URL should not have old port 8080, got: {device.config_url}"

    expected_url = "http://192.168.1.14:9000/provision/aabbccddeeff.cfg"
    assert (
        device.config_url == expected_url
    ), f"Expected regenerated URL: {expected_url}, got: {device.config_url}"

    print(f"✓ Config URL regenerated correctly: {device.config_url}")


def test_generate_config_url_helper():
    """Test the _generate_config_url helper method directly"""
    print("Testing _generate_config_url helper method...")

    class TestConfig:
        def get(self, key, default=None):
            if key == "api.port":
                return 9000
            elif key == "server.external_ip":
                return "10.0.0.5"
            elif key == "provisioning.url_format":
                return "http://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg"
            elif key == "api.ssl.enabled":
                return False
            return default

    config = TestConfig()
    provisioning = PhoneProvisioning(config, database=None)

    # Test URL generation
    mac = "aabbccddeeff"
    url = provisioning._generate_config_url(mac)

    assert url == "http://10.0.0.5:9000/provision/aabbccddeeff.cfg", f"Unexpected URL: {url}"

    print(f"✓ Helper method generates correct URL: {url}")


if __name__ == "__main__":
    test_config_url_uses_correct_port()
    print()
    test_config_url_regenerated_from_database()
    print()
    test_generate_config_url_helper()
    print()
    print("All provisioning config URL tests passed!")
