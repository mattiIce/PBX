"""
Presence and status system
Allows users to see availability of other extensions in real-time
"""

from datetime import UTC, datetime
from enum import Enum

from pbx.utils.logger import get_logger


class PresenceStatus(Enum):
    """User presence status"""

    AVAILABLE = "available"
    BUSY = "busy"
    AWAY = "away"
    DO_NOT_DISTURB = "do_not_disturb"
    IN_CALL = "in_call"
    IN_MEETING = "in_meeting"
    OFFLINE = "offline"


class UserPresence:
    """Represents presence information for a user"""

    def __init__(self, extension, name=""):
        """
        Initialize user presence

        Args:
            extension: Extension number
            name: User name
        """
        self.extension = extension
        self.name = name
        self.status = PresenceStatus.OFFLINE
        self.custom_message = ""
        self.last_activity = datetime.now(UTC)
        self.last_status_change = datetime.now(UTC)
        self.in_call = False
        self.call_id = None

    def set_status(self, status, custom_message=""):
        """
        set presence status

        Args:
            status: PresenceStatus enum value
            custom_message: Optional custom status message
        """
        self.status = status
        self.custom_message = custom_message
        self.last_status_change = datetime.now(UTC)
        self.last_activity = datetime.now(UTC)

    def set_in_call(self, call_id):
        """
        Mark user as in call

        Args:
            call_id: Call identifier
        """
        self.in_call = True
        self.call_id = call_id
        self.status = PresenceStatus.IN_CALL
        self.last_activity = datetime.now(UTC)

    def clear_call(self):
        """Mark user as not in call"""
        self.in_call = False
        self.call_id = None
        if self.status == PresenceStatus.IN_CALL:
            self.status = PresenceStatus.AVAILABLE

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(UTC)

    def get_idle_time(self):
        """Get time since last activity in seconds"""
        return (datetime.now(UTC) - self.last_activity).total_seconds()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "extension": self.extension,
            "name": self.name,
            "status": self.status.value,
            "custom_message": self.custom_message,
            "in_call": self.in_call,
            "last_activity": self.last_activity.isoformat(),
            "idle_time": self.get_idle_time(),
        }


class PresenceSystem:
    """Manages presence for all users"""

    def __init__(self, auto_away_timeout=300, auto_offline_timeout=1800):
        """
        Initialize presence system

        Args:
            auto_away_timeout: Seconds of inactivity before auto-away (5 min)
            auto_offline_timeout: Seconds of inactivity before auto-offline (30 min)
        """
        self.users = {}
        self.subscribers = {}  # extension -> list of subscribers
        self.logger = get_logger()
        self.auto_away_timeout = auto_away_timeout
        self.auto_offline_timeout = auto_offline_timeout

    def register_user(self, extension, name=""):
        """
        Register user for presence

        Args:
            extension: Extension number
            name: User name

        Returns:
            UserPresence object
        """
        if extension not in self.users:
            user = UserPresence(extension, name)
            user.set_status(PresenceStatus.AVAILABLE)
            self.users[extension] = user
            self.logger.info(f"Registered presence for {extension}")
            self._notify_subscribers(extension)
        return self.users[extension]

    def unregister_user(self, extension):
        """
        Unregister user

        Args:
            extension: Extension number
        """
        user = self.users.get(extension)
        if user:
            user.set_status(PresenceStatus.OFFLINE)
            self._notify_subscribers(extension)

    def set_status(self, extension, status, custom_message=""):
        """
        set user status

        Args:
            extension: Extension number
            status: PresenceStatus value
            custom_message: Optional message

        Returns:
            True if status was set
        """
        user = self.users.get(extension)
        if user:
            user.set_status(status, custom_message)
            self._notify_subscribers(extension)
            self.logger.debug(f"set status for {extension}: {status.value}")
            return True
        return False

    def set_in_call(self, extension, call_id):
        """
        Mark user as in call

        Args:
            extension: Extension number
            call_id: Call identifier
        """
        user = self.users.get(extension)
        if user:
            user.set_in_call(call_id)
            self._notify_subscribers(extension)

    def clear_call(self, extension):
        """
        Clear in-call status

        Args:
            extension: Extension number
        """
        user = self.users.get(extension)
        if user:
            user.clear_call()
            self._notify_subscribers(extension)

    def update_activity(self, extension):
        """
        Update user activity

        Args:
            extension: Extension number
        """
        user = self.users.get(extension)
        if user:
            user.update_activity()

    def get_status(self, extension):
        """
        Get user presence status

        Args:
            extension: Extension number

        Returns:
            UserPresence object or None
        """
        return self.users.get(extension)

    def subscribe(self, subscriber_extension, watched_extension):
        """
        Subscribe to presence updates

        Args:
            subscriber_extension: Extension subscribing
            watched_extension: Extension to watch
        """
        if watched_extension not in self.subscribers:
            self.subscribers[watched_extension] = []

        if subscriber_extension not in self.subscribers[watched_extension]:
            self.subscribers[watched_extension].append(subscriber_extension)
            self.logger.debug(f"{subscriber_extension} subscribed to {watched_extension}")

    def unsubscribe(self, subscriber_extension, watched_extension):
        """
        Unsubscribe from presence updates

        Args:
            subscriber_extension: Extension unsubscribing
            watched_extension: Extension being watched
        """
        if watched_extension in self.subscribers:
            if subscriber_extension in self.subscribers[watched_extension]:
                self.subscribers[watched_extension].remove(subscriber_extension)

    def _notify_subscribers(self, extension):
        """
        Notify subscribers of presence change

        Args:
            extension: Extension that changed
        """
        subscribers = self.subscribers.get(extension, [])
        if subscribers:
            user = self.users.get(extension)
            if user:
                self.logger.debug(
                    f"Notifying {len(subscribers)} subscribers of {extension} presence change"
                )
                # In a real implementation, send presence update messages

    def check_auto_status(self):
        """Check and update auto-away/offline status based on inactivity"""
        for user in self.users.values():
            if user.status == PresenceStatus.OFFLINE:
                continue

            idle_time = user.get_idle_time()

            # Auto-offline after extended inactivity
            if idle_time > self.auto_offline_timeout:
                if user.status != PresenceStatus.OFFLINE:
                    user.set_status(PresenceStatus.OFFLINE)
                    self._notify_subscribers(user.extension)

            # Auto-away after shorter inactivity
            elif idle_time > self.auto_away_timeout:
                if user.status == PresenceStatus.AVAILABLE:
                    user.set_status(PresenceStatus.AWAY, "Auto-away")
                    self._notify_subscribers(user.extension)

    def get_all_status(self):
        """
        Get status of all users

        Returns:
            list of presence dictionaries
        """
        return [user.to_dict() for user in self.users.values()]

    def get_available_users(self):
        """
        Get list of available users

        Returns:
            list of UserPresence objects
        """
        return [u for u in self.users.values() if u.status == PresenceStatus.AVAILABLE]
