"""Shared utilities for Flask API routes."""

import json
from collections.abc import Callable
from datetime import date, datetime
from functools import wraps
from pathlib import PurePath
from typing import Any

from flask import Response, current_app, jsonify, request

from pbx.utils.logger import get_logger

logger = get_logger()


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime and Path objects."""

    def default(self, obj: object) -> Any:
        if isinstance(obj, datetime | date):
            return obj.isoformat()
        if isinstance(obj, PurePath):
            return str(obj)
        return super().default(obj)


def get_pbx_core() -> Any:
    """Get PBX core instance from Flask app config."""
    return current_app.config.get("PBX_CORE")


def send_json(data: Any, status: int = 200) -> Response:
    """Send JSON response with DateTimeEncoder support."""
    response = current_app.response_class(
        response=json.dumps(data, cls=DateTimeEncoder),
        status=status,
        mimetype="application/json",
    )
    return response


def get_auth_token() -> str | None:
    """Extract authentication token from request headers."""
    auth_header: str = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return str(auth_header[7:])
    return None


def verify_authentication() -> tuple[bool, dict[str, Any] | None]:
    """Verify authentication token and return payload.

    Returns:
        tuple of (is_authenticated, payload)
    """
    token = get_auth_token()
    if not token:
        return False, None

    from pbx.utils.session_token import get_session_token_manager

    token_manager = get_session_token_manager()
    result: tuple[bool, dict[str, Any] | None] = token_manager.verify_token(token)
    return result


def require_auth(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that requires authentication."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        is_authenticated, payload = verify_authentication()
        if not is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        request.auth_payload = payload
        return f(*args, **kwargs)

    return decorated


def require_admin(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that requires admin privileges."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        is_authenticated, payload = verify_authentication()
        if not is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        if not payload or not payload.get("is_admin", False):
            return jsonify({"error": "Admin privileges required"}), 403
        request.auth_payload = payload
        return f(*args, **kwargs)

    return decorated


def get_request_body() -> dict[str, Any]:
    """Get request body as JSON dict."""
    return request.get_json(silent=True) or {}


def get_query_params() -> dict[str, Any]:
    """Get query parameters as a dict."""
    return dict(request.args)


def validate_limit_param(default: int = 50, max_value: int = 1000) -> int | None:
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
