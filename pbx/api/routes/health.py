"""Health check and monitoring Blueprint routes.

These routes do NOT require authentication. They provide health checks,
readiness/liveness probes, Prometheus metrics, and status endpoints.
"""

import json

from flask import Blueprint, current_app, redirect, request

from pbx.api.utils import get_pbx_core, send_json
from pbx.utils.logger import get_logger

logger = get_logger()

health_bp = Blueprint("health", __name__)

# Module-level cache for health checker instance
_health_checker = None


def _get_health_checker():
    """Get or create production health checker instance."""
    global _health_checker
    if _health_checker is None:
        from pbx.utils.production_health import ProductionHealthChecker

        pbx_core = get_pbx_core()
        config = None
        if pbx_core and hasattr(pbx_core, "config"):
            config = pbx_core.config

        _health_checker = ProductionHealthChecker(
            pbx_core=pbx_core, config=config
        )

    return _health_checker


@health_bp.route("/")
def handle_root():
    """Handle root path - redirect to admin panel."""
    return redirect("/admin", code=302)


@health_bp.route("/health")
@health_bp.route("/healthz")
def handle_health():
    """Lightweight health check endpoint for container orchestration.

    Combined liveness/readiness check for backward compatibility.
    """
    try:
        checker = _get_health_checker()
        is_ready, details = checker.check_readiness()

        status_code = 200 if is_ready else 503
        return send_json(details, status_code)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return send_json({"status": "error", "error": str(e)}, 500)


@health_bp.route("/ready")
@health_bp.route("/readiness")
def handle_readiness():
    """Kubernetes-style readiness probe - check if the app is ready for traffic."""
    try:
        checker = _get_health_checker()
        is_ready, details = checker.check_readiness()

        status_code = 200 if is_ready else 503
        return send_json(details, status_code)
    except Exception as e:
        logger.error(f"Readiness check error: {e}")
        return send_json({"status": "error", "error": str(e)}, 500)


@health_bp.route("/live")
@health_bp.route("/liveness")
def handle_liveness():
    """Kubernetes-style liveness probe - check if the app is alive."""
    try:
        checker = _get_health_checker()
        is_alive, details = checker.check_liveness()

        status_code = 200 if is_alive else 503
        return send_json(details, status_code)
    except Exception as e:
        logger.error(f"Liveness check error: {e}")
        return send_json({"status": "error", "error": str(e)}, 500)


@health_bp.route("/api/health/detailed")
def handle_detailed_health():
    """Comprehensive health status for monitoring dashboards."""
    try:
        checker = _get_health_checker()
        details = checker.get_detailed_status()

        is_healthy = details.get("overall_status") == "healthy"
        status_code = 200 if is_healthy else 503

        response = current_app.response_class(
            response=json.dumps(details, indent=2),
            status=status_code,
            mimetype="application/json",
        )
        return response
    except Exception as e:
        logger.error(f"Detailed health check error: {e}")
        return send_json({"status": "error", "error": str(e)}, 500)


@health_bp.route("/metrics")
def handle_prometheus_metrics():
    """Prometheus metrics endpoint."""
    try:
        checker = _get_health_checker()
        _, details = checker.check_readiness()

        from pbx.utils.production_health import format_health_check_response

        is_healthy = details.get("status") == "ready"

        status_code, metrics_text = format_health_check_response(
            is_healthy, details, format_type="prometheus"
        )

        response = current_app.response_class(
            response=metrics_text,
            status=status_code,
            mimetype="text/plain; version=0.0.4",
        )
        return response
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        response = current_app.response_class(
            response=f"# ERROR: {str(e)}\n",
            status=500,
            mimetype="text/plain",
        )
        return response


@health_bp.route("/api/status")
def handle_status():
    """Get PBX status."""
    pbx_core = get_pbx_core()
    if pbx_core:
        status = pbx_core.get_status()
        return send_json(status)
    else:
        return send_json({"error": "PBX not initialized"}, 500)
