"""License management Blueprint routes."""

import os
import tempfile
from pathlib import Path
from typing import Any

from flask import Blueprint, Response

from pbx.api.utils import (
    get_request_body,
    require_auth,
    send_json,
    verify_authentication,
)
from pbx.utils.logger import get_logger

logger = get_logger()

license_bp = Blueprint("license", __name__)


def _require_license_admin() -> tuple[bool, dict[str, Any]]:
    """Check if current user is the license administrator (extension 9322).

    Returns:
        tuple of (is_authorized, payload)

    The payload will be:
        - On success: the authenticated user payload from verify_authentication()
        - On authentication failure: a dict including at least {"status_code": 401}
        - On authorization failure: a dict including at least {"status_code": 403}
    """
    is_authenticated, payload = verify_authentication()
    if not is_authenticated:
        # User is not authenticated -> should be treated as 401 Unauthorized
        return False, {"status_code": 401, "error": "unauthenticated"}

    # Check if user is extension 9322 (license admin)
    from pbx.utils.license_admin import LICENSE_ADMIN_EXTENSION

    extension = payload.get("extension")

    if extension == LICENSE_ADMIN_EXTENSION:
        return True, payload

    # User is authenticated but not the license admin -> should be treated as 403 Forbidden
    return False, {"status_code": 403, "error": "forbidden", "extension": extension}


@license_bp.route("/api/license/status", methods=["GET"])
@require_auth
def handle_license_status() -> tuple[Response, int]:
    """Get current license status and information."""
    try:
        from pbx.utils.licensing import get_license_manager

        license_manager = get_license_manager()
        info = license_manager.get_license_info()

        return send_json({"success": True, "license": info}), 200
    except Exception as e:
        logger.error(f"Error getting license status: {e}")
        return send_json({"success": False, "error": str(e)}, 500), 500


@license_bp.route("/api/license/features", methods=["GET"])
@require_auth
def handle_license_features() -> tuple[Response, int]:
    """list all available features for current license."""
    try:
        from pbx.utils.licensing import get_license_manager

        license_manager = get_license_manager()

        # If licensing is disabled, all features available
        if not license_manager.enabled:
            return send_json({"success": True, "features": "all", "licensing_enabled": False}), 200

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
        feature_list: list[str] = []
        limits: dict[str, int | None] = {}

        for feature in features:
            if ":" in feature and any(
                feature.startswith(f"{limit}:")
                for limit in ["max_extensions", "max_concurrent_calls"]
            ):
                limit_name, limit_value = feature.split(":", 1)
                try:
                    if limit_value == "unlimited":
                        limits[limit_name] = None
                    else:
                        limits[limit_name] = int(limit_value)
                except ValueError:
                    # Malformed limit; log and skip this entry instead of failing
                    logger.warning(
                        "Ignoring malformed license limit value '%s' for '%s'",
                        limit_value,
                        limit_name,
                    )
                    continue
            else:
                feature_list.append(feature)

        return send_json(
            {
                "success": True,
                "license_type": license_type,
                "features": feature_list,
                "limits": limits,
                "licensing_enabled": True,
            }
        ), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error listing features: {e}")
        return send_json({"success": False, "error": str(e)}, 500), 500


@license_bp.route("/api/license/generate", methods=["POST"])
def handle_license_generate() -> tuple[Response, int]:
    """Generate a new license key (license admin only)."""
    # Check license admin authorization
    is_authorized, payload = _require_license_admin()
    if not is_authorized:
        status_code = payload.get("status_code", 401) if isinstance(payload, dict) else 401
        return send_json(
            {
                "success": False,
                "error": "Unauthorized. License management requires administrator authentication.",
            },
            status_code,
        ), status_code

    try:
        from pbx.utils.licensing import LicenseType, get_license_manager

        body = get_request_body()

        # Validate required fields
        license_type_str = body.get("type")
        issued_to = body.get("issued_to")

        if not license_type_str or not issued_to:
            return send_json(
                {"success": False, "error": "Missing required fields: type, issued_to"}, 400
            ), 400

        # Parse license type
        try:
            license_type = LicenseType(license_type_str)
        except ValueError:
            return send_json(
                {"success": False, "error": f"Invalid license type: {license_type_str}"}, 400
            ), 400

        # Get optional fields
        max_extensions = body.get("max_extensions")
        max_concurrent_calls = body.get("max_concurrent_calls")
        expiration_days = body.get("expiration_days")
        custom_features = body.get("custom_features")

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

        return send_json({"success": True, "license": license_data}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error generating license: {e}")
        return send_json({"success": False, "error": str(e)}, 500), 500


@license_bp.route("/api/license/install", methods=["POST"])
def handle_license_install() -> tuple[Response, int]:
    """Install a license key (license admin only)."""
    # Check license admin authorization
    is_authorized, payload = _require_license_admin()
    if not is_authorized:
        status_code = payload.get("status_code", 401) if isinstance(payload, dict) else 401
        return send_json(
            {
                "success": False,
                "error": "Unauthorized. License management requires administrator authentication.",
            },
            status_code,
        ), status_code

    try:
        from pbx.utils.licensing import get_license_manager

        body = get_request_body()
        license_data = body.get("license_data") or body
        enforce_licensing = body.get("enforce_licensing", False)

        # Validate license data
        if "key" not in license_data:
            return send_json({"success": False, "error": "Missing license key"}, 400), 400

        # Save license with optional enforcement
        license_manager = get_license_manager()
        success = license_manager.save_license(license_data, enforce_licensing=enforce_licensing)

        message = "License installed successfully"
        if enforce_licensing:
            message += " (licensing enforcement enabled - cannot be disabled)"

        if success:
            return send_json(
                {
                    "success": True,
                    "message": message,
                    "license": license_manager.get_license_info(),
                    "enforcement_locked": enforce_licensing,
                }
            ), 200
        return send_json({"success": False, "error": "Failed to install license"}, 500), 500
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error installing license: {e}")
        return send_json({"success": False, "error": str(e)}, 500), 500


@license_bp.route("/api/license/revoke", methods=["POST"])
def handle_license_revoke() -> tuple[Response, int]:
    """Revoke current license (license admin only)."""
    # Check license admin authorization
    is_authorized, _ = _require_license_admin()
    if not is_authorized:
        return send_json(
            {
                "success": False,
                "error": "Unauthorized. License management requires administrator authentication.",
            },
            401,
        ), 401

    try:
        from pbx.utils.licensing import get_license_manager

        license_manager = get_license_manager()
        success = license_manager.revoke_license()

        if success:
            return send_json({"success": True, "message": "License revoked successfully"}), 200
        return send_json({"success": False, "error": "Failed to revoke license"}, 500), 500
    except Exception as e:
        logger.error(f"Error revoking license: {e}")
        return send_json({"success": False, "error": str(e)}, 500), 500


@license_bp.route("/api/license/toggle", methods=["POST"])
def handle_license_toggle() -> tuple[Response, int]:
    """Enable or disable licensing enforcement (license admin only)."""
    # Check license admin authorization
    is_authorized, auth_status = _require_license_admin()
    if not is_authorized:
        # Determine appropriate status code:
        # - 401 for authentication failures
        # - 403 for authenticated users lacking license-admin privileges
        status_code = auth_status.get("status_code", 401) if isinstance(auth_status, dict) else 401
        return send_json(
            {
                "success": False,
                "error": "Unauthorized. License management requires administrator authentication.",
            },
            status_code,
        ), status_code

    try:
        from pbx.utils.licensing import get_license_manager, initialize_license_manager

        body = get_request_body()
        enabled = body.get("enabled")

        if enabled is None:
            return send_json({"success": False, "error": "Missing enabled flag"}, 400), 400

        # Update licensing status
        license_manager = get_license_manager()

        # Update .env file for persistence
        env_file = str(Path(__file__).resolve().parent.parent.parent / ".env")

        # Read existing .env
        env_lines = []
        if Path(env_file).exists():
            with Path(env_file).open() as f:
                env_lines = f.readlines()

        # Check if license lock exists
        lock_path = str(Path(__file__).resolve().parent.parent.parent / ".license_lock")
        if Path(lock_path).exists():
            return send_json(
                {
                    "success": False,
                    "error": "Cannot disable licensing - license lock file exists. Use remove_lock endpoint first.",
                    "licensing_enabled": True,
                },
                403,
            ), 403

        # Update or add PBX_LICENSING_ENABLED
        found = False
        for i, line in enumerate(env_lines):
            if line.startswith("PBX_LICENSING_ENABLED="):
                env_lines[i] = f"PBX_LICENSING_ENABLED={'true' if enabled else 'false'}\n"
                found = True
                break

        if not found:
            env_lines.append(
                f"\n# Licensing\nPBX_LICENSING_ENABLED={'true' if enabled else 'false'}\n"
            )

        # Write back atomically to avoid corrupting .env on partial failures
        env_dir = str(Path(env_file).parent)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=env_dir, prefix=".env.", suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w") as tmp_file:
                tmp_file.writelines(env_lines)
            # Atomically replace the original .env with the new version
            Path(tmp_path).replace(env_file)
        except OSError as write_err:
            # Best-effort cleanup of temporary file
            try:
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink()
            except OSError as cleanup_err:
                logger.warning("Failed to clean up temporary file %s: %s", tmp_path, cleanup_err)
            logger.error("Failed to update .env file for licensing: %s", write_err, exc_info=True)
            return send_json(
                {"success": False, "error": "Failed to persist licensing configuration"}, 500
            ), 500

        # Also update runtime environment for immediate effect
        os.environ["PBX_LICENSING_ENABLED"] = "true" if enabled else "false"

        # Reinitialize license manager
        license_manager = initialize_license_manager(license_manager.config)

        return send_json(
            {
                "success": True,
                "licensing_enabled": license_manager.enabled,
                "message": f"Licensing {'enabled' if enabled else 'disabled'} successfully",
            }
        ), 200
    except (KeyError, OSError, TypeError, ValueError) as e:
        logger.error(f"Error toggling licensing: {e}")
        return send_json({"success": False, "error": str(e)}, 500), 500


@license_bp.route("/api/license/remove_lock", methods=["POST"])
def handle_license_remove_lock() -> tuple[Response, int]:
    """Remove license lock file (license admin only)."""
    # Check license admin authorization
    is_authorized, payload = _require_license_admin()
    if not is_authorized:
        status_code = payload.get("status_code", 401) if isinstance(payload, dict) else 401
        return send_json(
            {
                "success": False,
                "error": "Unauthorized. License management requires administrator authentication.",
            },
            status_code,
        ), status_code

    try:
        from pbx.utils.licensing import get_license_manager

        license_manager = get_license_manager()
        success = license_manager.remove_license_lock()

        if success:
            return send_json(
                {
                    "success": True,
                    "message": "License lock removed - licensing can now be disabled",
                }
            ), 200
        return send_json(
            {
                "success": False,
                "error": "License lock file does not exist or could not be removed",
            },
            404,
        ), 404
    except Exception as e:
        logger.error(f"Error removing license lock: {e}")
        return send_json({"success": False, "error": str(e)}, 500), 500


@license_bp.route("/api/license/check", methods=["POST"])
@require_auth
def handle_license_check_feature() -> tuple[Response, int]:
    """Check if a specific feature is available."""
    try:
        from pbx.utils.licensing import get_license_manager

        body = get_request_body()
        feature_name = body.get("feature")

        if not feature_name:
            return send_json({"success": False, "error": "Missing feature name"}, 400), 400

        license_manager = get_license_manager()
        available = license_manager.has_feature(feature_name)

        return send_json({"success": True, "feature": feature_name, "available": available}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error checking feature: {e}")
        return send_json({"success": False, "error": str(e)}, 500), 500
