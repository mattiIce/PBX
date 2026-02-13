# ATA (Analog Telephone Adapter) Support Guide

## Overview

Warden VoIP PBX now includes full support for Analog Telephone Adapters (ATAs), allowing you to connect traditional analog phones and fax machines to your modern VoIP system.

## What is an ATA?

An Analog Telephone Adapter (ATA) is a device that converts analog signals from traditional phones/fax machines into digital SIP/VoIP signals. This allows you to:

- **Use legacy analog phones** without replacing them
- **Connect fax machines** that require analog lines
- **Preserve existing infrastructure** while migrating to VoIP
- **Support paging systems** through analog outputs

## Supported ATA Devices

The PBX includes auto-provisioning templates for popular ATAs:

### Grandstream ATAs
1. **HT801** - Single-port (1 FXS port)
   - Connect one analog phone or fax machine
   - Compact, wall-mountable design
   - T.38 fax support

2. **HT802** - Dual-port (2 FXS ports)
   - Connect two analog devices
   - Independent line configuration
   - T.38 fax support

### Cisco Small Business ATAs
3. **SPA112** - Dual-port (2 FXS ports)
   - Two analog lines
   - Advanced codec support
   - T.38 fax support

4. **SPA122** - Dual-port with Router
   - Two analog lines plus integrated router
   - Perfect for remote offices
   - Built-in DHCP server

### Cisco Enterprise ATAs
5. **ATA 191** (ATA191-3PW-K9) - Enterprise dual-port with PoE
   - Two FXS ports for analog devices
   - Power over Ethernet (PoE) support
   - Enterprise-grade reliability
   - T.38 fax support

6. **ATA 192** - Multiplatform dual-port
   - Two FXS ports for analog devices
   - Multiplatform firmware support
   - Enterprise features
   - T.38 fax support

## Key Features

### Analog Phone Support
- **Full SIP registration** - ATAs register like any other extension
- **Caller ID** - Display caller information on analog phones
- **Call waiting** - Standard telephony features work
- **DTMF support** - Touch-tone dialing for IVR/voicemail
- **Echo cancellation** - Crystal clear audio quality

### Fax Machine Support
- **T.38 protocol** - Fax over IP standard
- **G.711 codecs** - Uncompressed audio for reliability
- **Echo cancellation disabled during fax** - Prevents interference
- **Fallback to G.711 passthrough** - If T.38 not supported

### Paging System Integration
- Connect overhead paging amplifiers
- Multi-zone paging support
- Auto-answer configuration
- See [Paging System Guide](../COMPLETE_GUIDE.md#46-paging-system) for details

## Setup Guide

### 1. Physical Setup

1. **Connect the ATA:**
   - Plug ATA into your network (Ethernet port)
   - Connect analog phone to FXS port(s)
   - Power on the ATA

2. **Find the MAC Address:**
   - Look on the bottom label of the ATA
   - Or access the ATA web interface (default: http://192.168.0.1)
   - Format: `00:0B:82:XX:XX:XX` (Grandstream) or `00:1D:7E:XX:XX:XX` (Cisco)

### 2. Register the ATA in PBX

#### Via Admin Panel (Recommended)

1. Log into the admin panel: `http://your-pbx-ip:9000/admin/`
2. Go to **Phone Provisioning** tab
3. Click **Register New Device**
4. Fill in the form:
   - **MAC Address**: `000b82123456` (no separators)
   - **Extension**: `1001` (or any available extension)
   - **Vendor**: Select `Grandstream` or `Cisco`
   - **Model**: Select `ht801`, `ht802`, `spa112`, `spa122`, `ata191`, or `ata192`
5. Click **Register**
6. The ATA will auto-provision within 5 minutes

#### Via API

```bash
curl -X POST http://your-pbx-ip:9000/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "000b82123456",
    "extension_number": "1001",
    "vendor": "grandstream",
    "model": "ht801"
  }'
```

### 3. Configure ATA to Auto-Provision

#### Grandstream HT801/HT802

1. Access the ATA web interface (default: http://192.168.0.1)
2. Log in (default: admin/admin)
3. Go to **Maintenance** → **Upgrade and Provisioning**
4. Set:
   - **Config Server Path**: `http://your-pbx-ip:9000/provision/000b82123456.cfg`
   - **Firmware Upgrade**: Disabled (or set to your TFTP server)
5. Click **Update** and **Reboot**

#### Cisco SPA112/SPA122

1. Access the ATA admin interface
2. Go to **Admin Login** → **Advanced**
3. Under **Provisioning**:
   - **Profile Rule**: `http://your-pbx-ip:9000/provision/$MA.cfg`
   - **Resync On Reset**: No
   - **Provision Enable**: No (after initial setup)
4. Click **Submit All Changes**

### 4. Test the Configuration

1. **Pick up the analog phone** - You should hear dial tone
2. **Dial another extension** - e.g., dial `1002`
3. **Test inbound calls** - Call your analog extension from another phone
4. **Test voicemail** - Dial `*1001` (or your voicemail pattern)
5. **Test DTMF** - During a call or voicemail, press phone buttons

## Common Use Cases

### Use Case 1: Legacy Analog Phone

**Scenario**: You have an old but perfectly functional analog phone you want to keep using.

**Solution**:
1. Connect phone to Grandstream HT801
2. Register HT801 to extension 1005
3. Phone works like any other extension
4. All PBX features available (voicemail, call transfer, etc.)

### Use Case 2: Fax Machine

**Scenario**: You need to send/receive faxes over VoIP.

**Solution**:
1. Connect fax machine to HT801 or HT802
2. ATA automatically detects fax tones
3. Switches to T.38 fax protocol
4. Fax transmits reliably over IP network

**Configuration Tips**:
- Use dedicated extension for fax (e.g., 1099)
- Disable call waiting on fax extension
- Use G.711 codec (PCMU/PCMA) - already configured
- Test with short fax first

### Use Case 3: Overhead Paging

**Scenario**: Connect overhead paging amplifier for warehouse announcements.

**Solution**:
1. Connect paging amplifier to HT801 analog output
2. Configure for auto-answer
3. Set up paging zones in admin panel
4. Dial paging extension (e.g., 701) to page

See [Paging System Guide](../COMPLETE_GUIDE.md#46-paging-system) for complete setup.

### Use Case 4: Remote Office with Router

**Scenario**: Small remote office needs 2 phones and internet access.

**Solution**:
1. Use Cisco SPA122 (ATA + Router combo)
2. Connect to internet on WAN port
3. Connect office devices to LAN ports
4. Two analog phones on FXS ports
5. Single device provides routing and VoIP

## Advanced Configuration

### Dual-Port ATAs (HT802, SPA112, SPA122)

To use both ports with different extensions:

**Option 1: Web Interface (Recommended)**
1. Configure Port 1 via auto-provisioning (as above)
2. Access ATA web interface
3. Go to FXS PORT 2 settings
4. Manually configure second extension
5. Save and reboot

**Option 2: Multi-Extension Provisioning** (Future Enhancement)
- Register device twice with different extensions
- System generates config for both ports
- Currently requires manual configuration for port 2

### Custom Settings

You can customize ATA templates:

1. Export the template:
   ```bash
   curl -X POST http://your-pbx-ip:9000/api/provisioning/templates/grandstream/ht801/export
   ```

2. Edit `provisioning_templates/grandstream_ht801.template`

3. Reload templates:
   ```bash
   curl -X POST http://your-pbx-ip:9000/api/provisioning/reload-templates
   ```

### Regional Settings

Templates are configured for North America (FCC). To change:

**Grandstream:**
- `P25 = 0` - Impedance (0=600 ohm, 1=900 ohm)
- `P104 = 2000` - Ring frequency (Hz)
- `P1361 = 2` - Ring cadence

**Cisco:**
- `<FXS_Port_Impedance>600</FXS_Port_Impedance>`
- `<Ring_Frequency>20</Ring_Frequency>`

Consult your ATA documentation for region-specific values.

## Troubleshooting

### No Dial Tone

**Symptoms**: Pick up phone, no sound

**Solutions**:
1. Check physical connections (phone cable, power)
2. Verify ATA is powered on (LED indicators)
3. Check ATA registration status in admin panel
4. Access ATA web interface - verify registration
5. Check PBX logs: `tail -f logs/pbx.log | grep -i 1001`

### DTMF Not Working

**Symptoms**: Can't navigate voicemail menus, keypad tones don't work

**Solutions**:
1. Check DTMF method in template (should be SIP INFO or RFC2833)
2. Try different DTMF payload type (101, 100, 102)
3. For Grandstream: Set `P79 = 2` (SIP INFO)
4. For Cisco: Set `<DTMF_Tx_Method_1_>Auto</DTMF_Tx_Method_1_>`

### Poor Audio Quality

**Symptoms**: Echo, choppy audio, static

**Solutions**:
1. Enable echo cancellation (enabled by default)
2. Check network quality (ping, jitter, packet loss)
3. Adjust audio gain settings:
   - Grandstream: `P89` (speaker), `P90` (mic)
   - Cisco: `<Txgain_1_>`, `<Rxgain_1_>`
4. Use G.711 codec (PCMU/PCMA) for best quality
5. Check for network congestion

### Fax Not Working

**Symptoms**: Fax fails to send/receive

**Solutions**:
1. Verify T.38 is enabled (enabled by default in templates)
2. Use G.711 codec (PCMU/PCMA)
3. Disable echo cancellation during fax (automatic in templates)
4. Check that both endpoints support T.38
5. Try reducing fax speed (9600 baud instead of 14400)
6. Test with a simple 1-page fax first

### ATA Won't Auto-Provision

**Symptoms**: Manual config works, but auto-provision doesn't

**Solutions**:
1. Check provisioning URL is accessible:
   ```bash
   curl http://your-pbx-ip:9000/provision/000b82123456.cfg
   ```
2. Verify MAC address format (no colons, lowercase)
3. Check ATA can reach PBX (ping test)
4. Disable ATA firewall temporarily
5. Check PBX logs for provisioning requests
6. Try triggering manual resync on ATA

## API Reference

### Register ATA Device

```bash
POST /api/provisioning/devices
Content-Type: application/json

{
  "mac_address": "000b82123456",
  "extension_number": "1001",
  "vendor": "grandstream",
  "model": "ht801"
}
```

### Get ATA Configuration

```bash
GET /api/provision/000b82123456.cfg
```

Returns the fully-configured provisioning file for the ATA.

### List Registered Devices

```bash
GET /api/provisioning/devices
```

Returns all registered devices including ATAs.

### Trigger Reboot

```bash
POST /api/phones/1001/reboot
```

Sends SIP NOTIFY to trigger ATA reboot.

## Best Practices

1. **Use Dedicated Extensions for Fax** - Makes troubleshooting easier
2. **Label Physical Devices** - Note which extension each ATA serves
3. **Document Custom Settings** - Keep records of any template changes
4. **Test Before Deployment** - Verify all features work with your analog devices
5. **Monitor Call Quality** - Use QoS monitoring to track analog line quality
6. **Keep Firmware Updated** - Check vendor sites for ATA firmware updates
7. **Secure Web Interfaces** - Change default ATA admin passwords

## Security Considerations

1. **Change Default Passwords** - Both PBX extension and ATA admin passwords
2. **Use Strong SIP Passwords** - Auto-generated by PBX (FIPS-compliant)
3. **Disable Auto-Provisioning** - After initial setup (set Provision Enable = No)
4. **Restrict Web Access** - Use firewall rules to limit ATA web interface access
5. **Regular Updates** - Keep ATA firmware current for security patches

## Specifications

### Supported Codecs
- **G.711 (PCMU/PCMA)** - Primary codec, best for analog/fax
- **G.729** - Low bandwidth option
- **G.722** - HD audio (if ATA supports it)

### DTMF Methods
- **SIP INFO** - Recommended (most reliable)
- **RFC 2833 (RTP Events)** - Good compatibility
- **In-band** - Fallback option

### Fax Protocol
- **T.38** - Fax over IP standard (enabled by default)
- **G.711 Passthrough** - Fallback mode

## Related Documentation

- [Grandstream HT801 Documentation](https://www.grandstream.com/products/gateways-and-atas/analog-telephone-adaptors/product/ht801)
- [Grandstream HT802 Documentation](https://www.grandstream.com/products/gateways-and-atas/analog-telephone-adaptors/product/ht802)
- [Cisco SPA112 Documentation](https://www.cisco.com/c/en/us/support/unified-communications/spa112-2-port-phone-adapter/model.html)
- [Phone Provisioning Guide](../COMPLETE_GUIDE.md#43-phone-provisioning)
- [Paging System Guide](../COMPLETE_GUIDE.md#46-paging-system)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)

## Support

For issues not covered in this guide:

1. Check PBX logs: `tail -f logs/pbx.log`
2. Check ATA web interface system status
3. Review [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
4. Search existing issues on GitHub
5. Open a new issue with:
   - ATA make/model
   - Extension number
   - Problem description
   - Relevant log entries

---
