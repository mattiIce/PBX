"""
Do Not Disturb (DND) Scheduling System
Automatically sets DND status based on calendar events and scheduled rules
"""

import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from pbx.features.presence import PresenceStatus
from pbx.utils.logger import get_logger


class DNDRule:
    """Represents a DND scheduling rule"""

    def __init__(self, rule_id: str, extension: str, rule_type: str, config: dict) -> None:
        """
        Initialize DND rule

        Args:
            rule_id: Unique rule identifier
            extension: Extension number
            rule_type: type of rule (calendar, time_based, manual)
            config: Rule configuration
        """
        self.rule_id = rule_id
        self.extension = extension
        self.rule_type = rule_type
        self.config = config
        self.enabled = config.get("enabled", True)
        # Higher priority rules override lower
        self.priority = config.get("priority", 0)

    def should_apply(self, current_time: datetime | None = None) -> bool:
        """
        Check if rule should currently apply

        Args:
            current_time: Current time (defaults to now)

        Returns:
            True if rule should set DND
        """
        if not self.enabled:
            return False

        if current_time is None:
            current_time = datetime.now(UTC)

        if self.rule_type == "time_based":
            return self._check_time_based(current_time)
        if self.rule_type == "calendar":
            # Calendar rules are checked separately by calendar monitor
            return False

        return False

    def _check_time_based(self, current_time: datetime) -> bool:
        """Check if time-based rule applies"""
        # Check day of week
        days = self.config.get("days", [])
        if days and current_time.strftime("%A").lower() not in [d.lower() for d in days]:
            return False

        # Check time range
        start_time = self.config.get("start_time")  # Format: "HH:MM"
        end_time = self.config.get("end_time")  # Format: "HH:MM"

        if start_time and end_time:
            current_time_str = current_time.strftime("%H:%M")

            # Handle overnight ranges (e.g., 22:00 to 06:00)
            if start_time <= end_time:
                return start_time <= current_time_str <= end_time
            return current_time_str >= start_time or current_time_str <= end_time

        return False

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "rule_id": self.rule_id,
            "extension": self.extension,
            "rule_type": self.rule_type,
            "enabled": self.enabled,
            "priority": self.priority,
            "config": self.config,
        }


class CalendarMonitor:
    """Monitors calendar events and triggers DND"""

    def __init__(self, outlook_integration: Any | None = None, check_interval: int = 60) -> None:
        """
        Initialize calendar monitor

        Args:
            outlook_integration: Outlook integration instance
            check_interval: How often to check calendar (seconds)
        """
        self.logger = get_logger()
        self.outlook = outlook_integration
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.extension_email_map = {}  # extension -> email address
        self.active_meetings = {}  # extension -> meeting_info

    def register_user(self, extension: str, email: str) -> None:
        """
        Register user for calendar monitoring

        Args:
            extension: Extension number
            email: User's email address
        """
        self.extension_email_map[extension] = email
        self.logger.info(f"Registered calendar monitoring for {extension} ({email})")

    def unregister_user(self, extension: str) -> None:
        """
        Unregister user from calendar monitoring

        Args:
            extension: Extension number
        """
        if extension in self.extension_email_map:
            del self.extension_email_map[extension]
        if extension in self.active_meetings:
            del self.active_meetings[extension]

    def start(self) -> None:
        """Start calendar monitoring thread"""
        if self.running:
            return

        if not self.outlook or not self.outlook.enabled:
            self.logger.warning(
                "Calendar monitoring cannot start: Outlook integration not available"
            )
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info("Calendar monitoring started")

    def stop(self) -> None:
        """Stop calendar monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Calendar monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_all_calendars()
            except Exception as e:
                self.logger.error(f"Error in calendar monitoring: {e}")

            # Sleep in small increments to allow quick shutdown
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _check_all_calendars(self) -> None:
        """Check calendars for all registered users"""
        now = datetime.now(UTC)

        for extension, email in self.extension_email_map.items():
            try:
                # Get events for next 15 minutes
                start_time = now.isoformat()
                end_time = (now + timedelta(minutes=15)).isoformat()

                events = self.outlook.get_calendar_events(email, start_time, end_time)

                # Check if user is currently in a meeting
                in_meeting = False
                current_meeting = None

                for event in events:
                    event_start = datetime.fromisoformat(event["start"])
                    event_end = datetime.fromisoformat(event["end"])

                    # Check if event is happening now
                    if event_start <= now <= event_end:
                        # Check if user accepted the meeting
                        show_as = event.get("showAs", "busy").lower()
                        response_status = (
                            event.get("responseStatus", {}).get("response", "none").lower()
                        )

                        # set DND if busy and accepted
                        if show_as in ["busy", "outofoffice", "tentative"] and response_status in [
                            "accepted",
                            "organizer",
                            "tentativelyaccepted",
                        ]:
                            in_meeting = True
                            current_meeting = {
                                "subject": event.get("subject", "Meeting"),
                                "start": event_start.isoformat(),
                                "end": event_end.isoformat(),
                                "show_as": show_as,
                            }
                            break

                # Update active meetings tracking
                previous_state = extension in self.active_meetings

                if in_meeting and not previous_state:
                    # User entered meeting
                    self.active_meetings[extension] = current_meeting
                    self.logger.info(
                        f"Extension {extension} entered meeting: {current_meeting['subject']}"
                    )
                elif not in_meeting and previous_state:
                    # User left meeting
                    del self.active_meetings[extension]
                    self.logger.info(f"Extension {extension} left meeting")
                elif in_meeting:
                    # Update meeting info
                    self.active_meetings[extension] = current_meeting

            except (KeyError, TypeError, ValueError) as e:
                self.logger.error(f"Error checking calendar for {extension}: {e}")

    def is_in_meeting(self, extension: str) -> tuple[bool, dict | None]:
        """
        Check if user is currently in a meeting

        Args:
            extension: Extension number

        Returns:
            tuple of (in_meeting, meeting_info)
        """
        meeting = self.active_meetings.get(extension)
        return (meeting is not None, meeting)


class DNDScheduler:
    """
    Manages automatic DND scheduling based on calendar and time-based rules
    """

    def __init__(
        self,
        presence_system: Any | None = None,
        outlook_integration: Any | None = None,
        config: dict | None = None,
    ) -> None:
        """
        Initialize DND scheduler

        Args:
            presence_system: PresenceSystem instance
            outlook_integration: OutlookIntegration instance
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.presence_system = presence_system
        self.outlook = outlook_integration
        self.config = config or {}

        # Configuration
        self.enabled = self._get_config("features.dnd_scheduling.enabled", False)
        self.calendar_dnd_enabled = self._get_config("features.dnd_scheduling.calendar_dnd", True)
        self.check_interval = self._get_config("features.dnd_scheduling.check_interval", 60)

        # Storage
        self.rules = {}  # extension -> list of DNDRule
        self.manual_overrides = {}  # extension -> (status, until_time)
        # extension -> PresenceStatus (for restoration)
        self.previous_statuses = {}

        # Calendar monitor
        self.calendar_monitor = CalendarMonitor(
            outlook_integration=outlook_integration, check_interval=self.check_interval
        )

        # Monitoring thread
        self.running = False
        self.thread = None

        if self.enabled:
            self.logger.info("DND Scheduler initialized")

    def _get_config(self, key: str, default: Any | None = None) -> Any:
        """
        Get config value supporting both dot notation and nested dicts

        Args:
            key: Config key (e.g., 'features.dnd_scheduling.enabled')
            default: Default value if not found

        Returns:
            Config value or default
        """
        # Try dot notation first (Config object)
        if hasattr(self.config, "get") and "." in key:
            value = self.config.get(key, None)
            if value is not None:
                return value

        # Try nested dict navigation
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value if value is not None else default

    def start(self) -> None:
        """Start DND scheduler"""
        if not self.enabled:
            self.logger.info("DND Scheduler is disabled")
            return

        if self.running:
            return

        # Start calendar monitor
        if self.calendar_dnd_enabled and self.outlook:
            self.calendar_monitor.start()

        # Start rule checking thread
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()

        self.logger.info("DND Scheduler started")

    def stop(self) -> None:
        """Stop DND scheduler"""
        self.running = False

        # Stop calendar monitor
        self.calendar_monitor.stop()

        # Stop monitoring thread
        if self.thread:
            self.thread.join(timeout=5)

        self.logger.info("DND Scheduler stopped")

    def add_rule(self, extension: str, rule_type: str, config: dict) -> str:
        """
        Add DND rule for extension

        Args:
            extension: Extension number
            rule_type: type of rule (calendar, time_based)
            config: Rule configuration

        Returns:
            Rule ID
        """
        import uuid

        rule_id = str(uuid.uuid4())

        rule = DNDRule(rule_id, extension, rule_type, config)

        if extension not in self.rules:
            self.rules[extension] = []

        self.rules[extension].append(rule)
        self.logger.info(f"Added DND rule {rule_id} for extension {extension}")

        return rule_id

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove DND rule

        Args:
            rule_id: Rule identifier

        Returns:
            True if rule was removed
        """
        for rules in self.rules.values():
            for i, rule in enumerate(rules):
                if rule.rule_id == rule_id:
                    del rules[i]
                    self.logger.info(f"Removed DND rule {rule_id}")
                    return True
        return False

    def get_rules(self, extension: str) -> list[dict]:
        """
        Get all rules for extension

        Args:
            extension: Extension number

        Returns:
            list of rule dictionaries
        """
        if extension not in self.rules:
            return []

        return [rule.to_dict() for rule in self.rules[extension]]

    def register_calendar_user(self, extension: str, email: str) -> None:
        """
        Register user for calendar-based DND

        Args:
            extension: Extension number
            email: User's email address
        """
        if self.calendar_dnd_enabled:
            self.calendar_monitor.register_user(extension, email)

    def unregister_calendar_user(self, extension: str) -> None:
        """
        Unregister user from calendar-based DND

        Args:
            extension: Extension number
        """
        self.calendar_monitor.unregister_user(extension)

    def set_manual_override(
        self, extension: str, status: PresenceStatus, duration_minutes: int | None = None
    ) -> None:
        """
        Manually override DND scheduling

        Args:
            extension: Extension number
            status: Presence status to set
            duration_minutes: How long override lasts (None = indefinite)
        """
        until_time = None
        if duration_minutes:
            until_time = datetime.now(UTC) + timedelta(minutes=duration_minutes)

        self.manual_overrides[extension] = (status, until_time)

        # Apply override immediately
        if self.presence_system:
            self.presence_system.set_status(extension, status)

        self.logger.info(f"Manual DND override for {extension}: {status.value} until {until_time}")

    def clear_manual_override(self, extension: str) -> None:
        """
        Clear manual override

        Args:
            extension: Extension number
        """
        if extension in self.manual_overrides:
            del self.manual_overrides[extension]
            self.logger.info(f"Cleared manual override for {extension}")

    def _monitoring_loop(self) -> None:
        """Main monitoring loop for rule checking"""
        while self.running:
            try:
                self._check_all_rules()
            except Exception as e:
                self.logger.error(f"Error in DND monitoring: {e}")

            # Sleep in small increments
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _check_manual_override(self, extension: str, now: datetime) -> bool:
        """Check if extension has active manual override. Returns True if override is active."""
        if extension not in self.manual_overrides:
            return False

        _status, until_time = self.manual_overrides[extension]
        if until_time and now > until_time:
            # Override expired
            del self.manual_overrides[extension]
            return False
        # Override still active
        return True

    def _should_apply_dnd(self, extension: str, now: datetime) -> bool:
        """Determine if DND should be active for extension"""
        should_dnd = False
        highest_priority = -1

        # Check time-based rules
        if extension in self.rules:
            for rule in self.rules[extension]:
                if rule.should_apply(now) and rule.priority > highest_priority:
                    should_dnd = True
                    highest_priority = rule.priority

        # Check calendar-based DND
        if self.calendar_dnd_enabled:
            in_meeting, _meeting_info = self.calendar_monitor.is_in_meeting(extension)
            if in_meeting:
                # Calendar DND has high priority
                should_dnd = True

        return should_dnd

    def _apply_dnd_status(self, extension: str, current_status: str) -> None:
        """Apply DND or IN_MEETING status"""
        # Save previous status for restoration
        if extension not in self.previous_statuses:
            self.previous_statuses[extension] = current_status

        # set DND or IN_MEETING
        if self.calendar_dnd_enabled and self.calendar_monitor.is_in_meeting(extension)[0]:
            self.presence_system.set_status(
                extension, PresenceStatus.IN_MEETING, "In calendar meeting"
            )
        else:
            self.presence_system.set_status(
                extension, PresenceStatus.DO_NOT_DISTURB, "Auto-DND (scheduled)"
            )

    def _remove_dnd_status(self, extension: str) -> None:
        """Remove DND status and restore previous"""
        # Check if we set this status (not user)
        if extension in self.previous_statuses:
            # Restore previous status
            previous = self.previous_statuses[extension]
            self.presence_system.set_status(extension, previous)

    def _check_all_rules(self) -> None:
        """Check all rules and update presence accordingly"""
        if not self.presence_system:
            return

        now = datetime.now(UTC)

        for extension in list(
            set(list(self.rules.keys()) + list(self.calendar_monitor.extension_email_map.keys()))
        ):
            try:
                # Check manual override first
                if self._check_manual_override(extension, now):
                    continue

                # Determine if DND should be active
                should_dnd = self._should_apply_dnd(extension, now)

                # Get current status
                user = self.presence_system.users.get(extension)
                if not user:
                    continue

                current_status = user.status

                # Apply or remove DND
                if should_dnd and current_status not in [
                    PresenceStatus.DO_NOT_DISTURB,
                    PresenceStatus.IN_MEETING,
                ]:
                    self._apply_dnd_status(extension, current_status)

                elif not should_dnd and current_status in [
                    PresenceStatus.DO_NOT_DISTURB,
                    PresenceStatus.IN_MEETING,
                ]:
                    self._remove_dnd_status(extension)
                    del self.previous_statuses[extension]

            except (KeyError, TypeError, ValueError) as e:
                self.logger.error(f"Error checking DND for {extension}: {e}")

    def get_status(self, extension: str) -> dict:
        """
        Get DND scheduling status for extension

        Args:
            extension: Extension number

        Returns:
            Status dictionary
        """
        status = {
            "extension": extension,
            "dnd_active": False,
            "reason": None,
            "rules_count": len(self.rules.get(extension, [])),
            "manual_override": extension in self.manual_overrides,
            "in_meeting": False,
            "meeting_info": None,
        }

        # Check presence
        if self.presence_system:
            user = self.presence_system.users.get(extension)
            if user:
                status["dnd_active"] = user.status in [
                    PresenceStatus.DO_NOT_DISTURB,
                    PresenceStatus.IN_MEETING,
                ]
                status["current_status"] = user.status.value

        # Check calendar
        if self.calendar_dnd_enabled:
            in_meeting, meeting_info = self.calendar_monitor.is_in_meeting(extension)
            status["in_meeting"] = in_meeting
            status["meeting_info"] = meeting_info
            if in_meeting:
                status["reason"] = "calendar_meeting"

        # Check rules
        if extension in self.rules:
            for rule in self.rules[extension]:
                if rule.should_apply():
                    if not status["reason"]:
                        status["reason"] = "scheduled_rule"
                    break

        return status


def get_dnd_scheduler(
    presence_system: Any | None = None,
    outlook_integration: Any | None = None,
    config: dict | None = None,
) -> DNDScheduler:
    """Get DND scheduler instance"""
    return DNDScheduler(presence_system, outlook_integration, config)
