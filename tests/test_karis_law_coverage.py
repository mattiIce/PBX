"""Comprehensive tests for Kari's Law Compliance module."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestKarisLawComplianceInit:
    """Tests for KarisLawCompliance initialization."""

    def test_init_defaults_no_config(self) -> None:
        """Init with empty config uses defaults."""
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            kl = KarisLawCompliance(pbx_core=MagicMock(), config=None)
            assert kl.enabled is True
            assert kl.auto_notify is True
            assert kl.require_location is True
            assert kl.emergency_trunk_id is None
            assert kl.emergency_calls == []
            assert kl.max_call_history == 1000

    def test_init_with_full_config(self) -> None:
        """Init with full config applies all settings."""
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            config = {
                "features": {
                    "karis_law": {
                        "enabled": True,
                        "auto_notify": False,
                        "require_location": False,
                        "emergency_trunk_id": "trunk-e911",
                    }
                }
            }
            kl = KarisLawCompliance(pbx_core=MagicMock(), config=config)
            assert kl.enabled is True
            assert kl.auto_notify is False
            assert kl.require_location is False
            assert kl.emergency_trunk_id == "trunk-e911"

    def test_init_disabled_logs_warning(self) -> None:
        """Disabled Kari's Law logs a warning."""
        mock_logger = MagicMock()
        with patch("pbx.features.karis_law.get_logger", return_value=mock_logger):
            from pbx.features.karis_law import KarisLawCompliance

            config = {"features": {"karis_law": {"enabled": False}}}
            kl = KarisLawCompliance(pbx_core=MagicMock(), config=config)
            assert kl.enabled is False
            mock_logger.warning.assert_called()

    def test_init_enabled_logs_info(self) -> None:
        """Enabled Kari's Law logs info messages."""
        mock_logger = MagicMock()
        with patch("pbx.features.karis_law.get_logger", return_value=mock_logger):
            from pbx.features.karis_law import KarisLawCompliance

            kl = KarisLawCompliance(pbx_core=MagicMock(), config={})
            assert kl.enabled is True
            assert mock_logger.info.call_count >= 3


@pytest.mark.unit
class TestIsEmergencyNumber:
    """Tests for is_emergency_number."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.kl = KarisLawCompliance(pbx_core=MagicMock(), config={})

    def test_911_is_emergency(self) -> None:
        assert self.kl.is_emergency_number("911") is True

    def test_9911_is_emergency(self) -> None:
        assert self.kl.is_emergency_number("9911") is True

    def test_9_dash_911_is_emergency(self) -> None:
        assert self.kl.is_emergency_number("9-911") is True

    def test_regular_number_is_not_emergency(self) -> None:
        assert self.kl.is_emergency_number("5551234") is False

    def test_empty_string_is_not_emergency(self) -> None:
        assert self.kl.is_emergency_number("") is False

    def test_none_handled_as_empty(self) -> None:
        # None is falsy, returns False early
        assert self.kl.is_emergency_number(None) is False

    def test_whitespace_stripped(self) -> None:
        assert self.kl.is_emergency_number(" 911 ") is True

    def test_partial_match_not_accepted(self) -> None:
        assert self.kl.is_emergency_number("9111") is False

    def test_prefix_only_not_accepted(self) -> None:
        assert self.kl.is_emergency_number("9") is False


@pytest.mark.unit
class TestIsDirect911:
    """Tests for is_direct_911."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.kl = KarisLawCompliance(pbx_core=MagicMock(), config={})

    def test_direct_911(self) -> None:
        assert self.kl.is_direct_911("911") is True

    def test_legacy_9911_is_not_direct(self) -> None:
        assert self.kl.is_direct_911("9911") is False

    def test_9_dash_911_is_not_direct(self) -> None:
        assert self.kl.is_direct_911("9-911") is False

    def test_empty_returns_false(self) -> None:
        assert self.kl.is_direct_911("") is False

    def test_none_returns_false(self) -> None:
        assert self.kl.is_direct_911(None) is False


@pytest.mark.unit
class TestNormalizeEmergencyNumber:
    """Tests for normalize_emergency_number."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.kl = KarisLawCompliance(pbx_core=MagicMock(), config={})

    def test_911_stays_911(self) -> None:
        assert self.kl.normalize_emergency_number("911") == "911"

    def test_9911_normalized_to_911(self) -> None:
        assert self.kl.normalize_emergency_number("9911") == "911"

    def test_9_dash_911_normalized_to_911(self) -> None:
        assert self.kl.normalize_emergency_number("9-911") == "911"

    def test_non_emergency_returns_unchanged(self) -> None:
        assert self.kl.normalize_emergency_number("5551234") == "5551234"


@pytest.mark.unit
class TestHandleEmergencyCall:
    """Tests for handle_emergency_call."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            # Remove optional attributes so hasattr checks fail by default
            del self.pbx_core.e911_location
            del self.pbx_core.emergency_notification
            del self.pbx_core.extension_registry

            self.config = {
                "features": {
                    "karis_law": {
                        "enabled": True,
                        "auto_notify": True,
                        "require_location": True,
                    }
                }
            }
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config=self.config)

    def test_disabled_returns_error(self) -> None:
        self.kl.enabled = False
        success, info = self.kl.handle_emergency_call("1001", "911", "call-1", ("127.0.0.1", 5060))
        assert success is False
        assert "error" in info

    def test_non_emergency_number_returns_error(self) -> None:
        success, info = self.kl.handle_emergency_call(
            "1001", "5551234", "call-1", ("127.0.0.1", 5060)
        )
        assert success is False
        assert "error" in info

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_successful_emergency_call_with_trunk(self) -> None:
        """Successful emergency call via trunk system fallback."""
        mock_trunk = MagicMock()
        mock_trunk.trunk_id = "trunk-1"
        mock_trunk.name = "Main Trunk"
        self.pbx_core.trunk_system.route_outbound.return_value = (mock_trunk, "911")

        success, info = self.kl.handle_emergency_call("1001", "911", "call-1", ("127.0.0.1", 5060))
        assert success is True
        assert info["success"] is True
        assert info["trunk_id"] == "trunk-1"

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_emergency_call_recorded_in_history(self) -> None:
        """Emergency call is recorded in call history."""
        mock_trunk = MagicMock()
        mock_trunk.trunk_id = "trunk-1"
        mock_trunk.name = "Main Trunk"
        self.pbx_core.trunk_system.route_outbound.return_value = (mock_trunk, "911")

        self.kl.handle_emergency_call("1001", "911", "call-1", ("127.0.0.1", 5060))
        assert len(self.kl.emergency_calls) == 1
        assert self.kl.emergency_calls[0]["call_id"] == "call-1"
        assert self.kl.emergency_calls[0]["caller_extension"] == "1001"

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_emergency_call_history_capped(self) -> None:
        """Emergency call history does not exceed max."""
        mock_trunk = MagicMock()
        mock_trunk.trunk_id = "trunk-1"
        mock_trunk.name = "Main Trunk"
        self.pbx_core.trunk_system.route_outbound.return_value = (mock_trunk, "911")

        self.kl.max_call_history = 3
        for i in range(5):
            self.kl.handle_emergency_call("1001", "911", f"call-{i}", ("127.0.0.1", 5060))

        assert len(self.kl.emergency_calls) == 3

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_auto_notify_triggers_notification(self) -> None:
        """Auto notify triggers emergency notification system."""
        mock_trunk = MagicMock()
        mock_trunk.trunk_id = "trunk-1"
        mock_trunk.name = "Main Trunk"
        self.pbx_core.trunk_system.route_outbound.return_value = (mock_trunk, "911")

        # Add emergency notification back
        mock_notification = MagicMock()
        mock_notification.enabled = True
        self.pbx_core.emergency_notification = mock_notification

        self.kl.handle_emergency_call("1001", "911", "call-1", ("127.0.0.1", 5060))
        mock_notification.on_911_call.assert_called_once()

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_auto_notify_disabled_no_notification(self) -> None:
        """Disabled auto_notify skips notification."""
        self.kl.auto_notify = False
        mock_trunk = MagicMock()
        mock_trunk.trunk_id = "trunk-1"
        mock_trunk.name = "Main Trunk"
        self.pbx_core.trunk_system.route_outbound.return_value = (mock_trunk, "911")

        mock_notification = MagicMock()
        mock_notification.enabled = True
        self.pbx_core.emergency_notification = mock_notification

        self.kl.handle_emergency_call("1001", "911", "call-1", ("127.0.0.1", 5060))
        mock_notification.on_911_call.assert_not_called()

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_no_trunk_system_returns_error(self) -> None:
        """No trunk system returns error routing info."""
        del self.pbx_core.trunk_system

        success, info = self.kl.handle_emergency_call("1001", "911", "call-1", ("127.0.0.1", 5060))
        assert success is True  # handle succeeds, routing has error
        assert info["success"] is False
        assert "error" in info


@pytest.mark.unit
class TestGetLocationInfo:
    """Tests for _get_location_info."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            del self.pbx_core.e911_location
            del self.pbx_core.extension_registry
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config={})

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_no_location_services_returns_none(self) -> None:
        result = self.kl._get_location_info("1001")
        assert result is None

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_e911_location_service_returns_location(self) -> None:
        mock_e911 = MagicMock()
        mock_e911.get_location.return_value = {"dispatchable_location": "123 Main St"}
        self.pbx_core.e911_location = mock_e911

        result = self.kl._get_location_info("1001")
        assert result is not None
        assert result["dispatchable_location"] == "123 Main St"

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_e911_location_returns_none_falls_to_registry(self) -> None:
        mock_e911 = MagicMock()
        mock_e911.get_location.return_value = None
        self.pbx_core.e911_location = mock_e911

        mock_registry = MagicMock()
        mock_registry.get_extension.return_value = {
            "location": "Room 101",
        }
        self.pbx_core.extension_registry = mock_registry

        result = self.kl._get_location_info("1001")
        assert result is not None
        assert result["location"] == "Room 101"

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_extension_registry_no_location_returns_none(self) -> None:
        mock_registry = MagicMock()
        mock_registry.get_extension.return_value = {"name": "User"}
        self.pbx_core.extension_registry = mock_registry

        result = self.kl._get_location_info("1001")
        assert result is None

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_extension_registry_no_extension_returns_none(self) -> None:
        mock_registry = MagicMock()
        mock_registry.get_extension.return_value = None
        self.pbx_core.extension_registry = mock_registry

        result = self.kl._get_location_info("1001")
        assert result is None


@pytest.mark.unit
class TestGetCallerInfo:
    """Tests for _get_caller_info."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            del self.pbx_core.extension_registry
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config={})

    def test_no_registry_returns_basic_info(self) -> None:
        result = self.kl._get_caller_info("1001")
        assert result["extension"] == "1001"
        assert result["name"] == "Unknown"

    def test_with_registry_returns_full_info(self) -> None:
        mock_registry = MagicMock()
        mock_registry.get_extension.return_value = {
            "name": "John Doe",
            "email": "john@example.com",
            "department": "Engineering",
        }
        self.pbx_core.extension_registry = mock_registry

        result = self.kl._get_caller_info("1001")
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"
        assert result["department"] == "Engineering"

    def test_with_registry_no_extension_returns_basic(self) -> None:
        mock_registry = MagicMock()
        mock_registry.get_extension.return_value = None
        self.pbx_core.extension_registry = mock_registry

        result = self.kl._get_caller_info("1001")
        assert result["name"] == "Unknown"


@pytest.mark.unit
class TestRouteEmergencyCall:
    """Tests for _route_emergency_call."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            self.config = {
                "features": {
                    "karis_law": {
                        "enabled": True,
                        "emergency_trunk_id": "e911-trunk",
                    }
                }
            }
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config=self.config)

    def test_no_trunk_system(self) -> None:
        del self.pbx_core.trunk_system
        result = self.kl._route_emergency_call("1001", "911", "call-1", None, {})
        assert result["success"] is False
        assert "error" in result

    def test_global_emergency_trunk_available(self) -> None:
        mock_trunk = MagicMock()
        mock_trunk.name = "E911 Trunk"
        mock_trunk.can_make_call.return_value = True
        self.pbx_core.trunk_system.get_trunk.return_value = mock_trunk

        result = self.kl._route_emergency_call(
            "1001", "911", "call-1", None, {}, nomadic_e911_engine=None
        )
        assert result["success"] is True
        assert result["trunk_id"] == "e911-trunk"

    def test_global_trunk_unavailable_fallback(self) -> None:
        """When global trunk unavailable, fall back to route_outbound."""
        mock_trunk_global = MagicMock()
        mock_trunk_global.can_make_call.return_value = False
        self.pbx_core.trunk_system.get_trunk.return_value = mock_trunk_global

        mock_fallback_trunk = MagicMock()
        mock_fallback_trunk.trunk_id = "fallback-1"
        mock_fallback_trunk.name = "Fallback"
        self.pbx_core.trunk_system.route_outbound.return_value = (mock_fallback_trunk, "911")

        result = self.kl._route_emergency_call(
            "1001", "911", "call-1", None, {}, nomadic_e911_engine=None
        )
        assert result["success"] is True
        assert result["trunk_id"] == "fallback-1"
        assert result.get("fallback") is True

    def test_no_trunk_available_at_all(self) -> None:
        self.pbx_core.trunk_system.get_trunk.return_value = None
        self.pbx_core.trunk_system.route_outbound.return_value = (None, "911")

        self.kl.emergency_trunk_id = None
        result = self.kl._route_emergency_call(
            "1001", "911", "call-1", None, {}, nomadic_e911_engine=None
        )
        assert result["success"] is False
        assert "error" in result


@pytest.mark.unit
class TestFormatDispatchableLocation:
    """Tests for _format_dispatchable_location."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.kl = KarisLawCompliance(pbx_core=MagicMock(), config={})

    def test_full_location(self) -> None:
        loc = {
            "street_address": "123 Main St",
            "building": "HQ",
            "floor": "3",
            "room": "301",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
        }
        result = self.kl._format_dispatchable_location(loc)
        assert "123 Main St" in result
        assert "Building: HQ" in result
        assert "Floor 3" in result
        assert "Room 301" in result
        assert "Springfield" in result
        assert "IL" in result
        assert "62701" in result

    def test_empty_location(self) -> None:
        result = self.kl._format_dispatchable_location({})
        assert result == "Location on file"

    def test_partial_location(self) -> None:
        loc = {"street_address": "456 Oak Ave", "city": "Chicago"}
        result = self.kl._format_dispatchable_location(loc)
        assert "456 Oak Ave" in result
        assert "Chicago" in result


@pytest.mark.unit
class TestTriggerEmergencyNotification:
    """Tests for _trigger_emergency_notification."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            del self.pbx_core.emergency_notification
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config={})

    def test_no_notification_system(self) -> None:
        """No emergency_notification attribute does not raise."""
        self.kl._trigger_emergency_notification("1001", {"name": "Test"}, None, "call-1")
        # Should log warning but not raise

    def test_notification_disabled(self) -> None:
        mock_notif = MagicMock()
        mock_notif.enabled = False
        self.pbx_core.emergency_notification = mock_notif

        self.kl._trigger_emergency_notification("1001", {"name": "Test"}, None, "call-1")
        mock_notif.on_911_call.assert_not_called()

    def test_notification_with_location(self) -> None:
        mock_notif = MagicMock()
        mock_notif.enabled = True
        self.pbx_core.emergency_notification = mock_notif

        location = {
            "dispatchable_location": "123 Main St",
            "building": "HQ",
            "floor": "2",
            "room": "203",
        }
        self.kl._trigger_emergency_notification(
            "1001", {"name": "John"}, location, "call-1"
        )
        mock_notif.on_911_call.assert_called_once()

    def test_notification_without_location(self) -> None:
        mock_notif = MagicMock()
        mock_notif.enabled = True
        self.pbx_core.emergency_notification = mock_notif

        self.kl._trigger_emergency_notification("1001", {"name": "John"}, None, "call-1")
        mock_notif.on_911_call.assert_called_once()


@pytest.mark.unit
class TestGetEmergencyCallHistory:
    """Tests for get_emergency_call_history."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.kl = KarisLawCompliance(pbx_core=MagicMock(), config={})

    def test_empty_history(self) -> None:
        result = self.kl.get_emergency_call_history()
        assert result == []

    def test_filter_by_extension(self) -> None:
        self.kl.emergency_calls = [
            {"caller_extension": "1001", "call_id": "c1"},
            {"caller_extension": "1002", "call_id": "c2"},
            {"caller_extension": "1001", "call_id": "c3"},
        ]
        result = self.kl.get_emergency_call_history(extension="1001")
        assert len(result) == 2
        assert all(c["caller_extension"] == "1001" for c in result)

    def test_limit_applied(self) -> None:
        self.kl.emergency_calls = [
            {"caller_extension": "1001", "call_id": f"c{i}"} for i in range(10)
        ]
        result = self.kl.get_emergency_call_history(limit=3)
        assert len(result) == 3

    def test_no_filter_returns_all(self) -> None:
        self.kl.emergency_calls = [
            {"caller_extension": "1001", "call_id": "c1"},
            {"caller_extension": "1002", "call_id": "c2"},
        ]
        result = self.kl.get_emergency_call_history()
        assert len(result) == 2


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.kl = KarisLawCompliance(pbx_core=MagicMock(), config={})

    def test_statistics_structure(self) -> None:
        stats = self.kl.get_statistics()
        assert "enabled" in stats
        assert "total_emergency_calls" in stats
        assert "auto_notify" in stats
        assert "require_location" in stats
        assert "emergency_trunk_configured" in stats

    def test_statistics_values(self) -> None:
        self.kl.emergency_calls = [{"id": 1}, {"id": 2}]
        stats = self.kl.get_statistics()
        assert stats["total_emergency_calls"] == 2
        assert stats["enabled"] is True
        assert stats["emergency_trunk_configured"] is False


@pytest.mark.unit
class TestValidateCompliance:
    """Tests for validate_compliance."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            del self.pbx_core.emergency_notification
            del self.pbx_core.e911_location
            # Default trunk system returns a tuple for route_outbound
            self.pbx_core.trunk_system.route_outbound.return_value = (MagicMock(), "911")
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config={})

    def test_disabled_not_compliant(self) -> None:
        self.kl.enabled = False
        result = self.kl.validate_compliance()
        assert result["compliant"] is False
        assert any("disabled" in e.lower() for e in result["errors"])

    def test_no_emergency_trunk_warning(self) -> None:
        self.kl.emergency_trunk_id = None
        result = self.kl.validate_compliance()
        assert any("trunk" in w.lower() for w in result["warnings"])

    def test_no_trunk_system_error(self) -> None:
        del self.pbx_core.trunk_system
        result = self.kl.validate_compliance()
        assert result["compliant"] is False

    def test_emergency_trunk_not_found(self) -> None:
        self.kl.emergency_trunk_id = "missing-trunk"
        self.pbx_core.trunk_system.get_trunk.return_value = None
        self.pbx_core.trunk_system.route_outbound.return_value = (MagicMock(), "911")

        result = self.kl.validate_compliance()
        assert result["compliant"] is False
        assert any("not found" in e for e in result["errors"])

    def test_emergency_trunk_unavailable_warning(self) -> None:
        self.kl.emergency_trunk_id = "trunk-e911"
        mock_trunk = MagicMock()
        mock_trunk.can_make_call.return_value = False
        self.pbx_core.trunk_system.get_trunk.return_value = mock_trunk
        self.pbx_core.trunk_system.route_outbound.return_value = (MagicMock(), "911")

        result = self.kl.validate_compliance()
        assert any("not available" in w for w in result["warnings"])

    def test_no_route_for_911(self) -> None:
        self.pbx_core.trunk_system.get_trunk.return_value = None
        self.pbx_core.trunk_system.route_outbound.return_value = (None, None)
        self.kl.emergency_trunk_id = None

        result = self.kl.validate_compliance()
        assert result["compliant"] is False
        assert any("No trunk available" in e for e in result["errors"])

    def test_auto_notify_no_notification_system(self) -> None:
        self.kl.auto_notify = True
        self.pbx_core.trunk_system.route_outbound.return_value = (MagicMock(), "911")

        result = self.kl.validate_compliance()
        assert any("notification" in w.lower() for w in result["warnings"])

    def test_auto_notify_disabled_notification_system(self) -> None:
        self.kl.auto_notify = True
        mock_notif = MagicMock()
        mock_notif.enabled = False
        self.pbx_core.emergency_notification = mock_notif
        self.pbx_core.trunk_system.route_outbound.return_value = (MagicMock(), "911")

        result = self.kl.validate_compliance()
        assert any("notification" in w.lower() for w in result["warnings"])

    def test_require_location_no_e911(self) -> None:
        self.kl.require_location = True
        self.pbx_core.trunk_system.route_outbound.return_value = (MagicMock(), "911")

        result = self.kl.validate_compliance()
        assert any("location" in w.lower() for w in result["warnings"])

    def test_require_location_disabled_e911(self) -> None:
        self.kl.require_location = True
        mock_e911 = MagicMock()
        mock_e911.enabled = False
        self.pbx_core.e911_location = mock_e911
        self.pbx_core.trunk_system.route_outbound.return_value = (MagicMock(), "911")

        result = self.kl.validate_compliance()
        assert any("location" in w.lower() for w in result["warnings"])

    def test_fully_compliant(self) -> None:
        """Fully configured system is compliant."""
        self.kl.emergency_trunk_id = "e911-trunk"

        mock_trunk = MagicMock()
        mock_trunk.can_make_call.return_value = True
        self.pbx_core.trunk_system.get_trunk.return_value = mock_trunk
        self.pbx_core.trunk_system.route_outbound.return_value = (mock_trunk, "911")

        self.kl.auto_notify = False
        self.kl.require_location = False

        result = self.kl.validate_compliance()
        assert result["compliant"] is True
        assert len(result["errors"]) == 0


@pytest.mark.unit
class TestGetNomadicE911Engine:
    """Tests for _get_nomadic_e911_engine."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config={})

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False)
    def test_nomadic_not_available(self) -> None:
        result = self.kl._get_nomadic_e911_engine()
        assert result is None

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", True)
    def test_no_database(self) -> None:
        del self.pbx_core.database
        result = self.kl._get_nomadic_e911_engine()
        assert result is None

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", True)
    def test_database_disabled(self) -> None:
        self.pbx_core.database.enabled = False
        result = self.kl._get_nomadic_e911_engine()
        assert result is None

    @patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", True)
    @patch("pbx.features.karis_law.NomadicE911Engine")
    def test_engine_creation_error(self, mock_engine_cls) -> None:
        self.pbx_core.database.enabled = True
        mock_engine_cls.side_effect = RuntimeError("init error")

        result = self.kl._get_nomadic_e911_engine()
        assert result is None


@pytest.mark.unit
class TestGetSiteEmergencyTrunk:
    """Tests for _get_site_emergency_trunk."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config={})

    def test_no_engine_returns_none(self) -> None:
        result = self.kl._get_site_emergency_trunk("1001", nomadic_e911_engine=None)
        # Without NOMADIC_E911_AVAILABLE, engine is None
        with patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False):
            result = self.kl._get_site_emergency_trunk("1001")
            assert result is None

    def test_with_engine_and_site_trunk(self) -> None:
        mock_engine = MagicMock()
        mock_engine.get_location.return_value = {"ip_address": "10.0.0.1"}
        mock_engine.find_site_by_ip.return_value = {"emergency_trunk": "site-trunk-1"}

        result = self.kl._get_site_emergency_trunk(
            "1001", location_info=None, nomadic_e911_engine=mock_engine
        )
        assert result == "site-trunk-1"

    def test_with_engine_no_ip_address(self) -> None:
        mock_engine = MagicMock()
        mock_engine.get_location.return_value = {"some_field": "value"}

        result = self.kl._get_site_emergency_trunk(
            "1001", location_info=None, nomadic_e911_engine=mock_engine
        )
        assert result is None

    def test_with_location_info_provided(self) -> None:
        mock_engine = MagicMock()
        mock_engine.find_site_by_ip.return_value = {"emergency_trunk": "site-trunk-2"}

        location = {"ip_address": "10.0.0.5"}
        result = self.kl._get_site_emergency_trunk(
            "1001", location_info=location, nomadic_e911_engine=mock_engine
        )
        assert result == "site-trunk-2"

    def test_site_has_no_emergency_trunk(self) -> None:
        mock_engine = MagicMock()
        mock_engine.find_site_by_ip.return_value = {"name": "Site A"}

        location = {"ip_address": "10.0.0.5"}
        result = self.kl._get_site_emergency_trunk(
            "1001", location_info=location, nomadic_e911_engine=mock_engine
        )
        assert result is None

    def test_exception_returns_none(self) -> None:
        mock_engine = MagicMock()
        mock_engine.get_location.side_effect = KeyError("oops")

        result = self.kl._get_site_emergency_trunk(
            "1001", location_info=None, nomadic_e911_engine=mock_engine
        )
        assert result is None


@pytest.mark.unit
class TestGetSiteInfo:
    """Tests for _get_site_info."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.karis_law.get_logger"):
            from pbx.features.karis_law import KarisLawCompliance

            self.pbx_core = MagicMock()
            self.kl = KarisLawCompliance(pbx_core=self.pbx_core, config={})

    def test_no_engine_returns_none(self) -> None:
        with patch("pbx.features.karis_law.NOMADIC_E911_AVAILABLE", False):
            result = self.kl._get_site_info("1001")
            assert result is None

    def test_with_engine_returns_site(self) -> None:
        mock_engine = MagicMock()
        mock_engine.get_location.return_value = {"ip_address": "10.0.0.1"}
        mock_engine.find_site_by_ip.return_value = {
            "psap_number": "911",
            "elin": "5551234567",
        }

        result = self.kl._get_site_info("1001", nomadic_e911_engine=mock_engine)
        assert result is not None
        assert result["psap_number"] == "911"

    def test_no_ip_address_returns_none(self) -> None:
        mock_engine = MagicMock()
        mock_engine.get_location.return_value = {}

        result = self.kl._get_site_info("1001", nomadic_e911_engine=mock_engine)
        assert result is None

    def test_no_location_returns_none(self) -> None:
        mock_engine = MagicMock()
        mock_engine.get_location.return_value = None

        result = self.kl._get_site_info("1001", nomadic_e911_engine=mock_engine)
        assert result is None

    def test_exception_returns_none(self) -> None:
        mock_engine = MagicMock()
        mock_engine.get_location.side_effect = TypeError("bad")

        result = self.kl._get_site_info("1001", nomadic_e911_engine=mock_engine)
        assert result is None
