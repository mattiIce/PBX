# DTMF Payload Type Configuration Guide

> **⚠️ DEPRECATED**: This guide has been consolidated into [DTMF_CONFIGURATION_GUIDE.md](DTMF_CONFIGURATION_GUIDE.md). Please refer to the consolidated guide for the most up-to-date information on DTMF configuration and troubleshooting.

## Quick Start

**Not sure which payload type to use?** Run the interactive selector tool:

```bash
python scripts/dtmf_payload_selector.py
```

This tool will ask a few questions and recommend the best payload type for your setup.

**Or use the decision tree below** to choose manually.

---

## Overview

This guide explains how to configure the RFC2833 DTMF payload type for IP phones, particularly relevant for Zultys ZIP33G phones which may experience DTMF issues with the default payload type 101.

## Background

### What is RFC2833?

RFC 2833 defines how DTMF (Dual-Tone Multi-Frequency) digits are transmitted as RTP events over VoIP networks. This method is superior to in-band DTMF because:

- **Codec Independent**: Works with any audio codec (G.711, G.729, Opus, etc.)
- **More Reliable**: Not affected by codec compression or packet loss
- **Lower Latency**: Direct event transmission without audio processing
- **Industry Standard**: Supported by all modern SIP phones and PBX systems

### Payload Type Explained

In RTP (Real-time Transport Protocol), each type of media has a "payload type" number:

- **0**: PCMU (G.711 μ-law audio)
- **8**: PCMA (G.711 A-law audio)
- **9**: G.722 (Wideband HD audio)
- **101**: telephone-event (RFC2833 DTMF) - **Standard default**
- **96-127**: Dynamic payload types (can be used for telephone-event)

### The Problem

Some phone models or network configurations may have conflicts with payload type 101:

1. **SIP Provider Requirements**: Some carriers require specific payload types
2. **Phone Firmware Issues**: Certain phone firmware versions may have bugs with payload type 101
3. **Network Equipment**: Some SBCs or firewalls may filter payload type 101
4. **Codec Conflicts**: In rare cases, payload type 101 may conflict with proprietary codecs

### Symptoms of Payload Type Issues

If you're experiencing DTMF problems, you may see:

- DTMF digits not recognized in voicemail or auto-attendant
- Intermittent DTMF detection (works sometimes, fails other times)
- One-way DTMF (phone can send, but PBX can't receive, or vice versa)
- Phantom DTMF digits (digits detected that weren't pressed)

## Configuration

### Quick Payload Type Selector

**Use this decision tree to choose the right payload type:**

```
┌─────────────────────────────────────────────────────┐
│ Is DTMF working with payload type 101?              │
└────────────┬────────────────────────────────────────┘
             │
      ┌──────┴──────┐
      │    YES      │                 NO
      │             │                  │
      │  Keep 101   │         ┌────────┴────────┐
      │  (standard) │         │ Try these next: │
      └─────────────┘         └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
              ┌─────▼─────┐      ┌────▼────┐      ┌─────▼─────┐
              │ Step 1:   │      │ Step 2: │      │ Step 3:   │
              │ Try 100   │──┬──>│ Try 102 │──┬──>│ Try 96    │
              │ (Cisco)   │  │   │(Carrier)│  │   │(Generic)  │
              └───────────┘  │   └─────────┘  │   └───────────┘
                             │                │
                      ┌──────▼────────────────▼───────┐
                      │ Still not working?            │
                      │ • Check SIP provider docs     │
                      │ • Try 121 (Polycom)           │
                      │ • Switch to SIP INFO method   │
                      └───────────────────────────────┘
```

### Payload Type Reference Guide

| Payload Type | Use Case | When to Use | Compatibility |
|--------------|----------|-------------|---------------|
| **101** | RFC2833 Standard | **Default - Start here** | Most phones, most providers |
| **100** | Cisco/Alternative | Cisco systems, some providers | Cisco, Grandstream, some Yealink |
| **102** | Carrier Alternative | Required by specific carriers | Verizon, AT&T, some SIP trunks |
| **96** | Generic Fallback | When 100/101/102 don't work | Universal (first dynamic type) |
| **121** | Polycom Specific | Polycom phones with issues | Polycom VVX series |

### Step-by-Step Troubleshooting

**Step 1: Verify the symptom**
```bash
# Test DTMF by calling voicemail
# Dial *<extension> and try entering PIN
# Note what happens:
# - No response? → Try alternative payload type
# - Wrong digits detected? → Try alternative payload type
# - Works sometimes? → Network/timing issue (not payload type)
```

**Step 2: Try alternative payload types in this order**

1. **Start with 100** (most common alternative)
   ```yaml
   features:
     dtmf:
       payload_type: 100
   ```
   Restart PBX, reprovision phones, test

2. **If 100 fails, try 102** (carrier alternative)
   ```yaml
   features:
     dtmf:
       payload_type: 102
   ```
   Restart PBX, reprovision phones, test

3. **If 102 fails, try 96** (generic fallback)
   ```yaml
   features:
     dtmf:
       payload_type: 96
   ```
   Restart PBX, reprovision phones, test

**Step 3: Check SIP provider requirements**
```bash
# Contact your SIP provider and ask:
# "What RFC2833 payload type do you require for DTMF?"
# Common answers:
# - "We support 101" → Use 101
# - "Use 100" → Use 100
# - "We don't support RFC2833" → Switch to SIP INFO method
```

**Step 4: Last resort - Switch to SIP INFO**

If no payload type works, your provider may not support RFC2833:
```bash
# Edit phone template (e.g., zultys_zip33g.template)
# Change:
account.1.dtmf.type = 1          # Was 2, now 1 for RFC2833
# To:
account.1.dtmf.type = 2          # Back to SIP INFO (more compatible)
```

## Configuration

### Global Configuration (All Phones)

Edit `config.yml` to set the DTMF payload type for all phones:

```yaml
features:
  dtmf:
    payload_type: 101  # Change this to alternative value if needed (96-127)
```

**Common Alternatives:**
- `100` - Used by some Cisco systems
- `102` - Alternative used by some SIP providers
- `96` - First dynamic payload type, sometimes used as alternative
- `101` - Standard (default, recommended unless issues exist)

### Per-Phone Configuration

The payload type is automatically applied to all provisioning templates via the `{{DTMF_PAYLOAD_TYPE}}` placeholder.

**Affected Templates:**
- `provisioning_templates/zultys_zip33g.template`
- `provisioning_templates/zultys_zip37g.template`
- `provisioning_templates/yealink_t28g.template`
- `provisioning_templates/yealink_t46s.template`

**Template Line:**
```
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}
```

### Manual Override for Specific Phone

If you need a specific phone to use a different payload type:

1. Edit the template file directly (e.g., `zultys_zip33g.template`)
2. Change `{{DTMF_PAYLOAD_TYPE}}` to a hardcoded value like `100`
3. Restart the PBX to regenerate configs
4. Reprovision the phone

**Example:**
```
account.1.dtmf.dtmf_payload = 100  # Hardcoded for this phone model
```

## Testing and Verification

### 1. Check Phone Configuration

After reprovisioning, verify the phone received the correct payload type:

```bash
# Access phone web interface (if available)
http://<phone-ip>/config.txt

# Look for:
account.1.dtmf.dtmf_payload = 101  # (or your configured value)
```

### 2. Test DTMF Functionality

**Voicemail Test:**
```
1. Dial *<your-extension> (e.g., *1501)
2. Enter your PIN when prompted
3. Verify menu options are recognized
```

**Auto-Attendant Test:**
```
1. Dial 0 (auto-attendant)
2. Press extension numbers
3. Verify immediate response without delay
```

### 3. Monitor PBX Logs

Watch for DTMF detection in logs:

```bash
tail -f logs/pbx.log | grep -i dtmf

# Should see messages like:
# INFO - RFC 2833 DTMF event completed: 5 (duration: 160)
# INFO - Detected DTMF from out-of-band signaling: 7
```

### 4. Packet Capture Analysis

For advanced troubleshooting, capture RTP packets:

```bash
# On PBX server
sudo tcpdump -i any -w dtmf_test.pcap 'udp port 10000-20000'

# Make test call and press DTMF digits
# Stop capture (Ctrl+C)

# Analyze with Wireshark:
# 1. Open dtmf_test.pcap in Wireshark
# 2. Filter: rtp
# 3. Look for packets with your configured payload type
# 4. Verify RTP Event packets are present
```

## Deployment Process

### Step 1: Update Configuration

```bash
# Edit config.yml
vim config.yml

# Change features.dtmf.payload_type to desired value
features:
  dtmf:
    payload_type: 100  # Example: change from 101 to 100
```

### Step 2: Restart PBX

```bash
# Restart PBX service
sudo systemctl restart pbx

# Or restart main process
sudo ./main.py
```

### Step 3: Reprovision Phones

**Option A: Automatic (all phones)**
```bash
# Phones will auto-reprovision on next check (24 hours default)
# Or reboot all phones to force immediate reprovision
```

**Option B: Manual (specific phone)**
```
# On phone keypad:
Menu → Settings → Auto Provision → Provision Now

# Or reboot phone:
Menu → Settings → Reboot
```

### Step 4: Verify

Test DTMF functionality on affected phones (see Testing section above).

## Troubleshooting

### Issue: Changed payload type but DTMF still doesn't work

**Possible Causes:**

1. **Phone not reprovisioned**
   ```bash
   # Force phone to fetch new config
   # Reboot phone or use phone menu to reprovision
   ```

2. **SDP negotiation mismatch**
   ```bash
   # Check PBX logs for SDP offer:
   grep "SDP" logs/pbx.log
   
   # Should show new payload type:
   # m=audio 10000 RTP/AVP 0 8 9 100
   # a=rtpmap:100 telephone-event/8000
   ```

3. **Phone firmware doesn't support alternative payload type**
   ```
   # Try a different payload type (e.g., 96, 100, 102)
   # Or update phone firmware
   ```

### Issue: Some phones work, others don't

**Solution:**
```bash
# Different phone models may need different payload types
# Create per-model configuration:

# For ZIP33G phones:
vim provisioning_templates/zultys_zip33g.template
account.1.dtmf.dtmf_payload = 100

# For Yealink phones:
vim provisioning_templates/yealink_t46s.template
account.1.dtmf.dtmf_payload = 101

# Keep standard {{DTMF_PAYLOAD_TYPE}} for most phones
```

### Issue: DTMF works in one direction only

**Check:**
```bash
# 1. Verify phone can send DTMF
#    Check PBX logs for "RFC 2833 DTMF event completed"

# 2. Verify PBX can send DTMF
#    Test by having PBX play DTMF to phone (rare scenario)

# 3. Check RTP firewall rules
#    Ensure RTP ports (10000-20000) are bidirectional
```

## Best Practices

### 1. Use Standard Payload Type 101 Unless Issues Exist

The default payload type 101 is the RFC standard and most widely supported:

```yaml
features:
  dtmf:
    payload_type: 101  # Recommended default
```

**Only change if:**
- Experiencing documented DTMF issues
- Required by SIP provider
- Phone vendor recommends alternative

### 2. Document Phone-Specific Requirements

Maintain a compatibility matrix:

| Phone Model | Recommended Payload Type | Notes |
|-------------|-------------------------|-------|
| Zultys ZIP33G | 101 (default) | Works with SIP INFO primary |
| Zultys ZIP37G | 101 (default) | Works with SIP INFO primary |
| Yealink T46S | 101 (default) | Standard RFC2833 |
| Yealink T28G | 101 (default) | Standard RFC2833 |
| Cisco SPA504G | 100 | Cisco-specific requirement |

### 3. Test After Changes

Always test DTMF functionality after changing payload types:

```bash
# 1. Voicemail access test
# 2. Auto-attendant navigation test
# 3. Conference room PIN entry test
# 4. Check PBX logs for DTMF events
```

### 4. Monitor for Regressions

After deployment, monitor for DTMF-related issues:

```bash
# Check for DTMF failures in logs
grep -i "dtmf.*fail\|dtmf.*error" logs/pbx.log

# Monitor voicemail access failures
grep -i "voicemail.*fail\|invalid pin" logs/pbx.log
```

## Technical Details

### SDP Negotiation with Alternative Payload Types

When PBX makes a call, it sends an SDP offer with the configured payload type:

```
v=0
o=pbx 1234567890 0 IN IP4 192.168.1.14
s=PBX Call
c=IN IP4 192.168.1.14
t=0 0
m=audio 10000 RTP/AVP 0 8 9 100
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:9 G722/8000
a=rtpmap:100 telephone-event/8000
a=fmtp:100 0-16
a=sendrecv
```

Note: Payload type `100` instead of standard `101`.

### RFC 2833 Packet Structure

The payload type only affects the RTP header, not the RFC 2833 event format:

```
RTP Header:
- Payload Type: <configured value> (e.g., 100)

RFC 2833 Payload (4 bytes):
- Event: 0-15 (DTMF digit)
- End bit: 0 or 1
- Volume: 0-63
- Duration: timestamp units
```

### Compatibility Notes

**Standards Compliance:**
- Payload types 96-127 are designated for "dynamic" use (RFC 3551)
- Any value in this range can be used for telephone-event
- Both endpoints must agree on the payload type via SDP negotiation

**Phone Compatibility:**
- Modern phones support any dynamic payload type
- Older phones may be hardcoded to expect 101
- Check phone documentation or test before deploying

## Related Documentation

- [RFC 2833 Implementation Guide](RFC2833_IMPLEMENTATION_GUIDE.md)
- [Zultys DTMF Troubleshooting](ZULTYS_DTMF_TROUBLESHOOTING.md)
- [Complete DTMF Implementation Summary](COMPLETE_DTMF_IMPLEMENTATION_SUMMARY.md)
- [SIP INFO DTMF Guide](SIP_INFO_DTMF_GUIDE.md)
- [Phone Provisioning Guide](PHONE_PROVISIONING.md)

## Support

If you continue to experience DTMF issues after configuring the payload type:

1. **Check Phone Firmware**: Ensure phone firmware is up to date
2. **Review Network Configuration**: Check for SIP ALG, firewalls, or SBCs
3. **Try Alternative DTMF Method**: Switch to SIP INFO in phone template
4. **Capture Traffic**: Use tcpdump/Wireshark to analyze RTP packets
5. **Contact Vendor**: Some issues may require vendor firmware fixes

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | Dec 12, 2024 | Initial documentation for configurable DTMF payload types |

---

**Status**: ✅ Feature Complete  
**Applies to**: All IP phones  
**Default**: Payload type 101 (RFC standard)  
**Configurable**: Yes, via config.yml
