"""
Tests for Nomadic E911 Framework
"""

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.features.nomadic_e911 import NomadicE911Engine


class TestNomadicE911(unittest.TestCase):
    """Test Nomadic E911 functionality"""

    def setUp(self):
        """Set up test database"""
        # Create a minimal mock database backend
        import sqlite3

        class MockDB:
            def __init__(self):
                self.db_type = "sqlite"
                self.conn = sqlite3.connect(":memory:")
                self.enabled = True

            def execute(self, query, params=None):
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor.fetchall()

            def disconnect(self):
                self.conn.close()

        self.db = MockDB()

        # Create tables
        self.db.execute(
            """
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
        """
        )

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS e911_location_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extension TEXT NOT NULL,
                old_location TEXT,
                new_location TEXT,
                update_source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        self.db.execute(
            """
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
        """
        )

        self.config = {"nomadic_e911.enabled": True}
        self.engine = NomadicE911Engine(self.db, self.config)

    def tearDown(self):
        """Clean up test database"""
        self.db.disconnect()

    def test_initialization(self):
        """Test engine initialization"""
        self.assertIsNotNone(self.engine)
        self.assertTrue(self.engine.enabled)

    def test_update_location(self):
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
        self.assertTrue(result)

    def test_get_location(self):
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
        self.assertIsNotNone(location)
        self.assertEqual(location["extension"], "1001")
        self.assertEqual(location["city"], "Detroit")

    def test_create_site_config(self):
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
        self.assertTrue(result)

    def test_get_all_sites(self):
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
        self.assertGreater(len(sites), 0)
        self.assertEqual(sites[0]["site_name"], "Main Office")

    def test_ip_in_range(self):
        """Test IP range checking"""
        # Test IP in range
        result = self.engine._ip_in_range("192.168.1.50", "192.168.1.0", "192.168.1.255")
        self.assertTrue(result)

        # Test IP not in range
        result = self.engine._ip_in_range("192.168.2.50", "192.168.1.0", "192.168.1.255")
        self.assertFalse(result)

    def test_is_private_ip(self):
        """Test private IP detection"""
        # Test private IPs
        self.assertTrue(self.engine._is_private_ip("192.168.1.1"))
        self.assertTrue(self.engine._is_private_ip("10.0.0.1"))
        self.assertTrue(self.engine._is_private_ip("172.16.0.1"))

        # Test public IP
        self.assertFalse(self.engine._is_private_ip("8.8.8.8"))

    def test_find_site_by_ip(self):
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
        self.assertIsNotNone(site)
        self.assertEqual(site["site_name"], "Office A")

    def test_detect_location_by_ip(self):
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
        self.assertIsNotNone(location)
        self.assertEqual(location["location_name"], "Manufacturing Plant")
        self.assertEqual(location["city"], "Detroit")
        self.assertTrue(location["auto_detected"])

    def test_detect_location_private_ip_no_match(self):
        """Test detecting private IP with no site match"""
        location = self.engine.detect_location_by_ip("1003", "192.168.99.1")
        self.assertIsNotNone(location)
        self.assertEqual(location["location_name"], "Unknown Internal Location")
        self.assertTrue(location.get("needs_configuration", False))

    def test_detect_location_public_ip(self):
        """Test detecting public IP (no match)"""
        location = self.engine.detect_location_by_ip("1004", "8.8.8.8")
        self.assertIsNone(location)

    def test_location_history(self):
        """Test location update history"""
        # Create initial location
        location1 = {"street_address": "123 Main St", "city": "Detroit", "state": "MI"}
        self.engine.update_location("1005", location1)

        # Update to new location
        location2 = {"street_address": "456 New St", "city": "Warren", "state": "MI"}
        self.engine.update_location("1005", location2)

        # Get history
        history = self.engine.get_location_history("1005")
        self.assertGreater(len(history), 0)

    def test_multiple_sites(self):
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
        self.assertEqual(len(all_sites), 2)

    def test_location_with_coordinates(self):
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
        self.assertIsNotNone(location)
        self.assertAlmostEqual(location["latitude"], 42.3314, places=4)
        self.assertAlmostEqual(location["longitude"], -83.0458, places=4)


if __name__ == "__main__":
    unittest.main()
