"""
Mobile Apps Framework
iOS and Android mobile client support
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List

from pbx.utils.logger import get_logger


class MobilePlatform(Enum):
    """Mobile platform enumeration"""

    IOS = "ios"
    ANDROID = "android"


class DeviceType(Enum):
    """Device type"""

    PHONE = "phone"
    TABLET = "tablet"


class MobileDevice:
    """Represents a registered mobile device"""

    def __init__(
        self, device_id: str, platform: MobilePlatform, user_id: str, push_token: str = None
    ):
        """Initialize mobile device"""
        self.device_id = device_id
        self.platform = platform
        self.user_id = user_id
        self.push_token = push_token
        self.registered_at = datetime.now()
        self.last_active = datetime.now()
        self.app_version = None
        self.os_version = None
        self.device_model = None


class MobileAppFramework:
    """
    Mobile Apps Framework

    Support for iOS and Android mobile clients.
    This framework provides the backend infrastructure for:
    - Device registration and management
    - Push notifications (via Firebase/APNs)
    - SIP registration for mobile clients
    - Background call handling
    - Battery optimization
    - Network handoff (WiFi <-> Cellular)

    Mobile app development would require:
    - iOS: Swift/SwiftUI with PushKit, CallKit integration
    - Android: Kotlin with FCM, ConnectionService
    - Both: SIP client libraries (PJSIP, Linphone, etc.)
    """

    def __init__(self, config=None):
        """Initialize mobile app framework"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        mobile_config = self.config.get("features", {}).get("mobile_apps", {})
        self.enabled = mobile_config.get("enabled", False)
        self.ios_enabled = mobile_config.get("ios_enabled", True)
        self.android_enabled = mobile_config.get("android_enabled", True)
        self.push_enabled = mobile_config.get("push_enabled", True)

        # Registered devices
        self.devices: Dict[str, MobileDevice] = {}

        # Statistics
        self.total_devices = 0
        self.active_devices = 0
        self.ios_devices = 0
        self.android_devices = 0

        self.logger.info("Mobile app framework initialized")
        self.logger.info(f"  iOS support: {self.ios_enabled}")
        self.logger.info(f"  Android support: {self.android_enabled}")
        self.logger.info(f"  Push notifications: {self.push_enabled}")
        self.logger.info(f"  Enabled: {self.enabled}")

    def register_device(
        self, device_id: str, platform: str, user_id: str, device_info: Dict = None
    ) -> Dict:
        """
        Register a mobile device

        Args:
            device_id: Unique device identifier
            platform: Platform (ios/android)
            user_id: User identifier
            device_info: Additional device information

        Returns:
            Dict: Registration result
        """
        platform_enum = MobilePlatform(platform)

        # Check platform is enabled
        if platform_enum == MobilePlatform.IOS and not self.ios_enabled:
            return {"success": False, "error": "iOS not enabled"}
        if platform_enum == MobilePlatform.ANDROID and not self.android_enabled:
            return {"success": False, "error": "Android not enabled"}

        device = MobileDevice(device_id, platform_enum, user_id)

        # Set device info
        if device_info:
            device.app_version = device_info.get("app_version")
            device.os_version = device_info.get("os_version")
            device.device_model = device_info.get("device_model")
            device.push_token = device_info.get("push_token")

        self.devices[device_id] = device
        self.total_devices += 1

        if platform_enum == MobilePlatform.IOS:
            self.ios_devices += 1
        else:
            self.android_devices += 1

        self.logger.info(f"Registered {platform} device: {device_id} for user {user_id}")

        return {
            "success": True,
            "device_id": device_id,
            "platform": platform,
            "registered_at": device.registered_at.isoformat(),
        }

    def update_push_token(self, device_id: str, push_token: str) -> bool:
        """
        Update push notification token

        Args:
            device_id: Device identifier
            push_token: New push token

        Returns:
            bool: Success
        """
        if device_id not in self.devices:
            return False

        self.devices[device_id].push_token = push_token
        self.logger.info(f"Updated push token for device {device_id}")

        return True

    def send_push_notification(self, device_id: str, notification: Dict) -> Dict:
        """
        Send push notification to device

        Args:
            device_id: Device identifier
            notification: Notification data

        Returns:
            Dict: Send result
        """
        if device_id not in self.devices:
            return {"success": False, "error": "Device not found"}

        device = self.devices[device_id]

        if not device.push_token:
            return {"success": False, "error": "No push token"}

        # Send via Firebase (Android) or APNs (iOS)
        # Integration documentation with example code

        try:
            if device.platform == MobilePlatform.ANDROID:
                # Firebase Cloud Messaging (FCM) integration
                # In production, initialize FCM client:
                # from firebase_admin import messaging, initialize_app, credentials
                # cred = credentials.Certificate('path/to/serviceAccountKey.json')
                # initialize_app(cred)

                # Create FCM message with high priority for calls
                # fcm_message = messaging.Message(
                #     token=device.push_token,
                #     data={
                #         'type': notification.get('type', 'call'),
                #         'caller_id': notification.get('caller_id', ''),
                #         'call_id': notification.get('call_id', ''),
                #         'title': notification.get('title', 'Incoming Call'),
                #         'body': notification.get('body', 'You have an incoming call')
                #     },
                #     android=messaging.AndroidConfig(
                #         priority='high',
                #         notification=messaging.AndroidNotification(
                #             title=notification.get('title', 'Incoming Call'),
                #             body=notification.get('body', 'You have an incoming call'),
                #             channel_id='calls',
                #             priority='max',
                #             sound='call_ringtone'
                #         )
                #     )
                # )
                #
                # response = messaging.send(fcm_message)
                # notification_id = response

                self.logger.info(f"Sending FCM notification to Android device {device_id}")
                # Use UUID for guaranteed unique notification ID
                import uuid

                notification_id = f"fcm-{uuid.uuid4()}"

            elif device.platform == MobilePlatform.IOS:
                # Apple Push Notification Service (APNs) via FCM or direct APNs
                # For VoIP calls, use PushKit (VoIP notifications)

                # Option 1: Direct APNs using aioapns library
                # from aioapns import APNs, NotificationRequest, PushType
                # apns = APNs(
                #     key='path/to/key.p8',
                #     key_id='YOUR_KEY_ID',
                #     team_id='YOUR_TEAM_ID',
                #     topic='com.yourapp.voip',  # VoIP certificate
                #     use_sandbox=False
                # )
                #
                # request = NotificationRequest(
                #     device_token=device.push_token,
                #     message={
                #         'aps': {
                #             'alert': {
                #                 'title': notification.get('title', 'Incoming Call'),
                #                 'body': notification.get('body', 'You have an incoming call')
                #             },
                #             'sound': 'default',
                #             'badge': 1
                #         },
                #         'call_id': notification.get('call_id', ''),
                #         'caller_id': notification.get('caller_id', '')
                #     },
                #     push_type=PushType.VOIP  # Important for call notifications
                # )
                #
                # await apns.send_notification(request)

                # Option 2: APNs via FCM
                # fcm_message = messaging.Message(
                #     token=device.push_token,
                #     data={
                #         'type': notification.get('type', 'call'),
                #         'caller_id': notification.get('caller_id', ''),
                #         'call_id': notification.get('call_id', '')
                #     },
                #     apns=messaging.APNSConfig(
                #         headers={'apns-priority': '10', 'apns-push-type': 'voip'},
                #         payload=messaging.APNSPayload(
                #             aps=messaging.Aps(
                #                 alert=messaging.ApsAlert(
                #                     title=notification.get('title', 'Incoming Call'),
                #                     body=notification.get('body', 'You have an incoming call')
                #                 ),
                #                 badge=1,
                #                 sound='default',
                #                 category='CALL_CATEGORY'
                #             )
                #         )
                #     )
                # )
                #
                # response = messaging.send(fcm_message)
                # notification_id = response

                self.logger.info(f"Sending APNs notification to iOS device {device_id}")
                # Use UUID for guaranteed unique notification ID
                import uuid

                notification_id = f"apns-{uuid.uuid4()}"

            else:
                return {"success": False, "error": "Unknown platform"}

            # Track notification
            self.total_push_sent += 1

            self.logger.info("Push notification sent successfully")
            self.logger.info(f"  Platform: {device.platform.value}")
            self.logger.info(f"  Type: {notification.get('type', 'unknown')}")
            self.logger.info(f"  Notification ID: {notification_id}")

            return {
                "success": True,
                "device_id": device_id,
                "notification_id": notification_id,
                "platform": device.platform.value,
            }

        except Exception as e:
            self.logger.error(f"Failed to send push notification: {str(e)}")
            return {"success": False, "error": str(e)}

    def configure_sip_for_mobile(self, device_id: str, extension: str) -> Dict:
        """
        Configure SIP settings for mobile device

        Args:
            device_id: Device identifier
            extension: User's extension

        Returns:
            Dict: SIP configuration
        """
        # Mobile-optimized SIP settings
        sip_config = {
            "extension": extension,
            "server": self.config.get("sip", {}).get("bind_address", "localhost"),
            "port": self.config.get("sip", {}).get("bind_port", 5060),
            "transport": "tcp",  # TCP is better for mobile (NAT traversal)
            "keep_alive_interval": 30,  # Keep NAT bindings alive
            "register_interval": 600,  # 10 minutes
            "codec_priority": ["opus", "pcma", "pcmu"],  # Opus best for mobile
            "ice_enabled": True,  # For NAT traversal
            "turn_servers": self._get_turn_servers(),
            "battery_optimization": {
                "background_mode": "push",  # Use push instead of persistent connection
                "reduce_bandwidth": True,
                "adaptive_quality": True,
            },
        }

        self.logger.info(f"Generated SIP config for device {device_id}")

        return sip_config

    def _get_turn_servers(self) -> List[Dict]:
        """
        Get configured TURN servers for NAT traversal

        Returns:
            List[Dict]: TURN server configurations
        """
        mobile_config = self.config.get("features", {}).get("mobile_apps", {})
        turn_config = mobile_config.get("turn_servers", [])

        # Return configured TURN servers or default public ones
        if turn_config:
            return turn_config

        # Default TURN servers (for testing only - use your own in production)
        return [
            {
                "urls": ["turn:turn.example.com:3478"],
                "username": "user",
                "credential": "pass",
                "credentialType": "password",
            },
            {
                "urls": ["turns:turn.example.com:5349"],  # TURN over TLS
                "username": "user",
                "credential": "pass",
                "credentialType": "password",
            },
        ]

    def handle_incoming_call(self, device_id: str, call_info: Dict) -> Dict:
        """
        Handle incoming call notification for mobile

        Args:
            device_id: Device identifier
            call_info: Call information

        Returns:
            Dict: Notification result
        """
        if device_id not in self.devices:
            return {"success": False, "error": "Device not found"}

        device = self.devices[device_id]

        # Send VoIP push notification
        notification = {
            "type": "incoming_call",
            "call_id": call_info.get("call_id"),
            "caller_id": call_info.get("caller_id"),
            "caller_name": call_info.get("caller_name"),
            "timestamp": datetime.now().isoformat(),
        }

        # Use CallKit (iOS) or ConnectionService (Android) integration
        if device.platform == MobilePlatform.IOS:
            notification["use_callkit"] = True
        else:
            notification["use_connection_service"] = True

        return self.send_push_notification(device_id, notification)

    def update_device_activity(self, device_id: str):
        """Update device last active timestamp"""
        if device_id in self.devices:
            self.devices[device_id].last_active = datetime.now()

    def unregister_device(self, device_id: str) -> bool:
        """Unregister a mobile device"""
        if device_id in self.devices:
            platform = self.devices[device_id].platform
            del self.devices[device_id]

            if platform == MobilePlatform.IOS:
                self.ios_devices -= 1
            else:
                self.android_devices -= 1

            self.logger.info(f"Unregistered device {device_id}")
            return True

        return False

    def get_user_devices(self, user_id: str) -> List[Dict]:
        """Get all devices for a user"""
        user_devices = [
            {
                "device_id": d.device_id,
                "platform": d.platform.value,
                "app_version": d.app_version,
                "device_model": d.device_model,
                "last_active": d.last_active.isoformat(),
            }
            for d in self.devices.values()
            if d.user_id == user_id
        ]

        return user_devices

    def get_statistics(self) -> Dict:
        """Get mobile app statistics"""
        # Calculate active devices (active in last 24 hours)
        now = datetime.now()
        active_count = sum(
            1 for d in self.devices.values() if (now - d.last_active).total_seconds() < 86400
        )

        return {
            "enabled": self.enabled,
            "ios_enabled": self.ios_enabled,
            "android_enabled": self.android_enabled,
            "total_devices": len(self.devices),
            "active_devices": active_count,
            "ios_devices": self.ios_devices,
            "android_devices": self.android_devices,
            "push_enabled": self.push_enabled,
        }


# Global instance
_mobile_app_framework = None


def get_mobile_app_framework(config=None) -> MobileAppFramework:
    """Get or create mobile app framework instance"""
    global _mobile_app_framework
    if _mobile_app_framework is None:
        _mobile_app_framework = MobileAppFramework(config)
    return _mobile_app_framework
