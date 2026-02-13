"""API versioning compatibility Blueprint.

Provides /api/v1/* routes that forward to the existing /api/* handlers,
allowing gradual migration to versioned API endpoints.
"""

from flask import Blueprint, Response, redirect, request

compat_bp = Blueprint("compat", __name__)


@compat_bp.route("/api/v1/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def api_v1_proxy(path: str) -> Response:
    """Forward /api/v1/* requests to /api/* routes.

    This enables clients to start using versioned endpoints immediately.
    Once all clients migrate, the unversioned routes can be deprecated.
    """
    # Reconstruct the target URL without the version prefix
    target = f"/api/{path}"
    if request.query_string:
        target += f"?{request.query_string.decode()}"

    # Use internal redirect (307 preserves method and body)
    return redirect(target, code=307)
