"""
Mobile Push Notifications
Call and voicemail alerts using FCM (Firebase Cloud Messaging - free)
"""

import json
import sqlite3
from datetime import UTC, datetime

from pbx.utils.logger import get_logger
from typing import Any

# Try to import Firebase Admin SDK (free)
try:
    import firebase_admin
    from firebase_admin import credentials, messaging

    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class MobilePushNotifications:
    """Mobile push notification service using Firebase (free)"""

    def __init__(self, config: Any | None =None, database: Any | None =None) -> None:
        """Initialize mobile push notifications"""
        self.logger = get_logger()
        self.config = config or {}
        self.database = database

        # Configuration
        push_config = self.config.get("features", {}).get("mobile_push", {})
        self.enabled = push_config.get("enabled", False)
        self.fcm_credentials_path = push_config.get("fcm_credentials_path")

        # Device registrations
        self.device_tokens = {}  # user_id -> list of device tokens
        self.notification_history = []

        # Initialize database schema if database is available
        if self.database and self.database.enabled:
            self._initialize_schema()
            self._load_devices_from_database()

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

    def _initialize_schema(self) -> None:
        """Initialize database schema for mobile push notifications"""
        if not self.database or not self.database.enabled:
            return

        # Device registrations table
        device_table = """
        CREATE TABLE IF NOT EXISTS mobile_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id VARCHAR(50) NOT NULL,
            device_token VARCHAR(255) NOT NULL UNIQUE,
            platform VARCHAR(20) NOT NULL,
            registered_at TIMESTAMP NOT NULL,
            last_seen TIMESTAMP NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        if self.database.db_type == "postgresql":
            device_table = """
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
            )
            """

        # Notification history table
        if self.database.db_type == "postgresql":
            notification_table = """
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
            )
            """
        else:
            notification_table = """
            CREATE TABLE IF NOT EXISTS push_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(50) NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                title VARCHAR(200),
                body TEXT,
                data TEXT,
                sent_at TIMESTAMP NOT NULL,
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

        try:
            cursor = self.database.connection.cursor()
            cursor.execute(device_table)
            cursor.execute(notification_table)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mobile_devices_user_id
                ON mobile_devices(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_push_notifications_user_id
                ON push_notifications(user_id)
            """)

            self.database.connection.commit()
            cursor.close()
            self.logger.debug("Mobile push notifications database schema initialized")
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing mobile push schema: {e}")

    def _load_devices_from_database(self) -> None:
        """Load device registrations from database"""
        if not self.database or not self.database.enabled:
            return

        try:
            cursor = self.database.connection.cursor()

            # Handle boolean enabled field for both database types
            if self.database.db_type == "postgresql":
                cursor.execute("""
                    SELECT user_id, device_token, platform, registered_at, last_seen
                    FROM mobile_devices
                    WHERE enabled = TRUE
                    ORDER BY last_seen DESC
                """)
            else:
                cursor.execute("""
                    SELECT user_id, device_token, platform, registered_at, last_seen
                    FROM mobile_devices
                    WHERE enabled = 1
                    ORDER BY last_seen DESC
                """)

            rows = cursor.fetchall()
            for row in rows:
                user_id, device_token, platform, registered_at, last_seen = row

                if user_id not in self.device_tokens:
                    self.device_tokens[user_id] = []

                self.device_tokens[user_id].append(
                    {
                        "token": device_token,
                        "platform": platform,
                        "registered_at": registered_at,
                        "last_seen": last_seen,
                    }
                )

            cursor.close()
            if rows:
                self.logger.info(f"Loaded {len(rows)} mobile devices from database")
        except sqlite3.Error as e:
            self.logger.error(f"Error loading mobile devices from database: {e}")

    def _save_device_to_database(self, user_id: str, device_token: str, platform: str) -> bool:
        """Save device registration to database"""
        if not self.database or not self.database.enabled:
            return False

        try:
            cursor = self.database.connection.cursor()
            now = datetime.now(UTC)

            if self.database.db_type == "postgresql":
                cursor.execute(
                    """
                    INSERT INTO mobile_devices (user_id, device_token, platform, registered_at, last_seen, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (device_token) DO UPDATE SET
                        last_seen = EXCLUDED.last_seen,
                        updated_at = EXCLUDED.updated_at,
                        enabled = TRUE
                """,
                    (user_id, device_token, platform, now, now, now),
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO mobile_devices (user_id, device_token, platform, registered_at, last_seen, enabled, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                    (user_id, device_token, platform, now, now, now),
                )

            self.database.connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error saving device to database: {e}")
            return False

    def _remove_device_from_database(self, user_id: str, device_token: str) -> bool:
        """Remove device from database (soft delete)"""
        if not self.database or not self.database.enabled:
            return False

        try:
            cursor = self.database.connection.cursor()

            if self.database.db_type == "postgresql":
                cursor.execute(
                    """
                    UPDATE mobile_devices
                    SET enabled = FALSE, updated_at = %s
                    WHERE user_id = %s AND device_token = %s
                """,
                    (datetime.now(UTC), user_id, device_token),
                )
            else:
                cursor.execute(
                    """
                    UPDATE mobile_devices
                    SET enabled = 0, updated_at = ?
                    WHERE user_id = ? AND device_token = ?
                """,
                    (datetime.now(UTC), user_id, device_token),
                )

            self.database.connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error removing device from database: {e}")
            return False

    def _save_notification_to_database(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        body: str,
        data: dict,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Save notification history to database"""
        if not self.database or not self.database.enabled:
            return

        try:
            cursor = self.database.connection.cursor()
            data_json = json.dumps(data) if data else None

            if self.database.db_type == "postgresql":
                cursor.execute(
                    """
                    INSERT INTO push_notifications (user_id, notification_type, title, body, data, sent_at, success, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        user_id,
                        notification_type,
                        title,
                        body,
                        data_json,
                        datetime.now(UTC),
                        success,
                        error_message,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO push_notifications (user_id, notification_type, title, body, data, sent_at, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        notification_type,
                        title,
                        body,
                        data_json,
                        datetime.now(UTC),
                        1 if success else 0,
                        error_message,
                    ),
                )

            self.database.connection.commit()
            cursor.close()
        except (ValueError, json.JSONDecodeError, sqlite3.Error) as e:
            self.logger.error(f"Error saving notification to database: {e}")

    def register_device(self, user_id: str, device_token: str, platform: str = "unknown") -> bool:
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
            if token_info["token"] == device_token:
                # Update last seen
                token_info["last_seen"] = datetime.now(UTC)
                return True

        # Add new device
        self.device_tokens[user_id].append(
            {
                "token": device_token,
                "platform": platform,
                "registered_at": datetime.now(UTC),
                "last_seen": datetime.now(UTC),
            }
        )

        # Save to database
        self._save_device_to_database(user_id, device_token, platform)

        self.logger.info(f"Registered device for user {user_id} ({platform})")
        return True

    def unregister_device(self, user_id: str, device_token: str) -> bool:
        """Unregister a device"""
        if user_id not in self.device_tokens:
            return False

        original_count = len(self.device_tokens[user_id])
        self.device_tokens[user_id] = [
            t for t in self.device_tokens[user_id] if t["token"] != device_token
        ]

        removed = original_count - len(self.device_tokens[user_id])
        if removed > 0:
            # Remove from database
            self._remove_device_from_database(user_id, device_token)

            self.logger.info(f"Unregistered device for user {user_id}")
            return True

        return False

    def send_call_notification(
        self, user_id: str, caller_id: str, caller_name: str | None = None
    ) -> dict:
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
            return {"error": "Push notifications not available"}

        if user_id not in self.device_tokens:
            return {"error": "No devices registered for user"}

        title = "Incoming Call"
        body = f"Call from {caller_name or caller_id}"

        result = self._send_notification(
            user_id,
            title,
            body,
            data={
                "type": "incoming_call",
                "caller_id": caller_id,
                "caller_name": caller_name or "",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        self.logger.info(f"Sent call notification to {user_id} from {caller_id}")
        return result

    def send_voicemail_notification(
        self, user_id: str, message_id: str, caller_id: str, duration: int
    ) -> dict:
        """Send new voicemail notification"""
        if not self.enabled or not self.firebase_app:
            return {"error": "Push notifications not available"}

        if user_id not in self.device_tokens:
            return {"error": "No devices registered for user"}

        title = "New Voicemail"
        body = f"New message from {caller_id} ({duration}s)"

        result = self._send_notification(
            user_id,
            title,
            body,
            data={
                "type": "new_voicemail",
                "message_id": message_id,
                "caller_id": caller_id,
                "duration": str(duration),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        self.logger.info(f"Sent voicemail notification to {user_id}")
        return result

    def send_missed_call_notification(
        self, user_id: str, caller_id: str, call_time: datetime | None = None
    ) -> dict:
        """Send missed call notification"""
        if not self.enabled or not self.firebase_app:
            return {"error": "Push notifications not available"}

        if user_id not in self.device_tokens:
            return {"error": "No devices registered for user"}

        title = "Missed Call"
        body = f"Missed call from {caller_id}"

        result = self._send_notification(
            user_id,
            title,
            body,
            data={
                "type": "missed_call",
                "caller_id": caller_id,
                "call_time": (call_time or datetime.now(UTC)).isoformat(),
            },
        )

        self.logger.info(f"Sent missed call notification to {user_id}")
        return result

    def _send_notification(
        self, user_id: str, title: str, body: str, data: dict | None = None
    ) -> dict:
        """Send push notification to all user's devices"""
        if not FIREBASE_AVAILABLE or not self.firebase_app:
            # Stub mode - log notification
            self.logger.debug(f"Would send notification to {user_id}: {title}")
            return {"success": False, "stub_mode": True}

        tokens = [t["token"] for t in self.device_tokens.get(user_id, [])]
        if not tokens:
            return {"error": "No device tokens"}

        try:
            # Create notification message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                tokens=tokens,
            )

            # Send to all devices
            response = messaging.send_multicast(message)

            # Log history
            self.notification_history.append(
                {
                    "user_id": user_id,
                    "title": title,
                    "body": body,
                    "sent_at": datetime.now(UTC),
                    "success_count": response.success_count,
                    "failure_count": response.failure_count,
                }
            )

            # Save to database
            notification_type = data.get("type", "unknown") if data else "unknown"
            self._save_notification_to_database(user_id, notification_type, title, body, data, True)

            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
            }

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error sending push notification: {e}")

            # Save error to database
            notification_type = data.get("type", "unknown") if data else "unknown"
            self._save_notification_to_database(
                user_id, notification_type, title, body, data, False, str(e)
            )

            return {"error": str(e)}

    def get_user_devices(self, user_id: str) -> list[dict]:
        """Get list of registered devices for a user"""
        devices = self.device_tokens.get(user_id, [])
        return [
            {
                "platform": d["platform"],
                "registered_at": d["registered_at"].isoformat(),
                "last_seen": d["last_seen"].isoformat(),
            }
            for d in devices
        ]

    def cleanup_stale_devices(self, days: int = 90) -> None:
        """Remove devices not seen in X days"""
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(days=days)

        removed_count = 0
        for user_id in list(self.device_tokens.keys()):
            original_count = len(self.device_tokens[user_id])
            self.device_tokens[user_id] = [
                t for t in self.device_tokens[user_id] if t["last_seen"] > cutoff
            ]
            removed_count += original_count - len(self.device_tokens[user_id])

            # Remove user if no devices left
            if not self.device_tokens[user_id]:
                del self.device_tokens[user_id]

        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} stale devices")

    def get_statistics(self) -> dict:
        """Get push notification statistics"""
        total_devices = sum(len(tokens) for tokens in self.device_tokens.values())
        recent_notifications = len(
            [
                n
                for n in self.notification_history
                if (datetime.now(UTC) - n["sent_at"]).total_seconds() < 86400
            ]
        )

        return {
            "enabled": self.enabled,
            "firebase_available": FIREBASE_AVAILABLE,
            "total_users": len(self.device_tokens),
            "total_devices": total_devices,
            "notifications_24h": recent_notifications,
        }

    def send_test_notification(self, user_id: str) -> dict:
        """
        Send a test push notification to a user

        Args:
            user_id: User to send test notification to

        Returns:
            Notification result
        """
        return self._send_notification(
            user_id,
            "Test Notification",
            "This is a test push notification from PBX Admin Panel",
            {"type": "test", "timestamp": datetime.now(UTC).isoformat()},
        )
