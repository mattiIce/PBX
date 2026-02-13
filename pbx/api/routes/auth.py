"""Authentication Blueprint routes.

Handles login and logout for the PBX API. Login supports both regular
extension authentication (via voicemail PIN) and the special license
admin extension.
"""

import secrets
import traceback

from flask import Blueprint, Response, request

from pbx.api.utils import get_pbx_core, get_request_body, send_json
from pbx.utils.logger import get_logger

logger = get_logger()

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def handle_login() -> Response:
    """Authenticate extension and return session token."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500)

    try:
        body = get_request_body()
        extension_number = body.get("extension")
        password = body.get("password")

        if not extension_number or not password:
            return send_json({"error": "Extension and password required"}, 400)

        # Check if this is the special license admin extension (9322)
        from pbx.utils.license_admin import (
            LICENSE_ADMIN_USERNAME,
            is_license_admin_extension,
            verify_license_admin_credentials,
        )

        if is_license_admin_extension(extension_number):
            # Handle license admin authentication separately
            # For license admin, the password is the PIN
            # Username defaults to LICENSE_ADMIN_USERNAME if not provided in request
            username = body.get("username", LICENSE_ADMIN_USERNAME)
            if verify_license_admin_credentials(extension_number, username, password):
                # Generate session token for license admin
                from pbx.utils.session_token import get_session_token_manager

                token_manager = get_session_token_manager()
                token = token_manager.generate_token(
                    extension=extension_number,
                    is_admin=True,  # License admin has admin privileges
                    name="License Administrator",
                    email="",
                )

                return send_json(
                    {
                        "success": True,
                        "token": token,
                        "extension": extension_number,
                        "is_admin": True,
                        "name": "License Administrator",
                        "email": "",
                    }
                )
            else:
                return send_json({"error": "Invalid credentials"}, 401)

        # Get extension from database
        if not pbx_core.extension_db:
            return send_json({"error": "Database not available"}, 500)

        ext = pbx_core.extension_db.get(extension_number)
        if not ext:
            return send_json({"error": "Invalid credentials"}, 401)

        # Verify password using voicemail PIN
        # For Phase 3 authentication, the login password is the user's voicemail PIN
        # This provides a single credential for users to remember (their voicemail PIN)
        voicemail_pin_hash = ext.get("voicemail_pin_hash", "")

        # Check if voicemail PIN is hashed (contains salt) or plain text
        # For backwards compatibility, we support both
        from pbx.utils.encryption import get_encryption

        fips_mode = pbx_core.config.get("security.fips_mode", False)
        encryption = get_encryption(fips_mode)

        voicemail_pin_salt = ext.get("voicemail_pin_salt")
        if voicemail_pin_salt:
            # Voicemail PIN is hashed - verify using encryption
            if not encryption.verify_password(password, voicemail_pin_hash, voicemail_pin_salt):
                return send_json({"error": "Invalid credentials"}, 401)
        else:
            # Voicemail PIN is plain text (legacy) or not set
            # If no voicemail PIN is configured, deny access for security
            if not voicemail_pin_hash or voicemail_pin_hash == "":
                return send_json({"error": "Invalid credentials"}, 401)

            # Ensure both values are strings before comparison
            password_str = password if isinstance(password, str) else password.decode("utf-8")
            voicemail_pin_str = (
                voicemail_pin_hash
                if isinstance(voicemail_pin_hash, str)
                else str(voicemail_pin_hash)
            )
            if not secrets.compare_digest(
                password_str.encode("utf-8"), voicemail_pin_str.encode("utf-8")
            ):
                return send_json({"error": "Invalid credentials"}, 401)

        # Generate session token
        from pbx.utils.session_token import get_session_token_manager

        token_manager = get_session_token_manager()
        token = token_manager.generate_token(
            extension=extension_number,
            is_admin=ext.get("is_admin", False),
            name=ext.get("name"),
            email=ext.get("email"),
        )

        return send_json(
            {
                "success": True,
                "token": token,
                "extension": extension_number,
                "is_admin": ext.get("is_admin", False),
                "name": ext.get("name", "User"),
                "email": ext.get("email", ""),
            }
        )

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Login error: {e}")
        logger.error(traceback.format_exc())
        return send_json({"error": "Authentication failed"}, 500)


@auth_bp.route("/logout", methods=["POST"])
def handle_logout() -> Response:
    """Handle logout (client-side token removal).

    Logout is primarily handled client-side by removing the token.
    This endpoint is here for completeness and future server-side
    token invalidation.
    """
    return send_json({"success": True, "message": "Logged out successfully"})
