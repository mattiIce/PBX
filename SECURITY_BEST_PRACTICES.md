# Security Best Practices for PBX System

## Overview

This document outlines security best practices for deploying and maintaining the PBX system in production environments.

## Credential Management

### Environment Variables

**NEVER** commit credentials to version control. Instead:

1. Copy `.env.example` to `.env`
2. Fill in your actual credentials in `.env`
3. The `.env` file is automatically ignored by git

```bash
cp .env.example .env
# Edit .env with your actual credentials
nano .env
```

### Config File Security

The `config.yml` file contains example credentials for development. For production:

1. **Database passwords**: Use environment variables or a secrets manager
2. **SMTP passwords**: Store in environment variables
3. **API keys**: Never hardcode in config files
4. **Extension passwords**: Ensure they meet minimum complexity requirements

### Recommended Tools

- **HashiCorp Vault**: For enterprise secret management
- **AWS Secrets Manager**: For cloud deployments
- **Docker Secrets**: For containerized deployments
- **systemd credentials**: For Linux service deployments

## Network Security

### Firewall Configuration

Only expose necessary ports:

```bash
# Allow SIP signaling
sudo ufw allow 5060/udp

# Allow RTP media (adjust range as needed)
sudo ufw allow 10000:20000/udp

# Allow API (restrict to internal network)
sudo ufw allow from 192.168.1.0/24 to any port 8080

# Enable firewall
sudo ufw enable
```

### TLS/SRTP Encryption

Enable encrypted signaling and media:

```yaml
security:
  enable_tls: true
  tls_cert_file: /path/to/cert.pem
  tls_key_file: /path/to/key.pem
  enable_srtp: true
```

Generate self-signed certificates for testing:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

For production, use certificates from a trusted CA like Let's Encrypt.

## Authentication Security

### Strong Passwords

Configure password requirements in `config.yml`:

```yaml
security:
  min_password_length: 12
  require_strong_passwords: true
```

Strong passwords should include:
- At least 12 characters
- Uppercase and lowercase letters
- Numbers
- Special characters

### Extension Security

1. **Change default passwords immediately**
2. **Use unique passwords for each extension**
3. **Rotate passwords periodically** (every 90 days)
4. **Enable FIPS mode** for government-grade encryption

```yaml
security:
  fips_mode: true
```

### Rate Limiting

Protect against brute force attacks:

```yaml
security:
  max_failed_attempts: 5
  ban_duration: 300  # 5 minutes
```

## Database Security

### PostgreSQL Setup

1. **Use strong database passwords**
2. **Restrict network access** to localhost or specific IPs
3. **Enable SSL connections**

```bash
# In postgresql.conf
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'

# In pg_hba.conf
hostssl all all 0.0.0.0/0 md5
```

4. **Regular backups**

```bash
# Backup
pg_dump -U pbx_user pbx_system > backup.sql

# Restore
psql -U pbx_user pbx_system < backup.sql
```

### Database User Permissions

Create a dedicated database user with minimal privileges:

```sql
CREATE USER pbx_user WITH PASSWORD 'SecurePassword123!';
GRANT CONNECT ON DATABASE pbx_system TO pbx_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pbx_user;
```

## API Security

### Access Control

1. **Restrict API access** to internal network only
2. **Implement authentication** (add API key/token system)
3. **Enable CORS** only for trusted domains

```yaml
api:
  host: 127.0.0.1  # Localhost only
  port: 8080
  enable_cors: false
```

### HTTPS for API

Use a reverse proxy like nginx for HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name pbx.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Logging and Monitoring

### Secure Log Storage

1. **Restrict log file permissions**

```bash
chmod 640 logs/pbx.log
chown pbx:pbx logs/pbx.log
```

2. **Rotate logs regularly**

```bash
# In /etc/logrotate.d/pbx
/var/log/pbx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 640 pbx pbx
}
```

### Security Monitoring

Monitor for:
- Failed authentication attempts
- Unusual call patterns
- High call volumes
- Database access errors
- API access from unknown IPs

Set up alerts for security events:

```yaml
logging:
  level: INFO
  file: logs/pbx.log
  security_alerts: true
  alert_email: security@yourcompany.com
```

## Regular Updates

### Security Patches

1. **Keep Python and dependencies updated**

```bash
pip install --upgrade pip
pip install --upgrade -r requirements.txt
```

2. **Monitor security advisories**
   - Subscribe to Python security mailing lists
   - Monitor CVE databases
   - Use `pip-audit` for vulnerability scanning

```bash
pip install pip-audit
pip-audit
```

### System Updates

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade

# CentOS/RHEL
sudo yum update
```

## Compliance

### FIPS 140-2 Compliance

For government and regulated industries:

1. **Enable FIPS mode**
2. **Use FIPS-approved algorithms** (AES-256, SHA-256)
3. **Disable weak ciphers**

See [FIPS_COMPLIANCE.md](FIPS_COMPLIANCE.md) for details.

### Data Retention

Configure retention policies:

```yaml
recording:
  retention_days: 90  # Keep recordings for 90 days

voicemail:
  retention_days: 30  # Keep voicemail for 30 days

cdr:
  retention_days: 365  # Keep CDRs for 1 year
```

## Incident Response

### Security Breach Procedure

1. **Disconnect affected systems** from network
2. **Preserve logs** for forensic analysis
3. **Identify the attack vector**
4. **Patch vulnerabilities**
5. **Reset all credentials**
6. **Notify affected parties** if required by law

### Emergency Contacts

Maintain a list of:
- System administrators
- Security team
- Network team
- Legal/compliance team

## Regular Audits

### Security Checklist

Perform monthly:
- [ ] Review user accounts and remove inactive ones
- [ ] Check for failed login attempts
- [ ] Verify firewall rules
- [ ] Review API access logs
- [ ] Test backups and disaster recovery
- [ ] Update passwords for service accounts

### Penetration Testing

Conduct annual penetration testing:
- Internal security assessment
- External vulnerability scan
- Social engineering tests
- Physical security audit

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Controls](https://www.cisecurity.org/controls/)

## Contact

For security concerns or to report vulnerabilities:
- Email: security@yourcompany.com
- Create a private GitHub security advisory

**Never disclose vulnerabilities publicly before they are patched.**
