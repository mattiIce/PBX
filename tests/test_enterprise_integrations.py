#!/usr/bin/env python3
"""
Tests for enterprise integration implementations
Tests the newly implemented features in Zoom, Teams, Outlook, and Active Directory integrations
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.integrations.active_directory import ActiveDirectoryIntegration
from pbx.integrations.outlook import OutlookIntegration
from pbx.integrations.teams import TeamsIntegration
from pbx.integrations.zoom import ZoomIntegration


class MockConfig:
    """Mock config object that mimics Config class behavior"""

    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        keys = key.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val if val is not None else default


class MockTrunk:
    """Mock SIP trunk for testing"""

    def __init__(self, name, host):
        self.name = name
        self.host = host
        self.channels_in_use = 0
        self.channels_available = 10

    def can_make_call(self):
        return self.channels_in_use < self.channels_available

    def allocate_channel(self):
        if self.can_make_call():
            self.channels_in_use += 1
            return True
        return False

    def release_channel(self):
        if self.channels_in_use > 0:
            self.channels_in_use -= 1


class MockTrunkSystem:
    """Mock trunk system for testing"""

    def __init__(self):
        self.trunks = {}

    def add_trunk(self, trunk_id, trunk):
        self.trunks[trunk_id] = trunk


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self):
        self.trunk_system = MockTrunkSystem()
        self.extension_registry = MagicMock()
        self.call_manager = MagicMock()


def test_zoom_phone_routing():
    """Test Zoom Phone SIP trunk routing"""
    print("\nTesting Zoom Phone routing...")

    config = MockConfig(
        {
            "integrations": {
                "zoom": {
                    "enabled": True,
                    "phone_enabled": True,
                    "account_id": "test_account",
                    "client_id": "test_client",
                    "client_secret": "test_secret",
                }
            }
        }
    )

    zoom = ZoomIntegration(config)

    # Test without PBX core (should log setup instructions)
    result = zoom.route_to_zoom_phone("+15551234567", "+15559876543")
    assert result is False, "Should return False without PBX core"

    # Test with PBX core but no trunk
    pbx_core = MockPBXCore()
    result = zoom.route_to_zoom_phone("+15551234567", "+15559876543", pbx_core=pbx_core)
    assert result is False, "Should return False without configured trunk"

    # Test with PBX core and proper Zoom trunk
    zoom_trunk = MockTrunk("Zoom Phone Trunk", "pbx.zoom.us")
    pbx_core.trunk_system.add_trunk("zoom", zoom_trunk)
    result = zoom.route_to_zoom_phone("+15551234567", "+15559876543", pbx_core=pbx_core)
    assert result is True, "Should successfully route with configured trunk"
    assert zoom_trunk.channels_in_use == 1, "Should allocate channel"

    print("✓ Zoom Phone routing works")


def test_teams_direct_routing():
    """Test Microsoft Teams Direct Routing"""
    print("\nTesting Teams Direct Routing...")

    config = MockConfig(
        {
            "integrations": {
                "teams": {
                    "enabled": True,
                    "tenant_id": "test_tenant",
                    "client_id": "test_client",
                    "client_secret": "test_secret",
                    "sip_domain": "sip.contoso.com",
                },
                "microsoft_teams": {
                    "enabled": True,
                    "tenant_id": "test_tenant",
                    "client_id": "test_client",
                    "client_secret": "test_secret",
                    "direct_routing_domain": "sip.contoso.com",
                },
            }
        }
    )

    teams = TeamsIntegration(config)

    # Test without PBX core (should log setup instructions)
    result = teams.route_call_to_teams("+15551234567", "user@contoso.com")
    assert result is False, "Should return False without PBX core"

    # Test with PBX core but no trunk
    pbx_core = MockPBXCore()
    result = teams.route_call_to_teams("+15551234567", "user@contoso.com", pbx_core=pbx_core)
    assert result is False, "Should return False without configured trunk"

    # Test with PBX core and proper Teams trunk
    teams_trunk = MockTrunk("Microsoft Teams Trunk", "sip.contoso.com")
    pbx_core.trunk_system.add_trunk("teams", teams_trunk)
    result = teams.route_call_to_teams("+15551234567", "user@contoso.com", pbx_core=pbx_core)
    assert result is True, "Should successfully route with configured trunk"
    assert teams_trunk.channels_in_use == 1, "Should allocate channel"

    # Test with user without domain (should add domain)
    result = teams.route_call_to_teams("+15551234567", "testuser", pbx_core=pbx_core)
    assert result is True, "Should handle user without domain"

    print("✓ Teams Direct Routing works")


def test_outlook_meeting_reminder():
    """Test Outlook meeting reminder scheduling"""
    print("\nTesting Outlook meeting reminder...")

    config = MockConfig(
        {
            "integrations": {
                "outlook": {
                    "enabled": True,
                    "tenant_id": "test_tenant",
                    "client_id": "test_client",
                    "client_secret": "test_secret",
                }
            }
        }
    )

    outlook = OutlookIntegration(config)

    # Test without PBX core (should log setup instructions)
    result = outlook.send_meeting_reminder("user@company.com", "meeting-123", minutes_before=5)
    assert result is False, "Should return False without PBX core"

    # Test with PBX core but mock the Graph API call
    pbx_core = MockPBXCore()

    # Mock extension registry
    mock_extension = MagicMock()
    mock_extension.config = {"email": "user@company.com"}
    pbx_core.extension_registry.extensions = {"1001": mock_extension}

    # Mock the requests.get to return meeting details
    future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    mock_meeting = {"subject": "Test Meeting", "start": {"dateTime": future_time.isoformat()}}

    with patch("pbx.integrations.outlook.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_meeting
        mock_get.return_value = mock_response

        # Mock authenticate to return True
        outlook.authenticate = lambda: True
        outlook.access_token = "test_token"

        result = outlook.send_meeting_reminder(
            "user@company.com", "meeting-123", minutes_before=5, pbx_core=pbx_core
        )
        assert result is True, "Should successfully schedule reminder with PBX core"

    print("✓ Outlook meeting reminder works")


def test_active_directory_sync():
    """Test Active Directory user sync (already fully implemented)"""
    print("\nTesting Active Directory sync...")

    config = {
        "integrations": {
            "active_directory": {
                "enabled": False,  # Disabled to avoid needing real LDAP
                "server": "ldaps://dc.test.local:636",
                "base_dn": "DC=test,DC=local",
                "bind_dn": "CN=svc,DC=test,DC=local",
                "bind_password": "test",
            }
        }
    }

    ad = ActiveDirectoryIntegration(config)

    # Test that methods exist and handle disabled state gracefully
    result = ad.sync_users()
    assert result == 0, "Should return 0 when disabled"

    result = ad.get_user_groups("testuser")
    assert result == [], "Should return empty list when disabled"

    result = ad.get_user_photo("testuser")
    assert result is None, "Should return None when disabled"

    print("✓ Active Directory integration structure validated")


def test_integration_error_handling():
    """Test that integrations handle errors gracefully"""
    print("\nTesting error handling...")

    # Test with invalid/minimal config
    config = {"integrations": {}}

    zoom = ZoomIntegration(config)
    assert zoom.enabled is False, "Should be disabled with missing config"

    teams = TeamsIntegration(config)
    assert teams.enabled is False, "Should be disabled with missing config"

    outlook = OutlookIntegration(config)
    assert outlook.enabled is False, "Should be disabled with missing config"

    ad = ActiveDirectoryIntegration(config)
    assert ad.enabled is False, "Should be disabled with missing config"

    # Test that disabled integrations return safely
    assert zoom.route_to_zoom_phone("123", "456") is False
    assert teams.route_call_to_teams("123", "456") is False
    assert outlook.send_meeting_reminder("user@test.com", "meet-123") is False
    assert ad.sync_users() == 0

    print("✓ Error handling works correctly")


def run_all_tests():
    """Run all enterprise integration tests"""
    print("=" * 60)
    print("Running Enterprise Integration Tests")
    print("=" * 60)

    tests = [
        test_zoom_phone_routing,
        test_teams_direct_routing,
        test_outlook_meeting_reminder,
        test_active_directory_sync,
        test_integration_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
