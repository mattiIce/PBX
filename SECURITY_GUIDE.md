# PBX System Security Guide

**Last Updated**: December 18, 2024  
**Version**: 2.0

> **📋 Consolidated Guide**: This document combines all security-related documentation including FIPS compliance, MFA, best practices, and Ubuntu deployment.

## Table of Contents

1. [Security Overview](#security-overview)
2. [FIPS 140-2 Compliance](#fips-140-2-compliance)
3. [Multi-Factor Authentication (MFA)](#multi-factor-authentication-mfa)
4. [Security Best Practices](#security-best-practices)
5. [Ubuntu FIPS Deployment](#ubuntu-fips-deployment)
6. [CodeQL Security Analysis](#codeql-security-analysis)

---

## Security Overview

### Implemented Security Features

✅ Extension password authentication with FIPS 140-2 compliant hashing  
✅ Failed login attempt tracking  
✅ IP-based banning after max failed attempts  
✅ Configurable security policies  
✅ Input validation on SIP messages  
✅ Configuration-based access control  
✅ FIPS-compliant encryption module (AES-256, SHA-256, PBKDF2)  
✅ TLS/SIPS support with FIPS-approved cipher suites  
✅ SRTP support for encrypted media streams  
✅ Multi-Factor Authentication (TOTP, YubiKey, FIDO2)  
✅ Secure credential storage  
✅ API authentication options

### Security Layers

1. **Network Level**: Firewall, VPN, segmentation
2. **Application Level**: TLS/SRTP, strong passwords, MFA
3. **API Level**: Authentication, rate limiting, HTTPS
4. **System Level**: Non-root user, file permissions, updates
5. **Compliance Level**: FIPS 140-2, SOC2, industry standards

---

## FIPS 140-2 Compliance

### Executive Summary

FIPS 140-2 (Federal Information Processing Standard 140-2) is a US government security standard for cryptographic modules. This PBX system implements FIPS-approved algorithms for encryption, hashing, and key derivation.

**Status**: ✅ **FIPS-Compliant** (Code and configuration verified)

**What This Means**:
- Safe for government and regulated industries
- Uses NIST-certified cryptographic algorithms
- Password storage meets highest security standards
- Encryption uses government-approved methods

### FIPS-Approved Algorithms

| Algorithm | FIPS Standard | Usage | Key Size |
|-----------|--------------|-------|----------|
| **AES-256-GCM** | FIPS 197 | Symmetric encryption | 256-bit |
| **SHA-256** | FIPS 180-4 | Cryptographic hashing | 256-bit |
| **PBKDF2-HMAC-SHA256** | NIST SP 800-132 | Password derivation | 600,000 iterations |
| **TLS 1.2/1.3** | FIPS 140-2 Annex A | Secure transport | FIPS-approved ciphers |
| **SRTP** | NIST SP 800-52 | Media encryption | AES-GCM |

### Key Security Parameters

- **Password Hashing**: PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP 2024 recommendation)
- **Salt Length**: 32 bytes (cryptographically random)
- **Encryption Key**: 256-bit AES-GCM
- **TLS Version**: 1.2+ only (1.0/1.1 disabled)
- **Cipher Suites**: FIPS-approved only (ECDHE, AES-GCM, SHA-256+)

### Configuration

#### Enable FIPS Mode

Edit `config.yml`:

```yaml
security:
  # FIPS 140-2 Compliance
  fips_mode: true                    # Enable FIPS-compliant encryption
  
  # Password Policy (FIPS-compliant)
  min_password_length: 12            # Minimum 12 characters
  require_strong_passwords: true     # Enforce complexity
  password_iterations: 600000        # PBKDF2 iterations (OWASP 2024)
  
  # Authentication
  require_authentication: true
  max_failed_attempts: 5
  ban_duration: 300                  # 5 minutes
  
  # Encryption Settings
  encryption_algorithm: AES-256-GCM  # FIPS 197
  hash_algorithm: SHA-256            # FIPS 180-4
  
  # TLS/SRTP
  enable_tls: true
  enable_srtp: true
  tls_version: 1.2                   # Minimum TLS 1.2
  tls_ciphers: FIPS                  # FIPS-approved ciphers only
```

#### Install FIPS-Compliant Libraries

```bash
# Install cryptography library (required for FIPS mode)
pip install 'cryptography>=41.0.0'

# Verify installation
python -c "from cryptography.fernet import Fernet; print('OK')"
```

#### Verify FIPS Mode

```bash
# Run FIPS verification script
python scripts/verify_fips.py

# Expected output:
# ✅ FIPS mode enabled in config
# ✅ AES-256-GCM encryption: PASS
# ✅ SHA-256 hashing: PASS
# ✅ PBKDF2-HMAC-SHA256 (600K iterations): PASS
# ✅ Password hashing: FIPS-compliant
# ✅ All checks passed - System is FIPS-compliant
```

### Password Migration

After enabling FIPS mode, migrate existing passwords:

```python
# Hash passwords for all extensions
python scripts/migrate_passwords_fips.py

# Or manually for specific extension
from pbx.utils.encryption import hash_password
hashed = hash_password("password123")
print(hashed)  # Save to config.yml
```

### FIPS Enforcement

When `fips_mode: true`, the system:
- ✅ Uses only FIPS-approved algorithms
- ✅ Rejects non-compliant encryption attempts
- ✅ Validates password strength
- ✅ Enforces minimum iteration counts
- ✅ Uses FIPS-approved TLS cipher suites

See [FIPS_COMPLIANCE_STATUS.md](FIPS_COMPLIANCE_STATUS.md) for detailed compliance documentation (deprecated, content above).

---

## Multi-Factor Authentication (MFA)

### Overview

MFA adds an extra layer of security beyond passwords, requiring users to verify their identity using a second factor.

**Status**: ✅ **Fully Implemented**

### Supported MFA Methods

| Method | Type | Security Level | Hardware Required |
|--------|------|----------------|-------------------|
| **TOTP** | Time-based codes | High | Smartphone app |
| **YubiKey OTP** | Hardware token | Very High | YubiKey device |
| **FIDO2/WebAuthn** | Biometric/Hardware | Highest | FIDO2 key/device |
| **Backup Codes** | One-time codes | Medium | None |

### 1. TOTP (Time-based One-Time Password)

Most common MFA method using apps like Google Authenticator, Authy, or Microsoft Authenticator.

**Features**:
- 6-digit codes that change every 30 seconds
- Works offline (no internet required)
- Compatible with all TOTP-compliant apps

**Configuration**:

```yaml
security:
  mfa:
    enabled: true
    methods:
      totp:
        enabled: true
        issuer: "PBX System"        # Shown in authenticator app
        digits: 6                    # Code length
        period: 30                   # Seconds per code
        algorithm: SHA256            # HMAC algorithm
```

**Enrollment (API)**:

```bash
# Step 1: Generate TOTP secret
POST /api/mfa/totp/enroll
{
  "extension": "1001"
}

# Response includes:
# - secret: Base32-encoded secret
# - qr_code: Data URL for QR code image
# - manual_entry: Secret for manual entry

# Step 2: Scan QR code with authenticator app

# Step 3: Verify enrollment
POST /api/mfa/totp/verify-enrollment
{
  "extension": "1001",
  "code": "123456"
}
```

### 2. YubiKey OTP

Hardware-based authentication using YubiKey devices.

**Features**:
- Physical USB/NFC security key
- One-touch authentication
- Highly secure (hardware-protected secrets)

**Configuration**:

```yaml
security:
  mfa:
    methods:
      yubikey:
        enabled: true
        client_id: "YOUR_CLIENT_ID"          # From YubiCloud
        secret_key: "YOUR_SECRET_KEY"        # From YubiCloud
        verify_url: "https://api.yubico.com/wsapi/2.0/verify"
```

**Get YubiCloud Credentials**:
1. Visit https://upgrade.yubico.com/getapikey/
2. Enter email and YubiKey OTP
3. Receive Client ID and Secret Key

**Enrollment**:

```bash
POST /api/mfa/yubikey/enroll
{
  "extension": "1001",
  "otp": "ccccccccccccjklvneuigvgrnrblndbnhfdhhvuecnlk"  # From YubiKey
}
```

### 3. FIDO2/WebAuthn

Modern authentication using biometrics or hardware security keys.

**Features**:
- Fingerprint, face recognition, or hardware key
- Phishing-resistant (cryptographic challenge-response)
- Best security (FIDO Alliance standard)

**Configuration**:

```yaml
security:
  mfa:
    methods:
      fido2:
        enabled: true
        rp_name: "PBX System"
        rp_id: "pbx.example.com"     # Your domain
        timeout: 60000                # Registration timeout (ms)
```

**Enrollment** (Browser-based):

```javascript
// Step 1: Request registration options
const options = await fetch('/api/mfa/fido2/register-options', {
  method: 'POST',
  body: JSON.stringify({ extension: '1001' })
}).then(r => r.json());

// Step 2: Create credential
const credential = await navigator.credentials.create({
  publicKey: options
});

// Step 3: Complete registration
await fetch('/api/mfa/fido2/register-complete', {
  method: 'POST',
  body: JSON.stringify({ extension: '1001', credential })
});
```

### 4. Backup Codes

One-time use codes for account recovery.

**Features**:
- 10 single-use codes
- Use when primary MFA unavailable
- Generated during MFA enrollment

**Generation**:

```bash
POST /api/mfa/backup-codes/generate
{
  "extension": "1001"
}

# Response:
{
  "codes": [
    "ABCD-EFGH-IJKL",
    "MNOP-QRST-UVWX",
    ...
  ]
}
```

### MFA Verification Flow

```bash
# Step 1: Authenticate with password
POST /api/auth/login
{
  "extension": "1001",
  "password": "password123"
}

# Response includes:
{
  "mfa_required": true,
  "mfa_methods": ["totp", "yubikey"],
  "session_token": "temp-token-for-mfa"
}

# Step 2: Verify MFA code
POST /api/mfa/verify
{
  "session_token": "temp-token-for-mfa",
  "method": "totp",
  "code": "123456"
}

# Response:
{
  "success": true,
  "access_token": "full-access-token"
}
```

### MFA Best Practices

1. **Enforce MFA for Admins**: Always require MFA for admin accounts
2. **Backup Codes**: Generate and securely store backup codes
3. **Multiple Methods**: Enable multiple MFA methods for redundancy
4. **User Education**: Train users on MFA usage
5. **Recovery Process**: Document MFA recovery procedures

See [MFA_GUIDE.md](MFA_GUIDE.md) for full API reference (deprecated, content above).

---

## Security Best Practices

### Credential Management

#### Environment Variables

**NEVER** commit credentials to version control:

```bash
# Copy template
cp .env.example .env

# Edit with actual credentials
nano .env

# .env is automatically ignored by git
```

**Store in .env**:
- Database passwords
- SMTP passwords
- API keys
- OAuth client secrets
- Encryption keys

#### Recommended Secret Management Tools

- **HashiCorp Vault**: Enterprise secret management
- **AWS Secrets Manager**: Cloud deployments
- **Azure Key Vault**: Microsoft cloud
- **Docker Secrets**: Containerized deployments
- **systemd credentials**: Linux service deployments

### Network Security

#### Firewall Configuration

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

#### Network Segmentation

- **Voice VLAN**: Separate VLAN for voice traffic
- **Admin Network**: Restrict admin panel access
- **DMZ**: Place SIP trunks in DMZ
- **Internal**: Keep PBX in internal network

#### VPN for Remote Access

```bash
# Install WireGuard VPN
sudo apt install wireguard

# Configure VPN for remote admin access
# Only expose PBX through VPN, not public internet
```

### TLS/SRTP Encryption

#### Enable Encrypted Signaling and Media

```yaml
security:
  enable_tls: true
  tls_cert_file: /etc/pbx/ssl/cert.pem
  tls_key_file: /etc/pbx/ssl/key.pem
  tls_version: 1.2              # Minimum TLS 1.2
  enable_srtp: true
  srtp_crypto_suite: AES_CM_128_HMAC_SHA1_80
```

#### Generate SSL Certificate

**For Testing** (self-signed):
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

**For Production** (Let's Encrypt):
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d pbx.example.com
```

See [HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md) for detailed SSL configuration.

### Authentication Security

#### Strong Password Policy

```yaml
security:
  min_password_length: 12
  require_strong_passwords: true
  password_complexity:
    require_uppercase: true
    require_lowercase: true
    require_numbers: true
    require_special_chars: true
```

**Strong Password Requirements**:
- Minimum 12 characters
- Uppercase and lowercase letters
- Numbers
- Special characters (!@#$%^&*)

#### Password Rotation

```bash
# Rotate passwords every 90 days
# Use strong, unique passwords for each extension
# Never reuse passwords across services
```

#### Failed Login Protection

```yaml
security:
  max_failed_attempts: 5
  ban_duration: 300              # 5 minutes
  ban_on_invalid_extension: true # Ban on unknown extensions
```

### API Security

#### Enable API Authentication

```yaml
api:
  require_authentication: true
  authentication_method: jwt     # jwt, oauth2, or api_key
  
  # JWT Configuration
  jwt:
    secret_key: "your-secret-key-here"  # Store in .env
    algorithm: HS256
    expiration: 3600                     # 1 hour
  
  # Rate Limiting
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
```

#### HTTPS for API

```yaml
api:
  use_https: true
  ssl_cert: /etc/pbx/ssl/cert.pem
  ssl_key: /etc/pbx/ssl/key.pem
```

#### Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name pbx.example.com;
    
    ssl_certificate /etc/letsencrypt/live/pbx.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pbx.example.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### System Security

#### Run as Non-Root User

```bash
# Create PBX user
sudo useradd -r -s /bin/false pbx

# Set ownership
sudo chown -R pbx:pbx /opt/PBX

# Run as pbx user
sudo -u pbx python main.py
```

#### File Permissions

```bash
# Restrict config file access
chmod 600 config.yml
chmod 600 .env

# Voicemail directory
chmod 700 voicemail/
chown -R pbx:pbx voicemail/

# Log directory
chmod 750 logs/
chown -R pbx:pbx logs/
```

#### System Updates

```bash
# Keep system updated
sudo apt update && sudo apt upgrade -y

# Update PBX dependencies
pip install --upgrade -r requirements.txt

# Monitor security advisories
# Subscribe to CVE notifications for dependencies
```

#### Log Monitoring

```bash
# Monitor authentication failures
tail -f logs/pbx.log | grep "authentication failed"

# Monitor banned IPs
tail -f logs/pbx.log | grep "IP banned"

# Set up log rotation
sudo nano /etc/logrotate.d/pbx
```

### Additional Recommendations

#### Security Checklist

- [ ] Change all default passwords
- [ ] Enable FIPS mode (if required)
- [ ] Enable MFA for admin accounts
- [ ] Configure firewall rules
- [ ] Enable TLS/SRTP encryption
- [ ] Use HTTPS for API
- [ ] Set up reverse proxy
- [ ] Run as non-root user
- [ ] Restrict file permissions
- [ ] Enable log monitoring
- [ ] Regular security updates
- [ ] Backup configuration and data
- [ ] Document recovery procedures
- [ ] Test disaster recovery plan

#### Regular Security Audits

1. **Monthly**: Review access logs, update passwords
2. **Quarterly**: Security scan, dependency updates
3. **Annually**: Full security audit, penetration testing

See [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) for more details (deprecated, content above).

---

## Ubuntu FIPS Deployment

### Overview

For organizations requiring FIPS 140-2 validated cryptographic modules at the operating system level, Ubuntu Pro provides FIPS-certified kernels and libraries.

**Use Cases**:
- Government contracts (FISMA compliance)
- Defense industry
- Healthcare (HIPAA with FIPS requirement)
- Financial services

### Prerequisites

#### Supported Ubuntu Versions

- Ubuntu 20.04 LTS (Focal Fossa)
- Ubuntu 22.04 LTS (Jammy Jellyfish)
- Ubuntu 24.04 LTS (Noble Numbat) - When available

#### Hardware Requirements

- x86_64 (amd64) architecture
- Minimum 2 CPU cores
- 4 GB RAM
- 20 GB disk space

### Option 1: Ubuntu Pro FIPS (Recommended)

Ubuntu Pro provides FIPS 140-2 Level 1 validated cryptographic modules.

#### Step 1: Attach Ubuntu Pro

```bash
# Install Ubuntu Pro client (if not already installed)
sudo apt install ubuntu-advantage-tools

# Attach your Ubuntu Pro subscription
# Get token from: https://ubuntu.com/pro
sudo pro attach YOUR_TOKEN_HERE

# Verify attachment
sudo pro status
```

#### Step 2: Enable FIPS

```bash
# Enable FIPS kernel and cryptographic modules
sudo pro enable fips

# Reboot to load FIPS kernel
sudo reboot
```

#### Step 3: Verify FIPS

```bash
# Check FIPS kernel is loaded
uname -r | grep fips
# Should show: 5.15.0-1234-fips

# Verify FIPS mode is active
cat /proc/sys/crypto/fips_enabled
# Should show: 1

# Check OpenSSL FIPS mode
openssl version
# Should show: OpenSSL FIPS
```

### Option 2: OpenSSL FIPS Module (Alternative)

If Ubuntu Pro is not available, use OpenSSL FIPS module.

**Note**: This provides FIPS-compliant OpenSSL only, not kernel-level FIPS.

```bash
# Install OpenSSL FIPS module
sudo apt install openssl-fips

# Configure OpenSSL to use FIPS
sudo nano /etc/ssl/openssl.cnf
# Add: openssl_conf = openssl_init
# [openssl_init]
# providers = provider_sect
# [provider_sect]
# fips = fips_sect
# [fips_sect]
# activate = 1

# Verify
openssl list -providers | grep fips
```

### PBX Configuration for Ubuntu FIPS

After enabling system-level FIPS, configure PBX:

```yaml
security:
  fips_mode: true
  use_system_fips: true          # Use system FIPS modules
  
  # TLS Configuration
  enable_tls: true
  tls_version: 1.2
  tls_ciphers: FIPS              # Use only FIPS ciphers
```

### FIPS Compliance Verification

```bash
# Run full FIPS verification
python scripts/verify_fips_full.py

# Should report:
# ✅ System FIPS mode: ENABLED
# ✅ OpenSSL FIPS mode: ACTIVE
# ✅ PBX FIPS mode: ENABLED
# ✅ All algorithms: FIPS-compliant
```

### Troubleshooting Ubuntu FIPS

**Issue**: FIPS kernel not loading after reboot

```bash
# Check available kernels
dpkg --list | grep linux-image

# Ensure FIPS kernel is default
sudo grub-set-default 0
sudo update-grub
```

**Issue**: Applications failing with FIPS enabled

```bash
# Check application uses FIPS-compliant libraries
ldd /path/to/app | grep ssl
# Should show: libssl.so.1.1 (FIPS version)
```

See [UBUNTU_FIPS_GUIDE.md](UBUNTU_FIPS_GUIDE.md) for detailed deployment guide (deprecated, content above).

---

## CodeQL Security Analysis

### Overview

CodeQL is GitHub's semantic code analysis engine that helps find security vulnerabilities.

### Analysis Results

CodeQL identified 2 alerts related to socket binding:

#### Finding 1: pbx/rtp/handler.py

**Alert**: Socket binding to all network interfaces (0.0.0.0)

**Assessment**: ✅ **ACCEPTABLE** and **INTENTIONAL**

**Reason**: PBX systems must accept RTP media from any network interface. This is correct implementation for a VOIP server.

**Mitigation**: 
- Configurable in `config.yml` (can restrict to specific interface if needed)
- Firewall rules should be used to restrict access
- Network segmentation recommended

#### Finding 2: examples/simple_client.py

**Alert**: Example client binding to all interfaces

**Assessment**: ✅ **ACCEPTABLE** for test code

**Reason**: Example/test client needs to work in any environment

**Impact**: Low - this is example code, not production

### Security Posture Assessment

**Overall Rating**: ✅ **SECURE**

**Strengths**:
- FIPS 140-2 compliant encryption
- Strong authentication mechanisms
- MFA support
- Input validation
- Secure password storage
- TLS/SRTP support

**Recommendations**:
- Use firewall rules to restrict network access
- Enable TLS/SRTP in production
- Implement MFA for admin accounts
- Regular security updates

See [SECURITY.md](SECURITY.md) for full CodeQL analysis (deprecated, content above).

---

## Related Documentation

- **[SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md)** - Detailed implementation guide (deprecated, content above)
- **[HTTPS_SETUP_GUIDE.md](HTTPS_SETUP_GUIDE.md)** - SSL/TLS certificate setup
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API security endpoints

---

**Note**: This consolidated guide replaces the individual security guides:
- SECURITY.md
- SECURITY_BEST_PRACTICES.md
- SECURITY_IMPLEMENTATION.md
- MFA_GUIDE.md
- FIPS_COMPLIANCE_STATUS.md
- UBUNTU_FIPS_GUIDE.md
