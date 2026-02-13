# Merlin Legend Import Example Files

This directory contains example template files for importing voicemail data from AT&T Merlin Legend systems.

## Files

### voicemail_data.csv
Example CSV format for voicemail metadata. Use this as a template to prepare your own data.

**Format:**
```csv
extension,caller_id,timestamp,audio_file,duration,listened,voicemail_pin
```

### voicemail_data.json
Example JSON format for voicemail metadata. Use this for structured data imports.

**Format:**
```json
{
  "voicemails": [...],
  "pins": {...}
}
```

### pins.csv
Example format for importing voicemail PINs separately.

**Format:**
```csv
extension,pin
```

## Directory Structure Example

For filename-based import, organize your files like this:

```
voicemail_export/
  1001/
    5551234567_20240115_143000.wav
    5559876543_20240115_150000.wav
  1002/
    5551112222_20240116_091500.wav
  1003/
    5555556666_20240117_110000.wav
```

## Greeting Files Example

For custom greeting import:

```
greetings/
  1001_greeting.wav
  1002_greeting.wav
  1003_greeting.wav
```

## Usage

See [COMPLETE_GUIDE.md](../../COMPLETE_GUIDE.md) for complete documentation.

### Quick Start

1. Copy the appropriate template file
2. Replace example data with your actual data
3. Prepare your WAV audio files
4. Run the import:

```bash
# CSV import
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files

# JSON import
python scripts/import_merlin_voicemail.py \
    --json voicemail_data.json \
    --audio-dir /path/to/wav/files

# Filename-based import
python scripts/import_merlin_voicemail.py \
    --audio-dir /voicemail_export \
    --parse-filenames

# PINs only
python scripts/import_merlin_voicemail.py \
    --pins pins.csv
```

### Dry Run

Always test first with --dry-run:

```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files \
    --dry-run
```

## Notes

- Replace example data with your actual voicemail data
- Ensure extension numbers match your PBX configuration
- Use 4-digit numeric PINs only
- Audio files should be in WAV format
- Timestamps can be in various formats (see guide)
