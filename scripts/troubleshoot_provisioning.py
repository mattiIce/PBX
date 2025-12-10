#!/usr/bin/env python3
"""
Provisioning Troubleshooting Tool

This script helps diagnose and troubleshoot phone auto-provisioning issues.
"""
import sys
import os
import requests
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.config import Config
from pbx.features.phone_provisioning import normalize_mac_address


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text):
    """Print a formatted section header"""
    print(f"\n--- {text} ---")


def check_config():
    """Check provisioning configuration"""
    print_section("Configuration Check")
    
    try:
        config = Config("config.yml")
        
        # Check if provisioning is enabled
        enabled = config.get('provisioning.enabled', False)
        print(f"✓ Provisioning enabled: {enabled}")
        
        if not enabled:
            print("\n⚠ WARNING: Provisioning is DISABLED in config.yml")
            print("  To enable, set 'provisioning.enabled: true' in config.yml")
            return False
        
        # Check key configuration values
        url_format = config.get('provisioning.url_format', 'Not set')
        external_ip = config.get('server.external_ip', 'Not set')
        api_port = config.get('api.port', 'Not set')
        sip_host = config.get('server.sip_host', 'Not set')
        sip_port = config.get('server.sip_port', 'Not set')
        
        print(f"✓ URL Format: {url_format}")
        print(f"✓ External IP: {external_ip}")
        print(f"✓ API Port: {api_port}")
        print(f"✓ SIP Host: {sip_host}")
        print(f"✓ SIP Port: {sip_port}")
        
        # Check for issues
        issues = []
        if external_ip == 'Not set' or external_ip == '127.0.0.1':
            issues.append("server.external_ip should be set to the PBX server's actual IP address")
        if url_format == 'Not set':
            issues.append("provisioning.url_format is not configured")
        
        if issues:
            print("\n⚠ Configuration Issues Found:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False


def check_api_connectivity(host='localhost', port=8080):
    """Check if API server is accessible"""
    print_section("API Connectivity Check")
    
    try:
        url = f"https://{host}:{port}/api/status"
        print(f"Testing connection to: {url}")
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✓ API server is accessible")
            print(f"  Status: {json.dumps(status, indent=2)}")
            return True
        else:
            print(f"✗ API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to API server at {host}:{port}")
        print("  Is the PBX running? Start it with: python main.py")
        return False
    except Exception as e:
        print(f"✗ Error connecting to API: {e}")
        return False


def get_diagnostics(host='localhost', port=8080):
    """Get provisioning diagnostics from API"""
    print_section("Provisioning Diagnostics")
    
    try:
        url = f"https://{host}:{port}/api/provisioning/diagnostics"
        print(f"Fetching diagnostics from: {url}")
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            diagnostics = response.json()
            
            print(f"\n✓ Configuration:")
            for key, value in diagnostics['configuration'].items():
                print(f"  {key}: {value}")
            
            print(f"\n✓ Statistics:")
            for key, value in diagnostics['statistics'].items():
                print(f"  {key}: {value}")
            
            print(f"\n✓ Registered Devices: {len(diagnostics['devices'])}")
            for device in diagnostics['devices']:
                print(f"  - MAC: {device['mac_address']}, Extension: {device['extension_number']}, "
                      f"Vendor: {device['vendor']}, Model: {device['model']}")
            
            if diagnostics['warnings']:
                print(f"\n⚠ Warnings:")
                for warning in diagnostics['warnings']:
                    print(f"  - {warning}")
            
            return diagnostics
        else:
            print(f"✗ API returned status code: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ Error fetching diagnostics: {e}")
        return None


def get_recent_requests(host='localhost', port=8080, limit=10):
    """Get recent provisioning requests"""
    print_section(f"Recent Provisioning Requests (last {limit})")
    
    try:
        url = f"https://{host}:{port}/api/provisioning/requests?limit={limit}"
        print(f"Fetching request history from: {url}")
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            requests_list = data['requests']
            
            if not requests_list:
                print("  No provisioning requests recorded yet")
                print("  Phones have not attempted to fetch their configuration")
                return []
            
            print(f"\nTotal requests in history: {data['total']}")
            print(f"Showing: {len(requests_list)}\n")
            
            for i, req in enumerate(reversed(requests_list), 1):
                status = "✓ SUCCESS" if req.get('success') else "✗ FAILED"
                print(f"{i}. {req['timestamp']} - {status}")
                print(f"   MAC: {req['mac_address']} (normalized: {req['normalized_mac']})")
                print(f"   IP: {req.get('ip_address', 'Unknown')}")
                print(f"   User-Agent: {req.get('user_agent', 'Unknown')}")
                
                if req.get('success'):
                    print(f"   Extension: {req.get('extension')}, "
                          f"Vendor: {req.get('vendor')}, Model: {req.get('model')}")
                    print(f"   Config size: {req.get('config_size')} bytes")
                else:
                    print(f"   Error: {req.get('error', 'Unknown error')}")
                print()
            
            return requests_list
        else:
            print(f"✗ API returned status code: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ Error fetching request history: {e}")
        return []


def test_mac_lookup(mac_address, host='localhost', port=8080):
    """Test if a specific MAC address is registered"""
    print_section(f"Testing MAC Address: {mac_address}")
    
    normalized = normalize_mac_address(mac_address)
    print(f"Original: {mac_address}")
    print(f"Normalized: {normalized}")
    
    try:
        url = f"https://{host}:{port}/api/provisioning/devices"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            devices = response.json()
            
            found = False
            for device in devices:
                if device['mac_address'] == normalized:
                    found = True
                    print(f"\n✓ Device IS registered:")
                    print(f"  Extension: {device['extension_number']}")
                    print(f"  Vendor: {device['vendor']}")
                    print(f"  Model: {device['model']}")
                    print(f"  Config URL: {device['config_url']}")
                    if device.get('last_provisioned'):
                        print(f"  Last provisioned: {device['last_provisioned']}")
                    break
            
            if not found:
                print(f"\n✗ Device NOT registered")
                print(f"  Register it using:")
                print(f"    curl -X POST https://{host}:{port}/api/provisioning/devices \\")
                print(f"      -H 'Content-Type: application/json' \\")
                print(f"      -d '{{\"mac_address\":\"{mac_address}\",\"extension_number\":\"XXXX\",\"vendor\":\"VENDOR\",\"model\":\"MODEL\"}}'")
            
            return found
        else:
            print(f"✗ API returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error checking device: {e}")
        return False


def test_config_download(mac_address, host='localhost', port=8080):
    """Test downloading config for a MAC address"""
    print_section(f"Testing Config Download for: {mac_address}")
    
    normalized = normalize_mac_address(mac_address)
    
    try:
        url = f"https://{host}:{port}/provision/{normalized}.cfg"
        print(f"Testing URL: {url}")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print(f"✓ Config downloaded successfully")
            print(f"  Content-Type: {response.headers.get('Content-Type')}")
            print(f"  Size: {len(response.content)} bytes")
            print(f"\n  First 500 characters of config:")
            print("  " + "-" * 60)
            print("  " + response.text[:500].replace("\n", "\n  "))
            if len(response.text) > 500:
                print("  ... (truncated)")
            print("  " + "-" * 60)
            return True
        else:
            print(f"✗ Download failed with status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error downloading config: {e}")
        return False


def print_network_recommendations():
    """Print network connectivity recommendations"""
    print("\n1. Check Network Connectivity:")
    print("   - Ensure phones can reach the PBX server IP address")
    print("   - Test with: ping <pbx-server-ip> from phone's network")
    print("   - Verify firewall allows access to port 8080")


def print_phone_config_recommendations():
    """Print phone configuration recommendations"""
    print("\n2. Verify Phone Configuration:")
    print("   - Check phone's provisioning URL setting")
    print("   - URL format: https://<pbx-ip>:8080/provision/$mac.cfg")
    print("   - Some phones use $MA instead of $mac")
    print("   - Ensure phone is using DHCP Option 66 OR manual URL")


def print_device_registration_recommendations():
    """Print device registration recommendations"""
    print("\n3. Check Device Registration:")
    print("   - Use: curl https://localhost:8080/api/provisioning/devices")
    print("   - Register devices with POST /api/provisioning/devices")
    print("   - Ensure MAC address format matches (phone may use different format)")
    print("   - Note: System automatically triggers phone reboot after registration")


def print_log_review_recommendations():
    """Print log review recommendations"""
    print("\n4. Review Logs:")
    print("   - Check logs/pbx.log for detailed provisioning logs")
    print("   - Look for 'Provisioning request received' messages")
    print("   - Check for errors in config generation")


def print_manual_test_recommendations():
    """Print manual testing recommendations"""
    print("\n5. Test Manually:")
    print("   - Get MAC address from phone (usually in phone menu: Status → Network)")
    print("   - Test URL: curl https://<pbx-ip>:8080/provision/<mac>.cfg")
    print("   - If successful, issue is with phone configuration")
    print("   - If failed, issue is with PBX device registration")


def print_common_issues():
    """Print common issues"""
    print("\n6. Common Issues:")
    print("   - Wrong MAC address format (use : or - or no separator)")
    print("   - Phone not on same network as PBX")
    print("   - Firewall blocking port 8080")
    print("   - server.external_ip set to 127.0.0.1 (should be actual IP)")
    print("   - Device not registered in provisioning system")
    print("   - Wrong vendor/model in device registration")


def print_reprovisioning_recommendations():
    """Print re-provisioning recommendations"""
    print("\n7. Force Phone to Re-provision:")
    print("   - System automatically reboots phones after registration and AD sync")
    print("   - Manual reboot: power cycle or use phone menu")
    print("   - API: POST /api/phones/<extension>/reboot")
    print("   - Some phones need factory reset for new provisioning URL")


def print_recommendations():
    """Print troubleshooting recommendations"""
    print_section("Troubleshooting Recommendations")
    
    print_network_recommendations()
    print_phone_config_recommendations()
    print_device_registration_recommendations()
    print_log_review_recommendations()
    print_manual_test_recommendations()
    print_common_issues()
    print_reprovisioning_recommendations()


def main():
    """Main troubleshooting flow"""
    print_header("Phone Auto-Provisioning Troubleshooting Tool")
    
    # Parse command line arguments
    host = 'localhost'
    port = 8080
    mac_address = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("""
Usage: python troubleshoot_provisioning.py [OPTIONS]

Options:
  --host HOST          API host (default: localhost)
  --port PORT          API port (default: 8080)
  --mac MAC_ADDRESS    Test specific MAC address

Examples:
  python troubleshoot_provisioning.py
  python troubleshoot_provisioning.py --host 192.168.1.100 --port 8080
  python troubleshoot_provisioning.py --mac 00:15:65:12:34:56
""")
            return
        
        # Parse arguments
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == '--host' and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--port' and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == '--mac' and i + 1 < len(sys.argv):
                mac_address = sys.argv[i + 1]
                i += 2
            else:
                i += 1
    
    # Run diagnostics
    config_ok = check_config()
    api_ok = check_api_connectivity(host, port)
    
    if api_ok:
        diagnostics = get_diagnostics(host, port)
        requests_list = get_recent_requests(host, port, limit=10)
        
        if mac_address:
            test_mac_lookup(mac_address, host, port)
            test_config_download(mac_address, host, port)
    
    print_recommendations()
    
    print_header("Troubleshooting Complete")
    
    if config_ok and api_ok:
        print("\n✓ System appears to be configured correctly")
        print("  If phones still not provisioning, check network connectivity and phone settings")
    else:
        print("\n✗ Issues found - review output above and follow recommendations")


if __name__ == "__main__":
    main()
