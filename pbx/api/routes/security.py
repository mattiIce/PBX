"""Security, Hot-Desking, MFA, Threat Detection, and DND Blueprint routes."""

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

security_bp = Blueprint("security", __name__)


# ---------------------------------------------------------------------------
# Hot-Desking routes
# ---------------------------------------------------------------------------


@security_bp.route("/api/hot-desk/sessions", methods=["GET"])
@require_auth
def handle_get_hot_desk_sessions() -> tuple[Response, int]:
    """Get all hot-desk sessions."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "hot_desking"):
        return send_json({"error": "Hot-desking not available"}, 500), 500

    try:
        sessions = pbx_core.hot_desking.get_active_sessions()
        return send_json({"count": len(sessions), "sessions": sessions}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/hot-desk/session/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_hot_desk_session(subpath: str) -> tuple[Response, int]:
    """Get specific hot-desk session by device."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "hot_desking"):
        return send_json({"error": "Hot-desking not available"}, 500), 500

    try:
        device_id = subpath.rsplit("/", maxsplit=1)[-1]
        session = pbx_core.hot_desking.get_session(device_id)

        if session:
            return send_json(session.to_dict()), 200
        return send_json({"error": "No session found for device"}, 404), 404
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/hot-desk/extension/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_hot_desk_extension(subpath: str) -> tuple[Response, int]:
    """Get hot-desk information for extension."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "hot_desking"):
        return send_json({"error": "Hot-desking not available"}, 500), 500

    try:
        extension = subpath.rsplit("/", maxsplit=1)[-1]
        devices = pbx_core.hot_desking.get_extension_devices(extension)
        sessions = []

        for device_id in devices:
            session = pbx_core.hot_desking.get_session(device_id)
            if session:
                sessions.append(session.to_dict())

        return send_json(
            {
                "extension": extension,
                "logged_in": len(sessions) > 0,
                "device_count": len(devices),
                "sessions": sessions,
            }
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/hot-desk/login", methods=["POST"])
@require_auth
def handle_hot_desk_login() -> tuple[Response, int]:
    """Handle hot-desk login."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "hot_desking"):
        return send_json({"error": "Hot-desking not available"}, 500), 500

    try:
        data = get_request_body()
        extension = data.get("extension")
        device_id = data.get("device_id")
        ip_address = data.get("ip_address", request.remote_addr)
        pin = data.get("pin")

        if not all([extension, device_id]):
            return send_json({"error": "extension and device_id are required"}, 400), 400

        success = pbx_core.hot_desking.login(extension, device_id, ip_address, pin)

        if success:
            profile = pbx_core.hot_desking.get_extension_profile(extension)
            return send_json(
                {
                    "success": True,
                    "message": f"Extension {extension} logged in",
                    "profile": profile,
                }
            ), 200
        return send_json({"error": "Login failed"}, 401), 401
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/hot-desk/logout", methods=["POST"])
@require_auth
def handle_hot_desk_logout() -> tuple[Response, int]:
    """Handle hot-desk logout."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "hot_desking"):
        return send_json({"error": "Hot-desking not available"}, 500), 500

    try:
        data = get_request_body()
        device_id = data.get("device_id")
        # Optional: logout specific extension
        extension = data.get("extension")

        if device_id:
            success = pbx_core.hot_desking.logout(device_id)
            if success:
                return send_json(
                    {"success": True, "message": f"Logged out from device {device_id}"}
                ), 200
            return send_json({"error": "No active session for device"}, 404), 404
        if extension:
            count = pbx_core.hot_desking.logout_extension(extension)
            return send_json(
                {
                    "success": True,
                    "message": f"Extension {extension} logged out from {count} device(s)",
                }
            ), 200
        return send_json({"error": "device_id or extension is required"}, 400), 400
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


# ---------------------------------------------------------------------------
# MFA routes
# ---------------------------------------------------------------------------


@security_bp.route("/api/mfa/status/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_mfa_status(subpath: str) -> tuple[Response, int]:
    """Get MFA status for extension."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "mfa_manager"):
        return send_json({"error": "MFA not available"}, 500), 500

    try:
        extension = subpath.rsplit("/", maxsplit=1)[-1]
        enabled = pbx_core.mfa_manager.is_enabled_for_user(extension)

        return send_json(
            {
                "extension": extension,
                "mfa_enabled": enabled,
                "mfa_required": pbx_core.mfa_manager.required,
            }
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/mfa/methods/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_mfa_methods(subpath: str) -> tuple[Response, int]:
    """Get enrolled MFA methods for extension."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "mfa_manager"):
        return send_json({"error": "MFA not available"}, 500), 500

    try:
        extension = subpath.rsplit("/", maxsplit=1)[-1]
        methods = pbx_core.mfa_manager.get_enrolled_methods(extension)

        return send_json({"extension": extension, "methods": methods}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/mfa/enroll", methods=["POST"])
@require_auth
def handle_mfa_enroll() -> tuple[Response, int]:
    """Handle MFA enrollment."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "mfa_manager"):
        return send_json({"error": "MFA not available"}, 500), 500

    try:
        data = get_request_body()
        extension_number = data.get("extension")

        if not extension_number:
            return send_json({"error": "extension is required"}, 400), 400

        success, provisioning_uri, backup_codes = pbx_core.mfa_manager.enroll_user(extension_number)

        if success:
            return send_json(
                {
                    "success": True,
                    "provisioning_uri": provisioning_uri,
                    "backup_codes": backup_codes,
                    "message": "MFA enrollment initiated. Scan QR code and verify with first code.",
                }
            ), 200
        return send_json({"error": "MFA enrollment failed"}, 500), 500
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/mfa/verify-enrollment", methods=["POST"])
@require_auth
def handle_mfa_verify_enrollment() -> tuple[Response, int]:
    """Handle MFA enrollment verification."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "mfa_manager"):
        return send_json({"error": "MFA not available"}, 500), 500

    try:
        data = get_request_body()
        extension_number = data.get("extension")
        code = data.get("code")

        if not extension_number or not code:
            return send_json({"error": "extension and code are required"}, 400), 400

        success = pbx_core.mfa_manager.verify_enrollment(extension_number, code)

        if success:
            return send_json({"success": True, "message": "MFA successfully activated"}), 200
        return send_json({"error": "Invalid code"}, 401), 401
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/mfa/verify", methods=["POST"])
@require_auth
def handle_mfa_verify() -> tuple[Response, int]:
    """Handle MFA code verification."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "mfa_manager"):
        return send_json({"error": "MFA not available"}, 500), 500

    try:
        data = get_request_body()
        extension_number = data.get("extension")
        code = data.get("code")

        if not extension_number or not code:
            return send_json({"error": "extension and code are required"}, 400), 400

        success = pbx_core.mfa_manager.verify_code(extension_number, code)

        if success:
            return send_json({"success": True, "message": "MFA verification successful"}), 200
        return send_json({"error": "Invalid code"}, 401), 401
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/mfa/disable", methods=["POST"])
@require_auth
def handle_mfa_disable() -> tuple[Response, int]:
    """Handle MFA disable."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "mfa_manager"):
        return send_json({"error": "MFA not available"}, 500), 500

    try:
        data = get_request_body()
        extension_number = data.get("extension")

        if not extension_number:
            return send_json({"error": "extension is required"}, 400), 400

        success = pbx_core.mfa_manager.disable_for_user(extension_number)

        if success:
            return send_json({"success": True, "message": "MFA disabled successfully"}), 200
        return send_json({"error": "Failed to disable MFA"}, 500), 500
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/mfa/enroll-yubikey", methods=["POST"])
@require_auth
def handle_mfa_enroll_yubikey() -> tuple[Response, int]:
    """Handle YubiKey enrollment."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "mfa_manager"):
        return send_json({"error": "MFA not available"}, 500), 500

    try:
        data = get_request_body()
        extension_number = data.get("extension")
        otp = data.get("otp")
        device_name = data.get("device_name", "YubiKey")

        if not extension_number or not otp:
            return send_json({"error": "extension and otp are required"}, 400), 400

        success, error = pbx_core.mfa_manager.enroll_yubikey(extension_number, otp, device_name)

        if success:
            return send_json({"success": True, "message": "YubiKey enrolled successfully"}), 200
        return send_json({"error": error or "YubiKey enrollment failed"}, 400), 400
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/mfa/enroll-fido2", methods=["POST"])
@require_auth
def handle_mfa_enroll_fido2() -> tuple[Response, int]:
    """Handle FIDO2/WebAuthn credential enrollment."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "mfa_manager"):
        return send_json({"error": "MFA not available"}, 500), 500

    try:
        data = get_request_body()
        extension_number = data.get("extension")
        credential_data = data.get("credential_data")
        device_name = data.get("device_name", "Security Key")

        if not extension_number or not credential_data:
            return send_json({"error": "extension and credential_data are required"}, 400), 400

        success, error = pbx_core.mfa_manager.enroll_fido2(
            extension_number, credential_data, device_name
        )

        if success:
            return send_json(
                {"success": True, "message": "FIDO2 credential enrolled successfully"}
            ), 200
        return send_json({"error": error or "FIDO2 enrollment failed"}, 400), 400
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


# ---------------------------------------------------------------------------
# Threat Detection / Security routes
# ---------------------------------------------------------------------------


@security_bp.route("/api/security/threat-summary", methods=["GET"])
@require_auth
def handle_get_threat_summary() -> tuple[Response, int]:
    """Get threat detection summary."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "threat_detector"):
        return send_json({"error": "Threat detection not available"}, 500), 500

    try:
        # Get hours parameter from query string
        hours = int(request.args.get("hours", 24))

        summary = pbx_core.threat_detector.get_threat_summary(hours)

        return send_json(summary), 200
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/security/compliance-status", methods=["GET"])
@require_auth
def handle_get_security_compliance_status() -> tuple[Response, int]:
    """Get FIPS and security compliance status."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "security_monitor"):
        return send_json({"error": "Security monitor not available"}, 500), 500

    try:
        status = pbx_core.security_monitor.get_compliance_status()
        return send_json(status), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/security/health", methods=["GET"])
@require_auth
def handle_get_security_health() -> tuple[Response, int]:
    """Get comprehensive security health check."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "security_monitor"):
        return send_json({"error": "Security monitor not available"}, 500), 500

    try:
        # Perform security check
        results = pbx_core.security_monitor.perform_security_check()
        return send_json(results), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/security/check-ip/<path:subpath>", methods=["GET"])
@require_auth
def handle_check_ip(subpath: str) -> tuple[Response, int]:
    """Check if IP is blocked."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "threat_detector"):
        return send_json({"error": "Threat detection not available"}, 500), 500

    try:
        ip_address = subpath.rsplit("/", maxsplit=1)[-1]
        is_blocked, reason = pbx_core.threat_detector.is_ip_blocked(ip_address)

        return send_json(
            {"ip_address": ip_address, "is_blocked": is_blocked, "reason": reason}
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/security/block-ip", methods=["POST"])
@require_admin
def handle_block_ip() -> tuple[Response, int]:
    """Handle IP blocking."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "threat_detector"):
        return send_json({"error": "Threat detection not available"}, 500), 500

    try:
        data = get_request_body()
        ip_address = data.get("ip_address")
        reason = data.get("reason", "Manual block")
        duration = data.get("duration")  # Optional, in seconds

        if not ip_address:
            return send_json({"error": "ip_address is required"}, 400), 400

        pbx_core.threat_detector.block_ip(ip_address, reason, duration)

        return send_json({"success": True, "message": f"IP {ip_address} blocked successfully"}), 200
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/security/unblock-ip", methods=["POST"])
@require_admin
def handle_unblock_ip() -> tuple[Response, int]:
    """Handle IP unblocking."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "threat_detector"):
        return send_json({"error": "Threat detection not available"}, 500), 500

    try:
        data = get_request_body()
        ip_address = data.get("ip_address")

        if not ip_address:
            return send_json({"error": "ip_address is required"}, 400), 400

        pbx_core.threat_detector.unblock_ip(ip_address)

        return send_json(
            {"success": True, "message": f"IP {ip_address} unblocked successfully"}
        ), 200
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


# ---------------------------------------------------------------------------
# DND (Do Not Disturb) routes
# ---------------------------------------------------------------------------


@security_bp.route("/api/dnd/status/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_dnd_status(subpath: str) -> tuple[Response, int]:
    """Get DND status for extension."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "dnd_scheduler"):
        return send_json({"error": "DND Scheduler not available"}, 500), 500

    try:
        extension = subpath.rsplit("/", maxsplit=1)[-1]
        status = pbx_core.dnd_scheduler.get_status(extension)

        return send_json(status), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/dnd/rules/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_dnd_rules(subpath: str) -> tuple[Response, int]:
    """Get DND rules for extension."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "dnd_scheduler"):
        return send_json({"error": "DND Scheduler not available"}, 500), 500

    try:
        extension = subpath.rsplit("/", maxsplit=1)[-1]
        rules = pbx_core.dnd_scheduler.get_rules(extension)

        return send_json({"extension": extension, "rules": rules}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/dnd/rule", methods=["POST"])
@require_auth
def handle_add_dnd_rule() -> tuple[Response, int]:
    """Handle adding DND rule."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "dnd_scheduler"):
        return send_json({"error": "DND Scheduler not available"}, 500), 500

    try:
        data = get_request_body()
        extension = data.get("extension")
        rule_type = data.get("rule_type")  # 'calendar' or 'time_based'
        config = data.get("config", {})

        if not extension or not rule_type:
            return send_json({"error": "extension and rule_type are required"}, 400), 400

        rule_id = pbx_core.dnd_scheduler.add_rule(extension, rule_type, config)

        return send_json(
            {"success": True, "rule_id": rule_id, "message": "DND rule added successfully"}
        ), 200
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/dnd/register-calendar", methods=["POST"])
@require_auth
def handle_register_calendar_user() -> tuple[Response, int]:
    """Handle registering user for calendar-based DND."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "dnd_scheduler"):
        return send_json({"error": "DND Scheduler not available"}, 500), 500

    try:
        data = get_request_body()
        extension = data.get("extension")
        email = data.get("email")

        if not extension or not email:
            return send_json({"error": "extension and email are required"}, 400), 400

        pbx_core.dnd_scheduler.register_calendar_user(extension, email)

        return send_json(
            {"success": True, "message": f"Calendar monitoring registered for {extension}"}
        ), 200
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/dnd/override", methods=["POST"])
@require_auth
def handle_dnd_override() -> tuple[Response, int]:
    """Handle manual DND override."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "dnd_scheduler"):
        return send_json({"error": "DND Scheduler not available"}, 500), 500

    try:
        data = get_request_body()
        extension = data.get("extension")
        status = data.get("status")  # e.g., 'do_not_disturb', 'available'
        duration_minutes = data.get("duration_minutes")  # Optional

        if not extension or not status:
            return send_json({"error": "extension and status are required"}, 400), 400

        # Convert status string to PresenceStatus enum
        from pbx.features.presence import PresenceStatus

        try:
            status_enum = PresenceStatus(status)
        except ValueError:
            return send_json({"error": f"Invalid status: {status}"}, 400), 400

        pbx_core.dnd_scheduler.set_manual_override(extension, status_enum, duration_minutes)

        return send_json({"success": True, "message": f"Manual override set for {extension}"}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/dnd/rule/<rule_id>", methods=["DELETE"])
@require_auth
def handle_delete_dnd_rule(rule_id: str) -> tuple[Response, int]:
    """Handle deleting DND rule."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "dnd_scheduler"):
        return send_json({"error": "DND Scheduler not available"}, 500), 500

    try:
        success = pbx_core.dnd_scheduler.remove_rule(rule_id)

        if success:
            return send_json({"success": True, "message": "DND rule deleted successfully"}), 200
        return send_json({"error": "Rule not found"}, 404), 404
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@security_bp.route("/api/dnd/override/<extension>", methods=["DELETE"])
@require_auth
def handle_clear_dnd_override(extension: str) -> tuple[Response, int]:
    """Handle clearing DND override."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "dnd_scheduler"):
        return send_json({"error": "DND Scheduler not available"}, 500), 500

    try:
        pbx_core.dnd_scheduler.clear_manual_override(extension)

        return send_json({"success": True, "message": f"Override cleared for {extension}"}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500
