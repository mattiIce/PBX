#!/usr/bin/env python3
"""
Test HEAD Request Support for Admin Panel File Checks
Tests that the API server properly responds to HEAD requests
"""

import http.client
import time
from pathlib import Path

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_status(self) -> dict[str, int]:
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_head_request_for_static_files() -> bool:
    """Test that HEAD requests work for static admin files"""

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
        if not api_server.start():
            return False

        time.sleep(0.5)  # Give server time to fully start

        # Test HEAD request for CSS file
        conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=5)

        try:
            conn.request("HEAD", "/admin/css/admin.css")
            response = conn.getresponse()
            status = response.status

            if status == 200:
                # Verify no body is returned
                body = response.read()
                if len(body) != 0:
                    conn.close()
                    return False
            elif status == 501:
                conn.close()
                return False
            elif status == 404:
                pass  # Acceptable in test environment
            else:
                conn.close()
                return False

            conn.close()

            # Test HEAD request for JS file
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=5)
            conn.request("HEAD", "/admin/js/admin.js")
            response = conn.getresponse()
            status = response.status

            if status in [200, 404]:  # 200 OK or 404 if file doesn't exist
                # Verify no body is returned
                body = response.read()
                if len(body) != 0:
                    conn.close()
                    return False
            elif status == 501:
                conn.close()
                return False
            else:
                pass

            conn.close()

            # Test HEAD request for API endpoint
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=5)
            conn.request("HEAD", "/health")
            response = conn.getresponse()
            status = response.status

            if status == 200:
                # Verify no body is returned
                body = response.read()
                if len(body) != 0:
                    conn.close()
                    return False
            elif status == 501:
                conn.close()
                return False
            else:
                pass

            conn.close()

            return True

        except (OSError, ValueError):
            import traceback

            traceback.print_exc()
            return False

    finally:
        # Stop the server
        api_server.stop()
        time.sleep(0.5)
