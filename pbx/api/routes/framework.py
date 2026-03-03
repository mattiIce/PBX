"""Flask Blueprint for /api/framework/* routes.

Covers: Speech Analytics, Video Conference, Click-to-Dial, Team Messaging,
Nomadic E911, Integrations, Compliance, BI Integration, Call Tagging,
Call Blending, Geo Redundancy, Conversational AI, Predictive Dialing,
Voice Biometrics, Call Quality Prediction, Video Codec, Mobile Portability,
Recording Analytics, Voicemail Drop, DNS SRV, SBC, and Data Residency.
"""

import base64
from datetime import UTC, datetime, timedelta

from flask import Blueprint, Response, request

from pbx.api.utils import (
    get_pbx_core,
    get_request_body,
    require_admin,
    require_auth,
    send_json,
)
from pbx.utils.logger import get_logger

logger = get_logger()

framework_bp = Blueprint("framework", __name__, url_prefix="/api/framework")


# =============================================================================
# Speech Analytics
# =============================================================================


@framework_bp.route("/speech-analytics/configs", methods=["GET"])
@require_auth
def get_speech_analytics_configs() -> tuple[Response, int]:
    """Get all speech analytics configurations."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.speech_analytics import SpeechAnalyticsEngine

            engine = SpeechAnalyticsEngine(pbx_core.database, pbx_core.config)
            configs = engine.get_all_configs()
            return send_json({"configs": configs}), 200
        except Exception as e:
            logger.error(f"Error getting speech analytics configs: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/speech-analytics/config/<extension>", methods=["GET"])
@require_auth
def get_speech_analytics_config(extension: str) -> tuple[Response, int]:
    """Get speech analytics config for extension."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.speech_analytics import SpeechAnalyticsEngine

            engine = SpeechAnalyticsEngine(pbx_core.database, pbx_core.config)
            config = engine.get_config(extension)
            if config:
                return send_json(config), 200
            return send_json({"error": "Config not found"}, 404), 404
        except Exception as e:
            logger.error(f"Error getting speech analytics config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/speech-analytics/summary/<call_id>", methods=["GET"])
@require_auth
def get_call_summary(call_id: str) -> tuple[Response, int]:
    """Get stored call summary."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.speech_analytics import SpeechAnalyticsEngine

            engine = SpeechAnalyticsEngine(pbx_core.database, pbx_core.config)
            summary = engine.get_call_summary(call_id)
            if summary:
                return send_json(summary), 200
            return send_json({"error": "Summary not found"}, 404), 404
        except Exception as e:
            logger.error(f"Error getting call summary: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/speech-analytics/config/<extension>", methods=["POST"])
@require_auth
def update_speech_analytics_config(extension: str) -> tuple[Response, int]:
    """Update speech analytics configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.speech_analytics import SpeechAnalyticsEngine

            engine = SpeechAnalyticsEngine(pbx_core.database, pbx_core.config)
            if engine.update_config(extension, body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to update config"}, 500), 500
        except Exception as e:
            logger.error(f"Error updating speech analytics config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/speech-analytics/config/<extension>", methods=["DELETE"])
@require_auth
def delete_speech_analytics_config(extension: str) -> tuple[Response, int]:
    """Delete speech analytics configuration for an extension."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.speech_analytics import SpeechAnalyticsEngine

            engine = SpeechAnalyticsEngine(pbx_core.database, pbx_core.config)
            if engine.delete_config(extension):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to delete config"}, 500), 500
        except Exception as e:
            logger.error(f"Error deleting speech analytics config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/speech-analytics/analyze-sentiment", methods=["POST"])
@require_auth
def analyze_sentiment() -> tuple[Response, int]:
    """Analyze sentiment of provided text."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            text = body.get("text", "")
            if not text:
                return send_json({"error": "Text required"}, 400), 400

            from pbx.features.speech_analytics import SpeechAnalyticsEngine

            engine = SpeechAnalyticsEngine(pbx_core.database, pbx_core.config)
            result = engine.analyze_sentiment(text)
            return send_json(result), 200
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/speech-analytics/generate-summary/<call_id>", methods=["POST"])
@require_auth
def generate_summary(call_id: str) -> tuple[Response, int]:
    """Generate call summary from transcript."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            transcript = body.get("transcript", "")
            if not transcript:
                return send_json({"error": "Transcript required"}, 400), 400

            from pbx.features.speech_analytics import SpeechAnalyticsEngine

            engine = SpeechAnalyticsEngine(pbx_core.database, pbx_core.config)
            summary = engine.generate_summary(call_id, transcript)
            return send_json({"call_id": call_id, "summary": summary}), 200
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error generating summary: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


# =============================================================================
# Video Conference
# =============================================================================


@framework_bp.route("/video-conference/rooms", methods=["GET"])
@require_auth
def get_video_rooms() -> tuple[Response, int]:
    """Get all video conference rooms."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.video_conferencing import VideoConferencingEngine

            engine = VideoConferencingEngine(pbx_core.database, pbx_core.config)
            rooms = engine.get_all_rooms()
            return send_json({"rooms": rooms}), 200
        except Exception as e:
            logger.error(f"Error getting video rooms: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/video-conference/room/<room_id>", methods=["GET"])
@require_auth
def get_video_room(room_id: str) -> tuple[Response, int]:
    """Get video conference room details."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.video_conferencing import VideoConferencingEngine

            engine = VideoConferencingEngine(pbx_core.database, pbx_core.config)
            room = engine.get_room(int(room_id))
            if room:
                participants = engine.get_room_participants(int(room_id))
                room["participants"] = participants
                return send_json(room), 200
            return send_json({"error": "Room not found"}, 404), 404
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error getting video room: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/video-conference/create-room", methods=["POST"])
@require_auth
def create_video_room() -> tuple[Response, int]:
    """Create video conference room."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.video_conferencing import VideoConferencingEngine

            engine = VideoConferencingEngine(pbx_core.database, pbx_core.config)
            room_id = engine.create_room(body)
            if room_id:
                return send_json({"room_id": room_id, "success": True}), 200
            return send_json({"error": "Failed to create room"}, 500), 500
        except Exception as e:
            logger.error(f"Error creating video room: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/video-conference/join/<room_id>", methods=["POST"])
@require_auth
def join_video_room(room_id: str) -> tuple[Response, int]:
    """Join video conference room."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.video_conferencing import VideoConferencingEngine

            engine = VideoConferencingEngine(pbx_core.database, pbx_core.config)
            if engine.join_room(int(room_id), body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to join room"}, 500), 500
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error joining video room: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


# =============================================================================
# Click-to-Dial
# =============================================================================


@framework_bp.route("/click-to-dial/configs", methods=["GET"])
@require_auth
def get_click_to_dial_configs() -> tuple[Response, int]:
    """Get all click-to-dial configurations."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.click_to_dial import ClickToDialEngine

            engine = ClickToDialEngine(pbx_core.database, pbx_core.config, pbx_core)
            configs = engine.get_all_configs()
            return send_json({"configs": configs}), 200
        except Exception as e:
            logger.error(f"Error getting click-to-dial configs: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/click-to-dial/config/<extension>", methods=["GET"])
@require_auth
def get_click_to_dial_config(extension: str) -> tuple[Response, int]:
    """Get click-to-dial config for extension."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.click_to_dial import ClickToDialEngine

            engine = ClickToDialEngine(pbx_core.database, pbx_core.config, pbx_core)
            config = engine.get_config(extension)
            if config:
                return send_json(config), 200
            # Return default config
            return send_json(
                {
                    "extension": extension,
                    "enabled": True,
                    "auto_answer": False,
                    "browser_notification": True,
                }
            ), 200
        except Exception as e:
            logger.error(f"Error getting click-to-dial config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/click-to-dial/history/<extension>", methods=["GET"])
@require_auth
def get_click_to_dial_history(extension: str) -> tuple[Response, int]:
    """Get click-to-dial call history."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.click_to_dial import ClickToDialEngine

            engine = ClickToDialEngine(pbx_core.database, pbx_core.config, pbx_core)
            history = engine.get_call_history(extension)
            return send_json({"history": history}), 200
        except Exception as e:
            logger.error(f"Error getting click-to-dial history: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/click-to-dial/call/<extension>", methods=["POST"])
@require_auth
def click_to_dial_call(extension: str) -> tuple[Response, int]:
    """Initiate click-to-dial call."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            destination = body.get("destination")
            source = body.get("source", "web")

            from pbx.features.click_to_dial import ClickToDialEngine

            engine = ClickToDialEngine(pbx_core.database, pbx_core.config, pbx_core)
            call_id = engine.initiate_call(extension, destination, source)

            if call_id:
                return send_json({"call_id": call_id, "success": True}), 200
            return send_json({"error": "Failed to initiate call"}, 500), 500
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error initiating click-to-dial call: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/click-to-dial/config/<extension>", methods=["POST"])
@require_auth
def update_click_to_dial_config(extension: str) -> tuple[Response, int]:
    """Update click-to-dial configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.click_to_dial import ClickToDialEngine

            engine = ClickToDialEngine(pbx_core.database, pbx_core.config, pbx_core)
            if engine.update_config(extension, body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to update config"}, 500), 500
        except Exception as e:
            logger.error(f"Error updating click-to-dial config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


# =============================================================================
# Team Messaging
# =============================================================================


@framework_bp.route("/team-messaging/channels", methods=["GET"])
@require_auth
def get_team_channels() -> tuple[Response, int]:
    """Get all team messaging channels."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(pbx_core.database, pbx_core.config)
            channels = engine.get_all_channels()
            return send_json({"channels": channels}), 200
        except Exception as e:
            logger.error(f"Error getting team channels: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/team-messaging/messages/<channel_id>", methods=["GET"])
@require_auth
def get_team_messages(channel_id: str) -> tuple[Response, int]:
    """Get team messages for channel."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(pbx_core.database, pbx_core.config)
            messages = engine.get_channel_messages(int(channel_id))
            return send_json({"messages": messages}), 200
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error getting team messages: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/team-messaging/create-channel", methods=["POST"])
@require_auth
def create_team_channel() -> tuple[Response, int]:
    """Create team messaging channel."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(pbx_core.database, pbx_core.config)
            channel_id = engine.create_channel(body)
            if channel_id:
                return send_json({"channel_id": channel_id, "success": True}), 200
            return send_json({"error": "Failed to create channel"}, 500), 500
        except Exception as e:
            logger.error(f"Error creating team channel: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/team-messaging/send-message", methods=["POST"])
@require_auth
def send_team_message() -> tuple[Response, int]:
    """Send team message."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.team_collaboration import TeamMessagingEngine

            engine = TeamMessagingEngine(pbx_core.database, pbx_core.config)
            message_id = engine.send_message(body)
            if message_id:
                return send_json({"message_id": message_id, "success": True}), 200
            return send_json({"error": "Failed to send message"}, 500), 500
        except Exception as e:
            logger.error(f"Error sending team message: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


# =============================================================================
# Nomadic E911
# =============================================================================


@framework_bp.route("/nomadic-e911/sites", methods=["GET"])
@require_auth
def get_e911_sites() -> tuple[Response, int]:
    """Get all E911 site configurations."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            sites = engine.get_all_sites()
            return send_json({"sites": sites}), 200
        except Exception as e:
            logger.error(f"Error getting E911 sites: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/location/<extension>", methods=["GET"])
@require_auth
def get_e911_location(extension: str) -> tuple[Response, int]:
    """Get E911 location for extension."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            location = engine.get_location(extension)
            if location:
                return send_json(location), 200
            return send_json({"error": "Location not found"}, 404), 404
        except Exception as e:
            logger.error(f"Error getting E911 location: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/locations", methods=["GET"])
@require_auth
def get_all_e911_locations() -> tuple[Response, int]:
    """Get current E911 locations for all extensions."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            locations = engine.get_all_locations()
            return send_json({"locations": locations}), 200
        except Exception as e:
            logger.error(f"Error getting all E911 locations: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/history/<extension>", methods=["GET"])
@require_auth
def get_e911_history(extension: str) -> tuple[Response, int]:
    """Get E911 location history for extension."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            history = engine.get_location_history(extension)
            return send_json({"history": history}), 200
        except Exception as e:
            logger.error(f"Error getting E911 history: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/history", methods=["GET"])
@require_auth
def get_all_e911_history() -> tuple[Response, int]:
    """Get E911 location history for all extensions."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            history = engine.get_all_location_history()
            return send_json({"history": history}), 200
        except Exception as e:
            logger.error(f"Error getting all E911 history: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/update-location/<extension>", methods=["POST"])
@require_auth
def update_e911_location(extension: str) -> tuple[Response, int]:
    """Update E911 location for extension."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            if engine.update_location(extension, body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to update location"}, 500), 500
        except Exception as e:
            logger.error(f"Error updating E911 location: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/detect-location/<extension>", methods=["POST"])
@require_auth
def detect_e911_location(extension: str) -> tuple[Response, int]:
    """Auto-detect E911 location for extension by IP."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            ip_address = body.get("ip_address")
            if not ip_address:
                return send_json({"error": "IP address required"}, 400), 400

            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            location = engine.detect_location_by_ip(extension, ip_address)
            if location:
                return send_json(location), 200
            return send_json({"error": "Location could not be detected"}, 404), 404
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error detecting E911 location: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/create-site", methods=["POST"])
@require_auth
def create_e911_site() -> tuple[Response, int]:
    """Create E911 site configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            if engine.create_site_config(body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to create site"}, 500), 500
        except Exception as e:
            logger.error(f"Error creating E911 site: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/sites/<int:site_id>", methods=["PUT"])
@require_auth
def update_e911_site(site_id: int) -> tuple[Response, int]:
    """Update an existing E911 site configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            if engine.update_site_config(site_id, body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to update site"}, 500), 500
        except Exception as e:
            logger.error(f"Error updating E911 site: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/nomadic-e911/sites/<int:site_id>", methods=["DELETE"])
@require_auth
def delete_e911_site(site_id: int) -> tuple[Response, int]:
    """Delete an E911 site configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.nomadic_e911 import NomadicE911Engine

            engine = NomadicE911Engine(pbx_core.database, pbx_core.config)
            if engine.delete_site_config(site_id):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to delete site"}, 500), 500
        except Exception as e:
            logger.error(f"Error deleting E911 site: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


# =============================================================================
# Integrations (framework level)
# =============================================================================


@framework_bp.route("/integrations/hubspot", methods=["GET"])
@require_auth
def get_hubspot_config() -> tuple[Response, int]:
    """Get HubSpot integration configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.crm_integrations import HubSpotIntegration

            integration = HubSpotIntegration(pbx_core.database, pbx_core.config)
            config = integration.get_config()
            if config:
                return send_json(config), 200
            return send_json({"enabled": False}), 200
        except Exception as e:
            logger.error(f"Error getting HubSpot config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/integrations/zendesk", methods=["GET"])
@require_auth
def get_zendesk_config() -> tuple[Response, int]:
    """Get Zendesk integration configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.crm_integrations import ZendeskIntegration

            integration = ZendeskIntegration(pbx_core.database, pbx_core.config)
            config = integration.get_config()
            if config:
                return send_json(config), 200
            return send_json({"enabled": False}), 200
        except Exception as e:
            logger.error(f"Error getting Zendesk config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/integrations/activity-log", methods=["GET"])
@require_auth
def get_integration_activity() -> tuple[Response, int]:
    """Get integration activity log."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            # Query integration activity log directly from database
            result = pbx_core.database.execute(
                """SELECT id, integration_type, action, status, details, created_at FROM integration_activity_log
                   ORDER BY created_at DESC LIMIT 100"""
            )

            activities = [
                {
                    "integration_type": row[1],
                    "action": row[2],
                    "status": row[3],
                    "details": row[4],
                    "created_at": row[5],
                }
                for row in result or []
            ]

            return send_json({"activities": activities}), 200
        except Exception as e:
            logger.error(f"Error getting integration activity: {e}")
            # Return empty activities instead of error to prevent UI errors
            return send_json({"activities": []}), 200
    else:
        # Return empty activities when database is not available
        return send_json({"activities": []}), 200


@framework_bp.route("/integrations/hubspot/config", methods=["POST"])
@require_auth
def update_hubspot_config() -> tuple[Response, int]:
    """Update HubSpot integration configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.crm_integrations import HubSpotIntegration

            integration = HubSpotIntegration(pbx_core.database, pbx_core.config)
            if integration.update_config(body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to update config"}, 500), 500
        except Exception as e:
            logger.error(f"Error updating HubSpot config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/integrations/zendesk/config", methods=["POST"])
@require_auth
def update_zendesk_config() -> tuple[Response, int]:
    """Update Zendesk integration configuration."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.crm_integrations import ZendeskIntegration

            integration = ZendeskIntegration(pbx_core.database, pbx_core.config)
            if integration.update_config(body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to update config"}, 500), 500
        except Exception as e:
            logger.error(f"Error updating Zendesk config: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/integrations/activity-log/clear", methods=["POST"])
@require_admin
def clear_integration_activity() -> tuple[Response, int]:
    """Clear old integration activity log entries."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            # Delete entries older than 30 days
            cutoff_date = datetime.now(UTC) - timedelta(days=30)
            delete_query = """DELETE FROM integration_activity_log
                   WHERE created_at < %s"""
            pbx_core.database.execute(
                delete_query,
                (cutoff_date.isoformat(),),
            )

            return send_json(
                {
                    "success": True,
                    "message": "Old activity log entries cleared successfully",
                }
            ), 200
        except Exception as e:
            logger.error(f"Error clearing integration activity: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


# =============================================================================
# Compliance
# =============================================================================

# GDPR Handlers - COMMENTED OUT (not required for US-only operations)
# These handlers are not active (not required for US-only operations).
#
# def get_gdpr_consents(extension): ...
# def record_gdpr_consent(): ...
# def withdraw_gdpr_consent(): ...
# def create_gdpr_request(): ...
# def get_gdpr_requests(): ...

# PCI DSS Handlers - COMMENTED OUT (not required for US-only operations)
# These handlers are not active.
#
# def get_pci_audit_log(): ...
# def log_pci_event(): ...


@framework_bp.route("/compliance/gdpr/consents", methods=["GET"])
@require_auth
def get_gdpr_consents() -> tuple[Response, int]:
    """Get GDPR consent records."""
    extension = request.args.get("extension", "")
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.compliance_framework import GDPRComplianceEngine

            engine = GDPRComplianceEngine(pbx_core.database, pbx_core.config)
            consents = engine.get_consent_status(extension)
            return send_json({"consents": consents}), 200
        except Exception as e:
            logger.error(f"Error getting GDPR consents: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/compliance/gdpr/requests", methods=["GET"])
@require_auth
def get_gdpr_requests() -> tuple[Response, int]:
    """Get pending GDPR data requests."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.compliance_framework import GDPRComplianceEngine

            engine = GDPRComplianceEngine(pbx_core.database, pbx_core.config)
            requests_list = engine.get_pending_requests()
            return send_json({"requests": requests_list}), 200
        except Exception as e:
            logger.error(f"Error getting GDPR requests: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/compliance/soc2/controls", methods=["GET"])
@require_auth
def get_soc2_controls() -> tuple[Response, int]:
    """Get SOC 2 type 2 controls."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            engine = SOC2ComplianceEngine(pbx_core.database, pbx_core.config)
            controls = engine.get_all_controls()
            return send_json({"controls": controls}), 200
        except Exception as e:
            logger.error(f"Error getting SOC2 controls: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/compliance/pci/audit-log", methods=["GET"])
@require_auth
def get_pci_audit_log() -> tuple[Response, int]:
    """Get PCI DSS audit log."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            from pbx.features.compliance_framework import PCIDSSComplianceEngine

            engine = PCIDSSComplianceEngine(pbx_core.database, pbx_core.config)
            logs = engine.get_audit_log()
            return send_json({"logs": logs}), 200
        except Exception as e:
            logger.error(f"Error getting PCI audit log: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/compliance/gdpr/consent", methods=["POST"])
@require_auth
def record_gdpr_consent() -> tuple[Response, int]:
    """Record GDPR consent."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.compliance_framework import GDPRComplianceEngine

            engine = GDPRComplianceEngine(pbx_core.database, pbx_core.config)
            if engine.record_consent(body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to record consent"}, 500), 500
        except Exception as e:
            logger.error(f"Error recording GDPR consent: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/compliance/gdpr/withdraw", methods=["POST"])
@require_auth
def withdraw_gdpr_consent() -> tuple[Response, int]:
    """Withdraw GDPR consent."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.compliance_framework import GDPRComplianceEngine

            engine = GDPRComplianceEngine(pbx_core.database, pbx_core.config)
            if engine.withdraw_consent(body.get("extension"), body.get("consent_type")):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to withdraw consent"}, 500), 500
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error withdrawing GDPR consent: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/compliance/gdpr/request", methods=["POST"])
@require_auth
def create_gdpr_request() -> tuple[Response, int]:
    """Create GDPR data request."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.compliance_framework import GDPRComplianceEngine

            engine = GDPRComplianceEngine(pbx_core.database, pbx_core.config)
            request_id = engine.create_data_request(body)
            if request_id:
                return send_json({"request_id": request_id, "success": True}), 200
            return send_json({"error": "Failed to create request"}, 500), 500
        except Exception as e:
            logger.error(f"Error creating GDPR request: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/compliance/soc2/control", methods=["POST"])
@require_auth
def register_soc2_control() -> tuple[Response, int]:
    """Register SOC 2 type 2 control."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.compliance_framework import SOC2ComplianceEngine

            engine = SOC2ComplianceEngine(pbx_core.database, pbx_core.config)
            if engine.register_control(body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to register control"}, 500), 500
        except Exception as e:
            logger.error(f"Error registering SOC2 control: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


@framework_bp.route("/compliance/pci/log", methods=["POST"])
@require_auth
def log_pci_event() -> tuple[Response, int]:
    """Log PCI DSS event."""
    pbx_core = get_pbx_core()
    if pbx_core and pbx_core.database.enabled:
        try:
            body = get_request_body()
            from pbx.features.compliance_framework import PCIDSSComplianceEngine

            engine = PCIDSSComplianceEngine(pbx_core.database, pbx_core.config)
            if engine.log_audit_event(body):
                return send_json({"success": True}), 200
            return send_json({"error": "Failed to log event"}, 500), 500
        except Exception as e:
            logger.error(f"Error logging PCI event: {e}")
            return send_json({"error": str(e)}, 500), 500
    else:
        return send_json({"error": "Database not available"}, 500), 500


# =============================================================================
# BI Integration
# =============================================================================


@framework_bp.route("/bi-integration/datasets", methods=["GET"])
@require_auth
def get_bi_datasets() -> tuple[Response, int]:
    """Get available BI datasets."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.bi_integration import get_bi_integration

        bi = get_bi_integration(pbx_core.config if pbx_core else None)
        datasets = bi.get_available_datasets()
        return send_json({"datasets": datasets}), 200
    except Exception as e:
        logger.error(f"Error getting BI datasets: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/bi-integration/statistics", methods=["GET"])
@require_auth
def get_bi_statistics() -> tuple[Response, int]:
    """Get BI statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.bi_integration import get_bi_integration

        bi = get_bi_integration(pbx_core.config if pbx_core else None)
        stats = bi.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting BI statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/bi-integration/export/<dataset_name>", methods=["GET"])
@require_auth
def get_bi_export_status(dataset_name: str) -> tuple[Response, int]:
    """Get BI export status for a dataset."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.bi_integration import get_bi_integration

        bi = get_bi_integration(pbx_core.config if pbx_core else None)
        datasets = bi.get_available_datasets()
        dataset = next((d for d in datasets if d["name"] == dataset_name), None)
        if dataset:
            return send_json(dataset), 200
        return send_json({"error": "Dataset not found"}, 404), 404
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error getting export status: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/bi-integration/export", methods=["POST"])
@require_auth
def export_bi_dataset() -> tuple[Response, int]:
    """Export BI dataset."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        dataset_name = body.get("dataset")
        export_format = body.get("format", "csv")

        if not dataset_name:
            return send_json({"error": "Dataset name required"}, 400), 400

        from pbx.features.bi_integration import ExportFormat, get_bi_integration

        bi = get_bi_integration(pbx_core.config if pbx_core else None)

        # Convert format string to enum
        format_enum = ExportFormat.CSV
        if export_format.lower() == "json":
            format_enum = ExportFormat.JSON
        elif export_format.lower() == "excel":
            format_enum = ExportFormat.EXCEL

        result = bi.export_dataset(dataset_name, format_enum)
        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error exporting dataset: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/bi-integration/dataset", methods=["POST"])
@require_admin
def create_bi_dataset() -> tuple[Response, int]:
    """Create custom BI dataset."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        name = body.get("name")
        query = body.get("query")

        if not name or not query:
            return send_json({"error": "Name and query required"}, 400), 400

        from pbx.features.bi_integration import get_bi_integration

        bi = get_bi_integration(pbx_core.config if pbx_core else None)
        bi.create_custom_dataset(name, query)
        return send_json({"success": True, "dataset": name}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error creating dataset: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/bi-integration/test-connection", methods=["POST"])
@require_auth
def test_bi_connection() -> tuple[Response, int]:
    """Test BI provider connection."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        provider = body.get("provider", "tableau")
        credentials = body.get("credentials", {})

        from pbx.features.bi_integration import BIProvider, get_bi_integration

        bi = get_bi_integration(pbx_core.config if pbx_core else None)

        # Convert provider string to enum
        provider_enum = BIProvider.TABLEAU
        if provider.lower() == "powerbi":
            provider_enum = BIProvider.POWER_BI
        elif provider.lower() == "looker":
            provider_enum = BIProvider.LOOKER

        result = bi.test_connection(provider_enum, credentials)
        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error testing BI connection: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Call Tagging
# =============================================================================


@framework_bp.route("/call-tagging/tags", methods=["GET"])
@require_auth
def get_call_tags() -> tuple[Response, int]:
    """Get all call tags."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_tagging import get_call_tagging

        tagging = get_call_tagging(pbx_core.config if pbx_core else None)
        tags = tagging.get_all_tags()
        return send_json({"tags": tags}), 200
    except Exception as e:
        logger.error(f"Error getting call tags: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-tagging/rules", methods=["GET"])
@require_auth
def get_tagging_rules() -> tuple[Response, int]:
    """Get tagging rules."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_tagging import get_call_tagging

        tagging = get_call_tagging(pbx_core.config if pbx_core else None)
        rules = tagging.get_all_rules()
        return send_json({"rules": rules}), 200
    except Exception as e:
        logger.error(f"Error getting tagging rules: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-tagging/statistics", methods=["GET"])
@require_auth
def get_tagging_statistics() -> tuple[Response, int]:
    """Get tagging statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_tagging import get_call_tagging

        tagging = get_call_tagging(pbx_core.config if pbx_core else None)
        stats = tagging.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting tagging statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-tagging/tag", methods=["POST"])
@require_auth
def create_call_tag() -> tuple[Response, int]:
    """Create new call tag."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        name = body.get("name")
        description = body.get("description", "")
        color = body.get("color", "#007bff")

        if not name:
            return send_json({"error": "Tag name required"}, 400), 400

        from pbx.features.call_tagging import get_call_tagging

        tagging = get_call_tagging(pbx_core.config if pbx_core else None)
        tag_id = tagging.create_tag(name, description, color)
        return send_json({"success": True, "tag_id": tag_id}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error creating tag: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-tagging/rule", methods=["POST"])
@require_auth
def create_tagging_rule() -> tuple[Response, int]:
    """Create tagging rule."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        name = body.get("name")
        conditions = body.get("conditions", [])
        tag_id = body.get("tag_id")
        priority = body.get("priority", 100)

        if not name or not tag_id:
            return send_json({"error": "Name and tag_id required"}, 400), 400

        from pbx.features.call_tagging import get_call_tagging

        tagging = get_call_tagging(pbx_core.config if pbx_core else None)
        rule_id = tagging.create_rule(name, conditions, tag_id, priority)
        return send_json({"success": True, "rule_id": rule_id}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error creating tagging rule: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-tagging/classify/<call_id>", methods=["POST"])
@require_auth
def classify_call(call_id: str) -> tuple[Response, int]:
    """Classify call with tags."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_tagging import get_call_tagging

        tagging = get_call_tagging(pbx_core.config if pbx_core else None)
        tags = tagging.classify_call(call_id)
        return send_json({"call_id": call_id, "tags": tags}), 200
    except Exception as e:
        logger.error(f"Error classifying call: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Call Blending
# =============================================================================


@framework_bp.route("/call-blending/agents", methods=["GET"])
@require_auth
def get_blending_agents() -> tuple[Response, int]:
    """Get all blending agents."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_blending import get_call_blending

        blending = get_call_blending(pbx_core.config if pbx_core else None)
        agents = blending.get_all_agents()
        return send_json({"agents": agents}), 200
    except Exception as e:
        logger.error(f"Error getting blending agents: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-blending/statistics", methods=["GET"])
@require_auth
def get_blending_statistics() -> tuple[Response, int]:
    """Get blending statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_blending import get_call_blending

        blending = get_call_blending(pbx_core.config if pbx_core else None)
        stats = blending.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting blending statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-blending/agent/<agent_id>", methods=["GET"])
@require_auth
def get_blending_agent_status(agent_id: str) -> tuple[Response, int]:
    """Get blending agent status."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_blending import get_call_blending

        blending = get_call_blending(pbx_core.config if pbx_core else None)
        status = blending.get_agent_status(agent_id)
        if status:
            return send_json(status), 200
        return send_json({"error": "Agent not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-blending/agent", methods=["POST"])
@require_auth
def register_blending_agent() -> tuple[Response, int]:
    """Register blending agent."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        agent_id = body.get("agent_id")
        extension = body.get("extension")

        if not agent_id or not extension:
            return send_json({"error": "agent_id and extension required"}, 400), 400

        from pbx.features.call_blending import get_call_blending

        blending = get_call_blending(pbx_core.config if pbx_core else None)
        result = blending.register_agent(agent_id, extension)
        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error registering agent: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-blending/agent/<agent_id>/mode", methods=["POST"])
@require_auth
def set_agent_mode(agent_id: str) -> tuple[Response, int]:
    """set blending agent mode."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        mode = body.get("mode", "blended")

        from pbx.features.call_blending import get_call_blending

        blending = get_call_blending(pbx_core.config if pbx_core else None)
        result = blending.set_agent_mode(agent_id, mode)
        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error setting agent mode: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Geo Redundancy
# =============================================================================


@framework_bp.route("/geo-redundancy/regions", methods=["GET"])
@require_auth
def get_geo_regions() -> tuple[Response, int]:
    """Get all geo regions."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.geographic_redundancy import get_geographic_redundancy

        geo = get_geographic_redundancy(pbx_core.config if pbx_core else None)
        regions = geo.get_all_regions()
        return send_json({"regions": regions}), 200
    except Exception as e:
        logger.error(f"Error getting geo regions: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/geo-redundancy/statistics", methods=["GET"])
@require_auth
def get_geo_statistics() -> tuple[Response, int]:
    """Get geo redundancy statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.geographic_redundancy import get_geographic_redundancy

        geo = get_geographic_redundancy(pbx_core.config if pbx_core else None)
        stats = geo.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting geo statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/geo-redundancy/region/<region_id>", methods=["GET"])
@require_auth
def get_geo_region_status(region_id: str) -> tuple[Response, int]:
    """Get geo region status."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.geographic_redundancy import get_geographic_redundancy

        geo = get_geographic_redundancy(pbx_core.config if pbx_core else None)
        status = geo.get_region_status(region_id)
        if status:
            return send_json(status), 200
        return send_json({"error": "Region not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error getting region status: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/geo-redundancy/region", methods=["POST"])
@require_auth
def create_geo_region() -> tuple[Response, int]:
    """Create geo region."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        region_id = body.get("region_id")
        name = body.get("name")
        location = body.get("location")

        if not region_id or not name or not location:
            return send_json({"error": "region_id, name, and location required"}, 400), 400

        from pbx.features.geographic_redundancy import get_geographic_redundancy

        geo = get_geographic_redundancy(pbx_core.config if pbx_core else None)
        result = geo.create_region(region_id, name, location)
        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error creating region: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/geo-redundancy/region/<region_id>/failover", methods=["POST"])
@require_admin
def trigger_geo_failover(region_id: str) -> tuple[Response, int]:
    """Trigger geo failover for a region."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.geographic_redundancy import get_geographic_redundancy

        geo = get_geographic_redundancy(pbx_core.config if pbx_core else None)
        result = geo.trigger_failover(region_id)
        return send_json(result), 200
    except Exception as e:
        logger.error(f"Error triggering failover: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Conversational AI
# =============================================================================


@framework_bp.route("/conversational-ai/config", methods=["GET"])
@require_auth
def get_ai_config() -> tuple[Response, int]:
    """Get AI configuration."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.conversational_ai import get_conversational_ai

        ai = get_conversational_ai(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        config = {
            "enabled": ai.enabled,
            "provider": ai.provider,
            "model": ai.model,
            "max_tokens": ai.max_tokens,
            "temperature": ai.temperature,
        }
        return send_json(config), 200
    except Exception as e:
        logger.error(f"Error getting AI config: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/conversational-ai/statistics", methods=["GET"])
@require_auth
def get_ai_statistics() -> tuple[Response, int]:
    """Get AI statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.conversational_ai import get_conversational_ai

        db_backend = getattr(pbx_core, "db", None) if pbx_core else None
        ai = get_conversational_ai(pbx_core.config if pbx_core else None, db_backend)
        stats = ai.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting AI statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/conversational-ai/conversations", methods=["GET"])
@require_auth
def get_ai_conversations() -> tuple[Response, int]:
    """Get active AI conversations."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.conversational_ai import get_conversational_ai

        ai = get_conversational_ai(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        conversations = [
            {
                "call_id": conv.call_id,
                "caller_id": conv.caller_id,
                "started_at": conv.started_at.isoformat(),
                "intent": conv.intent,
                "message_count": len(conv.messages),
            }
            for conv in ai.active_conversations.values()
        ]
        return send_json({"conversations": conversations}), 200
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/conversational-ai/history", methods=["GET"])
@require_auth
def get_ai_conversation_history() -> tuple[Response, int]:
    """Get conversation history from database."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.conversational_ai import get_conversational_ai

        db_backend = getattr(pbx_core, "db", None) if pbx_core else None
        ai = get_conversational_ai(pbx_core.config if pbx_core else None, db_backend)

        # Get limit from query parameters
        limit = int(request.args.get("limit", 100))

        history = ai.get_conversation_history(limit)
        return send_json({"history": history}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error getting conversation history: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/conversational-ai/conversation", methods=["POST"])
@require_auth
def start_ai_conversation() -> tuple[Response, int]:
    """Start AI conversation."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        call_id = body.get("call_id")
        caller_id = body.get("caller_id")

        if not call_id or not caller_id:
            return send_json({"error": "call_id and caller_id required"}, 400), 400

        from pbx.features.conversational_ai import get_conversational_ai

        ai = get_conversational_ai(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        context = ai.start_conversation(call_id, caller_id)

        return send_json(
            {
                "success": True,
                "call_id": context.call_id,
                "started_at": context.started_at.isoformat(),
            }
        ), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error starting conversation: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/conversational-ai/process", methods=["POST"])
@require_auth
def process_ai_input() -> tuple[Response, int]:
    """Process user input in AI conversation."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        call_id = body.get("call_id")
        user_input = body.get("input")

        if not call_id or not user_input:
            return send_json({"error": "call_id and input required"}, 400), 400

        from pbx.features.conversational_ai import get_conversational_ai

        ai = get_conversational_ai(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        result = ai.process_user_input(call_id, user_input)

        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error processing input: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/conversational-ai/config", methods=["POST"])
@require_admin
def configure_ai_provider() -> tuple[Response, int]:
    """Configure AI provider."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        provider = body.get("provider")
        api_key = body.get("api_key")

        if not provider or not api_key:
            return send_json({"error": "provider and api_key required"}, 400), 400

        from pbx.features.conversational_ai import get_conversational_ai

        ai = get_conversational_ai(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        ai.configure_provider(provider, api_key, **body.get("options", {}))

        return send_json({"success": True, "provider": provider}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error configuring provider: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Predictive Dialing
# =============================================================================


@framework_bp.route("/predictive-dialing/campaigns", methods=["GET"])
@require_auth
def get_dialing_campaigns() -> tuple[Response, int]:
    """Get all dialing campaigns."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.predictive_dialing import get_predictive_dialer

        dialer = get_predictive_dialer(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        campaigns = [
            {
                "campaign_id": c.campaign_id,
                "name": c.name,
                "status": c.status.value,
                "dialing_mode": c.dialing_mode.value,
                "total_contacts": c.total_contacts,
                "contacts_completed": c.contacts_completed,
                "successful_calls": c.successful_calls,
            }
            for c in dialer.campaigns.values()
        ]
        return send_json({"campaigns": campaigns}), 200
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/predictive-dialing/statistics", methods=["GET"])
@require_auth
def get_dialing_statistics() -> tuple[Response, int]:
    """Get dialing statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.predictive_dialing import get_predictive_dialer

        dialer = get_predictive_dialer(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        stats = dialer.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting dialing statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/predictive-dialing/campaign/<campaign_id>", methods=["GET"])
@require_auth
def get_campaign_details(campaign_id: str) -> tuple[Response, int]:
    """Get campaign details."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.predictive_dialing import get_predictive_dialer

        dialer = get_predictive_dialer(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        stats = dialer.get_campaign_statistics(campaign_id)
        if stats:
            return send_json(stats), 200
        return send_json({"error": "Campaign not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error getting campaign details: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/predictive-dialing/campaign", methods=["POST"])
@require_auth
def create_dialing_campaign() -> tuple[Response, int]:
    """Create dialing campaign."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        campaign_id = body.get("campaign_id")
        name = body.get("name")
        dialing_mode = body.get("dialing_mode", "progressive")

        if not campaign_id or not name:
            return send_json({"error": "campaign_id and name required"}, 400), 400

        from pbx.features.predictive_dialing import DialingMode, get_predictive_dialer

        dialer = get_predictive_dialer(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )

        # Convert mode string to enum
        mode_enum = DialingMode.PROGRESSIVE
        if dialing_mode.lower() == "preview":
            mode_enum = DialingMode.PREVIEW
        elif dialing_mode.lower() == "predictive":
            mode_enum = DialingMode.PREDICTIVE
        elif dialing_mode.lower() == "power":
            mode_enum = DialingMode.POWER

        campaign = dialer.create_campaign(
            campaign_id,
            name,
            mode_enum,
        )

        # Note: max_attempts and retry_interval are set as defaults in Campaign.__init__
        # If client provides custom values, they are not currently persisted to database
        if body.get("max_attempts") is not None or body.get("retry_interval") is not None:
            logger.warning(
                f"Received max_attempts/retry_interval for campaign {campaign_id}, "
                "but these parameters are not currently persisted by the "
                "predictive dialing backend; using default settings (max_attempts=3, retry_interval=3600)."
            )

        return send_json(
            {"success": True, "campaign_id": campaign.campaign_id, "name": campaign.name}
        ), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error creating campaign: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/predictive-dialing/contacts", methods=["POST"])
@require_auth
def add_campaign_contacts() -> tuple[Response, int]:
    """Add contacts to dialing campaign."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        campaign_id = body.get("campaign_id")
        contacts = body.get("contacts", [])

        if not campaign_id or not contacts:
            return send_json({"error": "campaign_id and contacts required"}, 400), 400

        from pbx.features.predictive_dialing import get_predictive_dialer

        dialer = get_predictive_dialer(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        count = dialer.add_contacts(campaign_id, contacts)

        return send_json({"success": True, "contacts_added": count}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error adding contacts: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/predictive-dialing/campaign/<campaign_id>/start", methods=["POST"])
@require_auth
def start_dialing_campaign(campaign_id: str) -> tuple[Response, int]:
    """Start dialing campaign."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.predictive_dialing import get_predictive_dialer

        dialer = get_predictive_dialer(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        dialer.start_campaign(campaign_id)
        return send_json({"success": True, "status": "running"}), 200
    except Exception as e:
        logger.error(f"Error starting campaign: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/predictive-dialing/campaign/<campaign_id>/pause", methods=["POST"])
@require_auth
def pause_dialing_campaign(campaign_id: str) -> tuple[Response, int]:
    """Pause dialing campaign."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.predictive_dialing import get_predictive_dialer

        dialer = get_predictive_dialer(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        dialer.pause_campaign(campaign_id)
        return send_json({"success": True, "status": "paused"}), 200
    except Exception as e:
        logger.error(f"Error pausing campaign: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Voice Biometrics
# =============================================================================


@framework_bp.route("/voice-biometrics/profiles", methods=["GET"])
@require_auth
def get_voice_profiles() -> tuple[Response, int]:
    """Get all voice profiles."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.voice_biometrics import get_voice_biometrics

        vb = get_voice_biometrics(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        profiles = [
            {
                "user_id": p.user_id,
                "extension": p.extension,
                "status": p.status,
                "enrollment_completed": p.enrollment_completed,
                "created_at": p.created_at.isoformat(),
                "verification_count": p.verification_count,
                "fraud_attempts": p.fraud_attempts,
            }
            for p in vb.profiles.values()
        ]
        return send_json({"profiles": profiles}), 200
    except Exception as e:
        logger.error(f"Error getting voice profiles: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voice-biometrics/statistics", methods=["GET"])
@require_auth
def get_voice_statistics() -> tuple[Response, int]:
    """Get voice biometrics statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.voice_biometrics import get_voice_biometrics

        vb = get_voice_biometrics(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        stats = vb.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting voice statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voice-biometrics/profile/<user_id>", methods=["GET"])
@require_auth
def get_voice_profile(user_id: str) -> tuple[Response, int]:
    """Get voice profile for a user."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.voice_biometrics import get_voice_biometrics

        vb = get_voice_biometrics(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        profile = vb.get_profile(user_id)
        if profile:
            return send_json(
                {
                    "user_id": profile.user_id,
                    "extension": profile.extension,
                    "status": profile.status,
                    "enrollment_completed": profile.enrollment_completed,
                    "created_at": profile.created_at.isoformat(),
                    "verification_count": profile.verification_count,
                    "fraud_attempts": profile.fraud_attempts,
                }
            ), 200
        return send_json({"error": "Profile not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error getting voice profile: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voice-biometrics/profile", methods=["POST"])
@require_auth
def create_voice_profile() -> tuple[Response, int]:
    """Create voice profile."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        user_id = body.get("user_id")
        extension = body.get("extension")

        if not user_id or not extension:
            return send_json({"error": "user_id and extension required"}, 400), 400

        from pbx.features.voice_biometrics import get_voice_biometrics

        vb = get_voice_biometrics(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        profile = vb.create_profile(user_id, extension)

        return send_json(
            {
                "success": True,
                "user_id": profile.user_id,
                "extension": profile.extension,
                "status": profile.status,
            }
        ), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error creating voice profile: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voice-biometrics/enroll", methods=["POST"])
@require_auth
def start_voice_enrollment() -> tuple[Response, int]:
    """Start voice enrollment."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        user_id = body.get("user_id")

        if not user_id:
            return send_json({"error": "user_id required"}, 400), 400

        from pbx.features.voice_biometrics import get_voice_biometrics

        vb = get_voice_biometrics(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        result = vb.start_enrollment(user_id)

        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error starting enrollment: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voice-biometrics/verify", methods=["POST"])
@require_auth
def verify_speaker() -> tuple[Response, int]:
    """Verify speaker identity."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        user_id = body.get("user_id")
        # In a real implementation, audio_data would be base64 encoded string
        audio_data_str = body.get("audio_data", "")

        if not user_id:
            return send_json({"error": "user_id required"}, 400), 400

        # Convert base64 encoded audio data to bytes if provided
        if audio_data_str:
            try:
                audio_data = base64.b64decode(audio_data_str)
            except ValueError as e:
                return send_json({"error": f"Invalid base64 audio data: {e!s}"}, 400), 400
        else:
            audio_data = b""

        from pbx.features.voice_biometrics import get_voice_biometrics

        vb = get_voice_biometrics(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        result = vb.verify_speaker(user_id, audio_data)

        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error verifying speaker: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voice-biometrics/profile/<user_id>", methods=["DELETE"])
@require_auth
def delete_voice_profile(user_id: str) -> tuple[Response, int]:
    """Delete voice profile."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.voice_biometrics import get_voice_biometrics

        vb = get_voice_biometrics(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        success = vb.delete_profile(user_id)
        if success:
            return send_json({"success": True}), 200
        return send_json({"error": "Profile not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error deleting voice profile: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Call Quality Prediction
# =============================================================================


@framework_bp.route("/call-quality-prediction/predictions", methods=["GET"])
@require_auth
def get_quality_predictions() -> tuple[Response, int]:
    """Get all quality predictions."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_quality_prediction import get_quality_prediction

        qp = get_quality_prediction(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        predictions = qp.active_predictions.copy()
        return send_json({"predictions": predictions}), 200
    except Exception as e:
        logger.error(f"Error getting quality predictions: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-quality-prediction/statistics", methods=["GET"])
@require_auth
def get_quality_statistics() -> tuple[Response, int]:
    """Get quality prediction statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_quality_prediction import get_quality_prediction

        qp = get_quality_prediction(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        stats = qp.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting quality statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-quality-prediction/alerts", methods=["GET"])
@require_auth
def get_quality_alerts() -> tuple[Response, int]:
    """Get active quality alerts from database."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_quality_prediction import get_quality_prediction

        db_backend = getattr(pbx_core, "db", None) if pbx_core else None
        qp = get_quality_prediction(pbx_core.config if pbx_core else None, db_backend)

        if qp.db:
            alerts = qp.db.get_active_alerts()
            return send_json({"alerts": alerts}), 200
        return send_json({"alerts": [], "message": "Database not configured"}), 200
    except Exception as e:
        logger.error(f"Error getting quality alerts: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-quality-prediction/prediction/<call_id>", methods=["GET"])
@require_auth
def get_call_prediction(call_id: str) -> tuple[Response, int]:
    """Get quality prediction for a specific call."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_quality_prediction import get_quality_prediction

        qp = get_quality_prediction(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        prediction = qp.get_prediction(call_id)
        if prediction:
            return send_json(prediction), 200
        return send_json({"error": "Prediction not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error getting call prediction: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-quality-prediction/metrics", methods=["POST"])
@require_auth
def collect_quality_metrics() -> tuple[Response, int]:
    """Collect quality metrics for a call."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        call_id = body.get("call_id")

        if not call_id:
            return send_json({"error": "call_id required"}, 400), 400

        from pbx.features.call_quality_prediction import NetworkMetrics, get_quality_prediction

        qp = get_quality_prediction(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )

        # Create metrics object from request
        metrics = NetworkMetrics()
        metrics.packet_loss = body.get("packet_loss", 0.0)
        metrics.jitter = body.get("jitter", 0.0)
        metrics.latency = body.get("latency", 0.0)
        metrics.bandwidth = body.get("bandwidth", 0.0)

        qp.collect_metrics(call_id, metrics)

        return send_json({"success": True, "call_id": call_id}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error collecting metrics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/call-quality-prediction/train", methods=["POST"])
@require_auth
def train_quality_model() -> tuple[Response, int]:
    """Train quality prediction model."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        historical_data = body.get("data", [])

        if not historical_data:
            return send_json({"error": "historical data required"}, 400), 400

        from pbx.features.call_quality_prediction import get_quality_prediction

        qp = get_quality_prediction(
            pbx_core.config if pbx_core else None,
            getattr(pbx_core, "db", None) if pbx_core else None,
        )
        qp.train_model(historical_data)

        return send_json({"success": True, "samples_trained": len(historical_data)}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error training model: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Video Codec
# =============================================================================


@framework_bp.route("/video-codec/codecs", methods=["GET"])
@require_auth
def get_video_codecs() -> tuple[Response, int]:
    """Get supported video codecs."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.video_codec import get_video_codec_manager

        vc = get_video_codec_manager(pbx_core.config if pbx_core else None)
        codecs = vc.available_codecs
        return send_json({"codecs": codecs}), 200
    except Exception as e:
        logger.error(f"Error getting video codecs: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/video-codec/statistics", methods=["GET"])
@require_auth
def get_video_statistics() -> tuple[Response, int]:
    """Get video codec statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.video_codec import get_video_codec_manager

        vc = get_video_codec_manager(pbx_core.config if pbx_core else None)
        stats = vc.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting video statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/video-codec/bandwidth", methods=["POST"])
@require_auth
def calculate_video_bandwidth() -> tuple[Response, int]:
    """Calculate required video bandwidth."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        resolution_input = body.get("resolution", [1920, 1080])
        framerate = body.get("framerate", 30)
        codec = body.get("codec", "h264")
        quality = body.get("quality", "high")

        # Validate resolution input
        if not isinstance(resolution_input, list | tuple) or len(resolution_input) != 2:
            return send_json({"error": "resolution must be [width, height]"}, 400), 400

        try:
            resolution = (int(resolution_input[0]), int(resolution_input[1]))
        except (ValueError, TypeError):
            return send_json({"error": "resolution values must be numeric"}, 400), 400

        from pbx.features.video_codec import get_video_codec_manager

        vc = get_video_codec_manager(pbx_core.config if pbx_core else None)
        bandwidth = vc.calculate_bandwidth(resolution, framerate, quality)

        return send_json(
            {
                "resolution": list(resolution),
                "framerate": framerate,
                "codec": codec,
                "quality": quality,
                "bandwidth_mbps": bandwidth,
            }
        ), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error calculating bandwidth: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Mobile Portability
# =============================================================================


@framework_bp.route("/mobile-portability/mappings", methods=["GET"])
@require_auth
def get_mobile_mappings() -> tuple[Response, int]:
    """Get all mobile number mappings."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.mobile_number_portability import get_mobile_number_portability

        mnp = get_mobile_number_portability(pbx_core.config if pbx_core else None)
        mappings = [
            {"business_number": number, **details}
            for number, details in mnp.number_mappings.items()
        ]
        return send_json({"mappings": mappings}), 200
    except Exception as e:
        logger.error(f"Error getting mobile mappings: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/mobile-portability/statistics", methods=["GET"])
@require_auth
def get_mobile_statistics() -> tuple[Response, int]:
    """Get mobile portability statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.mobile_number_portability import get_mobile_number_portability

        mnp = get_mobile_number_portability(pbx_core.config if pbx_core else None)
        stats = mnp.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting mobile statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/mobile-portability/mapping/<business_number>", methods=["GET"])
@require_auth
def get_mobile_mapping(business_number: str) -> tuple[Response, int]:
    """Get specific mobile number mapping."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.mobile_number_portability import get_mobile_number_portability

        mnp = get_mobile_number_portability(pbx_core.config if pbx_core else None)
        mapping = mnp.get_mapping(business_number)
        if mapping:
            return send_json(mapping), 200
        return send_json({"error": "Mapping not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error getting mobile mapping: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/mobile-portability/mapping", methods=["POST"])
@require_auth
def create_mobile_mapping() -> tuple[Response, int]:
    """Create mobile number mapping."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        business_number = body.get("business_number")
        extension = body.get("extension")
        mobile_device = body.get("mobile_device")

        if not all([business_number, extension, mobile_device]):
            return send_json(
                {"error": "business_number, extension, and mobile_device required"}, 400
            ), 400

        from pbx.features.mobile_number_portability import get_mobile_number_portability

        mnp = get_mobile_number_portability(pbx_core.config if pbx_core else None)
        result = mnp.map_number_to_mobile(
            business_number, extension, mobile_device, body.get("forward_to_mobile", True)
        )

        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error creating mobile mapping: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/mobile-portability/mapping/<business_number>/toggle", methods=["POST"])
@require_auth
def toggle_mobile_mapping(business_number: str) -> tuple[Response, int]:
    """Toggle mobile number mapping active state."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        active = body.get("active", True)

        from pbx.features.mobile_number_portability import get_mobile_number_portability

        mnp = get_mobile_number_portability(pbx_core.config if pbx_core else None)
        success = mnp.toggle_mapping(business_number, active)

        if success:
            return send_json({"success": True, "active": active}), 200
        return send_json({"error": "Mapping not found"}, 404), 404
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error toggling mobile mapping: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/mobile-portability/mapping/<business_number>", methods=["DELETE"])
@require_auth
def delete_mobile_mapping(business_number: str) -> tuple[Response, int]:
    """Delete mobile number mapping."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.mobile_number_portability import get_mobile_number_portability

        mnp = get_mobile_number_portability(pbx_core.config if pbx_core else None)
        success = mnp.remove_mapping(business_number)

        if success:
            return send_json({"success": True}), 200
        return send_json({"error": "Mapping not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error deleting mobile mapping: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Recording Analytics
# =============================================================================


@framework_bp.route("/recording-analytics/analyses", methods=["GET"])
@require_auth
def get_recording_analyses() -> tuple[Response, int]:
    """Get all recording analyses."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_recording_analytics import get_recording_analytics

        ra = get_recording_analytics(pbx_core.config if pbx_core else None)
        analyses = ra.analyses.copy()
        return send_json({"analyses": analyses}), 200
    except Exception as e:
        logger.error(f"Error getting recording analyses: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/recording-analytics/statistics", methods=["GET"])
@require_auth
def get_recording_statistics() -> tuple[Response, int]:
    """Get recording analytics statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_recording_analytics import get_recording_analytics

        ra = get_recording_analytics(pbx_core.config if pbx_core else None)
        stats = ra.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting recording statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/recording-analytics/analysis/<recording_id>", methods=["GET"])
@require_auth
def get_recording_analysis(recording_id: str) -> tuple[Response, int]:
    """Get specific recording analysis."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.call_recording_analytics import get_recording_analytics

        ra = get_recording_analytics(pbx_core.config if pbx_core else None)
        analysis = ra.get_analysis(recording_id)
        if analysis:
            return send_json(analysis), 200
        return send_json({"error": "Analysis not found"}, 404), 404
    except Exception as e:
        logger.error(f"Error getting recording analysis: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/recording-analytics/analyze", methods=["POST"])
@require_auth
def analyze_recording() -> tuple[Response, int]:
    """Analyze a recording."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        recording_id = body.get("recording_id")
        audio_path = body.get("audio_path")

        if not recording_id or not audio_path:
            return send_json({"error": "recording_id and audio_path required"}, 400), 400

        from pbx.features.call_recording_analytics import get_recording_analytics

        ra = get_recording_analytics(pbx_core.config if pbx_core else None)
        result = ra.analyze_recording(
            recording_id, audio_path, analysis_types=body.get("analysis_types")
        )

        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error analyzing recording: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/recording-analytics/search", methods=["POST"])
@require_auth
def search_recordings() -> tuple[Response, int]:
    """Search recordings."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        criteria = body.get("criteria", {})

        from pbx.features.call_recording_analytics import get_recording_analytics

        ra = get_recording_analytics(pbx_core.config if pbx_core else None)
        results = ra.search_recordings(criteria)

        return send_json({"results": results}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error searching recordings: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Voicemail Drop
# =============================================================================


@framework_bp.route("/voicemail-drop/messages", methods=["GET"])
@require_auth
def get_voicemail_messages() -> tuple[Response, int]:
    """Get all voicemail drop messages."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.predictive_voicemail_drop import get_voicemail_drop

        vd = get_voicemail_drop(pbx_core.config if pbx_core else None)
        messages = vd.list_messages()
        return send_json({"messages": messages}), 200
    except Exception as e:
        logger.error(f"Error getting voicemail messages: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voicemail-drop/statistics", methods=["GET"])
@require_auth
def get_voicemail_drop_statistics() -> tuple[Response, int]:
    """Get voicemail drop statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.predictive_voicemail_drop import get_voicemail_drop

        vd = get_voicemail_drop(pbx_core.config if pbx_core else None)
        stats = vd.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting voicemail drop statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voicemail-drop/message", methods=["POST"])
@require_auth
def add_voicemail_message() -> tuple[Response, int]:
    """Add voicemail drop message."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        message_id = body.get("message_id")
        name = body.get("name")
        audio_path = body.get("audio_path")

        if not all([message_id, name, audio_path]):
            return send_json({"error": "message_id, name, and audio_path required"}, 400), 400

        from pbx.features.predictive_voicemail_drop import get_voicemail_drop

        vd = get_voicemail_drop(pbx_core.config if pbx_core else None)
        vd.add_message(message_id, name, audio_path, duration=body.get("duration"))

        return send_json({"success": True, "message_id": message_id}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error adding voicemail message: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/voicemail-drop/drop", methods=["POST"])
@require_auth
def drop_voicemail() -> tuple[Response, int]:
    """Drop message to voicemail."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        call_id = body.get("call_id")
        message_id = body.get("message_id")

        if not call_id or not message_id:
            return send_json({"error": "call_id and message_id required"}, 400), 400

        from pbx.features.predictive_voicemail_drop import get_voicemail_drop

        vd = get_voicemail_drop(pbx_core.config if pbx_core else None)
        result = vd.drop_message(call_id, message_id)

        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error dropping voicemail: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# DNS SRV
# =============================================================================


@framework_bp.route("/dns-srv/records", methods=["GET"])
@require_auth
def get_srv_records() -> tuple[Response, int]:
    """Get SRV records."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.dns_srv_failover import get_dns_srv_failover

        dns = get_dns_srv_failover(pbx_core.config if pbx_core else None)
        # Get all cached records
        records = {}
        for key, record_list in dns.srv_cache.items():
            records[key] = [
                {"priority": r.priority, "weight": r.weight, "port": r.port, "target": r.target}
                for r in record_list
            ]
        return send_json({"records": records}), 200
    except Exception as e:
        logger.error(f"Error getting SRV records: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/dns-srv/statistics", methods=["GET"])
@require_auth
def get_dns_srv_statistics() -> tuple[Response, int]:
    """Get DNS SRV statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.dns_srv_failover import get_dns_srv_failover

        dns = get_dns_srv_failover(pbx_core.config if pbx_core else None)
        stats = dns.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting DNS SRV statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/dns-srv/lookup", methods=["POST"])
@require_auth
def lookup_srv() -> tuple[Response, int]:
    """Lookup SRV records."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        service = body.get("service")
        protocol = body.get("protocol", "tcp")
        domain = body.get("domain")

        if not service or not domain:
            return send_json({"error": "service and domain required"}, 400), 400

        from pbx.features.dns_srv_failover import get_dns_srv_failover

        dns = get_dns_srv_failover(pbx_core.config if pbx_core else None)
        records = dns.lookup_srv(service, protocol, domain)

        return send_json({"records": records}), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error looking up SRV: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# SBC (Session Border Controller)
# =============================================================================


@framework_bp.route("/sbc/statistics", methods=["GET"])
@require_auth
def get_sbc_statistics() -> tuple[Response, int]:
    """Get SBC statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.session_border_controller import get_sbc

        sbc = get_sbc(pbx_core.config if pbx_core else None)
        stats = sbc.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting SBC statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/sbc/relays", methods=["GET"])
@require_auth
def get_sbc_relays() -> tuple[Response, int]:
    """Get active RTP relays."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.session_border_controller import get_sbc

        sbc = get_sbc(pbx_core.config if pbx_core else None)
        relays = sbc.relay_sessions.copy()
        return send_json({"relays": relays}), 200
    except Exception as e:
        logger.error(f"Error getting SBC relays: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/sbc/relay", methods=["POST"])
@require_auth
def allocate_sbc_relay() -> tuple[Response, int]:
    """Allocate RTP relay."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        call_id = body.get("call_id")
        codec = body.get("codec", "PCMU")

        if not call_id:
            return send_json({"error": "call_id required"}, 400), 400

        from pbx.features.session_border_controller import get_sbc

        sbc = get_sbc(pbx_core.config if pbx_core else None)
        result = sbc.allocate_relay(call_id, codec)

        return send_json(result), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error allocating SBC relay: {e}")
        return send_json({"error": str(e)}, 500), 500


# =============================================================================
# Data Residency
# =============================================================================


@framework_bp.route("/data-residency/regions", methods=["GET"])
@require_auth
def get_data_regions() -> tuple[Response, int]:
    """Get configured data residency regions."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.data_residency_controls import get_data_residency

        dr = get_data_residency(pbx_core.config if pbx_core else None)
        regions = {region.value: config for region, config in dr.region_configs.items()}
        return send_json({"regions": regions}), 200
    except Exception as e:
        logger.error(f"Error getting data regions: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/data-residency/statistics", methods=["GET"])
@require_auth
def get_data_residency_statistics() -> tuple[Response, int]:
    """Get data residency statistics."""
    try:
        pbx_core = get_pbx_core()
        from pbx.features.data_residency_controls import get_data_residency

        dr = get_data_residency(pbx_core.config if pbx_core else None)
        stats = dr.get_statistics()
        return send_json(stats), 200
    except Exception as e:
        logger.error(f"Error getting data residency statistics: {e}")
        return send_json({"error": str(e)}, 500), 500


@framework_bp.route("/data-residency/location", methods=["POST"])
@require_auth
def get_storage_location() -> tuple[Response, int]:
    """Get storage location for data category."""
    try:
        pbx_core = get_pbx_core()
        body = get_request_body()
        category = body.get("category")
        user_region = body.get("user_region")

        if not category:
            return send_json({"error": "category required"}, 400), 400

        from pbx.features.data_residency_controls import get_data_residency

        dr = get_data_residency(pbx_core.config if pbx_core else None)
        location = dr.get_storage_location(category, user_region)

        return send_json(location), 200
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error getting storage location: {e}")
        return send_json({"error": str(e)}, 500), 500
