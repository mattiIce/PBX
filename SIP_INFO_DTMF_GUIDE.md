# SIP INFO DTMF Support Guide

## Overview

The PBX system now supports DTMF (touch-tone) signaling via **SIP INFO** messages in addition to in-band audio detection. This guide explains the implementation and how to configure phones to use SIP INFO for DTMF.

## Background: Codec Mismatch Issue

The original issue occurred when phones using G.729 codec dialed into voicemail:

1. Phone sends INVITE with G.729 in SDP
2. PBX answers with 200 OK offering only G.711 (PCMU/PCMA)
3. Phone can't find compatible codec → sends ACK + BYE immediately
4. RTP handlers continue playing audio (race condition)

**Workaround**: Switch phone to use PCMU codec OR implement SIP INFO DTMF support.

## DTMF Transport Methods

### 1. In-Band (In-Audio) - ✅ Implemented
- DTMF tones embedded in audio RTP stream
- Detected using Goertzel algorithm
- **Pros**: Universal compatibility
- **Cons**: Affected by codec compression (especially G.729), audio quality issues
- **Status**: Fully implemented with fallback support

### 2. RFC 2833 (RTP Events) - ✅ Implemented
- DTMF sent as separate RTP events in RTP stream
- Uses payload type 101 (telephone-event)
- **Pros**: Most reliable RTP method, not affected by audio codec, industry standard
- **Cons**: Requires both endpoints to support RFC 2833
- **Status**: Fully implemented (see RFC2833_IMPLEMENTATION_GUIDE.md)

### 3. SIP INFO Messages - ✅ Implemented
- DTMF sent as SIP INFO requests with body
- Out-of-band SIP signaling
- **Pros**: Reliable signaling method, works with any audio codec
- **Cons**: Requires SIP server support
- **Status**: Fully implemented with priority queue system

## Implementation Details

### SIP Server (`pbx/sip/server.py`)

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

**SIP INFO Message Format**:
```
INFO sip:voicemail@pbx.example.com SIP/2.0
Call-ID: abc123...
Content-Type: application/dtmf-relay
Content-Length: 24

Signal=5
Duration=160
```

### PBX Core (`pbx/core/pbx.py`)

Added `handle_dtmf_info()` method:

```python
def handle_dtmf_info(self, call_id, dtmf_digit):
    """Queue DTMF digits received via SIP INFO for IVR processing"""
    call = self.call_manager.get_call(call_id)
    if not hasattr(call, 'dtmf_info_queue'):
        call.dtmf_info_queue = []
    call.dtmf_info_queue.append(dtmf_digit)
```

## Phone Configuration

### Grandstream Phones (GXP Series)

Configure via web interface or provisioning template:

```ini
# DTMF Settings
P79 = 2    # DTMF Type: 0=In-audio, 1=RFC2833, 2=SIP INFO
P184 = 0   # DTMF Info Type: 0=DTMF, 1=DTMF-Relay
P78 = 101  # DTMF Payload Type (for RFC2833 fallback)
```

**Web UI Path**: Account → Basic Settings → DTMF
- **DTMF Type**: SIP INFO
- **DTMF Info Type**: DTMF

### Yealink Phones (T46S, T48S, etc.)

Configure via provisioning template:

```ini
# DTMF Settings
account.1.dtmf.type = 2          # 0=Inband, 1=RFC2833, 2=SIP INFO
account.1.dtmf.info_type = 0     # 0=DTMF, 1=DTMF-Relay
account.1.dtmf.dtmf_payload = 101
```

**Web UI Path**: Account → Advanced → DTMF
- **DTMF Type**: SIP INFO
- **DTMF Info Format**: application/dtmf

### Polycom Phones

Add to configuration file:

```xml
<voice>
  <dtmf voice.dtmf.tx.mode="sipInfo"/>
</voice>
```

## Auto-Provisioning

The updated provisioning templates in `provisioning_templates/` directory now include DTMF configuration:

1. **Grandstream**: `grandstream_gxp2170.template`
2. **Yealink**: `yealink_t46s.template`

When phones fetch configuration via auto-provisioning, they will automatically be configured to use SIP INFO for DTMF.

## Current Status and Future Work

### ✅ Completed

- [x] SIP INFO message parsing and handling
- [x] DTMF queue infrastructure in PBX core
- [x] Provisioning templates with DTMF configuration
- [x] Documentation

### ✅ Full Implementation Complete

The IVR session loops now support all three DTMF methods with priority system:

**Voicemail IVR** (`pbx/core/pbx.py` - `_voicemail_ivr_session()`):
- **Priority 1**: Checks SIP INFO / RFC 2833 queue (dtmf_info_queue)
- **Priority 2**: Falls back to in-band audio detection
- Supports DTMF during:
  - PIN entry
  - Menu navigation
  - Greeting recording (# to stop)

**Auto-Attendant** (`pbx/core/pbx.py` - `_auto_attendant_session()`):
- **Priority 1**: Checks SIP INFO / RFC 2833 queue
- **Priority 2**: Falls back to in-band listener
- Supports menu navigation and transfers

**Implementation Pattern**:
```python
# Priority 1: Check SIP INFO / RFC 2833 queue (unified)
if hasattr(call, 'dtmf_info_queue') and call.dtmf_info_queue:
    digit = call.dtmf_info_queue.pop(0)
    self.logger.info(f"Detected DTMF from out-of-band signaling: {digit}")
else:
    # Priority 2: In-band detection (fallback)
    digit = dtmf_detector.detect(recent_audio)
    if digit:
        self.logger.info(f"Detected DTMF from in-band audio: {digit}")
```

**Note**: Both SIP INFO and RFC 2833 use the same `dtmf_info_queue`, ensuring seamless integration and preventing duplicates.

### 🔄 Future Enhancements

1. **G.729 Codec Support**: Add G.729 transcoding or native support for voicemail
2. **DTMF Buffer Management**: Add buffer size limits and timeout handling
3. **Testing**: Comprehensive testing with various phone models
4. **Performance Optimization**: Consider async queue processing
5. **16kHz RFC 2833**: Add wideband support for HD voice codecs

### ✅ Recently Completed Enhancements

1. **RFC 2833 Support**: ✅ COMPLETED (December 9, 2024)
   - Full RTP event packet parsing with payload type 101
   - RFC2833Receiver for incoming events
   - RFC2833Sender for outgoing events
   - Integration with voicemail and auto-attendant
   - See `RFC2833_IMPLEMENTATION_GUIDE.md` for details

## Testing

### Test Plan

1. **Configure test phone** with SIP INFO DTMF (see phone configuration section above)
2. **Dial voicemail** access code (*XXXX)
3. **Enter PIN** using phone keypad
4. **Navigate menus** (press 1, 2, *, etc.)
5. **Monitor logs** for DTMF detection messages
6. **Expected Behavior**: 
   - IVR responds to DTMF digits
   - Logs show "Detected DTMF from SIP INFO" messages
   - Voicemail menu navigation works correctly

### Verification Commands

```bash
# Watch for SIP INFO messages
tail -f logs/pbx.log | grep "INFO request"

# Check DTMF queueing
tail -f logs/pbx.log | grep "Queued DTMF"

# Monitor voicemail IVR activity
tail -f logs/pbx.log | grep "voicemail IVR"
```

## Troubleshooting

### Phone sends DTMF but IVR doesn't respond

**Check**:
1. Verify phone DTMF Type is set to "SIP INFO"
2. Check logs for "Queued DTMF" and "Detected DTMF from SIP INFO" messages
3. Ensure call is active (not ended by codec mismatch)
4. Try in-band DTMF as fallback test

### SIP INFO messages not received

**Check**:
1. Phone DTMF Type set to "SIP INFO" in configuration
2. PBX logs show "INFO request from..." messages
3. Network allows SIP signaling (port 5060)

### Codec mismatch still occurring

**Solution**: Phone must use G.711 (PCMU or PCMA) codec for voicemail calls until G.729 support is added.

## Security Considerations

- SIP INFO messages are authenticated as part of the existing SIP dialog
- No additional authentication required once call is established
- DTMF digits in logs should be handled securely (consider log sanitization for PIN entry)

## References

- RFC 2833: RTP Payload for DTMF Digits, Telephony Tones and Signals
- RFC 6086: Session Initiation Protocol (SIP) INFO Method and Package Framework
- RFC 2976: The SIP INFO Method (original)

## Support

For issues or questions:
1. Check PBX logs: `logs/pbx.log`
2. Verify phone configuration
3. Test with in-band DTMF as fallback
4. Report issues with phone model and log excerpts
