"""Comprehensive tests for Least-Cost Routing module."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pbx.features.least_cost_routing import RateEntry


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


class MockDatabaseError(MockDatabase):
    """Mock DatabaseBackend that raises errors on execute/fetch"""

    def __init__(self, error_on: str = "all") -> None:
        super().__init__()
        self.error_on = error_on

    def execute(self, query: str, params: tuple | None = None) -> bool:
        if self.error_on in ("all", "execute"):
            raise Exception("DB error")
        return super().execute(query, params)

    def fetch_all(self, query: str, params: tuple | None = None) -> list[dict]:
        if self.error_on in ("all", "fetch"):
            raise KeyError("fetch error")
        return super().fetch_all(query, params)


class MockDatabaseDisabled:
    """Mock DatabaseBackend that is disabled"""

    def __init__(self) -> None:
        self.enabled = False

    def execute(self, query: str, params: tuple | None = None) -> bool:
        return False

    def fetch_one(self, query: str, params: tuple | None = None) -> dict | None:
        return None

    def fetch_all(self, query: str, params: tuple | None = None) -> list[dict]:
        return []


@pytest.mark.unit
class TestDialPattern:
    """Tests for DialPattern class."""

    def test_init(self) -> None:
        from pbx.features.least_cost_routing import DialPattern

        dp = DialPattern(r"^1\d{10}$", "US Long Distance")
        assert dp.pattern == r"^1\d{10}$"
        assert dp.description == "US Long Distance"

    def test_matches_positive(self) -> None:
        from pbx.features.least_cost_routing import DialPattern

        dp = DialPattern(r"^1\d{10}$")
        assert dp.matches("12125551234") is True

    def test_matches_negative(self) -> None:
        from pbx.features.least_cost_routing import DialPattern

        dp = DialPattern(r"^1\d{10}$")
        assert dp.matches("5551234") is False

    def test_matches_empty_string(self) -> None:
        from pbx.features.least_cost_routing import DialPattern

        dp = DialPattern(r"^1\d{10}$")
        assert dp.matches("") is False

    def test_default_description(self) -> None:
        from pbx.features.least_cost_routing import DialPattern

        dp = DialPattern(r".*")
        assert dp.description == ""


@pytest.mark.unit
class TestRateEntry:
    """Tests for RateEntry class."""

    def _make_rate(self, **kwargs) -> RateEntry:
        from pbx.features.least_cost_routing import DialPattern, RateEntry

        defaults = {
            "trunk_id": "trunk-1",
            "pattern": DialPattern(r".*"),
            "rate_per_minute": 0.05,
            "connection_fee": 0.0,
            "minimum_seconds": 0,
            "billing_increment": 1,
        }
        defaults.update(kwargs)
        return RateEntry(**defaults)

    def test_init_defaults(self) -> None:
        rate = self._make_rate()
        assert rate.trunk_id == "trunk-1"
        assert rate.rate_per_minute == 0.05
        assert rate.connection_fee == 0.0
        assert rate.minimum_seconds == 0
        assert rate.billing_increment == 1

    def test_calculate_cost_simple(self) -> None:
        """3 minutes at $0.05/min = $0.15."""
        rate = self._make_rate(rate_per_minute=0.05)
        cost = rate.calculate_cost(180)
        assert cost == pytest.approx(0.15, abs=0.0001)

    def test_calculate_cost_with_connection_fee(self) -> None:
        rate = self._make_rate(rate_per_minute=0.05, connection_fee=0.10)
        cost = rate.calculate_cost(180)
        assert cost == pytest.approx(0.25, abs=0.0001)

    def test_calculate_cost_minimum_seconds(self) -> None:
        """10 seconds call with 60s minimum billed as 60s."""
        rate = self._make_rate(rate_per_minute=0.60, minimum_seconds=60)
        cost = rate.calculate_cost(10)
        assert cost == pytest.approx(0.60, abs=0.0001)

    def test_calculate_cost_billing_increment(self) -> None:
        """65 seconds with 6-second billing -> 66 seconds."""
        rate = self._make_rate(rate_per_minute=0.60, billing_increment=6)
        cost = rate.calculate_cost(65)
        # 65 seconds, round up to 66 (next 6-second increment)
        expected = (66 / 60.0) * 0.60
        assert cost == pytest.approx(expected, abs=0.0001)

    def test_calculate_cost_billing_increment_exact(self) -> None:
        """60 seconds with 6-second billing -> exact (no rounding)."""
        rate = self._make_rate(rate_per_minute=0.60, billing_increment=6)
        cost = rate.calculate_cost(60)
        assert cost == pytest.approx(0.60, abs=0.0001)

    def test_calculate_cost_zero_duration(self) -> None:
        rate = self._make_rate(rate_per_minute=0.05)
        cost = rate.calculate_cost(0)
        assert cost == 0.0

    def test_calculate_cost_zero_duration_with_minimum(self) -> None:
        rate = self._make_rate(rate_per_minute=0.60, minimum_seconds=30)
        cost = rate.calculate_cost(0)
        expected = (30 / 60.0) * 0.60
        assert cost == pytest.approx(expected, abs=0.0001)


@pytest.mark.unit
class TestTimeBasedRate:
    """Tests for TimeBasedRate class."""

    def test_init(self) -> None:
        from pbx.features.least_cost_routing import TimeBasedRate

        tbr = TimeBasedRate(
            name="Peak Hours",
            start_time=time(9, 0),
            end_time=time(17, 0),
            days_of_week=[0, 1, 2, 3, 4],
            rate_multiplier=1.5,
        )
        assert tbr.name == "Peak Hours"
        assert tbr.rate_multiplier == 1.5

    def test_applies_now_correct_day_and_time(self) -> None:
        from pbx.features.least_cost_routing import TimeBasedRate

        now = datetime(2026, 2, 17, 10, 0, tzinfo=UTC)  # Tuesday (1)
        tbr = TimeBasedRate(
            name="Peak",
            start_time=time(9, 0),
            end_time=time(17, 0),
            days_of_week=[1],  # Tuesday
            rate_multiplier=1.5,
        )
        with patch("pbx.features.least_cost_routing.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = tbr.applies_now()
            assert result is True

    def test_applies_now_wrong_day(self) -> None:
        from pbx.features.least_cost_routing import TimeBasedRate

        now = datetime(2026, 2, 17, 10, 0, tzinfo=UTC)  # Tuesday (1)
        tbr = TimeBasedRate(
            name="Weekend",
            start_time=time(0, 0),
            end_time=time(23, 59),
            days_of_week=[5, 6],  # Sat, Sun
            rate_multiplier=0.5,
        )
        with patch("pbx.features.least_cost_routing.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = tbr.applies_now()
            assert result is False

    def test_applies_now_outside_time(self) -> None:
        from pbx.features.least_cost_routing import TimeBasedRate

        now = datetime(2026, 2, 17, 20, 0, tzinfo=UTC)  # Tuesday 20:00
        tbr = TimeBasedRate(
            name="Peak",
            start_time=time(9, 0),
            end_time=time(17, 0),
            days_of_week=[1],
            rate_multiplier=1.5,
        )
        with patch("pbx.features.least_cost_routing.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = tbr.applies_now()
            assert result is False

    def test_applies_now_overnight_before_midnight(self) -> None:
        from pbx.features.least_cost_routing import TimeBasedRate

        now = datetime(2026, 2, 17, 23, 30, tzinfo=UTC)  # 23:30
        tbr = TimeBasedRate(
            name="Night",
            start_time=time(23, 0),
            end_time=time(3, 0),
            days_of_week=[1],
            rate_multiplier=0.5,
        )
        with patch("pbx.features.least_cost_routing.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = tbr.applies_now()
            assert result is True

    def test_applies_now_overnight_after_midnight(self) -> None:
        from pbx.features.least_cost_routing import TimeBasedRate

        now = datetime(2026, 2, 18, 1, 0, tzinfo=UTC)  # Wednesday 01:00
        tbr = TimeBasedRate(
            name="Night",
            start_time=time(23, 0),
            end_time=time(3, 0),
            days_of_week=[2],  # Wednesday
            rate_multiplier=0.5,
        )
        with patch("pbx.features.least_cost_routing.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = tbr.applies_now()
            assert result is True


@pytest.mark.unit
class TestLeastCostRouting:
    """Tests for LeastCostRouting class."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.mock_db = MockDatabase()
        self.pbx = MagicMock()
        self.pbx.database = self.mock_db

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            self.lcr = LeastCostRouting(self.pbx)

    def test_init_defaults(self) -> None:
        assert self.lcr.enabled is True
        assert self.lcr.prefer_quality is False
        assert self.lcr.quality_weight == 0.3
        assert self.lcr.total_routes == 0
        assert self.lcr.cost_savings == 0.0

    def test_init_no_database(self) -> None:
        """PBX with no database attribute uses None."""
        pbx = MagicMock(spec=[])
        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr = LeastCostRouting(pbx)
            assert lcr.db is None

    def test_add_rate(self) -> None:
        result = self.lcr.add_rate("trunk-1", r"^1\d{10}$", 0.05, "US LD")
        assert result is True
        assert len(self.lcr.rate_entries) == 1

    def test_add_rate_disabled(self) -> None:
        self.lcr.enabled = False
        result = self.lcr.add_rate("trunk-1", r"^1\d{10}$", 0.05)
        assert result is False

    def test_add_rate_persisted(self) -> None:
        """Rate is persisted in database and survives reload."""
        self.lcr.add_rate("trunk-1", r"^1\d{10}$", 0.05, "US LD")

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr2 = LeastCostRouting(self.pbx)
            assert len(lcr2.rate_entries) == 1
            assert lcr2.rate_entries[0].trunk_id == "trunk-1"

    def test_add_time_based_rate(self) -> None:
        result = self.lcr.add_time_based_rate("Peak Hours", 9, 0, 17, 0, [0, 1, 2, 3, 4], 1.5)
        assert result is True
        assert len(self.lcr.time_based_rates) == 1

    def test_add_time_based_rate_disabled(self) -> None:
        self.lcr.enabled = False
        result = self.lcr.add_time_based_rate("Peak", 9, 0, 17, 0, [0], 1.5)
        assert result is False

    def test_add_time_based_rate_persisted(self) -> None:
        self.lcr.add_time_based_rate("Peak", 9, 0, 17, 0, [0, 1, 2], 1.5)

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr2 = LeastCostRouting(self.pbx)
            assert len(lcr2.time_based_rates) == 1
            assert lcr2.time_based_rates[0].name == "Peak"
            assert lcr2.time_based_rates[0].rate_multiplier == 1.5

    def test_get_applicable_rates(self) -> None:
        self.lcr.add_rate("trunk-1", r"^1\d{10}$", 0.05, "US LD")
        self.lcr.add_rate("trunk-2", r"^1\d{10}$", 0.03, "US LD Cheap")

        rates = self.lcr.get_applicable_rates("12125551234")
        assert len(rates) == 2
        # Sorted by cost, cheapest first
        assert rates[0][0] == "trunk-2"
        assert rates[0][1] < rates[1][1]

    def test_get_applicable_rates_no_match(self) -> None:
        self.lcr.add_rate("trunk-1", r"^1\d{10}$", 0.05)
        rates = self.lcr.get_applicable_rates("44123456789")
        assert len(rates) == 0

    def test_get_applicable_rates_with_time_modifier(self) -> None:
        self.lcr.add_rate("trunk-1", r".*", 0.10)

        # Add a time modifier that always applies
        mock_time_rate = MagicMock()
        mock_time_rate.applies_now.return_value = True
        mock_time_rate.rate_multiplier = 2.0
        self.lcr.time_based_rates.append(mock_time_rate)

        rates = self.lcr.get_applicable_rates("12125551234")
        assert len(rates) == 1
        # Cost should be doubled
        base_cost = 0.10 * 3  # 3 minutes at 0.10
        assert rates[0][1] == pytest.approx(base_cost * 2.0, abs=0.01)

    def test_select_trunk_basic(self) -> None:
        self.lcr.add_rate("trunk-1", r".*", 0.10)
        self.lcr.add_rate("trunk-2", r".*", 0.05)

        selected = self.lcr.select_trunk("12125551234", ["trunk-1", "trunk-2"])
        assert selected == "trunk-2"
        assert self.lcr.total_routes == 1
        assert len(self.lcr.routing_decisions) == 1

    def test_select_trunk_disabled(self) -> None:
        self.lcr.enabled = False
        result = self.lcr.select_trunk("12125551234", ["trunk-1"])
        assert result is None

    def test_select_trunk_no_rates(self) -> None:
        result = self.lcr.select_trunk("12125551234", ["trunk-1"])
        assert result is None

    def test_select_trunk_no_available_trunks(self) -> None:
        self.lcr.add_rate("trunk-1", r".*", 0.05)
        result = self.lcr.select_trunk("12125551234", ["trunk-99"])
        assert result is None

    def test_select_trunk_filters_unavailable(self) -> None:
        self.lcr.add_rate("trunk-1", r".*", 0.10)
        self.lcr.add_rate("trunk-2", r".*", 0.05)  # cheaper but not available

        selected = self.lcr.select_trunk("12125551234", ["trunk-1"])
        assert selected == "trunk-1"

    def test_select_trunk_caps_decisions(self) -> None:
        """Routing decisions are capped at 100."""
        self.lcr.add_rate("trunk-1", r".*", 0.05)
        for i in range(110):
            self.lcr.select_trunk(f"1212555{i:04d}", ["trunk-1"])
        assert len(self.lcr.routing_decisions) == 100

    def test_select_trunk_with_quality(self) -> None:
        """Quality-based selection uses trunk stats."""
        self.lcr.prefer_quality = True
        self.lcr.add_rate("trunk-1", r".*", 0.10)
        self.lcr.add_rate("trunk-2", r".*", 0.05)

        mock_trunk1 = MagicMock()
        mock_trunk1.total_calls = 100
        mock_trunk1.successful_calls = 99  # 99% quality

        mock_trunk2 = MagicMock()
        mock_trunk2.total_calls = 100
        mock_trunk2.successful_calls = 50  # 50% quality

        def get_trunk_side(trunk_id):
            if trunk_id == "trunk-1":
                return mock_trunk1
            return mock_trunk2

        self.pbx.trunk_manager.get_trunk.side_effect = get_trunk_side

        selected = self.lcr.select_trunk("12125551234", ["trunk-1", "trunk-2"])
        assert selected is not None

    def test_select_with_quality_unknown_trunk(self) -> None:
        """Unknown trunk quality gets default 0.5 score."""
        from pbx.features.least_cost_routing import DialPattern, RateEntry

        self.lcr.prefer_quality = True

        mock_trunk = MagicMock()
        mock_trunk.total_calls = 0
        self.pbx.trunk_manager.get_trunk.return_value = mock_trunk

        result = self.lcr._select_with_quality([("trunk-1", 0.15)])
        assert result == "trunk-1"

    def test_select_with_quality_none_trunk(self) -> None:
        """None trunk from manager gets default quality."""
        self.lcr.prefer_quality = True
        self.pbx.trunk_manager.get_trunk.return_value = None

        result = self.lcr._select_with_quality([("trunk-1", 0.15), ("trunk-2", 0.10)])
        assert result is not None

    def test_get_statistics(self) -> None:
        stats = self.lcr.get_statistics()
        assert stats["enabled"] is True
        assert stats["total_routes"] == 0
        assert stats["rate_entries"] == 0
        assert stats["time_based_rates"] == 0
        assert stats["prefer_quality"] is False
        assert stats["quality_weight"] == 0.3
        assert stats["recent_decisions"] == []

    def test_get_statistics_with_data(self) -> None:
        self.lcr.add_rate("trunk-1", r".*", 0.05)
        self.lcr.select_trunk("12125551234", ["trunk-1"])

        stats = self.lcr.get_statistics()
        assert stats["total_routes"] == 1
        assert stats["rate_entries"] == 1
        assert len(stats["recent_decisions"]) == 1

    def test_clear_rates(self) -> None:
        self.lcr.add_rate("trunk-1", r".*", 0.05)
        self.lcr.add_rate("trunk-2", r".*", 0.10)
        assert len(self.lcr.rate_entries) == 2

        self.lcr.clear_rates()
        assert len(self.lcr.rate_entries) == 0

        # Verify database is also cleared
        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr2 = LeastCostRouting(self.pbx)
            assert len(lcr2.rate_entries) == 0

    def test_clear_time_rates(self) -> None:
        self.lcr.add_time_based_rate("Peak", 9, 0, 17, 0, [0, 1], 1.5)
        assert len(self.lcr.time_based_rates) == 1

        self.lcr.clear_time_rates()
        assert len(self.lcr.time_based_rates) == 0

        # Verify database is also cleared
        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr2 = LeastCostRouting(self.pbx)
            assert len(lcr2.time_based_rates) == 0


@pytest.mark.unit
class TestLeastCostRoutingDatabaseErrors:
    """Tests for database error handling in LeastCostRouting."""

    def test_init_database_error(self) -> None:
        """Database init error is handled gracefully."""
        mock_db = MockDatabaseError(error_on="execute")
        pbx = MagicMock()
        pbx.database = mock_db

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            _lcr = LeastCostRouting(pbx)
            # Should not crash - error is logged

    def test_save_rate_db_error(self) -> None:
        """Save rate handles DB errors."""
        mock_db = MockDatabase()
        pbx = MagicMock()
        pbx.database = mock_db

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr = LeastCostRouting(pbx)

            # Replace db with error-raising mock for the save call
            lcr.db = MockDatabaseError(error_on="execute")
            # Should not raise
            lcr._save_rate_to_db("trunk-1", r".*", 0.05)

    def test_save_time_rate_db_error(self) -> None:
        """Save time rate handles DB errors."""
        mock_db = MockDatabase()
        pbx = MagicMock()
        pbx.database = mock_db

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr = LeastCostRouting(pbx)

            # Replace db with error-raising mock for the save call
            lcr.db = MockDatabaseError(error_on="execute")
            lcr._save_time_rate_to_db("Peak", 9, 0, 17, 0, [0, 1], 1.5)

    def test_load_from_database_error(self) -> None:
        """Load from DB handles errors."""
        mock_db = MockDatabase()
        pbx = MagicMock()
        pbx.database = mock_db

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr = LeastCostRouting(pbx)
            lcr.rate_entries = []
            lcr.time_based_rates = []

            # Replace db with error-raising mock for the load call
            lcr.db = MockDatabaseError(error_on="fetch")
            lcr._load_from_database()
            # Should not crash

    def test_delete_all_rates_db_error(self) -> None:
        """Delete all rates handles DB errors."""
        mock_db = MockDatabase()
        pbx = MagicMock()
        pbx.database = mock_db

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr = LeastCostRouting(pbx)

            # Replace db with error-raising mock for the delete call
            lcr.db = MockDatabaseError(error_on="execute")
            lcr._delete_all_rates_from_db()

    def test_delete_all_time_rates_db_error(self) -> None:
        """Delete all time rates handles DB errors."""
        mock_db = MockDatabase()
        pbx = MagicMock()
        pbx.database = mock_db

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr = LeastCostRouting(pbx)

            # Replace db with error-raising mock for the delete call
            lcr.db = MockDatabaseError(error_on="execute")
            lcr._delete_all_time_rates_from_db()

    def test_disabled_database_skips_operations(self) -> None:
        """When database is disabled, all DB operations are skipped."""
        mock_db = MockDatabaseDisabled()
        pbx = MagicMock()
        pbx.database = mock_db

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr = LeastCostRouting(pbx)
            # Should initialize without errors, just skip DB operations
            assert lcr.db is not None
            assert lcr.db.enabled is False

            # These should all be no-ops, not errors
            lcr._save_rate_to_db("trunk-1", r".*", 0.05)
            lcr._save_time_rate_to_db("Peak", 9, 0, 17, 0, [0], 1.5)
            lcr._delete_all_rates_from_db()
            lcr._delete_all_time_rates_from_db()

    def test_no_database_attribute(self) -> None:
        """PBX without database attribute creates LCR with db=None."""
        pbx = MagicMock(spec=[])

        with patch("pbx.features.least_cost_routing.get_logger"):
            from pbx.features.least_cost_routing import LeastCostRouting

            lcr = LeastCostRouting(pbx)
            assert lcr.db is None

            # All DB operations should be safe no-ops
            lcr._save_rate_to_db("trunk-1", r".*", 0.05)
            lcr._save_time_rate_to_db("Peak", 9, 0, 17, 0, [0], 1.5)
            lcr._delete_all_rates_from_db()
            lcr._delete_all_time_rates_from_db()
            lcr._load_from_database()
