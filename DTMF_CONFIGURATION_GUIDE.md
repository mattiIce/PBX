# DTMF Configuration and Troubleshooting Guide

**Last Updated**: December 18, 2024  
**Version**: 2.0

## Overview

This comprehensive guide covers DTMF (Dual-Tone Multi-Frequency) configuration, implementation, and troubleshooting for the PBX system. DTMF is critical for IVR navigation, voicemail access, and interactive menu systems.

## Table of Contents

1. [DTMF Methods Overview](#dtmf-methods-overview)
2. [RFC 2833 Implementation](#rfc-2833-implementation)
3. [SIP INFO DTMF Support](#sip-info-dtmf-support)
4. [In-Band DTMF Detection](#in-band-dtmf-detection)
5. [Payload Type Configuration](#payload-type-configuration)
6. [Zultys Phone Configuration](#zultys-phone-configuration)
7. [Troubleshooting](#troubleshooting)

---

## DTMF Methods Overview

The PBX supports three methods for DTMF transmission:

| Method | Payload Type | Reliability | Codec Independence | Status |
|--------|--------------|-------------|-------------------|--------|
| **RFC 2833 (RTP Events)** | 101 (configurable) | Highest | ✅ Yes | ✅ Complete |
| **SIP INFO** | SIP signaling | High | ✅ Yes | ✅ Complete |
| **In-Band Audio** | Audio (0, 8) | Medium | ❌ No | ✅ Complete |

### Method Selection Priority

The PBX uses the following priority order:

1. **RFC 2833** - First choice (most reliable, widely supported)
2. **SIP INFO** - Fallback for codec compatibility issues
3. **In-Band Audio** - Final fallback using Goertzel algorithm

---

## RFC 2833 Implementation

**Status**: ✅ **FULLY IMPLEMENTED**  
**Date**: December 9, 2024

### Overview

RFC 2833 defines RTP Payload for DTMF Digits, Telephony Tones and Signals using payload type 101 (configurable). This is the industry-standard method for DTMF transmission in VoIP.

### Why RFC 2833?

1. **Most Reliable**: Events sent out-of-band in separate RTP packets
2. **Codec Independent**: Works with any audio codec (G.711, G.729, Opus, etc.)
3. **Industry Standard**: Supported by all major phone manufacturers
4. **Low Latency**: Events transmitted in real-time over RTP stream
5. **Redundant Transmission**: End packets sent 3 times for reliability

### Packet Structure

RFC 2833 uses 4-byte payloads in RTP packets:

```
0                   1                   2                   3
0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     event     |E|R| volume    |          duration             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**Fields**:
- **event** (8 bits): DTMF digit code (0-15)
- **E** (1 bit): End bit (1 = final packet for this event)
- **R** (1 bit): Reserved (must be 0)
- **volume** (6 bits): Power level (0 = loudest, 63 = silence)
- **duration** (16 bits): Event duration in timestamp units (8kHz sample rate)

### Event Codes

| Digit | Event Code | Digit | Event Code |
|-------|-----------|-------|-----------|
| 0 | 0 | 8 | 8 |
| 1 | 1 | 9 | 9 |
| 2 | 2 | * | 10 |
| 3 | 3 | # | 11 |
| 4 | 4 | A | 12 |
| 5 | 5 | B | 13 |
| 6 | 6 | C | 14 |
| 7 | 7 | D | 15 |

### Implementation Components

#### RFC 2833 Event Packet Handler (`pbx/rtp/rfc2833.py`)

**Classes**:

##### `RFC2833EventPacket`
Encodes and decodes RFC 2833 event packets.

```python
from pbx.rtp.rfc2833 import RFC2833EventPacket

# Create event packet
packet = RFC2833EventPacket('5', end=False, volume=10, duration=160)

# Pack to binary format
data = packet.pack()  # Returns 4 bytes

# Unpack from binary
packet = RFC2833EventPacket.unpack(data)
digit = packet.get_digit()  # Returns '5'
```

##### `RFC2833Receiver`
Receives and processes RFC 2833 event packets.

```python
from pbx.rtp.rfc2833 import RFC2833Receiver

# Initialize receiver
receiver = RFC2833Receiver(callback=handle_dtmf, payload_type=101)

# Process RTP packet
receiver.process_rtp_packet(rtp_payload, payload_type, timestamp, marker)
```

##### `RFC2833Sender`
Sends RFC 2833 event packets.

```python
from pbx.rtp.rfc2833 import RFC2833Sender

# Initialize sender
sender = RFC2833Sender(rtp_session, payload_type=101)

# Send DTMF digit
sender.send_dtmf('5', duration_ms=160)
```

### Configuration

```yaml
features:
  dtmf:
    payload_type: 101  # RFC 2833 payload type (96-127)
    method: rfc2833    # Primary DTMF method
    duration: 160      # Event duration in ms
```

### SDP Negotiation

The PBX includes RFC 2833 in SDP offers:

```
m=audio 10000 RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-15
```

---

## SIP INFO DTMF Support

**Status**: ✅ **FULLY IMPLEMENTED**

### Overview

SIP INFO provides an alternative DTMF signaling method using out-of-band SIP messages. This is particularly useful when codec compatibility issues exist.

### Background: Codec Mismatch Issue

SIP INFO solves problems when phones use codecs the PBX doesn't support:

1. Phone sends INVITE with G.729 in SDP
2. PBX answers with 200 OK offering only G.711 (PCMU/PCMA)
3. Phone can't find compatible codec → sends ACK + BYE immediately
4. RTP handlers continue playing audio (race condition)

**Solution**: Switch phone to use SIP INFO for DTMF, which works independently of audio codec.

### Implementation Details

#### SIP Server (`pbx/sip/server.py`)

Added `_handle_info()` method to process SIP INFO requests:

```python
def _handle_info(self, message, addr):
    """Handle INFO request (typically used for DTMF signaling)"""
    # Parse DTMF from message body
    # Format: Signal=1\nDuration=160
    if 'dtmf' in content_type.lower():
        # Extract digit and queue for processing
        self.pbx_core.handle_dtmf_info(call_id, dtmf_digit)
```

#### SIP INFO Message Format

```
INFO sip:voicemail@pbx.example.com SIP/2.0
Call-ID: abc123...
Content-Type: application/dtmf-relay
Content-Length: 24

Signal=5
Duration=160
```

#### PBX Core (`pbx/core/pbx.py`)

Added `handle_dtmf_info()` method with priority queue:

```python
def handle_dtmf_info(self, call_id, dtmf_digit):
    """Queue DTMF digits received via SIP INFO for IVR processing"""
    call = self.call_manager.get_call(call_id)
    if not hasattr(call, 'dtmf_info_queue'):
        call.dtmf_info_queue = []
    call.dtmf_info_queue.append(dtmf_digit)
```

### Configuration

Enable SIP INFO fallback in phone provisioning templates:

```ini
# DTMF Configuration
account.1.dtmf_mode = RFC2833                  # Primary method
account.1.dtmf_sip_info_fallback = 1           # Enable SIP INFO fallback
```

Or configure phones to use SIP INFO as primary method:

```ini
account.1.dtmf_mode = SIP_INFO                 # Primary method: SIP INFO
```

### When to Use SIP INFO

- ✅ Codec compatibility issues (e.g., G.729 phone with G.711-only PBX)
- ✅ RFC 2833 payload type conflicts
- ✅ Network equipment filtering RTP events
- ✅ Phone firmware issues with RFC 2833

---

## In-Band DTMF Detection

**Status**: ✅ **FULLY IMPLEMENTED**

### Overview

In-band DTMF detection uses the Goertzel algorithm to detect DTMF tones embedded in the audio RTP stream. This is the most universal method but least reliable.

### Characteristics

- **Pros**: 
  - ✅ Universal compatibility
  - ✅ No special phone configuration needed
  - ✅ Works with any codec that preserves audio
- **Cons**:
  - ❌ Affected by codec compression (especially G.729)
  - ❌ Audio quality issues can cause false detections
  - ❌ Higher CPU usage for tone detection
  - ❌ Latency in detection

### Implementation

The PBX uses the Goertzel algorithm to detect DTMF tones in PCM audio:

```python
from pbx.features.dtmf_detector import DTMFDetector

# Initialize detector
detector = DTMFDetector(sample_rate=8000)

# Process audio samples
digit = detector.process_samples(audio_samples)
if digit:
    handle_dtmf(digit)
```

### When to Use In-Band

- ✅ As automatic fallback when other methods unavailable
- ✅ Legacy systems without RFC 2833 or SIP INFO support
- ⚠️ Not recommended as primary method

---

## Payload Type Configuration

### Overview

RFC 2833 DTMF uses an RTP payload type to identify telephone-event packets. While 101 is the standard, some scenarios require alternative payload types.

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
| **96** | Generic Dynamic | Generic fallback | Universal dynamic range |
| **121** | Polycom Standard | Polycom phones | Polycom VVX series |

### Configuration

#### Global Configuration (config.yml)

```yaml
features:
  dtmf:
    payload_type: 101  # 96-127 (dynamic range)
```

#### Provisioning Template

Templates use placeholder for automatic substitution:

```ini
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}
```

The system automatically replaces `{{DTMF_PAYLOAD_TYPE}}` with the configured value.

### Changing Payload Type

1. **Edit config.yml**:
   ```yaml
   features:
     dtmf:
       payload_type: 100  # Change from 101 to 100
   ```

2. **Restart PBX** to apply changes

3. **Re-provision phones** to update their configuration

4. **Test DTMF** by accessing voicemail or auto-attendant

### Interactive Selector Tool

**Not sure which payload type to use?** Run the interactive selector:

```bash
python scripts/dtmf_payload_selector.py
```

This tool asks questions and recommends the best payload type for your setup.

### Symptoms of Payload Type Issues

If you're experiencing DTMF problems, you may see:

- DTMF digits not recognized in voicemail or auto-attendant
- Intermittent DTMF detection (works sometimes, fails other times)
- One-way DTMF (phone can send, but PBX can't receive, or vice versa)
- Phantom DTMF digits (digits detected that weren't pressed)

### Troubleshooting Steps

1. **Verify Configuration**: Check `config.yml` and phone templates
2. **Check SIP Traces**: Use `tcpdump` or Wireshark to verify payload type in SDP
3. **Test with Standard**: Try payload type 101 first
4. **Try Alternatives**: If 101 fails, try 100, 102, 96 in order
5. **Switch Method**: Consider SIP INFO if RFC 2833 continues to fail

---

## Zultys Phone Configuration

### ZIP33G vs ZIP37G DTMF Differences

**Date**: December 11, 2025

#### ZIP33G DTMF Requirements

The Zultys ZIP33G requires **explicit DTMF configuration** in provisioning templates:

```ini
# DTMF Configuration for ZIP33G
account.1.dtmf_mode = RFC2833                  # Primary method: RFC2833
account.1.dtmf_payload_type = 101              # Payload type 101
account.1.dtmf_duration = 160                  # 160ms duration
account.1.dtmf_sip_info_fallback = 1           # Enable SIP INFO fallback
```

#### ZIP37G DTMF Requirements

The ZIP37G works with simpler configuration:

```ini
# DTMF Configuration for ZIP37G
account.1.dtmf_mode = RFC2833                  # Primary method
account.1.dtmf_payload_type = 101              # Payload type
```

### Common Issues and Solutions

#### Issue 1: False BYE (Firmware Bug)

**Symptom**: Call connects but immediately disconnects before hearing prompts

**Root Cause**: ZIP33G sends premature BYE 0.15 seconds after ACK, then continues with audio and DTMF

**PCAP Evidence**:
```
Frame 139: INVITE to *1537
Frame 140: 200 OK from PBX  
Frame 142: ACK from phone
Frame 143: BYE from phone (CSeq 6) - FALSE BYE at t=6.13s
Frames 592-724: SIP INFO messages with DTMF at t=10.8s-12.9s
Frame 1087: BYE from phone (CSeq 7) - REAL BYE at t=18.89s
```

**Solution**: PBX implements false BYE workaround:
- Ignores first BYE within 2 seconds of call answer for voicemail calls
- Keeps call active for IVR processing
- Honors subsequent BYE requests normally

See `VOICEMAIL_FALSE_BYE_WORKAROUND.md` for details.

#### Issue 2: DTMF Not Recognized

**Symptom**: Can hear voicemail prompts but keypad presses are ignored

**Root Cause**: Missing or incorrect DTMF configuration in provisioning template

**Solution**: 
1. Verify DTMF configuration in template
2. Ensure RFC2833 is enabled
3. Enable SIP INFO fallback
4. Re-provision phone

#### Issue 3: Delayed DTMF Response

**Symptom**: Significant delay between pressing keys and system response

**Root Cause**: In-band detection being used instead of RFC 2833 or SIP INFO

**Solution**:
1. Verify phone is sending RFC 2833 events (check SIP traces)
2. Confirm payload type matches between phone and PBX
3. Enable SIP INFO if RFC 2833 fails
4. Check network for packet loss or jitter

### Provisioning Template Best Practices

#### Complete DTMF Configuration

Include all DTMF parameters in Zultys templates:

```ini
# Complete DTMF Configuration
account.1.dtmf_mode = RFC2833                  # Primary: RFC2833
account.1.dtmf_payload_type = {{DTMF_PAYLOAD_TYPE}}  # From config.yml
account.1.dtmf_duration = 160                  # 160ms duration
account.1.dtmf_sip_info_fallback = 1           # Enable SIP INFO fallback
account.1.dtmf_inband_enable = 0               # Disable in-band (not reliable)
```

#### Testing After Provisioning

1. **Re-provision phone** after template changes
2. **Test voicemail access**: Dial `*<extension>`
3. **Test PIN entry**: Enter voicemail PIN
4. **Test menu navigation**: Press digits to navigate menus
5. **Check SIP traces**: Verify DTMF method in use

---

## Troubleshooting

### Common DTMF Problems

#### Problem 1: No DTMF Detected

**Symptoms**:
- Phone keypad presses have no effect
- IVR menus don't respond
- Voicemail PIN entry fails

**Diagnostic Steps**:

1. **Check DTMF Method**:
   ```bash
   # Capture SIP/RTP traffic
   tcpdump -i any -s 0 -w /tmp/dtmf_test.pcap port 5060 or portrange 10000-20000
   
   # Look for:
   # - RFC 2833: RTP packets with payload type 101
   # - SIP INFO: INFO messages with application/dtmf-relay
   # - In-band: Only audio RTP packets
   ```

2. **Verify Configuration**:
   ```bash
   # Check PBX configuration
   grep -A5 "dtmf:" config.yml
   
   # Check phone provisioning
   grep "dtmf" provisioning_templates/zultys_zip33g.template
   ```

3. **Test Each Method**:
   - Test with RFC 2833 (payload type 101)
   - Test with RFC 2833 (payload type 100)
   - Test with SIP INFO
   - Test with in-band (last resort)

**Solutions**:
- Enable debug logging: `DEBUG_VM_PIN=true` in `.env`
- Check `logs/vm_ivr.log` for DTMF events
- Verify payload type matches between phone and PBX
- Try alternative DTMF method

#### Problem 2: Intermittent DTMF

**Symptoms**:
- DTMF works sometimes, fails other times
- Some digits detected, others missed
- Phantom digits appear

**Causes**:
- Network packet loss
- Jitter or delay
- Payload type mismatch
- Codec issues (if using in-band)

**Solutions**:
1. **Check Network Quality**:
   ```bash
   # Monitor packet loss
   iperf3 -c <phone_ip> -u -b 100k -t 30
   ```

2. **Use More Reliable Method**:
   - Switch from in-band to RFC 2833
   - Enable SIP INFO fallback
   - Increase DTMF duration (160ms → 200ms)

3. **Adjust Timing**:
   ```yaml
   features:
     dtmf:
       duration: 200      # Increase from 160ms
       min_gap: 100       # Minimum gap between digits
   ```

#### Problem 3: Codec Mismatch

**Symptoms**:
- Call disconnects immediately when accessing voicemail
- Audio prompts play but no DTMF possible
- Phone and PBX negotiating different codecs

**Solution**:
1. **Use SIP INFO**: Codec-independent DTMF
   ```ini
   account.1.dtmf_mode = SIP_INFO
   ```

2. **Match Codecs**: Ensure phone and PBX support same codecs
   ```yaml
   codecs:
     enabled:
       - PCMU    # Ensure compatibility
       - PCMA
   ```

3. **Check SDP Negotiation**: Verify compatible codec selected
   ```bash
   # Check SIP traces for SDP offer/answer
   grep -A10 "m=audio" /tmp/dtmf_test.pcap
   ```

### Debug Logging

#### Enable DTMF Debug Logging

Add to `.env` file:

```bash
DEBUG_VM_PIN=true
```

This enables detailed DTMF logging to `logs/vm_ivr.log`:

```
2024-12-18 10:30:15 - VM_IVR - INFO - DTMF digit '5' detected via RFC2833
2024-12-18 10:30:15 - VM_IVR - INFO - Current PIN buffer: '12345'
2024-12-18 10:30:15 - VM_IVR - INFO - PIN verified successfully for extension 1001
```

**⚠️ WARNING**: Debug logging exposes sensitive PIN data. Use only for troubleshooting, not in production.

#### Check Logs

```bash
# Watch live DTMF events
tail -f logs/vm_ivr.log | grep DTMF

# Search for PIN verification
grep "PIN verified" logs/vm_ivr.log

# Check for DTMF detection failures
grep "DTMF.*failed" logs/pbx.log
```

### Advanced Troubleshooting

#### PCAP Analysis

Capture and analyze SIP/RTP traffic:

```bash
# Capture traffic
tcpdump -i any -s 0 -w /tmp/dtmf_debug.pcap \
  'port 5060 or portrange 10000-20000'

# Analyze with Wireshark
wireshark /tmp/dtmf_debug.pcap

# Look for:
# 1. SDP negotiation (telephone-event payload type)
# 2. RTP packets with DTMF payload
# 3. SIP INFO messages with DTMF
# 4. Timing between DTMF packets
```

#### Test DTMF Methods Individually

```bash
# Test RFC 2833 only
# Configure phone: dtmf_mode = RFC2833
# Disable: dtmf_sip_info_fallback = 0

# Test SIP INFO only  
# Configure phone: dtmf_mode = SIP_INFO

# Test in-band only
# Configure phone: dtmf_mode = INBAND
# (Not recommended)
```

---

## Related Documentation

- **[CODEC_IMPLEMENTATION_GUIDE.md](CODEC_IMPLEMENTATION_GUIDE.md)** - Codec configuration affecting DTMF
- **[PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)** - Phone provisioning templates
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - General troubleshooting guide
- **[VOICEMAIL_CUSTOM_GREETING_GUIDE.md](VOICEMAIL_CUSTOM_GREETING_GUIDE.md)** - Voicemail IVR usage

---

**Note**: This consolidated guide replaces the individual DTMF guides:
- DTMF_PAYLOAD_TYPE_CONFIGURATION.md
- SIP_INFO_DTMF_GUIDE.md
- RFC2833_IMPLEMENTATION_GUIDE.md
- ZIP33G_DTMF_PAYLOAD_TYPE_RESOLUTION.md
- ZULTYS_DTMF_TROUBLESHOOTING.md
