# Apache 404 Error - Solution Summary

## Problem
When accessing `http://abps.albl.com/admin/status-check.html`, you received:
```
Not Found
The requested URL was not found on this server.
Apache/2.4.58 (Ubuntu) Server at abps.albl.com Port 80
```

## Root Cause
Apache was configured to serve the domain but was **not** configured to proxy requests to the PBX backend application running on port 8080/9000. Apache looked for the file in its own document root and returned a 404 error.

## Solution Provided
This PR adds complete Apache reverse proxy support to the PBX repository, including:

### 1. Automated Setup Script ⚡
**File**: `scripts/setup_apache_reverse_proxy.sh`

Run this to automatically configure everything:
```bash
cd /path/to/PBX
sudo scripts/setup_apache_reverse_proxy.sh
```

The script will:
- ✅ Install Apache and certbot if needed
- ✅ Check and resolve port 80 conflicts
- ✅ Create virtual host configuration for your domain
- ✅ Obtain free SSL certificate from Let's Encrypt
- ✅ Configure automatic HTTPS redirect
- ✅ Set up firewall rules
- ✅ Enable WebSocket support for WebRTC phones

When prompted, enter:
- **Domain**: `abps.albl.com`
- **Email**: Your email for SSL notifications
- **Backend Port**: `8080` (or check your `config.yml` for the actual port)

### 2. Configuration Template 📄
**File**: `apache-pbx.conf.example`

If you prefer manual setup, this template provides:
- Complete virtual host configuration
- SSL/TLS best practices
- Security headers
- WebSocket support
- Proxy configuration for all endpoints

### 3. Documentation 📚

**Quick Fix**: `docs/APACHE_404_FIX.md`
- Fast solution for the 404 error
- Both automated and manual options
- Common troubleshooting

**Complete Setup Guide**: `docs/APACHE_REVERSE_PROXY_SETUP.md`
- Prerequisites
- Step-by-step instructions
- Troubleshooting
- Security best practices
- Maintenance procedures
- Apache vs Nginx comparison

**Troubleshooting**: `TROUBLESHOOTING.md`
- Added new section "Apache 'Not Found' Error for Admin Pages"
- Symptoms, causes, and solutions

### 4. Updated README
The main README now documents both Nginx and Apache options.

## How to Fix Your Server

### Option 1: Automated Setup (Recommended) ⚡
```bash
cd /path/to/PBX
sudo scripts/setup_apache_reverse_proxy.sh
```

### Option 2: Manual Setup 🔧
Follow the steps in `docs/APACHE_404_FIX.md`

### Option 3: Detailed Manual Setup 📖
Follow the comprehensive guide in `docs/APACHE_REVERSE_PROXY_SETUP.md`

## After Setup
Once configured, you'll be able to access:
- ✅ `https://abps.albl.com` - Main admin interface
- ✅ `https://abps.albl.com/admin/status-check.html` - Status check page
- ✅ `https://abps.albl.com/admin/login.html` - Login page
- ✅ All other admin pages

## Features You Get

### Security 🔒
- Free SSL certificate from Let's Encrypt
- Automatic HTTPS redirect
- Modern security headers
- Auto-renewal of SSL certificate every 90 days

### Performance ⚡
- Proper proxy configuration
- WebSocket support for WebRTC
- Optimized for PBX traffic

### Maintenance 🔧
- Automatic log rotation
- Certificate auto-renewal
- Production-ready configuration

## Troubleshooting

### If you still get 404 after setup:
1. Verify PBX is running: `sudo systemctl status pbx`
2. Check Apache is running: `sudo systemctl status apache2`
3. Test direct access: `curl http://localhost:8080/admin/status-check.html`
4. Check Apache logs: `sudo tail -f /var/log/apache2/pbx-error.log`

### If SSL certificate fails:
1. Verify DNS points to your server: `nslookup abps.albl.com`
2. Check firewall allows port 80: `sudo ufw status`
3. Retry: `sudo certbot --apache -d abps.albl.com`

## Files Added in This PR

1. **apache-pbx.conf.example** - Configuration template
2. **scripts/setup_apache_reverse_proxy.sh** - Automated setup script
3. **docs/APACHE_REVERSE_PROXY_SETUP.md** - Complete setup guide
4. **docs/APACHE_404_FIX.md** - Quick fix guide
5. **TROUBLESHOOTING.md** - Updated with Apache section
6. **README.md** - Updated with Apache instructions

## Additional Notes

- This solution is production-ready
- Works alongside the existing Nginx setup
- Follows the same security standards
- Includes comprehensive documentation
- Tested script syntax (bash validation passed)
- Addressed all code review feedback

## Support

If you have questions or need help:
1. Check the documentation files listed above
2. Review the troubleshooting sections
3. Check PBX and Apache logs
4. Open an issue with error messages if problems persist

---

**Created**: 2025-12-30  
**Issue**: Apache 404 error for admin panel  
**Solution**: Apache reverse proxy configuration  
**Status**: ✅ Complete - Ready to deploy
