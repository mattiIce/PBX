"""Paging System Blueprint routes.

Handles paging zone management, DAC device configuration,
and active page session queries.
"""

from typing import Any

from flask import Blueprint, Response

from pbx.api.utils import (
    get_pbx_core,
    get_request_body,
    require_auth,
    send_json,
)
from pbx.utils.logger import get_logger

logger = get_logger()

paging_bp = Blueprint("paging", __name__, url_prefix="/api/paging")


def _get_paging_system() -> Any:
    """Get paging system instance or None if not available."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "paging_system"):
        return None

    if not pbx_core.paging_system or not pbx_core.paging_system.enabled:
        return None

    return pbx_core.paging_system


@paging_bp.route("/zones", methods=["GET"])
@require_auth
def handle_get_paging_zones() -> Response:
    """Get all paging zones."""
    paging_system = _get_paging_system()
    if not paging_system:
        return send_json({"zones": []})

    try:
        zones = paging_system.get_zones()
        return send_json(zones)
    except Exception as e:
        logger.error(f"Error getting paging zones: {e}")
        # Return empty zones instead of error to prevent UI errors
        return send_json({"zones": []})


@paging_bp.route("/devices", methods=["GET"])
@require_auth
def handle_get_paging_devices() -> Response:
    """Get all paging DAC devices."""
    paging_system = _get_paging_system()
    if not paging_system:
        return send_json({"devices": []})

    try:
        devices = paging_system.get_dac_devices()
        return send_json(devices)
    except Exception as e:
        logger.error(f"Error getting paging devices: {e}")
        # Return empty devices instead of error to prevent UI errors
        return send_json({"devices": []})


@paging_bp.route("/active", methods=["GET"])
@require_auth
def handle_get_active_pages() -> Response:
    """Get all active paging sessions."""
    paging_system = _get_paging_system()
    if not paging_system:
        return send_json({"active_pages": []})

    try:
        active_pages = paging_system.get_active_pages()
        return send_json(active_pages)
    except Exception as e:
        logger.error(f"Error getting active pages: {e}")
        # Return empty active pages instead of error to prevent UI errors
        return send_json({"active_pages": []})


@paging_bp.route("/zones", methods=["POST"])
@require_auth
def handle_add_paging_zone() -> Response:
    """Add a paging zone."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "paging_system"):
        return send_json({"error": "Paging system not enabled"}, 500)

    if not pbx_core.paging_system or not pbx_core.paging_system.enabled:
        return send_json({"error": "Paging system not enabled"}, 500)

    try:
        data = get_request_body()
        extension = data.get("extension")
        name = data.get("name")

        if not extension or not name:
            return send_json({"error": "Extension and name are required"}, 400)

        success = pbx_core.paging_system.add_zone(
            extension=extension,
            name=name,
            description=data.get("description"),
            dac_device=data.get("dac_device"),
        )

        if success:
            return send_json({"success": True, "message": f"Paging zone added: {extension}"})
        return send_json({"error": "Failed to add paging zone"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@paging_bp.route("/devices", methods=["POST"])
@require_auth
def handle_configure_paging_device() -> Response:
    """Configure a paging DAC device."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "paging_system"):
        return send_json({"error": "Paging system not enabled"}, 500)

    if not pbx_core.paging_system or not pbx_core.paging_system.enabled:
        return send_json({"error": "Paging system not enabled"}, 500)

    try:
        data = get_request_body()
        device_id = data.get("device_id")
        device_type = data.get("device_type")

        if not device_id or not device_type:
            return send_json({"error": "device_id and device_type are required"}, 400)

        success = pbx_core.paging_system.configure_dac_device(
            device_id=device_id,
            device_type=device_type,
            sip_uri=data.get("sip_uri"),
            ip_address=data.get("ip_address"),
            port=data.get("port", 5060),
        )

        if success:
            return send_json({"success": True, "message": f"DAC device configured: {device_id}"})
        return send_json({"error": "Failed to configure DAC device"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@paging_bp.route("/zones/<extension>", methods=["DELETE"])
@require_auth
def handle_delete_paging_zone(extension: str) -> Response:
    """Delete a paging zone."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "paging_system"):
        return send_json({"error": "Paging system not enabled"}, 500)

    if not pbx_core.paging_system or not pbx_core.paging_system.enabled:
        return send_json({"error": "Paging system not enabled"}, 500)

    try:
        success = pbx_core.paging_system.remove_zone(extension)

        if success:
            return send_json({"success": True, "message": f"Paging zone deleted: {extension}"})
        return send_json({"error": "Failed to delete paging zone"}, 500)
    except Exception as e:
        return send_json({"error": str(e)}, 500)
