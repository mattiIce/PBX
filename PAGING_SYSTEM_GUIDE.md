# Paging System Guide

## Overview

The PBX system includes a comprehensive paging system that allows overhead announcements through digital-to-analog converters (DACs). This system is designed for manufacturing facilities, office buildings, and other environments that require public address capabilities.

**Status**: ✅ **Admin Panel Available** - Full configuration UI in admin panel with API support. Hardware integration ready for deployment.

## Features

- **Multi-Zone Paging**: Configure multiple paging zones (e.g., Warehouse, Office, Production Floor)
- **All-Call Paging**: Page all zones simultaneously with a single extension
- **DAC Device Management**: Support for SIP-to-analog gateways from multiple vendors
- **Active Session Monitoring**: View all active paging sessions in real-time via admin panel
- **Simple Dial-to-Page**: Just dial a zone extension to initiate paging
- **Admin Panel**: Full web UI for managing zones, devices, and monitoring sessions

## Configuration

Add the following to your `config.yml`:

```yaml
features:
  paging:
    enabled: true
    prefix: "7"  # Dial 7xx for paging
    all_call_extension: "700"  # Dial 700 to page all zones
    dac_type: "sip_gateway"  # Type of DAC device
    
    # Paging zones
    zones:
      - extension: "701"
        name: "Zone 1 - Office"
        description: "Main office area"
        dac_device: "paging-gateway-1"
        analog_port: 1
      
      - extension: "702"
        name: "Zone 2 - Warehouse"
        description: "Warehouse and loading dock"
        dac_device: "paging-gateway-1"
        analog_port: 2
      
      - extension: "703"
        name: "Zone 3 - Outside"
        description: "Exterior speakers"
        dac_device: "paging-gateway-1"
        analog_port: 3
    
    # DAC devices (analog gateways)
    dac_devices:
      - device_id: "paging-gateway-1"
        device_type: "cisco_vg224"
        sip_uri: "sip:paging@192.168.1.100:5060"
        ip_address: "192.168.1.100"
        port: 5060
```

## Hardware Requirements

To implement full paging functionality, you need:

1. **Analog Gateway Device**:
   - Cisco VG202/VG204/VG224 (SIP-to-analog gateway)
   - Grandstream HT801/HT802 (ATA)
   - Polycom OBi series
   - Any SIP ATA that supports auto-answer

2. **Paging Amplifier**:
   - Bogen, Valcom, or similar PA amplifier
   - Connect to analog gateway FXO/FXS port

3. **Speakers**:
   - Overhead paging speakers
   - Configured to appropriate zones

## Usage

## Admin Panel

### Accessing the Paging Panel

1. Log in to the admin panel at `https://your-pbx-server/admin/`
2. Navigate to **Features** section in the left sidebar
3. Click **📢 Paging System**
4. You'll see three main sections:
   - **Active Paging Sessions**: Real-time view of ongoing pages
   - **Paging Zones**: Configure and manage paging zones
   - **DAC Devices**: Manage analog gateway devices

### Managing Paging Zones

#### Add a Zone

1. Click the **➕ Add Zone** button
2. Enter zone details in the prompts:
   - **Extension**: Zone extension number (e.g., "701")
   - **Name**: Descriptive zone name (e.g., "Warehouse")
   - **Description**: Optional description (e.g., "Warehouse and loading dock")
   - **Device ID**: Associated DAC device ID (optional)
3. Zone will be added immediately and appear in the table

#### View Zones

The zones table displays:
- Extension number
- Zone name
- Description
- Associated device
- Action buttons (Edit/Delete)

#### Delete a Zone

1. Find the zone in the zones table
2. Click the **🗑️** delete icon
3. Confirm the deletion when prompted
4. Zone will be removed from the system

### Managing DAC Devices

#### Add a Device

1. Click the **➕ Add Device** button
2. Enter device details in the prompts:
   - **Device ID**: Unique identifier (e.g., "dac-1")
   - **Name**: Descriptive name (e.g., "Main PA System")
   - **Type**: Device type (usually "sip_gateway")
   - **SIP Address**: SIP URI (e.g., "paging@192.168.1.10:5060")
3. Device will be added and appear in the devices table

#### View Devices

The devices table shows:
- Device ID
- Device name
- Type
- SIP address
- Status (Online/Offline/Unknown)
- Action buttons (Edit/Delete)

### Monitoring Active Pages

The **Active Paging Sessions** section displays real-time information:
- Page ID (unique identifier)
- From Extension (who initiated the page)
- Zone(s) being paged
- Start time
- Current status

Click **🔄 Refresh** to update the active sessions list.

### Testing Paging

Use the **Test Paging** form at the bottom:

1. Enter **From Extension** (your extension number)
2. Select a **Zone Extension** from the dropdown
3. Click **📢 Initiate Test Page**
4. Note: This will create a SIP call from the specified extension to the zone

### Making a Page

Users dial a paging extension to initiate a page:

- **Dial 700**: Page all zones (all-call)
- **Dial 701**: Page Zone 1 (Office)
- **Dial 702**: Page Zone 2 (Warehouse)
- **Dial 703**: Page Zone 3 (Outside)

The call is automatically answered by the gateway, and the user's audio is routed to the speakers.

### Ending a Page

Simply hang up to end the paging session. The gateway will disconnect and the page will end.

## REST API Endpoints

### Get All Zones

```bash
curl http://localhost:8080/api/paging/zones
```

Response:
```json
[
  {
    "extension": "701",
    "name": "Zone 1 - Office",
    "description": "Main office area",
    "dac_device": "paging-gateway-1",
    "created_at": "2024-01-01T10:00:00"
  }
]
```

### Add Zone

```bash
curl -X POST http://localhost:8080/api/paging/zones \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "701",
    "name": "Zone 1 - Office",
    "description": "Main office area",
    "dac_device": "paging-gateway-1"
  }'
```

### Delete Zone

```bash
curl -X DELETE http://localhost:8080/api/paging/zones/701
```

### Get DAC Devices

```bash
curl http://localhost:8080/api/paging/devices
```

### Configure DAC Device

```bash
curl -X POST http://localhost:8080/api/paging/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "paging-gateway-1",
    "device_type": "cisco_vg224",
    "sip_uri": "sip:paging@192.168.1.100:5060",
    "ip_address": "192.168.1.100",
    "port": 5060
  }'
```

### Get Active Pages

```bash
curl http://localhost:8080/api/paging/active
```

## Implementation Status

### Currently Implemented (Stub)

- ✅ Zone configuration and management
- ✅ DAC device configuration
- ✅ Paging extension detection
- ✅ Session tracking (in-memory)
- ✅ REST API endpoints
- ✅ Configuration file support

### Not Yet Implemented (Requires Hardware Integration)

- ❌ SIP call routing to gateway
- ❌ RTP audio streaming to analog output
- ❌ Auto-answer configuration on gateway
- ❌ Zone selection via DTMF
- ❌ Actual audio playback through speakers

## Implementation Guide

To complete the paging implementation, the following components need to be developed:

### 1. Gateway Registration

Register the analog gateway as a SIP endpoint in the PBX:

```python
# In pbx/features/paging.py
def _register_gateway(self, device):
    """Register gateway device with PBX"""
    # Create SIP registration for gateway
    # Configure auto-answer
    pass
```

### 2. Call Routing

Route paging calls to the appropriate gateway:

```python
# In pbx/core/pbx.py - handle_call method
if self.paging_system and self.paging_system.is_paging_extension(to_extension):
    page_id = self.paging_system.initiate_page(from_extension, to_extension)
    # Route call to gateway
    # Set up RTP stream
```

### 3. Audio Streaming

Stream audio from the calling extension to the gateway:

```python
# In pbx/rtp/handler.py
def route_to_paging(self, call, gateway_address):
    """Route RTP audio to paging gateway"""
    # Set up RTP relay
    # Forward audio packets
    pass
```

### 4. Zone Selection

For multi-port gateways, implement zone selection:

```python
def select_zone(self, gateway, zone_number):
    """Select zone on multi-port gateway"""
    # Send DTMF or use dedicated port
    # Cisco VG: Use specific FXO/FXS port
    # Other: May require DTMF signaling
    pass
```

## Hardware Setup Examples

### Cisco VG224 Setup

1. Configure FXS ports for paging:
```
voice-port 0/0
 no shutdown
 connection plar opx 701
 auto-answer
```

2. Configure SIP dial peers:
```
dial-peer voice 701 voip
 destination-pattern 701
 session protocol sipv2
 session target ipv4:192.168.1.10:5060
```

3. Connect FXS port to paging amplifier input

### Grandstream HT801 Setup

1. Configure device via web interface:
   - SIP Server: PBX IP address
   - SIP User ID: Extension number
   - Enable auto-answer
   - Disable call waiting

2. Connect FXS port to paging amplifier

3. Register device with PBX

## Best Practices

1. **Use Dedicated Extensions**: Reserve 7xx range for paging only
2. **Limit Page Duration**: Consider implementing max page duration (e.g., 2 minutes)
3. **Priority Handling**: Implement emergency override for critical pages
4. **Testing**: Test audio levels and zone coverage thoroughly
5. **Backup Power**: Ensure paging system has backup power for emergencies
6. **Training**: Train users on proper paging procedures

## Troubleshooting

### Paging extension not working

- Check that paging system is enabled in config
- Verify extension matches paging prefix
- Check that zone is configured
- Review PBX logs for errors

### No audio on page

- This is expected with the stub implementation
- Full implementation requires hardware integration
- Verify gateway is registered (when implemented)
- Check RTP routing (when implemented)

### Gateway not responding

- Verify gateway IP address and SIP configuration
- Check network connectivity to gateway
- Ensure gateway has auto-answer enabled
- Check gateway registration status

## Future Enhancements

Planned features for future releases:

- **Emergency Priority**: Override active pages for emergency notifications
- **Scheduled Paging**: Bell schedules for schools/factories
- **Page Recording**: Record pages for compliance
- **Background Music**: Play music when not paging
- **Multi-language**: Support for multiple language announcements
- **SMS Integration**: Send text alerts with pages
- **Integration with Emergency Systems**: Connect to fire alarms, etc.

## Security Considerations

- Limit who can access paging extensions (consider PIN codes)
- Monitor for paging abuse
- Implement rate limiting on paging calls
- Consider recording pages for security purposes
- Ensure emergency pages cannot be blocked

## Example Scenarios

### Office Building

- Zone 1: Office area (701)
- Zone 2: Conference rooms (702)
- Zone 3: Lobby (703)
- All-call: Entire building (700)

### Warehouse

- Zone 1: Receiving dock (701)
- Zone 2: Storage area (702)
- Zone 3: Shipping dock (703)
- Zone 4: Office area (704)
- All-call: Entire warehouse (700)

### School

- Zone 1: Elementary wing (701)
- Zone 2: Middle school wing (702)
- Zone 3: Gymnasium (703)
- Zone 4: Cafeteria (704)
- All-call: Entire school (700)

## Support

For questions or assistance with paging system implementation:

1. Review this guide and the stub implementation code
2. Check hardware compatibility with your specific gateway
3. Consult gateway vendor documentation for SIP configuration
4. Test thoroughly in a non-production environment first
