"""Comprehensive tests for DND Scheduling module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pbx.features.dnd_scheduling import DNDRule


@pytest.mark.unit
class TestDNDRule:
    """Tests for DNDRule class."""

    def _make_rule(self, rule_type: str = "time_based", config: dict | None = None) -> DNDRule:
        from pbx.features.dnd_scheduling import DNDRule

        config = config or {"enabled": True, "priority": 5}
        return DNDRule(rule_id="rule-1", extension="1001", rule_type=rule_type, config=config)

    def test_init_defaults(self) -> None:
        from pbx.features.dnd_scheduling import DNDRule

        rule = DNDRule("r1", "1001", "time_based", {})
        assert rule.rule_id == "r1"
        assert rule.extension == "1001"
        assert rule.rule_type == "time_based"
        assert rule.enabled is True
        assert rule.priority == 0

    def test_init_with_config(self) -> None:
        rule = self._make_rule(config={"enabled": False, "priority": 10})
        assert rule.enabled is False
        assert rule.priority == 10

    def test_should_apply_disabled(self) -> None:
        rule = self._make_rule(config={"enabled": False})
        assert rule.should_apply() is False

    def test_should_apply_calendar_type(self) -> None:
        rule = self._make_rule(rule_type="calendar", config={"enabled": True})
        assert rule.should_apply() is False

    def test_should_apply_unknown_type(self) -> None:
        rule = self._make_rule(rule_type="unknown", config={"enabled": True})
        assert rule.should_apply() is False

    def test_should_apply_time_based_matching_day_and_time(self) -> None:
        now = datetime(2026, 2, 17, 14, 0, tzinfo=UTC)  # Tuesday 14:00
        rule = self._make_rule(
            config={
                "enabled": True,
                "days": ["Tuesday"],
                "start_time": "13:00",
                "end_time": "15:00",
            }
        )
        assert rule.should_apply(now) is True

    def test_should_apply_time_based_wrong_day(self) -> None:
        now = datetime(2026, 2, 17, 14, 0, tzinfo=UTC)  # Tuesday
        rule = self._make_rule(
            config={
                "enabled": True,
                "days": ["Wednesday"],
                "start_time": "13:00",
                "end_time": "15:00",
            }
        )
        assert rule.should_apply(now) is False

    def test_should_apply_time_based_outside_time(self) -> None:
        now = datetime(2026, 2, 17, 16, 0, tzinfo=UTC)  # Tuesday 16:00
        rule = self._make_rule(
            config={
                "enabled": True,
                "days": ["Tuesday"],
                "start_time": "13:00",
                "end_time": "15:00",
            }
        )
        assert rule.should_apply(now) is False

    def test_should_apply_time_based_overnight(self) -> None:
        """Overnight rule: 22:00 to 06:00."""
        now = datetime(2026, 2, 17, 23, 0, tzinfo=UTC)  # Tuesday 23:00
        rule = self._make_rule(
            config={
                "enabled": True,
                "days": ["Tuesday"],
                "start_time": "22:00",
                "end_time": "06:00",
            }
        )
        assert rule.should_apply(now) is True

    def test_should_apply_time_based_overnight_early_morning(self) -> None:
        now = datetime(2026, 2, 17, 3, 0, tzinfo=UTC)  # Tuesday 03:00
        rule = self._make_rule(
            config={
                "enabled": True,
                "days": ["Tuesday"],
                "start_time": "22:00",
                "end_time": "06:00",
            }
        )
        assert rule.should_apply(now) is True

    def test_should_apply_no_days_filter(self) -> None:
        """No days specified means any day."""
        now = datetime(2026, 2, 17, 14, 0, tzinfo=UTC)
        rule = self._make_rule(
            config={
                "enabled": True,
                "days": [],
                "start_time": "13:00",
                "end_time": "15:00",
            }
        )
        assert rule.should_apply(now) is True

    def test_should_apply_no_time_range(self) -> None:
        """No start/end time returns False."""
        now = datetime(2026, 2, 17, 14, 0, tzinfo=UTC)
        rule = self._make_rule(config={"enabled": True, "days": []})
        assert rule.should_apply(now) is False

    def test_should_apply_uses_now_when_none(self) -> None:
        rule = self._make_rule(
            config={
                "enabled": True,
                "days": [],
                "start_time": "00:00",
                "end_time": "23:59",
            }
        )
        # Should not raise; applies or not depending on current time
        result = rule.should_apply(None)
        assert isinstance(result, bool)

    def test_to_dict(self) -> None:
        rule = self._make_rule(config={"enabled": True, "priority": 7})
        d = rule.to_dict()
        assert d["rule_id"] == "rule-1"
        assert d["extension"] == "1001"
        assert d["rule_type"] == "time_based"
        assert d["enabled"] is True
        assert d["priority"] == 7
        assert "config" in d


@pytest.mark.unit
class TestCalendarMonitor:
    """Tests for CalendarMonitor class."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.dnd_scheduling.get_logger"):
            from pbx.features.dnd_scheduling import CalendarMonitor

            self.outlook = MagicMock()
            self.outlook.enabled = True
            self.monitor = CalendarMonitor(outlook_integration=self.outlook, check_interval=5)

    def test_register_user(self) -> None:
        self.monitor.register_user("1001", "user@example.com")
        assert self.monitor.extension_email_map["1001"] == "user@example.com"

    def test_unregister_user(self) -> None:
        self.monitor.register_user("1001", "user@example.com")
        self.monitor.active_meetings["1001"] = {"subject": "Test"}
        self.monitor.unregister_user("1001")
        assert "1001" not in self.monitor.extension_email_map
        assert "1001" not in self.monitor.active_meetings

    def test_unregister_nonexistent_user(self) -> None:
        """Unregistering non-existent user does not raise."""
        self.monitor.unregister_user("9999")

    def test_start_already_running(self) -> None:
        self.monitor.running = True
        self.monitor.start()
        assert self.monitor.thread is None  # No new thread created

    def test_start_no_outlook(self) -> None:
        with patch("pbx.features.dnd_scheduling.get_logger"):
            from pbx.features.dnd_scheduling import CalendarMonitor

            monitor = CalendarMonitor(outlook_integration=None)
            monitor.start()
            assert monitor.running is False

    def test_start_outlook_disabled(self) -> None:
        self.outlook.enabled = False
        with patch("pbx.features.dnd_scheduling.get_logger"):
            from pbx.features.dnd_scheduling import CalendarMonitor

            monitor = CalendarMonitor(outlook_integration=self.outlook)
            monitor.start()
            assert monitor.running is False

    def test_start_and_stop(self) -> None:
        """Start then stop monitoring thread."""
        self.monitor.start()
        assert self.monitor.running is True
        assert self.monitor.thread is not None
        self.monitor.stop()
        assert self.monitor.running is False

    def test_stop_without_start(self) -> None:
        """Stopping without starting does not raise."""
        self.monitor.stop()
        assert self.monitor.running is False

    def test_is_in_meeting_no_meeting(self) -> None:
        result, info = self.monitor.is_in_meeting("1001")
        assert result is False
        assert info is None

    def test_is_in_meeting_with_meeting(self) -> None:
        meeting = {"subject": "Team Standup", "start": "2026-02-17T14:00:00"}
        self.monitor.active_meetings["1001"] = meeting
        result, info = self.monitor.is_in_meeting("1001")
        assert result is True
        assert info == meeting

    def test_check_all_calendars_user_enters_meeting(self) -> None:
        """User enters meeting - active_meetings is updated."""
        now = datetime.now(UTC)
        event_start = (now - timedelta(minutes=5)).isoformat()
        event_end = (now + timedelta(minutes=25)).isoformat()

        self.monitor.register_user("1001", "user@example.com")
        self.outlook.get_calendar_events.return_value = [
            {
                "start": event_start,
                "end": event_end,
                "showAs": "busy",
                "responseStatus": {"response": "accepted"},
                "subject": "Sprint Planning",
            }
        ]

        self.monitor._check_all_calendars()
        assert "1001" in self.monitor.active_meetings
        assert self.monitor.active_meetings["1001"]["subject"] == "Sprint Planning"

    def test_check_all_calendars_user_leaves_meeting(self) -> None:
        """User leaves meeting - removed from active_meetings."""
        self.monitor.register_user("1001", "user@example.com")
        self.monitor.active_meetings["1001"] = {"subject": "Old Meeting"}

        # Return empty events so user appears to have left
        self.outlook.get_calendar_events.return_value = []

        self.monitor._check_all_calendars()
        assert "1001" not in self.monitor.active_meetings

    def test_check_all_calendars_declined_meeting_ignored(self) -> None:
        """Declined meeting does not set DND."""
        now = datetime.now(UTC)
        event_start = (now - timedelta(minutes=5)).isoformat()
        event_end = (now + timedelta(minutes=25)).isoformat()

        self.monitor.register_user("1001", "user@example.com")
        self.outlook.get_calendar_events.return_value = [
            {
                "start": event_start,
                "end": event_end,
                "showAs": "busy",
                "responseStatus": {"response": "declined"},
                "subject": "Declined Meeting",
            }
        ]

        self.monitor._check_all_calendars()
        assert "1001" not in self.monitor.active_meetings

    def test_check_all_calendars_free_meeting_ignored(self) -> None:
        """Meeting marked as 'free' does not set DND."""
        now = datetime.now(UTC)
        event_start = (now - timedelta(minutes=5)).isoformat()
        event_end = (now + timedelta(minutes=25)).isoformat()

        self.monitor.register_user("1001", "user@example.com")
        self.outlook.get_calendar_events.return_value = [
            {
                "start": event_start,
                "end": event_end,
                "showAs": "free",
                "responseStatus": {"response": "accepted"},
                "subject": "Optional Meeting",
            }
        ]

        self.monitor._check_all_calendars()
        assert "1001" not in self.monitor.active_meetings

    def test_check_all_calendars_tentative_accepted(self) -> None:
        """Tentative meeting that is tentatively accepted sets DND."""
        now = datetime.now(UTC)
        event_start = (now - timedelta(minutes=5)).isoformat()
        event_end = (now + timedelta(minutes=25)).isoformat()

        self.monitor.register_user("1001", "user@example.com")
        self.outlook.get_calendar_events.return_value = [
            {
                "start": event_start,
                "end": event_end,
                "showAs": "tentative",
                "responseStatus": {"response": "tentativelyAccepted"},
                "subject": "Maybe Meeting",
            }
        ]

        self.monitor._check_all_calendars()
        assert "1001" in self.monitor.active_meetings

    def test_check_all_calendars_exception_handled(self) -> None:
        """Error checking a user's calendar does not crash loop."""
        self.monitor.register_user("1001", "user@example.com")
        self.outlook.get_calendar_events.side_effect = KeyError("missing field")

        self.monitor._check_all_calendars()
        # Should not raise

    def test_check_all_calendars_updates_existing_meeting(self) -> None:
        """Already-in-meeting user gets meeting info updated."""
        now = datetime.now(UTC)
        event_start = (now - timedelta(minutes=5)).isoformat()
        event_end = (now + timedelta(minutes=25)).isoformat()

        self.monitor.register_user("1001", "user@example.com")
        self.monitor.active_meetings["1001"] = {"subject": "Old"}

        self.outlook.get_calendar_events.return_value = [
            {
                "start": event_start,
                "end": event_end,
                "showAs": "busy",
                "responseStatus": {"response": "organizer"},
                "subject": "Updated Meeting",
            }
        ]

        self.monitor._check_all_calendars()
        assert self.monitor.active_meetings["1001"]["subject"] == "Updated Meeting"


@pytest.mark.unit
class TestDNDScheduler:
    """Tests for DNDScheduler class."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        with patch("pbx.features.dnd_scheduling.get_logger"):
            from pbx.features.dnd_scheduling import DNDScheduler

            self.presence = MagicMock()
            self.outlook = MagicMock()
            self.outlook.enabled = True
            self.config = {
                "features": {
                    "dnd_scheduling": {
                        "enabled": True,
                        "calendar_dnd": True,
                        "check_interval": 5,
                    }
                }
            }
            self.scheduler = DNDScheduler(
                presence_system=self.presence,
                outlook_integration=self.outlook,
                config=self.config,
            )

    def test_init_disabled(self) -> None:
        with patch("pbx.features.dnd_scheduling.get_logger"):
            from pbx.features.dnd_scheduling import DNDScheduler

            config = {"features": {"dnd_scheduling": {"enabled": False}}}
            sched = DNDScheduler(config=config)
            assert sched.enabled is False

    def test_init_enabled(self) -> None:
        assert self.scheduler.enabled is True
        assert self.scheduler.calendar_dnd_enabled is True
        assert self.scheduler.check_interval == 5

    def test_get_config_nested_dict(self) -> None:
        val = self.scheduler._get_config("features.dnd_scheduling.enabled")
        assert val is True

    def test_get_config_missing_key(self) -> None:
        val = self.scheduler._get_config("features.nonexistent.key", "default")
        assert val == "default"

    def test_get_config_dot_notation_on_config_object(self) -> None:
        """When config has a get method that supports dot notation."""
        mock_config = MagicMock()
        mock_config.get.return_value = "dotval"
        with patch("pbx.features.dnd_scheduling.get_logger"):
            from pbx.features.dnd_scheduling import DNDScheduler

            sched = DNDScheduler(config=mock_config)
            _val = sched._get_config("features.dnd_scheduling.enabled", False)
            # The mock config.get was called
            assert mock_config.get.called

    def test_start_disabled(self) -> None:
        self.scheduler.enabled = False
        self.scheduler.start()
        assert self.scheduler.running is False

    def test_start_already_running(self) -> None:
        self.scheduler.running = True
        self.scheduler.start()
        # No new thread started (thread is still None from init)

    def test_start_and_stop(self) -> None:
        self.scheduler.start()
        assert self.scheduler.running is True
        self.scheduler.stop()
        assert self.scheduler.running is False

    def test_stop_without_start(self) -> None:
        self.scheduler.stop()
        assert self.scheduler.running is False

    def test_add_rule(self) -> None:
        rule_id = self.scheduler.add_rule("1001", "time_based", {"enabled": True})
        assert rule_id is not None
        assert "1001" in self.scheduler.rules
        assert len(self.scheduler.rules["1001"]) == 1

    def test_add_multiple_rules(self) -> None:
        self.scheduler.add_rule("1001", "time_based", {"enabled": True})
        self.scheduler.add_rule("1001", "calendar", {"enabled": True})
        assert len(self.scheduler.rules["1001"]) == 2

    def test_remove_rule(self) -> None:
        rule_id = self.scheduler.add_rule("1001", "time_based", {"enabled": True})
        result = self.scheduler.remove_rule(rule_id)
        assert result is True
        assert len(self.scheduler.rules["1001"]) == 0

    def test_remove_nonexistent_rule(self) -> None:
        result = self.scheduler.remove_rule("nonexistent-id")
        assert result is False

    def test_get_rules_empty(self) -> None:
        result = self.scheduler.get_rules("1001")
        assert result == []

    def test_get_rules_with_data(self) -> None:
        self.scheduler.add_rule("1001", "time_based", {"enabled": True})
        result = self.scheduler.get_rules("1001")
        assert len(result) == 1
        assert result[0]["rule_type"] == "time_based"

    def test_register_calendar_user(self) -> None:
        self.scheduler.register_calendar_user("1001", "user@example.com")
        assert "1001" in self.scheduler.calendar_monitor.extension_email_map

    def test_register_calendar_user_disabled(self) -> None:
        self.scheduler.calendar_dnd_enabled = False
        self.scheduler.register_calendar_user("1001", "user@example.com")
        assert "1001" not in self.scheduler.calendar_monitor.extension_email_map

    def test_unregister_calendar_user(self) -> None:
        self.scheduler.register_calendar_user("1001", "user@example.com")
        self.scheduler.unregister_calendar_user("1001")
        assert "1001" not in self.scheduler.calendar_monitor.extension_email_map

    def test_set_manual_override_with_duration(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler.set_manual_override("1001", PresenceStatus.DO_NOT_DISTURB, 30)
        assert "1001" in self.scheduler.manual_overrides
        status, until = self.scheduler.manual_overrides["1001"]
        assert status == PresenceStatus.DO_NOT_DISTURB
        assert until is not None
        self.presence.set_status.assert_called_once_with("1001", PresenceStatus.DO_NOT_DISTURB)

    def test_set_manual_override_indefinite(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler.set_manual_override("1001", PresenceStatus.DO_NOT_DISTURB)
        _status, until = self.scheduler.manual_overrides["1001"]
        assert until is None

    def test_set_manual_override_no_presence(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler.presence_system = None
        self.scheduler.set_manual_override("1001", PresenceStatus.DO_NOT_DISTURB)
        assert "1001" in self.scheduler.manual_overrides

    def test_clear_manual_override(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler.set_manual_override("1001", PresenceStatus.DO_NOT_DISTURB)
        self.scheduler.clear_manual_override("1001")
        assert "1001" not in self.scheduler.manual_overrides

    def test_clear_manual_override_nonexistent(self) -> None:
        self.scheduler.clear_manual_override("9999")
        # Should not raise

    def test_check_manual_override_active(self) -> None:
        from pbx.features.presence import PresenceStatus

        now = datetime.now(UTC)
        future = now + timedelta(hours=1)
        self.scheduler.manual_overrides["1001"] = (PresenceStatus.DO_NOT_DISTURB, future)
        assert self.scheduler._check_manual_override("1001", now) is True

    def test_check_manual_override_expired(self) -> None:
        from pbx.features.presence import PresenceStatus

        now = datetime.now(UTC)
        past = now - timedelta(hours=1)
        self.scheduler.manual_overrides["1001"] = (PresenceStatus.DO_NOT_DISTURB, past)
        assert self.scheduler._check_manual_override("1001", now) is False
        assert "1001" not in self.scheduler.manual_overrides

    def test_check_manual_override_indefinite(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler.manual_overrides["1001"] = (PresenceStatus.DO_NOT_DISTURB, None)
        now = datetime.now(UTC)
        assert self.scheduler._check_manual_override("1001", now) is True

    def test_check_manual_override_no_override(self) -> None:
        now = datetime.now(UTC)
        assert self.scheduler._check_manual_override("1001", now) is False

    def test_should_apply_dnd_time_rule(self) -> None:
        now = datetime(2026, 2, 17, 14, 0, tzinfo=UTC)
        self.scheduler.add_rule(
            "1001",
            "time_based",
            {
                "enabled": True,
                "priority": 5,
                "days": ["Tuesday"],
                "start_time": "13:00",
                "end_time": "15:00",
            },
        )
        assert self.scheduler._should_apply_dnd("1001", now) is True

    def test_should_apply_dnd_calendar_meeting(self) -> None:
        now = datetime.now(UTC)
        self.scheduler.calendar_monitor.active_meetings["1001"] = {"subject": "Meet"}
        assert self.scheduler._should_apply_dnd("1001", now) is True

    def test_should_apply_dnd_no_rules_no_meeting(self) -> None:
        now = datetime.now(UTC)
        assert self.scheduler._should_apply_dnd("1001", now) is False

    def test_apply_dnd_status_meeting(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler.calendar_monitor.active_meetings["1001"] = {"subject": "Meet"}
        self.scheduler._apply_dnd_status("1001", PresenceStatus.AVAILABLE)

        self.presence.set_status.assert_called_with(
            "1001", PresenceStatus.IN_MEETING, "In calendar meeting"
        )
        assert self.scheduler.previous_statuses["1001"] == PresenceStatus.AVAILABLE

    def test_apply_dnd_status_scheduled(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler._apply_dnd_status("1001", PresenceStatus.AVAILABLE)
        self.presence.set_status.assert_called_with(
            "1001", PresenceStatus.DO_NOT_DISTURB, "Auto-DND (scheduled)"
        )

    def test_remove_dnd_status_restores_previous(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler.previous_statuses["1001"] = PresenceStatus.AVAILABLE
        self.scheduler._remove_dnd_status("1001")
        self.presence.set_status.assert_called_with("1001", PresenceStatus.AVAILABLE)

    def test_remove_dnd_status_no_previous(self) -> None:
        self.scheduler._remove_dnd_status("1001")
        self.presence.set_status.assert_not_called()

    def test_check_all_rules_no_presence(self) -> None:
        self.scheduler.presence_system = None
        self.scheduler._check_all_rules()
        # Should return early without error

    def test_check_all_rules_applies_dnd(self) -> None:
        from pbx.features.presence import PresenceStatus

        mock_user = MagicMock()
        mock_user.status = PresenceStatus.AVAILABLE
        self.presence.users = {"1001": mock_user}

        now = datetime(2026, 2, 17, 14, 0, tzinfo=UTC)
        self.scheduler.add_rule(
            "1001",
            "time_based",
            {
                "enabled": True,
                "priority": 5,
                "days": ["Tuesday"],
                "start_time": "00:00",
                "end_time": "23:59",
            },
        )

        with patch("pbx.features.dnd_scheduling.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = datetime
            self.scheduler._check_all_rules()

    def test_check_all_rules_removes_dnd(self) -> None:
        from pbx.features.presence import PresenceStatus

        mock_user = MagicMock()
        mock_user.status = PresenceStatus.DO_NOT_DISTURB
        self.presence.users = {"1001": mock_user}
        self.scheduler.previous_statuses["1001"] = PresenceStatus.AVAILABLE

        # No rules, so DND should be removed
        self.scheduler.rules["1001"] = []

        self.scheduler._check_all_rules()
        # Should call remove_dnd_status flow

    def test_check_all_rules_skips_manual_override(self) -> None:
        from pbx.features.presence import PresenceStatus

        now = datetime.now(UTC)
        future = now + timedelta(hours=1)
        self.scheduler.manual_overrides["1001"] = (PresenceStatus.DO_NOT_DISTURB, future)
        self.scheduler.rules["1001"] = []

        mock_user = MagicMock()
        mock_user.status = PresenceStatus.DO_NOT_DISTURB
        self.presence.users = {"1001": mock_user}

        self.scheduler._check_all_rules()
        # Should skip because of manual override

    def test_check_all_rules_no_user_in_presence(self) -> None:
        """User not found in presence system is skipped."""
        self.presence.users = {}
        self.scheduler.rules["1001"] = []
        self.scheduler._check_all_rules()
        # No error

    def test_check_all_rules_exception_handled(self) -> None:
        """Exception during rule check does not crash."""
        self.presence.users = {"1001": MagicMock(side_effect=KeyError("bad"))}
        self.scheduler.rules["1001"] = []
        # This may or may not raise depending on which property is accessed
        # The point is the except clause catches it
        self.scheduler._check_all_rules()

    def test_get_status_no_presence(self) -> None:
        self.scheduler.presence_system = None
        status = self.scheduler.get_status("1001")
        assert status["extension"] == "1001"
        assert status["dnd_active"] is False

    def test_get_status_with_presence_dnd_active(self) -> None:
        from pbx.features.presence import PresenceStatus

        mock_user = MagicMock()
        mock_user.status = PresenceStatus.DO_NOT_DISTURB
        self.presence.users = {"1001": mock_user}

        status = self.scheduler.get_status("1001")
        assert status["dnd_active"] is True
        assert status["current_status"] == "do_not_disturb"

    def test_get_status_in_meeting(self) -> None:
        from pbx.features.presence import PresenceStatus

        mock_user = MagicMock()
        mock_user.status = PresenceStatus.IN_MEETING
        self.presence.users = {"1001": mock_user}
        self.scheduler.calendar_monitor.active_meetings["1001"] = {"subject": "Standup"}

        status = self.scheduler.get_status("1001")
        assert status["in_meeting"] is True
        assert status["reason"] == "calendar_meeting"

    def test_get_status_with_rule_applying(self) -> None:
        from pbx.features.presence import PresenceStatus

        mock_user = MagicMock()
        mock_user.status = PresenceStatus.AVAILABLE
        self.presence.users = {"1001": mock_user}

        self.scheduler.add_rule(
            "1001",
            "time_based",
            {
                "enabled": True,
                "days": [],
                "start_time": "00:00",
                "end_time": "23:59",
            },
        )

        status = self.scheduler.get_status("1001")
        assert status["reason"] == "scheduled_rule"

    def test_get_status_manual_override(self) -> None:
        from pbx.features.presence import PresenceStatus

        self.scheduler.manual_overrides["1001"] = (PresenceStatus.DO_NOT_DISTURB, None)

        status = self.scheduler.get_status("1001")
        assert status["manual_override"] is True


@pytest.mark.unit
class TestGetDndScheduler:
    """Tests for get_dnd_scheduler factory function."""

    def test_returns_dnd_scheduler(self) -> None:
        with patch("pbx.features.dnd_scheduling.get_logger"):
            from pbx.features.dnd_scheduling import DNDScheduler, get_dnd_scheduler

            sched = get_dnd_scheduler(config={"features": {"dnd_scheduling": {"enabled": False}}})
            assert isinstance(sched, DNDScheduler)

    def test_passes_parameters(self) -> None:
        with patch("pbx.features.dnd_scheduling.get_logger"):
            from pbx.features.dnd_scheduling import get_dnd_scheduler

            presence = MagicMock()
            outlook = MagicMock()
            config = {"features": {"dnd_scheduling": {"enabled": False}}}
            sched = get_dnd_scheduler(presence, outlook, config)
            assert sched.presence_system is presence
            assert sched.outlook is outlook
