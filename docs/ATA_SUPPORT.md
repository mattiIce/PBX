# ATA (Analog Telephone Adapter) Support

This document provides information about ATA support in the Warden VoIP PBX System.

## Overview

Analog Telephone Adapters (ATAs) allow you to connect traditional analog devices such as:
- Analog telephones
- Fax machines
- Legacy PBX systems
- Door phones and intercoms
- Overhead paging systems

The Warden VoIP system provides comprehensive support for ATAs with automatic device type detection, separate management interfaces, and optimized configuration templates.

## Supported ATA Models

### Cisco ATAs

#### Cisco ATA 191/192 (Enterprise ATAs)
- **Cisco ATA 191**: 2-port enterprise ATA with Power over Ethernet (PoE)
- **Cisco ATA 192**: 2-port multiplatform ATA
- **Features**: 
  - Power over Ethernet (ATA 191)
  - Enterprise-grade security (TLS/SRTP)
  - T.38 fax support
  - Advanced codec support (G.711u/a, G.729a)
  - Echo cancellation and voice processing

#### Cisco SPA112/122 (Small Business ATAs)
- **Cisco SPA112**: 2-port analog telephone adapter
- **Cisco SPA122**: 2-port ATA with integrated router
- **Features**:
  - Reliable analog connectivity
  - T.38 fax support
  - DHCP server (SPA122)
  - NAT router functionality (SPA122)

### Grandstream ATAs

#### Grandstream HandyTone Series
- **HT801**: 1-port analog telephone adapter
- **HT802**: 2-port analog telephone adapter
- **HT812**: 2-port ATA with advanced routing
- **HT814**: 4-port analog telephone adapter
- **HT818**: 8-port analog telephone adapter
- **Features**:
  - Advanced security encryption
  - Automated provisioning
  - T.38 fax over IP
  - Caller ID support
  - Flexible dial plan

### Obihai ATAs

- **OBi200/202**: 2-port voice gateways
- **OBi300/302**: Business-grade ATAs
- **OBi504/508**: Multi-port enterprise solutions

## Feature Implementation

### 1. Device Type Detection

The system automatically detects whether a device is an ATA or regular phone based on:
- Vendor name (cisco, grandstream, obihai)
- Model name (ata191, ata192, spa112, spa122, ht801, ht802, etc.)
- Keywords in model name (ata, ht8, spa112, spa122, obi)

This detection happens automatically when registering a device.

### 2. Separate ATA Management

#### Admin Interface
- **Registered ATAs Tab**: View all currently registered ATA devices
  - Extension number
  - IP address
  - MAC address
  - Vendor/Model information
  - User agent string
  - Last registration time

- **Provisioned Devices Table**: Visual indicators distinguish ATAs from phones
  - 📠 badge for ATAs
  - ☎️ badge for phones

#### API Endpoints
- `GET /api/provisioning/atas` - List all provisioned ATAs
- `GET /api/provisioning/phones` - List phones only (excluding ATAs)
- `GET /api/registered-atas` - List currently registered ATAs

### 3. Database Schema

The `provisioned_devices` table includes a `device_type` column:
- `'ata'` - Analog telephone adapter
- `'phone'` - Regular SIP phone

Migration is automatic - existing databases will be updated on startup.

### 4. Configuration Templates

Each ATA model has an optimized configuration template with:

#### Cisco ATA 191 Template Features
- XML-based configuration format
- Power over Ethernet support
- Dual FXS port configuration
- Advanced codec selection (G.711u/a primary, G.729a fallback)
- T.38 fax support with redundancy
- Echo cancellation and suppression
- Caller ID (Bellcore standard)
- Security features (TLS/SRTP)
- Regional settings (NTP, time zone)
- QoS/DSCP marking
- Hook flash timer configuration

#### Grandstream HT801/802 Template Features
- Parameter-based configuration
- Single/dual port support
- DTMF relay (SIP INFO)
- T.38 fax mode
- Echo cancellation
- Analog-specific settings (caller ID, offhook auto-dial)
- Network configuration (DHCP, VLAN)

## Configuration Guide

### Step 1: Register the ATA Device

Using the Admin Interface:
1. Navigate to **Phone Provisioning** tab
2. Fill in the **Add New Phone Device** form:
   - MAC Address: Enter ATA's MAC address
   - Extension Number: Select the extension to assign
   - Phone Vendor: Select "cisco" or "grandstream"
   - Phone Model: Select the ATA model (ata191, ht801, etc.)
3. Click **Register Device**

Using the API:
```bash
curl -X POST https://your-pbx:8080/api/provisioning/devices \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -d '{
    "mac_address": "00:0B:82:11:22:33",
    "extension_number": "1001",
    "vendor": "cisco",
    "model": "ata191"
  }'
```

### Step 2: Configure ATA to Fetch Configuration

#### Option A: DHCP Option 66 (Automatic)
Configure your DHCP server to provide the provisioning URL:
```
Option 66: http://your-pbx-ip:8080/provision/{mac}.cfg
```

#### Option B: Manual Configuration
Access the ATA's web interface and configure:
- **Provisioning URL**: `http://your-pbx-ip:8080/provision/000b82112233.cfg`
  (Replace MAC address with your device's normalized MAC)

### Step 3: Reboot the ATA

The ATA will:
1. Download its configuration from the PBX
2. Apply the settings
3. Register to the PBX with the assigned extension

### Step 4: Verify Registration

1. Navigate to **Registered ATAs** tab in the admin interface
2. Verify your ATA appears in the list
3. Check that:
   - Extension number is correct
   - IP address is shown
   - Registration time is recent

## Best Practices

### 1. Extension Assignment
- **Dedicated extensions for fax machines**: Use separate extensions for fax devices to apply appropriate routing and codec settings
- **Port labeling**: For multi-port ATAs, document which physical port corresponds to each extension

### 2. Network Configuration
- **Static IP or DHCP reservation**: Assign consistent IP addresses to ATAs
- **VLAN segmentation**: Place ATAs on the same voice VLAN as phones
- **QoS**: Enable QoS on network switches to prioritize voice traffic

### 3. Codec Selection
- **G.711 for fax**: Always use G.711u or G.711a for fax machines (no compression)
- **T.38 recommended**: Enable T.38 fax over IP for best fax quality
- **Avoid G.729 for fax**: Compression codecs can cause fax failures

### 4. Security
- **Enable TLS/SRTP**: For secure SIP signaling and media encryption (Cisco ATA 191/192)
- **Strong passwords**: Use complex passwords for SIP authentication
- **Firmware updates**: Keep ATA firmware up to date

### 5. Troubleshooting
- **Phone lookup**: Use `/api/phone-lookup/{mac_or_ip}` to correlate provisioning and registration data
- **Provisioning logs**: Check `/api/provisioning/requests` for provisioning history
- **SIP registration**: Verify in **Registered ATAs** tab

## Troubleshooting

### ATA Not Appearing in Registered ATAs List

**Possible Causes:**
1. Device hasn't been provisioned
   - Solution: Register the device via admin interface or API
2. ATA hasn't rebooted to fetch configuration
   - Solution: Manually reboot the ATA
3. Provisioning URL incorrect
   - Solution: Verify DHCP option 66 or manual URL configuration
4. Network connectivity issues
   - Solution: Check firewall rules, ensure ATA can reach PBX on port 8080

### Fax Not Working

**Possible Causes:**
1. Wrong codec in use
   - Solution: Verify G.711u or G.711a is negotiated
2. T.38 disabled
   - Solution: Enable T.38 in ATA template
3. Echo cancellation interfering
   - Solution: Disable echo cancellation for fax extensions

### Configuration Not Applied

**Possible Causes:**
1. ATA not fetching configuration
   - Solution: Check provisioning request log
2. MAC address mismatch
   - Solution: Verify MAC address is correct and normalized
3. Template syntax error
   - Solution: Review template content

## Technical Details

### Device Type Detection Algorithm

```python
def _detect_device_type(vendor: str, model: str) -> str:
    """Detect if device is an ATA or regular phone"""
    
    # Known ATA models by vendor
    ata_models = {
        'cisco': ['ata191', 'ata192', 'spa112', 'spa122'],
        'grandstream': ['ht801', 'ht802', 'ht812', 'ht814', 'ht818'],
        'obihai': ['obi200', 'obi202', 'obi300', 'obi302', 'obi504', 'obi508'],
    }
    
    # Check exact model match
    if vendor in ata_models and model in ata_models[vendor]:
        return 'ata'
    
    # Check for ATA keywords in model name (generic patterns only)
    ata_keywords = ['ata', 'obi']
    if any(keyword in model for keyword in ata_keywords):
        return 'ata'
    
    return 'phone'
```

### Database Schema

```sql
CREATE TABLE provisioned_devices (
    id SERIAL PRIMARY KEY,
    mac_address VARCHAR(20) UNIQUE NOT NULL,
    extension_number VARCHAR(20) NOT NULL,
    vendor VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    device_type VARCHAR(20) DEFAULT 'phone',  -- 'ata' or 'phone'
    static_ip VARCHAR(50),
    config_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_provisioned TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Reference

### List Provisioned ATAs

```http
GET /api/provisioning/atas
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
[
  {
    "mac_address": "000b82112233",
    "extension_number": "1001",
    "vendor": "cisco",
    "model": "ata191",
    "device_type": "ata",
    "config_url": "http://192.168.1.10:8080/provision/000b82112233.cfg",
    "created_at": "2026-01-06T10:00:00Z",
    "last_provisioned": "2026-01-06T11:30:00Z"
  }
]
```

### List Registered ATAs

```http
GET /api/registered-atas
```

**Response:**
```json
[
  {
    "extension_number": "1001",
    "ip_address": "192.168.1.50",
    "mac_address": "000b82112233",
    "vendor": "cisco",
    "model": "ata191",
    "device_type": "ata",
    "user_agent": "Cisco-ATA191/1.2.3",
    "last_registered": "2026-01-06T11:45:00Z"
  }
]
```

## Related Documentation

- [Phone Provisioning Guide](PHONE_PROVISIONING.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

## Support

For issues or questions about ATA support:
1. Check the troubleshooting section above
2. Review the provisioning logs via `/api/provisioning/diagnostics`
3. Check the GitHub repository for known issues
4. Open a new issue with detailed information about your ATA model and configuration
