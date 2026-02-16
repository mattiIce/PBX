"""Flask Blueprint for call management and analytics routes."""

import tempfile
from pathlib import Path

from flask import Blueprint, Response, current_app, request

from pbx.api.utils import (
    get_pbx_core,
    require_auth,
    send_json,
)
from pbx.utils.logger import get_logger

logger = get_logger()

calls_bp = Blueprint("calls", __name__)


@calls_bp.route("/api/calls", methods=["GET"])
@require_auth
def get_calls() -> tuple[Response, int]:
    """Get active calls."""
    pbx_core = get_pbx_core()
    if pbx_core:
        calls = pbx_core.call_manager.get_active_calls()
        data = [str(call) for call in calls]
        return send_json(data), 200
    return send_json({"error": "PBX not initialized"}, 500), 500


@calls_bp.route("/api/statistics", methods=["GET"])
@require_auth
def get_statistics() -> tuple[Response, int]:
    """Get comprehensive statistics for dashboard."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "statistics_engine"):
        try:
            days = request.args.get("days", 7, type=int)

            # Get dashboard statistics
            stats = pbx_core.statistics_engine.get_dashboard_statistics(days)

            # Add call quality metrics (with QoS integration)
            stats["call_quality"] = pbx_core.statistics_engine.get_call_quality_metrics(pbx_core)

            # Add real-time metrics
            stats["real_time"] = pbx_core.statistics_engine.get_real_time_metrics(pbx_core)

            return send_json(stats), 200
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error getting statistics: {e}")
            return send_json({"error": f"Error getting statistics: {e!s}"}, 500), 500
    else:
        return send_json({"error": "Statistics engine not initialized"}, 500), 500


@calls_bp.route("/api/analytics/advanced", methods=["GET"])
@require_auth
def get_advanced_analytics() -> tuple[Response, int]:
    """Get advanced analytics with date range and filters."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "statistics_engine"):
        try:
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")

            if not start_date or not end_date:
                return send_json({"error": "start_date and end_date parameters required"}, 400), 400

            # Parse filters
            filters = {}
            if request.args.get("extension"):
                filters["extension"] = request.args.get("extension")
            if request.args.get("disposition"):
                filters["disposition"] = request.args.get("disposition")
            if request.args.get("min_duration"):
                filters["min_duration"] = int(request.args.get("min_duration"))

            analytics = pbx_core.statistics_engine.get_advanced_analytics(
                start_date, end_date, filters or None
            )

            return send_json(analytics), 200

        except ValueError as e:
            return send_json({"error": f"Invalid date format: {e!s}"}, 400), 400
        except (KeyError, TypeError) as e:
            logger.error(f"Error getting advanced analytics: {e}")
            return send_json({"error": f"Error getting advanced analytics: {e!s}"}, 500), 500
    else:
        return send_json({"error": "Statistics engine not initialized"}, 500), 500


@calls_bp.route("/api/analytics/call-center", methods=["GET"])
@require_auth
def get_call_center_metrics() -> tuple[Response, int]:
    """Get call center performance metrics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "statistics_engine"):
        try:
            days = request.args.get("days", 7, type=int)
            queue_name = request.args.get("queue")

            metrics = pbx_core.statistics_engine.get_call_center_metrics(days, queue_name)

            return send_json(metrics), 200

        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error getting call center metrics: {e}")
            return send_json({"error": f"Error getting call center metrics: {e!s}"}, 500), 500
    else:
        return send_json({"error": "Statistics engine not initialized"}, 500), 500


@calls_bp.route("/api/analytics/export", methods=["GET"])
@require_auth
def export_analytics() -> Response | tuple[Response, int]:
    """Export analytics data to CSV."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "statistics_engine"):
        try:
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")

            if not start_date or not end_date:
                return send_json({"error": "start_date and end_date parameters required"}, 400), 400

            # Get analytics data
            analytics = pbx_core.statistics_engine.get_advanced_analytics(
                start_date, end_date, None
            )

            # Export to CSV
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_file:
                pass

            if pbx_core.statistics_engine.export_to_csv(analytics["records"], temp_file.name):
                # Read the file and send as response
                with Path(temp_file.name).open("rb") as f:
                    csv_data = f.read()

                # Clean up temp file
                Path(temp_file.name).unlink()

                response = current_app.response_class(
                    response=csv_data,
                    status=200,
                    mimetype="text/csv",
                )
                response.headers["Content-Disposition"] = (
                    f'attachment; filename="cdr_export_{start_date}_to_{end_date}.csv"'
                )
                return response
            return send_json({"error": "Failed to export data"}, 500), 500

        except (KeyError, OSError, TypeError, ValueError) as e:
            logger.error(f"Error exporting analytics: {e}")
            return send_json({"error": f"Error exporting analytics: {e!s}"}, 500), 500
    else:
        return send_json({"error": "Statistics engine not initialized"}, 500), 500
