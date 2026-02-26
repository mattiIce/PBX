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


@calls_bp.route("/api/calls/<call_id>/transfer", methods=["POST"])
@require_auth
def transfer_call(call_id: str) -> tuple[Response, int]:
    """Transfer a call to a new destination.

    Supports three transfer types:
    - blind: Immediate transfer without consultation
    - attended: Complete an attended transfer using a consultation call
    - consultative: Start a consultation call before completing transfer

    Request body:
        destination: Extension number to transfer to
        type: Transfer type (blind, attended, consultative). Default: blind
        consultation_call_id: Required for attended transfer type
    """
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    data = request.get_json()
    if not data:
        return send_json({"error": "Request body required"}, 400), 400

    transfer_type = data.get("type", "blind")
    destination = data.get("destination")
    consultation_call_id = data.get("consultation_call_id")

    if transfer_type == "attended":
        if not consultation_call_id:
            return send_json(
                {"error": "consultation_call_id required for attended transfer"}, 400
            ), 400
        success = pbx_core.attended_transfer(call_id, consultation_call_id)
    elif transfer_type == "consultative":
        if not destination:
            return send_json({"error": "destination required for consultative transfer"}, 400), 400
        new_call_id = pbx_core.consultation_transfer_start(call_id, destination)
        if new_call_id:
            return send_json(
                {
                    "success": True,
                    "consultation_call_id": new_call_id,
                    "message": f"Consultation call started to {destination}",
                }
            ), 200
        return send_json({"error": "Failed to start consultation transfer"}, 500), 500
    else:
        # Default: blind transfer
        if not destination:
            return send_json({"error": "destination required"}, 400), 400
        success = pbx_core.blind_transfer(call_id, destination)

    if success:
        return send_json(
            {
                "success": True,
                "message": f"Call {call_id} transferred to {destination or 'consultation target'}",
                "transfer_type": transfer_type,
            }
        ), 200
    return send_json({"error": f"Transfer failed for call {call_id}"}, 500), 500


@calls_bp.route("/api/calls/<call_id>/hold", methods=["POST"])
@require_auth
def hold_call(call_id: str) -> tuple[Response, int]:
    """Place a call on hold."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    if pbx_core.hold_call(call_id):
        return send_json({"success": True, "message": f"Call {call_id} placed on hold"}), 200
    return send_json({"error": f"Failed to hold call {call_id}"}, 404), 404


@calls_bp.route("/api/calls/<call_id>/resume", methods=["POST"])
@require_auth
def resume_call(call_id: str) -> tuple[Response, int]:
    """Resume a call from hold."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    if pbx_core.resume_call(call_id):
        return send_json({"success": True, "message": f"Call {call_id} resumed"}), 200
    return send_json({"error": f"Failed to resume call {call_id}"}, 404), 404


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

            # Export to CSV - create temp file and write data
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_file:
                csv_path = temp_file.name

            try:
                if pbx_core.statistics_engine.export_to_csv(analytics["records"], csv_path):
                    # Read the file and send as response
                    with Path(csv_path).open("rb") as f:
                        csv_data = f.read()

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
            finally:
                Path(csv_path).unlink(missing_ok=True)

        except (KeyError, OSError, TypeError, ValueError) as e:
            logger.error(f"Error exporting analytics: {e}")
            return send_json({"error": f"Error exporting analytics: {e!s}"}, 500), 500
    else:
        return send_json({"error": "Statistics engine not initialized"}, 500), 500
