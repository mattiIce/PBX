# Ubuntu 24.04.2 LTS Setup Guide for PBX System

Complete step-by-step guide for setting up all databases and services needed for full PBX feature implementation on Ubuntu 24.04.2 LTS.

## Table of Contents
0. [Get the PBX Repository](#get-the-pbx-repository)
1. [System Preparation](#system-preparation)
2. [PostgreSQL Database Setup](#postgresql-database-setup)
3. [Python Environment Setup](#python-environment-setup)
4. [Database Schemas](#database-schemas)
5. [Active Directory Integration Setup](#active-directory-integration-setup)
6. [SMTP Configuration](#smtp-configuration)
7. [Audio Tools Installation](#audio-tools-installation)
8. [Network Configuration](#network-configuration)
9. [Service Configuration](#service-configuration)
10. [Testing](#testing)

---

## Get the PBX Repository

### First Time Setup (Clone Repository)
```bash
# Navigate to your desired installation directory
cd /home/runner/work/PBX

# Clone the repository
git clone https://github.com/mattiIce/PBX.git
cd PBX

# Verify files are present
ls -la
```

### Update Existing Installation
If you already have the repository and want to pull the latest updates:

```bash
# Navigate to your PBX directory
cd /home/runner/work/PBX/PBX

# Fetch latest changes from the repository
git fetch origin

# Pull the latest changes (this will update scripts, requirements.txt, etc.)
git pull origin main

# Verify the updates
git log -n 5 --oneline

# Check that new files are present
ls -la scripts/
```

**Important**: If you have made local changes to configuration files (like `config.yml`), you may need to stash or commit them before pulling:

```bash
# Option 1: Stash your local changes temporarily
git stash
git pull origin main
git stash pop  # Reapply your changes

# Option 2: Keep your local changes and merge
git pull origin main --no-rebase

# Option 3: View what files changed
git diff origin/main
```

---

## System Preparation

### Update System
```bash
# Update package lists and upgrade system
sudo apt update
sudo apt upgrade -y

# Install essential build tools
sudo apt install -y build-essential git curl wget vim
sudo apt install -y software-properties-common
```

### Set Hostname (if needed)
```bash
# Set hostname for PBX server
sudo hostnamectl set-hostname pbx-server

# Edit hosts file
sudo vim /etc/hosts
# Add: 127.0.0.1 pbx-server
```

### Create PBX User (Optional but Recommended)
```bash
# Create dedicated user for running PBX
sudo useradd -m -s /bin/bash pbxuser
sudo usermod -aG sudo pbxuser

# Switch to PBX user
sudo su - pbxuser
```

---

## PostgreSQL Database Setup

### Install PostgreSQL 16
```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Check installation
sudo systemctl status postgresql

# Verify version
psql --version
# Should show: psql (PostgreSQL) 16.x
```

### Initial PostgreSQL Configuration
```bash
# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check status
sudo systemctl status postgresql
```

### Create PBX Databases and Users
```bash
# Switch to postgres user
sudo -u postgres psql

# Now you're in the PostgreSQL prompt (postgres=#)
```

#### Create Main PBX Database
```sql
-- Create main PBX database
CREATE DATABASE pbx_system;

-- Create PBX user with password
CREATE USER pbx_user WITH PASSWORD 'YourSecurePassword123!';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;

-- Exit PostgreSQL
\q
```

#### Create VIP Callers Database
```bash
# Re-enter PostgreSQL as postgres user
sudo -u postgres psql
```

```sql
-- Use the pbx_system database
\c pbx_system

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO pbx_user;

-- Create VIP callers table
CREATE TABLE vip_callers (
    id SERIAL PRIMARY KEY,
    caller_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    priority_level INTEGER DEFAULT 1,
    notes TEXT,
    special_routing VARCHAR(50),
    skip_queue BOOLEAN DEFAULT FALSE,
    direct_extension VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_caller_id ON vip_callers(caller_id);
CREATE INDEX idx_priority ON vip_callers(priority_level);
CREATE INDEX idx_special_routing ON vip_callers(special_routing);

-- Grant table privileges to pbx_user
GRANT ALL PRIVILEGES ON TABLE vip_callers TO pbx_user;
GRANT USAGE, SELECT ON SEQUENCE vip_callers_id_seq TO pbx_user;

-- Create Call Detail Records (CDR) table
CREATE TABLE call_records (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(100) UNIQUE NOT NULL,
    from_extension VARCHAR(20) NOT NULL,
    to_extension VARCHAR(20) NOT NULL,
    caller_id VARCHAR(50),
    start_time TIMESTAMP NOT NULL,
    answer_time TIMESTAMP,
    end_time TIMESTAMP,
    duration INTEGER,  -- in seconds
    disposition VARCHAR(20),  -- ANSWERED, NO_ANSWER, BUSY, FAILED
    recording_file VARCHAR(255),
    cost DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for CDR
CREATE INDEX idx_call_id ON call_records(call_id);
CREATE INDEX idx_from_ext ON call_records(from_extension);
CREATE INDEX idx_to_ext ON call_records(to_extension);
CREATE INDEX idx_start_time ON call_records(start_time);
CREATE INDEX idx_disposition ON call_records(disposition);

-- Grant privileges
GRANT ALL PRIVILEGES ON TABLE call_records TO pbx_user;
GRANT USAGE, SELECT ON SEQUENCE call_records_id_seq TO pbx_user;

-- Create voicemail metadata table
CREATE TABLE voicemail_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(100) UNIQUE NOT NULL,
    extension VARCHAR(20) NOT NULL,
    caller_id VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    duration INTEGER,  -- in seconds
    file_path VARCHAR(500),
    listened BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE,
    transcription TEXT,  -- Future: voice-to-text transcription
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_vm_extension ON voicemail_messages(extension);
CREATE INDEX idx_vm_timestamp ON voicemail_messages(timestamp);
CREATE INDEX idx_vm_listened ON voicemail_messages(listened);

-- Grant privileges
GRANT ALL PRIVILEGES ON TABLE voicemail_messages TO pbx_user;
GRANT USAGE, SELECT ON SEQUENCE voicemail_messages_id_seq TO pbx_user;

-- Create extension settings table (for per-extension preferences)
CREATE TABLE extension_settings (
    id SERIAL PRIMARY KEY,
    extension VARCHAR(20) UNIQUE NOT NULL,
    call_forwarding_enabled BOOLEAN DEFAULT FALSE,
    forward_to VARCHAR(20),
    do_not_disturb BOOLEAN DEFAULT FALSE,
    voicemail_pin VARCHAR(10),
    voicemail_greeting VARCHAR(255),  -- Path to custom greeting
    max_concurrent_calls INTEGER DEFAULT 1,
    allow_external BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index
CREATE INDEX idx_ext_settings ON extension_settings(extension);

-- Grant privileges
GRANT ALL PRIVILEGES ON TABLE extension_settings TO pbx_user;
GRANT USAGE, SELECT ON SEQUENCE extension_settings_id_seq TO pbx_user;

-- Create function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE TRIGGER update_vip_callers_updated_at
    BEFORE UPDATE ON vip_callers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_extension_settings_updated_at
    BEFORE UPDATE ON extension_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Exit PostgreSQL
\q
```

### Configure PostgreSQL for Network Access (if needed)
```bash
# Edit PostgreSQL configuration
sudo vim /etc/postgresql/16/main/postgresql.conf

# Find and modify:
# listen_addresses = 'localhost'  # Change to '*' for all interfaces
# port = 5432

# Edit client authentication
sudo vim /etc/postgresql/16/main/pg_hba.conf

# Add this line for local network access (example):
# host    pbx_system    pbx_user    192.168.1.0/24    scram-sha-256

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Test Database Connection
```bash
# Test connection as pbx_user
psql -h localhost -U pbx_user -d pbx_system -W

# You'll be prompted for password
# Once connected, test:
\dt  # List tables
\q   # Exit
```

---

## Python Environment Setup

### Install Python 3.12 (Ubuntu 24.04 default)
```bash
# Check Python version
python3 --version
# Should show: Python 3.12.x

# Install pip and venv
sudo apt install -y python3-pip python3-venv python3-dev
```

### Create Virtual Environment (Recommended)
```bash
# Navigate to PBX directory
cd /home/runner/work/PBX/PBX

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Install PBX Requirements
```bash
# Install base requirements (includes psycopg2-binary for PostgreSQL)
pip install -r requirements.txt

# Install additional optional dependencies as needed:

# For LDAP support (Active Directory integration)
pip install ldap3 pyasn1

# For DTMF detection
pip install scipy numpy

# For API integrations (Microsoft 365, Zoom, etc.)
pip install msal requests PyJWT python-dateutil

# For database ORM (if needed)
pip install sqlalchemy

# Save all installed packages for reference
pip freeze > requirements-full.txt
```

### Create systemd Service (to run PBX on boot)
```bash
# Create service file
sudo vim /etc/systemd/system/pbx.service
```

Add this content:
```ini
[Unit]
Description=InHouse PBX System
After=network.target postgresql.service

[Service]
Type=simple
User=pbxuser
Group=pbxuser
WorkingDirectory=/home/runner/work/PBX/PBX
Environment="PATH=/home/runner/work/PBX/PBX/venv/bin"
ExecStart=/home/runner/work/PBX/PBX/venv/bin/python /home/runner/work/PBX/PBX/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable pbx.service

# Start service
sudo systemctl start pbx.service

# Check status
sudo systemctl status pbx.service

# View logs
sudo journalctl -u pbx.service -f
```

---

## Database Schemas

### Database Initialization Script
The database initialization script is included in the repository at `scripts/init_database.py`. This script will:
- Test the PostgreSQL connection
- Verify all required tables exist
- Add sample VIP caller data for testing

#### Configure Database Credentials

The script supports two methods for configuring database credentials:

**Method 1: Environment Variables (Recommended for Production)**
```bash
# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=pbx_system
export DB_USER=pbx_user
export DB_PASSWORD=YourSecurePassword123!
```

**Method 2: Edit the Script Directly (For Testing)**
```bash
# Edit the script and update the DB_CONFIG default values
vim /home/runner/work/PBX/PBX/scripts/init_database.py
# Change the password in the 'password' field (line ~18)
```

#### Run the Initialization Script
```bash
# Navigate to PBX directory
cd /home/runner/work/PBX/PBX

# Make the script executable (if not already)
chmod +x scripts/init_database.py

# Run the script
python3 scripts/init_database.py
```

---

## Active Directory Integration Setup

### Install LDAP Client Tools
```bash
# Install LDAP utilities
sudo apt install -y ldap-utils

# Install Python LDAP library
pip install ldap3 pyasn1
```

### Test LDAP Connection (if you have Active Directory)
```bash
# Test connection to AD server
ldapsearch -x -H ldap://dc.domain.local:389 \
  -D "CN=svc-pbx,OU=Service Accounts,DC=domain,DC=local" \
  -W -b "DC=domain,DC=local" \
  "(objectClass=user)" sAMAccountName displayName mail

# For LDAPS (secure):
ldapsearch -x -H ldaps://dc.domain.local:636 \
  -D "CN=svc-pbx,OU=Service Accounts,DC=domain,DC=local" \
  -W -b "DC=domain,DC=local" \
  "(objectClass=user)" sAMAccountName
```

### Configure PBX for Active Directory
Edit `config.yml`:
```yaml
integrations:
  active_directory:
    enabled: true
    server: "ldaps://dc.yourdomain.local:636"
    base_dn: "DC=yourdomain,DC=local"
    bind_dn: "CN=svc-pbx,OU=Service Accounts,DC=yourdomain,DC=local"
    bind_password: "YourADServiceAccountPassword"
    use_ssl: true
    user_search_base: "OU=Users,DC=yourdomain,DC=local"
    sync_interval: 3600  # Sync every hour
```

---

## SMTP Configuration

### Option 1: Using Gmail (for testing)
Edit `config.yml`:
```yaml
voicemail:
  email_notifications: true
  smtp:
    host: "smtp.gmail.com"
    port: 587
    use_tls: true
    username: "your-gmail@gmail.com"
    password: "your-app-specific-password"  # Generate at myaccount.google.com
  email:
    from_address: "pbx-voicemail@yourdomain.com"
    from_name: "PBX Voicemail System"
```

### Option 2: Using Local Postfix (recommended for production)
```bash
# Install Postfix
sudo apt install -y postfix

# During installation, select "Internet Site"
# Set system mail name (e.g., pbx.yourdomain.com)

# Configure Postfix
sudo vim /etc/postfix/main.cf

# Add/modify these lines:
# myhostname = pbx.yourdomain.com
# mydomain = yourdomain.com
# myorigin = $mydomain
# inet_interfaces = all
# mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain

# Restart Postfix
sudo systemctl restart postfix
sudo systemctl enable postfix

# Test sending email
echo "Test email from PBX" | mail -s "Test" your-email@example.com
```

Configure PBX to use local Postfix:
```yaml
voicemail:
  smtp:
    host: "localhost"
    port: 25
    use_tls: false
    username: ""
    password: ""
```

### Option 3: Using Office 365 SMTP
```yaml
voicemail:
  smtp:
    host: "smtp.office365.com"
    port: 587
    use_tls: true
    username: "pbx@yourdomain.com"
    password: "YourOffice365Password"
```

### Test SMTP Configuration
```bash
# Create test script
cat > /tmp/test_smtp.py << 'EOF'
import smtplib
from email.mime.text import MIMEText

# Configure these
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-gmail@gmail.com"
SMTP_PASS = "your-app-password"
FROM_ADDR = "pbx@yourdomain.com"
TO_ADDR = "test@example.com"

msg = MIMEText("Test email from PBX system")
msg['Subject'] = "PBX Test Email"
msg['From'] = FROM_ADDR
msg['To'] = TO_ADDR

try:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASS)
    server.send_message(msg)
    server.quit()
    print("✓ Email sent successfully!")
except Exception as e:
    print(f"✗ Email failed: {e}")
EOF

python3 /tmp/test_smtp.py
```

---

## Audio Tools Installation

### Install FFmpeg (for audio conversion)
```bash
# Install FFmpeg
sudo apt install -y ffmpeg

# Verify installation
ffmpeg -version
```

### Install SoX (Sound eXchange)
```bash
# Install SoX
sudo apt install -y sox libsox-fmt-all

# Verify installation
sox --version
```

### Create Audio Prompts Directory
```bash
# Create directories
mkdir -p /home/runner/work/PBX/PBX/voicemail/prompts
mkdir -p /home/runner/work/PBX/PBX/moh

# Set permissions
chmod 755 /home/runner/work/PBX/PBX/voicemail/prompts
```

### Convert Audio Files to PBX Format
```bash
# General format: Replace YOUR_AUDIO_FILE.wav and YOUR_OUTPUT_FILE.wav with your actual files
# ffmpeg -i YOUR_AUDIO_FILE.wav -ar 8000 -ac 1 -acodec pcm_mulaw YOUR_OUTPUT_FILE.wav

# Example 1: Convert a WAV file to PBX format
# ffmpeg -i myaudio.wav -ar 8000 -ac 1 -acodec pcm_mulaw pbx-ready.wav

# Example 2: Convert MP3 to PBX format
ffmpeg -i music.mp3 -ar 8000 -ac 1 -acodec pcm_mulaw hold-music.wav

# Example 3: Batch convert all MP3 files in directory
for file in *.mp3; do
    ffmpeg -i "$file" -ar 8000 -ac 1 -acodec pcm_mulaw "${file%.mp3}.wav"
done
```

### Create Simple Beep Tone
```bash
# Generate 1-second beep at 1000Hz
sox -n -r 8000 -c 1 beep.wav synth 1 sine 1000

# Convert to μ-law
ffmpeg -i beep.wav -ar 8000 -ac 1 -acodec pcm_mulaw /home/runner/work/PBX/PBX/voicemail/prompts/beep.wav
```

---

## Network Configuration

### Configure Firewall (UFW)
```bash
# Install UFW if not already installed
sudo apt install -y ufw

# Allow SSH (important!)
sudo ufw allow 22/tcp

# Allow SIP signaling
sudo ufw allow 5060/udp
sudo ufw allow 5060/tcp
sudo ufw allow 5061/tcp  # SIP TLS

# Allow RTP media (adjust range as needed)
sudo ufw allow 10000:20000/udp

# Allow HTTP API
sudo ufw allow 8080/tcp

# Allow HTTPS (for future SSL)
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### Configure Network Parameters
```bash
# Edit sysctl for network optimization
sudo vim /etc/sysctl.conf

# Add these lines at the end:
```

```
# Network optimization for VoIP
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.udp_rmem_min = 8192
net.ipv4.udp_wmem_min = 8192
net.core.netdev_max_backlog = 5000

# Increase local port range
net.ipv4.ip_local_port_range = 1024 65535

# Enable IP forwarding (if needed for SIP routing)
# net.ipv4.ip_forward = 1
```

Apply changes:
```bash
# Apply sysctl changes
sudo sysctl -p
```

### Set Static IP (optional but recommended)
```bash
# Edit netplan configuration
sudo vim /etc/netplan/00-installer-config.yaml
```

Example configuration:
```yaml
network:
  version: 2
  ethernets:
    eth0:  # or your interface name
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Apply network configuration:
```bash
sudo netplan apply
```

### Configure DNS
```bash
# Edit resolved.conf
sudo vim /etc/systemd/resolved.conf

# Add/modify:
# DNS=8.8.8.8 8.8.4.4
# FallbackDNS=1.1.1.1

# Restart systemd-resolved
sudo systemctl restart systemd-resolved
```

---

## Service Configuration

### Update PBX Configuration
Edit `/home/runner/work/PBX/PBX/config.yml`:

```yaml
# Server configuration
server:
  sip_host: 0.0.0.0
  sip_port: 5060
  external_ip: YOUR_PUBLIC_IP  # Or internal IP like 192.168.1.100
  rtp_port_range_start: 10000
  rtp_port_range_end: 20000

# API configuration
api:
  host: 0.0.0.0
  port: 8080

# Database configuration
database:
  host: localhost
  port: 5432
  name: pbx_system
  user: pbx_user
  password: YourSecurePassword123!
  
# Logging
logging:
  level: INFO
  file: logs/pbx.log
  console: true
  max_file_size: 10485760  # 10MB
  backup_count: 5

# VoIP Features
features:
  call_recording: true
  call_transfer: true
  call_hold: true
  conference: true
  voicemail: true
  call_parking: true
  call_queues: true
  presence: true
  music_on_hold: true

# Voicemail configuration
voicemail:
  storage_path: voicemail
  email_notifications: true
  no_answer_timeout: 30
  max_message_duration: 180
  smtp:
    host: localhost
    port: 25
    use_tls: false
    username: ""
    password: ""
  email:
    from_address: 'pbx@yourdomain.com'
    from_name: 'PBX Voicemail System'
    include_attachment: true
```

### Create Log Directory
```bash
# Create logs directory
mkdir -p /home/runner/work/PBX/PBX/logs

# Set permissions
chmod 755 /home/runner/work/PBX/PBX/logs
```

### Configure Log Rotation
```bash
# Create logrotate configuration
sudo vim /etc/logrotate.d/pbx
```

Add this content:
```
/home/runner/work/PBX/PBX/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 pbxuser pbxuser
    sharedscripts
    postrotate
        systemctl reload pbx.service > /dev/null 2>&1 || true
    endscript
}
```

---

## Testing

### Test Database Connection
```bash
# Run database initialization script
cd /home/runner/work/PBX/PBX

# Set database credentials (or edit scripts/init_database.py directly)
export DB_PASSWORD='YourSecurePassword123!'

# Run the script
python3 scripts/init_database.py
```

Expected output:
```
============================================================
PBX Database Initialization
============================================================
✓ Connected to PostgreSQL
  Version: PostgreSQL 16.x ...
============================================================
✓ Table 'vip_callers' exists
✓ Table 'call_records' exists
✓ Table 'voicemail_messages' exists
✓ Table 'extension_settings' exists
============================================================
✓ Added 3 sample VIP callers
✅ Database initialization complete!
```

### Test PBX Startup
```bash
# Start PBX manually (in virtual environment)
cd /home/runner/work/PBX/PBX
source venv/bin/activate
python3 main.py
```

Expected output:
```
============================================================
InHouse PBX System v1.0.0
============================================================
2025-12-04 12:00:00 - PBX - INFO - FIPS 140-2 compliant encryption enabled
2025-12-04 12:00:00 - PBX - INFO - Loaded extension 1001 (...)
...
2025-12-04 12:00:00 - PBX - INFO - SIP server started on 0.0.0.0:5060
2025-12-04 12:00:00 - PBX - INFO - API server started on http://0.0.0.0:8080
2025-12-04 12:00:00 - PBX - INFO - PBX system started successfully

PBX system is running...
Press Ctrl+C to stop
```

### Test Ctrl+C Shutdown
Press Ctrl+C and verify:
```
^C
Shutting down PBX system...
2025-12-04 12:01:00 - PBX - INFO - Stopping PBX system...
2025-12-04 12:01:00 - PBX - INFO - API server stopped
2025-12-04 12:01:00 - PBX - INFO - SIP server stopped
2025-12-04 12:01:00 - PBX - INFO - PBX system stopped
PBX system shutdown complete
```

### Test API Endpoint
```bash
# Test API status endpoint
curl http://localhost:8080/api/status

# Expected response:
# {"running": true, "registered_extensions": 0, "active_calls": 0, ...}
```

### Test Database Queries
```bash
# Query VIP callers
psql -h localhost -U pbx_user -d pbx_system -c "SELECT * FROM vip_callers;"

# Query call records (should be empty initially)
psql -h localhost -U pbx_user -d pbx_system -c "SELECT COUNT(*) FROM call_records;"
```

---

## Troubleshooting

### PostgreSQL Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Test connection manually
psql -h localhost -U pbx_user -d pbx_system -W
```

### PBX Service Issues
```bash
# Check service status
sudo systemctl status pbx.service

# View logs
sudo journalctl -u pbx.service -n 100 --no-pager

# Restart service
sudo systemctl restart pbx.service
```

### Network/Firewall Issues
```bash
# Check if ports are listening
sudo netstat -tulpn | grep -E '(5060|8080|5432)'

# Test SIP port
sudo nc -u -l 5060

# Check firewall rules
sudo ufw status verbose
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R pbxuser:pbxuser /home/runner/work/PBX/PBX

# Fix permissions
chmod +x /home/runner/work/PBX/PBX/main.py
```

---

## Backup and Maintenance

### Database Backup Script
```bash
# Create backup script
cat > /home/runner/work/PBX/PBX/scripts/backup_database.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/runner/work/PBX/PBX/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump -h localhost -U pbx_user -d pbx_system > "$BACKUP_DIR/pbx_backup_$DATE.sql"

# Compress backup
gzip "$BACKUP_DIR/pbx_backup_$DATE.sql"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "pbx_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: pbx_backup_$DATE.sql.gz"
EOF

chmod +x /home/runner/work/PBX/PBX/scripts/backup_database.sh
```

### Schedule Daily Backup
```bash
# Add to crontab
crontab -e

# Add this line (backup at 2 AM daily):
0 2 * * * /home/runner/work/PBX/PBX/scripts/backup_database.sh >> /home/runner/work/PBX/PBX/logs/backup.log 2>&1
```

### Restore Database
```bash
# Restore from backup
gunzip -c /home/runner/work/PBX/PBX/backups/pbx_backup_YYYYMMDD_HHMMSS.sql.gz | \
  psql -h localhost -U pbx_user -d pbx_system
```

---

## Next Steps

1. **Start the PBX service**: `sudo systemctl start pbx.service`
2. **Configure your SIP phones** to register to the PBX server
3. **Test call functionality** between extensions
4. **Set up voicemail** and test voicemail-to-email
5. **Add VIP callers** to the database
6. **Configure integrations** (AD, Outlook, etc.) as needed
7. **Review logs** regularly: `sudo journalctl -u pbx.service -f`

Refer to `IMPLEMENTATION_GUIDE.md` for implementing additional features like Zoom, Teams, and Active Directory integrations.
