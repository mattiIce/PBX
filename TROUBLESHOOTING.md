# PBX System - Troubleshooting Guide

This guide covers all known issues, solutions, and troubleshooting procedures for the Warden VoIP PBX system.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Audio Issues](#audio-issues)
3. [Registration & Connectivity](#registration--connectivity)
4. [Admin Panel Issues](#admin-panel-issues)
5. [Integration Problems](#integration-problems)
6. [Phone Provisioning](#phone-provisioning)
7. [Database Issues](#database-issues)
8. [Service Management](#service-management)
9. [Network & Firewall](#network--firewall)
10. [Configuration Issues](#configuration-issues)
11. [Performance & Monitoring](#performance--monitoring)
12. [Historical Fixes Reference](#historical-fixes-reference)

---

## Quick Reference

| Issue | Quick Fix | Section |
|-------|-----------|---------|
| No audio in calls | `sudo ufw allow 10000:20000/udp` | [Audio Issues](#audio-issues) |
| Phones won't register | `sudo ufw allow 5060/udp` | [Registration](#registration--connectivity) |
| Admin panel login fails | `Ctrl+Shift+R` then check `systemctl status pbx` | [Admin Panel](#admin-panel-issues) |
| ERR_SSL_PROTOCOL_ERROR | Set `api.ssl.enabled: false` in config.yml | [Admin Panel](#err_ssl_protocol_error-with-reverse-proxy) |
| Email not sending | `python -c "import smtplib; s=smtplib.SMTP('localhost'); s.quit(); print('OK')"` | [Integration Problems](#integration-problems) |
| Database errors | `python scripts/verify_database.py` | [Database Issues](#database-issues) |
| Voice prompts missing | `python scripts/generate_tts_prompts.py` | [Audio Issues](#audio-issues) |
| Phone won't provision | Check DHCP Option 66 or manual server | [Phone Provisioning](#phone-provisioning) |
| High CPU usage | Check active calls, restart service | [Performance](#performance--monitoring) |

---

## Audio Issues

### No Audio in Phone Calls

**Symptoms:**
- Phones connect but no audio in either direction
- Silent calls or one-way audio
- Call establishes but no voice transmission

**Root Causes:**
1. **RTP Firewall Blocked** (Most Common)
2. **Codec Mismatch**
3. **RTP Relay Issues**
4. **NAT/Network Issues**

**Solutions:**

**1. Check RTP Firewall Rules:**
```bash
# Open RTP port range
sudo ufw allow 10000:20000/udp

# Verify firewall status
sudo ufw status numbered

# Should see:
# 10000:20000/udp ALLOW IN  Anywhere
```

**2. Verify Codec Compatibility:**
```bash
# Check config.yml
grep -A 10 "codecs:" config.yml

# Ensure phones support enabled codecs
# Common codecs: PCMU, PCMA, G722, Opus
```

**3. Check RTP Relay Logs:**
```bash
tail -f logs/pbx.log | grep RTP

# Should see:
# "RTP relay allocated on port XXXXX"
# "Relayed XXX bytes: A->B"
# "Relayed XXX bytes: B->A"
```

**4. Test Audio Path:**
```bash
# Make test call between extensions
# Check both directions

# View SIP/RTP debug
tail -f logs/pbx.log | grep -E "(SIP|RTP)"
```

**5. Network/NAT Issues:**
```bash
# If behind NAT, configure external IP in config.yml
external_ip: "YOUR_PUBLIC_IP"

# Verify RTP can traverse NAT
# May need STUN/TURN configuration
```

### Distorted or Garbled Audio

**Status:** FIXED (December 19, 2025)

**Symptoms:**
- Audio plays but sounds distorted, robotic, or garbled
- TTS prompts sound incorrect
- Voicemail playback is unintelligible
- High-pitched or low-pitched audio

**Root Cause:**
Audio sample rate mismatch - voicemail prompt files were generated at 16kHz but system expects 8kHz for PCMU codec.

**Solution Applied:**
All voicemail and auto attendant prompts have been regenerated at the correct 8kHz sample rate.

**If Issues Persist:**
```bash
# Regenerate audio prompts at correct sample rate
python scripts/generate_tts_prompts.py

# Verify generated files
file voicemail_prompts/*.wav
# Should show: "RIFF (little-endian) data, WAVE audio, Microsoft PCM, 8 bit, mono 8000 Hz"

# Check auto-attendant prompts
file auto_attendant/prompts/*.wav
```

**Additional Verification:**
```bash
# Test specific prompt
play voicemail_prompts/beep.wav

# If distorted, regenerate:
python scripts/generate_tts_prompts.py --sample-rate 8000

# Clear cache and restart
sudo systemctl restart pbx
```

### No Audio for Voicemail/Auto-Attendant Prompts

**Symptoms:**
- Voicemail IVR has no beeps or voice prompts
- Auto attendant is silent
- Caller hears silence when routed to voicemail

**Root Causes & Solutions:**

**1. Missing Voice Prompt Files:**
```bash
# Check if prompts exist
ls -lh voicemail_prompts/
ls -lh auto_attendant/prompts/

# Generate if missing
python scripts/generate_tts_prompts.py

# Verify files were created
ls -lh voicemail_prompts/*.wav
ls -lh auto_attendant/prompts/*.wav
```

**2. Incorrect File Permissions:**
```bash
# Fix permissions
sudo chown -R pbx:pbx voicemail_prompts/
sudo chown -R pbx:pbx auto_attendant/prompts/
sudo chmod 644 voicemail_prompts/*.wav
sudo chmod 644 auto_attendant/prompts/*.wav
```

**3. Codec Encoding Issues:**
```bash
# Verify file encoding matches expected codec
# For PCMU (G.711): 8kHz, 16-bit, mono
file voicemail_prompts/beep.wav

# If wrong format, regenerate with correct parameters
```

**4. Check Logs for Errors:**
```bash
# Look for file not found or playback errors
tail -f logs/pbx.log | grep -i "prompt\|wav\|audio"
```

### One-Way Audio (Can Hear But Not Be Heard)

**Symptoms:**
- One party can hear, other cannot
- Asymmetric audio flow

**Solutions:**

**1. NAT/Firewall Configuration:**
```bash
# Ensure symmetric RTP ports
# Check NAT traversal settings

# Verify both directions in firewall
sudo ufw status | grep 10000:20000
```

**2. Check Codec Negotiation:**
```bash
# View SIP session details
tail -f logs/pbx.log | grep -A 20 "200 OK"

# Verify both endpoints agreed on same codec
```

**3. Phone Configuration:**
- Check phone's network settings
- Verify NAT keepalive is enabled
- Check phone's RTP port range matches PBX

---

## Registration & Connectivity

### Extensions Won't Register

**Symptoms:**
- Phone shows "Not Registered" or "Registration Failed"
- Extensions timeout during registration
- Cannot make or receive calls

**Solutions:**

**1. Check SIP Port:**
```bash
# Ensure SIP port is open
sudo ufw allow 5060/udp
sudo ufw status | grep 5060

# Verify PBX is listening
sudo netstat -ulnp | grep 5060
```

**2. Verify Credentials:**
```bash
# Check config.yml
grep -A 5 "extensions:" config.yml

# Verify extension number and password match phone settings
```

**3. Check Phone SIP Server Settings:**
- Server address should be: PBX IP or hostname
- Port: 5060
- Transport: UDP (or TCP if configured)
- Extension: matches config.yml
- Password: matches config.yml

**4. View Registration Logs:**
```bash
# Monitor SIP registration attempts
tail -f logs/pbx.log | grep REGISTER

# Should see successful 200 OK responses
```

**5. Test Connectivity:**
```bash
# From phone network, test SIP port
nc -u -v PBX_IP 5060

# Check if PBX is reachable
ping PBX_IP
```

**6. Check for Registration Conflicts:**
```bash
# Verify no duplicate extensions
grep "number:" config.yml | sort | uniq -d

# Clear any stale registrations
curl -k https://localhost:9000/api/extensions
```

### Intermittent Registration Drops

**Symptoms:**
- Phones register then unregister randomly
- Periodic registration failures

**Solutions:**

**1. Check Registration Timeout:**
```yaml
# config.yml
sip:
  registration_timeout: 3600  # Increase if too low
```

**2. Enable NAT Keepalive:**
- Configure phones to send keepalive packets
- Typical interval: 30-60 seconds

**3. Check Network Stability:**
```bash
# Monitor for network drops
ping -c 100 PHONE_IP

# Check for packet loss
```

**4. Review Firewall Timeout Settings:**
```bash
# Ensure firewall doesn't drop long-lived UDP connections
# May need to adjust connection tracking timeout
```

---

## Admin Panel Issues

### Login Connection Errors

**Symptoms:**
- "Connection error. Please try again." message
- Cannot access admin panel
- Login page loads but authentication fails

**Diagnostic Steps:**

**1. Check PBX Service Status:**
```bash
sudo systemctl status pbx

# If not running:
sudo systemctl start pbx

# Check for errors:
sudo journalctl -u pbx -n 50
```

**2. Verify API Accessibility:**
```bash
# Test API endpoint
curl -k https://localhost:9000/api/status

# Should return JSON with status information
```

**3. Check Browser Console:**
- Press F12 to open developer tools
- Look at Console tab for JavaScript errors
- Check Network tab for failed requests
- Note: Red CORS errors or 502/504 errors indicate connectivity issues

**4. Verify Firewall:**
```bash
sudo ufw status | grep 9000

# If not allowed:
sudo ufw allow 9000/tcp
```

**5. Check Port Binding:**
```bash
# Verify PBX is listening on correct port
sudo netstat -tlnp | grep 9000

# Should show python/pbx process
```

**6. Test from Different Network:**
- Try accessing from localhost
- Try from same network
- Try from external network (if applicable)

**7. Check Reverse Proxy (if used):**
```bash
# If using nginx
sudo systemctl status nginx
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### ERR_SSL_PROTOCOL_ERROR with Reverse Proxy

**Status:** DOCUMENTED (December 30, 2025)

**Symptoms:**
- Browser shows "This site can't provide a secure connection"
- ERR_SSL_PROTOCOL_ERROR message
- "sent an invalid response" error
- "Proxy Error: Error reading from remote server"
- Occurs after enabling SSL on admin UI with Apache/Nginx

**Root Cause:**
Backend API configured with SSL enabled (`api.ssl.enabled: true`) when it should be HTTP-only behind a reverse proxy. Apache/Nginx expects to proxy HTTPS → HTTP, but finds HTTPS → HTTPS causing SSL protocol mismatch.

**Architecture Overview:**

**Correct Setup:**
```
Browser ──HTTPS──> Apache (port 443) ──HTTP──> PBX Backend (port 9000)
         SSL/TLS    ↑ SSL Termination      ↑ Plain HTTP (internal)
```

**Incorrect Setup (Causes Error):**
```
Browser ──HTTPS──> Apache (port 443) ──HTTPS──> PBX Backend (port 9000)
         SSL/TLS                         SSL/TLS (conflict!)
```

**Quick Fix:**
```bash
# 1. Edit configuration
nano config.yml

# 2. Find api.ssl section and set:
api:
  ssl:
    enabled: false  # ← Must be false for reverse proxy

# 3. Restart service
sudo systemctl restart pbx

# 4. Verify backend is HTTP
curl http://localhost:9000/api/health  # Should work
curl https://localhost:9000/api/health  # Should fail
```

**Detailed Verification Steps:**

**1. Check Current Configuration:**
```bash
cd /path/to/PBX
grep -A 5 "api:" config.yml | grep -A 2 "ssl:"
```

Expected output for reverse proxy:
```yaml
ssl:
  enabled: false  # ← Should be FALSE
```

**2. Verify Backend HTTP Only:**
```bash
# Should return JSON health status
curl http://localhost:9000/api/health

# Should fail (connection refused or certificate error)
curl https://localhost:9000/api/health
```

**3. Test Apache/Nginx Proxy:**
```bash
# Should return JSON status through proxy
curl https://yourdomain.com/api/health
```

**4. Check Listening Ports:**
```bash
# PBX should listen on 9000 (HTTP, not SSL)
sudo netstat -tlnp | grep 9000

# Apache should listen on 443 (SSL)
sudo netstat -tlnp | grep 443
```

**Common Mistakes:**
- Enabling `api.ssl.enabled: true` when using reverse proxy
- Apache/Nginx proxy pointing to `https://localhost:9000` instead of `http://localhost:9000`
- Firewall blocking internal HTTP communication
- Wrong port in Apache/Nginx config

**When to Use Direct SSL:**
Only enable `api.ssl.enabled: true` when:
- NOT using Apache/Nginx reverse proxy
- Accessing PBX directly (e.g., `https://192.168.1.14:9000/admin/`)
- Development/testing environment
- Self-signed certificates are acceptable

**Note:** For production, always use reverse proxy with SSL termination.

### Admin Panel Display Issues (Broken UI)

**Status:** FIXED (December 23, 2025)

**Symptoms:**
- Admin panel displays incorrectly after updates
- Buttons not clickable
- Styles missing or broken
- Only login component works

**Root Cause:**
Browser caching old CSS/JavaScript files after server code updates.

**Immediate Fix:**
```
Press Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac) for hard refresh
```

**Permanent Prevention:**
- Cache-control meta tags added to HTML files
- Version query parameters added to CSS/JS includes
- Automatic detection with warning banner

**Diagnostic Page:**
```
Visit: https://localhost:9000/admin/status-check.html
```

This page will:
- Test API connectivity
- Verify JavaScript loading
- Check for cache issues
- Display system status

**Manual Cache Clear:**
```
1. Chrome: Settings → Privacy → Clear browsing data → Cached images and files
2. Firefox: Options → Privacy → Clear Data → Cached Web Content
3. Edge: Settings → Privacy → Choose what to clear → Cached data
```

### Cannot Access Admin Panel After Installation

**Symptoms:**
- Fresh installation, admin panel not accessible
- 404 or connection refused errors

**Solutions:**

**1. Verify Installation Completed:**
```bash
# Check if all files are present
ls -la admin/

# Should contain: index.html, login.html, css/, js/
```

**2. Check Service Started:**
```bash
sudo systemctl status pbx
sudo systemctl enable pbx  # Enable auto-start
sudo systemctl start pbx
```

**3. Wait for Initialization:**
```bash
# PBX may take 30-60 seconds to fully start
# Watch logs:
sudo journalctl -u pbx -f
```

**4. Verify SSL Certificate:**
```bash
# Check certificate exists
ls -la certs/

# Regenerate if needed
python scripts/generate_ssl_cert.py --hostname YOUR_IP
```

### Apache "Not Found" Error for Admin Pages

**Symptoms:**
- Accessing admin pages returns: "Not Found - The requested URL was not found on this server."
- Error message shows "Apache/2.4.58 (Ubuntu)" or similar
- Direct access to PBX port works (e.g., http://localhost:9000/admin/)

**Root Cause:**
Apache is serving requests directly without proxying to the PBX application. The admin files need to be accessed through a reverse proxy configuration.

**Quick Fix:**

**Option 1: Automated Setup (Recommended)**
```bash
cd /path/to/PBX
sudo scripts/setup_apache_reverse_proxy.sh
```

**Option 2: Manual Configuration**
```bash
# Enable required modules
sudo a2enmod proxy proxy_http proxy_wstunnel headers rewrite ssl

# Create virtual host configuration
sudo nano /etc/apache2/sites-available/pbx.conf
```

Add minimal configuration:
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    
    ProxyPreserveHost On
    ProxyRequests Off
    
    <Location />
        ProxyPass http://localhost:9000/
        ProxyPassReverse http://localhost:9000/
    </Location>
    
    ErrorLog ${APACHE_LOG_DIR}/pbx-error.log
    CustomLog ${APACHE_LOG_DIR}/pbx-access.log combined
</VirtualHost>
```

Enable site and restart:
```bash
sudo a2ensite pbx.conf
sudo apache2ctl configtest
sudo systemctl restart apache2
```

**Detailed Documentation:**
- Complete setup: `docs/APACHE_REVERSE_PROXY_SETUP.md`
- Configuration example: `apache-pbx.conf.example`

**Verification:**
```bash
# Test that pages now load
curl http://your-domain.com/admin/status-check.html

# Should return HTML content, not 404 error
```

---

## Integration Problems

### Email Notifications Not Sending

**Symptoms:**
- Voicemail notifications not received
- No emails from system
- SMTP errors in logs

**Solutions:**

**1. Test SMTP Configuration:**
```bash
# Run email test script
python -c "import smtplib; s=smtplib.SMTP('localhost'); s.quit(); print('OK')"

# Should show SMTP connection and send test
```

**2. Verify SMTP Credentials:**
```bash
# Check .env file
cat .env | grep SMTP

# Required:
# SMTP_HOST
# SMTP_PORT
# SMTP_USERNAME
# SMTP_PASSWORD
```

**3. Check Email Configuration:**
```yaml
# config.yml
voicemail:
  email_notifications: true
  smtp:
    host: "smtp.gmail.com"
    port: 587
    use_tls: true
    username: "${SMTP_USERNAME}"
    password: "${SMTP_PASSWORD}"
```

**4. Gmail-Specific Issues:**
```bash
# For Gmail, use App Password (not regular password)
# Enable 2FA on Google account
# Generate app password: https://myaccount.google.com/apppasswords
# Use app password in .env
```

**5. Office 365 Issues:**
```yaml
smtp:
  host: "smtp.office365.com"
  port: 587
  use_tls: true
```

**6. Check Logs:**
```bash
tail -f logs/pbx.log | grep -i email

# Look for SMTP connection errors
```

**7. Test Email Server Connectivity:**
```bash
# Test SMTP server reachable
telnet smtp.gmail.com 587

# Should connect successfully
```

**8. Verify Email in Extension Config:**
```yaml
extensions:
  - number: "1001"
    email: "user@company.com"  # Must be set
```

### Active Directory Integration Not Working

**Symptoms:**
- AD sync fails
- Cannot search AD users
- Authentication errors

**Solutions:**

**1. Test AD Connectivity:**
```bash
# Test LDAP connection
ldapsearch -x -H ldap://ad.company.com -D "CN=pbx-service,DC=company,DC=com" -W -b "DC=company,DC=com"
```

**2. Verify AD Configuration:**
```yaml
integrations:
  active_directory:
    enabled: true
    server: "ldap://ad.company.com"
    port: 389
    bind_dn: "CN=pbx-service,DC=company,DC=com"
    bind_password: "${AD_PASSWORD}"
    base_dn: "DC=company,DC=com"
```

**3. Check AD Credentials:**
```bash
# Verify .env has AD password
cat .env | grep AD_PASSWORD

# Test credentials directly
```

**4. Enable LDAPS (if using SSL):**
```yaml
active_directory:
  server: "ldaps://ad.company.com"
  port: 636
  use_ssl: true
```

**5. Check Firewall:**
```bash
# LDAP port
sudo ufw allow 389/tcp

# LDAPS port (if SSL)
sudo ufw allow 636/tcp
```

**6. View Integration Logs:**
```bash
tail -f logs/pbx.log | grep -i "AD\|LDAP"
```

### Webhook Delivery Failures

**Symptoms:**
- Webhooks not triggering
- Events not sent to external systems
- Webhook errors in logs

**Solutions:**

**1. Verify Webhook Configuration:**
```yaml
webhooks:
  enabled: true
  subscriptions:
    - url: "https://crm.company.com/api/pbx/events"
      events: ["call.answered", "call.ended"]
      secret: "${WEBHOOK_SECRET}"
```

**2. Test Webhook Endpoint:**
```bash
# Test destination is reachable
curl -v https://crm.company.com/api/pbx/events
```

**3. Check Webhook Logs:**
```bash
tail -f logs/pbx.log | grep -i webhook

# Look for delivery attempts and errors
```

**4. Verify HMAC Signature:**
- Ensure receiving system validates signature correctly
- Check secret matches in both systems

**5. Check Retry Configuration:**
```yaml
webhooks:
  retry:
    max_attempts: 3
    backoff_factor: 2
```

---

## Phone Provisioning

### Phones Won't Auto-Provision

**Symptoms:**
- Phone doesn't download configuration
- Manual configuration works but auto-provision fails
- Phone shows "Provisioning failed" or similar

**Solutions:**

**1. Verify Provisioning Server Running:**
```bash
# Check provisioning port
sudo netstat -tlnp | grep 8888

# Should show python/pbx listening on 8888
```

**2. Check DHCP Option 66:**
```bash
# Option 66 should point to: http://PBX_IP:8888

# Test from phone network:
curl http://PBX_IP:8888/
```

**3. Manual Phone Configuration:**
If DHCP Option 66 not available:
- Access phone web interface
- Set provision server: `http://PBX_IP:8888`
- Trigger reprovisioning

**4. Verify Template Exists:**
```bash
# Check templates directory
ls -la provisioning_templates/

# Should have templates for your phone brand
```

**5. Check Phone MAC Address:**
```bash
# Template filename often uses MAC address
# e.g., 00-15-65-12-34-56.cfg

# Verify MAC matches phone's actual MAC
```

**6. Check File Permissions:**
```bash
sudo chown -R pbx:pbx provisioning_templates/
sudo chmod 644 provisioning_templates/*.cfg
```

**7. View Provisioning Logs:**
```bash
tail -f logs/pbx.log | grep -i provision

# Should show HTTP requests from phones
```

**8. Test Template Generation:**
```bash
# View generated config for extension
curl http://localhost:8888/provision/1001

# Should return phone configuration
```

### Wrong Configuration Downloaded

**Symptoms:**
- Phone provisions but with wrong settings
- Extension number incorrect
- Server settings wrong

**Solutions:**

**1. Check Template Variables:**
```bash
# View template
cat provisioning_templates/yealink/t46s.cfg

# Verify variables are correct:
# {EXTENSION}, {PASSWORD}, {SIP_SERVER}, etc.
```

**2. Verify Extension Exists:**
```bash
# Check extension in config
grep -A 5 "number: \"1001\"" config.yml
```

**3. Clear Phone's Config:**
- Factory reset phone
- Reprovision from scratch

**4. Manual Template Test:**
```bash
# Test template rendering
curl http://localhost:8888/provision/1001?debug=true

# Should show populated template
```

### Phone-Specific Provisioning Issues

**Yealink:**
```bash
# Ensure MAC address format: 001565-AABBCC.cfg
# Server URL: http://PBX_IP:8888/$mac.cfg
```

**Polycom:**
```bash
# Boot file: 000000000000.cfg (MAC address)
# Needs both application and configuration files
```

**Cisco:**
```bash
# XML-based configuration
# Separate file per line: SEPXXXXXXXXXXXXX.cnf.xml
```

**Grandstream:**
```bash
# cfg + cfgMAC format
# HTTP provisioning on port 8888
```

### Provisioning Connection Error After Port Change

**Symptoms:**
- Phones show "Connection error" for provisioning
- Provisioning URL points to wrong port (e.g., 8080 instead of 9000)
- Direct access to PBX on the correct port works fine

**Root Cause:**
When `api.port` in `config.yml` is changed from the default (8080), previously registered devices may have cached provisioning URLs with the old port. The phone requests `http://server:8080/provision/...` but the server now listens on port 9000.

**Solution:**
1. **Restart the PBX service** - URLs are automatically regenerated from current config on startup:
   ```bash
   sudo systemctl restart pbx
   ```

2. **Verify the fix:**
   ```bash
   # Check the API port in logs
   sudo journalctl -u pbx -n 50 | grep "API port"

   # Verify provisioning works
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:9000/api/provisioning/devices | jq
   ```

3. **If phones still fail**, they may have cached the old URL:
   - Power cycle the phone to trigger re-provisioning
   - Or factory reset and re-provision

**Prevention:**
Use template variables in `config.yml` provisioning URL format:
```yaml
provisioning:
  enabled: true
  url_format: http://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg
```

---

## Database Issues

### Database Connection Errors

**Symptoms:**
- "Cannot connect to database" errors
- Voicemail fails to save
- CDR not logging

**Solutions:**

**1. Verify Database Running:**
```bash
# PostgreSQL
sudo systemctl status postgresql
sudo systemctl start postgresql

# Check connection
psql -U pbx_user -d pbx_system -h localhost
```

**2. Test Database Connection:**
```bash
python scripts/verify_database.py

# Should show successful connection
```

**3. Check Database Credentials:**
```bash
# Verify .env
cat .env | grep DB_

# Required:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=pbx_system
# DB_USER=pbx_user
# DB_PASSWORD=your_password
```

**4. Verify Database Exists:**
```bash
sudo -u postgres psql -l | grep pbx_system

# If not exists, create:
sudo -u postgres createdb pbx_system
```

**5. Check User Permissions:**
```bash
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;"
```

**6. Initialize Database:**
```bash
# Run initialization script
python scripts/init_database.py

# Should create tables
```

**7. Check Logs:**
```bash
tail -f logs/pbx.log | grep -i database

# Look for connection errors
```

### Database Migration Errors

**Symptoms:**
- Errors after upgrading PBX version
- Schema mismatch errors
- Missing table errors

**Solutions:**

**1. Backup Database:**
```bash
sudo -u postgres pg_dump pbx_system > /backup/pbx_backup.sql
```

**2. Run Migration:**
```bash
alembic upgrade head

# Follow prompts
```

**3. Check Schema Version:**
```bash
sudo -u postgres psql pbx_system -c "SELECT * FROM schema_version;"
```

**4. Manual Table Creation:**
```bash
# If specific table missing
sudo -u postgres psql pbx_system < schema/create_table.sql
```

### Voicemail Database Issues

**Symptoms:**
- Voicemails not saved
- Cannot retrieve messages
- Database errors in voicemail logs

**Solutions:**

**1. Initialize Voicemail Tables:**
```bash
python scripts/init_database.py

# Creates voicemail_messages table
```

**2. Verify Tables Exist:**
```bash
sudo -u postgres psql pbx_system -c "\dt"

# Should show voicemail_messages table
```

**3. Check File Storage:**
```bash
# Verify voicemail directory exists
ls -la voicemail/

# Create if missing
mkdir -p voicemail/1001
sudo chown -R pbx:pbx voicemail/
```

**4. Test Voicemail Save:**
```bash
# Make test call to voicemail
# Check if file created in voicemail/EXTENSION/
```

---

## Service Management

### PBX Service Won't Start

**Symptoms:**
- `systemctl start pbx` fails
- Service shows "failed" or "inactive"
- Immediate exit after start

**Solutions:**

**1. Check Service Status:**
```bash
sudo systemctl status pbx

# Look for exit code and error message
```

**2. View Detailed Logs:**
```bash
sudo journalctl -u pbx -n 100 --no-pager

# Look for Python errors or traceback
```

**3. Check Configuration File:**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yml'))"

# Should complete without errors
```

**4. Verify Python Dependencies:**
```bash
pip list | grep -i twisted
uv pip list | grep -i yaml

# Reinstall if missing
make install-prod
```

**5. Check File Permissions:**
```bash
sudo chown -R pbx:pbx /opt/pbx/
sudo chmod 755 /opt/pbx/main.py
```

**6. Test Manual Start:**
```bash
# Run manually to see errors
cd /opt/pbx
python main.py

# Should show startup messages or errors
```

**7. Check Port Conflicts:**
```bash
# Verify ports not in use
sudo netstat -tlnp | grep -E "(5060|9000)"

# If in use, kill conflicting process or change PBX ports
```

### Service Crashes or Restarts Frequently

**Symptoms:**
- Service keeps restarting
- Unexpected exits
- Crashes under load

**Solutions:**

**1. Check Crash Logs:**
```bash
sudo journalctl -u pbx -f

# Watch for crash patterns
```

**2. Review Application Logs:**
```bash
tail -f logs/pbx.log

# Look for exceptions or errors before crash
```

**3. Check Memory Usage:**
```bash
free -h
top -p $(pgrep -f "python.*main.py")

# Verify sufficient memory available
```

**4. Check Disk Space:**
```bash
df -h

# Ensure /var/log and application directories have space
```

**5. Review Core Dumps:**
```bash
# Check for core dumps
ls -la /var/crash/
ls -la core.*

# Analyze if present
```

**6. Enable Debug Logging:**
```yaml
# config.yml
logging:
  level: "DEBUG"
```

**7. Check SystemD Service Settings:**
```bash
# View service file
cat /etc/systemd/system/pbx.service

# Check Restart= settings
# May need to adjust restart policy
```

---

## Network & Firewall

### Firewall Blocking Traffic

**Symptoms:**
- Connections timeout
- Intermittent connectivity
- Some features work, others don't

**Solutions:**

**1. Check Firewall Status:**
```bash
sudo ufw status verbose

# Should show:
# 5060/udp ALLOW IN
# 9000/tcp ALLOW IN
# 10000:20000/udp ALLOW IN
```

**2. Open Required Ports:**
```bash
# SIP signaling
sudo ufw allow 5060/udp

# Admin/API
sudo ufw allow 9000/tcp
sudo ufw allow 443/tcp

# RTP media
sudo ufw allow 10000:20000/udp

# Reload firewall
sudo ufw reload
```

**3. Check IPTables (if using):**
```bash
sudo iptables -L -n -v | grep -E "(5060|9000|10000)"
```

**4. Test Connectivity:**
```bash
# From external host
nc -u -v PBX_IP 5060  # SIP
nc -v PBX_IP 9000     # HTTPS

# Should connect
```

**5. Disable Firewall Temporarily (Testing Only):**
```bash
sudo ufw disable

# Test if issue resolves
# Re-enable: sudo ufw enable
```

### NAT/Routing Issues

**Symptoms:**
- Works internally but not externally
- One-way audio across networks
- Registration from remote phones fails

**Solutions:**

**1. Configure External IP:**
```yaml
# config.yml
server:
  external_ip: "YOUR_PUBLIC_IP"
```

**2. Enable STUN:**
```yaml
stun:
  enabled: true
  server: "stun.l.google.com:19302"
```

**3. Port Forwarding:**
```bash
# On router, forward these ports to PBX:
# UDP 5060 (SIP)
# UDP 10000-20000 (RTP)
# TCP 9000 or 443 (HTTPS)
```

**4. Check NAT Type:**
```bash
# Test NAT behavior
# Symmetric NAT can cause issues
```

**5. Configure SIP NAT Keepalive:**
```yaml
sip:
  nat_keepalive: true
  keepalive_interval: 30
```

---

## Configuration Issues

### Invalid Configuration File

**Symptoms:**
- PBX won't start
- "YAML parse error" messages
- Configuration not loading

**Solutions:**

**1. Validate YAML Syntax:**
```bash
python -c "import yaml; yaml.safe_load(open('config.yml'))"

# Will show line number of syntax error
```

**2. Common YAML Mistakes:**
- Tabs instead of spaces (use spaces only)
- Incorrect indentation
- Missing colons
- Unquoted special characters

**3. Check for Merge Conflicts:**
```bash
grep -n "<<<<<<" config.yml
grep -n ">>>>>>" config.yml

# If found, resolve conflicts manually
```

**4. Use Example as Template:**
```bash
# Compare with working example
diff config.yml config.example.yml
```

**5. Test Minimal Config:**
```bash
# Start with minimal config.yml
# Add sections incrementally to find problem
```

### Environment Variables Not Loading

**Symptoms:**
- "${VAR}" appears in logs instead of value
- Authentication fails
- Missing credentials

**Solutions:**

**1. Verify .env File:**
```bash
cat .env

# Should not have quotes around values:
# DB_PASSWORD=mypassword  ✓
# DB_PASSWORD="mypassword"  ✗ (quotes will be included)
```

**2. Check File Location:**
```bash
# .env must be in same directory as main.py
ls -la .env

# Or set ENV_FILE path
export ENV_FILE=/opt/pbx/.env
```

**3. Test Variable Loading:**
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('DB_PASSWORD'))"

# Should print password value
```

**4. Check Permissions:**
```bash
sudo chmod 600 .env
sudo chown pbx:pbx .env
```

---

## Performance & Monitoring

### High CPU Usage

**Symptoms:**
- CPU constantly high
- System sluggish
- Calls affected

**Solutions:**

**1. Check Active Calls:**
```bash
curl -k https://localhost:9000/api/calls | jq '.'

# High call volume may be normal
```

**2. Review Process Stats:**
```bash
top -p $(pgrep -f "python.*main.py")

# Check CPU percentage
```

**3. Check for Loops:**
```bash
# Look for error loops in logs
tail -f logs/pbx.log | grep -i error

# May indicate infinite retry loop
```

**4. Check Database Performance:**
```bash
# Slow queries can cause CPU spikes
sudo -u postgres psql pbx_system -c "SELECT * FROM pg_stat_activity;"
```

**5. Optimize Configuration:**
```yaml
# Reduce logging level
logging:
  level: "WARNING"

# Disable unnecessary features
```

### Memory Leaks

**Symptoms:**
- Memory usage grows over time
- Eventually crashes or OOM
- Performance degrades

**Solutions:**

**1. Monitor Memory:**
```bash
# Watch memory usage
watch -n 5 'ps aux | grep python | grep main.py'
```

**2. Check Call Cleanup:**
```bash
# Verify calls are properly ended
curl -k https://localhost:9000/api/calls

# Stale calls indicate cleanup issue
```

**3. Restart Service Periodically:**
```bash
# Temporary workaround
# Add cron job for nightly restart
0 3 * * * systemctl restart pbx
```

**4. Enable Memory Profiling:**
```python
# Add to main.py temporarily
import tracemalloc
tracemalloc.start()
```

### Slow Performance

**Symptoms:**
- Delayed call setup
- Slow API responses
- UI lag

**Solutions:**

**1. Check System Resources:**
```bash
# CPU
top

# Memory
free -h

# Disk I/O
iostat
```

**2. Check Database Performance:**
```bash
# Add indexes if needed
sudo -u postgres psql pbx_system

# Analyze slow queries
EXPLAIN ANALYZE SELECT * FROM voicemail_messages;
```

**3. Optimize Logging:**
```yaml
logging:
  level: "WARNING"  # Reduce from DEBUG
```

**4. Check Network Latency:**
```bash
ping -c 100 REMOTE_ENDPOINT

# High latency affects performance
```

---

## Historical Fixes Reference

This section documents significant bugs that have been fixed. Included for reference if similar issues appear.

### Admin Panel Display Issues (Browser Cache)

**Date Fixed:** December 23, 2025  
**Status:** RESOLVED

**Problem:**
After server updates, admin panel displayed incorrectly with non-functional buttons.

**Solution:**
- Added cache-control meta tags
- Added version query parameters to CSS/JS
- Created diagnostic page: /admin/status-check.html
- Hard refresh: Ctrl+Shift+R

**Files Modified:**
- admin/index.html
- admin/login.html
- admin/status-check.html

### API Connection Timeout (Reverse Proxy)

**Date Fixed:** December 23, 2025  
**Status:** RESOLVED

**Problem:**
Admin panel API requests timing out through nginx reverse proxy.

**Solution:**
Added proxy timeouts to nginx configuration:
```nginx
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
```

### Audio Sample Rate Mismatch

**Date Fixed:** December 19, 2025  
**Status:** RESOLVED

**Problem:**
Voicemail prompts sounded distorted and garbled.

**Root Cause:**
Prompts generated at 16kHz but PCMU codec expects 8kHz.

**Solution:**
Regenerated all prompts at 8kHz sample rate.

**Verification:**
```bash
file voicemail_prompts/*.wav
# Should show: 8000 Hz
```

### RTP One-Way Audio

**Date Fixed:** December 2025  
**Status:** RESOLVED

**Problem:**
RTP relay had race condition causing one-way or no audio.

**Root Cause:**
Relay required both endpoints before forwarding packets.

**Solution:**
Modified RTP relay to:
- Set caller endpoint immediately
- Remove blocking condition
- Forward packets as soon as first endpoint known

### G.722 Codec Quantization

**Date Fixed:** December 2025  
**Status:** RESOLVED

**Problem:**
G.722 audio severely distorted.

**Root Cause:**
MAX_QUANTIZATION_RANGE set to 256 instead of 32768.

**Solution:**
```python
# pbx/features/g722_codec.py
MAX_QUANTIZATION_RANGE = 32768  # Corrected
```

---

## Related Documentation

### Documentation
- [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) - Comprehensive PBX guide
- [README.md](README.md) - Project overview
- [COMPLETE_GUIDE.md - Section 9.2: REST API](COMPLETE_GUIDE.md#92-rest-api-reference) - REST API reference

### Support
- GitHub Issues: https://github.com/mattiIce/PBX/issues
- Community Forum: (if available)

### External Resources
- SIP Protocol: RFC 3261
- RTP Protocol: RFC 3550
- VoIP Troubleshooting: https://www.voip-info.org/

---

## Quick Diagnostic Commands

```bash
# Full system check
sudo systemctl status pbx
curl -k https://localhost:9000/api/status
sudo ufw status
sudo netstat -tlnp | grep -E "(5060|9000)"
python scripts/verify_database.py

# Check logs for errors
tail -f logs/pbx.log | grep -i error

# Test basic functionality
curl -k https://localhost:9000/api/extensions
curl -k https://localhost:9000/api/calls

# Monitor real-time activity
tail -f logs/pbx.log
```
