# PBX Call Flow Documentation

This document explains how phone-to-phone calls work through the PBX system with proper audio relay.

## Overview

The PBX acts as a **back-to-back user agent (B2BUA)** that:
1. Terminates SIP calls from both endpoints
2. Relays RTP audio between them
3. Provides call control and management

## Call Flow for Phone-to-Phone Calls

### 1. Initial Setup
- Both phones (e.g., Zultys ZIP 37G) register with the PBX
- PBX stores each phone's IP address and port
- Example: Extension 1001 at 192.168.1.100:5060, Extension 1002 at 192.168.1.101:5060

### 2. Call Initiation (1001 calls 1002)

```
Phone 1001                 PBX (192.168.1.14)              Phone 1002
    |                             |                              |
    | INVITE (1)                  |                              |
    | To: 1002                    |                              |
    | SDP: RTP 192.168.1.100:10000|                              |
    |---------------------------->|                              |
    |                             |                              |
    |                        100 Trying                          |
    |<----------------------------|                              |
    |                             |                              |
    |                             | INVITE (2)                   |
    |                             | To: 1002                     |
    |                             | SDP: RTP 192.168.1.14:10000  |
    |                             |----------------------------->|
    |                             |                              |
    |                             |                     180 Ringing
    |                     180 Ringing                            |
    |<----------------------------|<-----------------------------|
```

**What happens:**
- Phone 1001 sends INVITE to PBX with its RTP endpoint (192.168.1.100:10000)
- PBX allocates RTP relay port (e.g., 10000)
- PBX forwards INVITE to Phone 1002 with PBX's RTP endpoint (192.168.1.14:10000)
- PBX stores: Caller RTP = 192.168.1.100:10000

### 3. Call Answer

```
Phone 1001                 PBX (192.168.1.14)              Phone 1002
    |                             |                              |
    |                             |                        200 OK |
    |                             |     SDP: RTP 192.168.1.101:10000
    |                             |<-----------------------------|
    |                             |                              |
    |                      200 OK |                              |
    | SDP: RTP 192.168.1.14:10000 |                              |
    |<----------------------------|                              |
    |                             |                              |
    | ACK                         |                              |
    |---------------------------->|                              |
    |                             | ACK                          |
    |                             |----------------------------->|
```

**What happens:**
- Phone 1002 answers with 200 OK containing its RTP endpoint (192.168.1.101:10000)
- PBX stores: Callee RTP = 192.168.1.101:10000
- PBX configures RTP relay: 192.168.1.100:10000 <-> 192.168.1.101:10000
- PBX sends 200 OK to Phone 1001 with PBX's RTP endpoint (192.168.1.14:10000)
- Phone 1001 sends ACK, PBX forwards to Phone 1002

### 4. Audio Flow (RTP Relay)

```
Phone 1001                 PBX RTP Relay                   Phone 1002
192.168.1.100:10000      192.168.1.14:10000            192.168.1.101:10000
    |                             |                              |
    | RTP Packets                 |                              |
    |---------------------------->|                              |
    |                             | RTP Packets                  |
    |                             |----------------------------->|
    |                             |                              |
    |                             |                  RTP Packets |
    |                  RTP Packets|<-----------------------------|
    |<----------------------------|                              |
    |                             |                              |
```

**What happens:**
- Phone 1001 sends RTP audio to PBX (192.168.1.14:10000)
- PBX relay receives and forwards to Phone 1002 (192.168.1.101:10000)
- Phone 1002 sends RTP audio to PBX (192.168.1.14:10000)
- PBX relay receives and forwards to Phone 1001 (192.168.1.100:10000)
- Both parties can hear each other

### 5. Call Termination

```
Phone 1001                 PBX                              Phone 1002
    |                             |                              |
    | BYE                         |                              |
    |---------------------------->|                              |
    |                             | BYE                          |
    |                             |----------------------------->|
    |                      200 OK |                       200 OK |
    |<----------------------------|<-----------------------------|
    |                             |                              |
```

## Configuration

### Setting the Server IP

In `config.yml`, set the external IP address:

```yaml
server:
  sip_host: "0.0.0.0"  # Binds to all interfaces
  sip_port: 5060
  external_ip: "192.168.1.14"  # IP address advertised in SDP
```

**Important:** The `external_ip` must be:
- Reachable by all phones
- The actual IP address of the server (not 0.0.0.0 or 127.0.0.1)
- Used in SDP to tell phones where to send RTP packets

## SDP (Session Description Protocol)

SDP describes media sessions. Example from PBX:

```
v=0
o=pbx test-call-123 0 IN IP4 192.168.1.14
s=PBX Call
c=IN IP4 192.168.1.14
t=0 0
m=audio 10000 RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=sendrecv
```

Key fields:
- `c=IN IP4 192.168.1.14` - Connection IP (where to send RTP)
- `m=audio 10000` - Media port for RTP
- `a=rtpmap:0 PCMU/8000` - Codec definitions

## Supported Codecs

- **PCMU (G.711 μ-law)** - Payload type 0
- **PCMA (G.711 A-law)** - Payload type 8
- **telephone-event** - Payload type 101 (DTMF)

## Troubleshooting

### No Audio (Silent Calls)

**Symptoms:** Phones ring but no audio in either direction

**Causes:**
1. ❌ Wrong `external_ip` in config.yml
2. ❌ Firewall blocking RTP ports (10000-20000)
3. ❌ NAT issues (phones behind different NAT than PBX)

**Solutions:**
1. ✅ Set `external_ip` to actual server IP (192.168.1.14)
2. ✅ Open UDP ports 10000-20000 for RTP
3. ✅ Ensure phones and PBX are on same network

### One-Way Audio

**Symptoms:** Can hear one direction but not the other

**Causes:**
1. ❌ Asymmetric firewall rules
2. ❌ One phone not sending to correct RTP address

**Solutions:**
1. ✅ Check logs for RTP relay activity
2. ✅ Verify both phones received correct SDP
3. ✅ Check network routing between phones and PBX

### Phones Don't Ring

**Symptoms:** INVITE sent but no ringing

**Causes:**
1. ❌ Extension not registered
2. ❌ Wrong extension number
3. ❌ Network connectivity issue

**Solutions:**
1. ✅ Check extension registration status
2. ✅ Verify extension exists in config.yml
3. ✅ Check PBX logs for INVITE processing

## Testing with Zultys Phones

### Zultys ZIP 37G Configuration

1. **Server Settings:**
   - SIP Server: 192.168.1.14
   - SIP Port: 5060
   - Registration: Required

2. **Extension Settings:**
   - Extension: 1001 (or as configured)
   - Password: password1001 (from config.yml)
   - Name: Office Extension 1

3. **Network Settings:**
   - Ensure phone can reach 192.168.1.14
   - UDP ports 5060 (SIP) and 10000-20000 (RTP) must be accessible

### Test Procedure

1. Register both phones (1001 and 1002)
2. Check PBX logs: "Extension 1001 registered"
3. From 1001, dial 1002
4. Phone 1002 should ring
5. Answer on 1002
6. Both parties should hear each other
7. Hang up from either phone

## Log Analysis

### Successful Call Logs

```
INFO - Extension 1001 registered from ('192.168.1.100', 5060)
INFO - Extension 1002 registered from ('192.168.1.101', 5060)
INFO - INVITE request from ('192.168.1.100', 5060)
INFO - Caller RTP: 192.168.1.100:10000
INFO - RTP relay allocated on port 10000
INFO - Forwarded INVITE to 1002 at ('192.168.1.101', 5060)
INFO - Routing call test-123: 1001 -> 1002 via RTP relay 10000
INFO - Callee answered call test-123
INFO - Callee RTP: 192.168.1.101:10000
INFO - RTP relay connected for call test-123
INFO - Sent 200 OK to caller for call test-123
DEBUG - Forwarded ACK to callee for call test-123
DEBUG - Relayed 160 bytes: A->B
DEBUG - Relayed 160 bytes: B->A
```

## Advanced Features

The PBX supports additional features:
- Call recording
- Call parking
- Conference calls
- Voicemail
- Call queues
- Presence

See the main README.md for details on these features.
