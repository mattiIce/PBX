# Production Deployment Guide

This comprehensive guide covers everything from pre-deployment planning through post-deployment verification. Use this as your single source of truth for production PBX deployments.

## Table of Contents
- [Pre-Deployment Checks](#pre-deployment-checks)
- [Installation Steps](#installation-steps)
- [Post-Deployment Setup](#post-deployment-setup)
- [Auto Attendant Configuration](#auto-attendant-configuration)
- [Post-Deployment Verification](#post-deployment-verification)
- [Production Monitoring](#production-monitoring)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Security Hardening](#security-hardening)
- [Compliance](#compliance)
- [Go-Live Checklist](#go-live-checklist)

---

## Pre-Deployment Checks

### Infrastructure Requirements
- [ ] Server meets minimum requirements (4GB RAM, 2 CPU cores, 50GB disk)
- [ ] Operating system is updated (Ubuntu 24.04 LTS recommended)
- [ ] Python 3.8+ is installed
- [ ] PostgreSQL 12+ is installed and running (for production)
- [ ] Network ports are available (5060 UDP, 10000-20000 UDP, 8080 TCP)

### Security Hardening
- [ ] Firewall is configured (UFW or iptables)
- [ ] Only required ports are open
- [ ] SSH is secured (key-based auth, non-standard port)
- [ ] Fail2ban or similar is installed for intrusion prevention
- [ ] SSL/TLS certificates are obtained and configured
- [ ] HTTPS is enabled for API endpoints
- [ ] Strong passwords are set for all extensions
- [ ] Database password is secure and stored in environment variables
- [ ] FIPS mode is enabled (if required for compliance)

### Configuration Validation
- [ ] Run configuration validator: `python -c "from pbx.utils.config_validator import validate_config_on_startup; from pbx.utils.config import Config; validate_config_on_startup(Config('config.yml').config)"`
- [ ] External IP is set correctly in config.yml
- [ ] SIP trunk configuration is tested
- [ ] Voicemail-to-email SMTP settings are configured
- [ ] Database connection string is correct
- [ ] Extension numbers don't conflict
- [ ] No default/example values remain in config

## Installation Steps

### 1. Install System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y postgresql nginx ufw fail2ban
sudo apt-get install -y espeak ffmpeg libopus-dev portaudio19-dev
```

### 2. Setup Database
```bash
# Create database and user
sudo -u postgres createdb pbx_system
sudo -u postgres psql -c "CREATE USER pbx_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;"

# Test connection
psql -h localhost -U pbx_user -d pbx_system -c "SELECT version();"
```

### 3. Configure Environment Variables
```bash
# Create .env file
cp .env.example .env

# Edit with secure values
nano .env

# Set permissions
chmod 600 .env
```

Required environment variables:
- `DB_HOST=localhost`
- `DB_PORT=5432`
- `DB_NAME=pbx_system`
- `DB_USER=pbx_user`
- `DB_PASSWORD=<secure_password>`

### 4. Install PBX System
```bash
# Clone repository
git clone https://github.com/mattiIce/PBX.git
cd PBX

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Generate SSL certificates (production)
python scripts/generate_ssl_cert.py --hostname pbx.yourcompany.com
# OR use Let's Encrypt
sudo certbot certonly --standalone -d pbx.yourcompany.com
```

### 5. Initialize Database
```bash
source venv/bin/activate
python scripts/init_database.py
python scripts/seed_extensions.py
```

### 6. Generate Voice Prompts
```bash
# Generate with gTTS (best quality, requires internet)
python scripts/generate_tts_prompts.py --company "Your Company Name"

# Verify files were created
ls -lh auto_attendant/*.wav voicemail_prompts/*.wav
```

### 7. Configure Firewall
```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow SIP signaling
sudo ufw allow 5060/udp

# Allow RTP media
sudo ufw allow 10000:20000/udp

# Allow HTTPS (if using reverse proxy)
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable

# Verify
sudo ufw status
```

### 8. Setup Systemd Service
```bash
# Copy service file
sudo cp pbx.service /etc/systemd/system/

# Edit service file with correct paths
sudo nano /etc/systemd/system/pbx.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable pbx

# Start service
sudo systemctl start pbx

# Check status
sudo systemctl status pbx
```

### 9. Configure Reverse Proxy (Optional but Recommended)
```bash
# Install nginx
sudo apt-get install nginx

# Configure reverse proxy
sudo bash scripts/setup_reverse_proxy.sh

# Or use Let's Encrypt with certbot
sudo certbot --nginx -d pbx.yourcompany.com
```

---

## Post-Deployment Setup

### 🔐 CRITICAL: First Steps (Do These Now)

#### 1. Update Database Password

During automated deployment, a random database password was generated. If you deployed manually or need to change it:

```bash
# Generate a new password
NEW_PASSWORD=$(openssl rand -base64 32)
echo "New password: $NEW_PASSWORD"

# Update PostgreSQL
sudo -u postgres psql -c "ALTER USER pbxuser WITH PASSWORD '$NEW_PASSWORD';"
```

**Then update your config.yml:**

```bash
cd /path/to/PBX
nano config.yml
```

Update the database section:
```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  name: pbx
  user: pbxuser
  password: "YOUR_NEW_PASSWORD_HERE"  # ← Update this
```

#### 2. Initialize the Database

```bash
# Activate virtual environment
cd /path/to/PBX
source venv/bin/activate

# Initialize database schema
python scripts/init_database.py

# Seed initial extensions
python scripts/seed_extensions.py

# Verify extensions
python scripts/list_extensions_from_db.py
```

#### 3. Generate Voice Prompts (REQUIRED)

Voice files are **NOT** included in the repository. You **MUST** generate them:

**Option A: Google TTS (RECOMMENDED - Best Quality)**

```bash
# Install dependencies
pip install gTTS pydub
sudo apt-get install ffmpeg

# Generate voice prompts
python scripts/generate_tts_prompts.py --company "Your Company Name"

# Verify files created (should see 17 files)
ls -lh auto_attendant/*.wav voicemail_prompts/*.wav
```

**Option B: Festival (Good Quality, Offline)**

If no internet or gTTS fails:

```bash
sudo apt-get install festival festvox-us-slt-hts ffmpeg
python scripts/generate_espeak_voices.py --engine festival
```

**Option C: eSpeak (Basic Quality, Offline)**

Last resort if others fail:

```bash
sudo apt-get install espeak ffmpeg
python scripts/generate_espeak_voices.py
```

See [Auto Attendant Configuration](#auto-attendant-configuration) below for detailed auto attendant setup.

#### 4. Start the PBX Service

```bash
# Start the service
sudo systemctl start pbx

# Check status
sudo systemctl status pbx

# View live logs
sudo journalctl -u pbx -f
```

### Essential Documentation (Read in Order)

After deployment, review these guides:

1. **[QUICK_START.md](QUICK_START.md)** - Basic configuration checklist (5 minutes)
2. **[ENV_SETUP_GUIDE.md](ENV_SETUP_GUIDE.md)** - Environment variables setup (5 minutes)
3. **[VOICEMAIL_DATABASE_SETUP.md](VOICEMAIL_DATABASE_SETUP.md)** - Database-backed extensions (10 minutes)
4. **[SECURITY_GUIDE.md](SECURITY_GUIDE.md)** - Security hardening (20 minutes)
5. **[HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)** - SSL/TLS configuration (15 minutes)

### Common Configuration Tasks

#### Add Extensions

```bash
# Use the API
curl -X POST http://localhost:8080/api/extensions \
  -H "Content-Type: application/json" \
  -d '{"number":"1005","name":"John Doe","email":"john@company.com","password":"securepass123","allow_external":true}'

# Or use the admin panel at: https://your-domain/admin/
```

#### Configure Email for Voicemail

Edit `config.yml`:
```yaml
voicemail:
  email_notifications: true
  smtp:
    host: "smtp.gmail.com"
    port: 587
    use_tls: true
    username: "your-email@gmail.com"
    password: "your-app-password"
  email:
    from_address: "pbx@yourcompany.com"
    from_name: "PBX Voicemail"
```

Restart the service:
```bash
sudo systemctl restart pbx
```

#### Configure Phone Provisioning

For auto-configuration of IP phones (Zultys, Yealink, Polycom, etc.):

```bash
# Run provisioning setup
python scripts/setup_phone_provisioning.py

# Verify templates
ls -lh provisioning_templates/
```

See **[PHONE_PROVISIONING.md](PHONE_PROVISIONING.md)** for detailed instructions.

---

## Auto Attendant Configuration

### Pre-Deployment for Auto Attendant

- [ ] Server has Python 3 installed
- [ ] Server has internet connection (for best voice quality)
- [ ] You have sudo/root access (for installing packages)
- [ ] PBX code is on the server
- [ ] Voice prompts generated (see above)

### Configuration

Review `config.yml` auto attendant section:

```yaml
auto_attendant:
  enabled: true
  extension: '0'
  timeout: 10
  max_retries: 3
  operator_extension: '1001'  # ← Verify this exists!
  menu_options:
    - digit: '1'
      destination: '8001'  # ← Verify destinations exist
      description: 'Sales Queue'
    - digit: '2'
      destination: '8002'
      description: 'Support Queue'
    - digit: '0'
      destination: '1001'
      description: 'Operator'
```

### Testing Auto Attendant

- [ ] Start PBX: `sudo systemctl start pbx`
- [ ] Call PBX from a phone
- [ ] Dial `0` to access auto attendant
- [ ] Listen to welcome message
- [ ] Press `1` - verify transfers to sales queue
- [ ] Press `2` - verify transfers to support queue
- [ ] Press invalid digit - verify error handling
- [ ] Wait for timeout - verify timeout handling
- [ ] Press `0` - verify transfers to operator

### Post-Deployment for Auto Attendant

- [ ] Voice quality is acceptable
- [ ] All menu options work correctly
- [ ] Timeouts work correctly
- [ ] Invalid inputs work correctly
- [ ] Operator fallback works
- [ ] Document for your team
- [ ] Monitor logs: `tail -f logs/pbx.log`

### Troubleshooting Auto Attendant

**Voice files not generated:**
```bash
# Check internet connection
ping google.com

# Check firewall allows HTTPS to Google
sudo ufw status

# Try Festival instead
python scripts/generate_espeak_voices.py --engine festival
```

**Auto attendant not answering:**
1. Check voice files exist: `ls auto_attendant/*.wav`
2. Check config: `auto_attendant.enabled: true`
3. Check logs: `tail -f logs/pbx.log`
4. Check extension 0 is not registered to a phone

**Voice sounds robotic:**
You're using eSpeak or Festival. Upgrade to gTTS:
```bash
pip install gTTS pydub
python scripts/generate_tts_prompts.py --company "Your Company"
sudo systemctl restart pbx
```

---

## Post-Deployment Verification

### Health Checks
- [ ] Liveness probe responds: `curl http://localhost:8080/live`
- [ ] Readiness probe responds: `curl http://localhost:8080/ready`
- [ ] Detailed health check passes: `curl http://localhost:8080/api/health/detailed`
- [ ] Metrics endpoint accessible: `curl http://localhost:8080/metrics`

### Functional Testing
- [ ] Admin panel loads: `https://your-server-ip:8080/admin/`
- [ ] Can login to admin panel
- [ ] Extensions are visible in admin panel
- [ ] SIP phone registers successfully
- [ ] Can make calls between extensions
- [ ] Can access voicemail (*extension_number)
- [ ] Voicemail-to-email works (if configured)
- [ ] Call recording works (if enabled)
- [ ] Auto attendant answers (dial 0)
- [ ] Call queues work (dial 8xxx)
- [ ] E911 calls route correctly (TEST CAREFULLY)

### Performance Testing
- [ ] System handles expected call load
- [ ] CPU usage is reasonable (< 50% average)
- [ ] Memory usage is stable
- [ ] No memory leaks over 24 hours
- [ ] Database connections are properly pooled
- [ ] RTP media quality is good (MOS score > 3.5)

### Monitoring Setup
- [ ] Prometheus metrics are being collected
- [ ] Grafana dashboards are configured (if using)
- [ ] Log aggregation is setup (if using)
- [ ] Alerts are configured for critical events:
  - Service down
  - High error rate
  - Database connection failures
  - High CPU/memory usage
  - Disk space low

### Backup Configuration
- [ ] Database backup script is scheduled (daily recommended)
- [ ] Configuration files are backed up
- [ ] Voicemail files are backed up
- [ ] Call recordings are backed up (if retention required)
- [ ] Backup restoration procedure is tested
- [ ] Backup monitoring/alerts are configured

### Documentation
- [ ] Network diagram is documented
- [ ] Extension assignments are documented
- [ ] SIP trunk configuration is documented
- [ ] Firewall rules are documented
- [ ] Emergency contact information is updated
- [ ] Runbook for common tasks is created
- [ ] Disaster recovery plan is documented

## Production Monitoring

### Daily Checks
- [ ] Check health endpoint: `curl http://localhost:8080/api/health/detailed`
- [ ] Review logs for errors: `sudo journalctl -u pbx -p err --since today`
- [ ] Check disk space: `df -h`
- [ ] Verify backups completed successfully

### Weekly Checks
- [ ] Review security logs: `sudo journalctl -u pbx | grep -i security`
- [ ] Check for failed login attempts
- [ ] Review call quality metrics (QoS)
- [ ] Verify all extensions are registered
- [ ] Check for software updates

### Monthly Checks
- [ ] Test disaster recovery procedure
- [ ] Review and rotate logs
- [ ] Update SSL certificates if needed
- [ ] Review and update documentation
- [ ] Performance tuning based on metrics
- [ ] Security audit

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status pbx

# View logs
sudo journalctl -u pbx -n 100 --no-pager

# Check configuration
python -c "from pbx.utils.config import Config; Config('config.yml')"

# Test database connection
python scripts/verify_database.py
```

### Health Checks Failing
```bash
# Check detailed health
curl http://localhost:8080/api/health/detailed | jq

# Check individual components
curl http://localhost:8080/live
curl http://localhost:8080/ready

# Check system resources
free -h
df -h
top -bn1 | head -20
```

### High CPU/Memory Usage
```bash
# Check process stats
sudo systemctl status pbx
top -p $(pgrep -f "python.*main.py")

# Check for memory leaks
python scripts/check_memory_usage.py

# Review active calls
curl http://localhost:8080/api/calls | jq
```

### Database Issues
```bash
# Check database connection
sudo -u postgres psql -d pbx_system -c "SELECT version();"

# Check connection pool
curl http://localhost:8080/api/health/detailed | jq '.readiness.checks.database'

# Check database size
sudo -u postgres psql -d pbx_system -c "SELECT pg_size_pretty(pg_database_size('pbx_system'));"
```

## Performance Tuning

### For High Call Volume (100+ simultaneous calls)
```yaml
# In config.yml
rtp:
  jitter_buffer:
    enabled: true
    max_length_ms: 200
    adaptive: true

database:
  # Use PostgreSQL with connection pooling
  type: postgresql
  pool_size: 20
  max_overflow: 10

api:
  # Use multiple worker threads
  workers: 4
```

### For Low-Latency Requirements
```yaml
codecs:
  opus:
    enabled: true
    sample_rate: 48000
    bitrate: 64000  # Higher bitrate for better quality

rtcp:
  enabled: true
  interval_seconds: 5
  monitor_quality: true
```

## Security Hardening

### Additional Security Measures
```bash
# Enable automatic security updates
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Setup fail2ban for PBX
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
# Add PBX-specific jail rules

# Configure SELinux/AppArmor (if available)
# ...

# Regular security audits
sudo apt-get install lynis
sudo lynis audit system
```

### SSL/TLS Hardening
```yaml
# In config.yml
api:
  ssl:
    enabled: true
    # Use strong ciphers only
    ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256"
    # Enforce TLS 1.2+
    min_tls_version: "TLSv1.2"
```

---

## Monitoring & Troubleshooting

### Access Monitoring Tools

- **Prometheus**: http://your-domain/prometheus/ or http://localhost:9090
- **Node Exporter**: http://your-domain/metrics or http://localhost:9100/metrics
- **Admin Panel**: https://your-domain/admin/ or https://localhost:8080/admin/

### View Logs

```bash
# System logs
sudo journalctl -u pbx -f

# Deployment log (if deployed with script)
tail -f /var/log/pbx-deployment.log

# Backup logs
tail -f /var/log/pbx-backup.log

# Application logs
tail -f /path/to/PBX/logs/pbx.log
```

### Check Service Status

```bash
# PBX service
sudo systemctl status pbx

# PostgreSQL
sudo systemctl status postgresql

# Nginx
sudo systemctl status nginx

# Prometheus (if installed)
sudo systemctl status prometheus
```

### Test Database Connection

```bash
# Connect to database
sudo -u postgres psql -d pbx

# List tables
\dt

# Check extensions
SELECT * FROM extensions;

# Exit
\q
```

### Testing Your Deployment

**1. Test PBX Startup**

```bash
# Stop service for manual test
sudo systemctl stop pbx

# Run manually to see logs
cd /path/to/PBX
source venv/bin/activate
python main.py

# Look for:
# ✓ SIP server started on 0.0.0.0:5060
# ✓ PBX system started successfully
```

**2. Test SIP Registration**

From a phone or SIP client:
- Server: your-domain or server-ip
- Port: 5060
- Extension: 1001 (or your extension)
- Password: (from database)

**3. Test Admin Panel**

Visit: https://your-domain/admin/
- Check that extensions are listed
- Verify system status
- Test adding/editing extensions

**4. Test Auto Attendant**

1. Call your PBX
2. Dial `0` to access auto attendant
3. Verify voice prompt plays
4. Test menu options (press 1, 2, etc.)

### Backup Information

**Automatic Backups** (if deployed with script)

The deployment script configures daily backups at 2 AM:

```bash
# Backup locations
/var/backups/pbx/db_*.sql.gz      # Database backups
/var/backups/pbx/config_*.tar.gz  # Configuration backups

# Retention: 7 days
```

**Manual Backup**

```bash
# Run backup now
sudo /usr/local/bin/pbx-backup.sh

# List backups
ls -lh /var/backups/pbx/
```

**Restore from Backup**

```bash
# Find latest backup
ls -lt /var/backups/pbx/db_*.sql.gz | head -1

# Restore database
gunzip -c /var/backups/pbx/db_TIMESTAMP.sql.gz | sudo -u postgres psql pbx

# Restore configuration
sudo tar -xzf /var/backups/pbx/config_TIMESTAMP.tar.gz -C /
```

### Security Checklist

Before going live, complete these security tasks:

- [ ] Change default database password ✅ (done in Post-Deployment Setup)
- [ ] Configure SSL/TLS certificate ✅ (done in Installation Steps)
- [ ] Review firewall rules: `sudo ufw status`
- [ ] Enable fail2ban for SSH: `sudo systemctl enable fail2ban`
- [ ] Set up log rotation
- [ ] Review user permissions
- [ ] Test backup restoration: `sudo /usr/local/bin/pbx-backup.sh`
- [ ] Document admin passwords (store securely)
- [ ] Set up monitoring alerts

### Getting Help

**Check Logs First**

Most issues can be diagnosed from logs:
```bash
sudo journalctl -u pbx -n 100 --no-pager
```

**Common Issues**

**PBX won't start:**
```bash
# Check for port conflicts
sudo netstat -tulpn | grep -E "5060|8080"

# Check database connection
python scripts/verify_database.py
```

**No audio on calls:**
- Check firewall allows UDP ports 10000-20000
- Verify voice prompts were generated
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Phones won't register:**
- Verify extension exists in database
- Check password is correct
- Verify firewall allows UDP port 5060

**Documentation Resources:**
- **Quick Issues**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Integration Issues**: [INTEGRATION_TROUBLESHOOTING_GUIDE.md](INTEGRATION_TROUBLESHOOTING_GUIDE.md)
- **Full Documentation**: [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

**Support:**
For issues and questions, open a GitHub issue at: https://github.com/mattiIce/PBX/issues

### Deployment Complete Checklist

Before considering your deployment complete:

- [ ] Database password updated in config.yml
- [ ] Database initialized and extensions seeded
- [ ] SSL/TLS certificate configured
- [ ] PBX service started successfully
- [ ] Voice prompts generated (17 files)
- [ ] Admin panel accessible
- [ ] Test extension registered successfully
- [ ] Test call completed successfully
- [ ] Auto attendant tested
- [ ] Voicemail tested
- [ ] Backups tested
- [ ] Monitoring accessible
- [ ] Security checklist completed
- [ ] Documentation reviewed

### Optional Documentation (As Needed)

Read these when you need specific features:

**Integrations:**
- **[FREE_INTEGRATION_OPTIONS.md](FREE_INTEGRATION_OPTIONS.md)** - Free/open-source integrations
- **[ENTERPRISE_INTEGRATIONS.md](ENTERPRISE_INTEGRATIONS.md)** - Zoom, Active Directory, Teams

**Advanced Features:**
- **[PHONE_BOOK_GUIDE.md](PHONE_BOOK_GUIDE.md)** - Centralized directory
- **[PAGING_SYSTEM_GUIDE.md](PAGING_SYSTEM_GUIDE.md)** - Overhead paging
- **[WEBHOOK_SYSTEM_GUIDE.md](WEBHOOK_SYSTEM_GUIDE.md)** - Event notifications

**Compliance & Security:**
- **[REGULATIONS_COMPLIANCE_GUIDE.md](REGULATIONS_COMPLIANCE_GUIDE.md)** - E911, STIR/SHAKEN
- **[SECURITY_GUIDE.md](SECURITY_GUIDE.md)** - Complete security reference

**Complete Documentation:**
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Full documentation catalog

---

### For FIPS 140-2 Compliance
```yaml
security:
  fips_mode: true
  enforce_fips: true
```

### For Call Recording Compliance
- [ ] Recording announcements are enabled
- [ ] Retention policies are configured
- [ ] Legal compliance is verified for your jurisdiction

### For E911 Compliance
- [ ] Kari's Law compliance verified (direct 911 dialing)
- [ ] Ray Baum's Act compliance verified (dispatchable location)
- [ ] Multi-site E911 configured (if applicable)
- [ ] Emergency notification contacts configured

## Go-Live Checklist

### Final Steps Before Production
- [ ] All checklist items above are completed
- [ ] Stakeholders are notified of go-live time
- [ ] Support team is briefed and available
- [ ] Rollback plan is documented and tested
- [ ] Migration plan is executed (if migrating from old system)
- [ ] Users are trained on new system
- [ ] User documentation is distributed

### During Go-Live
- [ ] Monitor health endpoints continuously
- [ ] Watch logs in real-time: `sudo journalctl -u pbx -f`
- [ ] Monitor system resources: `htop`
- [ ] Have support team on standby
- [ ] Test all critical features immediately after go-live

### Post Go-Live
- [ ] Monitor for 24 hours continuously
- [ ] Collect user feedback
- [ ] Address any issues immediately
- [ ] Document lessons learned
- [ ] Schedule post-mortem meeting

## Support Contacts

### Emergency Contacts
- **System Administrator**: [Name/Phone]
- **Database Administrator**: [Name/Phone]
- **Network Administrator**: [Name/Phone]
- **On-Call Support**: [Phone/Pager]

### Escalation Path
1. On-call support
2. System administrator
3. Vendor support (if applicable)
4. Management

---

## Next Steps

Once everything is working:

1. **Add Your Extensions** - Using admin panel or API
2. **Configure Features** - Voicemail, queues, conferencing
3. **Set Up Integrations** - CRM, Active Directory, etc.
4. **Train Users** - Distribute phone configuration guides
5. **Monitor System** - Check Prometheus for health metrics
6. **Schedule Maintenance** - Plan for updates and backups

---

**Remember**: Production deployment is not just about installing software. It's about ensuring reliability, security, and supportability for your organization.

**Welcome to your production PBX system! 🎉**
