#!/usr/bin/env python3
"""License Management API Endpoints.

Provides REST API for managing licensing and subscriptions.
Protected by license administrator authentication.
"""

import logging
import os

from flask import Blueprint, jsonify, request

from pbx.utils.license_admin import require_license_admin, verify_license_admin_session
from pbx.utils.licensing import LicenseType, get_license_manager

logger = logging.getLogger(__name__)

# Create blueprint
license_api = Blueprint("license_api", __name__)


@license_api.route("/api/license/status", methods=["GET"])
def get_license_status():
    """
    Get current license status and information.

    Available to all authenticated users to view license status.

    Returns:
        JSON with license status and details
    """
    try:
        license_manager = get_license_manager()
        info = license_manager.get_license_info()

        return jsonify({"success": True, "license": info}), 200

    except Exception as e:
        logger.error(f"Error getting license status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@license_api.route("/api/license/features", methods=["GET"])
def list_available_features():
    """
    list all available features for current license.

    Returns:
        JSON with available features list
    """
    try:
        license_manager = get_license_manager()

        # If licensing is disabled, all features available
        if not license_manager.enabled:
            return jsonify({"success": True, "features": "all", "licensing_enabled": False}), 200

        # Get license type
        if license_manager.current_license:
            license_type = license_manager.current_license.get("type", "trial")
        else:
            license_type = "trial"

        # Get features for this license type
        features = license_manager.features.get(license_type, [])

        # For custom license, get custom features
        if license_type == "custom" and license_manager.current_license:
            features = license_manager.current_license.get("custom_features", [])

        # Separate features and limits
        feature_list = []
        limits = {}

        for feature in features:
            if ":" in feature and any(
                feature.startswith(f"{limit}:")
                for limit in ["max_extensions", "max_concurrent_calls"]
            ):
                limit_name, limit_value = feature.split(":", 1)
                limits[limit_name] = None if limit_value == "unlimited" else int(limit_value)
            else:
                feature_list.append(feature)

        return (
            jsonify(
                {
                    "success": True,
                    "license_type": license_type,
                    "features": feature_list,
                    "limits": limits,
                    "licensing_enabled": True,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error listing features: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@license_api.route("/api/license/check", methods=["POST"])
def check_feature():
    """
    Check if a specific feature is available.

    Request JSON:
        {
            "feature": "feature_name"
        }

    Returns:
        JSON with availability status
    """
    try:
        data = request.get_json()
        feature_name = data.get("feature")

        if not feature_name:
            return jsonify({"success": False, "error": "Missing feature name"}), 400

        license_manager = get_license_manager()
        available = license_manager.has_feature(feature_name)

        return jsonify({"success": True, "feature": feature_name, "available": available}), 200

    except Exception as e:
        logger.error(f"Error checking feature: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@license_api.route("/api/license/generate", methods=["POST"])
@require_license_admin
def generate_license():
    """
    Generate a new license key (license admin only).

    Requires authentication as the special license administrator account.

    Request JSON:
        {
            "type": "trial|basic|professional|enterprise|perpetual|custom",
            "issued_to": "Organization Name",
            "max_extensions": 50 (optional),
            "max_concurrent_calls": 25 (optional),
            "expiration_days": 365 (optional, null for perpetual),
            "custom_features": ["feature1", "feature2"] (optional, for custom type)
        }

    Returns:
        JSON with generated license data
    """
    try:
        # Authentication handled by @require_license_admin decorator
        data = request.get_json()

        # Validate required fields
        license_type_str = data.get("type")
        issued_to = data.get("issued_to")

        if not license_type_str or not issued_to:
            return (
                jsonify({"success": False, "error": "Missing required fields: type, issued_to"}),
                400,
            )

        # Parse license type
        try:
            license_type = LicenseType(license_type_str)
        except ValueError:
            return (
                jsonify({"success": False, "error": f"Invalid license type: {license_type_str}"}),
                400,
            )

        # Get optional fields
        max_extensions = data.get("max_extensions")
        max_concurrent_calls = data.get("max_concurrent_calls")
        expiration_days = data.get("expiration_days")
        custom_features = data.get("custom_features")

        # Generate license
        license_manager = get_license_manager()
        license_data = license_manager.generate_license_key(
            license_type=license_type,
            issued_to=issued_to,
            max_extensions=max_extensions,
            max_concurrent_calls=max_concurrent_calls,
            expiration_days=expiration_days,
            custom_features=custom_features,
        )

        return jsonify({"success": True, "license": license_data}), 200

    except Exception as e:
        logger.error(f"Error generating license: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@license_api.route("/api/license/install", methods=["POST"])
@require_license_admin
def install_license():
    """
    Install a license key (license admin only).

    Requires authentication as the special license administrator account.

    Request JSON:
        {
            "license_data": { ... license data object ... },
            "enforce_licensing": true  # Optional: create lock file to prevent disabling
        }
        OR
        {
            "license_key": "XXXX-XXXX-XXXX-XXXX",
            "enforce_licensing": false,  # Optional (default: false)
            ... other license fields ...
        }

    Returns:
        JSON with installation status
    """
    try:

        data = request.get_json()
        license_data = data.get("license_data") or data
        enforce_licensing = data.get("enforce_licensing", False)

        # Validate license data
        if "key" not in license_data:
            return jsonify({"success": False, "error": "Missing license key"}), 400

        # Save license with optional enforcement
        license_manager = get_license_manager()
        success = license_manager.save_license(license_data, enforce_licensing=enforce_licensing)

        message = "License installed successfully"
        if enforce_licensing:
            message += " (licensing enforcement enabled - cannot be disabled)"

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": message,
                        "license": license_manager.get_license_info(),
                        "enforcement_locked": enforce_licensing,
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to install license"}), 500

    except Exception as e:
        logger.error(f"Error installing license: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@license_api.route("/api/license/revoke", methods=["POST"])
@require_license_admin
def revoke_license():
    """
    Revoke current license (license admin only).

    Requires authentication as the special license administrator account.

    Returns:
        JSON with revocation status
    """
    try:
        license_manager = get_license_manager()
        success = license_manager.revoke_license()

        if success:
            return jsonify({"success": True, "message": "License revoked successfully"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to revoke license"}), 500

    except Exception as e:
        logger.error(f"Error revoking license: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@license_api.route("/api/license/toggle", methods=["POST"])
@require_license_admin
def toggle_licensing():
    """
    Enable or disable licensing enforcement (license admin only).

    Requires authentication as the special license administrator account.

    Request JSON:
        {
            "enabled": true|false
        }

    Returns:
        JSON with new licensing status
    """
    try:
        data = request.get_json()
        enabled = data.get("enabled")

        if enabled is None:
            return jsonify({"success": False, "error": "Missing enabled flag"}), 400

        # Update licensing status
        # This writes to config file or environment
        license_manager = get_license_manager()

        # Update .env file for persistence
        # NOTE: PBX restart required for change to take full effect
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")

        # Read existing .env
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                env_lines = f.readlines()

        # Check if license lock exists
        lock_path = os.path.join(os.path.dirname(__file__), "..", "..", ".license_lock")
        if os.path.exists(lock_path):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Cannot disable licensing - license lock file exists. Use remove_lock endpoint first.",
                        "licensing_enabled": True,
                    }
                ),
                403,
            )

        # Update or add PBX_LICENSING_ENABLED
        found = False
        for i, line in enumerate(env_lines):
            if line.startswith("PBX_LICENSING_ENABLED="):
                env_lines[i] = f"PBX_LICENSING_ENABLED={'true' if enabled else 'false'}\n"
                found = True
                break

        if not found:
            env_lines.append(
                f'\n# Licensing\nPBX_LICENSING_ENABLED={"true" if enabled else "false"}\n'
            )

        # Write back
        with open(env_file, "w") as f:
            f.writelines(env_lines)

        # Also update runtime environment for immediate effect
        os.environ["PBX_LICENSING_ENABLED"] = "true" if enabled else "false"

        # Reinitialize license manager
        from pbx.utils.licensing import initialize_license_manager

        license_manager = initialize_license_manager(license_manager.config)

        return (
            jsonify(
                {
                    "success": True,
                    "licensing_enabled": license_manager.enabled,
                    "message": f'Licensing {"enabled" if enabled else "disabled"} successfully',
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error toggling licensing: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@license_api.route("/api/license/remove_lock", methods=["POST"])
@require_license_admin
def remove_license_lock():
    """
    Remove license lock file to allow disabling licensing (license admin only).

    Requires authentication as the special license administrator account.
    This is used when transitioning from commercial to open-source deployment.

    Returns:
        JSON with removal status
    """
    try:
        license_manager = get_license_manager()
        success = license_manager.remove_license_lock()

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "License lock removed - licensing can now be disabled",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "License lock file does not exist or could not be removed",
                    }
                ),
                404,
            )

    except Exception as e:
        logger.error(f"Error removing license lock: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@license_api.route("/api/license/verify_admin", methods=["GET"])
def verify_admin():
    """Verify if the current session belongs to the license administrator.

    Returns:
        JSON with verification status
    """
    is_authorized, error_msg = verify_license_admin_session(request)

    return (
        jsonify(
            {
                "success": True,
                "is_license_admin": is_authorized,
                "message": "Authorized" if is_authorized else (error_msg or "Not authorized"),
            }
        ),
        200,
    )


@license_api.route("/api/license/admin_login", methods=["POST"])
def admin_login():
    """
    Authenticate as the license administrator.

    Request JSON:
        {
            "extension": "9322",
            "username": "ICE",
            "pin": "26697647"
        }

    Returns:
        JSON with authentication status
    """
    from flask import session

    from pbx.utils.license_admin import verify_license_admin_credentials

    try:
        data = request.get_json()
        extension = data.get("extension", "").strip()
        username = data.get("username", "").strip()
        pin = data.get("pin", "").strip()

        if not extension or not username or not pin:
            return (
                jsonify(
                    {"success": False, "error": "Missing required fields: extension, username, pin"}
                ),
                400,
            )

        # Verify credentials using encrypted verification
        if verify_license_admin_credentials(extension, username, pin):
            # set session
            session["extension"] = extension
            session["username"] = username
            session["is_license_admin"] = True

            logger.info(f"License admin logged in: {extension}/{username}")

            return (
                jsonify(
                    {
                        "success": True,
                        "message": "License administrator authenticated successfully",
                        "extension": extension,
                        "username": username,
                    }
                ),
                200,
            )
        else:
            logger.warning(f"Failed license admin login attempt: {extension}/{username}")
            return jsonify({"success": False, "error": "Invalid credentials"}), 401

    except Exception as e:
        logger.error(f"Error during license admin login: {e}")
        return jsonify({"success": False, "error": "Authentication failed"}), 500


def register_license_routes(app):
    """
    Register license API routes with Flask app.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(license_api)
    logger.info("License API routes registered")
