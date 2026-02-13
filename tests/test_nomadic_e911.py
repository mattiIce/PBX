"""
Tests for Nomadic E911 Framework
"""

from typing import Any
import pytest


from pbx.features.nomadic_e911 import NomadicE911Engine


class TestNomadicE911:
    """Test Nomadic E911 functionality"""

    def setup_method(self) -> None:
        """Set up test database"""
        # Create a minimal mock database backend
        import sqlite3

        class MockDB:
            def __init__(self) -> None:
                self.db_type = "sqlite"
                self.conn = sqlite3.connect(":memory:")
                self.enabled = True

            def execute(self, query: str, params: Any = None) -> list[Any]:
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor.fetchall()

            def disconnect(self) -> None:
                self.conn.close()

        self.db = MockDB()

        # Create tables
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS nomadic_e911_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extension TEXT NOT NULL,
                ip_address TEXT,
                location_name TEXT,
                street_address TEXT,
                city TEXT,
                state TEXT,
                postal_code TEXT,
                country TEXT DEFAULT 'USA',
                building TEXT,
                floor TEXT,
                room TEXT,
                latitude REAL,
                longitude REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auto_detected INTEGER DEFAULT 0
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS e911_location_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extension TEXT NOT NULL,
                old_location TEXT,
                new_location TEXT,
                update_source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS multi_site_e911_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_name TEXT NOT NULL,
                ip_range_start TEXT NOT NULL,
                ip_range_end TEXT NOT NULL,
                emergency_trunk TEXT,
                psap_number TEXT,
                elin TEXT,
                street_address TEXT,
                city TEXT,
                state TEXT,
                postal_code TEXT,
                country TEXT DEFAULT 'USA',
                building TEXT,
                floor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.config = {"nomadic_e911.enabled": True}
        self.engine = NomadicE911Engine(self.db, self.config)

    def teardown_method(self) -> None:
        """Clean up test database"""
        self.db.disconnect()

    def test_initialization(self) -> None:
        """Test engine initialization"""
        assert self.engine is not None
        assert self.engine.enabled

    def test_update_location(self) -> None:
        """Test updating extension location"""
        location_data = {
            "ip_address": "192.168.1.100",
            "location_name": "Main Office",
            "street_address": "123 Main St",
            "city": "Detroit",
            "state": "MI",
            "postal_code": "48201",
            "building": "Building A",
            "floor": "2",
            "room": "201",
        }

        result = self.engine.update_location("1001", location_data)
        assert result

    def test_get_location(self) -> None:
        """Test retrieving extension location"""
        # First create a location
        location_data = {
            "ip_address": "192.168.1.100",
            "location_name": "Main Office",
            "street_address": "123 Main St",
            "city": "Detroit",
            "state": "MI",
            "postal_code": "48201",
        }

        self.engine.update_location("1001", location_data)

        # Now retrieve it
        location = self.engine.get_location("1001")
        assert location is not None
        assert location["extension"] == "1001"
        assert location["city"] == "Detroit"

    def test_create_site_config(self) -> None:
        """Test creating multi-site E911 configuration"""
        site_data = {
            "site_name": "Manufacturing Plant",
            "ip_range_start": "192.168.1.0",
            "ip_range_end": "192.168.1.255",
            "street_address": "456 Factory Rd",
            "city": "Detroit",
            "state": "MI",
            "postal_code": "48202",
            "building": "Plant 1",
            "floor": "1",
            "emergency_trunk": "trunk_911",
            "psap_number": "911",
        }

        result = self.engine.create_site_config(site_data)
        assert result

    def test_get_all_sites(self) -> None:
        """Test retrieving all site configurations"""
        # Create a site
        site_data = {
            "site_name": "Main Office",
            "ip_range_start": "192.168.1.0",
            "ip_range_end": "192.168.1.255",
            "street_address": "123 Main St",
            "city": "Detroit",
            "state": "MI",
        }

        self.engine.create_site_config(site_data)

        # Get all sites
        sites = self.engine.get_all_sites()
        assert len(sites) > 0
        assert sites[0]["site_name"] == "Main Office"

    def test_ip_in_range(self) -> None:
        """Test IP range checking"""
        # Test IP in range
        result = self.engine._ip_in_range("192.168.1.50", "192.168.1.0", "192.168.1.255")
        assert result
        # Test IP not in range
        result = self.engine._ip_in_range("192.168.2.50", "192.168.1.0", "192.168.1.255")
        assert not result

    def test_is_private_ip(self) -> None:
        """Test private IP detection"""
        # Test private IPs
        assert self.engine._is_private_ip("192.168.1.1")
        assert self.engine._is_private_ip("10.0.0.1")
        assert self.engine._is_private_ip("172.16.0.1")
        # Test public IP
        assert not self.engine._is_private_ip("8.8.8.8")

    def test_find_site_by_ip(self) -> None:
        """Test finding site by IP address"""
        # Create a site
        site_data = {
            "site_name": "Office A",
            "ip_range_start": "192.168.1.0",
            "ip_range_end": "192.168.1.255",
            "street_address": "123 Main St",
            "city": "Detroit",
            "state": "MI",
        }

        self.engine.create_site_config(site_data)

        # Find site
        site = self.engine._find_site_by_ip("192.168.1.100")
        assert site is not None
        assert site["site_name"] == "Office A"

    def test_detect_location_by_ip(self) -> None:
        """Test automatic location detection by IP"""
        # Create a site
        site_data = {
            "site_name": "Manufacturing Plant",
            "ip_range_start": "192.168.10.0",
            "ip_range_end": "192.168.10.255",
            "street_address": "789 Industrial Blvd",
            "city": "Detroit",
            "state": "MI",
            "postal_code": "48203",
            "building": "Plant 2",
            "floor": "1",
        }

        self.engine.create_site_config(site_data)

        # Detect location
        location = self.engine.detect_location_by_ip("1002", "192.168.10.50")
        assert location is not None
        assert location["location_name"] == "Manufacturing Plant"
        assert location["city"] == "Detroit"
        assert location["auto_detected"]

    def test_detect_location_private_ip_no_match(self) -> None:
        """Test detecting private IP with no site match"""
        location = self.engine.detect_location_by_ip("1003", "192.168.99.1")
        assert location is not None
        assert location["location_name"] == "Unknown Internal Location"
        assert location.get("needs_configuration", False)

    def test_detect_location_public_ip(self) -> None:
        """Test detecting public IP (no match)"""
        location = self.engine.detect_location_by_ip("1004", "8.8.8.8")
        assert location is None

    def test_location_history(self) -> None:
        """Test location update history"""
        # Create initial location
        location1 = {"street_address": "123 Main St", "city": "Detroit", "state": "MI"}
        self.engine.update_location("1005", location1)

        # Update to new location
        location2 = {"street_address": "456 New St", "city": "Warren", "state": "MI"}
        self.engine.update_location("1005", location2)

        # Get history
        history = self.engine.get_location_history("1005")
        assert len(history) > 0

    def test_multiple_sites(self) -> None:
        """Test multiple site configurations"""
        # Create multiple sites
        sites_data = [
            {
                "site_name": "Site A",
                "ip_range_start": "192.168.1.0",
                "ip_range_end": "192.168.1.255",
                "city": "Detroit",
            },
            {
                "site_name": "Site B",
                "ip_range_start": "192.168.2.0",
                "ip_range_end": "192.168.2.255",
                "city": "Warren",
            },
        ]

        for site in sites_data:
            self.engine.create_site_config(site)

        # Verify both sites
        all_sites = self.engine.get_all_sites()
        assert len(all_sites) == 2

    def test_location_with_coordinates(self) -> None:
        """Test location with latitude/longitude"""
        location_data = {
            "street_address": "123 Main St",
            "city": "Detroit",
            "state": "MI",
            "latitude": 42.3314,
            "longitude": -83.0458,
        }

        self.engine.update_location("1006", location_data)

        location = self.engine.get_location("1006")
        assert location is not None
        assert location["latitude"] == pytest.approx(42.3314, abs=10**(-4))
        assert location["longitude"] == pytest.approx(-83.0458, abs=10**(-4))
