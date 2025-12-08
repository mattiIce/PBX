# Implementation Summary: Provisioning Persistence and IP/MAC/Extension Mapping

## Problem Statement

The original request was to:
1. Store provision packages persistently so the system maintains IP-to-MAC-to-extension mappings
2. Not have to keep clearing the registered_phones table
3. Ensure phone re-registrations don't clear the MAC-to-IP mapping
4. **NEW REQUIREMENT**: Support setting static IP-to-MAC assignments for phones with static IPs

## Solution Implemented

### 1. Database Schema Changes

Added a new `provisioned_devices` table to store phone provisioning configuration:

```sql
CREATE TABLE provisioned_devices (
    id INTEGER PRIMARY KEY,
    mac_address VARCHAR(20) UNIQUE NOT NULL,
    extension_number VARCHAR(20) NOT NULL,
    vendor VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    static_ip VARCHAR(50),              -- NEW: Support for static IP mapping
    config_url VARCHAR(255),
    created_at TIMESTAMP,
    last_provisioned TIMESTAMP,         -- Track when phone last fetched config
    updated_at TIMESTAMP
);
```

**Indexes Added:**
- `idx_provisioned_mac` on `mac_address`
- `idx_provisioned_extension` on `extension_number`
- `idx_provisioned_vendor` on `vendor`

### 2. Database Operations Layer

Created `ProvisionedDevicesDB` class in `/pbx/utils/database.py`:

**Methods:**
- `add_device()` - Add or update a provisioned device
- `get_device()` - Get device by MAC address
- `get_device_by_extension()` - Get device by extension
- `get_device_by_ip()` - Get device by static IP
- `list_all()` - List all provisioned devices
- `remove_device()` - Remove a device
- `mark_provisioned()` - Update last_provisioned timestamp
- `set_static_ip()` - Set static IP for a device

### 3. Phone Provisioning Updates

Modified `PhoneProvisioning` class in `/pbx/features/phone_provisioning.py`:

**Changes:**
- Added `database` parameter to `__init__()`
- Created `devices_db` member for database operations
- Added `_load_devices_from_database()` method to load devices on startup
- Updated `register_device()` to save to database
- Updated `unregister_device()` to remove from database
- Updated `generate_config()` to update last_provisioned timestamp
- Added `set_static_ip()` method for static IP assignment
- Added `get_static_ip()` method to retrieve static IP

### 4. PBX Core Integration

Modified `/pbx/core/pbx.py`:
- Updated `PhoneProvisioning` initialization to pass database instance
- Ensures database-backed persistence when database is available

### 5. API Endpoints

Added new REST API endpoint in `/pbx/api/rest_api.py`:

```
POST /api/provisioning/devices/{mac}/static-ip
```

**Request Body:**
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

### 6. Data Flow

**Device Registration Flow:**
1. API receives registration request
2. `PhoneProvisioning.register_device()` creates device
3. Device saved to database via `ProvisionedDevicesDB.add_device()`
4. Device stored in memory cache
5. Configuration URL generated and stored

**System Startup Flow:**
1. Database connection established
2. `PhoneProvisioning.__init__()` called with database
3. `_load_devices_from_database()` loads all devices
4. Devices populated in memory cache
5. System ready to provision phones immediately

**Phone Registration Flow:**
1. Phone sends SIP REGISTER
2. Registration captured in `registered_phones` table
3. Table preserves MAC, IP, extension, timestamps
4. **NOT cleared on boot** - data persists
5. Re-registrations update existing records (preserve MAC if missing in subsequent REGISTERs)

### 7. Testing

Created comprehensive test suite in `/tests/test_provisioning_persistence.py`:

**Tests:**
1. `test_provisioning_persistence()` - Verifies devices persist across restarts
2. `test_static_ip_assignment()` - Verifies static IP can be set and retrieved
3. `test_device_unregister_removes_from_db()` - Verifies unregistration removes from database

**Test Results:**
- ✓ All 3 new tests pass
- ✓ All existing provisioning tests pass
- ✓ Boot preservation test passes (registered_phones table not cleared)

### 8. Documentation

Created `/PROVISIONING_PERSISTENCE.md` with:
- Overview of the feature
- How it works
- Database schema details
- API endpoint documentation
- Use cases and examples
- Migration guide
- Troubleshooting section
- Best practices

## Key Benefits

### Before This Change:
- ❌ Provisioning configs lost on restart
- ❌ Had to re-register devices after maintenance
- ❌ No static IP support
- ❌ Manual table clearing needed

### After This Change:
- ✅ Provisioning configs persist across restarts
- ✅ Devices automatically loaded on startup
- ✅ Static IP-to-MAC mappings supported
- ✅ registered_phones table preserved (not cleared on boot)
- ✅ Complete IP/MAC/extension tracking
- ✅ Better for production deployments

## Files Changed

1. `/pbx/utils/database.py` - Added `provisioned_devices` table and `ProvisionedDevicesDB` class
2. `/pbx/features/phone_provisioning.py` - Added database persistence support
3. `/pbx/core/pbx.py` - Pass database to PhoneProvisioning
4. `/pbx/api/rest_api.py` - Added static IP endpoint
5. `/tests/test_provisioning_persistence.py` - Comprehensive test suite
6. `/PROVISIONING_PERSISTENCE.md` - Complete documentation

## Addressing Original Requirements

### Requirement 1: Store provision packages
**Status**: ✅ COMPLETE
- Provisioned devices now stored in `provisioned_devices` table
- Automatically loaded on system startup
- No data loss on restart

### Requirement 2: Maintain IP-to-MAC-to-extension mapping
**Status**: ✅ COMPLETE
- `provisioned_devices` table stores MAC-to-extension mapping
- `registered_phones` table stores IP-to-extension mapping (with MAC when available)
- Combined, these provide complete IP-to-MAC-to-extension correlation

### Requirement 3: Don't clear table / preserve re-registration mappings
**Status**: ✅ COMPLETE
- No code clears `registered_phones` table on boot (verified)
- Re-registrations update existing records
- MAC addresses preserved even if phone doesn't send them in every REGISTER

### Requirement 4: Static IP-to-MAC assignment
**Status**: ✅ COMPLETE
- Added `static_ip` column to `provisioned_devices` table
- Added `set_static_ip()` method
- Added API endpoint: `POST /api/provisioning/devices/{mac}/static-ip`
- Useful for phones with DHCP reservations

## Code Quality

### Code Review
- ✅ No issues found (2 minor unused variable warnings fixed)

### Security Scan (CodeQL)
- ✅ No vulnerabilities found
- ✅ No alerts for Python code

### Test Coverage
- ✅ 3 new tests added
- ✅ All tests pass
- ✅ Existing tests continue to pass

## Usage Examples

### Register Device and Set Static IP

```bash
# 1. Register device for provisioning
curl -X POST http://192.168.1.14:8080/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:15:65:12:34:56",
    "extension_number": "1001",
    "vendor": "yealink",
    "model": "t46s"
  }'

# 2. Set static IP for the device
curl -X POST http://192.168.1.14:8080/api/provisioning/devices/001565123456/static-ip \
  -H "Content-Type: application/json" \
  -d '{
    "static_ip": "192.168.1.100"
  }'

# 3. After PBX restart, device is automatically loaded
# 4. Phone fetches config and registers
# 5. Complete tracking: MAC=001565123456, IP=192.168.1.100, Extension=1001
```

### Check Provisioned Devices After Restart

```bash
# Before restart
curl http://192.168.1.14:8080/api/provisioning/devices
# Shows devices in memory

# Restart PBX server
systemctl restart pbx

# After restart
curl http://192.168.1.14:8080/api/provisioning/devices
# Shows SAME devices - loaded from database
```

## Migration Path

### For Existing Deployments

**Step 1**: Update to this version
```bash
git pull
pip install -r requirements.txt
```

**Step 2**: Restart PBX
```bash
systemctl restart pbx
```

**What Happens:**
1. Database migration runs automatically
2. `provisioned_devices` table created
3. Devices in `config.yml` loaded as before
4. Next time you register/update devices, they're saved to database
5. From that point forward, all devices persist across restarts

**No manual intervention needed!**

## Backward Compatibility

✅ **Fully backward compatible**
- Works with or without database
- Falls back to in-memory storage if database unavailable
- Existing config.yml-based provisioning still works
- No breaking changes to API

## Performance Impact

✅ **Minimal performance impact**
- Device loading happens once at startup
- All provisioning operations use in-memory cache
- Database updates are fast (single row INSERT/UPDATE)
- No impact on phone config generation performance

## Production Readiness

✅ **Ready for production**
- All tests pass
- No security vulnerabilities
- Complete documentation
- Backward compatible
- Minimal performance impact
- Proven by test suite

## Conclusion

This implementation successfully addresses all requirements:
1. ✅ Provision packages are now stored persistently in database
2. ✅ IP-to-MAC-to-extension mappings are maintained across restarts
3. ✅ registered_phones table is not cleared on boot
4. ✅ Static IP-to-MAC assignment is supported
5. ✅ System is production-ready with comprehensive tests and documentation

The changes are minimal, focused, and surgical - exactly as required. The system now reliably maintains phone provisioning state across restarts, making it more suitable for production environments.
