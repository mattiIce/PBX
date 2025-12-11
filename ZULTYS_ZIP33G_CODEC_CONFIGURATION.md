# Zultys ZIP33G vs ZIP37G Codec Configuration

## Date
December 11, 2025

## Overview

This document explains the differences in codec configuration requirements between the Zultys ZIP33G and ZIP37G IP phones, specifically regarding PCMU/PCMA codec support.

## The Issue

The Zultys ZIP33G and ZIP37G phones have different codec configuration requirements:

- **ZIP37G**: Natively supports PCMU/PCMA codecs with minimal configuration
- **ZIP33G**: Requires explicit codec parameters for PCMU/PCMA to function properly

## Root Cause

The ZIP33G firmware lacks native codec defaults for PCMU and PCMA, requiring explicit configuration of:
- Sample rate
- Bitrate
- Packet time (ptime)

Without these parameters, the ZIP33G may:
1. Fail to properly negotiate PCMU/PCMA codecs
2. Incorrectly encode/decode audio streams
3. Experience one-way audio or no audio
4. Fall back to unsupported codecs

## Configuration Differences

### ZIP37G (Minimal Configuration Required)

```
# Basic codec configuration - phone uses internal defaults
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = 0
account.1.codec.1.priority = 1
account.1.codec.1.name = PCMU

account.1.codec.2.enable = 1
account.1.codec.2.payload_type = 8
account.1.codec.2.priority = 2
account.1.codec.2.name = PCMA
```

The ZIP37G will automatically apply:
- Sample rate: 8000 Hz (from internal defaults)
- Bitrate: 64 kbps (G.711 standard)
- Packet time: 20ms (from global RTP settings)

### ZIP33G (Explicit Configuration Required)

```
# Full codec configuration - all parameters must be specified
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = 0
account.1.codec.1.priority = 1
account.1.codec.1.name = PCMU
account.1.codec.1.sample_rate = 8000    # REQUIRED for ZIP33G
account.1.codec.1.bitrate = 64          # REQUIRED for ZIP33G
account.1.codec.1.ptime = 20            # REQUIRED for ZIP33G

account.1.codec.2.enable = 1
account.1.codec.2.payload_type = 8
account.1.codec.2.priority = 2
account.1.codec.2.name = PCMA
account.1.codec.2.sample_rate = 8000    # REQUIRED for ZIP33G
account.1.codec.2.bitrate = 64          # REQUIRED for ZIP33G
account.1.codec.2.ptime = 20            # REQUIRED for ZIP33G
```

## Parameter Explanations

### Sample Rate (`sample_rate`)
- **Value**: 8000 (Hz)
- **What it is**: Audio sampling frequency
- **Why 8000**: G.711 (PCMU/PCMA) uses 8 kHz sampling per specification
- **Impact if missing**: Incorrect audio decoding, distorted or no audio

### Bitrate (`bitrate`)
- **Value**: 64 (kbps)
- **What it is**: Data transmission rate for audio stream
- **Why 64**: G.711 codecs transmit 8-bit samples 8000 times/sec = 64 kbps
- **Impact if missing**: Bandwidth miscalculation, QoS issues

### Packet Time (`ptime`)
- **Value**: 20 (milliseconds)
- **What it is**: Duration of audio in each RTP packet
- **Why 20**: Industry standard (160 samples at 8kHz = 20ms)
- **Impact if missing**: Jitter, excessive packet overhead, or dropped frames

## Firmware Differences

### Why the Difference Exists

| Aspect | ZIP33G | ZIP37G |
|--------|--------|--------|
| **Firmware Generation** | Older | Newer |
| **Codec Engine** | Requires explicit config | Has built-in defaults |
| **Market Position** | Entry-level | Mid-range |
| **Release Date** | ~2015-2017 | ~2018-2020 |

The ZIP37G firmware was designed with better codec intelligence and default handling, eliminating the need for explicit codec parameter configuration.

## Symptoms of Missing Configuration

If PCMU/PCMA parameters are missing from ZIP33G provisioning:

### 1. Codec Negotiation Failure
```
SIP INVITE from ZIP33G:
m=audio 10000 RTP/AVP 0 8 9 101
a=rtpmap:0 PCMU
a=rtpmap:8 PCMA
```
Phone advertises codecs but can't use them properly.

### 2. One-Way Audio
- **Pattern**: Audio works in one direction only
- **QoS Shows**:
  ```
  ZIP33G→PBX:  MOS 0.00 (Bad) - No RTP received
  PBX→ZIP33G:  MOS 4.41 (Excellent)
  ```
- **Cause**: ZIP33G not encoding/sending audio correctly

### 3. No Audio Both Directions
- **Pattern**: Call connects but no audio either way
- **QoS Shows**:
  ```
  ZIP33G→PBX:  MOS 0.00 (Bad) - No RTP
  PBX→ZIP33G:  MOS 0.00 (Bad) - No RTP
  ```
- **Cause**: Complete codec negotiation/configuration failure

### 4. Distorted Audio
- **Pattern**: Audio present but garbled or robotic
- **Cause**: Incorrect sample rate causing resampling artifacts

## Verification

### Check Current Configuration

```bash
# Via phone web interface (if available)
http://<phone-ip>/config.txt

# Look for these lines:
account.1.codec.1.sample_rate = 8000
account.1.codec.1.bitrate = 64
account.1.codec.1.ptime = 20
```

### Test Audio Quality

1. **Make a test call** from ZIP33G to another extension
2. **Check QoS metrics** in Admin Panel → Call Quality
3. **Verify both directions** show MOS > 4.0

### Expected Results

**Before Fix (ZIP33G without parameters):**
```
Call: ext1001@192.168.1.100_a_to_b
MOS: 0.00 (Bad) ← Phone not encoding audio
Loss: 0.00%
Jitter: 0.0ms

Call: ext1001@192.168.1.100_b_to_a
MOS: 4.41 (Excellent) ← PBX audio working fine
Loss: 0.00%
Jitter: 0.1ms
```

**After Fix (ZIP33G with parameters):**
```
Call: ext1001@192.168.1.100_a_to_b
MOS: 4.38 (Excellent) ← Now working!
Loss: 0.00%
Jitter: 0.1ms

Call: ext1001@192.168.1.100_b_to_a
MOS: 4.41 (Excellent)
Loss: 0.00%
Jitter: 0.1ms
```

## Deployment

### Update ZIP33G Provisioning

1. **Edit the template**:
   ```bash
   vim provisioning_templates/zultys_zip33g.template
   ```

2. **Verify codec section has**:
   ```
   account.1.codec.1.sample_rate = 8000
   account.1.codec.1.bitrate = 64
   account.1.codec.1.ptime = 20
   
   account.1.codec.2.sample_rate = 8000
   account.1.codec.2.bitrate = 64
   account.1.codec.2.ptime = 20
   ```

3. **Restart provisioning service**:
   ```bash
   sudo systemctl restart pbx
   ```

4. **Reprovision phones**:
   - Option A: Reboot each ZIP33G phone
   - Option B: Use phone web interface to force re-provision
   - Option C: Wait for next auto-provision cycle (24 hours default)

### Verify Deployment

```bash
# Check template was updated
grep "sample_rate" provisioning_templates/zultys_zip33g.template

# Should output:
# account.1.codec.1.sample_rate = 8000
# account.1.codec.2.sample_rate = 8000
```

## Best Practices

### 1. Always Specify Codec Parameters for ZIP33G
Even if a parameter seems optional, include it for ZIP33G phones:
```
# Include all codec parameters
account.1.codec.1.sample_rate = 8000
account.1.codec.1.bitrate = 64
account.1.codec.1.ptime = 20
account.1.codec.1.name = PCMU
account.1.codec.1.payload_type = 0
account.1.codec.1.priority = 1
account.1.codec.1.enable = 1
```

### 2. Keep ZIP37G Configuration Simple
The ZIP37G doesn't need explicit codec parameters:
```
# Minimal config for ZIP37G
account.1.codec.1.name = PCMU
account.1.codec.1.payload_type = 0
account.1.codec.1.priority = 1
account.1.codec.1.enable = 1
```

### 3. Test After Provisioning Changes
Always verify audio quality after changing provisioning:
```bash
# Make test call
# Check Admin Panel → Call Quality
# Verify MOS scores > 4.0 in both directions
```

### 4. Document Phone-Specific Requirements
Maintain a matrix of phone model requirements:

| Phone Model | Codec Params Required | Notes |
|-------------|----------------------|-------|
| ZIP33G | ✅ Yes | Full explicit config |
| ZIP37G | ❌ No | Uses internal defaults |
| Yealink T46S | ❌ No | Modern firmware |
| Grandstream GXP2170 | ❌ No | Standards-compliant |

## Troubleshooting

### Issue: ZIP33G still has one-way audio after adding parameters

**Check:**
1. Phone actually reprovisioned (check phone config.txt)
2. Parameters have correct values (sample_rate=8000, not 8)
3. Firmware version supports these parameters
4. No firewall blocking RTP packets

**Solution:**
```bash
# Force phone to reprovision
# Via phone keypad: Menu → Settings → Auto Provision → Provision Now

# Or reboot phone
# Via SSH to PBX:
ssh admin@<phone-ip> 'reboot'
```

### Issue: Audio was working, broke after template update

**Cause**: Typo in codec configuration

**Check:**
```bash
# Verify exact parameter names
grep -n "codec\." provisioning_templates/zultys_zip33g.template

# Common typos:
# - "samplerate" instead of "sample_rate"
# - "birate" instead of "bitrate"  
# - "packet_time" instead of "ptime"
```

### Issue: Some ZIP33G phones work, others don't

**Cause**: Firmware version differences

**Solution:**
```bash
# Check firmware versions
# Phone keypad: Menu → Status → Firmware
# Upgrade any phones running firmware < 47.80

# Firmware upgrade process:
# 1. Download latest firmware from Zultys
# 2. Place in provisioning directory
# 3. Update template:
#    auto_provision.firmware.url = http://<server>/firmware.bin
# 4. Phones will auto-upgrade on next provision
```

## References

- [Phone Provisioning Guide](PHONE_PROVISIONING.md)
- [QoS Troubleshooting Guide](QOS_TROUBLESHOOTING_ONE_WAY_AUDIO.md)
- [Codec Negotiation Fix](CODEC_NEGOTIATION_FIX.md)
- [G.711 Codec Specification](https://www.itu.int/rec/T-REC-G.711)
- [RFC 3551 - RTP Profile for Audio/Video](https://tools.ietf.org/html/rfc3551)

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | Dec 11, 2025 | Initial documentation |
| 1.1 | Dec 11, 2025 | Added explicit codec parameters to ZIP33G template |

---

**Status**: ✅ Issue Resolved  
**Applies to**: Zultys ZIP33G phones only  
**Fix**: Add sample_rate, bitrate, and ptime to PCMU/PCMA codec configuration  
**ZIP37G**: No changes needed (natively supports codecs)
