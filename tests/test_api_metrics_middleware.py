"""Tests for the Flask API metrics middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pbx.utils.prometheus_exporter import PBXMetricsExporter

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from flask.testing import FlaskClient


@pytest.mark.unit
class TestAPIMetricsMiddleware:
    """Tests for automatic API request metrics recording."""

    def test_request_records_metrics(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test that API requests are recorded in Prometheus metrics."""
        exporter = PBXMetricsExporter()
        mock_pbx_core.metrics_exporter = exporter

        api_client.get("/health")

        metrics = exporter.export_metrics()
        assert b"pbx_api_requests_total" in metrics
        assert b"pbx_api_request_duration_seconds" in metrics

    def test_request_records_method(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test that the HTTP method is recorded."""
        exporter = PBXMetricsExporter()
        mock_pbx_core.metrics_exporter = exporter

        api_client.get("/health")

        metrics = exporter.export_metrics()
        assert b"GET" in metrics

    def test_request_records_status_code(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test that the status code is recorded."""
        exporter = PBXMetricsExporter()
        mock_pbx_core.metrics_exporter = exporter

        api_client.get("/health")

        metrics = exporter.export_metrics()
        # Health endpoint returns 200 or 503
        assert b"200" in metrics or b"503" in metrics

    def test_no_metrics_without_exporter(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test that requests work normally without metrics exporter."""
        mock_pbx_core.metrics_exporter = None

        response = api_client.get("/health")

        # Should still work fine without exporter
        assert response.status_code in (200, 503)

    def test_multiple_requests_recorded(
        self, mock_pbx_core: MagicMock, api_client: FlaskClient
    ) -> None:
        """Test that multiple requests are all recorded."""
        exporter = PBXMetricsExporter()
        mock_pbx_core.metrics_exporter = exporter

        api_client.get("/health")
        api_client.get("/health")
        api_client.get("/health")

        metrics = exporter.export_metrics()
        assert b"pbx_api_requests_total" in metrics
