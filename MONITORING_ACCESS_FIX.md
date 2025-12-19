# Monitoring Access Fix Guide

## Issue Description

If you ran `scripts/deploy_production_pilot.sh` and are experiencing:
- 404 errors when accessing Prometheus on port 9090
- 404 errors when accessing Node Exporter on port 9100
- 502 errors when accessing your domain (e.g., adps.albl.com)

This guide will help you fix these issues.

## Root Causes

The previous version of the deployment script had the following issues:

1. **Nginx configuration missing monitoring endpoints**: The reverse proxy didn't include proxy configurations for Prometheus and Node Exporter
2. **Firewall blocking monitoring ports**: UFW firewall rules didn't allow access to ports 9090 and 9100
3. **Wrong backend port**: Nginx was proxying to port 8000 instead of 8080 (the actual PBX backend port from config.yml)

## Solution

### Option 1: Re-run the Deployment Script (Recommended)

The easiest solution is to re-run the updated deployment script:

```bash
# Pull the latest changes
cd /path/to/PBX
git pull origin main

# Re-run the deployment (this will update nginx config and firewall rules)
sudo bash scripts/deploy_production_pilot.sh
```

This will update the Nginx configuration and firewall rules without affecting your existing database or configuration.

### Option 2: Manual Fix

If you prefer to fix manually, follow these steps:

#### Step 1: Update Nginx Configuration

Edit the Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/pbx
```

Update the server block to include the monitoring endpoints and fix the backend port:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;  # Changed from 8000 to 8080
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebRTC signaling
    location /ws {
        proxy_pass http://127.0.0.1:8443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Prometheus monitoring
    location /prometheus/ {
        proxy_pass http://127.0.0.1:9090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Node Exporter metrics
    location /metrics {
        proxy_pass http://127.0.0.1:9100/metrics;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Test the configuration and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### Step 2: Update Firewall Rules

Add rules to allow access to Prometheus and Node Exporter:

```bash
sudo ufw allow 9090/tcp
sudo ufw allow 9100/tcp
sudo ufw reload
```

Verify the rules:

```bash
sudo ufw status
```

## Verification

After applying the fix, verify that everything works:

### 1. Check Prometheus Access

```bash
# Via proxy
curl http://your-domain/prometheus/

# Direct access
curl http://localhost:9090
```

You should see the Prometheus web interface HTML.

### 2. Check Node Exporter Access

```bash
# Via proxy
curl http://your-domain/metrics

# Direct access
curl http://localhost:9100/metrics
```

You should see metrics in Prometheus format.

### 3. Check PBX Admin Panel

```bash
curl -I http://your-domain/
```

You should get a 200 OK response (not 502).

### 4. Check Firewall Rules

```bash
sudo ufw status numbered
```

You should see rules allowing:
- Port 9090/tcp (Prometheus)
- Port 9100/tcp (Node Exporter)
- Port 80/tcp (HTTP)
- Port 443/tcp (HTTPS)
- Port 5060/udp (SIP)
- Port 8443/tcp (WebRTC)
- Ports 10000:20000/udp (RTP)

## Access URLs

After the fix is applied, you can access:

- **PBX Admin Panel**: 
  - http://your-domain/
  - http://localhost:8080
  
- **Prometheus**: 
  - http://your-domain/prometheus/
  - http://localhost:9090
  
- **Node Exporter Metrics**: 
  - http://your-domain/metrics
  - http://localhost:9100/metrics

## Troubleshooting

### Prometheus still shows 404

1. Check if Prometheus is running:
   ```bash
   sudo systemctl status prometheus
   ```

2. If not running, start it:
   ```bash
   sudo systemctl start prometheus
   sudo systemctl enable prometheus
   ```

### Node Exporter still shows 404

1. Check if Node Exporter is running:
   ```bash
   sudo systemctl status prometheus-node-exporter
   ```

2. If not running, start it:
   ```bash
   sudo systemctl start prometheus-node-exporter
   sudo systemctl enable prometheus-node-exporter
   ```

### 502 errors persist

1. Check if PBX is running on the correct port:
   ```bash
   sudo netstat -tlnp | grep 8080
   # or
   sudo ss -tlnp | grep 8080
   ```

2. Check PBX logs:
   ```bash
   sudo journalctl -u pbx -f
   ```

3. Verify the port in config.yml matches:
   ```bash
   grep "port:" /path/to/PBX/config.yml
   ```

### Firewall rules not working

1. Check UFW status:
   ```bash
   sudo ufw status verbose
   ```

2. If UFW is inactive, enable it:
   ```bash
   sudo ufw enable
   ```

3. Reload firewall rules:
   ```bash
   sudo ufw reload
   ```

## Support

If you continue to experience issues after applying this fix, please:

1. Check the Nginx error logs:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

2. Check the PBX logs:
   ```bash
   sudo journalctl -u pbx -n 100
   ```

3. Open an issue on GitHub with the error logs and your configuration details.
