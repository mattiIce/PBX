"""
Nomadic E911 Framework
Location-based emergency routing for remote workers
"""

import ipaddress
import sqlite3
from typing import Any

from pbx.utils.logger import get_logger


class NomadicE911Engine:
    """
    Nomadic E911 framework
    Tracks and updates emergency locations for mobile/remote workers
    """

    def __init__(self, db_backend: Any | None, config: dict) -> None:
        """
        Initialize Nomadic E911 engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = config.get("nomadic_e911.enabled", True)

        self.logger.info("Nomadic E911 Framework initialized")

    def update_location(
        self, extension: str, location_data: dict, auto_detected: bool = False
    ) -> bool:
        """
        Update emergency location for extension

        Args:
            extension: Extension number
            location_data: Location information
            auto_detected: Whether location was auto-detected

        Returns:
            bool: True if successful
        """
        try:
            # Get current location
            current = self.get_location(extension)

            # Insert new location
            self.db.execute(
                (
                    """INSERT INTO nomadic_e911_locations
                   (extension, ip_address, location_name, street_address, city, state,
                    postal_code, country, building, floor, room, latitude, longitude, auto_detected)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO nomadic_e911_locations
                   (extension, ip_address, location_name, street_address, city, state,
                    postal_code, country, building, floor, room, latitude, longitude, auto_detected)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                ),
                (
                    extension,
                    location_data.get("ip_address"),
                    location_data.get("location_name"),
                    location_data.get("street_address"),
                    location_data.get("city"),
                    location_data.get("state"),
                    location_data.get("postal_code"),
                    location_data.get("country", "USA"),
                    location_data.get("building"),
                    location_data.get("floor"),
                    location_data.get("room"),
                    location_data.get("latitude"),
                    location_data.get("longitude"),
                    auto_detected,
                ),
            )

            # Log location update
            if current:
                old_loc = f"{current.get('street_address')}, {current.get('city')}, {current.get('state')}"
                new_loc = f"{location_data.get('street_address')}, {location_data.get('city')}, {location_data.get('state')}"

                self.db.execute(
                    (
                        """INSERT INTO e911_location_updates
                       (extension, old_location, new_location, update_source)
                       VALUES (?, ?, ?, ?)"""
                        if self.db.db_type == "sqlite"
                        else """INSERT INTO e911_location_updates
                       (extension, old_location, new_location, update_source)
                       VALUES (%s, %s, %s, %s)"""
                    ),
                    (extension, old_loc, new_loc, "auto" if auto_detected else "manual"),
                )

            self.logger.info(f"Updated E911 location for {extension}")
            return True

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to update E911 location: {e}")
            return False

    def get_location(self, extension: str) -> dict | None:
        """
        Get current emergency location for extension

        Args:
            extension: Extension number

        Returns:
            Location dict or None
        """
        try:
            result = self.db.execute(
                (
                    """SELECT * FROM nomadic_e911_locations
                   WHERE extension = ?
                   ORDER BY last_updated DESC LIMIT 1"""
                    if self.db.db_type == "sqlite"
                    else """SELECT * FROM nomadic_e911_locations
                   WHERE extension = %s
                   ORDER BY last_updated DESC LIMIT 1"""
                ),
                (extension,),
            )

            if result and result[0]:
                row = result[0]
                return {
                    "extension": row[1],
                    "ip_address": row[2],
                    "location_name": row[3],
                    "street_address": row[4],
                    "city": row[5],
                    "state": row[6],
                    "postal_code": row[7],
                    "country": row[8],
                    "building": row[9],
                    "floor": row[10],
                    "room": row[11],
                    "latitude": float(row[12]) if row[12] else None,
                    "longitude": float(row[13]) if row[13] else None,
                    "last_updated": row[14],
                    "auto_detected": bool(row[15]),
                }

            return None

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get E911 location: {e}")
            return None

    def detect_location_by_ip(self, extension: str, ip_address: str) -> dict | None:
        """
        Automatically detect location by IP address
        Uses internal network mapping (multi-site configs)

        Args:
            extension: Extension number
            ip_address: IP address

        Returns:
            Detected location or None
        """
        # Check multi-site configs for IP range match
        site = self._find_site_by_ip(ip_address)
        if site:
            location_data = {
                "ip_address": ip_address,
                "location_name": site["site_name"],
                "street_address": site.get("street_address", ""),
                "city": site.get("city", ""),
                "state": site.get("state", ""),
                "postal_code": site.get("postal_code", ""),
                "country": site.get("country", "USA"),
                "building": site.get("building", ""),
                "floor": site.get("floor", ""),
                "room": "",  # Room is typically not known from IP alone
                "auto_detected": True,
            }

            # Automatically update location for extension
            if self.update_location(extension, location_data, auto_detected=True):
                self.logger.info(
                    f"Auto-detected location for {extension} from IP {ip_address}: {site['site_name']}"
                )
                return location_data

        # If no site match found, check if this is a private IP
        # Private IPs suggest internal network but unknown site
        if self._is_private_ip(ip_address):
            self.logger.warning(
                f"Private IP {ip_address} for {extension} does not match any configured site"
            )
            return {
                "ip_address": ip_address,
                "location_name": "Unknown Internal Location",
                "auto_detected": True,
                "needs_configuration": True,
            }

        return None

    def find_site_by_ip(self, ip_address: str) -> dict | None:
        """
        Find site configuration by IP address (Public API)

        Args:
            ip_address: IP address to check

        Returns:
            Site config with full address details or None
        """
        return self._find_site_by_ip(ip_address)

    def _find_site_by_ip(self, ip_address: str) -> dict | None:
        """
        Find site configuration by IP address

        Args:
            ip_address: IP address to check

        Returns:
            Site config with full address details or None
        """
        try:
            result = self.db.execute("SELECT * FROM multi_site_e911_configs")

            for row in result or []:
                site_data = {
                    "id": row[0],
                    "site_name": row[1],
                    "ip_range_start": row[2],
                    "ip_range_end": row[3],
                    "emergency_trunk": row[4],
                    "psap_number": row[5],
                    "elin": row[6],
                    "street_address": row[7] if len(row) > 7 else "",
                    "city": row[8] if len(row) > 8 else "",
                    "state": row[9] if len(row) > 9 else "",
                    "postal_code": row[10] if len(row) > 10 else "",
                    "country": row[11] if len(row) > 11 else "USA",
                    "building": row[12] if len(row) > 12 else "",
                    "floor": row[13] if len(row) > 13 else "",
                }

                # Check if IP is in range
                if self._ip_in_range(
                    ip_address, site_data["ip_range_start"], site_data["ip_range_end"]
                ):
                    return site_data

            return None

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to find site by IP: {e}")
            return None

    def _ip_in_range(self, ip: str, start: str, end: str) -> bool:
        """
        Check if IP is in range

        Args:
            ip: IP address to check
            start: Range start IP
            end: Range end IP

        Returns:
            bool: True if in range
        """
        try:
            ip_addr = ipaddress.ip_address(ip)
            start_addr = ipaddress.ip_address(start)
            end_addr = ipaddress.ip_address(end)
            return start_addr <= ip_addr <= end_addr
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Invalid IP address in range check: {e}")
            return False

    def _is_private_ip(self, ip: str) -> bool:
        """
        Check if IP address is private (RFC 1918)

        Args:
            ip: IP address to check

        Returns:
            bool: True if private IP
        """
        try:
            ip_addr = ipaddress.ip_address(ip)
            return ip_addr.is_private
        except (ValueError, TypeError):
            return False

    def create_site_config(self, site_data: dict) -> bool:
        """
        Create multi-site E911 configuration

        Args:
            site_data: Site configuration including full address details

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                (
                    """INSERT INTO multi_site_e911_configs
                   (site_name, ip_range_start, ip_range_end, emergency_trunk, psap_number, elin,
                    street_address, city, state, postal_code, country, building, floor)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                    if self.db.db_type == "sqlite"
                    else """INSERT INTO multi_site_e911_configs
                   (site_name, ip_range_start, ip_range_end, emergency_trunk, psap_number, elin,
                    street_address, city, state, postal_code, country, building, floor)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                ),
                (
                    site_data["site_name"],
                    site_data["ip_range_start"],
                    site_data["ip_range_end"],
                    site_data.get("emergency_trunk"),
                    site_data.get("psap_number"),
                    site_data.get("elin"),
                    site_data.get("street_address", ""),
                    site_data.get("city", ""),
                    site_data.get("state", ""),
                    site_data.get("postal_code", ""),
                    site_data.get("country", "USA"),
                    site_data.get("building", ""),
                    site_data.get("floor", ""),
                ),
            )

            self.logger.info(f"Created E911 site config: {site_data['site_name']}")
            return True

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to create site config: {e}")
            return False

    def get_all_sites(self) -> list[dict]:
        """
        Get all E911 site configurations

        Returns:
            list of site dictionaries with full address information
        """
        try:
            result = self.db.execute("SELECT * FROM multi_site_e911_configs ORDER BY site_name")

            sites = [
                {
                    "id": row[0],
                    "site_name": row[1],
                    "ip_range_start": row[2],
                    "ip_range_end": row[3],
                    "emergency_trunk": row[4],
                    "psap_number": row[5],
                    "elin": row[6],
                    "street_address": row[7] if len(row) > 7 else "",
                    "city": row[8] if len(row) > 8 else "",
                    "state": row[9] if len(row) > 9 else "",
                    "postal_code": row[10] if len(row) > 10 else "",
                    "country": row[11] if len(row) > 11 else "USA",
                    "building": row[12] if len(row) > 12 else "",
                    "floor": row[13] if len(row) > 13 else "",
                    "created_at": row[14] if len(row) > 14 else None,
                }
                for row in result or []
            ]

            return sites

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get E911 sites: {e}")
            return []

    def get_location_history(self, extension: str, limit: int = 10) -> list[dict]:
        """
        Get location update history for extension

        Args:
            extension: Extension number
            limit: Maximum number of records

        Returns:
            list of location update dictionaries
        """
        try:
            result = self.db.execute(
                (
                    """SELECT * FROM e911_location_updates
                   WHERE extension = ?
                   ORDER BY updated_at DESC LIMIT ?"""
                    if self.db.db_type == "sqlite"
                    else """SELECT * FROM e911_location_updates
                   WHERE extension = %s
                   ORDER BY updated_at DESC LIMIT %s"""
                ),
                (extension, limit),
            )

            history = [
                {
                    "old_location": row[2],
                    "new_location": row[3],
                    "update_source": row[4],
                    "updated_at": row[5],
                }
                for row in result or []
            ]

            return history

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get location history: {e}")
            return []
