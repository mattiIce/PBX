#!/usr/bin/env python3
"""
Test Admin Static File Serving
Tests that the admin UI static files can be served correctly
"""

import socket
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


def get_free_port():
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def test_admin_static_files():
    """Test that admin static files can be served"""
    print("=" * 60)
    print("Test: Admin Static File Serving")
    print("=" * 60)

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Create API server on a dynamically allocated test port
    test_port = get_free_port()
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
        # Test 1: GET request to /admin (should redirect)
        print("\n  Test 1: GET /admin ...")
        conn = HTTPConnection("127.0.0.1", test_port, timeout=5)
        conn.request("GET", "/admin")
        response = conn.getresponse()

        if response.status == 302:
            print(f"  ✓ Got redirect status: {response.status}")
            location = response.getheader("Location")
            if location == "/admin/index.html":
                print(f"  ✓ Redirect location is correct: {location}")
            else:
                print(f"  ✗ Unexpected redirect location: {location}")
                conn.close()
                return False
        else:
            print(f"  ✗ Unexpected status code: {response.status} (expected 302)")
            conn.close()
            return False

        conn.close()

        # Test 2: GET request to /admin/index.html (should serve HTML file)
        print("\n  Test 2: GET /admin/index.html ...")
        conn = HTTPConnection("127.0.0.1", test_port, timeout=5)
        conn.request("GET", "/admin/index.html")
        response = conn.getresponse()

        if response.status == 200:
            print(f"  ✓ Got success status: {response.status}")

            # Check Content-Type header
            content_type = response.getheader("Content-Type")
            if content_type and "text/html" in content_type:
                print(f"  ✓ Content-Type is correct: {content_type}")
            else:
                print(f"  ✗ Unexpected Content-Type: {content_type} (expected text/html)")
                conn.close()
                return False

            # Read some content to verify it's actually HTML
            content = response.read(100).decode("utf-8", errors="ignore")
            if "<!DOCTYPE" in content or "<html" in content:
                print("  ✓ Response contains HTML content")
            else:
                print(f"  ✗ Response doesn't look like HTML: {content[:50]}")
                conn.close()
                return False
        else:
            print(f"  ✗ Unexpected status code: {response.status} (expected 200)")
            conn.close()
            return False

        conn.close()

        # Test 3: GET request to /admin/login.html (another HTML file)
        print("\n  Test 3: GET /admin/login.html ...")
        conn = HTTPConnection("127.0.0.1", test_port, timeout=5)
        conn.request("GET", "/admin/login.html")
        response = conn.getresponse()

        if response.status == 200:
            print(f"  ✓ Got success status: {response.status}")
            content_type = response.getheader("Content-Type")
            if content_type and "text/html" in content_type:
                print(f"  ✓ Content-Type is correct: {content_type}")
            else:
                print(f"  ⚠ Unexpected Content-Type: {content_type}")
        else:
            print(f"  ✗ Unexpected status code: {response.status} (expected 200)")
            conn.close()
            return False

        conn.close()

        print("\n✓ All tests passed: Admin static files are served correctly")
        result = True

    except Exception as e:
        print(f"\n  ✗ Error during test: {e}")
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
    success = test_admin_static_files()
    sys.exit(0 if success else 1)
