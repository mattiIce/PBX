"""Emergency Notification Blueprint routes.

Handles emergency contact management, notification triggering,
notification history, and testing of the emergency notification system.
"""

from typing import Any

from flask import Blueprint, Response, request

from pbx.api.utils import (
    get_pbx_core,
    get_request_body,
    require_admin,
    require_auth,
    send_json,
)
from pbx.utils.logger import get_logger

logger = get_logger()

emergency_bp = Blueprint("emergency", __name__, url_prefix="/api/emergency")


def _get_emergency_system() -> tuple[Any, Response | None]:
    """Get emergency notification system instance or return error response."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "emergency_notification"):
        return None, send_json({"error": "Emergency notification system not initialized"}, 500)

    return pbx_core.emergency_notification, None


@emergency_bp.route("/contacts", methods=["GET"])
@require_auth
def handle_get_emergency_contacts() -> Response:
    """Get emergency contacts."""
    emergency_system, error = _get_emergency_system()
    if error:
        return error

    try:
        # Parse query parameters
        priority_param = request.args.get("priority")
        priority_filter = int(priority_param) if priority_param else None

        contacts = emergency_system.get_emergency_contacts(priority_filter)

        return send_json({"contacts": contacts, "total": len(contacts)})

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error getting emergency contacts: {e}")
        return send_json({"error": f"Error getting emergency contacts: {e!s}"}, 500)


@emergency_bp.route("/history", methods=["GET"])
@require_auth
def handle_get_emergency_history() -> Response:
    """Get emergency notification history."""
    emergency_system, error = _get_emergency_system()
    if error:
        return error

    try:
        # Parse query parameters
        limit = int(request.args.get("limit", 50))

        history = emergency_system.get_notification_history(limit)

        return send_json({"history": history, "total": len(history)})

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error getting emergency history: {e}")
        return send_json({"error": f"Error getting emergency history: {e!s}"}, 500)


@emergency_bp.route("/test", methods=["GET"])
@require_auth
def handle_test_emergency_notification() -> Response:
    """Test emergency notification system."""
    emergency_system, error = _get_emergency_system()
    if error:
        return error

    try:
        result = emergency_system.test_emergency_notification()
        return send_json(result)

    except Exception as e:
        logger.error(f"Error testing emergency notification: {e}")
        return send_json({"error": f"Error testing emergency notification: {e!s}"}, 500)


@emergency_bp.route("/contacts", methods=["POST"])
@require_admin
def handle_add_emergency_contact() -> Response:
    """Add emergency contact. Requires admin privileges."""
    emergency_system, error = _get_emergency_system()
    if error:
        return error

    try:
        data = get_request_body()

        contact = emergency_system.add_emergency_contact(
            name=data.get("name"),
            extension=data.get("extension"),
            phone=data.get("phone"),
            email=data.get("email"),
            priority=data.get("priority", 1),
            notification_methods=data.get("notification_methods", ["call"]),
        )

        return send_json(
            {
                "success": True,
                "contact": contact.to_dict(),
                "message": "Emergency contact added successfully",
            }
        )

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error adding emergency contact: {e}")
        return send_json({"error": f"Error adding emergency contact: {e!s}"}, 500)


@emergency_bp.route("/trigger", methods=["POST"])
@require_admin
def handle_trigger_emergency_notification() -> Response:
    """Manually trigger emergency notification. Requires admin privileges."""
    emergency_system, error = _get_emergency_system()
    if error:
        return error

    try:
        data = get_request_body()

        success = emergency_system.trigger_emergency_notification(
            trigger_type=data.get("trigger_type", "manual"),
            details=data.get("details", {}),
        )

        return send_json({"success": success, "message": "Emergency notification triggered"})

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error triggering emergency notification: {e}")
        return send_json({"error": f"Error triggering emergency notification: {e!s}"}, 500)


@emergency_bp.route("/contacts/<contact_id>", methods=["DELETE"])
@require_admin
def handle_delete_emergency_contact(contact_id: str) -> Response:
    """Delete emergency contact. Requires admin privileges."""
    emergency_system, error = _get_emergency_system()
    if error:
        return error

    try:
        success = emergency_system.remove_emergency_contact(contact_id)

        if success:
            return send_json({"success": True, "message": "Emergency contact removed successfully"})
        return send_json({"error": "Contact not found"}, 404)

    except Exception as e:
        logger.error(f"Error deleting emergency contact: {e}")
        return send_json({"error": f"Error deleting emergency contact: {e!s}"}, 500)
