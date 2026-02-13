"""Quality of Service (QoS) monitoring Blueprint routes."""

import json

from flask import Blueprint, Response, jsonify, request, current_app

from pbx.api.utils import (
    get_pbx_core,
    send_json,
    verify_authentication,
    require_auth,
    require_admin,
    get_request_body,
    DateTimeEncoder,
)
from pbx.utils.logger import get_logger

logger = get_logger()

qos_bp = Blueprint("qos", __name__)


@qos_bp.route("/api/qos/metrics", methods=["GET"])
@require_auth
def handle_get_qos_metrics():
    """Get QoS metrics for all active calls."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "qos_monitor"):
        return send_json({"error": "QoS monitoring not enabled"}, 500), 500

    try:
        metrics = pbx_core.qos_monitor.get_all_active_metrics()
        return send_json({"active_calls": len(metrics), "metrics": metrics}), 200
    except Exception as e:
        logger.error(f"Error getting QoS metrics: {e}")
        return send_json({"error": f"Error getting QoS metrics: {str(e)}"}, 500), 500


@qos_bp.route("/api/qos/alerts", methods=["GET"])
@require_auth
def handle_get_qos_alerts():
    """Get QoS quality alerts."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "qos_monitor"):
        return send_json({"error": "QoS monitoring not enabled"}, 500), 500

    try:
        # Validate limit parameter
        limit = int(request.args.get("limit", 50))
        if limit < 1:
            return send_json({"error": "limit must be at least 1"}, 400), 400
        if limit > 1000:
            return send_json({"error": "limit cannot exceed 1000"}, 400), 400

        alerts = pbx_core.qos_monitor.get_alerts(limit)
        return send_json({"count": len(alerts), "alerts": alerts}), 200
    except ValueError as e:
        logger.error(f"Invalid parameter for QoS alerts: {e}")
        return send_json({"error": "Invalid limit parameter, must be an integer"}, 400), 400
    except Exception as e:
        logger.error(f"Error getting QoS alerts: {e}")
        return send_json({"error": f"Error getting QoS alerts: {str(e)}"}, 500), 500


@qos_bp.route("/api/qos/history", methods=["GET"])
@require_auth
def handle_get_qos_history():
    """Get historical QoS metrics."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "qos_monitor"):
        return send_json({"error": "QoS monitoring not enabled"}, 500), 500

    try:
        # Validate limit parameter
        limit = int(request.args.get("limit", 100))
        if limit < 1:
            return send_json({"error": "limit must be at least 1"}, 400), 400
        if limit > 10000:
            return send_json({"error": "limit cannot exceed 10000"}, 400), 400

        # Validate min_mos parameter
        min_mos = request.args.get("min_mos", None)
        if min_mos:
            min_mos = float(min_mos)
            if min_mos < 1.0 or min_mos > 5.0:
                return send_json({"error": "min_mos must be between 1.0 and 5.0"}, 400), 400

        history = pbx_core.qos_monitor.get_historical_metrics(limit, min_mos)
        return send_json({"count": len(history), "metrics": history}), 200
    except ValueError as e:
        logger.error(f"Invalid parameter for QoS history: {e}")
        return send_json(
            {"error": "Invalid parameters, check limit (integer) and min_mos (float)"}, 400
        ), 400
    except Exception as e:
        logger.error(f"Error getting QoS history: {e}")
        return send_json({"error": f"Error getting QoS history: {str(e)}"}, 500), 500


@qos_bp.route("/api/qos/statistics", methods=["GET"])
@require_auth
def handle_get_qos_statistics():
    """Get overall QoS statistics."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "qos_monitor"):
        return send_json({"error": "QoS monitoring not enabled"}, 500), 500

    try:
        stats = pbx_core.qos_monitor.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting QoS statistics: {e}")
        return send_json({"error": f"Error getting QoS statistics: {str(e)}"}, 500), 500


@qos_bp.route("/api/qos/call/<call_id>", methods=["GET"])
@require_auth
def handle_get_qos_call_metrics(call_id):
    """Get QoS metrics for a specific call."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "qos_monitor"):
        return send_json({"error": "QoS monitoring not enabled"}, 500), 500

    try:
        metrics = pbx_core.qos_monitor.get_metrics(call_id)
        if metrics:
            return send_json(metrics), 200
        else:
            return send_json({"error": f"No QoS metrics found for call {call_id}"}, 404), 404
    except Exception as e:
        logger.error(f"Error getting call QoS metrics: {e}")
        return send_json({"error": f"Error getting call QoS metrics: {str(e)}"}, 500), 500


@qos_bp.route("/api/qos/clear-alerts", methods=["POST"])
@require_admin
def handle_clear_qos_alerts():
    """Handle clearing QoS alerts."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "qos_monitor"):
        return send_json({"error": "QoS monitoring not available"}, 500), 500

    try:
        count = pbx_core.qos_monitor.clear_alerts()
        return send_json({"success": True, "message": f"Cleared {count} alerts"}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@qos_bp.route("/api/qos/thresholds", methods=["POST"])
@require_admin
def handle_update_qos_thresholds():
    """Handle updating QoS alert thresholds."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "qos_monitor"):
        return send_json({"error": "QoS monitoring not available"}, 500), 500

    try:
        data = get_request_body()
        thresholds = {}

        # Validate and convert threshold values with range checking
        if "mos_min" in data:
            mos_min = float(data["mos_min"])
            if mos_min < 1.0 or mos_min > 5.0:
                return send_json({"error": "mos_min must be between 1.0 and 5.0"}, 400), 400
            thresholds["mos_min"] = mos_min

        if "packet_loss_max" in data:
            packet_loss_max = float(data["packet_loss_max"])
            if packet_loss_max < 0.0 or packet_loss_max > 100.0:
                return send_json(
                    {"error": "packet_loss_max must be between 0.0 and 100.0"}, 400
                ), 400
            thresholds["packet_loss_max"] = packet_loss_max

        if "jitter_max" in data:
            jitter_max = float(data["jitter_max"])
            if jitter_max < 0.0 or jitter_max > 1000.0:
                return send_json(
                    {"error": "jitter_max must be between 0.0 and 1000.0 ms"}, 400
                ), 400
            thresholds["jitter_max"] = jitter_max

        if "latency_max" in data:
            latency_max = float(data["latency_max"])
            if latency_max < 0.0 or latency_max > 5000.0:
                return send_json(
                    {"error": "latency_max must be between 0.0 and 5000.0 ms"}, 400
                ), 400
            thresholds["latency_max"] = latency_max

        if not thresholds:
            return send_json({"error": "No valid threshold parameters provided"}, 400), 400

        pbx_core.qos_monitor.update_alert_thresholds(thresholds)

        return send_json(
            {
                "success": True,
                "message": "QoS thresholds updated",
                "thresholds": pbx_core.qos_monitor.alert_thresholds,
            }
        ), 200
    except ValueError as e:
        logger.error(f"Invalid threshold value: {e}")
        return send_json(
            {"error": "Invalid threshold values, must be valid numbers"}, 400
        ), 400
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500
