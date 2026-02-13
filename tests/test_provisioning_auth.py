#!/usr/bin/env python3
"""
Tests for provisioning API authentication
"""

import json
import time
from http.client import HTTPConnection
from pathlib import Path


from pbx.api.rest_api import PBXAPIServer
from pbx.features.extensions import Extension, ExtensionRegistry
from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.extension_registry = ExtensionRegistry(config)
        self.phone_provisioning = PhoneProvisioning(config)

    def get_status(self) -> dict[str, int]:
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_provisioning_endpoints_require_auth() -> bool:
    """Test that provisioning endpoints require authentication"""

    # Load test config using relative path from test file
    config_path = str(Path(__file__).parent.parent / "test_config.yml")
    config = Config(config_path)

    # Create mock PBX core
    pbx = MockPBXCore(config)

    # Create API server on test port
    test_port = 19099
    api_server = PBXAPIServer(pbx, host="127.0.0.1", port=test_port)

    # Start server
    if not api_server.start():
        return False

    # Wait for server to start
    time.sleep(1)

    # Test endpoints that should require authentication
    endpoints = [
        "/api/provisioning/devices",
        "/api/provisioning/vendors",
        "/api/provisioning/templates",
        "/api/provisioning/diagnostics",
        "/api/provisioning/requests",
    ]

    try:
        conn = HTTPConnection("localhost", test_port, timeout=5)

        for endpoint in endpoints:

            # Test without authentication - should return 401
            conn.request("GET", endpoint)
            response = conn.getresponse()
            response.read()  # Read the response to clear the buffer

            assert (
                response.status == 401
            ), f"{endpoint} should require authentication but returned {response.status}"

        return True

    finally:
        conn.close()
        api_server.stop()


def test_provisioning_endpoints_with_auth() -> bool:
    """Test that provisioning endpoints work with valid authentication"""

    # Load test config using relative path from test file
    config_path = str(Path(__file__).parent.parent / "test_config.yml")
    config = Config(config_path)

    # Create mock PBX core
    pbx = MockPBXCore(config)

    # Add a test extension for authentication (manually create Extension object)
    ext_config = {
        "number": "1001",
        "name": "Test Admin",
        "password_hash": pbx.extension_registry.encryption.hash_password("test123"),
        "email": "admin@test.com",
        "allow_external": True,
        "is_admin": True,
    }
    extension = Extension("1001", "Test Admin", ext_config)
    pbx.extension_registry.extensions["1001"] = extension

    # Create API server on test port
    test_port = 19098
    api_server = PBXAPIServer(pbx, host="127.0.0.1", port=test_port)

    # Start server
    if not api_server.start():
        return False

    # Wait for server to start
    time.sleep(1)

    try:
        conn = HTTPConnection("localhost", test_port, timeout=5)

        # First, login to get a token
        login_data = {"extension": "1001", "password": "test123"}
        headers = {"Content-Type": "application/json"}

        conn.request("POST", "/api/auth/login", body=json.dumps(login_data), headers=headers)
        response = conn.getresponse()
        login_result = json.loads(response.read().decode())

        assert "token" in login_result, f"Login should return a token but got: {login_result}"
        token = login_result["token"]

        # Now test endpoints with authentication
        auth_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        # Test /api/provisioning/vendors
        conn.request("GET", "/api/provisioning/vendors", headers=auth_headers)
        response = conn.getresponse()
        vendors_data = json.loads(response.read().decode())

        assert response.status == 200, f"Should return 200 with auth but got {response.status}"
        assert "vendors" in vendors_data, "Response should contain vendors"
        assert "models" in vendors_data, "Response should contain models"

        # Test /api/provisioning/devices
        conn.request("GET", "/api/provisioning/devices", headers=auth_headers)
        response = conn.getresponse()
        devices_data = json.loads(response.read().decode())

        assert response.status == 200, f"Should return 200 with auth but got {response.status}"
        assert isinstance(devices_data, list), "Response should be a list"

        return True

    finally:
        conn.close()
        api_server.stop()
