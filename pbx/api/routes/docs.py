"""API documentation Blueprint routes.

Serves Swagger UI for interactive API documentation and the
OpenAPI JSON specification, as well as architecture diagrams.
"""

from pathlib import Path

from flask import Blueprint, Response, jsonify

from pbx.api.openapi import get_openapi_spec
from pbx.api.utils import send_json
from pbx.utils.logger import get_logger

logger = get_logger()

docs_bp = Blueprint("docs", __name__)


@docs_bp.route("/api/docs/openapi.json")
def openapi_json() -> Response:
    """Return the OpenAPI specification as JSON."""
    spec = get_openapi_spec()
    return jsonify(spec)


@docs_bp.route("/api/docs")
def swagger_ui() -> Response:
    """Serve a Swagger UI page using the CDN-hosted swagger-ui-dist."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PBX API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <style>
        html { box-sizing: border-box; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin: 0; background: #fafafa; }
        .topbar { display: none; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({
            url: '/api/docs/openapi.json',
            dom_id: '#swagger-ui',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            layout: 'BaseLayout',
            deepLinking: true,
            defaultModelsExpandDepth: 1,
            defaultModelExpandDepth: 1,
        });
    </script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


@docs_bp.route("/api/docs/architecture")
def architecture_diagrams() -> Response:
    """Serve the architecture diagrams HTML file.

    Returns:
        Rendered HTML page with interactive architecture diagrams.
        Returns 404 if the file is not found.
    """
    try:
        docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
        diagram_file = docs_dir / "ARCHITECTURE_DIAGRAMS.html"

        if not diagram_file.exists() or not diagram_file.is_file():
            return send_json({"error": "Architecture diagrams not found"}, 404)

        with diagram_file.open("r", encoding="utf-8") as f:
            content = f.read()

        return Response(content, mimetype="text/html")
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error serving architecture diagrams: {e}")
        return send_json({"error": "Failed to serve architecture diagrams"}, 500)
