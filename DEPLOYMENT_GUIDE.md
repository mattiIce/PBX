# Deployment Guide for First-Time PBX Setup

This guide walks you through deploying the PBX system on your server at 192.168.1.14 for your Zultys phones.

## Pre-Deployment Checklist

Before you start, gather this information:

- [ ] Server IP address: **192.168.1.14** (you have this)
- [ ] Network details: What subnet are your phones on? (e.g., 192.168.1.0/24)
- [ ] How many Zultys phones you have and their extension numbers
- [ ] Server OS (Linux recommended, Ubuntu/Debian preferred)
- [ ] Do you have sudo/root access?
- [ ] Is Python 3.7+ installed?

## Step 1: Initial Server Setup

### 1.1 Connect to Your Server

```bash
# SSH into your server
ssh your-username@192.168.1.14
```

### 1.2 Verify Python Version

```bash
python3 --version
# Should show Python 3.7 or higher
```

If Python is not installed:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip
```

### 1.3 Install Git (if not already installed)

```bash
# Ubuntu/Debian
sudo apt install git

# CentOS/RHEL
sudo yum install git
```

## Step 2: Deploy the PBX Code

### 2.1 Choose Installation Directory

```bash
# Option 1: Install in your home directory
cd ~

# Option 2: Install in /opt (system-wide, requires sudo)
cd /opt
```

### 2.2 Clone or Copy the Repository

If you're deploying from this branch:
```bash
git clone https://github.com/mattiIce/PBX.git
cd PBX
git checkout copilot/debug-phone-call-issue
```

Or if you're copying files manually:
```bash
# Create directory
mkdir -p ~/PBX
cd ~/PBX

# Copy all files from your development environment
# (use scp, rsync, or your preferred method)
```

### 2.3 Install Python Dependencies

```bash
cd ~/PBX  # or wherever you installed

# Install required packages
pip3 install -r requirements.txt

# Or install individually
pip3 install PyYAML cryptography
```

### 2.4 Verify Installation

```bash
python3 -c "import yaml; import cryptography; print('Dependencies OK')"
# Should print: Dependencies OK
```

## Step 3: Configure the PBX

### 3.1 Edit Configuration File

```bash
nano config.yml
# Or use your preferred editor: vim, vi, etc.
```

### 3.2 **CRITICAL: Set Your Server IP**

Find this section and update it:

```yaml
server:
  sip_host: "0.0.0.0"          # Leave as 0.0.0.0 (binds to all interfaces)
  sip_port: 5060
  
  # ⚠️ IMPORTANT: Set this to your server's actual IP address
  external_ip: "192.168.1.14"  # ← YOU ALREADY HAVE THIS SET CORRECTLY!
  
  rtp_port_range_start: 10000
  rtp_port_range_end: 20000
```

### 3.3 Configure Extensions for Your Phones

Update the extensions section to match your phones:

```yaml
extensions:
  - number: "1001"
    name: "Reception Desk"
    password: "StrongPassword123!"  # ⚠️ Change this!
    allow_external: true
  
  - number: "1002"
    name: "Office 1"
    password: "StrongPassword456!"  # ⚠️ Change this!
    allow_external: true
    
  - number: "1003"
    name: "Office 2"
    password: "StrongPassword789!"  # ⚠️ Change this!
    allow_external: true
    
  # Add more extensions as needed for each Zultys phone
```

**Important Notes:**
- Use **strong, unique passwords** for each extension
- `number` is what users dial (e.g., dial 1002 to call Office 1)
- `name` is just a descriptive label
- Keep track of which extension number goes to which phone/person

### 3.4 Set Logging Level

For initial setup, use DEBUG to see what's happening:

```yaml
logging:
  level: "DEBUG"  # Change to INFO once everything works
  file: "logs/pbx.log"
  console: true
```

### 3.5 Save and Exit

```bash
# In nano: Ctrl+X, then Y, then Enter
# In vim: :wq
```

## Step 4: Firewall Configuration

### 4.1 Check Current Firewall Status

```bash
# Ubuntu/Debian (ufw)
sudo ufw status

# CentOS/RHEL (firewalld)
sudo firewall-cmd --state
```

### 4.2 Open Required Ports

**You MUST open these UDP ports:**

#### Using UFW (Ubuntu/Debian):

```bash
# SIP signaling
sudo ufw allow 5060/udp

# RTP media (audio streams)
sudo ufw allow 10000:20000/udp

# REST API (optional, for management)
sudo ufw allow 8080/tcp

# Reload firewall
sudo ufw reload

# Verify
sudo ufw status
```

#### Using firewalld (CentOS/RHEL):

```bash
# SIP signaling
sudo firewall-cmd --permanent --add-port=5060/udp

# RTP media (audio streams)
sudo firewall-cmd --permanent --add-port=10000-20000/udp

# REST API (optional, for management)
sudo firewall-cmd --permanent --add-port=8080/tcp

# Reload firewall
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

#### Using iptables (if no firewall manager):

```bash
# SIP signaling
sudo iptables -A INPUT -p udp --dport 5060 -j ACCEPT

# RTP media
sudo iptables -A INPUT -p udp --dport 10000:20000 -j ACCEPT

# REST API
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

# Save rules
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

**⚠️ WARNING:** Without these ports open, phones won't be able to:
- Register (needs 5060)
- Have audio (needs 10000-20000)

## Step 5: Create Required Directories

```bash
cd ~/PBX  # or your installation directory

# Create directories for logs and recordings
mkdir -p logs
mkdir -p recordings
mkdir -p voicemail
mkdir -p moh
mkdir -p cdr

# Set permissions
chmod 755 logs recordings voicemail moh cdr
```

## Step 6: Test Run the PBX

### 6.1 First Test - Manual Start

```bash
cd ~/PBX
python3 main.py
```

**Expected output:**
```
============================================================
InHouse PBX System v1.0.0
============================================================
2025-XX-XX XX:XX:XX - PBX - INFO - FIPS 140-2 compliant encryption enabled
2025-XX-XX XX:XX:XX - PBX - INFO - Loaded extension 1001 (Reception Desk)
2025-XX-XX XX:XX:XX - PBX - INFO - Loaded extension 1002 (Office 1)
2025-XX-XX XX:XX:XX - PBX - INFO - SIP server started on 0.0.0.0:5060
2025-XX-XX XX:XX:XX - PBX - INFO - SIP server listening for messages...
2025-XX-XX XX:XX:XX - PBX - INFO - API server started on http://0.0.0.0:8080
2025-XX-XX XX:XX:XX - PBX - INFO - PBX system started successfully

PBX system is running...
Press Ctrl+C to stop
```

**If you see errors:**
- "Permission denied" on port 5060 → Use sudo or change to port > 1024
- "Address already in use" → Another service is using port 5060
- "Module not found" → Dependencies not installed correctly

### 6.2 Verify Network Binding

Open another terminal and check:

```bash
# Check if PBX is listening on ports
sudo netstat -ulnp | grep python
# Should show:
# udp    0.0.0.0:5060    ... python3
# udp    0.0.0.0:10000   ... python3 (and more RTP ports)
```

### 6.3 Stop the Test

Press `Ctrl+C` in the terminal running the PBX.

## Step 7: Configure as System Service (Run Automatically)

To keep the PBX running even after you log out, set it up as a systemd service.

### 7.1 Install Service File

A template service file is provided in the repository. Edit and install it:

```bash
# Edit the template to match your installation
nano pbx.service

# Copy to systemd directory
sudo cp pbx.service /etc/systemd/system/
```

**⚠️ IMPORTANT:** Edit `pbx.service` and update:
- `WorkingDirectory`: Your PBX installation path (e.g., `/root/PBX`, `/opt/pbx`, `/home/username/PBX`)
- `ExecStart`: Path to your Python executable and main.py
- `User` and `Group`: User/group that owns the PBX files

See [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md) for detailed instructions and troubleshooting.

### 7.2 Alternative: Manual Creation

If you prefer to create the service file manually:

```bash
sudo nano /etc/systemd/system/pbx.service
```

Add this content (update paths as needed):

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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 7.3 Enable and Start Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable pbx

# Start the service now
sudo systemctl start pbx

# Check status
sudo systemctl status pbx
```

**Expected output:**
```
● pbx.service - InHouse PBX System
   Loaded: loaded (/etc/systemd/system/pbx.service; enabled)
   Active: active (running) since ...
```

### 7.4 View Logs

```bash
# Real-time logs
sudo journalctl -u pbx -f

# Or view log file
tail -f ~/PBX/logs/pbx.log
```

### 7.5 Service Management Commands

```bash
# Start PBX
sudo systemctl start pbx

# Stop PBX
sudo systemctl stop pbx

# Restart PBX (after config changes)
sudo systemctl restart pbx

# Check status
sudo systemctl status pbx

# View logs
sudo journalctl -u pbx -n 100  # Last 100 lines
```

## Step 8: Configure Your Zultys Phones

Now that the PBX is running, configure each phone.

### 8.1 Access Phone Web Interface

From your computer, open a web browser and go to your phone's IP address:
```
http://192.168.1.X  (where X is your phone's IP)
```

Or use the phone's menu system (check Zultys ZIP 37G manual).

### 8.2 SIP Account Configuration

For **Phone 1 (Extension 1001)**:

```
SIP Account 1:
  Display Name: Reception Desk
  User Name: 1001
  Authentication User: 1001
  Password: StrongPassword123!  (from your config.yml)
  
SIP Server:
  Server Address: 192.168.1.14
  Server Port: 5060
  Transport: UDP
  
Registration:
  Register: Yes
  Registration Expires: 3600
```

### 8.3 Repeat for Each Phone

For **Phone 2 (Extension 1002)**:
- User Name: 1002
- Password: StrongPassword456!
- Same server settings

And so on for each phone...

### 8.4 Test Registration

After saving settings, phone should register. On the phone display, you should see:
- Registration status: "Registered" or similar
- May show extension number (1001, 1002, etc.)

### 8.5 Verify in PBX Logs

```bash
tail -f ~/PBX/logs/pbx.log
```

Look for:
```
INFO - Extension 1001 registered from ('192.168.1.X', 5060)
INFO - Extension 1002 registered from ('192.168.1.Y', 5060)
```

## Step 9: Test Phone-to-Phone Calls

### 9.1 Make First Call

1. Pick up phone 1001
2. Dial: **1002**
3. Phone 1002 should ring
4. Answer on phone 1002
5. **Talk - you should hear each other!**

### 9.2 What to Check in Logs

```bash
tail -f ~/PBX/logs/pbx.log
```

**During call, you should see:**
```
INFO - INVITE request from ('192.168.1.X', 5060)
INFO - Caller RTP: 192.168.1.X:XXXXX
INFO - RTP relay allocated on port 10000
INFO - Forwarded INVITE to 1002
INFO - Callee answered call
INFO - RTP relay connected
DEBUG - Relayed 160 bytes: A->B
DEBUG - Relayed 160 bytes: B->A
```

### 9.3 If Audio Doesn't Work

See `TESTING_GUIDE.md` for detailed troubleshooting.

Quick checks:
1. Are UDP ports 10000-20000 open in firewall?
2. Is `external_ip` set correctly in config.yml?
3. Are phones on same network as server?
4. Check logs for "RTP relay" messages

## Step 10: Ongoing Maintenance

### 10.1 Monitor Logs

```bash
# Watch real-time logs
tail -f ~/PBX/logs/pbx.log

# Or with systemd
sudo journalctl -u pbx -f
```

### 10.2 Change Log Level After Testing

Once everything works, reduce logging:

```bash
nano ~/PBX/config.yml
```

Change:
```yaml
logging:
  level: "INFO"  # Change from DEBUG to INFO
```

Then restart:
```bash
sudo systemctl restart pbx
```

### 10.3 Backup Configuration

```bash
# Backup your config
cp ~/PBX/config.yml ~/PBX/config.yml.backup

# Include date in backup name
cp ~/PBX/config.yml ~/PBX/config.yml.$(date +%Y%m%d)
```

### 10.4 Add/Remove Extensions

To add new extensions:

1. Edit config.yml
2. Add new extension entry
3. Restart PBX
4. Configure new phone

```bash
nano ~/PBX/config.yml
# Add new extension
sudo systemctl restart pbx
```

### 10.5 Check System Status

```bash
# Is PBX running?
sudo systemctl status pbx

# What extensions are registered?
curl http://192.168.1.14:8080/api/extensions

# How many active calls?
curl http://192.168.1.14:8080/api/calls
```

## Troubleshooting Common Issues

### Issue: "Permission denied" on Port 5060

Port 5060 requires root privileges on Linux.

**Solution 1:** Run on higher port
```yaml
server:
  sip_port: 5160  # Use port > 1024
```

**Solution 2:** Allow Python to bind privileged ports
```bash
sudo setcap CAP_NET_BIND_SERVICE=+eip /usr/bin/python3
```

### Issue: Service Won't Start

```bash
# Check detailed status
sudo systemctl status pbx

# Check full logs
sudo journalctl -u pbx -n 50

# Test manually
cd ~/PBX
python3 main.py
```

### Issue: Phones Can't Register

1. **Check firewall:**
   ```bash
   sudo ufw status  # UFW
   sudo firewall-cmd --list-ports  # firewalld
   ```

2. **Check PBX is listening:**
   ```bash
   sudo netstat -ulnp | grep 5060
   ```

3. **Check network connectivity:**
   ```bash
   # From phone network, can you reach server?
   ping 192.168.1.14
   ```

4. **Check phone config:**
   - Server IP correct?
   - Password matches config.yml?
   - Port is 5060?

### Issue: No Audio in Calls

See `TESTING_GUIDE.md` for detailed audio troubleshooting.

Quick check:
```bash
# Are RTP ports open?
sudo ufw status | grep 10000:20000
```

## Security Recommendations

### 1. Strong Passwords

```yaml
extensions:
  - number: "1001"
    password: "Use-Long-Random-Passwords-123!"  # At least 12 characters
```

### 2. Limit Access (Optional)

If PBX should only be accessible from local network:

```bash
# Allow only from local subnet
sudo ufw allow from 192.168.1.0/24 to any port 5060 proto udp
sudo ufw allow from 192.168.1.0/24 to any port 10000:20000 proto udp
```

### 3. Enable TLS (Advanced)

For encrypted signaling, see `SECURITY.md` for TLS setup.

### 4. Regular Updates

```bash
cd ~/PBX
git pull origin main  # Or your branch
sudo systemctl restart pbx
```

## Quick Reference Commands

```bash
# Start/Stop/Restart PBX
sudo systemctl start pbx
sudo systemctl stop pbx
sudo systemctl restart pbx

# View logs
tail -f ~/PBX/logs/pbx.log
sudo journalctl -u pbx -f

# Check status
sudo systemctl status pbx
curl http://192.168.1.14:8080/api/status

# Edit config
nano ~/PBX/config.yml
sudo systemctl restart pbx  # After changes

# Test connectivity
ping 192.168.1.14
sudo netstat -ulnp | grep python
```

## Next Steps

Once basic calling works:

1. ✅ Test all phones can call each other
2. ✅ Set up voicemail (see `FEATURES.md`)
3. ✅ Configure call recording if needed
4. ✅ Set up conference rooms
5. ✅ Configure call queues for multiple callers

## Getting Help

If you run into issues:

1. **Check logs:** `tail -f ~/PBX/logs/pbx.log`
2. **Enable DEBUG logging** in config.yml
3. **Verify network:** Phones can ping 192.168.1.14
4. **Check firewall:** Ports 5060 and 10000-20000 are open
5. **Review:** `TESTING_GUIDE.md` and `CALL_FLOW.md`

Remember: This is your first PBX setup - it's normal to encounter a few issues. The logs will tell you what's happening!
