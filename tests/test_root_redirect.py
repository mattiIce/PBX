#!/usr/bin/env python3
"""
Test Root Path Redirect to Admin Panel
Tests that the root path "/" redirects to "/admin"
"""

import time
from http.client import HTTPConnection
from pathlib import Path

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_status(self) -> dict[str, int]:
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_root_redirect() -> bool:
    """Test that root path redirects to /admin"""

    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Create API server on a test port
    test_port = 8083
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)

    # Start the server
    if not api_server.start():
        return False

    # Give server a moment to be ready
    time.sleep(0.5)

    try:
        # Test GET request to root path
        conn = HTTPConnection("127.0.0.1", test_port, timeout=5)
        conn.request("GET", "/")
        response = conn.getresponse()

        # Check for redirect (302)
        if response.status == 302:
            # Check Location header
            location = response.getheader("Location")
            if location == "/admin":
                result = True
            else:
                result = False
        else:
            result = False

        conn.close()

    except (OSError, ValueError):
        import traceback

        traceback.print_exc()
        result = False
    finally:
        # Stop the server
        api_server.stop()

    return result
