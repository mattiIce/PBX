#!/usr/bin/env python3
"""Comprehensive tests for the production_health module."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from pbx.utils.production_health import (
    ProductionHealthChecker,
    format_health_check_response,
)


@pytest.mark.unit
class TestProductionHealthCheckerInit:
    """Tests for ProductionHealthChecker initialization."""

    def test_init_defaults(self) -> None:
        checker = ProductionHealthChecker()
        assert checker.pbx_core is None
        assert checker.config == {}
        assert isinstance(checker.start_time, float)

    def test_init_with_pbx_core(self) -> None:
        mock_core = MagicMock()
        checker = ProductionHealthChecker(pbx_core=mock_core)
        assert checker.pbx_core is mock_core

    def test_init_with_config(self) -> None:
        config = {"server": {"sip_port": 5060}}
        checker = ProductionHealthChecker(config=config)
        assert checker.config is config

    def test_init_with_both(self) -> None:
        mock_core = MagicMock()
        config = {"server": {"version": "1.0"}}
        checker = ProductionHealthChecker(pbx_core=mock_core, config=config)
        assert checker.pbx_core is mock_core
        assert checker.config is config

    def test_start_time_recorded(self) -> None:
        before = time.time()
        checker = ProductionHealthChecker()
        after = time.time()
        assert before <= checker.start_time <= after


@pytest.mark.unit
class TestCheckLiveness:
    """Tests for check_liveness method."""

    def test_liveness_returns_true(self) -> None:
        checker = ProductionHealthChecker()
        is_alive, details = checker.check_liveness()
        assert is_alive is True
        assert details["status"] == "alive"
        assert "uptime_seconds" in details
        assert "timestamp" in details

    def test_liveness_uptime_positive(self) -> None:
        checker = ProductionHealthChecker()
        time.sleep(0.01)
        _is_alive, details = checker.check_liveness()
        assert details["uptime_seconds"] > 0

    def test_liveness_exception(self) -> None:
        checker = ProductionHealthChecker()
        # Force an exception by setting start_time to a non-numeric value
        checker.start_time = "not_a_number"
        is_alive, details = checker.check_liveness()
        assert is_alive is False
        assert details["status"] == "dead"
        assert "error" in details


@pytest.mark.unit
class TestCheckReadiness:
    """Tests for check_readiness method."""

    @patch.object(ProductionHealthChecker, "_check_system_resources")
    @patch.object(ProductionHealthChecker, "_check_sip_server")
    @patch.object(ProductionHealthChecker, "_check_database")
    @patch.object(ProductionHealthChecker, "_check_pbx_core")
    def test_all_checks_pass(self, mock_pbx, mock_db, mock_sip, mock_resources) -> None:
        mock_pbx.return_value = (True, {"status": "operational"})
        mock_db.return_value = (True, {"status": "connected"})
        mock_sip.return_value = (True, {"status": "assumed_running"})
        mock_resources.return_value = (True, {"status": "ok"})

        checker = ProductionHealthChecker()
        is_ready, details = checker.check_readiness()

        assert is_ready is True
        assert details["status"] == "ready"
        assert "checks" in details
        assert "pbx_core" in details["checks"]
        assert "database" in details["checks"]
        assert "sip_server" in details["checks"]
        assert "system_resources" in details["checks"]

    @patch.object(ProductionHealthChecker, "_check_system_resources")
    @patch.object(ProductionHealthChecker, "_check_sip_server")
    @patch.object(ProductionHealthChecker, "_check_database")
    @patch.object(ProductionHealthChecker, "_check_pbx_core")
    def test_pbx_core_fails(self, mock_pbx, mock_db, mock_sip, mock_resources) -> None:
        mock_pbx.return_value = (False, {"status": "not_initialized"})
        mock_db.return_value = (True, {"status": "connected"})
        mock_sip.return_value = (True, {"status": "assumed_running"})
        mock_resources.return_value = (True, {"status": "ok"})

        checker = ProductionHealthChecker()
        is_ready, details = checker.check_readiness()

        assert is_ready is False
        assert details["status"] == "not_ready"

    @patch.object(ProductionHealthChecker, "_check_system_resources")
    @patch.object(ProductionHealthChecker, "_check_sip_server")
    @patch.object(ProductionHealthChecker, "_check_database")
    @patch.object(ProductionHealthChecker, "_check_pbx_core")
    def test_database_fails(self, mock_pbx, mock_db, mock_sip, mock_resources) -> None:
        mock_pbx.return_value = (True, {"status": "operational"})
        mock_db.return_value = (False, {"status": "unavailable"})
        mock_sip.return_value = (True, {"status": "assumed_running"})
        mock_resources.return_value = (True, {"status": "ok"})

        checker = ProductionHealthChecker()
        is_ready, details = checker.check_readiness()

        assert is_ready is False
        assert details["status"] == "not_ready"

    @patch.object(ProductionHealthChecker, "_check_system_resources")
    @patch.object(ProductionHealthChecker, "_check_sip_server")
    @patch.object(ProductionHealthChecker, "_check_database")
    @patch.object(ProductionHealthChecker, "_check_pbx_core")
    def test_multiple_failures(self, mock_pbx, mock_db, mock_sip, mock_resources) -> None:
        mock_pbx.return_value = (False, {"status": "error"})
        mock_db.return_value = (False, {"status": "error"})
        mock_sip.return_value = (False, {"status": "error"})
        mock_resources.return_value = (False, {"status": "warning"})

        checker = ProductionHealthChecker()
        is_ready, _details = checker.check_readiness()

        assert is_ready is False


@pytest.mark.unit
class TestGetDetailedStatus:
    """Tests for get_detailed_status method."""

    @patch.object(ProductionHealthChecker, "_get_metrics")
    @patch.object(ProductionHealthChecker, "check_readiness")
    @patch.object(ProductionHealthChecker, "check_liveness")
    def test_healthy_status(self, mock_liveness, mock_readiness, mock_metrics) -> None:
        mock_liveness.return_value = (True, {"status": "alive"})
        mock_readiness.return_value = (True, {"status": "ready"})
        mock_metrics.return_value = {"uptime_seconds": 100}

        checker = ProductionHealthChecker(
            config={"server": {"version": "2.0", "server_name": "TestPBX"}}
        )
        status = checker.get_detailed_status()

        assert status["overall_status"] == "healthy"
        assert status["liveness"]["status"] == "alive"
        assert status["readiness"]["status"] == "ready"
        assert status["version"] == "2.0"
        assert status["server_name"] == "TestPBX"

    @patch.object(ProductionHealthChecker, "_get_metrics")
    @patch.object(ProductionHealthChecker, "check_readiness")
    @patch.object(ProductionHealthChecker, "check_liveness")
    def test_unhealthy_status_liveness_fail(
        self, mock_liveness, mock_readiness, mock_metrics
    ) -> None:
        mock_liveness.return_value = (False, {"status": "dead"})
        mock_readiness.return_value = (True, {"status": "ready"})
        mock_metrics.return_value = {}

        checker = ProductionHealthChecker()
        status = checker.get_detailed_status()
        assert status["overall_status"] == "unhealthy"

    @patch.object(ProductionHealthChecker, "_get_metrics")
    @patch.object(ProductionHealthChecker, "check_readiness")
    @patch.object(ProductionHealthChecker, "check_liveness")
    def test_unhealthy_status_readiness_fail(
        self, mock_liveness, mock_readiness, mock_metrics
    ) -> None:
        mock_liveness.return_value = (True, {"status": "alive"})
        mock_readiness.return_value = (False, {"status": "not_ready"})
        mock_metrics.return_value = {}

        checker = ProductionHealthChecker()
        status = checker.get_detailed_status()
        assert status["overall_status"] == "unhealthy"

    @patch.object(ProductionHealthChecker, "_get_metrics")
    @patch.object(ProductionHealthChecker, "check_readiness")
    @patch.object(ProductionHealthChecker, "check_liveness")
    def test_default_version_and_server_name(
        self, mock_liveness, mock_readiness, mock_metrics
    ) -> None:
        mock_liveness.return_value = (True, {"status": "alive"})
        mock_readiness.return_value = (True, {"status": "ready"})
        mock_metrics.return_value = {}

        checker = ProductionHealthChecker()
        status = checker.get_detailed_status()
        assert status["version"] == "unknown"
        assert status["server_name"] == "Warden Voip"


@pytest.mark.unit
class TestCheckPbxCore:
    """Tests for _check_pbx_core method."""

    def test_no_pbx_core(self) -> None:
        checker = ProductionHealthChecker()
        is_ok, details = checker._check_pbx_core()
        assert is_ok is False
        assert details["status"] == "not_initialized"

    def test_pbx_core_incomplete_no_sip(self) -> None:
        mock_core = MagicMock(spec=[])
        checker = ProductionHealthChecker(pbx_core=mock_core)
        is_ok, details = checker._check_pbx_core()
        assert is_ok is False
        assert details["status"] == "incomplete"
        assert details["has_sip_server"] is False

    def test_pbx_core_incomplete_sip_is_none(self) -> None:
        mock_core = MagicMock()
        mock_core.sip_server = None
        checker = ProductionHealthChecker(pbx_core=mock_core)
        is_ok, details = checker._check_pbx_core()
        assert is_ok is False
        assert details["has_sip_server"] is False

    def test_pbx_core_operational(self) -> None:
        mock_core = MagicMock()
        mock_core.sip_server = MagicMock()
        mock_core.extension_registry = MagicMock()
        mock_core.call_manager = MagicMock()
        mock_core.call_manager.get_active_calls.return_value = ["call1"]

        mock_ext1 = MagicMock()
        mock_ext1.registered = True
        mock_ext2 = MagicMock()
        mock_ext2.registered = False
        mock_core.extension_registry.get_all.return_value = [mock_ext1, mock_ext2]

        checker = ProductionHealthChecker(pbx_core=mock_core)
        is_ok, details = checker._check_pbx_core()

        assert is_ok is True
        assert details["status"] == "operational"
        assert details["active_calls"] == 1
        assert details["registered_extensions"] == 1

    def test_pbx_core_operational_stats_error(self) -> None:
        mock_core = MagicMock()
        mock_core.sip_server = MagicMock()
        mock_core.extension_registry = MagicMock()
        mock_core.call_manager = MagicMock()
        mock_core.call_manager.get_active_calls.side_effect = RuntimeError("oops")

        checker = ProductionHealthChecker(pbx_core=mock_core)
        is_ok, details = checker._check_pbx_core()

        assert is_ok is True
        assert details["active_calls"] == 0
        assert details["registered_extensions"] == 0

    def test_pbx_core_exception(self) -> None:
        mock_core = MagicMock()
        # Make hasattr raise an exception (very unlikely but tests the outer except)
        type(mock_core).sip_server = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("bad"))
        )

        checker = ProductionHealthChecker(pbx_core=mock_core)
        is_ok, details = checker._check_pbx_core()

        assert is_ok is False
        assert details["status"] == "error"


@pytest.mark.unit
class TestCheckDatabase:
    """Tests for _check_database method."""

    def test_database_connected(self) -> None:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch.dict("sys.modules", {"pbx.utils.database": MagicMock()}):
            with patch(
                "pbx.utils.production_health.ProductionHealthChecker._check_database",
                wraps=None,
            ) as _:
                pass

            # Directly test by patching the import inside the method
            mock_db_module = MagicMock()
            mock_db_module.get_database_connection.return_value = mock_conn

            checker = ProductionHealthChecker(config={"database": {"type": "postgresql"}})
            with patch.dict("sys.modules", {"pbx.utils.database": mock_db_module}):
                is_ok, details = checker._check_database()
                assert is_ok is True
                assert details["status"] == "connected"
                assert details["type"] == "postgresql"

    def test_database_connection_returns_none(self) -> None:
        mock_db_module = MagicMock()
        mock_db_module.get_database_connection.return_value = None

        checker = ProductionHealthChecker(config={"database": {"type": "sqlite"}})
        with patch.dict("sys.modules", {"pbx.utils.database": mock_db_module}):
            is_ok, details = checker._check_database()
            assert is_ok is False
            assert details["status"] == "unavailable"
            assert details["type"] == "sqlite"

    def test_database_import_error(self) -> None:
        checker = ProductionHealthChecker()

        # Remove the module from cache if present, then make import fail
        import sys

        saved = sys.modules.pop("pbx.utils.database", None)
        try:
            original_import = (
                __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
            )

            def mock_import(name, *args, **kwargs):
                if name == "pbx.utils.database":
                    raise ImportError("no module")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                is_ok, details = checker._check_database()
                assert is_ok is True
                assert details["status"] == "not_configured"
        finally:
            if saved is not None:
                sys.modules["pbx.utils.database"] = saved

    def test_database_query_error(self) -> None:
        import sqlite3

        mock_db_module = MagicMock()
        mock_db_module.get_database_connection.side_effect = sqlite3.Error("query failed")

        checker = ProductionHealthChecker(config={"database": {"type": "sqlite"}})
        with patch.dict("sys.modules", {"pbx.utils.database": mock_db_module}):
            is_ok, details = checker._check_database()
            assert is_ok is False
            assert details["status"] == "error"
            assert "query failed" in details["error"]

    def test_database_default_config(self) -> None:
        mock_conn = MagicMock()
        mock_db_module = MagicMock()
        mock_db_module.get_database_connection.return_value = mock_conn

        checker = ProductionHealthChecker()
        with patch.dict("sys.modules", {"pbx.utils.database": mock_db_module}):
            is_ok, details = checker._check_database()
            assert is_ok is True
            assert details["type"] == "sqlite"


@pytest.mark.unit
class TestCheckSipServer:
    """Tests for _check_sip_server method."""

    @patch("pbx.utils.production_health.socket")
    def test_sip_server_port_available(self, mock_socket_module) -> None:
        mock_sock = MagicMock()
        mock_socket_module.socket.return_value = mock_sock
        mock_socket_module.AF_INET = 2
        mock_socket_module.SOCK_DGRAM = 2

        checker = ProductionHealthChecker(config={"server": {"sip_port": 5060}})
        is_ok, details = checker._check_sip_server()

        assert is_ok is True
        assert details["port"] == 5060

    @patch("pbx.utils.production_health.socket")
    def test_sip_server_port_in_use(self, mock_socket_module) -> None:
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError("Address already in use")
        mock_socket_module.socket.return_value = mock_sock
        mock_socket_module.AF_INET = 2
        mock_socket_module.SOCK_DGRAM = 2

        checker = ProductionHealthChecker(config={"server": {"sip_port": 5060}})
        is_ok, details = checker._check_sip_server()

        assert is_ok is True
        assert details["status"] == "port_in_use"

    @patch("pbx.utils.production_health.socket")
    def test_sip_server_socket_creation_error(self, mock_socket_module) -> None:
        mock_socket_module.socket.side_effect = OSError("Cannot create socket")
        mock_socket_module.AF_INET = 2
        mock_socket_module.SOCK_DGRAM = 2

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_sip_server()

        assert is_ok is False
        assert details["status"] == "error"

    @patch("pbx.utils.production_health.socket")
    def test_sip_server_default_port(self, mock_socket_module) -> None:
        mock_sock = MagicMock()
        mock_socket_module.socket.return_value = mock_sock
        mock_socket_module.AF_INET = 2
        mock_socket_module.SOCK_DGRAM = 2

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_sip_server()

        assert is_ok is True
        assert details["port"] == 5060


@pytest.mark.unit
class TestCheckSystemResources:
    """Tests for _check_system_resources method."""

    @patch("pbx.utils.production_health.psutil")
    def test_resources_ok(self, mock_psutil) -> None:
        mock_psutil.cpu_percent.return_value = 30.0
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.percent = 40.0
        mock_psutil.disk_usage.return_value = mock_disk

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_system_resources()

        assert is_ok is True
        assert details["status"] == "ok"
        assert details["cpu_percent"] == 30.0
        assert details["memory_percent"] == 50.0
        assert details["disk_percent"] == 40.0
        assert details["warnings"] is None

    @patch("pbx.utils.production_health.psutil")
    def test_resources_high_cpu(self, mock_psutil) -> None:
        mock_psutil.cpu_percent.return_value = 90.0
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.percent = 40.0
        mock_psutil.disk_usage.return_value = mock_disk

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_system_resources()

        assert is_ok is False
        assert details["status"] == "warning"
        assert any("CPU" in w for w in details["warnings"])

    @patch("pbx.utils.production_health.psutil")
    def test_resources_high_memory(self, mock_psutil) -> None:
        mock_psutil.cpu_percent.return_value = 30.0
        mock_memory = MagicMock()
        mock_memory.percent = 90.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.percent = 40.0
        mock_psutil.disk_usage.return_value = mock_disk

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_system_resources()

        assert is_ok is False
        assert any("memory" in w.lower() for w in details["warnings"])

    @patch("pbx.utils.production_health.psutil")
    def test_resources_high_disk(self, mock_psutil) -> None:
        mock_psutil.cpu_percent.return_value = 30.0
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.percent = 95.0
        mock_psutil.disk_usage.return_value = mock_disk

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_system_resources()

        assert is_ok is False
        assert any("disk" in w.lower() for w in details["warnings"])

    @patch("pbx.utils.production_health.psutil")
    def test_resources_all_high(self, mock_psutil) -> None:
        mock_psutil.cpu_percent.return_value = 95.0
        mock_memory = MagicMock()
        mock_memory.percent = 95.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.percent = 95.0
        mock_psutil.disk_usage.return_value = mock_disk

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_system_resources()

        assert is_ok is False
        assert len(details["warnings"]) == 3

    @patch("pbx.utils.production_health.psutil")
    def test_resources_at_threshold(self, mock_psutil) -> None:
        """Test at exact threshold values (below warning)."""
        mock_psutil.cpu_percent.return_value = 79.9
        mock_memory = MagicMock()
        mock_memory.percent = 84.9
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.percent = 89.9
        mock_psutil.disk_usage.return_value = mock_disk

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_system_resources()

        assert is_ok is True
        assert details["warnings"] is None

    @patch("pbx.utils.production_health.psutil")
    def test_resources_at_exact_threshold(self, mock_psutil) -> None:
        """Test at exact threshold values (at warning boundary)."""
        mock_psutil.cpu_percent.return_value = 80.0
        mock_memory = MagicMock()
        mock_memory.percent = 85.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.percent = 90.0
        mock_psutil.disk_usage.return_value = mock_disk

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_system_resources()

        assert is_ok is False
        assert len(details["warnings"]) == 3

    @patch("pbx.utils.production_health.psutil")
    def test_resources_exception(self, mock_psutil) -> None:
        mock_psutil.cpu_percent.side_effect = RuntimeError("psutil error")

        checker = ProductionHealthChecker()
        is_ok, details = checker._check_system_resources()

        # Should not fail readiness on resource check errors
        assert is_ok is True
        assert details["status"] == "unavailable"
        assert "error" in details


@pytest.mark.unit
class TestGetMetrics:
    """Tests for _get_metrics method."""

    @patch("pbx.utils.production_health.psutil")
    @patch("pbx.utils.production_health.os")
    def test_metrics_without_pbx_core(self, mock_os, mock_psutil) -> None:
        mock_os.getpid.return_value = 1234
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 5.0
        mock_mem_info = MagicMock()
        mock_mem_info.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.memory_info.return_value = mock_mem_info
        mock_psutil.Process.return_value = mock_process
        mock_psutil.cpu_percent.return_value = 30.0
        mock_vm = MagicMock()
        mock_vm.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_disk = MagicMock()
        mock_disk.percent = 40.0
        mock_psutil.disk_usage.return_value = mock_disk

        checker = ProductionHealthChecker()
        metrics = checker._get_metrics()

        assert "uptime_seconds" in metrics
        assert metrics["process_cpu_percent"] == 5.0
        assert metrics["process_memory_mb"] == 100.0
        assert metrics["system_cpu_percent"] == 30.0
        assert metrics["system_memory_percent"] == 50.0
        assert metrics["system_disk_percent"] == 40.0

    @patch("pbx.utils.production_health.psutil")
    @patch("pbx.utils.production_health.os")
    def test_metrics_with_pbx_core(self, mock_os, mock_psutil) -> None:
        mock_os.getpid.return_value = 1234
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 5.0
        mock_mem_info = MagicMock()
        mock_mem_info.rss = 50 * 1024 * 1024
        mock_process.memory_info.return_value = mock_mem_info
        mock_psutil.Process.return_value = mock_process
        mock_psutil.cpu_percent.return_value = 20.0
        mock_vm = MagicMock()
        mock_vm.percent = 40.0
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_disk = MagicMock()
        mock_disk.percent = 30.0
        mock_psutil.disk_usage.return_value = mock_disk

        mock_core = MagicMock()
        mock_core.call_manager.get_active_calls.return_value = ["c1", "c2"]
        mock_ext1 = MagicMock()
        mock_ext1.registered = True
        mock_ext2 = MagicMock()
        mock_ext2.registered = False
        mock_core.extension_registry.get_all.return_value = [mock_ext1, mock_ext2]

        checker = ProductionHealthChecker(pbx_core=mock_core)
        metrics = checker._get_metrics()

        assert metrics["active_calls"] == 2
        assert metrics["registered_extensions"] == 1
        assert metrics["total_extensions"] == 2

    @patch("pbx.utils.production_health.psutil")
    @patch("pbx.utils.production_health.os")
    def test_metrics_pbx_core_error(self, mock_os, mock_psutil) -> None:
        mock_os.getpid.return_value = 1234
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 5.0
        mock_mem_info = MagicMock()
        mock_mem_info.rss = 50 * 1024 * 1024
        mock_process.memory_info.return_value = mock_mem_info
        mock_psutil.Process.return_value = mock_process
        mock_psutil.cpu_percent.return_value = 20.0
        mock_vm = MagicMock()
        mock_vm.percent = 40.0
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_disk = MagicMock()
        mock_disk.percent = 30.0
        mock_psutil.disk_usage.return_value = mock_disk

        mock_core = MagicMock()
        mock_core.call_manager.get_active_calls.side_effect = TypeError("bad")

        checker = ProductionHealthChecker(pbx_core=mock_core)
        metrics = checker._get_metrics()

        # PBX metrics should be missing but other metrics present
        assert "uptime_seconds" in metrics
        assert "active_calls" not in metrics

    @patch("pbx.utils.production_health.psutil")
    @patch("pbx.utils.production_health.os")
    def test_metrics_psutil_error(self, mock_os, mock_psutil) -> None:
        mock_os.getpid.return_value = 1234
        mock_psutil.Process.side_effect = TypeError("psutil error")

        checker = ProductionHealthChecker()
        metrics = checker._get_metrics()

        assert metrics == {}


@pytest.mark.unit
class TestFormatHealthCheckResponse:
    """Tests for format_health_check_response function."""

    def test_json_format_healthy(self) -> None:
        details = {"status": "healthy", "checks": {}}
        status_code, body = format_health_check_response(True, details, "json")
        assert status_code == 200
        parsed = json.loads(body)
        assert parsed["status"] == "healthy"

    def test_json_format_unhealthy(self) -> None:
        details = {"status": "unhealthy"}
        status_code, body = format_health_check_response(False, details, "json")
        assert status_code == 503
        parsed = json.loads(body)
        assert parsed["status"] == "unhealthy"

    def test_plain_format_healthy(self) -> None:
        status_code, body = format_health_check_response(True, {}, "plain")
        assert status_code == 200
        assert body == "OK"

    def test_plain_format_unhealthy(self) -> None:
        status_code, body = format_health_check_response(False, {}, "plain")
        assert status_code == 503
        assert body == "UNHEALTHY"

    def test_prometheus_format_healthy(self) -> None:
        details = {
            "metrics": {
                "uptime_seconds": 100.5,
                "active_calls": 5,
            }
        }
        status_code, body = format_health_check_response(True, details, "prometheus")
        assert status_code == 200
        assert "pbx_health 1" in body
        assert "pbx_uptime_seconds 100.5" in body
        assert "pbx_active_calls 5" in body
        assert "# HELP" in body
        assert "# TYPE" in body

    def test_prometheus_format_unhealthy(self) -> None:
        details = {"metrics": {}}
        status_code, body = format_health_check_response(False, details, "prometheus")
        assert status_code == 503
        assert "pbx_health 0" in body

    def test_prometheus_skips_non_numeric_metrics(self) -> None:
        details = {
            "metrics": {
                "uptime_seconds": 100,
                "status": "running",  # Non-numeric, should be skipped
            }
        }
        _status_code, body = format_health_check_response(True, details, "prometheus")
        assert "pbx_uptime_seconds 100" in body
        assert "pbx_status" not in body

    def test_prometheus_no_metrics(self) -> None:
        details = {}
        status_code, body = format_health_check_response(True, details, "prometheus")
        assert status_code == 200
        assert "pbx_health 1" in body

    def test_default_format_is_json(self) -> None:
        details = {"status": "ok"}
        status_code, body = format_health_check_response(True, details)
        assert status_code == 200
        parsed = json.loads(body)
        assert parsed["status"] == "ok"

    def test_unknown_format_defaults_to_json(self) -> None:
        details = {"status": "ok"}
        status_code, body = format_health_check_response(True, details, "unknown_format")
        assert status_code == 200
        parsed = json.loads(body)
        assert parsed["status"] == "ok"
