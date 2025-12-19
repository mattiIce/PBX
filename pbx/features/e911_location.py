"""
E911 Support for Single Site with Multiple Buildings
Simplified location-based emergency routing for one site with 3 buildings
"""

from datetime import datetime
from typing import Dict, List, Optional

from pbx.utils.logger import get_logger


class E911LocationService:
    """Service for managing E911 locations and routing (single site, 3 buildings)"""

    def __init__(self, config=None):
        """Initialize E911 location service"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get("features", {}).get("e911", {}).get("enabled", False)

        # Single site with 3 buildings
        self.site_address = self.config.get("features", {}).get("e911", {}).get("site_address", {})
        self.buildings = {}  # building_id -> building info
        self.device_locations = {}  # device_id -> (building_id, floor, room)
        self.emergency_calls = []  # Log of emergency calls

        if self.enabled:
            self.logger.info("E911 location service initialized (single site, multi-building)")
            self._load_buildings()

    def _load_buildings(self):
        """Load building configurations for the site"""
        # Load from config or create defaults
        buildings_config = self.config.get("features", {}).get("e911", {}).get("buildings", [])

        if not buildings_config:
            # Default 3 buildings
            buildings_config = [
                {"id": "building_a", "name": "Building A", "floors": 2},
                {"id": "building_b", "name": "Building B", "floors": 2},
                {"id": "building_c", "name": "Building C", "floors": 1},
            ]

        for building in buildings_config:
            self.buildings[building["id"]] = building

        self.logger.info(f"Loaded {len(self.buildings)} buildings for E911")

    def register_location(
        self,
        device_id: str,
        building_id: str,
        floor: Optional[str] = None,
        room: Optional[str] = None,
    ) -> bool:
        """
        Register a location for a device/extension (simplified for single site)

        Args:
            device_id: Device or extension identifier
            building_id: Building identifier (building_a, building_b, building_c)
            floor: Floor number/name (optional)
            room: Room number/name (optional)

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        if building_id not in self.buildings:
            self.logger.error(f"Invalid building ID: {building_id}")
            return False

        self.device_locations[device_id] = {
            "building_id": building_id,
            "floor": floor,
            "room": room,
            "registered_at": datetime.now(),
        }

        self.logger.info(
            f"Registered E911 location for {device_id}: "
            f"{self.buildings[building_id]['name']}"
            + (f", Floor {floor}" if floor else "")
            + (f", Room {room}" if room else "")
        )
        return True

    def get_location(self, device_id: str) -> Optional[Dict]:
        """Get registered location for a device"""
        return self.device_locations.get(device_id)

    def list_buildings(self) -> List[Dict]:
        """List all buildings"""
        return [
            {"id": bid, "name": binfo["name"], "floors": binfo.get("floors", 1)}
            for bid, binfo in self.buildings.items()
        ]

    def route_emergency_call(self, device_id: str, caller_info: Dict) -> Dict:
        """
        Route an emergency call with location information

        Args:
            device_id: Device making the call
            caller_info: Caller information

        Returns:
            Routing information with location
        """
        if not self.enabled:
            return {"error": "E911 not enabled"}

        location = self.get_location(device_id)
        if not location:
            self.logger.error(f"No E911 location registered for {device_id}")
            return {"error": "No location registered", "device_id": device_id}

        building = self.buildings.get(location["building_id"])
        if not building:
            self.logger.error(f"Building {location['building_id']} not found in buildings database")
            return {"error": "Building not found", "device_id": device_id}

        # Format full location
        full_location = {
            "building": building["name"],
            "building_id": location["building_id"],
            "floor": location.get("floor"),
            "room": location.get("room"),
            "site_address": self.site_address,
        }

        # Log emergency call
        call_record = {
            "device_id": device_id,
            "caller_info": caller_info,
            "location": full_location,
            "timestamp": datetime.now(),
        }
        self.emergency_calls.append(call_record)

        self.logger.critical(f"EMERGENCY CALL from {device_id}")
        self.logger.critical(f"  Site: {self.site_address.get('address', 'N/A')}")
        self.logger.critical(f"  Building: {building['name']}")
        if location.get("floor"):
            self.logger.critical(f"  Floor: {location['floor']}")
        if location.get("room"):
            self.logger.critical(f"  Room: {location['room']}")

        return {
            "device_id": device_id,
            "location": full_location,
            "dispatchable_location": self._format_dispatchable_location(full_location),
            "routing": "emergency_trunk",
        }

    def _format_dispatchable_location(self, location: Dict) -> str:
        """Format location as dispatchable location string (Ray Baum's Act)"""
        site = location.get("site_address", {})
        parts = []

        # Site address
        if site.get("address"):
            parts.append(site["address"])

        # Building
        if location.get("building"):
            parts.append(f"Building: {location['building']}")

        # Floor and room
        if location.get("floor"):
            parts.append(f"Floor {location['floor']}")
        if location.get("room"):
            parts.append(f"Room {location['room']}")

        # City, state, zip
        if site.get("city"):
            parts.append(site["city"])
        if site.get("state"):
            parts.append(site["state"])
        if site.get("zip_code"):
            parts.append(site["zip_code"])

        return ", ".join(parts)

    def get_emergency_call_history(self, device_id: Optional[str] = None) -> List[Dict]:
        """Get history of emergency calls"""
        if device_id:
            return [call for call in self.emergency_calls if call["device_id"] == device_id]
        return self.emergency_calls

    def get_statistics(self) -> Dict:
        """Get E911 service statistics"""
        return {
            "enabled": self.enabled,
            "buildings": len(self.buildings),
            "registered_devices": len(self.device_locations),
            "emergency_calls": len(self.emergency_calls),
        }
