#!/usr/bin/env python3
"""
Comprehensive Phone Cleanup and Registration Tests
Tests phone cleanup on boot, registration preservation, and incomplete registration cleanup
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import Mock


from pbx.core.pbx import PBXCore
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB

# ============================================================================
# Phone Clear Functionality Tests
# ============================================================================


def test_clear_all_phones() -> None:
    """Test clearing all phone registrations"""

    # Create database backend (using SQLite for tests)
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Register multiple phones
    _ = phones_db.register_phone("1001", "192.168.1.100", "001565123456")
    _ = phones_db.register_phone("1002", "192.168.1.101", "001565123457")
    _ = phones_db.register_phone("1003", "192.168.1.102", None)

    # Verify phones were registered
    all_phones = phones_db.list_all()
    assert len(all_phones) == 3, f"Expected 3 phones, got {len(all_phones)}"

    # Clear all phones
    success = phones_db.clear_all()
    assert success, "Failed to clear phones"

    # Verify all phones were cleared
    all_phones = phones_db.list_all()
    assert len(all_phones) == 0, f"Expected 0 phones after clear, got {len(all_phones)}"


def test_clear_empty_table() -> None:
    """Test clearing an already empty table"""

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Clear empty table (should not fail)
    success = phones_db.clear_all()
    assert success, "Failed to clear empty table"

    # Verify still empty
    all_phones = phones_db.list_all()
    assert len(all_phones) == 0, f"Expected 0 phones, got {len(all_phones)}"


def test_register_after_clear() -> None:
    """Test that phones can be registered after clearing"""

    # Create database backend
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to database"
    assert db.create_tables(), "Failed to create tables"

    phones_db = RegisteredPhonesDB(db)

    # Register phones
    _ = phones_db.register_phone("1001", "192.168.1.100", "001565123456")
    _ = phones_db.register_phone("1002", "192.168.1.101", "001565123457")

    # Clear all
    phones_db.clear_all()

    # Verify cleared
    assert len(phones_db.list_all()) == 0, "Phones not cleared"

    # Register new phones
    success, _ = phones_db.register_phone("1003", "192.168.1.102", "001565123458")
    assert success, "Failed to register phone after clear"

    # Verify new phone is registered
    phones = phones_db.list_all()
    assert len(phones) == 1, f"Expected 1 phone, got {len(phones)}"
    assert phones[0]["extension_number"] == "1003", "Wrong extension registered"


# ============================================================================
# PBX Boot Preservation Tests
# ============================================================================


def test_pbx_preserves_phones_on_boot() -> None:
    """Test that PBX preserves registered phones table on boot"""

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")

    try:
        # Create a minimal test config
        config_content = f"""
server:
  sip_host: 127.0.0.1
  sip_port: 15060
  rtp_port_range_start: 20000
  rtp_port_range_end: 20100

database:
  type: sqlite
  path: {db_path}

api:
  host: 127.0.0.1
  port: 18080

logging:
  level: INFO
  console: false
  file: {os.path.join(temp_dir, 'test.log')}

extensions: []
"""
        config_path = os.path.join(temp_dir, "test_config.yml")
        with open(config_path, "w") as f:
            f.write(config_content)

        # Create first PBX instance and register some phones
        pbx1 = PBXCore(config_path)

        # Verify database is available
        assert pbx1.database.enabled, "Database not enabled"
        assert pbx1.registered_phones_db is not None, "Registered phones DB not initialized"

        # Register some phones directly in the database
        pbx1.registered_phones_db.register_phone("1001", "192.168.1.100", "001565123456")
        pbx1.registered_phones_db.register_phone("1002", "192.168.1.101", "001565123457")

        # Verify phones were registered
        phones = pbx1.registered_phones_db.list_all()
        assert len(phones) == 2, f"Expected 2 phones, got {len(phones)}"

        # Stop the PBX (simulating shutdown)
        pbx1.stop()

        # Create a new PBX instance (simulating server restart)
        pbx2 = PBXCore(config_path)

        # Start the PBX (this should NOT clear the phones table)
        success = pbx2.start()
        assert success, "Failed to start PBX"

        # Verify phones table was preserved
        phones = pbx2.registered_phones_db.list_all()
        phone_count = len(phones)
        assert phone_count == 2, f"Expected 2 phones after boot, got {phone_count}"

        # Stop the PBX
        pbx2.stop()


    finally:
        # Clean up
        shutil.rmtree(temp_dir)


# ============================================================================
# Incomplete Registration Cleanup Tests
# ============================================================================


class TestPhoneCleanupStartup:
    """Test cleanup of incomplete phone registrations"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.db = Mock(spec=DatabaseBackend)
        self.db.db_type = "sqlite"
        self.db.enabled = True
        self.phones_db = RegisteredPhonesDB(self.db)

    def test_cleanup_no_incomplete_registrations(self) -> None:
        """Test cleanup when there are no incomplete registrations"""
        # Mock fetch_one to return 0 count
        self.db.fetch_one.return_value = {"count": 0}

        success, count = self.phones_db.cleanup_incomplete_registrations()

        assert success
        assert count == 0
        # Execute should not be called since count is 0
        self.db.execute.assert_not_called()

    def test_cleanup_with_incomplete_registrations(self) -> None:
        """Test cleanup when there are incomplete registrations"""
        # Mock fetch_one to return 3 incomplete registrations
        self.db.fetch_one.return_value = {"count": 3}
        self.db.execute.return_value = True

        success, count = self.phones_db.cleanup_incomplete_registrations()

        assert success
        assert count == 3
        # Verify the DELETE query was executed
        self.db.execute.assert_called_once()
        call_args = self.db.execute.call_args[0][0]
        assert "DELETE FROM registered_phones" in call_args
        assert "mac_address IS NULL" in call_args
        assert "ip_address IS NULL" in call_args
        assert "extension_number IS NULL" in call_args

    def test_cleanup_database_error(self) -> None:
        """Test cleanup handles database errors gracefully"""
        # Mock fetch_one to raise an exception
        self.db.fetch_one.side_effect = Exception("Database error")

        success, count = self.phones_db.cleanup_incomplete_registrations()

        assert not success
        assert count == 0

    def test_cleanup_delete_failure(self) -> None:
        """Test cleanup when delete operation fails"""
        # Mock fetch_one to return 2 incomplete registrations
        self.db.fetch_one.return_value = {"count": 2}
        # Mock execute to return False (failure)
        self.db.execute.return_value = False

        success, count = self.phones_db.cleanup_incomplete_registrations()

        assert not success
        assert count == 2
        # Verify DELETE was attempted
        self.db.execute.assert_called_once()

    def test_cleanup_query_structure(self) -> None:
        """Test that cleanup query checks all required fields"""
        self.db.fetch_one.return_value = {"count": 5}
        self.db.execute.return_value = True

        self.phones_db.cleanup_incomplete_registrations()

        # Get the DELETE query
        delete_query = self.db.execute.call_args[0][0]

        # Verify it checks for NULL or empty string for all three fields
        assert "mac_address IS NULL OR mac_address = ''" in delete_query
        assert "ip_address IS NULL OR ip_address = ''" in delete_query
        assert "extension_number IS NULL OR extension_number = ''" in delete_query
        # Verify it uses OR between field conditions (mac_address OR ip_address OR extension_number)
        # Any single missing field should trigger deletion of that record
        assert "OR" in delete_query
# ============================================================================
# Test Runner
# ============================================================================


def run_functional_tests() -> bool:
    """Run functional tests (non-unittest)"""

    try:
        test_clear_all_phones()
        test_clear_empty_table()
        test_register_after_clear()
        test_pbx_preserves_phones_on_boot()

        return True
    except AssertionError as e:
        return False
    except Exception as e:
        import traceback

        traceback.print_exc()
        return False
