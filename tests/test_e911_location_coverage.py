"""
Tests for E911 Location Service
Comprehensive coverage of E911LocationService (single site, multi-building)
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.e911_location import E911LocationService


@pytest.mark.unit
class TestE911LocationServiceInit:
    """Test E911LocationService initialization"""

    @patch("pbx.features.e911_location.get_logger")
    def test_init_enabled_with_buildings(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with enabled config and custom buildings"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "site_address": {
                        "address": "123 Main St",
                        "city": "Springfield",
                        "state": "IL",
                        "zip_code": "62701",
                    },
                    "buildings": [
                        {"id": "hq", "name": "Headquarters", "floors": 5},
                        {"id": "annex", "name": "Annex Building", "floors": 2},
                    ],
                }
            }
        }
        service = E911LocationService(config)

        assert service.enabled is True
        assert len(service.buildings) == 2
        assert "hq" in service.buildings
        assert "annex" in service.buildings
        assert service.buildings["hq"]["name"] == "Headquarters"
        assert service.site_address["address"] == "123 Main St"

    @patch("pbx.features.e911_location.get_logger")
    def test_init_enabled_default_buildings(self, mock_get_logger: MagicMock) -> None:
        """Test initialization creates default buildings when none configured"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                }
            }
        }
        service = E911LocationService(config)

        assert service.enabled is True
        assert len(service.buildings) == 3
        assert "building_a" in service.buildings
        assert "building_b" in service.buildings
        assert "building_c" in service.buildings
        assert service.buildings["building_a"]["floors"] == 2
        assert service.buildings["building_c"]["floors"] == 1

    @patch("pbx.features.e911_location.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when disabled"""
        config = {
            "features": {
                "e911": {
                    "enabled": False,
                }
            }
        }
        service = E911LocationService(config)

        assert service.enabled is False
        assert service.buildings == {}

    @patch("pbx.features.e911_location.get_logger")
    def test_init_none_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with None config"""
        service = E911LocationService(None)

        assert service.enabled is False
        assert service.config == {}
        assert service.buildings == {}
        assert service.device_locations == {}
        assert service.emergency_calls == []

    @patch("pbx.features.e911_location.get_logger")
    def test_init_no_config_arg(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with no config argument (default)"""
        service = E911LocationService()

        assert service.enabled is False

    @patch("pbx.features.e911_location.get_logger")
    def test_init_empty_config(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with empty config"""
        service = E911LocationService({})

        assert service.enabled is False
        assert service.site_address == {}

    @patch("pbx.features.e911_location.get_logger")
    def test_init_site_address_default(self, mock_get_logger: MagicMock) -> None:
        """Test initialization defaults to empty site address"""
        service = E911LocationService({"features": {"e911": {"enabled": False}}})

        assert service.site_address == {}


@pytest.mark.unit
class TestE911RegisterLocation:
    """Test E911LocationService.register_location"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "buildings": [
                        {"id": "building_a", "name": "Building A", "floors": 2},
                        {"id": "building_b", "name": "Building B", "floors": 3},
                    ],
                }
            }
        }
        with patch("pbx.features.e911_location.get_logger"):
            self.service = E911LocationService(config)

    def test_register_location_full(self) -> None:
        """Test registering full location with floor and room"""
        result = self.service.register_location("ext-1001", "building_a", "2", "201")

        assert result is True
        loc = self.service.device_locations["ext-1001"]
        assert loc["building_id"] == "building_a"
        assert loc["floor"] == "2"
        assert loc["room"] == "201"
        assert isinstance(loc["registered_at"], datetime)

    def test_register_location_building_only(self) -> None:
        """Test registering location with building only"""
        result = self.service.register_location("ext-1002", "building_b")

        assert result is True
        loc = self.service.device_locations["ext-1002"]
        assert loc["building_id"] == "building_b"
        assert loc["floor"] is None
        assert loc["room"] is None

    def test_register_location_with_floor_no_room(self) -> None:
        """Test registering with floor but no room"""
        result = self.service.register_location("ext-1003", "building_a", floor="1")

        assert result is True
        loc = self.service.device_locations["ext-1003"]
        assert loc["floor"] == "1"
        assert loc["room"] is None

    def test_register_location_invalid_building(self) -> None:
        """Test registering location with invalid building ID"""
        result = self.service.register_location("ext-1001", "nonexistent_building")

        assert result is False
        assert "ext-1001" not in self.service.device_locations

    def test_register_location_disabled(self) -> None:
        """Test registering location when service is disabled"""
        with patch("pbx.features.e911_location.get_logger"):
            service = E911LocationService({"features": {"e911": {"enabled": False}}})

        result = service.register_location("ext-1001", "building_a")

        assert result is False

    def test_register_location_overwrites(self) -> None:
        """Test that re-registering overwrites previous location"""
        self.service.register_location("ext-1001", "building_a", "1", "101")
        self.service.register_location("ext-1001", "building_b", "3", "301")

        loc = self.service.device_locations["ext-1001"]
        assert loc["building_id"] == "building_b"
        assert loc["floor"] == "3"
        assert loc["room"] == "301"


@pytest.mark.unit
class TestE911GetLocation:
    """Test E911LocationService.get_location"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "buildings": [
                        {"id": "building_a", "name": "Building A", "floors": 2},
                    ],
                }
            }
        }
        with patch("pbx.features.e911_location.get_logger"):
            self.service = E911LocationService(config)

    def test_get_location_exists(self) -> None:
        """Test getting an existing location"""
        self.service.register_location("ext-1001", "building_a", "1", "100")

        result = self.service.get_location("ext-1001")

        assert result is not None
        assert result["building_id"] == "building_a"

    def test_get_location_not_found(self) -> None:
        """Test getting location for unregistered device"""
        result = self.service.get_location("unknown")

        assert result is None


@pytest.mark.unit
class TestE911ListBuildings:
    """Test E911LocationService.list_buildings"""

    @patch("pbx.features.e911_location.get_logger")
    def test_list_buildings_custom(self, mock_get_logger: MagicMock) -> None:
        """Test listing custom buildings"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "buildings": [
                        {"id": "hq", "name": "HQ", "floors": 5},
                        {"id": "warehouse", "name": "Warehouse", "floors": 1},
                    ],
                }
            }
        }
        service = E911LocationService(config)

        result = service.list_buildings()

        assert len(result) == 2
        ids = {b["id"] for b in result}
        assert "hq" in ids
        assert "warehouse" in ids

        hq = next(b for b in result if b["id"] == "hq")
        assert hq["name"] == "HQ"
        assert hq["floors"] == 5

    @patch("pbx.features.e911_location.get_logger")
    def test_list_buildings_default(self, mock_get_logger: MagicMock) -> None:
        """Test listing default buildings"""
        config = {"features": {"e911": {"enabled": True}}}
        service = E911LocationService(config)

        result = service.list_buildings()

        assert len(result) == 3

    @patch("pbx.features.e911_location.get_logger")
    def test_list_buildings_empty_when_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test listing buildings when service is disabled"""
        service = E911LocationService({"features": {"e911": {"enabled": False}}})

        result = service.list_buildings()

        assert result == []

    @patch("pbx.features.e911_location.get_logger")
    def test_list_buildings_missing_floors(self, mock_get_logger: MagicMock) -> None:
        """Test listing building that has no floors key"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "buildings": [
                        {"id": "shed", "name": "Shed"},
                    ],
                }
            }
        }
        service = E911LocationService(config)

        result = service.list_buildings()

        assert len(result) == 1
        assert result[0]["floors"] == 1  # default


@pytest.mark.unit
class TestE911RouteEmergencyCall:
    """Test E911LocationService.route_emergency_call"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "site_address": {
                        "address": "123 Main St",
                        "city": "Springfield",
                        "state": "IL",
                        "zip_code": "62701",
                    },
                    "buildings": [
                        {"id": "building_a", "name": "Building A", "floors": 2},
                        {"id": "building_b", "name": "Building B", "floors": 3},
                    ],
                }
            }
        }
        with patch("pbx.features.e911_location.get_logger"):
            self.service = E911LocationService(config)

    def test_route_emergency_call_full_location(self) -> None:
        """Test routing emergency call with full location"""
        self.service.register_location("ext-1001", "building_a", "2", "201")

        result = self.service.route_emergency_call("ext-1001", {"name": "John"})

        assert result["device_id"] == "ext-1001"
        assert result["routing"] == "emergency_trunk"
        assert result["location"]["building"] == "Building A"
        assert result["location"]["building_id"] == "building_a"
        assert result["location"]["floor"] == "2"
        assert result["location"]["room"] == "201"
        assert "123 Main St" in result["dispatchable_location"]
        assert "Building: Building A" in result["dispatchable_location"]
        assert "Floor 2" in result["dispatchable_location"]
        assert "Room 201" in result["dispatchable_location"]
        assert "Springfield" in result["dispatchable_location"]

    def test_route_emergency_call_building_only(self) -> None:
        """Test routing emergency call with building only"""
        self.service.register_location("ext-1002", "building_b")

        result = self.service.route_emergency_call("ext-1002", {"name": "Jane"})

        assert result["device_id"] == "ext-1002"
        assert result["location"]["floor"] is None
        assert result["location"]["room"] is None
        assert "Floor" not in result["dispatchable_location"]
        assert "Room" not in result["dispatchable_location"]

    def test_route_emergency_call_not_enabled(self) -> None:
        """Test routing emergency call when service is disabled"""
        with patch("pbx.features.e911_location.get_logger"):
            service = E911LocationService({"features": {"e911": {"enabled": False}}})

        result = service.route_emergency_call("ext-1001", {"name": "John"})

        assert "error" in result
        assert "not enabled" in result["error"]

    def test_route_emergency_call_no_location(self) -> None:
        """Test routing emergency call for unregistered device"""
        result = self.service.route_emergency_call("unknown-device", {"name": "John"})

        assert "error" in result
        assert "No location registered" in result["error"]
        assert result["device_id"] == "unknown-device"

    def test_route_emergency_call_building_not_found(self) -> None:
        """Test routing when building is missing from buildings dict"""
        # Manually register with a building that we then remove
        self.service.device_locations["ext-1001"] = {
            "building_id": "deleted_building",
            "floor": "1",
            "room": "100",
            "registered_at": datetime.now(UTC),
        }

        result = self.service.route_emergency_call("ext-1001", {"name": "John"})

        assert "error" in result
        assert "Building not found" in result["error"]

    def test_route_emergency_call_logs_call(self) -> None:
        """Test that routing logs the emergency call"""
        self.service.register_location("ext-1001", "building_a", "1", "101")

        self.service.route_emergency_call("ext-1001", {"name": "John", "ext": "1001"})

        assert len(self.service.emergency_calls) == 1
        call = self.service.emergency_calls[0]
        assert call["device_id"] == "ext-1001"
        assert call["caller_info"]["name"] == "John"
        assert isinstance(call["timestamp"], datetime)

    def test_route_emergency_call_multiple_calls(self) -> None:
        """Test multiple emergency calls are all logged"""
        self.service.register_location("ext-1001", "building_a")
        self.service.register_location("ext-1002", "building_b")

        self.service.route_emergency_call("ext-1001", {"name": "John"})
        self.service.route_emergency_call("ext-1002", {"name": "Jane"})

        assert len(self.service.emergency_calls) == 2

    def test_route_emergency_call_with_floor_and_room_logging(self) -> None:
        """Test that floor and room are logged when present"""
        self.service.register_location("ext-1001", "building_a", "2", "201")

        result = self.service.route_emergency_call("ext-1001", {"name": "John"})

        assert result["location"]["floor"] == "2"
        assert result["location"]["room"] == "201"

    def test_route_emergency_call_no_floor_no_room_logging(self) -> None:
        """Test logging when floor and room are not set"""
        self.service.register_location("ext-1001", "building_a")

        result = self.service.route_emergency_call("ext-1001", {"name": "John"})

        # Should succeed without floor/room
        assert result["routing"] == "emergency_trunk"


@pytest.mark.unit
class TestE911FormatDispatchableLocation:
    """Test E911LocationService._format_dispatchable_location"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        with patch("pbx.features.e911_location.get_logger"):
            self.service = E911LocationService({"features": {"e911": {"enabled": True}}})

    def test_format_full_location(self) -> None:
        """Test formatting with all location fields"""
        location = {
            "building": "Building A",
            "floor": "2",
            "room": "201",
            "site_address": {
                "address": "123 Main St",
                "city": "Springfield",
                "state": "IL",
                "zip_code": "62701",
            },
        }

        result = self.service._format_dispatchable_location(location)

        assert "123 Main St" in result
        assert "Building: Building A" in result
        assert "Floor 2" in result
        assert "Room 201" in result
        assert "Springfield" in result
        assert "IL" in result
        assert "62701" in result

    def test_format_minimal_location(self) -> None:
        """Test formatting with minimal location fields"""
        location = {"site_address": {}}

        result = self.service._format_dispatchable_location(location)

        assert result == ""

    def test_format_no_floor_no_room(self) -> None:
        """Test formatting without floor or room"""
        location = {
            "building": "Building A",
            "site_address": {"address": "123 Main St"},
        }

        result = self.service._format_dispatchable_location(location)

        assert "Floor" not in result
        assert "Room" not in result
        assert "123 Main St" in result
        assert "Building: Building A" in result

    def test_format_no_building(self) -> None:
        """Test formatting without building"""
        location = {
            "floor": "1",
            "room": "100",
            "site_address": {"address": "456 Elm St"},
        }

        result = self.service._format_dispatchable_location(location)

        assert "Building" not in result
        assert "Floor 1" in result
        assert "Room 100" in result

    def test_format_no_site_address(self) -> None:
        """Test formatting without site_address"""
        location = {"building": "Building A"}

        result = self.service._format_dispatchable_location(location)

        assert "Building: Building A" in result

    def test_format_partial_site_address(self) -> None:
        """Test formatting with partial site address"""
        location = {
            "site_address": {
                "city": "Chicago",
                "state": "IL",
            },
        }

        result = self.service._format_dispatchable_location(location)

        assert "Chicago" in result
        assert "IL" in result


@pytest.mark.unit
class TestE911EmergencyCallHistory:
    """Test E911LocationService.get_emergency_call_history"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "buildings": [
                        {"id": "building_a", "name": "Building A", "floors": 2},
                    ],
                }
            }
        }
        with patch("pbx.features.e911_location.get_logger"):
            self.service = E911LocationService(config)

    def test_get_history_all(self) -> None:
        """Test getting all emergency call history"""
        self.service.register_location("ext-1001", "building_a")
        self.service.route_emergency_call("ext-1001", {"name": "John"})
        self.service.route_emergency_call("ext-1001", {"name": "John again"})

        result = self.service.get_emergency_call_history()

        assert len(result) == 2

    def test_get_history_filtered_by_device(self) -> None:
        """Test getting history filtered by device ID"""
        self.service.register_location("ext-1001", "building_a")
        self.service.register_location("ext-1002", "building_a")
        self.service.route_emergency_call("ext-1001", {"name": "John"})
        self.service.route_emergency_call("ext-1002", {"name": "Jane"})

        result = self.service.get_emergency_call_history("ext-1001")

        assert len(result) == 1
        assert result[0]["device_id"] == "ext-1001"

    def test_get_history_empty(self) -> None:
        """Test getting history when no calls have been made"""
        result = self.service.get_emergency_call_history()

        assert result == []

    def test_get_history_no_match(self) -> None:
        """Test getting history for a device with no calls"""
        self.service.register_location("ext-1001", "building_a")
        self.service.route_emergency_call("ext-1001", {"name": "John"})

        result = self.service.get_emergency_call_history("ext-9999")

        assert result == []

    def test_get_history_none_returns_all(self) -> None:
        """Test that None device_id returns all history"""
        self.service.register_location("ext-1001", "building_a")
        self.service.route_emergency_call("ext-1001", {"name": "John"})

        result = self.service.get_emergency_call_history(None)

        assert len(result) == 1


@pytest.mark.unit
class TestE911Statistics:
    """Test E911LocationService.get_statistics"""

    @patch("pbx.features.e911_location.get_logger")
    def test_statistics_initial(self, mock_get_logger: MagicMock) -> None:
        """Test statistics right after initialization"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "buildings": [
                        {"id": "building_a", "name": "Building A", "floors": 2},
                        {"id": "building_b", "name": "Building B", "floors": 3},
                    ],
                }
            }
        }
        service = E911LocationService(config)

        stats = service.get_statistics()

        assert stats["enabled"] is True
        assert stats["buildings"] == 2
        assert stats["registered_devices"] == 0
        assert stats["emergency_calls"] == 0

    @patch("pbx.features.e911_location.get_logger")
    def test_statistics_with_registrations_and_calls(self, mock_get_logger: MagicMock) -> None:
        """Test statistics after registrations and emergency calls"""
        config = {
            "features": {
                "e911": {
                    "enabled": True,
                    "buildings": [
                        {"id": "building_a", "name": "Building A", "floors": 2},
                    ],
                }
            }
        }
        service = E911LocationService(config)
        service.register_location("ext-1001", "building_a")
        service.register_location("ext-1002", "building_a")
        service.route_emergency_call("ext-1001", {"name": "John"})

        stats = service.get_statistics()

        assert stats["registered_devices"] == 2
        assert stats["emergency_calls"] == 1

    @patch("pbx.features.e911_location.get_logger")
    def test_statistics_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test statistics when service is disabled"""
        service = E911LocationService({"features": {"e911": {"enabled": False}}})

        stats = service.get_statistics()

        assert stats["enabled"] is False
        assert stats["buildings"] == 0
        assert stats["registered_devices"] == 0
        assert stats["emergency_calls"] == 0
