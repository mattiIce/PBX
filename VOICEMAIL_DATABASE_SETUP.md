# Voicemail Database Setup Guide

## Overview

The PBX system stores voicemail data using a hybrid approach for optimal performance:

- **Database (PostgreSQL/SQLite)**: Stores voicemail metadata (caller ID, timestamp, duration, listened status, etc.)
- **File System**: Stores the actual audio WAV files

This is the industry-standard approach that:
- Keeps the database lightweight and fast
- Avoids storing large BLOBs in the database
- Allows efficient querying of voicemail metadata
- Preserves audio file accessibility

## Quick Verification

To verify your database is properly configured for voicemail storage, run:

```bash
python scripts/verify_database.py
```

This diagnostic tool will check:
- PostgreSQL driver installation
- Database configuration
- Database connectivity
- Table existence
- Current voicemail count

## Database Configuration

### PostgreSQL (Recommended for Production)

1. **Install PostgreSQL**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install postgresql postgresql-contrib
   
   # CentOS/RHEL
   sudo yum install postgresql postgresql-server
   sudo postgresql-setup initdb
   sudo systemctl start postgresql
   ```

2. **Create Database and User**:
   ```bash
   sudo -u postgres psql
   ```
   
   Then in the PostgreSQL prompt:
   ```sql
   CREATE DATABASE pbx_system;
   CREATE USER pbx_user WITH PASSWORD 'YourSecurePassword123!';
   GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;
   \q
   ```

3. **Configure config.yml**:
   ```yaml
   database:
     type: postgresql
     host: localhost
     port: 5432
     name: pbx_system
     user: pbx_user
     password: YourSecurePassword123!  # Use environment variables in production
   ```

4. **Install Python Driver**:
   ```bash
   pip install psycopg2-binary
   ```

5. **Verify Connection**:
   ```bash
   python scripts/verify_database.py
   ```

### SQLite (Recommended for Development/Testing)

1. **Configure config.yml**:
   ```yaml
   database:
     type: sqlite
     path: pbx.db
   ```

2. **No additional installation needed** - SQLite is included with Python

3. **Verify Configuration**:
   ```bash
   python scripts/verify_database.py
   ```

## How Voicemails Are Stored

### When a Voicemail is Saved

1. **Audio File** is written to disk:
   ```
   voicemail/1001/caller_20231204_143022.wav
   ```

2. **Metadata Record** is inserted into database:
   ```sql
   INSERT INTO voicemail_messages 
   (message_id, extension_number, caller_id, file_path, duration, listened, created_at)
   VALUES (...)
   ```

### Database Schema

The `voicemail_messages` table stores:

```sql
CREATE TABLE voicemail_messages (
    id                 SERIAL PRIMARY KEY,
    message_id         VARCHAR(100) UNIQUE NOT NULL,  -- Unique identifier
    extension_number   VARCHAR(20) NOT NULL,           -- Recipient extension
    caller_id          VARCHAR(50),                    -- Caller's number/ID
    file_path          VARCHAR(255),                   -- Path to WAV file
    duration           INTEGER,                        -- Duration in seconds
    listened           BOOLEAN DEFAULT FALSE,          -- Read status
    created_at         TIMESTAMP DEFAULT NOW()         -- When received
);
```

### Code Implementation

The voicemail system automatically handles database operations:

```python
# Save voicemail (pbx/features/voicemail.py, line 96-120)
if self.database and self.database.enabled:
    query = """
    INSERT INTO voicemail_messages 
    (message_id, extension_number, caller_id, file_path, duration, listened, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    self.database.execute(query, params)
```

## Troubleshooting

### Issue: "Database backend not available"

**Symptoms:**
- Log shows: "Database backend not available - running without database"
- Voicemails saved only as files
- No database records created

**Causes & Solutions:**

1. **PostgreSQL not running**:
   ```bash
   sudo systemctl status postgresql
   sudo systemctl start postgresql
   ```

2. **Database doesn't exist**:
   ```bash
   sudo -u postgres createdb pbx_system
   ```

3. **Wrong credentials**:
   - Check `config.yml` database section
   - Verify user/password with: `psql -U pbx_user -d pbx_system`

4. **Connection refused**:
   - Check PostgreSQL is listening: `sudo netstat -plnt | grep 5432`
   - Check firewall rules: `sudo ufw status`
   - Verify `pg_hba.conf` allows local connections

5. **psycopg2 not installed**:
   ```bash
   pip install psycopg2-binary
   ```

### Issue: "Tables don't exist"

If tables haven't been created:

```python
python -c "from pbx.core.pbx import PBXCore; pbx = PBXCore(); pbx.database.create_tables()"
```

Or they will be created automatically on first PBX start.

### Checking Current Status

**Check if voicemails are in database:**

```bash
# PostgreSQL
psql -U pbx_user -d pbx_system -c "SELECT COUNT(*) FROM voicemail_messages;"

# SQLite
sqlite3 pbx.db "SELECT COUNT(*) FROM voicemail_messages;"
```

**Check voicemail files on disk:**

```bash
find voicemail/ -name "*.wav" -type f
```

**View voicemail records:**

```bash
# PostgreSQL
psql -U pbx_user -d pbx_system -c "SELECT message_id, extension_number, caller_id, duration, listened FROM voicemail_messages ORDER BY created_at DESC LIMIT 10;"
```

## Migration from File-Only to Database

If you've been running without database and want to migrate existing voicemails:

1. **Set up database** using instructions above
2. **Restart PBX** - new voicemails will use database
3. **Old voicemail files** will still be accessible but won't have database records
4. **Optional**: Create a migration script to import old files into database

Example migration script:

```python
import os
from datetime import datetime
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend

config = Config('config.yml')
db = DatabaseBackend(config)
db.connect()

for root, dirs, files in os.walk('voicemail'):
    for file in files:
        if file.endswith('.wav'):
            # Parse filename: caller_YYYYMMDD_HHMMSS.wav
            parts = file[:-4].split('_')
            if len(parts) >= 3:
                caller_id = parts[0]
                date_str = parts[1]
                time_str = parts[2]
                
                extension = os.path.basename(root)
                file_path = os.path.join(root, file)
                message_id = file[:-4]
                
                # Insert into database
                query = """
                INSERT INTO voicemail_messages 
                (message_id, extension_number, caller_id, file_path, listened, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                db.execute(query, (message_id, extension, caller_id, file_path, False, timestamp))

db.disconnect()
```

## Testing

Run the test suite to verify database integration:

```bash
python tests/test_voicemail_database.py
```

Expected output:
```
✓ Database configuration loads correctly
✓ Database backend initializes correctly
✓ Voicemail database integration works correctly
✓ Voicemail system works without database
```

## Benefits of Database Storage

### With Database (Recommended)
- ✅ Fast metadata queries
- ✅ Efficient filtering (unread, by date, by caller)
- ✅ Easy reporting and statistics
- ✅ Scalable for large deployments
- ✅ Proper data integrity and transactions
- ✅ Better support for features like search, sorting, bulk operations

### Without Database (File-only)
- ⚠️ Slower queries (must scan file system)
- ⚠️ Limited filtering capabilities
- ⚠️ No efficient way to track listened status
- ⚠️ Difficult to generate reports
- ⚠️ Risk of metadata loss (filename-based only)

## Security Considerations

1. **Never commit passwords** to version control
2. **Use environment variables** for production credentials:
   ```yaml
   database:
     password: ${DATABASE_PASSWORD}
   ```

3. **Restrict database access**:
   ```sql
   -- PostgreSQL: Limit to localhost only
   # In pg_hba.conf:
   host    pbx_system    pbx_user    127.0.0.1/32    md5
   ```

4. **Regular backups**:
   ```bash
   # PostgreSQL
   pg_dump -U pbx_user pbx_system > backup_$(date +%Y%m%d).sql
   
   # Files
   tar -czf voicemail_backup_$(date +%Y%m%d).tar.gz voicemail/
   ```

## Support

For issues or questions:
1. Run `python scripts/verify_database.py` for diagnostics
2. Check logs: `logs/pbx.log`
3. Review this documentation
4. Open a GitHub issue with diagnostic output

---

**Remember**: The current implementation is correct! Audio files belong on the file system, metadata belongs in the database. This is the industry-standard approach for storing voicemails.
