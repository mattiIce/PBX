"""Provisioning Blueprint routes.

Handles phone provisioning, device registration, template management,
and serving provisioning configuration files to phones.
"""

import re
import traceback
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request

from pbx.api.utils import (
    DateTimeEncoder,
    get_pbx_core,
    get_request_body,
    require_admin,
    require_auth,
    send_json,
    verify_authentication,
)
from pbx.features.phone_provisioning import normalize_mac_address
from pbx.utils.logger import get_logger

logger = get_logger()

provisioning_bp = Blueprint("provisioning", __name__)

# MAC address placeholders that indicate misconfiguration
MAC_ADDRESS_PLACEHOLDERS = ["{mac}", "{MAC}", "{Ma}"]


def _get_provisioning_url_info() -> tuple[str, str, Any, str]:
    """Get provisioning URL information (protocol, server IP, port).

    Returns:
        tuple: (protocol, server_ip, port, base_url)
    """
    pbx_core = get_pbx_core()
    if not pbx_core:
        return "http", "192.168.1.14", 8080, "http://192.168.1.14:8080"

    ssl_enabled = pbx_core.config.get("api.ssl.enabled", False)
    protocol = "https" if ssl_enabled else "http"
    server_ip = pbx_core.config.get("server.external_ip", "192.168.1.14")
    port = pbx_core.config.get("api.port", 9000)
    base_url = f"{protocol}://{server_ip}:{port}"

    return protocol, server_ip, port, base_url


# ---------------------------------------------------------------------------
# GET routes
# ---------------------------------------------------------------------------


@provisioning_bp.route("/api/provisioning/devices", methods=["GET"])
@require_admin
def handle_get_provisioning_devices() -> Response:
    """Get all provisioned devices."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "phone_provisioning"):
        devices = pbx_core.phone_provisioning.get_all_devices()
        data = [d.to_dict() for d in devices]
        return send_json(data)
    else:
        return send_json({"error": "Phone provisioning not enabled"}, 500)


@provisioning_bp.route("/api/provisioning/atas", methods=["GET"])
@require_admin
def handle_get_provisioning_atas() -> Response:
    """Get all provisioned ATA devices."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "phone_provisioning"):
        atas = pbx_core.phone_provisioning.get_atas()
        data = [d.to_dict() for d in atas]
        return send_json(data)
    else:
        return send_json({"error": "Phone provisioning not enabled"}, 500)


@provisioning_bp.route("/api/provisioning/phones", methods=["GET"])
@require_admin
def handle_get_provisioning_phones() -> Response:
    """Get all provisioned phone devices (excluding ATAs)."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "phone_provisioning"):
        phones = pbx_core.phone_provisioning.get_phones()
        data = [d.to_dict() for d in phones]
        return send_json(data)
    else:
        return send_json({"error": "Phone provisioning not enabled"}, 500)


@provisioning_bp.route("/api/registered-atas", methods=["GET"])
@require_admin
def handle_get_registered_atas() -> Response:
    """Get all registered ATA devices from database."""
    pbx_core = get_pbx_core()
    if (
        pbx_core
        and hasattr(pbx_core, "registered_phones_db")
        and pbx_core.registered_phones_db
    ):
        try:
            # Get all registered phones
            all_phones = pbx_core.registered_phones_db.list_all()

            # Filter to only ATAs by checking provisioning data
            atas = []
            if hasattr(pbx_core, "phone_provisioning"):
                provisioned_atas = {
                    d.extension_number: d for d in pbx_core.phone_provisioning.get_atas()
                }

                for phone in all_phones:
                    ext = phone.get("extension_number")
                    if ext and ext in provisioned_atas:
                        # This phone is provisioned as an ATA
                        enhanced = dict(phone)
                        enhanced["device_type"] = "ata"
                        enhanced["vendor"] = provisioned_atas[ext].vendor
                        enhanced["model"] = provisioned_atas[ext].model
                        atas.append(enhanced)

            return send_json(atas)
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error loading registered ATAs from database: {e}")
            return send_json(
                {"error": str(e), "details": "Check server logs for full error details"}, 500
            )
    else:
        logger.warning("Database not available or not configured")
        return send_json([])


@provisioning_bp.route("/api/provisioning/vendors", methods=["GET"])
@require_auth
def handle_get_provisioning_vendors() -> Response:
    """Get supported vendors and models."""
    try:
        pbx_core = get_pbx_core()
        if pbx_core and hasattr(pbx_core, "phone_provisioning"):
            vendors = pbx_core.phone_provisioning.get_supported_vendors()
            models = pbx_core.phone_provisioning.get_supported_models()
            data = {"vendors": vendors, "models": models}
            return send_json(data)
        else:
            return send_json({"error": "Phone provisioning not enabled"}, 500)
    except Exception as e:
        logger.error(f"Error getting provisioning vendors: {e}")
        return send_json({"error": "Failed to retrieve provisioning vendors"}, 500)


@provisioning_bp.route("/api/provisioning/templates", methods=["GET"])
@require_auth
def handle_get_provisioning_templates() -> Response:
    """Get list of all provisioning templates."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    templates = pbx_core.phone_provisioning.list_all_templates()
    return send_json({"templates": templates, "total": len(templates)})


@provisioning_bp.route("/api/provisioning/templates/<vendor>/<model>", methods=["GET"])
@require_admin
def handle_get_template_content(vendor: str, model: str) -> Response:
    """Get content of a specific template."""
    # Validate vendor/model to prevent path traversal
    if not re.match(r"^[a-z0-9_-]+$", vendor) or not re.match(r"^[a-z0-9_-]+$", model):
        return send_json({"error": "Invalid vendor or model name"}, 400)

    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    content = pbx_core.phone_provisioning.get_template_content(vendor, model)
    if content:
        return send_json(
            {
                "vendor": vendor,
                "model": model,
                "content": content,
                "placeholders": [
                    "{{EXTENSION_NUMBER}}",
                    "{{EXTENSION_NAME}}",
                    "{{EXTENSION_PASSWORD}}",
                    "{{SIP_SERVER}}",
                    "{{SIP_PORT}}",
                    "{{SERVER_NAME}}",
                ],
            }
        )
    else:
        return send_json({"error": f"Template not found for {vendor} {model}"}, 404)


@provisioning_bp.route("/api/provisioning/diagnostics", methods=["GET"])
@require_admin
def handle_get_provisioning_diagnostics() -> Response:
    """Get provisioning system diagnostics."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    provisioning = pbx_core.phone_provisioning

    # Gather diagnostic information
    diagnostics = {
        "enabled": True,
        "configuration": {
            "url_format": pbx_core.config.get("provisioning.url_format", "Not configured"),
            "external_ip": pbx_core.config.get("server.external_ip", "Not configured"),
            "api_port": pbx_core.config.get("api.port", "Not configured"),
            "sip_host": pbx_core.config.get("server.sip_host", "Not configured"),
            "sip_port": pbx_core.config.get("server.sip_port", "Not configured"),
            "custom_templates_dir": pbx_core.config.get(
                "provisioning.custom_templates_dir", "Not configured"
            ),
        },
        "statistics": {
            "total_devices": len(provisioning.devices),
            "total_templates": len(provisioning.templates),
            "total_requests": len(provisioning.provision_requests),
            "successful_requests": sum(
                1 for r in provisioning.provision_requests if r.get("success")
            ),
            "failed_requests": sum(
                1 for r in provisioning.provision_requests if not r.get("success")
            ),
        },
        "devices": [d.to_dict() for d in provisioning.get_all_devices()],
        "vendors": provisioning.get_supported_vendors(),
        "models": provisioning.get_supported_models(),
        "recent_requests": provisioning.get_request_history(limit=20),
    }

    # Add warnings for common issues
    warnings = []
    if diagnostics["configuration"]["external_ip"] == "Not configured":
        warnings.append(
            "server.external_ip is not configured - phones may not be able to reach the PBX"
        )
    if diagnostics["statistics"]["total_devices"] == 0:
        warnings.append(
            "No devices registered - use POST /api/provisioning/devices to register devices"
        )
    if diagnostics["statistics"]["failed_requests"] > 0:
        warnings.append(
            f"{diagnostics['statistics']['failed_requests']} provisioning requests failed - check recent_requests for details"
        )

    diagnostics["warnings"] = warnings

    return send_json(diagnostics)


@provisioning_bp.route("/api/provisioning/requests", methods=["GET"])
@require_admin
def handle_get_provisioning_requests() -> Response:
    """Get provisioning request history."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    # Get limit from query parameter if provided
    limit = int(request.args.get("limit", 50))

    requests_history = pbx_core.phone_provisioning.get_request_history(limit=limit)
    return send_json(
        {
            "total": len(pbx_core.phone_provisioning.provision_requests),
            "limit": limit,
            "requests": requests_history,
        }
    )


@provisioning_bp.route("/api/registered-phones", methods=["GET"])
def handle_get_registered_phones() -> Response:
    """Get all registered phones from database."""
    pbx_core = get_pbx_core()
    if (
        pbx_core
        and hasattr(pbx_core, "registered_phones_db")
        and pbx_core.registered_phones_db
    ):
        try:
            phones = pbx_core.registered_phones_db.list_all()
            return send_json(phones)
        except Exception as e:
            logger.error(f"Error loading registered phones from database: {e}")
            logger.error(
                f"  Database type: {pbx_core.registered_phones_db.db.db_type if hasattr(pbx_core.registered_phones_db, 'db') else 'unknown'}"
            )
            logger.error(
                f"  Database enabled: {pbx_core.registered_phones_db.db.enabled if hasattr(pbx_core.registered_phones_db, 'db') else 'unknown'}"
            )
            logger.error(f"  Traceback: {traceback.format_exc()}")
            return send_json(
                {"error": str(e), "details": "Check server logs for full error details"}, 500
            )
    else:
        # Return empty array when database is not available (graceful degradation)
        logger.warning("Registered phones database not available - returning empty list")
        if pbx_core:
            logger.warning("  pbx_core exists: True")
            logger.warning(
                f"  has registered_phones_db attr: {hasattr(pbx_core, 'registered_phones_db')}"
            )
            if hasattr(pbx_core, "registered_phones_db"):
                logger.warning(
                    f"  registered_phones_db is None: {pbx_core.registered_phones_db is None}"
                )
        return send_json([])


@provisioning_bp.route("/api/registered-phones/with-mac", methods=["GET"])
def handle_get_registered_phones_with_mac() -> Response:
    """Get registered phones with MAC addresses from provisioning system."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500)

    # Get registered phones (IP + Extension from SIP registrations)
    registered_phones = []
    if hasattr(pbx_core, "registered_phones_db") and pbx_core.registered_phones_db:
        try:
            registered_phones = pbx_core.registered_phones_db.list_all()
        except Exception as e:
            logger.error(f"Error loading registered phones: {e}")

    # Get provisioned devices (MAC + Extension from provisioning config)
    provisioned_devices = {}
    if hasattr(pbx_core, "phone_provisioning"):
        try:
            devices = pbx_core.phone_provisioning.get_all_devices()
            # Create a lookup by extension
            for device in devices:
                provisioned_devices[device.extension_number] = device
        except Exception as e:
            logger.error(f"Error loading provisioned devices: {e}")

    # Correlate the two data sources
    enhanced_phones = []
    for phone in registered_phones:
        enhanced = dict(phone)
        extension = phone.get("extension_number")

        # Add MAC from provisioning if available and not already present
        if extension and extension in provisioned_devices and not phone.get("mac_address"):
            device = provisioned_devices[extension]
            enhanced["mac_address"] = device.mac_address
            enhanced["vendor"] = device.vendor
            enhanced["model"] = device.model
            enhanced["config_url"] = device.config_url
            enhanced["mac_source"] = "provisioning"
        elif phone.get("mac_address"):
            enhanced["mac_source"] = "sip_registration"

        enhanced_phones.append(enhanced)

    return send_json(enhanced_phones)


@provisioning_bp.route("/api/registered-phones/extension/<number>", methods=["GET"])
def handle_get_registered_phones_by_extension(number: str) -> Response:
    """Get registered phones for a specific extension."""
    pbx_core = get_pbx_core()
    if (
        pbx_core
        and hasattr(pbx_core, "registered_phones_db")
        and pbx_core.registered_phones_db
    ):
        try:
            phones = pbx_core.registered_phones_db.get_by_extension(number)
            return send_json(phones)
        except Exception as e:
            logger.error(
                f"Error loading registered phones for extension {number} from database: {e}"
            )
            logger.error(f"  Extension: {number}")
            logger.error(
                f"  Database type: {pbx_core.registered_phones_db.db.db_type if hasattr(pbx_core.registered_phones_db, 'db') else 'unknown'}"
            )
            logger.error(
                f"  Database enabled: {pbx_core.registered_phones_db.db.enabled if hasattr(pbx_core.registered_phones_db, 'db') else 'unknown'}"
            )
            logger.error(f"  Traceback: {traceback.format_exc()}")
            return send_json(
                {"error": str(e), "details": "Check server logs for full error details"}, 500
            )
    else:
        # Return empty array when database is not available (graceful degradation)
        logger.warning(
            f"Registered phones database not available for extension {number} - returning empty list"
        )
        if pbx_core:
            logger.warning("  pbx_core exists: True")
            logger.warning(
                f"  has registered_phones_db attr: {hasattr(pbx_core, 'registered_phones_db')}"
            )
            if hasattr(pbx_core, "registered_phones_db"):
                logger.warning(
                    f"  registered_phones_db is None: {pbx_core.registered_phones_db is None}"
                )
        return send_json([])


@provisioning_bp.route("/provision/<path:path>.cfg", methods=["GET"])
def handle_provisioning_request(path: str) -> Response:
    """Handle phone provisioning config request."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        logger.error("Phone provisioning not enabled but provisioning request received")
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    try:
        # Extract MAC address from path: /provision/{mac}.cfg
        filename = path.split("/")[-1]
        mac = filename

        # Gather request information for logging
        request_info = {
            "ip": request.remote_addr or "Unknown",
            "user_agent": request.headers.get("User-Agent", "Unknown"),
            "path": path,
        }

        logger.info(
            f"Provisioning config request: path={path}, IP={request_info['ip']}"
        )

        # Detect if MAC is a literal placeholder (misconfiguration)
        if mac in MAC_ADDRESS_PLACEHOLDERS:
            logger.error(
                f"CONFIGURATION ERROR: Phone requested provisioning with placeholder '{mac}' instead of actual MAC address"
            )
            logger.error(f"  Request from IP: {request_info['ip']}")
            logger.error(f"  User-Agent: {request_info['user_agent']}")
            logger.error("")
            logger.error("  WARNING: ROOT CAUSE: Phone is configured with wrong MAC variable format")
            logger.error("")
            logger.error(
                "  SOLUTION: Update provisioning URL to use correct MAC variable for your phone:"
            )
            logger.error("")

            # Get provisioning URL information
            protocol, server_ip, port, base_url = _get_provisioning_url_info()

            # Detect vendor from User-Agent and provide specific guidance
            user_agent = request_info["user_agent"].lower()
            if "zultys" in user_agent:
                logger.error(
                    f"  Zultys Phones - Use: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                )
                logger.error("    Configure in: Phone Menu -> Setup -> Network -> Provisioning")
                logger.error(
                    f"    Or DHCP Option 66: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                )
            elif "yealink" in user_agent:
                logger.error(
                    f"  Yealink Phones - Use: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                )
                logger.error("    Configure in: Web Interface -> Settings -> Auto Provision")
            elif "polycom" in user_agent:
                logger.error(
                    f"  Polycom Phones - Use: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                )
                logger.error("    Configure in: Web Interface -> Settings -> Provisioning Server")
            elif "cisco" in user_agent:
                logger.error(
                    f"  Cisco Phones - Use: {protocol}://{server_ip}:{port}/provision/$MA.cfg"
                )
                logger.error("    Note: Cisco uses $MA instead of $mac")
                logger.error(
                    "    Configure in: Web Interface -> Admin Login -> Voice -> Provisioning"
                )
            elif "grandstream" in user_agent:
                logger.error(
                    f"  Grandstream Phones - Use: {protocol}://{server_ip}:{port}/provision/$mac.cfg"
                )
                logger.error(
                    "    Configure in: Web Interface -> Maintenance -> Upgrade and Provisioning"
                )
            else:
                logger.error("  Common MAC variable formats by vendor:")
                logger.error("    Zultys, Yealink, Polycom, Grandstream: $mac")
                logger.error("    Cisco: $MA")
            logger.error("")
            logger.error(
                "  See PHONE_PROVISIONING.md for detailed vendor-specific instructions"
            )

            return send_json(
                {
                    "error": "Configuration error: MAC address placeholder detected",
                    "details": f'Phone is using placeholder "{mac}" instead of actual MAC. Update provisioning URL to use correct MAC variable format for your phone vendor.',
                },
                400,
            )

        logger.info(f"  MAC address from request: {mac}")

        # Generate configuration
        config_content, content_type = pbx_core.phone_provisioning.generate_config(
            mac, pbx_core.extension_registry, request_info
        )

        if config_content:
            logger.info(
                f"Provisioning config delivered: {len(config_content)} bytes to {request_info['ip']}"
            )

            # Store IP to MAC mapping in database for admin panel tracking
            if (
                pbx_core
                and hasattr(pbx_core, "registered_phones_db")
                and pbx_core.registered_phones_db
            ):
                try:
                    # Get the device to find its extension number
                    device = pbx_core.phone_provisioning.get_device(mac)
                    if device:
                        # Store/update the IP-MAC-Extension mapping
                        normalized_mac = normalize_mac_address(mac)

                        # Store the mapping in the database
                        success, stored_mac = pbx_core.registered_phones_db.register_phone(
                            extension_number=device.extension_number,
                            ip_address=request_info["ip"],
                            mac_address=normalized_mac,
                            user_agent=request_info.get("user_agent", "Unknown"),
                            contact_uri=None,  # Not available during provisioning request
                        )
                        if success:
                            logger.info(
                                f"  Stored IP-MAC mapping: {request_info['ip']} -> {stored_mac} (ext {device.extension_number})"
                            )
                except (KeyError, TypeError, ValueError) as e:
                    # Don't fail provisioning if database storage fails
                    logger.warning(f"  Could not store IP-MAC mapping in database: {e}")

            response = current_app.response_class(
                response=config_content,
                status=200,
                mimetype=content_type,
            )
            return response
        else:
            logger.warning(
                f"Provisioning failed for MAC {mac} from IP {request_info['ip']}"
            )
            logger.warning("  Reason: Device not registered or template not found")
            logger.warning("  See detailed error messages above for troubleshooting guidance")

            # Get provisioning URL information
            protocol, server_ip, port, base_url = _get_provisioning_url_info()

            logger.warning("  To register this device:")
            logger.warning(f"    curl -X POST {base_url}/api/provisioning/devices \\")
            logger.warning("      -H 'Content-type: application/json' \\")
            logger.warning(
                '      -d \'{"mac_address":"{mac}","extension_number":"XXXX","vendor":"VENDOR","model":"MODEL"}\''
            )
            return send_json({"error": "Device or template not found"}, 404)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error handling provisioning request: {e}")
        logger.error(f"  Path: {path}")
        logger.error(f"  Traceback: {traceback.format_exc()}")
        return send_json({"error": str(e)}, 500)


# ---------------------------------------------------------------------------
# POST routes
# ---------------------------------------------------------------------------


@provisioning_bp.route("/api/provisioning/devices", methods=["POST"])
@require_admin
def handle_register_device() -> Response:
    """Register a device for provisioning."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    try:
        body = get_request_body()
        mac = body.get("mac_address")
        extension = body.get("extension_number")
        vendor = body.get("vendor")
        model = body.get("model")

        if not all([mac, extension, vendor, model]):
            return send_json({"error": "Missing required fields"}, 400)

        device = pbx_core.phone_provisioning.register_device(mac, extension, vendor, model)

        # Automatically trigger phone reboot after registration
        # This ensures the phone fetches its fresh configuration immediately
        reboot_triggered = False
        try:
            ext = pbx_core.extension_registry.get(extension)
            if ext and ext.registered:
                logger.info(
                    f"Auto-provisioning: Automatically rebooting phone for extension {extension} after device registration"
                )
                reboot_triggered = pbx_core.phone_provisioning.reboot_phone(
                    extension, pbx_core.sip_server
                )
                if reboot_triggered:
                    logger.info(
                        f"Auto-provisioning: Successfully triggered reboot for extension {extension}"
                    )
                else:
                    logger.info(
                        f"Auto-provisioning: Extension {extension} not currently registered, phone will fetch config on next boot"
                    )
            else:
                logger.info(
                    f"Auto-provisioning: Extension {extension} not currently registered, phone will fetch config on next boot"
                )
        except (KeyError, TypeError, ValueError) as reboot_error:
            logger.warning(
                f"Auto-provisioning: Could not auto-reboot phone for extension {extension}: {reboot_error}"
            )
            # Don't fail the registration if reboot fails

        response_data = {"success": True, "device": device.to_dict()}
        if reboot_triggered:
            response_data["reboot_triggered"] = True
            response_data["message"] = "Device registered and phone reboot triggered automatically"
        else:
            response_data["reboot_triggered"] = False
            response_data["message"] = "Device registered. Phone will fetch config on next boot."

        return send_json(response_data)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@provisioning_bp.route("/api/provisioning/templates/<vendor>/<model>/export", methods=["POST"])
@require_admin
def handle_export_template(vendor: str, model: str) -> Response:
    """Export template to file."""
    # Validate vendor/model to prevent path traversal
    if not re.match(r"^[a-z0-9_-]+$", vendor) or not re.match(r"^[a-z0-9_-]+$", model):
        return send_json({"error": "Invalid vendor or model name"}, 400)

    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    success, message, filepath = pbx_core.phone_provisioning.export_template_to_file(
        vendor, model
    )
    if success:
        return send_json(
            {
                "success": True,
                "message": message,
                "filepath": filepath,
                "vendor": vendor,
                "model": model,
            }
        )
    else:
        return send_json({"error": message}, 404)


@provisioning_bp.route("/api/provisioning/reload-templates", methods=["POST"])
@require_admin
def handle_reload_templates() -> Response:
    """Reload all templates from disk."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    success, message, stats = pbx_core.phone_provisioning.reload_templates()
    if success:
        return send_json({"success": True, "message": message, "statistics": stats})
    else:
        return send_json({"error": message}, 500)


@provisioning_bp.route("/api/provisioning/devices/<mac>/static-ip", methods=["POST"])
@require_admin
def handle_set_static_ip(mac: str) -> Response:
    """set static IP for a device."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    try:
        body = get_request_body()
        static_ip = body.get("static_ip")

        if not static_ip:
            return send_json({"error": "Missing static_ip field"}, 400)

        success, message = pbx_core.phone_provisioning.set_static_ip(mac, static_ip)
        if success:
            return send_json({"success": True, "message": message})
        else:
            return send_json({"error": message}, 400)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


# ---------------------------------------------------------------------------
# PUT routes
# ---------------------------------------------------------------------------


@provisioning_bp.route("/api/provisioning/templates/<vendor>/<model>", methods=["PUT"])
@require_admin
def handle_update_template(vendor: str, model: str) -> Response:
    """Update template content."""
    # Validate vendor/model to prevent path traversal
    if not re.match(r"^[a-z0-9_-]+$", vendor) or not re.match(r"^[a-z0-9_-]+$", model):
        return send_json({"error": "Invalid vendor or model name"}, 400)

    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    try:
        body = get_request_body()
        content = body.get("content")

        if not content:
            return send_json({"error": "Missing template content"}, 400)

        success, message = pbx_core.phone_provisioning.update_template(
            vendor, model, content
        )
        if success:
            return send_json(
                {"success": True, "message": message, "vendor": vendor, "model": model}
            )
        else:
            return send_json({"error": message}, 500)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


# ---------------------------------------------------------------------------
# DELETE routes
# ---------------------------------------------------------------------------


@provisioning_bp.route("/api/provisioning/devices/<mac>", methods=["DELETE"])
@require_admin
def handle_unregister_device(mac: str) -> Response:
    """Unregister a device."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_provisioning"):
        return send_json({"error": "Phone provisioning not enabled"}, 500)

    try:
        success = pbx_core.phone_provisioning.unregister_device(mac)
        if success:
            return send_json({"success": True, "message": "Device unregistered"})
        else:
            return send_json({"error": "Device not found"}, 404)
    except Exception as e:
        return send_json({"error": str(e)}, 500)
