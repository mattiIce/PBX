"""API documentation Blueprint routes.

Serves Swagger UI for interactive API documentation and the
OpenAPI JSON specification.
"""

from flask import Blueprint, Response, jsonify

from pbx.api.openapi import get_openapi_spec

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
