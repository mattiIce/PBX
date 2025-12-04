# Voicemail System Fixes

## Issues Fixed

### Issue 1: Called Phone Continues Ringing
**Problem:** When a call times out and routes to voicemail, the called extension's phone continues to ring indefinitely.

**Root Cause:** The PBX was sending a 200 OK to the caller to start voicemail recording, but never sent a CANCEL to the called extension to stop the INVITE request.

**Fix:** Modified `pbx/core/pbx.py` in the `_handle_no_answer()` method to:
1. Store the callee's address and INVITE message when forwarding the call
2. Send a CANCEL request to the callee before answering the call for voicemail
3. This stops the called phone from ringing immediately

**Code Changes:**
```python
# Store callee info when forwarding INVITE (line ~298)
call.callee_addr = dest_ext_obj.address
call.callee_invite = invite_to_callee

# Send CANCEL to callee when routing to voicemail (line ~574)
if hasattr(call, 'callee_addr') and call.callee_addr:
    cancel_request = SIPMessageBuilder.build_request(
        method='CANCEL',
        uri=call.callee_invite.uri,
        from_addr=call.callee_invite.get_header('From'),
        to_addr=call.callee_invite.get_header('To'),
        call_id=call_id,
        cseq=int(call.callee_invite.get_header('CSeq').split()[0])
    )
    self.sip_server._send_message(cancel_request.build(), call.callee_addr)
```

### Issue 2: Caller Hears No Sound
**Problem:** When voicemail starts recording, the caller hears complete silence with no indication that they should start leaving a message.

**Root Cause:** The system answers the call (200 OK) and starts recording, but doesn't send any audio to the caller. The caller has no way to know when to start speaking.

**Fix:** 
1. Created new `RTPPlayer` class in `pbx/rtp/handler.py` to send audio packets
2. Created audio utilities in `pbx/utils/audio.py` to generate tones
3. Modified `_handle_no_answer()` to play a beep tone (1000 Hz, 500ms) to the caller before recording starts

**Code Changes:**

New RTPPlayer class (pbx/rtp/handler.py):
```python
class RTPPlayer:
    """RTP Player - Sends audio to remote endpoint"""
    
    def send_audio(self, audio_data, payload_type=0, samples_per_packet=160):
        # Send audio via RTP packets
        
    def play_beep(self, frequency=1000, duration_ms=500):
        # Generate and play a beep tone
```

Audio utilities (pbx/utils/audio.py):
```python
def generate_beep_tone(frequency=1000, duration_ms=500, sample_rate=8000):
    """Generate a simple beep tone in raw PCM format"""
    # Returns 16-bit signed PCM audio data

def generate_voicemail_beep():
    """Generate a voicemail beep tone with WAV header"""
    # Returns complete WAV file
```

Modified voicemail handling (pbx/core/pbx.py):
```python
# After answering call for voicemail (line ~612)
if call.caller_rtp:
    player = RTPPlayer(
        local_port=call.rtp_ports[0] + 1,
        remote_host=call.caller_rtp['address'],
        remote_port=call.caller_rtp['port'],
        call_id=call_id
    )
    if player.start():
        player.play_beep(frequency=1000, duration_ms=500)
        player.stop()
```

## Testing

### Test Scenario 1: No-Answer Voicemail
1. Extension 1001 calls extension 1002
2. Extension 1002 doesn't answer for 30 seconds (configurable timeout)
3. **Expected Result:**
   - Extension 1002's phone stops ringing immediately
   - Extension 1001 hears a beep tone
   - Extension 1001 can leave a voicemail message
   - Message is saved to extension 1002's voicemail

### Test Scenario 2: Direct Voicemail Access
1. Extension 1001 dials *1002 (voicemail access)
2. **Expected Result:**
   - Call connects immediately to voicemail
   - Extension 1001 hears a beep tone
   - Extension 1001 can leave a message

## Configuration

The voicemail timeout can be configured in `config.yml`:

```yaml
voicemail:
  no_answer_timeout: 30  # Seconds before routing to voicemail
  max_message_duration: 180  # Maximum voicemail length in seconds
```

## Future Enhancements

1. **Custom Greetings:** Allow users to record personalized voicemail greetings
2. **Multiple Beeps:** Play different tones for different voicemail types
3. **Voice Prompts:** Add spoken prompts ("Please leave a message after the beep")
4. **Early Media:** Use 183 Session Progress for better audio handling
5. **Silence Detection:** Automatically end voicemail if caller is silent for too long

## Related Files

- `pbx/core/pbx.py` - Main voicemail routing logic
- `pbx/rtp/handler.py` - RTP audio handling (player and recorder)
- `pbx/utils/audio.py` - Audio tone generation utilities
- `pbx/features/voicemail.py` - Voicemail storage and management
- `config.yml` - Voicemail configuration settings

## Notes

- The beep tone is standard telephony practice (1000 Hz for 500ms)
- RTP packets are sent at 20ms intervals for smooth playback
- The system uses G.711 codec (PCMU/PCMA) for compatibility
- Audio is generated at 8kHz sample rate (telephony standard)
