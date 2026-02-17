"""Comprehensive tests for mobile_number_portability feature module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.mobile_number_portability import (
    MobileNumberPortability,
    get_mobile_number_portability,
)


@pytest.mark.unit
class TestMobileNumberPortabilityInit:
    """Tests for MobileNumberPortability initialization."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_default_initialization(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        assert mnp.enabled is False
        assert mnp.sim_ring_enabled is True
        assert mnp.mobile_first is False
        assert mnp.number_mappings == {}
        assert mnp.total_mappings == 0
        assert mnp.calls_to_mobile == 0
        assert mnp.calls_to_desk == 0

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_initialization_with_config(self, mock_logger: MagicMock) -> None:
        config = {
            "features": {
                "mobile_number_portability": {
                    "enabled": True,
                    "simultaneous_ring": False,
                    "mobile_first": True,
                }
            }
        }
        mnp = MobileNumberPortability(config=config)
        assert mnp.enabled is True
        assert mnp.sim_ring_enabled is False
        assert mnp.mobile_first is True


@pytest.mark.unit
class TestMapNumberToMobile:
    """Tests for map_number_to_mobile method."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_basic_mapping(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        result = mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        assert result["success"] is True
        assert result["business_number"] == "5551234"
        assert "5551234" in mnp.number_mappings
        assert mnp.total_mappings == 1

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_mapping_with_settings(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        settings = {
            "simultaneous_ring": False,
            "mobile_first": True,
            "business_hours_only": True,
        }
        _result = mnp.map_number_to_mobile("5551234", "100", "mobile-001", settings=settings)
        mapping = mnp.number_mappings["5551234"]
        assert mapping["simultaneous_ring"] is False
        assert mapping["mobile_first"] is True
        assert mapping["business_hours_only"] is True

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_mapping_defaults(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        mapping = mnp.number_mappings["5551234"]
        assert mapping["simultaneous_ring"] is True
        assert mapping["mobile_first"] is False
        assert mapping["business_hours_only"] is False
        assert mapping["active"] is True
        assert isinstance(mapping["created_at"], datetime)

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_mapping_override(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        mnp.map_number_to_mobile("5551234", "100", "mobile-002")
        assert mnp.number_mappings["5551234"]["mobile_device_id"] == "mobile-002"


@pytest.mark.unit
class TestRouteCall:
    """Tests for route_call method."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_route_no_mapping(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        result = mnp.route_call("5551234", "5559999")
        assert result["route_to"] == "desk_phone"
        assert result["reason"] == "No mobile mapping"

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_route_inactive_mapping(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        mnp.number_mappings["5551234"]["active"] = False
        result = mnp.route_call("5551234", "5559999")
        assert result["route_to"] == "desk_phone"
        assert result["reason"] == "Mapping inactive"

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_route_simultaneous_ring(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        result = mnp.route_call("5551234", "5559999")
        assert result["route_to"] == "both"
        assert len(result["targets"]) == 2
        assert result["strategy"] == "first_answer"
        assert mnp.calls_to_mobile == 1
        assert mnp.calls_to_desk == 1

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_route_mobile_first(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        settings = {"simultaneous_ring": False, "mobile_first": True}
        mnp.map_number_to_mobile("5551234", "100", "mobile-001", settings=settings)
        result = mnp.route_call("5551234", "5559999")
        assert result["route_to"] == "mobile"
        assert result["device_id"] == "mobile-001"
        assert result["failover_to"] == "desk_phone"
        assert mnp.calls_to_mobile == 1

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_route_desk_phone_only(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        settings = {"simultaneous_ring": False, "mobile_first": False}
        mnp.map_number_to_mobile("5551234", "100", "mobile-001", settings=settings)
        result = mnp.route_call("5551234", "5559999")
        assert result["route_to"] == "desk_phone"
        assert result["extension"] == "100"
        assert mnp.calls_to_desk == 1

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_route_business_hours_only_outside(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        settings = {"business_hours_only": True}
        mnp.map_number_to_mobile("5551234", "100", "mobile-001", settings=settings)
        with patch.object(mnp, "_is_business_hours", return_value=False):
            result = mnp.route_call("5551234", "5559999")
            assert result["route_to"] == "desk_phone"
            assert result["reason"] == "Outside business hours"

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_route_business_hours_only_during(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        settings = {"business_hours_only": True}
        mnp.map_number_to_mobile("5551234", "100", "mobile-001", settings=settings)
        with patch.object(mnp, "_is_business_hours", return_value=True):
            result = mnp.route_call("5551234", "5559999")
            assert result["route_to"] == "both"  # Default sim ring


@pytest.mark.unit
class TestIsBusinessHours:
    """Tests for _is_business_hours method."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_during_business_hours(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        # Mock Monday at 10:30 AM UTC
        mock_dt = datetime(2026, 2, 16, 10, 30, tzinfo=UTC)  # Monday
        with patch("pbx.features.mobile_number_portability.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = mnp._is_business_hours()
            assert result is True

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_outside_business_hours(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        # Mock Monday at 8:00 AM UTC (before 9am)
        mock_dt = datetime(2026, 2, 16, 8, 0, tzinfo=UTC)  # Monday
        with patch("pbx.features.mobile_number_portability.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = mnp._is_business_hours()
            assert result is False

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_weekend(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        # Mock Saturday at noon
        mock_dt = datetime(2026, 2, 21, 12, 0, tzinfo=UTC)  # Saturday
        with patch("pbx.features.mobile_number_portability.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = mnp._is_business_hours()
            assert result is False

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_custom_business_hours(self, mock_logger: MagicMock) -> None:
        config = {
            "features": {
                "mobile_number_portability": {
                    "business_hours": {
                        "start_hour": 8,
                        "start_minute": 0,
                        "end_hour": 20,
                        "end_minute": 0,
                        "work_days": [0, 1, 2, 3, 4, 5],  # Mon-Sat
                    }
                }
            }
        }
        mnp = MobileNumberPortability(config=config)
        # Mock Saturday at 10am
        mock_dt = datetime(2026, 2, 21, 10, 0, tzinfo=UTC)  # Saturday
        with patch("pbx.features.mobile_number_portability.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = mnp._is_business_hours()
            assert result is True


@pytest.mark.unit
class TestToggleMapping:
    """Tests for toggle_mapping method."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_toggle_active(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        result = mnp.toggle_mapping("5551234", False)
        assert result is True
        assert mnp.number_mappings["5551234"]["active"] is False

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_toggle_reactivate(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        mnp.toggle_mapping("5551234", False)
        mnp.toggle_mapping("5551234", True)
        assert mnp.number_mappings["5551234"]["active"] is True

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_toggle_not_found(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        result = mnp.toggle_mapping("nonexistent", True)
        assert result is False


@pytest.mark.unit
class TestRemoveMapping:
    """Tests for remove_mapping method."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_remove_existing(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        result = mnp.remove_mapping("5551234")
        assert result is True
        assert "5551234" not in mnp.number_mappings

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_remove_nonexistent(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        result = mnp.remove_mapping("nonexistent")
        assert result is False


@pytest.mark.unit
class TestGetMapping:
    """Tests for get_mapping method."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_get_existing(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        result = mnp.get_mapping("5551234")
        assert result is not None
        assert result["business_number"] == "5551234"

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_get_nonexistent(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        assert mnp.get_mapping("nonexistent") is None


@pytest.mark.unit
class TestGetUserMappings:
    """Tests for get_user_mappings method."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_get_user_mappings(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        mnp.map_number_to_mobile("5555678", "100", "mobile-002")
        mnp.map_number_to_mobile("5559999", "200", "mobile-003")
        result = mnp.get_user_mappings("100")
        assert len(result) == 2

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_get_user_mappings_empty(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        result = mnp.get_user_mappings("100")
        assert result == []


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics method."""

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_get_statistics(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        mnp.route_call("5551234", "5559999")  # simultaneous ring
        stats = mnp.get_statistics()
        assert stats["total_mappings"] == 1
        assert stats["active_mappings"] == 1
        assert stats["calls_to_mobile"] == 1
        assert stats["calls_to_desk"] == 1

    @patch("pbx.features.mobile_number_portability.get_logger")
    def test_get_statistics_inactive_mapping(self, mock_logger: MagicMock) -> None:
        mnp = MobileNumberPortability()
        mnp.map_number_to_mobile("5551234", "100", "mobile-001")
        mnp.toggle_mapping("5551234", False)
        stats = mnp.get_statistics()
        assert stats["total_mappings"] == 1
        assert stats["active_mappings"] == 0


@pytest.mark.unit
class TestGetMobileNumberPortabilitySingleton:
    """Tests for get_mobile_number_portability global function."""

    def test_creates_instance(self) -> None:
        import pbx.features.mobile_number_portability as mod

        original = mod._mobile_number_portability
        mod._mobile_number_portability = None
        try:
            with patch("pbx.features.mobile_number_portability.get_logger"):
                instance = get_mobile_number_portability()
                assert isinstance(instance, MobileNumberPortability)
        finally:
            mod._mobile_number_portability = original

    def test_returns_same_instance(self) -> None:
        import pbx.features.mobile_number_portability as mod

        original = mod._mobile_number_portability
        mod._mobile_number_portability = None
        try:
            with patch("pbx.features.mobile_number_portability.get_logger"):
                i1 = get_mobile_number_portability()
                i2 = get_mobile_number_portability()
                assert i1 is i2
        finally:
            mod._mobile_number_portability = original
