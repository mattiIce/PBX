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

## Updating Phone Extension When Reprovisioning

When you reprovision a phone to a different extension (e.g., moving a phone with MAC `001565123456` from extension `1001` to extension `1002`), you need to update the `registered_phones` table to reflect this change. Otherwise, you may end up with duplicate entries for the same MAC address.

### Why This Matters

The `registered_phones` table tracks which phones are registered to which extensions. When you move a phone to a different extension:

1. **Provisioning Configuration**: Update in `config.yml` or via the Admin Panel to change the phone's extension
2. **Registered Phones Table**: Update the database to reflect the new extension assignment

If you don't update the database, the system may have stale data showing the phone registered to the old extension.

### Option 1: Update Extension via SQL

**PostgreSQL:**
```bash
psql -h localhost -U pbx_user -d pbx_system << EOF
-- Update phone's extension by MAC address
UPDATE registered_phones 
SET extension_number = '1002', last_registered = CURRENT_TIMESTAMP
WHERE mac_address = '001565123456';

-- Verify the change
SELECT mac_address, extension_number, ip_address, last_registered 
FROM registered_phones 
WHERE mac_address = '001565123456';
EOF
```

**SQLite:**
```bash
sqlite3 pbx_system.db << EOF
-- Update phone's extension by MAC address
UPDATE registered_phones 
SET extension_number = '1002', last_registered = datetime('now')
WHERE mac_address = '001565123456';

-- Verify the change
SELECT mac_address, extension_number, ip_address, last_registered 
FROM registered_phones 
WHERE mac_address = '001565123456';
EOF
```

### Option 2: Delete Old Registration and Let Phone Re-register

A simpler approach is to remove the old registration and let the phone register again with its new extension:

**PostgreSQL:**
```bash
psql -h localhost -U pbx_user -d pbx_system -c "DELETE FROM registered_phones WHERE mac_address = '001565123456';"
```

**SQLite:**
```bash
sqlite3 pbx_system.db "DELETE FROM registered_phones WHERE mac_address = '001565123456';"
```

After deletion, when the phone reboots and registers with its new extension, it will create a fresh entry in the table.

### Option 3: Using the Provided Script (Recommended)

The PBX system includes a ready-to-use script for updating phone extensions:

```bash
python scripts/update_phone_extension.py <mac_address> <new_extension>
```

Example:
```bash
python scripts/update_phone_extension.py 001565123456 1002
# or with colons in MAC address:
python scripts/update_phone_extension.py 00:15:65:12:34:56 1002
```

The script will:
- Connect to your configured database (PostgreSQL or SQLite)
- Show you the current phone information
- Ask for confirmation before making changes
- Update the extension and verify the change
- Provide next steps for completing the reprovisioning

### Option 4: Create Your Own Python Script

If you prefer to create a custom script, here's an example:

```python
#!/usr/bin/env python3
"""
Update phone extension in registered_phones table
"""
import psycopg2  # or sqlite3 for SQLite
from datetime import datetime

# For PostgreSQL
def update_phone_extension_postgresql(mac_address, new_extension):
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='pbx_system',
        user='pbx_user',
        password='YOUR_PASSWORD'  # Update with your password
    )
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE registered_phones SET extension_number = %s, last_registered = %s WHERE mac_address = %s",
        (new_extension, datetime.now(), mac_address)
    )
    rows_affected = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✓ Updated {rows_affected} phone(s) - MAC {mac_address} -> Extension {new_extension}")

# For SQLite
def update_phone_extension_sqlite(mac_address, new_extension):
    import sqlite3
    conn = sqlite3.connect('pbx_system.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE registered_phones SET extension_number = ?, last_registered = ? WHERE mac_address = ?",
        (new_extension, datetime.now(), mac_address)
    )
    rows_affected = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✓ Updated {rows_affected} phone(s) - MAC {mac_address} -> Extension {new_extension}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python update_phone_extension.py <mac_address> <new_extension>")
        print("Example: python update_phone_extension.py 001565123456 1002")
        sys.exit(1)
    
    mac = sys.argv[1]
    ext = sys.argv[2]
    
    # Uncomment the appropriate line below for your database type:
    # update_phone_extension_postgresql(mac, ext)  # For PostgreSQL
    # update_phone_extension_sqlite(mac, ext)      # For SQLite
```

Save as `update_phone_extension.py` and run:
```bash
python update_phone_extension.py 001565123456 1002
```

### Option 5: Using the PBX Python API

If you have access to the PBX code, you can use the `RegisteredPhonesDB` class:

```python
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB
from pbx.utils.config import Config

# Load configuration
config = Config("config.yml")

# Connect to database
db = DatabaseBackend(config)
db.connect()

# Create registered phones DB instance
phones_db = RegisteredPhonesDB(db)

# Update phone extension
success = phones_db.update_phone_extension(
    mac_address="001565123456",
    new_extension_number="1002"
)

if success:
    print("✓ Phone extension updated successfully")
else:
    print("✗ Failed to update phone extension")

# Disconnect
db.disconnect()
```

### Best Practice: Complete Reprovisioning Workflow

When moving a phone to a different extension, follow these steps:

1. **Update Provisioning Configuration:**
   - Via Admin Panel: Navigate to "Phone Provisioning" tab, edit the device, change extension
   - Via `config.yml`: Update the device's extension number in the `provisioning.devices` section

2. **Update Registered Phones Table:**
   - Use one of the options above to update or delete the old registration

3. **Reboot the Phone:**
   - Power cycle the phone or use the phone's menu to reboot
   - The phone will fetch new configuration with the updated extension

4. **Verify Registration:**
   - Check the Admin Panel's "Registered Phones" tab
   - Confirm the phone shows the new extension

### Troubleshooting Duplicate Entries

If you end up with duplicate entries (same MAC, different extensions), you can clean them up:

**PostgreSQL:**
```bash
psql -h localhost -U pbx_user -d pbx_system << EOF
-- Find duplicates
SELECT mac_address, extension_number, last_registered 
FROM registered_phones 
WHERE mac_address = '001565123456'
ORDER BY last_registered DESC;

-- Keep only the most recent registration
DELETE FROM registered_phones 
WHERE mac_address = '001565123456' 
AND id NOT IN (
    SELECT id FROM registered_phones 
    WHERE mac_address = '001565123456' 
    ORDER BY last_registered DESC 
    LIMIT 1
);
EOF
```

**SQLite:**
```bash
sqlite3 pbx_system.db << EOF
-- Find duplicates
SELECT mac_address, extension_number, last_registered 
FROM registered_phones 
WHERE mac_address = '001565123456'
ORDER BY last_registered DESC;

-- Keep only the most recent registration
DELETE FROM registered_phones 
WHERE mac_address = '001565123456' 
AND id NOT IN (
    SELECT id FROM registered_phones 
    WHERE mac_address = '001565123456' 
    ORDER BY last_registered DESC 
    LIMIT 1
);
EOF
```

## Related Documentation

- [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md) - Phone provisioning setup
- [PHONE_REGISTRATION_TRACKING.md](PHONE_REGISTRATION_TRACKING.md) - How phone registration tracking works
- [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md) - Database setup instructions
