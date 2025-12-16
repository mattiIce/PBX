# Music on Hold (MOH) System

This directory contains Music on Hold (MOH) audio files for the PBX system.

## Directory Structure

```
moh/
└── default/          # Default MOH class
    ├── ambient.wav   # Soothing ambient tones
    ├── arpeggio.wav  # Pleasant arpeggio pattern
    ├── chimes.wav    # Gentle chime sounds
    ├── melody.wav    # Simple melodic tune
    └── pad.wav       # Soft sustained pad sound
```

## Pre-Generated Files

This repository includes 5 pre-generated MOH tracks:

1. **melody.wav** - Simple, pleasant melody using major scale notes
2. **ambient.wav** - Soothing ambient tones with harmonious frequencies
3. **arpeggio.wav** - Flowing arpeggio pattern
4. **pad.wav** - Soft, sustained pad sound for a calming effect
5. **chimes.wav** - Gentle chime sounds with natural decay

All files are:
- **Format:** WAV (uncompressed)
- **Sample Rate:** 8000 Hz (telephony standard)
- **Bit Depth:** 16-bit
- **Channels:** Mono
- **Duration:** 30 seconds each

## How MOH Works

When a call is placed on hold in the PBX system:

1. The system loads all `.wav` files from the `moh/default/` directory
2. A random file is selected and played to the caller
3. The music loops seamlessly if the hold time exceeds the file duration
4. When the call is resumed, the music stops

## Regenerating MOH Files

You can regenerate the MOH files with different settings using the provided script:

### Basic Usage

```bash
# Generate all default tracks (30 seconds each)
python3 scripts/generate_moh_music.py

# Generate longer tracks (60 seconds)
python3 scripts/generate_moh_music.py --duration 60

# Generate specific tracks only
python3 scripts/generate_moh_music.py --melody --ambient
```

### Options

- `--output-dir DIR` - Output directory (default: moh/default)
- `--duration SEC` - Duration in seconds (default: 30)
- `--all` - Generate all tracks (default)
- `--melody` - Generate only simple melody
- `--ambient` - Generate only ambient tones
- `--arpeggio` - Generate only arpeggio
- `--pad` - Generate only soft pad
- `--chimes` - Generate only gentle chimes

### Examples

```bash
# Generate 2-minute tracks
python3 scripts/generate_moh_music.py --duration 120

# Generate only melody and chimes
python3 scripts/generate_moh_music.py --melody --chimes

# Generate to a custom directory
python3 scripts/generate_moh_music.py --output-dir moh/custom
```

## Adding Custom MOH Files

You can add your own music files to the `moh/default/` directory:

### Requirements

Your custom files must meet these specifications:
- Format: WAV (uncompressed)
- Sample Rate: 8000 Hz
- Bit Depth: 16-bit
- Channels: Mono (1 channel)

### Converting Files

If you have music in other formats (MP3, FLAC, etc.), convert them using ffmpeg:

```bash
# Convert MP3 to MOH format
ffmpeg -i your_music.mp3 -ar 8000 -ac 1 -sample_fmt s16 moh/default/your_music.wav

# Convert FLAC to MOH format
ffmpeg -i your_music.flac -ar 8000 -ac 1 -sample_fmt s16 moh/default/your_music.wav
```

### Tips for Custom Files

1. **Keep files under 2 minutes** - Shorter loops are less noticeable
2. **Use instrumental music** - Avoid vocals which can be distracting
3. **Choose pleasant, neutral music** - Classical, jazz, or ambient works well
4. **Avoid loud or jarring sounds** - Keep callers relaxed
5. **Test the audio quality** - 8000 Hz has lower quality than modern audio

## MOH Classes (Advanced)

The MOH system supports multiple "classes" for different hold music categories:

```
moh/
├── default/      # Standard hold music
├── sales/        # Music for sales queue
├── support/      # Music for support queue
└── executive/    # Premium hold music
```

To use different classes in your PBX configuration:

```python
# In your call handling code
pbx.moh.start_moh(call_id, moh_class='sales')
```

## Troubleshooting

### No music playing on hold

1. Check that files exist:
   ```bash
   ls -l moh/default/*.wav
   ```

2. Verify file format:
   ```bash
   file moh/default/melody.wav
   # Should show: RIFF ... WAVE audio, Microsoft PCM, 16 bit, mono 8000 Hz
   ```

3. Check PBX logs:
   ```bash
   grep -i "moh" logs/pbx.log
   ```

### Poor audio quality

The 8000 Hz telephony standard has lower quality than modern audio (44100 Hz or 48000 Hz). This is intentional for bandwidth efficiency in phone systems.

If quality is unacceptable:
1. Use higher-quality source files before conversion
2. Choose music with simpler arrangements
3. Avoid complex bass frequencies (they don't translate well at 8kHz)

### Files too large

Each second of 8000 Hz, 16-bit mono audio = ~16 KB

- 30-second file ≈ 480 KB
- 60-second file ≈ 960 KB
- 120-second file ≈ 1.9 MB

To reduce size:
- Use shorter files
- Use lower bit depth (8-bit instead of 16-bit, though quality suffers)

## Testing MOH

To test your MOH files:

1. **Listen to files directly:**
   ```bash
   # Linux
   aplay moh/default/melody.wav
   
   # macOS
   afplay moh/default/melody.wav
   
   # Using ffplay (cross-platform)
   ffplay -nodisp -autoexit moh/default/melody.wav
   ```

2. **Test in PBX:**
   - Make a call between two extensions
   - Put the call on hold
   - Verify the caller hears music

## License & Copyright

The generated MOH files in this directory are simple sine wave compositions created by the `generate_moh_music.py` script. They contain no copyrighted material and are free to use.

**Important:** If you add commercial music files, ensure you have the proper licensing rights (BMI, ASCAP, SESAC, etc.) for public performance.

## Additional Resources

- [PBX Features Documentation](../README.md#features)
- [Music on Hold Implementation](../pbx/features/music_on_hold.py)
- [MOH Configuration](../config.yml)

## Summary

✅ **Pre-generated files included** - 5 pleasant tracks ready to use  
✅ **Easy regeneration** - Simple script for custom durations  
✅ **Proper format** - All files in telephony-standard format  
✅ **Extensible** - Add your own files or create custom classes  
✅ **No dependencies** - Uses Python's built-in wave module  

Your PBX system is ready to provide pleasant hold music to callers!
