# Apache Reverse Proxy Setup Guide for Warden VoIP PBX

**Last Updated:** 2025-12-30  
**Priority:** HIGH - Production Deployment  
**Purpose:** Configure Apache as a reverse proxy for the PBX system

## Overview

This guide explains how to configure Apache as a reverse proxy for the Warden VoIP PBX system. Apache will handle SSL/TLS encryption and proxy requests to the PBX application running on localhost.

## Why Use a Reverse Proxy?

A reverse proxy provides several critical benefits:

1. **SSL/TLS Encryption** - Secure HTTPS connections with automated certificate management
2. **Professional URLs** - Use `https://pbx.yourcompany.com` instead of `http://ip-address:8080`
3. **Enhanced Security** - Hide the backend application from direct internet access
4. **Centralized Access Control** - Manage authentication and authorization in one place
5. **Load Balancing** - Distribute traffic across multiple backend servers (if needed)

## Prerequisites

- Ubuntu 24.04 LTS (or similar Linux distribution with Apache support)
- Root/sudo access to the server
- Domain name configured to point to your server's IP address
- PBX system installed and running (typically on port 8080 or 9000)
- Firewall configured to allow ports 80 and 443

## Quick Setup (Recommended)

The easiest way to set up Apache as a reverse proxy is to use the automated setup script:

```bash
# Navigate to the PBX directory
cd /path/to/PBX

# Run the Apache setup script
sudo scripts/setup_apache_reverse_proxy.sh
```

The script will:
1. Install Apache and required modules if not already installed
2. Install certbot for SSL certificate management
3. Check and resolve port 80 conflicts
4. Create Apache virtual host configuration
5. Obtain SSL certificate from Let's Encrypt
6. Configure automatic SSL certificate renewal
7. Set up security headers and optimizations

### What You'll Need to Provide

The script will ask for:
- **Domain name** (e.g., `pbx.yourcompany.com`)
- **Email address** (for SSL certificate notifications)
- **Backend port** (default: 8080, or 9000 if using the alternative port)

## Manual Setup

If you prefer to configure Apache manually, follow these steps:

### Step 1: Install Apache and Required Modules

```bash
# Update package list
sudo apt update

# Install Apache
sudo apt install -y apache2

# Install certbot for SSL certificates
sudo apt install -y certbot python3-certbot-apache

# Enable required Apache modules
sudo a2enmod proxy proxy_http proxy_wstunnel headers rewrite ssl
```

### Step 2: Create Apache Virtual Host Configuration

Create a new file `/etc/apache2/sites-available/pbx.conf`:

```bash
sudo nano /etc/apache2/sites-available/pbx.conf
```

Copy the example configuration from `apache-pbx.conf.example` in the repository root, or use this basic template:

```apache
# HTTP Virtual Host - Redirects to HTTPS
<VirtualHost *:80>
    ServerName pbx.yourcompany.com
    ServerAdmin admin@yourcompany.com

    # Redirect to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]

    # Allow Let's Encrypt certificate validation
    Alias /.well-known/acme-challenge/ /var/www/html/.well-known/acme-challenge/
    <Directory "/var/www/html/.well-known/acme-challenge/">
        Options None
        AllowOverride None
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/pbx-error.log
    CustomLog ${APACHE_LOG_DIR}/pbx-access.log combined
</VirtualHost>

# HTTPS Virtual Host
<VirtualHost *:443>
    ServerName pbx.yourcompany.com
    ServerAdmin admin@yourcompany.com

    SSLEngine on
    # SSL certificates will be auto-configured by certbot

    # Security Headers
    Header always set X-Frame-Options "DENY"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Permissions-Policy "geolocation=(), microphone=(self), camera=()"

    # Proxy Configuration
    ProxyPreserveHost On
    ProxyRequests Off
    ProxyTimeout 300

    # WebSocket support for WebRTC
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} =websocket [NC]
    RewriteRule ^/(.*)$ ws://localhost:8080/$1 [P,L]

    # Main proxy to PBX backend
    <Location />
        ProxyPass http://localhost:8080/
        ProxyPassReverse http://localhost:8080/
        RequestHeader set X-Forwarded-Proto "https"
        RequestHeader set X-Real-IP %{REMOTE_ADDR}s
    </Location>

    ErrorLog ${APACHE_LOG_DIR}/pbx-ssl-error.log
    CustomLog ${APACHE_LOG_DIR}/pbx-ssl-access.log combined
</VirtualHost>
```

**Important**: Replace the following placeholders:
- `pbx.yourcompany.com` - Your actual domain name
- `admin@yourcompany.com` - Your email address
- `8080` - Your PBX backend port (use 9000 if that's your configured port)

### Step 3: Enable the Site

```bash
# Disable default site (optional)
sudo a2dissite 000-default

# Enable PBX site
sudo a2ensite pbx.conf

# Test Apache configuration
sudo apache2ctl configtest

# If test passes, restart Apache
sudo systemctl restart apache2
```

### Step 4: Obtain SSL Certificate

```bash
# Run certbot to obtain and configure SSL certificate
sudo certbot --apache -d pbx.yourcompany.com

# Follow the prompts to:
# 1. Enter your email address
# 2. Agree to terms of service
# 3. Choose to redirect HTTP to HTTPS (recommended)
```

Certbot will automatically:
- Obtain an SSL certificate from Let's Encrypt
- Modify your Apache configuration to use the certificate
- Set up automatic certificate renewal (certificates renew every 90 days)

### Step 5: Configure Firewall

```bash
# Allow HTTP and HTTPS traffic
sudo ufw allow 'Apache Full'

# If UFW is not installed/enabled, you can use iptables:
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

### Step 6: Verify Setup

Test your setup by accessing:
- `http://your-domain.com` - Should redirect to HTTPS
- `https://your-domain.com` - Should show the PBX login page
- `https://your-domain.com/admin/status-check.html` - Should show the status check page

## Troubleshooting

### Error: Port 80 Already in Use

If you get an error that port 80 is already in use:

```bash
# Check what's using port 80
sudo lsof -i :80
# or
sudo ss -tlnp | grep :80

# If it's nginx or another web server, stop it
sudo systemctl stop nginx
sudo systemctl disable nginx  # Prevent it from starting on boot
```

### Error: SSL Certificate Failed

If certbot fails to obtain an SSL certificate:

1. **Check DNS**: Verify your domain points to your server's IP
   ```bash
   nslookup your-domain.com
   dig your-domain.com
   ```

2. **Check firewall**: Ensure port 80 is accessible from the internet
   ```bash
   sudo ufw status
   ```

3. **Check Apache logs**:
   ```bash
   sudo tail -f /var/log/apache2/error.log
   ```

4. **Try manual certificate request**:
   ```bash
   sudo certbot certonly --apache -d your-domain.com
   ```

### Error: 404 Not Found on Admin Pages

If you get "404 Not Found" errors when accessing admin pages:

1. **Verify PBX is running**:
   ```bash
   sudo systemctl status pbx
   # Check if PBX is listening on the backend port
   sudo netstat -tlnp | grep 8080
   ```

2. **Check Apache proxy configuration**:
   ```bash
   # Verify proxy modules are enabled
   apache2ctl -M | grep proxy
   
   # Should see:
   # proxy_module (shared)
   # proxy_http_module (shared)
   # proxy_wstunnel_module (shared)
   ```

3. **Check Apache error logs**:
   ```bash
   sudo tail -f /var/log/apache2/pbx-ssl-error.log
   ```

4. **Test direct access to PBX**:
   ```bash
   curl http://localhost:8080/admin/status-check.html
   ```
   If this works but the proxied version doesn't, there's a proxy configuration issue.

### Error: WebRTC Phone Not Working

If the WebRTC phone in the admin panel doesn't work:

1. **Verify WebSocket module is enabled**:
   ```bash
   sudo a2enmod proxy_wstunnel
   sudo systemctl restart apache2
   ```

2. **Check for WebSocket upgrade headers** in Apache configuration:
   ```apache
   RewriteEngine On
   RewriteCond %{HTTP:Upgrade} =websocket [NC]
   RewriteRule ^/(.*)$ ws://localhost:8080/$1 [P,L]
   ```

3. **Check browser console** for WebSocket connection errors

## Security Best Practices

1. **Use Strong SSL/TLS Configuration**
   - Disable old SSL/TLS versions (SSLv2, SSLv3, TLSv1.0, TLSv1.1)
   - Use strong cipher suites
   - Enable HSTS (HTTP Strict Transport Security)

2. **Limit Backend Access**
   - Configure PBX to listen only on localhost (127.0.0.1)
   - Never expose PBX port (8080/9000) directly to the internet

3. **Enable Rate Limiting**
   - Install `libapache2-mod-qos` for advanced rate limiting
   - Protect API endpoints from brute force attacks

4. **Regular Updates**
   - Keep Apache and certbot up to date
   - Monitor Apache security advisories
   - Update SSL certificates before expiration (auto-renewal handles this)

5. **Monitor Logs**
   - Regularly check Apache access and error logs
   - Set up log rotation to prevent disk space issues
   - Consider using log analysis tools (e.g., GoAccess, AWStats)

## Maintenance

### SSL Certificate Renewal

Certbot automatically renews certificates. To verify:

```bash
# Check certificate status
sudo certbot certificates

# Test renewal process
sudo certbot renew --dry-run

# Manual renewal (if needed)
sudo certbot renew
```

### Apache Log Management

```bash
# View recent access logs
sudo tail -f /var/log/apache2/pbx-ssl-access.log

# View recent error logs
sudo tail -f /var/log/apache2/pbx-ssl-error.log

# Log rotation is handled automatically by logrotate
# Configuration: /etc/logrotate.d/apache2
```

### Performance Monitoring

```bash
# Check Apache status
sudo systemctl status apache2

# Monitor Apache processes
sudo apache2ctl status

# Check active connections
sudo netstat -an | grep :443 | wc -l
```

## Comparison: Apache vs Nginx

Both Apache and Nginx are excellent choices for reverse proxying. Here's a quick comparison:

| Feature | Apache | Nginx |
|---------|--------|-------|
| Market Share | 30% | 33% |
| Configuration | .htaccess, per-directory | Centralized config files |
| Performance | Good | Excellent (async, event-driven) |
| Memory Usage | Higher | Lower |
| Dynamic Content | Built-in (mod_php) | Requires FastCGI |
| Documentation | Extensive | Extensive |
| Learning Curve | Moderate | Moderate |
| Certbot Support | Excellent | Excellent |

**Recommendation**: 
- Use **Nginx** if you want maximum performance and lower memory usage (recommended for new deployments)
- Use **Apache** if you're already familiar with it or have existing Apache infrastructure

Both work perfectly well for the PBX reverse proxy setup.

## Additional Resources

- [Official Apache Documentation](https://httpd.apache.org/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Apache mod_proxy Documentation](https://httpd.apache.org/docs/current/mod/mod_proxy.html)
- [Certbot Documentation](https://certbot.eff.org/docs/)

## Support

If you encounter issues not covered in this guide:

1. Check the PBX logs: `/path/to/PBX/logs/`
2. Check Apache logs: `/var/log/apache2/`
3. Review the troubleshooting section above
4. Consult the TROUBLESHOOTING.md file in the repository
5. Open an issue on the GitHub repository with detailed error messages and logs
