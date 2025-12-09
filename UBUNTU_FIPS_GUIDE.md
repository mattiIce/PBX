# Ubuntu Server FIPS 140-2 Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the PBX system on Ubuntu Server with FIPS 140-2 compliance enabled. It covers system-level FIPS configuration, application deployment, and verification.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System FIPS Configuration](#system-fips-configuration)
3. [PBX Deployment](#pbx-deployment)
4. [Verification](#verification)
5. [Troubleshooting](#troubleshooting)
6. [Production Deployment Checklist](#production-deployment-checklist)

---

## Prerequisites

### Supported Ubuntu Versions

FIPS 140-2 support is available on:
- **Ubuntu 20.04 LTS** (Focal Fossa) - with Ubuntu Pro
- **Ubuntu 22.04 LTS** (Jammy Jellyfish) - with Ubuntu Pro
- **Ubuntu 24.04 LTS** (Noble Numbat) - with Ubuntu Pro

### Hardware Requirements

- **CPU**: x86_64 architecture (AES-NI support recommended for performance)
- **RAM**: Minimum 4GB (8GB+ recommended for production)
- **Storage**: 20GB+ free disk space
- **Network**: Static IP address recommended

### Before You Begin

1. **Fresh Ubuntu Server installation** (recommended)
2. **Root or sudo access**
3. **Ubuntu Pro account** (free for personal use, up to 5 machines)
   - Sign up at: https://ubuntu.com/pro
4. **Backup** of any existing configuration

---

## System FIPS Configuration

### Option 1: Ubuntu Pro FIPS (Recommended)

Ubuntu Pro provides **NIST-validated FIPS 140-2 Level 1** cryptographic modules.

#### Step 1: Attach Ubuntu Pro

```bash
# Install Ubuntu Pro client (if not already installed)
sudo apt-get update
sudo apt-get install ubuntu-advantage-tools

# Attach your Ubuntu Pro subscription
sudo ua attach <YOUR-UBUNTU-PRO-TOKEN>

# Verify attachment
sudo ua status
```

#### Step 2: Enable FIPS

```bash
# Enable FIPS kernel and cryptographic modules
sudo ua enable fips --assume-yes
```

This will:
- Install FIPS-validated kernel
- Install FIPS cryptographic modules
- Configure OpenSSL for FIPS mode
- Update GRUB bootloader

#### Step 3: Reboot

```bash
sudo reboot
```

#### Step 4: Verify FIPS Mode

After reboot:

```bash
# Check kernel FIPS mode (should output: 1)
cat /proc/sys/crypto/fips_enabled

# Verify FIPS kernel is running
uname -r
# Should show: x.x.x-xxx-fips

# Check OpenSSL FIPS provider
openssl list -providers
# Should show 'fips' provider

# Run comprehensive verification
cd /path/to/PBX
python3 scripts/verify_fips.py
```

### Option 2: Automated Setup Script

We provide an automated script for FIPS enablement:

```bash
cd /path/to/PBX
sudo ./scripts/enable_fips_ubuntu.sh
```

The script will:
1. Detect your Ubuntu version
2. Guide you through Ubuntu Pro or OpenSSL FIPS setup
3. Configure system for FIPS mode
4. Provide post-reboot verification steps

### Option 3: OpenSSL FIPS Module (Alternative)

If Ubuntu Pro is not available, you can use OpenSSL 3.0+ FIPS provider:

**Note**: This provides FIPS-approved algorithms but is not formally NIST-validated.

```bash
# Ensure OpenSSL 3.0+ is installed (Ubuntu 22.04+)
openssl version
# Should show: OpenSSL 3.0.x or higher

# Configure FIPS provider
sudo cp /etc/ssl/openssl.cnf /etc/ssl/openssl.cnf.backup

# Add FIPS configuration to openssl.cnf
sudo tee -a /etc/ssl/openssl.cnf > /dev/null << 'EOF'

# FIPS Configuration
openssl_conf = openssl_init

[openssl_init]
providers = provider_sect

[provider_sect]
default = default_sect
fips = fips_sect

[default_sect]
activate = 1

[fips_sect]
activate = 1
EOF

# Enable FIPS in kernel boot parameters
sudo sed -i 's/GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="fips=1 /' /etc/default/grub
sudo update-grub

# Reboot
sudo reboot
```

---

## PBX Deployment

### Step 1: Install System Dependencies

```bash
# Update package list
sudo apt-get update

# Install required packages
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    build-essential \
    libssl-dev \
    git

# Optional: Install audio processing tools
sudo apt-get install -y espeak ffmpeg
```

### Step 2: Clone PBX Repository

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/mattiIce/PBX.git
cd PBX

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
# Install required packages
pip install --upgrade pip
pip install -r requirements.txt

# Verify cryptography library installation
python3 -c "import cryptography; print('Cryptography version:', cryptography.__version__)"
# Should be >= 41.0.0

# Check if cryptography uses FIPS-enabled OpenSSL
python3 -c "from cryptography.hazmat.backends import default_backend; print(default_backend())"
# Should show FIPS: True if system FIPS is enabled
```

### Step 4: Configure Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE pbx_system;
CREATE USER pbx_user WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE pbx_system TO pbx_user;
\q
```

### Step 5: Configure PBX System

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your database credentials
nano .env
```

Set these environment variables in `.env`:
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pbx_system
DB_USER=pbx_user
DB_PASSWORD=your-secure-password

# SMTP (for voicemail notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-app-password

# Active Directory (optional)
AD_BIND_PASSWORD=your-ad-password
```

### Step 6: Configure FIPS Mode

Edit `config.yml`:

```yaml
security:
  # Enable FIPS 140-2 compliant encryption
  fips_mode: true
  enforce_fips: true  # Fail startup if FIPS cannot be enabled
  
  # Password Policy (FIPS requirement)
  password:
    min_length: 12
    require_uppercase: true
    require_lowercase: true
    require_digit: true
    require_special: true
  
  # Enable TLS for SIP (SIPS)
  enable_tls: true
  tls_cert_file: "/etc/pbx/certs/server.crt"
  tls_key_file: "/etc/pbx/certs/server.key"
  
  # Enable SRTP for encrypted media
  enable_srtp: true
```

### Step 7: Generate TLS Certificates

For FIPS compliance, use RSA-2048 or RSA-4096:

```bash
# Create certificates directory
sudo mkdir -p /etc/pbx/certs
cd /etc/pbx/certs

# Generate RSA private key (2048 or 4096 bits)
sudo openssl genrsa -out server.key 2048

# Generate Certificate Signing Request
sudo openssl req -new -key server.key -out server.csr \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=pbx.company.com"

# Generate self-signed certificate (for testing)
sudo openssl x509 -req -days 365 -in server.csr \
  -signkey server.key -out server.crt

# For production, obtain certificates from a trusted CA

# Set proper permissions
sudo chmod 600 server.key
sudo chmod 644 server.crt
```

### Step 8: Initialize Database Schema

```bash
cd /opt/PBX
python3 -c "
from pbx.core.pbx import PBXCore
pbx = PBXCore('config.yml')
print('Database initialized successfully')
"
```

### Step 9: Test PBX System

```bash
# Run FIPS verification
python3 scripts/verify_fips.py

# If all checks pass, start PBX
python3 main.py
```

---

## Verification

### Comprehensive FIPS Verification

Run the verification script:

```bash
cd /opt/PBX
python3 scripts/verify_fips.py
```

This script checks:
- ✓ Kernel FIPS mode enabled
- ✓ OpenSSL FIPS provider active
- ✓ Python hashlib FIPS mode
- ✓ Cryptography library FIPS-enabled
- ✓ PBX configuration
- ✓ Encryption operations

### Manual Verification Steps

#### 1. System FIPS Status

```bash
# Kernel FIPS mode (should output: 1)
cat /proc/sys/crypto/fips_enabled

# OpenSSL providers
openssl list -providers
# Should include: name: OpenSSL FIPS Provider
```

#### 2. Python FIPS Status

```bash
python3 << 'EOF'
import hashlib
import sys

# Check hashlib FIPS mode
try:
    fips_mode = hashlib.get_fips_mode()
    print(f"Python hashlib FIPS mode: {fips_mode}")
except AttributeError:
    print("Python hashlib FIPS mode: Not available")

# Check cryptography
try:
    from cryptography.hazmat.backends import default_backend
    backend = default_backend()
    print(f"Cryptography backend: {backend}")
except ImportError:
    print("Cryptography library not installed")
EOF
```

#### 3. PBX Encryption Test

```bash
cd /opt/PBX
python3 << 'EOF'
from pbx.utils.encryption import get_encryption

# Test FIPS encryption
enc = get_encryption(fips_mode=True, enforce_fips=True)

# Test password hashing
password = "TestPassword123!"
hash1, salt = enc.hash_password(password)
is_valid = enc.verify_password(password, hash1, salt)

print(f"Password hashing: {'✓ PASS' if is_valid else '✗ FAIL'}")

# Test data hashing
hash_result = enc.hash_data("test data")
print(f"SHA-256 hashing: {'✓ PASS' if len(hash_result) == 64 else '✗ FAIL'}")

print("\nFIPS encryption verification complete!")
EOF
```

---

## Troubleshooting

### Issue: Kernel FIPS mode returns 0

**Cause**: FIPS not enabled in kernel boot parameters

**Solution**:
```bash
# Check GRUB configuration
sudo grep GRUB_CMDLINE_LINUX /etc/default/grub

# Should include: fips=1

# If missing, add it:
sudo sed -i 's/GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="fips=1 /' /etc/default/grub
sudo update-grub
sudo reboot
```

### Issue: OpenSSL FIPS provider not found

**Cause**: OpenSSL not configured for FIPS or FIPS module missing

**Solution for Ubuntu Pro**:
```bash
# Re-enable FIPS
sudo ua disable fips --assume-yes
sudo ua enable fips --assume-yes
sudo reboot
```

**Solution for OpenSSL 3.0**:
```bash
# Check if FIPS module exists
ls -la /usr/lib/x86_64-linux-gnu/ossl-modules/fips.so

# If missing, run enablement script
sudo ./scripts/enable_fips_ubuntu.sh
```

### Issue: Cryptography library not FIPS-enabled

**Cause**: System FIPS not enabled or cryptography built without FIPS support

**Solution**:
```bash
# Ensure system FIPS is enabled first
cat /proc/sys/crypto/fips_enabled  # Should be 1

# Reinstall cryptography after enabling system FIPS
pip uninstall cryptography
pip install --no-cache-dir cryptography>=41.0.0

# Verify
python3 -c "from cryptography.hazmat.backends import default_backend; print(default_backend())"
```

### Issue: PBX fails to start with FIPS enforcement

**Error**: `FIPS mode enforcement failed: cryptography library not available`

**Solution**:
```bash
# Install cryptography library
pip install cryptography>=41.0.0

# If still failing, check system FIPS
cat /proc/sys/crypto/fips_enabled

# If 0, enable system FIPS first
sudo ./scripts/enable_fips_ubuntu.sh
```

### Issue: Performance degradation with FIPS

**Cause**: FIPS encryption operations are more computationally intensive

**Mitigation**:
1. **Hardware acceleration**: Ensure CPU has AES-NI support
   ```bash
   grep aes /proc/cpuinfo
   ```

2. **Connection pooling**: Reduce authentication overhead by caching sessions

3. **Session caching**: Configure PBX to cache authenticated sessions

4. **Adjust iteration count** (only if absolutely necessary):
   - Default: 600,000 iterations (OWASP 2024 recommendation)
   - Minimum for FIPS: 10,000 iterations
   - Edit `pbx/utils/encryption.py` if needed (not recommended)

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Ubuntu Server installed (20.04+ LTS)
- [ ] System fully updated (`sudo apt-get update && sudo apt-get upgrade`)
- [ ] Static IP configured
- [ ] Firewall configured (UFW or iptables)
- [ ] Ubuntu Pro account created
- [ ] Backup strategy in place

### FIPS Configuration

- [ ] Ubuntu Pro attached (`sudo ua attach`)
- [ ] FIPS enabled (`sudo ua enable fips`)
- [ ] System rebooted
- [ ] Kernel FIPS verified (`cat /proc/sys/crypto/fips_enabled` = 1)
- [ ] OpenSSL FIPS verified (`openssl list -providers`)

### PBX Installation

- [ ] Dependencies installed
- [ ] Python 3.8+ installed
- [ ] Virtual environment created
- [ ] Requirements installed (`pip install -r requirements.txt`)
- [ ] Cryptography >= 41.0.0 verified
- [ ] Database configured (PostgreSQL recommended)
- [ ] Database schema initialized

### Security Configuration

- [ ] `config.yml` configured with `fips_mode: true`
- [ ] `config.yml` configured with `enforce_fips: true`
- [ ] Password policy configured (min 12 chars)
- [ ] TLS certificates generated (RSA-2048+)
- [ ] TLS enabled in config (`enable_tls: true`)
- [ ] SRTP enabled in config (`enable_srtp: true`)
- [ ] Audit logging enabled
- [ ] Rate limiting configured

### Verification

- [ ] FIPS verification script passed (`python3 scripts/verify_fips.py`)
- [ ] Encryption tests passed
- [ ] PBX starts successfully
- [ ] Extensions can register
- [ ] Calls can be placed
- [ ] TLS/SRTP working (if enabled)

### Monitoring

- [ ] Log monitoring configured
- [ ] Security audit logs enabled
- [ ] Failed authentication monitoring
- [ ] System health checks scheduled
- [ ] Backup automation configured

### Documentation

- [ ] Configuration documented
- [ ] Passwords stored in secure vault
- [ ] Network diagram updated
- [ ] Emergency procedures documented
- [ ] Support contacts identified

---

## Additional Resources

### Official Documentation

- [Ubuntu Pro FIPS](https://ubuntu.com/security/fips)
- [NIST FIPS 140-2 Standard](https://csrc.nist.gov/publications/detail/fips/140/2/final)
- [OpenSSL FIPS](https://www.openssl.org/docs/fips.html)

### PBX Documentation

- [FIPS Compliance Guide](FIPS_COMPLIANCE.md)
- [Security Best Practices](SECURITY_BEST_PRACTICES.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

### Support

For questions about Ubuntu FIPS deployment:
1. Review this guide and [FIPS_COMPLIANCE.md](FIPS_COMPLIANCE.md)
2. Run verification script: `python3 scripts/verify_fips.py`
3. Check Ubuntu Pro documentation: https://ubuntu.com/pro/tutorial
4. Consult with security team

---

## Version History

- **v1.0.0** (2025-12-09): Initial Ubuntu FIPS deployment guide
- Covers Ubuntu 20.04, 22.04, 24.04 LTS
- Ubuntu Pro FIPS and OpenSSL FIPS options
- Comprehensive verification procedures

---

**FIPS Status**: ✅ Ubuntu deployment ready for FIPS 140-2 compliance  
**Last Updated**: 2025-12-09  
**Version**: 1.0.0
