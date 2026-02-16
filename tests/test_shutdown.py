#!/usr/bin/env python3
"""
Test PBX shutdown functionality
"""

import os
import tempfile
import time
from pathlib import Path

import yaml

from pbx.core.pbx import PBXCore


def test_pbx_shutdown() -> None:
    """Test that PBX shuts down properly when stop() is called"""

    # Create a minimal config file
    config_data = {
        "server": {
            "sip_host": "127.0.0.1",
            "sip_port": 15060,  # Use non-standard port for testing
            "external_ip": "127.0.0.1",
            "rtp_port_range_start": 20000,
            "rtp_port_range_end": 20100,
        },
        "api": {"host": "127.0.0.1", "port": 18080},  # Use non-standard port for testing
        "logging": {"level": "ERROR", "console": False},  # Reduce log noise during testing
        "extensions": [
            {
                "number": "1001",
                "name": "Test User",
                "password": "test1001",
                "email": "test@example.com",
            }
        ],
        "dialplan": {"internal_pattern": "^1[0-9]{3}$"},
        "features": {"call_recording": False, "voicemail": False},
        "voicemail": {"storage_path": "/tmp/test_voicemail"},
        "provisioning": {"enabled": False},
    }

    # Write config to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(config_data, f)
        config_file = f.name

    try:
        # Create and start PBX
        pbx = PBXCore(config_file)
        assert pbx.start(), "PBX should start successfully"

        # Give it a moment to fully initialize
        time.sleep(2)

        # Verify it's running
        assert pbx.running, "PBX should be running"

        # Stop the PBX
        pbx.stop()

        # Give threads a moment to stop
        time.sleep(2)

        # Verify it stopped
        assert not pbx.running, "PBX should not be running after stop()"

    finally:
        # Clean up config file
        if Path(config_file).exists():
            os.unlink(config_file)


def test_signal_handling_simulation() -> None:
    """Test that signal handling mechanism works"""

    # Create a minimal config file
    config_data = {
        "server": {
            "sip_host": "127.0.0.1",
            "sip_port": 15061,  # Use different port
            "external_ip": "127.0.0.1",
            "rtp_port_range_start": 20100,
            "rtp_port_range_end": 20200,
        },
        "api": {"host": "127.0.0.1", "port": 18081},  # Use different port
        "logging": {"level": "ERROR", "console": False},
        "extensions": [
            {
                "number": "1001",
                "name": "Test User",
                "password": "test1001",
                "email": "test@example.com",
            }
        ],
        "dialplan": {"internal_pattern": "^1[0-9]{3}$"},
        "features": {"call_recording": False, "voicemail": False},
        "voicemail": {"storage_path": "/tmp/test_voicemail"},
        "provisioning": {"enabled": False},
    }

    # Write config to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(config_data, f)
        config_file = f.name

    running = True
    pbx = None

    def signal_handler_test() -> None:
        """Simulate the signal handler"""
        nonlocal running
        running = False
        if pbx:
            pbx.stop()

    try:
        # Create and start PBX
        pbx = PBXCore(config_file)
        assert pbx.start(), "PBX should start successfully"

        # Simulate the main loop
        loop_iterations = 0
        max_iterations = 5

        # After a few iterations, simulate Ctrl+C
        while running and loop_iterations < max_iterations:
            time.sleep(0.5)
            loop_iterations += 1

            # Simulate signal after 2 iterations
            if loop_iterations == 2:
                signal_handler_test()

        # Verify the loop exited because running was set to False
        assert not running, "Running flag should be False after signal"
        assert not pbx.running, "PBX should not be running"

    finally:
        # Clean up
        if Path(config_file).exists():
            os.unlink(config_file)
