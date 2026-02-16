#!/usr/bin/env python3
"""
Tests for Do Not Disturb (DND) Scheduling
"""

from datetime import datetime

from pbx.features.dnd_scheduling import CalendarMonitor, DNDRule, DNDScheduler
from pbx.features.presence import PresenceStatus, PresenceSystem


def test_dnd_rule_creation() -> bool:
    """Test DND rule creation"""

    config = {
        "enabled": True,
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "start_time": "09:00",
        "end_time": "17:00",
    }

    rule = DNDRule("rule1", "1001", "time_based", config)

    assert rule.rule_id == "rule1"
    assert rule.extension == "1001"
    assert rule.rule_type == "time_based"
    assert rule.enabled

    return True


def test_time_based_rule() -> bool:
    """Test time-based rule evaluation"""

    config = {
        "enabled": True,
        "days": ["Monday", "Wednesday", "Friday"],
        "start_time": "09:00",
        "end_time": "17:00",
    }

    rule = DNDRule("rule1", "1001", "time_based", config)

    # Test during work hours on Monday
    test_time = datetime(2025, 12, 8, 10, 0)  # Monday 10:00 AM
    assert rule.should_apply(test_time), "Should apply during work hours on Monday"

    # Test outside work hours
    test_time = datetime(2025, 12, 8, 18, 0)  # Monday 6:00 PM
    assert not rule.should_apply(test_time), "Should not apply outside work hours"

    # Test wrong day
    # Tuesday 10:00 AM (not in days list)
    test_time = datetime(2025, 12, 9, 10, 0)
    assert not rule.should_apply(test_time), "Should not apply on wrong day"

    return True


def test_overnight_rule() -> bool:
    """Test overnight time range (e.g., 22:00 to 06:00)"""

    config = {"enabled": True, "start_time": "22:00", "end_time": "06:00"}

    rule = DNDRule("rule1", "1001", "time_based", config)

    # Test at 23:00 (should apply)
    test_time = datetime(2025, 12, 8, 23, 0)
    assert rule.should_apply(test_time), "Should apply at 23:00"

    # Test at 02:00 (should apply)
    test_time = datetime(2025, 12, 9, 2, 0)
    assert rule.should_apply(test_time), "Should apply at 02:00"

    # Test at 12:00 (should not apply)
    test_time = datetime(2025, 12, 9, 12, 0)
    assert not rule.should_apply(test_time), "Should not apply at noon"

    return True


def test_dnd_scheduler_basic() -> bool:
    """Test DND scheduler basic functionality"""

    config = {
        "features": {
            "dnd_scheduling": {"enabled": True, "calendar_dnd": False, "check_interval": 1}
        }
    }

    presence_system = PresenceSystem()
    scheduler = DNDScheduler(presence_system=presence_system, config=config)

    assert scheduler.enabled, "Scheduler should be enabled"

    return True


def test_add_remove_rules() -> bool:
    """Test adding and removing DND rules"""

    config = {"features": {"dnd_scheduling": {"enabled": True}}}
    presence_system = PresenceSystem()
    scheduler = DNDScheduler(presence_system=presence_system, config=config)

    # Add rule
    rule_config = {"enabled": True, "days": ["Monday"], "start_time": "09:00", "end_time": "17:00"}

    rule_id = scheduler.add_rule("1001", "time_based", rule_config)
    assert rule_id, "Rule ID should be returned"

    # Get rules
    rules = scheduler.get_rules("1001")
    assert len(rules) == 1, "Should have 1 rule"
    assert rules[0]["rule_id"] == rule_id

    # Remove rule
    success = scheduler.remove_rule(rule_id)
    assert success, "Rule removal should succeed"

    # Verify removal
    rules = scheduler.get_rules("1001")
    assert len(rules) == 0, "Should have 0 rules after removal"

    return True


def test_manual_override() -> bool:
    """Test manual DND override"""

    config = {"features": {"dnd_scheduling": {"enabled": True}}}
    presence_system = PresenceSystem()
    presence_system.register_user("1001", "Test User")

    scheduler = DNDScheduler(presence_system=presence_system, config=config)

    # Set manual override
    scheduler.set_manual_override("1001", PresenceStatus.DO_NOT_DISTURB, duration_minutes=5)

    # Check if override is active
    assert "1001" in scheduler.manual_overrides

    # Check presence status
    user = presence_system.users.get("1001")
    assert user.status == PresenceStatus.DO_NOT_DISTURB

    # Clear override
    scheduler.clear_manual_override("1001")
    assert "1001" not in scheduler.manual_overrides

    return True


def test_dnd_status() -> bool:
    """Test getting DND status"""

    config = {"features": {"dnd_scheduling": {"enabled": True, "calendar_dnd": False}}}
    presence_system = PresenceSystem()
    presence_system.register_user("1001", "Test User")

    scheduler = DNDScheduler(presence_system=presence_system, config=config)

    # Get status
    status = scheduler.get_status("1001")

    assert "extension" in status
    assert status["extension"] == "1001"
    assert "dnd_active" in status
    assert "rules_count" in status

    return True


def test_calendar_monitor_registration() -> bool:
    """Test calendar monitor user registration"""

    calendar_monitor = CalendarMonitor(outlook_integration=None, check_interval=60)

    # Register user
    calendar_monitor.register_user("1001", "user@example.com")

    assert "1001" in calendar_monitor.extension_email_map
    assert calendar_monitor.extension_email_map["1001"] == "user@example.com"

    # Unregister user
    calendar_monitor.unregister_user("1001")
    assert "1001" not in calendar_monitor.extension_email_map

    return True


def test_rule_priority() -> bool:
    """Test DND rule priority"""

    config = {"features": {"dnd_scheduling": {"enabled": True}}}
    presence_system = PresenceSystem()
    scheduler = DNDScheduler(presence_system=presence_system, config=config)

    # Add low priority rule
    rule_config_low = {
        "enabled": True,
        "priority": 1,
        "days": ["Monday"],
        "start_time": "09:00",
        "end_time": "17:00",
    }
    scheduler.add_rule("1001", "time_based", rule_config_low)

    # Add high priority rule
    rule_config_high = {
        "enabled": True,
        "priority": 10,
        "days": ["Monday"],
        "start_time": "12:00",
        "end_time": "13:00",
    }
    scheduler.add_rule("1001", "time_based", rule_config_high)

    # Get rules
    rules = scheduler.get_rules("1001")
    assert len(rules) == 2, "Should have 2 rules"

    return True


def test_rule_to_dict() -> bool:
    """Test rule serialization"""

    config = {
        "enabled": True,
        "days": ["Monday", "Tuesday"],
        "start_time": "09:00",
        "end_time": "17:00",
        "priority": 5,
    }

    rule = DNDRule("rule1", "1001", "time_based", config)
    rule_dict = rule.to_dict()

    assert rule_dict["rule_id"] == "rule1"
    assert rule_dict["extension"] == "1001"
    assert rule_dict["rule_type"] == "time_based"
    assert rule_dict["enabled"]
    assert rule_dict["priority"] == 5

    return True
