# SIP Send Line and Send MAC Guide

## Overview

The PBX system supports **SIP Send Line** and **SIP Send MAC** functionality to enhance caller identification and device tracking. These features are **enabled by default** for maximum compatibility with modern IP phones and SIP networks.

## What is SIP Send Line?

**SIP Send Line** refers to the inclusion of caller identification headers in SIP INVITE messages. This allows multi-line IP phones to properly identify which line/account is being used for a call and provides enhanced caller information to receiving devices.

### Implemented Headers

The PBX automatically adds the following headers to outgoing INVITE messages:

#### 1. P-Asserted-Identity (RFC 3325)
- **Purpose**: Asserts the verified identity of the calling party
- **Format**: `P-Asserted-Identity: "Display Name" <sip:extension@server>`
- **Use Case**: Preferred for trusted networks (enterprise environments)
- **Example**: `P-Asserted-Identity: "John Doe" <sip:1001@192.168.1.100>`

#### 2. Remote-Party-ID (Legacy)
- **Purpose**: Provides caller identification for backward compatibility
- **Format**: `Remote-Party-ID: "Display Name" <sip:extension@server>;party=calling;privacy=off;screen=no`
- **Use Case**: Widely supported by older systems and SIP phones
- **Example**: `Remote-Party-ID: "Alice Smith" <sip:1002@192.168.1.100>;party=calling;privacy=off;screen=no`

### Benefits

- **Multi-line Phone Support**: Properly identifies which line is making the call
- **Enhanced Caller ID**: Provides display name along with extension number
- **SIP Trunk Compatibility**: Works with external SIP providers and carriers
- **Line Appearance**: Supports shared line appearance and busy lamp field (BLF) functionality

## What is SIP Send MAC?

**SIP Send MAC** refers to the inclusion of device MAC address in SIP headers for device identification and tracking.

### Implemented Header

The PBX adds the following custom header to INVITE messages when a MAC address is available:

#### X-MAC-Address (Custom Header)
- **Purpose**: Identifies the physical device making the call
- **Format**: `X-MAC-Address: XX:XX:XX:XX:XX:XX`
- **Example**: `X-MAC-Address: 00:11:22:33:44:55`

### MAC Address Sources

The PBX obtains MAC addresses from multiple sources:

1. **Registered Phones Database**: MAC extracted from REGISTER messages
2. **Contact Header**: `mac=` parameter in SIP Contact header
3. **User-Agent Header**: MAC embedded in User-Agent string
4. **Incoming INVITE**: Accepts X-MAC-Address from phone if included

### Benefits

- **Device Tracking**: Identify which physical phone made a call
- **Auto-Provisioning**: Link devices to extensions automatically
- **Hot Desking**: Track phone location changes
- **Troubleshooting**: Correlate calls with specific hardware
- **Security**: Verify registered device matches expected MAC

## Configuration

### Global Configuration (config.yml)

The features are enabled by default. You can customize the behavior in `config.yml`:

```yaml
sip:
  # Caller ID and Line Identification Headers (ENABLED BY DEFAULT)
  caller_id:
    # P-Asserted-Identity (RFC 3325)
    send_p_asserted_identity: true  # DEFAULT: true
    
    # Remote-Party-ID (Legacy)
    send_remote_party_id: true      # DEFAULT: true
    
  # Device Identification (ENABLED BY DEFAULT)
  device:
    # Send MAC address in X-MAC-Address header
    send_mac_address: true          # DEFAULT: true
    
    # Accept MAC address from phones in INVITE messages
    accept_mac_in_invite: true      # DEFAULT: true
```

### Phone Provisioning Templates

All provisioning templates have been updated to configure phones to send line and MAC information:

#### Yealink (T46S, T28G)
```
account.1.send_line_id = 1
account.1.enable_user_equal_phone = 1
```

#### Grandstream (GXP2170)
```
P2350 = 1  # Send P-Asserted-Identity
P2351 = 1  # Send Remote-Party-ID
```

#### Cisco (SPA504G)
```
Send_Caller_ID_In_From_Header_1_ : Yes
Remote_Party_ID_1_ : Yes
```

#### Zultys (ZIP33G, ZIP37G)
```
account.1.send_line_id = 1
account.1.enable_user_equal_phone = 1
```

#### Polycom (VVX450)
```xml
<call call.remotePartyID.1.render="1"
      call.remotePartyID.1.stage="1"/>
```

## How It Works

### Call Flow with SIP Send Line

1. **Phone A (Ext 1001) calls Phone B (Ext 1002)**
2. **PBX receives INVITE** from Phone A
3. **PBX looks up caller information**:
   - Extension number: 1001
   - Display name: "John Doe" (from extension registry)
   - MAC address: "00:11:22:33:44:55" (from registered phones DB)
4. **PBX adds headers** to forwarded INVITE:
   ```
   P-Asserted-Identity: "John Doe" <sip:1001@192.168.1.100>
   Remote-Party-ID: "John Doe" <sip:1001@192.168.1.100>;party=calling;privacy=off;screen=no
   X-MAC-Address: 00:11:22:33:44:55
   ```
5. **Phone B receives INVITE** with full caller information
6. **Phone B displays** "John Doe (1001)" on screen

### MAC Address Extraction

The PBX automatically extracts MAC addresses from REGISTER messages using multiple patterns:

1. **Contact Header with mac= parameter**:
   ```
   Contact: <sip:1001@192.168.1.50:5060;mac=00:11:22:33:44:55>
   ```

2. **SIP Instance ID (UUID)**:
   ```
   Contact: <sip:1001@192.168.1.50:5060>;+sip.instance="<urn:uuid:00112233-4455-6677-8899-aabbccddeeff>"
   ```

3. **User-Agent Header**:
   ```
   User-Agent: Yealink SIP-T46S 66.85.0.5 00:15:65:12:34:56
   ```

## Testing

### Verify SIP Headers

To verify that the headers are being sent, you can use a SIP packet capture tool like:

1. **tcpdump**: `tcpdump -i any -s 0 -w sip_capture.pcap port 5060`
2. **Wireshark**: Filter by `sip` protocol
3. **sngrep**: `sngrep -d any port 5060`

Look for the following headers in INVITE messages:
- `P-Asserted-Identity`
- `Remote-Party-ID`
- `X-MAC-Address`

### Test Call Example

```bash
# Make a test call
# From extension 1001 to extension 1002

# Check logs for header confirmation
tail -f logs/pbx.log | grep "Added caller ID headers"
tail -f logs/pbx.log | grep "Added X-MAC-Address"
```

Expected log output:
```
Added caller ID headers: John Doe <1001>
Added X-MAC-Address header: 00:11:22:33:44:55
```

## Troubleshooting

### Headers Not Appearing

If headers are not being sent:

1. **Check configuration** in `config.yml`:
   ```bash
   grep -A 10 "^sip:" config.yml
   ```

2. **Verify feature is enabled**:
   - `send_p_asserted_identity: true`
   - `send_remote_party_id: true`
   - `send_mac_address: true`

3. **Check extension has display name**:
   ```bash
   # Via API
   curl http://localhost:8080/api/extensions/1001
   
   # Check database
   psql -d pbx_system -c "SELECT extension_number, name FROM extensions WHERE extension_number = '1001';"
   ```

4. **Verify MAC address is registered**:
   ```bash
   # Via API
   curl http://localhost:8080/api/phones
   
   # Check database
   psql -d pbx_system -c "SELECT extension_number, mac_address FROM registered_phones WHERE extension_number = '1001';"
   ```

### MAC Address Not Found

If MAC address header is missing:

1. **Phone didn't send MAC in REGISTER**: Some phones may not include MAC by default
2. **Update provisioning template**: Ensure phone is configured to send MAC
3. **Manual registration**: You can manually register a phone with MAC via API:
   ```bash
   curl -X POST http://localhost:8080/api/phones/register \
     -H "Content-Type: application/json" \
     -d '{
       "mac": "00:11:22:33:44:55",
       "extension": "1001",
       "vendor": "yealink",
       "model": "t46s"
     }'
   ```

### Display Name Shows Extension Number

If display name shows extension number instead of user name:

1. **Extension missing name**: Add display name to extension
2. **Database not synchronized**: Check that extension exists in database
3. **Extension registry issue**: Restart PBX to reload extensions

## Security Considerations

### Trusted Networks Only

P-Asserted-Identity should only be used in trusted networks because:
- The PBX asserts the identity without verification
- Receiving systems trust the header implicitly
- Should not be forwarded to untrusted SIP trunks

### Privacy

When privacy is required:
- Set `send_p_asserted_identity: false`
- Set `send_remote_party_id: false`
- Headers will not be added to INVITE messages

### MAC Address Privacy

MAC addresses are considered sensitive device identifiers:
- Only sent within internal network
- Should be filtered at SIP trunk boundaries
- Consider disabling for privacy-sensitive deployments

## Standards and RFCs

- **RFC 3261**: SIP: Session Initiation Protocol
- **RFC 3323**: A Privacy Mechanism for the Session Initiation Protocol (SIP)
- **RFC 3325**: Private Extensions to the Session Initiation Protocol (SIP) for Asserted Identity within Trusted Networks
- **RFC 4474**: Enhancements for Authenticated Identity Management in the Session Initiation Protocol (SIP)

## Related Documentation

- [COMPLETE_GUIDE.md - Section 4.3: Phone Provisioning](../../COMPLETE_GUIDE.md#43-phone-provisioning) - Phone provisioning guide
- [SIP_METHODS_IMPLEMENTATION.md](SIP_METHODS_IMPLEMENTATION.md) - SIP methods reference
- [COMPLETE_GUIDE.md - Section 9.2: REST API](../../COMPLETE_GUIDE.md#92-rest-api-reference) - REST API reference

## Summary

SIP Send Line and Send MAC features are **enabled by default** and require no configuration for basic operation. The PBX automatically:

- Adds P-Asserted-Identity headers for caller identification
- Adds Remote-Party-ID headers for backward compatibility
- Adds X-MAC-Address headers for device tracking
- Extracts MAC addresses from REGISTER messages
- Configures phones via provisioning templates  

These features enhance call quality, troubleshooting, and device management without requiring manual intervention.
