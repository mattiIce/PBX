#!/usr/bin/env python3
"""
Tests for phone provisioning persistence in database
"""

import os
import shutil
import tempfile
from pathlib import Path

from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def test_provisioning_persistence() -> None:
    """Test that provisioned devices persist across restarts"""

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"

    try:
        # Create minimal config
        config = Config("config.yml")
        config.config["database"] = {"type": "sqlite", "path": db_path}
        config.config["provisioning"] = {"enabled": True}
        config.config["server"] = {"external_ip": "192.168.1.14", "sip_port": 5060}
        config.config["api"] = {"port": 9000}

        # Initialize database
        db1 = DatabaseBackend(config)
        assert db1.connect(), "Failed to connect to database"
        assert db1.create_tables(), "Failed to create tables"

        # Create first provisioning instance and register devices
        provisioning1 = PhoneProvisioning(config, database=db1)

        # Register some devices
        provisioning1.register_device("00:15:65:12:34:56", "1001", "yealink", "t46s")
        provisioning1.register_device("00:15:65:12:34:57", "1002", "polycom", "vvx450")

        # Verify devices were registered
        assert len(provisioning1.devices) == 2, (
            f"Expected 2 devices, got {len(provisioning1.devices)}"
        )

        # Disconnect database
        db1.disconnect()

        # Create new database connection (simulating restart)
        db2 = DatabaseBackend(config)
        assert db2.connect(), "Failed to reconnect to database"

        # Create new provisioning instance (simulating restart)
        provisioning2 = PhoneProvisioning(config, database=db2)

        # Verify devices were loaded from database
        assert len(provisioning2.devices) == 2, (
            f"Expected 2 devices after reload, got {len(provisioning2.devices)}"
        )

        # Verify device details
        device1_reloaded = provisioning2.get_device("00:15:65:12:34:56")
        assert device1_reloaded is not None, "Device 1 not found after reload"
        assert device1_reloaded.extension_number == "1001", "Wrong extension for device 1"
        assert device1_reloaded.vendor == "yealink", "Wrong vendor for device 1"

        device2_reloaded = provisioning2.get_device("00:15:65:12:34:57")
        assert device2_reloaded is not None, "Device 2 not found after reload"
        assert device2_reloaded.extension_number == "1002", "Wrong extension for device 2"
        assert device2_reloaded.vendor == "polycom", "Wrong vendor for device 2"

        # Clean up
        db2.disconnect()

    finally:
        # Clean up
        shutil.rmtree(temp_dir)


def test_static_ip_assignment() -> None:
    """Test setting static IP for a device"""

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"

    try:
        # Create minimal config
        config = Config("config.yml")
        config.config["database"] = {"type": "sqlite", "path": db_path}
        config.config["provisioning"] = {"enabled": True}
        config.config["server"] = {"external_ip": "192.168.1.14", "sip_port": 5060}
        config.config["api"] = {"port": 9000}

        # Initialize database
        db = DatabaseBackend(config)
        assert db.connect(), "Failed to connect to database"
        assert db.create_tables(), "Failed to create tables"

        # Create provisioning instance
        provisioning = PhoneProvisioning(config, database=db)

        # Register a device
        provisioning.register_device("00:15:65:12:34:56", "1001", "yealink", "t46s")

        # Set static IP
        success, message = provisioning.set_static_ip("00:15:65:12:34:56", "192.168.1.100")
        assert success, f"Failed to set static IP: {message}"

        # Verify static IP was set
        static_ip = provisioning.get_static_ip("00:15:65:12:34:56")
        assert static_ip == "192.168.1.100", f"Expected 192.168.1.100, got {static_ip}"

        # Clean up
        db.disconnect()

    finally:
        # Clean up
        shutil.rmtree(temp_dir)


def test_device_unregister_removes_from_db() -> None:
    """Test that unregistering a device removes it from database"""

    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"

    try:
        # Create minimal config
        config = Config("config.yml")
        config.config["database"] = {"type": "sqlite", "path": db_path}
        config.config["provisioning"] = {"enabled": True}
        config.config["server"] = {"external_ip": "192.168.1.14", "sip_port": 5060}
        config.config["api"] = {"port": 9000}

        # Initialize database
        db1 = DatabaseBackend(config)
        assert db1.connect(), "Failed to connect to database"
        assert db1.create_tables(), "Failed to create tables"

        # Create provisioning instance and register device
        provisioning1 = PhoneProvisioning(config, database=db1)
        provisioning1.register_device("00:15:65:12:34:56", "1001", "yealink", "t46s")

        # Verify device exists in memory
        assert len(provisioning1.devices) == 1, "Device not registered"

        # Unregister device
        success = provisioning1.unregister_device("00:15:65:12:34:56")
        assert success, "Failed to unregister device"

        # Verify device removed from memory
        assert len(provisioning1.devices) == 0, "Device not removed from memory"

        # Disconnect and reconnect
        db1.disconnect()

        db2 = DatabaseBackend(config)
        assert db2.connect(), "Failed to reconnect to database"

        # Create new provisioning instance
        provisioning2 = PhoneProvisioning(config, database=db2)

        # Verify device not loaded (it was deleted from database)
        assert len(provisioning2.devices) == 0, "Device should not exist in database"

        # Clean up
        db2.disconnect()

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
