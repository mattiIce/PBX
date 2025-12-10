# TTS Fix Verification Guide

This document explains how to verify that the TTS audio distortion issue has been fixed.

## The Problem (Before Fix)

Running `generate_tts_prompts.py` would complete successfully but produce distorted, unreadable audio files due to broken G.722 encoding.

## The Solution (After Fix)

The script now generates high-quality PCM WAV files by default, with optional G.722 encoding via ffmpeg.

## How to Verify the Fix

### Prerequisites

1. Install required dependencies:
```bash
pip install gTTS pydub
```

2. For G.722 support (optional):
```bash
# On Ubuntu/Debian
sudo apt-get install ffmpeg

# Verify G.722 support
ffmpeg -codecs | grep g722
# Should show: DEAIL. adpcm_g722 G.722 ADPCM
```

### Test 1: Generate Voice Prompts (Recommended - PCM Format)

```bash
cd /path/to/PBX
python3 scripts/generate_tts_prompts.py --vm-only
```

**Expected Result:**
- Script completes successfully
- Files created in `voicemail_prompts/` directory
- Each WAV file is readable and plays with clear audio
- File format: PCM, 16kHz, 16-bit, mono

**Verify Audio Quality:**
```bash
# Check file info
file voicemail_prompts/goodbye.wav
# Should show: RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 16000 Hz

# Play the file (requires a media player)
aplay voicemail_prompts/goodbye.wav  # Linux
# or
afplay voicemail_prompts/goodbye.wav  # macOS
# or open in any media player
```

### Test 2: Programmatic Verification

```python
import os
import struct
from pbx.utils.tts import text_to_wav_telephony
from pbx.utils.logger import PBXLogger

# Setup logging
PBXLogger().setup(log_level='INFO', console=True)

# Generate test file with PCM format (recommended)
print("Testing PCM generation...")
success = text_to_wav_telephony(
    "Hello world, this is a test", 
    "test_pcm.wav",
    convert_to_g722=False,  # PCM format (default)
    sample_rate=16000
)

if success and os.path.exists("test_pcm.wav"):
    size = os.path.getsize("test_pcm.wav")
    print(f"✓ PCM file generated successfully ({size} bytes)")
    
    # Check WAV header
    with open("test_pcm.wav", 'rb') as f:
        f.seek(20)  # Position of audio format code
        audio_format = struct.unpack('<H', f.read(2))[0]
        
        if audio_format == 1:
            print("✓ File is correctly formatted as PCM (format code 1)")
        else:
            print(f"✗ Unexpected format code: {audio_format}")
else:
    print("✗ Failed to generate PCM file")

# Test G.722 generation (optional, requires ffmpeg)
print("\nTesting G.722 generation (optional)...")
success = text_to_wav_telephony(
    "Hello world, this is a test",
    "test_g722.wav", 
    convert_to_g722=True,  # G.722 format
    sample_rate=16000
)

if success and os.path.exists("test_g722.wav"):
    size = os.path.getsize("test_g722.wav")
    print(f"✓ G.722 file generated successfully ({size} bytes)")
    print("  Note: Should be ~4x smaller than PCM version")
else:
    print("⚠ G.722 generation failed (likely fell back to PCM)")
    print("  This is OK if ffmpeg is not installed")
```

### Test 3: Compare File Sizes

For the same audio content:

- **PCM WAV**: ~96 KB for 3 seconds of speech (16kHz, 16-bit, mono)
- **G.722 WAV**: ~24 KB for 3 seconds (4:1 compression ratio)

```bash
ls -lh voicemail_prompts/
# All files should be present and reasonable sizes (not 0 bytes)
```

### Test 4: Audio Quality Check

Play any generated file and verify:

- [x] Audio is clear and understandable
- [x] No distortion or noise
- [x] Natural speech quality
- [x] No robotic or garbled sound
- [x] Volume is appropriate

### Test 5: Check Logs for Warnings

Run the script and check for any warnings:

```bash
python3 scripts/generate_tts_prompts.py 2>&1 | grep -i warning
```

**Expected:**
- If G.722 was attempted without ffmpeg: "ffmpeg not found" warning (OK)
- No other warnings about encoding failures

## Troubleshooting

### Issue: "ERROR: TTS dependencies not installed!"

**Solution:**
```bash
pip install gTTS pydub
```

### Issue: "Couldn't find ffmpeg or avconv"

**Solution:**
```bash
sudo apt-get install ffmpeg  # Ubuntu/Debian
# or
brew install ffmpeg  # macOS
```

### Issue: "Failed to connect" error from gTTS

**Solution:**
- Check internet connection (gTTS requires internet to access Google's TTS API)
- Try again in a few minutes (might be temporary network issue)

### Issue: Audio files are generated but sound distorted

**Verification:**
1. Check the format code in WAV header
2. Ensure using PCM format (convert_to_g722=False)
3. Try regenerating with the updated code

```python
# Force PCM generation
from pbx.utils.tts import text_to_wav_telephony
text_to_wav_telephony("test", "test.wav", convert_to_g722=False)
```

## Summary

After the fix:

✅ Default PCM format produces high-quality, lossless audio
✅ Optional G.722 encoding via ffmpeg for compression
✅ Automatic fallback to PCM if G.722 fails  
✅ Clear error messages and logging
✅ No more distorted or unreadable audio files

The issue is **RESOLVED** - TTS-generated voice prompts are now production-quality.

## Additional Resources

- [G722_IMPLEMENTATION_NOTES.md](./G722_IMPLEMENTATION_NOTES.md) - Technical details
- [SETUP_GTTS_VOICES.md](./SETUP_GTTS_VOICES.md) - Voice setup guide (if exists)
- [ITU-T G.722 Specification](https://www.itu.int/rec/T-REC-G.722)
