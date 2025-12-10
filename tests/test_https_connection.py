#!/usr/bin/env python3
"""
Test HTTPS connection to API server
"""
import sys
import os
import time
import ssl
import urllib.request
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.utils.config import Config
from pbx.api.rest_api import PBXAPIServer


class MockPBXCore:
    """Mock PBX core for testing"""
    def __init__(self, config):
        self.config = config
    
    def get_status(self):
        return {
            'registered_extensions': 0,
            'active_calls': 0,
            'uptime': 0
        }


def test_https_connection():
    """Test making HTTPS requests to the API server"""
    print("=" * 60)
    print("Test: HTTPS Connection to API Server")
    print("=" * 60)
    
    cert_file = "certs/server.crt"
    key_file = "certs/server.key"
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("  ⚠ Certificates not found, skipping connection test")
        print("  Generate with: python scripts/generate_ssl_cert.py")
        return True
    
    # Create config with SSL enabled
    config = Config("test_config.yml")
    
    # Override to enable SSL
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
    
    # Create and start API server
    api_server = PBXAPIServer(mock_pbx, host='127.0.0.1', port=8083)
    
    print("  Starting HTTPS API server...")
    if not api_server.start():
        print("  ✗ Failed to start API server")
        return False
    
    print("  ✓ API server started on https://127.0.0.1:8083")
    
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
        print(f"  Making HTTPS request to {url}...")
        
        with urllib.request.urlopen(url, context=ctx, timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"  ✓ HTTPS request successful")
            print(f"  Response: {data}")
            
            if 'registered_extensions' in data:
                print("  ✓ API response is valid")
            else:
                print("  ✗ Invalid API response")
                api_server.stop()
                return False
    
    except Exception as e:
        print(f"  ✗ HTTPS connection failed: {e}")
        import traceback
        traceback.print_exc()
        api_server.stop()
        return False
    
    # Stop server
    api_server.stop()
    time.sleep(1)
    print("  ✓ API server stopped")
    
    print()
    return True


def main():
    """Run the test"""
    print("\n" + "=" * 60)
    print("HTTPS Connection Test")
    print("=" * 60)
    print()
    
    try:
        success = test_https_connection()
        
        print("=" * 60)
        if success:
            print("✓ HTTPS connection test PASSED")
        else:
            print("✗ HTTPS connection test FAILED")
        print("=" * 60)
        
        return success
    except Exception as e:
        print(f"✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
