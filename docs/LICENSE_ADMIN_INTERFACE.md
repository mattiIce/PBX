# License Management Admin Interface

**Last Updated**: December 29, 2025  
**Purpose**: Complete guide for license management including quick reference and detailed procedures

## Table of Contents
- [Quick Reference](#quick-reference)
- [Admin Interface Access](#admin-interface-access)
- [Command-Line Tool](#command-line-tool)
- [License Types](#license-types)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)

---

## Quick Reference

### Admin Credentials (Encrypted)
```
Extension: 9322
Username:  ICE
PIN:       26697647
```
⚠️ This account has exclusive access to license management and uses triple-layer encryption.

### Quick Start Commands

**Generate a License**:
```bash
python scripts/license_manager.py generate \
  --type professional \
  --org "Customer Name" \
  --days 365 \
  --output license.json
```

**Batch Generate**:
```bash
python scripts/license_manager.py batch-generate examples/batch_licenses.json
```

**Install License**:
```bash
python scripts/license_manager.py install license.json
```

**Check Status**:
```bash
python scripts/license_manager.py status
```

### Common Tasks

**Enable Licensing:**
```bash
python scripts/license_manager.py enable
```

**Disable Licensing (Open-Source Mode):**
```bash
python scripts/license_manager.py disable
```

**Install with Enforcement (Commercial):**
```bash
python scripts/license_manager.py install license.json --enforce
```

**Remove License Lock:**
```bash
python scripts/license_manager.py remove-lock
```

### API Endpoints

**Public (All Users):**
- `GET /api/license/status` - View license status
- `GET /api/license/features` - List available features

**Admin Only (Extension 9322):**
- `POST /api/license/admin_login` - Authenticate
- `POST /api/license/generate` - Create new license
- `POST /api/license/install` - Install license
- `POST /api/license/revoke` - Remove license
- `POST /api/license/toggle` - Enable/disable licensing

### Batch Config Example

**JSON** (`config.json`):
```json
{
  "licenses": [
    {
      "type": "professional",
      "issued_to": "Customer Name",
      "expiration_days": 365,
      "max_extensions": 100,
      "max_concurrent_calls": 50
    }
  ]
}
```

**Generate**:
```bash
python scripts/license_manager.py batch-generate config.json --output-dir ./licenses
```

---

## Overview

The PBX system includes a comprehensive license management system with both a web-based admin interface and a command-line tool. License management functionality is **restricted to a special administrator account** for security purposes.

---

## Admin Interface Access

### Authentication

License management is **only accessible** by the special license administrator account:

- **Extension**: 9322
- **Username**: ICE  
- **PIN**: 26697647 (heavily encrypted with multi-layer verification)

This account:
- Cannot be edited or deleted
- Uses triple-layer encryption (SHA256, PBKDF2 with 100,000 iterations, and HMAC)
- Is automatically hidden from non-admin users
- Has exclusive access to license management features

### Accessing the Admin Interface

1. Log in to the PBX admin panel at `https://your-pbx-domain/admin/`
2. Use the license admin credentials (Extension 9322, Username ICE, PIN 26697647)
3. Navigate to **System** → **License Management** in the sidebar

The License Management tab will only be visible if you're logged in as the license administrator (Extension 9322).

### Features

The admin interface provides:

1. **License Status Dashboard**
   - View current license status
   - See license type, expiration, and limits
   - Check licensing enabled/disabled state

2. **Feature Management**
   - View all available features for current license
   - Check usage limits (extensions, concurrent calls)

3. **License Generation**
   - Generate new licenses for customers
   - Support for all license types (trial, basic, professional, enterprise, perpetual, custom)
   - Configure expiration dates and limits
   - Download generated licenses as JSON

4. **License Installation**
   - Upload and install license files
   - Optional enforcement mode (prevents disabling)
   - Instant activation

5. **System Controls**
   - Enable/disable licensing enforcement
   - Revoke current license
   - Remove license lock file (admin only)

## Command-Line Tool

For automation and scripting, use the `license_manager.py` CLI tool.

### Basic Commands

```bash
# Generate a single license
python scripts/license_manager.py generate \
  --type professional \
  --org "Acme Corp" \
  --days 365 \
  --max-extensions 100 \
  --max-calls 50

# Install a license
python scripts/license_manager.py install license_acme_corp_20251222.json

# Install with enforcement (commercial deployment)
python scripts/license_manager.py install license_acme_corp_20251222.json --enforce

# Check license status
python scripts/license_manager.py status

# List available features
python scripts/license_manager.py features

# Enable licensing
python scripts/license_manager.py enable

# Disable licensing (open-source mode)
python scripts/license_manager.py disable
```

### Batch License Generation

Generate multiple licenses automatically from a configuration file:

```bash
# Using JSON config
python scripts/license_manager.py batch-generate examples/batch_licenses.json

# Using YAML config
python scripts/license_manager.py batch-generate examples/batch_licenses.yml

# Specify custom output directory
python scripts/license_manager.py batch-generate batch_config.json --output-dir /path/to/output
```

### Batch Configuration Format

**JSON Example** (`examples/batch_licenses.json`):

```json
{
  "licenses": [
    {
      "type": "professional",
      "issued_to": "Customer Name",
      "expiration_days": 365,
      "max_extensions": 100,
      "max_concurrent_calls": 50
    },
    {
      "type": "enterprise",
      "issued_to": "Big Customer Inc",
      "expiration_days": 730
    }
  ]
}
```

**YAML Example** (`examples/batch_licenses.yml`):

```yaml
licenses:
  - type: professional
    issued_to: "Customer Name"
    expiration_days: 365
    max_extensions: 100
    max_concurrent_calls: 50
    
  - type: enterprise
    issued_to: "Big Customer Inc"
    expiration_days: 730
```

## API Endpoints

### Public Endpoints

These endpoints are available to all authenticated users:

- `GET /api/license/status` - Get current license status
- `GET /api/license/features` - List available features
- `POST /api/license/check` - Check if a specific feature is available

### Admin-Only Endpoints

These endpoints require license administrator authentication (Extension 9322):

- `POST /api/license/generate` - Generate a new license
- `POST /api/license/install` - Install a license
- `POST /api/license/revoke` - Revoke current license
- `POST /api/license/toggle` - Enable/disable licensing
- `POST /api/license/remove_lock` - Remove license lock file

### Authentication Endpoint

- `POST /api/license/admin_login` - Authenticate as license administrator

## Security Features

### Multi-Layer Encryption

The license admin PIN (26697647) is protected using three independent cryptographic methods:

1. **SHA256 Hash**: First layer of hashing
2. **PBKDF2 Key Derivation**: 100,000 iterations with salt
3. **HMAC Signature**: Message authentication code

All three methods must pass for authentication to succeed, providing defense-in-depth against:
- Brute force attacks
- Timing attacks (constant-time comparison)
- Rainbow table attacks
- Hash collision attacks

### Protected Account

The license administrator account (Extension 9322):
- Cannot be edited through normal admin interfaces
- Cannot be deleted
- Is automatically created by the system
- Uses heavily encrypted credential verification
- All login attempts are logged

### Session Security

- License admin sessions are verified on every protected API call
- Failed authentication attempts are logged with IP addresses
- Session tokens expire after inactivity

## Deployment Scenarios

### Open-Source / Internal Use

```bash
# Disable licensing (all features free)
python scripts/license_manager.py disable
```

In this mode:
- All features are available
- No license required
- No restrictions on extensions or calls
- Perfect for self-hosted deployments

### Commercial SaaS Deployment

```bash
# Generate and install license with enforcement
python scripts/license_manager.py generate \
  --type enterprise \
  --org "Customer Inc" \
  --days 365

python scripts/license_manager.py install license_customer_inc_20251222.json --enforce
```

In enforcement mode:
- Creates `.license_lock` file
- Licensing cannot be disabled via config or environment
- Requires license administrator intervention to remove lock
- Ideal for hosted/SaaS offerings

## Automation Examples

### Automated Trial License Generation

```python
#!/usr/bin/env python3
import subprocess
import json

def create_trial_license(customer_email, customer_name):
    """Create a 30-day trial license for a new customer."""
    result = subprocess.run([
        'python', 'scripts/license_manager.py', 'generate',
        '--type', 'trial',
        '--org', customer_name,
        '--days', '30',
        '--output', f'/tmp/trial_{customer_email}.json'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        with open(f'/tmp/trial_{customer_email}.json', 'r') as f:
            license_data = json.load(f)
        
        # Email license to customer
        send_license_email(customer_email, license_data)
        
        return license_data
    else:
        print(f"Error: {result.stderr}")
        return None
```

### Bulk Customer License Generation

```bash
#!/bin/bash
# Generate licenses for 100 customers

for i in {1..100}; do
    python scripts/license_manager.py generate \
        --type professional \
        --org "Customer $i" \
        --days 365 \
        --max-extensions 50 \
        --max-calls 25 \
        --output "licenses/customer_${i}.json"
done
```

Or use the batch generation feature with a dynamically generated config file.

## Troubleshooting

### Cannot Access License Management Tab

**Problem**: The License Management tab is not visible in the admin panel.

**Solution**: 
- Verify you are logged in as Extension 9322
- Check that the username is "ICE"
- Ensure you're using the correct PIN (26697647)
- Clear browser cache and reload

### License Admin Login Fails

**Problem**: Cannot authenticate with the license admin credentials.

**Solution**:
- Verify Extension: 9322
- Verify Username: ICE (case insensitive)
- Verify PIN: 26697647
- Check logs for authentication errors
- Ensure `license_admin.py` module is present

### API Returns 401 Unauthorized

**Problem**: License management API calls return 401 error.

**Solution**:
- Authenticate first using `/api/license/admin_login` endpoint
- Ensure session cookie is being sent with requests
- Check session hasn't expired
- Verify you're using the license admin credentials

## Migration Guide

### Upgrading Existing Installation

If you have an existing PBX installation:

1. Pull the latest code with license management features
2. The license admin account (Extension 9322) is automatically available
3. Access the admin panel and navigate to License Management
4. Generate or install your license

### Adding to CI/CD Pipeline

```yaml
# Example GitLab CI/CD
deploy:
  script:
    - python scripts/license_manager.py generate --type enterprise --org "$CUSTOMER_NAME" --days 365 --output license.json
    - python scripts/license_manager.py install license.json --enforce
    - systemctl restart pbx
```

## License Types

Quick comparison:

| Type | Duration | Extensions | Calls | Key Features |
|------|----------|-----------|-------|--------------|
| Trial | 30 days | 10 | 5 | Basic features |
| Basic | Variable | 50 | 25 | Small business |
| Professional | Variable | 200 | 100 | WebRTC, CRM |
| Enterprise | Variable | ∞ | ∞ | AI, HA, Multi-site |
| Perpetual | Forever | ∞ | ∞ | One-time purchase |
| Custom | Variable | Custom | Custom | Tailored features |

**Detailed Descriptions:**

- **Trial**: 30 days, 10 extensions, 5 concurrent calls
- **Basic**: Suitable for small businesses, 50 extensions, 25 concurrent calls
- **Professional**: Medium businesses, 200 extensions, 100 concurrent calls, WebRTC, CRM integration
- **Enterprise**: Unlimited extensions/calls, AI features, HA, multi-site
- **Perpetual**: One-time purchase, never expires
- **Custom**: Tailored feature sets for special requirements

See [COMPLETE_GUIDE.md](../COMPLETE_GUIDE.md) for complete feature documentation.

---

## Troubleshooting

**Can't see License Management tab?**
- Verify you're logged in as Extension 9322
- Clear browser cache (Ctrl+Shift+R)

**CLI command not found?**
```bash
cd /path/to/PBX
python scripts/license_manager.py --help
```

**Authentication fails?**
- Check Extension: 9322
- Check Username: ICE (case insensitive)
- Check PIN: 26697647
- Review logs: `tail -f logs/pbx.log`

**License generation fails?**
- Ensure all required parameters are provided
- Check file permissions in output directory
- Verify license secret key is configured in config.yml

**License installation fails?**
- Verify JSON file format is valid
- Check license has not expired
- Ensure licensing is enabled in config.yml
- Review logs for specific error messages

---

## Security Notes

**Triple-Layer Encryption:**
✅ SHA256 hashing  
✅ PBKDF2 with 100,000 iterations  
✅ HMAC verification  
✅ Constant-time comparison (timing attack prevention)  
✅ Protected system account (cannot be edited/deleted)  
✅ All authentication attempts logged  
✅ Session-based API protection  

**IMPORTANT**: 
- The license admin credentials (Extension 9322, PIN 26697647) should be kept confidential
- Change the `license_secret_key` in `config.yml` for production deployments
- The PIN is heavily encrypted, but the account cannot be locked out
- All authentication attempts are logged - monitor for suspicious activity
- In production, consider adding rate limiting to login endpoints

---

## Migration Guide

### Upgrading Existing Installation

If you have an existing PBX installation:

1. Pull the latest code with license management features
2. The license admin account (Extension 9322) is automatically available
3. Access the admin panel and navigate to License Management
4. Generate or install your license

### Adding to CI/CD Pipeline

```yaml
# Example GitLab CI/CD
deploy:
  script:
    - python scripts/license_manager.py generate --type enterprise --org "$CUSTOMER_NAME" --days 365 --output license.json
    - python scripts/license_manager.py install license.json --enforce
    - systemctl restart pbx
```

---

## Support and Documentation

For issues or questions:
- See **[COMPLETE_GUIDE.md](../COMPLETE_GUIDE.md)** for comprehensive documentation
- Check logs in `logs/pbx.log` for authentication errors
- Ensure all dependencies are installed: `make install-prod`

---

**Last Updated**: December 29, 2025  
**Status**: Production Ready
