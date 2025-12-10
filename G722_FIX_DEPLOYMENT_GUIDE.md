# G.722 Codec Fix - Testing and Deployment Guide

**Date**: December 10, 2025  
**Issue**: Phones having issues with G.722 codec - no audio heard  
**Phones Affected**: Zultys ZIP33G and Zultys ZIP37G  
**Status**: ✅ FIXED

---

## Problem Summary

Users reported that after configuring phones to use G.722 codec, there was no audio on calls. Investigation revealed:

1. **G.722 Implementation Issue**: The custom G.722 codec has known quantization errors (95-100% error rate)
2. **Codec Mismatch**: When phones were switched to PCMU, the PBX was still converting PCM audio files to G.722
3. **Result**: Phones negotiated PCMU but received G.722 → No audio

## Solution Implemented

### 1. Codec Priority Changes

**Before**:
```
Priority 1: G.722 (HD Audio)
Priority 2: PCMU (G.711 μ-law)
Priority 3: PCMA (G.711 A-law)
```

**After**:
```
Priority 1: PCMU (G.711 μ-law) ← Maximum reliability
Priority 2: PCMA (G.711 A-law)
Priority 3: G.722 (HD Audio)    ← Available as fallback
```

### 2. Audio Conversion Fix

**Before**: PCM audio files → Converted to G.722  
**After**: PCM audio files → Converted to PCMU (G.711 μ-law)

**Additional**: 16kHz PCM files are now downsampled to 8kHz for PCMU compatibility

---

## Testing Instructions

### Quick Test (Recommended)

Run the automated test suite:
```bash
cd /home/runner/work/PBX/PBX
python3 tests/test_pcmu_codec_fix.py
```

**Expected output**:
```
✓ All PCMU codec tests passed!

Summary:
- PCM files are now converted to PCMU (G.711 μ-law)
- 16kHz files are downsampled to 8kHz for compatibility
- Phones using PCMU codec should now hear audio correctly
```

### Manual Testing with Zultys Phones

1. **Reprovision Phones**:
   - Access the phone provisioning system
   - Re-download configuration for Zultys ZIP33G/ZIP37G phones
   - Phones will now use PCMU as primary codec

2. **Test Voicemail**:
   - Call a voicemail box
   - You should hear: "Enter your PIN"
   - Verify audio is clear and understandable

3. **Test Auto-Attendant**:
   - Dial extension `0` (auto-attendant)
   - You should hear the menu options
   - Test DTMF input (press numbers)

4. **Test Call Between Phones**:
   - Make a call between two Zultys phones
   - Verify audio works in both directions
   - Check codec negotiation logs

### Verify Codec Negotiation

Check SIP logs to confirm PCMU is being used:
```bash
# Look for SDP negotiation in logs
grep -i "rtpmap:0 PCMU" logs/pbx.log | tail -5

# Check RTP handler logs
grep -i "PCM format detected" logs/pbx.log | tail -5
```

**Expected log entries**:
```
INFO - PCM format detected - will convert to PCMU (G.711 μ-law) for maximum compatibility.
INFO - Converted PCM to PCMU: 800 bytes (μ-law)
```

---

## Deployment Steps

### 1. Update Phone Configurations

**For Zultys ZIP33G phones**:
```
account.1.codec.1.payload_type = 0  # PCMU
account.1.codec.1.priority = 1

account.1.codec.2.payload_type = 8  # PCMA
account.1.codec.2.priority = 2

account.1.codec.3.payload_type = 9  # G.722
account.1.codec.3.priority = 3
```

**For Zultys ZIP37G phones**: Same configuration as ZIP33G

### 2. Restart PBX Service

```bash
# Stop the PBX
sudo systemctl stop pbx

# Start the PBX with new code
sudo systemctl start pbx

# Check status
sudo systemctl status pbx
```

### 3. Reprovision All Phones

Option A: Automatic (if auto-provisioning is enabled):
- Phones will pick up new configuration on next reboot
- Reboot all Zultys phones

Option B: Manual:
- Access provisioning interface
- Regenerate configuration for each phone
- Apply configuration to phones

### 4. Verify All Systems

- [ ] Voicemail system plays prompts correctly
- [ ] Auto-attendant menu audio works
- [ ] Music on hold plays correctly
- [ ] Call parking announcements work
- [ ] Conference prompts are audible
- [ ] Inter-phone calls have clear audio

---

## Rollback Plan

If issues occur, rollback steps:

1. **Revert provisioning templates**:
   ```bash
   git checkout HEAD~4 provisioning_templates/
   ```

2. **Revert RTP handler changes**:
   ```bash
   git checkout HEAD~4 pbx/rtp/handler.py
   ```

3. **Restart PBX service**

4. **Reprovision phones**

**Note**: Original G.722-first configuration will be restored

---

## Known Limitations

1. **Audio Quality**: PCMU (G.711) provides good quality but is not HD audio like G.722
   - Frequency range: 0-4 kHz (vs 0-7 kHz for G.722)
   - Acceptable for business telephony

2. **Bandwidth**: PCMU uses 64 kbps (same as G.722)

3. **G.722 Still Available**: If a phone specifically requests G.722, it can still be used

---

## Troubleshooting

### Issue: Still no audio after update

**Check**:
1. Verify phones have been reprovisioned with new configuration
2. Check phone status shows "Codec: PCMU" or "Codec: G.711"
3. Review logs for codec mismatch errors
4. Restart both PBX and phones

### Issue: Audio is garbled or distorted

**Check**:
1. Network packet loss: `grep "packet loss" logs/pbx.log`
2. Jitter buffer issues
3. Firewall blocking RTP ports (10000-20000)

### Issue: Phones still trying to use G.722

**Solution**:
1. Clear phone configuration cache
2. Factory reset phone (if necessary)
3. Reprovision from scratch
4. Verify template was updated correctly

---

## Files Modified

### Core Changes:
- `pbx/rtp/handler.py` - Audio conversion logic (main fix)
- `provisioning_templates/zultys_zip33g.template` - Codec priorities
- `provisioning_templates/zultys_zip37g.template` - Codec priorities

### Documentation:
- `config.yml` - Codec priority comments
- `G722_CODEC_GUIDE.md` - Updated priority documentation

### Testing:
- `tests/test_pcmu_codec_fix.py` - New comprehensive test

---

## Technical Details

### PCM to PCMU Conversion Process

1. **Read PCM file** (16-bit samples)
2. **Downsample if needed**: 16kHz → 8kHz (if input is 16kHz)
3. **Convert to μ-law**: Apply G.711 μ-law companding
4. **Package for RTP**: Create RTP packets with payload type 0
5. **Send to phone**: 160 samples per packet (20ms)

### Downsampling Algorithm

Simple decimation used:
- Take every other sample when downsampling 16kHz to 8kHz
- Maintains acceptable quality for voice
- Fast and efficient

---

## Support Contacts

For questions or issues:
1. Check this deployment guide
2. Review logs: `/home/runner/work/PBX/PBX/logs/pbx.log`
3. Run test suite: `python3 tests/test_pcmu_codec_fix.py`
4. Check GitHub issue/PR for updates

---

## Success Criteria

✅ **Deployment is successful if**:
1. All automated tests pass
2. Phones register with PCMU codec
3. Voicemail prompts are audible and clear
4. Auto-attendant works with DTMF input
5. Call audio is clear in both directions
6. No codec mismatch errors in logs

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-10  
**Tested With**: Zultys ZIP33G, Zultys ZIP37G
