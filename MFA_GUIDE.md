# Multi-Factor Authentication (MFA) Guide

> **⚠️ DEPRECATED**: This guide has been consolidated into [SECURITY_GUIDE.md](SECURITY_GUIDE.md#multi-factor-authentication-mfa). Please refer to the "Multi-Factor Authentication" section in the consolidated guide.

## Overview

The PBX system supports comprehensive Multi-Factor Authentication (MFA) to enhance security for user accounts. Multiple authentication methods are supported to accommodate different security requirements and user preferences.

## Supported MFA Methods

### 1. TOTP (Time-based One-Time Password)
**Compatible with:**
- Google Authenticator
- Microsoft Authenticator
- Authy
- FreeOTP
- Any TOTP-compliant authenticator app

**How it works:**
- User scans a QR code during enrollment
- Authenticator app generates 6-digit codes that change every 30 seconds
- User enters the current code to authenticate

### 2. YubiKey OTP
**Compatible with:**
- YubiKey hardware tokens (all models with OTP support)
- YubiKey 4, 5 series recommended

**How it works:**
- User enrolls their YubiKey by generating an OTP
- When authenticating, user touches YubiKey to generate a 44-character OTP
- System validates OTP via YubiCloud (or local validation server)

### 3. FIDO2/WebAuthn
**Compatible with:**
- YubiKey 5 series
- Other FIDO2-compliant security keys
- Platform authenticators (Windows Hello, Touch ID, etc.)

**How it works:**
- User registers security key via WebAuthn protocol
- When authenticating, user is prompted to touch their security key
- Cryptographic challenge-response validates the key

### 4. Backup Codes
**Always included:**
- 10 single-use backup codes generated during enrollment
- Can be used if primary MFA method is unavailable
- Should be stored securely (printed, password manager, etc.)

## Configuration

### Enable MFA in config.yml

```yaml
security:
  # Enable FIPS 140-2 compliant encryption
  fips_mode: true
  enforce_fips: true
  
  # MFA configuration
  mfa:
    enabled: true              # Enable MFA system
    required: false            # Require MFA for all users (optional)
    backup_codes: 10           # Number of backup codes to generate
    
    # YubiKey OTP configuration (optional)
    yubikey:
      enabled: true
      client_id: "YOUR_YUBICO_CLIENT_ID"     # Get from yubico.com
      api_key: "YOUR_YUBICO_API_KEY"         # Get from yubico.com
    
    # FIDO2/WebAuthn configuration (optional)
    fido2:
      enabled: true
```

### YubiCloud API Credentials

To use YubiKey OTP validation:
1. Get API credentials from https://upgrade.yubico.com/getapikey/
2. Add `client_id` and `api_key` to your config.yml
3. For production, consider setting up a local YubiKey validation server

## API Endpoints

### TOTP Enrollment

**POST /api/mfa/enroll**
```json
{
  "extension": "1001"
}
```

Response:
```json
{
  "success": true,
  "provisioning_uri": "otpauth://totp/PBX%20System:1001?secret=...",
  "backup_codes": [
    "ABCD-EFGH",
    "IJKL-MNOP",
    ...
  ],
  "message": "MFA enrollment initiated. Scan QR code and verify with first code."
}
```

**Generate QR Code:**
The `provisioning_uri` can be converted to a QR code for easy scanning:
- Use a QR code library (qrcode, pyqrcode, etc.)
- Display QR code to user during enrollment
- User scans with authenticator app

### Verify Enrollment

**POST /api/mfa/verify-enrollment**
```json
{
  "extension": "1001",
  "code": "123456"
}
```

Response:
```json
{
  "success": true,
  "message": "MFA successfully activated"
}
```

### Verify MFA Code

**POST /api/mfa/verify**
```json
{
  "extension": "1001",
  "code": "123456"  // TOTP code, YubiKey OTP, or backup code
}
```

Response:
```json
{
  "success": true,
  "message": "MFA verification successful"
}
```

### YubiKey Enrollment

**POST /api/mfa/enroll-yubikey**
```json
{
  "extension": "1001",
  "otp": "ccccccbcgujhingjrdejhgfnuetrgigvejhhgbkugded",  // Touch YubiKey
  "device_name": "My YubiKey 5"  // Optional friendly name
}
```

Response:
```json
{
  "success": true,
  "message": "YubiKey enrolled successfully"
}
```

### FIDO2 Enrollment

**POST /api/mfa/enroll-fido2**
```json
{
  "extension": "1001",
  "credential_data": {
    "credential_id": "base64_encoded_credential_id",
    "public_key": "base64_encoded_public_key",
    "attestation": "optional_attestation_object"
  },
  "device_name": "Security Key"  // Optional friendly name
}
```

Response:
```json
{
  "success": true,
  "message": "FIDO2 credential enrolled successfully"
}
```

### Get MFA Status

**GET /api/mfa/status/{extension}**

Response:
```json
{
  "extension": "1001",
  "mfa_enabled": true,
  "mfa_required": false
}
```

### Get Enrolled Methods

**GET /api/mfa/methods/{extension}**

Response:
```json
{
  "extension": "1001",
  "methods": {
    "totp": true,
    "yubikeys": [
      {
        "public_id": "ccccccbcgujh",
        "device_name": "My YubiKey 5",
        "enrolled_at": "2025-12-07T14:00:00"
      }
    ],
    "fido2": [
      {
        "credential_id": "base64_encoded_id",
        "device_name": "Security Key",
        "enrolled_at": "2025-12-07T14:00:00"
      }
    ],
    "backup_codes": 8
  }
}
```

### Disable MFA

**POST /api/mfa/disable**
```json
{
  "extension": "1001"
}
```

Response:
```json
{
  "success": true,
  "message": "MFA disabled successfully"
}
```

## User Enrollment Flow

### TOTP (Google Authenticator, etc.)

1. **Initiate Enrollment**
   - User requests MFA enrollment via admin portal or API
   - System generates TOTP secret and backup codes

2. **Display QR Code**
   - Convert provisioning URI to QR code
   - Display QR code and backup codes to user
   - User saves backup codes securely

3. **Scan QR Code**
   - User opens authenticator app (Google Authenticator, etc.)
   - User scans QR code with app
   - App begins generating 6-digit codes

4. **Verify Enrollment**
   - User enters current 6-digit code from app
   - System verifies code and activates MFA

5. **Complete**
   - MFA is now active for the user
   - User will need code for all future logins

### YubiKey Enrollment

1. **Initiate Enrollment**
   - User requests YubiKey enrollment
   - System is ready to accept YubiKey OTP

2. **Insert YubiKey**
   - User inserts YubiKey into USB port
   - Or taps YubiKey on NFC reader (mobile)

3. **Generate OTP**
   - User clicks in OTP field
   - User touches YubiKey button
   - YubiKey generates 44-character OTP

4. **Verify and Enroll**
   - System extracts public ID from OTP
   - System validates OTP with YubiCloud
   - YubiKey is enrolled for user

5. **Complete**
   - User can now authenticate with YubiKey
   - Multiple YubiKeys can be enrolled

### FIDO2 Enrollment (Advanced)

1. **Browser Support**
   - Requires modern browser with WebAuthn support
   - Chrome, Firefox, Safari, Edge (latest versions)

2. **Initiate Registration**
   - System creates WebAuthn challenge
   - Browser prompts user to use security key

3. **Touch Security Key**
   - User touches FIDO2 security key
   - Key generates cryptographic credential

4. **Complete Registration**
   - System stores credential public key
   - Private key remains on security key (never leaves device)

5. **Future Authentication**
   - User touches key to prove possession
   - Cryptographic challenge-response validates key

## Authentication Flow

When MFA is enabled for a user:

1. **Primary Authentication**
   - User provides username/password (or extension/password)
   - System validates credentials

2. **MFA Challenge**
   - System prompts for MFA code
   - User can provide:
     - TOTP code (6 digits from authenticator app)
     - YubiKey OTP (44 characters, touch YubiKey)
     - FIDO2 assertion (touch security key)
     - Backup code (8 characters, one-time use)

3. **Verification**
   - System validates provided MFA credential
   - Access granted if valid

4. **Failed Attempts**
   - Invalid codes are logged
   - Rate limiting prevents brute force
   - Account may be locked after repeated failures

## Security Features

### FIPS 140-2 Compliance
- All secrets encrypted with AES-256-GCM
- Key derivation using PBKDF2-HMAC-SHA256
- 600,000 iterations (OWASP 2024 recommendation)

### Secret Storage
- TOTP secrets encrypted at rest in database
- Encryption key derived from extension number
- Each user's secret has unique salt

### Backup Code Security
- Backup codes hashed before storage (like passwords)
- Each code has unique salt
- Codes are single-use only
- Marked as used after successful authentication

### Rate Limiting
- Failed MFA attempts tracked
- Automatic lockout after threshold
- Prevents brute force attacks

### Audit Logging
- All MFA events logged
- Enrollment, verification, failures tracked
- Integrated with security audit system

## Database Schema

### mfa_secrets
Stores TOTP secrets for users:
```sql
CREATE TABLE mfa_secrets (
    id SERIAL PRIMARY KEY,
    extension_number VARCHAR(20) UNIQUE NOT NULL,
    secret_encrypted TEXT NOT NULL,
    secret_salt VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    enrolled_at TIMESTAMP,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### mfa_backup_codes
Stores backup codes for users:
```sql
CREATE TABLE mfa_backup_codes (
    id SERIAL PRIMARY KEY,
    extension_number VARCHAR(20) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    code_salt VARCHAR(255) NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### mfa_yubikey_devices
Stores enrolled YubiKeys:
```sql
CREATE TABLE mfa_yubikey_devices (
    id SERIAL PRIMARY KEY,
    extension_number VARCHAR(20) NOT NULL,
    public_id VARCHAR(20) UNIQUE NOT NULL,
    device_name VARCHAR(100),
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### mfa_fido2_credentials
Stores FIDO2 credentials:
```sql
CREATE TABLE mfa_fido2_credentials (
    id SERIAL PRIMARY KEY,
    extension_number VARCHAR(20) NOT NULL,
    credential_id VARCHAR(255) UNIQUE NOT NULL,
    public_key TEXT NOT NULL,
    device_name VARCHAR(100),
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Testing

Run MFA tests:
```bash
python3 tests/test_mfa.py
```

Test coverage includes:
- TOTP code generation and verification
- Time window handling (clock skew tolerance)
- Provisioning URI format
- MFA manager initialization
- Database persistence
- Enrollment and verification flow
- Backup code generation and usage
- One-time use enforcement

## Troubleshooting

### QR Code Not Scanning
- Ensure QR code is large enough
- Try different authenticator app
- Manually enter secret key as alternative
- Secret is displayed in provisioning URI

### TOTP Codes Not Working
- Check device time synchronization
- Most TOTP issues are clock skew
- System allows ±30 second window
- Ensure correct secret was scanned

### YubiKey OTP Not Working
- Verify YubiCloud credentials in config
- Check YubiKey is generating OTPs (44 characters)
- Ensure YubiKey is enrolled for user
- Check network connectivity to YubiCloud

### Backup Codes Not Working
- Each code is single-use only
- Codes are case-insensitive
- Format is XXXX-XXXX (dash required)
- Check if code was already used

### Lost MFA Device
- Use backup codes to regain access
- Admin can disable MFA for user account
- User can re-enroll with new device
- Keep backup codes in secure location

## Best Practices

### For Users
1. **Save Backup Codes**
   - Print and store securely
   - Keep separate from device
   - Use password manager

2. **Multiple Methods**
   - Enroll multiple devices if possible
   - Have backup authenticator app
   - Consider YubiKey as backup

3. **Keep Device Secure**
   - Lock phone/computer
   - Use device PIN/biometrics
   - Don't share authenticator

### For Administrators
1. **Require MFA for Privileged Accounts**
   - Admin accounts should have MFA
   - Consider making MFA mandatory

2. **User Education**
   - Provide clear enrollment instructions
   - Explain backup codes importance
   - Document recovery procedures

3. **Monitor MFA Events**
   - Review audit logs regularly
   - Watch for failed attempts
   - Investigate suspicious patterns

4. **Test Recovery Procedures**
   - Ensure backup codes work
   - Test admin override process
   - Document support procedures

## Integration Examples

### Python Client Example
```python
import requests
import qrcode

# Enroll user in MFA
response = requests.post('http://pbx-server:8080/api/mfa/enroll', json={
    'extension': '1001'
})

data = response.json()

if data['success']:
    # Generate QR code
    qr = qrcode.QRCode()
    qr.add_data(data['provisioning_uri'])
    qr.make()
    img = qr.make_image()
    img.save('mfa_qr_code.png')
    
    # Display backup codes
    print("Backup Codes (save these!):")
    for code in data['backup_codes']:
        print(f"  {code}")
    
    # Wait for user to scan and verify
    code = input("Enter code from authenticator app: ")
    
    # Verify enrollment
    verify_response = requests.post('http://pbx-server:8080/api/mfa/verify-enrollment', json={
        'extension': '1001',
        'code': code
    })
    
    if verify_response.json()['success']:
        print("MFA successfully activated!")
```

### JavaScript/Web Example
```javascript
// Enroll in MFA
async function enrollMFA(extension) {
    const response = await fetch('/api/mfa/enroll', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({extension})
    });
    
    const data = await response.json();
    
    if (data.success) {
        // Display QR code
        const qr = new QRCode(document.getElementById('qrcode'), {
            text: data.provisioning_uri,
            width: 256,
            height: 256
        });
        
        // Display backup codes
        displayBackupCodes(data.backup_codes);
        
        // Show verification form
        showVerificationForm(extension);
    }
}

// Verify enrollment
async function verifyEnrollment(extension, code) {
    const response = await fetch('/api/mfa/verify-enrollment', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({extension, code})
    });
    
    const data = await response.json();
    
    if (data.success) {
        alert('MFA successfully activated!');
    } else {
        alert('Invalid code. Please try again.');
    }
}

// Authenticate with MFA
async function authenticateWithMFA(extension, code) {
    const response = await fetch('/api/mfa/verify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({extension, code})
    });
    
    return await response.json();
}
```

## Related Documentation

- [SECURITY.md](SECURITY.md) - General security features
- [SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md) - Security architecture
- [FIPS_COMPLIANCE.md](FIPS_COMPLIANCE.md) - FIPS 140-2 compliance details
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Complete API reference

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review audit logs for error details
3. Ensure configuration is correct
4. Test with backup codes to isolate issue
5. Contact system administrator

## Future Enhancements

Planned improvements:
- SMS/Email OTP as fallback method
- Push notifications (mobile app)
- Biometric authentication
- Risk-based authentication (adaptive MFA)
- Remember device/trusted device management
- Self-service MFA recovery options
