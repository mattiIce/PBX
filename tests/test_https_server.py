#!/usr/bin/env python3
"""
Test HTTPS/SSL support for API server
"""
import sys
import os
import time
import ssl
import socket
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.utils.config import Config
from pbx.api.rest_api import PBXAPIServer


class MockPBXCore:
    """Mock PBX core for testing"""
    def __init__(self, config):
        self.config = config


def test_ssl_configuration():
    """Test SSL configuration loading"""
    print("=" * 60)
    print("Test 1: SSL Configuration Loading")
    print("=" * 60)
    
    # Create test config with SSL enabled
    config = Config("test_config.yml")
    
    # Check if SSL config is present
    ssl_config = config.get('api.ssl', {})
    print(f"✓ SSL config loaded: {ssl_config}")
    
    ssl_enabled = ssl_config.get('enabled', False)
    print(f"  SSL enabled: {ssl_enabled}")
    
    if ssl_enabled:
        cert_file = ssl_config.get('cert_file', 'certs/server.crt')
        key_file = ssl_config.get('key_file', 'certs/server.key')
        print(f"  Certificate file: {cert_file}")
        print(f"  Key file: {key_file}")
        
        # Check if files exist
        if os.path.exists(cert_file):
            print(f"  ✓ Certificate file exists")
        else:
            print(f"  ✗ Certificate file not found")
            
        if os.path.exists(key_file):
            print(f"  ✓ Key file exists")
        else:
            print(f"  ✗ Key file not found")
    
    print()
    return True


def test_api_server_with_ssl_disabled():
    """Test API server starts with SSL disabled"""
    print("=" * 60)
    print("Test 2: API Server with SSL Disabled")
    print("=" * 60)
    
    # Create config with SSL disabled
    config = Config("test_config.yml")
    
    mock_pbx = MockPBXCore(config)
    
    # Create API server
    api_server = PBXAPIServer(mock_pbx, host='127.0.0.1', port=8081)
    
    print(f"  SSL enabled: {api_server.ssl_enabled}")
    print(f"  SSL context: {api_server.ssl_context}")
    
    if not api_server.ssl_enabled:
        print("✓ API server correctly configured without SSL")
    else:
        print("✗ API server should not have SSL enabled")
        return False
    
    # Try to start server
    print("  Starting API server...")
    if api_server.start():
        print("  ✓ API server started successfully (HTTP)")
        time.sleep(1)
        api_server.stop()
        print("  ✓ API server stopped")
    else:
        print("  ✗ Failed to start API server")
        return False
    
    print()
    return True


def test_certificate_files():
    """Test certificate files are valid"""
    print("=" * 60)
    print("Test 3: Certificate File Validation")
    print("=" * 60)
    
    cert_file = "certs/server.crt"
    key_file = "certs/server.key"
    
    if not os.path.exists(cert_file):
        print(f"  ⚠ Certificate not found: {cert_file}")
        print(f"  Generate with: python scripts/generate_ssl_cert.py")
        print()
        return True  # Not a failure, just skip
    
    if not os.path.exists(key_file):
        print(f"  ⚠ Key file not found: {key_file}")
        print()
        return True  # Not a failure, just skip
    
    # Try to load certificate with SSL
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        print(f"  ✓ Certificate and key files are valid")
        print(f"  ✓ SSL context created successfully")
    except Exception as e:
        print(f"  ✗ Error loading certificate: {e}")
        return False
    
    print()
    return True


def test_api_server_with_ssl_enabled():
    """Test API server starts with SSL enabled"""
    print("=" * 60)
    print("Test 4: API Server with SSL Enabled")
    print("=" * 60)
    
    cert_file = "certs/server.crt"
    key_file = "certs/server.key"
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("  ⚠ Certificates not found, skipping SSL test")
        print("  Generate with: python scripts/generate_ssl_cert.py")
        print()
        return True  # Not a failure, just skip
    
    # Create a config object and override SSL settings
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
    
    mock_pbx = MockPBXCore(config)
    
    # Create API server
    api_server = PBXAPIServer(mock_pbx, host='127.0.0.1', port=8082)
    
    print(f"  SSL enabled: {api_server.ssl_enabled}")
    print(f"  SSL context: {api_server.ssl_context is not None}")
    
    if not api_server.ssl_enabled:
        print("  ✗ API server should have SSL enabled")
        return False
    
    if api_server.ssl_context is None:
        print("  ✗ SSL context should be created")
        return False
    
    # Try to start server
    print("  Starting API server with SSL...")
    if api_server.start():
        print("  ✓ API server started successfully (HTTPS)")
        time.sleep(1)
        api_server.stop()
        print("  ✓ API server stopped")
    else:
        print("  ✗ Failed to start API server with SSL")
        return False
    
    print()
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("HTTPS/SSL API Server Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("SSL Configuration", test_ssl_configuration),
        ("API Server (SSL Disabled)", test_api_server_with_ssl_disabled),
        ("Certificate Validation", test_certificate_files),
        ("API Server (SSL Enabled)", test_api_server_with_ssl_enabled),
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
    
    print("=" * 60)
    print(f"Tests completed: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
