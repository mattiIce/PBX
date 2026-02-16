"""Phone Book Blueprint routes.

Handles phone book CRUD operations, search, sync with Active Directory,
and export in multiple formats (Yealink XML, Cisco XML, JSON).
"""

from typing import Any

from flask import Blueprint, Response, request

from pbx.api.utils import (
    get_pbx_core,
    get_request_body,
    require_auth,
    send_json,
)
from pbx.utils.logger import get_logger

logger = get_logger()

phone_book_bp = Blueprint("phone_book", __name__, url_prefix="/api/phone-book")


def _get_phone_book() -> tuple[Any, Response | None]:
    """Get phone book instance or return error response."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "phone_book"):
        return None, send_json({"error": "Phone book feature not enabled"}, 500)

    if not pbx_core.phone_book or not pbx_core.phone_book.enabled:
        return None, send_json({"error": "Phone book feature not enabled"}, 500)

    return pbx_core.phone_book, None


@phone_book_bp.route("", methods=["GET"])
@require_auth
def handle_get_phone_book() -> Response:
    """Get all phone book entries."""
    phone_book, error = _get_phone_book()
    if error:
        return error

    try:
        entries = phone_book.get_all_entries()
        return send_json(entries)
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@phone_book_bp.route("", methods=["POST"])
@require_auth
def handle_add_phone_book_entry() -> Response:
    """Add or update a phone book entry."""
    phone_book, error = _get_phone_book()
    if error:
        return error

    try:
        data = get_request_body()
        extension = data.get("extension")
        name = data.get("name")

        if not extension or not name:
            return send_json({"error": "Extension and name are required"}, 400)

        success = phone_book.add_entry(
            extension=extension,
            name=name,
            department=data.get("department"),
            email=data.get("email"),
            mobile=data.get("mobile"),
            office_location=data.get("office_location"),
            ad_synced=data.get("ad_synced", False),
        )

        if success:
            return send_json(
                {"success": True, "message": f"Phone book entry added/updated: {extension}"}
            )
        return send_json({"error": "Failed to add phone book entry"}, 500)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)


@phone_book_bp.route("/sync", methods=["POST"])
@require_auth
def handle_sync_phone_book() -> Response:
    """Sync phone book from Active Directory."""
    phone_book, error = _get_phone_book()
    if error:
        return error

    pbx_core = get_pbx_core()
    if not hasattr(pbx_core, "ad_integration") or not pbx_core.ad_integration:
        return send_json({"error": "Active Directory integration not enabled"}, 500)

    try:
        synced_count = phone_book.sync_from_ad(pbx_core.ad_integration, pbx_core.extension_registry)

        return send_json(
            {
                "success": True,
                "message": "Phone book synced from Active Directory",
                "synced_count": synced_count,
            }
        )
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@phone_book_bp.route("/<extension>", methods=["DELETE"])
@require_auth
def handle_delete_phone_book_entry(extension: str) -> Response:
    """Delete a phone book entry."""
    phone_book, error = _get_phone_book()
    if error:
        return error

    try:
        success = phone_book.remove_entry(extension)

        if success:
            return send_json({"success": True, "message": f"Phone book entry deleted: {extension}"})
        return send_json({"error": "Failed to delete phone book entry"}, 500)
    except Exception as e:
        return send_json({"error": str(e)}, 500)


def _generate_xml_from_extensions(pbx_core: Any) -> str:
    """Generate phone book XML from extension registry (fallback)."""
    if not pbx_core or not hasattr(pbx_core, "extension_registry"):
        return '<?xml version="1.0" encoding="UTF-8"?><YealinkIPPhoneDirectory><Title>Directory</Title></YealinkIPPhoneDirectory>'

    extensions = pbx_core.extension_registry.get_all()

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append("<YealinkIPPhoneDirectory>")
    xml_lines.append("  <Title>Company Directory</Title>")

    for ext in sorted(extensions, key=lambda x: x.name):
        xml_lines.append("  <DirectoryEntry>")
        name = ext.name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        xml_lines.append(f"    <Name>{name}</Name>")
        xml_lines.append(f"    <Telephone>{ext.number}</Telephone>")
        xml_lines.append("  </DirectoryEntry>")

    xml_lines.append("</YealinkIPPhoneDirectory>")
    return "\n".join(xml_lines)


def _generate_cisco_xml_from_extensions(pbx_core: Any) -> str:
    """Generate Cisco phone book XML from extension registry (fallback)."""
    if not pbx_core or not hasattr(pbx_core, "extension_registry"):
        return '<?xml version="1.0" encoding="UTF-8"?><CiscoIPPhoneDirectory><Title>Directory</Title></CiscoIPPhoneDirectory>'

    extensions = pbx_core.extension_registry.get_all()

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append("<CiscoIPPhoneDirectory>")
    xml_lines.append("  <Title>Company Directory</Title>")
    xml_lines.append("  <Prompt>Select a contact</Prompt>")

    for ext in sorted(extensions, key=lambda x: x.name):
        xml_lines.append("  <DirectoryEntry>")
        name = ext.name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        xml_lines.append(f"    <Name>{name}</Name>")
        xml_lines.append(f"    <Telephone>{ext.number}</Telephone>")
        xml_lines.append("  </DirectoryEntry>")

    xml_lines.append("</CiscoIPPhoneDirectory>")
    return "\n".join(xml_lines)


@phone_book_bp.route("/export/xml", methods=["GET"])
@require_auth
def handle_export_phone_book_xml() -> Response:
    """Export phone book as XML (Yealink format)."""
    try:
        pbx_core = get_pbx_core()
        if (
            pbx_core
            and hasattr(pbx_core, "phone_book")
            and pbx_core.phone_book
            and pbx_core.phone_book.enabled
        ):
            xml_content = pbx_core.phone_book.export_xml()
        else:
            xml_content = _generate_xml_from_extensions(pbx_core)

        return Response(xml_content, status=200, mimetype="application/xml")
    except Exception as e:
        logger.error(f"Error exporting phone book XML: {e}")
        return send_json({"error": str(e)}, 500)


@phone_book_bp.route("/export/cisco-xml", methods=["GET"])
@require_auth
def handle_export_phone_book_cisco_xml() -> Response:
    """Export phone book as Cisco XML format."""
    try:
        pbx_core = get_pbx_core()
        if (
            pbx_core
            and hasattr(pbx_core, "phone_book")
            and pbx_core.phone_book
            and pbx_core.phone_book.enabled
        ):
            xml_content = pbx_core.phone_book.export_cisco_xml()
        else:
            xml_content = _generate_cisco_xml_from_extensions(pbx_core)

        return Response(xml_content, status=200, mimetype="application/xml")
    except Exception as e:
        logger.error(f"Error exporting Cisco phone book XML: {e}")
        return send_json({"error": str(e)}, 500)


@phone_book_bp.route("/export/json", methods=["GET"])
@require_auth
def handle_export_phone_book_json() -> Response:
    """Export phone book as JSON."""
    phone_book, error = _get_phone_book()
    if error:
        return error

    try:
        json_content = phone_book.export_json()
        return Response(json_content, status=200, mimetype="application/json")
    except Exception as e:
        return send_json({"error": str(e)}, 500)


@phone_book_bp.route("/search", methods=["GET"])
@require_auth
def handle_search_phone_book() -> Response:
    """Search phone book entries."""
    phone_book, error = _get_phone_book()
    if error:
        return error

    try:
        query = request.args.get("q", "")

        if not query:
            return send_json({"error": 'Query parameter "q" is required'}, 400)

        results = phone_book.search(query)
        return send_json(results)
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500)
