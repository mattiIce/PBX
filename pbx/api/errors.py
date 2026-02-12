"""Standardized error handling for Flask API."""

from flask import jsonify

from pbx.utils.logger import get_logger

logger = get_logger()


class APIError(Exception):
    """Base API error with status code."""

    def __init__(self, message: str, status_code: int = 400, code: str = "BAD_REQUEST"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class NotFoundError(APIError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404, "NOT_FOUND")


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401, "UNAUTHORIZED")


class ForbiddenError(APIError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 403, "FORBIDDEN")


class ValidationError(APIError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, 422, "VALIDATION_ERROR")


def register_error_handlers(app):
    """Register Flask error handlers for standardized error responses."""

    @app.errorhandler(APIError)
    def handle_api_error(error):
        return (
            jsonify(
                {
                    "error": {
                        "code": error.code,
                        "message": error.message,
                        "status": error.status_code,
                    }
                }
            ),
            error.status_code,
        )

    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def handle_405(error):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def handle_500(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
