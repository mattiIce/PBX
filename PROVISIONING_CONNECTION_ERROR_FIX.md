# Provisioning Connection Error Fix

## Problem

When phones try to fetch their provisioning configuration from the PBX server, they may encounter a "Connection error" even though:
- The device is properly registered in the provisioning system
- The PBX server is running
- The network connectivity is working

### Example Error Message
```
Provisioning Profile:    http://192.168.1.14:8080/provision/68:79:09:9b:e7:68.cfg
Provisioning Status:     Failed
Provisioning Failure Reason: Connection error
```

## Root Cause

The issue occurs when:

1. **The API port in config.yml differs from the default (8080)**
   - For example, if `api.port` is set to `9000` in config.yml
   
2. **A device was registered before the fix was applied**
   - The device's provisioning URL was saved to the database with port 8080
   - The URL persists even after the system restarts

3. **The phone tries to connect to the wrong port**
   - Phone requests: `http://192.168.1.14:8080/provision/...`
   - Server listens on: `http://192.168.1.14:9000/`
   - Result: Connection refused/timeout

## Solution

The fix ensures that provisioning URLs are always generated using the **current** configuration values, not the values that were saved when the device was originally registered.

### What Changed

1. **New helper method**: `_generate_config_url(mac_address)`
   - Generates provisioning URLs from current config values
   - Uses current `api.port` and `server.external_ip`

2. **Updated `register_device()` method**
   - Uses the helper to generate fresh URLs

3. **Updated `_load_devices_from_database()` method**
   - Regenerates URLs when loading devices from database
   - Ignores the stored `config_url` in favor of current config

### Benefits

✅ Provisioning URLs automatically update when config changes  
✅ No manual intervention needed when changing API port or server IP  
✅ Existing devices work correctly after config updates  
✅ New devices always get correct URLs  

## How to Apply This Fix

### For Existing Installations

If you already have devices registered in the system:

1. **Update to the latest version** that includes this fix

2. **Restart the PBX service**:
   ```bash
   sudo systemctl restart pbx
   ```

3. **Verify the fix is working**:
   - Check the logs for the API port being used:
     ```bash
     sudo journalctl -u pbx -n 50 | grep "API port"
     ```
   - You should see: `API port: 9000` (or your configured port)

4. **Test provisioning**:
   - Power cycle a phone or trigger provisioning
   - The phone should now connect to the correct port

### No Re-registration Required

**Important**: You do **NOT** need to re-register your devices. The fix automatically regenerates the provisioning URLs when the system loads devices from the database.

## Verification

To verify the fix is working:

1. **Check device config URLs in logs**:
   ```bash
   sudo journalctl -u pbx | grep "config_url"
   ```

2. **Use the API to check a device**:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:9000/api/provisioning/devices | jq
   ```
   
3. **Verify provisioning request succeeds**:
   - Trigger provisioning from the phone
   - Check logs: `sudo journalctl -u pbx -f`
   - Look for: "✓ Provisioning config delivered"

## Configuration Best Practices

To avoid similar issues in the future:

### 1. Use Consistent Port Configuration

In `config.yml`, ensure the API port is set correctly:

```yaml
api:
  host: 0.0.0.0
  port: 9000  # Your desired port
```

### 2. Use Dynamic URL Format

In `config.yml`, use template variables in the provisioning URL:

```yaml
provisioning:
  enabled: true
  url_format: http://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg
```

These placeholders are automatically replaced:
- `{{SERVER_IP}}` → value from `server.external_ip`
- `{{PORT}}` → value from `api.port`
- `{mac}` → device's MAC address

### 3. Set Correct External IP

Ensure `server.external_ip` matches your actual server IP:

```yaml
server:
  external_ip: 192.168.1.14  # Your server's IP
```

## Troubleshooting

### Still Getting Connection Errors?

If you still see connection errors after applying the fix:

1. **Check if the API server is listening on the configured port**:
   ```bash
   sudo netstat -tlnp | grep :9000
   ```

2. **Verify firewall allows the port**:
   ```bash
   sudo ufw status | grep 9000
   ```
   
   If blocked, allow it:
   ```bash
   sudo ufw allow 9000/tcp
   ```

3. **Check for SSL configuration issues**:
   - If `api.ssl.enabled: true` in config.yml
   - Phones may not be able to validate self-signed certificates
   - Consider using HTTP for provisioning (see config.yml comments)

4. **Review provisioning URL in phone configuration**:
   - Some phones cache the provisioning URL
   - You may need to manually update it on the phone
   - Or factory reset the phone to fetch the new URL

### Getting Help

Check the logs for detailed error messages:
```bash
sudo journalctl -u pbx -n 100 --no-pager
```

Look for:
- "Provisioning request received for MAC: ..."
- "Device ... not registered in provisioning system"
- "Template not found for ..."
- "Extension ... not found"

## Technical Details

For developers and advanced users:

### Code Changes

**File**: `pbx/features/phone_provisioning.py`

**New Method**:
```python
def _generate_config_url(self, mac_address):
    """Generate provisioning config URL for a device"""
    # Reads current config values and generates URL
```

**Modified Methods**:
- `register_device()`: Uses helper to generate URL
- `_load_devices_from_database()`: Regenerates URLs on load

### Testing

Run the test suite to verify the fix:

```bash
cd /path/to/PBX
python3 tests/test_provisioning_config_url.py
```

Expected output:
```
✓ Config URL correctly uses port 9000
✓ Config URL regenerated correctly
✓ Helper method generates correct URL
All provisioning config URL tests passed!
```

## Related Documentation

- [Phone Provisioning Guide](PHONE_PROVISIONING.md)
- [Configuration Guide](config.yml)
- [API Documentation](API_DOCUMENTATION.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

## Version History

- **v1.0.1** (2026-01-08): Fix applied for provisioning connection errors
- Affects all previous versions where `api.port` != 8080
