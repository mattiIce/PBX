#!/usr/bin/env python3
"""
Example: Phone MAC/IP Lookup and Correlation

Demonstrates how to use the phone lookup API to correlate MAC addresses
with IP addresses, which is useful when phones register without providing
their MAC address in SIP headers.
"""
import requests
import json
import sys


def print_json(data, title=None):
    """Pretty print JSON data"""
    if title:
        print(f"\n{title}")
        print("=" * len(title))
    print(json.dumps(data, indent=2))
    print()


def list_all_phones_with_mac(pbx_url="https://localhost:8080"):
    """
    List all registered phones with MAC addresses from provisioning
    """
    print("\n" + "=" * 70)
    print("LISTING ALL PHONES WITH MAC/IP CORRELATION")
    print("=" * 70)
    
    response = requests.get(f"{pbx_url}/api/registered-phones/with-mac")
    
    if response.status_code == 200:
        phones = response.json()
        
        if not phones:
            print("\nNo phones currently registered")
            return
        
        print(f"\nFound {len(phones)} registered phone(s):\n")
        
        for phone in phones:
            print(f"Extension: {phone['extension_number']}")
            print(f"  IP Address:   {phone['ip_address']}")
            print(f"  MAC Address:  {phone.get('mac_address', 'Not available')}")
            if phone.get('mac_source'):
                print(f"  MAC Source:   {phone['mac_source']}")
            if phone.get('vendor'):
                print(f"  Vendor/Model: {phone['vendor']} {phone['model']}")
            print(f"  User-Agent:   {phone.get('user_agent', 'Unknown')}")
            print(f"  Last Reg:     {phone.get('last_registered', 'Unknown')}")
            print()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def lookup_by_ip(ip_address, pbx_url="https://localhost:8080"):
    """
    Lookup phone by IP address to find MAC and other details
    
    This is useful when you see a phone registered with a specific IP
    and want to know its MAC address and which physical device it is.
    """
    print("\n" + "=" * 70)
    print(f"LOOKING UP PHONE BY IP ADDRESS: {ip_address}")
    print("=" * 70)
    
    response = requests.get(f"{pbx_url}/api/phone-lookup/{ip_address}")
    
    if response.status_code == 200:
        result = response.json()
        print_json(result)
        
        # Provide a human-readable summary
        if result['correlation']['matched']:
            corr = result['correlation']
            print("✓ FOUND AND MATCHED!")
            print(f"  Extension:    {corr['extension']}")
            print(f"  MAC Address:  {corr['mac_address']}")
            print(f"  IP Address:   {corr['ip_address']}")
            print(f"  Device:       {corr['vendor']} {corr['model']}")
        else:
            print("⚠ " + result['correlation']['message'])
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def lookup_by_mac(mac_address, pbx_url="https://localhost:8080"):
    """
    Lookup phone by MAC address to find current IP
    
    This is useful when you have a device provisioned with a MAC address
    and want to know what IP it's currently using.
    """
    print("\n" + "=" * 70)
    print(f"LOOKING UP PHONE BY MAC ADDRESS: {mac_address}")
    print("=" * 70)
    
    response = requests.get(f"{pbx_url}/api/phone-lookup/{mac_address}")
    
    if response.status_code == 200:
        result = response.json()
        print_json(result)
        
        # Provide a human-readable summary
        if result['correlation']['matched']:
            corr = result['correlation']
            print("✓ FOUND AND MATCHED!")
            print(f"  Extension:    {corr['extension']}")
            print(f"  MAC Address:  {corr['mac_address']}")
            print(f"  IP Address:   {corr['ip_address']}")
            print(f"  Device:       {corr['vendor']} {corr['model']}")
        else:
            print("⚠ " + result['correlation']['message'])
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def find_phones_without_mac_in_sip(pbx_url="https://localhost:8080"):
    """
    Find phones that didn't provide MAC in SIP registration
    but have MAC in provisioning system
    """
    print("\n" + "=" * 70)
    print("FINDING PHONES WITHOUT MAC IN SIP (but with MAC in provisioning)")
    print("=" * 70)
    
    # Get all registered phones
    response = requests.get(f"{pbx_url}/api/registered-phones")
    if response.status_code != 200:
        print(f"Error getting registered phones: {response.status_code}")
        return
    
    phones = response.json()
    phones_without_mac = [p for p in phones if not p.get('mac_address')]
    
    if not phones_without_mac:
        print("\n✓ All registered phones provided MAC addresses in SIP")
        return
    
    print(f"\nFound {len(phones_without_mac)} phone(s) without MAC in SIP:\n")
    
    for phone in phones_without_mac:
        extension = phone['extension_number']
        ip = phone['ip_address']
        
        print(f"Extension {extension} at IP {ip}")
        
        # Try to get MAC from provisioning via lookup
        lookup_response = requests.get(f"{pbx_url}/api/phone-lookup/{ip}")
        if lookup_response.status_code == 200:
            result = lookup_response.json()
            if result['correlation']['matched'] and result.get('provisioned_device'):
                mac = result['provisioned_device']['mac_address']
                vendor = result['provisioned_device']['vendor']
                model = result['provisioned_device']['model']
                print(f"  → MAC from provisioning: {mac}")
                print(f"  → Device: {vendor} {model}")
            else:
                print(f"  → No provisioning data found")
        print()


def demonstrate_use_case_scenarios(pbx_url="https://localhost:8080"):
    """
    Demonstrate practical use case scenarios
    """
    print("\n" + "=" * 70)
    print("PRACTICAL USE CASE SCENARIOS")
    print("=" * 70)
    
    print("\nScenario 1: Network Admin sees unknown IP")
    print("-" * 50)
    print("Network admin sees traffic from 192.168.1.100")
    print("Question: Which phone is this? What's the MAC?")
    print("\nSolution: Use /api/phone-lookup/192.168.1.100")
    print("Result: Gets extension, MAC, vendor, and model")
    
    print("\n\nScenario 2: Provisioning a phone")
    print("-" * 50)
    print("You provision phone with MAC 00:15:65:12:34:56 for ext 1001")
    print("Phone boots and registers, but you don't see MAC in logs")
    print("Question: Did my phone get the right IP via DHCP?")
    print("\nSolution: Use /api/phone-lookup/00:15:65:12:34:56")
    print("Result: Gets current IP address from SIP registration")
    
    print("\n\nScenario 3: Troubleshooting phone issues")
    print("-" * 50)
    print("User reports phone issues on extension 1002")
    print("Question: What device are they using? What IP?")
    print("\nSolution: Use /api/registered-phones/extension/1002")
    print("Result: Gets all registration details + provisioning info")
    
    print("\n\nScenario 4: Asset inventory")
    print("-" * 50)
    print("Need to create asset inventory of all phones")
    print("Question: What phones are deployed and where?")
    print("\nSolution: Use /api/registered-phones/with-mac")
    print("Result: Complete list with MAC, IP, vendor, model")
    print()


def main():
    """Main function"""
    pbx_url = "https://localhost:8080"
    
    if len(sys.argv) > 1:
        pbx_url = sys.argv[1]
    
    print("\n" + "=" * 70)
    print("Phone MAC/IP Lookup and Correlation Example")
    print("=" * 70)
    print(f"PBX URL: {pbx_url}")
    
    # Show practical use case scenarios
    demonstrate_use_case_scenarios(pbx_url)
    
    # List all phones with correlation
    list_all_phones_with_mac(pbx_url)
    
    # Find phones that need MAC correlation
    find_phones_without_mac_in_sip(pbx_url)
    
    # Example lookups (if you have specific phones to test)
    # Uncomment and modify these as needed:
    
    # lookup_by_ip("192.168.1.100", pbx_url)
    # lookup_by_mac("00:15:65:12:34:56", pbx_url)
    
    print("\n" + "=" * 70)
    print("For more examples, see API_DOCUMENTATION.md")
    print("=" * 70)
    print()


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.RequestException as e:
        # Catches ConnectionError, Timeout, HTTPError, etc.
        print("\n✗ Error: Could not connect to PBX server")
        print(f"Details: {e}")
        print("Make sure the PBX is running and accessible")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
