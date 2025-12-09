# AT&T Merlin Legend Import - Quick Reference Card

## Quick Commands

### Import from CSV + Audio Files
```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files
```

### Import from JSON + Audio Files
```bash
python scripts/import_merlin_voicemail.py \
    --json voicemail_data.json \
    --audio-dir /path/to/wav/files
```

### Import from Directory Structure (Filename Parsing)
```bash
python scripts/import_merlin_voicemail.py \
    --audio-dir /path/to/voicemail_export \
    --parse-filenames
```

### Import PINs Only
```bash
python scripts/import_merlin_voicemail.py \
    --pins pins.csv
```

### Import Custom Greetings
```bash
python scripts/import_merlin_voicemail.py \
    --greetings-dir /path/to/greetings
```

### Import Everything at Once
```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files \
    --pins pins.csv \
    --greetings-dir /path/to/greetings
```

### Dry Run (Preview Only)
```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files \
    --dry-run
```

## File Format Templates

### CSV Format (voicemail_data.csv)
```csv
extension,caller_id,timestamp,audio_file,duration,listened,voicemail_pin
1001,5551234567,2024-01-15 14:30:00,msg001.wav,45,false,1234
1002,5559876543,2024-01-16 09:15:00,msg002.wav,30,true,5678
```

### JSON Format (voicemail_data.json)
```json
{
  "voicemails": [
    {
      "extension": "1001",
      "caller_id": "5551234567",
      "timestamp": "2024-01-15T14:30:00",
      "audio_file": "msg001.wav",
      "duration": 45,
      "listened": false
    }
  ],
  "pins": {
    "1001": "1234",
    "1002": "5678"
  }
}
```

### PINs CSV Format (pins.csv)
```csv
extension,pin
1001,1234
1002,5678
```

### Directory Structure (Filename Parsing)
```
voicemail_export/
  1001/
    5551234567_20240115_143000.wav
    5559876543_20240115_150000.wav
  1002/
    5551112222_20240116_091500.wav
```
**Filename format:** `{caller_id}_{YYYYMMDD}_{HHMMSS}.wav`

### Greetings Directory
```
greetings/
  1001_greeting.wav
  1002_greeting.wav
  1003_greeting.wav
```
**Filename format:** `{extension}_greeting.wav`

## Supported Timestamp Formats

- `2024-01-15T14:30:00` (ISO format)
- `2024-01-15 14:30:00`
- `01/15/2024 14:30:00`
- `20240115_143000`

## Audio File Requirements

- **Format:** WAV
- **Codec:** PCM (uncompressed)
- **Sample Rate:** 8000 Hz or 16000 Hz
- **Bit Depth:** 16-bit
- **Channels:** Mono (1 channel)

### Convert Audio Files
```bash
# Single file
ffmpeg -i input.au -ar 8000 -ac 1 output.wav

# Batch convert
for f in *.au; do ffmpeg -i "$f" -ar 8000 -ac 1 "${f%.au}.wav"; done
```

## Pre-Flight Checklist

Before importing:

- [ ] Export voicemail data from Merlin Legend
- [ ] Convert audio files to WAV format
- [ ] Prepare metadata file (CSV or JSON)
- [ ] Verify all extensions exist in PBX
- [ ] Test with `--dry-run` first
- [ ] Backup database (optional but recommended)

### Check Extensions Exist
```bash
python scripts/list_extensions_from_db.py
```

### Verify Database
```bash
python scripts/verify_database.py
```

## Verification Commands

### Check Import Results
```bash
# View voicemail directory
ls -R voicemail/

# Count voicemails in database (PostgreSQL)
psql -U pbx_user -d pbx_system -c \
  "SELECT extension_number, COUNT(*) FROM voicemail_messages GROUP BY extension_number;"

# Count voicemails in database (SQLite)
sqlite3 pbx.db \
  "SELECT extension_number, COUNT(*) FROM voicemail_messages GROUP BY extension_number;"
```

### View Recent Imports
```bash
# PostgreSQL
psql -U pbx_user -d pbx_system -c \
  "SELECT * FROM voicemail_messages ORDER BY created_at DESC LIMIT 10;"

# SQLite
sqlite3 pbx.db \
  "SELECT * FROM voicemail_messages ORDER BY created_at DESC LIMIT 10;"
```

### Check Logs
```bash
tail -f logs/pbx.log
```

## Common Issues

### "Audio file not found"
- Verify `--audio-dir` path
- Check file names match metadata
- Ensure proper directory structure

### "Invalid PIN format"
- PINs must be exactly 4 digits
- Only numeric characters (0-9)
- No spaces or special characters

### "Extension not found"
- Add extensions via admin interface
- Or add to config.yml
- Run: `python scripts/migrate_extensions_to_db.py`

### "Database connection failed"
- Check database is running
- Verify config.yml settings
- Run: `python scripts/verify_database.py`
- Import still works (file-only mode)

## Get Help

```bash
# View all options
python scripts/import_merlin_voicemail.py --help

# View full documentation
cat MERLIN_IMPORT_GUIDE.md
```

## Example Templates

Example files are in: `examples/merlin_import/`
- `voicemail_data.csv` - CSV template
- `voicemail_data.json` - JSON template
- `pins.csv` - PINs template
- `test_audio/` - Sample WAV files
- `test_greetings/` - Sample greeting files

## Notes

- **Always use `--dry-run` first** to preview import
- Script **automatically skips duplicates** (safe to re-run)
- **Metadata stored in database**, audio files on disk
- Import is **non-destructive** (doesn't modify existing data)
- **Logs** saved to `logs/pbx.log`

## Support

For detailed documentation, see: **[MERLIN_IMPORT_GUIDE.md](MERLIN_IMPORT_GUIDE.md)**
