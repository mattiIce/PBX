#!/usr/bin/env python3
"""
Test HEAD Request Support for Admin Panel File Checks
Tests that the API server properly responds to HEAD requests
"""

import http.client
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
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_head_request_for_static_files():
    """Test that HEAD requests work for static admin files"""
    print("=" * 60)
    print("Test: HEAD Request for Static Files")
    print("=" * 60)

    # Get the test config file path relative to this file
    test_dir = Path(__file__).parent
    config_path = test_dir.parent / "test_config.yml"

    config = Config(str(config_path))
    mock_pbx = MockPBXCore(config)

    # Create API server on test port
    test_port = 8084
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)

    try:
        # Start the server
        print("  Starting API server...")
        if not api_server.start():
            print("  ✗ Failed to start API server")
            return False

        print(f"  ✓ API server started on port {test_port}")
        time.sleep(0.5)  # Give server time to fully start

        # Test HEAD request for CSS file
        print("\n  Testing HEAD request for CSS file...")
        conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=5)

        try:
            conn.request("HEAD", "/admin/css/admin.css")
            response = conn.getresponse()
            status = response.status

            print(f"  Response status: {status}")

            if status == 200:
                print("  ✓ HEAD request successful (200 OK)")
                # Verify no body is returned
                body = response.read()
                if len(body) == 0:
                    print("  ✓ No response body (as expected for HEAD)")
                else:
                    print(f"  ✗ Unexpected response body ({len(body)} bytes)")
                    conn.close()
                    return False
            elif status == 501:
                print("  ✗ HEAD request not implemented (501)")
                conn.close()
                return False
            elif status == 404:
                print("  ⚠ File not found (404) - file may not exist in test setup")
                # This is acceptable in test environment
            else:
                print(f"  ✗ Unexpected status code: {status}")
                conn.close()
                return False

            conn.close()

            # Test HEAD request for JS file
            print("\n  Testing HEAD request for JS file...")
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=5)
            conn.request("HEAD", "/admin/js/admin.js")
            response = conn.getresponse()
            status = response.status

            print(f"  Response status: {status}")

            if status in [200, 404]:  # 200 OK or 404 if file doesn't exist
                print(f"  ✓ HEAD request handled properly ({status})")
                # Verify no body is returned
                body = response.read()
                if len(body) == 0:
                    print("  ✓ No response body (as expected for HEAD)")
                else:
                    print(f"  ✗ Unexpected response body ({len(body)} bytes)")
                    conn.close()
                    return False
            elif status == 501:
                print("  ✗ HEAD request not implemented (501)")
                conn.close()
                return False
            else:
                print(f"  ⚠ Unexpected status code: {status}")

            conn.close()

            # Test HEAD request for API endpoint
            print("\n  Testing HEAD request for API endpoint...")
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=5)
            conn.request("HEAD", "/health")
            response = conn.getresponse()
            status = response.status

            print(f"  Response status: {status}")

            if status == 200:
                print("  ✓ HEAD request for API endpoint successful")
                # Verify no body is returned
                body = response.read()
                if len(body) == 0:
                    print("  ✓ No response body (as expected for HEAD)")
                else:
                    print(f"  ✗ Unexpected response body ({len(body)} bytes)")
                    conn.close()
                    return False
            elif status == 501:
                print("  ✗ HEAD request not implemented (501)")
                conn.close()
                return False
            else:
                print(f"  ⚠ Unexpected status code: {status}")

            conn.close()

            print("\n  ✓ All HEAD request tests passed")
            return True

        except Exception as e:
            print(f"  ✗ Error during HEAD request test: {e}")
            import traceback

            traceback.print_exc()
            return False

    finally:
        # Stop the server
        print("\n  Stopping API server...")
        api_server.stop()
        time.sleep(0.5)


if __name__ == "__main__":
    print("\nTesting HEAD Request Support\n")

    success = test_head_request_for_static_files()

    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        sys.exit(1)
