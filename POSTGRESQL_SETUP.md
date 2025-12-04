# PostgreSQL Setup Guide for PBX System

This guide will help you configure PostgreSQL for the PBX system to enable advanced database features.

**Note:** The PBX system stores voicemail metadata, CDR records, and VIP caller data in the database. Audio files are stored on the file system for optimal performance. See [VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md) for more details.

## Prerequisites

✅ PostgreSQL is already installed on your server

## Quick Setup

### 1. Create Database and User

Connect to PostgreSQL as the postgres user:

```bash
sudo -u postgres psql
```

Run the following SQL commands:

```sql
-- Create database
CREATE DATABASE pbx;

-- Create user
CREATE USER pbx_user WITH ENCRYPTED PASSWORD 'your_secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE pbx TO pbx_user;

-- Connect to the database
\c pbx

-- Grant schema privileges (PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO pbx_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pbx_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pbx_user;

-- Exit psql
\q
```

### 2. Configure PBX System

Edit your `config.yml`:

```yaml
database:
  type: postgresql  # or 'sqlite' for file-based
  host: localhost
  port: 5432
  name: pbx
  user: pbx_user
  password: your_secure_password_here
```

### 3. Initialize Database Tables

The PBX system will automatically create tables on first run. You can also initialize manually:

```bash
python -c "
from pbx.utils.database import DatabaseBackend
from pbx.utils.config import Config

config = Config('config.yml')
db = DatabaseBackend(config._config)
if db.connect():
    db.create_tables()
    print('Database initialized successfully')
"
```

## Database Schema

The PBX system creates the following tables:

### VIP Callers Table
```sql
CREATE TABLE vip_callers (
    id SERIAL PRIMARY KEY,
    caller_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255),
    priority_level INTEGER DEFAULT 1,
    notes TEXT,
    special_routing VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vip_caller_id ON vip_callers(caller_id);
CREATE INDEX idx_vip_priority ON vip_callers(priority_level);
```

### Call Detail Records Table
```sql
CREATE TABLE call_records (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(100) UNIQUE NOT NULL,
    from_extension VARCHAR(20),
    to_extension VARCHAR(20),
    caller_id VARCHAR(50),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration INTEGER,
    status VARCHAR(20),
    recording_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cdr_call_id ON call_records(call_id);
CREATE INDEX idx_cdr_from ON call_records(from_extension);
CREATE INDEX idx_cdr_start_time ON call_records(start_time);
```

### Voicemail Messages Table
```sql
CREATE TABLE voicemail_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(100) UNIQUE NOT NULL,
    extension_number VARCHAR(20) NOT NULL,
    caller_id VARCHAR(50),
    file_path VARCHAR(255),
    duration INTEGER,
    listened BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vm_extension ON voicemail_messages(extension_number);
CREATE INDEX idx_vm_listened ON voicemail_messages(listened);
```

## Using the Database Backend

### Update Operator Console to Use Database

Modify `pbx/features/operator_console.py` to optionally use PostgreSQL:

```python
from pbx.utils.database import DatabaseBackend, VIPCallerDB

# In __init__:
if self.config.get('database.type') in ['postgresql', 'sqlite']:
    self.db_backend = DatabaseBackend(self.config._config)
    if self.db_backend.connect():
        self.db_backend.create_tables()
        self.vip_db = VIPCallerDB(self.db_backend)
    else:
        self.vip_db = None
else:
    self.vip_db = None
```

### Example Usage

```python
from pbx.utils.database import DatabaseBackend, VIPCallerDB

# Initialize database
db = DatabaseBackend(config)
db.connect()
db.create_tables()

# Use VIP caller database
vip_db = VIPCallerDB(db)

# Add VIP caller
vip_db.add_vip('5551234567', priority_level=1, name='Important Client')

# Check if caller is VIP
if vip_db.is_vip('5551234567'):
    print("VIP caller!")

# Get VIP info
vip_info = vip_db.get_vip('5551234567')
print(f"VIP: {vip_info['name']} - Priority: {vip_info['priority_level']}")

# List all VIPs
all_vips = vip_db.list_vips()

# Remove VIP
vip_db.remove_vip('5551234567')
```

## Migration from JSON to PostgreSQL

If you have existing VIP callers in JSON format:

```python
import json
from pbx.utils.database import DatabaseBackend, VIPCallerDB

# Load existing JSON data
with open('vip_callers.json', 'r') as f:
    json_vips = json.load(f)

# Initialize database
db = DatabaseBackend(config)
db.connect()
db.create_tables()
vip_db = VIPCallerDB(db)

# Migrate data
for caller_id, vip_data in json_vips.items():
    vip_db.add_vip(
        caller_id=vip_data['caller_id'],
        priority_level=vip_data.get('priority_level', 1),
        name=vip_data.get('name'),
        notes=vip_data.get('notes')
    )

print(f"Migrated {len(json_vips)} VIP callers to database")
```

## PostgreSQL Configuration

### Allow Remote Connections (if needed)

Edit `/etc/postgresql/{version}/main/postgresql.conf`:

```conf
listen_addresses = '*'  # or specific IP
```

Edit `/etc/postgresql/{version}/main/pg_hba.conf`:

```conf
# Allow PBX server to connect
host    pbx    pbx_user    192.168.1.0/24    md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Performance Tuning

For better performance with many calls:

```sql
-- Connect to pbx database
\c pbx

-- Optimize for read-heavy workload
ALTER TABLE call_records SET (fillfactor = 90);
ALTER TABLE vip_callers SET (fillfactor = 90);

-- Create materialized view for statistics
CREATE MATERIALIZED VIEW call_statistics AS
SELECT 
    from_extension,
    COUNT(*) as total_calls,
    AVG(duration) as avg_duration,
    MAX(start_time) as last_call
FROM call_records
GROUP BY from_extension;

CREATE UNIQUE INDEX ON call_statistics (from_extension);

-- Refresh periodically (e.g., via cron)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY call_statistics;
```

## Backup and Maintenance

### Daily Backup Script

```bash
#!/bin/bash
# backup-pbx-db.sh

BACKUP_DIR="/var/backups/pbx"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pbx_backup_$TIMESTAMP.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U pbx_user -d pbx -f $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

# Keep only last 7 days
find $BACKUP_DIR -name "pbx_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

### Database Maintenance

```sql
-- Vacuum to reclaim space
VACUUM ANALYZE vip_callers;
VACUUM ANALYZE call_records;
VACUUM ANALYZE voicemail_messages;

-- Reindex
REINDEX TABLE vip_callers;
REINDEX TABLE call_records;
REINDEX TABLE voicemail_messages;
```

## Monitoring

### Check Database Size

```sql
SELECT 
    pg_size_pretty(pg_database_size('pbx')) as database_size;

SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Active Connections

```sql
SELECT * FROM pg_stat_activity WHERE datname = 'pbx';
```

## Troubleshooting

### Connection Issues

Test connection:
```bash
psql -U pbx_user -d pbx -h localhost
```

Check PostgreSQL is running:
```bash
sudo systemctl status postgresql
```

Check logs:
```bash
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

### Permission Issues

Grant all permissions:
```sql
\c pbx
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pbx_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pbx_user;
```

### Performance Issues

Check slow queries:
```sql
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## SQLite Alternative

If PostgreSQL is too heavy, you can use SQLite:

```yaml
database:
  type: sqlite
  path: /var/lib/pbx/pbx.db
```

SQLite is:
- ✅ Zero configuration
- ✅ No separate server process
- ✅ Good for small to medium deployments
- ❌ No concurrent write access
- ❌ Limited scalability

## Security Best Practices

1. **Use strong passwords**: Generate with `openssl rand -base64 32`
2. **Limit network access**: Configure pg_hba.conf appropriately
3. **Use SSL connections**: Enable SSL in postgresql.conf
4. **Regular backups**: Automate daily backups
5. **Monitor logs**: Watch for unauthorized access attempts
6. **Update regularly**: Keep PostgreSQL updated

## Integration with PBX Features

### VIP Caller Management

With PostgreSQL backend, VIP caller management becomes:
- ✅ Scalable to millions of callers
- ✅ Fast lookups with indexes
- ✅ Concurrent access support
- ✅ Transaction support
- ✅ Better reporting capabilities

### Call Detail Records

Store call records in database for:
- Advanced reporting and analytics
- Billing integration
- Compliance requirements
- Historical analysis

### Voicemail Messages

Database tracking provides:
- Quick message lookups
- Statistics on voicemail usage
- Integration with email notifications
- Message lifecycle management

## Next Steps

1. ✅ PostgreSQL installed (done)
2. ⏳ Configure database (follow steps above)
3. ⏳ Initialize tables
4. ⏳ Migrate existing data (if any)
5. ⏳ Configure backup schedule
6. ⏳ Monitor performance

## Support

For PostgreSQL issues:
- Official docs: https://www.postgresql.org/docs/
- Ubuntu PostgreSQL: https://ubuntu.com/server/docs/databases-postgresql

For PBX integration issues:
- Check logs: `logs/pbx.log`
- Test connection: Use the test script above
- Enable debug logging in config.yml

## Dependencies

Install PostgreSQL adapter:
```bash
pip install psycopg2-binary
```

Or for production (compile from source):
```bash
sudo apt-get install libpq-dev
pip install psycopg2
```
