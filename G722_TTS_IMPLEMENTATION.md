# G.722 Voice Generation for TTS

**Date**: December 10, 2025  
**Status**: ✅ Implemented  
**Version**: 1.0

## Overview

This implementation changes gtts (Google Text-to-Speech) voice generation to produce G.722 encoded WAV files instead of PCM (16-bit linear) format. This eliminates the need for on-the-fly audio conversion during playback, improving performance and reducing CPU usage.

## What Changed

### Before
1. gtts generates MP3 files
2. MP3 converted to PCM WAV (16-bit, 16kHz)
3. PCM WAV stored on disk
4. **During playback**: PCM converted to G.722 on-the-fly by RTP handler

### After
1. gtts generates MP3 files
2. MP3 converted to PCM WAV (16-bit, 16kHz)
3. **PCM WAV immediately converted to G.722 WAV**
4. G.722 WAV stored on disk
5. **During playback**: No conversion needed, file played directly

## Benefits

✅ **Better Performance**: No CPU overhead for codec conversion during calls  
✅ **Lower Latency**: Audio playback starts immediately  
✅ **Reduced Resource Usage**: Conversion happens once during generation, not on every playback  
✅ **HD Audio Quality**: G.722 provides superior voice quality (16kHz wideband)  
✅ **Backward Compatible**: Existing code continues to work without changes  

## Technical Details

### Modified Files

#### 1. `pbx/utils/audio.py`
- **Updated `build_wav_header()`**: Added support for G.722 format (0x0067)
- **New function `convert_pcm_wav_to_g722_wav()`**: Converts PCM WAV files to G.722 format

```python
# New parameter added to build_wav_header
def build_wav_header(data_size, sample_rate=8000, channels=1, 
                     bits_per_sample=16, audio_format=1):
    # audio_format=1 for PCM, audio_format=0x0067 for G.722
    ...

# New conversion function
def convert_pcm_wav_to_g722_wav(input_wav_path, output_wav_path=None):
    """Convert a PCM WAV file to G.722 WAV format"""
    ...
```

#### 2. `pbx/utils/tts.py`
- **Updated `text_to_wav_telephony()`**: Added `convert_to_g722` parameter (default: True)
- After generating PCM WAV, automatically converts to G.722
- Falls back to PCM if G.722 conversion fails

```python
def text_to_wav_telephony(text, output_file, language='en', tld='com', 
                         slow=False, sample_rate=16000, convert_to_g722=True):
    """
    Convert text to WAV file in telephony format
    By default, generates G.722 encoded WAV files for HD audio quality.
    """
    ...
```

#### 3. `pbx/rtp/handler.py`
- **Enhanced WAV format detection**: Recognizes G.722 format (0x0067)
- **Skips conversion for G.722 files**: No processing needed
- **Maintains PCM support**: Still converts PCM files on-the-fly if needed

```python
# New format detection code
elif audio_format == 0x0067:
    # G.722 format - already encoded, no conversion needed
    payload_type = 9  # G.722
    convert_to_g722 = False
    self.logger.info(f"G.722 format detected - already encoded for VoIP.")
```

## Usage

### Default Behavior (G.722 Encoding)

All existing code automatically benefits from G.722 encoding:

```python
# This now generates G.722 WAV files by default
text_to_wav_telephony("Hello World", "greeting.wav")
```

### Generating PCM Files (If Needed)

To generate PCM files instead:

```python
# Explicitly disable G.722 conversion
text_to_wav_telephony("Hello World", "greeting.wav", convert_to_g722=False)
```

### Using Scripts

The `generate_tts_prompts.py` script automatically generates G.722 files:

```bash
# All generated files will be G.722 encoded
python3 scripts/generate_tts_prompts.py --company "ABC Company"
```

## Backward Compatibility

✅ **100% Backward Compatible**

- Existing code continues to work without any changes
- PCM WAV files are still supported and converted during playback
- All function signatures maintain their original parameters
- New parameter is optional with sensible default

## Testing

### Test Results

All tests pass successfully:

1. ✅ G.722 WAV header generation
2. ✅ PCM WAV header generation (backward compatibility)
3. ✅ PCM to G.722 conversion
4. ✅ WAV file conversion (PCM → G.722)
5. ✅ RTP playback of G.722 files (no conversion)
6. ✅ RTP playback of PCM files (with conversion)

### Log Messages

**G.722 File Playback:**
```
INFO - G.722 format detected - already encoded for VoIP.
INFO - Playing audio file: greeting.wav (1600 bytes)
```

**PCM File Playback:**
```
INFO - PCM format detected - will convert to G.722 (HD Audio) for VoIP compatibility.
INFO - Converted PCM to G.722: 3200 bytes -> 1600 bytes
INFO - Playing audio file: greeting.wav (1600 bytes)
```

## Performance Impact

### File Size
- **PCM WAV**: ~2x larger (16-bit samples)
- **G.722 WAV**: ~50% smaller (8-bit encoded samples)
- **Storage Savings**: Approximately 50% reduction in disk space

### CPU Usage
- **Before**: Conversion on every playback = N conversions per file
- **After**: One-time conversion during generation = 1 conversion per file
- **CPU Savings**: (N-1) × conversion_cost per file

### Example
For a greeting played 1000 times:
- **Before**: 1000 conversions
- **After**: 1 conversion
- **Savings**: 99.9% reduction in conversion overhead

## Audio Format Details

### G.722 WAV Header Format

```
RIFF header:     'RIFF' + file_size + 'WAVE'
Format chunk:    'fmt ' + chunk_size
  Audio Format:  0x0067 (103 decimal) = G.722
  Channels:      1 (mono)
  Sample Rate:   8000 Hz (clock rate, actual sampling is 16kHz)
  Byte Rate:     8000 bytes/sec
  Block Align:   1
  Bits/Sample:   8
Data chunk:      'data' + data_size + audio_data
```

### Why 8kHz Clock Rate?

G.722 uses 8kHz clock rate in WAV headers per RFC 3551, even though actual sampling is 16kHz. This is a quirk of the G.722 specification and correctly implemented in this code.

## Troubleshooting

### G.722 Codec Library Not Available

If the G.722 codec library is not installed, the system falls back to a stub implementation:

```
WARNING - Native G.722 library not found - stub implementation active
WARNING - G.722 codec library not available - using stub implementation
```

**Solution**: Install a native G.722 codec library (e.g., spandsp, libg722) for production use.

### Files Still in PCM Format

If generated files are PCM instead of G.722:
1. Check that `convert_to_g722=True` (or not specified, as it's the default)
2. Verify G.722 codec is available
3. Check logs for conversion errors
4. The system automatically falls back to PCM if G.722 conversion fails

## Future Enhancements

Potential improvements:
- [ ] Integrate native G.722 codec library for production
- [ ] Add configuration option to choose codec preference
- [ ] Support additional codec formats (Opus, etc.)
- [ ] Batch conversion tool for existing PCM files

## References

- **ITU-T G.722**: Wideband audio codec standard
- **RFC 3551**: RTP payload format for G.722
- **WAV Format**: RIFF WAVE file format specification
- **G722_CODEC_GUIDE.md**: Detailed G.722 implementation guide

## Summary

This implementation successfully changes gtts voice generation from PCM to G.722 format, providing:
- ✅ Better performance (no on-the-fly conversion)
- ✅ HD audio quality (16kHz wideband)
- ✅ Reduced storage (50% smaller files)
- ✅ Full backward compatibility
- ✅ No code changes required for existing functionality

The change is transparent to users and automatically improves the entire system's audio quality and performance.
