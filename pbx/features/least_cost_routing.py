"""
Least-Cost Routing (LCR) System
Automatically selects the most cost-effective trunk for outbound calls
based on destination, time of day, and carrier rates
"""

import re
import sqlite3
from datetime import UTC, datetime, time
from typing import Any

from pbx.utils.logger import get_logger


class DialPattern:
    """Represents a dial pattern for routing"""

    def __init__(self, pattern: str, description: str = "") -> None:
        """
        Initialize dial pattern

        Args:
            pattern: Regex pattern to match dialed numbers
            description: Human-readable description
        """
        self.pattern = pattern
        self.regex = re.compile(pattern)
        self.description = description

    def matches(self, number: str) -> bool:
        """Check if number matches this pattern"""
        return bool(self.regex.match(number))


class RateEntry:
    """Represents a rate for a specific destination pattern and trunk"""

    def __init__(
        self,
        trunk_id: str,
        pattern: DialPattern,
        rate_per_minute: float,
        connection_fee: float = 0.0,
        minimum_seconds: int = 0,
        billing_increment: int = 1,
    ) -> None:
        """
        Initialize rate entry

        Args:
            trunk_id: Trunk identifier
            pattern: Dial pattern this rate applies to
            rate_per_minute: Cost per minute in dollars
            connection_fee: One-time connection fee in dollars
            minimum_seconds: Minimum billable seconds
            billing_increment: Billing increment in seconds (e.g., 6 for 6-second increments)
        """
        self.trunk_id = trunk_id
        self.pattern = pattern
        self.rate_per_minute = rate_per_minute
        self.connection_fee = connection_fee
        self.minimum_seconds = minimum_seconds
        self.billing_increment = billing_increment

    def calculate_cost(self, duration_seconds: int) -> float:
        """
        Calculate cost for a call duration

        Args:
            duration_seconds: Call duration in seconds

        Returns:
            Cost in dollars
        """
        # Apply minimum duration
        billable_seconds = max(duration_seconds, self.minimum_seconds)

        # Round up to billing increment
        if self.billing_increment > 1:
            remainder = billable_seconds % self.billing_increment
            if remainder > 0:
                billable_seconds += self.billing_increment - remainder

        # Calculate cost
        minutes = billable_seconds / 60.0
        call_cost = (minutes * self.rate_per_minute) + self.connection_fee

        return round(call_cost, 4)


class TimeBasedRate:
    """Represents time-based rate modifiers"""

    def __init__(
        self,
        name: str,
        start_time: time,
        end_time: time,
        days_of_week: list[int],  # 0=Monday, 6=Sunday
        rate_multiplier: float = 1.0,
    ) -> None:
        """
        Initialize time-based rate

        Args:
            name: Name of time period (e.g., "Peak Hours", "Weekend")
            start_time: Start time
            end_time: End time
            days_of_week: list of applicable days (0=Monday, 6=Sunday)
            rate_multiplier: Multiplier for rates during this period
        """
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
        self.days_of_week = days_of_week
        self.rate_multiplier = rate_multiplier

    def applies_now(self) -> bool:
        """Check if this time period applies now"""
        now = datetime.now(UTC)
        current_time = now.time()
        current_day = now.weekday()

        # Check day of week
        if current_day not in self.days_of_week:
            return False

        # Check time range
        if self.start_time <= self.end_time:
            # Normal case (e.g., 9:00 AM - 5:00 PM)
            return self.start_time <= current_time <= self.end_time
        # Crosses midnight (e.g., 11:00 PM - 3:00 AM)
        return current_time >= self.start_time or current_time <= self.end_time


class LeastCostRouting:
    """Least-Cost Routing engine with database persistence"""

    def __init__(self, pbx: Any) -> None:
        """
        Initialize LCR engine

        Args:
            pbx: PBX instance
        """
        self.pbx = pbx
        self.logger = get_logger()

        # Get database path from PBX config
        if hasattr(pbx, "config") and pbx.config:
            self.db_path = pbx.config.get("database", {}).get("path", "pbx.db")
        else:
            self.db_path = "pbx.db"

        # Initialize database
        self._init_database()

        # Rate database - load from DB
        self.rate_entries: list[RateEntry] = []
        self.time_based_rates: list[TimeBasedRate] = []
        self._load_from_database()

        # Configuration
        self.enabled = True
        self.prefer_quality = False  # If True, use quality metrics in addition to cost
        self.quality_weight = 0.3  # Weight of quality in routing decision (0-1)

        # Statistics
        self.total_routes = 0
        self.cost_savings = 0.0
        self.routing_decisions = []  # Last 100 routing decisions

        self.logger.info(
            f"Least-Cost Routing engine initialized with {len(self.rate_entries)} rates"
        )

    def _init_database(self) -> None:
        """Initialize database tables for LCR persistence"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create LCR rates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lcr_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trunk_id TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    description TEXT,
                    rate_per_minute REAL NOT NULL,
                    connection_fee REAL DEFAULT 0.0,
                    minimum_seconds INTEGER DEFAULT 0,
                    billing_increment INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trunk_id, pattern)
                )
            """)

            # Create time-based rates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lcr_time_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    start_hour INTEGER NOT NULL,
                    start_minute INTEGER NOT NULL,
                    end_hour INTEGER NOT NULL,
                    end_minute INTEGER NOT NULL,
                    days_of_week TEXT NOT NULL,
                    rate_multiplier REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()
            self.logger.info("LCR database tables initialized")
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing LCR database: {e}")

    def _load_from_database(self) -> None:
        """Load rates and time-based rates from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Load regular rates
            cursor.execute("""
                SELECT trunk_id, pattern, description, rate_per_minute,
                       connection_fee, minimum_seconds, billing_increment
                FROM lcr_rates
            """)
            rows = cursor.fetchall()

            for row in rows:
                dial_pattern = DialPattern(row[1], row[2] or "")
                rate_entry = RateEntry(
                    trunk_id=row[0],
                    pattern=dial_pattern,
                    rate_per_minute=row[3],
                    connection_fee=row[4],
                    minimum_seconds=row[5],
                    billing_increment=row[6],
                )
                self.rate_entries.append(rate_entry)

            # Load time-based rates
            cursor.execute("""
                SELECT name, start_hour, start_minute, end_hour, end_minute,
                       days_of_week, rate_multiplier
                FROM lcr_time_rates
            """)
            time_rows = cursor.fetchall()

            for row in time_rows:
                # Parse days_of_week from comma-separated string
                days = [int(d) for d in row[5].split(",")]
                time_rate = TimeBasedRate(
                    name=row[0],
                    start_time=time(row[1], row[2]),
                    end_time=time(row[3], row[4]),
                    days_of_week=days,
                    rate_multiplier=row[6],
                )
                self.time_based_rates.append(time_rate)

            conn.close()

            if rows:
                self.logger.info(f"Loaded {len(rows)} LCR rates from database")
            if time_rows:
                self.logger.info(f"Loaded {len(time_rows)} time-based rates from database")

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Error loading LCR rates from database: {e}")

    def _save_rate_to_db(
        self,
        trunk_id: str,
        pattern: str,
        rate_per_minute: float,
        description: str = "",
        connection_fee: float = 0.0,
        minimum_seconds: int = 0,
        billing_increment: int = 1,
    ) -> None:
        """Save a rate entry to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO lcr_rates
                (trunk_id, pattern, description, rate_per_minute, connection_fee,
                 minimum_seconds, billing_increment, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    trunk_id,
                    pattern,
                    description,
                    rate_per_minute,
                    connection_fee,
                    minimum_seconds,
                    billing_increment,
                ),
            )

            conn.commit()
            conn.close()
            self.logger.debug(f"LCR rate saved to database: {trunk_id} - {pattern}")
        except sqlite3.Error as e:
            self.logger.error(f"Error saving LCR rate to database: {e}")

    def _save_time_rate_to_db(
        self,
        name: str,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
        days: list[int],
        multiplier: float,
    ) -> None:
        """Save a time-based rate to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Convert days list to comma-separated string
            days_str = ",".join(str(d) for d in days)

            cursor.execute(
                """
                INSERT OR REPLACE INTO lcr_time_rates
                (name, start_hour, start_minute, end_hour, end_minute,
                 days_of_week, rate_multiplier, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (name, start_hour, start_minute, end_hour, end_minute, days_str, multiplier),
            )

            conn.commit()
            conn.close()
            self.logger.debug(f"Time-based rate saved to database: {name}")
        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Error saving time-based rate to database: {e}")

    def _delete_all_rates_from_db(self) -> None:
        """Delete all rates from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lcr_rates")
            conn.commit()
            conn.close()
            self.logger.info("All LCR rates deleted from database")
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting LCR rates from database: {e}")

    def _delete_all_time_rates_from_db(self) -> None:
        """Delete all time-based rates from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lcr_time_rates")
            conn.commit()
            conn.close()
            self.logger.info("All time-based rates deleted from database")
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting time-based rates from database: {e}")

    def add_rate(
        self,
        trunk_id: str,
        pattern: str,
        rate_per_minute: float,
        description: str = "",
        connection_fee: float = 0.0,
        minimum_seconds: int = 0,
        billing_increment: int = 1,
    ) -> bool:
        """
        Add a rate entry and persist to database

        Args:
            trunk_id: Trunk identifier
            pattern: Dial pattern regex
            rate_per_minute: Cost per minute
            description: Pattern description
            connection_fee: Connection fee
            minimum_seconds: Minimum billable seconds
            billing_increment: Billing increment
        """
        if not self.enabled:
            self.logger.error("Cannot add rate: Least cost routing feature is not enabled")
            return False

        dial_pattern = DialPattern(pattern, description)
        rate_entry = RateEntry(
            trunk_id=trunk_id,
            pattern=dial_pattern,
            rate_per_minute=rate_per_minute,
            connection_fee=connection_fee,
            minimum_seconds=minimum_seconds,
            billing_increment=billing_increment,
        )
        self.rate_entries.append(rate_entry)

        # Save to database
        self._save_rate_to_db(
            trunk_id,
            pattern,
            rate_per_minute,
            description,
            connection_fee,
            minimum_seconds,
            billing_increment,
        )

        self.logger.info(f"Added LCR rate: {description} via {trunk_id} at ${rate_per_minute}/min")
        return True

    def add_time_based_rate(
        self,
        name: str,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
        days: list[int],
        multiplier: float,
    ) -> bool:
        """
        Add time-based rate modifier and persist to database

        Args:
            name: Period name
            start_hour: Start hour (0-23)
            start_minute: Start minute (0-59)
            end_hour: End hour (0-23)
            end_minute: End minute (0-59)
            days: Days of week (0=Monday, 6=Sunday)
            multiplier: Rate multiplier
        """
        if not self.enabled:
            self.logger.error(
                "Cannot add time-based rate: Least cost routing feature is not enabled"
            )
            return False

        start_time = time(start_hour, start_minute)
        end_time = time(end_hour, end_minute)

        time_rate = TimeBasedRate(
            name=name,
            start_time=start_time,
            end_time=end_time,
            days_of_week=days,
            rate_multiplier=multiplier,
        )
        self.time_based_rates.append(time_rate)

        # Save to database
        self._save_time_rate_to_db(
            name, start_hour, start_minute, end_hour, end_minute, days, multiplier
        )

        self.logger.info(f"Added time-based rate: {name} ({multiplier}x)")
        return True

    def get_applicable_rates(self, dialed_number: str) -> list[tuple[str, float]]:
        """
        Get applicable rates for a dialed number

        Args:
            dialed_number: Number being dialed

        Returns:
            list of (trunk_id, estimated_cost) tuples sorted by cost
        """
        applicable_rates = []

        # Find matching rate entries
        for rate_entry in self.rate_entries:
            if rate_entry.pattern.matches(dialed_number):
                # Calculate cost for average call (assume 3 minutes)
                estimated_cost = rate_entry.calculate_cost(180)

                # Apply time-based modifiers
                for time_rate in self.time_based_rates:
                    if time_rate.applies_now():
                        estimated_cost *= time_rate.rate_multiplier

                applicable_rates.append((rate_entry.trunk_id, estimated_cost))

        # Sort by cost (lowest first)
        applicable_rates.sort(key=lambda x: x[1])

        return applicable_rates

    def select_trunk(self, dialed_number: str, available_trunks: list[str]) -> str | None:
        """
        Select the best trunk for a call using LCR

        Args:
            dialed_number: Number being dialed
            available_trunks: list of available trunk IDs

        Returns:
            Selected trunk ID or None
        """
        if not self.enabled:
            return None

        # Get applicable rates
        rates = self.get_applicable_rates(dialed_number)

        if not rates:
            self.logger.warning(f"No LCR rates found for {dialed_number}")
            return None

        # Filter to only available trunks
        available_rates = [(trunk, cost) for trunk, cost in rates if trunk in available_trunks]

        if not available_rates:
            self.logger.warning(f"No available trunks for {dialed_number}")
            return None

        # Select best trunk
        if self.prefer_quality and hasattr(self.pbx, "trunk_manager"):
            # Use quality metrics in addition to cost
            selected_trunk = self._select_with_quality(available_rates)
        else:
            # Pure cost-based selection
            selected_trunk = available_rates[0][0]

        # Record decision
        decision = {
            "timestamp": datetime.now(UTC).isoformat(),
            "number": dialed_number,
            "selected_trunk": selected_trunk,
            "estimated_cost": available_rates[0][1],
            "alternatives": len(available_rates) - 1,
        }
        self.routing_decisions.append(decision)

        # Keep only last 100 decisions
        if len(self.routing_decisions) > 100:
            self.routing_decisions = self.routing_decisions[-100:]

        self.total_routes += 1
        self.logger.info(
            f"LCR selected trunk {selected_trunk} for {dialed_number} "
            f"(est. cost: ${available_rates[0][1]:.4f})"
        )

        return selected_trunk

    def _select_with_quality(self, available_rates: list[tuple[str, float]]) -> str:
        """
        Select trunk considering both cost and quality

        Args:
            available_rates: list of (trunk_id, cost) tuples

        Returns:
            Selected trunk ID
        """
        # Get trunk quality scores (0-1, higher is better)
        trunk_scores = []

        for trunk_id, cost in available_rates:
            trunk = self.pbx.trunk_manager.get_trunk(trunk_id)

            # Calculate quality score based on success rate
            if trunk and trunk.total_calls > 0:
                quality_score = trunk.successful_calls / trunk.total_calls
            else:
                quality_score = 0.5  # Default for unknown quality

            # Normalize cost (inverse, so lower cost = higher score)
            # Assume max reasonable cost is $1/min for 3 min call
            cost_score = max(0, 1 - (cost / 3.0))

            # Combined score
            combined_score = (
                self.quality_weight * quality_score + (1 - self.quality_weight) * cost_score
            )

            trunk_scores.append((trunk_id, combined_score))

        # Sort by combined score (highest first)
        trunk_scores.sort(key=lambda x: x[1], reverse=True)

        return trunk_scores[0][0]

    def get_statistics(self) -> dict:
        """Get LCR statistics"""
        return {
            "enabled": self.enabled,
            "total_routes": self.total_routes,
            "estimated_savings": self.cost_savings,
            "rate_entries": len(self.rate_entries),
            "time_based_rates": len(self.time_based_rates),
            "recent_decisions": self.routing_decisions[-10:] if self.routing_decisions else [],
            "prefer_quality": self.prefer_quality,
            "quality_weight": self.quality_weight,
        }

    def clear_rates(self) -> None:
        """Clear all rate entries and delete from database"""
        self.rate_entries = []
        self._delete_all_rates_from_db()
        self.logger.info("Cleared all LCR rates from memory and database")

    def clear_time_rates(self) -> None:
        """Clear all time-based rates and delete from database"""
        self.time_based_rates = []
        self._delete_all_time_rates_from_db()
        self.logger.info("Cleared all time-based rates from memory and database")
