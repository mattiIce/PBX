# Premium Features - Usage Guide

This guide explains how to use the premium features that have been implemented in the PBX system.

## Table of Contents

1. [License Management](#license-management)
2. [Advanced Analytics](#advanced-analytics)
3. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
4. [Premium Admin Panel](#premium-admin-panel)
5. [API Endpoints](#api-endpoints)

---

## License Management

### Overview

The licensing system controls access to premium features based on subscription tier:

- **FREE**: Basic PBX features, limited extensions (5), limited concurrent calls (2)
- **BASIC**: Advanced analytics, custom reports, 25 extensions, 10 concurrent calls
- **PROFESSIONAL**: All BASIC features plus supervisor dashboard, voicemail transcription, SMS integration, IVR, 100 extensions, 50 concurrent calls
- **ENTERPRISE**: All features, unlimited extensions and calls

### Configuration

The license is stored in `license.json` at the root of the project:

```json
{
  "tier": "professional",
  "organization": "Your Company Name",
  "issued_date": "2024-01-01T00:00:00",
  "expiry_date": "2025-12-31T23:59:59",
  "license_key": "YOUR-LICENSE-KEY",
  "max_extensions": 100,
  "custom_features": [],
  "support_tier": "priority"
}
```

### Usage in Code

```python
from pbx.features.licensing import LicenseManager, FeatureFlag

# Initialize license manager
license_mgr = LicenseManager(config)

# Check if a feature is available
if license_mgr.has_feature(FeatureFlag.ADVANCED_ANALYTICS):
    # Use advanced analytics
    pass

# Check capacity limits
if license_mgr.check_limit('max_extensions', current_count):
    # Add extension
    pass

# Get complete license info
info = license_mgr.get_license_info()
```

### Available Feature Flags

- `ADVANCED_ANALYTICS` - Advanced call analytics and reporting
- `CALL_QUALITY_METRICS` - QoS monitoring (MOS, jitter, latency)
- `SUPERVISOR_DASHBOARD` - Real-time monitoring dashboard
- `CALL_MONITORING` - Silent monitoring, whisper, barge-in
- `VOICEMAIL_TRANSCRIPTION` - Speech-to-text voicemail
- `AI_ROUTING` - AI-powered call routing
- `CRM_INTEGRATION` - CRM system integrations
- `SMS_INTEGRATION` - SMS messaging
- `ADVANCED_IVR` - Visual IVR builder
- `VIDEO_CONFERENCING` - Video calls
- `TIERED_STORAGE` - Automatic storage tier management
- `ADVANCED_SECURITY` - Enhanced security features
- `SSO_INTEGRATION` - Single sign-on

---

## Advanced Analytics

### Overview

The analytics engine provides comprehensive insights into call center performance, historical trends, and predictive analytics.

### Features

1. **Call Volume Analysis**
   - By hour of day
   - By day of week/month
   - Trend analysis

2. **Extension Statistics**
   - Inbound/outbound call counts
   - Total duration
   - Average call duration
   - Busiest hours

3. **Executive Summary**
   - Period overview
   - Answer rates
   - Performance trends

### Usage

```python
from pbx.features.analytics import AnalyticsEngine

# Initialize analytics engine
analytics = AnalyticsEngine(config, cdr_manager)

# Get call volume by hour (last 7 days)
volume = analytics.get_call_volume_by_hour(days=7)

# Get extension statistics
stats = analytics.get_extension_statistics('1001', days=30)
print(f"Total calls: {stats['total_calls']}")
print(f"Average duration: {stats['average_duration_seconds']}s")

# Generate executive summary
summary = analytics.generate_executive_summary(days=7)
print(f"Answer rate: {summary['overview']['answer_rate']}%")

# Get top callers
top_callers = analytics.get_top_callers(limit=10, days=30)
```

### API Endpoints

```bash
# Call volume by hour
GET /api/analytics/volume/hour?days=7

# Call volume by day
GET /api/analytics/volume/day?days=30

# Extension statistics
GET /api/analytics/extension/1001?days=30

# Top callers
GET /api/analytics/top-callers?limit=10&days=30

# Call quality metrics (requires Professional or higher)
GET /api/analytics/quality?days=7

# Executive summary
GET /api/analytics/summary?days=7
```

---

## Role-Based Access Control (RBAC)

### Overview

RBAC provides granular control over admin panel access with predefined roles and custom permissions.

### Roles

1. **Super Admin** - Full system access
2. **Admin** - Most features except system administration
3. **Supervisor** - Call monitoring and reporting
4. **Agent** - Limited access (own calls, voicemail)
5. **Viewer** - Read-only access

### Permissions

Each role has specific permissions:

- `VIEW_DASHBOARD` - View dashboard
- `VIEW_EXTENSIONS` - View extensions
- `ADD_EXTENSION` - Add new extensions
- `EDIT_EXTENSION` - Edit extensions
- `DELETE_EXTENSION` - Delete extensions
- `VIEW_CALLS` - View active calls
- `MONITOR_CALLS` - Monitor/listen to calls
- `TERMINATE_CALLS` - Terminate active calls
- `VIEW_RECORDINGS` - View call recordings
- `DOWNLOAD_RECORDINGS` - Download recordings
- `DELETE_RECORDINGS` - Delete recordings
- `VIEW_CONFIG` - View configuration
- `EDIT_CONFIG` - Edit configuration
- `MANAGE_USERS` - Manage admin users
- `SYSTEM_ADMIN` - System administration

### Usage

#### Creating Users

```python
from pbx.features.rbac import RBACManager, Role

# Initialize RBAC manager
rbac = RBACManager(config)

# Create a new supervisor
rbac.create_user(
    username='supervisor1',
    password='secure_password',
    role=Role.SUPERVISOR,
    email='supervisor@company.com'
)

# Create user with custom permissions
rbac.create_user(
    username='custom_user',
    password='password',
    role=Role.AGENT,
    email='user@company.com',
    custom_permissions=['download_recordings']
)
```

#### Authentication

```python
# Authenticate user
user = rbac.authenticate('supervisor1', 'password')
if user:
    print(f"Logged in as: {user['username']}")
    print(f"Role: {user['role']}")
    print(f"Permissions: {user['permissions']}")

# Create session
token = rbac.create_session('supervisor1')

# Validate session
username = rbac.validate_session(token)
if username:
    print(f"Valid session for: {username}")

# Destroy session
rbac.destroy_session(token)
```

#### Permission Checking

```python
from pbx.features.rbac import Permission

# Check if user has permission
if rbac.has_permission('supervisor1', Permission.MONITOR_CALLS):
    # Allow call monitoring
    pass
```

### API Endpoints

```bash
# Login
POST /api/admin/login
{
  "username": "admin",
  "password": "password"
}

# Response includes session token
{
  "success": true,
  "token": "session-token-here",
  "user": {
    "username": "admin",
    "role": "super_admin",
    "permissions": [...]
  }
}

# List users
GET /api/admin/users
```

### Default Credentials

The system creates a default admin user on first run with a **randomly generated password** for security.

- **Username**: `admin`
- **Password**: Randomly generated (displayed in logs on first run)

**⚠️ Important**: 
- The random password is displayed in the logs ONLY ONCE when the admin user is first created
- Save this password immediately - it cannot be recovered
- Check the PBX logs for the password on first startup
- You can reset the password by deleting `admin_users.json` and restarting (generates a new random password)

---

## Premium Admin Panel

### Accessing Premium Features

1. Navigate to the admin panel: `http://localhost:8080/admin/`
2. Click on the "✨ Premium" tab in the navigation
3. View available features based on your license tier

### Features Display

The premium features page shows:

- Current license tier and expiration
- Available features (green checkmark)
- Locked features (requires upgrade)
- Feature descriptions and benefits
- Upgrade options

### Live Analytics Dashboard

For users with the `ADVANCED_ANALYTICS` feature:

- Real-time call statistics
- Historical performance charts
- Extension performance metrics
- Quality metrics (MOS, jitter, latency)
- Top callers report

---

## API Endpoints

### License Information

```bash
GET /api/license
```

Response:
```json
{
  "tier": "professional",
  "organization": "Your Company",
  "valid": true,
  "issued_date": "2024-01-01T00:00:00",
  "expiry_date": "2025-12-31T23:59:59",
  "features": [
    "advanced_analytics",
    "supervisor_dashboard",
    ...
  ],
  "limits": {
    "max_extensions": 100,
    "max_concurrent_calls": 50,
    "max_recording_storage_gb": 100,
    "api_calls_per_day": 10000
  },
  "usage": {
    "api_calls_today": 152,
    "total_calls_month": 5243,
    "recording_storage_used_gb": 23.5
  }
}
```

### Analytics Endpoints

All analytics endpoints require the `ADVANCED_ANALYTICS` feature.

```bash
# Call volume by hour
GET /api/analytics/volume/hour?days=7

# Call volume by day  
GET /api/analytics/volume/day?days=30

# Extension statistics
GET /api/analytics/extension/{extension_number}?days=30

# Top callers
GET /api/analytics/top-callers?limit=10&days=30

# Call quality metrics
GET /api/analytics/quality?days=7

# Executive summary
GET /api/analytics/summary?days=7
```

### RBAC Endpoints

```bash
# Login (creates session)
POST /api/admin/login
{
  "username": "admin",
  "password": "password"
}

# List users
GET /api/admin/users
```

---

## Configuration

Add to `config.yml`:

```yaml
# Premium Features Configuration
licensing:
  enabled: true
  license_file: license.json
  usage_file: usage.json

rbac:
  enabled: true
  users_file: admin_users.json
  session_timeout_hours: 8  # Session timeout (default: 24 hours)

analytics:
  enabled: true

cdr:
  directory: cdr
```

---

## Upgrading Your License

To upgrade your license tier:

1. Contact sales: sales@pbx-system.com
2. Receive new license key
3. Update `license.json` with new tier and key
4. Restart PBX system or reload license via API

### Pricing (Example)

- **FREE**: $0/month - 5 extensions, basic features
- **BASIC**: $49/month - 25 extensions, analytics
- **PROFESSIONAL**: $99/month - 100 extensions, advanced features
- **ENTERPRISE**: Custom pricing - unlimited, all features

---

## Security Considerations

1. **Change Default Credentials**: Always change the default admin password
2. **Use Strong Passwords**: Enforce password complexity
3. **Regular License Checks**: Monitor license expiration
4. **Audit Logging**: Track user actions (coming soon)
5. **Session Management**: Sessions expire after 24 hours of inactivity
6. **HTTPS**: Use TLS for admin panel in production
7. **API Rate Limiting**: Enforced based on license tier

---

## Troubleshooting

### License Issues

```bash
# Check license status
curl http://localhost:8080/api/license

# Common issues:
# - "valid": false - License expired, contact sales
# - Feature not available - Upgrade required
# - Usage limits exceeded - Upgrade or wait for reset
```

### RBAC Issues

```bash
# Default admin not working
# - Check admin_users.json exists
# - Try recreating: delete file and restart

# Permission denied
# - Verify user role has required permission
# - Check custom_permissions array
```

### Analytics Issues

```bash
# No data available
# - Ensure CDR directory exists
# - Check calls are being logged to CDR
# - Verify date range has data
```

---

## Support

For assistance with premium features:

- **Documentation**: This guide
- **Technical Support**: support@pbx-system.com
- **Sales**: sales@pbx-system.com
- **GitHub Issues**: https://github.com/mattiIce/PBX/issues

---

**Note**: Some features mentioned in PREMIUM_FEATURES.md are roadmap items and may require additional implementation. This guide covers currently implemented features.
