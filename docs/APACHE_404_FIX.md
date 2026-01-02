# Quick Fix for "Not Found" Error on Apache

## Problem
Accessing `http://your-domain.com/admin/status-check.html` returns:
```
Not Found
The requested URL was not found on this server.
Apache/2.4.58 (Ubuntu) Server at your-domain.com Port 80
```

## Root Cause
Apache is serving requests directly without proxying them to the PBX application. The PBX admin files are not in Apache's document root - they need to be proxied to the PBX backend server running on port 8080 or 9000.

## Quick Fix

### Option 1: Automated Setup (Recommended)

Run the automated Apache configuration script:

```bash
cd /path/to/PBX
sudo scripts/setup_apache_reverse_proxy.sh
```

This script will:
1. Configure Apache as a reverse proxy
2. Set up SSL certificates (optional but recommended)
3. Handle all the configuration automatically

### Option 2: Manual Configuration

If you prefer to configure Apache manually:

1. **Enable required Apache modules:**
   ```bash
   sudo a2enmod proxy proxy_http proxy_wstunnel headers rewrite ssl
   ```

2. **Create Apache virtual host configuration:**
   ```bash
   sudo nano /etc/apache2/sites-available/pbx.conf
   ```

3. **Add this minimal configuration:**
   ```apache
   <VirtualHost *:80>
       ServerName your-domain.com
       
       ProxyPreserveHost On
       ProxyRequests Off
       
       <Location />
           ProxyPass http://localhost:8080/
           ProxyPassReverse http://localhost:8080/
       </Location>
       
       ErrorLog ${APACHE_LOG_DIR}/pbx-error.log
       CustomLog ${APACHE_LOG_DIR}/pbx-access.log combined
   </VirtualHost>
   ```
   
   Replace:
   - `your-domain.com` with your actual domain (e.g., `abps.albl.com`)
   - `8080` with your PBX port (check `config.yml` for `api.port`)

4. **Enable the site and restart Apache:**
   ```bash
   sudo a2ensite pbx.conf
   sudo apache2ctl configtest
   sudo systemctl restart apache2
   ```

## Verification

After configuration, test by accessing:
- `http://your-domain.com/admin/status-check.html` - Should now load the status page
- `http://your-domain.com/admin/` - Should show the admin interface
- `http://your-domain.com/api/status` - Should return PBX status JSON

## Common Issues

### Issue: Still getting 404
**Solution:** Verify PBX is running:
```bash
sudo systemctl status pbx
sudo netstat -tlnp | grep 8080
```

### Issue: Connection refused
**Solution:** Check if PBX is listening on localhost:
```bash
curl http://localhost:8080/api/status
```

If this doesn't work, PBX isn't running or is listening on a different port.

### Issue: Proxy errors in Apache logs
**Solution:** Check Apache error log:
```bash
sudo tail -f /var/log/apache2/pbx-error.log
```

Look for lines containing "proxy" or "connection refused".

## For Production: Add SSL

After basic configuration works, add SSL for security:

```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d your-domain.com
```

This will:
- Obtain a free SSL certificate from Let's Encrypt
- Automatically configure Apache to use HTTPS
- Set up automatic certificate renewal

## More Information

- Complete setup guide: `docs/APACHE_REVERSE_PROXY_SETUP.md`
- Configuration example: `apache-pbx.conf.example`
- General troubleshooting: `TROUBLESHOOTING.md`

## Support

If you're still having issues:
1. Check PBX logs: `tail -f /path/to/PBX/logs/pbx.log`
2. Check Apache logs: `tail -f /var/log/apache2/pbx-error.log`
3. Verify PBX configuration: `cat config.yml | grep -A5 "^api:"`
4. Contact support with the error messages from the logs
