# Security Compliance Check

This directory contains comprehensive security compliance checking tools for the Warden VoIP PBX system.

## Overview

The security compliance checker validates the system against:
- **FIPS 140-2** - Federal Information Processing Standard for cryptographic modules
- **SOC 2 Type 2** - Service Organization Control 2 for secure service delivery

## Scripts

### security_compliance_check.py

**Purpose**: Comprehensive security compliance audit covering FIPS 140-2 and SOC 2 Type 2 requirements

**Usage**:
```bash
# Full compliance check with detailed output
python scripts/security_compliance_check.py

# JSON output for automation
python scripts/security_compliance_check.py --json

# Save report to file
python scripts/security_compliance_check.py --output compliance_report.json

# Quiet mode (exit code only)
python scripts/security_compliance_check.py --quiet
```

**What it checks**:

#### FIPS 140-2 Compliance
- ✓ Kernel FIPS mode enabled
- ✓ OpenSSL FIPS provider available
- ✓ Cryptography library installed and configured
- ✓ PBX FIPS mode enabled in config.yml
- ✓ FIPS-approved algorithms:
  - PBKDF2-HMAC-SHA256 (600,000 iterations)
  - SHA-256 hashing
  - AES-256-GCM encryption

#### SOC 2 Type 2 Compliance
- ✓ Control implementation status
- ✓ Control testing coverage
- ✓ Category compliance (Security, Availability, Processing Integrity, Confidentiality)
- ✓ Implementation percentage

#### Security Configuration
- ✓ Authentication required
- ✓ Password policy (minimum 12 characters)
- ✓ Failed login protection
- ✓ TLS/SIPS enabled (recommended)
- ✓ SRTP enabled (recommended)
- ✓ API authentication

**Exit codes**:
- `0` - Fully compliant or compliant with warnings
- `1` - Non-compliant (critical issues found)
- `2` - Error during check
- `130` - Cancelled by user

### verify_fips.py

**Purpose**: Detailed FIPS 140-2 compliance verification

**Usage**:
```bash
python scripts/verify_fips.py
```

**What it checks**:
- System FIPS configuration
- Cryptography library version and configuration
- PBX FIPS settings
- Encryption operations testing
- Python dependencies

### check_fips_health.py

**Purpose**: Quick FIPS health check for monitoring

**Usage**:
```bash
# Human-readable output
python scripts/check_fips_health.py

# JSON output
python scripts/check_fips_health.py --json

# Quiet mode (for cron jobs)
python scripts/check_fips_health.py --quiet
```

**Monitoring integration**:
```bash
# Add to crontab for regular monitoring
*/15 * * * * /opt/PBX/scripts/check_fips_health.py --quiet || /usr/bin/alert-admin
```

## Compliance Reports

### JSON Report Format

```json
{
  "timestamp": "2024-12-29T12:00:00.000000",
  "fips": {
    "compliant": true,
    "checks": {
      "kernel_fips": true,
      "openssl_fips": true,
      "crypto_library": true,
      "pbx_fips_mode": true,
      "pbkdf2_sha256": true,
      "sha256": true,
      "aes_256_gcm": true
    },
    "issues": []
  },
  "soc2": {
    "compliant": true,
    "controls": {
      "Security": {"total": 10, "implemented": 10},
      "Availability": {"total": 2, "implemented": 2},
      "Processing Integrity": {"total": 2, "implemented": 2},
      "Confidentiality": {"total": 2, "implemented": 2}
    },
    "summary": {
      "total_controls": 16,
      "implemented": 16,
      "pending": 0,
      "tested": 16,
      "compliance_percentage": 100.0
    },
    "issues": []
  },
  "security": {
    "compliant": true,
    "checks": {
      "require_authentication": true,
      "password_min_length": true,
      "max_failed_attempts": true,
      "tls_enabled": true,
      "srtp_enabled": true,
      "api_authentication": true
    },
    "issues": []
  },
  "overall": {
    "status": "COMPLIANT",
    "fips_compliant": true,
    "soc2_compliant": true,
    "security_ok": true,
    "exit_code": 0
  }
}
```

## Achieving Compliance

### FIPS 140-2 Compliance

#### 1. Enable System FIPS Mode (Ubuntu Pro)

```bash
# For Ubuntu Pro subscribers
sudo scripts/enable_fips_ubuntu.sh

# Verify kernel FIPS mode
cat /proc/sys/crypto/fips_enabled
# Should output: 1
```

#### 2. Configure PBX for FIPS

Edit `config.yml`:
```yaml
security:
  fips_mode: true              # Enable FIPS mode
  enforce_fips: true           # Enforce FIPS requirements
  
  # Password policy
  password:
    min_length: 12
    require_strong_passwords: true
    iterations: 600000          # PBKDF2 iterations
  
  # Encryption
  enable_tls: true             # TLS for SIP signaling
  enable_srtp: true            # SRTP for media encryption
```

#### 3. Install Required Libraries

```bash
pip install cryptography>=41.0.0
```

#### 4. Verify Compliance

```bash
python scripts/verify_fips.py
```

### SOC 2 Type 2 Compliance

#### 1. Initialize SOC 2 Controls

The system automatically creates 16 default SOC 2 controls covering:
- **Security** (10 controls)
- **Availability** (2 controls)
- **Processing Integrity** (2 controls)
- **Confidentiality** (2 controls)

#### 2. Review Control Implementation

```bash
# Check current status
python scripts/security_compliance_check.py

# View controls via API
curl http://localhost:8080/api/framework/compliance/soc2/controls
```

#### 3. Test Controls

Document testing in the database:
```python
from pbx.features.compliance_framework import SOC2ComplianceEngine

engine = SOC2ComplianceEngine(db, config)

# Update control test results
engine.update_control_test(
    control_id="CC6.1",
    test_results="Passed - Quarterly audit on 2024-12-29"
)
```

#### 4. Generate Compliance Report

```bash
# Generate detailed report
python scripts/security_compliance_check.py --output soc2_report.json
```

## Troubleshooting

### FIPS Mode Issues

**Problem**: Kernel FIPS mode not enabled

**Solution**:
```bash
# Check if Ubuntu Pro FIPS is available
sudo pro status

# Enable FIPS (requires Ubuntu Pro)
sudo pro enable fips
sudo reboot

# Verify
cat /proc/sys/crypto/fips_enabled
```

**Problem**: Cryptography operations fail in FIPS mode

**Solution**:
```bash
# Verify cryptography library version
pip show cryptography

# Upgrade if needed
pip install --upgrade 'cryptography>=41.0.0'

# Test encryption
python -c "from pbx.utils.encryption import get_encryption; enc = get_encryption(fips_mode=True); print('OK')"
```

### SOC 2 Issues

**Problem**: No controls found in database

**Solution**:
The system automatically initializes controls on first run. If missing:
```python
from pbx.features.compliance_framework import SOC2ComplianceEngine
from pbx.utils.database import DatabaseBackend
from pbx.utils.config import Config

config = Config("config.yml")
db = DatabaseBackend(config)
engine = SOC2ComplianceEngine(db, config.config)

# Initialize default controls
# (happens automatically in __init__)
```

**Problem**: Control testing percentage too low

**Solution**:
```bash
# Review all controls
curl http://localhost:8080/api/framework/compliance/soc2/controls

# Update test results for each control
curl -X POST http://localhost:8080/api/framework/compliance/soc2/control \
  -H "Content-Type: application/json" \
  -d '{
    "control_id": "CC6.1",
    "test_results": "Passed - Testing date and results"
  }'
```

## Production Deployment Checklist

Before deploying to production, ensure:

### FIPS Requirements
- [ ] Kernel FIPS mode enabled (`cat /proc/sys/crypto/fips_enabled` = 1)
- [ ] OpenSSL FIPS provider available
- [ ] Cryptography library >= 41.0.0 installed
- [ ] PBX FIPS mode enabled in config.yml
- [ ] All encryption tests pass

### SOC 2 Requirements
- [ ] All 16 default controls implemented
- [ ] Controls tested within last 90 days
- [ ] Test results documented
- [ ] Compliance percentage = 100%

### Security Configuration
- [ ] Authentication required
- [ ] Password minimum length >= 12
- [ ] Failed login protection enabled
- [ ] TLS/SIPS enabled for production
- [ ] SRTP enabled for media encryption
- [ ] API authentication enabled

### Verification
```bash
# Run full compliance check
python scripts/security_compliance_check.py

# Should output:
# ✓ OVERALL STATUS: FULLY COMPLIANT
```

## Continuous Compliance Monitoring

### Automated Monitoring

Add to crontab for regular checks:
```bash
# Check compliance daily at 2 AM
0 2 * * * cd /opt/PBX && python scripts/security_compliance_check.py --output /var/log/pbx/compliance_$(date +\%Y\%m\%d).json

# Quick health check every hour
0 * * * * cd /opt/PBX && python scripts/check_fips_health.py --quiet || /usr/local/bin/alert-admin
```

### Integration with Monitoring Systems

**Prometheus/Grafana**:
```bash
# Export metrics
python scripts/security_compliance_check.py --json | jq '.overall.status' > /var/lib/node_exporter/textfile_collector/pbx_compliance.prom
```

**Nagios/Icinga**:
```bash
# Use exit code for monitoring
python scripts/security_compliance_check.py --quiet
# Exit code: 0=OK, 1=WARNING, 2=CRITICAL
```

## Related Documentation

- [SECURITY_GUIDE.md](../SECURITY_GUIDE.md) - Comprehensive security documentation
- [REGULATIONS_COMPLIANCE_GUIDE.md](../REGULATIONS_COMPLIANCE_GUIDE.md) - Regulatory compliance
- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - Production deployment
- [API_DOCUMENTATION.md](../API_DOCUMENTATION.md) - API reference for compliance endpoints

## Support

For issues or questions:
1. Review this documentation
2. Check existing security guides
3. Run the compliance checker with verbose output
4. Review logs in `/var/log/pbx/`

---

**Last Updated**: 2024-12-29
**Status**: Production Ready
