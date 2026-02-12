"""Webhooks Blueprint routes.

Handles webhook subscription management including listing,
adding, and removing webhook subscriptions.
"""

from urllib.parse import unquote

from flask import Blueprint

from pbx.api.utils import (
    get_pbx_core,
    get_request_body,
    require_auth,
    send_json,
)
from pbx.utils.logger import get_logger

logger = get_logger()

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")


def _get_webhook_system():
    """Get webhook system instance or return error response."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "webhook_system"):
        return None, send_json({"error": "Webhook system not available"}, 500)

    return pbx_core.webhook_system, None


@webhooks_bp.route("", methods=["GET"])
@require_auth
def handle_get_webhooks():
    """Get all webhook subscriptions."""
    webhook_system, error = _get_webhook_system()
    if error:
        return error

    try:
        subscriptions = webhook_system.get_subscriptions()
        return send_json(subscriptions)
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@webhooks_bp.route("", methods=["POST"])
@require_auth
def handle_add_webhook():
    """Add a webhook subscription."""
    webhook_system, error = _get_webhook_system()
    if error:
        return error

    try:
        data = get_request_body()
        url = data.get("url")
        events = data.get("events", ["*"])
        secret = data.get("secret")
        headers = data.get("headers")

        if not url:
            return send_json({"error": "URL is required"}, 400)

        subscription = webhook_system.add_subscription(
            url=url, events=events, secret=secret, headers=headers
        )

        return send_json(
            {
                "success": True,
                "message": f"Webhook subscription added: {url}",
                "subscription": {
                    "url": subscription.url,
                    "events": subscription.events,
                    "enabled": subscription.enabled,
                },
            }
        )
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@webhooks_bp.route("/<path:url>", methods=["DELETE"])
@require_auth
def handle_delete_webhook(url):
    """Delete a webhook subscription.

    The URL is passed as a path parameter. Since webhook URLs contain
    slashes, the <path:url> converter is used to capture the full URL.
    The URL is decoded from percent-encoding before use.
    """
    webhook_system, error = _get_webhook_system()
    if error:
        return error

    # Validate the URL parameter
    decoded_url = unquote(url)
    if not decoded_url or not (decoded_url.startswith("http://") or decoded_url.startswith("https://")):
        return send_json({"error": "Invalid webhook URL"}, 400)

    try:
        success = webhook_system.remove_subscription(decoded_url)

        if success:
            return send_json(
                {"success": True, "message": f"Webhook subscription deleted: {decoded_url}"}
            )
        else:
            return send_json({"error": "Webhook subscription not found"}, 404)
    except Exception as e:
        return send_json({"error": str(e)}, 500)
