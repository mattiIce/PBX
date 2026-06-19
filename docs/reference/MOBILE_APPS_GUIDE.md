# Mobile Apps Framework Guide

## Overview

The Mobile Apps framework provides comprehensive support for iOS and Android mobile clients, enabling full PBX functionality on mobile devices including calls, voicemail, presence, and more.

## Features

- **Native Mobile Clients** - iOS and Android app support
- **Push Notifications** - Firebase Cloud Messaging (FCM) and APNs
- **SIP Registration** - Mobile-optimized SIP client configuration (TCP, push wake, Opus)
- **Background Calling** - Wake the app for incoming calls via push notifications
- **Device Management** - Multi-device support per user

## Supported Platforms

- **iOS** - iPhone and iPad (iOS 13+)
- **Android** - Android 8.0 (Oreo) and above
- **SIP Clients** - Compatible with standard SIP clients (Linphone, Zoiper, etc.)

## Configuration

### config.yml

The mobile app framework (`MobileAppFramework`) reads the following keys from
`features.mobile_apps`:

```yaml
features:
  mobile_apps:
    enabled: true
    ios_enabled: true      # Allow iOS device registration (default: true)
    android_enabled: true  # Allow Android device registration (default: true)
    push_enabled: true     # Enable push notifications (default: true)
    turn_servers:          # Optional TURN servers returned in mobile SIP config
      - urls: ["turn:turn.example.com:3478"]
        username: "user"
        credential: "pass"
        credentialType: "password"
```

Push delivery itself is handled by the separate `MobilePushNotifications` service
(Firebase Cloud Messaging), configured under `features.mobile_push`:

```yaml
features:
  mobile_push:
    enabled: true
    fcm_credentials_path: "/path/to/serviceAccountKey.json"  # Firebase service account
```

## Mobile Device Registration

### Register Device
```python
from pbx.features.mobile_apps import get_mobile_app_framework, MobilePlatform

mobile = get_mobile_app_framework()

# Register iOS device
result = mobile.register_device(
    device_id='device-id-123',
    platform=MobilePlatform.IOS.value,
    user_id='1001',
    device_info={
        'device_model': 'iPhone 14 Pro',
        'os_version': '17.1',
        'app_version': '1.0.0',
        'push_token': 'apns-device-token-here'
    }
)

# Register Android device
result = mobile.register_device(
    device_id='device-id-456',
    platform=MobilePlatform.ANDROID.value,
    user_id='1002',
    device_info={
        'device_model': 'Pixel 7',
        'os_version': '14',
        'app_version': '1.0.0',
        'push_token': 'fcm-device-token-here'
    }
)
```

### SIP Configuration for Mobile

```python
# Get SIP config for mobile client
sip_config = mobile.configure_sip_for_mobile('device-id-123', '1001')

# Returns:
# {
#     'extension': '1001',
#     'server': 'localhost',
#     'port': 5060,
#     'transport': 'tcp',
#     'keep_alive_interval': 30,
#     'register_interval': 600,
#     'codec_priority': ['opus', 'pcma', 'pcmu'],
#     'ice_enabled': True,
#     'turn_servers': [...],
#     'battery_optimization': {
#         'background_mode': 'push',
#         'reduce_bandwidth': True,
#         'adaptive_quality': True
#     }
# }
```

## Push Notifications

### Send Push Notification

```python
# Send incoming call notification (iOS)
mobile.send_push_notification(
    device_id='device-123',
    notification={
        'type': 'incoming_call',
        'caller_id': '555-0100',
        'caller_name': 'John Doe',
        'call_id': 'call-456'
    }
)

# Send voicemail notification (Android)
mobile.send_push_notification(
    device_id='device-456',
    notification={
        'type': 'new_voicemail',
        'sender': '555-0200',
        'duration': 45,
        'timestamp': '2025-01-15T10:30:00Z'
    }
)

# Send missed call notification
mobile.send_push_notification(
    device_id='device-789',
    notification={
        'type': 'missed_call',
        'caller_id': '555-0300',
        'timestamp': '2025-01-15T09:15:00Z'
    }
)
```

### Notification Types

The `type` field in the notification dict identifies the notification category. Common values:

- **incoming_call** - Alert for incoming call with wake-up
- **new_voicemail** - New voicemail message
- **missed_call** - Missed call notification
- **test** - Test notification

## REST API Endpoints

### Register Mobile Device
```bash
POST /api/mobile-push/register
{
  "user_id": "1001",
  "device_token": "apns-device-token",
  "platform": "ios"
}
```

### List Devices for a User
```bash
GET /api/mobile-push/devices/{user_id}
```

### List All Registered Devices
```bash
GET /api/mobile-push/devices
```

### Send Test Push Notification
```bash
POST /api/mobile-push/test
{
  "user_id": "1001"
}
```

### Unregister Device
```bash
POST /api/mobile-push/unregister
{
  "user_id": "1001",
  "device_token": "apns-device-token"
}
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

### mobile_devices
```sql
CREATE TABLE IF NOT EXISTS mobile_devices (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    device_token VARCHAR(255) NOT NULL UNIQUE,
    platform VARCHAR(20) NOT NULL,
    registered_at TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### push_notifications
```sql
CREATE TABLE IF NOT EXISTS push_notifications (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    body TEXT,
    data TEXT,
    sent_at TIMESTAMP NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
- [PLANNED_FEATURES.md](../PLANNED_FEATURES.md) - Planned (not-yet-implemented) capabilities for this feature
- [COMPLETE_GUIDE.md - Section 9.2: REST API](../../COMPLETE_GUIDE.md#92-rest-api-reference)
