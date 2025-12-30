# Reverse Proxy SSL Troubleshooting Guide

## ERR_SSL_PROTOCOL_ERROR - Common Issue After Enabling SSL

### Problem Description

After configuring SSL on the admin UI using Apache as a reverse proxy, you may encounter:

```
This site can't provide a secure connection
abps.albl.com sent an invalid response.
ERR_SSL_PROTOCOL_ERROR
```

or

```
Proxy Error
The proxy server received an invalid response from an upstream server.
The proxy server could not handle the request

Reason: Error reading from remote server
```

### Root Cause

This error occurs when the **backend PBX API has SSL enabled** (`api.ssl.enabled: true` in `config.yml`) while Apache is configured as a reverse proxy expecting an HTTP backend.

### Architecture Explanation

#### ✅ Correct Setup (Works)
```
Browser ──HTTPS──> Apache (port 443) ──HTTP──> PBX Backend (port 9000)
         SSL/TLS    ↑ SSL Termination      ↑ Plain HTTP
```

- Apache handles SSL/TLS encryption on port 443
- Apache proxies requests to backend on port 9000 using plain HTTP
- Backend serves HTTP only (internal communication)
- **Configuration**: `api.ssl.enabled: false` in `config.yml`

#### ❌ Incorrect Setup (Causes Error)
```
Browser ──HTTPS──> Apache (port 443) ──HTTPS──> PBX Backend (port 9000)
         SSL/TLS                         SSL/TLS (causes conflict)
```

- Apache expects HTTP backend but finds HTTPS
- SSL protocol mismatch occurs
- Results in ERR_SSL_PROTOCOL_ERROR
- **Configuration**: `api.ssl.enabled: true` in `config.yml` (WRONG!)

### Solution

#### Step 1: Check Current Configuration

```bash
cd /path/to/PBX
grep -A 5 "api:" config.yml | grep -A 2 "ssl:"
```

You should see:
```yaml
ssl:
  enabled: false  # ← This should be FALSE for reverse proxy
```

#### Step 2: Edit Configuration

If `enabled: true`, change it to `false`:

```bash
nano config.yml
```

Find the `api.ssl` section and ensure:
```yaml
api:
  host: 0.0.0.0
  port: 9000
  ssl:
    enabled: false  # ← Set to false when using Apache reverse proxy
```

#### Step 3: Restart PBX Service

```bash
sudo systemctl restart pbx
```

#### Step 4: Verify Backend is Running HTTP

```bash
# Should return JSON health status
curl http://localhost:9000/api/health

# Should get connection refused or certificate error
curl https://localhost:9000/api/health
```

#### Step 5: Test Through Apache

```bash
# This should work now
curl https://abps.albl.com/api/health
```

### Verification Checklist

- [ ] `config.yml` has `api.ssl.enabled: false`
- [ ] PBX service restarted: `sudo systemctl restart pbx`
- [ ] Backend responds to HTTP: `curl http://localhost:9000/api/health`
- [ ] Backend does NOT respond to HTTPS: `curl https://localhost:9000/api/health` (should fail)
- [ ] Apache HTTPS works: `curl https://abps.albl.com/api/health`
- [ ] Browser can access: `https://abps.albl.com/admin/`

### Apache Configuration Verification

Your Apache configuration (`/etc/apache2/sites-available/pbx.conf`) should proxy to HTTP:

```apache
<VirtualHost *:443>
    ServerName abps.albl.com
    
    # SSL Certificate (handled by Apache)
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/abps.albl.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/abps.albl.com/privkey.pem
    
    # Proxy to HTTP backend (NOT HTTPS!)
    <Location />
        ProxyPass http://localhost:9000/
        ProxyPassReverse http://localhost:9000/
        
        # Important: Tell backend it's behind HTTPS proxy
        RequestHeader set X-Forwarded-Proto "https"
        RequestHeader set X-Forwarded-Port "443"
    </Location>
</VirtualHost>
```

Note the `http://localhost:9000/` (not `https://`)

### Common Mistakes

1. **Enabling SSL in config.yml** when using reverse proxy
   - Fix: Set `api.ssl.enabled: false`

2. **Apache proxy pointing to HTTPS**
   - Fix: Change `ProxyPass https://localhost:9000/` to `ProxyPass http://localhost:9000/`

3. **Firewall blocking internal HTTP**
   - Fix: Ensure localhost communication isn't blocked

4. **Wrong port in Apache config**
   - Fix: Ensure port matches `config.yml` (default: 9000)

### When to Use Direct SSL (api.ssl.enabled: true)

Only use `api.ssl.enabled: true` when:
- **NOT** using Apache/Nginx as reverse proxy
- Accessing PBX API directly (e.g., `https://192.168.1.14:9000/admin/`)
- Development or testing environment
- Self-signed certificates are acceptable

**Not recommended for production!** Use reverse proxy instead.

### Debugging Tools

#### Check Apache Logs
```bash
tail -f /var/log/apache2/pbx-ssl-error.log
```

#### Check PBX Logs
```bash
tail -f /path/to/PBX/logs/pbx.log
```

#### Test Backend Directly
```bash
# Should work (HTTP)
curl -v http://localhost:9000/api/health

# Should fail (HTTPS) when correctly configured
curl -v https://localhost:9000/api/health
```

#### Test Through Reverse Proxy
```bash
# Should work
curl -v https://abps.albl.com/api/health
```

#### Check Listening Ports
```bash
# PBX should listen on 9000 (not SSL)
sudo netstat -tlnp | grep 9000

# Apache should listen on 443 (SSL)
sudo netstat -tlnp | grep 443
```

### Getting Help

If the issue persists after following this guide:

1. Check both Apache and PBX logs for errors
2. Verify Apache modules are enabled:
   ```bash
   sudo a2enmod proxy proxy_http ssl headers
   sudo systemctl restart apache2
   ```
3. Ensure PBX backend is actually running:
   ```bash
   sudo systemctl status pbx
   ```
4. Review the complete configuration files for typos or conflicts

### Summary

**Key Point**: When using Apache (or Nginx) as a reverse proxy for SSL termination, the backend PBX API **must run on HTTP** (not HTTPS). The reverse proxy handles all SSL/TLS encryption.

Set `api.ssl.enabled: false` in `config.yml` and restart the PBX service.
