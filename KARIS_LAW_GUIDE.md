# Kari's Law Compliance Guide

## Overview

This PBX system implements **Kari's Law** compliance, which is a federal requirement under 47 CFR § 9.16 for multi-line telephone systems (MLTS). 

Kari's Law requires that:
1. **Direct 911 dialing** is enabled without requiring a prefix or access code
2. **Immediate routing** to emergency services without delay
3. **Automatic notification** to designated contacts when 911 is dialed

This implementation also supports **Ray Baum's Act** which requires providing dispatchable location information with 911 calls.

## Features

### ✅ Direct 911 Dialing (Kari's Law Requirement)

Users can dial **911 directly** without needing to dial a prefix like "9-911":

```
User dials: 911
System routes: Directly to emergency services
```

### ✅ Legacy Prefix Support

The system also accepts legacy dialing patterns for backward compatibility:

- `911` - Direct dialing (preferred)
- `9911` - Legacy prefix
- `9-911` - Legacy prefix with dash

All formats are automatically normalized to `911` before routing.

### ✅ Automatic Emergency Notification

When 911 is dialed, the system **automatically** notifies designated emergency contacts:

- Security team
- Building management
- Safety coordinators
- Other configured contacts

Notification methods include:
- Internal calls
- Overhead paging
- Email alerts
- SMS messages (if configured)

### ✅ Location Information (Ray Baum's Act)

Emergency calls include **dispatchable location** information:

- Building name/number
- Floor
- Room number
- Full address
- City, state, ZIP code

This ensures emergency responders know exactly where to go.

### ✅ Emergency Call Tracking

All emergency calls are logged with:
- Caller extension
- Caller name
- Location information
- Timestamp
- Call routing details
- Notification status

## Configuration

### Enable Kari's Law Compliance

Add to your `config.yml`:

```yaml
features:
  karis_law:
    enabled: true                    # Enable Kari's Law compliance
    auto_notify: true                # Auto-notify contacts on 911 calls
    require_location: true           # Require location registration
    emergency_trunk_id: "emergency"  # Dedicated emergency trunk (optional)
```

### Configure E911 Location Service

```yaml
features:
  e911:
    enabled: true
    site_address:
      address: "123 Manufacturing Drive"
      city: "Industrial City"
      state: "MI"
      zip_code: "48001"
    buildings:
      - id: "building_a"
        name: "Building A - Main Assembly"
        floors: 2
      - id: "building_b"
        name: "Building B - Warehouse"
        floors: 2
      - id: "building_c"
        name: "Building C - Offices"
        floors: 3
```

### Configure Emergency Trunk

Dedicated emergency trunk for 911 calls:

```yaml
trunks:
  - id: "emergency"
    name: "Emergency Services Trunk"
    host: "emergency.sip.provider.com"
    username: "emergency_user"
    password: "secure_password"
    priority: 1                      # Highest priority
    max_channels: 5
```

### Configure Emergency Contacts

```yaml
features:
  emergency_notification:
    enabled: true
    notify_on_911: true
    contacts:
      - name: "Security Team"
        extension: "1100"
        priority: 1
        notification_methods: ["call", "page"]
      
      - name: "Building Manager"
        extension: "1101"
        email: "manager@company.com"
        priority: 2
        notification_methods: ["call", "email"]
      
      - name: "Safety Coordinator"
        phone: "+15551234567"
        email: "safety@company.com"
        priority: 3
        notification_methods: ["sms", "email"]
```

## Registering Device Locations

### Via API

Register extension location for E911:

```bash
curl -X POST http://pbx-server:5000/api/e911/location/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "1001",
    "building_id": "building_a",
    "floor": "2",
    "room": "205"
  }'
```

### Via Admin Panel

1. Navigate to Admin Panel → E911 Management
2. Select extension
3. Choose building, floor, and room
4. Save location

## How It Works

### Call Flow for 911 Dialing

1. **User dials 911** from extension 1001
2. **System detects emergency number** (Kari's Law module)
3. **Location lookup** (Building A, Floor 2, Room 205)
4. **Emergency notification triggered** (all contacts notified)
5. **Call routed to emergency trunk** (direct to 911)
6. **Location info sent** (Ray Baum's Act compliance)
7. **Call tracked and logged** (compliance audit trail)

### Automatic Notification Flow

When 911 is dialed:

```
1. Caller: Extension 1001 dials 911
   ↓
2. System: Detects emergency call
   ↓
3. Location: Building A, Floor 2, Room 205 retrieved
   ↓
4. Notification: All emergency contacts alerted
   - Security (ext 1100): Called + Paged
   - Manager (ext 1101): Called + Emailed
   - Safety (phone): SMS + Email
   ↓
5. Routing: Call routed to emergency services
   ↓
6. Logging: Full audit trail created
```

## Compliance Validation

### Check Compliance Status

```python
# Via API
GET /api/karis-law/compliance

# Response
{
  "compliant": true,
  "warnings": [],
  "errors": []
}
```

### Validate Configuration

The system performs automatic validation:

✅ **Compliant Configuration:**
- Kari's Law enabled
- Emergency trunk configured and available
- Emergency notification system active
- E911 location service enabled

⚠️ **Warnings:**
- No dedicated emergency trunk (using fallback)
- Emergency notification disabled
- Location service not configured

❌ **Non-Compliant:**
- Kari's Law disabled
- No trunk available to route 911 calls

## Testing

### Test Emergency Notification

```bash
# Via API
POST /api/emergency/test

# Response
{
  "success": true,
  "contacts_notified": 3,
  "message": "Emergency notification test completed"
}
```

### Test 911 Dialing (Development Only)

⚠️ **WARNING**: Never test actual 911 calls in production!

In test/development mode:
- Set `TEST_MODE=1` environment variable
- Actual 911 calls are blocked
- Logging shows what would happen
- Notifications are sent to test contacts

```bash
export TEST_MODE=1
python tests/test_karis_law.py
```

## Monitoring and Reporting

### View Emergency Call History

```bash
# Via API
GET /api/karis-law/history?limit=50

# Response
{
  "calls": [
    {
      "call_id": "emergency-20251212-143000",
      "caller_extension": "1001",
      "caller_name": "John Smith",
      "location": "Building A, Floor 2, Room 205",
      "timestamp": "2025-12-12T14:30:00",
      "routing": {
        "success": true,
        "trunk_id": "emergency",
        "trunk_name": "Emergency Services Trunk"
      }
    }
  ]
}
```

### Statistics

```bash
# Via API
GET /api/karis-law/statistics

# Response
{
  "enabled": true,
  "total_emergency_calls": 5,
  "auto_notify": true,
  "require_location": true,
  "emergency_trunk_configured": true
}
```

## Legal Compliance

### Kari's Law (47 CFR § 9.16)

This implementation satisfies all Kari's Law requirements:

✅ **Direct 911 dialing** without prefix  
✅ **Immediate routing** to emergency services  
✅ **Automatic notification** to designated contacts  
✅ **No delays** in emergency call processing  

### Ray Baum's Act

This implementation provides dispatchable location:

✅ **Building identifier**  
✅ **Floor number**  
✅ **Room/office number**  
✅ **Street address**  
✅ **City, state, ZIP**  

### Audit Trail

All emergency calls are logged:

✅ **Caller identification**  
✅ **Timestamp**  
✅ **Location information**  
✅ **Routing details**  
✅ **Notification status**  

## Best Practices

### 1. Register All Device Locations

Ensure every phone/device has a registered location:

```bash
# Check unregistered devices
GET /api/e911/unregistered-devices
```

### 2. Test Regularly

Test emergency notification monthly:

```bash
POST /api/emergency/test
```

### 3. Keep Emergency Contacts Updated

Review and update emergency contacts quarterly:

```bash
GET /api/emergency/contacts
PUT /api/emergency/contacts/{contact_id}
```

### 4. Monitor Emergency Trunk Health

Ensure emergency trunk is always available:

```bash
GET /api/trunks/emergency/status
```

### 5. Review Compliance Status

Check compliance regularly:

```bash
GET /api/karis-law/compliance
```

## Troubleshooting

### Issue: 911 Calls Not Routing

**Check:**
1. Is Kari's Law enabled? (`features.karis_law.enabled: true`)
2. Is emergency trunk registered? (`GET /api/trunks/emergency/status`)
3. Are there available channels? (`trunk.channels_available > 0`)

**Fix:**
```yaml
# Ensure emergency trunk is configured
trunks:
  - id: "emergency"
    name: "Emergency Services"
    host: "emergency.sip.provider.com"
    priority: 1
    max_channels: 5
```

### Issue: Notifications Not Sent

**Check:**
1. Is emergency notification enabled? (`features.emergency_notification.enabled: true`)
2. Are contacts configured? (`GET /api/emergency/contacts`)
3. Is auto-notify enabled? (`features.karis_law.auto_notify: true`)

**Fix:**
```yaml
features:
  karis_law:
    auto_notify: true
  emergency_notification:
    enabled: true
    notify_on_911: true
```

### Issue: Location Not Available

**Check:**
1. Is E911 service enabled? (`features.e911.enabled: true`)
2. Is location registered? (`GET /api/e911/location/{extension}`)

**Fix:**
```bash
# Register location for extension
POST /api/e911/location/register
{
  "device_id": "1001",
  "building_id": "building_a",
  "floor": "2",
  "room": "205"
}
```

## API Reference

### Kari's Law Endpoints

```
GET  /api/karis-law/compliance      - Check compliance status
GET  /api/karis-law/history         - Get emergency call history
GET  /api/karis-law/statistics      - Get statistics
```

### E911 Location Endpoints

```
POST /api/e911/location/register    - Register device location
GET  /api/e911/location/{device_id} - Get device location
GET  /api/e911/buildings            - List all buildings
```

### Emergency Notification Endpoints

```
GET  /api/emergency/contacts        - List emergency contacts
POST /api/emergency/contacts        - Add emergency contact
POST /api/emergency/test            - Test notification system
GET  /api/emergency/history         - Get notification history
```

## Security Considerations

### 1. E911 Protection in Test Mode

The system automatically blocks 911 calls in test/development:

```python
# Environment detection
TEST_MODE=1  # Blocks actual 911 calls
PYTEST_CURRENT_TEST=...  # Detected during tests
```

### 2. Access Control

Restrict E911 configuration to administrators:

```yaml
security:
  rbac:
    roles:
      - name: "admin"
        permissions: ["e911:manage", "emergency:configure"]
```

### 3. Audit Logging

All emergency calls and configuration changes are logged:

```bash
tail -f logs/emergency.log
```

## Support

For questions or issues with Kari's Law compliance:

1. Check this guide
2. Review compliance status: `GET /api/karis-law/compliance`
3. Check system logs: `logs/pbx.log`
4. Test notification: `POST /api/emergency/test`

## References

- **Kari's Law**: 47 CFR § 9.16
- **RAY BAUM'S Act**: Public Law 115-127
- **FCC Kari's Law**: [https://www.fcc.gov/911-dispatchable-location](https://www.fcc.gov/911-dispatchable-location)
- **Implementation Date**: December 12, 2025

---

**Implementation Status**: ✅ FULLY COMPLIANT  
**Last Updated**: December 12, 2025  
**Version**: 1.0.0
