# Production Deployment Checklist

This comprehensive checklist ensures your PBX system is production-ready before go-live.

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

## Compliance

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

**Remember**: Production deployment is not just about installing software. It's about ensuring reliability, security, and supportability for your organization.

**Good luck with your deployment!**
