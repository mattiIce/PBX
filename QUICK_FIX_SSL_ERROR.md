# Quick Fix: ERR_SSL_PROTOCOL_ERROR

## The Problem

You're seeing this error after enabling SSL:
```
ERR_SSL_PROTOCOL_ERROR
This site can't provide a secure connection
abps.albl.com sent an invalid response
```

## The Solution (30 seconds)

```bash
# 1. Edit the config file
sudo nano /path/to/PBX/config.yml

# 2. Find this section and change 'true' to 'false':
api:
  ssl:
    enabled: false  # ← Change this to false

# 3. Save (Ctrl+O, Enter, Ctrl+X) and restart
sudo systemctl restart pbx

# 4. Done! Test your site
# Open browser: https://abps.albl.com/admin/
```

## Why This Works

When using Apache as a reverse proxy:

**✅ CORRECT (Works):**
```
Internet → Apache (HTTPS) → PBX Backend (HTTP)
          SSL Handled Here ↑      Plain HTTP ↑
```

**❌ WRONG (Causes Error):**
```
Internet → Apache (HTTPS) → PBX Backend (HTTPS)
          SSL Here ↑          SSL Here Too ↑
                            ← CONFLICT! →
```

Apache **expects** the backend to be HTTP. When the backend is HTTPS, you get ERR_SSL_PROTOCOL_ERROR.

## Verify It's Fixed

After restarting, these should be true:

✓ Backend on HTTP:
```bash
curl http://localhost:9000/api/health
# Returns JSON status
```

✓ Backend NOT on HTTPS:
```bash
curl https://localhost:9000/api/health
# Connection refused (expected!)
```

✓ Apache proxy works:
```bash
curl https://abps.albl.com/api/health
# Returns JSON status through Apache
```

## Need More Help?

See the detailed guide: [REVERSE_PROXY_SSL_TROUBLESHOOTING.md](REVERSE_PROXY_SSL_TROUBLESHOOTING.md)

Or check the main troubleshooting guide: [TROUBLESHOOTING.md](TROUBLESHOOTING.md#err_ssl_protocol_error-with-reverse-proxy)
