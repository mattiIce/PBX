"""
SIP Trunk Support
Allows external calls through SIP providers
Includes health monitoring and automatic failover
"""

import threading
import time
from datetime import UTC, datetime
from enum import Enum

from pbx.utils.e911_protection import E911Protection
from pbx.utils.logger import get_logger
from typing import Any


class TrunkStatus(Enum):
    """SIP trunk status"""

    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    FAILED = "failed"
    DISABLED = "disabled"
    DEGRADED = "degraded"  # Partial failure


class TrunkHealthStatus(Enum):
    """Health status of trunk"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


class SIPTrunk:
    """Represents a SIP trunk connection"""

    def __init__(
        self,
        trunk_id: str,
        name: str,
        host: str,
        username: str,
        password: str,
        port: int =5060,
        codec_preferences: list | None =None,
        priority: int =100,
        max_channels: int =10,
        health_check_interval: int =60,
    ) -> None:
        """
        Initialize SIP trunk

        Args:
            trunk_id: Trunk identifier
            name: Trunk name
            host: SIP provider host
            username: SIP username
            password: SIP password
            port: SIP port (default 5060)
            codec_preferences: list of preferred codecs
            priority: Trunk priority (lower is better, for failover)
            max_channels: Maximum concurrent channels
            health_check_interval: Seconds between health checks
        """
        self.trunk_id = trunk_id
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.codec_preferences = codec_preferences or ["G.711", "G.729"]
        self.status = TrunkStatus.UNREGISTERED
        self.priority = priority
        self.max_channels = max_channels
        self.channels_available = max_channels
        self.channels_in_use = 0
        self.health_check_interval = health_check_interval
        self.logger = get_logger()

        # Health monitoring
        self.health_status = TrunkHealthStatus.DOWN
        self.last_health_check = None
        self.last_successful_call = None
        self.last_failed_call = None
        self.consecutive_failures = 0
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.last_registration_attempt = None
        self.registration_failures = 0

        # Performance metrics
        self.average_call_setup_time = 0.0
        self.call_setup_times = []

        # Failover tracking
        self.failover_count = 0
        self.last_failover_time = None

    def register(self) -> bool:
        """
        Register trunk with provider

        Returns:
            True if registration successful
        """
        self.logger.info(f"Registering SIP trunk {self.name} with {self.host}")
        self.last_registration_attempt = datetime.now(UTC)

        # In a real implementation:
        # 1. Send SIP REGISTER to provider
        # 2. Handle authentication challenge
        # 3. Maintain registration with periodic re-REGISTER

        self.status = TrunkStatus.REGISTERED
        self.health_status = TrunkHealthStatus.HEALTHY
        self.registration_failures = 0
        self.consecutive_failures = 0
        return True

    def unregister(self) -> None:
        """Unregister trunk"""
        self.logger.info(f"Unregistering SIP trunk {self.name}")
        self.status = TrunkStatus.UNREGISTERED
        self.health_status = TrunkHealthStatus.DOWN

    def can_make_call(self) -> bool:
        """Check if trunk can make call"""
        return (
            self.status == TrunkStatus.REGISTERED
            and self.health_status in [TrunkHealthStatus.HEALTHY, TrunkHealthStatus.WARNING]
            and self.channels_in_use < self.channels_available
        )

    def allocate_channel(self) -> bool:
        """Allocate channel for outbound call"""
        if self.can_make_call():
            self.channels_in_use += 1
            self.total_calls += 1
            return True
        return False

    def release_channel(self) -> None:
        """Release channel"""
        if self.channels_in_use > 0:
            self.channels_in_use -= 1

    def record_successful_call(self, setup_time: float | None = None) -> None:
        """Record successful call"""
        self.successful_calls += 1
        self.last_successful_call = datetime.now(UTC)
        self.consecutive_failures = 0

        if setup_time is not None:
            self.call_setup_times.append(setup_time)
            # Keep only last 100 call setup times
            if len(self.call_setup_times) > 100:
                self.call_setup_times.pop(0)
            self.average_call_setup_time = sum(self.call_setup_times) / len(self.call_setup_times)

        # Update health status based on success rate
        self._update_health_status()

    def record_failed_call(self, reason: str | None = None) -> None:
        """Record failed call"""
        self.failed_calls += 1
        self.last_failed_call = datetime.now(UTC)
        self.consecutive_failures += 1

        self.logger.warning(f"Call failed on trunk {self.name}: {reason or 'Unknown'}")

        # Update health status
        self._update_health_status()

        # Mark trunk as failed if too many consecutive failures
        if self.consecutive_failures >= 5:
            self.logger.error(
                f"Trunk {self.name} marked as FAILED after {self.consecutive_failures} consecutive failures"
            )
            self.status = TrunkStatus.FAILED
            self.health_status = TrunkHealthStatus.DOWN

    def _update_health_status(self) -> None:
        """Update health status based on metrics"""
        if self.total_calls < 10:
            # Not enough data yet
            return

        success_rate = self.successful_calls / self.total_calls

        if success_rate >= 0.95:
            self.health_status = TrunkHealthStatus.HEALTHY
        elif success_rate >= 0.80:
            self.health_status = TrunkHealthStatus.WARNING
        elif success_rate >= 0.50:
            self.health_status = TrunkHealthStatus.CRITICAL
        else:
            self.health_status = TrunkHealthStatus.DOWN

    def check_health(self) -> TrunkHealthStatus:
        """
        Perform health check on trunk

        Returns:
            Current health status
        """
        self.last_health_check = datetime.now(UTC)

        # Check if trunk is registered
        if self.status != TrunkStatus.REGISTERED:
            self.health_status = TrunkHealthStatus.DOWN
            return self.health_status

        # Check consecutive failures
        if self.consecutive_failures >= 5:
            self.health_status = TrunkHealthStatus.DOWN
        elif self.consecutive_failures >= 3:
            self.health_status = TrunkHealthStatus.CRITICAL
        elif self.consecutive_failures >= 1:
            self.health_status = TrunkHealthStatus.WARNING

        # Check last successful call time
        if self.last_successful_call:
            time_since_success = (datetime.now(UTC) - self.last_successful_call).total_seconds()
            if time_since_success > 3600:  # 1 hour
                self.health_status = TrunkHealthStatus.CRITICAL

        # In a real implementation, would:
        # 1. Send OPTIONS ping to trunk
        # 2. Measure response time
        # 3. Check registration status
        # 4. Verify DNS resolution

        self.logger.debug(f"Health check for {self.name}: {self.health_status.value}")
        return self.health_status

    def get_success_rate(self) -> float:
        """Get call success rate"""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    def get_health_metrics(self) -> dict:
        """Get comprehensive health metrics"""
        return {
            "health_status": self.health_status.value,
            "last_health_check": (
                self.last_health_check.isoformat() if self.last_health_check else None
            ),
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": self.get_success_rate(),
            "consecutive_failures": self.consecutive_failures,
            "average_setup_time": self.average_call_setup_time,
            "last_successful_call": (
                self.last_successful_call.isoformat() if self.last_successful_call else None
            ),
            "last_failed_call": (
                self.last_failed_call.isoformat() if self.last_failed_call else None
            ),
            "failover_count": self.failover_count,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "trunk_id": self.trunk_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "status": self.status.value,
            "health_status": self.health_status.value,
            "priority": self.priority,
            "max_channels": self.max_channels,
            "channels_available": self.channels_available,
            "channels_in_use": self.channels_in_use,
            "codec_preferences": self.codec_preferences,
            "success_rate": self.get_success_rate(),
            "consecutive_failures": self.consecutive_failures,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
        }


class OutboundRule:
    """Routing rule for outbound calls"""

    def __init__(self, rule_id: str, pattern: str, trunk_id: str, prepend: str ="", strip: int =0) -> None:
        """
        Initialize outbound rule

        Args:
            rule_id: Rule identifier
            pattern: Dial pattern (regex)
            trunk_id: Trunk to use
            prepend: Digits to prepend
            strip: Number of digits to strip from beginning
        """
        self.rule_id = rule_id
        self.pattern = pattern
        self.trunk_id = trunk_id
        self.prepend = prepend
        self.strip = strip

    def matches(self, number: str) -> bool:
        """
        Check if number matches pattern

        Args:
            number: Dialed number

        Returns:
            True if matches
        """
        import re

        return bool(re.match(self.pattern, number))

    def transform_number(self, number: str) -> str:
        """
        Transform number according to rule

        Args:
            number: Original number

        Returns:
            Transformed number
        """
        # Strip digits
        if self.strip > 0:
            number = number[self.strip :]

        # Prepend digits
        if self.prepend:
            number = self.prepend + number

        return number


class SIPTrunkSystem:
    """Manages SIP trunks for external calls with health monitoring and failover"""

    def __init__(self, config: Any | None =None) -> None:
        """Initialize SIP trunk system

        Args:
            config: Configuration object (optional)
        """
        self.trunks = {}
        self.outbound_rules = []
        self.logger = get_logger()
        self.e911_protection = E911Protection(config)

        # Health monitoring
        self.health_check_enabled = True
        self.health_check_thread = None
        self.health_check_interval = 60  # seconds
        self.monitoring_active = False

        # Failover configuration
        self.failover_enabled = True
        self.auto_recovery_enabled = True
        self.failover_threshold = 3  # consecutive failures before failover

    def start_health_monitoring(self) -> None:
        """Start health monitoring thread"""
        if self.monitoring_active:
            self.logger.warning("Health monitoring already active")
            return

        self.monitoring_active = True
        self.health_check_thread = threading.Thread(
            target=self._health_monitoring_loop, daemon=True
        )
        self.health_check_thread.start()
        self.logger.info("Started SIP trunk health monitoring")

    def stop_health_monitoring(self) -> None:
        """Stop health monitoring thread"""
        self.monitoring_active = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        self.logger.info("Stopped SIP trunk health monitoring")

    def _health_monitoring_loop(self) -> None:
        """Background thread for health monitoring"""
        while self.monitoring_active:
            try:
                self._perform_health_checks()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(5)

    def _perform_health_checks(self) -> None:
        """Perform health checks on all trunks"""
        for trunk in self.trunks.values():
            try:
                old_status = trunk.health_status
                new_status = trunk.check_health()

                # Log status changes
                if old_status != new_status:
                    self.logger.warning(
                        f"Trunk {trunk.name} health changed: {old_status.value} -> {new_status.value}"
                    )

                    # Trigger failover if trunk went down
                    if new_status == TrunkHealthStatus.DOWN and self.failover_enabled:
                        self._handle_trunk_failure(trunk)
            except Exception as e:
                self.logger.error(f"Error checking health of trunk {trunk.name}: {e}")

    def add_trunk(self, trunk: Any) -> None:
        """
        Add SIP trunk

        Args:
            trunk: SIPTrunk object
        """
        self.trunks[trunk.trunk_id] = trunk
        self.logger.info(f"Added SIP trunk: {trunk.name}")

    def remove_trunk(self, trunk_id: str) -> None:
        """Remove SIP trunk"""
        if trunk_id in self.trunks:
            trunk = self.trunks[trunk_id]
            trunk.unregister()
            del self.trunks[trunk_id]
            self.logger.info(f"Removed SIP trunk: {trunk_id}")

    def get_trunk(self, trunk_id: str) -> Any | None:
        """Get trunk by ID"""
        return self.trunks.get(trunk_id)

    def register_all(self) -> None:
        """Register all trunks"""
        for trunk in self.trunks.values():
            trunk.register()

    def add_outbound_rule(self, rule: Any) -> None:
        """
        Add outbound routing rule

        Args:
            rule: OutboundRule object
        """
        self.outbound_rules.append(rule)
        self.logger.info(f"Added outbound rule: {rule.pattern} -> trunk {rule.trunk_id}")

    def route_outbound(self, number: str) -> tuple:
        """
        Route outbound call

        Args:
            number: Dialed number

        Returns:
            tuple of (trunk, transformed_number) or (None, None)
        """
        # Block E911 calls in test mode
        if self.e911_protection.block_if_e911(number, context="route_outbound"):
            self.logger.error(f"E911 call to {number} blocked by protection system")
            return (None, None)

        for rule in self.outbound_rules:
            if rule.matches(number):
                trunk = self.get_trunk(rule.trunk_id)

                if trunk and trunk.can_make_call():
                    transformed = rule.transform_number(number)
                    self.logger.info(f"Routing {number} -> {transformed} via trunk {trunk.name}")
                    return (trunk, transformed)

        self.logger.warning(f"No route found for outbound number {number}")
        return (None, None)

    def get_trunk_status(self) -> dict:
        """Get status of all trunks"""
        return [trunk.to_dict() for trunk in self.trunks.values()]

    def make_outbound_call(self, from_extension: str, to_number: str) -> bool:
        """
        Initiate outbound call

        Args:
            from_extension: Calling extension
            to_number: External number to call

        Returns:
            True if call initiated
        """
        # Block E911 calls in test mode
        if self.e911_protection.block_if_e911(to_number, context="make_outbound_call"):
            self.logger.error(
                f"E911 call from {from_extension} to {to_number} blocked by protection system"
            )
            return False

        trunk, transformed_number = self.route_outbound(to_number)

        if not trunk:
            return False

        if trunk.allocate_channel():
            self.logger.info(f"Making outbound call from {from_extension} to {transformed_number}")

            # In a real implementation:
            # 1. Build SIP INVITE to trunk
            # 2. Include authentication
            # 3. Bridge with internal extension
            # 4. Handle call progress

            return True

        return False

    def _handle_trunk_failure(self, failed_trunk: SIPTrunk) -> None:
        """
        Handle trunk failure and initiate failover if needed

        Args:
            failed_trunk: The trunk that failed
        """
        self.logger.error(f"Handling failure of trunk: {failed_trunk.name}")

        # Mark failover time
        failed_trunk.last_failover_time = datetime.now(UTC)
        failed_trunk.failover_count += 1

        # Find rules using this trunk
        affected_rules = [
            rule for rule in self.outbound_rules if rule.trunk_id == failed_trunk.trunk_id
        ]

        if not affected_rules:
            return

        # Find alternative trunks
        alternative_trunks = self._get_available_trunks_by_priority()

        if not alternative_trunks:
            self.logger.critical(
                f"No alternative trunks available for failover from {failed_trunk.name}"
            )
            return

        # Use highest priority alternative
        failover_trunk = alternative_trunks[0]

        self.logger.warning(
            f"Failing over from trunk {failed_trunk.name} to {failover_trunk.name} "
            f"for {len(affected_rules)} routes"
        )

        # In a full implementation, would:
        # 1. Temporarily reroute affected rules to failover trunk
        # 2. Notify administrators
        # 3. Monitor for recovery of failed trunk
        # 4. Automatically restore when recovered (if auto_recovery_enabled)

    def _get_available_trunks_by_priority(self) -> list[SIPTrunk]:
        """
        Get list of available trunks sorted by priority

        Returns:
            list of available trunks
        """
        available = [
            trunk
            for trunk in self.trunks.values()
            if trunk.status == TrunkStatus.REGISTERED
            and trunk.health_status in [TrunkHealthStatus.HEALTHY, TrunkHealthStatus.WARNING]
        ]

        # Sort by priority (lower is better)
        available.sort(key=lambda t: t.priority)
        return available

    def route_outbound_with_failover(self, number: str) -> tuple[SIPTrunk | None, str | None]:
        """
        Route outbound call with automatic failover

        Args:
            number: Dialed number

        Returns:
            tuple of (trunk, transformed_number) or (None, None)
        """
        # Block E911 calls in test mode
        if self.e911_protection.block_if_e911(number, context="route_outbound_with_failover"):
            self.logger.error(f"E911 call to {number} blocked by protection system")
            return (None, None)

        # Try primary trunk first
        for rule in self.outbound_rules:
            if rule.matches(number):
                trunk = self.get_trunk(rule.trunk_id)

                if trunk and trunk.can_make_call():
                    transformed = rule.transform_number(number)
                    self.logger.info(f"Routing {number} -> {transformed} via trunk {trunk.name}")
                    return (trunk, transformed)
                if trunk:
                    # Primary trunk unavailable, try failover
                    self.logger.warning(
                        f"Primary trunk {trunk.name} unavailable (status: {trunk.status.value}, "
                        f"health: {trunk.health_status.value})"
                    )

                    if self.failover_enabled:
                        failover_trunk = self._find_failover_trunk(trunk)
                        if failover_trunk:
                            transformed = rule.transform_number(number)
                            self.logger.warning(
                                f"Failover: Routing {number} -> {transformed} via trunk {failover_trunk.name}"
                            )
                            return (failover_trunk, transformed)

        self.logger.warning(f"No route found for outbound number {number}")
        return (None, None)

    def _find_failover_trunk(self, primary_trunk: SIPTrunk) -> SIPTrunk | None:
        """
        Find suitable failover trunk

        Args:
            primary_trunk: The primary trunk that failed

        Returns:
            Alternative trunk or None
        """
        available_trunks = self._get_available_trunks_by_priority()

        # Exclude the failed trunk
        available_trunks = [t for t in available_trunks if t.trunk_id != primary_trunk.trunk_id]

        if available_trunks:
            return available_trunks[0]

        return None

    def get_trunk_health_summary(self) -> dict:
        """
        Get health summary of all trunks

        Returns:
            Dictionary with health statistics
        """
        summary = {
            "total_trunks": len(self.trunks),
            "healthy": 0,
            "warning": 0,
            "critical": 0,
            "down": 0,
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "trunks": [],
        }

        for trunk in self.trunks.values():
            # Count by health status
            if trunk.health_status == TrunkHealthStatus.HEALTHY:
                summary["healthy"] += 1
            elif trunk.health_status == TrunkHealthStatus.WARNING:
                summary["warning"] += 1
            elif trunk.health_status == TrunkHealthStatus.CRITICAL:
                summary["critical"] += 1
            elif trunk.health_status == TrunkHealthStatus.DOWN:
                summary["down"] += 1

            # Aggregate call stats
            summary["total_calls"] += trunk.total_calls
            summary["successful_calls"] += trunk.successful_calls
            summary["failed_calls"] += trunk.failed_calls

            # Add trunk details
            summary["trunks"].append(
                {
                    "trunk_id": trunk.trunk_id,
                    "name": trunk.name,
                    "status": trunk.status.value,
                    "health": trunk.health_status.value,
                    "success_rate": trunk.get_success_rate(),
                    "metrics": trunk.get_health_metrics(),
                }
            )

        # Calculate overall success rate
        if summary["total_calls"] > 0:
            summary["overall_success_rate"] = summary["successful_calls"] / summary["total_calls"]
        else:
            summary["overall_success_rate"] = 0.0

        return summary


# Global instance
_trunk_manager = None


def get_trunk_manager(config: Any | None =None) -> SIPTrunkSystem:
    """
    Get or create SIP trunk manager instance.

    Args:
        config: Configuration dict. Required for first initialization.

    Returns:
        SIPTrunkSystem instance or None if not yet initialized.
        Callers must check for None before using.
    """
    global _trunk_manager
    if _trunk_manager is None and config is not None:
        _trunk_manager = SIPTrunkSystem(config)
    return _trunk_manager
