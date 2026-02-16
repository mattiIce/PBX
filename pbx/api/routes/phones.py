"""Phones Blueprint routes.

Handles phone lookup by MAC/IP address and phone reboot operations.
"""

import re

from flask import Blueprint, Response

from pbx.api.utils import (
    get_pbx_core,
    require_admin,
    require_auth,
    send_json,
)
from pbx.features.phone_provisioning import normalize_mac_address
from pbx.utils.logger import get_logger

logger = get_logger()

phones_bp = Blueprint("phones", __name__)


@phones_bp.route("/api/phone-lookup/<identifier>", methods=["GET"])
@require_auth
def handle_phone_lookup(identifier: str) -> Response:
    """Unified phone lookup by MAC or IP address."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500)

    result = {
        "identifier": identifier,
        "type": None,
        "registered_phone": None,
        "provisioned_device": None,
        "correlation": None,
    }

    # Normalize the identifier to detect if it's a MAC or IP
    # Check if it looks like a MAC address using regex
    # Matches formats: XX:XX:XX:XX:XX:XX, XX-XX-XX-XX-XX-XX, XXXXXXXXXXXX
    mac_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$")
    is_mac = bool(mac_pattern.match(identifier))

    # Check if it looks like an IP address using regex
    # Matches valid IPv4 addresses
    ip_pattern = re.compile(
        r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    is_ip = bool(ip_pattern.match(identifier))

    # Try MAC address lookup
    if is_mac:
        result["type"] = "mac"
        normalized_mac = normalize_mac_address(identifier)

        # Check provisioning system
        if hasattr(pbx_core, "phone_provisioning"):
            device = pbx_core.phone_provisioning.get_device(identifier)
            if device:
                result["provisioned_device"] = device.to_dict()

        # Check registered phones
        if hasattr(pbx_core, "registered_phones_db") and pbx_core.registered_phones_db:
            try:
                phone = pbx_core.registered_phones_db.get_by_mac(normalized_mac)
                if phone:
                    result["registered_phone"] = phone
            except (KeyError, TypeError, ValueError) as e:
                logger.error(f"Error looking up MAC in registered_phones: {e}")

    # Try IP address lookup
    elif is_ip:
        result["type"] = "ip"

        # Check registered phones first
        if hasattr(pbx_core, "registered_phones_db") and pbx_core.registered_phones_db:
            try:
                phone = pbx_core.registered_phones_db.get_by_ip(identifier)
                if phone:
                    result["registered_phone"] = phone

                    # Now try to find MAC from provisioning using the extension
                    extension = phone.get("extension_number")
                    if extension and hasattr(pbx_core, "phone_provisioning"):
                        device = None
                        # Search through provisioned devices for this extension
                        for dev in pbx_core.phone_provisioning.get_all_devices():
                            if dev.extension_number == extension:
                                device = dev
                                break
                        if device:
                            result["provisioned_device"] = device.to_dict()
            except (KeyError, TypeError, ValueError) as e:
                logger.error(f"Error looking up IP in registered_phones: {e}")
    else:
        result["type"] = "unknown"
        return send_json(
            {"error": f"Could not determine if {identifier} is a MAC address or IP address"},
            400,
        )

    # Add correlation summary
    if result["registered_phone"] and result["provisioned_device"]:
        result["correlation"] = {
            "matched": True,
            "extension": result["registered_phone"].get("extension_number"),
            "mac_address": result["provisioned_device"].get("mac_address"),
            "ip_address": result["registered_phone"].get("ip_address"),
            "vendor": result["provisioned_device"].get("vendor"),
            "model": result["provisioned_device"].get("model"),
        }
    elif result["registered_phone"]:
        result["correlation"] = {
            "matched": False,
            "message": "Phone is registered but not provisioned in the system",
            "extension": result["registered_phone"].get("extension_number"),
            "ip_address": result["registered_phone"].get("ip_address"),
        }
    elif result["provisioned_device"]:
        result["correlation"] = {
            "matched": False,
            "message": "Device is provisioned but not currently registered",
            "extension": result["provisioned_device"].get("extension_number"),
            "mac_address": result["provisioned_device"].get("mac_address"),
        }
    else:
        result["correlation"] = {
            "matched": False,
            "message": "No information found for this identifier",
        }

    return send_json(result)


@phones_bp.route("/api/phones/reboot", methods=["POST"])
@require_admin
def handle_reboot_phones() -> Response:
    """Reboot all registered phones."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    try:
        # Send SIP NOTIFY to all registered phones
        results = pbx_core.phone_provisioning.reboot_all_phones(pbx_core.sip_server)

        return send_json(
            {
                "success": True,
                "message": f"Rebooted {results['success_count']} phones",
                "rebooted": results["rebooted"],
                "failed": results["failed"],
                "success_count": results["success_count"],
                "failed_count": results["failed_count"],
            }
        )
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@phones_bp.route("/api/phones/<extension>/reboot", methods=["POST"])
@require_admin
def handle_reboot_phone(extension: str) -> Response:
    """Reboot a specific phone."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    try:
        # Send SIP NOTIFY to reboot the phone
        success = pbx_core.phone_provisioning.reboot_phone(extension, pbx_core.sip_server)

        if success:
            return send_json(
                {"success": True, "message": f"Reboot signal sent to extension {extension}"}
            )
        return send_json(
            {
                "error": f"Failed to send reboot signal to extension {extension}. Extension may not be registered."
            },
            400,
        )
    except Exception as e:
        return send_json({"error": str(e)}, 500)
