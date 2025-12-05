# Extension Database Storage Guide

## Overview

Starting with this version, **extensions are stored in the database** instead of being hardcoded in `config.yml`. This provides:

- ✅ **Dynamic updates** without file edits or system restarts
- ✅ **Better scalability** for managing many extensions
- ✅ **Query capabilities** for searching and reporting
- ✅ **Active Directory sync** with proper tracking
- ✅ **Web interface management** for easy administration
- ✅ **Proper data integrity** with transactions

## What's Stored Where

### Database (Recommended for Production)
- ✅ **Extensions** - User accounts with phone numbers
- ✅ **Voicemail messages** - Metadata and tracking
- ✅ **Call Detail Records** - Call history and statistics
- ✅ **VIP Callers** - Priority caller database
- ✅ **Registered Phones** - Device tracking by MAC/IP

### Config.yml (System Configuration Only)
- Server settings (IP addresses, ports)
- Database connection details
- Feature flags (enabled/disabled)
- Integration credentials (AD, email SMTP)
- Dialplan patterns
- System-level settings

## Database Schema

The `extensions` table stores:

```sql
CREATE TABLE extensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number VARCHAR(20) UNIQUE NOT NULL,         -- Extension number
    name VARCHAR(255) NOT NULL,                  -- Display name
    email VARCHAR(255),                          -- Email for voicemail
    password_hash VARCHAR(255) NOT NULL,         -- SIP password
    allow_external BOOLEAN DEFAULT TRUE,         -- External calling permission
    voicemail_pin VARCHAR(10),                   -- Voicemail PIN
    ad_synced BOOLEAN DEFAULT FALSE,             -- Synced from Active Directory
    ad_username VARCHAR(100),                    -- AD username
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Migration from config.yml

If you have existing extensions in `config.yml`, migrate them to the database:

### Step 1: Backup Your Config

```bash
cp config.yml config.yml.backup
```

### Step 2: Run Migration Script

```bash
# Dry run to see what will be migrated
python scripts/migrate_extensions_to_db.py --dry-run

# Actually migrate
python scripts/migrate_extensions_to_db.py
```

Example output:
```
======================================================================
Extension Migration: config.yml → Database
======================================================================

Connecting to database...
✓ Connected to database

Ensuring database tables exist...
✓ Database tables ready

Found 4 extensions in config.yml

→ Extension 1001 (Codi Mattinson)
  Email: cmattinson@albl.com
  Allow external: True
  AD synced: False
  ✓ Migrated successfully

→ Extension 1002 (Bill Sautter)
  Email: bsautter@albl.com
  Allow external: True
  AD synced: False
  ✓ Migrated successfully

======================================================================
Migration Summary
======================================================================
Migrated: 4
Skipped:  0 (already in database)
Errors:   0

✓ Migration completed successfully!
```

### Step 3: Verify Migration

```bash
# List all extensions from database
python scripts/list_extensions_from_db.py

# List only AD-synced extensions
python scripts/list_extensions_from_db.py --ad-only
```

### Step 4: Optional Cleanup

After successful migration, you can optionally remove extensions from `config.yml` (keep as backup if desired):

```bash
# The system will now load extensions from database automatically
# Config.yml extensions are ignored when database is available
```

## Managing Extensions

### Via Admin Web Interface (Recommended)

1. Start the PBX system:
   ```bash
   python main.py
   ```

2. Open admin panel:
   ```
   http://localhost:8080/admin/
   ```

3. Go to **Extensions** tab

4. **Add Extension**: Click "➕ Add Extension"
   - Enter extension number (4 digits)
   - Enter name
   - Enter email (optional, for voicemail)
   - Set password (minimum 8 characters)
   - Toggle "Allow External Calls"

5. **Edit Extension**: Click "✏️ Edit" next to any extension
   - Update name, email, password
   - Change permissions
   - Note: AD-synced extensions show a green "AD" badge

6. **Delete Extension**: Click "🗑️ Delete"
   - Confirms before deletion
   - Cannot be undone (backup database first!)

### Via REST API

```bash
# Add extension
curl -X POST http://localhost:8080/api/extensions \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1005",
    "name": "New User",
    "email": "user@company.com",
    "password": "securepass123",
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

# List all extensions
curl http://localhost:8080/api/extensions
```

### Via Command Line Scripts

```bash
# List extensions from database
python scripts/list_extensions_from_db.py

# List only AD-synced extensions
python scripts/list_extensions_from_db.py --ad-only

# Migrate from config.yml
python scripts/migrate_extensions_to_db.py
```

## Active Directory Integration

When AD sync is enabled, extensions are automatically created/updated in the database:

### Configure AD Integration

Edit `config.yml`:

```yaml
integrations:
  active_directory:
    enabled: true
    server: ldaps://dc.example.com:636
    base_dn: DC=example,DC=com
    user_search_base: CN=Users,DC=example,DC=com
    bind_dn: CN=svc-pbx,CN=Users,DC=example,DC=com
    bind_password: ${AD_BIND_PASSWORD}  # Use environment variable
    use_ssl: true
    auto_provision: true
    deactivate_removed_users: true
```

### Test AD Integration

```bash
# Test AD connection and configuration
python scripts/test_ad_integration.py

# With verbose output
python scripts/test_ad_integration.py --verbose
```

### Sync Users from AD

```bash
# Sync users to database
python scripts/sync_ad_users.py

# Dry run (see what would be synced)
python scripts/sync_ad_users.py --dry-run
```

**What happens during sync:**
- ✅ New users with phone numbers → Creates extensions in database
- ✅ Existing users → Updates name, email (preserves password)
- ✅ Removed users → Deactivates extensions (sets `allow_external=false`)
- ✅ All synced extensions marked with `ad_synced=true` and AD username

**AD-synced extensions in admin interface:**
- Show green "AD" badge next to extension number
- Display AD username in extension details
- Can be edited (name, email, password)
- Permissions can be modified
- Can be deleted (will be recreated on next sync if user still in AD)

## Database Backends

### SQLite (Default, Development)

Easiest to set up, no server required:

```yaml
database:
  type: sqlite
  path: pbx.db
```

**Pros:**
- No setup required
- Single file database
- Perfect for testing and small deployments

**Cons:**
- Limited concurrent writes
- Not recommended for high-traffic production

### PostgreSQL (Recommended for Production)

Better performance and concurrency:

```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  name: pbx_system
  user: pbx_user
  password: ${DB_PASSWORD}  # Use environment variable
```

**Setup PostgreSQL:**

```bash
# Install PostgreSQL
sudo apt-get install postgresql

# Create database and user
sudo -u postgres createdb pbx_system
sudo -u postgres psql -c "CREATE USER pbx_user WITH PASSWORD 'YourPassword';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;"

# Verify connection
python scripts/verify_database.py
```

**Pros:**
- Excellent performance
- High concurrency support
- Advanced features (replication, backup)
- Industry standard

## Troubleshooting

### Extensions Not Loading

**Problem:** PBX starts but no extensions loaded

**Solution:**
```bash
# Check if database is connected
python scripts/verify_database.py

# Check extensions in database
python scripts/list_extensions_from_db.py

# If empty, migrate from config.yml
python scripts/migrate_extensions_to_db.py
```

### Can't Connect to Database

**Problem:** `Failed to connect to database`

**For SQLite:**
- Check file permissions on `pbx.db`
- Ensure directory is writable

**For PostgreSQL:**
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check credentials in `config.yml`
- Test connection: `psql -h localhost -U pbx_user -d pbx_system`

### AD Sync Not Working

**Problem:** AD sync doesn't create extensions in database

**Solution:**
```bash
# Test AD integration first
python scripts/test_ad_integration.py --verbose

# Check database connection
python scripts/verify_database.py

# Run sync with verbose output
python scripts/sync_ad_users.py --verbose
```

### Duplicate Extensions

**Problem:** Extension exists in both config.yml and database

**Solution:**
- Database takes precedence
- Extensions in config.yml are ignored when database is available
- You can safely remove extensions from config.yml after migration

## Backup and Recovery

### Backup Database

**SQLite:**
```bash
# Simple file copy
cp pbx.db pbx.db.backup

# Or use SQLite backup
sqlite3 pbx.db ".backup pbx.db.backup"
```

**PostgreSQL:**
```bash
# Dump database
pg_dump -U pbx_user pbx_system > pbx_backup.sql

# Or use pg_dump with compression
pg_dump -U pbx_user pbx_system | gzip > pbx_backup.sql.gz
```

### Restore Database

**SQLite:**
```bash
cp pbx.db.backup pbx.db
```

**PostgreSQL:**
```bash
# Drop and recreate database
sudo -u postgres dropdb pbx_system
sudo -u postgres createdb pbx_system
sudo -u postgres psql -U pbx_user pbx_system < pbx_backup.sql
```

## Best Practices

1. **Use PostgreSQL for production** - Better performance and reliability
2. **Backup regularly** - Automate daily database backups
3. **Use environment variables** - Don't hardcode passwords in config.yml
4. **Monitor database** - Check disk space and performance
5. **Test AD sync** - Use test_ad_integration.py before going live
6. **Migrate carefully** - Always backup before running migration
7. **Document changes** - Keep track of manual extension modifications
8. **Review AD syncs** - Check sync logs regularly for errors

## Security Considerations

### Password Storage

**IMPORTANT:** Passwords are currently stored without additional hashing in the database. This is acceptable for:
- Development and testing environments
- Internal networks behind firewalls
- Systems where the database itself is properly secured

**For production deployments**, consider implementing:
- Proper password hashing (bcrypt, PBKDF2, Argon2)
- Salt generation per password
- Configurable hash iterations
- Password complexity requirements

The SIP authentication system handles password verification. Database storage is used for credential lookup.

### Additional Security

- **Database Access**: Restrict database user permissions to only what's needed (no DROP, ALTER unless needed)
- **Backup Security**: Encrypt database backups containing sensitive data
- **AD Credentials**: Always use environment variables for AD bind passwords (`${AD_BIND_PASSWORD}`)
- **API Access**: Implement authentication for REST API endpoints in production
- **Network Security**: Use firewall rules to restrict database access
- **Audit Logging**: Monitor database access and modifications

## Performance Tuning

### Database Indexes

Indexes are automatically created for:
- Extension number (primary lookup)
- Email (for voicemail routing)
- AD sync status (for filtering)

### Connection Pooling

For high-traffic deployments, consider:
- Using connection pooling (pgBouncer for PostgreSQL)
- Caching frequently accessed extensions
- Implementing read replicas for reporting

## Future Enhancements

Planned features:
- [ ] Password hashing with bcrypt/PBKDF2
- [ ] Extension groups and departments
- [ ] Permission roles (admin, user, guest)
- [ ] API authentication and rate limiting
- [ ] Real-time extension status updates via WebSocket
- [ ] Extension usage statistics and reporting
- [ ] Bulk import/export tools

## Support

For issues:
1. Check logs: `logs/pbx.log`
2. Verify database: `python scripts/verify_database.py`
3. Test AD: `python scripts/test_ad_integration.py`
4. Review this documentation
5. Check GitHub issues

## Migration Checklist

Use this checklist when migrating to database storage:

- [ ] Backup `config.yml`
- [ ] Backup current database (if exists)
- [ ] Run database verification: `scripts/verify_database.py`
- [ ] Run migration dry-run: `scripts/migrate_extensions_to_db.py --dry-run`
- [ ] Review dry-run output
- [ ] Run actual migration: `scripts/migrate_extensions_to_db.py`
- [ ] Verify extensions: `scripts/list_extensions_from_db.py`
- [ ] Test SIP registration with a few extensions
- [ ] Test admin interface (add, edit, delete)
- [ ] If using AD: Test `scripts/test_ad_integration.py`
- [ ] If using AD: Run `scripts/sync_ad_users.py`
- [ ] Verify AD-synced extensions have "AD" badge in admin interface
- [ ] Document any custom extensions or configurations
- [ ] Set up automated database backups
- [ ] Monitor logs for any issues

✓ Migration complete!
