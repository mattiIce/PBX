# Phone Provisioning Persistence

The PBX system now stores phone provisioning configurations persistently in the database, ensuring that device registrations and IP/MAC/extension mappings are maintained across system restarts.

## Overview

Previously, phone provisioning devices were stored only in memory, which meant:
- Device configurations were lost on PBX restart
- You had to re-register devices after each reboot
- Static IP-to-MAC mappings were not supported

With database persistence, the system now:
- **Stores all provisioned devices in the database** (`provisioned_devices` table)
- **Maintains IP-to-MAC-to-extension mappings** across restarts
- **Preserves phone registration history** in the `registered_phones` table
- **Supports static IP assignments** for phones with static IPs

## Benefits

✓ **No Data Loss**: Provisioning configurations survive server restarts  
✓ **Automatic Recovery**: Devices are automatically loaded from database on startup  
✓ **Better Tracking**: Complete history of device provisioning  
✓ **Static IP Support**: Assign and track static IPs for phones  
✓ **Simplified Management**: No need to re-register devices after maintenance  

## How It Works

### 1. Device Registration

When you register a device via the API or Admin Panel:

```bash
curl -X POST http://192.168.1.14:8080/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:15:65:12:34:56",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s"
  }'
```

The system:
1. Creates an in-memory `ProvisioningDevice` object
2. Saves the device configuration to the `provisioned_devices` database table
3. Records: MAC address, extension, vendor, model, config URL, timestamps

### 2. System Startup

When the PBX starts:

1. Database connection is established
2. Phone provisioning system initializes
3. **All devices are automatically loaded from database** into memory
4. Devices are ready to provision immediately

### 3. Phone Registration Tracking

When phones register via SIP:

1. Registration is tracked in the `registered_phones` table
2. Table stores: MAC (if available), IP, extension, user-agent, timestamps
3. **Data is preserved across restarts** (table is NOT cleared on boot)
4. Phones will re-register automatically (typically every 30-60 seconds)

### 4. Static IP Assignment

For phones with static IPs, you can now create explicit IP-to-MAC mappings:

```bash
# Set static IP for a device
curl -X POST http://192.168.1.14:8080/api/provisioning/devices/001565123456/static-ip \
  -H "Content-Type: application/json" \
  -d '{
    "static_ip": "192.168.1.100"
  }'
```

This creates a permanent mapping that:
- Associates the MAC address with a specific IP
- Helps with network troubleshooting
- Useful for devices that don't include MAC in SIP headers

## Database Schema

### provisioned_devices Table

```sql
CREATE TABLE provisioned_devices (
    id INTEGER PRIMARY KEY,
    mac_address VARCHAR(20) UNIQUE NOT NULL,
    extension_number VARCHAR(20) NOT NULL,
    vendor VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    static_ip VARCHAR(50),              -- Optional static IP
    config_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_provisioned TIMESTAMP,         -- Last time phone fetched config
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### registered_phones Table

```sql
CREATE TABLE registered_phones (
    id INTEGER PRIMARY KEY,
    mac_address VARCHAR(20),
    extension_number VARCHAR(20) NOT NULL,
    user_agent VARCHAR(255),
    ip_address VARCHAR(50) NOT NULL,
    first_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    contact_uri VARCHAR(255),
    UNIQUE(mac_address, extension_number),
    UNIQUE(ip_address, extension_number)
);
```

## API Endpoints

### Set Static IP

```bash
POST /api/provisioning/devices/{mac}/static-ip
```

**Request:**
```json
{
  "static_ip": "192.168.1.100"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Static IP 192.168.1.100 set for device 001565123456"
}
```

### List All Provisioned Devices

```bash
GET /api/provisioning/devices
```

Returns all devices from database with their provisioning details.

### List All Registered Phones

```bash
GET /api/registered-phones
```

Returns all phones that have registered, including their IP addresses.

### Phone Lookup (MAC or IP)

```bash
GET /api/phone-lookup/{mac_or_ip}
```

Correlates provisioning data with registration data to provide complete device information.

## Use Cases

### Use Case 1: Static IP Phones

**Scenario**: Your organization uses DHCP reservations to assign static IPs to phones.

**Setup:**
1. Register device with MAC and extension
2. Set static IP for the device
3. System maintains the mapping permanently

```bash
# Register device
curl -X POST http://192.168.1.14:8080/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:15:65:12:34:56",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s"
  }'

# Set static IP
curl -X POST http://192.168.1.14:8080/api/provisioning/devices/001565123456/static-ip \
  -H "Content-Type: application/json" \
  -d '{"static_ip": "192.168.1.100"}'
```

**Benefits:**
- Complete device tracking (MAC + IP + Extension)
- Easy network troubleshooting
- Historical tracking of devices

### Use Case 2: Server Maintenance

**Scenario**: You need to restart the PBX server for updates.

**Before (without persistence):**
1. Stop PBX
2. Perform updates
3. Start PBX
4. **Re-register all devices manually** ❌
5. Wait for phones to fetch new configs

**Now (with persistence):**
1. Stop PBX
2. Perform updates
3. Start PBX
4. **Devices automatically loaded from database** ✓
5. Phones fetch configs immediately when they check

### Use Case 3: Bulk Provisioning

**Scenario**: You're deploying 50 new phones.

**Workflow:**
1. Register all 50 devices via API or Admin Panel
2. Devices are saved to database
3. Distribute phones to users
4. Phones boot and automatically fetch their configs
5. **If PBX restarts during deployment, no data is lost**

## Migration from In-Memory Storage

If you've been using the system before this feature was added:

### Automatic Migration

The system will automatically start using database storage when:
1. Database is configured and connected
2. Phone provisioning is enabled
3. No action required from you

### First Boot After Upgrade

On first boot with the new version:
1. `provisioned_devices` table is created automatically
2. Any devices in `config.yml` are loaded into memory as before
3. When you register or update devices via API, they're saved to database
4. From that point on, all devices are persisted

### Checking Persistence Status

Check logs on startup:
```
[INFO] Phone provisioning will use database for persistent storage
[INFO] Loaded 15 provisioned devices from database
```

If you see this, persistence is active and working.

## Troubleshooting

### Devices Not Loading After Restart

**Check database connection:**
```bash
# Look for this in logs on startup
grep "Database backend initialized" logs/pbx.log
```

**Verify devices in database:**
```bash
# For PostgreSQL
psql -h localhost -U pbx_user -d pbx_system -c "SELECT * FROM provisioned_devices;"

# For SQLite
sqlite3 pbx.db "SELECT * FROM provisioned_devices;"
```

### Static IP Not Being Set

**Error: "Database not available"**

This means database is not connected. Check:
1. Database configuration in `config.yml`
2. Database service is running
3. Database credentials are correct

### Duplicate Device Entries

If you have duplicate MAC addresses in the database:

```bash
# For PostgreSQL
psql -h localhost -U pbx_user -d pbx_system -c "
  SELECT mac_address, COUNT(*) 
  FROM provisioned_devices 
  GROUP BY mac_address 
  HAVING COUNT(*) > 1;
"
```

This shouldn't happen (MAC is UNIQUE), but if it does:
1. The database constraint will prevent duplicates
2. Update operations will modify the existing record
3. No manual cleanup needed

## Best Practices

1. **Use Database**: Always configure a database (PostgreSQL or SQLite) for production
2. **Backup Database**: Include the `provisioned_devices` table in your backup strategy
3. **Set Static IPs**: For phones with DHCP reservations, set the static IP in the system
4. **Monitor Logs**: Check logs on startup to verify devices are loaded
5. **Test Restarts**: Periodically restart the PBX to verify persistence is working

## Configuration Example

Enable phone provisioning with database persistence:

```yaml
# config.yml
database:
  type: postgresql  # or sqlite
  host: localhost
  port: 5432
  name: pbx_system
  user: pbx_user
  password: your_password

provisioning:
  enabled: true
  url_format: "http://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg"
  devices: []  # Not needed anymore - devices are in database
```

## Technical Details

### Database Operations

**On Device Registration:**
- INSERT or UPDATE to `provisioned_devices`
- Atomic operation (either succeeds completely or fails)
- Rollback on error

**On Device Unregistration:**
- DELETE from `provisioned_devices`
- Device removed from both memory and database

**On Config Generation:**
- UPDATE `last_provisioned` timestamp
- Tracks when phone last fetched config

### Performance

- Device loading is done once at startup
- All provisioning operations work from in-memory cache
- Database is updated asynchronously
- No performance impact on phone config requests

### Data Integrity

- MAC address is UNIQUE (can't have duplicates)
- Foreign key constraints ensure data consistency
- Timestamps track all changes
- Database transactions ensure atomic updates

## Related Documentation

- [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md) - Complete provisioning guide
- [PHONE_REGISTRATION_TRACKING.md](PHONE_REGISTRATION_TRACKING.md) - Registration tracking
- [MAC_TO_IP_CORRELATION.md](MAC_TO_IP_CORRELATION.md) - MAC/IP correlation features
- [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md) - Database setup instructions
- [DATABASE_MIGRATION_GUIDE.md](DATABASE_MIGRATION_GUIDE.md) - Migration guide

## Summary

Phone provisioning persistence ensures that:
- ✓ Device configurations survive restarts
- ✓ IP-to-MAC-to-extension mappings are maintained
- ✓ Static IP assignments are supported
- ✓ Phone registration history is preserved
- ✓ No manual intervention needed after PBX restarts

This makes the system more reliable, easier to maintain, and better suited for production environments where uptime and data integrity are critical.
