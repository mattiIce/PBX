# Voicemail False BYE Workaround

## Issue Description

Some phone firmwares send a spurious BYE request immediately after receiving a 200 OK response during voicemail access. This causes the voicemail IVR session to terminate prematurely before the user can interact with it.

## Symptoms

When accessing voicemail (dialing `*<extension>`):
1. Phone dials voicemail access code
2. PBX answers with 200 OK
3. Phone immediately sends BYE (within < 1 second)
4. IVR session exits before user can enter PIN
5. User can still hear audio and press DTMF keys, but they are ignored

Example from logs:
```
2025-12-09 14:48:41 - PBX - INFO - [VM Access] ✓ 200 OK sent to ('192.168.10.155', 5060)
2025-12-09 14:48:41 - PBX - INFO - [VM Access] ✓ Call state changed to: CallState.CONNECTED
2025-12-09 14:48:41 - PBX - INFO - >>> BYE REQUEST RECEIVED <<<
2025-12-09 14:48:41 - PBX - INFO -   Call ID: 0_925399296@192.168.10.155
```

Note that the BYE is received at the exact same timestamp as the 200 OK.

## Root Cause

This is a known issue with certain phone firmwares that incorrectly handle the call state during voicemail access. The phone sends a BYE but continues to maintain the RTP audio stream and send DTMF signals, indicating that from the phone's perspective, the call is still active.

## Solution

The PBX now implements a workaround that ignores the first BYE request received within 2 seconds of answering a voicemail access call. This allows the IVR session to proceed normally.

### Implementation Details

- **Location**: `pbx/sip/server.py` in the `_handle_bye()` method
- **Logic**:
  1. Check if the call is a voicemail access call (`call.voicemail_access == True`)
  2. Check if this is the first BYE (no `first_bye_ignored` flag set)
  3. Check if the BYE was received within 2 seconds of call answer
  4. If all conditions are met, ignore the BYE and keep the call active
  5. Mark the BYE as ignored to honor subsequent BYE requests

### Behavior

- **First BYE within 2 seconds**: Ignored, call remains active
- **Second BYE**: Honored normally, call ends
- **BYE after 2 seconds**: Honored normally, even if first
- **Regular calls**: Not affected by this workaround

## Testing

Run the test suite to verify the workaround:
```bash
python3 tests/test_voicemail_false_bye.py
```

## Log Output

When the workaround is triggered, you'll see these log messages:
```
>>> BYE REQUEST RECEIVED <<<
  Call ID: <call_id>
  From: <address>
  Call Type: Voicemail Access
  ⚠ IGNORING spurious BYE for voicemail access (received 0.03s after answer)
  ⚠ This is a known issue with some phone firmwares
  ✓ Call remains active for voicemail IVR session
  ✓ Sent 200 OK response to <address> (but call continues)
```

## Affected Phone Models

This issue has been observed with:
- Zultys ZIP phones (ZIP33G, ZIP37G)
- Possibly other models (to be documented as discovered)

## Phone Configuration Export

If you experience this issue with your phone model, you can help by exporting and sharing your phone configuration:

1. Access your phone's web interface
2. Export the configuration file
3. Add it to the `provisioning_templates/` directory
4. Document the phone model and firmware version

This will help identify configuration settings that may trigger this behavior.

## Alternative Solutions

If the 2-second window is not sufficient for your deployment:

1. **Adjust the timeout**: Edit `pbx/sip/server.py` and change the `< 2.0` check to a larger value (e.g., `< 5.0` for 5 seconds)
2. **Phone firmware update**: Check if a firmware update is available for your phone that fixes this issue
3. **Phone configuration**: Some phones have SIP timer settings that may help (see provisioning templates)

## Future Improvements

Potential enhancements to consider:
- Make the timeout configurable in `config.yml`
- Track phone models that exhibit this behavior and apply workaround selectively
- Add metrics to monitor how often this workaround is triggered

## Related Files

- Implementation: `pbx/sip/server.py`
- Tests: `tests/test_voicemail_false_bye.py`
- Related: `tests/test_voicemail_ivr_bye_race.py`
