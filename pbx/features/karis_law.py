from __future__ import annotations

"""
Kari's Law Compliance Module

Implements Kari's Law requirements for direct 911 dialing:
- Direct 911 dialing without prefix (no "9-911")
- Immediate routing to emergency services
- Automatic notification to designated contacts
- No delay in emergency call routing

Federal law requires multi-line telephone systems (MLTS) to allow direct
dialing of 911 without requiring a prefix or access code.

References:
- 47 CFR § 9.16 (Kari's Law)
- RAY BAUM'S Act (dispatchable location)
"""

import re
from datetime import UTC, datetime
from typing import Any, ClassVar

from pbx.utils.logger import get_logger

# Import for multi-site E911 support (avoid repeated imports in methods)
try:
    from pbx.features.nomadic_e911 import NomadicE911Engine

    NOMADIC_E911_AVAILABLE = True
except ImportError:
    NOMADIC_E911_AVAILABLE = False


class KarisLawCompliance:
    """
    Kari's Law compliance handler for direct 911 dialing

    Ensures that:
    1. 911 can be dialed directly without prefix
    2. Emergency calls are routed immediately
    3. Designated contacts are notified automatically
    4. Location information is provided (Ray Baum's Act)
    """

    # Emergency number patterns (Kari's Law)
    EMERGENCY_PATTERNS: ClassVar[list[str]] = [
        r"^911$",  # Standard 911
        r"^9911$",  # Legacy prefix (should be deprecated but supported)
        r"^9-911$",  # Legacy prefix with dash
    ]

    # Direct 911 pattern (primary)
    DIRECT_911_PATTERN = r"^911$"

    def __init__(self, pbx_core: Any | None, config: dict | None = None) -> None:
        """
        Initialize Kari's Law compliance module

        Args:
            pbx_core: Reference to PBX core
            config: Configuration dictionary
        """
        self.pbx_core = pbx_core
        self.logger = get_logger()
        self.config = config or {}

        # Kari's Law settings
        self.enabled = self.config.get("features", {}).get("karis_law", {}).get("enabled", True)
        self.auto_notify = (
            self.config.get("features", {}).get("karis_law", {}).get("auto_notify", True)
        )
        self.require_location = (
            self.config.get("features", {}).get("karis_law", {}).get("require_location", True)
        )

        # Emergency trunk configuration
        self.emergency_trunk_id = (
            self.config.get("features", {}).get("karis_law", {}).get("emergency_trunk_id")
        )

        # Call tracking
        self.emergency_calls = []
        self.max_call_history = 1000

        if self.enabled:
            self.logger.info("Kari's Law compliance module initialized")
            self.logger.info("Direct 911 dialing: ENABLED")
            self.logger.info(f"Auto-notification: {'ENABLED' if self.auto_notify else 'DISABLED'}")
            self.logger.info(
                f"Location requirement: {'ENABLED' if self.require_location else 'DISABLED'}"
            )
        else:
            self.logger.warning("Kari's Law compliance DISABLED - not recommended for production")

    def is_emergency_number(self, number: str) -> bool:
        """
        Check if number is an emergency number

        Args:
            number: Phone number to check

        Returns:
            True if number matches emergency patterns
        """
        if not number:
            return False

        number_str = str(number).strip()

        return any(re.match(pattern, number_str) for pattern in self.EMERGENCY_PATTERNS)

    def is_direct_911(self, number: str) -> bool:
        """
        Check if number is direct 911 (without prefix)

        Args:
            number: Phone number to check

        Returns:
            True if number is direct 911
        """
        if not number:
            return False

        number_str = str(number).strip()
        return re.match(self.DIRECT_911_PATTERN, number_str) is not None

    def normalize_emergency_number(self, number: str) -> str:
        """
        Normalize emergency number to standard 911

        Removes legacy prefixes (9-911, 9911) and normalizes to 911

        Args:
            number: Emergency number to normalize

        Returns:
            Normalized number (911)
        """
        if not self.is_emergency_number(number):
            return number

        # Strip legacy prefix if present
        number_str = str(number).strip()

        # Remove prefix (9 or 9-)
        if number_str.startswith("9-") or (number_str.startswith("9") and len(number_str) == 4):
            return "911"

        return "911"

    def handle_emergency_call(
        self, caller_extension: str, dialed_number: str, call_id: str, from_addr: tuple
    ) -> tuple[bool, dict]:
        """
        Handle emergency call according to Kari's Law

        Args:
            caller_extension: Extension making the call
            dialed_number: Number dialed (911, 9911, etc.)
            call_id: Call identifier
            from_addr: Caller address

        Returns:
            tuple of (success, routing_info)
        """
        if not self.enabled:
            return False, {"error": "Kari's Law compliance disabled"}

        if not self.is_emergency_number(dialed_number):
            return False, {"error": "Not an emergency number"}

        # Normalize to 911
        normalized_number = self.normalize_emergency_number(dialed_number)

        self.logger.critical("=" * 70)
        self.logger.critical("🚨 EMERGENCY CALL (KARI'S LAW)")
        self.logger.critical("=" * 70)
        self.logger.critical(f"Caller Extension: {caller_extension}")
        self.logger.critical(f"Dialed Number: {dialed_number}")
        self.logger.critical(f"Normalized: {normalized_number}")
        self.logger.critical(f"Call ID: {call_id}")
        self.logger.critical(f"Time: {datetime.now(UTC).isoformat()}")

        # Get location information (Ray Baum's Act)
        location_info = self._get_location_info(caller_extension)

        if location_info:
            self.logger.critical(
                f"Location: {location_info.get('dispatchable_location', 'Unknown')}"
            )
        else:
            self.logger.warning("⚠️  Location information not available")
            if self.require_location:
                self.logger.warning("Location is required but not configured for this extension")

        # Get caller information
        caller_info = self._get_caller_info(caller_extension)

        # Create nomadic E911 engine once for this call (cache for performance)
        nomadic_e911_engine = self._get_nomadic_e911_engine()

        # Route to emergency trunk
        routing_info = self._route_emergency_call(
            caller_extension=caller_extension,
            normalized_number=normalized_number,
            call_id=call_id,
            location_info=location_info,
            caller_info=caller_info,
            nomadic_e911_engine=nomadic_e911_engine,
        )

        # Automatic notification (Kari's Law requirement)
        if self.auto_notify:
            self._trigger_emergency_notification(
                caller_extension=caller_extension,
                caller_info=caller_info,
                location_info=location_info,
                call_id=call_id,
            )

        # Record emergency call
        call_record = {
            "call_id": call_id,
            "caller_extension": caller_extension,
            "caller_info": caller_info,
            "dialed_number": dialed_number,
            "normalized_number": normalized_number,
            "location": location_info,
            "timestamp": datetime.now(UTC),
            "routing": routing_info,
        }

        self.emergency_calls.append(call_record)
        if len(self.emergency_calls) > self.max_call_history:
            self.emergency_calls.pop(0)

        self.logger.critical("Emergency call routing completed")
        self.logger.critical("=" * 70)

        return True, routing_info

    def _get_nomadic_e911_engine(self) -> NomadicE911Engine | None:
        """
        Get or create nomadic E911 engine instance

        Returns:
            NomadicE911Engine instance or None if not available
        """
        if not NOMADIC_E911_AVAILABLE:
            return None

        if not hasattr(self.pbx_core, "database") or not self.pbx_core.database.enabled:
            return None

        try:
            return NomadicE911Engine(self.pbx_core.database, self.config)
        except Exception as e:
            self.logger.warning(f"Could not create nomadic E911 engine: {e}")
            return None

    def _format_dispatchable_location(self, location: dict) -> str:
        """Format location dictionary as dispatchable location string"""
        parts = []
        if location.get("street_address"):
            parts.append(location["street_address"])
        if location.get("building"):
            parts.append(f"Building: {location['building']}")
        if location.get("floor"):
            parts.append(f"Floor {location['floor']}")
        if location.get("room"):
            parts.append(f"Room {location['room']}")
        if location.get("city"):
            parts.append(location["city"])
        if location.get("state"):
            parts.append(location["state"])
        if location.get("postal_code"):
            parts.append(location["postal_code"])
        return ", ".join(parts) if parts else "Location on file"

    def _get_location_info(self, extension: str) -> dict | None:
        """
        Get location information for extension (Ray Baum's Act)

        Args:
            extension: Extension number

        Returns:
            Location information dictionary or None
        """
        # First try nomadic E911 (multi-site support)
        nomadic_e911 = self._get_nomadic_e911_engine()
        if nomadic_e911:
            try:
                location = nomadic_e911.get_location(extension)
                if location:
                    location["dispatchable_location"] = self._format_dispatchable_location(location)
                    return location
            except (KeyError, TypeError, ValueError) as e:
                self.logger.warning(f"Could not get nomadic E911 location: {e}")

        # Check if E911 location service is available (single-site)
        if hasattr(self.pbx_core, "e911_location") and self.pbx_core.e911_location:
            location = self.pbx_core.e911_location.get_location(extension)
            if location:
                return location

        # Fallback to extension registry location info
        if hasattr(self.pbx_core, "extension_registry"):
            ext_info = self.pbx_core.extension_registry.get_extension(extension)
            if ext_info and "location" in ext_info:
                return {
                    "location": ext_info["location"],
                    "dispatchable_location": ext_info.get("location", "Unknown"),
                }

        return None

    def _get_caller_info(self, extension: str) -> dict:
        """
        Get caller information

        Args:
            extension: Extension number

        Returns:
            Caller information dictionary
        """
        caller_info = {"extension": extension, "name": "Unknown"}

        if hasattr(self.pbx_core, "extension_registry"):
            ext_info = self.pbx_core.extension_registry.get_extension(extension)
            if ext_info:
                caller_info["name"] = ext_info.get("name", "Unknown")
                caller_info["email"] = ext_info.get("email")
                caller_info["department"] = ext_info.get("department")

        return caller_info

    def _route_emergency_call(
        self,
        caller_extension: str,
        normalized_number: str,
        call_id: str,
        location_info: dict | None,
        caller_info: dict,
        nomadic_e911_engine: NomadicE911Engine | None = None,
    ) -> dict:
        """
        Route emergency call to appropriate trunk

        Multi-Site E911 Integration:
        1. Try site-specific emergency trunk (from nomadic E911 config)
        2. Try global emergency trunk (from config)
        3. Fallback to any available trunk

        Args:
            caller_extension: Caller extension
            normalized_number: Normalized emergency number (911)
            call_id: Call ID
            location_info: Location information
            caller_info: Caller information
            nomadic_e911_engine: Optional cached NomadicE911Engine instance

        Returns:
            Routing information
        """
        routing_info = {
            "success": False,
            "trunk_id": None,
            "destination": normalized_number,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Get trunk system
        if not hasattr(self.pbx_core, "trunk_system"):
            self.logger.error("Trunk system not available - cannot route emergency call")
            routing_info["error"] = "Trunk system not available"
            return routing_info

        trunk_system = self.pbx_core.trunk_system

        # Multi-Site E911: Try to use site-specific emergency trunk
        site_trunk_id = self._get_site_emergency_trunk(
            caller_extension, location_info, nomadic_e911_engine
        )
        if site_trunk_id:
            trunk = trunk_system.get_trunk(site_trunk_id)
            if trunk and trunk.can_make_call():
                self.logger.critical(
                    f"Routing emergency call via SITE-SPECIFIC trunk: {site_trunk_id}"
                )
                routing_info["success"] = True
                routing_info["trunk_id"] = site_trunk_id
                routing_info["trunk_name"] = trunk.name
                routing_info["site_specific"] = True

                # Include site-specific PSAP and ELIN if available
                site_info = self._get_site_info(caller_extension, nomadic_e911_engine)
                if site_info:
                    routing_info["psap_number"] = site_info.get("psap_number")
                    routing_info["elin"] = site_info.get("elin")

                return routing_info
            self.logger.warning(f"Site-specific emergency trunk {site_trunk_id} not available")

        # Try to route via global emergency trunk if configured
        if self.emergency_trunk_id:
            trunk = trunk_system.get_trunk(self.emergency_trunk_id)
            if trunk and trunk.can_make_call():
                self.logger.critical(
                    f"Routing emergency call via GLOBAL trunk: {self.emergency_trunk_id}"
                )
                routing_info["success"] = True
                routing_info["trunk_id"] = self.emergency_trunk_id
                routing_info["trunk_name"] = trunk.name
                return routing_info
            self.logger.warning(f"Global emergency trunk {self.emergency_trunk_id} not available")

        # Fallback: try to route via any available trunk
        routed_trunk, _transformed_number = trunk_system.route_outbound(normalized_number)

        if routed_trunk:
            self.logger.critical(
                f"Routing emergency call via FALLBACK trunk: {routed_trunk.trunk_id}"
            )
            routing_info["success"] = True
            routing_info["trunk_id"] = routed_trunk.trunk_id
            routing_info["trunk_name"] = routed_trunk.name
            routing_info["fallback"] = True
        else:
            self.logger.error("❌ NO TRUNK AVAILABLE FOR EMERGENCY CALL")
            routing_info["error"] = "No trunk available"

        return routing_info

    def _get_site_emergency_trunk(
        self,
        extension: str,
        location_info: dict | None = None,
        nomadic_e911_engine: NomadicE911Engine | None = None,
    ) -> str | None:
        """
        Get site-specific emergency trunk for extension (Multi-Site E911)

        Args:
            extension: Extension number
            location_info: Optional location info (if already retrieved)
            nomadic_e911_engine: Optional cached NomadicE911Engine instance

        Returns:
            Site-specific emergency trunk ID or None
        """
        # Use cached engine or create new one
        nomadic_e911 = nomadic_e911_engine or self._get_nomadic_e911_engine()
        if not nomadic_e911:
            return None

        try:
            # Get location if not provided
            if not location_info:
                location_info = nomadic_e911.get_location(extension)

            if not location_info or not location_info.get("ip_address"):
                return None

            # Find site by IP address using public API
            site = nomadic_e911.find_site_by_ip(location_info["ip_address"])
            if site and site.get("emergency_trunk"):
                self.logger.info(
                    f"Found site-specific emergency trunk for {extension}: {site['emergency_trunk']}"
                )
                return site["emergency_trunk"]

            return None

        except (KeyError, TypeError, ValueError) as e:
            self.logger.warning(f"Could not get site emergency trunk: {e}")
            return None

    def _get_site_info(
        self, extension: str, nomadic_e911_engine: NomadicE911Engine | None = None
    ) -> dict | None:
        """
        Get site information for extension (PSAP, ELIN, etc.)

        Args:
            extension: Extension number
            nomadic_e911_engine: Optional cached NomadicE911Engine instance

        Returns:
            Site information or None
        """
        # Use cached engine or create new one
        nomadic_e911 = nomadic_e911_engine or self._get_nomadic_e911_engine()
        if not nomadic_e911:
            return None

        try:
            location = nomadic_e911.get_location(extension)
            if not location or not location.get("ip_address"):
                return None

            # Use public API method instead of private _find_site_by_ip
            site = nomadic_e911.find_site_by_ip(location["ip_address"])
            return site

        except (KeyError, TypeError, ValueError) as e:
            self.logger.warning(f"Could not get site info: {e}")
            return None

    def _trigger_emergency_notification(
        self, caller_extension: str, caller_info: dict, location_info: dict | None, call_id: str
    ) -> None:
        """
        Trigger automatic notification to designated contacts (Kari's Law requirement)

        Args:
            caller_extension: Caller extension
            caller_info: Caller information
            location_info: Location information
            call_id: Call ID
        """
        # Check if emergency notification system is available
        if not hasattr(self.pbx_core, "emergency_notification"):
            self.logger.warning("Emergency notification system not available")
            return

        emergency_notification = self.pbx_core.emergency_notification

        if not emergency_notification.enabled:
            self.logger.warning("Emergency notification system is disabled")
            return

        # Build notification details
        details = {
            "caller_extension": caller_extension,
            "caller_name": caller_info.get("name", "Unknown"),
            "call_id": call_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "compliance": "Karis Law",
        }

        # Add location if available
        if location_info:
            details["location"] = location_info.get("dispatchable_location", "Unknown")
            if "building" in location_info:
                details["building"] = location_info["building"]
            if "floor" in location_info:
                details["floor"] = location_info["floor"]
            if "room" in location_info:
                details["room"] = location_info["room"]
        else:
            details["location"] = "Location not registered"

        # Trigger notification
        self.logger.warning("Triggering automatic emergency notification (Kari's Law)")
        emergency_notification.on_911_call(
            caller_extension=caller_extension,
            caller_name=caller_info.get("name", "Unknown"),
            location=details.get("location", "Unknown"),
        )

    def get_emergency_call_history(self, extension: str | None = None, limit: int = 50) -> list:
        """
        Get emergency call history

        Args:
            extension: Filter by extension (optional)
            limit: Maximum number of records to return

        Returns:
            list of emergency call records
        """
        calls = self.emergency_calls

        if extension:
            calls = [call for call in calls if call["caller_extension"] == extension]

        # Return most recent calls
        return calls[-limit:]

    def get_statistics(self) -> dict:
        """
        Get Kari's Law compliance statistics

        Returns:
            Statistics dictionary
        """
        return {
            "enabled": self.enabled,
            "total_emergency_calls": len(self.emergency_calls),
            "auto_notify": self.auto_notify,
            "require_location": self.require_location,
            "emergency_trunk_configured": self.emergency_trunk_id is not None,
        }

    def validate_compliance(self) -> dict:
        """
        Validate Kari's Law compliance configuration

        Returns:
            Validation results dictionary
        """
        results = {"compliant": True, "warnings": [], "errors": []}

        # Check if enabled
        if not self.enabled:
            results["compliant"] = False
            results["errors"].append("Kari's Law compliance is disabled")

        # Check emergency trunk configuration
        if not self.emergency_trunk_id:
            results["warnings"].append("No dedicated emergency trunk configured")

        # Check trunk system
        if hasattr(self.pbx_core, "trunk_system"):
            trunk_system = self.pbx_core.trunk_system

            # Verify emergency trunk exists
            if self.emergency_trunk_id:
                trunk = trunk_system.get_trunk(self.emergency_trunk_id)
                if not trunk:
                    results["compliant"] = False
                    results["errors"].append(
                        f"Emergency trunk '{self.emergency_trunk_id}' not found"
                    )
                elif not trunk.can_make_call():
                    results["warnings"].append(
                        f"Emergency trunk '{self.emergency_trunk_id}' is not available"
                    )

            # Check if any trunk can handle 911
            routed_trunk, _ = trunk_system.route_outbound("911")
            if not routed_trunk:
                results["compliant"] = False
                results["errors"].append("No trunk available to route 911 calls")
        else:
            results["compliant"] = False
            results["errors"].append("Trunk system not available")

        # Check emergency notification system
        if self.auto_notify:
            if not hasattr(self.pbx_core, "emergency_notification"):
                results["warnings"].append("Emergency notification system not available")
            elif not self.pbx_core.emergency_notification.enabled:
                results["warnings"].append("Emergency notification system is disabled")

        # Check E911 location service
        if self.require_location:
            if not hasattr(self.pbx_core, "e911_location"):
                results["warnings"].append("E911 location service not available")
            elif not self.pbx_core.e911_location.enabled:
                results["warnings"].append("E911 location service is disabled")

        return results
