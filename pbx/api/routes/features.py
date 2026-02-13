"""Features Blueprint routes for the PBX system.

Covers Auto-Attendant, SIP Trunks, LCR, FMFM, Time Routing,
Recording Retention, Fraud Detection, Callback Queue, Mobile Push,
Recording Announcements, and Skills-Based Routing.
"""

import json
import os
import re

from typing import Any

from flask import Blueprint, Response, jsonify, request, current_app

from pbx.api.utils import (
    get_pbx_core,
    send_json,
    verify_authentication,
    require_auth,
    require_admin,
    get_request_body,
    DateTimeEncoder,
)
from pbx.utils.logger import get_logger

logger = get_logger()

features_bp = Blueprint("features", __name__)


# ==========================================================================
# Auto-Attendant Routes
# ==========================================================================


@features_bp.route("/api/auto-attendant/config", methods=["GET"])
@require_auth
def get_auto_attendant_config() -> tuple[Response, int]:
    """Get auto attendant configuration."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant
        config = {
            "enabled": aa.enabled,
            "extension": aa.extension,
            "timeout": aa.timeout,
            "max_retries": aa.max_retries,
            "audio_path": aa.audio_path,
        }
        return send_json(config), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/config", methods=["PUT"])
@require_auth
def update_auto_attendant_config() -> tuple[Response, int]:
    """Update auto attendant configuration."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        data = get_request_body()
        aa = pbx_core.auto_attendant

        # Update configuration using the new update_config method
        config_updates = {}
        if "enabled" in data:
            config_updates["enabled"] = bool(data["enabled"])
        if "extension" in data:
            config_updates["extension"] = str(data["extension"])
        if "timeout" in data:
            config_updates["timeout"] = int(data["timeout"])
        if "max_retries" in data:
            config_updates["max_retries"] = int(data["max_retries"])

        # Apply updates and persist to database
        if config_updates:
            aa.update_config(**config_updates)
            config_changed = True
        else:
            config_changed = False

        # Check if prompts configuration was updated
        prompts_updated = "prompts" in data

        # Trigger voice regeneration if prompts or menu options changed
        if prompts_updated or config_changed:
            try:
                _regenerate_voice_prompts(pbx_core, data.get("prompts", {}))
            except Exception as e:
                logger.warning(f"Failed to regenerate voice prompts: {e}")

        return send_json(
            {
                "success": True,
                "message": "Auto attendant configuration updated and persisted to database",
            }
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menu-options", methods=["GET"])
@require_auth
def get_auto_attendant_menu_options() -> tuple[Response, int]:
    """Get auto attendant menu options."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant
        options = []
        for digit, option in aa.menu_options.items():
            options.append(
                {
                    "digit": digit,
                    "destination": option["destination"],
                    "description": option["description"],
                }
            )
        return send_json({"menu_options": options}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menu-options", methods=["POST"])
@require_auth
def add_auto_attendant_menu_option() -> tuple[Response, int]:
    """Add auto attendant menu option."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        data = get_request_body()
        digit = str(data.get("digit"))
        destination = data.get("destination")
        description = data.get("description", "")

        if not digit or not destination:
            return send_json({"error": "digit and destination are required"}, 400), 400

        aa = pbx_core.auto_attendant
        # Use the new add_menu_option method which persists to database
        aa.add_menu_option(digit, destination, description)

        # Trigger voice regeneration after menu option addition
        try:
            _regenerate_voice_prompts(pbx_core, {})
        except Exception as e:
            logger.warning(f"Failed to regenerate voice prompts: {e}")

        return send_json(
            {"success": True, "message": f"Menu option {digit} added and persisted to database"}
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menu-options/<path:subpath>", methods=["PUT"])
@require_auth
def update_auto_attendant_menu_option(subpath: str) -> tuple[Response, int]:
    """Update auto attendant menu option."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        digit = subpath.split("/")[-1]
        data = get_request_body()

        aa = pbx_core.auto_attendant
        if digit not in aa.menu_options:
            return send_json({"error": f"Menu option {digit} not found"}, 404), 404

        # Get current values
        destination = aa.menu_options[digit]["destination"]
        description = aa.menu_options[digit]["description"]

        # Update with new values if provided
        if "destination" in data:
            destination = data["destination"]
        if "description" in data:
            description = data["description"]

        # Use add_menu_option which will update and persist to database
        aa.add_menu_option(digit, destination, description)

        # Trigger voice regeneration after menu option update
        try:
            _regenerate_voice_prompts(pbx_core, {})
        except Exception as e:
            logger.warning(f"Failed to regenerate voice prompts: {e}")

        return send_json(
            {
                "success": True,
                "message": f"Menu option {digit} updated and persisted to database",
            }
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menu-options/<digit>", methods=["DELETE"])
@require_auth
def delete_auto_attendant_menu_option(digit: str) -> tuple[Response, int]:
    """Delete auto attendant menu option."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant
        if digit in aa.menu_options:
            # Use the new remove_menu_option method which deletes from database
            aa.remove_menu_option(digit)

            # Trigger voice regeneration after menu option deletion
            try:
                _regenerate_voice_prompts(pbx_core, {})
            except Exception as e:
                logger.warning(f"Failed to regenerate voice prompts: {e}")

            return send_json(
                {
                    "success": True,
                    "message": f"Menu option {digit} deleted and removed from database",
                }
            ), 200
        else:
            return send_json({"error": f"Menu option {digit} not found"}, 404), 404
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/prompts", methods=["GET"])
@require_auth
def get_auto_attendant_prompts() -> tuple[Response, int]:
    """Get auto attendant prompt texts."""
    pbx_core = get_pbx_core()
    try:
        # Return current prompt configuration
        from pbx.utils.config import Config

        config = pbx_core.config if pbx_core else Config()
        aa_config = config.get("auto_attendant", {})

        prompts = aa_config.get(
            "prompts",
            {
                "welcome": "Thank you for calling {company_name}.",
                "main_menu": "For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.",
                "invalid": "That is not a valid option. Please try again.",
                "timeout": "We did not receive your selection. Please try again.",
                "transferring": "Please hold while we transfer your call.",
            },
        )

        company_name = config.get("company_name", "your company")

        return send_json({"prompts": prompts, "company_name": company_name}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/prompts", methods=["PUT"])
@require_auth
def update_auto_attendant_prompts() -> tuple[Response, int]:
    """Update auto attendant prompt texts and regenerate voices."""
    pbx_core = get_pbx_core()
    try:
        data = get_request_body()
        prompts = data.get("prompts", {})
        company_name = data.get("company_name")

        # Update configuration
        from pbx.utils.config import Config

        config = pbx_core.config if pbx_core else Config()

        # Ensure auto_attendant section exists
        if "auto_attendant" not in config.config:
            config.config["auto_attendant"] = {}

        # Update prompts
        if prompts:
            config.config["auto_attendant"]["prompts"] = prompts

        # Update company name
        if company_name:
            config.config["company_name"] = company_name

        # Save configuration
        success = config.save()
        if not success:
            raise Exception("Failed to save configuration file")

        # Trigger voice regeneration
        _regenerate_voice_prompts(pbx_core, prompts, company_name)

        return send_json(
            {"success": True, "message": "Prompts updated and voices regenerated successfully"}
        ), 200
    except Exception as e:
        logger.error(f"Error updating prompts: {e}")
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus", methods=["GET"])
@require_auth
def get_menus() -> tuple[Response, int]:
    """Get list of all menus."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant
        menus = aa.list_menus()
        return send_json({"menus": menus}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus/<menu_id>", methods=["GET"])
@require_auth
def get_menu(menu_id: str) -> tuple[Response, int]:
    """Get details of a specific menu."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant
        menu = aa.get_menu(menu_id)

        if not menu:
            return send_json({"error": f"Menu '{menu_id}' not found"}, 404), 404

        return send_json({"menu": menu}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus", methods=["POST"])
@require_auth
def create_menu() -> tuple[Response, int]:
    """Create a new menu or submenu."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        data = get_request_body()
        menu_id = data.get("menu_id")
        parent_menu_id = data.get("parent_menu_id")
        menu_name = data.get("menu_name")
        prompt_text = data.get("prompt_text", "")

        if not menu_id or not menu_name:
            return send_json({"error": "menu_id and menu_name are required"}, 400), 400

        # Validate menu_id format (alphanumeric, dashes, underscores only)
        if not re.match(r"^[a-z0-9_-]+$", menu_id):
            return send_json(
                {
                    "error": "menu_id must contain only lowercase letters, numbers, dashes, and underscores"
                },
                400,
            ), 400

        aa = pbx_core.auto_attendant
        success = aa.create_menu(menu_id, parent_menu_id, menu_name, prompt_text)

        if not success:
            return send_json(
                {
                    "error": "Failed to create menu (check depth limit, circular references, or duplicate ID)"
                },
                400,
            ), 400

        # Generate voice prompt for the submenu if prompt_text provided
        if prompt_text:
            try:
                from pbx.features.auto_attendant import generate_submenu_prompt

                audio_path = aa.audio_path
                audio_file = generate_submenu_prompt(menu_id, prompt_text, audio_path)
                if audio_file:
                    aa.update_menu(menu_id, audio_file=audio_file)
                    logger.info(f"Generated voice prompt for menu '{menu_id}'")
            except Exception as e:
                logger.warning(f"Failed to generate voice prompt: {e}")

        return send_json(
            {
                "success": True,
                "message": f"Menu '{menu_id}' created successfully",
                "menu_id": menu_id,
            }
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus/<menu_id>", methods=["PUT"])
@require_auth
def update_menu(menu_id: str) -> tuple[Response, int]:
    """Update an existing menu."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        data = get_request_body()
        menu_name = data.get("menu_name")
        prompt_text = data.get("prompt_text")

        aa = pbx_core.auto_attendant

        # Check if menu exists
        if not aa.get_menu(menu_id):
            return send_json({"error": f"Menu '{menu_id}' not found"}, 404), 404

        # Update menu
        success = aa.update_menu(menu_id, menu_name=menu_name, prompt_text=prompt_text)

        if not success:
            return send_json({"error": "Failed to update menu"}, 500), 500

        # Regenerate voice prompt if prompt_text changed
        if prompt_text:
            try:
                from pbx.features.auto_attendant import generate_submenu_prompt

                audio_path = aa.audio_path
                audio_file = generate_submenu_prompt(menu_id, prompt_text, audio_path)
                if audio_file:
                    aa.update_menu(menu_id, audio_file=audio_file)
                    logger.info(f"Regenerated voice prompt for menu '{menu_id}'")
            except Exception as e:
                logger.warning(f"Failed to regenerate voice prompt: {e}")

        return send_json({"success": True, "message": f"Menu '{menu_id}' updated successfully"}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus/<menu_id>", methods=["DELETE"])
@require_auth
def delete_menu(menu_id: str) -> tuple[Response, int]:
    """Delete a menu."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant
        success = aa.delete_menu(menu_id)

        if not success:
            return send_json(
                {
                    "error": "Failed to delete menu (cannot delete main menu or menu is referenced by other items)"
                },
                400,
            ), 400

        return send_json({"success": True, "message": f"Menu '{menu_id}' deleted successfully"}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus/<menu_id>/items", methods=["GET"])
@require_auth
def get_menu_items(menu_id: str) -> tuple[Response, int]:
    """Get menu items for a specific menu."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant

        # Check if menu exists
        if not aa.get_menu(menu_id):
            return send_json({"error": f"Menu '{menu_id}' not found"}, 404), 404

        items = aa.get_menu_items(menu_id)
        return send_json({"menu_id": menu_id, "items": items}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus/<menu_id>/items", methods=["POST"])
@require_auth
def add_menu_item(menu_id: str) -> tuple[Response, int]:
    """Add an item to a menu."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        data = get_request_body()
        digit = data.get("digit")
        destination_type = data.get("destination_type")
        destination_value = data.get("destination_value")
        description = data.get("description", "")

        if not digit or not destination_type or not destination_value:
            return send_json(
                {"error": "digit, destination_type, and destination_value are required"}, 400
            ), 400

        aa = pbx_core.auto_attendant

        # Check if menu exists
        if not aa.get_menu(menu_id):
            return send_json({"error": f"Menu '{menu_id}' not found"}, 404), 404

        success = aa.add_menu_item(
            menu_id, digit, destination_type, destination_value, description
        )

        if not success:
            return send_json(
                {"error": "Failed to add menu item (check destination_type validity)"}, 400
            ), 400

        return send_json(
            {
                "success": True,
                "message": f"Menu item {digit} added to menu '{menu_id}' successfully",
            }
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus/<menu_id>/items/<digit>", methods=["PUT"])
@require_auth
def update_menu_item(menu_id: str, digit: str) -> tuple[Response, int]:
    """Update a menu item."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        data = get_request_body()
        destination_type = data.get("destination_type")
        destination_value = data.get("destination_value")
        description = data.get("description")

        if not destination_type and not destination_value and description is None:
            return send_json({"error": "At least one field must be provided to update"}, 400), 400

        aa = pbx_core.auto_attendant

        # Get current item to check if it exists
        current_items = aa.get_menu_items(menu_id)
        item_exists = any(item["digit"] == digit for item in current_items)

        if not item_exists:
            return send_json({"error": f"Menu item {digit} not found in menu '{menu_id}'"}, 404), 404

        # Get current values if not provided
        current_item = next(item for item in current_items if item["digit"] == digit)
        final_dest_type = destination_type or current_item["destination_type"]
        final_dest_value = destination_value or current_item["destination_value"]
        final_description = (
            description if description is not None else current_item["description"]
        )

        # Update (add_menu_item handles both insert and update)
        success = aa.add_menu_item(
            menu_id, digit, final_dest_type, final_dest_value, final_description
        )

        if not success:
            return send_json({"error": "Failed to update menu item"}, 500), 500

        return send_json(
            {
                "success": True,
                "message": f"Menu item {digit} in menu '{menu_id}' updated successfully",
            }
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menus/<menu_id>/items/<digit>", methods=["DELETE"])
@require_auth
def delete_menu_item(menu_id: str, digit: str) -> tuple[Response, int]:
    """Delete a menu item."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant
        success = aa.remove_menu_item(menu_id, digit)

        if not success:
            return send_json(
                {"error": f"Failed to delete menu item {digit} from menu '{menu_id}'"}, 500
            ), 500

        return send_json(
            {
                "success": True,
                "message": f"Menu item {digit} deleted from menu '{menu_id}' successfully",
            }
        ), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/auto-attendant/menu-tree", methods=["GET"])
@require_auth
def get_menu_tree() -> tuple[Response, int]:
    """Get complete menu hierarchy as a tree."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "auto_attendant"):
        return send_json({"error": "Auto attendant not available"}, 500), 500

    try:
        aa = pbx_core.auto_attendant
        tree = aa.get_menu_tree("main")

        if not tree:
            return send_json({"error": "Failed to build menu tree"}, 500), 500

        return send_json({"menu_tree": tree}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


def _regenerate_voice_prompts(pbx_core: Any, custom_prompts: dict[str, str] | None = None, company_name: str | None = None) -> None:
    """Regenerate voice prompts using gTTS.

    Args:
        pbx_core: The PBX core instance.
        custom_prompts: Optional dict of custom prompt texts.
        company_name: Optional company name override.
    """
    try:
        from pbx.utils.tts import get_tts_requirements, is_tts_available, text_to_wav_telephony

        # Check if TTS is available
        if not is_tts_available():
            raise ImportError(
                f"TTS dependencies not available. Install with: {get_tts_requirements()}"
            )

        # Get configuration
        from pbx.utils.config import Config

        config = pbx_core.config if pbx_core else Config()
        aa_config = config.get("auto_attendant", {})

        if not company_name:
            company_name = config.get("company_name", "your company")

        # Get prompt texts
        default_prompts = {
            "welcome": f"Thank you for calling {company_name}.",
            "main_menu": "For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.",
            "invalid": "That is not a valid option. Please try again.",
            "timeout": "We did not receive your selection. Please try again.",
            "transferring": "Please hold while we transfer your call.",
        }

        # Merge custom prompts
        prompts = {**default_prompts}
        if custom_prompts:
            prompts.update(custom_prompts)

        # Get output directory
        audio_path = aa_config.get("audio_path", "auto_attendant")
        if not os.path.exists(audio_path):
            os.makedirs(audio_path)

        # Generate each prompt using shared TTS utility
        logger.info("Regenerating voice prompts using gTTS...")
        for filename, text in prompts.items():
            output_file = os.path.join(audio_path, f"{filename}.wav")

            try:
                # Use shared utility function for TTS generation with 8kHz
                # for PCMU
                if text_to_wav_telephony(
                    text, output_file, language="en", tld="com", slow=False, sample_rate=8000
                ):
                    logger.info(f"Generated {filename}.wav using gTTS")
            except Exception as e:
                logger.error(f"Failed to generate {filename}.wav: {e}")

        logger.info("Voice prompt regeneration complete")
    except Exception as e:
        logger.error(f"Error regenerating voice prompts: {e}")
        raise


# ==========================================================================
# SIP Trunks Routes
# ==========================================================================


@features_bp.route("/api/sip-trunks", methods=["GET"])
@require_auth
def get_sip_trunks() -> tuple[Response, int]:
    """Get all SIP trunks."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "trunk_system"):
        try:
            trunks = pbx_core.trunk_system.get_trunk_status()
            return send_json({"trunks": trunks, "count": len(trunks)}), 200
        except Exception as e:
            logger.error(f"Error getting SIP trunks: {e}")
            return send_json({"error": f"Error getting SIP trunks: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "SIP trunk system not initialized"}, 500), 500


@features_bp.route("/api/sip-trunks/health", methods=["GET"])
@require_auth
def get_trunk_health() -> tuple[Response, int]:
    """Get health status of all trunks."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "trunk_system"):
        try:
            health_data = []
            for trunk in pbx_core.trunk_system.trunks.values():
                health_metrics = trunk.get_health_metrics()
                health_metrics["trunk_id"] = trunk.trunk_id
                health_metrics["name"] = trunk.name
                health_data.append(health_metrics)

            return send_json(
                {
                    "health": health_data,
                    "monitoring_active": pbx_core.trunk_system.monitoring_active,
                    "failover_enabled": pbx_core.trunk_system.failover_enabled,
                }
            ), 200
        except Exception as e:
            logger.error(f"Error getting trunk health: {e}")
            return send_json({"error": f"Error getting trunk health: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "SIP trunk system not initialized"}, 500), 500


@features_bp.route("/api/sip-trunks", methods=["POST"])
@require_auth
def add_sip_trunk() -> tuple[Response, int]:
    """Add a new SIP trunk."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "trunk_system"):
        try:
            data = get_request_body()

            from pbx.features.sip_trunk import SIPTrunk

            trunk = SIPTrunk(
                trunk_id=data["trunk_id"],
                name=data["name"],
                host=data["host"],
                username=data["username"],
                password=data["password"],
                port=data.get("port", 5060),
                codec_preferences=data.get("codec_preferences", ["G.711", "G.729"]),
                priority=data.get("priority", 100),
                max_channels=data.get("max_channels", 10),
                health_check_interval=data.get("health_check_interval", 60),
            )

            pbx_core.trunk_system.add_trunk(trunk)
            trunk.register()

            return send_json(
                {
                    "success": True,
                    "message": f"Trunk {trunk.name} added successfully",
                    "trunk": trunk.to_dict(),
                }
            ), 200

        except Exception as e:
            logger.error(f"Error adding SIP trunk: {e}")
            return send_json({"error": f"Error adding SIP trunk: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "SIP trunk system not initialized"}, 500), 500


@features_bp.route("/api/sip-trunks/test", methods=["POST"])
@require_auth
def test_sip_trunk() -> tuple[Response, int]:
    """Test a SIP trunk connection."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "trunk_system"):
        try:
            data = get_request_body()

            trunk_id = data.get("trunk_id")
            trunk = pbx_core.trunk_system.get_trunk(trunk_id)

            if trunk:
                # Perform health check
                health_status = trunk.check_health()

                return send_json(
                    {
                        "success": True,
                        "trunk_id": trunk_id,
                        "health_status": health_status.value,
                        "metrics": trunk.get_health_metrics(),
                    }
                ), 200
            else:
                return send_json({"error": "Trunk not found"}, 404), 404

        except Exception as e:
            logger.error(f"Error testing SIP trunk: {e}")
            return send_json({"error": f"Error testing SIP trunk: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "SIP trunk system not initialized"}, 500), 500


@features_bp.route("/api/sip-trunks/<trunk_id>", methods=["DELETE"])
@require_auth
def delete_sip_trunk(trunk_id: str) -> tuple[Response, int]:
    """Delete a SIP trunk."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "trunk_system"):
        try:
            trunk = pbx_core.trunk_system.get_trunk(trunk_id)
            if trunk:
                pbx_core.trunk_system.remove_trunk(trunk_id)
                return send_json(
                    {"success": True, "message": f"Trunk {trunk_id} removed successfully"}
                ), 200
            else:
                return send_json({"error": "Trunk not found"}, 404), 404

        except Exception as e:
            logger.error(f"Error deleting SIP trunk: {e}")
            return send_json({"error": f"Error deleting SIP trunk: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "SIP trunk system not initialized"}, 500), 500


# ==========================================================================
# LCR (Least-Cost Routing) Routes
# ==========================================================================


@features_bp.route("/api/lcr/rates", methods=["GET"])
@require_auth
def get_lcr_rates() -> tuple[Response, int]:
    """Get all LCR rates."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "lcr"):
        try:
            rates = []
            for rate_entry in pbx_core.lcr.rate_entries:
                rates.append(
                    {
                        "trunk_id": rate_entry.trunk_id,
                        "pattern": rate_entry.pattern.pattern,
                        "description": rate_entry.pattern.description,
                        "rate_per_minute": rate_entry.rate_per_minute,
                        "connection_fee": rate_entry.connection_fee,
                        "minimum_seconds": rate_entry.minimum_seconds,
                        "billing_increment": rate_entry.billing_increment,
                    }
                )

            time_rates = []
            for time_rate in pbx_core.lcr.time_based_rates:
                time_rates.append(
                    {
                        "name": time_rate.name,
                        "start_time": time_rate.start_time.strftime("%H:%M"),
                        "end_time": time_rate.end_time.strftime("%H:%M"),
                        "days_of_week": time_rate.days_of_week,
                        "rate_multiplier": time_rate.rate_multiplier,
                    }
                )

            return send_json({"rates": rates, "time_rates": time_rates, "count": len(rates)}), 200

        except Exception as e:
            logger.error(f"Error getting LCR rates: {e}")
            # Return empty rates instead of error to prevent UI errors
            return send_json({"rates": [], "time_rates": [], "count": 0}), 200
    else:
        # Return empty rates when LCR is not initialized
        return send_json({"rates": [], "time_rates": [], "count": 0}), 200


@features_bp.route("/api/lcr/statistics", methods=["GET"])
@require_auth
def get_lcr_statistics() -> tuple[Response, int]:
    """Get LCR statistics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "lcr"):
        try:
            stats = pbx_core.lcr.get_statistics()
            return send_json(stats), 200

        except Exception as e:
            logger.error(f"Error getting LCR statistics: {e}")
            # Return empty statistics instead of error to prevent UI errors
            return send_json({
                "total_calls": 0,
                "total_cost": 0.0,
                "total_savings": 0.0,
                "routes_by_trunk": {}
            }), 200
    else:
        # Return empty statistics when LCR is not initialized
        return send_json({
            "total_calls": 0,
            "total_cost": 0.0,
            "total_savings": 0.0,
            "routes_by_trunk": {}
        }), 200


@features_bp.route("/api/lcr/rate", methods=["POST"])
@require_auth
def add_lcr_rate() -> tuple[Response, int]:
    """Add a new LCR rate."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "lcr"):
        try:
            data = get_request_body()

            pbx_core.lcr.add_rate(
                trunk_id=data["trunk_id"],
                pattern=data["pattern"],
                rate_per_minute=float(data["rate_per_minute"]),
                description=data.get("description", ""),
                connection_fee=float(data.get("connection_fee", 0.0)),
                minimum_seconds=int(data.get("minimum_seconds", 0)),
                billing_increment=int(data.get("billing_increment", 1)),
            )

            return send_json({"success": True, "message": "LCR rate added successfully"}), 200

        except Exception as e:
            logger.error(f"Error adding LCR rate: {e}")
            return send_json({"error": f"Error adding LCR rate: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "LCR system not initialized"}, 500), 500


@features_bp.route("/api/lcr/time-rate", methods=["POST"])
@require_auth
def add_lcr_time_rate() -> tuple[Response, int]:
    """Add a time-based rate modifier."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "lcr"):
        try:
            data = get_request_body()

            pbx_core.lcr.add_time_based_rate(
                name=data["name"],
                start_hour=int(data["start_hour"]),
                start_minute=int(data["start_minute"]),
                end_hour=int(data["end_hour"]),
                end_minute=int(data["end_minute"]),
                days=data["days"],  # list of day indices
                multiplier=float(data["multiplier"]),
            )

            return send_json({"success": True, "message": "Time-based rate added successfully"}), 200

        except Exception as e:
            logger.error(f"Error adding time-based rate: {e}")
            return send_json({"error": f"Error adding time-based rate: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "LCR system not initialized"}, 500), 500


@features_bp.route("/api/lcr/clear-rates", methods=["POST"])
@require_auth
def clear_lcr_rates() -> tuple[Response, int]:
    """Clear all LCR rates."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "lcr"):
        try:
            pbx_core.lcr.clear_rates()
            return send_json({"success": True, "message": "All LCR rates cleared successfully"}), 200

        except Exception as e:
            logger.error(f"Error clearing LCR rates: {e}")
            return send_json({"error": f"Error clearing LCR rates: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "LCR system not initialized"}, 500), 500


@features_bp.route("/api/lcr/clear-time-rates", methods=["POST"])
@require_auth
def clear_lcr_time_rates() -> tuple[Response, int]:
    """Clear all time-based rates."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "lcr"):
        try:
            pbx_core.lcr.clear_time_rates()
            return send_json(
                {"success": True, "message": "All time-based rates cleared successfully"}
            ), 200

        except Exception as e:
            logger.error(f"Error clearing time-based rates: {e}")
            return send_json({"error": f"Error clearing time-based rates: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "LCR system not initialized"}, 500), 500


# ==========================================================================
# FMFM (Find Me/Follow Me) Routes
# ==========================================================================


@features_bp.route("/api/fmfm/extensions", methods=["GET"])
@require_auth
def get_fmfm_extensions() -> tuple[Response, int]:
    """Get all extensions with FMFM configured."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "find_me_follow_me"):
        try:
            extensions = pbx_core.find_me_follow_me.list_extensions_with_fmfm()
            configs = []
            for ext in extensions:
                config = pbx_core.find_me_follow_me.get_config(ext)
                if config:
                    configs.append(config)

            return send_json({"extensions": configs, "count": len(configs)}), 200
        except Exception as e:
            logger.error(f"Error getting FMFM extensions: {e}")
            return send_json({"error": f"Error getting FMFM extensions: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Find Me/Follow Me not initialized"}, 500), 500


@features_bp.route("/api/fmfm/config/<extension>", methods=["GET"])
@require_auth
def get_fmfm_config(extension: str) -> tuple[Response, int]:
    """Get FMFM configuration for an extension."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "find_me_follow_me"):
        try:
            config = pbx_core.find_me_follow_me.get_config(extension)
            if config:
                return send_json(config), 200
            else:
                return send_json(
                    {
                        "extension": extension,
                        "enabled": False,
                        "message": "No FMFM configuration found",
                    }
                ), 200
        except Exception as e:
            logger.error(f"Error getting FMFM config for {extension}: {e}")
            return send_json({"error": f"Error getting FMFM config: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Find Me/Follow Me not initialized"}, 500), 500


@features_bp.route("/api/fmfm/statistics", methods=["GET"])
@require_auth
def get_fmfm_statistics() -> tuple[Response, int]:
    """Get FMFM statistics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "find_me_follow_me"):
        try:
            stats = pbx_core.find_me_follow_me.get_statistics()
            return send_json(stats), 200
        except Exception as e:
            logger.error(f"Error getting FMFM statistics: {e}")
            return send_json({"error": f"Error getting FMFM statistics: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Find Me/Follow Me not initialized"}, 500), 500


@features_bp.route("/api/fmfm/config", methods=["POST"])
@require_auth
def set_fmfm_config() -> tuple[Response, int]:
    """set FMFM configuration for an extension."""
    logger.info("Received FMFM config save request")

    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "find_me_follow_me"):
        try:
            data = get_request_body()

            logger.info(f"FMFM config data: {data}")

            extension = data.get("extension")
            if not extension:
                logger.warning("FMFM config request missing extension")
                return send_json({"error": "Extension required"}, 400), 400

            success = pbx_core.find_me_follow_me.set_config(extension, data)

            if success:
                logger.info(f"Successfully configured FMFM for extension {extension}")
                return send_json(
                    {
                        "success": True,
                        "message": f"FMFM configured for extension {extension}",
                        "config": pbx_core.find_me_follow_me.get_config(extension),
                    }
                ), 200
            else:
                logger.error(f"Failed to set FMFM configuration for extension {extension}")
                return send_json({"error": "Failed to set FMFM configuration"}, 500), 500

        except Exception as e:
            logger.error(f"Error setting FMFM config: {e}")
            return send_json({"error": f"Error setting FMFM config: {str(e)}"}, 500), 500
    else:
        logger.error("Find Me/Follow Me not initialized")
        return send_json({"error": "Find Me/Follow Me not initialized"}, 500), 500


@features_bp.route("/api/fmfm/destination", methods=["POST"])
@require_auth
def add_fmfm_destination() -> tuple[Response, int]:
    """Add a destination to FMFM config."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "find_me_follow_me"):
        try:
            data = get_request_body()

            extension = data.get("extension")
            number = data.get("number")
            ring_time = data.get("ring_time", 20)

            if not extension or not number:
                return send_json({"error": "Extension and number required"}, 400), 400

            success = pbx_core.find_me_follow_me.add_destination(
                extension, number, ring_time
            )

            if success:
                return send_json(
                    {
                        "success": True,
                        "message": f"Destination {number} added to {extension}",
                        "config": pbx_core.find_me_follow_me.get_config(extension),
                    }
                ), 200
            else:
                return send_json({"error": "Failed to add destination"}, 500), 500

        except Exception as e:
            logger.error(f"Error adding FMFM destination: {e}")
            return send_json({"error": f"Error adding FMFM destination: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Find Me/Follow Me not initialized"}, 500), 500


@features_bp.route("/api/fmfm/destination/<extension>/<number>", methods=["DELETE"])
@require_auth
def remove_fmfm_destination(extension: str, number: str) -> tuple[Response, int]:
    """Remove a destination from FMFM config."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "find_me_follow_me"):
        try:
            success = pbx_core.find_me_follow_me.remove_destination(extension, number)

            if success:
                return send_json(
                    {
                        "success": True,
                        "message": f"Destination {number} removed from {extension}",
                    }
                ), 200
            else:
                return send_json({"error": "Failed to remove destination"}, 404), 404

        except Exception as e:
            logger.error(f"Error removing FMFM destination: {e}")
            return send_json({"error": f"Error removing FMFM destination: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Find Me/Follow Me not initialized"}, 500), 500


@features_bp.route("/api/fmfm/config/<extension>", methods=["DELETE"])
@require_auth
def disable_fmfm(extension: str) -> tuple[Response, int]:
    """Delete FMFM configuration for an extension."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "find_me_follow_me"):
        try:
            success = pbx_core.find_me_follow_me.delete_config(extension)

            if success:
                return send_json(
                    {
                        "success": True,
                        "message": f"FMFM configuration deleted for extension {extension}",
                    }
                ), 200
            else:
                return send_json({"error": "FMFM configuration not found"}, 404), 404

        except Exception as e:
            logger.error(f"Error deleting FMFM config: {e}")
            return send_json({"error": f"Error deleting FMFM config: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Find Me/Follow Me not initialized"}, 500), 500


# ==========================================================================
# Time-Based Routing Routes
# ==========================================================================


@features_bp.route("/api/time-routing/rules", methods=["GET"])
@require_auth
def get_time_routing_rules() -> tuple[Response, int]:
    """Get all time-based routing rules."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "time_based_routing"):
        try:
            # Parse query parameters for filtering
            destination = request.args.get("destination")

            rules = pbx_core.time_based_routing.list_rules(destination=destination)
            return send_json({"rules": rules, "count": len(rules)}), 200
        except Exception as e:
            logger.error(f"Error getting time routing rules: {e}")
            return send_json({"error": f"Error getting time routing rules: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Time-based routing not initialized"}, 500), 500


@features_bp.route("/api/time-routing/statistics", methods=["GET"])
@require_auth
def get_time_routing_statistics() -> tuple[Response, int]:
    """Get time-based routing statistics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "time_based_routing"):
        try:
            stats = pbx_core.time_based_routing.get_statistics()
            return send_json(stats), 200
        except Exception as e:
            logger.error(f"Error getting time routing statistics: {e}")
            return send_json({"error": f"Error getting time routing statistics: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Time-based routing not initialized"}, 500), 500


@features_bp.route("/api/time-routing/rule", methods=["POST"])
@require_auth
def add_time_routing_rule() -> tuple[Response, int]:
    """Add a time-based routing rule."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "time_based_routing"):
        try:
            data = get_request_body()

            # Validate required fields
            required_fields = ["name", "destination", "route_to", "time_conditions"]
            if not all(field in data for field in required_fields):
                return send_json({"error": "Missing required fields"}, 400), 400

            rule_id = pbx_core.time_based_routing.add_rule(data)

            if rule_id:
                return send_json(
                    {
                        "success": True,
                        "rule_id": rule_id,
                        "message": f'Time routing rule "{data["name"]}" added successfully',
                    }
                ), 200
            else:
                return send_json({"error": "Failed to add time routing rule"}, 500), 500

        except Exception as e:
            logger.error(f"Error adding time routing rule: {e}")
            return send_json({"error": f"Error adding time routing rule: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Time-based routing not initialized"}, 500), 500


@features_bp.route("/api/time-routing/rule/<rule_id>", methods=["DELETE"])
@require_auth
def delete_time_routing_rule(rule_id: str) -> tuple[Response, int]:
    """Delete a time-based routing rule."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "time_based_routing"):
        try:
            success = pbx_core.time_based_routing.delete_rule(rule_id)

            if success:
                return send_json(
                    {"success": True, "message": f"Time routing rule {rule_id} deleted"}
                ), 200
            else:
                return send_json({"error": "Rule not found"}, 404), 404

        except Exception as e:
            logger.error(f"Error deleting time routing rule: {e}")
            return send_json({"error": f"Error deleting time routing rule: {str(e)}"}, 500), 500
    else:
        return send_json({"error": "Time-based routing not initialized"}, 500), 500


# ==========================================================================
# Recording Retention Routes
# ==========================================================================


@features_bp.route("/api/recording-retention/policies", methods=["GET"])
@require_auth
def get_retention_policies() -> tuple[Response, int]:
    """Get all recording retention policies."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "recording_retention"):
        try:
            policies = []
            for (
                policy_id,
                policy,
            ) in pbx_core.recording_retention.retention_policies.items():
                # Sanitize output - don't expose sensitive paths
                safe_policy = {
                    "policy_id": policy_id,
                    "name": policy.get("name", policy_id),
                    "retention_days": policy.get("retention_days", 0),
                    "tags": policy.get("tags", []),
                    "created_at": None,
                }

                # Safely handle created_at datetime
                created_at = policy.get("created_at")
                if created_at and hasattr(created_at, "isoformat"):
                    safe_policy["created_at"] = created_at.isoformat()

                policies.append(safe_policy)

            return send_json({"policies": policies, "count": len(policies)}), 200
        except Exception as e:
            logger.error(f"Error getting retention policies: {e}")
            return send_json({"error": "Error getting retention policies"}, 500), 500
    else:
        return send_json({"error": "Recording retention not initialized"}, 500), 500


@features_bp.route("/api/recording-retention/statistics", methods=["GET"])
@require_auth
def get_retention_statistics() -> tuple[Response, int]:
    """Get recording retention statistics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "recording_retention"):
        try:
            stats = pbx_core.recording_retention.get_statistics()

            # Transform to match frontend expectations
            result = {
                "total_policies": stats.get("policies", 0),
                "total_recordings": stats.get("total_recordings", 0),
                "deleted_count": stats.get("lifetime_deleted", 0),
                "last_cleanup": stats.get("last_cleanup"),
            }

            return send_json(result), 200
        except Exception as e:
            logger.error(f"Error getting retention statistics: {e}")
            return send_json({"error": "Error getting retention statistics"}, 500), 500
    else:
        return send_json({"error": "Recording retention not initialized"}, 500), 500


@features_bp.route("/api/recording-retention/policy", methods=["POST"])
@require_auth
def add_retention_policy() -> tuple[Response, int]:
    """Add a recording retention policy."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "recording_retention"):
        try:
            data = get_request_body()

            # Validate required fields
            required_fields = ["name", "retention_days"]
            if not all(field in data for field in required_fields):
                return send_json({"error": "Missing required fields: name, retention_days"}, 400), 400

            # Validate retention_days is a positive integer
            try:
                retention_days = int(data["retention_days"])
                if retention_days < 1 or retention_days > 3650:  # Max 10 years
                    return send_json({"error": "retention_days must be between 1 and 3650"}, 400), 400
            except (ValueError, TypeError):
                return send_json({"error": "retention_days must be a valid integer"}, 400), 400

            # Sanitize name to prevent injection
            if not re.match(r"^[a-zA-Z0-9_\-\s]+$", data["name"]):
                return send_json({"error": "Policy name contains invalid characters"}, 400), 400

            policy_id = pbx_core.recording_retention.add_policy(data)

            if policy_id:
                return send_json(
                    {
                        "success": True,
                        "policy_id": policy_id,
                        "message": f'Retention policy "{data["name"]}" added successfully',
                    }
                ), 200
            else:
                return send_json({"error": "Failed to add retention policy"}, 500), 500

        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error adding retention policy: {e}")
            return send_json({"error": "Error adding retention policy"}, 500), 500
    else:
        return send_json({"error": "Recording retention not initialized"}, 500), 500


@features_bp.route("/api/recording-retention/policy/<policy_id>", methods=["DELETE"])
@require_auth
def delete_retention_policy(policy_id: str) -> tuple[Response, int]:
    """Delete a retention policy."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "recording_retention"):
        try:
            if policy_id in pbx_core.recording_retention.retention_policies:
                del pbx_core.recording_retention.retention_policies[policy_id]
                return send_json(
                    {"success": True, "message": f"Retention policy {policy_id} deleted"}
                ), 200
            else:
                return send_json({"error": "Policy not found"}, 404), 404

        except Exception as e:
            logger.error(f"Error deleting retention policy: {e}")
            return send_json({"error": "Error deleting retention policy"}, 500), 500
    else:
        return send_json({"error": "Recording retention not initialized"}, 500), 500


# ==========================================================================
# Fraud Detection Routes
# ==========================================================================


@features_bp.route("/api/fraud-detection/alerts", methods=["GET"])
@require_auth
def get_fraud_alerts() -> tuple[Response, int]:
    """Get fraud detection alerts."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "fraud_detection"):
        try:
            # Parse query parameters
            extension = request.args.get("extension")
            # Note: backend get_alerts uses 'hours' parameter, not 'limit'
            hours = int(request.args.get("hours", 24))

            # Validate hours
            hours = min(hours, 720)  # Max 30 days

            alerts = pbx_core.fraud_detection.get_alerts(extension=extension, hours=hours)

            return send_json({"alerts": alerts, "count": len(alerts)}), 200
        except Exception as e:
            logger.error(f"Error getting fraud alerts: {e}")
            return send_json({"error": "Error getting fraud alerts"}, 500), 500
    else:
        return send_json({"error": "Fraud detection not initialized"}, 500), 500


@features_bp.route("/api/fraud-detection/statistics", methods=["GET"])
@require_auth
def get_fraud_statistics() -> tuple[Response, int]:
    """Get fraud detection statistics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "fraud_detection"):
        try:
            stats = pbx_core.fraud_detection.get_statistics()

            # Transform to match frontend expectations
            result = {
                "total_alerts": stats.get("total_alerts", 0),
                "high_risk_alerts": sum(
                    1
                    for a in pbx_core.fraud_detection.alerts
                    if a.get("fraud_score", 0) > 0.7
                ),
                "blocked_patterns_count": stats.get("blocked_patterns", 0),
                "extensions_flagged": stats.get("total_extensions_tracked", 0),
                "alerts_24h": stats.get("alerts_24h", 0),
                "blocked_patterns": pbx_core.fraud_detection.blocked_patterns,
            }

            return send_json(result), 200
        except Exception as e:
            logger.error(f"Error getting fraud statistics: {e}")
            return send_json({"error": "Error getting fraud statistics"}, 500), 500
    else:
        return send_json({"error": "Fraud detection not initialized"}, 500), 500


@features_bp.route("/api/fraud-detection/extension/<extension>", methods=["GET"])
@require_auth
def get_fraud_extension_stats(extension: str) -> tuple[Response, int]:
    """Get fraud statistics for a specific extension."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "fraud_detection"):
        try:
            # Validate extension format
            if not re.match(r"^\d{3,5}$", extension):
                return send_json({"error": "Invalid extension format"}, 400), 400

            stats = pbx_core.fraud_detection.get_extension_statistics(extension)
            return send_json(stats), 200
        except Exception as e:
            logger.error(f"Error getting extension fraud stats: {e}")
            return send_json({"error": "Error getting extension statistics"}, 500), 500
    else:
        return send_json({"error": "Fraud detection not initialized"}, 500), 500


@features_bp.route("/api/fraud-detection/blocked-pattern", methods=["POST"])
@require_auth
def add_blocked_pattern() -> tuple[Response, int]:
    """Add a blocked number pattern."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "fraud_detection"):
        try:
            data = get_request_body()

            # Validate required fields
            if "pattern" not in data or "reason" not in data:
                return send_json({"error": "Missing required fields: pattern, reason"}, 400), 400

            # Validate pattern is a valid regex (prevent ReDoS)
            try:
                re.compile(data["pattern"])
            except re.error:
                return send_json({"error": "Invalid regex pattern"}, 400), 400

            # Sanitize reason
            reason = str(data["reason"])[:200]  # Limit length

            success = pbx_core.fraud_detection.add_blocked_pattern(data["pattern"], reason)

            if success:
                return send_json(
                    {"success": True, "message": "Blocked pattern added successfully"}
                ), 200
            else:
                return send_json({"error": "Failed to add blocked pattern"}, 500), 500

        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error adding blocked pattern: {e}")
            return send_json({"error": "Error adding blocked pattern"}, 500), 500
    else:
        return send_json({"error": "Fraud detection not initialized"}, 500), 500


@features_bp.route("/api/fraud-detection/blocked-pattern/<pattern_id>", methods=["DELETE"])
@require_auth
def delete_blocked_pattern(pattern_id: str) -> tuple[Response, int]:
    """Delete a blocked pattern."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "fraud_detection"):
        try:
            # Find and remove pattern by ID/index
            try:
                index = int(pattern_id)
                if 0 <= index < len(pbx_core.fraud_detection.blocked_patterns):
                    del pbx_core.fraud_detection.blocked_patterns[index]
                    return send_json({"success": True, "message": "Blocked pattern deleted"}), 200
                else:
                    return send_json({"error": "Pattern not found"}, 404), 404
            except (ValueError, IndexError):
                return send_json({"error": "Invalid pattern ID"}, 400), 400

        except Exception as e:
            logger.error(f"Error deleting blocked pattern: {e}")
            return send_json({"error": "Error deleting blocked pattern"}, 500), 500
    else:
        return send_json({"error": "Fraud detection not initialized"}, 500), 500


# ==========================================================================
# Callback Queue Routes
# ==========================================================================


@features_bp.route("/api/callback-queue/statistics", methods=["GET"])
@require_auth
def get_callback_statistics() -> tuple[Response, int]:
    """Get callback queue statistics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "callback_queue"):
        try:
            stats = pbx_core.callback_queue.get_statistics()
            return send_json(stats), 200
        except Exception as e:
            logger.error(f"Error getting callback statistics: {e}")
            return send_json({"error": "Error getting callback statistics"}, 500), 500
    else:
        return send_json({"error": "Callback queue not initialized"}, 500), 500


@features_bp.route("/api/callback-queue/list", methods=["GET"])
@require_auth
def get_callback_list() -> tuple[Response, int]:
    """Get list of all callbacks."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "callback_queue"):
        try:
            callbacks = []
            for callback_id in pbx_core.callback_queue.callbacks:
                info = pbx_core.callback_queue.get_callback_info(callback_id)
                if info:
                    callbacks.append(info)

            # Sort by requested_at descending (most recent first)
            callbacks.sort(key=lambda x: x.get("requested_at", ""), reverse=True)

            return send_json({"callbacks": callbacks}), 200
        except Exception as e:
            logger.error(f"Error getting callback list: {e}")
            return send_json({"error": "Error getting callback list"}, 500), 500
    else:
        return send_json({"error": "Callback queue not initialized"}, 500), 500


@features_bp.route("/api/callback-queue/queue/<queue_id>", methods=["GET"])
@require_auth
def get_queue_callbacks(queue_id: str) -> tuple[Response, int]:
    """Get callbacks for a specific queue."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "callback_queue"):
        try:
            # Sanitize queue_id
            if not re.match(r"^[\w-]{1,50}$", queue_id):
                return send_json({"error": "Invalid queue_id format"}, 400), 400

            callbacks = pbx_core.callback_queue.list_queue_callbacks(queue_id)
            stats = pbx_core.callback_queue.get_queue_statistics(queue_id)

            return send_json({"queue_id": queue_id, "callbacks": callbacks, "statistics": stats}), 200
        except Exception as e:
            logger.error(f"Error getting queue callbacks: {e}")
            return send_json({"error": "Error getting queue callbacks"}, 500), 500
    else:
        return send_json({"error": "Callback queue not initialized"}, 500), 500


@features_bp.route("/api/callback-queue/info/<callback_id>", methods=["GET"])
@require_auth
def get_callback_info(callback_id: str) -> tuple[Response, int]:
    """Get information about a specific callback."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "callback_queue"):
        try:
            # Sanitize callback_id
            if not re.match(r"^cb_[\w]{1,100}$", callback_id):
                return send_json({"error": "Invalid callback_id format"}, 400), 400

            info = pbx_core.callback_queue.get_callback_info(callback_id)

            if info:
                return send_json(info), 200
            else:
                return send_json({"error": "Callback not found"}, 404), 404
        except Exception as e:
            logger.error(f"Error getting callback info: {e}")
            return send_json({"error": "Error getting callback info"}, 500), 500
    else:
        return send_json({"error": "Callback queue not initialized"}, 500), 500


@features_bp.route("/api/callback-queue/request", methods=["POST"])
@require_auth
def request_callback() -> tuple[Response, int]:
    """Request a callback from queue."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "callback_queue"):
        try:
            data = get_request_body()

            # Validate required fields
            if "queue_id" not in data or "caller_number" not in data:
                return send_json(
                    {"error": "Missing required fields: queue_id, caller_number"}, 400
                ), 400

            # Sanitize inputs
            queue_id = str(data["queue_id"])[:50]
            caller_number = str(data["caller_number"])[:50]
            caller_name = (
                str(data.get("caller_name", ""))[:100] if data.get("caller_name") else None
            )

            # Parse preferred_time if provided
            preferred_time = None
            if "preferred_time" in data:
                try:
                    from datetime import datetime

                    preferred_time = datetime.fromisoformat(data["preferred_time"])
                except (ValueError, TypeError):
                    return send_json(
                        {"error": "Invalid preferred_time format. Use ISO 8601 format."}, 400
                    ), 400

            result = pbx_core.callback_queue.request_callback(
                queue_id, caller_number, caller_name, preferred_time
            )

            if "error" in result:
                return send_json(result, 400), 400
            else:
                return send_json({"success": True, **result}), 200
        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error requesting callback: {e}")
            return send_json({"error": "Error requesting callback"}, 500), 500
    else:
        return send_json({"error": "Callback queue not initialized"}, 500), 500


@features_bp.route("/api/callback-queue/start", methods=["POST"])
@require_auth
def start_callback() -> tuple[Response, int]:
    """Start processing a callback."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "callback_queue"):
        try:
            data = get_request_body()

            if "callback_id" not in data or "agent_id" not in data:
                return send_json(
                    {"error": "Missing required fields: callback_id, agent_id"}, 400
                ), 400

            callback_id = str(data["callback_id"])[:100]
            agent_id = str(data["agent_id"])[:50]

            result = pbx_core.callback_queue.start_callback(callback_id, agent_id)

            if "error" in result:
                return send_json(result, 404), 404
            else:
                return send_json({"success": True, **result}), 200
        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error starting callback: {e}")
            return send_json({"error": "Error starting callback"}, 500), 500
    else:
        return send_json({"error": "Callback queue not initialized"}, 500), 500


@features_bp.route("/api/callback-queue/complete", methods=["POST"])
@require_auth
def complete_callback() -> tuple[Response, int]:
    """Complete a callback."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "callback_queue"):
        try:
            data = get_request_body()

            if "callback_id" not in data or "success" not in data:
                return send_json({"error": "Missing required fields: callback_id, success"}, 400), 400

            callback_id = str(data["callback_id"])[:100]
            success = bool(data["success"])
            notes = str(data.get("notes", ""))[:500] if data.get("notes") else None

            result = pbx_core.callback_queue.complete_callback(callback_id, success, notes)

            if result:
                return send_json({"success": True, "message": "Callback completed"}), 200
            else:
                return send_json({"error": "Callback not found"}, 404), 404
        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error completing callback: {e}")
            return send_json({"error": "Error completing callback"}, 500), 500
    else:
        return send_json({"error": "Callback queue not initialized"}, 500), 500


@features_bp.route("/api/callback-queue/cancel", methods=["POST"])
@require_auth
def cancel_callback() -> tuple[Response, int]:
    """Cancel a pending callback."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "callback_queue"):
        try:
            data = get_request_body()

            if "callback_id" not in data:
                return send_json({"error": "Missing required field: callback_id"}, 400), 400

            callback_id = str(data["callback_id"])[:100]

            result = pbx_core.callback_queue.cancel_callback(callback_id)

            if result:
                return send_json({"success": True, "message": "Callback cancelled"}), 200
            else:
                return send_json({"error": "Callback not found"}, 404), 404
        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error cancelling callback: {e}")
            return send_json({"error": "Error cancelling callback"}, 500), 500
    else:
        return send_json({"error": "Callback queue not initialized"}, 500), 500


# ==========================================================================
# Mobile Push Notification Routes
# ==========================================================================


@features_bp.route("/api/mobile-push/devices", methods=["GET"])
@require_auth
def get_all_devices() -> tuple[Response, int]:
    """Get all registered mobile devices."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "mobile_push"):
        try:
            all_devices = []
            for user_id, devices in pbx_core.mobile_push.device_tokens.items():
                for device in devices:
                    all_devices.append(
                        {
                            "user_id": user_id,
                            "platform": device["platform"],
                            "registered_at": device["registered_at"].isoformat(),
                            "last_seen": device["last_seen"].isoformat(),
                        }
                    )

            # Sort by last_seen descending
            all_devices.sort(key=lambda x: x["last_seen"], reverse=True)

            return send_json({"devices": all_devices, "total": len(all_devices)}), 200
        except Exception as e:
            logger.error(f"Error getting all devices: {e}")
            return send_json({"error": "Error getting devices"}, 500), 500
    else:
        return send_json({"error": "Mobile push notifications not initialized"}, 500), 500


@features_bp.route("/api/mobile-push/devices/<user_id>", methods=["GET"])
@require_auth
def get_user_devices(user_id: str) -> tuple[Response, int]:
    """Get devices for a specific user."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "mobile_push"):
        try:
            # Sanitize user_id
            if not re.match(r"^[\w]{1,50}$", user_id):
                return send_json({"error": "Invalid user_id format"}, 400), 400

            devices = pbx_core.mobile_push.get_user_devices(user_id)
            return send_json({"user_id": user_id, "devices": devices, "count": len(devices)}), 200
        except Exception as e:
            logger.error(f"Error getting user devices: {e}")
            return send_json({"error": "Error getting user devices"}, 500), 500
    else:
        return send_json({"error": "Mobile push notifications not initialized"}, 500), 500


@features_bp.route("/api/mobile-push/statistics", methods=["GET"])
@require_auth
def get_push_statistics() -> tuple[Response, int]:
    """Get push notification statistics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "mobile_push"):
        try:
            # Count devices
            total_devices = sum(
                len(devices) for devices in pbx_core.mobile_push.device_tokens.values()
            )
            total_users = len(pbx_core.mobile_push.device_tokens)

            # Count by platform
            platform_counts = {}
            for devices in pbx_core.mobile_push.device_tokens.values():
                for device in devices:
                    platform = device["platform"]
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1

            # Recent notifications
            recent_notifications = len(pbx_core.mobile_push.notification_history)

            return send_json(
                {
                    "total_devices": total_devices,
                    "total_users": total_users,
                    "platforms": platform_counts,
                    "recent_notifications": recent_notifications,
                }
            ), 200
        except Exception as e:
            logger.error(f"Error getting push statistics: {e}")
            return send_json({"error": "Error getting push statistics"}, 500), 500
    else:
        return send_json({"error": "Mobile push notifications not initialized"}, 500), 500


@features_bp.route("/api/mobile-push/history", methods=["GET"])
@require_auth
def get_push_history() -> tuple[Response, int]:
    """Get push notification history."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "mobile_push"):
        try:
            # Get recent notification history
            history = []
            for notif in pbx_core.mobile_push.notification_history[-100:]:  # Last 100
                history.append(
                    {
                        "user_id": notif["user_id"],
                        "title": notif["title"],
                        "body": notif["body"],
                        "sent_at": notif["sent_at"].isoformat(),
                        "success_count": notif.get("success_count", 0),
                        "failure_count": notif.get("failure_count", 0),
                    }
                )

            # Sort by sent_at descending
            history.sort(key=lambda x: x["sent_at"], reverse=True)

            return send_json({"history": history}), 200
        except Exception as e:
            logger.error(f"Error getting push history: {e}")
            return send_json({"error": "Error getting push history"}, 500), 500
    else:
        return send_json({"error": "Mobile push notifications not initialized"}, 500), 500


@features_bp.route("/api/mobile-push/register", methods=["POST"])
@require_auth
def register_mobile_device() -> tuple[Response, int]:
    """Register a mobile device for push notifications."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "mobile_push"):
        try:
            data = get_request_body()

            if "user_id" not in data or "device_token" not in data:
                return send_json(
                    {"error": "Missing required fields: user_id, device_token"}, 400
                ), 400

            user_id = str(data["user_id"])[:50]
            device_token = str(data["device_token"])[:255]
            platform = str(data.get("platform", "unknown"))[:20]

            success = pbx_core.mobile_push.register_device(user_id, device_token, platform)

            if success:
                return send_json({"success": True, "message": "Device registered successfully"}), 200
            else:
                return send_json({"error": "Failed to register device"}, 500), 500
        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return send_json({"error": "Error registering device"}, 500), 500
    else:
        return send_json({"error": "Mobile push notifications not initialized"}, 500), 500


@features_bp.route("/api/mobile-push/unregister", methods=["POST"])
@require_auth
def unregister_mobile_device() -> tuple[Response, int]:
    """Unregister a mobile device."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "mobile_push"):
        try:
            data = get_request_body()

            if "user_id" not in data or "device_token" not in data:
                return send_json(
                    {"error": "Missing required fields: user_id, device_token"}, 400
                ), 400

            user_id = str(data["user_id"])[:50]
            device_token = str(data["device_token"])[:255]

            success = pbx_core.mobile_push.unregister_device(user_id, device_token)

            if success:
                return send_json(
                    {"success": True, "message": "Device unregistered successfully"}
                ), 200
            else:
                return send_json({"error": "Device not found"}, 404), 404
        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error unregistering device: {e}")
            return send_json({"error": "Error unregistering device"}, 500), 500
    else:
        return send_json({"error": "Mobile push notifications not initialized"}, 500), 500


@features_bp.route("/api/mobile-push/test", methods=["POST"])
@require_auth
def test_push_notification() -> tuple[Response, int]:
    """Send a test push notification."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "mobile_push"):
        try:
            data = get_request_body()

            if "user_id" not in data:
                return send_json({"error": "Missing required field: user_id"}, 400), 400

            user_id = str(data["user_id"])[:50]

            result = pbx_core.mobile_push.send_test_notification(user_id)

            if "error" in result:
                return send_json(result, 400), 400
            else:
                return send_json({"success": True, **result}), 200
        except json.JSONDecodeError:
            return send_json({"error": "Invalid JSON"}, 400), 400
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            return send_json({"error": "Error sending test notification"}, 500), 500
    else:
        return send_json({"error": "Mobile push notifications not initialized"}, 500), 500


# ==========================================================================
# Recording Announcements Routes
# ==========================================================================


@features_bp.route("/api/recording-announcements/statistics", methods=["GET"])
@require_auth
def get_announcement_statistics() -> tuple[Response, int]:
    """Get recording announcements statistics."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "recording_announcements"):
        try:
            stats = {
                "enabled": pbx_core.recording_announcements.enabled,
                "announcements_played": pbx_core.recording_announcements.announcements_played,
                "consent_accepted": pbx_core.recording_announcements.consent_accepted,
                "consent_declined": pbx_core.recording_announcements.consent_declined,
                "announcement_type": pbx_core.recording_announcements.announcement_type,
                "require_consent": pbx_core.recording_announcements.require_consent,
            }
            return send_json(stats), 200
        except Exception as e:
            logger.error(f"Error getting announcement statistics: {e}")
            return send_json({"error": "Error getting announcement statistics"}, 500), 500
    else:
        return send_json({"error": "Recording announcements not initialized"}, 500), 500


@features_bp.route("/api/recording-announcements/config", methods=["GET"])
@require_auth
def get_announcement_config() -> tuple[Response, int]:
    """Get recording announcements configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and hasattr(pbx_core, "recording_announcements"):
        try:
            config = pbx_core.recording_announcements.get_announcement_config()
            return send_json(config), 200
        except Exception as e:
            logger.error(f"Error getting announcement config: {e}")
            return send_json({"error": "Error getting announcement config"}, 500), 500
    else:
        return send_json({"error": "Recording announcements not initialized"}, 500), 500


# ==========================================================================
# Skills-Based Routing Routes
# ==========================================================================


@features_bp.route("/api/skills/all", methods=["GET"])
@require_auth
def get_all_skills() -> tuple[Response, int]:
    """Get all skills."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "skills_router"):
        return send_json({"error": "Skills routing not available"}, 500), 500

    try:
        skills = pbx_core.skills_router.get_all_skills()
        return send_json({"skills": skills}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/skills/agent/<path:subpath>", methods=["GET"])
@require_auth
def get_agent_skills(subpath: str) -> tuple[Response, int]:
    """Get agent skills."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "skills_router"):
        return send_json({"error": "Skills routing not available"}, 500), 500

    try:
        agent_extension = subpath.split("/")[-1]
        skills = pbx_core.skills_router.get_agent_skills(agent_extension)

        return send_json({"agent_extension": agent_extension, "skills": skills}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/skills/queue/<path:subpath>", methods=["GET"])
@require_auth
def get_queue_requirements(subpath: str) -> tuple[Response, int]:
    """Get queue skill requirements."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "skills_router"):
        return send_json({"error": "Skills routing not available"}, 500), 500

    try:
        queue_number = subpath.split("/")[-1]
        requirements = pbx_core.skills_router.get_queue_requirements(queue_number)

        return send_json({"queue_number": queue_number, "requirements": requirements}), 200
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/skills/skill", methods=["POST"])
@require_auth
def add_skill() -> tuple[Response, int]:
    """Handle adding a new skill."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "skills_router"):
        return send_json({"error": "Skills routing not available"}, 500), 500

    try:
        data = get_request_body()
        skill_id = data.get("skill_id")
        name = data.get("name")
        description = data.get("description", "")

        if not skill_id or not name:
            return send_json({"error": "skill_id and name are required"}, 400), 400

        success = pbx_core.skills_router.add_skill(skill_id, name, description)

        if success:
            return send_json(
                {"success": True, "skill_id": skill_id, "message": "Skill added successfully"}
            ), 200
        else:
            return send_json({"error": "Skill already exists"}, 409), 409
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/skills/assign", methods=["POST"])
@require_auth
def assign_skill() -> tuple[Response, int]:
    """Handle assigning skill to agent."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "skills_router"):
        return send_json({"error": "Skills routing not available"}, 500), 500

    try:
        data = get_request_body()
        agent_extension = data.get("agent_extension")
        skill_id = data.get("skill_id")
        proficiency = data.get("proficiency", 5)

        if not agent_extension or not skill_id:
            return send_json({"error": "agent_extension and skill_id are required"}, 400), 400

        success = pbx_core.skills_router.assign_skill_to_agent(
            agent_extension, skill_id, proficiency
        )

        if success:
            return send_json(
                {"success": True, "message": f"Skill assigned to agent {agent_extension}"}
            ), 200
        else:
            return send_json({"error": "Failed to assign skill"}, 500), 500
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/skills/queue-requirements", methods=["POST"])
@require_auth
def set_queue_requirements() -> tuple[Response, int]:
    """Handle setting queue skill requirements."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "skills_router"):
        return send_json({"error": "Skills routing not available"}, 500), 500

    try:
        data = get_request_body()
        queue_number = data.get("queue_number")
        requirements = data.get("requirements", [])

        if not queue_number:
            return send_json({"error": "queue_number is required"}, 400), 400

        success = pbx_core.skills_router.set_queue_requirements(queue_number, requirements)

        if success:
            return send_json(
                {"success": True, "message": f"Requirements set for queue {queue_number}"}
            ), 200
        else:
            return send_json({"error": "Failed to set requirements"}, 500), 500
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@features_bp.route("/api/skills/assign/<agent_extension>/<skill_id>", methods=["DELETE"])
@require_auth
def remove_skill_from_agent(agent_extension: str, skill_id: str) -> tuple[Response, int]:
    """Handle removing skill from agent."""
    pbx_core = get_pbx_core()
    if not pbx_core or not hasattr(pbx_core, "skills_router"):
        return send_json({"error": "Skills routing not available"}, 500), 500

    try:
        success = pbx_core.skills_router.remove_skill_from_agent(agent_extension, skill_id)

        if success:
            return send_json(
                {"success": True, "message": f"Skill removed from agent {agent_extension}"}
            ), 200
        else:
            return send_json({"error": "Skill not found for agent"}, 404), 404
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500
