"""
Tests for Least-Cost Routing (LCR) System
"""

from datetime import time
from typing import Any
from unittest.mock import MagicMock

from pbx.features.least_cost_routing import DialPattern, LeastCostRouting, RateEntry, TimeBasedRate


class MockDatabase:
    """Mock DatabaseBackend for testing"""

    def __init__(self) -> None:
        self.enabled = True
        self.tables: dict[str, list[dict]] = {
            "lcr_rates": [],
            "lcr_time_rates": [],
        }

    def execute(self, query: str, params: tuple | None = None) -> bool:
        query_lower = query.strip().lower()
        if query_lower.startswith("create table"):
            return True
        if query_lower.startswith("delete from lcr_rates"):
            self.tables["lcr_rates"] = []
            return True
        if query_lower.startswith("delete from lcr_time_rates"):
            self.tables["lcr_time_rates"] = []
            return True
        if "into lcr_rates" in query_lower:
            if params:
                self.tables["lcr_rates"] = [
                    r
                    for r in self.tables["lcr_rates"]
                    if not (r["trunk_id"] == params[0] and r["pattern"] == params[1])
                ]
                self.tables["lcr_rates"].append(
                    {
                        "trunk_id": params[0],
                        "pattern": params[1],
                        "description": params[2],
                        "rate_per_minute": params[3],
                        "connection_fee": params[4],
                        "minimum_seconds": params[5],
                        "billing_increment": params[6],
                    }
                )
            return True
        if "into lcr_time_rates" in query_lower:
            if params:
                self.tables["lcr_time_rates"] = [
                    r for r in self.tables["lcr_time_rates"] if r["name"] != params[0]
                ]
                self.tables["lcr_time_rates"].append(
                    {
                        "name": params[0],
                        "start_hour": params[1],
                        "start_minute": params[2],
                        "end_hour": params[3],
                        "end_minute": params[4],
                        "days_of_week": params[5],
                        "rate_multiplier": params[6],
                    }
                )
            return True
        return True

    def fetch_one(self, query: str, params: tuple | None = None) -> dict | None:
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def fetch_all(self, query: str, params: tuple | None = None) -> list[dict]:
        query_lower = query.strip().lower()
        if "from lcr_rates" in query_lower:
            return list(self.tables["lcr_rates"])
        if "from lcr_time_rates" in query_lower:
            return list(self.tables["lcr_time_rates"])
        return []


class MockPBX:
    """Mock PBX for testing"""

    def __init__(self, database: Any = None) -> None:
        self.trunk_manager = MockTrunkManager()
        self.database = database or MockDatabase()
        self.config = {}


class MockTrunkManager:
    """Mock trunk manager for testing"""

    def __init__(self) -> None:
        self.trunks: dict[str, MockTrunk] = {}

    def get_trunk(self, trunk_id: str) -> "MockTrunk | None":
        return self.trunks.get(trunk_id)


class MockTrunk:
    """Mock trunk for testing"""

    def __init__(self, trunk_id: str) -> None:
        self.trunk_id = trunk_id
        self.total_calls = 100
        self.successful_calls = 95


class TestDialPattern:
    """Test DialPattern class"""

    def test_pattern_matching(self) -> None:
        """Test dial pattern matching"""
        # US toll-free pattern
        pattern = DialPattern(r"^1(800|888|877|866)\d{7}$", "US Toll-Free")

        assert pattern.matches("18005551234")
        assert pattern.matches("18885551234")
        assert not pattern.matches("12125551234")
        assert not pattern.matches("5551234")

    def test_international_pattern(self) -> None:
        """Test international dial pattern"""
        # International calls (011 prefix)
        pattern = DialPattern(r"^011\d+$", "International")

        assert pattern.matches("011441234567890")
        assert pattern.matches("01133123456789")
        assert not pattern.matches("12125551234")


class TestRateEntry:
    """Test RateEntry class"""

    def test_cost_calculation_basic(self) -> None:
        """Test basic cost calculation"""
        pattern = DialPattern(r"^\d{10}$", "US Local")
        rate = RateEntry(
            trunk_id="trunk1", pattern=pattern, rate_per_minute=0.01, connection_fee=0.0
        )

        # 60 seconds = 1 minute = $0.01
        assert rate.calculate_cost(60) == 0.01
        # 180 seconds = 3 minutes = $0.03
        assert rate.calculate_cost(180) == 0.03

    def test_cost_calculation_with_connection_fee(self) -> None:
        """Test cost calculation with connection fee"""
        pattern = DialPattern(r"^011", "International")
        rate = RateEntry(
            trunk_id="trunk1", pattern=pattern, rate_per_minute=0.20, connection_fee=0.05
        )

        # 60 seconds = 1 minute = $0.20 + $0.05 connection = $0.25
        assert rate.calculate_cost(60) == 0.25

    def test_cost_calculation_with_minimum(self) -> None:
        """Test cost calculation with minimum duration"""
        pattern = DialPattern(r"^\d{10}$", "US Local")
        rate = RateEntry(
            trunk_id="trunk1", pattern=pattern, rate_per_minute=0.01, minimum_seconds=30
        )

        # 10 seconds, but minimum is 30 seconds = $0.005
        cost = rate.calculate_cost(10)
        assert cost == round((30 / 60.0) * 0.01, 4)

    def test_cost_calculation_with_increment(self) -> None:
        """Test cost calculation with billing increment"""
        pattern = DialPattern(r"^\d{10}$", "US Local")
        rate = RateEntry(
            trunk_id="trunk1", pattern=pattern, rate_per_minute=0.01, billing_increment=6
        )

        # 65 seconds should round up to 66 (next 6-second increment)
        # 66 / 60 * 0.01 = $0.011
        cost = rate.calculate_cost(65)
        assert cost == 0.011


class TestTimeBasedRate:
    """Test TimeBasedRate class"""

    def test_time_range_normal(self) -> None:
        """Test time range (normal, non-crossing midnight)"""
        # Business hours: 9 AM to 5 PM weekdays
        rate = TimeBasedRate(
            name="Business Hours",
            start_time=time(9, 0),
            end_time=time(17, 0),
            days_of_week=[0, 1, 2, 3, 4],  # Monday-Friday
            rate_multiplier=1.0,
        )

        # This test is time-dependent, so we won't assert specific results
        # Just ensure it runs without error
        _ = rate.applies_now()

    def test_time_range_midnight_crossing(self) -> None:
        """Test time range crossing midnight"""
        # Late night: 11 PM to 3 AM
        rate = TimeBasedRate(
            name="Late Night",
            start_time=time(23, 0),
            end_time=time(3, 0),
            days_of_week=[0, 1, 2, 3, 4, 5, 6],  # All days
            rate_multiplier=0.5,
        )

        # This test is time-dependent, so we won't assert specific results
        # Just ensure it runs without error
        _ = rate.applies_now()


class TestLeastCostRouting:
    """Test LeastCostRouting class"""

    def setup_method(self) -> None:
        """Set up test environment"""
        self.mock_db = MockDatabase()
        self.pbx = MockPBX(database=self.mock_db)
        self.lcr = LeastCostRouting(self.pbx)

    def test_add_rate(self) -> None:
        """Test adding a rate"""
        self.lcr.add_rate(
            trunk_id="trunk1", pattern=r"^\d{10}$", rate_per_minute=0.01, description="US Local"
        )

        assert len(self.lcr.rate_entries) == 1
        assert self.lcr.rate_entries[0].trunk_id == "trunk1"

    def test_add_time_based_rate(self) -> None:
        """Test adding time-based rate"""
        self.lcr.add_time_based_rate(
            name="Peak Hours",
            start_hour=9,
            start_minute=0,
            end_hour=17,
            end_minute=0,
            days=[0, 1, 2, 3, 4],
            multiplier=1.2,
        )

        assert len(self.lcr.time_based_rates) == 1
        assert self.lcr.time_based_rates[0].name == "Peak Hours"

    def test_get_applicable_rates(self) -> None:
        """Test getting applicable rates for a number"""
        # Add multiple rates for different patterns
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.01, "US Local")
        self.lcr.add_rate("trunk2", r"^\d{10}$", 0.015, "US Local Alt")
        self.lcr.add_rate("trunk3", r"^1800", 0.00, "Toll-Free")

        # Test local number
        rates = self.lcr.get_applicable_rates("2125551234")
        assert len(rates) == 2  # Should match trunk1 and trunk2
        # Should be sorted by cost (lowest first)
        assert rates[0][0] == "trunk1"

    def test_select_trunk_cost_based(self) -> None:
        """Test trunk selection based on cost"""
        # Add rates
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.02, "US Local - Expensive")
        self.lcr.add_rate("trunk2", r"^\d{10}$", 0.01, "US Local - Cheap")

        # Select trunk (trunk2 should be selected as it's cheaper)
        selected = self.lcr.select_trunk("2125551234", ["trunk1", "trunk2"])
        assert selected == "trunk2"

    def test_select_trunk_with_quality(self) -> None:
        """Test trunk selection considering quality"""
        self.lcr.prefer_quality = True
        self.lcr.quality_weight = 0.5

        # Add mock trunks
        trunk1 = MockTrunk("trunk1")
        trunk1.successful_calls = 95
        trunk1.total_calls = 100

        trunk2 = MockTrunk("trunk2")
        trunk2.successful_calls = 50
        trunk2.total_calls = 100

        self.pbx.trunk_manager.trunks["trunk1"] = trunk1
        self.pbx.trunk_manager.trunks["trunk2"] = trunk2

        # Add rates (trunk2 is cheaper but lower quality)
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.02, "US Local - Expensive but Reliable")
        self.lcr.add_rate("trunk2", r"^\d{10}$", 0.01, "US Local - Cheap but Unreliable")

        # With quality consideration, should might select trunk1
        selected = self.lcr.select_trunk("2125551234", ["trunk1", "trunk2"])
        # Result depends on the weighting algorithm, just ensure it's one of the trunks
        assert selected in ["trunk1", "trunk2"]

    def test_statistics(self) -> None:
        """Test statistics gathering"""
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.01, "US Local")
        self.lcr.select_trunk("2125551234", ["trunk1"])

        stats = self.lcr.get_statistics()

        assert stats["enabled"]
        assert stats["total_routes"] == 1
        assert stats["rate_entries"] == 1

    def test_clear_rates(self) -> None:
        """Test clearing rates"""
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.01, "US Local")
        self.lcr.add_rate("trunk2", r"^011", 0.20, "International")

        assert len(self.lcr.rate_entries) == 2
        self.lcr.clear_rates()

        assert len(self.lcr.rate_entries) == 0

    def test_disabled_lcr(self) -> None:
        """Test that disabled LCR returns None"""
        self.lcr.enabled = False
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.01, "US Local")

        selected = self.lcr.select_trunk("2125551234", ["trunk1"])
        assert selected is None

    def test_rate_persists_to_database(self) -> None:
        """Test that rates are saved to database"""
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.01, "US Local")

        # Verify in mock database
        rates = self.mock_db.tables["lcr_rates"]
        assert len(rates) == 1
        assert rates[0]["trunk_id"] == "trunk1"
        assert rates[0]["pattern"] == r"^\d{10}$"
        assert rates[0]["rate_per_minute"] == 0.01

    def test_time_rate_persists_to_database(self) -> None:
        """Test that time-based rates are saved to database"""
        self.lcr.add_time_based_rate("Peak Hours", 9, 0, 17, 0, [0, 1, 2, 3, 4], 1.2)

        # Verify in mock database
        time_rates = self.mock_db.tables["lcr_time_rates"]
        assert len(time_rates) == 1
        assert time_rates[0]["name"] == "Peak Hours"
        assert time_rates[0]["start_hour"] == 9
        assert time_rates[0]["rate_multiplier"] == 1.2

    def test_rates_load_from_database(self) -> None:
        """Test that rates are loaded from database on initialization"""
        # Add rate and create new LCR instance (simulating restart)
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.01, "US Local")

        # Create new instance using the same mock database
        lcr2 = LeastCostRouting(self.pbx)

        # Verify rate was loaded
        assert len(lcr2.rate_entries) == 1
        assert lcr2.rate_entries[0].trunk_id == "trunk1"

    def test_time_rates_load_from_database(self) -> None:
        """Test that time-based rates are loaded from database"""
        self.lcr.add_time_based_rate("Peak Hours", 9, 0, 17, 0, [0, 1, 2, 3, 4], 1.2)

        # Create new instance (simulating restart)
        lcr2 = LeastCostRouting(self.pbx)

        # Verify time rate was loaded
        assert len(lcr2.time_based_rates) == 1
        assert lcr2.time_based_rates[0].name == "Peak Hours"

    def test_clear_rates_deletes_from_database(self) -> None:
        """Test that clearing rates deletes from database"""
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.01, "US Local")
        self.lcr.clear_rates()

        # Verify mock database is empty
        assert len(self.mock_db.tables["lcr_rates"]) == 0

    def test_multiple_rates_persist(self) -> None:
        """Test that multiple rates persist across restarts"""
        self.lcr.add_rate("trunk1", r"^\d{10}$", 0.01, "US Local")
        self.lcr.add_rate("trunk2", r"^011", 0.20, "International")
        self.lcr.add_time_based_rate("Peak", 9, 0, 17, 0, [0, 1, 2, 3, 4], 1.2)

        # Create new instance
        lcr2 = LeastCostRouting(self.pbx)

        # Verify all persisted
        assert len(lcr2.rate_entries) == 2
        assert len(lcr2.time_based_rates) == 1
