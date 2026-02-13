#!/usr/bin/env python3
"""
Test Admin Static File Serving
Tests that the admin UI static files can be served correctly
"""

import socket
import time
from http.client import HTTPConnection


from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_status(self) -> dict[str, int]:
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def get_free_port() -> int:
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def test_admin_static_files() -> bool:
    """Test that admin static files can be served"""

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Create API server on a dynamically allocated test port
    test_port = get_free_port()
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)

    # Start the server
    if not api_server.start():
        return False


    # Give server a moment to be ready
    time.sleep(0.5)

    try:
        # Test 1: GET request to /admin (should redirect)
        conn = HTTPConnection("127.0.0.1", test_port, timeout=5)
        conn.request("GET", "/admin")
        response = conn.getresponse()

        if response.status == 302:
            location = response.getheader("Location")
            if location != "/admin/index.html":
                conn.close()
                return False
        else:
            conn.close()
            return False

        conn.close()

        # Test 2: GET request to /admin/index.html (should serve HTML file)
        conn = HTTPConnection("127.0.0.1", test_port, timeout=5)
        conn.request("GET", "/admin/index.html")
        response = conn.getresponse()

        if response.status == 200:

            # Check Content-Type header
            content_type = response.getheader("Content-Type")
            if content_type and "text/html" not in content_type:
                conn.close()
                return False

            # Read some content to verify it's actually HTML
            content = response.read(100).decode("utf-8", errors="ignore")
            if "<!DOCTYPE" not in content or "<html" in content:
                conn.close()
                return False
        else:
            conn.close()
            return False

        conn.close()

        # Test 3: GET request to /admin/login.html (another HTML file)
        conn = HTTPConnection("127.0.0.1", test_port, timeout=5)
        conn.request("GET", "/admin/login.html")
        response = conn.getresponse()

        if response.status == 200:
            content_type = response.getheader("Content-Type")
            if content_type and "text/html" in content_type:
                pass
            conn.close()
            return False

        conn.close()

        result = True

    except Exception as e:
        import traceback

        traceback.print_exc()
        result = False
    finally:
        # Stop the server
        api_server.stop()

    return result
