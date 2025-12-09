# FIPS 140-2 Quick Reference Guide

## ✅ System Status: FIPS-Enabled

Your Ubuntu server is already configured with FIPS 140-2 compliance network-wide. This guide provides quick reference commands and verification steps for the PBX system.

---

## Quick Verification Commands

### 1. Check System FIPS Status

```bash
# Kernel FIPS mode (should output: 1)
cat /proc/sys/crypto/fips_enabled

# OpenSSL FIPS provider (should list 'fips' provider)
openssl list -providers

# Python FIPS mode
python3 -c "import hashlib; print('FIPS:', hashlib.get_fips_mode())"
```

### 2. Verify PBX FIPS Configuration

```bash
cd /path/to/PBX

# Comprehensive FIPS verification
python3 scripts/verify_fips.py

# Quick health check
python3 scripts/check_fips_health.py

# Health check with JSON output (for monitoring)
python3 scripts/check_fips_health.py --json

# Silent health check (exit code only)
python3 scripts/check_fips_health.py --quiet
echo $?  # 0=healthy, 1=warning, 2=critical
```

---

## Expected Results on FIPS-Enabled Server

When running on your FIPS-enabled Ubuntu server, you should see:

### System Checks
- ✅ Kernel FIPS mode: **1**
- ✅ OpenSSL FIPS provider: **Active**
- ✅ Python hashlib FIPS: **Enabled**
- ✅ Cryptography backend: **FIPS: True**

### PBX Configuration
- ✅ FIPS mode: **Enabled** (`security.fips_mode: true`)
- ✅ FIPS enforcement: **Enabled** (`security.enforce_fips: true`)
- ✅ Password policy: **12+ characters, complexity required**
- ✅ Encryption: **AES-256-GCM, SHA-256, PBKDF2-HMAC-SHA256**

### Encryption Operations
- ✅ Password hashing: **PBKDF2-HMAC-SHA256 (600,000 iterations)**
- ✅ Data encryption: **AES-256-GCM**
- ✅ Hashing: **SHA-256**
- ✅ Random generation: **FIPS-compliant**

---

## PBX FIPS-Approved Algorithms

The PBX system uses only FIPS 140-2 approved algorithms:

| Operation | Algorithm | FIPS Standard |
|-----------|-----------|---------------|
| Symmetric Encryption | AES-256-GCM | FIPS 197 |
| Password Hashing | PBKDF2-HMAC-SHA256 | NIST SP 800-132 |
| Data Hashing | SHA-256 | FIPS 180-4 |
| TLS/SIPS | TLS 1.2/1.3 | RFC 5246/8446 |
| Media Encryption | SRTP with AES-GCM | RFC 3711 |
| Random Generation | secrets module | System CSPRNG |

---

## Configuration Checklist

Ensure these settings in `config.yml`:

```yaml
security:
  # FIPS Compliance
  fips_mode: true              # ✓ Enable FIPS-compliant encryption
  enforce_fips: true           # ✓ Fail if FIPS cannot be enabled
  
  # Password Policy (FIPS requirement)
  password:
    min_length: 12             # ✓ Minimum 12 characters
    require_uppercase: true    # ✓ Complexity requirements
    require_lowercase: true
    require_digit: true
    require_special: true
  
  # Transport Security (Recommended)
  enable_tls: true             # ⚠ Enable for SIPS
  tls_cert_file: "/etc/pbx/certs/server.crt"
  tls_key_file: "/etc/pbx/certs/server.key"
  
  # Media Security (Recommended)
  enable_srtp: true            # ⚠ Enable for encrypted RTP
```

---

## Common Scenarios

### Starting the PBX System

```bash
cd /path/to/PBX
python3 main.py
```

The PBX will automatically:
1. Check FIPS configuration
2. Verify cryptography library
3. Initialize FIPS-compliant encryption
4. Start services with FIPS mode enabled

### Startup Output (FIPS Enabled)

```
============================================================
InHouse PBX System v1.0.0
============================================================

Performing security checks...
✓ FIPS 140-2 mode is ENABLED
✓ Cryptography library available
✓ FIPS 140-2 compliance verified
✓ FIPS-compliant encryption initialized

============================================================
STARTING PBX SERVER
============================================================
```

### Adding New Extensions

When creating extensions, passwords are automatically hashed using FIPS-compliant PBKDF2:

```python
from pbx.core.pbx import PBXCore

pbx = PBXCore("config.yml")

# Password is automatically hashed with PBKDF2-HMAC-SHA256
pbx.extension_registry.add_extension(
    number="1001",
    name="John Doe",
    password="SecureP@ss123"  # Will be hashed with 600,000 iterations
)
```

---

## Monitoring FIPS Compliance

### Automated Health Checks

Add to crontab for periodic monitoring:

```bash
# Check FIPS health every hour
0 * * * * cd /path/to/PBX && python3 scripts/check_fips_health.py --quiet || echo "FIPS health check failed" | mail -s "PBX FIPS Alert" admin@company.com
```

### Integration with Monitoring Systems

The health check script outputs JSON for easy integration:

```bash
# Get JSON status
curl -s http://localhost:8080/health/fips

# Or run locally
python3 scripts/check_fips_health.py --json
```

Example JSON output:
```json
{
  "timestamp": "2025-12-09T01:00:00.000000",
  "status": "HEALTHY",
  "health_score": 100.0,
  "checks": {
    "kernel_fips": true,
    "python_fips": true,
    "cryptography_fips": true,
    "pbx_fips_mode": true,
    "pbx_enforce_fips": true,
    "encryption_operations": true
  },
  "summary": {
    "passed": 5,
    "total": 5
  }
}
```

---

## Troubleshooting

### Issue: PBX Won't Start

**Error**: `FIPS mode enforcement failed`

**Solution**: Verify system FIPS is enabled:
```bash
cat /proc/sys/crypto/fips_enabled  # Should be 1
python3 scripts/verify_fips.py     # Run full verification
```

### Issue: Performance Concerns

FIPS encryption is computationally intensive. To optimize:

1. **Check CPU features**:
   ```bash
   grep aes /proc/cpuinfo  # Should show AES-NI support
   ```

2. **Monitor performance**:
   ```bash
   # Check authentication times
   grep "Authentication" /path/to/logs/pbx.log | tail -20
   ```

3. **Expected overhead**:
   - Password hashing: ~600ms per authentication
   - TLS handshake: ~50-100ms
   - SRTP encryption: <5% CPU overhead

### Issue: Extension Authentication Failing

**Cause**: Old non-hashed passwords in database

**Solution**: Migrate passwords to FIPS-compliant hashed format:
```bash
cd /path/to/PBX
python3 scripts/migrate_passwords.py  # If you have this script
```

Or manually update through admin interface.

---

## Security Best Practices

### 1. TLS Certificate Management

Generate FIPS-compliant certificates:
```bash
# Use RSA-2048 or RSA-4096 (FIPS-approved)
openssl genrsa -out server.key 2048

# Generate CSR
openssl req -new -key server.key -out server.csr

# For production, get CA-signed certificate
```

### 2. Password Policy Enforcement

The system enforces strong passwords by default:
- Minimum 12 characters
- Must include: uppercase, lowercase, digit, special character
- Cannot be common passwords

### 3. Audit Logging

All security events are logged:
```bash
# View security audit log
tail -f /path/to/logs/pbx.log | grep SECURITY
```

### 4. Rate Limiting

Built-in protection against brute force:
- Max 5 failed attempts per 5 minutes
- 15-minute lockout after threshold
- Automatic IP blocking for repeated violations

---

## Documentation Links

- **Comprehensive Guide**: [FIPS_COMPLIANCE.md](FIPS_COMPLIANCE.md)
- **Ubuntu Deployment**: [UBUNTU_FIPS_GUIDE.md](UBUNTU_FIPS_GUIDE.md)
- **Security Practices**: [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md)

---

## Support Commands

```bash
# Full FIPS verification with detailed output
python3 scripts/verify_fips.py

# Quick health status
python3 scripts/check_fips_health.py

# View encryption configuration
grep -A 20 "security:" config.yml

# Check PBX logs for FIPS messages
grep -i fips /path/to/logs/pbx.log

# Test encryption operations
python3 -c "
from pbx.utils.encryption import get_encryption
enc = get_encryption(fips_mode=True)
print('FIPS encryption test: OK')
"
```

---

## Exit Codes

Health check script exit codes:
- **0**: Healthy (all checks passed)
- **1**: Warning (80%+ checks passed)
- **2**: Critical (<80% checks passed)

---

**Status**: ✅ FIPS 140-2 compliant system  
**Version**: 1.0.0  
**Last Updated**: 2025-12-09
