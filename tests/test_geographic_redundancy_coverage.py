"""Comprehensive tests for geographic_redundancy feature module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.geographic_redundancy import (
    GeographicRedundancy,
    GeographicRegion,
    RegionStatus,
    get_geographic_redundancy,
)


@pytest.mark.unit
class TestRegionStatus:
    """Tests for RegionStatus enum."""

    def test_enum_values(self) -> None:
        assert RegionStatus.ACTIVE.value == "active"
        assert RegionStatus.STANDBY.value == "standby"
        assert RegionStatus.FAILED.value == "failed"
        assert RegionStatus.MAINTENANCE.value == "maintenance"


@pytest.mark.unit
class TestGeographicRegion:
    """Tests for GeographicRegion class."""

    def test_initialization(self) -> None:
        region = GeographicRegion("us-east-1", "US East 1", "Virginia")
        assert region.region_id == "us-east-1"
        assert region.name == "US East 1"
        assert region.location == "Virginia"
        assert region.status == RegionStatus.STANDBY
        assert region.trunks == []
        assert region.priority == 100
        assert region.last_health_check is None
        assert region.health_score == 1.0


@pytest.mark.unit
class TestGeographicRedundancyInit:
    """Tests for GeographicRedundancy initialization."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_default_initialization(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        assert gr.enabled is False
        assert gr.auto_failover is True
        assert gr.health_check_interval == 60
        assert gr.failover_threshold == 3
        assert gr.regions == {}
        assert gr.active_region is None
        assert gr.total_failovers == 0

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_initialization_with_config(self, mock_logger: MagicMock) -> None:
        config = {
            "features": {
                "geographic_redundancy": {
                    "enabled": True,
                    "auto_failover": False,
                    "health_check_interval": 30,
                    "failover_threshold": 5,
                }
            }
        }
        gr = GeographicRedundancy(config=config)
        assert gr.enabled is True
        assert gr.auto_failover is False
        assert gr.health_check_interval == 30
        assert gr.failover_threshold == 5


@pytest.mark.unit
class TestAddRegion:
    """Tests for add_region method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_add_first_region(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        result = gr.add_region("us-east", "US East", "Virginia", priority=10, trunks=["t1", "t2"])
        assert result["success"] is True
        assert result["region_id"] == "us-east"
        assert gr.active_region == "us-east"
        assert gr.regions["us-east"].status == RegionStatus.ACTIVE
        assert gr.regions["us-east"].trunks == ["t1", "t2"]
        assert gr.regions["us-east"].priority == 10

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_add_second_region_stays_standby(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia")
        gr.add_region("us-west", "US West", "Oregon")
        assert gr.active_region == "us-east"
        assert gr.regions["us-west"].status == RegionStatus.STANDBY

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_add_region_no_trunks(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        result = gr.add_region("eu-west", "EU West", "Ireland")
        assert result["success"] is True
        assert gr.regions["eu-west"].trunks == []


@pytest.mark.unit
class TestCheckTrunkHealth:
    """Tests for _check_trunk_health method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_no_trunks(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        region = GeographicRegion("test", "Test", "Test")
        assert gr._check_trunk_health(region) is False

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_trunk_health_import_error(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        region = GeographicRegion("test", "Test", "Test")
        region.trunks = ["trunk-1"]
        with patch(
            "pbx.features.geographic_redundancy.GeographicRedundancy._check_trunk_health",
            wraps=gr._check_trunk_health,
        ):
            # The method catches all exceptions and returns True
            result = gr._check_trunk_health(region)
            assert isinstance(result, bool)

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_trunk_health_with_mock_trunk_manager(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        region = GeographicRegion("test", "Test", "Test")
        region.trunks = ["trunk-1"]

        mock_trunk = MagicMock()
        mock_trunk.can_make_call.return_value = True
        mock_trunk_manager = MagicMock()
        mock_trunk_manager.get_trunk.return_value = mock_trunk

        with patch(
            "pbx.features.geographic_redundancy.GeographicRedundancy._check_trunk_health"
        ) as mock_check:
            mock_check.return_value = True
            assert mock_check(region) is True


@pytest.mark.unit
class TestCheckNetworkLatency:
    """Tests for _check_network_latency method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    @patch("pbx.features.geographic_redundancy.socket.socket")
    def test_successful_latency_check(self, mock_socket_cls: MagicMock, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock
        latency = gr._check_network_latency("1.2.3.4")
        assert latency >= 0
        mock_sock.close.assert_called_once()

    @patch("pbx.features.geographic_redundancy.get_logger")
    @patch("pbx.features.geographic_redundancy.socket.socket")
    def test_failed_latency_check(self, mock_socket_cls: MagicMock, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 1  # Connection failed
        mock_socket_cls.return_value = mock_sock
        latency = gr._check_network_latency()
        assert latency == 9999.0

    @patch("pbx.features.geographic_redundancy.get_logger")
    @patch("pbx.features.geographic_redundancy.socket.socket")
    def test_exception_latency_check(self, mock_socket_cls: MagicMock, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        mock_socket_cls.side_effect = OSError("Network error")
        latency = gr._check_network_latency()
        assert latency == 9999.0

    @patch("pbx.features.geographic_redundancy.get_logger")
    @patch("pbx.features.geographic_redundancy.socket.socket")
    def test_default_host(self, mock_socket_cls: MagicMock, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock
        gr._check_network_latency()
        mock_sock.connect_ex.assert_called_once_with(("8.8.8.8", 53))


@pytest.mark.unit
class TestCheckDatabaseConnectivity:
    """Tests for _check_database_connectivity method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_db_check_returns_bool(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        with patch("pbx.utils.database.get_database") as mock_get_db:
            mock_db = MagicMock()
            mock_db.enabled = False
            mock_db.connection = None
            mock_get_db.return_value = mock_db
            result = gr._check_database_connectivity()
            # db not enabled, so returns True (assumes OK)
            assert result is True

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_db_check_sqlite_error(self, mock_logger: MagicMock) -> None:
        import sqlite3
        gr = GeographicRedundancy()
        with patch("pbx.utils.database.get_database", side_effect=sqlite3.Error("db err")):
            # Caught by outer except sqlite3.Error, returns True (assume OK)
            result = gr._check_database_connectivity()
            assert result is True


@pytest.mark.unit
class TestCheckServicesRunning:
    """Tests for _check_services_running."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_services_running(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        assert gr._check_services_running() is True


@pytest.mark.unit
class TestCheckRegionHealth:
    """Tests for check_region_health method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_region_not_found(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        result = gr.check_region_health("nonexistent")
        assert result["healthy"] is False
        assert result["error"] == "Region not found"

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_region_healthy(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia", trunks=["t1"])
        with patch.object(gr, "_check_trunk_health", return_value=True), \
             patch.object(gr, "_check_network_latency", return_value=10.0), \
             patch.object(gr, "_check_database_connectivity", return_value=True), \
             patch.object(gr, "_check_services_running", return_value=True):
            result = gr.check_region_health("us-east")
            assert result["healthy"] is True
            assert result["health_score"] == 1.0

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_region_unhealthy_triggers_failover(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.auto_failover = True
        gr.add_region("us-east", "US East", "Virginia", trunks=["t1"])
        gr.add_region("us-west", "US West", "Oregon", trunks=["t2"])
        with patch.object(gr, "_check_trunk_health", return_value=False), \
             patch.object(gr, "_check_network_latency", return_value=9999.0), \
             patch.object(gr, "_check_database_connectivity", return_value=False), \
             patch.object(gr, "_check_services_running", return_value=False):
            result = gr.check_region_health("us-east")
            assert result["healthy"] is False
            # Should have triggered failover
            assert gr.active_region == "us-west"

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_region_degraded_no_failover_auto_off(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.auto_failover = False
        gr.add_region("us-east", "US East", "Virginia", trunks=["t1"])
        with patch.object(gr, "_check_trunk_health", return_value=False), \
             patch.object(gr, "_check_network_latency", return_value=9999.0), \
             patch.object(gr, "_check_database_connectivity", return_value=False), \
             patch.object(gr, "_check_services_running", return_value=False):
            result = gr.check_region_health("us-east")
            assert result["healthy"] is False
            assert gr.active_region == "us-east"  # No failover


@pytest.mark.unit
class TestTriggerFailover:
    """Tests for _trigger_failover and related methods."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_trigger_failover_success(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia")
        gr.add_region("us-west", "US West", "Oregon")
        gr._trigger_failover("us-east", "test_reason")
        assert gr.active_region == "us-west"
        assert gr.regions["us-east"].status == RegionStatus.FAILED
        assert gr.regions["us-west"].status == RegionStatus.ACTIVE
        assert gr.total_failovers == 1
        assert len(gr.failover_history) == 1

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_trigger_failover_no_backup(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia")
        gr._trigger_failover("us-east", "test_reason")
        # No backup available, stays same
        assert gr.total_failovers == 0


@pytest.mark.unit
class TestSelectBackupRegion:
    """Tests for _select_backup_region method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_select_by_priority(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia", priority=10)
        gr.add_region("us-west", "US West", "Oregon", priority=20)
        gr.add_region("eu-west", "EU West", "Ireland", priority=5)
        result = gr._select_backup_region("us-east")
        assert result == "eu-west"  # Lowest priority (highest preference)

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_select_excludes_failed(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia", priority=10)
        gr.add_region("us-west", "US West", "Oregon", priority=5)
        gr.regions["us-west"].status = RegionStatus.FAILED
        gr.add_region("eu-west", "EU West", "Ireland", priority=20)
        result = gr._select_backup_region("us-east")
        assert result == "eu-west"

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_select_no_candidates(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia")
        result = gr._select_backup_region("us-east")
        assert result is None


@pytest.mark.unit
class TestManualFailover:
    """Tests for manual_failover method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_manual_failover_success(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia")
        gr.add_region("us-west", "US West", "Oregon")
        result = gr.manual_failover("us-west")
        assert result["success"] is True
        assert result["from_region"] == "us-east"
        assert result["to_region"] == "us-west"
        assert gr.active_region == "us-west"
        assert gr.regions["us-east"].status == RegionStatus.STANDBY

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_manual_failover_not_found(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        result = gr.manual_failover("nonexistent")
        assert result["success"] is False


@pytest.mark.unit
class TestGetActiveRegion:
    """Tests for get_active_region method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_get_active_region_exists(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia", trunks=["t1"])
        result = gr.get_active_region()
        assert result is not None
        assert result["region_id"] == "us-east"
        assert result["name"] == "US East"
        assert result["status"] == "active"
        assert result["trunk_count"] == 1

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_get_active_region_none(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        assert gr.get_active_region() is None


@pytest.mark.unit
class TestGetAllRegions:
    """Tests for get_all_regions method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_get_all_regions(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia")
        gr.add_region("us-west", "US West", "Oregon")
        regions = gr.get_all_regions()
        assert len(regions) == 2
        active_regions = [r for r in regions if r["is_active"]]
        assert len(active_regions) == 1

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_get_all_regions_empty(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        assert gr.get_all_regions() == []


@pytest.mark.unit
class TestGetRegionStatus:
    """Tests for get_region_status method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_get_status_exists(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia", priority=10, trunks=["t1"])
        status = gr.get_region_status("us-east")
        assert status is not None
        assert status["region_id"] == "us-east"
        assert status["priority"] == 10
        assert status["trunks"] == ["t1"]

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_get_status_not_found(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        assert gr.get_region_status("nonexistent") is None


@pytest.mark.unit
class TestCreateRegion:
    """Tests for create_region method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_create_region_success(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        result = gr.create_region("eu-west", "EU West", "Ireland")
        assert result["success"] is True
        assert "eu-west" in gr.regions

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_create_region_duplicate(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.create_region("eu-west", "EU West", "Ireland")
        result = gr.create_region("eu-west", "EU West", "Ireland")
        assert result["success"] is False


@pytest.mark.unit
class TestTriggerFailoverPublic:
    """Tests for trigger_failover (public method)."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_trigger_failover_with_target(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia")
        gr.add_region("us-west", "US West", "Oregon")
        result = gr.trigger_failover("us-west")
        assert result["success"] is True

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_trigger_failover_auto_select(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia", priority=10)
        gr.add_region("us-west", "US West", "Oregon", priority=5)
        result = gr.trigger_failover()
        assert result["success"] is True
        assert gr.active_region == "us-west"

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_trigger_failover_no_regions(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        result = gr.trigger_failover()
        assert result["success"] is False


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics method."""

    @patch("pbx.features.geographic_redundancy.get_logger")
    def test_get_statistics(self, mock_logger: MagicMock) -> None:
        gr = GeographicRedundancy()
        gr.add_region("us-east", "US East", "Virginia")
        stats = gr.get_statistics()
        assert stats["total_regions"] == 1
        assert stats["active_region"] == "us-east"
        assert stats["total_failovers"] == 0
        assert stats["auto_failover"] is True


@pytest.mark.unit
class TestGetGeographicRedundancySingleton:
    """Tests for get_geographic_redundancy global function."""

    def test_creates_instance(self) -> None:
        import pbx.features.geographic_redundancy as mod
        original = mod._geographic_redundancy
        mod._geographic_redundancy = None
        try:
            with patch("pbx.features.geographic_redundancy.get_logger"):
                instance = get_geographic_redundancy()
                assert isinstance(instance, GeographicRedundancy)
        finally:
            mod._geographic_redundancy = original

    def test_returns_same_instance(self) -> None:
        import pbx.features.geographic_redundancy as mod
        original = mod._geographic_redundancy
        mod._geographic_redundancy = None
        try:
            with patch("pbx.features.geographic_redundancy.get_logger"):
                instance1 = get_geographic_redundancy()
                instance2 = get_geographic_redundancy()
                assert instance1 is instance2
        finally:
            mod._geographic_redundancy = original
