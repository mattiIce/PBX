# Phone Registration Cleanup at Startup

**Date**: December 9, 2025  
**Status**: ✅ Implemented  
**Version**: 1.0

## Overview

The PBX system now automatically cleans up incomplete phone registrations at startup. Only phones with complete information (MAC address, IP address, and Extension number) are retained in the database.

## Purpose

Phone registrations can become incomplete when:
- Phones register without providing MAC address information
- Partial registration data is stored during network issues
- Database entries are manually added without all required fields
- Registration process is interrupted

Keeping incomplete registrations clutters the database and can cause confusion about actual registered devices.

## Implementation

### Automatic Cleanup at Startup

When the PBX system starts:

1. **Database Connection**: After database tables are created
2. **Cleanup Execution**: `cleanup_incomplete_registrations()` is called
3. **Removal Criteria**: Any registration missing MAC, IP, or Extension is removed
4. **Logging**: Number of removed registrations is logged

### What Gets Removed

A phone registration is considered **incomplete** and will be removed if:
- `mac_address` is NULL or empty string
- **OR** `ip_address` is NULL or empty string  
- **OR** `extension_number` is NULL or empty string

### What Gets Retained

A phone registration is **retained** only if:
- `mac_address` is NOT NULL and NOT empty
- **AND** `ip_address` is NOT NULL and NOT empty
- **AND** `extension_number` is NOT NULL and NOT empty

## Example Scenarios

### Before Cleanup
```
ID | MAC Address       | IP Address    | Extension
---+-------------------+---------------+-----------
1  | 00:11:22:33:44:55| 192.168.1.10  | 1001      -> KEPT (complete)
2  | NULL             | 192.168.1.11  | 1002      -> REMOVED (no MAC)
3  | 00:11:22:33:44:56| NULL          | 1003      -> REMOVED (no IP)
4  | 00:11:22:33:44:57| 192.168.1.12  | NULL      -> REMOVED (no Extension)
5  | ''               | 192.168.1.13  | 1005      -> REMOVED (empty MAC)
6  | 00:11:22:33:44:58| 192.168.1.14  | 1006      -> KEPT (complete)
```

### After Cleanup
```
ID | MAC Address       | IP Address    | Extension
---+-------------------+---------------+-----------
1  | 00:11:22:33:44:55| 192.168.1.10  | 1001
6  | 00:11:22:33:44:58| 192.168.1.14  | 1006
```

**Result**: 4 incomplete registrations removed, 2 complete registrations retained.

## Log Output

When the PBX starts, you'll see log messages like:

```
2025-12-09 00:00:01 - PBX - INFO - Database backend initialized successfully (postgresql)
2025-12-09 00:00:01 - PBX - INFO - Extensions, voicemail metadata, and phone registrations will be stored in database
2025-12-09 00:00:01 - PBX - INFO - Cleaned up 4 incomplete phone registration(s) from database
2025-12-09 00:00:01 - PBX - INFO - Only phones with MAC, IP, and Extension are retained
2025-12-09 00:00:01 - PBX - INFO - Startup cleanup: Removed 4 incomplete phone registration(s)
```

If no incomplete registrations are found:
```
2025-12-09 00:00:01 - PBX - INFO - No incomplete phone registrations found
```

## Manual Cleanup

If you need to manually clean up incomplete registrations:

### Using SQL

```sql
-- Connect to database
psql -U pbx_user -d pbx_system

-- View incomplete registrations before cleanup
SELECT id, mac_address, ip_address, extension_number 
FROM registered_phones 
WHERE mac_address IS NULL OR mac_address = '' 
   OR ip_address IS NULL OR ip_address = ''
   OR extension_number IS NULL OR extension_number = '';

-- Remove incomplete registrations
DELETE FROM registered_phones 
WHERE mac_address IS NULL OR mac_address = '' 
   OR ip_address IS NULL OR ip_address = ''
   OR extension_number IS NULL OR extension_number = '';

-- Verify cleanup
SELECT COUNT(*) FROM registered_phones;
```

### Using Python Script

Create a script to manually trigger cleanup:

```python
#!/usr/bin/env python3
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB
from pbx.utils.config import Config

# Load config
config = Config("config.yml")

# Connect to database
db = DatabaseBackend(config)
if db.connect():
    db.create_tables()
    
    # Create phones DB instance
    phones_db = RegisteredPhonesDB(db)
    
    # Run cleanup
    success, count = phones_db.cleanup_incomplete_registrations()
    
    if success:
        print(f"✓ Cleaned up {count} incomplete registration(s)")
    else:
        print("✗ Cleanup failed")
else:
    print("✗ Failed to connect to database")
```

## Technical Details

### Database Query

The cleanup uses the following SQL query:

```sql
DELETE FROM registered_phones 
WHERE mac_address IS NULL OR mac_address = '' 
   OR ip_address IS NULL OR ip_address = ''
   OR extension_number IS NULL OR extension_number = '';
```

### Method Signature

```python
def cleanup_incomplete_registrations(self) -> tuple[bool, int]:
    """
    Remove phone registrations that are missing MAC address, IP address, or extension number.
    Only phones with all three fields (MAC, IP, and Extension) should be retained.
    This is called at startup to ensure data integrity.
    
    Returns:
        tuple[bool, int]: Success status and count of removed registrations
    """
```

### Integration Point

The cleanup is called in `pbx/core/pbx.py` during initialization:

```python
# Clean up incomplete phone registrations at startup
# Only phones with MAC, IP, and Extension should be retained
success, count = self.registered_phones_db.cleanup_incomplete_registrations()
if success and count > 0:
    self.logger.info(f"Startup cleanup: Removed {count} incomplete phone registration(s)")
```

## Testing

Run the cleanup tests:

```bash
python -m unittest tests.test_phone_cleanup_startup -v
```

Expected output:
```
test_cleanup_database_error ... ok
test_cleanup_delete_failure ... ok
test_cleanup_no_incomplete_registrations ... ok
test_cleanup_query_structure ... ok
test_cleanup_with_incomplete_registrations ... ok
test_cleanup_removes_only_incomplete_registrations ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.002s

OK
```

## Benefits

1. **Data Integrity**: Ensures registered_phones table only contains complete information
2. **Accurate Reporting**: Phone counts reflect actual registered devices
3. **Reduced Confusion**: No partial/incomplete entries to cause issues
4. **Automatic Maintenance**: Runs on every startup without manual intervention
5. **Safe Operation**: Only removes incomplete entries, never touches valid registrations

## Disabling Cleanup (Not Recommended)

If you need to disable the automatic cleanup (not recommended):

Comment out the cleanup call in `pbx/core/pbx.py`:

```python
# Clean up incomplete phone registrations at startup
# Only phones with MAC, IP, and Extension should be retained
# success, count = self.registered_phones_db.cleanup_incomplete_registrations()
# if success and count > 0:
#     self.logger.info(f"Startup cleanup: Removed {count} incomplete phone registration(s)")
```

## Related Documentation

- [Phone Registration Tracking](PHONE_REGISTRATION_TRACKING.md)
- [Clear Registered Phones](CLEAR_REGISTERED_PHONES.md)
- [Phone Provisioning](PHONE_PROVISIONING.md)

## Troubleshooting

### Issue: Too many registrations being removed

**Cause**: Phones are not providing complete information during registration

**Solution**: 
- Check SIP REGISTER messages for Contact header with MAC info
- Verify phone provisioning templates include MAC address
- Review network issues that might interrupt registration

### Issue: Cleanup fails to execute

**Cause**: Database connection or permission issues

**Solution**:
- Verify database connection is working
- Check database user has DELETE permissions
- Review database logs for errors

### Issue: Need to keep registrations with missing MAC temporarily

**Cause**: Some phone models don't report MAC address in SIP messages

**Solution**:
- Modify cleanup query to only check IP and Extension
- Update phones to newer firmware that reports MAC
- Use phone provisioning to ensure MAC is known

---

**Version**: 1.0  
**Last Updated**: December 9, 2025  
**Status**: ✅ Production Ready  
**Test Coverage**: 6/6 tests passing (100%)
