#!/usr/bin/env python3
"""
Test API Server Retry Logic for Address Binding
Tests that the API server properly retries when port is in use
"""

import socket
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    print("=" * 60)
    print("Test 1: Socket Reuse Options")
    print("=" * 60)

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Create API server
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=8082)

    # Start the server
    print("  Starting API server...")
    if api_server.start():
        print("  ✓ API server started successfully")

        # Check socket options
        server_socket = api_server.server.socket

        # Check SO_REUSEADDR
        reuse_addr = server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        print(f"  SO_REUSEADDR: {reuse_addr}")
        if reuse_addr:
            print("  ✓ SO_REUSEADDR is enabled")
        else:
            print("  ✗ SO_REUSEADDR is not enabled")
            api_server.stop()
            return False

        # Check SO_REUSEPORT (if available)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                reuse_port = server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT)
                print(f"  SO_REUSEPORT: {reuse_port}")
                if reuse_port:
                    print("  ✓ SO_REUSEPORT is enabled")
                else:
                    print("  ⚠ SO_REUSEPORT is not enabled (optional)")
            except Exception as e:
                print(f"  ⚠ SO_REUSEPORT check failed: {e} (optional)")
        else:
            print("  ⚠ SO_REUSEPORT not available on this platform (optional)")

        time.sleep(0.5)
        api_server.stop()
        time.sleep(0.5)
        print()
        return True
    else:
        print("  ✗ Failed to start API server")
        return False


def test_retry_on_port_in_use() -> bool:
    """Test that API server retries when port is already in use"""
    print("=" * 60)
    print("Test 2: Retry on Port In Use")
    print("=" * 60)

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
        print(f"  ✓ Blocking socket created on port {test_port}")

        # Try to start API server on the same port (should fail initially)
        api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)

        print(f"  Starting API server on port {test_port} (should retry)...")
        start_time = time.time()

        # This should fail after retries
        result = api_server.start()

        elapsed = time.time() - start_time
        print(f"  Elapsed time: {elapsed:.2f}s")

        if not result:
            print("  ✓ API server correctly failed after retries")
            if elapsed >= MIN_RETRY_TIME:
                print(f"  ✓ Retry logic executed (took {elapsed:.2f}s)")
            else:
                print(f"  ⚠ Retry may not have executed (took {elapsed:.2f}s)")
        else:
            print("  ✗ API server should have failed when port is blocked")
            api_server.stop()
            return False

    finally:
        # Always close the blocker socket
        blocker.close()
        print("  ✓ Blocker socket closed")
        time.sleep(0.5)  # Give time for OS to release the port

    # Create a new API server instance and try again
    api_server2 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    print(f"  Starting API server on port {test_port} again (should succeed)...")

    if api_server2.start():
        print("  ✓ API server started successfully after blocker removed")
        time.sleep(0.5)
        api_server2.stop()
        time.sleep(0.5)
        print()
        return True
    else:
        print("  ✗ API server should have started after blocker removed")
        return False


def test_rapid_restart() -> bool:
    """Test that API server can handle rapid restarts"""
    print("=" * 60)
    print("Test 3: Rapid Restart")
    print("=" * 60)

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    test_port = 8084

    # Start server
    api_server1 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    print(f"  Starting first API server on port {test_port}...")
    if not api_server1.start():
        print("  ✗ Failed to start first API server")
        return False
    print("  ✓ First API server started")
    time.sleep(0.5)

    # Stop it
    print("  Stopping first API server...")
    api_server1.stop()
    time.sleep(0.5)
    print("  ✓ First API server stopped")

    # Immediately try to start another server on the same port
    api_server2 = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    print(f"  Starting second API server on port {test_port} (rapid restart)...")
    if api_server2.start():
        print("  ✓ Second API server started successfully (rapid restart worked)")
        time.sleep(0.5)
        api_server2.stop()
        time.sleep(0.5)
        print()
        return True
    else:
        print("  ✗ Failed to start second API server (rapid restart failed)")
        return False


def main() -> bool:
    """Run all tests"""
    print("\n")
    print("=" * 60)
    print("API Server Retry Logic Tests")
    print("=" * 60)
    print()

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
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print()

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
