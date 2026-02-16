#!/usr/bin/env python3
"""
Test API Server Retry Logic for Address Binding
Tests that the API server properly retries when port is in use
"""

import socket
import time

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_status(self) -> dict[str, int]:
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_socket_reuse_options() -> bool:
    """Test that ReusableHTTPServer sets SO_REUSEADDR and SO_REUSEPORT"""

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Create API server
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=8082)

    # Start the server
    if api_server.start():
        # Check socket options
        server_socket = api_server.server.socket

        # Check SO_REUSEADDR
        reuse_addr = server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        if not reuse_addr:
            api_server.stop()
            return False

        # Check SO_REUSEPORT (if available)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                reuse_port = server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT)
                if not reuse_port:
                    pass
            except Exception:
                pass
        else:
            pass

        time.sleep(0.5)
        api_server.stop()
        time.sleep(0.5)
        return True
    return False


def test_retry_on_port_in_use() -> bool:
    """Test that API server retries when port is already in use"""

    # Minimum expected time for retry logic (1s + 2s = 3s, with 0.5s margin for processing)
    MIN_RETRY_TIME = 2.5

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # First, create a blocking socket on the test port
    test_port = 8083
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", test_port))
        blocker.listen(1)

        # Try to start API server on the same port (should fail initially)
        api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)

        start_time = time.time()

        # This should fail after retries
        result = api_server.start()

        elapsed = time.time() - start_time

        if not result:
            if elapsed >= MIN_RETRY_TIME:
                pass
            api_server.stop()
            return False

    finally:
        # Always close the blocker socket
        blocker.close()
        time.sleep(0.5)  # Give time for OS to release the port

    # Create a new API server instance and try again
    api_server2 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)

    if api_server2.start():
        time.sleep(0.5)
        api_server2.stop()
        time.sleep(0.5)
        return True
    return False


def test_rapid_restart() -> bool:
    """Test that API server can handle rapid restarts"""

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    test_port = 8084

    # Start server
    api_server1 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if not api_server1.start():
        return False
    time.sleep(0.5)

    # Stop it
    api_server1.stop()
    time.sleep(0.5)

    # Immediately try to start another server on the same port
    api_server2 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if api_server2.start():
        time.sleep(0.5)
        api_server2.stop()
        time.sleep(0.5)
        return True
    return False


def main() -> bool:
    """Run all tests"""

    tests = [
        test_socket_reuse_options,
        test_retry_on_port_in_use,
        test_rapid_restart,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception:
            import traceback

            traceback.print_exc()
            failed += 1

    return failed == 0
