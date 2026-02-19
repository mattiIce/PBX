"""Flask application factory for PBX API."""

from pathlib import Path

from flask import Flask, Response, request

from pbx.api.errors import register_error_handlers
from pbx.utils.logger import get_logger

logger = get_logger()

ADMIN_DIR = str(Path(__file__).resolve().parent.parent.parent / "admin")


def create_app(pbx_core: object | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        pbx_core: PBXCore instance to make available to routes.

    Returns:
        Configured Flask application.
    """
    app = Flask(__name__, static_folder=None)
    app.config["PBX_CORE"] = pbx_core
    app.config["ADMIN_DIR"] = ADMIN_DIR

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        # CORS: restrict to configured origins (default: same-origin only)
        cors_origins: list[str] = []
        if pbx_core:
            config = getattr(pbx_core, "config", None)
            if config:
                cors_origins = config.get("api.cors_allowed_origins", []) or []

        origin = request.headers.get("Origin", "")
        if cors_origins and origin in cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"

        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=()"

        # Build CSP with configurable connect-src
        connect_sources = ["'self'"]
        if pbx_core:
            config = getattr(pbx_core, "config", None)
            if config:
                extra_sources = config.get("api.csp_connect_sources", []) or []
                connect_sources.extend(extra_sources)
        connect_src = " ".join(connect_sources)

        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            f"connect-src {connect_src} https://cdn.jsdelivr.net;"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

    register_error_handlers(app)
    _register_blueprints(app)

    return app


def _register_blueprints(app: Flask) -> None:
    """Register all route Blueprints."""
    from pbx.api.routes.auth import auth_bp
    from pbx.api.routes.calls import calls_bp
    from pbx.api.routes.compat import compat_bp
    from pbx.api.routes.config import config_bp
    from pbx.api.routes.docs import docs_bp
    from pbx.api.routes.emergency import emergency_bp
    from pbx.api.routes.extensions import extensions_bp
    from pbx.api.routes.features import features_bp
    from pbx.api.routes.framework import framework_bp
    from pbx.api.routes.health import health_bp
    from pbx.api.routes.integrations import integrations_bp
    from pbx.api.routes.license import license_bp
    from pbx.api.routes.paging import paging_bp
    from pbx.api.routes.phone_book import phone_book_bp
    from pbx.api.routes.phones import phones_bp
    from pbx.api.routes.provisioning import provisioning_bp
    from pbx.api.routes.qos import qos_bp
    from pbx.api.routes.security import security_bp
    from pbx.api.routes.static import static_bp
    from pbx.api.routes.voicemail import voicemail_bp
    from pbx.api.routes.webhooks import webhooks_bp
    from pbx.api.routes.webrtc import webrtc_bp

    blueprints = [
        health_bp,
        auth_bp,
        extensions_bp,
        calls_bp,
        provisioning_bp,
        phones_bp,
        config_bp,
        voicemail_bp,
        webrtc_bp,
        integrations_bp,
        phone_book_bp,
        paging_bp,
        webhooks_bp,
        emergency_bp,
        security_bp,
        qos_bp,
        features_bp,
        framework_bp,
        static_bp,
        license_bp,
        compat_bp,
        docs_bp,
    ]

    for bp in blueprints:
        app.register_blueprint(bp)
        logger.debug("Registered blueprint: %s", bp.name)
