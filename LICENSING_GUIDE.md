# Licensing and Subscription System Guide

**Version**: 1.0  
**Date**: December 22, 2025  
**Status**: Production-Ready

---

## Overview

The PBX system includes a flexible licensing and subscription system that can be **enabled or disabled** by the administrator. This system supports multiple license tiers, feature gating, and trial modes.

**Key Features**:
- ✅ **Admin Toggle**: Turn licensing on/off via environment variable or API
- ✅ **Multiple License Tiers**: Trial, Basic, Professional, Enterprise, Perpetual, Custom
- ✅ **Feature Gating**: Control access to features based on license
- ✅ **Usage Limits**: Enforce limits on extensions and concurrent calls
- ✅ **Trial Mode**: Automatic 30-day trial for new installations
- ✅ **Grace Periods**: 7-day grace period after license expiration
- ✅ **Offline Validation**: Works without internet connection
- ✅ **REST API**: Full API for license management

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Enabling/Disabling Licensing](#enablingdisabling-licensing)
3. [License Tiers](#license-tiers)
4. [Generating Licenses](#generating-licenses)
5. [Installing Licenses](#installing-licenses)
6. [Feature Gating](#feature-gating)
7. [API Reference](#api-reference)
8. [Usage Examples](#usage-examples)
9. [Trial Mode](#trial-mode)
10. [Grace Periods](#grace-periods)
11. [Troubleshooting](#troubleshooting)

---

## Quick Start

### For Programmers (Controlling Licensing)

**Enable licensing**:
```bash
export PBX_LICENSING_ENABLED=true
python main.py
```

**Disable licensing** (all features unlocked):
```bash
export PBX_LICENSING_ENABLED=false
python main.py
```

**Toggle via API**:
```bash
# Disable licensing
curl -X POST http://localhost:8080/api/license/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Enable licensing
curl -X POST http://localhost:8080/api/license/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### For End Users

**Check license status**:
```bash
curl http://localhost:8080/api/license/status
```

**List available features**:
```bash
curl http://localhost:8080/api/license/features
```

---

## Enabling/Disabling Licensing

The licensing system can be controlled in **four ways** (in order of priority):

### 1. License Lock File (Highest Priority - Enforcement Mode)

**For Commercial Deployments**: When a license is installed with the `--enforce` flag, a `.license_lock` file is created. This **prevents licensing from being disabled** via config or environment variables.

```bash
# Install license with enforcement (commercial deployment)
python scripts/license_manager.py install license.json --enforce
```

**Effect**: 
- Licensing is **mandatory** and cannot be disabled
- Config and environment variable settings are ignored
- Ideal for SaaS deployments where you control the server

**To disable licensing again** (transition back to open-source):
```bash
# Remove the lock file (admin only)
python scripts/license_manager.py remove-lock

# Then disable licensing
python scripts/license_manager.py disable
```

### 2. Environment Variable (Second Priority)

```bash
# Enable licensing
export PBX_LICENSING_ENABLED=true

# Disable licensing (all features available)
export PBX_LICENSING_ENABLED=false
```

Add to `.env` file for persistence:
```bash
PBX_LICENSING_ENABLED=false
```

**Note**: If `.license_lock` exists, this setting is ignored.

### 3. Configuration File (Third Priority)

Add to `config.yml`:
```yaml
licensing:
  enabled: false  # Set to true to enable licensing
  grace_period_days: 7
  trial_period_days: 30
  license_secret_key: "your-secret-key-here"  # Change in production!
```

**Note**: If `.license_lock` exists or environment variable is set, this setting is ignored.

### 4. REST API (Runtime Toggle)

```bash
POST /api/license/toggle
{
  "enabled": true  # or false
}
```

**Note**: Environment variable takes precedence over config file.

### Default Behavior

If not specified, licensing is **DISABLED** by default. This makes the system fully open-source and free to use.

---

## License Tiers

### Trial (30 Days)

**Features**:
- Basic calling
- Voicemail
- Call recording
- Basic IVR

**Limits**:
- Max extensions: 10
- Max concurrent calls: 5

**Use Case**: Evaluation and testing

---

### Basic

**Features**:
- All Trial features
- Advanced IVR
- Call queues
- Conference calling

**Limits**:
- Max extensions: 50
- Max concurrent calls: 25

**Price**: $29/month or $290/year (example pricing)

---

### Professional

**Features**:
- All Basic features
- Call parking
- Hot-desking
- WebRTC browser calling
- CRM integration
- Active Directory integration
- Multi-factor authentication

**Limits**:
- Max extensions: 200
- Max concurrent calls: 100

**Price**: $79/month or $790/year (example pricing)

---

### Enterprise

**Features**:
- All Professional features
- AI features (speech analytics, voice biometrics)
- Advanced analytics
- High availability
- Multi-site support
- Session Border Controller

**Limits**:
- Unlimited extensions
- Unlimited concurrent calls

**Price**: Custom pricing (contact sales)

---

### Perpetual

**Features**:
- All Professional features (no AI, HA, or advanced features)
- Lifetime license (no expiration)

**Limits**:
- Unlimited extensions
- Unlimited concurrent calls

**Price**: One-time $2,500 (example pricing)

---

### Custom

**Features**:
- Custom feature set defined per customer

**Limits**:
- Custom limits

**Price**: Custom pricing

---

## Generating Licenses

### Using Python Script

```python
#!/usr/bin/env python3
from pbx.utils.licensing import LicenseManager, LicenseType

# Initialize license manager
config = {
    'license_secret_key': 'your-secret-key-here'
}
lm = LicenseManager(config)

# Generate enterprise license
license_data = lm.generate_license_key(
    license_type=LicenseType.ENTERPRISE,
    issued_to="Acme Corporation",
    expiration_days=365  # 1 year
)

# Save to file
lm.save_license(license_data)

print(f"License Key: {license_data['key']}")
```

### Using REST API

```bash
POST /api/license/generate
{
  "type": "professional",
  "issued_to": "Example Company",
  "max_extensions": 100,
  "max_concurrent_calls": 50,
  "expiration_days": 365
}
```

**Response**:
```json
{
  "success": true,
  "license": {
    "key": "A3F2-8C1D-9E4B-7F05",
    "type": "professional",
    "issued_to": "Example Company",
    "issued_date": "2025-12-22T10:30:00",
    "expiration": "2026-12-22T10:30:00",
    "max_extensions": 100,
    "max_concurrent_calls": 50,
    "signature": "..."
  }
}
```

### Generating Custom Licenses

```bash
POST /api/license/generate
{
  "type": "custom",
  "issued_to": "Special Customer",
  "expiration_days": 730,
  "custom_features": [
    "basic_calling",
    "voicemail",
    "webrtc",
    "ai_features",
    "max_extensions:150",
    "max_concurrent_calls:75"
  ]
}
```

---

## Installing Licenses

### Method 1: REST API

**Standard Installation** (open-source/internal use):
```bash
POST /api/license/install
{
  "license_data": {
    "key": "A3F2-8C1D-9E4B-7F05",
    "type": "professional",
    "issued_to": "Example Company",
    ... (rest of license data)
  }
}
```

**Commercial Installation with Enforcement**:
```bash
POST /api/license/install
{
  "license_data": {
    "key": "A3F2-8C1D-9E4B-7F05",
    "type": "professional",
    "issued_to": "Example Company",
    ... (rest of license data)
  },
  "enforce_licensing": true
}
```

**Response**:
```json
{
  "success": true,
  "message": "License installed successfully (licensing enforcement enabled - cannot be disabled)",
  "license": { ... },
  "enforcement_locked": true
}
```

When `enforce_licensing: true` is set:
- Creates a `.license_lock` file
- Prevents licensing from being disabled
- Ideal for commercial SaaS deployments

### Method 2: CLI Tool

**Standard Installation**:
```bash
python scripts/license_manager.py install license.json
```

**Commercial Installation with Enforcement**:
```bash
python scripts/license_manager.py install license.json --enforce
```

Output:
```
Installing license from license.json...
⚠️  Enforcement mode: License lock file will be created
    Licensing cannot be disabled once lock file exists

✓ License installed successfully!
✓ License lock file created - licensing enforcement is mandatory
```

### Method 3: Manual File Installation

1. Save license data to `.license` file in PBX root directory:

```bash
cat > .license << 'EOF'
{
  "key": "A3F2-8C1D-9E4B-7F05",
  "type": "professional",
  "issued_to": "Example Company",
  "issued_date": "2025-12-22T10:30:00",
  "expiration": "2026-12-22T10:30:00",
  "max_extensions": 100,
  "max_concurrent_calls": 50,
  "signature": "..."
}
EOF
```

2. **(Optional)** For commercial enforcement, create lock file:

```bash
cat > .license_lock << 'EOF'
{
  "created": "2025-12-22T10:30:00",
  "license_key": "A3F2-8C1D-9E4B-7F05...",
  "issued_to": "Example Company",
  "type": "professional",
  "enforcement": "mandatory"
}
EOF
chmod 600 .license_lock
```

3. Restart PBX system:

```bash
sudo systemctl restart pbx
```

### Removing License Lock (Admin Operation)

To transition from commercial to open-source deployment:

**CLI**:
```bash
python scripts/license_manager.py remove-lock
```

**API**:
```bash
POST /api/license/remove_lock
```

**Warning**: Only use this when transitioning deployment modes. This allows licensing to be disabled again.

---

## Feature Gating

### In Python Code

```python
from pbx.utils.licensing import has_feature, check_limit

# Check if feature is available
if has_feature('webrtc'):
    # Enable WebRTC functionality
    enable_webrtc_calling()
else:
    # Show upgrade message
    show_feature_unavailable('WebRTC', 'Professional')

# Check limits
current_extensions = len(get_all_extensions())
if not check_limit('max_extensions', current_extensions):
    raise LimitExceeded('Maximum extensions reached. Upgrade license.')
```

### Via REST API

```bash
POST /api/license/check
{
  "feature": "ai_features"
}
```

**Response**:
```json
{
  "success": true,
  "feature": "ai_features",
  "available": true
}
```

### Example: Protecting Admin Panel Features

```python
from flask import abort, jsonify
from pbx.utils.licensing import has_feature

@app.route('/api/ai/speech-analytics', methods=['GET'])
def get_speech_analytics():
    # Check license
    if not has_feature('ai_features'):
        return jsonify({
            'success': False,
            'error': 'AI features require Enterprise license',
            'upgrade_url': '/pricing'
        }), 403
    
    # Feature is available, proceed
    return get_analytics_data()
```

---

## API Reference

### GET /api/license/status

Get current license status and information.

**Response**:
```json
{
  "success": true,
  "license": {
    "enabled": true,
    "status": "active",
    "message": "License active. Expires in 180 days",
    "type": "professional",
    "issued_to": "Example Company",
    "issued_date": "2025-12-22T10:30:00",
    "expiration": "2026-12-22T10:30:00",
    "key": "A3F2-8C1D-9E4B-7F05...",
    "limits": {
      "max_extensions": 100,
      "max_concurrent_calls": 50
    }
  }
}
```

### GET /api/license/features

List all available features for current license.

**Response**:
```json
{
  "success": true,
  "license_type": "professional",
  "features": [
    "basic_calling",
    "voicemail",
    "call_recording",
    "ivr",
    "call_queues",
    "conference",
    "call_parking",
    "hot_desking",
    "webrtc",
    "crm_integration",
    "ad_integration",
    "mfa"
  ],
  "limits": {
    "max_extensions": 100,
    "max_concurrent_calls": 50
  },
  "licensing_enabled": true
}
```

### POST /api/license/check

Check if specific feature is available.

**Request**:
```json
{
  "feature": "ai_features"
}
```

**Response**:
```json
{
  "success": true,
  "feature": "ai_features",
  "available": false
}
```

### POST /api/license/generate

Generate a new license (admin only).

**Request**:
```json
{
  "type": "professional",
  "issued_to": "Example Company",
  "max_extensions": 100,
  "max_concurrent_calls": 50,
  "expiration_days": 365
}
```

**Response**: Full license data object

### POST /api/license/install

Install a license (admin only).

**Request**:
```json
{
  "license_data": { ... }
}
```

**Response**:
```json
{
  "success": true,
  "message": "License installed successfully",
  "license": { ... }
}
```

### POST /api/license/revoke

Revoke current license (admin only).

**Response**:
```json
{
  "success": true,
  "message": "License revoked successfully"
}
```

### POST /api/license/toggle

Enable or disable licensing (admin only).

**Request**:
```json
{
  "enabled": false
}
```

**Response**:
```json
{
  "success": true,
  "licensing_enabled": false,
  "message": "Licensing disabled successfully"
}
```

---

## Usage Examples

### Example 1: Check License Before Adding Extension

```python
from pbx.utils.licensing import check_limit, has_feature

def add_extension(extension_number, user_data):
    # Count current extensions
    current_count = len(extensions_db.get_all())
    
    # Check limit
    if not check_limit('max_extensions', current_count + 1):
        raise Exception(
            f"License limit reached. Maximum {get_limit('max_extensions')} extensions allowed. "
            f"Upgrade to add more."
        )
    
    # Add extension
    extensions_db.add(extension_number, user_data)
```

### Example 2: Feature-Gated UI Element

```javascript
// Admin panel - check if AI features available
fetch('/api/license/check', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({feature: 'ai_features'})
})
.then(r => r.json())
.then(data => {
  if (data.available) {
    // Show AI menu item
    document.getElementById('ai-menu').style.display = 'block';
  } else {
    // Hide and show upgrade prompt
    document.getElementById('ai-menu').style.display = 'none';
  }
});
```

### Example 3: Trial Mode Banner

```python
from pbx.utils.licensing import get_license_manager, LicenseStatus

def get_trial_banner():
    lm = get_license_manager()
    status, message = lm.get_license_status()
    
    if status == LicenseStatus.ACTIVE:
        info = lm.get_license_info()
        if info['type'] == 'trial':
            return {
                'show_banner': True,
                'message': message,
                'cta': 'Upgrade Now',
                'cta_url': '/pricing'
            }
    
    return {'show_banner': False}
```

---

## Trial Mode

### How It Works

1. **First Run**: When PBX starts without a license and licensing is enabled, trial mode automatically activates
2. **Trial Marker**: System creates `.trial_start` file with start date
3. **Duration**: 30 days by default (configurable)
4. **Features**: Trial tier features (see License Tiers)

### Checking Trial Status

```bash
curl http://localhost:8080/api/license/status
```

**Response**:
```json
{
  "license": {
    "status": "active",
    "message": "Trial mode active (25 days remaining)",
    "type": "trial"
  }
}
```

### Configuring Trial Period

In `config.yml`:
```yaml
licensing:
  trial_period_days: 30  # Change to desired number of days
```

---

## Grace Periods

### How It Works

After license expiration, system enters **grace period** mode:

1. **Duration**: 7 days by default (configurable)
2. **Features**: All features remain available
3. **Warnings**: System displays expiration warnings
4. **Enforcement**: After grace period, features are restricted

### Configuring Grace Period

In `config.yml`:
```yaml
licensing:
  grace_period_days: 7  # Change to desired number of days
```

### Grace Period Status

```json
{
  "license": {
    "status": "grace_period",
    "message": "License expired. Grace period ends in 5 days"
  }
}
```

---

## Troubleshooting

### Licensing Won't Disable

**Problem**: Set `PBX_LICENSING_ENABLED=false` but licensing still active

**Solution**: Check for environment variable in multiple places:
```bash
# Check current environment
echo $PBX_LICENSING_ENABLED

# Check .env file
cat .env | grep LICENSING

# Check config.yml
grep -A 2 "licensing:" config.yml
```

**Fix**: Ensure environment variable is set before starting PBX:
```bash
export PBX_LICENSING_ENABLED=false
python main.py
```

### License Invalid Error

**Problem**: Installed license shows as invalid

**Solution**: Check license signature:
1. Ensure `license_secret_key` in config matches key used to generate license
2. Verify license file JSON is not corrupted
3. Check license file permissions (should be readable)

### Trial Already Used

**Problem**: Trial period already consumed

**Solution**: Remove trial marker to reset (for testing only):
```bash
rm .trial_start
```

**Warning**: Only do this for testing. In production, trial should only be used once.

### Features Not Available

**Problem**: License installed but features show as unavailable

**Solution**:
1. Check license status: `curl http://localhost:8080/api/license/status`
2. Verify license type includes feature: `curl http://localhost:8080/api/license/features`
3. Restart PBX to reload license: `sudo systemctl restart pbx`

---

## Security Considerations

### License Secret Key

**Important**: Change the default `license_secret_key` in production!

```yaml
licensing:
  license_secret_key: "$(openssl rand -hex 32)"
```

### Store Keys Securely

- **Never** commit license keys to version control
- Store in `.env` file (excluded from git)
- Use environment variables in production
- Restrict file permissions on `.license` file

```bash
chmod 600 .license
```

### Admin API Protection

**TODO**: Add authentication to admin license endpoints:
- `/api/license/generate`
- `/api/license/install`
- `/api/license/revoke`
- `/api/license/toggle`

Implement admin authentication before deploying to production.

---

## Business Models

### Subscription Model

**Monthly/Annual Billing**:
- Trial: Free (30 days)
- Basic: $29/month or $290/year
- Professional: $79/month or $790/year
- Enterprise: Custom pricing

**Implementation**:
1. Generate licenses with 30/365 day expiration
2. Auto-renew via payment system integration
3. Send expiration reminders at 30/14/7 days
4. Revoke on payment failure

### Perpetual Licensing

**One-Time Purchase**:
- Professional: $2,500 (lifetime)
- Enterprise: $10,000 (lifetime)

**Implementation**:
1. Generate license with no expiration
2. Optional maintenance/support subscription
3. Major version upgrades may require new license

### Freemium Model

**Free Tier**:
- Basic calling
- Limited extensions (10)
- No advanced features

**Paid Tiers**: Add advanced features

**Implementation**:
1. Licensing disabled by default (free)
2. Users activate license for paid features
3. Trial mode for testing paid features

---

## Future Enhancements

Potential improvements to the licensing system:

1. **Online License Validation**
   - Verify license with central server
   - Prevent license sharing
   - Track license usage

2. **Hardware Binding**
   - Bind license to server hardware
   - Prevent unauthorized transfers

3. **Floating Licenses**
   - Concurrent user limits
   - License check-out/check-in

4. **Usage-Based Billing**
   - Track actual usage
   - Bill based on minutes/calls

5. **Multi-Site Licensing**
   - Single license for multiple locations
   - Centralized license management

6. **License Portal**
   - Customer self-service portal
   - License key retrieval
   - Renewal management

---

## Support

For licensing questions or issues:

1. Check this guide
2. Review API documentation
3. Check system logs: `logs/pbx.log`
4. Contact support: support@example.com

---

**Last Updated**: December 22, 2025  
**Version**: 1.0  
**Status**: Production-Ready
