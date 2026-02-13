# Production Operations Runbook

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Common Operations](#common-operations)
3. [Incident Response](#incident-response)
4. [Monitoring & Alerts](#monitoring--alerts)
5. [Backup & Recovery](#backup--recovery)
6. [Performance Tuning](#performance-tuning)
7. [Security Operations](#security-operations)
8. [Troubleshooting Guide](#troubleshooting-guide)

---

## Quick Reference

### Emergency Contacts

| Role | Contact | Escalation Time |
|------|---------|-----------------|
| On-Call Engineer | [Contact Info] | Immediate |
| Lead SRE | [Contact Info] | 15 minutes |
| Engineering Manager | [Contact Info] | 30 minutes |
| CTO | [Contact Info] | 1 hour |

### Service Status Commands

```bash
# Check service status
sudo systemctl status pbx

# View recent logs
sudo journalctl -u pbx -n 100 -f

# Check health
python3 scripts/production_health_check.py

# View active calls
curl http://localhost:8080/api/calls

# Check database connectivity
python3 scripts/verify_database.py
```

### Critical File Locations

| File/Directory | Purpose | Location |
|----------------|---------|----------|
| Configuration | Main config | `/path/to/PBX/config.yml` |
| Environment | Secrets | `/path/to/PBX/.env` |
| Logs | Application logs | `/var/log/pbx/` or `logs/` |
| Recordings | Call recordings | `recordings/` |
| Voicemail | Voicemail files | `voicemail/` |
| Backups | Database backups | Configured in backup script |

---

## Common Operations

### 1. Deployment

#### Standard Deployment (Zero-Downtime)

```bash
# 1. Pull latest code
cd /path/to/PBX
git pull origin main

# 2. Run zero-downtime deployment
sudo ./scripts/zero_downtime_deploy.sh

# 3. Verify deployment
python3 scripts/production_health_check.py
python3 scripts/smoke_tests.py
```

#### Emergency Rollback

```bash
# Rollback to previous version
sudo ./scripts/zero_downtime_deploy.sh --rollback

# Verify rollback
python3 scripts/production_health_check.py
```

### 2. Service Management

#### Start/Stop/Restart

```bash
# Start service
sudo systemctl start pbx

# Stop service (graceful)
sudo systemctl stop pbx

# Restart service
sudo systemctl restart pbx

# Reload configuration (without restart)
sudo systemctl reload pbx
```

#### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot
sudo systemctl enable pbx

# Disable auto-start
sudo systemctl disable pbx
```

### 3. Configuration Changes

#### Update Configuration

```bash
# 1. Edit configuration file
sudo nano /path/to/PBX/config.yml

# 2. Validate configuration
python3 -c "import yaml; yaml.safe_load(open('config.yml'))"

# 3. Reload service
sudo systemctl reload pbx

# 4. Verify changes
curl http://localhost:8080/api/config
```

#### Update Environment Variables

```bash
# 1. Edit .env file
sudo nano /path/to/PBX/.env

# 2. Restart service (required for .env changes)
sudo systemctl restart pbx

# 3. Verify
python3 scripts/production_health_check.py
```

### 4. Extension Management

#### Add New Extension

```bash
# Via API
curl -X POST http://localhost:8080/api/extensions \
  -H "Content-Type: application/json" \
  -d '{
    "number": "1100",
    "name": "New User",
    "email": "user@company.com",
    "password": "secure_password_here"
  }'

# Via Admin Panel
# Navigate to: https://your-server/admin/#/extensions
```

#### Delete Extension

```bash
# Via API
curl -X DELETE http://localhost:8080/api/extensions/1100

# Via Admin Panel
# Navigate to: https://your-server/admin/#/extensions
```

### 5. Database Operations

#### Manual Backup

```bash
# Run backup script
sudo ./scripts/backup.sh

# Verify backup
ls -lh /path/to/backups/
```

#### Database Maintenance

```bash
# Connect to database
psql -U pbx_user -d pbx_system

# Vacuum and analyze
VACUUM ANALYZE;

# Check database size
SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname))
FROM pg_database;
```

---

## Incident Response

### Severity Levels

| Severity | Response Time | Description | Escalation |
|----------|---------------|-------------|------------|
| P0 - Critical | 5 minutes | Complete service outage | Immediate |
| P1 - High | 15 minutes | Major feature unavailable | 30 minutes |
| P2 - Medium | 1 hour | Minor feature impact | 2 hours |
| P3 - Low | 4 hours | Cosmetic issues | Next business day |

### P0 - Service Down

**Symptoms:**
- PBX service not responding
- No calls can be made/received
- API returning 500 errors

**Immediate Actions:**

1. **Confirm outage:**
   ```bash
   sudo systemctl status pbx
   curl http://localhost:8080/health
   ```

2. **Check logs:**
   ```bash
   sudo journalctl -u pbx -n 200 --no-pager
   tail -100 /var/log/pbx/pbx.log
   ```

3. **Attempt service restart:**
   ```bash
   sudo systemctl restart pbx
   sleep 5
   sudo systemctl status pbx
   ```

4. **If restart fails:**
   ```bash
   # Check for port conflicts
   sudo netstat -tulpn | grep -E ':(5060|8080)'
   
   # Check disk space
   df -h
   
   # Check memory
   free -h
   
   # Check database
   python3 scripts/verify_database.py
   ```

5. **Rollback if recent deployment:**
   ```bash
   sudo ./scripts/zero_downtime_deploy.sh --rollback
   ```

6. **Emergency recovery:**
   ```bash
   sudo ./scripts/emergency_recovery.sh
   ```

### P1 - Database Connection Issues

**Symptoms:**
- "Database connection failed" errors
- Features requiring database not working
- Intermittent failures

**Actions:**

1. **Check database status:**
   ```bash
   sudo systemctl status postgresql
   sudo -u postgres psql -c "SELECT version();"
   ```

2. **Check connection from PBX:**
   ```bash
   python3 scripts/verify_database.py
   ```

3. **Check connection pool:**
   ```bash
   # In PostgreSQL
   SELECT count(*) FROM pg_stat_activity WHERE datname='pbx_system';
   ```

4. **Restart database if needed:**
   ```bash
   sudo systemctl restart postgresql
   ```

### P1 - High Call Volume / Performance Degradation

**Symptoms:**
- Slow call setup
- Poor voice quality
- API timeouts

**Actions:**

1. **Check system resources:**
   ```bash
   # CPU and memory
   top -bn1 | head -20
   
   # Disk I/O
   iostat -x 1 5
   
   # Network
   netstat -s | grep -i error
   ```

2. **Check active calls:**
   ```bash
   curl http://localhost:8080/api/calls | python3 -m json.tool
   ```

3. **Check QoS metrics:**
   ```bash
   python3 scripts/diagnose_qos.py
   ```

4. **Scale resources if needed:**
   - For bare metal: Add more resources
   - For Docker: `docker compose up -d --scale pbx=2`
   - For Kubernetes: `kubectl scale deployment pbx --replicas=3`

---

## Monitoring & Alerts

### Key Metrics to Monitor

| Metric | Warning Threshold | Critical Threshold | Action |
|--------|------------------|-------------------|---------|
| Service Status | N/A | Down | Restart service |
| CPU Usage | >70% | >90% | Investigate/scale |
| Memory Usage | >80% | >95% | Investigate/scale |
| Disk Space | <20% | <10% | Clean up logs/recordings |
| Active Calls | >80% capacity | >95% capacity | Scale resources |
| Call Success Rate | <95% | <90% | Check trunks/network |
| API Response Time | >1s | >2s | Investigate performance |
| Database Connections | >80% pool | >95% pool | Increase pool size |

### Alert Configuration

Health checks are provided via:

```bash
# Run health check (exit code 0=healthy, 1=critical, 2=warning)
python3 scripts/production_health_check.py

# JSON output for monitoring systems
python3 scripts/production_health_check.py --json

# Integration with monitoring (example for Nagios/Icinga)
# Add to /etc/nagios/nrpe.cfg:
# command[check_pbx]=/usr/bin/python3 /path/to/PBX/scripts/production_health_check.py --critical-only
```

### Log Monitoring

```bash
# Watch for errors in real-time
sudo journalctl -u pbx -f | grep -i error

# Count errors per hour
sudo journalctl -u pbx --since "1 hour ago" | grep -c ERROR

# Find failed calls
grep "call failed" /var/log/pbx/pbx.log | tail -20
```

---

## Backup & Recovery

### Backup Schedule

| Type | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| Database | Daily (2 AM) | 30 days | `scripts/backup.sh` |
| Configuration | On change | 90 days | Git + backup script |
| Recordings | Weekly | Per policy | Backup script |
| Voicemail | Daily | 30 days | Backup script |

### Manual Backup

```bash
# Full backup
sudo ./scripts/backup.sh

# Database only
sudo -u postgres pg_dump pbx_system > backup_$(date +%Y%m%d).sql

# Configuration only
tar -czf config_backup_$(date +%Y%m%d).tar.gz config.yml .env
```

### Restore Procedure

```bash
# 1. Stop service
sudo systemctl stop pbx

# 2. Restore database
sudo -u postgres psql pbx_system < backup_YYYYMMDD.sql

# 3. Restore configuration
tar -xzf config_backup_YYYYMMDD.tar.gz

# 4. Start service
sudo systemctl start pbx

# 5. Verify
python3 scripts/production_health_check.py
```

### Disaster Recovery Test

```bash
# Run DR test (automated)
python3 scripts/test_disaster_recovery.py --test-type full

# Or follow manual procedure in DISASTER_RECOVERY.md
```

---

## Performance Tuning

### Database Optimization

```sql
-- Run vacuum and analyze
VACUUM ANALYZE;

-- Check slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Update statistics
ANALYZE;
```

### System Tuning

```bash
# Check current limits
ulimit -a

# Increase file descriptors (if needed)
# Edit /etc/security/limits.conf
# pbx  soft  nofile  65536
# pbx  hard  nofile  65536

# Apply changes
sudo sysctl -p
```

### Call Quality Optimization

```bash
# Check QoS settings
python3 scripts/verify_qos_fix.py

# Diagnose call quality
python3 scripts/diagnose_qos.py

# For detailed troubleshooting, see TROUBLESHOOTING.md
```

---

## Security Operations

### Security Checklist

- [ ] SSL certificates valid and renewed
- [ ] Firewall rules configured correctly
- [ ] Fail2ban active and monitoring
- [ ] All passwords rotated (quarterly)
- [ ] Security patches applied
- [ ] Audit logs reviewed (weekly)

### Certificate Renewal

```bash
# Check certificate expiration
python3 scripts/letsencrypt_manager.py --check

# Renew certificate (automated)
python3 scripts/letsencrypt_manager.py --renew

# Manual renewal
sudo certbot renew
sudo systemctl reload nginx  # or apache2
```

### Security Audit

```bash
# Run security compliance check
python3 scripts/security_compliance_check.py

# Run FIPS verification
python3 scripts/verify_fips.py

# Check for vulnerabilities
bandit -r pbx/ -f json -o security_report.json
```

### Rotate Credentials

```bash
# 1. Generate new database password
NEW_PASS=$(openssl rand -base64 32)

# 2. Update PostgreSQL
sudo -u postgres psql -c "ALTER USER pbx_user PASSWORD '$NEW_PASS';"

# 3. Update .env file
sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$NEW_PASS/" .env

# 4. Restart service
sudo systemctl restart pbx
```

---

## Troubleshooting Guide

### Service Won't Start

**Check 1: Port conflicts**
```bash
sudo netstat -tulpn | grep -E ':(5060|8080|10000:20000)'
```

**Check 2: Configuration errors**
```bash
python3 -c "import yaml; yaml.safe_load(open('config.yml'))"
```

**Check 3: Database connectivity**
```bash
python3 scripts/verify_database.py
```

**Check 4: Dependencies**
```bash
python3 -c "import yaml, cryptography, twisted, sqlalchemy"
```

### Calls Not Connecting

**Check 1: SIP registration**
```bash
curl http://localhost:8080/api/extensions
```

**Check 2: Network/firewall**
```bash
# SIP port
sudo netstat -tulpn | grep 5060

# RTP ports
sudo netstat -tulpn | grep -E '10000|11000|12000'
```

**Check 3: SIP trunk status** (if using external trunks)
```bash
# Check trunk configuration in config.yml
grep -A 10 "sip_trunks:" config.yml
```

### Poor Call Quality

**Check 1: QoS metrics**
```bash
python3 scripts/diagnose_qos.py
```

**Check 2: Network latency**
```bash
ping -c 10 <remote_ip>
mtr <remote_ip>
```

**Check 3: Codec negotiation**
```bash
# Check active call codec
curl http://localhost:8080/api/calls | grep codec
```

### Admin Panel Not Accessible

**Check 1: Web server status**
```bash
# If using nginx
sudo systemctl status nginx

# If using apache
sudo systemctl status apache2
```

**Check 2: API server status**
```bash
curl http://localhost:8080/health
```

**Check 3: Browser cache**
```
Press Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac) to hard refresh
```

### Database Performance Issues

**Check 1: Connection pool**
```sql
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE datname='pbx_system';
```

**Check 2: Lock contention**
```sql
SELECT * FROM pg_locks WHERE NOT granted;
```

**Check 3: Table bloat**
```sql
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Escalation Procedures

### When to Escalate

1. **Immediate Escalation (P0):**
   - Complete service outage >15 minutes
   - Data loss detected
   - Security breach suspected

2. **Standard Escalation (P1):**
   - Unable to resolve within SLA
   - Root cause unclear
   - Requires architectural changes

3. **Scheduled Escalation (P2/P3):**
   - Feature requests
   - Optimization needs
   - Documentation improvements

### Escalation Contacts

See [Emergency Contacts](#emergency-contacts) section above.

---

## Appendix

### Useful Commands Reference

```bash
# Service status
sudo systemctl status pbx
sudo systemctl is-active pbx

# Logs
sudo journalctl -u pbx -n 100
sudo journalctl -u pbx --since "1 hour ago"
tail -f /var/log/pbx/pbx.log

# Health checks
python3 scripts/production_health_check.py
python3 scripts/smoke_tests.py
python3 scripts/verify_database.py

# Monitoring
curl http://localhost:8080/api/status
curl http://localhost:8080/api/calls
curl http://localhost:8080/metrics  # Prometheus metrics

# Database
sudo -u postgres psql pbx_system
python3 scripts/verify_database.py

# Backups
sudo ./scripts/backup.sh
ls -lh /path/to/backups/
```

### Related Documentation

- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Comprehensive troubleshooting guide
- [COMPLETE_GUIDE.md](../COMPLETE_GUIDE.md) - Full system documentation
- [INCIDENT_RESPONSE_PLAYBOOK.md](INCIDENT_RESPONSE_PLAYBOOK.md) - Detailed incident procedures

---
