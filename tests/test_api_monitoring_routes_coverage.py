"""Tests for monitoring routes coverage.

Note: The file pbx/api/routes/monitoring.py does not exist in this codebase.
Monitoring-related endpoints may be spread across other route modules
(health.py, qos.py, etc.). This file validates that there is no monitoring
blueprint by testing that the expected module does not exist.
"""

import importlib

import pytest


@pytest.mark.unit
class TestMonitoringModuleExists:
    """Verify that the monitoring route module state is as expected."""

    def test_monitoring_module_does_not_exist(self) -> None:
        """The monitoring route module should not be importable."""
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("pbx.api.routes.monitoring")
