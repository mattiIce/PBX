# Integration Port Allocation Guide

**Date**: December 15, 2025  
**Status**: Fixed - Port Conflicts Resolved

## Summary

This document describes the port allocation for all open-source integrations and how to update existing configurations to avoid port conflicts.

## Port Conflicts Fixed

### Problem
The original configuration had port conflicts:
- **Jitsi** was configured to use `https://localhost` (default HTTPS port 443)
- **EspoCRM** was also configured to use `https://localhost` (default HTTPS port 443)
- Both services trying to use port 443 would cause conflicts

### Solution
Updated default configurations to use different approaches:

| Integration | Old Configuration | New Configuration | Port Used |
|-------------|------------------|-------------------|-----------|
| **Jitsi Meet** | `https://localhost` (port 443) | `https://meet.jit.si` (public server) | N/A (external) |
| **Matrix** | `https://localhost:8008` | `https://matrix.org` (public server) | N/A (external) |
| **EspoCRM** | `https://localhost/api/v1` (port 443) | `http://localhost:8000/api/v1` | 8000 |
| **PBX API** | `http://0.0.0.0:8080` | `http://0.0.0.0:8080` | 8080 |
| **PBX SIP** | `udp://0.0.0.0:5060` | `udp://0.0.0.0:5060` | 5060 |

## Default Configuration Strategy

The new defaults use **public servers** for Jitsi and Matrix to avoid local port conflicts:

### Jitsi Meet
- **Default**: `https://meet.jit.si` (free public server)
- **Self-hosted alternative**: `https://jitsi.yourcompany.com:8443` (port 8443)
- **Local development**: `http://localhost:8888` (port 8888)

### Matrix
- **Default**: `https://matrix.org` (public homeserver)
- **Self-hosted alternative**: `http://localhost:8008` (Matrix Synapse default port)
- **HTTPS alternative**: `https://localhost:8448` (Synapse federation port)

### EspoCRM
- **Default**: `http://localhost:8000/api/v1` (port 8000 to avoid conflicts)
- **Production**: `https://crm.yourcompany.com/api/v1` (standard HTTPS port 443 on dedicated server)

## Updating Existing Configurations

If you have an existing `config.yml`, follow these steps to update it:

### Option 1: Automatic Update (Recommended)

Your existing `config.yml` will be automatically updated when you pull the latest changes. The system will use the new defaults which point to public servers (no local installation required).

### Option 2: Manual Update

If you prefer self-hosted integrations, edit your `config.yml`:

```yaml
integrations:
  # Jitsi Meet - Video Conferencing
  jitsi:
    enabled: true
    # Option 1: Use free public server (no installation needed)
    server_url: https://meet.jit.si
    
    # Option 2: Self-hosted on dedicated port
    # server_url: https://jitsi.yourcompany.com:8443
    
    # Option 3: Local development
    # server_url: http://localhost:8888

  # Matrix - Team Messaging
  matrix:
    enabled: true
    # Option 1: Use public homeserver (requires account creation)
    homeserver_url: https://matrix.org
    
    # Option 2: Self-hosted Synapse (default port)
    # homeserver_url: http://localhost:8008
    
    # Option 3: Self-hosted with HTTPS
    # homeserver_url: https://localhost:8448
    
    bot_username: ''  # Required for Matrix
    bot_password: ${MATRIX_BOT_PASSWORD}
    notification_room: ''

  # EspoCRM - CRM
  espocrm:
    enabled: true
    # Option 1: Local installation on dedicated port (avoids conflict)
    api_url: http://localhost:8000/api/v1
    
    # Option 2: Production server (standard HTTPS port)
    # api_url: https://crm.yourcompany.com/api/v1
    
    api_key: ${ESPOCRM_API_KEY}
```

### Option 3: Keep Self-Hosted with Dedicated Ports

If you're running self-hosted services on the same machine as the PBX:

#### Configure Apache/Nginx for EspoCRM on Port 8000

**Apache Configuration** (`/etc/apache2/sites-available/espocrm.conf`):
```apache
Listen 8000
<VirtualHost *:8000>
    DocumentRoot /var/www/espocrm
    ServerName localhost
    
    <Directory /var/www/espocrm>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

Enable and restart:
```bash
sudo a2ensite espocrm
sudo systemctl restart apache2
```

#### Configure Jitsi on Port 8443

**Nginx Configuration** (modify `/etc/nginx/sites-available/jitsi-meet.conf`):
```nginx
server {
    listen 8443 ssl http2;
    listen [::]:8443 ssl http2;
    server_name jitsi.yourcompany.com;
    
    # SSL configuration
    ssl_certificate /etc/jitsi/meet/jitsi.crt;
    ssl_certificate_key /etc/jitsi/meet/jitsi.key;
    
    # ... rest of configuration
}
```

Restart Jitsi:
```bash
sudo systemctl restart nginx
sudo systemctl restart jicofo
sudo systemctl restart jitsi-videobridge2
```

## Port Allocation Reference

### Standard Ports (No Changes Required)

| Service | Protocol | Port | Purpose |
|---------|----------|------|---------|
| PBX SIP | UDP | 5060 | SIP signaling |
| PBX RTP | UDP | 10000-20000 | Audio/video streams |
| PBX API | HTTP | 8080 | REST API and admin panel |

### Integration Ports (New Allocations)

| Service | Protocol | Port | Configuration |
|---------|----------|------|---------------|
| Matrix Synapse | HTTP | 8008 | Client API (if self-hosted) |
| Matrix Federation | HTTPS | 8448 | Server-to-server (if self-hosted) |
| Jitsi Meet | HTTPS | 8443 | Web interface (if self-hosted) |
| EspoCRM | HTTP | 8000 | API endpoint (if self-hosted) |

### Public Server Defaults (No Local Ports)

If using default configuration with public servers:
- **Jitsi**: Uses `https://meet.jit.si` (no local ports)
- **Matrix**: Uses `https://matrix.org` (no local ports)
- **EspoCRM**: Must be self-hosted (default: port 8000)

## Firewall Configuration

If self-hosting all services, update your firewall rules:

```bash
# PBX Core (no changes)
sudo firewall-cmd --permanent --add-port=5060/udp    # SIP
sudo firewall-cmd --permanent --add-port=10000-20000/udp  # RTP
sudo firewall-cmd --permanent --add-port=8080/tcp    # API

# Integration Ports (new)
sudo firewall-cmd --permanent --add-port=8000/tcp    # EspoCRM
sudo firewall-cmd --permanent --add-port=8008/tcp    # Matrix HTTP
sudo firewall-cmd --permanent --add-port=8448/tcp    # Matrix Federation
sudo firewall-cmd --permanent --add-port=8443/tcp    # Jitsi

sudo firewall-cmd --reload
```

## Verification

After updating your configuration, verify no port conflicts:

```bash
# Check which ports are in use
sudo netstat -tulpn | grep -E ':(443|8000|8008|8080|8443|8448)'

# Expected output (if all self-hosted):
# tcp  0.0.0.0:8080  PBX API
# tcp  0.0.0.0:8000  Apache (EspoCRM)
# tcp  0.0.0.0:8008  Synapse (Matrix)
# tcp  0.0.0.0:8448  Synapse Federation
# tcp  0.0.0.0:8443  Nginx (Jitsi)
```

## Migration Path

### From Old Config to New Config

1. **Backup** your current `config.yml`:
   ```bash
   cp config.yml config.yml.backup
   ```

2. **Pull** the latest changes:
   ```bash
   git pull origin main
   ```

3. **Review** the integration section in `config.yml`

4. **Choose** your deployment strategy:
   - **Easy**: Use default public servers (Jitsi, Matrix)
   - **Advanced**: Self-host on dedicated ports

5. **Update** environment variables in `.env`:
   ```bash
   # Matrix bot credentials (if using Matrix)
   MATRIX_BOT_PASSWORD=your-bot-password
   
   # EspoCRM API key (if using EspoCRM)
   ESPOCRM_API_KEY=your-api-key
   ```

6. **Restart** the PBX:
   ```bash
   sudo systemctl restart pbx
   ```

## Benefits of New Configuration

✅ **No Port Conflicts**: Each service uses a unique port  
✅ **Easier Setup**: Default to public servers (no installation needed)  
✅ **Flexible**: Can switch to self-hosted anytime  
✅ **Production Ready**: Clear separation for scaling  
✅ **Well-Documented**: Port allocation clearly defined  

## Troubleshooting

### Error: "Address already in use"

If you see this error, another service is using the port:

```bash
# Find what's using the port
sudo lsof -i :8000

# Stop the conflicting service or choose a different port
```

### Integration Not Working

1. Check if integration is enabled:
   ```bash
   grep -A 5 "jitsi:\|matrix:\|espocrm:" config.yml
   ```

2. Verify API endpoints are accessible:
   ```bash
   # For self-hosted services
   curl http://localhost:8000/api/v1  # EspoCRM
   curl http://localhost:8008/_matrix/client/versions  # Matrix
   curl https://localhost:8443  # Jitsi
   ```

3. Check PBX logs:
   ```bash
   tail -f logs/pbx.log | grep -i "integration"
   ```

## Summary

The port allocation has been fixed to prevent conflicts. The new default configuration uses public servers for ease of setup, but you can easily switch to self-hosted services on dedicated ports as documented above.

---

**For more information**, see:
- [OPEN_SOURCE_INTEGRATIONS.md](OPEN_SOURCE_INTEGRATIONS.md) - Complete integration guide
- [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md) - Setup troubleshooting
- [QUICK_SETUP_GUIDE.md](QUICK_SETUP_GUIDE.md) - Quick start guide
