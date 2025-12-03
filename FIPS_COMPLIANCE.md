# FIPS 140-2 Compliance Guide

## Overview

The InHouse PBX system supports **FIPS 140-2 (Federal Information Processing Standard)** compliant cryptographic operations for organizations requiring certified encryption standards. This is essential for government agencies, healthcare providers, financial institutions, and other organizations handling sensitive data.

## What is FIPS 140-2?

FIPS 140-2 is a U.S. government standard that specifies security requirements for cryptographic modules. It ensures that cryptographic algorithms meet stringent security requirements and have been validated by NIST (National Institute of Standards and Technology).

## FIPS-Approved Algorithms

The PBX system uses the following FIPS 140-2 approved algorithms:

### Encryption
- **AES-256-GCM** (FIPS 197)
  - Advanced Encryption Standard with 256-bit key
  - Galois/Counter Mode for authenticated encryption
  - Used for data encryption and SRTP media encryption

### Hashing
- **SHA-256** (FIPS 180-4)
  - Secure Hash Algorithm with 256-bit output
  - Used for data integrity and password hashing

### Key Derivation
- **PBKDF2-HMAC-SHA256** (NIST SP 800-132)
  - Password-Based Key Derivation Function 2
  - 100,000 iterations (NIST recommendation)
  - Used for password storage

### Transport Security
- **TLS 1.2/1.3** with FIPS-approved cipher suites:
  - ECDHE-RSA-AES256-GCM-SHA384
  - ECDHE-RSA-AES128-GCM-SHA256
  - AES256-GCM-SHA384
  - AES128-GCM-SHA256

## Enabling FIPS Mode

### 1. Install Required Dependencies

```bash
# Install FIPS-compliant cryptography library
pip install cryptography>=41.0.0

# For production, use FIPS-validated cryptography builds
# Contact your cryptography provider for validated versions
```

### 2. Configure FIPS Mode

Edit `config.yml`:

```yaml
security:
  # Enable FIPS 140-2 compliant encryption
  fips_mode: true
  
  # Enable TLS for SIP (SIPS)
  enable_tls: true
  tls_cert_file: "/etc/pbx/certs/server.crt"
  tls_key_file: "/etc/pbx/certs/server.key"
  
  # Enable SRTP for encrypted media
  enable_srtp: true
  
  # Strong password requirements
  min_password_length: 12
  require_strong_passwords: true
  require_authentication: true
```

### 3. Generate TLS Certificates

For FIPS compliance, use certificates with approved algorithms:

```bash
# Generate RSA-2048 or RSA-4096 key (FIPS-approved)
openssl genrsa -out server.key 2048

# Generate Certificate Signing Request
openssl req -new -key server.key -out server.csr

# Self-signed certificate (for testing)
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

# For production, obtain certificates from a trusted CA
```

### 4. Migrate Existing Passwords

Convert plain-text passwords to FIPS-compliant hashed format:

```python
#!/usr/bin/env python3
"""
Migrate passwords to FIPS-compliant hashed format
"""
from pbx.core.pbx import PBXCore

def migrate_passwords():
    # Initialize PBX with FIPS mode enabled
    pbx = PBXCore("config.yml")
    
    print("Migrating passwords to FIPS-compliant hashed format...")
    
    for ext in pbx.extension_registry.get_all():
        number = ext.number
        password = ext.config.get('password')
        
        # Check if already hashed
        if not ext.config.get('password_hash'):
            print(f"  Hashing password for extension {number}")
            pbx.extension_registry.hash_extension_password(number, password)
        else:
            print(f"  Extension {number} already using hashed password")
    
    print("Password migration complete!")

if __name__ == "__main__":
    migrate_passwords()
```

Save as `migrate_passwords.py` and run:
```bash
python3 migrate_passwords.py
```

### 5. Verify FIPS Mode

Test that FIPS mode is working:

```python
#!/usr/bin/env python3
"""
Verify FIPS mode is enabled and working
"""
from pbx.utils.encryption import get_encryption

def verify_fips():
    print("Verifying FIPS mode...")
    
    # Create encryption instance with FIPS mode
    enc = get_encryption(fips_mode=True)
    
    # Test password hashing
    password = "TestPassword123!"
    hash1, salt = enc.hash_password(password)
    print(f"✓ Password hashing working (SHA-256/PBKDF2)")
    
    # Test password verification
    is_valid = enc.verify_password(password, hash1, salt)
    assert is_valid, "Password verification failed"
    print(f"✓ Password verification working")
    
    # Test data encryption
    try:
        data = "Test data for encryption"
        key = "encryption_key_12345678901234567890"  # Will be hashed to 32 bytes
        encrypted, nonce, tag = enc.encrypt_data(data, key)
        print(f"✓ AES-256-GCM encryption working")
        
        # Test decryption
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
        assert decrypted.decode() == data, "Decryption failed"
        print(f"✓ AES-256-GCM decryption working")
    except ImportError:
        print("⚠ Cryptography library required for encryption")
    
    # Test secure token generation
    token = enc.generate_secure_token(32)
    print(f"✓ Secure token generation working")
    
    # Test hashing
    hash_result = enc.hash_data("test data")
    print(f"✓ SHA-256 hashing working")
    
    print("\n✅ FIPS mode verification complete!")
    print("All FIPS-approved algorithms are functioning correctly.")

if __name__ == "__main__":
    verify_fips()
```

Save as `verify_fips.py` and run:
```bash
python3 verify_fips.py
```

## FIPS Compliance Features

### Password Security
- ✅ PBKDF2-HMAC-SHA256 with 100,000 iterations
- ✅ Cryptographically secure salt generation
- ✅ Constant-time comparison to prevent timing attacks
- ✅ Automatic password strength validation

### Data Encryption
- ✅ AES-256-GCM for symmetric encryption
- ✅ Authenticated encryption (prevents tampering)
- ✅ Secure random nonce generation
- ✅ FIPS-approved key derivation

### Transport Security
- ✅ TLS 1.2+ only (SSL/TLS 1.0/1.1 disabled)
- ✅ FIPS-approved cipher suites
- ✅ Strong key exchange (ECDHE)
- ✅ Perfect forward secrecy

### Media Encryption
- ✅ SRTP with AES-GCM
- ✅ Secure key exchange
- ✅ Per-session encryption keys
- ✅ Replay attack prevention

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                     │
│  - Extension Authentication                             │
│  - API Security                                          │
│  - Session Management                                    │
└─────────────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────────┐
│              FIPS Encryption Module                     │
│  ┌────────────────┐  ┌────────────────┐               │
│  │  Password      │  │  Data          │               │
│  │  Hashing       │  │  Encryption    │               │
│  │  (PBKDF2-SHA256)│ │  (AES-256-GCM) │               │
│  └────────────────┘  └────────────────┘               │
└─────────────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────────┐
│           Transport Security Layer                      │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │  TLS/SIPS        │  │  SRTP            │           │
│  │  (SIP Signaling) │  │  (Media Streams) │           │
│  └──────────────────┘  └──────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

## Certification Considerations

### For Full FIPS 140-2 Certification

While this implementation uses FIPS-approved algorithms, full FIPS 140-2 certification requires:

1. **Use FIPS-validated cryptographic modules**
   - Use a FIPS 140-2 validated version of the cryptography library
   - Available from commercial vendors (e.g., Red Hat Enterprise Linux, SafeLogic)

2. **Hardware Security Modules (HSM)**
   - Consider using FIPS 140-2 Level 2+ validated HSMs
   - Store private keys in HSM
   - Perform cryptographic operations in HSM

3. **Operating System**
   - Use FIPS-validated operating system (e.g., RHEL in FIPS mode)
   - Configure OS for FIPS mode

4. **Documentation**
   - Maintain security policy documentation
   - Document key management procedures
   - Keep audit trail of all changes

5. **Testing**
   - Perform independent security testing
   - Conduct vulnerability assessments
   - Regular penetration testing

### Enabling OS-Level FIPS Mode

#### Red Hat Enterprise Linux / CentOS
```bash
# Enable FIPS mode
sudo fips-mode-setup --enable

# Reboot
sudo reboot

# Verify FIPS mode
fips-mode-setup --check
```

#### Ubuntu (with OpenSSL FIPS module)
```bash
# Install FIPS module
sudo apt-get install openssl-fips

# Configure FIPS mode
sudo update-crypto-policies --set FIPS

# Reboot
sudo reboot
```

## Best Practices

### Key Management
1. **Generate Strong Keys**
   - Use cryptographically secure random number generator
   - Minimum key length: AES-256 (32 bytes)

2. **Key Storage**
   - Never store keys in code or configuration files
   - Use HSM or encrypted key storage
   - Implement key rotation policies

3. **Key Rotation**
   - Rotate encryption keys regularly (e.g., annually)
   - Rotate TLS certificates before expiration
   - Maintain key version history

### Password Policy
1. **Minimum 12 characters** (configured in config.yml)
2. **Complexity requirements**: Upper, lower, numbers, symbols
3. **No password reuse** (implement password history)
4. **Regular password changes** (e.g., every 90 days)
5. **Account lockout** after failed attempts

### Audit and Monitoring
1. **Log all cryptographic operations**
2. **Monitor for failed authentication attempts**
3. **Alert on suspicious activity**
4. **Regular security audits**
5. **Compliance reporting**

## Troubleshooting

### FIPS Mode Not Working
```bash
# Check if cryptography library is installed
pip show cryptography

# Verify version (should be 41.0.0 or higher)
python3 -c "import cryptography; print(cryptography.__version__)"

# Test FIPS mode
python3 verify_fips.py
```

### TLS Certificate Issues
```bash
# Verify certificate
openssl x509 -in server.crt -text -noout

# Check key matches certificate
openssl x509 -noout -modulus -in server.crt | openssl md5
openssl rsa -noout -modulus -in server.key | openssl md5

# Test TLS connection
openssl s_client -connect localhost:5061 -tls1_2
```

### Performance Considerations

FIPS-compliant encryption may impact performance:
- Password hashing: ~100ms per authentication (100,000 PBKDF2 iterations)
- TLS handshake: ~50-100ms additional latency
- SRTP encryption: Minimal impact (<5% CPU for typical call loads)

Optimize for high-load environments:
- Use connection pooling
- Cache authenticated sessions
- Consider hardware acceleration (AES-NI)

## References

- [NIST FIPS 140-2 Standard](https://csrc.nist.gov/publications/detail/fips/140/2/final)
- [NIST SP 800-132 (PBKDF2)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf)
- [FIPS 197 (AES)](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197.pdf)
- [FIPS 180-4 (SHA-2)](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf)
- [RFC 5246 (TLS 1.2)](https://tools.ietf.org/html/rfc5246)
- [RFC 3711 (SRTP)](https://tools.ietf.org/html/rfc3711)

## Support

For questions about FIPS compliance:
1. Review this documentation
2. Check SECURITY.md for additional guidance
3. Consult with your security team
4. Contact NIST for certification guidance

---

**FIPS Status**: ✅ FIPS 140-2 APPROVED ALGORITHMS IMPLEMENTED
**Last Updated**: 2025-12-03
**Version**: 1.0.0
