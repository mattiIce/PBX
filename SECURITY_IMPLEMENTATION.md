# Security Implementation Guide

## Overview

This document describes the comprehensive security features implemented in the PBX system, including FIPS 140-2 compliance, password policies, rate limiting, and audit logging.

---

## Table of Contents

1. [FIPS 140-2 Compliance](#fips-140-2-compliance)
2. [Password Security](#password-security)
3. [Rate Limiting & Brute Force Protection](#rate-limiting--brute-force-protection)
4. [Security Audit Logging](#security-audit-logging)
5. [Environment Variable Support](#environment-variable-support)
6. [REST API Security Headers](#rest-api-security-headers)
7. [Database Security](#database-security)
8. [Configuration](#configuration)
9. [Migration Guide](#migration-guide)

---

## FIPS 140-2 Compliance

### What is FIPS 140-2?

FIPS (Federal Information Processing Standards) 140-2 is a U.S. government security standard that specifies security requirements for cryptographic modules. The PBX system implements FIPS 140-2 compliant cryptography using approved algorithms.

### Compliance Status

✅ **FIPS 140-2 MODE IS ENABLED AND ENFORCED**

The system uses:
- **PBKDF2-HMAC-SHA256** for password hashing (NIST SP 800-132)
- **AES-256-GCM** for data encryption (FIPS 197)
- **SHA-256** for checksums and hashing (FIPS 180-4)
- **600,000 iterations** for key derivation (OWASP 2024 recommendation, enhanced from 100,000)

### Requirements

To enable FIPS mode, the system requires:

```bash
pip install cryptography>=41.0.0
```

### FIPS Enforcement

The system enforces FIPS compliance at startup. If FIPS mode is enabled but the cryptography library is not available, the system will:

1. **Log an error** explaining the requirement
2. **Refuse to start** if `enforce_fips: true` in configuration
3. **Display clear error message** with installation instructions

Example startup output with FIPS enabled:

```
Performing security checks...
✓ FIPS 140-2 mode is ENABLED
✓ Cryptography library available
✓ FIPS 140-2 compliance verified
✓ FIPS-compliant encryption initialized
```

### Configuration

In `config.yml`:

```yaml
security:
  fips_mode: true  # Enable FIPS 140-2 compliance
  enforce_fips: true  # Fail startup if FIPS unavailable
```

### Verification

Run FIPS compliance tests:

```bash
python tests/test_fips.py
```

Expected output:
```
Results: 5 passed, 0 failed
✅ All FIPS compliance tests passed!
```

---

## Password Security

### Password Policy

The system enforces strong password requirements:

#### Default Requirements

- **Minimum Length**: 12 characters
- **Maximum Length**: 128 characters
- **Uppercase Letters**: At least 1 required
- **Lowercase Letters**: At least 1 required
- **Digits**: At least 1 required
- **Special Characters**: At least 1 required (`!@#$%^&*()_+-=[]{}|;:,.<>?`)

#### Additional Protections

- **Common Password Blocking**: Rejects passwords like "password123", "admin", etc.
- **Sequential Character Detection**: Rejects passwords with 4+ sequential characters (e.g., "abcd", "1234")
- **Repeated Character Detection**: Rejects passwords with 4+ repeated characters (e.g., "aaaa")
- **Case-Insensitive Checking**: Prevents common password variations

### Password Storage

✅ **All passwords are hashed using FIPS-compliant PBKDF2-HMAC-SHA256**

- **Never stored in plaintext**
- **Unique random salt** for each password (32 bytes)
- **100,000 iterations** for key derivation
- **Base64 encoding** for database storage
- **Constant-time comparison** to prevent timing attacks

### Password Migration

To migrate existing plaintext passwords to secure hashed storage:

```bash
# Dry run (see what would be migrated)
python scripts/migrate_passwords_to_database.py --dry-run

# Perform actual migration
python scripts/migrate_passwords_to_database.py
```

The migration script:
- ✓ Hashes all extension passwords
- ✓ Hashes all voicemail PINs
- ✓ Stores hashes with salts in database
- ✓ Skips already migrated extensions
- ✓ Provides detailed progress and error reporting

### Configuration

In `config.yml`:

```yaml
security:
  password:
    min_length: 12
    max_length: 128
    require_uppercase: true
    require_lowercase: true
    require_digit: true
    require_special: true
```

---

## Rate Limiting & Brute Force Protection

### Overview

The system protects against brute force attacks using configurable rate limiting.

### How It Works

1. **Failed Attempt Tracking**: Each failed login is recorded with timestamp
2. **Time Window**: Attempts are counted within a sliding time window (default: 5 minutes)
3. **Automatic Lockout**: After max attempts exceeded, account is locked
4. **Lockout Duration**: Locked accounts automatically unlock after duration expires (default: 15 minutes)
5. **Successful Login**: Clears all failed attempts for that user

### Configuration

```yaml
security:
  rate_limit:
    max_attempts: 5  # Maximum failed login attempts
    window_seconds: 300  # Time window (5 minutes)
    lockout_duration: 900  # Lockout time (15 minutes)
```

### Example Scenario

1. User tries wrong password 5 times in 3 minutes
2. System locks out user for 15 minutes
3. After 15 minutes, lockout automatically expires
4. User can try again (failed attempts reset)

### Logging

Rate limit events are logged:

```
2025-12-06 12:44:00 - PBX - WARNING - Rate limit exceeded for user1234. Locked out for 900 seconds
```

---

## Security Audit Logging

### Overview

All security-related events are logged for audit purposes.

### Event Types

The system logs:
- `login_success` - Successful authentication
- `login_failure` - Failed authentication attempt
- `password_change` - Password modification
- `password_reset` - Password reset operation
- `account_locked` - Account locked due to rate limit
- `account_unlocked` - Account unlocked (manual or automatic)
- `permission_denied` - Authorization failure
- `config_change` - Security configuration change
- `suspicious_activity` - Unusual activity detected

### Storage

Audit logs are stored in two locations:

1. **Database Table** (`security_audit`):
   - Permanent storage
   - Queryable for analysis
   - Indexed for performance

2. **Application Logs**:
   - Real-time monitoring
   - Log level: INFO (success) or WARNING (failure)

### Audit Log Schema

```sql
CREATE TABLE security_audit (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    event_type VARCHAR(50),
    identifier VARCHAR(100),  -- username, extension, etc.
    ip_address VARCHAR(45),
    success BOOLEAN,
    details TEXT  -- JSON format
);
```

### Example Log Entry

```
2025-12-06 12:44:00 - PBX - INFO - SECURITY: login_success - ext1001 from 192.168.1.100 - SUCCESS
```

### Querying Audit Logs

SQL examples:

```sql
-- Recent failed logins
SELECT * FROM security_audit 
WHERE event_type = 'login_failure' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Login attempts by user
SELECT identifier, success, COUNT(*) as attempts
FROM security_audit
WHERE event_type IN ('login_success', 'login_failure')
GROUP BY identifier, success;

-- Suspicious activity
SELECT * FROM security_audit
WHERE event_type = 'suspicious_activity'
OR (event_type = 'login_failure' AND identifier IN (
    SELECT identifier FROM security_audit
    WHERE event_type = 'login_failure'
    GROUP BY identifier
    HAVING COUNT(*) > 10
));
```

### Configuration

```yaml
security:
  audit:
    enabled: true
    log_to_database: true
    log_to_file: false  # Optional file logging
    log_file: 'logs/security_audit.log'
```

---

## Environment Variable Support

### Overview

Sensitive configuration values (passwords, API keys) should **never** be stored in version control. Use environment variables instead.

### Usage

In `config.yml`, reference environment variables:

```yaml
database:
  password: ${DB_PASSWORD}  # From environment

integrations:
  active_directory:
    bind_password: ${AD_BIND_PASSWORD}
```

### .env File

Create a `.env` file (never commit this!):

```bash
# Database
DB_PASSWORD=YourSecurePassword123!

# Active Directory
AD_BIND_PASSWORD=YourADPassword456!

# Integrations
ZOOM_CLIENT_SECRET=your-zoom-secret
OUTLOOK_CLIENT_SECRET=your-outlook-secret
```

### Automatic Loading

The system automatically:
1. Loads `.env` file if it exists
2. Resolves `${VAR_NAME}` references in configuration
3. Falls back to hardcoded values if env var not found
4. Logs warnings for missing critical variables

### Supported Formats

Both formats are supported:

```yaml
# ${VAR_NAME} format (recommended)
password: ${DB_PASSWORD}

# $VAR_NAME format
password: $DB_PASSWORD
```

---

## REST API Security Headers

### Implemented Headers

The REST API includes comprehensive security headers:

#### X-Content-Type-Options
```
X-Content-Type-Options: nosniff
```
Prevents MIME type sniffing attacks.

#### X-Frame-Options
```
X-Frame-Options: DENY
```
Prevents clickjacking attacks by blocking framing.

#### X-XSS-Protection
```
X-XSS-Protection: 1; mode=block
```
Enables browser XSS filter (for older browsers).

#### Content-Security-Policy
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
```
Restricts resource loading to prevent XSS and data injection.

#### Referrer-Policy
```
Referrer-Policy: strict-origin-when-cross-origin
```
Controls referrer information sent with requests.

#### Permissions-Policy
```
Permissions-Policy: geolocation=(), microphone=(), camera=()
```
Disables unnecessary browser features.

### HTTPS Only (When TLS Enabled)

When TLS is enabled, the system also sends:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

This enforces HTTPS connections for one year.

---

## Database Security

### Secure Password Storage

Extension passwords are stored securely:

```sql
CREATE TABLE extensions (
    ...
    password_hash VARCHAR(255) NOT NULL,  -- PBKDF2-HMAC-SHA256 hash
    password_salt VARCHAR(255),           -- Unique random salt
    voicemail_pin_hash VARCHAR(255),      -- Hashed PIN
    voicemail_pin_salt VARCHAR(255),      -- PIN salt
    password_changed_at TIMESTAMP,        -- Track password age
    failed_login_attempts INTEGER,        -- Brute force tracking
    account_locked_until TIMESTAMP,       -- Lockout expiry
    ...
);
```

### Benefits

- ✓ **Rainbow table attacks prevented** (unique salts)
- ✓ **Brute force attacks slowed** (100,000 iterations)
- ✓ **Password age tracking** (for rotation policies)
- ✓ **Account lockout support** (automatic brute force protection)

### Database Connection Security

Use environment variables for credentials:

```yaml
database:
  type: postgresql
  host: ${DB_HOST}
  user: ${DB_USER}
  password: ${DB_PASSWORD}  # Never hardcode!
```

### Connection Encryption

For PostgreSQL, enable SSL:

```yaml
database:
  type: postgresql
  ssl_mode: require  # or 'verify-full' for certificate validation
```

---

## Configuration

### Complete Security Configuration

```yaml
security:
  # FIPS Compliance (REQUIRED FOR PRODUCTION)
  fips_mode: true
  enforce_fips: true
  
  # Password Policy
  password:
    min_length: 12
    max_length: 128
    require_uppercase: true
    require_lowercase: true
    require_digit: true
    require_special: true
  
  # Rate Limiting
  rate_limit:
    max_attempts: 5
    window_seconds: 300
    lockout_duration: 900
  
  # Security Audit
  audit:
    enabled: true
    log_to_database: true
    log_to_file: false
  
  # TLS/SSL
  enable_tls: false  # Enable for production
  tls_cert_file: '/path/to/cert.pem'
  tls_key_file: '/path/to/key.pem'
  
  # SRTP
  enable_srtp: false  # Enable for encrypted media
```

---

## Migration Guide

### From Plaintext to Hashed Passwords

#### Step 1: Backup Configuration

```bash
cp config.yml config.yml.backup
```

#### Step 2: Run Migration (Dry Run)

```bash
python scripts/migrate_passwords_to_database.py --dry-run
```

Review output to ensure everything looks correct.

#### Step 3: Perform Migration

```bash
python scripts/migrate_passwords_to_database.py
```

Example output:

```
======================================================================
Extension Password Migration to Secure Database Storage
======================================================================

✓ Connected to database
✓ Database tables ready

Found 4 extensions in configuration

Processing extension 1001 (Codi Mattinson)...
  ✓ Password hashed successfully
  ✓ Migrated successfully

Processing extension 1002 (Bill Sautter)...
  ✓ Password hashed successfully
  ✓ Migrated successfully

...

======================================================================
Migration Summary
======================================================================
Total extensions: 4
Migrated: 4
Skipped: 0
Errors: 0

✓ Migration completed successfully!
```

#### Step 4: Verify Migration

Test extension authentication:

```bash
# Try registering a SIP phone
# Or test via API
curl -X POST http://localhost:8080/api/auth \
  -H "Content-Type: application/json" \
  -d '{"extension":"1001","password":"password1001"}'
```

#### Step 5: Remove Plaintext Passwords (Optional)

Once migration is verified, you can remove plaintext passwords from `config.yml`:

```yaml
extensions:
- number: '1001'
  name: Codi Mattinson
  # password: removed - now in database
  email: 'cmattinson@albl.com'
```

---

## Best Practices

### 1. Use Environment Variables

✅ **DO**:
```yaml
password: ${DB_PASSWORD}
```

❌ **DON'T**:
```yaml
password: 'MyPassword123!'
```

### 2. Enable FIPS Mode

✅ **DO**:
```yaml
security:
  fips_mode: true
  enforce_fips: true
```

### 3. Strong Password Policy

✅ **DO**:
```yaml
security:
  password:
    min_length: 12
    require_uppercase: true
    require_lowercase: true
    require_digit: true
    require_special: true
```

### 4. Enable Audit Logging

✅ **DO**:
```yaml
security:
  audit:
    enabled: true
    log_to_database: true
```

### 5. Regular Security Reviews

- Review audit logs weekly
- Monitor failed login attempts
- Update passwords every 90 days
- Keep cryptography library updated
- Review security configuration quarterly

---

## Testing

### Run Security Tests

```bash
# Password policy and security features
python tests/test_security.py

# FIPS compliance
python tests/test_fips.py

# All stub tests (includes security)
python tests/test_stub_implementations.py
```

### Expected Results

```
============================================================
Running Security Tests
============================================================

✓ Password policy validation works
✓ Password generation works
✓ Rate limiter works
✓ Security auditor works
✓ Password manager works
✓ Password migration compatibility verified

Results: 6 passed, 0 failed
============================================================
```

---

## Troubleshooting

### FIPS Mode Fails to Start

**Error**: `FIPS mode enforcement failed: cryptography library not available`

**Solution**:
```bash
pip install cryptography
```

### Environment Variables Not Loaded

**Error**: `Environment variable DB_PASSWORD not found`

**Solution**:
1. Create `.env` file in PBX root directory
2. Add: `DB_PASSWORD=your_password_here`
3. Ensure `.env` is in `.gitignore`

### Migration Fails

**Error**: `Failed to connect to database`

**Solution**:
1. Check database is running
2. Verify database credentials in config.yml
3. Ensure database user has INSERT/UPDATE permissions

### Rate Limit False Positives

**Issue**: Legitimate users getting locked out

**Solution**:
Adjust rate limit settings:
```yaml
security:
  rate_limit:
    max_attempts: 10  # Increase
    window_seconds: 600  # Increase window
```

---

## Security Checklist

### Pre-Production

- [ ] FIPS mode enabled (`fips_mode: true`)
- [ ] FIPS enforcement enabled (`enforce_fips: true`)
- [ ] Cryptography library installed
- [ ] All passwords migrated to database
- [ ] Environment variables configured in `.env`
- [ ] `.env` file added to `.gitignore`
- [ ] No plaintext passwords in config.yml
- [ ] Strong password policy enabled
- [ ] Rate limiting configured
- [ ] Audit logging enabled
- [ ] TLS/SSL certificates configured
- [ ] Database connection uses SSL
- [ ] Security tests passing

### Post-Deployment

- [ ] Verify FIPS mode active (check logs)
- [ ] Test extension authentication
- [ ] Review security audit logs
- [ ] Monitor failed login attempts
- [ ] Backup database regularly
- [ ] Document security procedures
- [ ] Train staff on security practices

---

## Support

For security issues or questions:
1. Review this documentation
2. Check test files for examples
3. Review security audit logs
4. Consult FIPS documentation: https://csrc.nist.gov/publications/detail/fips/140/2/final

**Report Security Vulnerabilities**: Contact security team immediately

---

**Last Updated**: December 6, 2025
**Version**: 1.0.0
**FIPS Compliance**: ✅ ENABLED AND ENFORCED
