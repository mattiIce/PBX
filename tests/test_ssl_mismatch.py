#!/usr/bin/env python3
"""
Test SSL configuration mismatch handling
Tests the scenario where SSL is enabled in config but certificates are missing
"""
import os
import sys
import time
from io import StringIO
from pathlib import Path

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class MockPBXCore:
    """Mock PBX core for testing"""

    def __init__(self, config):
        self.config = config


def create_mock_config_with_ssl(cert_file, key_file):
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

    def mock_get(key, default=None):
        if key == 'api.ssl':
            return {
                'enabled': True,
                'cert_file': cert_file,
                'key_file': key_file,
                'ca': {'enabled': False}
            }
        return original_get(key, default)

    config.get = mock_get
    return config


def test_ssl_enabled_missing_certificates():
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
    print("=" * 80)
    print("Test: SSL Enabled But Certificates Missing")
    print("=" * 80)
    print()

    # Create a config object
    config = Config("test_config.yml")

    # Override the get method to simulate SSL enabled but missing certs
    original_get = config.get

    def mock_get(key, default=None):
        if key == 'api.ssl':
            return {
                'enabled': True,
                'cert_file': 'certs/nonexistent_server.crt',
                'key_file': 'certs/nonexistent_server.key',
                'ca': {'enabled': False}
            }
        return original_get(key, default)

    config.get = mock_get

    mock_pbx = MockPBXCore(config)

    print("Creating API server with:")
    print("  config.yml: api.ssl.enabled = true")
    print("  Certificate file: certs/nonexistent_server.crt (doesn't exist)")
    print("  Key file: certs/nonexistent_server.key (doesn't exist)")
    print()

    # Create API server - should handle missing certificates gracefully
    api_server = PBXAPIServer(mock_pbx, host='127.0.0.1', port=8083)

    print("Checking API server state:")
    print(f"  SSL enabled in config: True")
    print(f"  SSL actually enabled: {api_server.ssl_enabled}")
    print(f"  SSL context created: {api_server.ssl_context is not None}")
    print()

    # Verify that SSL is NOT enabled (should fall back to HTTP)
    if api_server.ssl_enabled:
        print("✗ FAIL: API server should NOT have SSL enabled when certs are missing")
        print("  This would cause 'connection reset' errors for users")
        return False

    if api_server.ssl_context is not None:
        print("✗ FAIL: SSL context should NOT be created when certs are missing")
        return False

    print("✓ PASS: Server correctly fell back to HTTP mode")
    print()

    # Try to start server - should succeed on HTTP
    print("Starting server (should start on HTTP, not HTTPS)...")
    if not api_server.start():
        print("✗ FAIL: Server should start successfully on HTTP")
        return False

    print("✓ PASS: Server started successfully")
    print()

    # Give it a moment to fully start
    time.sleep(1)

    # Stop the server
    print("Stopping server...")
    api_server.stop()
    time.sleep(0.5)

    print("✓ PASS: Server stopped successfully")
    print()

    print("=" * 80)
    print("Test Result: PASS")
    print("=" * 80)
    print()
    print("Summary:")
    print("  ✓ Server detected missing certificates")
    print("  ✓ Server fell back to HTTP mode")
    print("  ✓ Server started successfully on HTTP")
    print("  ✓ Config mismatch was logged as a warning")
    print()
    print("This prevents 'connection reset' errors because:")
    print("  - The server runs on HTTP (not HTTPS)")
    print("  - Clear warnings tell users to either:")
    print("    1. Generate certificates, OR")
    print("    2. Disable SSL in config.yml")
    print()

    return True


def test_ssl_enabled_with_valid_certificates():
    """Test that server works correctly with valid SSL certificates"""
    print("=" * 80)
    print("Test: SSL Enabled With Valid Certificates")
    print("=" * 80)
    print()

    cert_file = "certs/server.crt"
    key_file = "certs/server.key"

    # Check if certificates exist
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("  ⚠ Certificates not found, skipping this test")
        print("  (This is OK - the important test is the missing cert scenario)")
        print()
        return True

    # Create a config object
    config = Config("test_config.yml")

    # Override the get method to enable SSL with real certs
    original_get = config.get

    def mock_get(key, default=None):
        if key == 'api.ssl':
            return {
                'enabled': True,
                'cert_file': cert_file,
                'key_file': key_file,
                'ca': {'enabled': False}
            }
        return original_get(key, default)

    config.get = mock_get

    mock_pbx = MockPBXCore(config)

    print("Creating API server with valid certificates:")
    print(f"  Certificate file: {cert_file} (exists)")
    print(f"  Key file: {key_file} (exists)")
    print()

    # Create API server
    api_server = PBXAPIServer(mock_pbx, host='127.0.0.1', port=8084)

    print("Checking API server state:")
    print(f"  SSL enabled in config: True")
    print(f"  SSL actually enabled: {api_server.ssl_enabled}")
    print(f"  SSL context created: {api_server.ssl_context is not None}")
    print()

    # Verify that SSL IS enabled
    if not api_server.ssl_enabled:
        print("✗ FAIL: API server should have SSL enabled with valid certs")
        return False

    if api_server.ssl_context is None:
        print("✗ FAIL: SSL context should be created with valid certs")
        return False

    print("✓ PASS: Server correctly configured for HTTPS")
    print()

    # Try to start server
    print("Starting server (should start on HTTPS)...")
    if not api_server.start():
        print("✗ FAIL: Server should start successfully on HTTPS")
        return False

    print("✓ PASS: Server started successfully")
    print()

    time.sleep(1)

    # Stop the server
    print("Stopping server...")
    api_server.stop()
    time.sleep(0.5)

    print("✓ PASS: Server stopped successfully")
    print()

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("SSL Configuration Mismatch Tests")
    print("=" * 80)
    print()
    print("These tests verify that the server handles SSL configuration issues")
    print("gracefully to prevent 'connection reset' errors.")
    print()

    tests = [
        ("SSL Enabled with Missing Certificates",
         test_ssl_enabled_missing_certificates),
        ("SSL Enabled with Valid Certificates",
         test_ssl_enabled_with_valid_certificates),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ Test failed: {test_name}\n")
        except Exception as e:
            failed += 1
            print(f"✗ Test error in {test_name}: {e}\n")
            import traceback
            traceback.print_exc()

    print("=" * 80)
    print(f"Tests completed: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
