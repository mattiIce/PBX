# Login Connection Error - Troubleshooting Guide

## Symptom
When trying to log into the admin panel at `/admin/login.html`, you see the error:
- "Connection error. Please try again."
- "Cannot reach API server at http://hostname:9000"

## Quick Diagnosis

### Step 1: Open Browser Console
1. Press `F12` to open Developer Tools
2. Go to the **Console** tab
3. Refresh the login page
4. Look for error messages

### Step 2: Check Console Messages

The login page now provides detailed diagnostic information:

**Good Signs (Server is working):**
```
Final API Base URL: http://your-server:9000
Testing API connectivity...
✓ API server is reachable
```

**Problem Signs:**

**A) Server Not Running:**
```
✗ Cannot reach API server: TypeError: Failed to fetch
```
**Solution:** Start the PBX server (see below)

**B) Wrong Port:**
```
✗ Cannot reach API server at http://your-server:8080
```
**Solution:** The API runs on port 9000, not 8080. Check your URL.

**C) Firewall Blocking:**
```
✗ Cannot reach API server: net::ERR_CONNECTION_REFUSED
```
**Solution:** Check firewall rules (see below)

**D) Invalid Response:**
```
Invalid response type: text/html
Response status: 500
```
**Solution:** Server error - check PBX logs (see below)

## Common Fixes

### Fix 1: Start the PBX Server

**If running as a service:**
```bash
# Check if service is running
sudo systemctl status pbx

# If not running, start it
sudo systemctl start pbx

# Check for errors
sudo journalctl -u pbx -n 50
```

**If running manually:**
```bash
cd /home/runner/work/PBX/PBX  # Or your installation directory
python3 main.py
```

**Expected output:**
```
============================================================
Warden Voip System v1.0.0
============================================================
Starting REST API server on 0.0.0.0:9000...
REST API server started successfully
```

### Fix 2: Check API Port Configuration

Verify the API port in `config.yml`:

```bash
grep -A3 "^api:" config.yml
```

**Should show:**
```yaml
api:
  host: 0.0.0.0
  port: 9000
```

**If port is different (e.g., 8080):**
1. Either update `config.yml` to use port 9000
2. OR update the login page meta tag to match your port:
   ```html
   <meta name="api-base-url" content="http://your-server:YOUR_PORT">
   ```

### Fix 3: Check Firewall Rules

**Allow port 9000:**
```bash
# For UFW (Ubuntu)
sudo ufw allow 9000/tcp
sudo ufw status

# For firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

**Check if port is open:**
```bash
# From the server itself
sudo netstat -tlnp | grep 9000

# From another machine
telnet your-server-ip 9000
# OR
nc -zv your-server-ip 9000
```

### Fix 4: Check PBX Logs

```bash
# For systemd service
sudo journalctl -u pbx -f

# For manual run
tail -f logs/pbx.log
```

**Look for:**
- Startup errors
- Port binding issues
- Database connection errors
- Authentication errors

### Fix 5: Reverse Proxy Configuration

If you're using a reverse proxy (nginx/Apache):

**Check nginx configuration:**
```bash
sudo nginx -t
sudo systemctl status nginx
```

**Common nginx issues:**
- Proxy not forwarding to correct port
- Missing CORS headers
- SSL/HTTPS misconfiguration

See [REVERSE_PROXY_SETUP.md](REVERSE_PROXY_SETUP.md) for detailed setup.

## Testing API Connectivity

### Test from Command Line

**Using curl:**
```bash
# Test status endpoint
curl http://localhost:9000/api/status

# Expected response:
{"status": "running", "uptime": ..., ...}
```

**Using Python:**
```python
import requests
response = requests.get('http://localhost:9000/api/status')
print(response.status_code, response.json())
```

### Test from Browser

Open your browser to:
```
http://your-server:9000/api/status
```

You should see JSON response, not an error page.

## Advanced Troubleshooting

### Check Network Connectivity

```bash
# From client machine to server
ping your-server-ip

# Check DNS resolution
nslookup your-server-hostname

# Trace route
traceroute your-server-ip
```

### Check Server Bindings

```bash
# Verify PBX is listening on all interfaces (0.0.0.0:9000)
sudo netstat -tlnp | grep python

# Should show:
# tcp  0  0  0.0.0.0:9000  0.0.0.0:*  LISTEN  12345/python3
```

### Check for Port Conflicts

```bash
# See what's using port 9000
sudo lsof -i :9000

# OR
sudo netstat -tlnp | grep 9000
```

### Database Connection Issues

The login endpoint requires database access. Check:

```bash
# For PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT 1"

# Test database connection from PBX
python3 scripts/verify_database.py
```

## Deployment-Specific Issues

### Docker/Container Deployments

```bash
# Check container is running
docker ps | grep pbx

# Check container logs
docker logs pbx-container

# Check port mapping
docker port pbx-container
```

### Cloud Deployments (AWS, Azure, GCP)

- Verify security group allows inbound traffic on port 9000
- Check network ACLs
- Verify instance public IP/DNS
- Check load balancer configuration

## Still Having Issues?

### Collect Diagnostic Information

```bash
# Create diagnostic report
cat > diagnostic-report.txt << EOF
=== System Information ===
$(uname -a)

=== PBX Service Status ===
$(sudo systemctl status pbx)

=== PBX Logs (last 50 lines) ===
$(sudo journalctl -u pbx -n 50)

=== Network Listeners ===
$(sudo netstat -tlnp | grep -E ':(5060|9000|8080)')

=== Firewall Status ===
$(sudo ufw status verbose)

=== Config File ===
$(grep -A5 "^api:" /home/runner/work/PBX/PBX/config.yml)
EOF

cat diagnostic-report.txt
```

### Get Help

1. Open a GitHub issue with your diagnostic report
2. Include browser console errors (F12 → Console)
3. Specify your deployment method (service, manual, Docker)
4. Include your OS and browser version

## Related Documentation

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting guide
- [REVERSE_PROXY_SETUP.md](REVERSE_PROXY_SETUP.md) - Reverse proxy configuration
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment best practices
- [ADMIN_PORTAL_FIX_SUMMARY.md](ADMIN_PORTAL_FIX_SUMMARY.md) - Previous admin portal fixes

---
**Last Updated:** December 23, 2025
**Status:** Active troubleshooting guide
