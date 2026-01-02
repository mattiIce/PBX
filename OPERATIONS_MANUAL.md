# Production Operations Manual

**Last Updated**: January 2, 2026  
**Version**: 1.0.0  
**Purpose**: Day-to-day operations guide for production PBX system

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Weekly Tasks](#weekly-tasks)
3. [Monthly Tasks](#monthly-tasks)
4. [Common Administrative Tasks](#common-administrative-tasks)
5. [Monitoring and Alerts](#monitoring-and-alerts)
6. [Backup and Recovery](#backup-and-recovery)
7. [Performance Tuning](#performance-tuning)
8. [Security Operations](#security-operations)

---

## Daily Operations

### Morning Health Check (< 10 minutes)

**Frequency**: Every business day at start of shift

**Procedure**:

1. **Run Health Monitor**:
   ```bash
   python3 scripts/health_monitor.py --format html --output /tmp/health-report.html
   ```
   Review the report for any critical issues or warnings.

2. **Check Service Status**:
   ```bash
   sudo systemctl status pbx
   ```
   Verify the service is active and running.

3. **Verify Call Processing**:
   - Make a test call to verify inbound routing
   - Make a test call to verify outbound routing
   - Check voicemail deposit and retrieval
   - Verify admin panel is accessible

4. **Review Overnight Logs**:
   ```bash
   # Check for errors in the last 24 hours
   grep -i error /var/log/pbx/pbx.log | tail -50
   
   # Check for critical events
   grep -i critical /var/log/pbx/pbx.log | tail -20
   ```

5. **Check Disk Space**:
   ```bash
   df -h | grep -E '(Filesystem|pbx|voicemail|recordings)'
   ```
   Alert if any partition is > 80% full.

6. **Review Active Calls** (via admin panel):
   - Check for stuck or long-duration calls
   - Verify call quality metrics (MOS scores)

7. **Check SIP Trunk Status** (via admin panel):
   - Verify all trunks are registered
   - Check trunk health metrics

**Expected Time**: 5-10 minutes

---

### End of Day Review (< 5 minutes)

**Frequency**: End of each business day

**Procedure**:

1. **Review Call Statistics**:
   ```bash
   # Via API
   curl -k https://localhost:8080/api/statistics
   ```
   or check admin panel Analytics tab

2. **Check for Alerts**:
   - Review any email alerts received during the day
   - Check monitoring dashboard for trends

3. **Verify Backup Completion**:
   ```bash
   ls -lh /var/backups/pbx/ | tail -5
   ```

**Expected Time**: 5 minutes

---

## Weekly Tasks

### Weekly System Review (< 30 minutes)

**Frequency**: Once per week (recommended: Monday morning)

**Procedure**:

1. **Review System Performance**:
   ```bash
   # CPU and memory trends
   sar -u 1 10  # CPU usage
   sar -r 1 10  # Memory usage
   
   # Disk I/O
   iostat -x 1 5
   ```

2. **Analyze Call Quality Trends**:
   - Review QoS metrics for the past week
   - Identify any patterns in poor call quality
   - Check for network issues

3. **Review Security Logs**:
   ```bash
   # Failed login attempts
   grep "authentication failed" /var/log/pbx/pbx.log | wc -l
   
   # Blocked IPs
   grep "IP blocked" /var/log/pbx/pbx.log | tail -20
   ```

4. **Update System Packages** (if applicable):
   ```bash
   sudo apt update
   sudo apt list --upgradable
   
   # Review upgrades and apply if safe
   sudo apt upgrade -y
   ```

5. **Test Backup Restoration**:
   - Randomly select a backup
   - Test database restoration to test environment
   - Verify file integrity

6. **Review Voicemail Storage**:
   ```bash
   # Find old voicemails (> 90 days)
   find /path/to/voicemail -type f -mtime +90 -ls
   
   # Clean up if necessary
   ```

7. **Check Call Detail Records (CDR)**:
   - Review call patterns
   - Identify any anomalies
   - Export weekly statistics for reporting

**Expected Time**: 20-30 minutes

---

## Monthly Tasks

### Monthly Maintenance (< 2 hours)

**Frequency**: First Saturday of each month (or low-traffic time)

**Procedure**:

1. **Database Maintenance**:
   ```bash
   # Vacuum and analyze database
   sudo -u postgres psql pbx_system -c "VACUUM ANALYZE;"
   
   # Check database size
   sudo -u postgres psql pbx_system -c "SELECT pg_size_pretty(pg_database_size('pbx_system'));"
   
   # Check for bloat
   sudo -u postgres psql pbx_system -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"
   ```

2. **Log Rotation Verification**:
   ```bash
   # Check logrotate is working
   sudo logrotate -d /etc/logrotate.d/pbx
   
   # Verify old logs are compressed
   ls -lh /var/log/pbx/*.gz | tail -10
   ```

3. **Certificate Expiration Check**:
   ```bash
   # Check SSL certificate expiration
   openssl x509 -in /path/to/ssl/pbx.crt -noout -enddate
   
   # Calculate days until expiration
   python3 scripts/health_monitor.py --format json | jq '.checks.ssl'
   ```

4. **Security Audit**:
   ```bash
   # Run FIPS verification
   python3 scripts/verify_fips.py
   
   # Run production readiness validation
   python3 scripts/validate_production_readiness.py
   ```

5. **Performance Baseline**:
   - Run load test
   - Document maximum concurrent calls
   - Measure API response times
   - Update capacity planning documentation

6. **Review and Update Documentation**:
   - Update network diagrams if changes made
   - Review and update troubleshooting guides
   - Update contact lists and escalation procedures

7. **SIP Trunk Provider Review**:
   - Verify billing matches usage
   - Review call quality metrics
   - Check for better pricing options

**Expected Time**: 1-2 hours

---

## Common Administrative Tasks

### Adding a New Extension

**Procedure**:

1. **Via Admin Panel** (Recommended):
   - Log into admin panel: https://your-pbx:8080/admin/
   - Go to "Extensions" tab
   - Click "Add Extension"
   - Fill in details:
     - Extension number (e.g., 1005)
     - User name
     - Email address (for voicemail)
     - Password (minimum 12 characters)
     - Admin privileges (if needed)
   - Click "Save"

2. **Via API**:
   ```bash
   curl -X POST https://localhost:8080/api/extensions \
     -H "Content-Type: application/json" \
     -d '{
       "number": "1005",
       "name": "John Doe",
       "email": "john.doe@company.com",
       "password": "SecurePassword123!",
       "allow_external": true,
       "is_admin": false
     }'
   ```

3. **Verification**:
   - Test SIP registration with new credentials
   - Make test call to/from new extension
   - Verify voicemail works

---

### Provisioning a New IP Phone

**Procedure**:

1. **Gather Information**:
   - Phone model and MAC address
   - Extension number to assign
   - Network location (for VLAN/QoS)

2. **Configure Phone Provisioning**:
   ```bash
   # Generate configuration (automatic via templates)
   curl -k https://localhost:8080/api/provisioning/{mac_address}
   ```

3. **Phone Configuration**:
   - **Option A** (Auto-provisioning):
     - Set DHCP option 66 to point to PBX server
     - Phone will auto-download configuration
   
   - **Option B** (Manual):
     - Access phone's web interface
     - Configure SIP server: your-pbx-server:5060
     - Enter extension credentials
     - Set codec preferences: G.711 (PCMU/PCMA)

4. **Verification**:
   - Check phone registration in admin panel
   - Make test call
   - Verify features (transfer, hold, conference)

---

### Modifying Voicemail Settings

**Procedure**:

1. **Update SMTP Configuration** (via admin panel):
   - Go to "Configuration" tab
   - Update SMTP settings:
     - Host, port, username, password
     - From address and name
   - Click "Save"

2. **Test Email Delivery**:
   - Leave a test voicemail
   - Verify email is received
   - Check email has audio attachment

3. **Adjust No-Answer Timeout** (in config.yml):
   ```yaml
   voicemail:
     no_answer_timeout: 30  # seconds
   ```
   Restart service after changes:
   ```bash
   sudo systemctl restart pbx
   ```

---

### Adding a SIP Trunk

**Procedure**:

1. **Gather Provider Information**:
   - SIP server address
   - Authentication credentials
   - Allowed codecs
   - DID numbers

2. **Update Configuration** (config.yml):
   ```yaml
   sip_trunks:
     - name: "Primary Trunk"
       host: "sip.provider.com"
       port: 5060
       username: "your-account"
       password: "your-password"
       priority: 1
       enabled: true
   ```

3. **Restart Service**:
   ```bash
   sudo systemctl restart pbx
   ```

4. **Verify Registration**:
   - Check admin panel for trunk status
   - Review logs:
     ```bash
     grep "REGISTER" /var/log/pbx/pbx.log | grep "sip.provider.com"
     ```

5. **Test Calls**:
   - Make outbound call
   - Make inbound call (if DID configured)

---

## Monitoring and Alerts

### Alert Response

**Email Alert Received**:

1. **Assess Severity**:
   - Read alert message
   - Determine impact (service down, degraded, etc.)

2. **Acknowledge Alert**:
   - Log into monitoring system
   - Acknowledge alert to prevent duplicate notifications

3. **Investigate**:
   - Follow troubleshooting guide for specific alert type
   - Check logs and metrics
   - Identify root cause

4. **Resolve**:
   - Execute fix procedure
   - Verify service restoration
   - Close alert

5. **Document**:
   - Update incident log
   - Note resolution steps
   - Identify preventive actions

---

### Monitoring Dashboard Access

**Grafana** (if configured):
- URL: https://your-pbx:3000
- Default login: admin / configured-password
- Key dashboards:
  - PBX System Overview
  - Call Quality Metrics
  - Resource Utilization
  - SIP Trunk Status

**Admin Panel**:
- URL: https://your-pbx:8080/admin/
- Built-in monitoring:
  - Active calls
  - Extension status
  - System statistics
  - Quality metrics

---

## Backup and Recovery

### Manual Backup

**When to use**: Before major changes, on-demand backups

**Procedure**:
```bash
# Full backup
sudo ./scripts/backup.sh --full --destination /mnt/backup-drive

# Incremental backup (last 30 days of recordings)
sudo ./scripts/backup.sh --incremental
```

**Verification**:
```bash
# List recent backups
ls -lh /var/backups/pbx/

# Verify backup integrity
tar -tzf /var/backups/pbx/pbx_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

### Database Restore

**Procedure**:

1. **Stop PBX Service**:
   ```bash
   sudo systemctl stop pbx
   ```

2. **Restore Database**:
   ```bash
   # Extract backup
   tar -xzf /var/backups/pbx/pbx_backup_YYYYMMDD_HHMMSS.tar.gz
   
   # Drop existing database (WARNING!)
   sudo -u postgres psql -c "DROP DATABASE pbx_system;"
   
   # Create new database
   sudo -u postgres psql -c "CREATE DATABASE pbx_system OWNER pbx_user;"
   
   # Restore from backup
   sudo -u postgres psql pbx_system < YYYYMMDD_HHMMSS/database/pbx_database.sql
   ```

3. **Restart PBX Service**:
   ```bash
   sudo systemctl start pbx
   sudo systemctl status pbx
   ```

4. **Verify**:
   - Check logs for errors
   - Test calls
   - Verify extensions

---

## Performance Tuning

### Database Optimization

**When**: Monthly or when performance degrades

**Procedure**:

1. **Analyze Query Performance**:
   ```sql
   -- Find slow queries
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

2. **Optimize Tables**:
   ```bash
   sudo -u postgres psql pbx_system -c "VACUUM FULL ANALYZE;"
   ```

3. **Update Statistics**:
   ```sql
   ANALYZE;
   ```

4. **Check Indexes**:
   ```sql
   -- Missing indexes
   SELECT schemaname, tablename, attname
   FROM pg_stats
   WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
   AND n_distinct > 100
   ORDER BY n_distinct DESC;
   ```

---

### System Resource Optimization

**CPU Optimization**:
- Review process priorities
- Consider CPU affinity for PBX process
- Monitor for CPU-intensive operations

**Memory Optimization**:
- Adjust PostgreSQL shared_buffers
- Review Python process memory usage
- Enable swap if not already configured

**Network Optimization**:
- Enable QoS/DSCP marking
- Verify MTU settings (1500 for Ethernet)
- Check for packet loss/jitter

---

## Security Operations

### Security Patch Management

**Procedure**:

1. **Check for Updates**:
   ```bash
   sudo apt update
   sudo apt list --upgradable
   ```

2. **Review Security Updates**:
   ```bash
   sudo apt list --upgradable | grep security
   ```

3. **Apply Critical Security Patches**:
   ```bash
   # Apply immediately for critical issues
   sudo apt install [package-name]
   
   # Restart affected services
   sudo systemctl restart pbx  # if needed
   ```

4. **Schedule Non-Critical Updates**:
   - Plan maintenance window
   - Notify users
   - Apply updates and test

---

### Access Control Review

**Frequency**: Monthly

**Procedure**:

1. **Review User Accounts**:
   ```bash
   # List all extensions
   curl -k https://localhost:8080/api/extensions
   ```

2. **Disable Inactive Accounts**:
   - Identify users who haven't logged in > 90 days
   - Disable or delete accounts via admin panel

3. **Review Admin Access**:
   - Verify list of admin users
   - Remove admin access if no longer needed

4. **Check Failed Login Attempts**:
   ```bash
   grep "authentication failed" /var/log/pbx/pbx.log | tail -50
   ```

5. **Review Firewall Rules**:
   ```bash
   sudo ufw status
   ```

---

## Appendix

### Quick Reference Commands

```bash
# Service management
sudo systemctl status pbx
sudo systemctl restart pbx
sudo systemctl stop pbx
sudo systemctl start pbx

# View logs
tail -f /var/log/pbx/pbx.log
journalctl -u pbx -f

# Check ports
sudo netstat -tlnp | grep -E '(5060|8080)'

# Database access
sudo -u postgres psql pbx_system

# Health check
python3 scripts/health_monitor.py

# Validation
python3 scripts/validate_production_readiness.py

# Backup
sudo ./scripts/backup.sh --full
```

---

### Escalation Contacts

| Role | Name | Phone | Email | Hours |
|------|------|-------|-------|-------|
| Primary On-Call | ______ | ______ | ______ | 24/7 |
| Backup On-Call | ______ | ______ | ______ | 24/7 |
| IT Manager | ______ | ______ | ______ | Business Hours |
| Network Admin | ______ | ______ | ______ | Business Hours |
| Database Admin | ______ | ______ | ______ | Business Hours |

---

**Document Version**: 1.0.0  
**Last Updated**: January 2, 2026  
**Next Review**: Quarterly  
**Owner**: IT Operations Team
