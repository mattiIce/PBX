#!/usr/bin/env python3
"""
Example script demonstrating phone provisioning
"""
import requests
import json
import time

# PBX API base URL
BASE_URL = "http://localhost:8080"


def check_pbx_status():
    """Check if PBX is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✓ PBX is running")
            print(f"  - Extensions registered: {status.get('registered_extensions', 0)}")
            print(f"  - Active calls: {status.get('active_calls', 0)}")
            return True
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to PBX. Is it running?")
        return False


def get_supported_vendors():
    """Get list of supported phone vendors and models"""
    print("\n📱 Supported Phone Vendors and Models:")
    response = requests.get(f"{BASE_URL}/api/provisioning/vendors")
    
    if response.status_code == 200:
        data = response.json()
        vendors = data.get('vendors', [])
        models = data.get('models', {})
        
        for vendor in vendors:
            print(f"  • {vendor.capitalize()}")
            vendor_models = models.get(vendor, [])
            for model in vendor_models:
                print(f"    - {model}")
    else:
        print(f"  Error: {response.text}")


def register_device(mac, extension, vendor, model):
    """Register a phone device for provisioning"""
    print(f"\n📞 Registering device {mac} for extension {extension}...")
    
    data = {
        "mac_address": mac,
        "extension_number": extension,
        "vendor": vendor,
        "model": model
    }
    
    response = requests.post(
        f"{BASE_URL}/api/provisioning/devices",
        headers={"Content-Type": "application/json"},
        data=json.dumps(data)
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            device = result.get('device', {})
            print(f"✓ Device registered successfully!")
            print(f"  - Config URL: {device.get('config_url')}")
            return True
    
    print(f"✗ Registration failed: {response.text}")
    return False


def list_provisioned_devices():
    """List all provisioned devices"""
    print("\n📋 Provisioned Devices:")
    response = requests.get(f"{BASE_URL}/api/provisioning/devices")
    
    if response.status_code == 200:
        devices = response.json()
        
        if not devices:
            print("  No devices provisioned yet.")
            return
        
        for device in devices:
            print(f"  • {device['mac_address']}")
            print(f"    Extension: {device['extension_number']}")
            print(f"    Vendor: {device['vendor']}")
            print(f"    Model: {device['model']}")
            print(f"    Config URL: {device['config_url']}")
            if device.get('last_provisioned'):
                print(f"    Last Provisioned: {device['last_provisioned']}")
            print()
    else:
        print(f"  Error: {response.text}")


def get_device_config(mac):
    """Get device configuration"""
    print(f"\n📄 Configuration for device {mac}:")
    
    # Normalize MAC address for URL
    normalized_mac = mac.replace(':', '').replace('-', '').replace('.', '').lower()
    
    response = requests.get(f"{BASE_URL}/provision/{normalized_mac}.cfg")
    
    if response.status_code == 200:
        print("=" * 60)
        print(response.text)
        print("=" * 60)
    else:
        print(f"  Error: {response.text}")


def unregister_device(mac):
    """Unregister a device"""
    print(f"\n🗑️  Unregistering device {mac}...")
    
    # Normalize MAC address for URL
    normalized_mac = mac.replace(':', '').replace('-', '').replace('.', '').lower()
    
    response = requests.delete(f"{BASE_URL}/api/provisioning/devices/{normalized_mac}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"✓ Device unregistered successfully!")
            return True
    
    print(f"✗ Unregistration failed: {response.text}")
    return False


def main():
    """Main example function"""
    print("=" * 60)
    print("Phone Provisioning Example")
    print("=" * 60)
    
    # Check PBX status
    if not check_pbx_status():
        print("\nPlease start the PBX server first:")
        print("  python main.py")
        return
    
    # Get supported vendors
    get_supported_vendors()
    
    # Register some example devices
    print("\n" + "=" * 60)
    print("Example Device Registration")
    print("=" * 60)
    
    devices = [
        ("00:15:65:12:34:56", "1001", "zip", "33g"),
        ("00:15:65:12:34:57", "1002", "zip", "37g"),
        ("00:04:f2:ab:cd:ef", "1003", "zip", "37g"),
    ]
    
    for mac, ext, vendor, model in devices:
        register_device(mac, ext, vendor, model)
        time.sleep(0.5)  # Small delay between registrations
    
    # List all provisioned devices
    list_provisioned_devices()
    
    # Get configuration for first device
    get_device_config(devices[0][0])
    
    # Demonstrate unregistration
    print("\n" + "=" * 60)
    print("Example Device Unregistration")
    print("=" * 60)
    
    print("\nUnregistering first device as an example...")
    unregister_device(devices[0][0])
    
    # List devices again to show removal
    list_provisioned_devices()
    
    print("\n" + "=" * 60)
    print("Example Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Configure your IP phones to use the provisioning URL")
    print("2. Set DHCP Option 66 to: http://<pbx-ip>:8080/provision/{mac}.cfg")
    print("3. Reboot phones to auto-provision")
    print("\nFor more information, see PHONE_PROVISIONING.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
