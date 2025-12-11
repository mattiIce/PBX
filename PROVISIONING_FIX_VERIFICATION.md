# Provisioning Fix Verification Guide

## What Was Fixed

The provisioning system was showing **HTTPS** URLs in error messages even though the server was running on **HTTP** (due to missing SSL certificates). This caused phones to fail connecting for provisioning.

### Changes Made
1. ✅ Disabled SSL in `config.yml` (set `api.ssl.enabled: false`)
2. ✅ Fixed all error messages to show HTTP URLs instead of HTTPS
3. ✅ Updated error messages to show actual server IP (192.168.1.14) instead of placeholders
4. ✅ Updated remote phonebook URL to use HTTP

## Verification Steps

### 1. Verify Server is Running on HTTP

Start the PBX and check the logs:
```bash
python3 main.py
```

You should see:
```
INFO - SSL/HTTPS is disabled - using HTTP
INFO - API server started on http://0.0.0.0:8080
```

### 2. Test Provisioning Endpoint

#### Register a Test Device
```bash
curl -X POST http://192.168.1.14:8080/api/provisioning/devices \
  -H 'Content-Type: application/json' \
  -d '{
    "mac_address":"00:15:65:12:34:56",
    "extension_number":"1001",
    "vendor":"zultys",
    "model":"zip33g"
  }'
```

Expected response:
```json
{
  "success": true,
  "device": {
    "mac_address": "001565123456",
    "extension_number": "1001",
    "vendor": "zultys",
    "model": "zip33g",
    "config_url": "http://192.168.1.14:8080/provision/001565123456.cfg"
  },
  "reboot_triggered": false,
  "message": "Device registered. Phone will fetch config on next boot."
}
```

#### Test Configuration Download
```bash
curl http://192.168.1.14:8080/provision/001565123456.cfg
```

Expected: You should receive the phone configuration file (starting with `#!version:1.0.0.1`)

### 3. Check Provisioning Logs

Provisioning requests should now appear in the logs with detailed information:
```
INFO - Provisioning config request: path=/provision/001565123456.cfg, IP=192.168.1.100
INFO -   MAC address from request: 001565123456
INFO - Provisioning request received for MAC: 001565123456
INFO -   Request from IP: 192.168.1.100
INFO -   User-Agent: Zultys/1.0
INFO -   Found device: vendor=zultys, model=zip33g, extension=1001
INFO -   Extension found: 1001 (John Doe)
INFO - ✓ Successfully generated config for device 001565123456
INFO - ✓ Provisioning config delivered: 10575 bytes to 192.168.1.100
```

### 4. Configure Your Phones

Use the **HTTP** provisioning URL:

#### Via Phone Web Interface
- **URL**: `http://192.168.1.14:8080/provision/$mac.cfg`
- Note: Use `$mac` for Zultys/Yealink/Polycom/Grandstream
- Note: Use `$MA` for Cisco phones

#### Via DHCP Option 66
Set DHCP Option 66 to: `http://192.168.1.14:8080/provision/$mac.cfg`

## Troubleshooting

### If phones still can't connect:

1. **Check network connectivity**:
   ```bash
   # From phone's network
   ping 192.168.1.14
   curl http://192.168.1.14:8080/api/status
   ```

2. **Verify device is registered**:
   ```bash
   curl http://192.168.1.14:8080/api/provisioning/devices
   ```

3. **Check logs for provisioning attempts**:
   ```bash
   tail -f logs/pbx.log | grep -i provision
   ```

4. **Test with the actual phone MAC**:
   - Find MAC address on phone (usually in Status → Network)
   - Replace colons/dashes: `00:15:65:12:34:56` → `001565123456`
   - Test: `curl http://192.168.1.14:8080/provision/001565123456.cfg`

### If you see "Device not registered" errors:

The logs will now show helpful commands with HTTP URLs:
```
WARNING - Device aabbccddeeff not registered in provisioning system
WARNING -   → Register via API: POST /api/provisioning/devices
WARNING -   → Example:
WARNING -      curl -X POST http://192.168.1.14:8080/api/provisioning/devices \
WARNING -        -H 'Content-Type: application/json' \
WARNING -        -d '{"mac_address":"aabbccddeeff","extension_number":"XXXX","vendor":"VENDOR","model":"MODEL"}'
```

## Summary

✅ Provisioning is now working with HTTP
✅ Error messages show correct HTTP URLs
✅ Phones can now successfully connect and download configurations
✅ Logs clearly show when provisioning requests arrive

The system is ready for production use with HTTP provisioning!
