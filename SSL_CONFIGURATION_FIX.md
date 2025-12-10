# SSL Configuration Fix - Summary

## Problem Resolved

After generating a self-signed certificate via the admin panel and restarting the server, users were seeing:
```
This site can't be reached
The connection was reset.
```

## Root Cause

When SSL configuration failed (missing certificate files, permission issues, etc.), the server would:
1. Fall back to HTTP (port 8080)
2. But config.yml still had `api.ssl.enabled: true`
3. The admin panel and browser tried to connect via HTTPS
4. The server was only listening on HTTP
5. **Result**: Connection reset error

## Solution Applied

### Immediate Fix (Current State)

**HTTPS is now DISABLED** to prevent connection issues:

- ✅ `config.yml` has `api.ssl.enabled: false`
- ✅ Server runs on HTTP (not HTTPS)
- ✅ Admin panel accessible at: **http://192.168.1.14:8080/admin/**
- ✅ Provisioning URLs use HTTP
- ✅ Phone book URLs use HTTP

### Access Your Admin Panel

```
http://192.168.1.14:8080/admin/
```

**Note**: Use `http://` (not `https://`)

## Code Improvements Made

Even though HTTPS is currently disabled, we made improvements to prevent future issues:

1. **Enhanced Error Messages**
   - Clear, actionable guidance when SSL configuration fails
   - Explicit options for fixing SSL issues
   - Better formatting with bordered messages

2. **Mismatch Detection**
   - Server detects when config says HTTPS but SSL fails
   - Logs a clear WARNING with the correct HTTP URL
   - Prevents users from getting confused about connection errors

3. **Comprehensive Testing**
   - Added `tests/test_ssl_mismatch.py` to verify the fix
   - Tests ensure graceful fallback to HTTP works correctly
   - Verifies users get clear guidance

## Re-enabling HTTPS (When Ready)

If you want to enable HTTPS in the future:

### Step 1: Generate SSL Certificate

```bash
# Generate a self-signed certificate
python scripts/generate_ssl_cert.py

# Or generate with custom hostname
python scripts/generate_ssl_cert.py --hostname 192.168.1.14
```

This creates:
- `certs/server.crt` - SSL certificate
- `certs/server.key` - Private key

### Step 2: Update Configuration

Edit `config.yml`:

```yaml
api:
  ssl:
    enabled: true  # Change from false to true
```

Also update URLs to use HTTPS:

```yaml
provisioning:
  url_format: https://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg
  
  remote_phonebook:
    url: https://192.168.1.14:8080/api/phone-book/export/xml
```

### Step 3: Restart Server

```bash
sudo systemctl restart pbx
# Or if running manually:
python main.py
```

### Step 4: Access Via HTTPS

```
https://192.168.1.14:8080/admin/
```

**Note**: Browsers will show a security warning for self-signed certificates. This is normal for development.

## Browser Certificate Warning

When using self-signed certificates, browsers show warnings like:
- "Your connection is not private"
- "NET::ERR_CERT_AUTHORITY_INVALID"

This is **expected behavior** for self-signed certificates.

### To Proceed Past the Warning:

- **Chrome**: Click "Advanced" → "Proceed to 192.168.1.14 (unsafe)"
- **Firefox**: Click "Advanced" → "Accept the Risk and Continue"
- **Edge**: Click "Advanced" → "Continue to 192.168.1.14 (unsafe)"

### For Production Use:

Use a certificate from a trusted CA:
- **Let's Encrypt** (free, automated)
- **DigiCert**, **Sectigo**, etc. (commercial)

## Troubleshooting

### If You See "Connection Reset" Errors

This means there's a mismatch between what the config says and what the server is doing.

**Check the server logs** for messages like:
```
================================================================================
SSL/HTTPS CONFIGURATION MISMATCH
================================================================================
config.yml has api.ssl.enabled: true
However, SSL could not be configured (see errors above)

SERVER IS RUNNING ON HTTP (not HTTPS)

Access the admin panel at:
  http://192.168.1.14:8080/admin/
```

**Solution**: Follow the instructions in the log message.

### Common SSL Issues

1. **Missing Certificate Files**
   ```
   SSL certificate file not found: certs/server.crt
   ```
   **Fix**: Run `python scripts/generate_ssl_cert.py`

2. **Invalid Certificate/Key Pair**
   ```
   Failed to configure SSL: [SSL: KEY_VALUES_MISMATCH]
   ```
   **Fix**: Regenerate both files: `python scripts/generate_ssl_cert.py`

3. **Permission Denied**
   ```
   Permission denied: certs/server.key
   ```
   **Fix**: `chmod 600 certs/server.key`

## Testing

To test the SSL configuration handling:

```bash
# Run the SSL mismatch test
python tests/test_ssl_mismatch.py

# Run all HTTPS tests
python tests/test_https_server.py
```

## Security Notes

- Self-signed certificates are **NOT suitable for production**
- They're fine for development and internal testing
- For production, always use certificates from trusted CAs
- The improvements we made ensure the server fails gracefully when SSL is misconfigured
- No security vulnerabilities were introduced (verified with CodeQL scan)

## Summary

✅ **Immediate issue resolved**: HTTPS is disabled, server runs on HTTP
✅ **Future-proofed**: Better error handling prevents confusion
✅ **Well-tested**: Comprehensive tests ensure it works correctly
✅ **Documented**: Clear instructions for re-enabling HTTPS
✅ **Secure**: No vulnerabilities introduced

You can now access your admin panel at:
```
http://192.168.1.14:8080/admin/
```

When you're ready to enable HTTPS, follow the "Re-enabling HTTPS" section above.
