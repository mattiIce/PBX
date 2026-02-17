"""Comprehensive tests for Hot-Desking feature."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestHotDeskSession:
    """Tests for HotDeskSession."""

    @patch("pbx.features.hot_desking.get_logger")
    def test_session_init(self, mock_get_logger: MagicMock) -> None:
        """Test session initialization."""
        from pbx.features.hot_desking import HotDeskSession

        session = HotDeskSession("1001", "device-mac-1", "192.168.1.100")

        assert session.extension == "1001"
        assert session.device_id == "device-mac-1"
        assert session.ip_address == "192.168.1.100"
        assert session.auto_logout_enabled is True
        assert isinstance(session.logged_in_at, datetime)
        assert isinstance(session.last_activity, datetime)

    @patch("pbx.features.hot_desking.get_logger")
    def test_update_activity(self, mock_get_logger: MagicMock) -> None:
        """Test updating activity timestamp."""
        from pbx.features.hot_desking import HotDeskSession

        session = HotDeskSession("1001", "device-1", "192.168.1.100")
        old_activity = session.last_activity

        # Small delay to ensure timestamp differs
        import time

        time.sleep(0.01)
        session.update_activity()

        assert session.last_activity >= old_activity

    @patch("pbx.features.hot_desking.get_logger")
    def test_to_dict(self, mock_get_logger: MagicMock) -> None:
        """Test session serialization to dict."""
        from pbx.features.hot_desking import HotDeskSession

        session = HotDeskSession("1001", "device-1", "192.168.1.100")
        result = session.to_dict()

        assert result["extension"] == "1001"
        assert result["device_id"] == "device-1"
        assert result["ip_address"] == "192.168.1.100"
        assert result["auto_logout_enabled"] is True
        assert "logged_in_at" in result
        assert "last_activity" in result


@pytest.mark.unit
class TestHotDeskingSystemInit:
    """Tests for HotDeskingSystem initialization."""

    @patch("pbx.features.hot_desking.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when disabled."""
        from pbx.features.hot_desking import HotDeskingSystem

        config = MagicMock()
        config.get.return_value = False

        system = HotDeskingSystem(config=config)

        assert system.enabled is False
        assert system.sessions == {}

    @patch("pbx.features.hot_desking.HotDeskingSystem._start_cleanup_thread")
    @patch("pbx.features.hot_desking.get_logger")
    def test_init_enabled(self, mock_get_logger: MagicMock, mock_cleanup: MagicMock) -> None:
        """Test initialization when enabled."""
        from pbx.features.hot_desking import HotDeskingSystem

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "features.hot_desking.enabled": True,
                "features.hot_desking.auto_logout_timeout": 28800,
                "features.hot_desking.require_pin": True,
                "features.hot_desking.allow_concurrent_logins": False,
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get

        system = HotDeskingSystem(config=config)

        assert system.enabled is True
        assert system.auto_logout_timeout == 28800
        assert system.require_pin is True
        mock_cleanup.assert_called_once()

    @patch("pbx.features.hot_desking.get_logger")
    def test_init_no_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with no config."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()

        assert system.enabled is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_config_no_get(self, mock_get_logger: MagicMock) -> None:
        """Test _get_config with non-dict config."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem(config="not_a_dict")

        assert system._get_config("key", "default") == "default"


@pytest.mark.unit
class TestHotDeskingLogin:
    """Tests for HotDeskingSystem.login."""

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test login when disabled."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.enabled = False

        assert system.login("1001", "device-1", "192.168.1.1") is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_extension_not_found(self, mock_get_logger: MagicMock) -> None:
        """Test login when extension doesn't exist."""
        from pbx.features.hot_desking import HotDeskingSystem

        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = None

        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True

        assert system.login("9999", "device-1", "192.168.1.1") is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_pin_required_no_pin(self, mock_get_logger: MagicMock) -> None:
        """Test login when PIN is required but not provided."""
        from pbx.features.hot_desking import HotDeskingSystem

        ext = {"voicemail_pin": "1234"}
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = ext

        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True
        system.require_pin = True

        assert system.login("1001", "device-1", "192.168.1.1") is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_pin_invalid(self, mock_get_logger: MagicMock) -> None:
        """Test login with invalid PIN."""
        from pbx.features.hot_desking import HotDeskingSystem

        ext = {"voicemail_pin": "1234"}
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = ext

        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True
        system.require_pin = True

        assert system.login("1001", "device-1", "192.168.1.1", pin="9999") is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_success(self, mock_get_logger: MagicMock) -> None:
        """Test successful login."""
        from pbx.features.hot_desking import HotDeskingSystem

        ext = {"voicemail_pin": "1234"}
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = ext
        # Remove webhook_system attribute to skip webhook
        del pbx_core.webhook_system

        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True
        system.require_pin = True

        result = system.login("1001", "device-1", "192.168.1.1", pin="1234")

        assert result is True
        assert "device-1" in system.sessions
        assert "1001" in system.extension_devices

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_triggers_webhook(self, mock_get_logger: MagicMock) -> None:
        """Test login triggers webhook event."""
        from pbx.features.hot_desking import HotDeskingSystem

        ext = {"voicemail_pin": "1234"}
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = ext

        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True
        system.require_pin = True

        system.login("1001", "device-1", "192.168.1.1", pin="1234")

        pbx_core.webhook_system.trigger_event.assert_called_once()
        call_args = pbx_core.webhook_system.trigger_event.call_args
        assert call_args[0][0] == "hot_desk.login"

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_replaces_existing_session(self, mock_get_logger: MagicMock) -> None:
        """Test login replaces existing session on same device."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        ext = {"voicemail_pin": "1234"}
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = ext
        del pbx_core.webhook_system

        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True
        system.require_pin = True

        # First login
        system.login("1001", "device-1", "192.168.1.1", pin="1234")
        # Second login with different extension on same device
        system.login("1002", "device-1", "192.168.1.1", pin="1234")

        assert system.sessions["device-1"].extension == "1002"

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_concurrent_not_allowed_logs_out_other(self, mock_get_logger: MagicMock) -> None:
        """Test login without concurrent logins logs out other device."""
        from pbx.features.hot_desking import HotDeskingSystem

        ext = {"voicemail_pin": "1234"}
        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = ext
        del pbx_core.webhook_system

        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True
        system.require_pin = True
        system.allow_concurrent_logins = False

        # Login on device-1
        system.login("1001", "device-1", "192.168.1.1", pin="1234")
        # Login on device-2 with same extension
        system.login("1001", "device-2", "192.168.1.2", pin="1234")

        assert "device-1" not in system.sessions
        assert "device-2" in system.sessions

    @patch("pbx.features.hot_desking.get_logger")
    def test_login_no_extension_registry(self, mock_get_logger: MagicMock) -> None:
        """Test login without extension registry."""
        from pbx.features.hot_desking import HotDeskingSystem

        pbx_core = MagicMock(spec=[])  # No attributes at all

        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True

        assert system.login("1001", "device-1", "192.168.1.1") is False


@pytest.mark.unit
class TestHotDeskingLogout:
    """Tests for HotDeskingSystem.logout and related methods."""

    @patch("pbx.features.hot_desking.get_logger")
    def test_logout_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test logout when disabled."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.enabled = False

        assert system.logout("device-1") is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_logout_no_session(self, mock_get_logger: MagicMock) -> None:
        """Test logout when no session exists."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.enabled = True

        assert system.logout("nonexistent") is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_logout_success(self, mock_get_logger: MagicMock) -> None:
        """Test successful logout."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        system.enabled = True

        session = HotDeskSession("1001", "device-1", "192.168.1.1")
        system.sessions["device-1"] = session
        system.extension_devices["1001"] = ["device-1"]

        result = system.logout("device-1")

        assert result is True
        assert "device-1" not in system.sessions
        assert "1001" not in system.extension_devices

    @patch("pbx.features.hot_desking.get_logger")
    def test_logout_triggers_webhook(self, mock_get_logger: MagicMock) -> None:
        """Test logout triggers webhook."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        pbx_core = MagicMock()
        system = HotDeskingSystem(pbx_core=pbx_core)
        system.enabled = True

        session = HotDeskSession("1001", "device-1", "192.168.1.1")
        system.sessions["device-1"] = session
        system.extension_devices["1001"] = ["device-1"]

        system.logout("device-1")

        pbx_core.webhook_system.trigger_event.assert_called_once()

    @patch("pbx.features.hot_desking.get_logger")
    def test_logout_extension(self, mock_get_logger: MagicMock) -> None:
        """Test logout extension from all devices."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        system.enabled = True

        system.sessions["device-1"] = HotDeskSession("1001", "device-1", "192.168.1.1")
        system.sessions["device-2"] = HotDeskSession("1001", "device-2", "192.168.1.2")
        system.extension_devices["1001"] = ["device-1", "device-2"]

        count = system.logout_extension("1001")

        assert count == 2
        assert len(system.sessions) == 0

    @patch("pbx.features.hot_desking.get_logger")
    def test_logout_extension_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test logout_extension when disabled."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.enabled = False

        assert system.logout_extension("1001") == 0


@pytest.mark.unit
class TestHotDeskingQueries:
    """Tests for query methods."""

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_session(self, mock_get_logger: MagicMock) -> None:
        """Test get session by device ID."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        session = HotDeskSession("1001", "device-1", "192.168.1.1")
        system.sessions["device-1"] = session

        result = system.get_session("device-1")

        assert result is session

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_session_not_found(self, mock_get_logger: MagicMock) -> None:
        """Test get session when not found."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()

        assert system.get_session("nonexistent") is None

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_extension_session(self, mock_get_logger: MagicMock) -> None:
        """Test get session by extension."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        session = HotDeskSession("1001", "device-1", "192.168.1.1")
        system.sessions["device-1"] = session
        system.extension_devices["1001"] = ["device-1"]

        result = system.get_extension_session("1001")

        assert result is session

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_extension_session_not_found(self, mock_get_logger: MagicMock) -> None:
        """Test get extension session when not found."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()

        assert system.get_extension_session("9999") is None

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_extension_devices(self, mock_get_logger: MagicMock) -> None:
        """Test get all devices for extension."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.extension_devices["1001"] = ["device-1", "device-2"]

        result = system.get_extension_devices("1001")

        assert result == ["device-1", "device-2"]

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_extension_devices_empty(self, mock_get_logger: MagicMock) -> None:
        """Test get devices for unlogged extension."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()

        assert system.get_extension_devices("9999") == []

    @patch("pbx.features.hot_desking.get_logger")
    def test_is_logged_in_true(self, mock_get_logger: MagicMock) -> None:
        """Test is_logged_in returns True."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.extension_devices["1001"] = ["device-1"]

        assert system.is_logged_in("1001") is True

    @patch("pbx.features.hot_desking.get_logger")
    def test_is_logged_in_false(self, mock_get_logger: MagicMock) -> None:
        """Test is_logged_in returns False."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()

        assert system.is_logged_in("1001") is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_is_logged_in_empty_devices(self, mock_get_logger: MagicMock) -> None:
        """Test is_logged_in with empty device list."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.extension_devices["1001"] = []

        assert system.is_logged_in("1001") is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_update_session_activity(self, mock_get_logger: MagicMock) -> None:
        """Test updating session activity."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        session = HotDeskSession("1001", "device-1", "192.168.1.1")
        system.sessions["device-1"] = session
        old_activity = session.last_activity

        import time

        time.sleep(0.01)
        system.update_session_activity("device-1")

        assert session.last_activity >= old_activity

    @patch("pbx.features.hot_desking.get_logger")
    def test_update_session_activity_no_session(self, mock_get_logger: MagicMock) -> None:
        """Test updating activity for nonexistent session."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.update_session_activity("nonexistent")
        # Should not raise

    @patch("pbx.features.hot_desking.get_logger")
    def test_set_auto_logout_true(self, mock_get_logger: MagicMock) -> None:
        """Test enabling auto-logout."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        session = HotDeskSession("1001", "device-1", "192.168.1.1")
        system.sessions["device-1"] = session

        result = system.set_auto_logout("device-1", False)

        assert result is True
        assert session.auto_logout_enabled is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_set_auto_logout_no_session(self, mock_get_logger: MagicMock) -> None:
        """Test setting auto-logout for nonexistent session."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()

        assert system.set_auto_logout("nonexistent", True) is False

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_active_sessions(self, mock_get_logger: MagicMock) -> None:
        """Test getting all active sessions."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        system.sessions["device-1"] = HotDeskSession("1001", "device-1", "192.168.1.1")
        system.sessions["device-2"] = HotDeskSession("1002", "device-2", "192.168.1.2")

        result = system.get_active_sessions()

        assert len(result) == 2
        assert all(isinstance(s, dict) for s in result)

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_session_count(self, mock_get_logger: MagicMock) -> None:
        """Test getting session count."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        system.sessions["device-1"] = HotDeskSession("1001", "device-1", "192.168.1.1")

        assert system.get_session_count() == 1


@pytest.mark.unit
class TestHotDeskingProfile:
    """Tests for get_extension_profile."""

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_profile_no_pbx_core(self, mock_get_logger: MagicMock) -> None:
        """Test get profile without PBX core."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()

        assert system.get_extension_profile("1001") is None

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_profile_extension_not_found(self, mock_get_logger: MagicMock) -> None:
        """Test get profile when extension not found."""
        from pbx.features.hot_desking import HotDeskingSystem

        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = None

        system = HotDeskingSystem(pbx_core=pbx_core)

        assert system.get_extension_profile("9999") is None

    @patch("pbx.features.hot_desking.get_logger")
    def test_get_profile_success(self, mock_get_logger: MagicMock) -> None:
        """Test successful profile retrieval."""
        from pbx.features.hot_desking import HotDeskingSystem

        ext = {
            "name": "John Doe",
            "email": "john@example.com",
            "allow_external": True,
            "call_forwarding": {"number": "5551234567"},
            "do_not_disturb": False,
        }
        ext_mock = MagicMock()
        ext_mock.get.side_effect = lambda key, default=None: ext.get(key, default)

        pbx_core = MagicMock()
        pbx_core.extension_registry.get_extension.return_value = ext_mock

        system = HotDeskingSystem(pbx_core=pbx_core)
        profile = system.get_extension_profile("1001")

        assert profile is not None
        assert profile["extension"] == "1001"
        assert profile["voicemail_enabled"] is True


@pytest.mark.unit
class TestHotDeskingAutoLogout:
    """Tests for auto-logout functionality."""

    @patch("pbx.features.hot_desking.get_logger")
    def test_auto_logout_inactive_sessions(self, mock_get_logger: MagicMock) -> None:
        """Test auto-logout of inactive sessions."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        system.auto_logout_timeout = 10  # 10 seconds

        # Create a session that is expired
        session = HotDeskSession("1001", "device-1", "192.168.1.1")
        session.last_activity = datetime.now(UTC) - timedelta(seconds=30)
        system.sessions["device-1"] = session
        system.extension_devices["1001"] = ["device-1"]

        system._auto_logout_inactive_sessions()

        assert "device-1" not in system.sessions

    @patch("pbx.features.hot_desking.get_logger")
    def test_auto_logout_skips_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test auto-logout skips sessions with auto_logout disabled."""
        from pbx.features.hot_desking import HotDeskingSystem, HotDeskSession

        system = HotDeskingSystem()
        system.auto_logout_timeout = 10

        session = HotDeskSession("1001", "device-1", "192.168.1.1")
        session.last_activity = datetime.now(UTC) - timedelta(seconds=30)
        session.auto_logout_enabled = False
        system.sessions["device-1"] = session
        system.extension_devices["1001"] = ["device-1"]

        system._auto_logout_inactive_sessions()

        assert "device-1" in system.sessions  # Still present

    @patch("pbx.features.hot_desking.get_logger")
    def test_stop(self, mock_get_logger: MagicMock) -> None:
        """Test stopping the system."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.running = True
        system.cleanup_thread = MagicMock()
        system.cleanup_thread.is_alive.return_value = True

        system.stop()

        assert system.running is False
        system.cleanup_thread.join.assert_called_once_with(timeout=5)

    @patch("pbx.features.hot_desking.get_logger")
    def test_stop_no_thread(self, mock_get_logger: MagicMock) -> None:
        """Test stopping when no cleanup thread exists."""
        from pbx.features.hot_desking import HotDeskingSystem

        system = HotDeskingSystem()
        system.running = True
        system.cleanup_thread = None

        system.stop()

        assert system.running is False
