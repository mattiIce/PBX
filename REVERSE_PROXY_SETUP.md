# Reverse Proxy Setup Guide for PBX System

This guide shows you how to access your PBX web interface via a friendly URL (like `abps.albl.com`) instead of `IP:8080`.

## Why Use a Reverse Proxy?

**Security and Best Practices:**
- ✅ **Standard HTTPS port (443)** - No need to specify `:8080` in URLs
- ✅ **SSL/TLS encryption** - Secure communication for admin panel
- ✅ **Certificate management** - Centralized SSL certificate handling
- ✅ **Additional security layer** - Rate limiting, access control, etc.
- ✅ **Professional appearance** - Clean URLs like `https://abps.albl.com`

**Recommended:** Use reverse proxy (nginx or Apache) for production deployments.

## Option 1: Nginx Reverse Proxy (Recommended)

### Prerequisites
- DNS record pointing `abps.albl.com` to your PBX server IP
- Root/sudo access to the server
- SSL certificate (Let's Encrypt recommended, or use existing certificates)

### Step 1: Install Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx

# Start and enable nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 2: Configure Nginx for abps.albl.com

Create nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/abps.albl.com
```

**Configuration for HTTPS (Recommended):**

```nginx
# HTTP - Redirect to HTTPS
server {
    listen 80;
    server_name abps.albl.com;
    
    # Redirect all HTTP traffic to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS - Main configuration
server {
    listen 443 ssl http2;
    server_name abps.albl.com;

    # SSL Certificate Configuration
    # Option A: Let's Encrypt certificates (recommended)
    ssl_certificate /etc/letsencrypt/live/abps.albl.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/abps.albl.com/privkey.pem;
    
    # Option B: Your own certificates
    # ssl_certificate /path/to/abps.albl.com.crt;
    # ssl_certificate_key /path/to/abps.albl.com.key;

    # Strong SSL Configuration (TLS 1.2+)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/abps.albl.com-access.log;
    error_log /var/log/nginx/abps.albl.com-error.log;

    # Proxy to PBX backend (running on port 8080)
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        
        # WebSocket support (for WebRTC phone)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Forward original request information
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running connections
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Provisioning endpoint - Special handling for IP phones
    # Phones may not support HTTPS, so we allow HTTP access to /provision/*
    # But it's proxied through HTTPS to the admin panel
    location /provision/ {
        proxy_pass http://localhost:8080/provision/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Rate limiting to prevent abuse
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://localhost:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Configuration for HTTP Only (Not Recommended for Production):**

If you don't have SSL certificates yet and want to test:

```nginx
server {
    listen 80;
    server_name abps.albl.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Step 3: Enable the Configuration

```bash
# Create symbolic link to enable site
sudo ln -s /etc/nginx/sites-available/abps.albl.com /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

### Step 4: Get SSL Certificate (Let's Encrypt - Free)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate for abps.albl.com
sudo certbot --nginx -d abps.albl.com

# Follow the prompts:
# - Enter email address for renewal notifications
# - Agree to terms of service
# - Choose whether to redirect HTTP to HTTPS (recommended: yes)

# Certbot will automatically configure nginx and enable auto-renewal
```

### Step 5: Configure Firewall

```bash
# Allow HTTP and HTTPS through firewall
sudo ufw allow 'Nginx Full'

# Or manually:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Optionally block direct access to port 8080 from external network
# (keep it accessible only from localhost)
sudo ufw deny 8080/tcp
```

### Step 6: Update PBX Configuration (Optional)

If you want to restrict PBX to only listen on localhost (more secure):

Edit `/home/runner/work/PBX/PBX/config.yml`:

```yaml
api:
  host: 127.0.0.1  # Only listen on localhost
  port: 8080
  enable_cors: true
```

Then restart the PBX:

```bash
sudo systemctl restart pbx
```

### Step 7: Test Your Setup

1. **Open browser and navigate to:** `https://abps.albl.com`
2. **You should see:** The PBX admin login page
3. **Check certificate:** Click the padlock icon to verify SSL is working

## Option 2: Apache Reverse Proxy (Alternative)

### Prerequisites
Same as nginx (DNS, root access, SSL certificate)

### Step 1: Install Apache

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install apache2

# Enable required modules
sudo a2enmod proxy proxy_http ssl rewrite headers

# Start and enable apache
sudo systemctl start apache2
sudo systemctl enable apache2
```

### Step 2: Configure Apache for abps.albl.com

Create Apache configuration:

```bash
sudo nano /etc/apache2/sites-available/abps.albl.com.conf
```

**HTTPS Configuration:**

```apache
<VirtualHost *:80>
    ServerName abps.albl.com
    
    # Redirect to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]
</VirtualHost>

<VirtualHost *:443>
    ServerName abps.albl.com
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/abps.albl.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/abps.albl.com/privkey.pem
    
    # Strong SSL Configuration
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite HIGH:!aNULL:!MD5
    SSLHonorCipherOrder on
    
    # Security Headers
    Header always set Strict-Transport-Security "max-age=31536000"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    
    # Logging
    ErrorLog ${APACHE_LOG_DIR}/abps.albl.com-error.log
    CustomLog ${APACHE_LOG_DIR}/abps.albl.com-access.log combined
    
    # Reverse Proxy Configuration
    ProxyPreserveHost On
    ProxyPass / http://localhost:8080/
    ProxyPassReverse / http://localhost:8080/
    
    # WebSocket support
    RewriteEngine on
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://localhost:8080/$1" [P,L]
</VirtualHost>
```

### Step 3: Enable and Test

```bash
# Enable site
sudo a2ensite abps.albl.com.conf

# Test configuration
sudo apache2ctl configtest

# Reload Apache
sudo systemctl reload apache2

# Get SSL certificate
sudo certbot --apache -d abps.albl.com
```

## DNS Configuration

### On Your DNS Server

Add an A record pointing to your PBX server:

```
Type: A
Name: abps
Domain: albl.com
Value: <YOUR_PBX_SERVER_IP>
TTL: 3600
```

Full record: `abps.albl.com` → `<YOUR_PBX_SERVER_IP>`

### Verify DNS Resolution

```bash
# Check DNS resolution
nslookup abps.albl.com

# Or
dig abps.albl.com

# Should return your PBX server IP address
```

## Security Recommendations

1. **Use HTTPS (SSL/TLS)** - Always encrypt admin panel traffic
2. **Keep certificates updated** - Let's Encrypt auto-renews every 90 days
3. **Restrict access** - Use firewall rules or nginx access controls
4. **Monitor logs** - Check `/var/log/nginx/` regularly
5. **Keep software updated** - Update nginx/Apache and PBX regularly

### Example: Restrict Access to Internal Network Only

Add to nginx configuration inside `server {}` block:

```nginx
# Only allow access from internal network
allow 192.168.1.0/24;  # Your internal network
deny all;
```

## Troubleshooting

### Can't Access https://abps.albl.com

1. **Check DNS:** `nslookup abps.albl.com` should return correct IP
2. **Check nginx:** `sudo systemctl status nginx`
3. **Check logs:** `sudo tail -f /var/log/nginx/abps.albl.com-error.log`
4. **Check firewall:** `sudo ufw status`
5. **Test locally:** `curl -I http://localhost:8080/admin/`

### SSL Certificate Issues

```bash
# Check certificate
sudo certbot certificates

# Renew manually
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

### Nginx Configuration Test Failed

```bash
# Test and see detailed errors
sudo nginx -t

# Common issues:
# - Missing semicolon
# - Wrong file paths for SSL certificates
# - Duplicate server_name directives
```

## Summary

**Recommended Setup for abps.albl.com:**

1. ✅ **Nginx reverse proxy** (or Apache)
2. ✅ **Let's Encrypt SSL certificate** (free, auto-renews)
3. ✅ **HTTP → HTTPS redirect**
4. ✅ **PBX listening on localhost:8080** (not exposed to internet)
5. ✅ **Nginx listening on ports 80/443** (standard web ports)

**Result:** 
- Access admin panel: `https://abps.albl.com` (no port number needed!)
- Secure HTTPS connection with valid SSL certificate
- Professional, easy-to-remember URL

---

**Need Help?** Check logs at:
- Nginx: `/var/log/nginx/abps.albl.com-error.log`
- PBX: `/home/runner/work/PBX/PBX/logs/pbx.log`
