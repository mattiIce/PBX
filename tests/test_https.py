#!/usr/bin/env python3
"""
Comprehensive HTTPS/SSL Tests for API Server
Tests SSL configuration, certificate validation, and HTTPS connections
"""

import json
import os
import ssl
import time
import urllib.request
from typing import Any


from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_status(self) -> dict[str, int]:
        return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}


def test_ssl_configuration() -> bool:
    """Test SSL configuration loading"""

    # Create test config with SSL enabled
    config = Config("test_config.yml")

    # Check if SSL config is present
    ssl_config = config.get("api.ssl", {})

    ssl_enabled = ssl_config.get("enabled", False)

    if ssl_enabled:
        cert_file = ssl_config.get("cert_file", "certs/server.crt")
        key_file = ssl_config.get("key_file", "certs/server.key")

        # Check if files exist
        if not os.path.exists(cert_file):
            pass

        if not os.path.exists(key_file):
            pass

    return True


def test_api_server_with_ssl_disabled() -> bool:
    """Test API server starts with SSL disabled"""

    # Create config with SSL disabled
    config = Config("test_config.yml")

    mock_pbx = MockPBXCore(config)

    # Create API server
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=8081)


    if api_server.ssl_enabled:
        return False

    # Try to start server
    if api_server.start():
        time.sleep(1)
        api_server.stop()
    else:
        return False

    return True


def test_certificate_files() -> bool:
    """Test certificate files are valid"""

    cert_file = "certs/server.crt"
    key_file = "certs/server.key"

    if not os.path.exists(cert_file):
        return True  # Not a failure, just skip

    if not os.path.exists(key_file):
        return True  # Not a failure, just skip

    # Try to load certificate with SSL
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
    except (OSError, ssl.SSLError) as e:
        return False

    return True


def test_api_server_with_ssl_enabled() -> bool:
    """Test API server starts with SSL enabled"""

    cert_file = "certs/server.crt"
    key_file = "certs/server.key"

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        return True  # Not a failure, just skip

    # Create a config object and override SSL settings
    config = Config("test_config.yml")

    # Override the get method to return our SSL config
    original_get = config.get

    def mock_get(key: str, default: Any = None) -> Any:
        if key == "api.ssl":
            return {
                "enabled": True,
                "cert_file": cert_file,
                "key_file": key_file,
                "ca": {"enabled": False},
            }
        return original_get(key, default)

    config.get = mock_get

    mock_pbx = MockPBXCore(config)

    # Create API server
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=8082)


    if not api_server.ssl_enabled:
        return False

    if api_server.ssl_context is None:
        return False

    # Try to start server
    if api_server.start():
        time.sleep(1)
        api_server.stop()
    else:
        return False

    return True


def test_https_connection() -> bool:
    """Test making HTTPS requests to the API server"""

    cert_file = "certs/server.crt"
    key_file = "certs/server.key"

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        return True

    # Create config with SSL enabled
    config = Config("test_config.yml")

    # Override to enable SSL
    original_get = config.get

    def mock_get(key: str, default: Any = None) -> Any:
        if key == "api.ssl":
            return {
                "enabled": True,
                "cert_file": cert_file,
                "key_file": key_file,
                "ca": {"enabled": False},
            }
        return original_get(key, default)

    config.get = mock_get

    mock_pbx = MockPBXCore(config)

    # Create and start API server
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=8083)

    if not api_server.start():
        return False


    # Give it a moment to start
    time.sleep(1)

    # Try to connect
    try:
        # Create SSL context that doesn't verify self-signed cert
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Make HTTPS request
        url = "https://127.0.0.1:8083/api/status"

        with urllib.request.urlopen(url, context=ctx, timeout=5) as response:
            data = json.loads(response.read().decode())

            if "registered_extensions" not in data:
                api_server.stop()
                return False

    except (OSError, ValueError, json.JSONDecodeError, ssl.SSLError) as e:
        import traceback

        traceback.print_exc()
        api_server.stop()
        return False

    # Stop server
    api_server.stop()
    time.sleep(1)

    return True


def main() -> bool:
    """Run all tests"""

    tests = [
        ("SSL Configuration", test_ssl_configuration),
        ("API Server (SSL Disabled)", test_api_server_with_ssl_disabled),
        ("Certificate Validation", test_certificate_files),
        ("API Server (SSL Enabled)", test_api_server_with_ssl_enabled),
        ("HTTPS Connection", test_https_connection),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            import traceback

            traceback.print_exc()


    return failed == 0
