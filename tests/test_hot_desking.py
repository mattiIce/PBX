#!/usr/bin/env python3
"""
Test hot-desking feature
"""

import time
from typing import Any

from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession


def test_hot_desk_session_creation() -> bool:
    """Test hot desk session creation"""

    session = HotDeskSession("1001", "device-123", "192.168.1.100")

    assert session.extension == "1001", "Extension should match"
    assert session.device_id == "device-123", "Device ID should match"
    assert session.ip_address == "192.168.1.100", "IP should match"
    assert session.auto_logout_enabled, "Auto-logout should be enabled by default"

    # Test to_dict()
    data = session.to_dict()
    assert "extension" in data, "Should have extension"
    assert "device_id" in data, "Should have device_id"
    assert "logged_in_at" in data, "Should have logged_in_at"

    return True


def test_hot_desking_initialization() -> bool:
    """Test hot-desking system initialization"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.hot_desking.enabled": True,
                "features.hot_desking.auto_logout_timeout": 28800,
                "features.hot_desking.require_pin": True,
                "features.hot_desking.allow_concurrent_logins": False,
            }
            return config_map.get(key, default)

    config = MockConfig()
    hot_desk = HotDeskingSystem(config)

    assert hot_desk.enabled, "Should be enabled"
    assert hot_desk.auto_logout_timeout == 28800, "Timeout should be 28800"
    assert hot_desk.require_pin, "Should require PIN"
    assert hot_desk.allow_concurrent_logins is False, "Should not allow concurrent logins"

    hot_desk.stop()

    return True


def test_hot_desk_login_logout() -> bool:
    """Test hot-desk login and logout"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.hot_desking.enabled": True,
                "features.hot_desking.require_pin": True,
            }
            return config_map.get(key, default)

    class MockExtension:
        def get(self, key: str, default: Any = None) -> Any:
            return {"name": "John Doe", "voicemail_pin": "1234"}.get(key, default)

    class MockExtensionRegistry:
        def get_extension(self, ext: str) -> MockExtension | None:
            if ext == "1001":
                return MockExtension()
            return None

    class MockPBXCore:
        def __init__(self) -> None:
            self.extension_registry = MockExtensionRegistry()

    config = MockConfig()
    pbx_core = MockPBXCore()
    hot_desk = HotDeskingSystem(config, pbx_core)

    # Test login
    success = hot_desk.login("1001", "device-abc", "192.168.1.50", "1234")
    assert success, "Login should succeed"

    # Verify session
    session = hot_desk.get_session("device-abc")
    assert session is not None, "Session should exist"
    assert session.extension == "1001", "Extension should match"

    # Verify extension is logged in
    assert hot_desk.is_logged_in("1001"), "Extension should be logged in"

    # Test logout
    success = hot_desk.logout("device-abc")
    assert success, "Logout should succeed"

    # Verify session is removed
    session = hot_desk.get_session("device-abc")
    assert session is None, "Session should be removed"

    # Verify extension is logged out
    assert hot_desk.is_logged_in("1001") is False, "Extension should be logged out"

    hot_desk.stop()

    return True


def test_hot_desk_invalid_pin() -> bool:
    """Test hot-desk login with invalid PIN"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.hot_desking.enabled": True,
                "features.hot_desking.require_pin": True,
            }
            return config_map.get(key, default)

    class MockExtension:
        def get(self, key: str, default: Any = None) -> Any:
            return {"name": "Jane Doe", "voicemail_pin": "5678"}.get(key, default)

    class MockExtensionRegistry:
        def get_extension(self, ext: str) -> MockExtension | None:
            if ext == "1002":
                return MockExtension()
            return None

    class MockPBXCore:
        def __init__(self) -> None:
            self.extension_registry = MockExtensionRegistry()

    config = MockConfig()
    pbx_core = MockPBXCore()
    hot_desk = HotDeskingSystem(config, pbx_core)

    # Test login with wrong PIN
    success = hot_desk.login("1002", "device-xyz", "192.168.1.60", "9999")
    assert success is False, "Login should fail with wrong PIN"

    # Verify no session was created
    session = hot_desk.get_session("device-xyz")
    assert session is None, "No session should exist"

    # Test login without PIN (when required)
    success = hot_desk.login("1002", "device-xyz", "192.168.1.60", None)
    assert success is False, "Login should fail without PIN"

    hot_desk.stop()

    return True


def test_hot_desk_concurrent_logins() -> bool:
    """Test concurrent login behavior"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.hot_desking.enabled": True,
                "features.hot_desking.require_pin": False,
                "features.hot_desking.allow_concurrent_logins": False,
            }
            return config_map.get(key, default)

    class MockExtension:
        def get(self, key: str, default: Any = None) -> Any:
            return {"name": "Bob Smith"}.get(key, default)

    class MockExtensionRegistry:
        def get_extension(self, ext: str) -> MockExtension | None:
            if ext == "1003":
                return MockExtension()
            return None

    class MockPBXCore:
        def __init__(self) -> None:
            self.extension_registry = MockExtensionRegistry()

    config = MockConfig()
    pbx_core = MockPBXCore()
    hot_desk = HotDeskingSystem(config, pbx_core)

    # Login to first device
    success = hot_desk.login("1003", "device-1", "192.168.1.10")
    assert success, "First login should succeed"

    # Try to login to second device (should log out from first)
    success = hot_desk.login("1003", "device-2", "192.168.1.20")
    assert success, "Second login should succeed"

    # Verify first device is logged out
    session1 = hot_desk.get_session("device-1")
    assert session1 is None, "First device should be logged out"

    # Verify second device is logged in
    session2 = hot_desk.get_session("device-2")
    assert session2 is not None, "Second device should be logged in"
    assert session2.extension == "1003", "Extension should match"

    hot_desk.stop()

    return True


def test_hot_desk_allow_concurrent() -> bool:
    """Test allowing concurrent logins"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.hot_desking.enabled": True,
                "features.hot_desking.require_pin": False,
                "features.hot_desking.allow_concurrent_logins": True,
            }
            return config_map.get(key, default)

    class MockExtension:
        def get(self, key: str, default: Any = None) -> Any:
            return {"name": "Alice Cooper"}.get(key, default)

    class MockExtensionRegistry:
        def get_extension(self, ext: str) -> MockExtension | None:
            if ext == "1004":
                return MockExtension()
            return None

    class MockPBXCore:
        def __init__(self) -> None:
            self.extension_registry = MockExtensionRegistry()

    config = MockConfig()
    pbx_core = MockPBXCore()
    hot_desk = HotDeskingSystem(config, pbx_core)

    # Login to first device
    success = hot_desk.login("1004", "device-a", "192.168.1.30")
    assert success, "First login should succeed"

    # Login to second device (should both remain logged in)
    success = hot_desk.login("1004", "device-b", "192.168.1.40")
    assert success, "Second login should succeed"

    # Verify both devices are logged in
    session_a = hot_desk.get_session("device-a")
    session_b = hot_desk.get_session("device-b")
    assert session_a is not None, "First device should still be logged in"
    assert session_b is not None, "Second device should be logged in"

    # Verify extension has 2 devices
    devices = hot_desk.get_extension_devices("1004")
    assert len(devices) == 2, "Should have 2 devices"

    hot_desk.stop()

    return True


def test_hot_desk_extension_logout() -> bool:
    """Test logging out extension from all devices"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.hot_desking.enabled": True,
                "features.hot_desking.require_pin": False,
                "features.hot_desking.allow_concurrent_logins": True,
            }
            return config_map.get(key, default)

    class MockExtension:
        def get(self, key: str, default: Any = None) -> Any:
            return {"name": "Test User"}.get(key, default)

    class MockExtensionRegistry:
        def get_extension(self, ext: str) -> MockExtension | None:
            if ext == "1005":
                return MockExtension()
            return None

    class MockPBXCore:
        def __init__(self) -> None:
            self.extension_registry = MockExtensionRegistry()

    config = MockConfig()
    pbx_core = MockPBXCore()
    hot_desk = HotDeskingSystem(config, pbx_core)

    # Login to multiple devices
    hot_desk.login("1005", "dev1", "192.168.1.1")
    hot_desk.login("1005", "dev2", "192.168.1.2")
    hot_desk.login("1005", "dev3", "192.168.1.3")

    # Verify 3 devices
    devices = hot_desk.get_extension_devices("1005")
    assert len(devices) == 3, "Should have 3 devices"

    # Logout extension from all devices
    count = hot_desk.logout_extension("1005")
    assert count == 3, "Should log out from 3 devices"

    # Verify all sessions are removed
    assert hot_desk.is_logged_in("1005") is False, "Extension should be logged out"

    hot_desk.stop()

    return True


def test_hot_desk_session_activity() -> bool:
    """Test session activity tracking"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.hot_desking.enabled": True,
                "features.hot_desking.require_pin": False,
            }
            return config_map.get(key, default)

    class MockExtension:
        def get(self, key: str, default: Any = None) -> Any:
            return {"name": "Active User"}.get(key, default)

    class MockExtensionRegistry:
        def get_extension(self, ext: str) -> MockExtension | None:
            if ext == "1006":
                return MockExtension()
            return None

    class MockPBXCore:
        def __init__(self) -> None:
            self.extension_registry = MockExtensionRegistry()

    config = MockConfig()
    pbx_core = MockPBXCore()
    hot_desk = HotDeskingSystem(config, pbx_core)

    # Login
    hot_desk.login("1006", "device-test", "192.168.1.70")

    session1 = hot_desk.get_session("device-test")
    initial_activity = session1.last_activity

    # Wait a bit
    time.sleep(0.1)

    # Update activity
    hot_desk.update_session_activity("device-test")

    session2 = hot_desk.get_session("device-test")
    updated_activity = session2.last_activity

    assert updated_activity > initial_activity, "Activity should be updated"

    hot_desk.stop()

    return True


def test_hot_desk_profile_retrieval() -> bool:
    """Test extension profile retrieval"""

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {"features.hot_desking.enabled": True}
            return config_map.get(key, default)

    class MockExtension:
        def get(self, key: str, default: Any = None) -> Any:
            return {
                "name": "Profile User",
                "email": "user@company.com",
                "allow_external": True,
                "do_not_disturb": False,
            }.get(key, default)

    class MockExtensionRegistry:
        def get_extension(self, ext: str) -> MockExtension | None:
            if ext == "1007":
                return MockExtension()
            return None

    class MockPBXCore:
        def __init__(self) -> None:
            self.extension_registry = MockExtensionRegistry()

    config = MockConfig()
    pbx_core = MockPBXCore()
    hot_desk = HotDeskingSystem(config, pbx_core)

    # Get profile
    profile = hot_desk.get_extension_profile("1007")

    assert profile is not None, "Profile should exist"
    assert profile["extension"] == "1007", "Extension should match"
    assert profile["name"] == "Profile User", "Name should match"
    assert profile["email"] == "user@company.com", "Email should match"
    assert profile["allow_external"], "allow_external should match"

    hot_desk.stop()

    return True
