#!/usr/bin/env python3
"""
Test Root Path Redirect to Admin Panel
Tests that the root path "/" redirects to "/admin"
"""
import sys
import time
from http.client import HTTPConnection
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
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_root_redirect():
    """Test that root path redirects to /admin"""
    print("=" * 60)
    print("Test: Root Path Redirect to Admin Panel")
    print("=" * 60)

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Create API server on a test port
    test_port = 8083
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)

    # Start the server
    print("  Starting API server...")
    if not api_server.start():
        print("  ✗ Failed to start API server")
        return False

    print("  ✓ API server started successfully")

    # Give server a moment to be ready
    time.sleep(0.5)

    try:
        # Test GET request to root path
        print("  Testing GET / ...")
        conn = HTTPConnection("127.0.0.1", test_port, timeout=5)
        conn.request("GET", "/")
        response = conn.getresponse()

        # Check for redirect (302)
        if response.status == 302:
            print(f"  ✓ Got redirect status: {response.status}")

            # Check Location header
            location = response.getheader("Location")
            if location == "/admin":
                print(f"  ✓ Redirect location is correct: {location}")
                print("\n✓ Test passed: Root path correctly redirects to /admin")
                result = True
            else:
                print(f"  ✗ Unexpected redirect location: {location} (expected /admin)")
                result = False
        else:
            print(f"  ✗ Unexpected status code: {response.status} (expected 302)")
            result = False

        conn.close()

    except Exception as e:
        print(f"  ✗ Error during test: {e}")
        import traceback

        traceback.print_exc()
        result = False
    finally:
        # Stop the server
        print("\n  Stopping API server...")
        api_server.stop()
        print("  ✓ API server stopped")

    return result


if __name__ == "__main__":
    success = test_root_redirect()
    sys.exit(0 if success else 1)
