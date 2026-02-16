"""
Fraud Detection and Alert System
Pattern analysis for unusual call behavior using custom algorithms
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from pbx.utils.logger import get_logger


class FraudDetectionSystem:
    """System for detecting and alerting on unusual call patterns"""

    def __init__(self, config=None) -> None:
        """Initialize fraud detection system"""
        self.logger = get_logger()
        self.config = config or {}

        # Configuration
        fraud_config = self.config.get("features", {}).get("fraud_detection", {})
        self.enabled = fraud_config.get("enabled", False)

        # Detection thresholds
        self.max_calls_per_hour = fraud_config.get("max_calls_per_hour", 100)
        self.max_international_calls_per_day = fraud_config.get("max_international_calls", 20)
        self.max_call_duration = fraud_config.get("max_call_duration", 7200)  # 2 hours
        self.max_cost_per_day = fraud_config.get("max_cost_per_day", 500.0)
        self.unusual_hour_start = fraud_config.get("unusual_hour_start", 23)  # 11 PM
        self.unusual_hour_end = fraud_config.get("unusual_hour_end", 6)  # 6 AM

        # Tracking data
        self.call_history = defaultdict(list)  # extension -> calls
        self.alerts = []  # list of fraud alerts
        self.blocked_patterns = []  # Blocked number patterns

        if self.enabled:
            self.logger.info("Fraud detection system initialized")
            self.logger.info(f"  Max calls/hour: {self.max_calls_per_hour}")
            self.logger.info(
                f"  Max international calls/day: {self.max_international_calls_per_day}"
            )
            self.logger.info(f"  Max call duration: {self.max_call_duration}s")

    def analyze_call(self, call_data: dict) -> dict:
        """
        Analyze a call for fraud patterns

        Args:
            call_data: Call information (from, to, duration, timestamp, etc.)

        Returns:
            Analysis result with fraud score and alerts
        """
        if not self.enabled:
            return {"fraud_score": 0.0, "alerts": []}

        extension = call_data.get("from")
        destination = call_data.get("to")
        duration = call_data.get("duration", 0)
        timestamp = call_data.get("timestamp", datetime.now(UTC))

        # Track call
        self.call_history[extension].append(
            {
                "destination": destination,
                "duration": duration,
                "timestamp": timestamp,
                "cost": call_data.get("cost", 0.0),
            }
        )

        # Analyze patterns
        fraud_score = 0.0
        alerts = []

        # Check call frequency
        freq_score, freq_alerts = self._check_call_frequency(extension)
        fraud_score += freq_score
        alerts.extend(freq_alerts)

        # Check international calls
        intl_score, intl_alerts = self._check_international_calls(extension, destination)
        fraud_score += intl_score
        alerts.extend(intl_alerts)

        # Check call duration
        duration_score, duration_alerts = self._check_call_duration(duration)
        fraud_score += duration_score
        alerts.extend(duration_alerts)

        # Check unusual hours
        hour_score, hour_alerts = self._check_unusual_hours(timestamp)
        fraud_score += hour_score
        alerts.extend(hour_alerts)

        # Check cost patterns
        cost_score, cost_alerts = self._check_cost_patterns(extension)
        fraud_score += cost_score
        alerts.extend(cost_alerts)

        # Store alerts if fraud detected
        if fraud_score > 0.5:
            # Store only essential info, not full call_data (avoid exposing sensitive info)
            self.alerts.append(
                {
                    "extension": extension,
                    "destination": destination,
                    "fraud_score": fraud_score,
                    "alerts": alerts,
                    "timestamp": timestamp,
                    "call_duration": call_data.get("duration", 0),
                    "call_cost": call_data.get("cost", 0.0),
                }
            )

            self.logger.warning(
                f"Fraud detected for extension {extension}: score={fraud_score:.2f}"
            )
            for alert in alerts:
                self.logger.warning(f"  - {alert}")

        return {
            "fraud_score": fraud_score,
            "alerts": alerts,
            "recommendation": (
                "block" if fraud_score > 0.8 else "monitor" if fraud_score > 0.5 else "allow"
            ),
        }

    def _check_call_frequency(self, extension: str) -> tuple:
        """Check for unusually high call frequency"""
        score = 0.0
        alerts = []

        if extension not in self.call_history:
            return score, alerts

        # Count calls in last hour
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        recent_calls = [c for c in self.call_history[extension] if c["timestamp"] > cutoff]

        if len(recent_calls) > self.max_calls_per_hour:
            score = 0.3
            alerts.append(f"High call frequency: {len(recent_calls)} calls in last hour")

        return score, alerts

    def _check_international_calls(self, extension: str, destination: str) -> tuple:
        """Check for excessive international calls"""
        score = 0.0
        alerts = []

        # Simple check: international numbers typically start with + or 011
        is_international = destination.startswith(("+", "011"))

        if not is_international:
            return score, alerts

        # Count international calls today
        cutoff = datetime.now(UTC) - timedelta(days=1)
        intl_calls = [
            c
            for c in self.call_history.get(extension, [])
            if c["timestamp"] > cutoff
            and (c["destination"].startswith("+") or c["destination"].startswith("011"))
        ]

        if len(intl_calls) > self.max_international_calls_per_day:
            score = 0.4
            alerts.append(f"Excessive international calls: {len(intl_calls)} in last 24 hours")

        return score, alerts

    def _check_call_duration(self, duration: int) -> tuple:
        """Check for unusually long calls"""
        score = 0.0
        alerts = []

        if duration > self.max_call_duration:
            score = 0.2
            alerts.append(f"Unusually long call: {duration}s (max: {self.max_call_duration}s)")

        return score, alerts

    def _check_unusual_hours(self, timestamp: datetime) -> tuple:
        """Check if call is during unusual hours"""
        score = 0.0
        alerts = []

        hour = timestamp.hour

        # Check if between unusual_hour_start and unusual_hour_end
        if self.unusual_hour_start > self.unusual_hour_end:
            # Spans midnight
            is_unusual = hour >= self.unusual_hour_start or hour < self.unusual_hour_end
        else:
            is_unusual = self.unusual_hour_start <= hour < self.unusual_hour_end

        if is_unusual:
            score = 0.1
            alerts.append(f"Call during unusual hours: {hour}:00")

        return score, alerts

    def _check_cost_patterns(self, extension: str) -> tuple:
        """Check for unusual cost patterns"""
        score = 0.0
        alerts = []

        if extension not in self.call_history:
            return score, alerts

        # Calculate total cost today
        cutoff = datetime.now(UTC) - timedelta(days=1)
        daily_cost = sum(c["cost"] for c in self.call_history[extension] if c["timestamp"] > cutoff)

        if daily_cost > self.max_cost_per_day:
            score = 0.3
            alerts.append(f"High daily cost: ${daily_cost:.2f} (max: ${self.max_cost_per_day})")

        return score, alerts

    def add_blocked_pattern(self, pattern: str, reason: str) -> bool:
        """Add a number pattern to block list"""
        self.blocked_patterns.append(
            {"pattern": pattern, "reason": reason, "added_at": datetime.now(UTC)}
        )
        self.logger.info(f"Added blocked pattern: {pattern} ({reason})")
        return True

    def is_number_blocked(self, number: str) -> tuple:
        """Check if a number matches any blocked patterns"""
        for pattern in self.blocked_patterns:
            if number.startswith(pattern["pattern"]):
                return True, pattern["reason"]
        return False, None

    def get_alerts(self, extension: str | None = None, hours: int = 24) -> list[dict]:
        """Get recent fraud alerts"""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        alerts = [a for a in self.alerts if a["timestamp"] > cutoff]

        if extension:
            alerts = [a for a in alerts if a["extension"] == extension]

        return sorted(alerts, key=lambda x: x["fraud_score"], reverse=True)

    def get_extension_statistics(self, extension: str) -> dict:
        """Get call statistics for an extension"""
        if extension not in self.call_history:
            return {"total_calls": 0}

        calls = self.call_history[extension]
        cutoff_24h = datetime.now(UTC) - timedelta(days=1)
        recent_calls = [c for c in calls if c["timestamp"] > cutoff_24h]

        return {
            "total_calls": len(calls),
            "calls_24h": len(recent_calls),
            "total_duration": sum(c["duration"] for c in calls),
            "total_cost": sum(c["cost"] for c in calls),
            "international_calls": sum(
                1
                for c in calls
                if c["destination"].startswith("+") or c["destination"].startswith("011")
            ),
        }

    def cleanup_old_data(self, days: int = 30) -> None:
        """Clean up old call history"""
        cutoff = datetime.now(UTC) - timedelta(days=days)

        for extension in self.call_history:
            self.call_history[extension] = [
                c for c in self.call_history[extension] if c["timestamp"] > cutoff
            ]

        self.alerts = [a for a in self.alerts if a["timestamp"] > cutoff]

        self.logger.info(f"Cleaned up fraud detection data older than {days} days")

    def get_statistics(self) -> dict:
        """Get fraud detection statistics"""
        return {
            "enabled": self.enabled,
            "total_extensions_tracked": len(self.call_history),
            "total_alerts": len(self.alerts),
            "blocked_patterns": len(self.blocked_patterns),
            "alerts_24h": len(self.get_alerts(hours=24)),
        }
