# Production Operations Runbook

This runbook provides step-by-step procedures for common operational tasks in a production PBX environment.

## Table of Contents
- [Daily Operations](#daily-operations)
- [Health Monitoring](#health-monitoring)
- [Common Issues](#common-issues)
- [Emergency Procedures](#emergency-procedures)
- [Maintenance Tasks](#maintenance-tasks)

## Daily Operations

### Morning Health Check
```bash
#!/bin/bash
# Save as: scripts/daily_health_check.sh

echo "=== PBX Daily Health Check ==="
echo "Date: $(date)"
echo ""

# 1. Check service status
echo "1. Service Status:"
systemctl is-active pbx && echo "  ✓ Service is running" || echo "  ✗ Service is DOWN"
echo ""

# 2. Check health endpoints
echo "2. Health Endpoints:"
curl -s http://localhost:8080/live | jq -r '.status' | grep -q "alive" && \
  echo "  ✓ Liveness check passed" || echo "  ✗ Liveness check FAILED"

curl -s http://localhost:8080/ready | jq -r '.status' | grep -q "ready" && \
  echo "  ✓ Readiness check passed" || echo "  ✗ Readiness check FAILED"
echo ""

# 3. Check system resources
echo "3. System Resources:"
cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print 100 - $8"%"}')
mem=$(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100}')
disk=$(df -h / | awk 'NR==2 {print $5}')

echo "  CPU Usage: $cpu"
echo "  Memory Usage: $mem"
echo "  Disk Usage: $disk"
echo ""

# 4. Check PBX stats
echo "4. PBX Statistics:"
stats=$(curl -s http://localhost:8080/api/status)
echo "  Active Calls: $(echo $stats | jq -r '.active_calls')"
echo "  Registered Extensions: $(echo $stats | jq -r '.registered_extensions')"
echo ""

# 5. Check recent errors
echo "5. Recent Errors (last hour):"
error_count=$(journalctl -u pbx --since "1 hour ago" -p err | wc -l)
echo "  Error count: $error_count"
if [ $error_count -gt 0 ]; then
    echo "  Recent errors:"
    journalctl -u pbx --since "1 hour ago" -p err --no-pager | tail -5
fi
echo ""

# 6. Check database
echo "6. Database Status:"
sudo -u postgres psql -d pbx_system -c "SELECT 1" >/dev/null 2>&1 && \
  echo "  ✓ Database is accessible" || echo "  ✗ Database is DOWN"
echo ""

# 7. Check backups
echo "7. Backup Status:"
if [ -f /var/backups/pbx/latest.sql.gz ]; then
    backup_age=$(find /var/backups/pbx/latest.sql.gz -mtime -1 | wc -l)
    if [ $backup_age -eq 1 ]; then
        echo "  ✓ Backup is recent (< 24 hours)"
    else
        echo "  ⚠ Backup is old (> 24 hours)"
    fi
else
    echo "  ✗ No backup found"
fi
echo ""

echo "=== End of Health Check ==="
```

### Evening Status Report
```bash
#!/bin/bash
# Save as: scripts/daily_status_report.sh

echo "=== PBX Daily Status Report ==="
echo "Date: $(date)"
echo ""

# Get call statistics for today
echo "Call Statistics (today):"
curl -s "http://localhost:8080/api/analytics/advanced?date_from=$(date +%Y-%m-%d)&date_to=$(date +%Y-%m-%d)" | jq

# Get QoS metrics
echo ""
echo "Quality of Service Metrics:"
curl -s http://localhost:8080/api/qos/statistics | jq

# Get system uptime
echo ""
echo "System Uptime:"
uptime

echo ""
echo "=== End of Status Report ==="
```

## Health Monitoring

### Check Overall System Health
```bash
# Comprehensive health check
curl -s http://localhost:8080/api/health/detailed | jq

# Expected output:
# {
#   "overall_status": "healthy",
#   "liveness": { "status": "alive", ... },
#   "readiness": { 
#     "status": "ready",
#     "checks": {
#       "pbx_core": { "status": "operational", ... },
#       "database": { "status": "connected", ... },
#       "sip_server": { "status": "port_in_use", ... },
#       "system_resources": { "status": "ok", ... }
#     }
#   },
#   "metrics": { ... }
# }
```

### Monitor Specific Components

#### PBX Core
```bash
# Check PBX status
curl http://localhost:8080/api/status | jq

# Check active calls
curl http://localhost:8080/api/calls | jq

# Check registered extensions
curl http://localhost:8080/api/extensions | jq
```

#### Database
```bash
# Test database connection
sudo -u postgres psql -d pbx_system -c "SELECT version();"

# Check database size
sudo -u postgres psql -d pbx_system -c "
SELECT pg_size_pretty(pg_database_size('pbx_system')) as size;
"

# Check active connections
sudo -u postgres psql -d pbx_system -c "
SELECT count(*) FROM pg_stat_activity 
WHERE datname = 'pbx_system';
"
```

#### System Resources
```bash
# CPU and memory
free -h
top -bn1 | head -20

# Disk usage
df -h

# Network connections
ss -tuln | grep -E ':(5060|8080)'

# Process stats
ps aux | grep python | grep -v grep
```

### Prometheus Metrics
```bash
# Get Prometheus-format metrics
curl http://localhost:8080/metrics

# Example metrics:
# pbx_health 1
# pbx_uptime_seconds 86400.5
# pbx_active_calls 5
# pbx_registered_extensions 12
# pbx_system_cpu_percent 15.2
# pbx_system_memory_percent 45.8
```

## Common Issues

### Issue: Service Won't Start

**Symptoms**: `systemctl start pbx` fails

**Diagnosis**:
```bash
# Check service status
sudo systemctl status pbx

# View recent logs
sudo journalctl -u pbx -n 100 --no-pager

# Check for port conflicts
sudo ss -tuln | grep -E ':(5060|8080)'

# Validate configuration
source /path/to/venv/bin/activate
python -c "from pbx.utils.config import Config; Config('config.yml')"
```

**Resolution**:
1. Check logs for specific error message
2. If port is in use, find and stop conflicting process
3. If config is invalid, fix errors in config.yml
4. If database connection fails, verify database is running
5. Restart service: `sudo systemctl restart pbx`

### Issue: High CPU Usage

**Symptoms**: CPU usage > 80%

**Diagnosis**:
```bash
# Check process CPU usage
top -p $(pgrep -f "python.*main.py")

# Check active calls
curl http://localhost:8080/api/calls | jq '. | length'

# Check for infinite loops in logs
sudo journalctl -u pbx --since "10 minutes ago" | grep -i error
```

**Resolution**:
1. If high call volume, consider scaling horizontally
2. If memory leak suspected, restart service
3. If specific feature causing issue, check feature logs
4. Monitor after restart to confirm resolution

### Issue: Extensions Not Registering

**Symptoms**: Phones can't register to PBX

**Diagnosis**:
```bash
# Check SIP server is listening
sudo ss -uln | grep 5060

# Check firewall
sudo ufw status | grep 5060

# Check phone configuration
# - Verify IP address is correct
# - Verify port is 5060
# - Verify credentials match config.yml

# Check PBX logs for registration attempts
sudo journalctl -u pbx | grep -i register | tail -20
```

**Resolution**:
1. Verify SIP port (5060) is open in firewall
2. Verify network connectivity from phone to server
3. Check extension credentials in config.yml
4. Restart phone and PBX if needed

### Issue: No Audio in Calls

**Symptoms**: Calls connect but no audio

**Diagnosis**:
```bash
# Check RTP ports are open
sudo ufw status | grep 10000:20000

# Check for firewall blocking RTP
sudo iptables -L -n | grep -E '10000|20000'

# Check codec compatibility
curl http://localhost:8080/api/config | jq '.codecs'

# Check for NAT/routing issues
# - Verify external_ip in config.yml is correct
```

**Resolution**:
1. Open RTP port range in firewall (10000-20000 UDP)
2. Verify external_ip setting in config.yml
3. Check codec configuration (G.711 should be enabled)
4. Review QoS metrics: `curl http://localhost:8080/api/qos/statistics`

### Issue: Database Connection Failures

**Symptoms**: Health check shows database error

**Diagnosis**:
```bash
# Test database connection
sudo -u postgres psql -d pbx_system -c "SELECT 1;"

# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials
cat .env | grep DB_

# Check connection limit
sudo -u postgres psql -c "SHOW max_connections;"
```

**Resolution**:
1. Restart PostgreSQL: `sudo systemctl restart postgresql`
2. Verify database credentials in .env file
3. Check PostgreSQL logs: `sudo journalctl -u postgresql`
4. Increase max_connections if needed (pg_hba.conf)

### Issue: High Memory Usage

**Symptoms**: Memory usage > 90%

**Diagnosis**:
```bash
# Check memory usage
free -h

# Check PBX process memory
ps aux | grep python | grep -v grep

# Check for memory leaks
# Monitor over time to see if memory grows continuously
watch -n 60 'free -h'
```

**Resolution**:
1. Restart service to clear memory: `sudo systemctl restart pbx`
2. Check for memory leaks in logs
3. Consider increasing server RAM if sustained high usage
4. Optimize database queries if database is consuming memory

## Emergency Procedures

### Emergency Restart
```bash
# Quick restart when service is unresponsive
sudo systemctl restart pbx

# Force kill if restart hangs
sudo pkill -9 -f "python.*main.py"
sudo systemctl start pbx

# Verify restart
sudo systemctl status pbx
curl http://localhost:8080/api/status
```

### Database Recovery
```bash
# Stop PBX
sudo systemctl stop pbx

# Restore from latest backup
cd /var/backups/pbx
latest=$(ls -t *.sql.gz | head -1)
gunzip < $latest | sudo -u postgres psql -d pbx_system

# Start PBX
sudo systemctl start pbx

# Verify
curl http://localhost:8080/api/status
```

### Rollback to Previous Version
```bash
# Stop service
sudo systemctl stop pbx

# Restore from backup
cd /path/to/PBX
git stash
git checkout <previous-version-tag>

# Restore configuration
cp /var/backups/pbx/config.yml.backup config.yml

# Restart
sudo systemctl start pbx
sudo systemctl status pbx
```

### Emergency Contact Escalation
1. **Check health endpoint**: `curl http://localhost:8080/api/health/detailed`
2. **Review logs**: `sudo journalctl -u pbx -n 100`
3. **Attempt restart**: `sudo systemctl restart pbx`
4. **If still failing**: Contact on-call engineer
5. **If critical**: Escalate to management

## Maintenance Tasks

### Weekly Log Rotation
```bash
# Compress old logs
sudo journalctl --vacuum-time=7d

# Backup current logs
sudo journalctl -u pbx > /var/backups/pbx/logs/pbx_$(date +%Y%m%d).log

# Clean up old backups (keep 30 days)
find /var/backups/pbx/logs -name "pbx_*.log" -mtime +30 -delete
```

### Monthly Database Maintenance
```bash
# Vacuum and analyze database
sudo -u postgres psql -d pbx_system -c "VACUUM ANALYZE;"

# Check database size
sudo -u postgres psql -d pbx_system -c "
SELECT pg_size_pretty(pg_database_size('pbx_system'));
"

# Clean up old CDR records (older than 1 year)
sudo -u postgres psql -d pbx_system -c "
DELETE FROM cdr WHERE timestamp < NOW() - INTERVAL '1 year';
"
```

### Software Updates
```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade

# Update Python dependencies
cd /path/to/PBX
source venv/bin/activate
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# Restart service
sudo systemctl restart pbx

# Verify
curl http://localhost:8080/api/status
```

### SSL Certificate Renewal
```bash
# If using Let's Encrypt
sudo certbot renew

# If using self-signed (renew annually)
python scripts/generate_ssl_cert.py --hostname pbx.yourcompany.com

# Restart nginx (if using reverse proxy)
sudo systemctl restart nginx

# Restart PBX
sudo systemctl restart pbx
```

### Performance Tuning
```bash
# Monitor performance metrics
curl http://localhost:8080/metrics

# Check database query performance
sudo -u postgres psql -d pbx_system -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
"

# Optimize database if needed
sudo -u postgres psql -d pbx_system -c "REINDEX DATABASE pbx_system;"
```

---

## Quick Reference Commands

```bash
# Service management
sudo systemctl start pbx
sudo systemctl stop pbx
sudo systemctl restart pbx
sudo systemctl status pbx

# View logs
sudo journalctl -u pbx -f              # Follow logs
sudo journalctl -u pbx -n 100          # Last 100 lines
sudo journalctl -u pbx --since "1 hour ago"  # Last hour
sudo journalctl -u pbx -p err          # Errors only

# Health checks
curl http://localhost:8080/live        # Liveness
curl http://localhost:8080/ready       # Readiness
curl http://localhost:8080/api/status  # PBX status
curl http://localhost:8080/metrics     # Prometheus metrics

# Database
sudo -u postgres psql -d pbx_system    # Connect to DB
sudo systemctl status postgresql       # PostgreSQL status

# Network
sudo ss -tuln | grep -E ':(5060|8080)' # Check ports
sudo ufw status                        # Firewall status

# System resources
free -h                                # Memory
df -h                                  # Disk
top                                    # CPU/processes
```

---

**Remember**: Always test changes in a staging environment before applying to production!
