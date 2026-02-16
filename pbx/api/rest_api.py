"""Legacy REST API module - DEPRECATED.

This module existed as a monolithic 11K-line HTTP handler using BaseHTTPRequestHandler.
It has been replaced by Flask blueprints in pbx.api.app.

This shim preserves backward compatibility for tests during migration.
All new code should use the Flask blueprint API (pbx.api.app).
"""

import warnings

warnings.warn(
    "pbx.api.rest_api is deprecated and will be removed. "
    "Use pbx.api.app (Flask Blueprints) instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export constants that tests depend on
MAC_ADDRESS_PLACEHOLDERS = ["{mac}", "{MAC}", "{Ma}"]


class PBXAPIHandler:
    """Deprecated stub - use Flask blueprints instead."""

    pbx_core: object | None = None


class PBXAPIServer:
    """Deprecated stub - use Flask app via create_app() instead."""
