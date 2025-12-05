# Phone MAC/IP Lookup - Quick Start Guide

## The Problem

**Phones register with IP but not MAC** → Hard to identify which phone is which

## The Solution

New API endpoints that correlate provisioning data (MAC) with registration data (IP) using the extension number.

## Quick Usage

### 1. Find MAC from IP Address

When you see an IP and want to know the MAC:

```bash
curl http://192.168.1.14:8080/api/phone-lookup/192.168.1.100
```

Returns:
```json
{
  "correlation": {
    "matched": true,
    "extension": "1001",
    "mac_address": "001565123456",
    "ip_address": "192.168.1.100",
    "vendor": "yealink",
    "model": "t46s"
  }
}
```

### 2. Find IP from MAC Address

When you have a MAC and want the current IP:

```bash
curl http://192.168.1.14:8080/api/phone-lookup/00:15:65:12:34:56
```

Returns:
```json
{
  "correlation": {
    "matched": true,
    "extension": "1001",
    "mac_address": "001565123456",
    "ip_address": "192.168.1.100",
    "vendor": "yealink",
    "model": "t46s"
  }
}
```

### 3. List All Phones with Both MAC and IP

Get complete inventory:

```bash
curl http://192.168.1.14:8080/api/registered-phones/with-mac
```

Returns array:
```json
[
  {
    "extension_number": "1001",
    "ip_address": "192.168.1.100",
    "mac_address": "001565123456",
    "vendor": "yealink",
    "model": "t46s",
    "mac_source": "provisioning"
  }
]
```

## Common Scenarios

### Scenario: Unknown IP in Network Logs

```bash
# Problem: See IP 192.168.1.105, don't know which phone
curl http://192.168.1.14:8080/api/phone-lookup/192.168.1.105

# Result: Extension 1003, MAC 00:15:65:AB:CD:EF, Polycom VVX 450
```

### Scenario: Provisioned Phone, Need Current IP

```bash
# Problem: Provisioned MAC 00:15:65:12:34:56, what IP did DHCP assign?
curl http://192.168.1.14:8080/api/phone-lookup/00:15:65:12:34:56

# Result: Current IP is 192.168.1.100
```

### Scenario: Asset Inventory

```bash
# Problem: Need complete inventory with MAC and IP
curl http://192.168.1.14:8080/api/registered-phones/with-mac | jq .

# Result: All phones with MAC, IP, vendor, model
```

## Python Example

```python
import requests

# Lookup by IP
response = requests.get('http://192.168.1.14:8080/api/phone-lookup/192.168.1.100')
data = response.json()

if data['correlation']['matched']:
    print(f"Extension: {data['correlation']['extension']}")
    print(f"MAC: {data['correlation']['mac_address']}")
    print(f"IP: {data['correlation']['ip_address']}")
    print(f"Device: {data['correlation']['vendor']} {data['correlation']['model']}")
```

## Complete Example Script

Run the included example script:

```bash
python examples/phone_lookup_example.py http://192.168.1.14:8080
```

## How It Works

1. **Provisioning system** stores: MAC → Extension
2. **SIP registration** stores: IP → Extension
3. **Correlation** uses Extension as the key to link MAC ↔ IP

## Requirements

- Phone must be registered in provisioning system (POST /api/provisioning/devices)
- Phone must be registered via SIP (happens automatically when phone boots)
- Both must use the same extension number

## More Information

- Full documentation: [MAC_TO_IP_CORRELATION.md](MAC_TO_IP_CORRELATION.md)
- API documentation: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- Phone provisioning guide: [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)
