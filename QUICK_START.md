# Quick Start Checklist - First Time PBX Setup

Use this checklist when deploying to your server at 192.168.1.14.

## ☐ Before You Start

- [ ] You have SSH access to server 192.168.1.14
- [ ] Python 3.7+ is installed: `python3 --version`
- [ ] You have sudo/root access
- [ ] You know your network subnet (e.g., 192.168.1.0/24)

## ☐ Step 1: Install PBX (5 minutes)

```bash
# Connect to server
ssh user@192.168.1.14

# Clone repository
cd ~
git clone https://github.com/mattiIce/PBX.git
cd PBX
git checkout copilot/debug-phone-call-issue

# Install dependencies
pip3 install -r requirements.txt

# Create directories
mkdir -p logs recordings voicemail moh cdr
```

## ☐ Step 2: Configure PBX (5 minutes)

```bash
# Edit config
nano config.yml
```

**Check these settings:**

```yaml
server:
  external_ip: "192.168.1.14"  # ✓ Already set correctly!

database:
  type: sqlite  # SQLite for quick start (use postgresql for production)
  path: pbx.db

logging:
  level: "DEBUG"  # Use DEBUG for initial setup
```

Save: `Ctrl+X`, `Y`, `Enter`

**Initialize database and add extensions:**

```bash
# Seed initial extensions into database
python3 scripts/seed_extensions.py

# Verify extensions were added
python3 scripts/list_extensions_from_db.py
```

**Note:** Extensions are now stored securely in the database, not in config.yml.
This prevents exposing passwords in plain text configuration files.

## ☐ Step 3: Open Firewall Ports (2 minutes)

**CRITICAL - Without this, nothing works!**

### Ubuntu/Debian:
```bash
sudo ufw allow 5060/udp
sudo ufw allow 10000:20000/udp
sudo ufw allow 8080/tcp
sudo ufw reload
sudo ufw status  # Verify
```

### CentOS/RHEL:
```bash
sudo firewall-cmd --permanent --add-port=5060/udp
sudo firewall-cmd --permanent --add-port=10000-20000/udp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports  # Verify
```

## ☐ Step 4: Test Run (2 minutes)

```bash
cd ~/PBX
python3 main.py
```

**Should see:**
```
✓ SIP server started on 0.0.0.0:5060
✓ PBX system started successfully
```

**If errors, see DEPLOYMENT_GUIDE.md**

Stop with: `Ctrl+C`

## ☐ Step 5: Set Up as Service (3 minutes)

```bash
# Create service file
sudo nano /etc/systemd/system/pbx.service
```

**Copy this (replace YOUR_USERNAME):**

```ini
[Unit]
Description=InHouse PBX System
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/PBX
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/PBX/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable pbx
sudo systemctl start pbx
sudo systemctl status pbx  # Should show "active (running)"
```

## ☐ Step 6: Configure First Phone (5 minutes)

### On your Zultys ZIP 37G phone:

Access phone settings (web interface or phone menu)

**Account 1 Settings:**
```
Display Name: Phone 1
Username: 1001
Password: [from your config.yml]

Server: 192.168.1.14
Port: 5060
Transport: UDP

Registration: Enabled
```

Save and wait for "Registered" status

## ☐ Step 7: Verify Registration

**Check PBX logs:**
```bash
tail -f ~/PBX/logs/pbx.log
```

**Should see:**
```
INFO - Extension 1001 registered from ('192.168.1.X', 5060)
```

If not, see TROUBLESHOOTING below.

## ☐ Step 8: Configure Second Phone

Repeat Step 6 with:
```
Username: 1002
Password: [from your config.yml]
Server: 192.168.1.14
```

## ☐ Step 9: Test Call! 🎉

1. **Pick up phone 1001**
2. **Dial: 1002**
3. **Phone 1002 rings** ✓
4. **Answer phone 1002**
5. **Talk - hear each other!** ✓

**Check logs for:**
```
INFO - INVITE request from ...
INFO - RTP relay allocated on port 10000
INFO - Routing call: 1001 -> 1002
DEBUG - Relayed 160 bytes: A->B  ← Audio working!
DEBUG - Relayed 160 bytes: B->A  ← Audio working!
```

## ☐ Step 10: Configure Remaining Phones

For each additional Zultys phone:
1. Add extension to config.yml
2. Restart: `sudo systemctl restart pbx`
3. Configure phone (Step 6)
4. Test call

## Quick Troubleshooting

### Phone Won't Register

**Check:**
```bash
# Is PBX running?
sudo systemctl status pbx

# Is port open?
sudo netstat -ulnp | grep 5060

# Can phone reach server?
ping 192.168.1.14  # From phone's network

# Check firewall
sudo ufw status | grep 5060
```

### No Audio in Calls

**Check:**
```bash
# RTP ports open?
sudo ufw status | grep 10000:20000

# external_ip correct in config?
grep external_ip ~/PBX/config.yml
# Should show: external_ip: "192.168.1.14"

# See logs
tail -f ~/PBX/logs/pbx.log | grep RTP
```

### Service Won't Start

```bash
# Check errors
sudo journalctl -u pbx -n 50

# Test manually
cd ~/PBX
python3 main.py
# Look for error messages
```

## Useful Commands

```bash
# Service control
sudo systemctl start pbx     # Start
sudo systemctl stop pbx      # Stop
sudo systemctl restart pbx   # Restart (after config changes)
sudo systemctl status pbx    # Check status

# View logs
tail -f ~/PBX/logs/pbx.log          # Live log view
sudo journalctl -u pbx -f           # System logs
sudo journalctl -u pbx -n 100       # Last 100 lines

# Edit config
nano ~/PBX/config.yml
sudo systemctl restart pbx   # Always restart after changes

# Check system
curl http://192.168.1.14:8080/api/status
curl http://192.168.1.14:8080/api/extensions
```

## Success Criteria ✓

You're done when:

- [✓] PBX service is running: `sudo systemctl status pbx`
- [✓] All phones show "Registered"
- [✓] Phones can call each other
- [✓] **Audio works in both directions** ← Main goal!
- [✓] Calls can be ended from either phone

## Next Steps

Once basic calling works:

1. **Change logging to INFO** in config.yml (reduce log verbosity)
2. **Backup your config:** `cp config.yml config.yml.backup`
3. **Read FEATURES.md** for voicemail, recording, etc.
4. **Set up monitoring** (check logs daily)

## Need Help?

1. **DEPLOYMENT_GUIDE.md** - Detailed setup instructions
2. **TESTING_GUIDE.md** - Testing and troubleshooting
3. **CALL_FLOW.md** - How calls work
4. **Check logs** - They tell you everything!

---

**Remember:** This is your first PBX! Start simple:
- Get 2 phones working first
- Then add more phones
- Then explore advanced features

The fix for silent audio is already in the code - now it's about proper deployment! 🎯
