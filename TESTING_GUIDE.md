# Testing Guide for Phone-to-Phone Audio Fix

## Problem Summary
You reported that with your Zultys ZIP 37G and other Zultys phones:
- ✅ Server IP is 192.168.1.14
- ✅ Phones register successfully
- ❌ When calling phone to phone, it's silent (no audio)
- ❌ The other phone rings but there's no audio in either direction

## What Was Fixed

The root cause was **missing SDP (Session Description Protocol) handling**. The PBX was not:
1. Parsing where phones wanted to send/receive RTP audio
2. Telling phones where to send their audio (to the PBX relay)
3. Setting up bidirectional audio relay between the two phones

### Changes Made

1. **Added SDP Support** - The PBX now:
   - Parses SDP from INVITE messages to learn phone RTP endpoints
   - Builds SDP to tell phones where to send audio (to PBX relay)
   - Properly negotiates codecs (PCMU, PCMA)

2. **Added RTP Relay** - The PBX now:
   - Allocates RTP ports for each call (from pool 10000-20000)
   - Receives audio from both phones
   - Forwards audio bidirectionally between them

3. **Fixed SIP Signaling** - The PBX now:
   - Forwards INVITE with proper SDP to callee
   - Returns 200 OK with proper SDP to caller
   - Forwards ACK to complete the handshake

4. **Added Configuration** - Set external IP:
   ```yaml
   server:
     external_ip: "192.168.1.14"
   ```

## How to Test

### Step 1: Verify Configuration

Check `config.yml` has the correct settings:

```yaml
server:
  sip_host: "0.0.0.0"          # Binds to all interfaces
  sip_port: 5060
  external_ip: "192.168.1.14"  # YOUR SERVER IP - phones will send RTP here
  rtp_port_range_start: 10000
  rtp_port_range_end: 20000
```

### Step 2: Start the PBX

```bash
cd /home/runner/work/PBX/PBX
python main.py
```

Expected output:
```
============================================================
InHouse PBX System v1.0.0
============================================================
2025-XX-XX XX:XX:XX - PBX - INFO - Loaded extension 1001 (Office Extension 1)
2025-XX-XX XX:XX:XX - PBX - INFO - Loaded extension 1002 (Office Extension 2)
2025-XX-XX XX:XX:XX - PBX - INFO - SIP server started on 0.0.0.0:5060
2025-XX-XX XX:XX:XX - PBX - INFO - PBX system started successfully
```

### Step 3: Configure Your Zultys Phones

**Phone 1 (Extension 1001):**
- SIP Server: 192.168.1.14
- SIP Port: 5060
- Extension/Username: 1001
- Password: password1001

**Phone 2 (Extension 1002):**
- SIP Server: 192.168.1.14
- SIP Port: 5060
- Extension/Username: 1002
- Password: password1002

### Step 4: Register Phones

Watch the PBX logs for:
```
INFO - Extension 1001 registered from ('192.168.1.X', 5060)
INFO - Extension 1002 registered from ('192.168.1.Y', 5060)
```

### Step 5: Make a Test Call

1. **From phone 1001, dial: 1002**

2. **Expected PBX logs:**
   ```
   INFO - INVITE request from ('192.168.1.X', 5060)
   INFO - Caller RTP: 192.168.1.X:XXXXX
   INFO - RTP relay allocated on port 10000
   INFO - Forwarded INVITE to 1002 at ('192.168.1.Y', 5060)
   INFO - Routing call xxx: 1001 -> 1002 via RTP relay 10000
   ```

3. **Phone 1002 should ring**

4. **Expected PBX logs (ringing):**
   ```
   INFO - Callee ringing for call xxx
   ```

5. **Answer on phone 1002**

6. **Expected PBX logs (answer):**
   ```
   INFO - Callee answered call xxx
   INFO - Callee RTP: 192.168.1.Y:YYYYY
   INFO - RTP relay connected for call xxx
   INFO - Sent 200 OK to caller for call xxx
   DEBUG - Forwarded ACK to callee for call xxx
   ```

7. **Expected audio behavior:**
   - ✅ **Both phones should hear each other**
   - ✅ Audio should be clear (G.711 codec)
   - ✅ Bidirectional audio (both can talk and hear)

8. **During the call, you should see:**
   ```
   DEBUG - Relayed 160 bytes: A->B
   DEBUG - Relayed 160 bytes: B->A
   DEBUG - Relayed 160 bytes: A->B
   DEBUG - Relayed 160 bytes: B->A
   ```

### Step 6: End the Call

Hang up from either phone. Expected logs:
```
INFO - BYE request from ('192.168.1.X', 5060)
INFO - Ending call xxx
INFO - Released RTP relay for call xxx
```

## Troubleshooting

### Issue: Still No Audio

**Check 1: Network Configuration**
```bash
# On PBX server, verify IP address
ip addr show

# Verify UDP ports are open
sudo netstat -ulnp | grep python
# Should show port 5060 and ports from 10000-20000
```

**Check 2: Configuration**
```bash
# Verify external_ip is set correctly
grep external_ip config.yml
# Should show: external_ip: "192.168.1.14"
```

**Check 3: Phone Configuration**
- Ensure phones are pointed to 192.168.1.14:5060
- Ensure phones are on same network (192.168.1.x)
- Check phones can ping 192.168.1.14

**Check 4: Firewall**
```bash
# If using firewall, open ports
sudo ufw allow 5060/udp     # SIP signaling
sudo ufw allow 10000:20000/udp  # RTP media
```

### Issue: One-Way Audio

**Symptoms:** Can hear in one direction only

**Check:** Look for asymmetric RTP relay logs:
```
DEBUG - Relayed 160 bytes: A->B
DEBUG - Relayed 160 bytes: A->B
# If you only see A->B and never B->A, phone B isn't sending
```

**Solutions:**
1. Check phone B's network settings
2. Verify phone B received correct SDP (check logs)
3. Test network connectivity from phone B to 192.168.1.14

### Issue: Phones Don't Ring

**Check 1:** Verify extension is registered:
```
# In logs, look for:
INFO - Extension 1002 registered from ...
```

**Check 2:** Verify extension exists in config.yml:
```bash
grep -A 3 "number: \"1002\"" config.yml
```

**Check 3:** Enable DEBUG logging in config.yml:
```yaml
logging:
  level: "DEBUG"  # Change from INFO to DEBUG
```

## Expected Call Flow

```
Phone 1001              PBX (192.168.1.14)              Phone 1002
(192.168.1.100)         RTP Port: 10000             (192.168.1.101)
    |                        |                             |
    | INVITE                 |                             |
    | SDP: 192.168.1.100:X   |                             |
    |----------------------->|                             |
    |                        | INVITE                      |
    |                        | SDP: 192.168.1.14:10000     |
    |                        |---------------------------->|
    |                        |                             |
    |                 180 Ringing                   180 Ringing
    |<-----------------------|<----------------------------|
    |                        |                             |
    |                        |                      200 OK |
    |                        | SDP: 192.168.1.101:Y        |
    |                        |<----------------------------|
    |                 200 OK |                             |
    | SDP: 192.168.1.14:10000|                             |
    |<-----------------------|                             |
    |                        |                             |
    | ACK                    |                             |
    |----------------------->| ACK                         |
    |                        |---------------------------->|
    |                        |                             |
    | RTP Audio              |              RTP Audio      |
    |=======================>|============================>|
    |                        |                             |
    |              RTP Audio |              RTP Audio      |
    |<======================|<============================|
    |                        |                             |
```

## Verification Checklist

- [ ] PBX starts without errors
- [ ] Both phones register successfully
- [ ] Call from 1001 to 1002 makes phone ring
- [ ] Answering the call connects both parties
- [ ] **Audio works in BOTH directions** ← Main fix!
- [ ] Call can be ended from either phone
- [ ] RTP relay logs show bidirectional traffic

## Additional Notes

### Supported Codecs
Your Zultys phones will negotiate one of:
- **PCMU (G.711 μ-law)** - Most common in North America
- **PCMA (G.711 A-law)** - Most common in Europe
- **telephone-event** - For DTMF tones

### Network Requirements
- All devices on same subnet (192.168.1.0/24) is simplest
- No NAT between phones and PBX
- UDP ports not blocked by firewalls
- Reasonable latency (<100ms) for good voice quality

### Log Levels
- **INFO** - Normal operation, shows call flow
- **DEBUG** - Detailed, shows every RTP packet relay
- **WARNING** - Problems but system continues
- **ERROR** - Serious issues

## Getting Help

If audio still doesn't work after following this guide:

1. **Collect logs** with DEBUG level enabled
2. **Test network** connectivity between phones and PBX
3. **Verify** SDP is being sent correctly (check logs for "RTP:" entries)
4. **Check** that RTP relay shows bidirectional traffic

The fix is in the code - it's now a matter of configuration and network setup!
