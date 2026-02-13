# Incident Response Playbook

---

## Table of Contents

1. [Overview](#overview)
2. [Incident Severity Levels](#incident-severity-levels)
3. [Emergency Contacts](#emergency-contacts)
4. [Common Incidents](#common-incidents)
5. [Incident Response Procedures](#incident-response-procedures)
6. [Post-Incident Review](#post-incident-review)

---

## Overview

This playbook provides step-by-step procedures for responding to incidents affecting the PBX system. Follow these procedures to minimize downtime and ensure rapid service restoration.

### Key Principles

- **Safety First**: Emergency calls (911) always take priority
- **Communicate**: Keep stakeholders informed
- **Document**: Log all actions taken during incidents
- **Learn**: Conduct post-incident reviews to prevent recurrence

---

## Incident Severity Levels

### Severity 1 (Critical) - Response Time: Immediate

**Impact**: Complete service outage affecting all users

**Examples**:
- PBX server completely down
- Database unavailable
- No incoming/outgoing calls possible
- 911 calls not working

**Response**:
- Escalate immediately to on-call engineer
- Notify management within 15 minutes
- Begin recovery within 5 minutes
- Page backup support if needed

### Severity 2 (High) - Response Time: 15 minutes

**Impact**: Major functionality degraded affecting most users

**Examples**:
- Voicemail system down
- Call quality severely degraded
- Intermittent call failures (>25% failure rate)
- Admin panel unavailable

**Response**:
- Contact on-call engineer
- Notify management within 30 minutes
- Begin investigation immediately
- Implement workaround if possible

### Severity 3 (Medium) - Response Time: 1 hour

**Impact**: Limited functionality affected, minor user impact

**Examples**:
- Single feature not working (e.g., call parking)
- Isolated call quality issues
- Non-critical integration failure
- Performance degradation (<25% impact)

**Response**:
- Log ticket and assign to support team
- Notify affected users
- Schedule fix during business hours
- Monitor for escalation

### Severity 4 (Low) - Response Time: Next business day

**Impact**: Cosmetic issues, no functional impact

**Examples**:
- UI display issues
- Non-critical log warnings
- Documentation errors
- Feature requests

**Response**:
- Log ticket for review
- Schedule for next maintenance window
- No immediate action required

---

## Emergency Contacts

### Primary On-Call

- **Name**: ___________________
- **Phone**: ___________________
- **Email**: ___________________
- **Hours**: 24/7

### Backup On-Call

- **Name**: ___________________
- **Phone**: ___________________
- **Email**: ___________________
- **Hours**: 24/7

### Management

- **IT Manager**: ___________________
- **Phone**: ___________________
- **Email**: ___________________

### Vendors

- **SIP Trunk Provider**: ___________________
- **Support Phone**: ___________________
- **Account Number**: ___________________

- **Internet Service Provider**: ___________________
- **Support Phone**: ___________________
- **Account Number**: ___________________

---

## Common Incidents

### 1. Complete System Outage

**Symptoms**: 
- No calls possible
- Admin panel unreachable
- SIP phones showing "No Service"

**Quick Diagnosis**:
```bash
# Check if PBX service is running
sudo systemctl status pbx

# Check if process is listening
sudo netstat -tlnp | grep :5060
sudo netstat -tlnp | grep :8080

# Check recent logs
sudo journalctl -u pbx -n 100 --no-pager
tail -100 /var/log/pbx/pbx.log
```

**Recovery Steps**:

1. **Immediate**: Check if service is running
   ```bash
   sudo systemctl status pbx
   ```

2. **If stopped**: Start the service
   ```bash
   sudo systemctl start pbx
   sudo systemctl status pbx
   ```

3. **If failed to start**: Check logs for errors
   ```bash
   sudo journalctl -u pbx -n 50 --no-pager
   tail -50 /var/log/pbx/pbx.log
   ```

4. **Common issues**:
   - Database connection failure → Check PostgreSQL
   - Port already in use → Find and kill conflicting process
   - Configuration error → Validate config.yml
   - Permission issues → Check file ownership

5. **If still failing**: Restore from last known good configuration
   ```bash
   sudo cp /path/to/backup/config.yml /path/to/pbx/config.yml
   sudo systemctl restart pbx
   ```

6. **Last resort**: Restore from backup
   - See [Disaster Recovery](#disaster-recovery-procedures) section

**Estimated Recovery Time**: 5-30 minutes

---

### 2. Database Connection Failure

**Symptoms**:
- "Database connection error" in logs
- Service starts but fails immediately
- Voicemail/CDR features not working

**Quick Diagnosis**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
psql -h localhost -U pbx_user -d pbx_system -c "SELECT 1;"

# Check database logs
sudo journalctl -u postgresql -n 50 --no-pager
```

**Recovery Steps**:

1. **Check PostgreSQL service**:
   ```bash
   sudo systemctl status postgresql
   sudo systemctl start postgresql  # if stopped
   ```

2. **Verify database exists**:
   ```bash
   sudo -u postgres psql -l | grep pbx_system
   ```

3. **Test connection with correct credentials**:
   ```bash
   psql -h localhost -U pbx_user -d pbx_system
   ```

4. **Check connection limits**:
   ```bash
   sudo -u postgres psql -c "SHOW max_connections;"
   sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
   ```

5. **If database is corrupted**:
   - Stop PBX service
   - Restore database from backup
   - Restart PBX service

**Estimated Recovery Time**: 10-60 minutes

---

### 3. No Incoming Calls

**Symptoms**:
- Outgoing calls work
- Incoming calls fail or don't ring
- SIP trunk registration issues

**Quick Diagnosis**:
```bash
# Check SIP trunk registration
# (Check admin panel or logs)
grep "REGISTER" /var/log/pbx/pbx.log | tail -20

# Test network connectivity to SIP provider
ping -c 4 sip-provider.example.com
traceroute sip-provider.example.com

# Check firewall rules
sudo iptables -L -n | grep 5060
sudo ufw status | grep 5060
```

**Recovery Steps**:

1. **Verify SIP trunk configuration**:
   - Check admin panel for trunk status
   - Verify credentials in config.yml
   - Check trunk provider's service status

2. **Check network connectivity**:
   ```bash
   # Can reach SIP provider?
   ping sip-provider.example.com
   
   # DNS resolution working?
   nslookup sip-provider.example.com
   ```

3. **Verify firewall allows SIP traffic**:
   ```bash
   sudo ufw allow 5060/udp
   sudo ufw reload
   ```

4. **Re-register with SIP trunk**:
   - Restart PBX service to force re-registration
   - Or use admin panel to trigger re-registration

5. **Contact SIP trunk provider**:
   - Verify account status
   - Check for service outages
   - Verify IP address is whitelisted

**Estimated Recovery Time**: 15-45 minutes

---

### 4. Poor Call Quality

**Symptoms**:
- Choppy audio
- One-way audio
- Echo or delay
- Calls dropping

**Quick Diagnosis**:
```bash
# Check system resources
top
free -h
df -h

# Check network statistics
netstat -s | grep -i error
netstat -s | grep -i drop

# Check QoS metrics (if monitoring enabled)
curl -k https://localhost:8080/api/qos/statistics
```

**Recovery Steps**:

1. **Check system resources**:
   ```bash
   # CPU usage
   top -b -n 1 | head -20
   
   # Memory usage
   free -h
   
   # Disk space
   df -h
   ```

2. **Check network quality**:
   ```bash
   # Packet loss test
   ping -c 100 8.8.8.8 | grep loss
   
   # Jitter test (requires mtr)
   mtr -r -c 100 sip-provider.example.com
   ```

3. **Verify QoS settings**:
   - Check if DSCP tagging is enabled
   - Verify router QoS configuration
   - Check for bandwidth saturation

4. **Adjust codec settings**:
   - Switch to lower bandwidth codec (G.729 instead of G.711)
   - Disable HD codecs if network is congested
   - Edit config.yml and restart service

5. **Check for network issues**:
   - Contact ISP if packet loss >1%
   - Check for local network problems
   - Verify no heavy downloads in progress

**Estimated Recovery Time**: 30-120 minutes (depends on root cause)

---

### 5. Voicemail System Failure

**Symptoms**:
- Cannot leave voicemail
- Cannot retrieve voicemail
- Voicemail emails not sending

**Quick Diagnosis**:
```bash
# Check voicemail directory
ls -lh /path/to/pbx/voicemail/

# Check disk space
df -h /path/to/pbx/voicemail/

# Check voicemail permissions
ls -ld /path/to/pbx/voicemail/

# Check SMTP configuration (for email)
grep -A 10 "smtp:" config.yml
```

**Recovery Steps**:

1. **Check disk space**:
   ```bash
   df -h /path/to/pbx/voicemail/
   ```
   - If full, delete old voicemails or expand storage

2. **Verify directory permissions**:
   ```bash
   sudo chown -R pbx:pbx /path/to/pbx/voicemail/
   sudo chmod 755 /path/to/pbx/voicemail/
   ```

3. **Check voicemail prompts exist**:
   ```bash
   ls -lh /path/to/pbx/voicemail_prompts/
   ```
   - If missing, regenerate prompts

4. **For email issues**:
   - Verify SMTP configuration in config.yml
   - Test SMTP connectivity
   - Check email logs

5. **Restart service**:
   ```bash
   sudo systemctl restart pbx
   ```

**Estimated Recovery Time**: 15-30 minutes

---

### 6. Admin Panel Unreachable

**Symptoms**:
- Cannot access https://hostname:8080/admin/
- Connection timeout or refused
- SSL certificate errors

**Quick Diagnosis**:
```bash
# Check if API service is listening
sudo netstat -tlnp | grep :8080

# Check SSL certificate
openssl s_client -connect localhost:8080 -servername hostname

# Check firewall
sudo ufw status | grep 8080

# Check nginx/reverse proxy (if used)
sudo systemctl status nginx
```

**Recovery Steps**:

1. **Verify service is running**:
   ```bash
   sudo systemctl status pbx
   sudo netstat -tlnp | grep :8080
   ```

2. **Check SSL certificate**:
   ```bash
   # Verify certificate exists and is valid
   openssl x509 -in /path/to/ssl/pbx.crt -text -noout
   ```

3. **Check firewall rules**:
   ```bash
   sudo ufw allow 8080/tcp
   sudo ufw reload
   ```

4. **If using reverse proxy**:
   ```bash
   # Check nginx/apache
   sudo systemctl status nginx
   sudo nginx -t  # test configuration
   sudo systemctl restart nginx
   ```

5. **Check browser console for errors**:
   - Press F12 in browser
   - Look for JavaScript or network errors
   - Clear browser cache (Ctrl+Shift+R)

**Estimated Recovery Time**: 10-30 minutes

---

### 7. High CPU/Memory Usage

**Symptoms**:
- System slow or unresponsive
- Calls dropping
- High load average

**Quick Diagnosis**:
```bash
# Check system load
top -b -n 1 | head -20
uptime

# Check PBX process
ps aux | grep python | grep main.py

# Check memory usage
free -h

# Check for memory leaks
ps aux --sort=-rss | head -10
```

**Recovery Steps**:

1. **Identify resource hog**:
   ```bash
   top -b -n 1 | head -20
   ```

2. **Check for runaway processes**:
   ```bash
   # Find processes using most CPU
   ps aux --sort=-pcpu | head -10
   
   # Find processes using most memory
   ps aux --sort=-rss | head -10
   ```

3. **If PBX is consuming excessive resources**:
   - Check number of active calls
   - Check for call loops or stuck calls
   - Restart service if necessary

4. **Clear system cache** (if safe):
   ```bash
   sync
   sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
   ```

5. **Restart PBX service**:
   ```bash
   sudo systemctl restart pbx
   ```

6. **If problem persists**:
   - Review recent configuration changes
   - Check for memory leaks in logs
   - Consider scaling up resources

**Estimated Recovery Time**: 5-60 minutes

---

## Incident Response Procedures

### General Incident Response Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. DETECT                                                │
│    - Alert received or issue reported                    │
│    - Log incident in tracking system                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. ASSESS                                                │
│    - Determine severity level                            │
│    - Identify affected systems/users                     │
│    - Estimate impact                                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. ESCALATE (if needed)                                  │
│    - Contact on-call engineer                            │
│    - Notify management for Sev 1/2                       │
│    - Assemble incident response team                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. COMMUNICATE                                           │
│    - Notify affected users                               │
│    - Post status updates                                 │
│    - Keep stakeholders informed                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. INVESTIGATE & DIAGNOSE                                │
│    - Check logs and metrics                              │
│    - Run diagnostic commands                             │
│    - Identify root cause                                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 6. RESOLVE                                               │
│    - Execute recovery procedures                         │
│    - Implement workaround if needed                      │
│    - Verify service restoration                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 7. VERIFY                                                │
│    - Test all affected functionality                     │
│    - Confirm users can make/receive calls               │
│    - Monitor for recurrence                              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 8. DOCUMENT                                              │
│    - Complete incident report                            │
│    - Document root cause and resolution                  │
│    - Update knowledge base                               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 9. POST-MORTEM                                           │
│    - Conduct lessons learned session                     │
│    - Identify preventive actions                         │
│    - Update procedures and documentation                 │
└─────────────────────────────────────────────────────────┘
```

### Communication Templates

#### Initial Notification (Sev 1/2)

```
Subject: [SEV {1|2}] PBX System Incident - {Brief Description}

INCIDENT DETAILS:
- Incident ID: {INCIDENT-YYYY-MM-DD-NNN}
- Severity: {1|2}
- Start Time: {YYYY-MM-DD HH:MM} UTC
- Impact: {Description of user impact}
- Affected Services: {List of affected services}

STATUS:
{Current status - investigating, identified, resolving, etc.}

NEXT UPDATE:
Next update expected in {time period}

Contact: {On-call engineer name and contact}
```

#### Status Update

```
Subject: [UPDATE] {Incident ID} - PBX System Incident

UPDATE as of {HH:MM} UTC:

ACTIONS TAKEN:
- {List of actions taken}

CURRENT STATUS:
{Current status and progress}

NEXT STEPS:
- {Planned next steps}

ESTIMATED RESOLUTION:
{ETA for resolution}

Next update in {time period}
```

#### Resolution Notice

```
Subject: [RESOLVED] {Incident ID} - PBX System Incident

INCIDENT RESOLVED as of {HH:MM} UTC

SUMMARY:
{Brief summary of incident}

ROOT CAUSE:
{Description of root cause}

RESOLUTION:
{Description of how it was resolved}

PREVENTIVE ACTIONS:
{Actions taken to prevent recurrence}

POST-MORTEM:
A detailed post-mortem will be conducted on {date}

Thank you for your patience during this incident.
```

---

## Disaster Recovery Procedures

### Complete System Failure

If the PBX system cannot be recovered:

1. **Activate Backup System** (if available):
   - Switch DNS to backup server
   - Activate backup SIP trunks
   - Notify users of temporary number changes

2. **Restore from Backup**:
   ```bash
   # Restore database
   sudo -u postgres psql pbx_system < /backups/pbx-backup-latest.sql
   
   # Restore configuration
   sudo cp /backups/config.yml /path/to/pbx/config.yml
   sudo cp /backups/.env /path/to/pbx/.env
   
   # Restore voicemail
   sudo rsync -avz /backups/voicemail/ /path/to/pbx/voicemail/
   
   # Restart service
   sudo systemctl restart pbx
   ```

3. **Verify Functionality**:
   - Test inbound calls
   - Test outbound calls
   - Test voicemail
   - Test admin panel

4. **Monitor Closely**:
   - Watch logs for errors
   - Monitor call quality
   - Track user reports

### Hardware Failure

1. **Identify Failed Component**:
   - Server hardware
   - Network equipment
   - Storage device

2. **Implement Temporary Solution**:
   - Failover to backup hardware
   - Reroute traffic through alternate path
   - Use cloud/virtual instance temporarily

3. **Restore Service**:
   - Repair or replace failed hardware
   - Restore from backups
   - Migrate back to primary system

4. **Test Thoroughly** before putting back in production

---

## Post-Incident Review

After every Severity 1 or 2 incident, conduct a post-incident review:

### Review Meeting (Within 48 hours)

**Attendees**:
- Incident responders
- IT management
- Affected stakeholders

**Agenda**:
1. **Timeline Review**: Walk through incident timeline
2. **Root Cause Analysis**: Identify underlying cause
3. **Response Assessment**: What went well? What didn't?
4. **Action Items**: Preventive measures and improvements

### Post-Incident Report Template

```
INCIDENT POST-MORTEM REPORT

Incident ID: {INCIDENT-YYYY-MM-DD-NNN}
Date: {YYYY-MM-DD}
Duration: {X hours Y minutes}
Severity: {1|2|3}

SUMMARY:
{Brief description of incident}

IMPACT:
- Affected Users: {number/percentage}
- Services Down: {list}
- Revenue Impact: {if applicable}
- Duration: {time}

TIMELINE:
{HH:MM} - {Event description}
{HH:MM} - {Event description}
...

ROOT CAUSE:
{Detailed explanation of what caused the incident}

CONTRIBUTING FACTORS:
- {Factor 1}
- {Factor 2}

WHAT WENT WELL:
- {Positive aspect 1}
- {Positive aspect 2}

WHAT WENT POORLY:
- {Issue 1}
- {Issue 2}

ACTION ITEMS:
[Priority: High/Medium/Low] [Owner] [Due Date] {Action Description}
...

LESSONS LEARNED:
- {Lesson 1}
- {Lesson 2}

PREVENTIVE MEASURES:
- {Measure 1}
- {Measure 2}

Prepared by: {Name}
Reviewed by: {Name}
Date: {YYYY-MM-DD}
```

---

## Appendix

### Useful Commands Reference

```bash
# Service management
sudo systemctl status pbx
sudo systemctl start pbx
sudo systemctl stop pbx
sudo systemctl restart pbx
sudo systemctl reload pbx
sudo journalctl -u pbx -f

# Process management
ps aux | grep python | grep main.py
sudo kill -HUP {PID}
sudo kill -9 {PID}

# Network diagnostics
sudo netstat -tlnp | grep :5060
sudo netstat -tlnp | grep :8080
sudo tcpdump -i any -n port 5060
sudo lsof -i :5060

# Database
sudo systemctl status postgresql
sudo -u postgres psql pbx_system
psql -h localhost -U pbx_user -d pbx_system

# Logs
tail -f /var/log/pbx/pbx.log
sudo journalctl -u pbx -n 100 --no-pager
grep ERROR /var/log/pbx/pbx.log | tail -20

# System resources
top
htop
free -h
df -h
iostat
vmstat 1

# Backups
pg_dump -U pbx_user pbx_system > backup.sql
tar -czf voicemail-backup.tar.gz voicemail/
```

### Emergency Bypass Procedures

If PBX is completely unavailable and calls must continue:

1. **Redirect at Trunk Level**:
   - Contact SIP trunk provider
   - Redirect calls to backup number
   - Use provider's call forwarding

2. **Use Backup System**:
   - Activate standby PBX server
   - Update DNS records
   - Notify users of any changes

3. **Temporary Call Forwarding**:
   - Forward main numbers to cell phones
   - Use cloud-based temporary solution
   - Rent emergency trunk service

---

**Document Control**:
- **Version**: 1.0.0
- **Last Updated**: January 2, 2026
- **Next Review**: Quarterly
- **Owner**: IT Operations Team
