# HTTPS/SSL Setup Guide

This guide explains how to configure HTTPS/SSL encryption for the PBX API server.

## Overview

The PBX system supports HTTPS/SSL for secure API communication. This includes:
- **Self-signed certificates** for development and testing
- **In-house CA integration** for enterprise environments
- **Manual certificate configuration** for production use with trusted CAs

## Quick Start

### ⭐ NEW: Admin Panel Method (Recommended)

The easiest way to set up HTTPS is through the admin panel - no terminal commands required!

1. **Access the admin panel:**
   ```
   http://YOUR_SERVER_IP:8080/admin/
   ```

2. **Navigate to Configuration tab:**
   - Click on the "Configuration" tab in the admin panel
   - Scroll down to the "🔒 SSL/HTTPS Configuration" section

3. **Generate a self-signed certificate:**
   - Enter your server's hostname or IP address
   - Set the validity period (default: 365 days)
   - Click "🔐 Generate Certificate"
   - The certificate will be automatically generated and saved

4. **Enable HTTPS:**
   - Check the "Enable HTTPS/SSL" checkbox
   - Click "💾 Save SSL Settings"

5. **Restart the PBX server:**
   ```bash
   sudo systemctl restart pbx
   ```
   Or if running manually:
   ```bash
   python main.py
   ```

6. **Access the admin panel via HTTPS:**
   ```
   https://YOUR_SERVER_IP:8080/admin/
   ```
   
   **Note:** Your browser will show a security warning for self-signed certificates. This is expected for development.

### Option 1: Self-Signed Certificate (Command Line)

For users who prefer the command line or need automation:

1. **Generate a self-signed certificate:**
   ```bash
   python scripts/generate_ssl_cert.py
   ```

2. **Enable SSL in config.yml:**
   ```yaml
   api:
     ssl:
       enabled: true
       cert_file: certs/server.crt
       key_file: certs/server.key
   ```

3. **Start the PBX server:**
   ```bash
   python main.py
   ```

4. **Access the admin panel:**
   ```
   https://YOUR_SERVER_IP:8080/admin/
   ```
   
   **Note:** Your browser will show a security warning for self-signed certificates. This is expected for development.

### Option 2: In-House CA (Enterprise)

If your organization has an in-house Certificate Authority:

1. **Configure CA settings in config.yml:**
   ```yaml
   api:
     ssl:
       enabled: true
       cert_file: certs/server.crt
       key_file: certs/server.key
       ca:
         enabled: true
         server_url: https://ca.example.com
         request_endpoint: /api/sign-cert
         ca_cert: certs/ca.crt  # Optional: CA certificate for validation
   ```

2. **Request certificate from CA:**
   ```bash
   python scripts/request_ca_cert.py
   ```
   
   Or enable auto-request (certificate will be requested automatically on startup if not found).

3. **Start the PBX server:**
   ```bash
   python main.py
   ```

### Option 3: Manual Certificate (Production)

For production use with certificates from trusted CAs (Let's Encrypt, DigiCert, etc.):

1. **Obtain certificate from your CA**
   - Generate CSR using standard tools or `openssl`
   - Submit to your CA
   - Receive signed certificate

2. **Place certificate files:**
   ```
   certs/
   ├── server.crt    # Your signed certificate
   └── server.key    # Your private key
   ```

3. **Configure in config.yml:**
   ```yaml
   api:
     ssl:
       enabled: true
       cert_file: certs/server.crt
       key_file: certs/server.key
   ```

4. **Start the PBX server:**
   ```bash
   python main.py
   ```

## Configuration Reference

### SSL Configuration Options

```yaml
api:
  host: 0.0.0.0
  port: 8080
  enable_cors: true
  
  ssl:
    enabled: true                           # Enable/disable HTTPS
    cert_file: certs/server.crt            # Path to SSL certificate
    key_file: certs/server.key             # Path to private key
    
    # In-house CA configuration (optional)
    ca:
      enabled: false                        # Enable auto-request from CA
      server_url: https://ca.example.com    # CA server URL
      request_endpoint: /api/sign-cert      # CA API endpoint
      ca_cert: certs/ca.crt                 # CA certificate (optional)
```

### Security Settings

The HTTPS implementation includes:
- **TLS 1.2 or higher** (TLS 1.0 and 1.1 are disabled)
- **Strong cipher suites** (weak ciphers are excluded)
- **No SSLv2/SSLv3** support
- **FIPS-compatible** (when using appropriate certificates)

## Admin Panel SSL Management

The admin panel provides a user-friendly interface for managing SSL certificates without using the terminal.

### Features

- **Certificate Status Dashboard**: View current SSL configuration and certificate details
- **Certificate Generation**: Generate self-signed certificates with custom hostname and validity period
- **Expiry Warnings**: Automatic alerts when certificates are expiring soon
- **One-Click Enable/Disable**: Toggle HTTPS on/off from the admin panel
- **Certificate Details**: View subject, issuer, validity dates, and expiry countdown

### Accessing SSL Configuration

1. Log into the admin panel at `http://YOUR_SERVER_IP:8080/admin/`
2. Click the "Configuration" tab
3. Scroll to the "🔒 SSL/HTTPS Configuration" section

### Generating Certificates via Admin Panel

1. In the SSL/HTTPS Configuration section, check "Enable HTTPS/SSL"
2. The certificate section will expand
3. Enter your server's hostname or IP address in the "Hostname/IP Address" field
4. Set the certificate validity period (1-3650 days)
5. Click "🔐 Generate Certificate"
6. A success message will confirm the certificate was created
7. Click "💾 Save SSL Settings" to persist the configuration
8. Restart the PBX server for changes to take effect

### Monitoring Certificate Status

The admin panel displays:
- **Current Status**: Whether HTTPS is enabled or disabled
- **Certificate Existence**: Whether certificate files are present
- **Certificate Details**: Subject, issuer, validity period
- **Expiry Warning**: Days until certificate expires
  - ✅ Green: More than 30 days remaining
  - ⚠️ Orange: Less than 30 days remaining
  - ❌ Red: Certificate has expired

### API Endpoints

The admin panel uses these REST API endpoints:

- `GET /api/ssl/status` - Retrieve SSL configuration and certificate status
- `POST /api/ssl/generate-certificate` - Generate a new self-signed certificate
- `PUT /api/config/section` - Update SSL configuration

## Script Reference

### generate_ssl_cert.py

Generate a self-signed certificate for development/testing via command line.

**Usage:**
```bash
python scripts/generate_ssl_cert.py [options]

Options:
  --hostname HOSTNAME   Hostname for certificate (default: localhost)
  --days DAYS          Validity period in days (default: 365)
  --cert-dir DIR       Output directory (default: certs)
```

**Example:**
```bash
# Generate certificate for specific hostname
python scripts/generate_ssl_cert.py --hostname pbx.example.com --days 730
```

**Note:** The admin panel provides the same functionality in a more user-friendly interface.

### request_ca_cert.py

Request a certificate from your in-house Certificate Authority.

**Usage:**
```bash
python scripts/request_ca_cert.py [options]

Options:
  --ca-server URL      CA server URL (e.g., https://ca.example.com)
  --ca-endpoint PATH   CA API endpoint (default: /api/sign-cert)
  --hostname HOSTNAME  Hostname for certificate (default: from config.yml)
  --cert-dir DIR       Output directory (default: certs)
  --ca-cert FILE       CA certificate for verification (optional)
  --config FILE        Path to config.yml (default: config.yml)
```

**Example:**
```bash
# Request certificate from in-house CA
python scripts/request_ca_cert.py \
  --ca-server https://ca.example.com \
  --hostname pbx.example.com
```

## Updating URLs

With HTTPS enabled, all URLs in the system automatically use HTTPS:

### Admin Panel
- Access at: `https://YOUR_SERVER_IP:8080/admin/`
- The admin panel JavaScript automatically detects and uses the current protocol

### Phone Provisioning
- Provisioning URL: `https://YOUR_SERVER_IP:8080/provision/{mac}.cfg`
- Phone book URL: `https://YOUR_SERVER_IP:8080/api/phone-book/export/xml`

### API Endpoints
All API endpoints are available over HTTPS:
- Status: `https://YOUR_SERVER_IP:8080/api/status`
- Extensions: `https://YOUR_SERVER_IP:8080/api/extensions`
- Provisioning: `https://YOUR_SERVER_IP:8080/api/provisioning/devices`

### Using curl with Self-Signed Certificates

When using self-signed certificates, use the `-k` flag with curl:

```bash
# Example: Get status
curl -k https://localhost:8080/api/status

# Example: Register device
curl -k -X POST https://localhost:8080/api/provisioning/devices \
  -H 'Content-Type: application/json' \
  -d '{"mac_address":"00:11:22:33:44:55","extension_number":"1001","vendor":"yealink","model":"t46s"}'
```

For production with trusted certificates, the `-k` flag is not needed.

## Troubleshooting

### Certificate Not Found

**Error:** `SSL certificate file not found: certs/server.crt`

**Solution:**
- Generate certificate: `python scripts/generate_ssl_cert.py`
- Or request from CA: `python scripts/request_ca_cert.py`
- Or disable SSL: Set `api.ssl.enabled: false` in config.yml

### Permission Denied on Private Key

**Error:** `Permission denied: certs/server.key`

**Solution:**
```bash
chmod 600 certs/server.key
```

### Browser Security Warning

**Issue:** Browser shows "Your connection is not private" or similar warning

**Explanation:** This is expected behavior for self-signed certificates in development.

**Solutions:**
- For development: Click "Advanced" and proceed anyway
- For production: Use a certificate from a trusted CA (Let's Encrypt, DigiCert, etc.)

### Phones Can't Connect

**Issue:** IP phones can't download provisioning files over HTTPS

**Possible causes:**
1. **Self-signed certificate:** Some older IP phones don't support self-signed certificates
   - Solution: Use a certificate from a trusted CA or configure phone to trust your CA

2. **TLS version:** Some older phones only support TLS 1.0
   - Solution: The system requires TLS 1.2+. Upgrade phone firmware or use HTTP for provisioning only

3. **Certificate hostname mismatch:** Certificate hostname doesn't match server IP
   - Solution: Generate certificate with correct hostname: `python scripts/generate_ssl_cert.py --hostname YOUR_IP`

### CA Auto-Request Fails

**Error:** `Failed to obtain certificate from in-house CA`

**Troubleshooting:**
1. Verify CA server URL is correct
2. Check network connectivity to CA server
3. Verify CA endpoint path
4. Check CA server logs for errors
5. Test manually: `python scripts/request_ca_cert.py --ca-server https://YOUR_CA`

## Best Practices

### Development
- Use self-signed certificates
- Enable SSL early in development to catch issues
- Test with actual devices to ensure compatibility

### Production
- Use certificates from trusted CAs (Let's Encrypt, DigiCert, etc.)
- Set appropriate certificate validity periods
- Monitor certificate expiration dates
- Use strong private keys (2048-bit RSA minimum)
- Restrict private key file permissions (chmod 600)
- Keep certificates and keys in secure locations
- Never commit private keys to version control

### In-House CA
- Distribute CA certificate to all devices
- Configure phones to trust your CA
- Automate certificate renewal
- Monitor certificate expiration
- Keep CA secure and backed up

## Let's Encrypt Integration

For production deployments, consider using Let's Encrypt for free, trusted certificates:

1. **Install certbot:**
   ```bash
   sudo apt-get install certbot
   ```

2. **Obtain certificate:**
   ```bash
   sudo certbot certonly --standalone -d pbx.example.com
   ```

3. **Configure PBX:**
   ```yaml
   api:
     ssl:
       enabled: true
       cert_file: /etc/letsencrypt/live/pbx.example.com/fullchain.pem
       key_file: /etc/letsencrypt/live/pbx.example.com/privkey.pem
   ```

4. **Setup auto-renewal:**
   ```bash
   sudo certbot renew --dry-run
   ```

## Security Considerations

1. **Certificate Validation:** Always validate certificates in production
2. **Private Key Protection:** Keep private keys secure with restricted permissions
3. **Certificate Expiration:** Monitor and renew certificates before expiration
4. **Strong Ciphers:** The system uses strong cipher suites by default
5. **TLS Version:** Only TLS 1.2 and higher are supported
6. **HSTS:** Consider adding HSTS headers for production deployments

## Additional Resources

- [Let's Encrypt](https://letsencrypt.org/) - Free SSL certificates
- [SSL Labs](https://www.ssllabs.com/ssltest/) - Test your SSL configuration
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/) - Generate SSL configs
- [FIPS Compliance Guide](FIPS_COMPLIANCE.md) - FIPS 140-2 compliance information

## Support

For issues or questions:
1. Check this guide and troubleshooting section
2. Review logs in `logs/pbx.log`
3. Test with curl using `-v` flag for verbose output
4. Check certificate validity: `openssl x509 -in certs/server.crt -text -noout`
5. Verify private key: `openssl rsa -in certs/server.key -check`
