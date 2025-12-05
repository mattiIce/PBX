# Database Migration Guide: Extensions from config.yml to Database

This guide explains how to migrate your extensions from `config.yml` to the database for centralized management.

## Why Migrate to Database?

**Benefits:**
- ✅ **Centralized Management**: All extensions in one place, separate from configuration
- ✅ **Better for AD Integration**: AD sync writes directly to database
- ✅ **Admin Interface**: Manage extensions through web UI at `/admin/`
- ✅ **API Support**: Full CRUD operations via REST API
- ✅ **No Config File Edits**: Add/modify extensions without touching config.yml
- ✅ **Better Tracking**: Metadata like `ad_synced`, `ad_username` automatically tracked
- ✅ **Persistence**: Extensions survive config file changes

## Prerequisites

1. **Database must be configured and running**
   - PostgreSQL (recommended for production)
   - SQLite (good for testing/development)

2. **Database tables must be initialized**
   ```bash
   python scripts/init_database.py
   ```

3. **Verify database connection**
   ```bash
   python scripts/verify_database.py
   ```

## Migration Steps

### Step 1: Backup Your Config

Create a backup of your current config.yml:

```bash
cp config.yml config.yml.backup_$(date +%Y%m%d)
```

### Step 2: Run Migration (Dry Run First)

Test the migration without making changes:

```bash
python scripts/migrate_extensions_to_db.py --dry-run
```

Review the output to ensure all extensions will be migrated correctly.

### Step 3: Run Actual Migration

If the dry run looks good, run the actual migration:

```bash
python scripts/migrate_extensions_to_db.py
```

**Output example:**
```
======================================================================
Extension Migration: config.yml → Database
======================================================================

Found 4 extensions in config.yml

→ Extension 1001 (Codi Mattinson)
  Email: cmattinson@albl.com
  Allow external: True
  AD synced: False
  ✓ Migrated successfully

→ Extension 1002 (Bill Sautter)
  ...

======================================================================
Migration Summary
======================================================================
Migrated: 4
Skipped:  0 (already in database)
Errors:   0

✓ Migration completed successfully!
```

### Step 4: Verify Migration

List extensions from the database to verify:

```bash
python scripts/list_extensions_from_db.py
```

You should see all your extensions with their details.

### Step 5: Test the System

Start the PBX and verify extensions are loaded from database:

```bash
python main.py
```

Check the logs for:
```
INFO - Loading X extensions from database
INFO - Loaded extension 1001 (Name)
...
```

### Step 6: Clean Up config.yml (Optional)

Once you've verified everything works, you can remove extensions from config.yml:

```bash
python scripts/cleanup_config_extensions.py
```

This will:
- Create a backup of config.yml
- Remove the `extensions:` section
- Add comments explaining where extensions are now stored

**Important:** The PBX will still work with extensions in config.yml as a fallback, so this step is optional. The system loads from database first, then falls back to config.yml if database is unavailable.

## After Migration

### Managing Extensions

**Via Admin Web Interface:**
1. Open http://YOUR_SERVER_IP:8080/admin/ (replace YOUR_SERVER_IP with your actual server address, e.g., localhost, 192.168.1.100)
2. Go to "Extensions" tab
3. Use "Add Extension" button to create new extensions
4. Click "Edit" or "Delete" on existing extensions

**Via API:**
```bash
# List all extensions
curl http://localhost:8080/api/extensions

# Add new extension
curl -X POST http://localhost:8080/api/extensions \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1005",
    "name": "New User",
    "email": "newuser@company.com",
    "password": "securepassword",
    "allow_external": true
  }'

# Update extension
curl -X PUT http://localhost:8080/api/extensions/1005 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "email": "newemail@company.com"
  }'

# Delete extension
curl -X DELETE http://localhost:8080/api/extensions/1005
```

**Via Database Scripts:**
```bash
# List all extensions
python scripts/list_extensions_from_db.py

# List only AD-synced extensions
python scripts/list_extensions_from_db.py --ad-only
```

### Active Directory Integration

After migration, AD sync will write directly to the database:

```bash
# Sync users from AD to database
python scripts/sync_ad_users.py
```

Or use the admin web interface:
1. Open http://YOUR_SERVER_IP:8080/admin/ (replace YOUR_SERVER_IP with your server address)
2. Go to "Dashboard" tab
3. Click "Sync Users from AD" button

## Database Schema

The `extensions` table has the following structure:

```sql
CREATE TABLE extensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    allow_external BOOLEAN DEFAULT 1,
    voicemail_pin VARCHAR(10),
    ad_synced BOOLEAN DEFAULT 0,
    ad_username VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Rollback

If you need to rollback to using config.yml:

1. **Stop the PBX**
   ```bash
   # Press Ctrl+C or send SIGTERM
   ```

2. **Restore config.yml backup**
   ```bash
   cp config.yml.backup_YYYYMMDD config.yml
   ```

3. **Disable database** (optional)
   Edit config.yml:
   ```yaml
   database:
     type: sqlite
     path: /dev/null  # This will cause database to fail, forcing fallback to config
   ```

4. **Restart PBX**
   ```bash
   python main.py
   ```
   
   The system will automatically fall back to loading extensions from config.yml.

## Troubleshooting

### "Extensions already in database"

If you run the migration multiple times, extensions that already exist will be skipped:
```
⚠ Extension 1001 (Name) - Already in database, skipping
```

This is normal and safe.

### "Failed to connect to database"

Ensure:
1. Database is running (for PostgreSQL)
2. Database credentials in config.yml are correct
3. Database has been initialized: `python scripts/init_database.py`

### "No extensions found in config.yml"

This means your config.yml doesn't have an `extensions:` section, or it's empty. Check:
1. Config file path is correct
2. Extensions are defined in config.yml
3. YAML syntax is valid

### Extensions not loading after migration

Check the PBX logs:
```bash
python main.py | grep -i extension
```

If you see "Loading X extensions from database", it's working.
If you see "Loading X extensions from config.yml", database connection failed.

## Best Practices

1. **Always backup config.yml** before migration
2. **Run dry-run first** to preview changes
3. **Verify in database** after migration
4. **Test PBX startup** before cleaning up config.yml
5. **Keep config.yml backup** even after cleanup (for disaster recovery)
6. **Document custom fields** if you've added any to extensions
7. **Test all extension features** (registration, calling, voicemail) after migration

## Security Notes

### Password Storage

⚠️ **Important**: Currently, passwords are migrated as-is from config.yml to the database.

**For production deployment:**
1. Implement proper password hashing (bcrypt, PBKDF2, or Argon2)
2. Ensure FIPS mode is enabled: `security.fips_mode: true` in config.yml
3. Consider password complexity requirements
4. Implement password rotation policies

### Database Security

1. **Use strong database passwords**
2. **Restrict database access** to localhost or specific IPs
3. **Enable database authentication** (for PostgreSQL)
4. **Regular backups** of database
5. **Encrypt database** at rest (for sensitive deployments)

## Support

For issues or questions:
1. Check logs: `logs/pbx.log`
2. Verify database: `python scripts/verify_database.py`
3. List extensions: `python scripts/list_extensions_from_db.py`
4. Review this guide for troubleshooting steps
