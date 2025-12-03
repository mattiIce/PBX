# Phone Provisioning Guide

The PBX system includes a comprehensive phone provisioning system that allows automatic configuration of IP phones from multiple vendors.

## Overview

Phone provisioning enables zero-touch or simplified deployment of IP phones by automatically generating and serving configuration files. When a phone boots up, it can request its configuration from the PBX server, eliminating the need for manual configuration of each device.

## Supported Phone Vendors

The system includes built-in templates for the following vendors and models:

### Yealink
- T46S
- T48S
- T42S

### Polycom
- VVX 450
- VVX 350
- VVX 250

### Cisco
- SPA504G
- SPA525G

### Grandstream
- GXP2160
- GXP2140
- GXP1628

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
      vendor: "yealink"
      model: "t46s"
    
    - mac: "00:04:f2:ab:cd:ef"
      extension: "1002"
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
    "vendor": "yealink",
    "model": "t46s",
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
  "vendors": ["cisco", "grandstream", "polycom", "yealink"],
  "models": {
    "yealink": ["t42s", "t46s", "t48s"],
    "polycom": ["vvx250", "vvx350", "vvx450"],
    "cisco": ["spa504g", "spa525g"],
    "grandstream": ["gxp1628", "gxp2140", "gxp2160"]
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
    "vendor": "yealink",
    "model": "t46s"
  }'
```

Response:
```json
{
  "success": true,
  "device": {
    "mac_address": "001565123456",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s",
    "config_url": "http://192.168.1.14:8080/provision/001565123456.cfg"
  }
}
```

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

### Setting Up Phones

#### Method 1: DHCP Option 66 (Recommended)

Configure your DHCP server to provide the provisioning server URL:

```
Option 66: http://192.168.1.14:8080/provision/{mac}.cfg
```

Most IP phones will automatically request configuration on boot.

#### Method 2: Manual Configuration

Access the phone's web interface or menu system and set the provisioning URL manually.

**Yealink:**
- Navigate to: Settings → Auto Provisioning
- Server URL: `http://192.168.1.14:8080/provision/$mac.cfg`

**Polycom:**
- Navigate to: Settings → Provisioning Server
- Server Type: HTTP
- Server Address: `192.168.1.14:8080/provision/`

**Cisco:**
- Navigate to: Admin Login → Advanced → Provisioning
- Profile Rule: `http://192.168.1.14:8080/provision/$MA.cfg`

**Grandstream:**
- Navigate to: Maintenance → Upgrade and Provisioning
- Config Server Path: `http://192.168.1.14:8080/provision/cfg$mac.cfg`

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
  "00:15:65:12:34:56,1001,yealink,t46s"
  "00:15:65:12:34:57,1002,yealink,t46s"
  "00:04:f2:ab:cd:ef,1003,polycom,vvx450"
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
- [ ] Support for additional vendors (Fanvil, Sangoma, etc.)

## References

### Vendor Documentation

- **Yealink**: [Auto Provisioning Guide](http://support.yealink.com/)
- **Polycom**: [Provisioning Guide](https://documents.polycom.com/)
- **Cisco**: [SPA Configuration Guide](https://www.cisco.com/c/en/us/support/collaboration-endpoints/spa500-series-ip-phones/products-installation-guides-list.html)
- **Grandstream**: [Provisioning Guide](http://www.grandstream.com/support)

---

For additional support or questions, please open a GitHub issue.
