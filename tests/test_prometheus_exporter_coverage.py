"""Comprehensive tests for the PBXMetricsExporter (Prometheus exporter) module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pbx.utils.prometheus_exporter import PBXMetricsExporter


@pytest.mark.unit
class TestPBXMetricsExporterInit:
    """Tests for PBXMetricsExporter initialization."""

    def test_init_creates_default_registry(self) -> None:
        """Test initialization creates a new CollectorRegistry when none provided."""
        exporter = PBXMetricsExporter()

        assert exporter.registry is not None

    def test_init_with_custom_registry(self) -> None:
        """Test initialization with a custom CollectorRegistry."""
        from prometheus_client import CollectorRegistry

        custom_registry = CollectorRegistry()
        exporter = PBXMetricsExporter(registry=custom_registry)

        assert exporter.registry is custom_registry

    def test_all_metrics_created(self) -> None:
        """Test that all expected metrics are created during init."""
        exporter = PBXMetricsExporter()

        # System info
        assert exporter.pbx_info is not None

        # Call metrics
        assert exporter.calls_total is not None
        assert exporter.active_calls is not None
        assert exporter.call_duration is not None
        assert exporter.call_setup_time is not None

        # Extension metrics
        assert exporter.registered_extensions is not None
        assert exporter.extension_registrations_total is not None

        # Call quality metrics
        assert exporter.call_quality_mos is not None
        assert exporter.packet_loss_percent is not None
        assert exporter.jitter_ms is not None
        assert exporter.rtt_ms is not None

        # Voicemail metrics
        assert exporter.voicemail_total is not None
        assert exporter.voicemail_storage_bytes is not None

        # Conference metrics
        assert exporter.conferences_active is not None
        assert exporter.conference_participants is not None

        # Queue metrics
        assert exporter.queue_waiting_calls is not None
        assert exporter.queue_average_wait_time is not None
        assert exporter.queue_abandoned_calls is not None

        # API metrics
        assert exporter.api_requests_total is not None
        assert exporter.api_request_duration is not None

        # Database metrics
        assert exporter.db_connections_active is not None
        assert exporter.db_query_duration is not None

        # System resource metrics
        assert exporter.cpu_usage_percent is not None
        assert exporter.memory_usage_bytes is not None
        assert exporter.disk_usage_bytes is not None

        # SIP trunk metrics
        assert exporter.trunk_status is not None
        assert exporter.trunk_calls_active is not None

        # Error metrics
        assert exporter.errors_total is not None

        # Security metrics
        assert exporter.authentication_attempts is not None
        assert exporter.blocked_ips is not None

        # Certificate metrics
        assert exporter.certificate_expiry_days is not None


@pytest.mark.unit
class TestPBXMetricsExporterCallMetrics:
    """Tests for call-related metric recording."""

    def test_record_call_start_inbound(self) -> None:
        """Test recording an inbound call start."""
        exporter = PBXMetricsExporter()

        exporter.record_call_start(direction="inbound")

        # Verify the metrics were updated (no exception raised)
        metrics = exporter.export_metrics()
        assert b"pbx_calls_total" in metrics
        assert b"pbx_active_calls" in metrics

    def test_record_call_start_outbound(self) -> None:
        """Test recording an outbound call start."""
        exporter = PBXMetricsExporter()

        exporter.record_call_start(direction="outbound")

        metrics = exporter.export_metrics()
        assert b"outbound" in metrics

    def test_record_call_start_default_direction(self) -> None:
        """Test recording a call start with default direction (inbound)."""
        exporter = PBXMetricsExporter()

        exporter.record_call_start()

        metrics = exporter.export_metrics()
        assert b"inbound" in metrics

    def test_record_call_end_completed(self) -> None:
        """Test recording a completed call end."""
        exporter = PBXMetricsExporter()

        exporter.record_call_start(direction="inbound")
        exporter.record_call_end(duration=120.5, status="completed", direction="inbound")

        metrics = exporter.export_metrics()
        assert b"pbx_call_duration_seconds" in metrics

    def test_record_call_end_failed(self) -> None:
        """Test recording a failed call end."""
        exporter = PBXMetricsExporter()

        exporter.record_call_start(direction="inbound")
        exporter.record_call_end(duration=0.5, status="failed", direction="inbound")

        metrics = exporter.export_metrics()
        assert b"failed" in metrics

    def test_record_call_end_abandoned(self) -> None:
        """Test recording an abandoned call end."""
        exporter = PBXMetricsExporter()

        exporter.record_call_start(direction="inbound")
        exporter.record_call_end(duration=30.0, status="abandoned", direction="inbound")

        metrics = exporter.export_metrics()
        assert b"abandoned" in metrics

    def test_record_call_setup(self) -> None:
        """Test recording call setup time."""
        exporter = PBXMetricsExporter()

        exporter.record_call_setup(setup_time=2.5)

        metrics = exporter.export_metrics()
        assert b"pbx_call_setup_seconds" in metrics

    def test_record_multiple_calls(self) -> None:
        """Test recording multiple call starts and ends."""
        exporter = PBXMetricsExporter()

        exporter.record_call_start(direction="inbound")
        exporter.record_call_start(direction="outbound")
        exporter.record_call_start(direction="inbound")

        exporter.record_call_end(60.0, "completed", "inbound")
        exporter.record_call_end(120.0, "completed", "outbound")

        # active_calls should reflect: 3 starts - 2 ends = 1
        metrics = exporter.export_metrics()
        assert b"pbx_active_calls" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterCallQuality:
    """Tests for call quality metric recording."""

    def test_update_call_quality(self) -> None:
        """Test updating call quality metrics for an extension."""
        exporter = PBXMetricsExporter()

        exporter.update_call_quality(
            extension="1001",
            mos=4.2,
            packet_loss=0.5,
            jitter=15.0,
            rtt=45.0,
        )

        metrics = exporter.export_metrics()
        assert b"pbx_call_quality_mos" in metrics
        assert b"pbx_packet_loss_percent" in metrics
        assert b"pbx_jitter_milliseconds" in metrics
        assert b"pbx_rtt_milliseconds" in metrics
        assert b"1001" in metrics

    def test_update_call_quality_multiple_extensions(self) -> None:
        """Test updating call quality for multiple extensions."""
        exporter = PBXMetricsExporter()

        exporter.update_call_quality("1001", 4.5, 0.1, 5.0, 20.0)
        exporter.update_call_quality("1002", 3.8, 2.0, 25.0, 80.0)

        metrics = exporter.export_metrics()
        assert b"1001" in metrics
        assert b"1002" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterExtensions:
    """Tests for extension metric recording."""

    def test_update_extensions(self) -> None:
        """Test updating registered extensions count."""
        exporter = PBXMetricsExporter()

        exporter.update_extensions(registered_count=25)

        metrics = exporter.export_metrics()
        assert b"pbx_registered_extensions" in metrics

    def test_record_extension_registration_success(self) -> None:
        """Test recording a successful extension registration."""
        exporter = PBXMetricsExporter()

        exporter.record_extension_registration(status="success")

        metrics = exporter.export_metrics()
        assert b"pbx_extension_registrations_total" in metrics
        assert b"success" in metrics

    def test_record_extension_registration_failure(self) -> None:
        """Test recording a failed extension registration."""
        exporter = PBXMetricsExporter()

        exporter.record_extension_registration(status="failure")

        metrics = exporter.export_metrics()
        assert b"failure" in metrics

    def test_record_extension_registration_default(self) -> None:
        """Test recording extension registration with default status."""
        exporter = PBXMetricsExporter()

        exporter.record_extension_registration()

        metrics = exporter.export_metrics()
        assert b"success" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterAPIMetrics:
    """Tests for API metric recording."""

    def test_record_api_request(self) -> None:
        """Test recording an API request."""
        exporter = PBXMetricsExporter()

        exporter.record_api_request(
            method="GET",
            endpoint="/api/extensions",
            status_code=200,
            duration=0.05,
        )

        metrics = exporter.export_metrics()
        assert b"pbx_api_requests_total" in metrics
        assert b"pbx_api_request_duration_seconds" in metrics
        assert b"GET" in metrics

    def test_record_api_request_different_methods(self) -> None:
        """Test recording API requests with different HTTP methods."""
        exporter = PBXMetricsExporter()

        exporter.record_api_request("GET", "/api/calls", 200, 0.01)
        exporter.record_api_request("POST", "/api/calls", 201, 0.05)
        exporter.record_api_request("DELETE", "/api/calls/123", 204, 0.02)

        metrics = exporter.export_metrics()
        assert b"GET" in metrics
        assert b"POST" in metrics
        assert b"DELETE" in metrics

    def test_record_api_request_error_status(self) -> None:
        """Test recording API request with error status code."""
        exporter = PBXMetricsExporter()

        exporter.record_api_request("GET", "/api/missing", 404, 0.01)
        exporter.record_api_request("POST", "/api/bad", 500, 0.1)

        metrics = exporter.export_metrics()
        assert b"404" in metrics
        assert b"500" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterSystemResources:
    """Tests for system resource metric recording."""

    def test_update_system_resources(self) -> None:
        """Test updating CPU and memory metrics."""
        exporter = PBXMetricsExporter()

        exporter.update_system_resources(cpu_percent=45.5, memory_bytes=1073741824)

        metrics = exporter.export_metrics()
        assert b"pbx_cpu_usage_percent" in metrics
        assert b"pbx_memory_usage_bytes" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterQueueMetrics:
    """Tests for queue metric recording."""

    def test_update_queue_metrics(self) -> None:
        """Test updating queue metrics."""
        exporter = PBXMetricsExporter()

        exporter.update_queue_metrics(
            queue_name="support",
            waiting_calls=5,
            avg_wait_time=120.0,
        )

        metrics = exporter.export_metrics()
        assert b"pbx_queue_waiting_calls" in metrics
        assert b"pbx_queue_average_wait_seconds" in metrics
        assert b"support" in metrics

    def test_record_queue_abandoned(self) -> None:
        """Test recording an abandoned call in a queue."""
        exporter = PBXMetricsExporter()

        exporter.record_queue_abandoned(queue_name="sales")

        metrics = exporter.export_metrics()
        assert b"pbx_queue_abandoned_calls_total" in metrics
        assert b"sales" in metrics

    def test_update_multiple_queues(self) -> None:
        """Test updating metrics for multiple queues."""
        exporter = PBXMetricsExporter()

        exporter.update_queue_metrics("support", 3, 60.0)
        exporter.update_queue_metrics("sales", 1, 30.0)

        metrics = exporter.export_metrics()
        assert b"support" in metrics
        assert b"sales" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterTrunkMetrics:
    """Tests for SIP trunk metric recording."""

    def test_update_trunk_status_up(self) -> None:
        """Test updating trunk status as up."""
        exporter = PBXMetricsExporter()

        exporter.update_trunk_status("main_trunk", is_up=True, active_calls=5)

        metrics = exporter.export_metrics()
        assert b"pbx_trunk_status" in metrics
        assert b"pbx_trunk_calls_active" in metrics
        assert b"main_trunk" in metrics

    def test_update_trunk_status_down(self) -> None:
        """Test updating trunk status as down."""
        exporter = PBXMetricsExporter()

        exporter.update_trunk_status("backup_trunk", is_up=False, active_calls=0)

        metrics = exporter.export_metrics()
        assert b"backup_trunk" in metrics

    def test_update_trunk_status_default_calls(self) -> None:
        """Test updating trunk status with default active_calls (0)."""
        exporter = PBXMetricsExporter()

        exporter.update_trunk_status("trunk1", is_up=True)

        metrics = exporter.export_metrics()
        assert b"trunk1" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterErrorMetrics:
    """Tests for error metric recording."""

    def test_record_error(self) -> None:
        """Test recording an error."""
        exporter = PBXMetricsExporter()

        exporter.record_error(error_type="timeout", component="sip")

        metrics = exporter.export_metrics()
        assert b"pbx_errors_total" in metrics
        assert b"timeout" in metrics
        assert b"sip" in metrics

    def test_record_multiple_error_types(self) -> None:
        """Test recording different error types."""
        exporter = PBXMetricsExporter()

        exporter.record_error("timeout", "sip")
        exporter.record_error("codec_error", "rtp")
        exporter.record_error("auth_failure", "api")

        metrics = exporter.export_metrics()
        assert b"timeout" in metrics
        assert b"codec_error" in metrics
        assert b"auth_failure" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterSecurityMetrics:
    """Tests for security metric recording."""

    def test_record_auth_attempt_success(self) -> None:
        """Test recording a successful authentication attempt."""
        exporter = PBXMetricsExporter()

        exporter.record_auth_attempt(status="success", method="password")

        metrics = exporter.export_metrics()
        assert b"pbx_authentication_attempts_total" in metrics
        assert b"success" in metrics
        assert b"password" in metrics

    def test_record_auth_attempt_failure(self) -> None:
        """Test recording a failed authentication attempt."""
        exporter = PBXMetricsExporter()

        exporter.record_auth_attempt(status="failure", method="api_key")

        metrics = exporter.export_metrics()
        assert b"failure" in metrics
        assert b"api_key" in metrics

    def test_record_auth_attempt_default_method(self) -> None:
        """Test recording auth attempt with default method (password)."""
        exporter = PBXMetricsExporter()

        exporter.record_auth_attempt(status="success")

        metrics = exporter.export_metrics()
        assert b"password" in metrics

    def test_update_certificate_expiry(self) -> None:
        """Test updating certificate expiry metric."""
        exporter = PBXMetricsExporter()

        exporter.update_certificate_expiry("main_cert", days_until_expiry=30)

        metrics = exporter.export_metrics()
        assert b"pbx_certificate_expiry_days" in metrics
        assert b"main_cert" in metrics

    def test_update_certificate_expiry_multiple_certs(self) -> None:
        """Test updating expiry for multiple certificates."""
        exporter = PBXMetricsExporter()

        exporter.update_certificate_expiry("tls_cert", 90)
        exporter.update_certificate_expiry("api_cert", 15)

        metrics = exporter.export_metrics()
        assert b"tls_cert" in metrics
        assert b"api_cert" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterVoicemailMetrics:
    """Tests for voicemail metric recording."""

    def test_voicemail_total_counter(self) -> None:
        """Test voicemail total counter metric."""
        exporter = PBXMetricsExporter()

        exporter.voicemail_total.labels(status="received").inc()
        exporter.voicemail_total.labels(status="listened").inc()

        metrics = exporter.export_metrics()
        assert b"pbx_voicemail_messages_total" in metrics

    def test_voicemail_storage_gauge(self) -> None:
        """Test voicemail storage gauge metric."""
        exporter = PBXMetricsExporter()

        exporter.voicemail_storage_bytes.set(1048576)

        metrics = exporter.export_metrics()
        assert b"pbx_voicemail_storage_bytes" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterConferenceMetrics:
    """Tests for conference metric recording."""

    def test_conferences_active_gauge(self) -> None:
        """Test active conferences gauge metric."""
        exporter = PBXMetricsExporter()

        exporter.conferences_active.set(3)

        metrics = exporter.export_metrics()
        assert b"pbx_conferences_active" in metrics

    def test_conference_participants_gauge(self) -> None:
        """Test conference participants gauge metric."""
        exporter = PBXMetricsExporter()

        exporter.conference_participants.labels(conference_id="conf-001").set(5)
        exporter.conference_participants.labels(conference_id="conf-002").set(10)

        metrics = exporter.export_metrics()
        assert b"pbx_conference_participants" in metrics
        assert b"conf-001" in metrics
        assert b"conf-002" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterDatabaseMetrics:
    """Tests for database metric recording."""

    def test_db_connections_active(self) -> None:
        """Test active database connections gauge."""
        exporter = PBXMetricsExporter()

        exporter.db_connections_active.set(10)

        metrics = exporter.export_metrics()
        assert b"pbx_db_connections_active" in metrics

    def test_db_query_duration(self) -> None:
        """Test database query duration histogram."""
        exporter = PBXMetricsExporter()

        exporter.db_query_duration.labels(query_type="select").observe(0.05)
        exporter.db_query_duration.labels(query_type="insert").observe(0.01)

        metrics = exporter.export_metrics()
        assert b"pbx_db_query_duration_seconds" in metrics
        assert b"select" in metrics
        assert b"insert" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterDiskMetrics:
    """Tests for disk usage metric recording."""

    def test_disk_usage_bytes(self) -> None:
        """Test disk usage gauge with mount point label."""
        exporter = PBXMetricsExporter()

        exporter.disk_usage_bytes.labels(mount_point="/").set(50000000000)
        exporter.disk_usage_bytes.labels(mount_point="/data").set(100000000000)

        metrics = exporter.export_metrics()
        assert b"pbx_disk_usage_bytes" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterBlockedIPs:
    """Tests for blocked IPs metric recording."""

    def test_blocked_ips_gauge(self) -> None:
        """Test blocked IPs gauge metric."""
        exporter = PBXMetricsExporter()

        exporter.blocked_ips.set(42)

        metrics = exporter.export_metrics()
        assert b"pbx_blocked_ips" in metrics


@pytest.mark.unit
class TestPBXMetricsExporterExport:
    """Tests for metrics export functionality."""

    def test_export_metrics_returns_bytes(self) -> None:
        """Test that export_metrics returns bytes."""
        exporter = PBXMetricsExporter()

        result = exporter.export_metrics()

        assert isinstance(result, bytes)

    def test_export_metrics_contains_help_text(self) -> None:
        """Test that exported metrics contain HELP documentation."""
        exporter = PBXMetricsExporter()

        result = exporter.export_metrics()

        assert b"# HELP" in result

    def test_export_metrics_contains_type_info(self) -> None:
        """Test that exported metrics contain TYPE information."""
        exporter = PBXMetricsExporter()

        result = exporter.export_metrics()

        assert b"# TYPE" in result

    def test_export_metrics_after_recording(self) -> None:
        """Test that export includes recently recorded metrics."""
        exporter = PBXMetricsExporter()

        exporter.record_call_start("inbound")
        exporter.record_call_end(60.0, "completed", "inbound")
        exporter.record_error("timeout", "sip")
        exporter.update_extensions(10)

        result = exporter.export_metrics()

        assert b"pbx_calls_total" in result
        assert b"pbx_errors_total" in result
        assert b"pbx_registered_extensions" in result


@pytest.mark.unit
class TestPBXMetricsExporterSystemInfo:
    """Tests for system info metric recording."""

    def test_set_system_info_version_only(self) -> None:
        """Test setting system info with version only."""
        exporter = PBXMetricsExporter()

        exporter.set_system_info(version="1.0.0")

        metrics = exporter.export_metrics()
        assert b"pbx_system_info" in metrics
        assert b"1.0.0" in metrics

    def test_set_system_info_with_kwargs(self) -> None:
        """Test setting system info with additional keyword arguments."""
        exporter = PBXMetricsExporter()

        exporter.set_system_info(
            version="2.0.0",
            hostname="pbx-server-01",
            environment="production",
        )

        metrics = exporter.export_metrics()
        assert b"2.0.0" in metrics
        assert b"pbx-server-01" in metrics
        assert b"production" in metrics
