#!/usr/bin/env python3
"""
Test API server restart and socket reuse
Tests that the server can be stopped and restarted quickly without "Address already in use" errors
"""
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config):
        self.config = config

    def get_status(self):
        return {
            'registered_extensions': 0,
            'active_calls': 0,
            'uptime': 0
        }


def test_api_server_restart():
    """Test that API server can be restarted quickly without address conflicts"""
    print("=" * 60)
    print("Test: API Server Restart and Socket Reuse")
    print("=" * 60)

    # Create config
    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Use a unique port for testing
    test_port = 18080

    print(f"Testing API server restart on port {test_port}...")
    print()

    # First start
    print("1. Starting API server (first time)...")
    api_server1 = PBXAPIServer(mock_pbx, host='127.0.0.1', port=test_port)
    if not api_server1.start():
        print("  ✗ Failed to start API server (first time)")
        return False
    print("  ✓ API server started successfully")
    
    # Give it a moment to fully start
    time.sleep(0.5)

    # Stop the server
    print("2. Stopping API server...")
    api_server1.stop()
    print("  ✓ API server stopped")
    
    # Wait a brief moment for cleanup
    time.sleep(0.5)

    # Immediate restart - this should succeed with SO_REUSEADDR
    print("3. Restarting API server (should reuse address)...")
    api_server2 = PBXAPIServer(mock_pbx, host='127.0.0.1', port=test_port)
    if not api_server2.start():
        print("  ✗ Failed to restart API server - Address already in use?")
        return False
    print("  ✓ API server restarted successfully (socket reused)")
    
    # Give it a moment
    time.sleep(0.5)

    # Clean up
    print("4. Cleaning up...")
    api_server2.stop()
    print("  ✓ API server stopped")

    print()
    print("✓ All tests passed - socket reuse working correctly")
    print()
    return True


def test_failed_start_cleanup():
    """Test that failed server start properly cleans up socket"""
    print("=" * 60)
    print("Test: Failed Start Cleanup")
    print("=" * 60)

    # Create config
    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Use a unique port for testing
    test_port = 18081

    print(f"Testing cleanup after failed start on port {test_port}...")
    print()

    # Start a server successfully first
    print("1. Starting API server...")
    api_server1 = PBXAPIServer(mock_pbx, host='127.0.0.1', port=test_port)
    if not api_server1.start():
        print("  ✗ Failed to start API server")
        return False
    print("  ✓ API server started successfully")
    
    time.sleep(0.5)

    # Try to start another server on the same port (should fail)
    print("2. Attempting to start second server on same port (should fail)...")
    api_server2 = PBXAPIServer(mock_pbx, host='127.0.0.1', port=test_port)
    if api_server2.start():
        print("  ✗ Second server should have failed to start")
        api_server2.stop()
        api_server1.stop()
        return False
    print("  ✓ Second server correctly failed to start")
    
    # Verify the second server cleaned up properly
    if api_server2.server is not None:
        print("  ✗ Failed server didn't clean up (server object still exists)")
        api_server1.stop()
        return False
    print("  ✓ Failed server properly cleaned up")
    
    # Verify running flag was reset
    if api_server2.running:
        print("  ✗ Failed server didn't reset running flag")
        api_server1.stop()
        return False
    print("  ✓ Failed server reset running flag")
    
    # Verify thread reference was cleared
    if api_server2.server_thread is not None:
        print("  ✗ Failed server didn't clear thread reference")
        api_server1.stop()
        return False
    print("  ✓ Failed server cleared thread reference")

    # Stop the first server
    print("3. Stopping first server...")
    api_server1.stop()
    print("  ✓ First server stopped")
    
    time.sleep(0.5)

    # Now the second server should be able to start
    print("4. Starting new server after cleanup...")
    api_server3 = PBXAPIServer(mock_pbx, host='127.0.0.1', port=test_port)
    if not api_server3.start():
        print("  ✗ Failed to start server after cleanup")
        return False
    print("  ✓ Server started successfully after cleanup")
    
    time.sleep(0.5)
    api_server3.stop()

    print()
    print("✓ Cleanup test passed")
    print()
    return True


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("API Server Restart Tests")
    print("=" * 60 + "\n")

    all_passed = True

    # Run tests
    if not test_api_server_restart():
        all_passed = False

    if not test_failed_start_cleanup():
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60 + "\n")

    sys.exit(0 if all_passed else 1)
