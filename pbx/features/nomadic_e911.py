"""
Nomadic E911 Framework
Location-based emergency routing for remote workers
"""
from datetime import datetime
from typing import Dict, List, Optional
import ipaddress

from pbx.utils.logger import get_logger


class NomadicE911Engine:
    """
    Nomadic E911 framework
    Tracks and updates emergency locations for mobile/remote workers
    """

    def __init__(self, db_backend, config: dict):
        """
        Initialize Nomadic E911 engine

        Args:
            db_backend: DatabaseBackend instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.db = db_backend
        self.config = config
        self.enabled = config.get('nomadic_e911.enabled', True)

        self.logger.info("Nomadic E911 Framework initialized")

    def update_location(self, extension: str, location_data: Dict, auto_detected: bool = False) -> bool:
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
                """INSERT INTO nomadic_e911_locations 
                   (extension, ip_address, location_name, street_address, city, state,
                    postal_code, country, building, floor, room, latitude, longitude, auto_detected)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                if self.db.db_type == 'sqlite'
                else """INSERT INTO nomadic_e911_locations 
                   (extension, ip_address, location_name, street_address, city, state,
                    postal_code, country, building, floor, room, latitude, longitude, auto_detected)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    extension,
                    location_data.get('ip_address'),
                    location_data.get('location_name'),
                    location_data.get('street_address'),
                    location_data.get('city'),
                    location_data.get('state'),
                    location_data.get('postal_code'),
                    location_data.get('country', 'USA'),
                    location_data.get('building'),
                    location_data.get('floor'),
                    location_data.get('room'),
                    location_data.get('latitude'),
                    location_data.get('longitude'),
                    auto_detected
                )
            )

            # Log location update
            if current:
                old_loc = f"{current.get('street_address')}, {current.get('city')}, {current.get('state')}"
                new_loc = f"{location_data.get('street_address')}, {location_data.get('city')}, {location_data.get('state')}"
                
                self.db.execute(
                    """INSERT INTO e911_location_updates 
                       (extension, old_location, new_location, update_source)
                       VALUES (?, ?, ?, ?)"""
                    if self.db.db_type == 'sqlite'
                    else """INSERT INTO e911_location_updates 
                       (extension, old_location, new_location, update_source)
                       VALUES (%s, %s, %s, %s)""",
                    (extension, old_loc, new_loc, 'auto' if auto_detected else 'manual')
                )

            self.logger.info(f"Updated E911 location for {extension}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update E911 location: {e}")
            return False

    def get_location(self, extension: str) -> Optional[Dict]:
        """
        Get current emergency location for extension

        Args:
            extension: Extension number

        Returns:
            Location dict or None
        """
        try:
            result = self.db.execute(
                """SELECT * FROM nomadic_e911_locations 
                   WHERE extension = ? 
                   ORDER BY last_updated DESC LIMIT 1"""
                if self.db.db_type == 'sqlite'
                else """SELECT * FROM nomadic_e911_locations 
                   WHERE extension = %s 
                   ORDER BY last_updated DESC LIMIT 1""",
                (extension,)
            )

            if result and result[0]:
                row = result[0]
                return {
                    'extension': row[1],
                    'ip_address': row[2],
                    'location_name': row[3],
                    'street_address': row[4],
                    'city': row[5],
                    'state': row[6],
                    'postal_code': row[7],
                    'country': row[8],
                    'building': row[9],
                    'floor': row[10],
                    'room': row[11],
                    'latitude': float(row[12]) if row[12] else None,
                    'longitude': float(row[13]) if row[13] else None,
                    'last_updated': row[14],
                    'auto_detected': bool(row[15])
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get E911 location: {e}")
            return None

    def detect_location_by_ip(self, extension: str, ip_address: str) -> Optional[Dict]:
        """
        Automatically detect location by IP address
        Framework method - integrates with IP geolocation

        Args:
            extension: Extension number
            ip_address: IP address

        Returns:
            Detected location or None
        """
        # Framework implementation
        # TODO: Integrate with IP geolocation service
        # - MaxMind GeoIP2
        # - IPinfo.io
        # - Internal network mapping

        # Check multi-site configs first
        site = self._find_site_by_ip(ip_address)
        if site:
            return {
                'ip_address': ip_address,
                'location_name': site['site_name'],
                'auto_detected': True
            }

        return None

    def _find_site_by_ip(self, ip_address: str) -> Optional[Dict]:
        """
        Find site configuration by IP address

        Args:
            ip_address: IP address to check

        Returns:
            Site config or None
        """
        try:
            result = self.db.execute(
                "SELECT * FROM multi_site_e911_configs"
            )

            for row in (result or []):
                site_data = {
                    'id': row[0],
                    'site_name': row[1],
                    'ip_range_start': row[2],
                    'ip_range_end': row[3],
                    'emergency_trunk': row[4],
                    'psap_number': row[5],
                    'elin': row[6]
                }

                # Check if IP is in range
                if self._ip_in_range(ip_address, site_data['ip_range_start'], site_data['ip_range_end']):
                    return site_data

            return None

        except Exception as e:
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
        except Exception:
            return False

    def create_site_config(self, site_data: Dict) -> bool:
        """
        Create multi-site E911 configuration

        Args:
            site_data: Site configuration

        Returns:
            bool: True if successful
        """
        try:
            self.db.execute(
                """INSERT INTO multi_site_e911_configs 
                   (site_name, ip_range_start, ip_range_end, emergency_trunk, psap_number, elin)
                   VALUES (?, ?, ?, ?, ?, ?)"""
                if self.db.db_type == 'sqlite'
                else """INSERT INTO multi_site_e911_configs 
                   (site_name, ip_range_start, ip_range_end, emergency_trunk, psap_number, elin)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    site_data['site_name'],
                    site_data['ip_range_start'],
                    site_data['ip_range_end'],
                    site_data.get('emergency_trunk'),
                    site_data.get('psap_number'),
                    site_data.get('elin')
                )
            )

            self.logger.info(f"Created E911 site config: {site_data['site_name']}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create site config: {e}")
            return False

    def get_all_sites(self) -> List[Dict]:
        """
        Get all E911 site configurations

        Returns:
            List of site dictionaries
        """
        try:
            result = self.db.execute(
                "SELECT * FROM multi_site_e911_configs ORDER BY site_name"
            )

            sites = []
            for row in (result or []):
                sites.append({
                    'id': row[0],
                    'site_name': row[1],
                    'ip_range_start': row[2],
                    'ip_range_end': row[3],
                    'emergency_trunk': row[4],
                    'psap_number': row[5],
                    'elin': row[6],
                    'created_at': row[7]
                })

            return sites

        except Exception as e:
            self.logger.error(f"Failed to get E911 sites: {e}")
            return []

    def get_location_history(self, extension: str, limit: int = 10) -> List[Dict]:
        """
        Get location update history for extension

        Args:
            extension: Extension number
            limit: Maximum number of records

        Returns:
            List of location update dictionaries
        """
        try:
            result = self.db.execute(
                """SELECT * FROM e911_location_updates 
                   WHERE extension = ? 
                   ORDER BY updated_at DESC LIMIT ?"""
                if self.db.db_type == 'sqlite'
                else """SELECT * FROM e911_location_updates 
                   WHERE extension = %s 
                   ORDER BY updated_at DESC LIMIT %s""",
                (extension, limit)
            )

            history = []
            for row in (result or []):
                history.append({
                    'old_location': row[2],
                    'new_location': row[3],
                    'update_source': row[4],
                    'updated_at': row[5]
                })

            return history

        except Exception as e:
            self.logger.error(f"Failed to get location history: {e}")
            return []
