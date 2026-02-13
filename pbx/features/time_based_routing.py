"""
Time-Based Routing
Route calls based on business hours and schedules
"""

from datetime import datetime, time

from pbx.utils.logger import get_logger


class TimeBasedRouting:
    """Time-based call routing system"""

    def __init__(self, config=None):
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

    def _load_rules(self):
        """Load routing rules from config"""
        rules = self.config.get("features", {}).get("time_based_routing", {}).get("rules", [])
        for rule in rules:
            self.add_rule(rule)

    def add_rule(self, rule: Dict) -> str:
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
        rule_id = f"tbr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.routing_rules)}"

        rule["rule_id"] = rule_id
        rule["created_at"] = datetime.now()
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

    def get_routing_destination(
        self, destination: str, call_time: datetime | None = None
    ) -> Dict:
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
            call_time = datetime.now()

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

    def _evaluate_time_conditions(self, conditions: Dict, check_time: datetime) -> bool:
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
        if "exclude_holidays" in conditions and conditions["exclude_holidays"]:
            if self._is_holiday(check_time):
                return False

        return True

    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM format)"""
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))

    def _is_time_in_range(self, check_time: time, start_time: time, end_time: time) -> bool:
        """Check if time is in range"""
        if start_time <= end_time:
            return start_time <= check_time <= end_time
        else:
            # Range spans midnight
            return check_time >= start_time or check_time <= end_time

    def _is_holiday(self, check_date: datetime) -> bool:
        """Check if date is a holiday"""
        # Stub - in production would check against holiday calendar
        holidays = self.config.get("features", {}).get("time_based_routing", {}).get("holidays", [])
        date_str = check_date.strftime("%Y-%m-%d")
        return date_str in holidays

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

    def list_rules(self, destination: str | None = None) -> list[Dict]:
        """List routing rules"""
        if destination:
            rule_ids = self.destination_rules.get(destination, [])
            return [self.routing_rules[rid] for rid in rule_ids if rid in self.routing_rules]

        return list(self.routing_rules.values())

    def get_statistics(self) -> Dict:
        """Get time-based routing statistics"""
        enabled_rules = sum(1 for r in self.routing_rules.values() if r.get("enabled", True))

        return {
            "enabled": self.enabled,
            "total_rules": len(self.routing_rules),
            "enabled_rules": enabled_rules,
            "destinations_with_rules": len(self.destination_rules),
        }
