# Production Deployment Guide (Step-by-Step)

**Last Updated**: January 2, 2026  
**Version**: 1.0.0  
**Audience**: System Administrators, DevOps Engineers

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Application Deployment](#application-deployment)
4. [Post-Deployment Validation](#post-deployment-validation)
5. [Monitoring Setup](#monitoring-setup)
6. [Backup Configuration](#backup-configuration)
7. [Go-Live Checklist](#go-live-checklist)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Planning Phase

- [ ] **Capacity Planning Completed**
  ```bash
  # Run capacity calculator
  python3 scripts/capacity_calculator.py \
    --extensions 100 \
    --concurrent-calls 25 \
    --recording
  ```
  Document the results and provision accordingly.

- [ ] **Infrastructure Provisioned**
  - [ ] Server/VM with required specifications
  - [ ] Static IP address assigned
  - [ ] DNS records configured (A, PTR, optional SRV)
  - [ ] Firewall rules prepared
  - [ ] Load balancer configured (if HA)

- [ ] **Network Configuration Ready**
  - [ ] VLANs configured for voice traffic (optional but recommended)
  - [ ] QoS/DSCP markings configured on network equipment
  - [ ] SIP trunk credentials obtained (if applicable)
  - [ ] E911 location information prepared

- [ ] **Credentials & Secrets Prepared**
  - [ ] Database password (strong, 20+ characters)
  - [ ] API admin password
  - [ ] SMTP credentials for email notifications
  - [ ] Integration credentials (AD, Zoom, etc.)
  - [ ] SSL certificate (or Let's Encrypt ready)

- [ ] **Stakeholder Communication**
  - [ ] Deployment window scheduled
  - [ ] Users notified of upcoming change
  - [ ] Rollback plan documented
  - [ ] On-call engineer assigned

---

## Infrastructure Setup

### Step 1: Provision Server

**Recommended Specifications** (for 100 users, 25 concurrent calls):
- **OS**: Ubuntu 24.04 LTS
- **CPU**: 4 vCPUs
- **RAM**: 16 GB
- **Disk**: 100 GB SSD
- **Network**: 1 Gbps, static IP

**Provision Server**:
```bash
# If using cloud provider (AWS, DigitalOcean, etc.)
# Create instance via console or CLI

# If using bare metal/VM
# Install Ubuntu 24.04 LTS from ISO
```

### Step 2: Initial Server Configuration

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Set hostname
sudo hostnamectl set-hostname pbx.yourdomain.com

# Configure timezone
sudo timedatectl set-timezone America/New_York  # Adjust as needed

# Install NTP for time synchronization
sudo apt-get install -y systemd-timesyncd
sudo systemctl enable systemd-timesyncd
sudo systemctl start systemd-timesyncd
```

### Step 3: Configure Firewall

```bash
# Install UFW firewall
sudo apt-get install -y ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (IMPORTANT: Do this before enabling firewall!)
sudo ufw allow 22/tcp

# Allow SIP
sudo ufw allow 5060/udp

# Allow RTP
sudo ufw allow 10000:20000/udp

# Allow HTTPS (API)
sudo ufw allow 8080/tcp
# Or if using reverse proxy:
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Verify rules
sudo ufw status verbose
```

### Step 4: Install PostgreSQL

```bash
# Install PostgreSQL 14+
sudo apt-get install -y postgresql postgresql-contrib

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE pbx_system;
CREATE USER pbx_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;
ALTER DATABASE pbx_system OWNER TO pbx_user;
\q
EOF

# Verify connection
psql -h localhost -U pbx_user -d pbx_system -c "SELECT 1;"
```

### Step 5: Install System Dependencies

```bash
# Install required packages
sudo apt-get install -y \
  python3.12 \
  python3.12-venv \
  python3-pip \
  espeak \
  ffmpeg \
  libopus-dev \
  portaudio19-dev \
  libspeex-dev \
  git \
  nginx \
  certbot \
  python3-certbot-nginx
```

---

## Application Deployment

### Step 1: Create Application User

```bash
# Create dedicated user for PBX
sudo useradd -r -s /bin/bash -d /opt/pbx -m pbx

# Add to required groups
sudo usermod -aG audio pbx
```

### Step 2: Clone Repository

```bash
# Clone repository
sudo -u pbx git clone https://github.com/mattiIce/PBX.git /opt/pbx/

# Change to PBX directory
cd /opt/pbx
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
sudo -u pbx python3 -m venv /opt/pbx/venv

# Activate virtual environment
sudo -u pbx /opt/pbx/venv/bin/pip install --upgrade pip

# Install dependencies
sudo -u pbx /opt/pbx/venv/bin/pip install -r requirements.txt
```

### Step 4: Configure Application

```bash
# Copy configuration templates
sudo -u pbx cp /opt/pbx/.env.example /opt/pbx/.env
sudo -u pbx cp /opt/pbx/config.yml /opt/pbx/config.prod.yml

# Edit .env file
sudo -u pbx nano /opt/pbx/.env
```

**Critical `.env` settings**:
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pbx_system
DB_USER=pbx_user
DB_PASSWORD=your_secure_password_here

# Email
SMTP_HOST=smtp.yourserver.com
SMTP_PORT=587
SMTP_USERNAME=pbx@yourdomain.com
SMTP_PASSWORD=your_smtp_password
```

**Edit `config.prod.yml`**:
```bash
sudo -u pbx nano /opt/pbx/config.prod.yml
```

Key settings:
- `external_ip`: Your server's public IP
- `sip_port`: 5060 (default)
- `rtp_port_range`: [10000, 20000]
- `max_calls`: Based on capacity planning
- Extensions configuration

### Step 5: Initialize Database

```bash
# Run database initialization
sudo -u pbx /opt/pbx/venv/bin/python /opt/pbx/scripts/init_database.py

# Verify tables created
psql -h localhost -U pbx_user -d pbx_system -c "\dt"
```

### Step 6: Generate Voice Prompts

```bash
# Generate TTS prompts
sudo -u pbx /opt/pbx/venv/bin/python /opt/pbx/scripts/generate_tts_prompts.py

# Verify prompts
ls -lh /opt/pbx/voicemail_prompts/
```

### Step 7: Configure SSL Certificate

**Option A: Let's Encrypt (Recommended)**
```bash
# Using our automated script
sudo -u pbx /opt/pbx/venv/bin/python /opt/pbx/scripts/letsencrypt_manager.py \
  --domain pbx.yourdomain.com \
  --email admin@yourdomain.com \
  --install-certbot \
  --obtain \
  --setup-auto-renewal
```

**Option B: Existing Certificate**
```bash
# Copy certificate files
sudo cp your_certificate.crt /opt/pbx/ssl/server.crt
sudo cp your_private_key.key /opt/pbx/ssl/server.key
sudo chown pbx:pbx /opt/pbx/ssl/*
sudo chmod 644 /opt/pbx/ssl/server.crt
sudo chmod 600 /opt/pbx/ssl/server.key
```

### Step 8: Install Systemd Service

```bash
# Copy service file
sudo cp /opt/pbx/pbx.service /etc/systemd/system/

# Edit if needed
sudo nano /etc/systemd/system/pbx.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable pbx

# Start service
sudo systemctl start pbx

# Check status
sudo systemctl status pbx
```

### Step 9: Configure Nginx Reverse Proxy (Optional)

```bash
# Copy nginx configuration
sudo cp /opt/pbx/apache-pbx.conf.example /etc/nginx/sites-available/pbx

# Edit configuration
sudo nano /etc/nginx/sites-available/pbx

# Enable site
sudo ln -s /etc/nginx/sites-available/pbx /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## Post-Deployment Validation

### Step 1: Run Production Validation

```bash
# Run validation script
python3 /opt/pbx/scripts/validate_production_readiness.py

# Address any failed checks
```

### Step 2: Run Smoke Tests

```bash
# Run smoke tests
python3 /opt/pbx/scripts/smoke_tests.py

# All critical tests must pass
```

### Step 3: Verify Core Functionality

```bash
# Check service is running
sudo systemctl status pbx

# Check logs for errors
sudo tail -100 /var/log/pbx/pbx.log

# Test API
curl -k https://localhost:8080/health

# Check registered extensions
curl -k https://localhost:8080/api/extensions/registered
```

### Step 4: Test a Call

1. **Register a SIP phone** to extension 1001
2. **Register another SIP phone** to extension 1002
3. **Make a test call** from 1001 to 1002
4. **Verify call quality** (clear audio, no delays)
5. **Test call features**:
   - Hold
   - Transfer
   - Conference (if needed)
   - Voicemail

### Step 5: Run Performance Benchmark

```bash
# Run benchmark
python3 /opt/pbx/scripts/benchmark_performance.py \
  --save /tmp/baseline-benchmark.json

# Review score (should be >75)
```

---

## Monitoring Setup

### Step 1: Configure Prometheus (Optional)

```bash
# Install Prometheus
# See: https://prometheus.io/download/

# Add PBX scrape config to prometheus.yml
scrape_configs:
  - job_name: 'pbx'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
```

### Step 2: Import Grafana Dashboards

```bash
# Import dashboard
# Copy from grafana/dashboards/pbx-overview.json
# Import in Grafana UI
```

### Step 3: Configure Health Monitoring

```bash
# Add cron job for health checks
sudo crontab -e

# Add line:
*/15 * * * * /opt/pbx/venv/bin/python /opt/pbx/scripts/health_monitor.py --format json > /var/log/pbx/health.json
```

---

## Backup Configuration

### Step 1: Configure Automated Backups

```bash
# Test backup script
sudo bash /opt/pbx/scripts/backup.sh --full

# Add to cron (daily at 2 AM)
sudo crontab -e

# Add line:
0 2 * * * /opt/pbx/scripts/backup.sh --full >> /var/log/pbx/backup.log 2>&1
```

### Step 2: Configure Off-Site Backup (Optional)

```bash
# Edit backup script to add S3 credentials
sudo nano /opt/pbx/scripts/backup.sh

# Set:
S3_BUCKET="your-bucket-name"
AWS_ACCESS_KEY_ID="your-key"
AWS_SECRET_ACCESS_KEY="your-secret"
```

### Step 3: Test Restore

```bash
# Test database restore
# See OPERATIONS_MANUAL.md
```

---

## Go-Live Checklist

### Final Pre-Launch Checks

- [ ] All smoke tests passing
- [ ] Performance benchmark score >75
- [ ] SSL certificate valid and not expiring soon
- [ ] Backups configured and tested
- [ ] Monitoring dashboards accessible
- [ ] On-call engineer ready
- [ ] Rollback plan documented

### Launch Steps

1. **Notify users** of go-live
2. **Monitor closely** for first hour
3. **Run health checks** every 15 minutes
4. **Review logs** for errors
5. **Test critical features**
6. **Document any issues**

### Post-Launch

- [ ] Day 1 review completed
- [ ] Week 1 review scheduled
- [ ] Performance baseline documented
- [ ] User feedback collected

---

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
sudo journalctl -u pbx -n 50

# Check permissions
ls -l /opt/pbx

# Check configuration
python3 -c "import yaml; yaml.safe_load(open('/opt/pbx/config.prod.yml'))"
```

**Phones won't register:**
```bash
# Check SIP port
sudo netstat -tulpn | grep 5060

# Check firewall
sudo ufw status

# Check logs
grep -i "registration" /var/log/pbx/pbx.log
```

**Poor call quality:**
```bash
# Run QoS diagnostics
python3 /opt/pbx/scripts/diagnose_qos.py

# Check network
ping -c 100 <sip_trunk_provider>
```

See **PRODUCTION_RUNBOOK.md** for detailed troubleshooting procedures.

---

**Last Updated**: January 2, 2026  
**Version**: 1.0.0
