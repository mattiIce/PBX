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
Updated default configurations to use dedicated local ports to avoid conflicts:

| Integration | Old Configuration | New Configuration | Port Used |
|-------------|------------------|-------------------|-----------|
| **Jitsi Meet** | `https://localhost` (port 443) | `https://localhost:8443` | 8443 |
| **Matrix** | `https://localhost:8008` | `https://localhost:8008` | 8008 |
| **EspoCRM** | `https://localhost/api/v1` (port 443) | `https://localhost:8001/api/v1` | 8001 |
| **PBX API** | `http://0.0.0.0:8080` | `http://0.0.0.0:8080` | 8080 |
| **PBX SIP** | `udp://0.0.0.0:5060` | `udp://0.0.0.0:5060` | 5060 |

## Default Configuration Strategy

The new defaults use **dedicated local ports** for each integration to avoid conflicts while keeping all services on the same machine:

### Jitsi Meet
- **Default**: `https://localhost:8443` (dedicated HTTPS port)
- **Alternative**: `https://jitsi.yourcompany.com:8443` (network deployment)
- **Development**: `http://localhost:8888` (HTTP for testing)

### Matrix
- **Default**: `https://localhost:8008` (Matrix Synapse standard port)
- **Alternative**: `https://localhost:8448` (Synapse federation port for HTTPS)
- **Network**: `https://matrix.yourcompany.com:8008`

### EspoCRM
- **Default**: `https://localhost:8001/api/v1` (dedicated port to avoid conflicts)
- **Alternative**: `http://localhost:8001/api/v1` (HTTP for development)
- **Network**: `https://crm.yourcompany.com/api/v1` (standard HTTPS on dedicated server)

## Updating Existing Configurations

If you have an existing `config.yml`, follow these steps to update it:

### Option 1: Automatic Update (Recommended)

Your existing `config.yml` will be automatically updated when you pull the latest changes. The system will use the new defaults which point to local servers on dedicated ports to avoid conflicts.

### Option 2: Manual Update

If you need to customize the ports, edit your `config.yml`:

```yaml
integrations:
  # Jitsi Meet - Video Conferencing
  jitsi:
    enabled: true
    # Default: Local server on dedicated port 8443
    server_url: https://localhost:8443
    
    # Alternative: Network deployment
    # server_url: https://jitsi.yourcompany.com:8443
    
    # Alternative: Development (HTTP)
    # server_url: http://localhost:8888

  # Matrix - Team Messaging
  matrix:
    enabled: true
    # Default: Local Synapse on standard port 8008
    homeserver_url: https://localhost:8008
    
    # Alternative: Federation port with HTTPS
    # homeserver_url: https://localhost:8448
    
    # Alternative: Network deployment
    # homeserver_url: https://matrix.yourcompany.com:8008
    
    bot_username: ''  # Required for Matrix
    bot_password: ${MATRIX_BOT_PASSWORD}
    notification_room: ''

  # EspoCRM - CRM
  espocrm:
    enabled: true
    # Default: Local installation on dedicated port 8001
    api_url: https://localhost:8001/api/v1
    
    # Alternative: HTTP for development
    # api_url: http://localhost:8001/api/v1
    
    # Alternative: Network deployment
    # api_url: https://crm.yourcompany.com/api/v1
    
    api_key: ${ESPOCRM_API_KEY}
```

### Option 3: Self-Hosted Configuration on Same Machine

If you're running self-hosted services on the same machine as the PBX, here's how to configure each service:

#### Configure Apache/Nginx for EspoCRM on Port 8001

**Apache Configuration** (`/etc/apache2/sites-available/espocrm.conf`):
```apache
Listen 8001
<VirtualHost *:8001>
    DocumentRoot /var/www/espocrm
    ServerName localhost
    
    # SSL Configuration (recommended)
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/espocrm.crt
    SSLCertificateKeyFile /etc/ssl/private/espocrm.key
    
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
sudo a2enmod ssl  # Enable SSL module
sudo systemctl restart apache2
```

#### Configure Jitsi on Port 8443

**Nginx Configuration** (modify `/etc/nginx/sites-available/jitsi-meet.conf`):
```nginx
server {
    listen 8443 ssl http2;
    listen [::]:8443 ssl http2;
    server_name localhost;  # or jitsi.yourcompany.com
    
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

#### Matrix Synapse on Port 8008 (Default)

Matrix Synapse uses port 8008 by default, which doesn't conflict. No changes needed unless you want to use HTTPS on port 8448.

## Port Allocation Reference

### Standard Ports (No Changes Required)

| Service | Protocol | Port | Purpose |
|---------|----------|------|---------|
| PBX SIP | UDP | 5060 | SIP signaling |
| PBX RTP | UDP | 10000-20000 | Audio/video streams |
| PBX API | HTTP | 8080 | REST API and admin panel |

### Integration Ports (Local Self-Hosted)

| Service | Protocol | Port | Configuration |
|---------|----------|------|---------------|
| Matrix Synapse | HTTPS | 8008 | Client API (default, no conflict) |
| Matrix Federation | HTTPS | 8448 | Server-to-server (alternative) |
| Jitsi Meet | HTTPS | 8443 | Web interface (dedicated port) |
| EspoCRM | HTTPS | 8001 | API endpoint (dedicated port) |

**All ports are unique - no conflicts**

## Firewall Configuration

If self-hosting all services locally, update your firewall rules:

```bash
# PBX Core (no changes)
sudo firewall-cmd --permanent --add-port=5060/udp    # SIP
sudo firewall-cmd --permanent --add-port=10000-20000/udp  # RTP
sudo firewall-cmd --permanent --add-port=8080/tcp    # API

# Integration Ports (local servers)
sudo firewall-cmd --permanent --add-port=8001/tcp    # EspoCRM HTTPS
sudo firewall-cmd --permanent --add-port=8008/tcp    # Matrix HTTPS
sudo firewall-cmd --permanent --add-port=8448/tcp    # Matrix Federation (optional)
sudo firewall-cmd --permanent --add-port=8443/tcp    # Jitsi HTTPS

sudo firewall-cmd --reload
```

## Verification

After updating your configuration, verify no port conflicts:

```bash
# Check which ports are in use
sudo netstat -tulpn | grep -E ':(8001|8008|8080|8443|8448)'

# Expected output (if all self-hosted locally):
# tcp  0.0.0.0:8080  PBX API
# tcp  0.0.0.0:8001  Apache (EspoCRM)
# tcp  0.0.0.0:8008  Synapse (Matrix)
# tcp  0.0.0.0:8448  Synapse Federation (optional)
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

4. **Configure your local servers** on the new ports:
   - Jitsi: Port 8443 (instead of 443)
   - Matrix: Port 8008 (no change, already used)
   - EspoCRM: Port 8001 (instead of 443)

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
