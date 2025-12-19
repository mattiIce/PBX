# PBX System Troubleshooting Guide

This comprehensive guide covers common issues and their solutions for the PBX system.

## Quick Navigation

- [Audio Issues](#audio-issues)
- [Integration Problems](#integration-problems)
- [Phone Registration](#phone-registration)
- [Network and Connectivity](#network-and-connectivity)
- [Configuration Issues](#configuration-issues)
- [Service Management](#service-management)

---

## Audio Issues

### No Audio in Phone Calls

**Symptoms:**
- Phones connect but no audio in either direction
- Silent calls or one-way audio

**Root Cause:**
Race condition in RTP relay setup where packets arriving before both endpoints are known get dropped.

**Solution:**
This has been fixed in the current version. The RTP relay now:
1. Sets caller endpoint immediately when INVITE is received
2. Removes blocking condition that required both endpoints
3. Accepts and forwards packets as soon as first endpoint is known

**Verification:**
```bash
# Check logs for RTP relay activity
tail -f ~/PBX/logs/pbx.log | grep RTP

# Should see:
# - "RTP relay allocated on port XXXXX"
# - "Relayed XXX bytes: A->B"
# - "Relayed XXX bytes: B->A"
```

### Distorted or Garbled Audio

**Status:** ✅ **FIXED** (December 19, 2025)

**Symptoms:**
- Audio plays but sounds distorted or garbled
- TTS prompts sound incorrect
- Voicemail playback is unintelligible

**Root Cause:**
Audio sample rate mismatch - voicemail prompt files were at 16kHz but system expects 8kHz for PCMU codec.

**Solution Applied:**
All voicemail and auto attendant prompts have been regenerated at the correct 8kHz sample rate.

**If you need to regenerate prompts again:**
```bash
# Regenerate audio prompts at correct sample rate
cd /home/runner/work/PBX/PBX
python3 scripts/generate_tts_prompts.py --sample-rate 8000

# Verify generated files
file voicemail_prompts/*.wav
# Should show: 8000 Hz, 16 bit, mono
```

**Additional Steps (if needed):**
1. Clear any cached audio files
2. Restart PBX service: `sudo systemctl restart pbx`
3. Test voicemail prompts

### No Audio for Voicemail Prompts

**Symptoms:**
- Voicemail IVR has no beeps or prompts
- Auto attendant is silent

**Root Causes and Solutions:**

**1. Incorrect Audio Encoding**
```python
# Fixed in pbx/features/voicemail.py
# Beeps now use PCMU encoding (G.711 μ-law)
# Sample rate: 8000 Hz
```

**2. G.722 Codec Issues**
If using G.722 codec, ensure proper quantization:
```python
# Fixed in pbx/features/g722_codec.py
# MAX_QUANTIZATION_RANGE = 32768 (correct)
# Was 256 (too small, causing distortion)
```

**Verification:**
```bash
# Test voicemail system
# Dial *1001 and listen for prompts
# Should hear clear beep tones
```

### Audio Quality Issues

**Symptoms:**
- Choppy or broken audio
- Intermittent silence during calls
- Echo or feedback

**Diagnostics:**
```bash
# Check RTP packet loss
tail -f ~/PBX/logs/pbx.log | grep "packet loss"

# Check network quality
ping -c 100 [phone_ip_address]

# Monitor RTP ports
sudo netstat -ulnp | grep -E "10000|11000|12000"
```

**Solutions:**

**1. Network Issues**
- Ensure RTP ports (10000-20000) are open in firewall
- Check for network congestion
- Verify QoS settings for VoIP traffic

**2. Bidirectional RTP Packet Loss**
```bash
# Check if both directions are relaying
grep "Relayed.*bytes" ~/PBX/logs/pbx.log | tail -20

# Should see both A->B and B->A
```

**3. Codec Negotiation**
- Verify both phones support same codec
- Check codec configuration in config.yml
- Ensure PCMU/PCMA is enabled (most compatible)

---

## Integration Problems

### Jitsi Integration Not Working

**Symptoms:**
- Jitsi video conference button doesn't work
- Can't create Jitsi meetings from PBX

**Quick Fix:**
```bash
# 1. Enable Jitsi in config
nano /home/runner/work/PBX/PBX/config.yml

# Find and change:
integrations:
  jitsi:
    enabled: true  # Change from false to true
    server: "https://your-jitsi-server"  # Or "https://meet.jit.si" for public

# 2. Restart PBX
sudo systemctl restart pbx
```

**Port Conflict Resolution:**
If running self-hosted Jitsi:
```bash
# Jitsi should use port 443 (HTTPS)
# EspoCRM can use port 8888 or different port
# Matrix should use port 8008

# Verify no conflicts:
sudo netstat -tlnp | grep -E "443|8080|8008|8888"
```

### Matrix Integration Issues

**Symptoms:**
- Can't send messages to Matrix
- Bot not responding
- Connection errors

**Solutions:**

**1. Set Bot Password**
```bash
# Edit .env file
nano /home/runner/work/PBX/PBX/.env

# Add:
MATRIX_BOT_PASSWORD=your-bot-password
```

**2. Verify Bot Username Format**
- Should be: `@botname:server.com`
- For local: `@pbxbot:localhost`
- Check in Admin Panel → Integrations → Matrix

**3. Test Connection**
```bash
# Check Matrix server is running
curl https://localhost:8008/_matrix/client/versions

# Test bot login manually
curl -X POST https://localhost:8008/_matrix/client/r0/login \
  -H "Content-Type: application/json" \
  -d '{"type":"m.login.password","user":"pbxbot","password":"your-password"}'
```

### EspoCRM Integration Problems

**Symptoms:**
- Screen pop doesn't work
- Can't log calls in CRM
- API connection errors

**Solutions:**

**1. Verify API Configuration**
```bash
# Check .env file
nano /home/runner/work/PBX/PBX/.env

# Should have:
ESPOCRM_API_KEY=your-api-key-here
```

**2. Test API Connection**
```bash
# Test API endpoint
curl -X GET "https://localhost/api/v1/Account" \
  -H "X-Api-Key: your-api-key"

# Should return JSON response with account data
```

**3. Port Configuration**
If EspoCRM conflicts with PBX:
```yaml
# In config.yml
integrations:
  espocrm:
    api_url: "https://localhost:8888/api/v1"  # Use different port
```

### Integration Not Initialized

**Symptoms:**
- Integration enabled but not working
- No integration features appear in UI

**Solution:**
```bash
# Verify integrations are initialized in PBX core
grep "Integration initialized" ~/PBX/logs/pbx.log

# Should see:
# - "Jitsi integration initialized"
# - "Matrix integration initialized"
# - "EspoCRM integration initialized"

# If missing, check config.yml and restart:
sudo systemctl restart pbx
```

---

## Phone Registration

### Phone Won't Register

**Symptoms:**
- Phone shows "Not registered"
- Can't make or receive calls
- SIP registration fails

**Diagnostics:**
```bash
# 1. Check if PBX is running
sudo systemctl status pbx

# 2. Check if SIP port is listening
sudo netstat -ulnp | grep 5060

# 3. Check firewall
sudo ufw status | grep 5060

# 4. Test from phone's network
ping [pbx_server_ip]
telnet [pbx_server_ip] 5060
```

**Solutions:**

**1. Firewall Not Open**
```bash
# Open SIP port
sudo ufw allow 5060/udp
sudo ufw allow 10000:20000/udp
sudo ufw reload
```

**2. Wrong Server IP**
```bash
# Verify external_ip in config
grep external_ip ~/PBX/config.yml
# Should match your PBX server's IP address
```

**3. Wrong Credentials**
- Verify extension number matches configuration
- Check password is correct
- Extensions are now in database, not config.yml

**4. Check Extension in Database**
```bash
# List all extensions
python3 scripts/list_extensions_from_db.py

# Should show your extension number
```

### Phone Registers But Can't Make Calls

**Symptoms:**
- Phone shows "Registered"
- Dialing results in "Not Available" or error

**Solutions:**

**1. Check Dialplan**
```bash
# Verify dialplan in config.yml
# Should have patterns for internal extensions
nano ~/PBX/config.yml

# Look for:
dialplan:
  - pattern: "^1[0-9]{3}$"  # Matches 1XXX extensions
    destination: "extension"
```

**2. Verify Call Routing**
```bash
# Watch logs while making call
tail -f ~/PBX/logs/pbx.log | grep "Routing call"

# Should see:
# "Routing call: 1001 -> 1002"
```

### Phone Registration Tracking

**View Registered Phones:**
```bash
# List currently registered phones
curl http://localhost:8080/api/registered_phones

# Clear registration database (if needed)
python3 scripts/clear_registered_phones.py
```

---

## Network and Connectivity

### One-Way Audio

**Symptoms:**
- Can hear caller but they can't hear you
- Or vice versa

**Causes:**
1. NAT/Firewall blocking return path
2. Incorrect external_ip configuration
3. RTP ports not open

**Solutions:**
```bash
# 1. Verify external_ip
nano ~/PBX/config.yml
# Set to your public/external IP if behind NAT

# 2. Open RTP ports
sudo ufw allow 10000:20000/udp

# 3. Check NAT configuration
# If behind NAT, ensure port forwarding is set up:
# - UDP 5060 → PBX server
# - UDP 10000-20000 → PBX server
```

### Packet Loss Issues

**Symptoms:**
- Choppy audio
- Intermittent dropouts
- Call quality degradation

**Diagnostics:**
```bash
# Monitor packet loss
tail -f ~/PBX/logs/pbx.log | grep "loss"

# Check network statistics
ip -s link show [interface]
```

**Solutions:**
1. Implement QoS for VoIP traffic
2. Increase network bandwidth
3. Reduce network congestion
4. Check for faulty network equipment

---

## Configuration Issues

### SSL/HTTPS Configuration

**Symptoms:**
- Browser shows security warnings
- HTTPS not working
- Certificate errors

**Solutions:**

**For Development (Self-Signed):**
```bash
# Generate self-signed certificate
python3 scripts/generate_ssl_cert.py --hostname [your_ip_or_hostname]

# Browser will show warning - this is normal for self-signed
# Click "Advanced" → "Proceed anyway"
```

**For Production (Let's Encrypt):**
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Update config.yml
nano ~/PBX/config.yml

# Set:
api:
  ssl:
    cert: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
    key: /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### Database Connection Issues

**Symptoms:**
- Can't add extensions
- Voicemail not working
- "Database connection failed" errors

**Solutions:**

**For PostgreSQL:**
```bash
# Test connection
python3 scripts/verify_database.py

# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials in .env
nano ~/PBX/.env

# Should have:
DB_HOST=localhost
DB_NAME=pbx_system
DB_USER=pbx_user
DB_PASSWORD=your_password
```

**For SQLite:**
```bash
# Check database file exists
ls -lh pbx.db

# Verify permissions
chmod 644 pbx.db

# Test manually
sqlite3 pbx.db "SELECT * FROM extensions;"
```

### YAML Configuration Errors

**Symptoms:**
- PBX won't start
- "YAML parsing error"
- Configuration not loading

**Solutions:**
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config.yml'))"

# Common issues:
# 1. Incorrect indentation (use spaces, not tabs)
# 2. Missing colons after keys
# 3. Unquoted special characters

# Backup before editing
cp config.yml config.yml.backup

# Use proper editor
nano config.yml  # Shows line numbers
```

### Merge Conflicts in config.yml

**Symptoms:**
- Git shows merge conflicts in config.yml
- File contains `<<<<<<<`, `=======`, `>>>>>>>` markers

**Solution:**
See [FIXING_YAML_MERGE_CONFLICTS.md](FIXING_YAML_MERGE_CONFLICTS.md) for detailed guide.

Quick fix:
```bash
# Manually edit to remove conflict markers
nano config.yml

# Remove lines with <<<<<<< ======= >>>>>>>
# Keep the version you want
# Save and commit
```

---

## Service Management

### PBX Service Won't Start

**Diagnostics:**
```bash
# Check service status
sudo systemctl status pbx

# View error logs
sudo journalctl -u pbx -n 50

# Test manually to see errors
cd ~/PBX
python3 main.py
```

**Common Issues:**

**1. CHDIR Error (Exit Code 200)**
```bash
# Check service status - look for "status=200/CHDIR"
sudo systemctl status pbx

# This means WorkingDirectory is missing or incorrect
```

**Solution:**
The service file is missing the `WorkingDirectory` directive or it points to a non-existent directory.

```bash
# Edit service file
sudo nano /etc/systemd/system/pbx.service

# Ensure it includes WorkingDirectory and uses absolute paths:
# [Service]
# WorkingDirectory=/root/PBX  # or your actual PBX path
# ExecStart=/root/PBX/venv/bin/python /root/PBX/main.py

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart pbx
```

See [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md) for detailed service configuration.

**2. Port Already in Use**
```bash
# Find what's using port 5060
sudo lsof -i :5060

# Kill the process or change PBX port
```

**3. Missing Dependencies**
```bash
# Reinstall requirements
pip3 install -r requirements.txt
```

**4. Permission Errors**
```bash
# Check file permissions
ls -la ~/PBX

# Fix if needed
chmod +x main.py
```

### Logs Not Updating

**Symptoms:**
- Log file empty or not changing
- Can't debug issues

**Solutions:**
```bash
# Check logging level in config.yml
nano ~/PBX/config.yml

# Set to DEBUG for troubleshooting
logging:
  level: "DEBUG"

# Restart service
sudo systemctl restart pbx

# Verify logs are being written
tail -f ~/PBX/logs/pbx.log
```

---

## Getting More Help

If issues persist after trying these solutions:

1. **Check Detailed Guides:**
   - [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment details
   - [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing procedures
   - [CALL_FLOW.md](CALL_FLOW.md) - Understanding call flow

2. **Enable Debug Logging:**
   ```yaml
   logging:
     level: "DEBUG"
   ```

3. **Collect Diagnostic Information:**
   ```bash
   # System info
   python3 --version
   uname -a
   
   # Service status
   sudo systemctl status pbx
   
   # Network info
   sudo netstat -tlnup | grep -E "5060|8080"
   
   # Recent logs
   tail -100 ~/PBX/logs/pbx.log > debug_log.txt
   ```

4. **Open GitHub Issue** with:
   - Description of the problem
   - Steps to reproduce
   - Error messages from logs
   - System configuration details

---

**Last Updated:** December 16, 2025  
**Status:** Production Ready
