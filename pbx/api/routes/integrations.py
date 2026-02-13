"""Integrations Blueprint routes for PBX API.

Handles Active Directory, CRM, Jitsi, EspoCRM, and Matrix integration
endpoints.
"""

from typing import Any

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

integrations_bp = Blueprint("integrations", __name__)

# Module-level cache for integration endpoints
_integration_endpoints = None


def _get_integration_endpoints() -> Any:
    """Get integration endpoints (cached)."""
    global _integration_endpoints
    if _integration_endpoints is None:
        from pbx.api.opensource_integration_api import add_opensource_integration_endpoints

        _integration_endpoints = add_opensource_integration_endpoints(None)
    return _integration_endpoints


def _check_integration_available(integration_name: str) -> tuple[bool, str | None]:
    """Check if integration is available and enabled."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return False, "PBX core not available"

    attr_name = f"{integration_name}_integration"
    if not hasattr(pbx_core, attr_name):
        return False, f"{integration_name.capitalize()} integration not available"

    integration = getattr(pbx_core, attr_name)
    if not integration or not integration.enabled:
        return False, f"{integration_name.capitalize()} integration not enabled"

    return True, None


# ========== Active Directory Integration ==========


@integrations_bp.route("/api/integrations/ad/status", methods=["GET"])
@require_auth
def handle_ad_status() -> Response:
    """Get Active Directory integration status."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500)

    try:
        status = pbx_core.get_ad_integration_status()
        return send_json(status)
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@integrations_bp.route("/api/integrations/ad/search", methods=["GET"])
@require_auth
def handle_ad_search() -> Response:
    """Search for users in Active Directory."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500)

    if not hasattr(pbx_core, "ad_integration") or not pbx_core.ad_integration:
        return send_json({"error": "Active Directory integration not enabled"}, 500)

    try:
        query = request.args.get("q", "")

        if not query:
            return send_json({"error": 'Query parameter "q" is required'}, 400)

        # Get max_results parameter (optional) with validation
        try:
            max_results = int(request.args.get("max_results", "50"))
            if max_results < 1 or max_results > 100:
                return send_json({"error": "max_results must be between 1 and 100"}, 400)
        except ValueError:
            return send_json({"error": "max_results must be a valid integer"}, 400)

        # Search AD users using the telephoneNumber attribute (and other
        # attributes)
        results = pbx_core.ad_integration.search_users(query, max_results)

        return send_json({"success": True, "count": len(results), "results": results})
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@integrations_bp.route("/api/integrations/ad/sync", methods=["POST"])
@require_admin
def handle_ad_sync() -> Response:
    """Manually trigger Active Directory user synchronization."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500)

    try:
        result = pbx_core.sync_ad_users()
        if result["success"]:
            return send_json(
                {
                    "success": True,
                    "message": f'Successfully synchronized {result["synced_count"]} users from Active Directory',
                    "synced_count": result["synced_count"],
                }
            )
        else:
            return send_json({"success": False, "error": result["error"]}, 400)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


# ========== CRM Integration ==========


@integrations_bp.route("/api/crm/lookup", methods=["GET"])
@require_auth
def handle_crm_lookup() -> Response:
    """Look up caller information."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "crm_integration"):
        return send_json({"error": "CRM integration not available"}, 500)

    try:
        # Get phone number from query string
        phone_number = request.args.get("phone")

        if not phone_number:
            return send_json({"error": "phone parameter is required"}, 400)

        # Look up caller info
        caller_info = pbx_core.crm_integration.lookup_caller(phone_number)

        if caller_info:
            return send_json({"found": True, "caller_info": caller_info.to_dict()})
        else:
            return send_json({"found": False, "message": "Caller not found"})
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@integrations_bp.route("/api/crm/providers", methods=["GET"])
@require_auth
def handle_get_crm_providers() -> Response:
    """Get CRM provider status."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "crm_integration"):
        return send_json({"error": "CRM integration not available"}, 500)

    try:
        providers = pbx_core.crm_integration.get_provider_status()
        return send_json(
            {"enabled": pbx_core.crm_integration.enabled, "providers": providers}
        )
    except Exception as e:
        return send_json({"error": str(e)}, 500)


# ========== Jitsi Integration ==========


@integrations_bp.route("/api/integrations/jitsi/meetings", methods=["POST"])
@require_auth
def handle_jitsi_create_meeting() -> Response:
    """Create Jitsi meeting."""
    available, error = _check_integration_available("jitsi")
    if not available:
        return send_json({"error": error}, 400)

    try:
        endpoints = _get_integration_endpoints()
        handler = endpoints.get("POST /api/integrations/jitsi/meetings")
        if handler:
            return handler(request)
        else:
            return send_json({"error": "Handler not found"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error in Jitsi create meeting: {e}")
        return send_json({"error": str(e)}, 500)


@integrations_bp.route("/api/integrations/jitsi/instant", methods=["POST"])
@require_auth
def handle_jitsi_instant_meeting() -> Response:
    """Create instant Jitsi meeting."""
    available, error = _check_integration_available("jitsi")
    if not available:
        return send_json({"error": error}, 400)

    try:
        endpoints = _get_integration_endpoints()
        handler = endpoints.get("POST /api/integrations/jitsi/instant")
        if handler:
            return handler(request)
        else:
            return send_json({"error": "Handler not found"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error in Jitsi instant meeting: {e}")
        return send_json({"error": str(e)}, 500)


# ========== EspoCRM Integration ==========


@integrations_bp.route("/api/integrations/espocrm/contacts", methods=["POST"])
@require_auth
def handle_espocrm_create_contact() -> Response:
    """Create EspoCRM contact."""
    available, error = _check_integration_available("espocrm")
    if not available:
        return send_json({"error": error}, 400)

    try:
        endpoints = _get_integration_endpoints()
        handler = endpoints.get("POST /api/integrations/espocrm/contacts")
        if handler:
            return handler(request)
        else:
            return send_json({"error": "Handler not found"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error in EspoCRM create contact: {e}")
        return send_json({"error": str(e)}, 500)


@integrations_bp.route("/api/integrations/espocrm/calls", methods=["POST"])
@require_auth
def handle_espocrm_log_call() -> Response:
    """Log call in EspoCRM."""
    available, error = _check_integration_available("espocrm")
    if not available:
        return send_json({"error": error}, 400)

    try:
        endpoints = _get_integration_endpoints()
        handler = endpoints.get("POST /api/integrations/espocrm/calls")
        if handler:
            return handler(request)
        else:
            return send_json({"error": "Handler not found"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error in EspoCRM log call: {e}")
        return send_json({"error": str(e)}, 500)


@integrations_bp.route("/api/integrations/espocrm/contacts/search", methods=["GET"])
@require_auth
def handle_espocrm_search_contact() -> Response:
    """Search EspoCRM contact by phone."""
    available, error = _check_integration_available("espocrm")
    if not available:
        return send_json({"error": error}, 400)

    try:
        endpoints = _get_integration_endpoints()
        handler = endpoints.get("GET /api/integrations/espocrm/contacts/search")
        if handler:
            return handler(request)
        else:
            return send_json({"error": "Handler not found"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error in EspoCRM search contact: {e}")
        return send_json({"error": str(e)}, 500)


# ========== Matrix Integration ==========


@integrations_bp.route("/api/integrations/matrix/messages", methods=["POST"])
@require_auth
def handle_matrix_send_message() -> Response:
    """Send message to Matrix room."""
    available, error = _check_integration_available("matrix")
    if not available:
        return send_json({"error": error}, 400)

    try:
        endpoints = _get_integration_endpoints()
        handler = endpoints.get("POST /api/integrations/matrix/messages")
        if handler:
            return handler(request)
        else:
            return send_json({"error": "Handler not found"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error in Matrix send message: {e}")
        return send_json({"error": str(e)}, 500)


@integrations_bp.route("/api/integrations/matrix/notifications", methods=["POST"])
@require_auth
def handle_matrix_send_notification() -> Response:
    """Send Matrix notification."""
    available, error = _check_integration_available("matrix")
    if not available:
        return send_json({"error": error}, 400)

    try:
        endpoints = _get_integration_endpoints()
        handler = endpoints.get("POST /api/integrations/matrix/notifications")
        if handler:
            return handler(request)
        else:
            return send_json({"error": "Handler not found"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error in Matrix send notification: {e}")
        return send_json({"error": str(e)}, 500)


@integrations_bp.route("/api/integrations/matrix/rooms", methods=["POST"])
@require_auth
def handle_matrix_create_room() -> Response:
    """Create Matrix room."""
    available, error = _check_integration_available("matrix")
    if not available:
        return send_json({"error": error}, 400)

    try:
        endpoints = _get_integration_endpoints()
        handler = endpoints.get("POST /api/integrations/matrix/rooms")
        if handler:
            return handler(request)
        else:
            return send_json({"error": "Handler not found"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error in Matrix create room: {e}")
        return send_json({"error": str(e)}, 500)
