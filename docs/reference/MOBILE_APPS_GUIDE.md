# Mobile Apps Framework Guide

## Overview

The Mobile Apps framework provides comprehensive support for iOS and Android mobile clients, enabling full PBX functionality on mobile devices including calls, voicemail, presence, and more.

## Features

- **Native Mobile Clients** - iOS and Android app support
- **Push Notifications** - Firebase Cloud Messaging (FCM) and APNs
- **SIP Registration** - Mobile device SIP client registration
- **Background Calling** - Handle calls while app is in background
- **Device Management** - Multi-device support per user
- **Call Continuity** - Transfer calls between desk and mobile
- **Voicemail Access** - Visual voicemail on mobile
- **Presence Updates** - Real-time status from mobile

## Supported Platforms

- **iOS** - iPhone and iPad (iOS 13+)
- **Android** - Android 8.0 (Oreo) and above
- **SIP Clients** - Compatible with standard SIP clients (Linphone, Zoiper, etc.)

## Configuration

### config.yml
```yaml
features:
  mobile_apps:
    enabled: true
    push_notifications:
      enabled: true
      fcm_enabled: true      # Firebase Cloud Messaging
      apns_enabled: true     # Apple Push Notification Service
      fcm_server_key: "your-fcm-server-key"
      apns_cert_path: "/path/to/apns-cert.pem"
      apns_key_path: "/path/to/apns-key.pem"
      apns_team_id: "your-team-id"
      apns_bundle_id: "com.yourcompany.pbxapp"
    sip_configuration:
      enable_tcp: true
      enable_tls: true
      enable_push_wake: true
    background_mode:
      enabled: true
      keep_alive_interval: 30  # seconds
```

## Mobile Device Registration

### Register Device
```python
from pbx.features.mobile_apps import get_mobile_apps, Platform

mobile = get_mobile_apps()

# Register iOS device
result = mobile.register_device(
    extension='1001',
    platform=Platform.IOS,
    device_token='apns-device-token-here',
    device_info={
        'model': 'iPhone 14 Pro',
        'os_version': '17.1',
        'app_version': '1.0.0'
    }
)

# Register Android device
result = mobile.register_device(
    extension='1002',
    platform=Platform.ANDROID,
    device_token='fcm-device-token-here',
    device_info={
        'model': 'Pixel 7',
        'os_version': '14',
        'app_version': '1.0.0'
    }
)
```

### SIP Configuration for Mobile

```python
# Get SIP config for mobile client
sip_config = mobile.get_sip_config_for_device('device-id-123')

# Returns:
# {
#     'server': 'pbx.yourcompany.com',
#     'port': 5060,
#     'transport': 'tcp',  # tcp or tls
#     'username': '1001',
#     'password': 'encrypted-password',
#     'realm': 'yourcompany.com',
#     'stun_servers': ['stun:stun.l.google.com:19302'],
#     'push_enabled': true
# }
```

## Push Notifications

### Send Push Notification

```python
from pbx.features.mobile_apps import NotificationType

# Send incoming call notification (iOS)
mobile.send_push_notification(
    device_id='device-123',
    notification_type=NotificationType.INCOMING_CALL,
    data={
        'caller_id': '555-0100',
        'caller_name': 'John Doe',
        'call_id': 'call-456'
    }
)

# Send voicemail notification (Android)
mobile.send_push_notification(
    device_id='device-456',
    notification_type=NotificationType.VOICEMAIL,
    data={
        'sender': '555-0200',
        'duration': 45,
        'timestamp': '2025-01-15T10:30:00Z'
    }
)

# Send missed call notification
mobile.send_push_notification(
    device_id='device-789',
    notification_type=NotificationType.MISSED_CALL,
    data={
        'caller_id': '555-0300',
        'timestamp': '2025-01-15T09:15:00Z'
    }
)
```

### Notification Types

- **INCOMING_CALL** - Alert for incoming call with wake-up
- **VOICEMAIL** - New voicemail message
- **MISSED_CALL** - Missed call notification
- **MESSAGE** - Text/chat message (future)
- **PRESENCE_UPDATE** - Status change of contact

## REST API Endpoints

### Register Mobile Device
```bash
POST /api/framework/mobile-apps/register
{
  "extension": "1001",
  "platform": "ios",
  "device_token": "apns-device-token",
  "device_info": {
    "model": "iPhone 14",
    "os_version": "17.1",
    "app_version": "1.0.0"
  }
}
```

### Get SIP Configuration
```bash
GET /api/framework/mobile-apps/sip-config/{device_id}
```

### Send Push Notification
```bash
POST /api/framework/mobile-apps/push
{
  "device_id": "device-123",
  "type": "incoming_call",
  "data": {
    "caller_id": "555-0100",
    "caller_name": "John Doe"
  }
}
```

### List Devices for Extension
```bash
GET /api/framework/mobile-apps/devices/{extension}
```

### Unregister Device
```bash
DELETE /api/framework/mobile-apps/device/{device_id}
```

## iOS App Integration

### PushKit (VoIP Notifications)

```swift
// AppDelegate.swift
import PushKit

func registerForVoIPPushes() {
    let voipRegistry = PKPushRegistry(queue: nil)
    voipRegistry.delegate = self
    voipRegistry.desiredPushTypes = [.voIP]
}

func pushRegistry(_ registry: PKPushRegistry, 
                 didReceiveIncomingPushWith payload: PKPushPayload,
                 for type: PKPushType) {
    if type == .voIP {
        let callerID = payload.dictionaryPayload["caller_id"] as? String
        let callerName = payload.dictionaryPayload["caller_name"] as? String
        
        // Report incoming call to CallKit
        reportIncomingCall(callerID: callerID, callerName: callerName)
    }
}
```

### CallKit Integration

```swift
import CallKit

let provider = CXProvider(configuration: CXProviderConfiguration())

func reportIncomingCall(callerID: String, callerName: String) {
    let update = CXCallUpdate()
    update.remoteHandle = CXHandle(type: .phoneNumber, value: callerID)
    update.localizedCallerName = callerName
    
    provider.reportNewIncomingCall(with: UUID(), update: update) { error in
        if let error = error {
            print("Failed to report call: \(error)")
        }
    }
}
```

## Android App Integration

### Firebase Cloud Messaging

```java
// MyFirebaseMessagingService.java
public class MyFirebaseMessagingService extends FirebaseMessagingService {
    
    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        String type = remoteMessage.getData().get("type");
        
        if ("incoming_call".equals(type)) {
            String callerID = remoteMessage.getData().get("caller_id");
            String callerName = remoteMessage.getData().get("caller_name");
            
            // Show incoming call notification
            showIncomingCallNotification(callerID, callerName);
            
            // Wake up SIP client
            wakeSipClient();
        }
    }
    
    @Override
    public void onNewToken(String token) {
        // Send token to PBX server
        registerDeviceToken(token);
    }
}
```

### Foreground Service for Calls

```java
public class CallService extends Service {
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Notification notification = createCallNotification();
        startForeground(1, notification);
        
        // Handle SIP call
        return START_STICKY;
    }
}
```

## Background Mode

### Keep-Alive Mechanism

The framework implements a keep-alive mechanism for mobile devices:

```python
# Background keep-alive configuration
mobile.configure_keep_alive(
    interval=30,  # Send keep-alive every 30 seconds
    timeout=90    # Consider device offline after 90 seconds
)

# Handle keep-alive from mobile device
mobile.handle_keep_alive(device_id='device-123')
```

### Battery Optimization

```python
# Configure battery-optimized settings
mobile.configure_battery_optimization(
    device_id='device-123',
    settings={
        'push_only_mode': True,      # Use push notifications instead of persistent connection
        'aggressive_timeout': False,  # Don't timeout quickly
        'reduce_bandwidth': True      # Use lower quality codecs
    }
)
```

## Call Continuity

### Transfer Call to Mobile

```python
# Transfer active call from desk phone to mobile
mobile.transfer_call_to_mobile(
    call_id='call-123',
    from_device='desk-phone',
    to_device='mobile-device-456'
)
```

### Pickup Call on Mobile

```python
# Pickup ringing call on mobile device
mobile.pickup_call_on_mobile(
    call_id='call-123',
    device_id='mobile-device-456'
)
```

## Admin Panel

Access Mobile Apps management in the admin panel:

1. Navigate to **Admin Panel** → **Framework Features** → **Mobile Apps**
2. View registered mobile devices
3. Send test push notifications
4. Configure push notification settings
5. Monitor device status and connectivity
6. View device statistics

## Best Practices

### Security
- **TLS Required:** Always use TLS for SIP on mobile
- **Token Rotation:** Rotate device tokens periodically
- **Authentication:** Require strong passwords for SIP accounts
- **Certificate Pinning:** Implement certificate pinning in mobile apps

### Performance
- **Codec Selection:** Use efficient codecs (Opus) for mobile
- **Bandwidth Adaptation:** Adapt to network conditions
- **Battery Life:** Minimize keep-alive frequency
- **Push Wake:** Use push notifications to wake app for calls

### User Experience
- **CallKit (iOS):** Integrate with native call UI
- **Foreground Service (Android):** Use for active calls
- **Offline Handling:** Handle offline state gracefully
- **Network Switching:** Handle WiFi/cellular transitions

## Database Schema

### mobile_app_installations
```sql
CREATE TABLE mobile_app_installations (
    id SERIAL PRIMARY KEY,
    extension VARCHAR(10) NOT NULL,
    device_id VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(20) NOT NULL,  -- ios, android
    device_token TEXT NOT NULL,
    device_info JSONB,
    sip_registered BOOLEAN DEFAULT false,
    push_enabled BOOLEAN DEFAULT true,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_extension (extension),
    INDEX idx_platform (platform)
);
```

### push_notification_log
```sql
CREATE TABLE push_notification_log (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    payload JSONB,
    delivered BOOLEAN DEFAULT false,
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT NOW()
);
```

## Troubleshooting

### Push Notifications Not Working

**iOS:**
- Verify APNS certificates are valid
- Check app bundle ID matches configuration
- Ensure PushKit is properly configured
- Test in production environment (not debug)

**Android:**
- Verify FCM server key is correct
- Check app is not battery-optimized
- Ensure Firebase is properly initialized
- Test with latest Google Play Services

### Calls Not Waking Device

**Solution:**
- Ensure VoIP push notifications are enabled
- Verify CallKit integration (iOS)
- Check foreground service (Android)
- Review device battery optimization settings

### SIP Registration Fails

**Solution:**
- Check network connectivity
- Verify SIP credentials
- Ensure firewall allows SIP ports
- Try TCP instead of UDP for mobile

## Next Steps

1. **Develop Mobile Apps:** Build iOS and Android apps
2. **Configure Push:** Set up FCM and APNS credentials
3. **Test Push Notifications:** Send test notifications
4. **Deploy Apps:** Publish to App Store and Play Store
5. **Monitor Usage:** Track device registrations and usage

## Related Documentation

- [FRAMEWORK_FEATURES_COMPLETE_GUIDE.md](FRAMEWORK_FEATURES_COMPLETE_GUIDE.md)
- [COMPLETE_GUIDE.md - Section 9.2: REST API](../../COMPLETE_GUIDE.md#92-rest-api-reference)
