#!/usr/bin/env python3
"""
Test SSL configuration mismatch handling
Tests the scenario where SSL is enabled in config but certificates are missing
"""

import os
import time
from pathlib import Path
from typing import Any

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config: Any) -> None:
        self.config = config


def create_mock_config_with_ssl(cert_file: str, key_file: str) -> Config:
    """
    Helper function to create a mock config with SSL settings

    Args:
        cert_file: Path to certificate file
        key_file: Path to key file

    Returns:
        Config object with mocked SSL settings
    """
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
    return config


def test_ssl_enabled_missing_certificates() -> bool:
    """
    Test that server handles SSL enabled with missing certificates gracefully

    This tests the scenario where:
    1. User enables SSL in config.yml
    2. Certificate files don't exist (not generated or deleted)
    3. Server should:
       - Log clear error messages
       - Fall back to HTTP
       - Warn about the mismatch
    """

    # Create a config object
    config = Config("test_config.yml")

    # Override the get method to simulate SSL enabled but missing certs
    original_get = config.get

    def mock_get(key: str, default: Any = None) -> Any:
        if key == "api.ssl":
            return {
                "enabled": True,
                "cert_file": "certs/nonexistent_server.crt",
                "key_file": "certs/nonexistent_server.key",
                "ca": {"enabled": False},
            }
        return original_get(key, default)

    config.get = mock_get

    mock_pbx = MockPBXCore(config)

    # Create API server - should handle missing certificates gracefully
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=8083)

    # Verify that SSL is NOT enabled (should fall back to HTTP)
    if api_server.ssl_enabled:
        return False

    if api_server.ssl_context is not None:
        return False

    # Try to start server - should succeed on HTTP
    if not api_server.start():
        return False

    # Give it a moment to fully start
    time.sleep(1)

    # Stop the server
    api_server.stop()
    time.sleep(0.5)

    return True


def test_ssl_enabled_with_valid_certificates() -> bool:
    """Test that server works correctly with valid SSL certificates"""

    cert_file = "certs/server.crt"
    key_file = "certs/server.key"

    # Check if certificates exist
    if not Path(cert_file).exists() or not Path(key_file).exists():
        return True

    # Create a config object
    config = Config("test_config.yml")

    # Override the get method to enable SSL with real certs
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
    api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=8084)

    # Verify that SSL IS enabled
    if not api_server.ssl_enabled:
        return False

    if api_server.ssl_context is None:
        return False

    # Try to start server
    if not api_server.start():
        return False

    time.sleep(1)

    # Stop the server
    api_server.stop()
    time.sleep(0.5)

    return True


def main() -> bool:
    """Run all tests"""

    tests = [
        ("SSL Enabled with Missing Certificates", test_ssl_enabled_missing_certificates),
        ("SSL Enabled with Valid Certificates", test_ssl_enabled_with_valid_certificates),
    ]

    passed = 0
    failed = 0

    for _test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            import traceback

            traceback.print_exc()

    return failed == 0
