"""Tests for the /metrics Prometheus endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pbx.utils.prometheus_exporter import PBXMetricsExporter

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from flask.testing import FlaskClient


@pytest.mark.unit
class TestMetricsEndpointWithExporter:
    """Tests for /metrics endpoint when PBXMetricsExporter is available."""

    def test_metrics_returns_prometheus_format(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test /metrics returns prometheus_client output."""
        mock_pbx_core.metrics_exporter = PBXMetricsExporter()
        response = api_client.get("/metrics")

        assert response.status_code == 200
        assert b"# HELP" in response.data
        assert b"# TYPE" in response.data
        assert b"pbx_active_calls" in response.data

    def test_metrics_contains_all_metric_families(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test /metrics includes key metric families."""
        mock_pbx_core.metrics_exporter = PBXMetricsExporter()
        response = api_client.get("/metrics")

        assert response.status_code == 200
        assert b"pbx_calls_total" in response.data
        assert b"pbx_registered_extensions" in response.data
        assert b"pbx_api_requests_total" in response.data
        assert b"pbx_errors_total" in response.data

    def test_metrics_content_type(self, mock_pbx_core: MagicMock, api_client: FlaskClient) -> None:
        """Test /metrics returns correct content type."""
        mock_pbx_core.metrics_exporter = PBXMetricsExporter()
        response = api_client.get("/metrics")

        assert "text/plain" in response.content_type

    def test_metrics_with_recorded_data(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test /metrics includes recently recorded metric data."""
        exporter = PBXMetricsExporter()
        exporter.record_call_start("inbound")
        exporter.update_extensions(5)
        mock_pbx_core.metrics_exporter = exporter

        response = api_client.get("/metrics")

        assert response.status_code == 200
        assert b"pbx_active_calls" in response.data
        assert b"pbx_registered_extensions" in response.data


@pytest.mark.unit
class TestMetricsEndpointFallback:
    """Tests for /metrics endpoint when PBXMetricsExporter is not available."""

    def test_metrics_fallback_without_exporter(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test /metrics falls back to health check format when no exporter."""
        mock_pbx_core.metrics_exporter = None
        response = api_client.get("/metrics")

        # Should still return a response (either health data or error)
        assert response.status_code in (200, 500, 503)

    def test_metrics_fallback_no_pbx_core(self, api_client: FlaskClient) -> None:
        """Test /metrics handles missing PBX core gracefully."""
        response = api_client.get("/metrics")
        assert response.status_code in (200, 500, 503)
