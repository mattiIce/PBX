#!/usr/bin/env python3
"""
Test API server restart and socket reuse
Tests that the server can be stopped and restarted quickly without "Address already in use" errors
"""

import time


from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_status(self) -> dict[str, int]:
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_api_server_restart() -> bool:
    """Test that API server can be restarted quickly without address conflicts"""

    # Create config
    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Use a unique port for testing
    test_port = 18080


    # First start
    api_server1 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if not api_server1.start():
        return False

    # Give it a moment to fully start
    time.sleep(0.5)

    # Stop the server
    api_server1.stop()

    # Wait a brief moment for cleanup
    time.sleep(0.5)

    # Immediate restart - this should succeed with SO_REUSEADDR
    api_server2 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if not api_server2.start():
        return False

    # Give it a moment
    time.sleep(0.5)

    # Clean up
    api_server2.stop()

    return True


def test_failed_start_cleanup() -> bool:
    """Test that failed server start properly cleans up socket"""

    # Create config
    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Use a unique port for testing
    test_port = 18081


    # Start a server successfully first
    api_server1 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if not api_server1.start():
        return False

    time.sleep(0.5)

    # Try to start another server on the same port (should fail)
    api_server2 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if api_server2.start():
        api_server2.stop()
        api_server1.stop()
        return False

    # Verify the second server cleaned up properly
    if api_server2.server is not None:
        api_server1.stop()
        return False

    # Verify running flag was reset
    if api_server2.running:
        api_server1.stop()
        return False

    # Verify thread reference was cleared
    if api_server2.server_thread is not None:
        api_server1.stop()
        return False

    # Stop the first server
    api_server1.stop()

    time.sleep(0.5)

    # Now the second server should be able to start
    api_server3 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if not api_server3.start():
        return False

    time.sleep(0.5)
    api_server3.stop()

    return True
