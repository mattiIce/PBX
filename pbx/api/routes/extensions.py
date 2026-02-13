"""Flask Blueprint for extension management routes."""

from flask import Blueprint, Response, jsonify, request, current_app

from pbx.api.utils import (
    get_pbx_core,
    send_json,
    verify_authentication,
    require_auth,
    require_admin,
    get_request_body,
    DateTimeEncoder,
    validate_limit_param,
)
from pbx.utils.config import Config
from pbx.utils.logger import get_logger

logger = get_logger()

extensions_bp = Blueprint("extensions", __name__)


@extensions_bp.route("/api/extensions", methods=["GET"])
def get_extensions() -> tuple[Response, int]:
    """Get extensions."""
    # SECURITY: Require authentication (but not necessarily admin)
    is_authenticated, payload = verify_authentication()
    if not is_authenticated:
        return jsonify({"error": "Authentication required"}), 401

    try:
        pbx_core = get_pbx_core()
        if pbx_core:
            extensions = pbx_core.extension_registry.get_all()

            # Check if user is admin
            is_admin = payload.get("is_admin", False)
            current_extension = payload.get("extension")

            # Non-admin users should only see their own extension
            if not is_admin:
                extensions = [e for e in extensions if e.number == current_extension]

            data = [
                {
                    "number": e.number,
                    "name": e.name,
                    "email": e.config.get("email"),
                    "registered": e.registered,
                    "allow_external": e.config.get("allow_external", True),
                    "ad_synced": e.config.get("ad_synced", False),
                    "voicemail_pin_hash": e.config.get("voicemail_pin_hash"),
                    "is_admin": e.config.get("is_admin", False),
                }
                for e in extensions
            ]
            return send_json(data), 200
        else:
            return send_json({"error": "PBX not initialized"}, 500), 500
    except Exception as e:
        logger.error(f"Error getting extensions: {e}")
        return send_json({"error": "Failed to retrieve extensions"}, 500), 500


@extensions_bp.route("/api/extensions", methods=["POST"])
@require_admin
def add_extension() -> tuple[Response, int]:
    """Add a new extension."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        body = get_request_body()
        number = body.get("number")
        name = body.get("name")
        email = body.get("email")
        password = body.get("password")
        allow_external = body.get("allow_external", True)
        voicemail_pin = body.get("voicemail_pin")
        is_admin = body.get("is_admin", False)

        if not all([number, name, password]):
            return send_json({"error": "Missing required fields"}, 400), 400

        # SECURITY: Validate voicemail PIN is provided
        if not voicemail_pin:
            return send_json({"error": "Voicemail PIN is required for security"}, 400), 400

        # Validate voicemail PIN format (4-6 digits)
        if (
            not str(voicemail_pin).isdigit()
            or len(str(voicemail_pin)) < 4
            or len(str(voicemail_pin)) > 6
        ):
            return send_json({"error": "Voicemail PIN must be 4-6 digits"}, 400), 400

        # Validate extension number format (4 digits)
        if not str(number).isdigit() or len(str(number)) != 4:
            return send_json({"error": "Extension number must be 4 digits"}, 400), 400

        # Validate password strength (minimum 8 characters)
        if len(password) < 8:
            return send_json({"error": "Password must be at least 8 characters"}, 400), 400

        # Validate email format if provided
        if email and not Config.validate_email(email):
            return send_json({"error": "Invalid email format"}, 400), 400

        # Check if extension already exists
        if pbx_core.extension_registry.get(number):
            return send_json({"error": "Extension already exists"}, 400), 400

        # Try to add to database first, fall back to config.yml
        if pbx_core.extension_db:
            # Add to database
            # NOTE: For production, use FIPS-compliant hashing via pbx.utils.encryption.FIPSEncryption.hash_password()
            # Currently storing plain password; system supports both plain
            # and hashed passwords
            password_hash = password
            success = pbx_core.extension_db.add(
                number=number,
                name=name,
                password_hash=password_hash,
                email=email if email else None,
                allow_external=allow_external,
                voicemail_pin=voicemail_pin if voicemail_pin else None,
                ad_synced=False,
                ad_username=None,
                is_admin=is_admin,
            )
        else:
            # Fall back to config.yml
            success = pbx_core.config.add_extension(
                number, name, email, password, allow_external
            )

        if success:
            # Reload extensions
            pbx_core.extension_registry.reload()
            return send_json({"success": True, "message": "Extension added successfully"}), 200
        else:
            return send_json({"error": "Failed to add extension"}, 500), 500
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@extensions_bp.route("/api/extensions/<number>", methods=["PUT"])
@require_admin
def update_extension(number: str) -> tuple[Response, int]:
    """Update an existing extension."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        body = get_request_body()
        name = body.get("name")
        email = body.get("email")
        password = body.get("password")  # Optional
        allow_external = body.get("allow_external")
        voicemail_pin = body.get("voicemail_pin")
        is_admin = body.get("is_admin")

        # Check if extension exists
        extension = pbx_core.extension_registry.get(number)
        if not extension:
            return send_json({"error": "Extension not found"}, 404), 404

        # Validate password strength if provided (minimum 8 characters)
        if password and len(password) < 8:
            return send_json({"error": "Password must be at least 8 characters"}, 400), 400

        # SECURITY: Validate voicemail PIN format if provided (4-6 digits)
        if voicemail_pin is not None:
            if (
                not str(voicemail_pin).isdigit()
                or len(str(voicemail_pin)) < 4
                or len(str(voicemail_pin)) > 6
            ):
                return send_json({"error": "Voicemail PIN must be 4-6 digits"}, 400), 400

        # Validate email format if provided
        if email and not Config.validate_email(email):
            return send_json({"error": "Invalid email format"}, 400), 400

        # Try to update in database first, fall back to config.yml
        if pbx_core.extension_db:
            # Update in database
            # NOTE: For production, use FIPS-compliant hashing via pbx.utils.encryption.FIPSEncryption.hash_password()
            # Currently storing plain password; system supports both plain
            # and hashed passwords
            password_hash = password if password else None
            success = pbx_core.extension_db.update(
                number=number,
                name=name,
                email=email,
                password_hash=password_hash,
                allow_external=allow_external,
                voicemail_pin=voicemail_pin,
                is_admin=is_admin,
            )
        else:
            # Fall back to config.yml
            success = pbx_core.config.update_extension(
                number, name, email, password, allow_external
            )

        if success:
            # Reload extensions
            pbx_core.extension_registry.reload()
            return send_json({"success": True, "message": "Extension updated successfully"}), 200
        else:
            return send_json({"error": "Failed to update extension"}, 500), 500
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@extensions_bp.route("/api/extensions/<number>", methods=["DELETE"])
@require_admin
def delete_extension(number: str) -> tuple[Response, int]:
    """Delete an extension."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        # Check if extension exists
        extension = pbx_core.extension_registry.get(number)
        if not extension:
            return send_json({"error": "Extension not found"}, 404), 404

        # Try to delete from database first, fall back to config.yml
        if pbx_core.extension_db:
            # Delete from database
            success = pbx_core.extension_db.delete(number)
        else:
            # Fall back to config.yml
            success = pbx_core.config.delete_extension(number)

        if success:
            # Reload extensions
            pbx_core.extension_registry.reload()
            return send_json({"success": True, "message": "Extension deleted successfully"}), 200
        else:
            return send_json({"error": "Failed to delete extension"}, 500), 500
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500
