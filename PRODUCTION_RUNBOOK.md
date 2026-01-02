# Production Runbook

**Last Updated**: January 2, 2026  
**Version**: 1.0.0  
**Purpose**: Step-by-step procedures for common production scenarios

---

## Table of Contents

1. [Emergency Procedures](#emergency-procedures)
2. [Daily Operations](#daily-operations)
3. [Common Issues & Solutions](#common-issues--solutions)
4. [Maintenance Procedures](#maintenance-procedures)
5. [Performance Issues](#performance-issues)
6. [Security Incidents](#security-incidents)
7. [Capacity Management](#capacity-management)

---

## Emergency Procedures

### Complete Service Outage (SEV-1)

**Response Time**: Immediate (< 5 minutes)

#### Symptoms
- No incoming or outgoing calls
- Admin interface unreachable
- Service status check fails

#### Quick Diagnosis
```bash
# Check service status
sudo systemctl status pbx

# Check if process is running
ps aux | grep python | grep main.py

# Check port availability
sudo netstat -tulpn | grep -E ':(5060|8080)'

# Quick health check
curl -k https://localhost:8080/health
```

#### Recovery Steps

**Step 1: Verify Infrastructure**
```bash
# Check disk space (must be > 10% free)
df -h

# Check memory (must have available memory)
free -h

# Check CPU (should not be 100% consistently)
top -bn1 | head -20
```

**Step 2: Restart Service**
```bash
# Restart PBX service
sudo systemctl restart pbx

# Wait 30 seconds
sleep 30

# Verify service is running
sudo systemctl status pbx

# Check logs for errors
sudo tail -100 /var/log/pbx/pbx.log | grep -i error
```

**Step 3: Verify Functionality**
```bash
# Run smoke tests
python3 scripts/smoke_tests.py

# Test a call (replace extension numbers)
# Make test call from extension 1001 to 1002

# Check API
curl -k https://localhost:8080/api/status
```

**Step 4: Escalate if Needed**
If service doesn't recover after restart:
1. Check database connectivity
2. Check for recent configuration changes
3. Review system logs for critical errors
4. Contact senior engineer immediately

---

### Database Connection Failure

#### Symptoms
- Service logs show database errors
- API returns 500 errors
- Calls fail to connect

#### Diagnosis
```bash
# Test database connection
psql -h localhost -U pbx_user -d pbx_system -c "SELECT 1;"

# Check PostgreSQL service
sudo systemctl status postgresql

# Check connection count
psql -h localhost -U pbx_user -d pbx_system -c \
  "SELECT count(*) FROM pg_stat_activity;"
```

#### Recovery Steps

**If PostgreSQL is down:**
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

**If connection limit reached:**
```bash
# Check current connections
psql -U postgres -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Kill idle connections (if safe)
psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE datname='pbx_system' AND state='idle' AND 
   state_change < NOW() - INTERVAL '10 minutes';"

# Restart PBX service
sudo systemctl restart pbx
```

**If credentials are wrong:**
```bash
# Verify .env file has correct credentials
sudo cat /opt/pbx/.env | grep DB_

# Reset password if needed (PostgreSQL)
sudo -u postgres psql -c \
  "ALTER USER pbx_user WITH PASSWORD 'new_password';"

# Update .env file
sudo nano /opt/pbx/.env
# Update DB_PASSWORD

# Restart service
sudo systemctl restart pbx
```

---

### High Call Quality Issues (SEV-2)

#### Symptoms
- Multiple users report choppy audio
- MOS scores < 3.5
- High packet loss or jitter

#### Diagnosis
```bash
# Check QoS metrics
python3 scripts/diagnose_qos.py

# Check network statistics
netstat -s | grep -E 'packet|error|drop'

# Check bandwidth usage
iftop -i eth0  # or your network interface

# Check for network congestion
ping -c 100 <sip_trunk_provider>
```

#### Recovery Steps

**Step 1: Identify Scope**
- Is it all users or specific extensions?
- Is it all calls or specific destinations?
- Did it start at a specific time?

**Step 2: Quick Fixes**
```bash
# Reduce concurrent calls if needed
# Edit config.yml and reduce max_calls

# Restart RTP services
sudo systemctl restart pbx

# Verify QoS/DSCP settings
tc -s qdisc show dev eth0
```

**Step 3: Network Investigation**
```bash
# Check for packet loss
mtr -r -c 100 <destination>

# Check for firewall issues
sudo iptables -L -n -v | grep -E '5060|10000:20000'

# Verify RTP ports are open
sudo netstat -tulpn | grep -E '10000|10001|10002'
```

**Step 4: Codec Adjustment**
If bandwidth is limited:
1. Edit config.yml
2. Prioritize lower-bandwidth codecs (G.729, G.726)
3. Disable high-bandwidth codecs (G.722, Opus)
4. Restart service

---

## Daily Operations

### Morning Health Check (5-10 minutes)

**Checklist:**
```bash
# 1. Service status
sudo systemctl status pbx

# 2. Quick health check
python3 scripts/health_monitor.py --format text

# 3. Check for critical errors in last 24 hours
sudo grep -i "critical\|fatal" /var/log/pbx/pbx.log | tail -20

# 4. Verify backups completed
ls -lh /var/backups/pbx/ | tail -5

# 5. Check disk space
df -h | grep -E 'Use%|pbx|postgres'

# 6. Check registered extensions count
curl -k https://localhost:8080/api/extensions/registered | jq '.count'

# 7. Review active calls
curl -k https://localhost:8080/api/calls/active | jq '.count'

# 8. Check certificate expiry
openssl x509 -in /opt/pbx/ssl/server.crt -noout -dates
```

**Expected Results:**
- ✓ Service: active (running)
- ✓ Health: All checks passing
- ✓ No critical errors in logs
- ✓ Backup exists from today
- ✓ Disk usage < 80%
- ✓ Extensions registered: normal count
- ✓ Active calls: within expected range
- ✓ Certificate: > 30 days until expiry

---

### Log Review Procedure

**Check for patterns:**
```bash
# Authentication failures (potential security issue)
sudo grep "authentication failed" /var/log/pbx/pbx.log | tail -20

# Failed calls
sudo grep "call failed" /var/log/pbx/pbx.log | tail -20

# Database errors
sudo grep -i "database\|sql" /var/log/pbx/pbx.log | grep -i error | tail -20

# Memory issues
sudo grep -i "memory\|oom" /var/log/syslog | tail -20
```

**Action Items:**
- > 10 auth failures from same IP: Block IP with `fail2ban`
- Repeated database errors: Check database health
- Memory issues: Consider increasing resources

---

## Common Issues & Solutions

### Issue: Extensions Not Registering

**Diagnosis:**
```bash
# Check SIP port is listening
sudo netstat -tulpn | grep 5060

# Check firewall rules
sudo ufw status | grep 5060

# Test from phone
# Set phone to debug mode and check registration logs
```

**Solutions:**

**Problem: Port not open**
```bash
sudo ufw allow 5060/udp
sudo ufw reload
```

**Problem: Wrong credentials**
```bash
# List extensions
curl -k https://localhost:8080/api/extensions

# Reset extension password
curl -k -X POST https://localhost:8080/api/extensions/1001/password \
  -H "Content-Type: application/json" \
  -d '{"password": "new_password"}'
```

**Problem: NAT issues**
```bash
# Edit config.yml
# Set external_ip to your public IP
external_ip: "x.x.x.x"

# Restart service
sudo systemctl restart pbx
```

---

### Issue: Voicemail Not Working

**Diagnosis:**
```bash
# Check voicemail directory
ls -lh /opt/pbx/voicemail/

# Check voicemail prompts
ls -lh /opt/pbx/voicemail_prompts/

# Check SMTP settings
grep SMTP /opt/pbx/.env

# Test email
python3 -c "
import smtplib
from email.mime.text import MIMEText
msg = MIMEText('Test')
msg['Subject'] = 'PBX Test'
msg['From'] = 'pbx@yourdomain.com'
msg['To'] = 'test@yourdomain.com'
s = smtplib.SMTP('smtp.server.com', 587)
s.starttls()
s.login('username', 'password')
s.send_message(msg)
s.quit()
print('Email sent')
"
```

**Solutions:**

**Missing voice prompts:**
```bash
# Generate voice prompts
python3 scripts/generate_tts_prompts.py

# Verify prompts exist
ls -lh /opt/pbx/voicemail_prompts/
```

**Email not sending:**
```bash
# Update SMTP settings in .env
sudo nano /opt/pbx/.env

# Update these:
SMTP_HOST=smtp.yourserver.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password

# Restart service
sudo systemctl restart pbx
```

---

### Issue: Call Recording Not Working

**Diagnosis:**
```bash
# Check recordings directory
ls -lh /opt/pbx/recordings/

# Check disk space
df -h /opt/pbx/recordings/

# Check permissions
ls -ld /opt/pbx/recordings/

# Verify recording is enabled in config
grep recording /opt/pbx/config.yml
```

**Solutions:**

**Disk full:**
```bash
# Clean old recordings (older than 90 days)
find /opt/pbx/recordings/ -name "*.wav" -mtime +90 -delete

# Or archive to S3/NAS before deleting
```

**Permission issue:**
```bash
sudo chown -R pbx:pbx /opt/pbx/recordings/
sudo chmod 755 /opt/pbx/recordings/
```

---

## Maintenance Procedures

### Updating the System

**Preparation (15 minutes before):**
```bash
# 1. Notify users of upcoming maintenance

# 2. Backup current system
sudo bash scripts/backup.sh --full

# 3. Verify backup
ls -lh /var/backups/pbx/

# 4. Document current version
cat /opt/pbx/VERSION
```

**Update Procedure:**
```bash
# 1. Stop the service
sudo systemctl stop pbx

# 2. Backup configuration
sudo cp /opt/pbx/config.yml /opt/pbx/config.yml.backup
sudo cp /opt/pbx/.env /opt/pbx/.env.backup

# 3. Pull latest code
cd /opt/pbx
sudo -u pbx git fetch
sudo -u pbx git pull origin main

# 4. Update dependencies
sudo -u pbx /opt/pbx/venv/bin/pip install -r requirements.txt

# 5. Run database migrations (if any)
sudo -u pbx /opt/pbx/venv/bin/python scripts/migrate_database.py

# 6. Start the service
sudo systemctl start pbx

# 7. Verify service
sleep 10
sudo systemctl status pbx

# 8. Run smoke tests
python3 scripts/smoke_tests.py

# 9. Test a call
# Make test call to verify functionality
```

**Rollback Procedure (if update fails):**
```bash
# 1. Stop service
sudo systemctl stop pbx

# 2. Restore code
cd /opt/pbx
sudo -u pbx git reset --hard HEAD~1

# 3. Restore configuration
sudo cp /opt/pbx/config.yml.backup /opt/pbx/config.yml
sudo cp /opt/pbx/.env.backup /opt/pbx/.env

# 4. Restore database (if migrations ran)
# See OPERATIONS_MANUAL.md for database restore

# 5. Start service
sudo systemctl start pbx
```

---

### Database Maintenance

**Weekly vacuum and analyze:**
```bash
# Connect to database
psql -h localhost -U pbx_user -d pbx_system

-- Run vacuum and analyze
VACUUM ANALYZE;

-- Check bloat
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Monthly index maintenance:**
```bash
psql -h localhost -U pbx_user -d pbx_system -c "REINDEX DATABASE pbx_system;"
```

---

## Performance Issues

### High CPU Usage

**Diagnosis:**
```bash
# Check top processes
top -bn1 | head -20

# Check PBX process specifically
ps aux | grep python | grep main.py

# Check number of active calls
curl -k https://localhost:8080/api/calls/active
```

**Solutions:**

**Too many concurrent calls:**
- Reduce max_calls in config.yml
- Add more servers with load balancing

**Codec issues:**
- Use lower-complexity codecs (G.711 instead of Opus)
- Disable unnecessary transcoding

**Database queries:**
- Check slow query log
- Add indexes if needed
- Optimize query patterns

---

### High Memory Usage

**Diagnosis:**
```bash
# Check memory usage
free -h

# Check PBX memory usage
ps aux | grep python | grep main.py | awk '{print $6}'

# Check for memory leaks
watch -n 5 'ps aux | grep python | grep main.py'
```

**Solutions:**

**Memory leak suspected:**
```bash
# Restart service (temporary fix)
sudo systemctl restart pbx

# Monitor for recurring issue
# Report to development team with logs
```

**Insufficient memory:**
- Increase server RAM
- Reduce max_calls
- Enable swap (not recommended for production)

---

## Security Incidents

### Suspected Toll Fraud

**Immediate Actions:**
```bash
# 1. Check unusual call patterns
curl -k https://localhost:8080/api/cdr | jq '.calls[] | select(.duration > 3600)'

# 2. Check failed auth attempts
sudo grep "authentication failed" /var/log/pbx/pbx.log | tail -100

# 3. Block suspicious IPs
sudo ufw deny from <suspicious_ip>

# 4. Disable compromised extensions
curl -k -X POST https://localhost:8080/api/extensions/<ext>/disable

# 5. Change all extension passwords
```

**Investigation:**
- Review CDR for abnormal patterns
- Check for international calls
- Review extension usage patterns
- Check for unauthorized extensions

---

### Brute Force Attack

**Detection:**
```bash
# Check failed auth attempts
sudo grep "authentication failed" /var/log/pbx/pbx.log | \
  awk '{print $NF}' | sort | uniq -c | sort -rn | head -10
```

**Response:**
```bash
# Block attacking IPs with fail2ban
sudo fail2ban-client set pbx banip <IP_ADDRESS>

# Or manually with UFW
sudo ufw deny from <IP_ADDRESS>

# Strengthen passwords
# Force password change for all users
```

---

## Capacity Management

### Monitoring Capacity

**Key metrics to track:**
```bash
# Concurrent calls capacity
curl -k https://localhost:8080/api/calls/active | jq '.count'

# Extension registration capacity
curl -k https://localhost:8080/api/extensions/registered | jq '.count'

# Database size
psql -h localhost -U pbx_user -d pbx_system -c \
  "SELECT pg_size_pretty(pg_database_size('pbx_system'));"

# Storage usage
du -sh /opt/pbx/voicemail/
du -sh /opt/pbx/recordings/
```

### Scaling Decisions

**When to scale up:**
- CPU usage consistently > 70%
- Memory usage > 80%
- Concurrent calls > 80% of max_calls
- API response time > 500ms

**When to scale out:**
- Need for high availability
- Geographic distribution required
- Concurrent calls > 200

---

## Quick Reference

### Important Commands
```bash
# Restart service
sudo systemctl restart pbx

# View logs
sudo tail -f /var/log/pbx/pbx.log

# Health check
python3 scripts/health_monitor.py

# Run backup
sudo bash scripts/backup.sh --full

# Smoke tests
python3 scripts/smoke_tests.py
```

### Important Files
- `/opt/pbx/config.yml` - Main configuration
- `/opt/pbx/.env` - Secrets and credentials
- `/var/log/pbx/pbx.log` - Application logs
- `/var/backups/pbx/` - Backup location

### Emergency Contacts
- **On-Call Engineer**: [Phone/Email]
- **Database Admin**: [Phone/Email]
- **Network Team**: [Phone/Email]
- **Manager**: [Phone/Email]

---

**Document Version**: 1.0.0  
**Last Updated**: January 2, 2026  
**Next Review**: Quarterly
