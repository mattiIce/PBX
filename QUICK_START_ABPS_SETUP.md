# Quick Start: abps.albl.com Setup Guide

This is your complete implementation guide for Option 1: DNS + Reverse Proxy setup for accessing your PBX at `https://abps.albl.com`.

> **Note:** In this guide, `[PBX_INSTALL_DIR]` refers to your PBX installation directory (e.g., `/opt/PBX`, `/home/user/PBX`, or wherever you installed the PBX system).

## ✅ What You'll Get

After completing these steps:
- ✅ Access admin panel: **`https://abps.albl.com`** (no port needed!)
- ✅ Valid SSL certificate from Let's Encrypt (auto-renews every 90 days)
- ✅ Professional, secure HTTPS connection with TLS 1.3 support
- ✅ Standard ports (80/443) instead of :8080
- ✅ Enhanced security with rate limiting and security headers
- ✅ WebSocket support for WebRTC phone functionality

---

## 📋 Prerequisites Checklist

Before starting, make sure you have:

### Required ✅
- [ ] Root/sudo access to your PBX server
- [ ] PBX system installed and running (see [INSTALLATION.md](INSTALLATION.md))
- [ ] Access to your DNS server to add records
- [ ] Your PBX server's **public** IP address
- [ ] Port 80 and 443 available (not blocked by firewall)
- [ ] Valid email address for SSL certificate notifications

### Recommended ⚡
- [ ] Ubuntu 24.04 LTS or 22.04 LTS (tested and verified)
- [ ] At least 2GB RAM and 20GB disk space
- [ ] Static IP address or dynamic DNS service
- [ ] Firewall configured (ufw or iptables)

---

## 🚀 Implementation Steps

### Step 1: Configure DNS (Do This First!)

Add an A record to your DNS server:

```
Type: A
Name: abps
Domain: albl.com
Value: [YOUR_PBX_SERVER_IP]
TTL: 3600 (or your default)
```

**Result:** `abps.albl.com` → `your-pbx-server-ip`

**Verify DNS is working:**
```bash
nslookup abps.albl.com
# Should return your PBX server IP
```

⚠️ **Important:** Wait a few minutes for DNS propagation before proceeding to Step 2.

---

### Step 2: Run Automated Setup (Easiest Method)

SSH into your PBX server and run:

```bash
# Navigate to PBX directory
cd [PBX_INSTALL_DIR]

# Run the automated setup script
sudo scripts/setup_reverse_proxy.sh
```

**When prompted, enter:**
1. **Domain name:** `abps.albl.com`
2. **Email address:** Your email for SSL notifications
3. **Backend port:** `8080` (default, just press Enter)
4. **Confirm:** Type `y` and press Enter

**The script will:**
- ✅ Install nginx (if not already installed)
- ✅ Install certbot for SSL certificates
- ✅ Create nginx configuration for abps.albl.com
- ✅ Obtain free SSL certificate from Let's Encrypt
- ✅ Configure automatic HTTPS redirect
- ✅ Enable rate limiting for API endpoints
- ✅ Configure firewall rules
- ✅ Start nginx

**Expected output (if SSL succeeds):**
```
================================================================
Setup Complete!
================================================================

Your PBX admin panel is now accessible at:
  https://abps.albl.com
```

**Note:** If the SSL certificate setup encounters an error (e.g., OpenSSL compatibility issue), the script will:
- ✅ Continue with HTTP-only configuration
- ✅ Provide detailed troubleshooting steps
- ✅ Complete successfully so you can access the site via `http://abps.albl.com`
- ⚠️ You can fix the SSL issue later following the provided instructions

---

### Step 3: Test Your Setup

1. **Open your web browser**
2. **Navigate to:** `https://abps.albl.com`
3. **You should see:** PBX admin login page with valid SSL (green padlock)

**Troubleshooting if it doesn't work:**
```bash
# Check nginx status
sudo systemctl status nginx

# Check nginx logs
sudo tail -f /var/log/nginx/abps.albl.com-error.log

# Check DNS
nslookup abps.albl.com

# Test locally on server
curl -I http://localhost:8080/admin/
```

**If you got an SSL certificate error during setup:**

The script will have provided specific solutions. Common fix for OpenSSL compatibility issues:

```bash
# Option 1: Update certbot
sudo apt update
sudo apt upgrade certbot python3-certbot-nginx
sudo pip3 install --upgrade cryptography
sudo certbot --nginx -d abps.albl.com

# Option 2: Reinstall certbot via snap (recommended)
sudo apt remove certbot python3-certbot-nginx
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx -d abps.albl.com
```

See the [Reverse Proxy Setup Guide](REVERSE_PROXY_SETUP.md#certbot-openssl-compatibility-error) for more details.

---

### Step 4: (Optional) Restrict PBX to Localhost Only

For enhanced security, restrict PBX to only listen on localhost:

**Edit config.yml:**
```bash
nano [PBX_INSTALL_DIR]/config.yml
```

**Change:**
```yaml
api:
  host: 127.0.0.1  # Changed from 0.0.0.0
  port: 8080
```

**Restart PBX:**
```bash
sudo systemctl restart pbx
# Or if running manually: stop and restart python main.py
```

**Why do this?**
- PBX is only accessible through nginx (more secure)
- Can't bypass nginx to access :8080 directly
- All traffic goes through HTTPS

---

## 🔐 Security Configuration

### Firewall Rules (Priority: CRITICAL ⚠️)

```bash
# Allow HTTPS and HTTP (handled by setup script, but verify)
sudo ufw allow 80/tcp comment "HTTP for Let's Encrypt validation"
sudo ufw allow 443/tcp comment "HTTPS for admin panel"

# Block direct access to 8080 from external network (STRONGLY RECOMMENDED)
# NOTE: Configure PBX to bind to 127.0.0.1 BEFORE applying this rule (see below)
sudo ufw delete allow 8080/tcp  # Remove if exists
sudo ufw deny from any to any port 8080 comment "Block direct PBX access"

# Allow SIP for phones (UDP recommended for SIP)
sudo ufw allow 5060/udp comment "SIP signaling"
sudo ufw allow 5060/tcp comment "SIP signaling (TCP)"

# Allow RTP for audio (adjust range if needed)
sudo ufw allow 10000:20000/udp comment "RTP media streams"

# Enable firewall if not already enabled
sudo ufw enable

# Check firewall status
sudo ufw status numbered
```

### Additional Security Measures

**1. Restrict PBX to Localhost Only (HIGHLY RECOMMENDED)**

⚠️ **IMPORTANT:** Do this FIRST before blocking port 8080 in the firewall!

This ensures the PBX API is ONLY accessible through nginx, not directly:

```bash
# Edit config.yml
nano [PBX_INSTALL_DIR]/config.yml
```

Change the following in config.yml:
```yaml
api:
  # CRITICAL: Preserve exact indentation (2 spaces per level)
  host: 127.0.0.1  # Changed from 0.0.0.0 - binds to localhost only
  port: 8080
```

⚠️ **Restart PBX immediately** after this change:
```bash
sudo systemctl restart pbx

# Verify PBX is running and accessible via nginx
curl -I http://localhost:8080/admin/
```

**Why this matters:** Changing from 0.0.0.0 to 127.0.0.1 makes the PBX only accessible from localhost. The service must be restarted for this change to take effect.
```

**2. Monitor Failed Login Attempts**

```bash
# Check nginx logs for suspicious activity
sudo tail -f /var/log/nginx/abps.albl.com-access.log | grep -i "login\|admin"
```

**3. Keep System Updated**

```bash
# Update system packages regularly
sudo apt update && sudo apt upgrade -y

# Check for PBX updates
cd [PBX_INSTALL_DIR]
git fetch
git status
```

### SSL Certificate Auto-Renewal

Let's Encrypt certificates expire every 90 days but auto-renew.

**Verify auto-renewal is set up:**
```bash
sudo certbot renew --dry-run
```

**Check certificate status:**
```bash
sudo certbot certificates
```

**Manual renewal (if needed):**
```bash
sudo certbot renew
sudo systemctl reload nginx
```

---

## 📊 Monitoring & Logs

### Check Logs

**Nginx access log:**
```bash
sudo tail -f /var/log/nginx/abps.albl.com-access.log
```

**Nginx error log:**
```bash
sudo tail -f /var/log/nginx/abps.albl.com-error.log
```

**PBX log:**
```bash
tail -f [PBX_INSTALL_DIR]/logs/pbx.log
```

### Test Nginx Configuration

```bash
# Test configuration syntax
sudo nginx -t

# Reload nginx (after config changes)
sudo systemctl reload nginx

# Restart nginx (if needed)
sudo systemctl restart nginx
```

---

## 🎯 Quick Reference

### URLs
- **Admin Panel:** `https://abps.albl.com`
- **API:** `https://abps.albl.com/api/`
- **Phone Provisioning:** `http://abps.albl.com/provision/{mac}.cfg`

### Ports
- **External (Internet):** 80 (HTTP), 443 (HTTPS), 5060 (SIP), 10000-20000 (RTP)
- **Internal (Localhost):** 8080 (PBX API)

### Service Management

```bash
# PBX
sudo systemctl status pbx
sudo systemctl restart pbx

# Nginx
sudo systemctl status nginx
sudo systemctl restart nginx

# Check what's listening
sudo netstat -tuln | grep -E ":(80|443|8080|5060)"
```

---

## ❓ Common Issues & Solutions

### Issue: "Connection Refused"
**Solution:**
```bash
# Check nginx is running
sudo systemctl start nginx

# Check PBX is running
sudo systemctl start pbx

# Verify DNS
nslookup abps.albl.com
```

### Issue: "SSL Certificate Invalid"
**Solution:**
```bash
# Re-run certbot
sudo certbot --nginx -d abps.albl.com

# Check certificate
sudo certbot certificates
```

### Issue: "502 Bad Gateway"
**Solution:**
```bash
# PBX isn't running or listening on wrong port
sudo systemctl status pbx
curl http://localhost:8080/admin/

# Check nginx config
sudo nginx -t
```

### Issue: "DNS Not Resolving"
**Solution:**
- Verify A record is correct in DNS server
- Wait for DNS propagation (can take up to 24 hours, usually < 5 minutes)
- Try `dig abps.albl.com` or `nslookup abps.albl.com`
- Check with your DNS provider

---

## 📱 Next Steps

Now that your PBX is accessible at `https://abps.albl.com`:

### Immediate Actions (Priority: HIGH)
1. **Log in** to the admin panel and verify all features work
2. **Test SSL certificate** - Ensure browser shows secure connection
3. **Configure extensions** for your team (see [QUICK_START.md](QUICK_START.md))
4. **Set up at least one SIP phone** to register and test calls

### Essential Setup (Priority: MEDIUM)
5. **Configure voicemail** settings for each extension
6. **Set up auto attendant** for incoming calls (see [ADMIN_PANEL_AUTO_ATTENDANT.md](ADMIN_PANEL_AUTO_ATTENDANT.md))
7. **Configure call routing** and queues if needed
8. **Set up emergency notification** contacts (see [E911_PROTECTION_GUIDE.md](E911_PROTECTION_GUIDE.md))

### Additional Features (Priority: LOW)
9. **Enable monitoring** and alerting (see [PRODUCTION_OPERATIONS_RUNBOOK.md](PRODUCTION_OPERATIONS_RUNBOOK.md))
10. **Configure backups** for system and call recordings
11. **Review security best practices** (see [SECURITY_GUIDE.md](SECURITY_GUIDE.md))
12. **Set up integrations** (CRM, AD, etc.) if needed

---

## 🔄 Manual Setup (Alternative to Script)

If you prefer manual setup or the script fails, see the complete manual guide:
- **Detailed Guide:** [REVERSE_PROXY_SETUP.md](REVERSE_PROXY_SETUP.md)
- **Architecture Diagram:** [docs/REVERSE_PROXY_ARCHITECTURE.md](docs/REVERSE_PROXY_ARCHITECTURE.md)

---

## ✅ Setup Complete!

**Your PBX is now accessible at:** `https://abps.albl.com`

**Enjoy your professional, secure PBX system! 🎉**

**Support:**
- Check logs if issues arise
- Refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common problems
- Review [SECURITY_GUIDE.md](SECURITY_GUIDE.md) for hardening

---

**Last Updated:** 2025-12-23  
**For:** PBX v1.0.0 with abps.albl.com domain  
**Priority:** HIGH - Production deployment recommended
