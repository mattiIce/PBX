# How to Clear Registered Phones Database Table

This document provides instructions for manually clearing the `registered_phones` table in the PBX database.

## Why Clear This Table?

The `registered_phones` table tracks phone registration history including MAC addresses, IP addresses, and extension associations. You may want to clear this table:
- To start fresh after testing
- To remove stale registration data
- To clean up before production deployment
- After network changes or phone replacements

**Note:** This does NOT affect phone provisioning configuration (that's stored separately). Phones will re-populate this table when they register again.

## Option 1: PostgreSQL Database

If you're using PostgreSQL (default production setup):

### Using psql Command Line:

```bash
# Connect to the database
psql -h localhost -U pbx_user -d pbx_system

# Clear the table
TRUNCATE TABLE registered_phones;

# Verify it's empty
SELECT COUNT(*) FROM registered_phones;

# Exit
\q
```

### Using SQL in One Command:

```bash
psql -h localhost -U pbx_user -d pbx_system -c "TRUNCATE TABLE registered_phones;"
```

### Alternative: Drop and Recreate:

If TRUNCATE doesn't work, you can drop and recreate:

```bash
psql -h localhost -U pbx_user -d pbx_system << EOF
DROP TABLE IF EXISTS registered_phones;
CREATE TABLE registered_phones (
    id SERIAL PRIMARY KEY,
    extension_number VARCHAR(20),
    ip_address VARCHAR(45),
    mac_address VARCHAR(17),
    user_agent TEXT,
    contact_uri TEXT,
    first_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_phones_mac ON registered_phones(mac_address);
CREATE INDEX IF NOT EXISTS idx_phones_extension ON registered_phones(extension_number);
EOF
```

## Option 2: SQLite Database

If you're using SQLite (for testing):

### Using sqlite3 Command Line:

```bash
# Connect to the database
sqlite3 pbx_system.db

# Clear the table
DELETE FROM registered_phones;

# Verify it's empty
SELECT COUNT(*) FROM registered_phones;

# Exit
.quit
```

### Using SQL in One Command:

```bash
sqlite3 pbx_system.db "DELETE FROM registered_phones;"
```

### Alternative: Drop and Recreate:

```bash
sqlite3 pbx_system.db << EOF
DROP TABLE IF EXISTS registered_phones;
CREATE TABLE registered_phones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extension_number TEXT,
    ip_address TEXT,
    mac_address TEXT,
    user_agent TEXT,
    contact_uri TEXT,
    first_registered TEXT,
    last_registered TEXT
);
CREATE INDEX IF NOT EXISTS idx_phones_mac ON registered_phones(mac_address);
CREATE INDEX IF NOT EXISTS idx_phones_extension ON registered_phones(extension_number);
EOF
```

## Option 3: Using Python Script

Create a script to clear the table programmatically:

```python
#!/usr/bin/env python3
"""
Clear registered phones table
"""
import psycopg2  # or sqlite3 for SQLite

# For PostgreSQL
def clear_registered_phones_postgresql():
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='pbx_system',
        user='pbx_user',
        password='YOUR_PASSWORD'  # Update with your password
    )
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE registered_phones;")
    conn.commit()
    cursor.close()
    conn.close()
    print("✓ Registered phones table cleared (PostgreSQL)")

# For SQLite
def clear_registered_phones_sqlite():
    import sqlite3
    conn = sqlite3.connect('pbx_system.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registered_phones;")
    conn.commit()
    cursor.close()
    conn.close()
    print("✓ Registered phones table cleared (SQLite)")

if __name__ == '__main__':
    # Uncomment the appropriate line for your database:
    clear_registered_phones_postgresql()
    # clear_registered_phones_sqlite()
```

Save as `clear_registered_phones.py` and run:
```bash
python clear_registered_phones.py
```

## Option 4: Using the API (Future Enhancement)

You could add an API endpoint to clear this table:

```bash
# Not implemented yet, but could be added as:
curl -X POST http://localhost:8080/api/registered-phones/clear
```

## Verification

After clearing, verify the table is empty:

**PostgreSQL:**
```bash
psql -h localhost -U pbx_user -d pbx_system -c "SELECT COUNT(*) FROM registered_phones;"
```

**SQLite:**
```bash
sqlite3 pbx_system.db "SELECT COUNT(*) FROM registered_phones;"
```

Expected output: `0`

## What Happens After Clearing?

1. **Immediate Effect:**
   - Admin panel "Registered Phones" tab will show empty
   - No registered phone history will be visible
   - MAC/IP correlation data is lost

2. **When Phones Register Again:**
   - SIP REGISTER messages will populate the table
   - Phone provisioning requests will add MAC/IP mappings
   - Data will rebuild automatically over time

3. **What's NOT Affected:**
   - Phone provisioning configuration (devices registered in `provisioning.devices`)
   - Extension configurations
   - Active SIP registrations (in-memory only)
   - Voicemail, CDR, or other data

## Automated Clearing on Startup (Not Recommended for Production)

If you want to automatically clear this table every time the PBX starts, you can add code to the PBX initialization, but this is **NOT recommended for production** as you'll lose all registration history.

For testing environments only, you could modify `pbx/core/pbx.py` to add:

```python
# In PBXCore.__init__() after database connection
if self.registered_phones_db and self.registered_phones_db.db.enabled:
    try:
        self.logger.warning("Clearing registered_phones table (testing mode)")
        cursor = self.registered_phones_db.db.connection.cursor()
        if self.registered_phones_db.db.db_type == 'postgresql':
            cursor.execute("TRUNCATE TABLE registered_phones;")
        else:
            cursor.execute("DELETE FROM registered_phones;")
        self.registered_phones_db.db.connection.commit()
        cursor.close()
        self.logger.info("✓ Registered phones table cleared")
    except Exception as e:
        self.logger.error(f"Failed to clear registered phones: {e}")
```

## Best Practices

1. **Backup First:** Before clearing, consider backing up:
   ```bash
   # PostgreSQL
   pg_dump -h localhost -U pbx_user -d pbx_system -t registered_phones > registered_phones_backup.sql
   
   # SQLite
   sqlite3 pbx_system.db ".dump registered_phones" > registered_phones_backup.sql
   ```

2. **Inform Users:** If phones are actively registered, clearing this table won't affect their operation, but tracking data will be lost.

3. **Production:** Only clear in production if absolutely necessary. This data is useful for troubleshooting and monitoring.

4. **Testing:** Feel free to clear frequently in test environments to start fresh.

## Troubleshooting

### Permission Denied (PostgreSQL)

```bash
# Grant permissions if needed
psql -h localhost -U postgres -d pbx_system -c "GRANT ALL PRIVILEGES ON TABLE registered_phones TO pbx_user;"
```

### Database File Not Found (SQLite)

```bash
# Find the database file
find . -name "*.db" -type f

# Common locations:
# ./pbx_system.db
# ./pbx/pbx_system.db
```

### Table Doesn't Exist

If the table doesn't exist, the PBX will create it automatically on next startup or you can create it manually using the CREATE TABLE statements above.

## Related Documentation

- [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md) - Phone provisioning setup
- [PHONE_REGISTRATION_TRACKING.md](PHONE_REGISTRATION_TRACKING.md) - How phone registration tracking works
- [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md) - Database setup instructions
