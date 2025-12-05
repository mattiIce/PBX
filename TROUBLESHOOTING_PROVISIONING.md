# Phone Auto-Provisioning Troubleshooting Guide

## Automatic Phone Management

**Good News**: Starting with this version, the PBX automatically handles phone reboots during provisioning operations. No manual intervention required!

### Automatic Behavior

1. **Device Registration**: When you register a new device via the API, the system automatically triggers a phone reboot if the extension is currently registered
2. **AD Sync Updates**: When Active Directory sync updates user names, the system automatically reboots affected phones to apply the changes
3. **Zero Configuration**: These behaviors are built-in and always active - no configuration needed

### How It Works

**After Device Registration:**
```bash
curl -X POST http://your-pbx-ip:8080/api/provisioning/devices \
  -H "Content-Type: application/json" \
  -d '{"mac_address":"00:15:65:12:34:56","extension_number":"1001","vendor":"yealink","model":"t46s"}'

# Response includes:
# "reboot_triggered": true
# "message": "Device registered and phone reboot triggered automatically"
```

The phone will:
1. Receive SIP NOTIFY from PBX
2. Automatically reboot
3. Fetch fresh configuration on startup
4. Display correct extension name and settings

**After AD Sync:**
```bash
curl -X POST http://your-pbx-ip:8080/api/integrations/ad/sync

# System automatically:
# 1. Updates extension names from AD
# 2. Identifies phones needing updates
# 3. Sends SIP NOTIFY to trigger reboots
# 4. Phones fetch fresh config with updated names
```

### Manual Options (if needed)

While automatic reboots handle most cases, you can still manually trigger reboots:

```bash
# Reboot all phones
curl -X POST http://your-pbx-ip:8080/api/phones/reboot

# Or reboot specific extension
curl -X POST http://your-pbx-ip:8080/api/phones/1001/reboot
```

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

### Issue: Phone requesting with MAC placeholder instead of actual MAC

**Symptoms:**
- Logs show: "CONFIGURATION ERROR: Phone requested provisioning with placeholder '{mac}' instead of actual MAC address"
- Phone tries to fetch config but gets 400 error
- Phone displays provisioning error
- User-Agent shows phone vendor (e.g., "Zultys ZIP 33G")

**Root Cause:**
Phone is configured with wrong MAC variable format. Different vendors use different MAC variables:
- Zultys, Yealink, Polycom, Grandstream use: `$mac`
- Cisco uses: `$MA`

**Solution:**

1. **Update Phone Configuration** with correct MAC variable for your vendor:

   **For Zultys phones:**
   - Phone Menu → Setup → Network → Provisioning
   - Set Server URL to: `http://192.168.1.14:8080/provision/$mac.cfg`
   - Note: Use `$mac` NOT `{mac}`

   **For Yealink phones:**
   - Web Interface → Settings → Auto Provision
   - Set Server URL to: `http://192.168.1.14:8080/provision/$mac.cfg`

   **For Polycom phones:**
   - Web Interface → Settings → Provisioning Server
   - Set Server URL to: `http://192.168.1.14:8080/provision/$mac.cfg`

   **For Cisco phones:**
   - Web Interface → Admin Login → Voice → Provisioning
   - Set Profile Rule to: `http://192.168.1.14:8080/provision/$MA.cfg`
   - Note: Cisco uses `$MA` instead of `$mac`

   **For Grandstream phones:**
   - Web Interface → Maintenance → Upgrade and Provisioning
   - Set Config Server Path to: `http://192.168.1.14:8080/provision/$mac.cfg`

2. **Update DHCP Option 66** (if using DHCP provisioning):
   ```
   # For Zultys, Yealink, Polycom, Grandstream:
   Option 66: http://192.168.1.14:8080/provision/$mac.cfg
   
   # For Cisco:
   Option 66: http://192.168.1.14:8080/provision/$MA.cfg
   ```

3. **Reboot the phone** to apply new provisioning URL

**The system will now provide detailed vendor-specific guidance when this error occurs.**

### Issue: Device not registered in provisioning system

**Symptoms:**
- Phone tries to fetch config but gets 404 error
- Logs show: "Device not registered in provisioning system" with actual MAC address
- Phone displays provisioning error

**New Enhanced Error Messages:**

The system now provides detailed, actionable guidance when a device is not registered:

```
2025-12-05 19:27:15 - PBX - WARNING - Device 00:0B:EA:85:AB:CD not registered in provisioning system
2025-12-05 19:27:15 - PBX - WARNING -   Normalized MAC: 000bea85abcd
2025-12-05 19:27:15 - PBX - WARNING -   Registered devices: ['000bea85ed68', '000bea85f554']
2025-12-05 19:27:15 - PBX - WARNING -   → Device needs to be registered first
2025-12-05 19:27:15 - PBX - WARNING -   → Register via API: POST /api/provisioning/devices
2025-12-05 19:27:15 - PBX - WARNING -      with JSON: {"mac_address":"00:0B:EA:85:AB:CD","extension_number":"XXXX","vendor":"VENDOR","model":"MODEL"}
2025-12-05 19:27:15 - PBX - WARNING -   → Similar MACs found (same vendor): ['000bea85ed68', '000bea85f554']
2025-12-05 19:27:15 - PBX - WARNING -      This might be a typo in the MAC address
```

**Solution:**

1. **Register the device via API:**
   ```bash
   curl -X POST http://your-pbx-ip:8080/api/provisioning/devices \
     -H "Content-Type: application/json" \
     -d '{"mac_address":"00:0B:EA:85:AB:CD","extension_number":"1001","vendor":"zultys","model":"zip33g"}'
   ```

2. **If similar MACs are shown in logs:**
   - Check for typos in the MAC address
   - Verify the phone's actual MAC (usually in phone menu: Status → Network)
   - Use the exact MAC format doesn't matter (colons, dashes, or none - all work)

3. **Verify registration:**
   ```bash
   curl http://your-pbx-ip:8080/api/provisioning/devices
   ```

4. **Test config download:**
   ```bash
   curl http://your-pbx-ip:8080/provision/000bea85abcd.cfg
   ```

**MAC Address Format Support:**

The system automatically normalizes MAC addresses in any format:
- `00:0B:EA:85:ED:68` (colon-separated)
- `00-0B-EA-85-ED-68` (dash-separated)
- `000B.EA85.ED68` (dot-separated, Cisco style)
- `000BEA85ED68` (no separators)
- `000bea85ed68` (lowercase, no separators)

All normalize to: `000bea85ed68`

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
- See "Automatic Phone Management" section above
- The system automatically handles this - phone reboots are triggered automatically after AD sync
- No configuration needed!

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
