# Phone Auto-Provisioning Troubleshooting Guide

## Quick Fix: Phone Display Name Not Updating from Active Directory

If you've fixed the provisioning URL issue but the phone still shows the old name instead of the AD user's name, here's why and how to fix it:

### The Problem

When Active Directory sync updates user names in the PBX, the phones don't automatically see these changes. This is because:

1. Phones only fetch their configuration when they boot up
2. AD sync updates the extension names in the PBX database/config
3. But phones keep using their cached configuration until they reboot

### Solution 1: Manual Phone Reboot (Immediate Fix)

Reboot the phone(s) to force them to fetch fresh configuration with updated names:

```bash
# Reboot all phones at once
curl -X POST http://your-pbx-ip:8080/api/phones/reboot

# Or reboot a specific extension
curl -X POST http://your-pbx-ip:8080/api/phones/1001/reboot
```

You can also reboot phones manually via their physical interface (varies by phone model).

### Solution 2: Enable Automatic Reboot After AD Sync (Recommended)

To avoid this issue in the future, enable automatic phone reboots after AD sync:

**Edit `config.yml`:**

```yaml
integrations:
  active_directory:
    enabled: true
    server: ldaps://your-ad-server:636
    base_dn: DC=company,DC=com
    # ... other AD settings ...
    
    # Add this line to enable automatic phone reboot after AD sync
    reboot_phones_after_sync: true
```

With this setting enabled:
- When AD sync runs (manually or automatically)
- And user names are updated
- PBX will automatically send SIP NOTIFY to phones
- Phones will reboot and fetch fresh config with updated display names

### Verify the Fix

1. **Check extension name in PBX:**
   ```bash
   curl http://your-pbx-ip:8080/api/extensions | grep -A5 '"number":"1001"'
   ```

2. **Verify phone config contains correct name:**
   ```bash
   # Replace MAC address with your phone's MAC
   curl http://your-pbx-ip:8080/provision/001565123456.cfg | grep -i "display\|label"
   ```

3. **Check the phone display** - it should now show the AD user's name

## Using the Troubleshooting Tool

A comprehensive troubleshooting tool has been added to help diagnose provisioning issues:

```bash
# Run full diagnostic check
python scripts/troubleshoot_provisioning.py

# Check specific MAC address
python scripts/troubleshoot_provisioning.py --mac 00:15:65:12:34:56

# Check remote PBX
python scripts/troubleshoot_provisioning.py --host 192.168.1.14 --port 8080
```

### What the Tool Checks

1. **Configuration Validation**
   - Provisioning enabled status
   - URL format configuration
   - External IP and port settings
   - Common configuration issues

2. **API Connectivity**
   - Tests connection to PBX API
   - Verifies server is running
   - Shows current system status

3. **Provisioning Diagnostics**
   - Lists all registered devices
   - Shows supported vendors/models
   - Displays provisioning statistics
   - Highlights configuration warnings

4. **Request History**
   - Shows recent provisioning attempts
   - Success/failure status for each request
   - MAC addresses, IP addresses, User-Agent strings
   - Detailed error messages for failures

5. **MAC Address Testing** (with --mac option)
   - Tests if device is registered
   - Attempts config download
   - Shows actual config content
   - Provides registration commands if needed

## New API Endpoints for Troubleshooting

### Get Provisioning Diagnostics

```bash
curl http://your-pbx-ip:8080/api/provisioning/diagnostics
```

Returns comprehensive diagnostics including:
- Configuration status
- Statistics (devices, templates, requests)
- List of registered devices
- Recent provisioning requests
- Configuration warnings

### View Provisioning Request History

```bash
# Get last 20 requests
curl http://your-pbx-ip:8080/api/provisioning/requests?limit=20
```

Shows:
- Timestamp of each request
- MAC address (original and normalized)
- Source IP address
- User-Agent string
- Success/failure status
- Error details for failures

## Common Issues and Solutions

### Issue: Provisioning URL was partial/incomplete

**Symptoms:**
- Phones not fetching config
- Phones showing "provisioning failed" error
- No requests in provisioning history

**Solution:**
1. Check `config.yml` for correct URL format:
   ```yaml
   provisioning:
     enabled: true
     url_format: http://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg
   ```

2. Verify `server.external_ip` is set to actual IP (not 127.0.0.1):
   ```yaml
   server:
     external_ip: 192.168.1.14  # Your actual PBX IP
   ```

3. Configure phone with full URL: `http://192.168.1.14:8080/provision/$mac.cfg`

### Issue: Phone displays old name after AD sync

**Symptoms:**
- AD sync shows success
- Extension name is correct in PBX
- Phone still displays old name

**Solution:**
- See "Quick Fix: Phone Display Name Not Updating" section above
- Enable `reboot_phones_after_sync: true` in config.yml

### Issue: Device not registered

**Symptoms:**
- Phone requests config but gets 404
- Logs show "Device not registered in provisioning system"

**Solution:**
1. Register the device:
   ```bash
   curl -X POST http://your-pbx-ip:8080/api/provisioning/devices \
     -H "Content-Type: application/json" \
     -d '{
       "mac_address": "00:15:65:12:34:56",
       "extension_number": "1001",
       "vendor": "yealink",
       "model": "t46s"
     }'
   ```

2. Verify registration:
   ```bash
   curl http://your-pbx-ip:8080/api/provisioning/devices
   ```

### Issue: MAC address format mismatch

**Symptoms:**
- Device registered but config requests fail
- Logs show different MAC format in requests

**Solution:**
- PBX normalizes all MAC addresses (removes separators, lowercase)
- Try registering with different formats if needed
- Check phone logs to see exact MAC format being used

### Issue: Wrong vendor/model template

**Symptoms:**
- Config downloads but phone rejects it
- Phone shows config error

**Solution:**
1. Check supported vendors/models:
   ```bash
   curl http://your-pbx-ip:8080/api/provisioning/vendors
   ```

2. Verify device registration uses correct vendor/model
3. Update if needed:
   ```bash
   # Delete old registration
   curl -X DELETE http://your-pbx-ip:8080/api/provisioning/devices/00:15:65:12:34:56
   
   # Add with correct vendor/model
   curl -X POST http://your-pbx-ip:8080/api/provisioning/devices ...
   ```

## Enhanced Logging

All provisioning requests now generate detailed logs in `logs/pbx.log`:

```
2025-12-05 19:00:00 - PBX - INFO - Provisioning request received for MAC: 001565123456
2025-12-05 19:00:00 - PBX - INFO -   Request from IP: 192.168.1.50
2025-12-05 19:00:00 - PBX - INFO -   User-Agent: Yealink SIP-T46S 66.85.0.15
2025-12-05 19:00:00 - PBX - INFO -   Found device: vendor=yealink, model=t46s, extension=1001
2025-12-05 19:00:00 - PBX - INFO -   Extension found: 1001 (John Smith)
2025-12-05 19:00:00 - PBX - INFO -   Server config: SIP=192.168.1.14:5060
2025-12-05 19:00:00 - PBX - INFO - ✓ Successfully generated config for device 001565123456
2025-12-05 19:00:00 - PBX - INFO -   Config size: 1234 bytes, Content-Type: text/plain
2025-12-05 19:00:00 - PBX - INFO - ✓ Provisioning config delivered: 1234 bytes to 192.168.1.50
```

Use these logs to:
- Verify phones are requesting config
- Check if device is registered
- See which extension names are being used
- Identify network/connectivity issues

## Need More Help?

1. Run the troubleshooting tool: `python scripts/troubleshoot_provisioning.py`
2. Check logs: `tail -f logs/pbx.log | grep -i provision`
3. Review full documentation: [PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)
4. Check diagnostics endpoint: `curl http://your-pbx-ip:8080/api/provisioning/diagnostics`
