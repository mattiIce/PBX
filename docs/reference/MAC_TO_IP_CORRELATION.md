# MAC Address to IP Address Correlation Feature

## Problem Statement

When IP phones register via SIP protocol, they provide their IP address but **often do not provide their MAC address** in the SIP headers. This creates a challenge:

- **Provisioning System** knows: MAC Address → Extension Number
- **SIP Registration** knows: IP Address → Extension Number
- **The Gap**: How to find MAC when you only have IP, or vice versa?

This makes it difficult to:
- Identify which physical phone is at which IP address
- Track phone inventory with both MAC and IP
- Troubleshoot phone issues
- Perform network administration tasks

## Solution Overview

The solution implements API endpoints that **correlate** provisioning data with SIP registration data using the **Extension Number** as the common key:

```
Provisioning: MAC → Extension
                      ↓
Registration: IP ← Extension

Result: MAC ↔ IP (bidirectional lookup)
```

## Implementation

### Database Structure

The system uses two existing data sources:

1. **Phone Provisioning** (in-memory)
   ```python
   devices = {
       "001565123456": {  # Normalized MAC
           "mac_address": "001565123456",
           "extension_number": "1001",
           "vendor": "yealink",
           "model": "t46s"
       }
   }
   ```

2. **Registered Phones** (database table)
   ```sql
   CREATE TABLE registered_phones (
       id INTEGER PRIMARY KEY,
       mac_address VARCHAR(20),         -- May be NULL
       extension_number VARCHAR(20) NOT NULL,
       ip_address VARCHAR(50) NOT NULL,
       user_agent VARCHAR(255),
       first_registered TIMESTAMP,
       last_registered TIMESTAMP,
       contact_uri VARCHAR(255),
       UNIQUE(mac_address, extension_number),
       UNIQUE(ip_address, extension_number)
   );
   ```

### New API Endpoints

#### 1. GET /api/registered-phones/with-mac

Enhanced endpoint that shows all registered phones with MAC addresses from provisioning.

**What it does:**
- Queries all phones from SIP registration (has IP)
- Cross-references with provisioning system (has MAC)
- Matches by extension number
- Returns combined data

**Example Response:**
```json
[
  {
    "extension_number": "1001",
    "ip_address": "192.168.1.100",
    "mac_address": "001565123456",
    "mac_source": "provisioning",
    "vendor": "yealink",
    "model": "t46s",
    "user_agent": "Yealink SIP-T46S 66.85.0.5"
  }
]
```

#### 2. GET /api/phone-lookup/{identifier}

Unified lookup that accepts either MAC or IP address.

**Auto-detection:**
- Uses regex to detect if input is MAC or IP
- MAC pattern: `^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$`
- IP pattern: `^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$`

**Example - Lookup by IP:**
```bash
curl http://192.168.1.14:8080/api/phone-lookup/192.168.1.100
```

**Response:**
```json
{
  "identifier": "192.168.1.100",
  "type": "ip",
  "registered_phone": {
    "extension_number": "1001",
    "ip_address": "192.168.1.100",
    "mac_address": null
  },
  "provisioned_device": {
    "mac_address": "001565123456",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s"
  },
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

### Correlation Logic

The correlation algorithm:

```python
def correlate_by_ip(ip_address):
    # Step 1: Find phone in SIP registration
    phone = registered_phones_db.get_by_ip(ip_address)
    if not phone:
        return None
    
    # Step 2: Get extension from registration
    extension = phone['extension_number']
    
    # Step 3: Find provisioned device with same extension
    for device in provisioning.get_all_devices():
        if device.extension_number == extension:
            # Step 4: Return combined data
            return {
                'ip': phone['ip_address'],
                'mac': device.mac_address,
                'extension': extension,
                'vendor': device.vendor,
                'model': device.model
            }
```

## Use Cases

### 1. Network Administrator Sees Unknown IP

**Scenario:**
- Network admin sees traffic from IP 192.168.1.105
- Question: Which phone is this? What's the MAC?

**Solution:**
```bash
curl http://192.168.1.14:8080/api/phone-lookup/192.168.1.105
```

**Result:**
- Extension: 1003
- MAC: 00:15:65:AB:CD:EF
- Device: Polycom VVX 450

### 2. Finding Current IP for Provisioned Phone

**Scenario:**
- Provisioned phone with MAC 00:15:65:12:34:56
- Question: What IP did it get from DHCP?

**Solution:**
```bash
curl http://192.168.1.14:8080/api/phone-lookup/00:15:65:12:34:56
```

**Result:**
- Current IP: 192.168.1.100
- Extension: 1001
- Last registered: 2025-12-05T12:00:00

### 3. Asset Inventory Management

**Scenario:**
- Need complete inventory of all phones
- Require both MAC and IP for each phone

**Solution:**
```bash
curl http://192.168.1.14:8080/api/registered-phones/with-mac | jq .
```

**Result:**
- Complete list with MAC, IP, vendor, model
- Export to CSV for inventory system

### 4. Troubleshooting Phone Issues

**Scenario:**
- User on extension 1002 reports problems
- Need to identify exact device and current IP

**Solution:**
```bash
curl http://192.168.1.14:8080/api/registered-phones/extension/1002
```

**Result:**
- Device details with IP and MAC
- User agent (phone model/firmware)
- Last registration time

## Workflow Example

### Complete Phone Provisioning and Tracking Flow

```bash
# 1. Register device for provisioning (stores MAC → Extension)
curl -X POST http://192.168.1.14:8080/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:15:65:12:34:56",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s"
  }'

# 2. Phone boots and registers via SIP (stores IP → Extension)
#    This happens automatically when phone starts
#    System captures: IP=192.168.1.100, Extension=1001

# 3. Look up phone by IP to get MAC
curl http://192.168.1.14:8080/api/phone-lookup/192.168.1.100
# Returns: MAC=001565123456, Extension=1001, Vendor=yealink

# 4. Look up phone by MAC to get current IP
curl http://192.168.1.14:8080/api/phone-lookup/00:15:65:12:34:56
# Returns: IP=192.168.1.100, Extension=1001

# 5. Get all phones with complete information
curl http://192.168.1.14:8080/api/registered-phones/with-mac
# Returns: Array of all phones with MAC, IP, vendor, model
```

## Technical Details

### MAC Address Normalization

All MAC addresses are normalized to a consistent format:
- Lowercase
- No separators (removes `:`, `-`, `.`)
- Example: `00:15:65:12:34:56` → `001565123456`

### Validation

**MAC Address Validation:**
- Accepts formats: `XX:XX:XX:XX:XX:XX`, `XX-XX-XX-XX-XX-XX`, `XXXXXXXXXXXX`
- Regex: `^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$`
- Rejects invalid inputs like: `abcd:efgh:ijkl`, `GG:15:65:12:34:56`

**IP Address Validation:**
- Accepts valid IPv4 addresses
- Regex: `^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$`
- Rejects invalid inputs like: `999.999.999.999`, `1.2.3.abc`

### Error Handling

When device is not found during provisioning:
```
✗ Provisioning failed for MAC 00:15:65:12:34:56 from IP 192.168.10.159
  Reason: Device not registered or template not found
  To register this device:
    curl -X POST http://YOUR_PBX_IP:8080/api/provisioning/devices \
      -H 'Content-Type: application/json' \
      -d '{"mac_address":"00:15:65:12:34:56","extension_number":"XXXX","vendor":"VENDOR","model":"MODEL"}'
```

## Testing

Comprehensive test suite with 6 tests:
1. MAC address normalization
2. Provisioned device structure
3. Registered phone lookup methods
4. MAC-to-IP correlation scenario
5. IP-to-MAC correlation scenario
6. Phone without MAC in SIP registration

All tests pass with 100% success rate.

## Security

- **No security vulnerabilities** found by CodeQL scanner
- Input validation prevents injection attacks
- Proper regex patterns prevent malformed inputs
- No sensitive data exposed in error messages

## Files Modified

1. `pbx/api/rest_api.py` - New API endpoints
2. `pbx/features/phone_provisioning.py` - Improved error messages
3. `tests/test_phone_mac_ip_correlation.py` - Comprehensive tests
4. `examples/phone_lookup_example.py` - Usage examples
5. `COMPLETE_GUIDE.md` - API documentation (Section 9.2)
6. `COMPLETE_GUIDE.md` - Phone provisioning (Section 4.3)

## Benefits

✓ **Identify phones easily** - Know which MAC corresponds to which IP
✓ **Better troubleshooting** - Find phone details quickly
✓ **Asset tracking** - Complete inventory with MAC and IP
✓ **Network management** - Identify devices on the network
✓ **No manual correlation** - Automatic via extension number
✓ **Works with phones that don't provide MAC in SIP** - Most common case
✓ **Bidirectional lookup** - Find IP from MAC or MAC from IP

## Limitations

- Correlation requires phone to be registered via SIP
- Requires extension number to be the same in both systems
- Only tracks currently registered phones (not historical data)
- Does not work for phones that are provisioned but never registered

## Future Enhancements

Possible improvements:
- Historical tracking of MAC/IP changes over time
- Alert when unknown devices register
- Integration with network inventory systems
- Export functionality for asset management
- Web UI for visual phone mapping
