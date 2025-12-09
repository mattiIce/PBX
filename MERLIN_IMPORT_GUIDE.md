# AT&T Merlin Legend Voicemail Import Guide

## Overview

This guide explains how to import voicemail data from an AT&T Merlin Legend phone system into this PBX system. The import tool supports multiple formats to accommodate different export methods from the legacy system.

## What Can Be Imported

- ✅ **Voicemail Messages** - Audio files and metadata (caller ID, timestamp, duration, listened status)
- ✅ **Voicemail PINs** - 4-digit access codes for each mailbox
- ✅ **Custom Greetings** - Personalized voicemail greetings

## Prerequisites

1. **Extract data from Merlin Legend system**
   - Export voicemail audio files (WAV format preferred)
   - Extract metadata (mailbox numbers, caller IDs, timestamps)
   - Note voicemail PINs for each mailbox

2. **Prepare PBX system**
   - Ensure PBX is installed and configured
   - Verify database connection (optional but recommended)
   - Ensure extensions exist in the PBX for import

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Supported Import Formats

The import tool supports three input formats to maximize compatibility:

### Format 1: CSV Metadata + WAV Files

Most flexible format for manual data preparation.

**CSV File Format (voicemail_data.csv):**
```csv
extension,caller_id,timestamp,audio_file,duration,listened,voicemail_pin
1001,5551234567,2024-01-15 14:30:00,msg001.wav,45,false,1234
1002,5559876543,2024-01-15 15:00:00,msg002.wav,30,true,5678
1003,5551112222,2024-01-16 09:15:00,msg003.wav,60,false,9999
```

**Field Descriptions:**
- `extension` - Extension number (required)
- `caller_id` - Caller's phone number (required)
- `timestamp` - Message timestamp in ISO format or common date formats (required)
- `audio_file` - Name of WAV file (required)
- `duration` - Message duration in seconds (optional)
- `listened` - Whether message was listened to: true/false (optional, default: false)
- `voicemail_pin` - 4-digit PIN for mailbox (optional)

**Supported Timestamp Formats:**
- `2024-01-15T14:30:00` (ISO format)
- `2024-01-15 14:30:00`
- `01/15/2024 14:30:00`
- `20240115_143000`

**Import Command:**
```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files
```

### Format 2: JSON Metadata + WAV Files

Best for programmatic exports or when you need structured data.

**JSON File Format (voicemail_data.json):**
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
    },
    {
      "extension": "1002",
      "caller_id": "5559876543",
      "timestamp": "2024-01-15T15:00:00",
      "audio_file": "msg002.wav",
      "duration": 30,
      "listened": true
    }
  ],
  "pins": {
    "1001": "1234",
    "1002": "5678",
    "1003": "9999"
  }
}
```

**Import Command:**
```bash
python scripts/import_merlin_voicemail.py \
    --json voicemail_data.json \
    --audio-dir /path/to/wav/files
```

### Format 3: Directory Structure with Filename Parsing

Use when you only have audio files without separate metadata.

**Directory Structure:**
```
/voicemail_export/
  1001/
    5551234567_20240115_143000.wav
    5559876543_20240115_150000.wav
  1002/
    5551112222_20240116_091500.wav
  1003/
    5553334444_20240116_103000.wav
```

**Filename Format:** `{caller_id}_{YYYYMMDD}_{HHMMSS}.wav`

Example: `5551234567_20240115_143000.wav`
- Caller ID: 5551234567
- Date: January 15, 2024
- Time: 14:30:00 (2:30 PM)

**Import Command:**
```bash
python scripts/import_merlin_voicemail.py \
    --audio-dir /voicemail_export \
    --parse-filenames
```

## Importing Voicemail PINs

If you only need to import PINs without voicemail messages:

**PIN CSV Format (pins.csv):**
```csv
extension,pin
1001,1234
1002,5678
1003,9999
```

**Import Command:**
```bash
python scripts/import_merlin_voicemail.py --pins pins.csv
```

**Important PIN Requirements:**
- Must be exactly 4 digits
- Only numeric characters (0-9)
- Each extension can have one PIN

## Importing Custom Greetings

Import personalized voicemail greetings for each mailbox.

**Directory Structure:**
```
/greetings/
  1001_greeting.wav
  1002_greeting.wav
  1003_greeting.wav
```

**Filename Format:** `{extension}_greeting.wav`

**Import Command:**
```bash
python scripts/import_merlin_voicemail.py \
    --greetings-dir /path/to/greetings
```

## Complete Import Example

Import everything at once:

```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files \
    --pins pins.csv \
    --greetings-dir /path/to/greetings
```

## Dry Run Mode

Preview the import without making any changes:

```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files \
    --dry-run
```

This will show what would be imported without actually importing anything.

## Step-by-Step Migration Process

### Step 1: Export Data from Merlin Legend

**Note:** AT&T Merlin Legend uses proprietary formats, so you may need:
- Technical assistance from your phone system vendor
- Access to the Merlin Legend administration interface
- Backup files from the system's storage

**What to export:**
1. All voicemail audio files (convert to WAV if needed)
2. Mailbox configurations and PINs
3. Custom greeting recordings
4. Voicemail metadata (timestamps, caller IDs, etc.)

### Step 2: Prepare Data Files

**Option A: Create CSV**
1. Create a spreadsheet with columns: extension, caller_id, timestamp, audio_file, duration, listened, voicemail_pin
2. Fill in data for each voicemail message
3. Save as CSV file

**Option B: Organize Files by Directory**
1. Create a folder for each extension (e.g., 1001/, 1002/)
2. Rename audio files using format: `{caller_id}_{YYYYMMDD}_{HHMMSS}.wav`
3. Place files in appropriate extension folders

**Option C: Create JSON**
1. Create JSON file following the format shown above
2. Include all voicemail messages and PINs

### Step 3: Verify Extensions Exist

Make sure all extensions referenced in your import data exist in the PBX:

```bash
# List extensions from database
python scripts/list_extensions_from_db.py

# Or check config.yml
grep -A 2 'number:' config.yml
```

If extensions are missing, add them:
```bash
# Using admin interface
python main.py
# Then open http://localhost:8080/admin/

# Or add to config.yml manually
```

### Step 4: Test with Dry Run

Always test first:

```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files \
    --dry-run
```

Review the output carefully. It should show:
- Number of messages found
- Each message with details
- Number of PINs found
- Any warnings or errors

### Step 5: Perform Import

If dry run looks good, perform the actual import:

```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files
```

### Step 6: Verify Import

Check that voicemails were imported:

```bash
# Check voicemail directory
ls -R voicemail/

# Check database (if using PostgreSQL)
psql -U pbx_user -d pbx_system -c "SELECT extension_number, COUNT(*) FROM voicemail_messages GROUP BY extension_number;"

# Or SQLite
sqlite3 pbx.db "SELECT extension_number, COUNT(*) FROM voicemail_messages GROUP BY extension_number;"
```

### Step 7: Test Access

1. Start the PBX: `python main.py`
2. Register a phone to an extension
3. Dial `*{extension}` to access voicemail (e.g., `*1001`)
4. Enter the PIN when prompted
5. Verify messages are accessible

## Troubleshooting

### Issue: "Audio file not found"

**Cause:** Script can't locate the WAV files

**Solutions:**
- Verify `--audio-dir` path is correct
- Check that audio file names in metadata match actual files
- Ensure WAV files are in correct subdirectories

### Issue: "Invalid PIN format"

**Cause:** PIN doesn't meet requirements

**Solutions:**
- Ensure PINs are exactly 4 digits
- Remove any non-numeric characters
- Don't use spaces or special characters

### Issue: "Extension not found"

**Cause:** Extension doesn't exist in PBX

**Solutions:**
- Add extensions using admin interface
- Or add to config.yml and restart PBX
- Run `python scripts/migrate_extensions_to_db.py` if needed

### Issue: "Database connection failed"

**Cause:** Database not available

**Solutions:**
- Check database is running: `sudo systemctl status postgresql`
- Verify config.yml database settings
- Run `python scripts/verify_database.py` for diagnostics
- Import will still work (files only) but won't store metadata in database

### Issue: "Message already exists"

**Cause:** Message with same ID already imported

**Solutions:**
- This is normal if re-running import
- Message is skipped automatically
- Check if duplicate data in source files

### Issue: Timestamp parsing errors

**Cause:** Timestamp format not recognized

**Solutions:**
- Use ISO format: `2024-01-15T14:30:00`
- Or common format: `2024-01-15 14:30:00`
- Check for typos in timestamp column

## Audio File Format Requirements

**Recommended Format:**
- **Codec:** PCM (uncompressed)
- **Sample Rate:** 8000 Hz (phone quality) or 16000 Hz
- **Bit Depth:** 16-bit
- **Channels:** Mono (1 channel)
- **Format:** WAV

**Converting Audio Files:**

If your Merlin Legend exports are in a different format, convert them:

```bash
# Using ffmpeg (install with: sudo apt-get install ffmpeg)

# Convert to WAV
ffmpeg -i input.au -ar 8000 -ac 1 output.wav

# Batch convert
for f in *.au; do ffmpeg -i "$f" -ar 8000 -ac 1 "${f%.au}.wav"; done
```

## Database Storage

Voicemail data is stored using a hybrid approach:

- **Database** (PostgreSQL/SQLite): Stores metadata (caller ID, timestamp, duration, listened status)
- **File System**: Stores actual WAV audio files

This is the industry-standard approach that:
- Keeps database lightweight and fast
- Avoids storing large BLOBs
- Allows efficient querying
- Preserves audio accessibility

See [VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md) for database configuration details.

## Security Considerations

1. **Protect PINs**: Store PIN files securely and delete after import
2. **Verify Data**: Always use `--dry-run` first
3. **Backup Original Data**: Keep original Merlin export as backup
4. **Audit Trail**: Import creates logs in `logs/pbx.log`
5. **File Permissions**: Ensure voicemail files have appropriate permissions

```bash
# Set appropriate permissions after import
chmod 640 voicemail/*/*.wav
chown -R pbx:pbx voicemail/
```

## Best Practices

1. **Test with Small Dataset First**: Import a few messages to verify process
2. **Use Dry Run**: Always preview with `--dry-run` before actual import
3. **Verify Extensions**: Ensure all extensions exist before importing
4. **Document PINs**: Keep secure record of voicemail PINs
5. **Backup Database**: Backup database before large imports
6. **Monitor Disk Space**: Voicemail audio files can be large

## Example Templates

### Example CSV Template

Create a file named `voicemail_template.csv`:
```csv
extension,caller_id,timestamp,audio_file,duration,listened,voicemail_pin
1001,5551234567,2024-01-15 14:30:00,msg001.wav,45,false,1234
```

### Example JSON Template

Create a file named `voicemail_template.json`:
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
    "1001": "1234"
  }
}
```

### Example PINs CSV Template

Create a file named `pins_template.csv`:
```csv
extension,pin
1001,1234
1002,5678
1003,9999
```

## Advanced Usage

### Import Only New Messages

The script automatically skips existing messages based on message ID:

```bash
# This is safe to run multiple times
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files
```

### Custom Config File

Use a different configuration file:

```bash
python scripts/import_merlin_voicemail.py \
    --csv voicemail_data.csv \
    --audio-dir /path/to/wav/files \
    --config /path/to/custom_config.yml
```

### Combining Multiple Sources

Import from multiple sources in one command:

```bash
python scripts/import_merlin_voicemail.py \
    --csv january_voicemails.csv \
    --json february_voicemails.json \
    --audio-dir /voicemail_archive \
    --pins all_pins.csv \
    --greetings-dir /custom_greetings
```

## Getting Help

### Check Import Script Help

```bash
python scripts/import_merlin_voicemail.py --help
```

### View Logs

```bash
tail -f logs/pbx.log
```

### Verify Database

```bash
python scripts/verify_database.py
```

### List Imported Voicemails

```bash
# PostgreSQL
psql -U pbx_user -d pbx_system -c "SELECT * FROM voicemail_messages ORDER BY created_at DESC LIMIT 10;"

# SQLite
sqlite3 pbx.db "SELECT * FROM voicemail_messages ORDER BY created_at DESC LIMIT 10;"
```

## Related Documentation

- [VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md) - Database configuration
- [VOICEMAIL_EMAIL_GUIDE.md](VOICEMAIL_EMAIL_GUIDE.md) - Email notifications
- [VOICEMAIL_CUSTOM_GREETING_GUIDE.md](VOICEMAIL_CUSTOM_GREETING_GUIDE.md) - Custom greetings
- [README.md](README.md) - Main PBX documentation

## Support

For issues or questions:
1. Check this guide thoroughly
2. Review logs: `logs/pbx.log`
3. Run diagnostic tools: `python scripts/verify_database.py`
4. Open a GitHub issue with diagnostic output

---

**Note:** The AT&T Merlin Legend system uses proprietary formats. You may need assistance from your telecom vendor or a specialist familiar with legacy AT&T/Lucent PBX systems to extract data from the original system.
