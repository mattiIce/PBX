# Phone Provisioning Guide

**Last Updated**: December 29, 2025  
**Purpose**: Complete guide for phone provisioning setup, configuration, and management

## Table of Contents
- [Overview](#overview)
- [Quick Setup](#quick-setup)
- [Supported Phone Vendors](#supported-phone-vendors)
- [Configuration](#configuration)
- [Database Persistence](#database-persistence)
- [Template Customization](#template-customization)
- [Registration Cleanup](#registration-cleanup)
- [Troubleshooting](#troubleshooting)

---

## Overview

The PBX system includes a comprehensive phone provisioning system that allows automatic configuration of IP phones from multiple vendors.

Phone provisioning enables zero-touch or simplified deployment of IP phones by automatically generating and serving configuration files. When a phone boots up, it can request its configuration from the PBX server, eliminating the need for manual configuration of each device.

### Key Features

- **Database Persistence**: Provisioning configurations stored in database, survive restarts
- **Automatic Cleanup**: Incomplete registrations automatically removed at startup
- **Template System**: Customizable templates for different phone vendors and models
- **Web Admin Interface**: Easy device management through admin panel
- **REST API**: Programmatic device registration and management
- **Multi-Vendor Support**: Zultys, Yealink, Polycom, Cisco, Grandstream

---

## Quick Setup

The PBX now provides **two easy ways** to set up phone provisioning:

### 1. Interactive CLI Setup (Recommended for initial setup)

Run the interactive setup wizard that will guide you through the provisioning setup:

```bash
python scripts/setup_phone_provisioning.py
```

The wizard will:
- Ask you for provisioning settings (server IP, port, etc.)
- Help you add phone devices one by one
- Register devices via API (if PBX is running) or save to config.yml
- Show you next steps to complete the setup

### 2. Web Admin Interface (Recommended for ongoing management)

1. Access the admin panel: `http://your-pbx-ip:8080/admin/`
2. Click on the **"Phone Provisioning"** tab
3. Enable auto-provisioning and configure settings
4. Click **"Add Device"** to register phones
5. Fill in the MAC address, extension, vendor, and model
6. The phone will automatically download its configuration on boot

Both methods use the same underlying REST API and configuration system.

## Supported Phone Vendors

The system includes built-in templates for the following vendors and models:

### Zultys
- ZIP 33G - Basic SIP phone
- ZIP 37G - Advanced SIP phone with additional features

### Yealink
- T28G - Basic business IP phone with 6 lines
- T46S - Popular business IP phone with color display

### Polycom
- VVX 450 - Business media phone with touchscreen

### Cisco
- SPA504G - 4-line IP phone with 2-port switch

### Grandstream
- GXP2170 - High-end IP phone with 12 lines

## Configuration

### Enable Provisioning

Edit `config.yml` to enable phone provisioning:

```yaml
provisioning:
  enabled: true
  url_format: "http://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg"
  custom_templates_dir: ""  # Optional: custom templates directory
  devices: []  # Pre-configured devices
```

### Configure Devices in config.yml

You can pre-configure devices in `config.yml`:

```yaml
provisioning:
  enabled: true
  devices:
    - mac: "00:15:65:12:34:56"
      extension: "1001"
      vendor: "zultys"
      model: "zip33g"
    
    - mac: "00:04:f2:ab:cd:ef"
      extension: "1002"
      vendor: "zultys"
      model: "zip37g"
    
    - mac: "00:04:f2:12:ab:cd"
      extension: "1003"
      vendor: "yealink"
      model: "t46s"
    
    - mac: "00:04:f2:ab:cd:ab"
      extension: "1004"
      vendor: "polycom"
      model: "vvx450"
```

## REST API Usage

### List Provisioned Devices

```bash
curl http://localhost:8080/api/provisioning/devices
```

Response:
```json
[
  {
    "mac_address": "001565123456",
    "extension_number": "1001",
    "vendor": "zultys",
    "model": "zip33g",
    "config_url": "http://192.168.1.14:8080/provision/001565123456.cfg",
    "created_at": "2025-12-03T10:30:00",
    "last_provisioned": "2025-12-03T10:35:00"
  }
]
```

### Get Supported Vendors and Models

```bash
curl http://localhost:8080/api/provisioning/vendors
```

Response:
```json
{
  "vendors": ["cisco", "grandstream", "polycom", "yealink", "zultys"],
  "models": {
    "cisco": ["spa504g"],
    "grandstream": ["gxp2170"],
    "polycom": ["vvx450"],
    "yealink": ["t46s"],
    "zultys": ["zip33g", "zip37g"]
  }
}
```

### Register a Device

```bash
curl -X POST http://localhost:8080/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:15:65:12:34:56",
    "extension_number": "1001",
    "vendor": "zultys",
    "model": "zip33g"
  }'
```

Response:
```json
{
  "success": true,
  "device": {
    "mac_address": "001565123456",
    "extension_number": "1001",
    "vendor": "zultys",
    "model": "zip33g",
    "config_url": "http://192.168.1.14:8080/provision/001565123456.cfg"
  },
  "reboot_triggered": true,
  "message": "Device registered and phone reboot triggered automatically"
}
```

**Note:** The system automatically triggers a phone reboot (via SIP NOTIFY) if the extension is currently registered. This ensures the phone immediately fetches its fresh configuration without manual intervention.

### Unregister a Device

```bash
curl -X DELETE http://localhost:8080/api/provisioning/devices/00:15:65:12:34:56
```

Response:
```json
{
  "success": true,
  "message": "Device unregistered"
}
```

## Phone Configuration

### Provisioning URL

Phones fetch their configuration from:
```
http://<pbx-server-ip>:8080/provision/<mac-address>.cfg
```

Example:
```
http://192.168.1.14:8080/provision/001565123456.cfg
```

### ⚠️ IMPORTANT: MAC Variable Formats

**Different phone vendors use different MAC address variable formats in provisioning URLs.**

When configuring phones, you must use the correct variable format for your phone vendor:

| Vendor | MAC Variable | Example URL |
|--------|-------------|-------------|
| **Zultys** | `$mac` | `http://192.168.1.14:8080/provision/$mac.cfg` |
| **Yealink** | `$mac` | `http://192.168.1.14:8080/provision/$mac.cfg` |
| **Polycom** | `$mac` | `http://192.168.1.14:8080/provision/$mac.cfg` |
| **Grandstream** | `$mac` | `http://192.168.1.14:8080/provision/$mac.cfg` |
| **Cisco** | `$MA` | `http://192.168.1.14:8080/provision/$MA.cfg` |

**Common Mistake:** Using `{mac}` instead of `$mac` will cause the phone to request the literal string "{mac}" instead of its actual MAC address, resulting in provisioning failure.

**Note:** While DHCP Option 66 documentation often shows `{mac}` as a placeholder for humans, actual phone configuration requires the vendor-specific variable format shown above.

### Setting Up Phones

#### Method 1: DHCP Option 66 (Recommended)

Configure your DHCP server to provide the provisioning server URL **using the correct MAC variable for your phones**:

**For Zultys, Yealink, Polycom, Grandstream:**
```
Option 66: http://192.168.1.14:8080/provision/$mac.cfg
```

**For Cisco:**
```
Option 66: http://192.168.1.14:8080/provision/$MA.cfg
```

Most IP phones will automatically request configuration on boot.

#### Method 2: Manual Configuration

Access the phone's web interface or menu system and set the provisioning URL manually.

**Zultys ZIP Phones (33G and 37G):**
- Navigate to: Settings → Auto Provisioning
- Server URL: `http://192.168.1.14:8080/provision/$mac.cfg`
- Or access via phone menu: Setup → Network → Provisioning

**Yealink Phones:**
- Web Interface: Settings → Auto Provision
- Server URL: `http://192.168.1.14:8080/provision/$mac.cfg`

**Polycom Phones:**
- Web Interface: Settings → Provisioning Server
- Server URL: `http://192.168.1.14:8080/provision/$mac.cfg`

**Cisco Phones:**
- Web Interface: Admin Login → Voice → Provisioning
- Profile Rule: `http://192.168.1.14:8080/provision/$MA.cfg`

**Grandstream Phones:**
- Web Interface: Maintenance → Upgrade and Provisioning
- Config Server Path: `http://192.168.1.14:8080/provision/`

## Configuration Templates

### Built-in Templates

The system includes pre-configured templates for each supported vendor. These templates configure:

- Extension number and display name
- SIP server address and port
- Authentication credentials
- Codec preferences (G.711 PCMU/PCMA)
- Time zone settings
- Basic phone settings

### Custom Templates

You can create custom templates for additional phone models or vendors.

1. Create a template file in your custom templates directory
2. Name it: `vendor_model.template`
3. Use placeholders for variable substitution

**Available Placeholders:**
- `{{EXTENSION_NUMBER}}` - Extension number
- `{{EXTENSION_NAME}}` - Extension display name
- `{{EXTENSION_PASSWORD}}` - Extension password
- `{{SIP_SERVER}}` - SIP server IP address
- `{{SIP_PORT}}` - SIP server port
- `{{SERVER_NAME}}` - PBX server name

**Example Custom Template:**

Create `custom_templates/yealink_t57w.template`:
```ini
#!version:1.0.0.1

# Account 1
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}

# Custom settings for T57W
wifi.enable = 1
bluetooth.enable = 1
```

Update `config.yml`:
```yaml
provisioning:
  enabled: true
  custom_templates_dir: "custom_templates"
```

## Security Considerations

### Best Practices

1. **Use HTTPS**: In production, configure HTTPS for the provisioning server to encrypt credentials in transit.

2. **Network Segmentation**: Keep phones and PBX on a separate VLAN from user workstations.

3. **Access Control**: Consider implementing MAC address filtering or authentication for provisioning endpoints.

4. **Password Strength**: Use strong, unique passwords for each extension.

5. **Regular Updates**: Keep phone firmware updated to address security vulnerabilities.

### HTTPS Configuration (Future)

While the current implementation uses HTTP, production deployments should use HTTPS:

```yaml
provisioning:
  enabled: true
  use_https: true
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"
  url_format: "https://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg"
```

## Troubleshooting

### Phone Not Provisioning

1. **Check network connectivity**: Ensure phone can reach PBX server
   ```bash
   # From phone's network
   ping 192.168.1.14
   curl http://192.168.1.14:8080/api/status
   ```

2. **Verify device registration**: Check if device is registered
   ```bash
   curl http://192.168.1.14:8080/api/provisioning/devices
   ```

3. **Check MAC address**: Ensure MAC address is correct (try different formats)
   ```bash
   # Phone logs usually show the MAC being used
   # Try registering with exact format
   ```

4. **Review logs**: Check PBX logs for provisioning requests
   ```bash
   tail -f logs/pbx.log | grep -i provision
   ```

5. **Test config generation**: Manually request config file
   ```bash
   curl http://192.168.1.14:8080/provision/001565123456.cfg
   ```

### Phone Registers but No Audio

This is typically not a provisioning issue. Check:
- NAT/firewall configuration
- RTP port range (10000-20000)
- Codec compatibility

### Wrong Configuration Applied

1. Check device registration matches correct extension
2. Verify extension configuration in config.yml
3. Re-provision phone (reboot or force update)

### Phone Display Name Not Updating from Active Directory

**Good News**: As of this version, phone reboots are **automatically triggered** after Active Directory synchronization updates user names. No manual intervention or configuration required!

**How It Works**:
- When AD sync updates extension names, the system automatically detects which phones need updating
- PBX sends SIP NOTIFY messages to trigger phone reboots
- Phones reboot and fetch fresh configuration with updated display names
- All happens automatically during the AD sync process

**Manual Options** (if needed):
If you need to manually trigger a reboot:

1. **Via API**:
   ```bash
   # Reboot all phones
   curl -X POST http://192.168.1.14:8080/api/phones/reboot
   
   # Or reboot specific extension
   curl -X POST http://192.168.1.14:8080/api/phones/1001/reboot
   ```

2. **Via Phone Menu**:
   - Access phone menu (varies by vendor)
   - Navigate to System → Reboot
   - Phone will fetch fresh config on startup

**Verify Name Update**:
```bash
# Check current extension name in PBX
curl http://192.168.1.14:8080/api/extensions | grep -A3 '"number":"1001"'

# Test config generation for a device
curl http://192.168.1.14:8080/provision/001565123456.cfg | grep -i "display\|label"
```

### Use Troubleshooting Tool

For comprehensive provisioning diagnostics, use the built-in troubleshooting tool:

```bash
# Run full diagnostic check
python scripts/troubleshoot_provisioning.py

# Check specific MAC address
python scripts/troubleshoot_provisioning.py --mac 00:15:65:12:34:56

# Check remote PBX
python scripts/troubleshoot_provisioning.py --host 192.168.1.14 --port 8080
```

The tool will:
- Check provisioning configuration
- Test API connectivity
- Show provisioning statistics
- Display recent provisioning requests
- Test MAC address registration
- Test config download
- Provide specific recommendations

### API Endpoints for Troubleshooting

```bash
# Get provisioning diagnostics
curl http://192.168.1.14:8080/api/provisioning/diagnostics

# View recent provisioning requests
curl http://192.168.1.14:8080/api/provisioning/requests?limit=20

# List all provisioned devices
curl http://192.168.1.14:8080/api/provisioning/devices

# Check supported vendors/models
curl http://192.168.1.14:8080/api/provisioning/vendors
```

## MAC Address to IP Address Correlation

### Problem Statement

When phones register via SIP, they provide their IP address but often **do not provide their MAC address** in SIP headers. This makes it difficult to identify which physical phone is which when you only see an IP address in the logs.

The PBX system tracks phones in two places:
1. **Provisioning System** - Stores MAC addresses (from when you register devices)
2. **SIP Registration** - Stores IP addresses (from when phones actually connect)

### Solution: Correlation API Endpoints

The system provides API endpoints that correlate these two data sources, allowing you to:
- Given an IP address → Find the MAC address
- Given a MAC address → Find the current IP address
- See all phones with both MAC and IP information

### GET /api/registered-phones/with-mac

List all registered phones with MAC addresses correlated from provisioning data.

**Example:**
```bash
curl http://192.168.1.14:8080/api/registered-phones/with-mac
```

**Response:**
```json
[
  {
    "id": 1,
    "extension_number": "1001",
    "ip_address": "192.168.1.100",
    "mac_address": "001565123456",
    "user_agent": "Yealink SIP-T46S 66.85.0.5",
    "mac_source": "provisioning",
    "vendor": "yealink",
    "model": "t46s",
    "config_url": "http://192.168.1.14:8080/provision/001565123456.cfg",
    "first_registered": "2025-12-05T10:00:00",
    "last_registered": "2025-12-05T12:00:00"
  }
]
```

**Key Fields:**
- `mac_source`: Shows if MAC came from `"sip_registration"` or `"provisioning"`
- `vendor`, `model`: From provisioning system
- `config_url`: Where phone gets its configuration

### GET /api/phone-lookup/{mac_or_ip}

Unified lookup endpoint that accepts either MAC address or IP address.

**Lookup by IP Address:**
```bash
# When you see IP 192.168.1.100 and want to know which phone it is
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
    "user_agent": "Yealink SIP-T46S"
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

**Lookup by MAC Address:**
```bash
# When you have MAC and want to know current IP
curl http://192.168.1.14:8080/api/phone-lookup/00:15:65:12:34:56
```

**Response:**
```json
{
  "identifier": "00:15:65:12:34:56",
  "type": "mac",
  "provisioned_device": {
    "mac_address": "001565123456",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s"
  },
  "registered_phone": {
    "extension_number": "1001",
    "ip_address": "192.168.1.100"
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

### Use Case Examples

#### 1. Identify Unknown IP Address

**Problem:** You see phone traffic from IP 192.168.1.105 and want to identify which phone it is.

**Solution:**
```bash
curl http://192.168.1.14:8080/api/phone-lookup/192.168.1.105
```

**Result:** Get extension, MAC address, vendor, and model

#### 2. Find Current IP for Provisioned Device

**Problem:** You provisioned device with MAC 00:15:65:AB:CD:EF and want to know what IP it got from DHCP.

**Solution:**
```bash
curl http://192.168.1.14:8080/api/phone-lookup/00:15:65:AB:CD:EF
```

**Result:** Get current IP address from SIP registration

#### 3. Asset Inventory

**Problem:** Need complete inventory of all phones with MAC and IP addresses.

**Solution:**
```bash
curl http://192.168.1.14:8080/api/registered-phones/with-mac | jq .
```

**Result:** Complete list with MAC, IP, vendor, model for each phone

#### 4. Troubleshooting Phone Issues

**Problem:** User on extension 1002 reports issues, need to identify exact device.

**Solution:**
```bash
curl http://192.168.1.14:8080/api/registered-phones/extension/1002
```

**Result:** Get all registration details including IP and MAC

### Python Example

See `examples/phone_lookup_example.py` for a complete Python script demonstrating these endpoints:

```bash
python examples/phone_lookup_example.py http://192.168.1.14:8080
```

### Workflow: Provisioning and Tracking

1. **Register device in provisioning system** (stores MAC):
   ```bash
   curl -X POST http://192.168.1.14:8080/api/provisioning/devices \
     -H "Content-Type: application/json" \
     -d '{
       "mac_address": "00:15:65:12:34:56",
       "extension_number": "1001",
       "vendor": "yealink",
       "model": "t46s"
     }'
   ```

2. **Phone boots and registers via SIP** (stores IP):
   - Phone automatically registers
   - System captures IP address
   - MAC may or may not be in SIP headers

3. **Query correlation to get both MAC and IP**:
   ```bash
   # By IP
   curl http://192.168.1.14:8080/api/phone-lookup/192.168.1.100
   
   # By MAC
   curl http://192.168.1.14:8080/api/phone-lookup/00:15:65:12:34:56
   
   # All phones with both
   curl http://192.168.1.14:8080/api/registered-phones/with-mac
   ```

## Integration Examples

### Python Integration

```python
import requests

# Register a new device
response = requests.post(
    'http://localhost:8080/api/provisioning/devices',
    json={
        'mac_address': '00:15:65:12:34:56',
        'extension_number': '1005',
        'vendor': 'yealink',
        'model': 't46s'
    }
)

print(response.json())

# List all devices
devices = requests.get('http://localhost:8080/api/provisioning/devices')
print(devices.json())
```

### Batch Provisioning Script

```bash
#!/bin/bash
# Provision multiple phones

PBX_SERVER="http://192.168.1.14:8080"

# Array of devices: MAC,Extension,Vendor,Model
DEVICES=(
  "00:15:65:12:34:56,1001,zultys,zip33g"
  "00:15:65:12:34:57,1002,zultys,zip37g"
  "00:04:f2:ab:cd:ef,1003,yealink,t46s"
  "00:04:f2:12:ab:cd,1004,polycom,vvx450"
)

for device in "${DEVICES[@]}"; do
  IFS=',' read -r mac ext vendor model <<< "$device"
  
  echo "Registering $mac for extension $ext..."
  curl -X POST "$PBX_SERVER/api/provisioning/devices" \
    -H "Content-Type: application/json" \
    -d "{
      \"mac_address\": \"$mac\",
      \"extension_number\": \"$ext\",
      \"vendor\": \"$vendor\",
      \"model\": \"$model\"
    }"
  echo ""
done

echo "All devices registered!"
```

---

## Database Persistence

### Overview

The PBX system stores phone provisioning configurations persistently in the database, ensuring that device registrations and IP/MAC/extension mappings are maintained across system restarts.

**Benefits:**
- ✓ **No Data Loss**: Provisioning configurations survive server restarts
- ✓ **Automatic Recovery**: Devices are automatically loaded from database on startup
- ✓ **Better Tracking**: Complete history of device provisioning
- ✓ **Static IP Support**: Assign and track static IPs for phones
- ✓ **Simplified Management**: No need to re-register devices after maintenance

### How It Works

**Device Registration:**

When you register a device via the API or Admin Panel:

```bash
curl -X POST http://your-server:8080/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:15:65:12:34:56",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s"
  }'
```

The system:
1. Creates an in-memory `ProvisioningDevice` object
2. Saves the device configuration to the `provisioned_devices` database table
3. Records: MAC address, extension, vendor, model, config URL, timestamps

**System Startup:**

When the PBX starts:
1. Connects to database
2. Loads all provisioned devices from `provisioned_devices` table
3. Populates the in-memory device registry
4. Makes devices available for configuration requests

**Phone Requests Configuration:**

When a phone boots and requests its configuration file:
1. Phone makes HTTP request: `GET /provision/00-15-65-12-34-56.cfg`
2. PBX looks up device by MAC address (in memory, loaded from database)
3. Generates configuration from template with device-specific parameters
4. Updates `last_provisioned` timestamp in database
5. Serves configuration file to phone

### Database Tables

**provisioned_devices:**
```sql
CREATE TABLE provisioned_devices (
    id SERIAL PRIMARY KEY,
    mac_address VARCHAR(17) UNIQUE NOT NULL,
    extension_number VARCHAR(20) NOT NULL,
    vendor VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    config_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_provisioned TIMESTAMP
);
```

**registered_phones:**
```sql
CREATE TABLE registered_phones (
    id SERIAL PRIMARY KEY,
    mac_address VARCHAR(17),
    ip_address VARCHAR(45),
    extension_number VARCHAR(20),
    vendor VARCHAR(50),
    model VARCHAR(50),
    user_agent TEXT,
    registered_at TIMESTAMP DEFAULT NOW()
);
```

### Managing Persistence

**List all provisioned devices:**
```bash
python scripts/list_provisioned_devices.py
```

**Clear provisioning data:**
```bash
# Clear from database
python scripts/clear_provisioned_devices.py

# Or via SQL
psql -d pbx_system -c "DELETE FROM provisioned_devices;"
```

**Export/Import provisioning data:**
```bash
# Export to JSON
python scripts/export_provisioning.py > devices.json

# Import from JSON
python scripts/import_provisioning.py devices.json
```

---

## Template Customization

### Overview

The PBX system automatically generates phone configuration files based on templates. Each template contains placeholders that are automatically replaced with device-specific information when a phone requests its configuration.

### Built-in Templates

Built-in templates are embedded in the code at:
```
pbx/features/phone_provisioning.py
```

**Supported placeholders:**
- `{{SERVER_IP}}` - PBX server IP address
- `{{SIP_PORT}}` - SIP port (default: 5060)
- `{{EXTENSION}}` - Extension number
- `{{PASSWORD}}` - Extension password
- `{{DISPLAY_NAME}}` - Extension display name
- `{{MAC_ADDRESS}}` - Phone MAC address
- `{{VENDOR}}` - Phone vendor
- `{{MODEL}}` - Phone model

### Custom Templates Directory

To use custom templates:

1. **Create templates directory:**
   ```bash
   mkdir -p provisioning_templates
   ```

2. **Configure in config.yml:**
   ```yaml
   provisioning:
     enabled: true
     custom_templates_dir: "provisioning_templates"
   ```

3. **Create template file:**
   
   File naming convention: `{vendor}_{model}.cfg`
   
   Example: `provisioning_templates/yealink_t46s.cfg`
   
   ```xml
   #!version:1.0.0.1
   
   [ account ]
   path=/config/voip/sipAccount0.cfg
   Enable=1
   Label={{DISPLAY_NAME}}
   DisplayName={{DISPLAY_NAME}}
   AuthName={{EXTENSION}}
   UserName={{EXTENSION}}
   password={{PASSWORD}}
   SIPServerHost={{SERVER_IP}}
   SIPServerPort={{SIP_PORT}}
   ```

### Viewing Current Templates

**List available templates:**
```bash
python scripts/list_provisioning_templates.py
```

**View template content:**
```bash
python scripts/view_template.py yealink t46s
```

**Test template generation:**
```bash
python scripts/test_template.py \
  --vendor yealink \
  --model t46s \
  --extension 1001 \
  --mac 00:15:65:12:34:56
```

### Creating Custom Templates

**Template Guidelines:**
1. Use vendor-specific configuration format
2. Include all required parameters for phone operation
3. Test with actual phone before deploying
4. Document any custom settings
5. Keep security in mind (use HTTPS where possible)

**Example: Custom Yealink Template**

File: `provisioning_templates/yealink_custom.cfg`

```xml
#!version:1.0.0.1

# Account Configuration
[ account ]
path=/config/voip/sipAccount0.cfg
Enable=1
Label={{DISPLAY_NAME}}
DisplayName={{DISPLAY_NAME}}
AuthName={{EXTENSION}}
UserName={{EXTENSION}}
password={{PASSWORD}}
SIPServerHost={{SERVER_IP}}
SIPServerPort={{SIP_PORT}}

# Custom: Time Zone
[ Time ]
path=/config/Setting/autop/Time.cfg
TimeZone=-5  # EST
TimeZoneName=US-Eastern

# Custom: Call Features
[ Features ]
path=/config/Features/features.cfg
call_waiting.enable=1
forward.always.enable=0
auto_answer.enable=0
dnd.enable=0

# Custom: Network Settings
[ Network ]
path=/config/Network/network.cfg
static_ip.enable=0  # Use DHCP
vlan.enable=0
qos.enable=1
qos.audio.dscp=46  # Expedited Forwarding
```

### Template Priority

Templates are loaded in this order (first match wins):
1. Custom template in `custom_templates_dir`
2. Built-in template in code
3. Generic fallback template

---

## Registration Cleanup

### Overview

The PBX system automatically cleans up incomplete phone registrations at startup to maintain database integrity.

### Automatic Cleanup at Startup

When the PBX system starts:

1. **Database Connection**: After database tables are created
2. **Cleanup Execution**: `cleanup_incomplete_registrations()` is called
3. **Removal Criteria**: Any registration missing MAC, IP, or Extension is removed
4. **Logging**: Number of removed registrations is logged

### What Gets Removed

A phone registration is considered **incomplete** and will be removed if:
- `mac_address` is NULL or empty string
- **OR** `ip_address` is NULL or empty string
- **OR** `extension_number` is NULL or empty string

### What Gets Retained

A phone registration is **retained** only if:
- `mac_address` is NOT NULL and NOT empty
- **AND** `ip_address` is NOT NULL and NOT empty
- **AND** `extension_number` is NOT NULL and NOT empty

### Example Scenarios

**Before Cleanup:**
```
ID | MAC Address       | IP Address    | Extension  | Status
1  | 00:15:65:12:34:56 | 192.168.1.100 | 1001      | ✓ Complete
2  | NULL              | 192.168.1.101 | 1002      | ✗ Incomplete (missing MAC)
3  | 00:15:65:ab:cd:ef | NULL          | 1003      | ✗ Incomplete (missing IP)
4  | 00:15:65:11:22:33 | 192.168.1.102 | NULL      | ✗ Incomplete (missing Extension)
5  | 00:15:65:44:55:66 | 192.168.1.103 | 1005      | ✓ Complete
```

**After Cleanup:**
```
ID | MAC Address       | IP Address    | Extension  | Status
1  | 00:15:65:12:34:56 | 192.168.1.100 | 1001      | ✓ Complete
5  | 00:15:65:44:55:66 | 192.168.1.103 | 1005      | ✓ Complete
```

**Logs:**
```
INFO - Removed 3 incomplete phone registrations
INFO - Kept 2 complete phone registrations
```

### Manual Cleanup

To manually trigger cleanup without restarting:

```bash
python scripts/cleanup_phone_registrations.py
```

### Why Cleanup is Important

- Prevents database clutter
- Avoids confusion about registered devices
- Ensures accurate device inventory
- Improves query performance
- Maintains data integrity

---

## Troubleshooting

### Phone Not Getting Configuration

**Problem**: Phone requests configuration but gets 404

**Solutions:**
1. Verify device is registered:
   ```bash
   curl http://your-server:8080/api/provisioning/devices
   ```

2. Check MAC address format matches (hyphens vs colons)

3. Verify provisioning is enabled in config.yml

4. Check logs:
   ```bash
   tail -f logs/pbx.log | grep -i provision
   ```

### Configuration Not Updating

**Problem**: Made changes but phone still has old config

**Solutions:**
1. Reboot the phone (may cache configuration)
2. Update `last_provisioned` timestamp:
   ```bash
   curl -X PUT http://your-server:8080/api/provisioning/devices/00-15-65-12-34-56/touch
   ```
3. Clear phone's configuration cache (vendor-specific)

### Template Errors

**Problem**: Phone gets malformed configuration

**Solutions:**
1. Verify template syntax for vendor
2. Test template generation:
   ```bash
   python scripts/test_template.py --vendor yealink --model t46s --extension 1001
   ```
3. Check all placeholders are replaced
4. Review vendor documentation for required fields

### Database Issues

**Problem**: Devices not persisting across restarts

**Solutions:**
1. Verify database connection:
   ```bash
   python scripts/verify_database.py
   ```
2. Check `provisioned_devices` table exists
3. Verify write permissions to database
4. Check logs for database errors

### Incomplete Registrations

**Problem**: Devices being removed at startup

**Solutions:**
1. Ensure phones provide all required information during registration
2. Check SIP REGISTER messages include Contact header with IP
3. Verify MAC address extraction from User-Agent or Contact header
4. Review phone's SIP configuration

---

## Future Enhancements

Planned improvements for phone provisioning:

- [ ] TFTP server support
- [ ] HTTPS/TLS support for secure provisioning
- [ ] Phone firmware management
- [ ] Advanced configuration options (BLF, speed dials, etc.)
- [ ] Template editor UI
- [ ] Bulk import/export of device configurations
- [ ] Phone status monitoring
- [ ] Automatic MAC address discovery
- [ ] Support for additional vendors and models (Fanvil, Sangoma, Avaya, etc.)
- [ ] Additional Yealink models (T42S, T48S, T54W, T57W)
- [ ] Additional Polycom models (VVX 250, VVX 350, VVX 410)
- [ ] Additional Cisco models (SPA525G2, SPA303)
- [ ] Additional Grandstream models (GXP1620, GXP1628, GXP2135)

## References

### Vendor Documentation

- **Zultys ZIP Phones**: Contact Zultys for specific provisioning documentation for ZIP 33G and ZIP 37G models
- **Yealink**: [Yealink Auto Provisioning Guide](http://support.yealink.com/documentFront/forwardToDocumentFrontDisplayPage)
- **Polycom**: [Polycom UC Software Administration Guide](https://documents.polycom.com/)
- **Cisco**: [Cisco Small Business SPA500 Series IP Phones Administration Guide](https://www.cisco.com/c/en/us/support/collaboration-endpoints/small-business-spa-500-series-ip-phones/products-maintenance-guides-list.html)
- **Grandstream**: [Grandstream Device Management System](http://www.grandstream.com/support/tools)

---

For additional support or questions, please open a GitHub issue.
