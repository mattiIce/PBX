"""Voicemail Blueprint routes for PBX API.

Handles voicemail message management, voicemail box operations,
greeting management, and voicemail export functionality.
"""

import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from flask import Blueprint, Response, current_app, request

from pbx.api.utils import (
    get_pbx_core,
    get_request_body,
    require_auth,
    send_json,
)
from pbx.utils.logger import get_logger

logger = get_logger()

voicemail_bp = Blueprint("voicemail", __name__)


# ========== Voicemail Message Routes ==========


@voicemail_bp.route("/api/voicemail/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_voicemail(subpath: str) -> Response:
    """Get voicemail messages for an extension."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail not enabled"}, 500)

    try:
        # Parse subpath: {extension} or {extension}/{message_id}
        parts = subpath.split("/")
        if len(parts) < 1:
            return send_json({"error": "Invalid path"}, 400)

        extension = parts[0]

        # Get mailbox
        mailbox = pbx_core.voicemail_system.get_mailbox(extension)

        if len(parts) == 1:
            # list all messages
            messages = mailbox.get_messages()
            data = []
            for msg in messages:
                data.append(
                    {
                        "id": msg["id"],
                        "caller_id": msg["caller_id"],
                        "timestamp": msg["timestamp"].isoformat() if msg["timestamp"] else None,
                        "listened": msg["listened"],
                        "duration": msg["duration"],
                    }
                )
            return send_json({"messages": data})
        if len(parts) == 2:
            # Get specific message or download audio
            message_id = parts[1]

            # Find message
            message = None
            for msg in mailbox.get_messages():
                if msg["id"] == message_id:
                    message = msg
                    break

            if not message:
                return send_json({"error": "Message not found"}, 404)

            # Check if request is for metadata only (via query parameter)
            metadata_param = request.args.get("metadata", "false")
            if metadata_param in ["true", "1"]:
                # Return message metadata as JSON
                return send_json(
                    {
                        "id": message["id"],
                        "caller_id": message["caller_id"],
                        "timestamp": (
                            message["timestamp"].isoformat() if message["timestamp"] else None
                        ),
                        "listened": message["listened"],
                        "duration": message["duration"],
                        "file_path": message["file_path"],
                    }
                )
            # Default: Serve audio file for playback in admin panel
            if Path(message["file_path"]).exists():
                with open(message["file_path"], "rb") as f:
                    audio_data = f.read()
                response = current_app.response_class(
                    response=audio_data,
                    status=200,
                    mimetype="audio/wav",
                )
                return response
            return send_json({"error": "Audio file not found"}, 404)
    except (KeyError, OSError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@voicemail_bp.route("/api/voicemail/<path:subpath>", methods=["PUT"])
@require_auth
def handle_update_voicemail(subpath: str) -> Response:
    """Update voicemail settings (mark as read, update PIN)."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail not enabled"}, 500)

    try:
        # Parse subpath: {extension}/pin or {extension}/{message_id}/mark-read
        parts = subpath.split("/")
        if len(parts) < 1:
            return send_json({"error": "Invalid path"}, 400)

        extension = parts[0]
        body = get_request_body()

        # Get mailbox
        mailbox = pbx_core.voicemail_system.get_mailbox(extension)

        if len(parts) == 2 and parts[1] == "pin":
            # Update PIN
            pin = body.get("pin")
            if not pin:
                return send_json({"error": "PIN required"}, 400)

            if mailbox.set_pin(pin):
                # Also update in config
                pbx_core.config.update_voicemail_pin(extension, pin)
                return send_json({"success": True, "message": "PIN updated successfully"})
            return send_json({"error": "Invalid PIN format. Must be 4 digits."}, 400)
        if len(parts) == 3 and parts[2] == "mark-read":
            # Mark message as read
            message_id = parts[1]
            mailbox.mark_listened(message_id)
            return send_json({"success": True, "message": "Message marked as read"})
        return send_json({"error": "Invalid operation"}, 400)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@voicemail_bp.route("/api/voicemail/<path:subpath>", methods=["DELETE"])
@require_auth
def handle_delete_voicemail(subpath: str) -> Response:
    """Delete voicemail message."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail not enabled"}, 500)

    try:
        # Parse subpath: {extension}/{message_id}
        parts = subpath.split("/")
        if len(parts) != 2:
            return send_json({"error": "Invalid path"}, 400)

        extension = parts[0]
        message_id = parts[1]

        # Get mailbox
        mailbox = pbx_core.voicemail_system.get_mailbox(extension)

        # Delete message
        if mailbox.delete_message(message_id):
            return send_json({"success": True, "message": "Message deleted successfully"})
        return send_json({"error": "Message not found"}, 404)
    except Exception as e:
        return send_json({"error": str(e)}, 500)


# ========== Voicemail Box Routes ==========


@voicemail_bp.route("/api/voicemail-boxes", methods=["GET"])
@require_auth
def handle_get_voicemail_boxes() -> Response:
    """Get list of all voicemail boxes."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail system not available"}, 500)

    try:
        vm_system = pbx_core.voicemail_system
        boxes = []

        for extension, mailbox in vm_system.mailboxes.items():
            messages = mailbox.get_messages(unread_only=False)
            unread_count = len(mailbox.get_messages(unread_only=True))

            boxes.append(
                {
                    "extension": extension,
                    "total_messages": len(messages),
                    "unread_messages": unread_count,
                    "has_custom_greeting": mailbox.has_custom_greeting(),
                    "storage_path": mailbox.storage_path,
                }
            )

        return send_json({"voicemail_boxes": boxes})
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@voicemail_bp.route("/api/voicemail-boxes/<path:subpath>", methods=["GET"])
@require_auth
def handle_get_voicemail_box(subpath: str) -> Response:
    """Handle GET requests for voicemail boxes.

    Routes:
    - /api/voicemail-boxes/{box_id} -> box details
    - /api/voicemail-boxes/{box_id}/greeting -> get greeting audio
    """
    parts = subpath.split("/")

    if len(parts) == 2 and parts[1] == "greeting":
        return _handle_get_voicemail_greeting(subpath)
    if len(parts) == 2 and parts[1] == "export":
        # GET with /export suffix - redirect to POST handler conceptually,
        # but return method not allowed
        return send_json({"error": "Use POST method for export"}, 405)
    return _handle_get_voicemail_box_details(subpath)


def _handle_get_voicemail_box_details(subpath: str) -> Response:
    """Get details of a specific voicemail box."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail system not available"}, 500)

    try:
        # Extract extension from subpath
        parts = subpath.split("/")
        extension = parts[0] if len(parts) > 0 else None

        if not extension:
            return send_json({"error": "Invalid path"}, 400)

        vm_system = pbx_core.voicemail_system
        mailbox = vm_system.get_mailbox(extension)
        messages = mailbox.get_messages(unread_only=False)

        details = {
            "extension": extension,
            "total_messages": len(messages),
            "unread_messages": len(mailbox.get_messages(unread_only=True)),
            "has_custom_greeting": mailbox.has_custom_greeting(),
            "storage_path": mailbox.storage_path,
            "messages": [],
        }

        for msg in messages:
            details["messages"].append(
                {
                    "id": msg["id"],
                    "caller_id": msg["caller_id"],
                    "timestamp": (
                        msg["timestamp"].isoformat()
                        if hasattr(msg["timestamp"], "isoformat")
                        else str(msg["timestamp"])
                    ),
                    "listened": msg["listened"],
                    "duration": msg.get("duration"),
                    "file_path": msg["file_path"],
                }
            )

        return send_json(details)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


def _handle_get_voicemail_greeting(subpath: str) -> Response:
    """Get custom voicemail greeting."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail system not available"}, 500)

    try:
        # Extract extension from subpath
        parts = subpath.split("/")
        extension = parts[0] if len(parts) > 0 else None

        if not extension:
            return send_json({"error": "Invalid path"}, 400)

        vm_system = pbx_core.voicemail_system
        mailbox = vm_system.get_mailbox(extension)
        greeting_path = mailbox.get_greeting_path()

        if not greeting_path or not Path(greeting_path).exists():
            return send_json({"error": "No custom greeting found"}, 404)

        # Serve greeting file
        with open(greeting_path, "rb") as f:
            greeting_data = f.read()

        response = current_app.response_class(
            response=greeting_data,
            status=200,
            mimetype="audio/wav",
        )
        response.headers["Content-Disposition"] = f'attachment; filename="greeting_{extension}.wav"'
        response.headers["Content-Length"] = str(len(greeting_data))
        return response

    except (KeyError, OSError, TypeError, ValueError) as e:
        logger.error(f"Error getting voicemail greeting: {e}")
        return send_json({"error": str(e)}, 500)


@voicemail_bp.route("/api/voicemail-boxes/<path:subpath>/export", methods=["POST"])
@require_auth
def handle_export_voicemail_box(subpath: str) -> Response:
    """Export all voicemails from a mailbox as a ZIP file."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail system not available"}, 500)

    try:
        extension = subpath.split("/", maxsplit=1)[0] if subpath else None

        if not extension:
            return send_json({"error": "Invalid path"}, 400)

        vm_system = pbx_core.voicemail_system
        mailbox = vm_system.get_mailbox(extension)
        messages = mailbox.get_messages(unread_only=False)

        if not messages:
            return send_json({"error": "No messages to export"}, 404)

        # Create temporary directory for ZIP creation
        temp_dir = tempfile.mkdtemp()
        zip_filename = f"voicemail_{extension}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = Path(temp_dir) / zip_filename

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add a manifest file with message details
                manifest_lines = ["Voicemail Export Manifest\n"]
                manifest_lines.append(f"Extension: {extension}\n")
                manifest_lines.append(f"Export Date: {datetime.now(UTC).isoformat()}\n")
                manifest_lines.append(f"Total Messages: {len(messages)}\n\n")
                manifest_lines.append("Message Details:\n")
                manifest_lines.append("-" * 80 + "\n")

                for msg in messages:
                    # Add audio file to ZIP
                    if Path(msg["file_path"]).exists():
                        arcname = Path(msg["file_path"]).name
                        zipf.write(msg["file_path"], arcname)

                        # Add to manifest
                        manifest_lines.append(f"\nFile: {arcname}\n")
                        manifest_lines.append(f"Caller ID: {msg['caller_id']}\n")
                        manifest_lines.append(f"Timestamp: {msg['timestamp']}\n")
                        manifest_lines.append(f"Duration: {msg.get('duration', 'Unknown')}s\n")
                        manifest_lines.append(
                            f"Status: {'Read' if msg['listened'] else 'Unread'}\n"
                        )

                # Add manifest to ZIP
                zipf.writestr("MANIFEST.txt", "".join(manifest_lines))

            # Read ZIP file content
            with open(zip_path, "rb") as f:
                zip_content = f.read()

            # Send ZIP file as response
            response = current_app.response_class(
                response=zip_content,
                status=200,
                mimetype="application/zip",
            )
            response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
            response.headers["Content-Length"] = str(len(zip_content))
            return response

        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    except (KeyError, OSError, TypeError, ValueError) as e:
        logger.error(f"Error exporting voicemail box: {e}")
        return send_json({"error": str(e)}, 500)


@voicemail_bp.route("/api/voicemail-boxes/<path:subpath>/greeting", methods=["PUT"])
@require_auth
def handle_upload_voicemail_greeting(subpath: str) -> Response:
    """Upload/update custom voicemail greeting."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail system not available"}, 500)

    try:
        # Extract extension from subpath
        extension = subpath.split("/", maxsplit=1)[0] if subpath else None

        if not extension:
            return send_json({"error": "Invalid path"}, 400)

        # Get audio data from request body
        audio_data = request.get_data()
        if not audio_data:
            return send_json({"error": "No audio data provided"}, 400)

        vm_system = pbx_core.voicemail_system
        mailbox = vm_system.get_mailbox(extension)

        if mailbox.save_greeting(audio_data):
            return send_json(
                {
                    "success": True,
                    "message": f"Custom greeting uploaded for extension {extension}",
                }
            )
        return send_json({"error": "Failed to save greeting"}, 500)

    except Exception as e:
        return send_json({"error": str(e)}, 500)


@voicemail_bp.route("/api/voicemail-boxes/<path:subpath>/clear", methods=["DELETE"])
@require_auth
def handle_clear_voicemail_box(subpath: str) -> Response:
    """Clear all messages from a voicemail box."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail system not available"}, 500)

    try:
        extension = subpath.split("/", maxsplit=1)[0] if subpath else None

        if not extension:
            return send_json({"error": "Invalid path"}, 400)

        vm_system = pbx_core.voicemail_system
        mailbox = vm_system.get_mailbox(extension)
        messages = mailbox.get_messages(unread_only=False)

        deleted_count = 0
        for msg in messages[:]:  # Create a copy to iterate over
            if mailbox.delete_message(msg["id"]):
                deleted_count += 1

        return send_json(
            {
                "success": True,
                "message": f"Cleared {deleted_count} voicemail message(s) from extension {extension}",
                "deleted_count": deleted_count,
            }
        )
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@voicemail_bp.route("/api/voicemail-boxes/<path:subpath>/greeting", methods=["DELETE"])
@require_auth
def handle_delete_voicemail_greeting(subpath: str) -> Response:
    """Delete custom voicemail greeting."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "voicemail_system"):
        return send_json({"error": "Voicemail system not available"}, 500)

    try:
        # Extract extension from subpath
        extension = subpath.split("/", maxsplit=1)[0] if subpath else None

        if not extension:
            return send_json({"error": "Invalid path"}, 400)

        vm_system = pbx_core.voicemail_system
        mailbox = vm_system.get_mailbox(extension)

        if mailbox.delete_greeting():
            return send_json(
                {
                    "success": True,
                    "message": f"Custom greeting deleted for extension {extension}",
                }
            )
        return send_json({"error": "No custom greeting found"}, 404)

    except Exception as e:
        return send_json({"error": str(e)}, 500)
