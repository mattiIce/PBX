#!/usr/bin/env python3
"""
Test license API routes integration
Tests that license management routes are accessible and working
"""

import http.client
import json
import time


from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.extension_db = None  # No database for this test

    def get_status(self) -> dict[str, int]:
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_license_routes() -> bool:
    """Test that license API routes are accessible"""

    # Create config
    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Use a unique port for testing
    test_port = 18090

    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if not api_server.start():
        return False

    try:
        # Wait for server to be ready
        time.sleep(1)

        # Test 1: License status endpoint (public)
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        conn.request("GET", "/api/license/status")
        response = conn.getresponse()
        data = json.loads(response.read().decode())
        conn.close()

        if response.status != 200 and data.get("success"):
            return False

        # Test 2: License features endpoint (public)
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        conn.request("GET", "/api/license/features")
        response = conn.getresponse()
        data = json.loads(response.read().decode())
        conn.close()

        if response.status != 200 and data.get("success"):
            return False

        # Test 3: License generate endpoint (requires admin auth)

        # First, try without authentication (should fail)
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        body = json.dumps({"type": "trial", "issued_to": "Test Organization"})
        conn.request(
            "POST", "/api/license/generate", body=body, headers={"Content-Type": "application/json"}
        )
        response = conn.getresponse()
        json.loads(response.read().decode())
        conn.close()

        if response.status != 401:
            return False

        # Test 4: Get license admin token
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        login_body = json.dumps({"extension": "9322", "username": "ICE", "password": "26697647"})
        conn.request(
            "POST", "/api/auth/login", body=login_body, headers={"Content-Type": "application/json"}
        )
        response = conn.getresponse()
        login_data = json.loads(response.read().decode())
        conn.close()

        if response.status == 200 and login_data.get("success"):
            token = login_data.get("token")

            # Test 5: Try license generate with authentication
            conn = http.client.HTTPConnection("127.0.0.1", test_port)
            body = json.dumps({"type": "trial", "issued_to": "Test Organization"})
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
            conn.request("POST", "/api/license/generate", body=body, headers=headers)
            response = conn.getresponse()
            data = json.loads(response.read().decode())
            conn.close()

            if response.status != 200 and data.get("success"):
                return False
        else:
            pass

        return True

    finally:
        # Clean up
        api_server.stop()
