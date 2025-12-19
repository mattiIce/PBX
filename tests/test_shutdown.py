#!/usr/bin/env python3
"""
Test PBX shutdown functionality
"""
import os
import signal
import sys
import tempfile
import threading
import time

import yaml

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.core.pbx import PBXCore


def test_pbx_shutdown():
    """Test that PBX shuts down properly when stop() is called"""
    print("Testing PBX shutdown...")

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
        print("✓ PBX started")

        # Give it a moment to fully initialize
        time.sleep(2)

        # Verify it's running
        assert pbx.running, "PBX should be running"
        print("✓ PBX is running")

        # Stop the PBX
        pbx.stop()
        print("✓ PBX stop() called")

        # Give threads a moment to stop
        time.sleep(2)

        # Verify it stopped
        assert not pbx.running, "PBX should not be running after stop()"
        print("✓ PBX stopped successfully")

    finally:
        # Clean up config file
        if os.path.exists(config_file):
            os.unlink(config_file)

    print("✓ PBX shutdown test passed")


def test_signal_handling_simulation():
    """Test that signal handling mechanism works"""
    print("\nTesting signal handling simulation...")

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

    def signal_handler_test():
        """Simulate the signal handler"""
        nonlocal running, pbx
        print("Signal handler called")
        running = False
        if pbx:
            pbx.stop()

    try:
        # Create and start PBX
        pbx = PBXCore(config_file)
        assert pbx.start(), "PBX should start successfully"
        print("✓ PBX started")

        # Simulate the main loop
        loop_iterations = 0
        max_iterations = 5

        # After a few iterations, simulate Ctrl+C
        while running and loop_iterations < max_iterations:
            time.sleep(0.5)
            loop_iterations += 1

            # Simulate signal after 2 iterations
            if loop_iterations == 2:
                print("Simulating Ctrl+C signal...")
                signal_handler_test()

        # Verify the loop exited because running was set to False
        assert not running, "Running flag should be False after signal"
        assert not pbx.running, "PBX should not be running"
        print("✓ Signal handling simulation passed")

    finally:
        # Clean up
        if os.path.exists(config_file):
            os.unlink(config_file)

    print("✓ Signal handling test passed")


def run_all_tests():
    """Run all tests in this module"""
    test_pbx_shutdown()
    test_signal_handling_simulation()
    print("\n✅ All shutdown tests passed!")
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
