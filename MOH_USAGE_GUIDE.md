# Music on Hold (MOH) Usage Guide

## Overview

The PBX system now includes pre-generated Music on Hold (MOH) files that automatically play when callers are placed on hold. This guide explains how to use, customize, and manage the MOH system.

## Quick Start

### Pre-Generated Files Included ✅

The repository includes 5 professionally-generated MOH tracks:

1. **melody.wav** - Simple, pleasant melody (30 seconds)
2. **ambient.wav** - Soothing ambient tones (30 seconds)
3. **arpeggio.wav** - Flowing arpeggio pattern (30 seconds)
4. **pad.wav** - Soft sustained pad sound (30 seconds)
5. **chimes.wav** - Gentle chime sounds (30 seconds)

**No setup required!** The PBX automatically loads these files on startup.

## How It Works

When you start the PBX system, it:
1. Scans the `moh/default/` directory for `.wav` files
2. Loads all compatible audio files into the MOH system
3. Plays a random track when a call is placed on hold
4. Loops the music seamlessly if hold time exceeds file duration

You'll see this in the startup logs:
```
INFO - Loaded MOH class 'default' with 5 files
```

## Using MOH in Your PBX

MOH is automatically used when:
- A call is placed on hold using the HOLD feature
- A caller is waiting in a call queue
- A call is parked and waiting to be retrieved
- A transfer is being processed

**Example: Placing a call on hold**
```python
# In your call handling code
pbx.moh_system.start_moh(call_id)  # Starts playing random MOH track
# ... hold operation ...
pbx.moh_system.stop_moh(call_id)   # Stops MOH when call is resumed
```

## Regenerating MOH Files

You can regenerate the MOH files with different durations or customize which tracks to generate:

### Change Duration

```bash
# Generate 60-second tracks instead of 30 seconds
cd /home/runner/work/PBX/PBX
python3 scripts/generate_moh_music.py --duration 60

# Generate 2-minute tracks
python3 scripts/generate_moh_music.py --duration 120
```

### Generate Specific Tracks

```bash
# Generate only melody and ambient
python3 scripts/generate_moh_music.py --melody --ambient

# Generate only chimes
python3 scripts/generate_moh_music.py --chimes
```

### All Options

```bash
python3 scripts/generate_moh_music.py --help

Options:
  --output-dir DIR  Output directory (default: moh/default)
  --duration SEC    Duration in seconds (default: 30)
  --all            Generate all tracks (default)
  --melody         Generate only simple melody
  --ambient        Generate only ambient tones
  --arpeggio       Generate only arpeggio
  --pad            Generate only soft pad
  --chimes         Generate only gentle chimes
```

## Adding Your Own Music

You can replace the generated tracks with your own music files.

### Requirements

Your custom files must be:
- **Format:** WAV (uncompressed)
- **Sample Rate:** 8000 Hz
- **Bit Depth:** 16-bit
- **Channels:** Mono (1 channel)

### Converting Your Music

Use ffmpeg to convert your music to the correct format:

```bash
# Convert MP3 to MOH format
ffmpeg -i your_song.mp3 -ar 8000 -ac 1 -sample_fmt s16 moh/default/your_song.wav

# Convert any audio format
ffmpeg -i your_music.flac -ar 8000 -ac 1 -sample_fmt s16 moh/default/custom.wav
```

### Best Practices for Custom Music

1. **Choose instrumental music** - Vocals can be distracting on hold
2. **Keep files 30-120 seconds** - Shorter loops are less noticeable
3. **Use pleasant, neutral genres** - Classical, jazz, or ambient work well
4. **Test before deploying** - The 8kHz telephony format reduces quality
5. **Consider licensing** - Ensure you have rights to use commercial music

### Recommended Music Sources

- **Free/Royalty-Free:**
  - [Incompetech (Kevin MacLeod)](https://incompetech.com) - Free music with attribution
  - [Free Music Archive](https://freemusicarchive.org)
  - [YouTube Audio Library](https://www.youtube.com/audiolibrary)
  
- **Paid/Licensed:**
  - Ensure you have BMI, ASCAP, or SESAC licensing for commercial use
  - Many stock music sites offer telephone hold music licenses

## Testing Your MOH

### Listen to Files Directly

```bash
# Linux
aplay moh/default/melody.wav

# macOS
afplay moh/default/melody.wav

# Cross-platform (requires ffplay)
ffplay -nodisp -autoexit moh/default/melody.wav
```

### Test in the PBX

1. Start the PBX system:
   ```bash
   python3 main.py
   ```

2. Check the startup log for MOH confirmation:
   ```
   INFO - Loaded MOH class 'default' with 5 files
   ```

3. Make a test call and place it on hold:
   - Register two SIP extensions (e.g., 1001 and 1002)
   - Call from 1001 to 1002
   - Put the call on hold from either side
   - Verify music plays to the other party

### Verify Files Are Loaded

```python
# Quick test script
python3 -c "
from pbx.features.music_on_hold import MusicOnHold
moh = MusicOnHold()
print(f'MOH Classes: {moh.get_classes()}')
print(f'Files in default class: {len(moh.get_class_files(\"default\"))}')
for file in moh.get_class_files('default'):
    print(f'  - {file}')
"
```

## Advanced: Multiple MOH Classes

The MOH system supports multiple "classes" for different contexts:

### Creating Custom Classes

```bash
# Create a new MOH class for sales queue
mkdir -p moh/sales

# Add music files
ffmpeg -i upbeat_sales.mp3 -ar 8000 -ac 1 -sample_fmt s16 moh/sales/upbeat.wav

# The PBX will automatically load it on next restart
```

### Using Specific Classes

```python
# In your call queue configuration
pbx.moh_system.start_moh(call_id, moh_class='sales')

# In auto attendant
pbx.moh_system.start_moh(call_id, moh_class='support')

# Default class (if not specified)
pbx.moh_system.start_moh(call_id)  # Uses 'default' class
```

### Example Directory Structure

```
moh/
├── README.md
├── default/          # Standard hold music
│   ├── melody.wav
│   ├── ambient.wav
│   ├── arpeggio.wav
│   ├── pad.wav
│   └── chimes.wav
├── sales/            # Energetic music for sales
│   ├── upbeat1.wav
│   └── upbeat2.wav
├── support/          # Calming music for support
│   ├── calm1.wav
│   └── calm2.wav
└── executive/        # Premium music for VIP callers
    ├── classical1.wav
    └── classical2.wav
```

## Troubleshooting

### No Music Playing

1. **Check files exist:**
   ```bash
   ls -l moh/default/*.wav
   ```

2. **Verify file format:**
   ```bash
   file moh/default/melody.wav
   # Should show: RIFF ... WAVE audio, Microsoft PCM, 16 bit, mono 8000 Hz
   ```

3. **Check PBX logs:**
   ```bash
   grep -i "moh" logs/pbx.log
   ```

4. **Verify MOH is enabled in config:**
   ```yaml
   # config.yml
   features:
     music_on_hold: true
   ```

### Poor Audio Quality

The 8000 Hz telephony format has lower quality than modern audio (44.1 kHz). This is normal and expected for phone systems.

**Tips for better quality:**
- Use high-quality source files before conversion
- Choose music with simpler arrangements
- Avoid complex bass frequencies (don't translate well at 8kHz)
- Test files before deploying to production

### Files Not Loading

1. **Check directory structure:**
   ```bash
   ls -la moh/default/
   ```

2. **Verify permissions:**
   ```bash
   chmod -R 755 moh/
   ```

3. **Restart PBX:**
   ```bash
   # The MOH system loads files at startup
   python3 main.py
   ```

## Configuration Reference

### config.yml Settings

```yaml
features:
  music_on_hold: true  # Enable/disable MOH system
```

### MOH System Initialization

The MOH system is automatically initialized in `pbx/core/pbx.py`:

```python
self.moh_system = MusicOnHold()  # Loads files from moh/default/
```

## File Specifications

All MOH files must meet these exact specifications:

| Property | Value | Required |
|----------|-------|----------|
| Format | WAV (RIFF) | ✅ Yes |
| Sample Rate | 8000 Hz | ✅ Yes |
| Bit Depth | 16-bit | ✅ Yes |
| Channels | Mono (1) | ✅ Yes |
| Encoding | PCM | ✅ Yes |

**File size:** ~16 KB per second (30 seconds ≈ 480 KB)

## Summary

✅ **Ready to Use** - 5 pre-generated tracks included  
✅ **Automatic Loading** - Files load on PBX startup  
✅ **Easy Customization** - Add your own files or regenerate  
✅ **Multiple Classes** - Support for different hold music categories  
✅ **No Dependencies** - Works with Python's built-in libraries  

Your PBX system is fully configured with pleasant hold music!

## Additional Resources

- [MOH README](moh/README.md) - Detailed MOH documentation
- [Generate MOH Script](scripts/generate_moh_music.py) - Music generation tool
- [MOH Implementation](pbx/features/music_on_hold.py) - Source code
- [PBX Configuration](config.yml) - System configuration

## Questions?

Check the logs for MOH-related messages:
```bash
grep -i "moh\|music" logs/pbx.log
```

For issues, verify:
1. Files exist in `moh/default/`
2. Files are in correct format (8000 Hz, 16-bit, mono WAV)
3. MOH feature is enabled in `config.yml`
4. PBX logs show "Loaded MOH class 'default'" on startup
