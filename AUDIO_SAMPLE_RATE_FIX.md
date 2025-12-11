# Audio Sample Rate Fix

## Problem

The PBX system is experiencing audio quality issues due to a sample rate mismatch:

1. **Current State**: Voicemail prompt WAV files are generated at **16kHz** (16000 Hz)
2. **Expected State**: Telephony audio should be at **8kHz** (8000 Hz) for PCMU (G.711 μ-law) codec
3. **Result**: The RTP handler downsamples 16kHz audio to 8kHz, causing audio distortion and quality degradation

## Root Cause

The voicemail_prompts/*.wav files were generated with `--sample-rate 16000` option:
```bash
# What was done (INCORRECT for PCMU):
python scripts/generate_tts_prompts.py --sample-rate 16000 --voicemail
```

This creates 16kHz PCM WAV files. When played through the RTP handler:
1. File is read as 16kHz PCM
2. Downsampled to 8kHz (simple decimation - takes every other sample)
3. Converted to PCMU (μ-law)
4. Transmitted over SIP/RTP

The decimation process (taking every other sample) causes aliasing and quality loss.

## Verification

Check the current sample rate of voicemail prompts:
```bash
python3 -c "
import wave
wav_file = 'voicemail_prompts/enter_pin.wav'
with wave.open(wav_file, 'rb') as w:
    print(f'Sample rate: {w.getframerate()} Hz')
    print(f'Expected: 8000 Hz for PCMU telephony')
"
```

Output shows:
```
Sample rate: 16000 Hz
Expected: 8000 Hz for PCMU telephony
```

## Solution

Regenerate all voicemail prompts at 8kHz sample rate:

```bash
# Backup existing files (optional)
mv voicemail_prompts voicemail_prompts.backup.16khz

# Regenerate at correct 8kHz sample rate
python scripts/generate_tts_prompts.py --sample-rate 8000 --voicemail
```

This will create 8kHz PCM WAV files that:
1. Don't require downsampling
2. Convert cleanly to PCMU without quality loss
3. Are the correct format for telephony applications

## Alternative Solution (Advanced)

If you want high-quality wideband audio, use G.722 codec instead of PCMU:

1. Generate files at 16kHz:
   ```bash
   python scripts/generate_tts_prompts.py --sample-rate 16000 --voicemail
   ```

2. Ensure G.722 codec is enabled in config.yml:
   ```yaml
   codecs:
     g722:
       enabled: true
       bitrate: 64000
   ```

3. The RTP handler will use G.722 for 16kHz audio (no downsampling needed)

**Note**: G.722 requires both the PBX and the phone to support the codec.

## Testing

After regenerating files, test audio quality:

1. Call voicemail: Dial `*1001` to access your voicemail
2. Listen to the prompts - they should sound clear, not distorted
3. Check logs for confirmation:
   ```bash
   tail -f logs/pbx.log | grep -i "sample\|downsample"
   ```

You should NOT see "Downsampled from 16kHz to 8kHz" messages when using 8kHz files.

## Impact

- **Before**: 16kHz PCM → downsample → 8kHz PCMU (distorted audio)
- **After**: 8kHz PCM → 8kHz PCMU (clean audio, no downsampling)

Audio quality should improve significantly after regenerating files at the correct sample rate.

## Related Files

- `scripts/generate_tts_prompts.py` - TTS generation script
- `pbx/rtp/handler.py` - RTP handler (lines 905-913: downsampling logic)
- `pbx/utils/tts.py` - TTS utilities
- `voicemail_prompts/*.wav` - Voicemail audio files (currently 16kHz, should be 8kHz)

## Status

⚠️ **Fix Required**: Voicemail prompts need to be regenerated at 8kHz sample rate.

This is one component of the broader hardphone audio issues mentioned in the Known Issues section of README.md.
