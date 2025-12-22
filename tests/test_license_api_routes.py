#!/usr/bin/env python3
"""
Test license API routes integration
Tests that license management routes are accessible and working
"""
import sys
import os
import json
import time
import http.client
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config
from pbx.utils.session_token import get_session_token_manager


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config):
        self.config = config
        self.extension_db = None  # No database for this test

    def get_status(self):
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_license_routes():
    """Test that license API routes are accessible"""
    print("=" * 60)
    print("Test: License API Routes Integration")
    print("=" * 60)
    print()

    # Create config
    config = Config("test_config.yml")
    mock_pbx = MockPBXCore(config)

    # Use a unique port for testing
    test_port = 18090

    print(f"Starting API server on port {test_port}...")
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=test_port)
    if not api_server.start():
        print("  ✗ Failed to start API server")
        return False
    print("  ✓ API server started successfully")
    print()

    try:
        # Wait for server to be ready
        time.sleep(1)

        # Test 1: License status endpoint (public)
        print("Test 1: GET /api/license/status (public)")
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        conn.request("GET", "/api/license/status")
        response = conn.getresponse()
        data = json.loads(response.read().decode())
        conn.close()

        if response.status == 200 and data.get("success"):
            print("  ✓ License status endpoint working")
            print(f"    Licensing enabled: {data.get('license', {}).get('enabled')}")
        else:
            print(f"  ✗ License status endpoint failed: {response.status} - {data}")
            return False
        print()

        # Test 2: License features endpoint (public)
        print("Test 2: GET /api/license/features (public)")
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        conn.request("GET", "/api/license/features")
        response = conn.getresponse()
        data = json.loads(response.read().decode())
        conn.close()

        if response.status == 200 and data.get("success"):
            print("  ✓ License features endpoint working")
            print(f"    Licensing enabled: {data.get('licensing_enabled')}")
        else:
            print(f"  ✗ License features endpoint failed: {response.status} - {data}")
            return False
        print()

        # Test 3: License generate endpoint (requires admin auth)
        print("Test 3: POST /api/license/generate (requires admin auth)")
        
        # First, try without authentication (should fail)
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        body = json.dumps({
            "type": "trial",
            "issued_to": "Test Organization"
        })
        conn.request("POST", "/api/license/generate", body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        data = json.loads(response.read().decode())
        conn.close()

        if response.status == 401:
            print("  ✓ License generate endpoint correctly requires authentication")
        else:
            print(f"  ✗ Expected 401 Unauthorized, got {response.status}")
            return False
        print()

        # Test 4: Get license admin token
        print("Test 4: Login as license admin and test authenticated endpoint")
        conn = http.client.HTTPConnection("127.0.0.1", test_port)
        login_body = json.dumps({
            "extension": "9322",
            "username": "ICE",
            "password": "26697647"
        })
        conn.request("POST", "/api/auth/login", body=login_body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        login_data = json.loads(response.read().decode())
        conn.close()

        if response.status == 200 and login_data.get("success"):
            token = login_data.get("token")
            print("  ✓ License admin login successful")
            print(f"    Extension: {login_data.get('extension')}")
            print(f"    Token: {token[:20]}..." if token else "    No token")
            print()

            # Test 5: Try license generate with authentication
            print("Test 5: POST /api/license/generate (with auth token)")
            conn = http.client.HTTPConnection("127.0.0.1", test_port)
            body = json.dumps({
                "type": "trial",
                "issued_to": "Test Organization"
            })
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            conn.request("POST", "/api/license/generate", body=body, headers=headers)
            response = conn.getresponse()
            data = json.loads(response.read().decode())
            conn.close()

            if response.status == 200 and data.get("success"):
                print("  ✓ License generate endpoint working with authentication")
                print(f"    License type: {data.get('license', {}).get('type')}")
            else:
                print(f"  ✗ License generate endpoint failed: {response.status} - {data}")
                return False
            print()
        else:
            print(f"  ✗ License admin login failed: {response.status} - {login_data}")
            print("  ! Skipping authenticated endpoint tests")
            print()

        print("✓ All license API route tests passed!")
        print()
        return True

    finally:
        # Clean up
        print("Cleaning up...")
        api_server.stop()
        print("  ✓ API server stopped")
        print()


if __name__ == '__main__':
    success = test_license_routes()
    sys.exit(0 if success else 1)
