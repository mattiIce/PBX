"""
Time-Based Routing
Route calls based on business hours and schedules
"""

from datetime import UTC, datetime, time
from typing import Any

from pbx.utils.logger import get_logger


class TimeBasedRouting:
    """Time-based call routing system"""

    def __init__(self, config: Any | None = None) -> None:
        """Initialize time-based routing"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = (
            self.config.get("features", {}).get("time_based_routing", {}).get("enabled", False)
        )

        # Routing rules
        self.routing_rules = {}  # rule_id -> rule
        self.destination_rules = {}  # destination -> list of rule_ids

        if self.enabled:
            self.logger.info("Time-based routing initialized")
            self._load_rules()

    def _load_rules(self) -> None:
        """Load routing rules from config"""
        rules = self.config.get("features", {}).get("time_based_routing", {}).get("rules", [])
        for rule in rules:
            self.add_rule(rule)

    def add_rule(self, rule: dict) -> str:
        """
        Add a time-based routing rule

        Args:
            rule: Routing rule configuration
                Required: name, destination, time_conditions
                Optional: priority, enabled

        Returns:
            Rule ID
        """
        if not self.enabled:
            return ""

        # Generate rule ID
        rule_id = f"tbr_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{len(self.routing_rules)}"

        rule["rule_id"] = rule_id
        rule["created_at"] = datetime.now(UTC)
        rule["enabled"] = rule.get("enabled", True)
        rule["priority"] = rule.get("priority", 100)

        self.routing_rules[rule_id] = rule

        # Index by destination
        destination = rule["destination"]
        if destination not in self.destination_rules:
            self.destination_rules[destination] = []
        self.destination_rules[destination].append(rule_id)

        self.logger.info(f"Added time-based routing rule: {rule['name']} (ID: {rule_id})")
        return rule_id

    def get_routing_destination(self, destination: str, call_time: datetime | None = None) -> dict:
        """
        Get routing destination based on time rules

        Args:
            destination: Original destination (extension, queue, etc.)
            call_time: Call time (defaults to now)

        Returns:
            Routing information with actual destination
        """
        if not self.enabled:
            return {"destination": destination, "rule": None}

        if call_time is None:
            call_time = datetime.now(UTC)

        # Get rules for this destination
        rule_ids = self.destination_rules.get(destination, [])
        if not rule_ids:
            return {"destination": destination, "rule": None}

        # Evaluate rules by priority
        applicable_rules = []
        for rule_id in rule_ids:
            rule = self.routing_rules[rule_id]
            if not rule.get("enabled", True):
                continue

            if self._evaluate_time_conditions(rule["time_conditions"], call_time):
                applicable_rules.append(rule)

        if not applicable_rules:
            return {"destination": destination, "rule": None}

        # Sort by priority (lower number = higher priority)
        applicable_rules.sort(key=lambda r: r["priority"])

        # Use first matching rule
        selected_rule = applicable_rules[0]

        return {
            "destination": selected_rule.get("route_to", destination),
            "rule": selected_rule["rule_id"],
            "rule_name": selected_rule["name"],
            "original_destination": destination,
        }

    def _evaluate_time_conditions(self, conditions: dict, check_time: datetime) -> bool:
        """Evaluate if time conditions match"""
        # Check day of week
        if "days_of_week" in conditions:
            day_of_week = check_time.weekday()  # 0=Monday, 6=Sunday
            if day_of_week not in conditions["days_of_week"]:
                return False

        # Check time range
        if "time_range" in conditions:
            time_range = conditions["time_range"]
            start_time = self._parse_time(time_range["start"])
            end_time = self._parse_time(time_range["end"])
            current_time = check_time.time()

            if not self._is_time_in_range(current_time, start_time, end_time):
                return False

        # Check date range
        if "date_range" in conditions:
            date_range = conditions["date_range"]
            start_date = datetime.fromisoformat(date_range["start"]).date()
            end_date = datetime.fromisoformat(date_range["end"]).date()
            current_date = check_time.date()

            if not (start_date <= current_date <= end_date):
                return False

        # Check holidays
        return not (conditions.get("exclude_holidays") and self._is_holiday(check_time))

    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM format)"""
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))

    def _is_time_in_range(self, check_time: time, start_time: time, end_time: time) -> bool:
        """Check if time is in range"""
        if start_time <= end_time:
            return start_time <= check_time <= end_time
        # Range spans midnight
        return check_time >= start_time or check_time <= end_time

    def _is_holiday(self, check_date: datetime) -> bool:
        """Check if a date falls on a configured holiday.

        The holiday calendar is read from
        ``config.features.time_based_routing.holidays``.  The value can be
        a simple list of date strings **or** a list of dicts with richer
        matching capabilities.

        Supported formats:
        - ``"YYYY-MM-DD"`` — matches a specific date (e.g. ``"2026-01-01"``)
        - ``"MM-DD"`` — matches the same month/day every year
          (e.g. ``"12-25"`` for Christmas)
        - dict with ``date`` key — same string formats above, plus an
          optional ``name`` for logging/display
        - dict with ``weekday`` (0-6, Monday=0) and optional ``month``
          (1-12) — matches a recurring weekday, optionally limited to a
          specific month
        - dict with ``nth_weekday`` — matches the Nth occurrence of a
          weekday in a month (e.g. 4th Thursday in November for US
          Thanksgiving).  Keys: ``month`` (1-12), ``weekday`` (0-6),
          ``n`` (1-based occurrence)

        Args:
            check_date: The datetime to check.

        Returns:
            ``True`` if the date is a configured holiday.
        """
        holidays = self.config.get("features", {}).get("time_based_routing", {}).get("holidays", [])

        if not holidays:
            return False

        check_date_str = check_date.strftime("%Y-%m-%d")
        check_mmdd = check_date.strftime("%m-%d")

        for entry in holidays:
            # Simple string entry (exact date or recurring MM-DD)
            if isinstance(entry, str):
                if entry == check_date_str:
                    return True
                # Recurring annual holiday (MM-DD format)
                if len(entry) == 5 and entry == check_mmdd:
                    return True
                continue

            # Dict entry — richer matching
            if not isinstance(entry, dict):
                continue

            # Nth weekday in a month (e.g. 4th Thursday in November)
            if "nth_weekday" in entry or ("n" in entry and "weekday" in entry and "month" in entry):
                month = entry.get("month")
                weekday = entry.get("weekday")
                n = entry.get("n") or entry.get("nth_weekday")
                if (
                    month is not None
                    and weekday is not None
                    and n is not None
                    and self._matches_nth_weekday(check_date, int(month), int(weekday), int(n))
                ):
                    return True
                continue

            # Recurring weekday (optionally in a specific month)
            if (
                "weekday" in entry
                and "date" not in entry
                and check_date.weekday() == entry["weekday"]
                and ("month" not in entry or check_date.month == entry["month"])
            ):
                return True
            if "weekday" in entry and "date" not in entry:
                continue

            # Date string inside a dict (with optional name)
            date_val = entry.get("date", "")
            if date_val == check_date_str:
                return True
            if len(date_val) == 5 and date_val == check_mmdd:
                return True

        return False

    @staticmethod
    def _matches_nth_weekday(check_date: datetime, month: int, weekday: int, n: int) -> bool:
        """Check if *check_date* is the *n*-th occurrence of *weekday* in *month*.

        Args:
            check_date: Date to test.
            month: Required month (1-12).
            weekday: Required weekday (0=Monday .. 6=Sunday).
            n: 1-based occurrence (e.g. 4 for "fourth").

        Returns:
            ``True`` if the date matches.
        """
        if check_date.month != month or check_date.weekday() != weekday:
            return False
        # The Nth weekday falls on days (n-1)*7+1 .. n*7
        day = check_date.day
        return (n - 1) * 7 < day <= n * 7

    def create_business_hours_rule(
        self,
        destination: str,
        route_to: str,
        start_time: str = "09:00",
        end_time: str = "17:00",
        weekdays_only: bool = True,
    ) -> str:
        """
        Create a standard business hours routing rule

        Args:
            destination: Original destination
            route_to: Where to route during business hours
            start_time: Business hours start (HH:MM)
            end_time: Business hours end (HH:MM)
            weekdays_only: Only apply Mon-Fri

        Returns:
            Rule ID
        """
        rule = {
            "name": f"Business Hours - {destination}",
            "destination": destination,
            "route_to": route_to,
            "time_conditions": {
                "time_range": {"start": start_time, "end": end_time},
                "exclude_holidays": True,
            },
            "priority": 100,
        }

        if weekdays_only:
            rule["time_conditions"]["days_of_week"] = [0, 1, 2, 3, 4]  # Mon-Fri

        return self.add_rule(rule)

    def create_after_hours_rule(
        self, destination: str, route_to: str, after_time: str = "17:00", before_time: str = "09:00"
    ) -> str:
        """Create an after-hours routing rule"""
        rule = {
            "name": f"After Hours - {destination}",
            "destination": destination,
            "route_to": route_to,
            "time_conditions": {
                "time_range": {"start": after_time, "end": before_time}  # Spans midnight
            },
            "priority": 90,
        }

        return self.add_rule(rule)

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a routing rule"""
        if rule_id in self.routing_rules:
            self.routing_rules[rule_id]["enabled"] = True
            self.logger.info(f"Enabled routing rule {rule_id}")
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a routing rule"""
        if rule_id in self.routing_rules:
            self.routing_rules[rule_id]["enabled"] = False
            self.logger.info(f"Disabled routing rule {rule_id}")
            return True
        return False

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a routing rule"""
        if rule_id in self.routing_rules:
            rule = self.routing_rules[rule_id]
            destination = rule["destination"]

            # Remove from index
            if destination in self.destination_rules:
                self.destination_rules[destination].remove(rule_id)

            del self.routing_rules[rule_id]
            self.logger.info(f"Deleted routing rule {rule_id}")
            return True
        return False

    def list_rules(self, destination: str | None = None) -> list[dict]:
        """list routing rules"""
        if destination:
            rule_ids = self.destination_rules.get(destination, [])
            return [self.routing_rules[rid] for rid in rule_ids if rid in self.routing_rules]

        return list(self.routing_rules.values())

    def get_statistics(self) -> dict:
        """Get time-based routing statistics"""
        enabled_rules = sum(1 for r in self.routing_rules.values() if r.get("enabled", True))

        return {
            "enabled": self.enabled,
            "total_rules": len(self.routing_rules),
            "enabled_rules": enabled_rules,
            "destinations_with_rules": len(self.destination_rules),
        }
