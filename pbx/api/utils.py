"""Shared utilities for Flask API routes."""

import json
from datetime import date, datetime
from functools import wraps
from typing import Any, Optional

from flask import current_app, jsonify, request

from pbx.utils.logger import get_logger

logger = get_logger()


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj: object) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def get_pbx_core():
    """Get PBX core instance from Flask app config."""
    return current_app.config.get("PBX_CORE")


def send_json(data: Any, status: int = 200):
    """Send JSON response with DateTimeEncoder support."""
    response = current_app.response_class(
        response=json.dumps(data, cls=DateTimeEncoder),
        status=status,
        mimetype="application/json",
    )
    return response


def get_auth_token() -> Optional[str]:
    """Extract authentication token from request headers."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def verify_authentication() -> tuple[bool, Optional[dict]]:
    """Verify authentication token and return payload.

    Returns:
        Tuple of (is_authenticated, payload)
    """
    token = get_auth_token()
    if not token:
        return False, None

    from pbx.utils.session_token import get_session_token_manager

    token_manager = get_session_token_manager()
    return token_manager.verify_token(token)


def require_auth(f):
    """Decorator that requires authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        is_authenticated, payload = verify_authentication()
        if not is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        request.auth_payload = payload
        return f(*args, **kwargs)

    return decorated


def require_admin(f):
    """Decorator that requires admin privileges."""

    @wraps(f)
    def decorated(*args, **kwargs):
        is_authenticated, payload = verify_authentication()
        if not is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        if not payload.get("is_admin", False):
            return jsonify({"error": "Admin privileges required"}), 403
        request.auth_payload = payload
        return f(*args, **kwargs)

    return decorated


def get_request_body() -> dict:
    """Get request body as JSON dict."""
    return request.get_json(silent=True) or {}


def get_query_params() -> dict:
    """Get query parameters as a dict."""
    return request.args


def validate_limit_param(default: int = 50, max_value: int = 1000) -> Optional[int]:
    """Validate a 'limit' query parameter.

    Returns:
        Validated limit value or None with error response sent.
    """
    try:
        limit = int(request.args.get("limit", default))
        if limit < 1:
            return None
        if limit > max_value:
            return None
        return limit
    except ValueError:
        return None
