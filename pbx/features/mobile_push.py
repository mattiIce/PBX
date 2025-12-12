"""
Mobile Push Notifications
Call and voicemail alerts using FCM (Firebase Cloud Messaging - free)
"""
from datetime import datetime
from typing import Dict, List, Optional
from pbx.utils.logger import get_logger
import json

# Try to import Firebase Admin SDK (free)
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class MobilePushNotifications:
    """Mobile push notification service using Firebase (free)"""
    
    def __init__(self, config=None):
        """Initialize mobile push notifications"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        push_config = self.config.get('features', {}).get('mobile_push', {})
        self.enabled = push_config.get('enabled', False)
        self.fcm_credentials_path = push_config.get('fcm_credentials_path')
        
        # Device registrations
        self.device_tokens = {}  # user_id -> list of device tokens
        self.notification_history = []
        
        # Initialize Firebase
        self.firebase_app = None
        if self.enabled and FIREBASE_AVAILABLE and self.fcm_credentials_path:
            try:
                cred = credentials.Certificate(self.fcm_credentials_path)
                self.firebase_app = firebase_admin.initialize_app(cred)
                self.logger.info("Mobile push notifications initialized with Firebase")
            except Exception as e:
                self.logger.error(f"Failed to initialize Firebase: {e}")
        elif self.enabled and not FIREBASE_AVAILABLE:
            self.logger.warning("Mobile push enabled but firebase-admin not installed")
            self.logger.info("  Install with: pip install firebase-admin")
    
    def register_device(self, user_id: str, device_token: str, 
                       platform: str = 'unknown') -> bool:
        """
        Register a device for push notifications
        
        Args:
            user_id: User identifier
            device_token: FCM device token
            platform: Platform (ios, android)
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        if user_id not in self.device_tokens:
            self.device_tokens[user_id] = []
        
        # Check if already registered
        for token_info in self.device_tokens[user_id]:
            if token_info['token'] == device_token:
                # Update last seen
                token_info['last_seen'] = datetime.now()
                return True
        
        # Add new device
        self.device_tokens[user_id].append({
            'token': device_token,
            'platform': platform,
            'registered_at': datetime.now(),
            'last_seen': datetime.now()
        })
        
        self.logger.info(f"Registered device for user {user_id} ({platform})")
        return True
    
    def unregister_device(self, user_id: str, device_token: str) -> bool:
        """Unregister a device"""
        if user_id not in self.device_tokens:
            return False
        
        original_count = len(self.device_tokens[user_id])
        self.device_tokens[user_id] = [
            t for t in self.device_tokens[user_id]
            if t['token'] != device_token
        ]
        
        removed = original_count - len(self.device_tokens[user_id])
        if removed > 0:
            self.logger.info(f"Unregistered device for user {user_id}")
            return True
        
        return False
    
    def send_call_notification(self, user_id: str, caller_id: str, 
                              caller_name: Optional[str] = None) -> Dict:
        """
        Send incoming call notification
        
        Args:
            user_id: User receiving call
            caller_id: Caller's number
            caller_name: Caller's name
            
        Returns:
            Notification result
        """
        if not self.enabled or not self.firebase_app:
            return {'error': 'Push notifications not available'}
        
        if user_id not in self.device_tokens:
            return {'error': 'No devices registered for user'}
        
        title = "Incoming Call"
        body = f"Call from {caller_name or caller_id}"
        
        result = self._send_notification(
            user_id,
            title,
            body,
            data={
                'type': 'incoming_call',
                'caller_id': caller_id,
                'caller_name': caller_name or '',
                'timestamp': datetime.now().isoformat()
            }
        )
        
        self.logger.info(f"Sent call notification to {user_id} from {caller_id}")
        return result
    
    def send_voicemail_notification(self, user_id: str, message_id: str,
                                   caller_id: str, duration: int) -> Dict:
        """Send new voicemail notification"""
        if not self.enabled or not self.firebase_app:
            return {'error': 'Push notifications not available'}
        
        if user_id not in self.device_tokens:
            return {'error': 'No devices registered for user'}
        
        title = "New Voicemail"
        body = f"New message from {caller_id} ({duration}s)"
        
        result = self._send_notification(
            user_id,
            title,
            body,
            data={
                'type': 'new_voicemail',
                'message_id': message_id,
                'caller_id': caller_id,
                'duration': str(duration),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        self.logger.info(f"Sent voicemail notification to {user_id}")
        return result
    
    def send_missed_call_notification(self, user_id: str, caller_id: str,
                                     call_time: Optional[datetime] = None) -> Dict:
        """Send missed call notification"""
        if not self.enabled or not self.firebase_app:
            return {'error': 'Push notifications not available'}
        
        if user_id not in self.device_tokens:
            return {'error': 'No devices registered for user'}
        
        title = "Missed Call"
        body = f"Missed call from {caller_id}"
        
        result = self._send_notification(
            user_id,
            title,
            body,
            data={
                'type': 'missed_call',
                'caller_id': caller_id,
                'call_time': (call_time or datetime.now()).isoformat()
            }
        )
        
        self.logger.info(f"Sent missed call notification to {user_id}")
        return result
    
    def _send_notification(self, user_id: str, title: str, body: str, 
                          data: Optional[Dict] = None) -> Dict:
        """Send push notification to all user's devices"""
        if not FIREBASE_AVAILABLE or not self.firebase_app:
            # Stub mode - log notification
            self.logger.debug(f"Would send notification to {user_id}: {title}")
            return {'success': False, 'stub_mode': True}
        
        tokens = [t['token'] for t in self.device_tokens.get(user_id, [])]
        if not tokens:
            return {'error': 'No device tokens'}
        
        try:
            # Create notification message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                tokens=tokens
            )
            
            # Send to all devices
            response = messaging.send_multicast(message)
            
            # Log history
            self.notification_history.append({
                'user_id': user_id,
                'title': title,
                'body': body,
                'sent_at': datetime.now(),
                'success_count': response.success_count,
                'failure_count': response.failure_count
            })
            
            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count
            }
            
        except Exception as e:
            self.logger.error(f"Error sending push notification: {e}")
            return {'error': str(e)}
    
    def get_user_devices(self, user_id: str) -> List[Dict]:
        """Get list of registered devices for a user"""
        devices = self.device_tokens.get(user_id, [])
        return [
            {
                'platform': d['platform'],
                'registered_at': d['registered_at'].isoformat(),
                'last_seen': d['last_seen'].isoformat()
            }
            for d in devices
        ]
    
    def cleanup_stale_devices(self, days: int = 90):
        """Remove devices not seen in X days"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        removed_count = 0
        for user_id in list(self.device_tokens.keys()):
            original_count = len(self.device_tokens[user_id])
            self.device_tokens[user_id] = [
                t for t in self.device_tokens[user_id]
                if t['last_seen'] > cutoff
            ]
            removed_count += original_count - len(self.device_tokens[user_id])
            
            # Remove user if no devices left
            if not self.device_tokens[user_id]:
                del self.device_tokens[user_id]
        
        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} stale devices")
    
    def get_statistics(self) -> Dict:
        """Get push notification statistics"""
        total_devices = sum(len(tokens) for tokens in self.device_tokens.values())
        recent_notifications = len([
            n for n in self.notification_history
            if (datetime.now() - n['sent_at']).total_seconds() < 86400
        ])
        
        return {
            'enabled': self.enabled,
            'firebase_available': FIREBASE_AVAILABLE,
            'total_users': len(self.device_tokens),
            'total_devices': total_devices,
            'notifications_24h': recent_notifications
        }
