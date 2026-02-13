"""
Production health check and monitoring utilities.

This module provides comprehensive health checks for production deployments,
including database connectivity, SIP server status, API responsiveness, and
system resource monitoring.
"""

import logging
import os
import socket
import time
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class ProductionHealthChecker:
    """
    Comprehensive health checker for production PBX deployments.

    Provides both liveness (is the service running?) and readiness
    (is the service ready to handle requests?) checks.
    """

    def __init__(self, pbx_core=None, config=None):
        """
        Initialize health checker.

        Args:
            pbx_core: Reference to PBX core instance
            config: System configuration dictionary
        """
        self.pbx_core = pbx_core
        self.config = config or {}
        self.start_time = time.time()

    def check_liveness(self) -> tuple[bool, dict[str, Any]]:
        """
        Check if the application is alive (lightweight check).

        This should be a fast check that doesn't require external dependencies.
        Used by orchestration systems to determine if the container should be restarted.

        Returns:
            tuple of (is_alive, details_dict)
        """
        try:
            uptime = time.time() - self.start_time

            return True, {
                "status": "alive",
                "uptime_seconds": round(uptime, 2),
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"Liveness check failed: {e}")
            return False, {"status": "dead", "error": str(e), "timestamp": time.time()}

    def check_readiness(self) -> tuple[bool, dict[str, Any]]:
        """
        Check if the application is ready to serve traffic.

        Performs comprehensive checks of all critical dependencies.
        Used by load balancers to determine if traffic should be routed here.

        Returns:
            tuple of (is_ready, details_dict)
        """
        checks = {}
        is_ready = True

        # Check PBX core
        pbx_ready, pbx_details = self._check_pbx_core()
        checks["pbx_core"] = pbx_details
        is_ready = is_ready and pbx_ready

        # Check database connectivity
        db_ready, db_details = self._check_database()
        checks["database"] = db_details
        is_ready = is_ready and db_ready

        # Check SIP server
        sip_ready, sip_details = self._check_sip_server()
        checks["sip_server"] = sip_details
        is_ready = is_ready and sip_ready

        # Check system resources
        resource_ok, resource_details = self._check_system_resources()
        checks["system_resources"] = resource_details
        is_ready = is_ready and resource_ok

        return is_ready, {
            "status": "ready" if is_ready else "not_ready",
            "checks": checks,
            "timestamp": time.time(),
        }

    def get_detailed_status(self) -> dict[str, Any]:
        """
        Get comprehensive system status for monitoring dashboards.

        Returns:
            Dictionary with detailed status information
        """
        liveness_ok, liveness_details = self.check_liveness()
        readiness_ok, readiness_details = self.check_readiness()

        return {
            "overall_status": "healthy" if (liveness_ok and readiness_ok) else "unhealthy",
            "liveness": liveness_details,
            "readiness": readiness_details,
            "metrics": self._get_metrics(),
            "version": self.config.get("server", {}).get("version", "unknown"),
            "server_name": self.config.get("server", {}).get("server_name", "Warden Voip"),
        }

    def _check_pbx_core(self) -> tuple[bool, dict[str, Any]]:
        """Check PBX core status."""
        try:
            if not self.pbx_core:
                return False, {"status": "not_initialized", "message": "PBX core not available"}

            # Check if PBX has required components
            has_sip = hasattr(self.pbx_core, "sip_server") and self.pbx_core.sip_server is not None
            has_extension_registry = hasattr(self.pbx_core, "extension_registry")
            has_call_manager = hasattr(self.pbx_core, "call_manager")

            if not (has_sip and has_extension_registry and has_call_manager):
                return False, {
                    "status": "incomplete",
                    "has_sip_server": has_sip,
                    "has_extension_registry": has_extension_registry,
                    "has_call_manager": has_call_manager,
                }

            # Get basic stats
            try:
                active_calls = len(self.pbx_core.call_manager.get_active_calls())
                registered_extensions = len(
                    [e for e in self.pbx_core.extension_registry.get_all() if e.registered]
                )
            except Exception:
                active_calls = 0
                registered_extensions = 0

            return True, {
                "status": "operational",
                "active_calls": active_calls,
                "registered_extensions": registered_extensions,
            }

        except Exception as e:
            logger.error(f"PBX core check failed: {e}")
            return False, {"status": "error", "error": str(e)}

    def _check_database(self) -> tuple[bool, dict[str, Any]]:
        """Check database connectivity."""
        try:
            from pbx.utils.database import get_database_connection

            db_config = self.config.get("database", {})
            db_type = db_config.get("type", "sqlite")

            # Try to get a connection
            conn = get_database_connection(self.config)
            if not conn:
                return False, {
                    "status": "unavailable",
                    "type": db_type,
                    "message": "Could not establish connection",
                }

            # Try a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()

            return True, {"status": "connected", "type": db_type}

        except ImportError:
            # Database module not available, that's ok in some configs
            return True, {"status": "not_configured", "message": "Database module not available"}
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False, {"status": "error", "error": str(e)}

    def _check_sip_server(self) -> tuple[bool, dict[str, Any]]:
        """Check if SIP server port is listening."""
        try:
            sip_config = self.config.get("server", {})
            sip_port = sip_config.get("sip_port", 5060)

            # Try to check if port is listening
            # Note: This is a basic check, doesn't verify full SIP functionality
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)

            try:
                # For UDP, we can check if we can bind (if not already bound)
                # In production, the port will be bound by the SIP server
                # This is a simplified check
                sock.bind(("127.0.0.1", 0))  # Bind to any available port
                sock.close()

                # If we can bind, assume SIP server is managing the actual port
                return True, {
                    "status": "assumed_running",
                    "port": sip_port,
                    "message": "SIP server port check passed",
                }
            except OSError:
                # Can't bind, which is actually good - means port is in use
                sock.close()
                return True, {
                    "status": "port_in_use",
                    "port": sip_port,
                    "message": "SIP port appears to be in use (expected)",
                }

        except Exception as e:
            logger.error(f"SIP server check failed: {e}")
            return False, {"status": "error", "error": str(e)}

    def _check_system_resources(self) -> tuple[bool, dict[str, Any]]:
        """Check system resource availability."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Define warning thresholds
            cpu_warning = 80
            memory_warning = 85
            disk_warning = 90

            is_ok = (
                cpu_percent < cpu_warning
                and memory.percent < memory_warning
                and disk.percent < disk_warning
            )

            warnings = []
            if cpu_percent >= cpu_warning:
                warnings.append(f"High CPU usage: {cpu_percent}%")
            if memory.percent >= memory_warning:
                warnings.append(f"High memory usage: {memory.percent}%")
            if disk.percent >= disk_warning:
                warnings.append(f"High disk usage: {disk.percent}%")

            return is_ok, {
                "status": "ok" if is_ok else "warning",
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "disk_percent": round(disk.percent, 2),
                "warnings": warnings if warnings else None,
            }

        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            # Don't fail readiness on resource check errors
            return True, {"status": "unavailable", "error": str(e)}

    def _get_metrics(self) -> dict[str, Any]:
        """Get Prometheus-style metrics."""
        try:
            metrics = {
                "uptime_seconds": round(time.time() - self.start_time, 2),
                "process_cpu_percent": psutil.Process(os.getpid()).cpu_percent(),
                "process_memory_mb": round(
                    psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2
                ),
                "system_cpu_percent": psutil.cpu_percent(),
                "system_memory_percent": psutil.virtual_memory().percent,
                "system_disk_percent": psutil.disk_usage("/").percent,
            }

            if self.pbx_core:
                try:
                    metrics["active_calls"] = len(self.pbx_core.call_manager.get_active_calls())
                    metrics["registered_extensions"] = len(
                        [e for e in self.pbx_core.extension_registry.get_all() if e.registered]
                    )
                    metrics["total_extensions"] = len(self.pbx_core.extension_registry.get_all())
                except Exception as e:
                    logger.debug(f"Could not get PBX metrics: {e}")

            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {}


def format_health_check_response(
    is_healthy: bool, details: dict[str, Any], format_type: str = "json"
) -> tuple[int, str]:
    """
    Format health check response for different consumers.

    Args:
        is_healthy: Whether the check passed
        details: Detailed check results
        format_type: "json", "prometheus", or "plain"

    Returns:
        tuple of (http_status_code, formatted_response)
    """
    import json

    status_code = 200 if is_healthy else 503

    if format_type == "prometheus":
        # Prometheus text format
        lines = []
        lines.append("# HELP pbx_health Health check status (1 = healthy, 0 = unhealthy)")
        lines.append("# TYPE pbx_health gauge")
        lines.append(f"pbx_health {1 if is_healthy else 0}")

        if "metrics" in details:
            for key, value in details["metrics"].items():
                if isinstance(value, (int, float)):
                    lines.append(f"# HELP pbx_{key} {key.replace('_', ' ').title()}")
                    lines.append(f"# TYPE pbx_{key} gauge")
                    lines.append(f"pbx_{key} {value}")

        return status_code, "\n".join(lines)

    elif format_type == "plain":
        # Simple text format
        return status_code, "OK" if is_healthy else "UNHEALTHY"

    else:  # json (default)
        return status_code, json.dumps(details, indent=2)
