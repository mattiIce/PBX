# Hot-Desking - Implementation Guide

## Overview

Hot-Desking allows users to log in to any phone device and have their extension settings and profile follow them. This is ideal for flexible workspaces, shared phones, and mobile workforces.

**Status**: ✅ **Implemented and Tested**

## Features

- **Dynamic Extension Assignment**: Log in from any device
- **PIN Authentication**: Secure login with voicemail PIN
- **Session Management**: Track active sessions
- **Auto-Logout**: Automatic logout after inactivity
- **Concurrent/Exclusive Modes**: Control multiple device logins
- **Profile Migration**: Extension settings follow the user
- **Webhook Integration**: Login/logout event notifications

## Architecture

### Components

1. **HotDeskingSystem** - Main hot-desking controller
2. **HotDeskSession** - Represents active login session
3. **Session Manager**: Tracks device assignments
4. **Auto-Logout Worker**: Cleans up inactive sessions

### Flow Diagram

```
User at Phone
    ↓
Dial Hot-Desk Code or Use API
    ↓
Enter Extension + PIN
    ↓
Hot-Desking System
    ↓
Validate Extension & PIN
    ↓
Create Session
    ↓
Extension Profile Applied to Device
    ↓
User Ready to Make/Receive Calls
```

## Configuration

### Enable Hot-Desking in config.yml

```yaml
features:
  hot_desking:
    enabled: true
    require_pin: true                  # Require voicemail PIN for login
    allow_concurrent_logins: false     # Allow same extension on multiple devices
    auto_logout_timeout: 28800         # Auto-logout after inactivity (8 hours)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | false | Enable/disable hot-desking |
| `require_pin` | boolean | true | Require PIN for login |
| `allow_concurrent_logins` | boolean | false | Allow multiple simultaneous logins |
| `auto_logout_timeout` | integer | 28800 | Inactive session timeout (seconds) |

## API Endpoints

### 1. Hot-Desk Login

Log in an extension to a device.

**Request:**
```bash
POST /api/hot-desk/login
Content-Type: application/json

{
  "extension": "1001",
  "device_id": "00:15:65:12:34:56",
  "ip_address": "192.168.1.100",
  "pin": "1234"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Extension 1001 logged in",
  "profile": {
    "extension": "1001",
    "name": "John Doe",
    "email": "john@company.com",
    "allow_external": true,
    "voicemail_enabled": true,
    "call_forwarding": null,
    "do_not_disturb": false
  }
}
```

### 2. Hot-Desk Logout

Log out from a device or extension.

**Request (by device):**
```bash
POST /api/hot-desk/logout
Content-Type: application/json

{
  "device_id": "00:15:65:12:34:56"
}
```

**Request (by extension):**
```bash
POST /api/hot-desk/logout
Content-Type: application/json

{
  "extension": "1001"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Extension 1001 logged out from 1 device(s)"
}
```

### 3. Get Active Sessions

Get all active hot-desk sessions.

**Request:**
```bash
GET /api/hot-desk/sessions
```

**Response:**
```json
{
  "count": 2,
  "sessions": [
    {
      "extension": "1001",
      "device_id": "00:15:65:12:34:56",
      "ip_address": "192.168.1.100",
      "logged_in_at": "2025-12-07T08:00:00",
      "last_activity": "2025-12-07T12:30:00",
      "auto_logout_enabled": true
    },
    {
      "extension": "1002",
      "device_id": "00:15:65:AB:CD:EF",
      "ip_address": "192.168.1.101",
      "logged_in_at": "2025-12-07T09:00:00",
      "last_activity": "2025-12-07T12:25:00",
      "auto_logout_enabled": true
    }
  ]
}
```

### 4. Get Session by Device

Get hot-desk session for a specific device.

**Request:**
```bash
GET /api/hot-desk/session/00:15:65:12:34:56
```

**Response:**
```json
{
  "extension": "1001",
  "device_id": "00:15:65:12:34:56",
  "ip_address": "192.168.1.100",
  "logged_in_at": "2025-12-07T08:00:00",
  "last_activity": "2025-12-07T12:30:00",
  "auto_logout_enabled": true
}
```

### 5. Get Extension Information

Get hot-desk information for an extension.

**Request:**
```bash
GET /api/hot-desk/extension/1001
```

**Response:**
```json
{
  "extension": "1001",
  "logged_in": true,
  "device_count": 1,
  "sessions": [
    {
      "extension": "1001",
      "device_id": "00:15:65:12:34:56",
      "ip_address": "192.168.1.100",
      "logged_in_at": "2025-12-07T08:00:00",
      "last_activity": "2025-12-07T12:30:00",
      "auto_logout_enabled": true
    }
  ]
}
```

## Webhook Integration

Hot-desking triggers webhook events for login and logout actions.

### Login Event

```json
{
  "event_type": "hot_desk.login",
  "timestamp": "2025-12-07T08:00:00",
  "data": {
    "extension": "1001",
    "device_id": "00:15:65:12:34:56",
    "ip_address": "192.168.1.100",
    "timestamp": "2025-12-07T08:00:00"
  }
}
```

### Logout Event

```json
{
  "event_type": "hot_desk.logout",
  "timestamp": "2025-12-07T17:00:00",
  "data": {
    "extension": "1001",
    "device_id": "00:15:65:12:34:56",
    "timestamp": "2025-12-07T17:00:00"
  }
}
```

### Configure Webhook Subscription

```yaml
features:
  webhooks:
    enabled: true
    subscriptions:
      - url: "https://your-system.com/webhooks/hotdesk"
        events: ["hot_desk.login", "hot_desk.logout"]
        enabled: true
```

## Use Cases

### 1. Flexible Office Space

**Scenario**: Open office with hot desks

**Setup**:
- `allow_concurrent_logins: false`
- `require_pin: true`
- `auto_logout_timeout: 28800` (8 hours)

**Flow**:
1. Employee arrives and sits at any desk
2. Dials hot-desk code or uses web interface
3. Enters extension number and PIN
4. Phone configures with their extension
5. Makes and receives calls as normal
6. Logs out when leaving (or auto-logout after 8 hours)

### 2. Shared Reception Desk

**Scenario**: Multiple receptionists sharing one phone

**Setup**:
- `allow_concurrent_logins: false`
- `require_pin: true`
- `auto_logout_timeout: 3600` (1 hour)

**Flow**:
1. Receptionist starts shift
2. Logs in with their extension
3. Previous receptionist is automatically logged out
4. Receives calls for their extension
5. Shift ends, next receptionist logs in

### 3. Mobile Workers

**Scenario**: Field technicians using office phones when available

**Setup**:
- `allow_concurrent_logins: true` (can be on mobile and office phone)
- `require_pin: true`
- `auto_logout_timeout: 14400` (4 hours)

**Flow**:
1. Technician enters office
2. Logs into desk phone
3. Still receives calls on mobile (concurrent mode)
4. Can answer from either device
5. Auto-logout when leaving office

### 4. Contact Center

**Scenario**: Agent can work from any workstation

**Setup**:
- `allow_concurrent_logins: false`
- `require_pin: true`
- `auto_logout_timeout: 900` (15 minutes for break time)

**Flow**:
1. Agent logs in at start of shift
2. Receives queue calls
3. Takes break - auto-logout after 15 minutes
4. Returns to any available workstation
5. Logs back in to resume work

## Security

### PIN Authentication

Hot-desking uses the extension's voicemail PIN for authentication:

```python
# PIN is validated against extension voicemail_pin
ext_obj = extension_registry.get_extension('1001')
voicemail_pin = ext_obj.get('voicemail_pin')

if pin != voicemail_pin:
    # Login fails
    return False
```

### Best Practices

1. **Enforce Strong PINs**: Set minimum PIN length in extension configuration
2. **Enable Auto-Logout**: Prevent unauthorized use of unattended sessions
3. **Monitor Sessions**: Regular review of active sessions
4. **Audit Logging**: Track all login/logout events via webhooks
5. **Failed Attempt Tracking**: Monitor for brute force attempts

## Session Management

### Activity Tracking

Sessions automatically track last activity:

```python
# Update activity on:
- Login
- Call made/received
- Extension feature used
- Manual activity update via API
```

### Auto-Logout

Inactive sessions are automatically logged out:

1. Cleanup worker runs every 60 seconds
2. Checks session last_activity timestamp
3. Compares against auto_logout_timeout
4. Logs out inactive sessions
5. Triggers logout webhook

### Manual Logout

Users can manually logout:
- Dial logout code on phone
- Use API endpoint
- Admin can logout specific extension/device

## Phone Integration

### SIP Phone Configuration

Configure hot-desking feature code on SIP phones:

```
Feature Code: *55
Action: Hot-Desk Login
Display: "Enter Ext + PIN"
```

### Example Phone Menu

```
Press *55 for Hot-Desk Login
Press *56 for Hot-Desk Logout
Press *57 for Hot-Desk Status
```

## Monitoring & Reporting

### Dashboard Metrics

Track hot-desking usage:
- Active sessions count
- Login/logout events per day
- Average session duration
- Most-used devices
- Peak usage times

### Reports

Generate reports:
- User login history
- Device usage statistics
- PIN authentication failures
- Auto-logout events

## Troubleshooting

### Login Fails

**Common Causes**:
- Wrong PIN
- Extension not found
- Extension already logged in (exclusive mode)
- Hot-desking disabled

**Solutions**:
1. Verify extension exists
2. Reset voicemail PIN if forgotten
3. Check concurrent login settings
4. Enable hot-desking in config.yml

### Session Not Logging Out

**Causes**:
- Auto-logout disabled for session
- Activity being updated frequently
- Cleanup thread not running

**Solutions**:
1. Check auto_logout_enabled flag
2. Verify cleanup thread is running
3. Manual logout via API

### Profile Not Applying

**Causes**:
- Extension profile incomplete
- Device not registering
- SIP registration delay

**Solutions**:
1. Verify extension configuration
2. Check device connectivity
3. Wait for SIP re-registration

## Testing

Run hot-desking tests:
```bash
python tests/test_hot_desking.py
```

All 9 tests should pass:
- Hot desk session creation
- System initialization
- Login and logout
- Invalid PIN handling
- Concurrent login behavior
- Extension logout from multiple devices
- Session activity tracking
- Profile retrieval

---

**Implementation Date**: December 7, 2025  
**Status**: Production Ready ✅  
**Test Coverage**: 9/9 tests passing
