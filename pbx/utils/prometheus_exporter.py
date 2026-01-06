#!/usr/bin/env python3
"""
Prometheus metrics exporter for PBX system.

Provides comprehensive metrics for monitoring call quality, system health,
and performance in production environments.
"""

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Info,
        CollectorRegistry,
        generate_latest,
    )
except ImportError as exc:
    raise ImportError(
        "The 'prometheus-client' package is required to use PBXMetricsExporter. "
        "Install it with 'pip install prometheus-client' or disable Prometheus "
        "metrics if they are not needed."
    ) from exc


class PBXMetricsExporter:
    """Export PBX metrics in Prometheus format."""

    def __init__(self, registry: CollectorRegistry = None):
        """
        Initialize metrics exporter.

        Args:
            registry: Prometheus registry (creates new one if None)
        """
        self.registry = registry or CollectorRegistry()

        # System info
        self.pbx_info = Info(
            "pbx_system",
            "PBX system information",
            registry=self.registry,
        )

        # Call metrics
        self.calls_total = Counter(
            "pbx_calls_total",
            "Total number of calls",
            ["status", "direction"],
            registry=self.registry,
        )

        self.active_calls = Gauge(
            "pbx_active_calls",
            "Number of currently active calls",
            registry=self.registry,
        )

        self.call_duration = Histogram(
            "pbx_call_duration_seconds",
            "Call duration in seconds",
            ["status"],
            buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],
            registry=self.registry,
        )

        self.call_setup_time = Histogram(
            "pbx_call_setup_seconds",
            "Time to establish a call in seconds",
            buckets=[0.5, 1, 2, 3, 5, 10, 30],
            registry=self.registry,
        )

        # Extension metrics
        self.registered_extensions = Gauge(
            "pbx_registered_extensions",
            "Number of registered SIP extensions",
            registry=self.registry,
        )

        self.extension_registrations_total = Counter(
            "pbx_extension_registrations_total",
            "Total number of extension registrations",
            ["status"],
            registry=self.registry,
        )

        # Call quality metrics
        self.call_quality_mos = Gauge(
            "pbx_call_quality_mos",
            "Mean Opinion Score (MOS) for call quality",
            ["extension"],
            registry=self.registry,
        )

        self.packet_loss_percent = Gauge(
            "pbx_packet_loss_percent",
            "Packet loss percentage",
            ["extension"],
            registry=self.registry,
        )

        self.jitter_ms = Gauge(
            "pbx_jitter_milliseconds",
            "Jitter in milliseconds",
            ["extension"],
            registry=self.registry,
        )

        self.rtt_ms = Gauge(
            "pbx_rtt_milliseconds",
            "Round-trip time in milliseconds",
            ["extension"],
            registry=self.registry,
        )

        # Voicemail metrics
        self.voicemail_total = Counter(
            "pbx_voicemail_messages_total",
            "Total number of voicemail messages",
            ["status"],
            registry=self.registry,
        )

        self.voicemail_storage_bytes = Gauge(
            "pbx_voicemail_storage_bytes",
            "Total voicemail storage in bytes",
            registry=self.registry,
        )

        # Conference metrics
        self.conferences_active = Gauge(
            "pbx_conferences_active",
            "Number of active conferences",
            registry=self.registry,
        )

        self.conference_participants = Gauge(
            "pbx_conference_participants",
            "Number of conference participants",
            ["conference_id"],
            registry=self.registry,
        )

        # Queue metrics
        self.queue_waiting_calls = Gauge(
            "pbx_queue_waiting_calls",
            "Number of calls waiting in queue",
            ["queue_name"],
            registry=self.registry,
        )

        self.queue_average_wait_time = Gauge(
            "pbx_queue_average_wait_seconds",
            "Average wait time in queue",
            ["queue_name"],
            registry=self.registry,
        )

        self.queue_abandoned_calls = Counter(
            "pbx_queue_abandoned_calls_total",
            "Total number of abandoned calls",
            ["queue_name"],
            registry=self.registry,
        )

        # API metrics
        self.api_requests_total = Counter(
            "pbx_api_requests_total",
            "Total API requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        self.api_request_duration = Histogram(
            "pbx_api_request_duration_seconds",
            "API request duration",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
            registry=self.registry,
        )

        # Database metrics
        self.db_connections_active = Gauge(
            "pbx_db_connections_active",
            "Number of active database connections",
            registry=self.registry,
        )

        self.db_query_duration = Histogram(
            "pbx_db_query_duration_seconds",
            "Database query duration",
            ["query_type"],
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1, 5],
            registry=self.registry,
        )

        # System resource metrics
        self.cpu_usage_percent = Gauge(
            "pbx_cpu_usage_percent",
            "CPU usage percentage",
            registry=self.registry,
        )

        self.memory_usage_bytes = Gauge(
            "pbx_memory_usage_bytes",
            "Memory usage in bytes",
            registry=self.registry,
        )

        self.disk_usage_bytes = Gauge(
            "pbx_disk_usage_bytes",
            "Disk usage in bytes",
            ["mount_point"],
            registry=self.registry,
        )

        # SIP trunk metrics
        self.trunk_status = Gauge(
            "pbx_trunk_status",
            "SIP trunk status (1=up, 0=down)",
            ["trunk_name"],
            registry=self.registry,
        )

        self.trunk_calls_active = Gauge(
            "pbx_trunk_calls_active",
            "Active calls on trunk",
            ["trunk_name"],
            registry=self.registry,
        )

        # Error metrics
        self.errors_total = Counter(
            "pbx_errors_total",
            "Total number of errors",
            ["error_type", "component"],
            registry=self.registry,
        )

        # Security metrics
        self.authentication_attempts = Counter(
            "pbx_authentication_attempts_total",
            "Authentication attempts",
            ["status", "method"],
            registry=self.registry,
        )

        self.blocked_ips = Gauge(
            "pbx_blocked_ips",
            "Number of blocked IP addresses",
            registry=self.registry,
        )

        # Certificate metrics
        self.certificate_expiry_days = Gauge(
            "pbx_certificate_expiry_days",
            "Days until certificate expiration",
            ["certificate_name"],
            registry=self.registry,
        )

    def record_call_start(self, direction: str = "inbound"):
        """
        Record a call start.

        Args:
            direction: Call direction (inbound/outbound)
        """
        self.calls_total.labels(status="started", direction=direction).inc()
        self.active_calls.inc()

    def record_call_end(
        self, duration: float, status: str = "completed", direction: str = "inbound"
    ):
        """
        Record a call end.

        Args:
            duration: Call duration in seconds
            status: Call status (completed/failed/abandoned)
            direction: Call direction
        """
        self.calls_total.labels(status=status, direction=direction).inc()
        self.active_calls.dec()
        self.call_duration.labels(status=status).observe(duration)

    def record_call_setup(self, setup_time: float):
        """
        Record call setup time.

        Args:
            setup_time: Setup time in seconds
        """
        self.call_setup_time.observe(setup_time)

    def update_call_quality(
        self, extension: str, mos: float, packet_loss: float, jitter: float, rtt: float
    ):
        """
        Update call quality metrics.

        Args:
            extension: Extension number
            mos: Mean Opinion Score
            packet_loss: Packet loss percentage
            jitter: Jitter in milliseconds
            rtt: Round-trip time in milliseconds
        """
        self.call_quality_mos.labels(extension=extension).set(mos)
        self.packet_loss_percent.labels(extension=extension).set(packet_loss)
        self.jitter_ms.labels(extension=extension).set(jitter)
        self.rtt_ms.labels(extension=extension).set(rtt)

    def update_extensions(self, registered_count: int):
        """
        Update registered extensions count.

        Args:
            registered_count: Number of registered extensions
        """
        self.registered_extensions.set(registered_count)

    def record_extension_registration(self, status: str = "success"):
        """
        Record extension registration attempt.

        Args:
            status: Registration status (success/failure)
        """
        self.extension_registrations_total.labels(status=status).inc()

    def record_api_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """
        Record API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            status_code: HTTP status code
            duration: Request duration in seconds
        """
        self.api_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()
        self.api_request_duration.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    def update_system_resources(self, cpu_percent: float, memory_bytes: int):
        """
        Update system resource metrics.

        Args:
            cpu_percent: CPU usage percentage
            memory_bytes: Memory usage in bytes
        """
        self.cpu_usage_percent.set(cpu_percent)
        self.memory_usage_bytes.set(memory_bytes)

    def update_queue_metrics(
        self, queue_name: str, waiting_calls: int, avg_wait_time: float
    ):
        """
        Update call queue metrics.

        Args:
            queue_name: Queue name
            waiting_calls: Number of waiting calls
            avg_wait_time: Average wait time in seconds
        """
        self.queue_waiting_calls.labels(queue_name=queue_name).set(waiting_calls)
        self.queue_average_wait_time.labels(queue_name=queue_name).set(avg_wait_time)

    def record_queue_abandoned(self, queue_name: str):
        """
        Record abandoned call in queue.

        Args:
            queue_name: Queue name
        """
        self.queue_abandoned_calls.labels(queue_name=queue_name).inc()

    def update_trunk_status(self, trunk_name: str, is_up: bool, active_calls: int = 0):
        """
        Update SIP trunk status.

        Args:
            trunk_name: Trunk name
            is_up: Whether trunk is up
            active_calls: Number of active calls on trunk
        """
        self.trunk_status.labels(trunk_name=trunk_name).set(1 if is_up else 0)
        self.trunk_calls_active.labels(trunk_name=trunk_name).set(active_calls)

    def record_error(self, error_type: str, component: str):
        """
        Record an error.

        Args:
            error_type: Type of error
            component: Component where error occurred
        """
        self.errors_total.labels(error_type=error_type, component=component).inc()

    def record_auth_attempt(self, status: str, method: str = "password"):
        """
        Record authentication attempt.

        Args:
            status: Authentication status (success/failure)
            method: Authentication method
        """
        self.authentication_attempts.labels(status=status, method=method).inc()

    def update_certificate_expiry(self, cert_name: str, days_until_expiry: int):
        """
        Update certificate expiry metric.

        Args:
            cert_name: Certificate name
            days_until_expiry: Days until expiration
        """
        self.certificate_expiry_days.labels(certificate_name=cert_name).set(
            days_until_expiry
        )

    def export_metrics(self) -> bytes:
        """
        Export metrics in Prometheus format.

        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry)

    def set_system_info(self, version: str, **kwargs):
        """
        Set system information.

        Args:
            version: PBX version
            **kwargs: Additional system info
        """
        info = {"version": version}
        info.update(kwargs)
        self.pbx_info.info(info)
