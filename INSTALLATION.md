# Installation and Deployment Guide

## Table of Contents
- [Quick Start Checklist](#quick-start-checklist)
- [System Requirements](#system-requirements)
- [Installation Steps](#installation-steps)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start Checklist

**For first-time setup - follow these steps in order:**

### ☐ Before You Start

- [ ] You have SSH access to your server
- [ ] Python 3.7+ is installed: `python3 --version`
- [ ] You have sudo/root access
- [ ] You know your server's IP address

### ☐ Step 1: Install PBX (5 minutes)

```bash
# Connect to server
ssh user@your-server-ip

# Clone repository
cd ~
git clone https://github.com/mattiIce/PBX.git
cd PBX

# Install dependencies
pip3 install -r requirements.txt
# Or on Debian/Ubuntu:
./install_requirements.sh

# Create directories
mkdir -p logs recordings voicemail moh cdr
```

### ☐ Step 2: Configure PBX (5 minutes)

```bash
# Edit config
nano config.yml
```

**Check these settings:**

```yaml
server:
  external_ip: "YOUR.SERVER.IP"  # Update with your server IP

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

### ☐ Step 3: Open Firewall Ports (2 minutes)

**CRITICAL - Without this, nothing works!**

**Ubuntu/Debian:**
```bash
sudo ufw allow 5060/udp
sudo ufw allow 10000:20000/udp
sudo ufw allow 8080/tcp
sudo ufw reload
sudo ufw status  # Verify
```

**CentOS/RHEL:**
```bash
sudo firewall-cmd --permanent --add-port=5060/udp
sudo firewall-cmd --permanent --add-port=10000-20000/udp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports  # Verify
```

### ☐ Step 4: Test Run (2 minutes)

```bash
cd ~/PBX
python3 main.py
```

**Should see:**
```
✓ SIP server started on 0.0.0.0:5060
✓ PBX system started successfully
```

**If errors, see [Troubleshooting](#troubleshooting) below**

Stop with: `Ctrl+C`

### ☐ Step 5: Set Up as Service (3 minutes)

**Option A: Use Template (Recommended)**
```bash
# Edit the provided template
nano pbx.service

# Update WorkingDirectory, ExecStart, User paths
# Then install:
sudo cp pbx.service /etc/systemd/system/
```

**Option B: Create Manually**
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

**⚠️ IMPORTANT:** The `WorkingDirectory` line is required to avoid CHDIR errors!

**Start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable pbx
sudo systemctl start pbx
sudo systemctl status pbx  # Should show "active (running)"
```

See [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md) for troubleshooting.

### ☐ Step 6: Configure First Phone (5 minutes)

**On your SIP phone (Zultys, Yealink, etc.):**

Access phone settings (web interface or phone menu)

**Account Settings:**
```
Display Name: Phone 1
Username: 1001
Password: [from database - check with list_extensions_from_db.py]

Server: YOUR.SERVER.IP
Port: 5060
Transport: UDP

Registration: Enabled
```

Save and wait for "Registered" status

### ☐ Step 7: Verify Registration

**Check PBX logs:**
```bash
tail -f ~/PBX/logs/pbx.log
```

**Should see:**
```
INFO - Extension 1001 registered from ('192.168.x.x', 5060)
```

### ☐ Step 8: Configure Second Phone

Repeat Step 6 with:
```
Username: 1002
Password: [from database]
Server: YOUR.SERVER.IP
```

### ☐ Step 9: Test Call! 🎉

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

### Success Criteria ✓

You're done when:

- [✓] PBX service is running: `sudo systemctl status pbx`
- [✓] All phones show "Registered"
- [✓] Phones can call each other
- [✓] **Audio works in both directions** ← Main goal!
- [✓] Calls can be ended from either phone

### Useful Commands

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
curl http://localhost:8080/api/status
curl http://localhost:8080/api/extensions
```

### Next Steps

Once basic calling works:

1. **Change logging to INFO** in config.yml (reduce log verbosity)
2. **Backup your config:** `cp config.yml config.yml.backup`
3. **Read [FEATURES.md](FEATURES.md)** for voicemail, recording, etc.
4. **Set up monitoring** (check logs daily)
5. **For production deployment**, see [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)

---

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 2GB
- **Storage**: 10GB (more for recordings)
- **OS**: Linux, macOS, or Windows
- **Python**: 3.7 or higher
- **Network**: UDP ports 5060, 10000-20000, TCP port 8080

### Recommended for Production
- **CPU**: 4+ cores
- **RAM**: 4GB+
- **Storage**: 50GB+ SSD
- **Network**: Dedicated network interface, QoS enabled
- **OS**: Ubuntu 20.04 LTS or CentOS 8

## Installation Steps

### 1. Install Python and Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip git
```

#### CentOS/RHEL
```bash
sudo yum install python3 python3-pip git
```

#### macOS
```bash
brew install python3 git
```

### 2. Clone Repository
```bash
git clone https://github.com/mattiIce/PBX.git
cd PBX
```

### 3. Install Python Dependencies

#### Basic Installation (Core Features Only)
```bash
pip3 install pyyaml
```

#### Full Installation (All Features)
For systems where pip is externally managed (Debian/Ubuntu):
```bash
# Use the provided installation script which handles system package conflicts
./install_requirements.sh

# Or manually with the appropriate flags:
pip3 install -r requirements.txt --break-system-packages --ignore-installed typing_extensions
```

For other systems or virtual environments:
```bash
pip3 install -r requirements.txt
```

**Note**: On Debian/Ubuntu systems, `typing_extensions` is managed by the system package manager.
The `--ignore-installed` flag allows pip to use the system-provided version (4.10.0),
which is compatible with Python 3.12 and all required packages.

### 4. Configure Firewall

#### Ubuntu (UFW)
```bash
sudo ufw allow 5060/udp
sudo ufw allow 10000:20000/udp
sudo ufw allow 8080/tcp
```

#### CentOS (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=5060/udp
sudo firewall-cmd --permanent --add-port=10000-20000/udp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### 5. Configure the System

Edit `config.yml`:
```bash
cp config.yml config.local.yml
nano config.local.yml
```

Important settings to configure:
- Extension usernames and passwords
- SIP and RTP port ranges
- API server settings
- Feature enablement
- SIP trunk credentials (if using external calls)

### 6. Create Required Directories
```bash
mkdir -p logs recordings voicemail cdr moh/default
```

### 7. Test the Installation
```bash
python3 main.py
```

You should see:
```
InHouse PBX System v1.0.0
PBX system is running...
```

## Production Deployment

### Running as a Service (systemd)

A template service file (`pbx.service`) is provided in the repository. 

**Quick Installation:**

```bash
# Edit the template to match your installation
nano pbx.service

# Copy to systemd directory
sudo cp pbx.service /etc/systemd/system/

# Reload systemd and start
sudo systemctl daemon-reload
sudo systemctl enable pbx
sudo systemctl start pbx
```

See [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md) for detailed instructions.

**Manual Creation:**

Alternatively, create `/etc/systemd/system/pbx.service`:

```ini
[Unit]
Description=InHouse PBX System
After=network.target

[Service]
Type=simple
User=pbx
Group=pbx
WorkingDirectory=/opt/pbx
ExecStart=/usr/bin/python3 /opt/pbx/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**⚠️ IMPORTANT:** Update `WorkingDirectory`, `ExecStart`, `User`, and `Group` to match your installation.

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pbx
sudo systemctl start pbx
sudo systemctl status pbx
```

### Create Dedicated User
```bash
sudo useradd -r -s /bin/false pbx
sudo mkdir -p /opt/pbx
sudo cp -r /path/to/PBX/* /opt/pbx/
sudo chown -R pbx:pbx /opt/pbx
```

### Log Rotation

Create `/etc/logrotate.d/pbx`:
```
/opt/pbx/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 pbx pbx
    sharedscripts
    postrotate
        systemctl reload pbx
    endscript
}
```

### Monitoring

#### Check Status
```bash
# System status
curl http://localhost:8080/api/status

# View logs
tail -f /opt/pbx/logs/pbx.log

# Service status
sudo systemctl status pbx
```

#### Health Checks
Create a simple health check script:
```bash
#!/bin/bash
response=$(curl -s http://localhost:8080/api/status)
if [ $? -eq 0 ]; then
    echo "PBX is running"
else
    echo "PBX is down!"
    # Alert or restart
fi
```

### Backup Strategy

#### What to Backup
- Configuration: `config.yml`
- Recordings: `recordings/`
- Voicemail: `voicemail/`
- CDR data: `cdr/`
- Music on hold: `moh/`

#### Backup Script
```bash
#!/bin/bash
BACKUP_DIR="/backup/pbx/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

cp /opt/pbx/config.yml $BACKUP_DIR/
tar czf $BACKUP_DIR/recordings.tar.gz /opt/pbx/recordings/
tar czf $BACKUP_DIR/voicemail.tar.gz /opt/pbx/voicemail/
tar czf $BACKUP_DIR/cdr.tar.gz /opt/pbx/cdr/

# Retention: keep 30 days
find /backup/pbx/ -mtime +30 -delete
```

### Security Hardening

1. **Change Default Passwords**: Update all extension passwords in `config.yml`

2. **Firewall Rules**: Only allow SIP/RTP from trusted networks

3. **API Security**: 
   - Use reverse proxy (nginx) with authentication
   - Enable HTTPS with SSL certificates

4. **Regular Updates**: Keep system and Python packages updated

5. **Monitor Logs**: Watch for suspicious activity

### Performance Tuning

#### Linux Kernel Parameters
Edit `/etc/sysctl.conf`:
```
# Increase UDP buffer sizes
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# Increase file descriptor limit
fs.file-max = 65536
```

Apply:
```bash
sudo sysctl -p
```

#### System Limits
Edit `/etc/security/limits.conf`:
```
pbx soft nofile 65536
pbx hard nofile 65536
```

## Troubleshooting

### PBX Won't Start

1. Check Python version:
```bash
python3 --version  # Should be 3.13+
```

2. Check dependencies:
```bash
pip3 install pyyaml
```

3. Check config file:
```bash
python3 -c "import yaml; yaml.safe_load(open('config.yml'))"
```

4. Check port availability:
```bash
sudo netstat -tulpn | grep 5060
sudo netstat -tulpn | grep 8080
```

### Extensions Can't Register

1. Check firewall allows UDP 5060
2. Verify extension credentials in `config.yml`
3. Check logs: `tail -f logs/pbx.log`
4. Test with example client: `python examples/simple_client.py`

### No Audio in Calls

1. Check RTP port range is open (UDP 10000-20000)
2. Verify NAT/firewall allows UDP traffic
3. Check codec compatibility
4. Review RTP logs in debug mode

### API Not Accessible

1. Check port 8080 is open
2. Verify `api.host` in `config.yml`
3. Test locally: `curl http://localhost:8080/api/status`
4. Check for binding errors in logs

## Upgrading

1. Backup current installation
2. Pull latest code:
```bash
git pull origin main
```
3. Check for config changes:
```bash
diff config.yml config.yml.new
```
4. Restart service:
```bash
sudo systemctl restart pbx
```

## Docker Deployment

The PBX system includes production-ready Docker containerization with multi-stage builds for optimal image size and security.

### Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose (included with Docker Desktop)

### Quick Start with Docker Compose

1. **Copy the environment template**:
```bash
cp .env.example .env
```

2. **Edit `.env` and set required variables**:
```bash
# Required configuration
DB_PASSWORD=YourSecurePassword123!
REDIS_PASSWORD=YourRedisPassword456!

# Optional: Add other credentials as needed
SMTP_HOST=smtp.yourserver.com
SMTP_PORT=587
# ... etc
```

3. **Start all services** (PBX, PostgreSQL, Redis):
```bash
docker compose up -d
```

4. **Check logs**:
```bash
docker compose logs -f pbx
```

5. **Access the system**:
- API/Web Interface: http://localhost:8880
- SIP Port: UDP 5060
- RTP Ports: UDP 10000-20000

### Docker Compose Services

The `docker-compose.yml` orchestrates three services:

- **pbx**: Main PBX application
- **postgres**: PostgreSQL database (persistent storage)
- **redis**: Redis cache (sessions, real-time features)

### Building the Docker Image

To build the image separately:
```bash
docker build -t pbx-system:latest .
```

The Dockerfile uses:
- Multi-stage build for smaller final image size
- Python 3.11 slim base image
- Non-root user (pbx:1000) for security
- System dependencies: ffmpeg, portaudio, opus, speex, etc.
- Health check on API port

### Data Persistence

The following volumes persist data:
- `postgres_data`: Database
- `redis_data`: Redis cache
- `recordings`: Call recordings
- `voicemail`: Voicemail messages
- `cdr`: Call detail records
- `moh`: Music on hold files
- `logs`: Application logs

### Customization

**Custom configuration**: Mount your own `config.yml`:
```yaml
volumes:
  - ./my-config.yml:/app/config.yml:ro
```

**Custom voice prompts**: Mount your own audio files:
```yaml
volumes:
  - ./my-prompts:/app/auto_attendant:ro
```

**SSL/TLS certificates**: Mount certificate directory:
```yaml
volumes:
  - ./certs:/app/certs:ro
```

### Stopping and Cleanup

Stop services:
```bash
docker compose down
```

Stop and remove volumes (⚠️ deletes all data):
```bash
docker compose down -v
```

### Troubleshooting

**View logs**:
```bash
docker compose logs -f pbx        # PBX logs
docker compose logs -f postgres   # Database logs
docker compose logs -f redis      # Redis logs
```

**Access container shell**:
```bash
docker compose exec pbx /bin/bash
```

**Rebuild after code changes**:
```bash
docker compose up -d --build
```

## Getting Help

- Check logs: `logs/pbx.log`
- Review configuration: `config.yml`
- Test with examples: `examples/simple_client.py`
- Open GitHub issue for bugs
