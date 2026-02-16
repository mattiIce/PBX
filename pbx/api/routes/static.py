"""Static file serving Blueprint routes.

Handles serving the admin panel static files and the /admin redirect.
Uses current_app.config['ADMIN_DIR'] for the admin directory path.
"""

import mimetypes
from pathlib import Path

from flask import Blueprint, Response, current_app, redirect

from pbx.api.utils import send_json
from pbx.utils.logger import get_logger

logger = get_logger()

static_bp = Blueprint("static_files", __name__)


@static_bp.route("/admin")
def handle_admin_redirect() -> Response:
    """Redirect to admin panel."""
    return redirect("/admin/index.html", code=302)


@static_bp.route("/admin/<path:path>")
def handle_static_file(path: str) -> Response:
    """Serve static files from admin directory.

    Includes directory traversal protection to ensure paths stay
    within the admin directory.
    """
    try:
        admin_dir = current_app.config["ADMIN_DIR"]
        full_path = Path(admin_dir) / path

        # Prevent directory traversal attacks - ensure path stays within
        # admin directory
        real_admin_dir = str(Path(admin_dir).resolve())
        real_full_path = str(Path(full_path).resolve())

        if not real_full_path.startswith(real_admin_dir):
            return send_json({"error": "Access denied"}, 403)

        if not Path(full_path).exists() or not Path(full_path).is_file():
            return send_json({"error": "File not found"}, 404)

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(full_path))
        if not content_type:
            content_type = "application/octet-stream"

        # Read and serve file
        with open(full_path, "rb") as f:
            content = f.read()

        response = current_app.response_class(
            response=content,
            status=200,
            mimetype=content_type,
        )
        return response
    except KeyError:
        logger.error("ADMIN_DIR not configured in Flask app config")
        return send_json({"error": "Admin directory not configured"}, 500)
    except (KeyError, OSError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)
