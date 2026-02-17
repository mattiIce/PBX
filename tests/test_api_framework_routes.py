"""Tests for Flask API framework routes.

Covers all endpoints in pbx/api/routes/framework.py including:
Speech Analytics, Video Conference, Click-to-Dial, Team Messaging,
Nomadic E911, Integrations, Compliance, BI Integration, Call Tagging,
Call Blending, Geo Redundancy, Conversational AI, Predictive Dialing,
Voice Biometrics, Call Quality Prediction, Video Codec, Mobile Portability,
Recording Analytics, Voicemail Drop, DNS SRV, SBC, and Data Residency.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient


AUTH_PATCH = "pbx.api.utils.verify_authentication"
AUTH_RETURN = (True, {"extension": "1001", "is_admin": True})
AUTH_NON_ADMIN = (True, {"extension": "1001", "is_admin": False})


def _json(response) -> dict:
    """Parse JSON from response."""
    return json.loads(response.data)


# =============================================================================
# Speech Analytics
# =============================================================================


@pytest.mark.unit
class TestSpeechAnalyticsRoutes:
    """Test speech analytics endpoints."""

    def test_get_configs_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.get_all_configs.return_value = [{"id": 1}]
            response = api_client.get("/api/framework/speech-analytics/configs")
            assert response.status_code == 200
            assert _json(response)["configs"] == [{"id": 1}]

    def test_get_configs_no_auth(self, api_client: FlaskClient) -> None:
        response = api_client.get("/api/framework/speech-analytics/configs")
        assert response.status_code == 401

    def test_get_configs_db_unavailable(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = False
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.get("/api/framework/speech-analytics/configs")
            assert response.status_code == 500
            assert "Database not available" in _json(response)["error"]

    def test_get_config_by_extension(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.get_config.return_value = {"extension": "1001"}
            response = api_client.get("/api/framework/speech-analytics/config/1001")
            assert response.status_code == 200

    def test_get_config_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.get_config.return_value = None
            response = api_client.get("/api/framework/speech-analytics/config/9999")
            assert response.status_code == 404

    def test_get_call_summary_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.get_call_summary.return_value = {"text": "summary"}
            response = api_client.get("/api/framework/speech-analytics/summary/call123")
            assert response.status_code == 200

    def test_get_call_summary_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.get_call_summary.return_value = None
            response = api_client.get("/api/framework/speech-analytics/summary/call999")
            assert response.status_code == 404

    def test_update_config_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.update_config.return_value = True
            response = api_client.post(
                "/api/framework/speech-analytics/config/1001",
                json={"enabled": True},
            )
            assert response.status_code == 200
            assert _json(response)["success"] is True

    def test_update_config_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.update_config.return_value = False
            response = api_client.post(
                "/api/framework/speech-analytics/config/1001",
                json={"enabled": True},
            )
            assert response.status_code == 500

    def test_analyze_sentiment_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.analyze_sentiment.return_value = {"score": 0.8}
            response = api_client.post(
                "/api/framework/speech-analytics/analyze-sentiment",
                json={"text": "great service"},
            )
            assert response.status_code == 200

    def test_analyze_sentiment_no_text(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/speech-analytics/analyze-sentiment",
                json={"text": ""},
            )
            assert response.status_code == 400

    def test_generate_summary_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.speech_analytics.SpeechAnalyticsEngine") as MockEngine:
            MockEngine.return_value.generate_summary.return_value = "Call summary text"
            response = api_client.post(
                "/api/framework/speech-analytics/generate-summary/call123",
                json={"transcript": "Hello, I need help."},
            )
            assert response.status_code == 200
            data = _json(response)
            assert data["call_id"] == "call123"

    def test_generate_summary_no_transcript(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/speech-analytics/generate-summary/call123",
                json={"transcript": ""},
            )
            assert response.status_code == 400


# =============================================================================
# Video Conference
# =============================================================================


@pytest.mark.unit
class TestVideoConferenceRoutes:
    """Test video conference endpoints."""

    def test_get_rooms_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_conferencing.VideoConferencingEngine") as MockEngine:
            MockEngine.return_value.get_all_rooms.return_value = [{"id": 1, "name": "Room1"}]
            response = api_client.get("/api/framework/video-conference/rooms")
            assert response.status_code == 200
            assert len(_json(response)["rooms"]) == 1

    def test_get_rooms_no_auth(self, api_client: FlaskClient) -> None:
        response = api_client.get("/api/framework/video-conference/rooms")
        assert response.status_code == 401

    def test_get_rooms_db_unavailable(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = False
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.get("/api/framework/video-conference/rooms")
            assert response.status_code == 500

    def test_get_room_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_conferencing.VideoConferencingEngine") as MockEngine:
            MockEngine.return_value.get_room.return_value = {"id": 1}
            MockEngine.return_value.get_room_participants.return_value = []
            response = api_client.get("/api/framework/video-conference/room/1")
            assert response.status_code == 200

    def test_get_room_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_conferencing.VideoConferencingEngine") as MockEngine:
            MockEngine.return_value.get_room.return_value = None
            response = api_client.get("/api/framework/video-conference/room/999")
            assert response.status_code == 404

    def test_create_room_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_conferencing.VideoConferencingEngine") as MockEngine:
            MockEngine.return_value.create_room.return_value = 42
            response = api_client.post(
                "/api/framework/video-conference/create-room",
                json={"name": "TestRoom"},
            )
            assert response.status_code == 200
            assert _json(response)["room_id"] == 42

    def test_create_room_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_conferencing.VideoConferencingEngine") as MockEngine:
            MockEngine.return_value.create_room.return_value = None
            response = api_client.post(
                "/api/framework/video-conference/create-room",
                json={"name": "TestRoom"},
            )
            assert response.status_code == 500

    def test_join_room_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_conferencing.VideoConferencingEngine") as MockEngine:
            MockEngine.return_value.join_room.return_value = True
            response = api_client.post(
                "/api/framework/video-conference/join/1",
                json={"user": "test"},
            )
            assert response.status_code == 200


# =============================================================================
# Click-to-Dial
# =============================================================================


@pytest.mark.unit
class TestClickToDialRoutes:
    """Test click-to-dial endpoints."""

    def test_get_configs_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.click_to_dial.ClickToDialEngine") as MockEngine:
            MockEngine.return_value.get_all_configs.return_value = [{"ext": "1001"}]
            response = api_client.get("/api/framework/click-to-dial/configs")
            assert response.status_code == 200
            assert "configs" in _json(response)

    def test_get_configs_no_auth(self, api_client: FlaskClient) -> None:
        response = api_client.get("/api/framework/click-to-dial/configs")
        assert response.status_code == 401

    def test_get_config_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.click_to_dial.ClickToDialEngine") as MockEngine:
            MockEngine.return_value.get_config.return_value = {"extension": "1001", "enabled": True}
            response = api_client.get("/api/framework/click-to-dial/config/1001")
            assert response.status_code == 200

    def test_get_config_default(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.click_to_dial.ClickToDialEngine") as MockEngine:
            MockEngine.return_value.get_config.return_value = None
            response = api_client.get("/api/framework/click-to-dial/config/1001")
            assert response.status_code == 200
            data = _json(response)
            assert data["extension"] == "1001"
            assert data["enabled"] is True

    def test_get_history(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.click_to_dial.ClickToDialEngine") as MockEngine:
            MockEngine.return_value.get_call_history.return_value = []
            response = api_client.get("/api/framework/click-to-dial/history/1001")
            assert response.status_code == 200
            assert _json(response)["history"] == []

    def test_initiate_call_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.click_to_dial.ClickToDialEngine") as MockEngine:
            MockEngine.return_value.initiate_call.return_value = "call-abc"
            response = api_client.post(
                "/api/framework/click-to-dial/call/1001",
                json={"destination": "5551234567"},
            )
            assert response.status_code == 200
            assert _json(response)["call_id"] == "call-abc"

    def test_initiate_call_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.click_to_dial.ClickToDialEngine") as MockEngine:
            MockEngine.return_value.initiate_call.return_value = None
            response = api_client.post(
                "/api/framework/click-to-dial/call/1001",
                json={"destination": "5551234567"},
            )
            assert response.status_code == 500

    def test_update_config_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.click_to_dial.ClickToDialEngine") as MockEngine:
            MockEngine.return_value.update_config.return_value = True
            response = api_client.post(
                "/api/framework/click-to-dial/config/1001",
                json={"enabled": False},
            )
            assert response.status_code == 200


# =============================================================================
# Team Messaging
# =============================================================================


@pytest.mark.unit
class TestTeamMessagingRoutes:
    """Test team messaging endpoints."""

    def test_get_channels(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.team_collaboration.TeamMessagingEngine") as MockEngine:
            MockEngine.return_value.get_all_channels.return_value = [{"id": 1}]
            response = api_client.get("/api/framework/team-messaging/channels")
            assert response.status_code == 200
            assert len(_json(response)["channels"]) == 1

    def test_get_channels_no_auth(self, api_client: FlaskClient) -> None:
        response = api_client.get("/api/framework/team-messaging/channels")
        assert response.status_code == 401

    def test_get_messages(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.team_collaboration.TeamMessagingEngine") as MockEngine:
            MockEngine.return_value.get_channel_messages.return_value = [{"text": "hi"}]
            response = api_client.get("/api/framework/team-messaging/messages/1")
            assert response.status_code == 200

    def test_create_channel_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.team_collaboration.TeamMessagingEngine") as MockEngine:
            MockEngine.return_value.create_channel.return_value = 10
            response = api_client.post(
                "/api/framework/team-messaging/create-channel",
                json={"name": "general"},
            )
            assert response.status_code == 200
            assert _json(response)["channel_id"] == 10

    def test_create_channel_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.team_collaboration.TeamMessagingEngine") as MockEngine:
            MockEngine.return_value.create_channel.return_value = None
            response = api_client.post(
                "/api/framework/team-messaging/create-channel",
                json={"name": "general"},
            )
            assert response.status_code == 500

    def test_send_message_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.team_collaboration.TeamMessagingEngine") as MockEngine:
            MockEngine.return_value.send_message.return_value = 55
            response = api_client.post(
                "/api/framework/team-messaging/send-message",
                json={"channel_id": 1, "text": "hello"},
            )
            assert response.status_code == 200
            assert _json(response)["message_id"] == 55


# =============================================================================
# Nomadic E911
# =============================================================================


@pytest.mark.unit
class TestNomadicE911Routes:
    """Test Nomadic E911 endpoints."""

    def test_get_sites(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.nomadic_e911.NomadicE911Engine") as MockEngine:
            MockEngine.return_value.get_all_sites.return_value = [{"id": 1}]
            response = api_client.get("/api/framework/nomadic-e911/sites")
            assert response.status_code == 200
            assert "sites" in _json(response)

    def test_get_sites_no_auth(self, api_client: FlaskClient) -> None:
        response = api_client.get("/api/framework/nomadic-e911/sites")
        assert response.status_code == 401

    def test_get_location_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.nomadic_e911.NomadicE911Engine") as MockEngine:
            MockEngine.return_value.get_location.return_value = {"address": "123 Main St"}
            response = api_client.get("/api/framework/nomadic-e911/location/1001")
            assert response.status_code == 200

    def test_get_location_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.nomadic_e911.NomadicE911Engine") as MockEngine:
            MockEngine.return_value.get_location.return_value = None
            response = api_client.get("/api/framework/nomadic-e911/location/9999")
            assert response.status_code == 404

    def test_get_history(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.nomadic_e911.NomadicE911Engine") as MockEngine:
            MockEngine.return_value.get_location_history.return_value = []
            response = api_client.get("/api/framework/nomadic-e911/history/1001")
            assert response.status_code == 200

    def test_update_location_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.nomadic_e911.NomadicE911Engine") as MockEngine:
            MockEngine.return_value.update_location.return_value = True
            response = api_client.post(
                "/api/framework/nomadic-e911/update-location/1001",
                json={"address": "456 Oak Ave"},
            )
            assert response.status_code == 200

    def test_detect_location_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.nomadic_e911.NomadicE911Engine") as MockEngine:
            MockEngine.return_value.detect_location_by_ip.return_value = {"address": "auto"}
            response = api_client.post(
                "/api/framework/nomadic-e911/detect-location/1001",
                json={"ip_address": "192.168.1.100"},
            )
            assert response.status_code == 200

    def test_detect_location_no_ip(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/nomadic-e911/detect-location/1001",
                json={},
            )
            assert response.status_code == 400

    def test_detect_location_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.nomadic_e911.NomadicE911Engine") as MockEngine:
            MockEngine.return_value.detect_location_by_ip.return_value = None
            response = api_client.post(
                "/api/framework/nomadic-e911/detect-location/1001",
                json={"ip_address": "10.0.0.1"},
            )
            assert response.status_code == 404

    def test_create_site_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.nomadic_e911.NomadicE911Engine") as MockEngine:
            MockEngine.return_value.create_site_config.return_value = True
            response = api_client.post(
                "/api/framework/nomadic-e911/create-site",
                json={"name": "HQ", "address": "789 Elm"},
            )
            assert response.status_code == 200


# =============================================================================
# Integrations
# =============================================================================


@pytest.mark.unit
class TestIntegrationRoutes:
    """Test integration endpoints."""

    def test_get_hubspot_config(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.crm_integrations.HubSpotIntegration") as MockInt:
            MockInt.return_value.get_config.return_value = {"api_key": "abc"}
            response = api_client.get("/api/framework/integrations/hubspot")
            assert response.status_code == 200

    def test_get_hubspot_config_empty(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.crm_integrations.HubSpotIntegration") as MockInt:
            MockInt.return_value.get_config.return_value = None
            response = api_client.get("/api/framework/integrations/hubspot")
            assert response.status_code == 200
            assert _json(response)["enabled"] is False

    def test_get_zendesk_config(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.crm_integrations.ZendeskIntegration") as MockInt:
            MockInt.return_value.get_config.return_value = {"url": "zendesk.com"}
            response = api_client.get("/api/framework/integrations/zendesk")
            assert response.status_code == 200

    def test_get_activity_log(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        mock_pbx_core.database.execute.return_value = [
            (1, "hubspot", "sync", "success", "details", "2025-01-01"),
        ]
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.get("/api/framework/integrations/activity-log")
            assert response.status_code == 200
            data = _json(response)
            assert len(data["activities"]) == 1
            assert data["activities"][0]["integration_type"] == "hubspot"

    def test_get_activity_log_db_unavailable(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = False
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.get("/api/framework/integrations/activity-log")
            assert response.status_code == 200
            assert _json(response)["activities"] == []

    def test_update_hubspot_config(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.crm_integrations.HubSpotIntegration") as MockInt:
            MockInt.return_value.update_config.return_value = True
            response = api_client.post(
                "/api/framework/integrations/hubspot/config",
                json={"api_key": "new_key"},
            )
            assert response.status_code == 200

    def test_update_zendesk_config(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.crm_integrations.ZendeskIntegration") as MockInt:
            MockInt.return_value.update_config.return_value = True
            response = api_client.post(
                "/api/framework/integrations/zendesk/config",
                json={"url": "new.zendesk.com"},
            )
            assert response.status_code == 200

    def test_clear_activity_log_admin(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        mock_pbx_core.database.db_type = "sqlite"
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post("/api/framework/integrations/activity-log/clear")
            assert response.status_code == 200
            assert _json(response)["success"] is True

    def test_clear_activity_log_non_admin(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_NON_ADMIN):
            response = api_client.post("/api/framework/integrations/activity-log/clear")
            assert response.status_code == 403


# =============================================================================
# Compliance
# =============================================================================


@pytest.mark.unit
class TestComplianceRoutes:
    """Test compliance endpoints."""

    def test_get_gdpr_consents(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.GDPRComplianceEngine", create=True) as MockEngine:
            MockEngine.return_value.get_consent_status.return_value = [{"type": "recording"}]
            response = api_client.get("/api/framework/compliance/gdpr/consents?extension=1001")
            assert response.status_code == 200
            assert "consents" in _json(response)

    def test_get_gdpr_requests(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.GDPRComplianceEngine", create=True) as MockEngine:
            MockEngine.return_value.get_pending_requests.return_value = []
            response = api_client.get("/api/framework/compliance/gdpr/requests")
            assert response.status_code == 200

    def test_get_soc2_controls(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.SOC2ComplianceEngine") as MockEngine:
            MockEngine.return_value.get_all_controls.return_value = [{"control": "CC1.1"}]
            response = api_client.get("/api/framework/compliance/soc2/controls")
            assert response.status_code == 200

    def test_get_pci_audit_log(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.PCIDSSComplianceEngine", create=True) as MockEngine:
            MockEngine.return_value.get_audit_log.return_value = []
            response = api_client.get("/api/framework/compliance/pci/audit-log")
            assert response.status_code == 200

    def test_record_gdpr_consent(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.GDPRComplianceEngine", create=True) as MockEngine:
            MockEngine.return_value.record_consent.return_value = True
            response = api_client.post(
                "/api/framework/compliance/gdpr/consent",
                json={"extension": "1001", "consent_type": "recording"},
            )
            assert response.status_code == 200

    def test_withdraw_gdpr_consent(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.GDPRComplianceEngine", create=True) as MockEngine:
            MockEngine.return_value.withdraw_consent.return_value = True
            response = api_client.post(
                "/api/framework/compliance/gdpr/withdraw",
                json={"extension": "1001", "consent_type": "recording"},
            )
            assert response.status_code == 200

    def test_create_gdpr_request(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.GDPRComplianceEngine", create=True) as MockEngine:
            MockEngine.return_value.create_data_request.return_value = "req-123"
            response = api_client.post(
                "/api/framework/compliance/gdpr/request",
                json={"extension": "1001", "type": "export"},
            )
            assert response.status_code == 200
            assert _json(response)["request_id"] == "req-123"

    def test_register_soc2_control(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.SOC2ComplianceEngine") as MockEngine:
            MockEngine.return_value.register_control.return_value = True
            response = api_client.post(
                "/api/framework/compliance/soc2/control",
                json={"control_id": "CC1.1", "name": "Access Control"},
            )
            assert response.status_code == 200

    def test_log_pci_event(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.database.enabled = True
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.compliance_framework.PCIDSSComplianceEngine", create=True) as MockEngine:
            MockEngine.return_value.log_audit_event.return_value = True
            response = api_client.post(
                "/api/framework/compliance/pci/log",
                json={"event": "card_access", "user": "1001"},
            )
            assert response.status_code == 200


# =============================================================================
# BI Integration
# =============================================================================


@pytest.mark.unit
class TestBIIntegrationRoutes:
    """Test BI integration endpoints."""

    def test_get_datasets(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.bi_integration.get_bi_integration") as mock_bi:
            mock_bi.return_value.get_available_datasets.return_value = [{"name": "calls"}]
            response = api_client.get("/api/framework/bi-integration/datasets")
            assert response.status_code == 200
            assert len(_json(response)["datasets"]) == 1

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.bi_integration.get_bi_integration") as mock_bi:
            mock_bi.return_value.get_statistics.return_value = {"total": 100}
            response = api_client.get("/api/framework/bi-integration/statistics")
            assert response.status_code == 200

    def test_get_export_status_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.bi_integration.get_bi_integration") as mock_bi:
            mock_bi.return_value.get_available_datasets.return_value = [
                {"name": "calls", "status": "ready"},
            ]
            response = api_client.get("/api/framework/bi-integration/export/calls")
            assert response.status_code == 200

    def test_get_export_status_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.bi_integration.get_bi_integration") as mock_bi:
            mock_bi.return_value.get_available_datasets.return_value = []
            response = api_client.get("/api/framework/bi-integration/export/nonexistent")
            assert response.status_code == 404

    def test_export_dataset_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.bi_integration.get_bi_integration") as mock_bi, \
             patch("pbx.features.bi_integration.ExportFormat"):
            mock_bi.return_value.export_dataset.return_value = {"url": "/exports/calls.csv"}
            response = api_client.post(
                "/api/framework/bi-integration/export",
                json={"dataset": "calls", "format": "csv"},
            )
            assert response.status_code == 200

    def test_export_dataset_no_name(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/bi-integration/export",
                json={"format": "csv"},
            )
            assert response.status_code == 400

    def test_create_dataset_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.bi_integration.get_bi_integration") as mock_bi:
            response = api_client.post(
                "/api/framework/bi-integration/dataset",
                json={"name": "custom", "query": "SELECT * FROM calls"},
            )
            assert response.status_code == 200
            assert _json(response)["dataset"] == "custom"

    def test_create_dataset_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/bi-integration/dataset",
                json={"name": "custom"},
            )
            assert response.status_code == 400

    def test_test_connection(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.bi_integration.get_bi_integration") as mock_bi, \
             patch("pbx.features.bi_integration.BIProvider"):
            mock_bi.return_value.test_connection.return_value = {"connected": True}
            response = api_client.post(
                "/api/framework/bi-integration/test-connection",
                json={"provider": "tableau", "credentials": {"key": "abc"}},
            )
            assert response.status_code == 200


# =============================================================================
# Call Tagging
# =============================================================================


@pytest.mark.unit
class TestCallTaggingRoutes:
    """Test call tagging endpoints."""

    def test_get_tags(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_tagging.get_call_tagging") as mock_ct:
            mock_ct.return_value.get_all_tags.return_value = [{"id": 1, "name": "VIP"}]
            response = api_client.get("/api/framework/call-tagging/tags")
            assert response.status_code == 200

    def test_get_rules(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_tagging.get_call_tagging") as mock_ct:
            mock_ct.return_value.get_all_rules.return_value = []
            response = api_client.get("/api/framework/call-tagging/rules")
            assert response.status_code == 200

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_tagging.get_call_tagging") as mock_ct:
            mock_ct.return_value.get_statistics.return_value = {"total_tags": 5}
            response = api_client.get("/api/framework/call-tagging/statistics")
            assert response.status_code == 200

    def test_create_tag_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_tagging.get_call_tagging") as mock_ct:
            mock_ct.return_value.create_tag.return_value = 1
            response = api_client.post(
                "/api/framework/call-tagging/tag",
                json={"name": "VIP", "description": "VIP calls", "color": "#ff0000"},
            )
            assert response.status_code == 200
            assert _json(response)["tag_id"] == 1

    def test_create_tag_no_name(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/call-tagging/tag",
                json={"description": "test"},
            )
            assert response.status_code == 400

    def test_create_rule_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_tagging.get_call_tagging") as mock_ct:
            mock_ct.return_value.create_rule.return_value = 1
            response = api_client.post(
                "/api/framework/call-tagging/rule",
                json={"name": "Rule1", "tag_id": 1, "conditions": []},
            )
            assert response.status_code == 200

    def test_create_rule_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/call-tagging/rule",
                json={"name": "Rule1"},
            )
            assert response.status_code == 400

    def test_classify_call(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_tagging.get_call_tagging") as mock_ct:
            mock_ct.return_value.classify_call.return_value = ["VIP", "Sales"]
            response = api_client.post("/api/framework/call-tagging/classify/call123")
            assert response.status_code == 200
            data = _json(response)
            assert data["call_id"] == "call123"
            assert data["tags"] == ["VIP", "Sales"]


# =============================================================================
# Call Blending
# =============================================================================


@pytest.mark.unit
class TestCallBlendingRoutes:
    """Test call blending endpoints."""

    def test_get_agents(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_blending.get_call_blending") as mock_cb:
            mock_cb.return_value.get_all_agents.return_value = [{"id": "a1"}]
            response = api_client.get("/api/framework/call-blending/agents")
            assert response.status_code == 200

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_blending.get_call_blending") as mock_cb:
            mock_cb.return_value.get_statistics.return_value = {"total": 10}
            response = api_client.get("/api/framework/call-blending/statistics")
            assert response.status_code == 200

    def test_get_agent_status_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_blending.get_call_blending") as mock_cb:
            mock_cb.return_value.get_agent_status.return_value = {"mode": "blended"}
            response = api_client.get("/api/framework/call-blending/agent/a1")
            assert response.status_code == 200

    def test_get_agent_status_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_blending.get_call_blending") as mock_cb:
            mock_cb.return_value.get_agent_status.return_value = None
            response = api_client.get("/api/framework/call-blending/agent/bad")
            assert response.status_code == 404

    def test_register_agent_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_blending.get_call_blending") as mock_cb:
            mock_cb.return_value.register_agent.return_value = {"success": True}
            response = api_client.post(
                "/api/framework/call-blending/agent",
                json={"agent_id": "a1", "extension": "1001"},
            )
            assert response.status_code == 200

    def test_register_agent_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/call-blending/agent",
                json={"agent_id": "a1"},
            )
            assert response.status_code == 400

    def test_set_agent_mode(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_blending.get_call_blending") as mock_cb:
            mock_cb.return_value.set_agent_mode.return_value = {"mode": "inbound"}
            response = api_client.post(
                "/api/framework/call-blending/agent/a1/mode",
                json={"mode": "inbound"},
            )
            assert response.status_code == 200


# =============================================================================
# Geo Redundancy
# =============================================================================


@pytest.mark.unit
class TestGeoRedundancyRoutes:
    """Test geo redundancy endpoints."""

    def test_get_regions(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.geographic_redundancy.get_geographic_redundancy") as mock_geo:
            mock_geo.return_value.get_all_regions.return_value = [{"id": "us-east"}]
            response = api_client.get("/api/framework/geo-redundancy/regions")
            assert response.status_code == 200

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.geographic_redundancy.get_geographic_redundancy") as mock_geo:
            mock_geo.return_value.get_statistics.return_value = {"regions": 3}
            response = api_client.get("/api/framework/geo-redundancy/statistics")
            assert response.status_code == 200

    def test_get_region_status_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.geographic_redundancy.get_geographic_redundancy") as mock_geo:
            mock_geo.return_value.get_region_status.return_value = {"status": "active"}
            response = api_client.get("/api/framework/geo-redundancy/region/us-east")
            assert response.status_code == 200

    def test_get_region_status_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.geographic_redundancy.get_geographic_redundancy") as mock_geo:
            mock_geo.return_value.get_region_status.return_value = None
            response = api_client.get("/api/framework/geo-redundancy/region/bad")
            assert response.status_code == 404

    def test_create_region_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.geographic_redundancy.get_geographic_redundancy") as mock_geo:
            mock_geo.return_value.create_region.return_value = {"id": "us-west"}
            response = api_client.post(
                "/api/framework/geo-redundancy/region",
                json={"region_id": "us-west", "name": "US West", "location": "Oregon"},
            )
            assert response.status_code == 200

    def test_create_region_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/geo-redundancy/region",
                json={"region_id": "us-west"},
            )
            assert response.status_code == 400

    def test_trigger_failover(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.geographic_redundancy.get_geographic_redundancy") as mock_geo:
            mock_geo.return_value.trigger_failover.return_value = {"status": "failover_complete"}
            response = api_client.post("/api/framework/geo-redundancy/region/us-east/failover")
            assert response.status_code == 200


# =============================================================================
# Conversational AI
# =============================================================================


@pytest.mark.unit
class TestConversationalAIRoutes:
    """Test conversational AI endpoints."""

    def test_get_config(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.conversational_ai.get_conversational_ai") as mock_ai:
            ai_inst = mock_ai.return_value
            ai_inst.enabled = True
            ai_inst.provider = "openai"
            ai_inst.model = "gpt-4"
            ai_inst.max_tokens = 1000
            ai_inst.temperature = 0.7
            response = api_client.get("/api/framework/conversational-ai/config")
            assert response.status_code == 200
            data = _json(response)
            assert data["enabled"] is True
            assert data["provider"] == "openai"

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.conversational_ai.get_conversational_ai") as mock_ai:
            mock_ai.return_value.get_statistics.return_value = {"conversations": 50}
            response = api_client.get("/api/framework/conversational-ai/statistics")
            assert response.status_code == 200

    def test_get_conversations(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.conversational_ai.get_conversational_ai") as mock_ai:
            mock_ai.return_value.active_conversations = {}
            response = api_client.get("/api/framework/conversational-ai/conversations")
            assert response.status_code == 200
            assert _json(response)["conversations"] == []

    def test_get_history(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.conversational_ai.get_conversational_ai") as mock_ai:
            mock_ai.return_value.get_conversation_history.return_value = []
            response = api_client.get("/api/framework/conversational-ai/history?limit=50")
            assert response.status_code == 200

    def test_start_conversation_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        from datetime import UTC, datetime

        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.conversational_ai.get_conversational_ai") as mock_ai:
            context = MagicMock()
            context.call_id = "call-1"
            context.started_at = datetime(2025, 1, 1, tzinfo=UTC)
            mock_ai.return_value.start_conversation.return_value = context
            response = api_client.post(
                "/api/framework/conversational-ai/conversation",
                json={"call_id": "call-1", "caller_id": "1001"},
            )
            assert response.status_code == 200
            assert _json(response)["success"] is True

    def test_start_conversation_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/conversational-ai/conversation",
                json={"call_id": "call-1"},
            )
            assert response.status_code == 400

    def test_process_input_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.conversational_ai.get_conversational_ai") as mock_ai:
            mock_ai.return_value.process_user_input.return_value = {"response": "Hello!"}
            response = api_client.post(
                "/api/framework/conversational-ai/process",
                json={"call_id": "call-1", "input": "Hi there"},
            )
            assert response.status_code == 200

    def test_process_input_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/conversational-ai/process",
                json={"call_id": "call-1"},
            )
            assert response.status_code == 400

    def test_configure_provider_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.conversational_ai.get_conversational_ai") as mock_ai:
            response = api_client.post(
                "/api/framework/conversational-ai/config",
                json={"provider": "openai", "api_key": "sk-test"},
            )
            assert response.status_code == 200

    def test_configure_provider_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/conversational-ai/config",
                json={"provider": "openai"},
            )
            assert response.status_code == 400


# =============================================================================
# Predictive Dialing
# =============================================================================


@pytest.mark.unit
class TestPredictiveDialingRoutes:
    """Test predictive dialing endpoints."""

    def test_get_campaigns(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_dialing.get_predictive_dialer") as mock_pd:
            mock_pd.return_value.campaigns = {}
            response = api_client.get("/api/framework/predictive-dialing/campaigns")
            assert response.status_code == 200
            assert _json(response)["campaigns"] == []

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_dialing.get_predictive_dialer") as mock_pd:
            mock_pd.return_value.get_statistics.return_value = {"active": 2}
            response = api_client.get("/api/framework/predictive-dialing/statistics")
            assert response.status_code == 200

    def test_get_campaign_details_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_dialing.get_predictive_dialer") as mock_pd:
            mock_pd.return_value.get_campaign_statistics.return_value = {"name": "Camp1"}
            response = api_client.get("/api/framework/predictive-dialing/campaign/c1")
            assert response.status_code == 200

    def test_get_campaign_details_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_dialing.get_predictive_dialer") as mock_pd:
            mock_pd.return_value.get_campaign_statistics.return_value = None
            response = api_client.get("/api/framework/predictive-dialing/campaign/bad")
            assert response.status_code == 404

    def test_create_campaign_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_dialing.get_predictive_dialer") as mock_pd, \
             patch("pbx.features.predictive_dialing.DialingMode"):
            campaign = MagicMock()
            campaign.campaign_id = "c1"
            campaign.name = "Camp1"
            mock_pd.return_value.create_campaign.return_value = campaign
            response = api_client.post(
                "/api/framework/predictive-dialing/campaign",
                json={"campaign_id": "c1", "name": "Camp1", "dialing_mode": "progressive"},
            )
            assert response.status_code == 200

    def test_create_campaign_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/predictive-dialing/campaign",
                json={"campaign_id": "c1"},
            )
            assert response.status_code == 400

    def test_add_contacts_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_dialing.get_predictive_dialer") as mock_pd:
            mock_pd.return_value.add_contacts.return_value = 5
            response = api_client.post(
                "/api/framework/predictive-dialing/contacts",
                json={"campaign_id": "c1", "contacts": [{"phone": "555-0001"}]},
            )
            assert response.status_code == 200
            assert _json(response)["contacts_added"] == 5

    def test_add_contacts_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/predictive-dialing/contacts",
                json={"campaign_id": "c1"},
            )
            assert response.status_code == 400

    def test_start_campaign(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_dialing.get_predictive_dialer") as mock_pd:
            response = api_client.post("/api/framework/predictive-dialing/campaign/c1/start")
            assert response.status_code == 200
            assert _json(response)["status"] == "running"

    def test_pause_campaign(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_dialing.get_predictive_dialer") as mock_pd:
            response = api_client.post("/api/framework/predictive-dialing/campaign/c1/pause")
            assert response.status_code == 200
            assert _json(response)["status"] == "paused"


# =============================================================================
# Voice Biometrics
# =============================================================================


@pytest.mark.unit
class TestVoiceBiometricsRoutes:
    """Test voice biometrics endpoints."""

    def test_get_profiles(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            mock_vb.return_value.profiles = {}
            response = api_client.get("/api/framework/voice-biometrics/profiles")
            assert response.status_code == 200
            assert _json(response)["profiles"] == []

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            mock_vb.return_value.get_statistics.return_value = {"total": 10}
            response = api_client.get("/api/framework/voice-biometrics/statistics")
            assert response.status_code == 200

    def test_get_profile_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        from datetime import UTC, datetime

        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            profile = MagicMock()
            profile.user_id = "u1"
            profile.extension = "1001"
            profile.status = "enrolled"
            profile.enrollment_completed = True
            profile.created_at = datetime(2025, 1, 1, tzinfo=UTC)
            profile.verification_count = 5
            profile.fraud_attempts = 0
            mock_vb.return_value.get_profile.return_value = profile
            response = api_client.get("/api/framework/voice-biometrics/profile/u1")
            assert response.status_code == 200
            assert _json(response)["user_id"] == "u1"

    def test_get_profile_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            mock_vb.return_value.get_profile.return_value = None
            response = api_client.get("/api/framework/voice-biometrics/profile/bad")
            assert response.status_code == 404

    def test_create_profile_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            profile = MagicMock()
            profile.user_id = "u1"
            profile.extension = "1001"
            profile.status = "pending"
            mock_vb.return_value.create_profile.return_value = profile
            response = api_client.post(
                "/api/framework/voice-biometrics/profile",
                json={"user_id": "u1", "extension": "1001"},
            )
            assert response.status_code == 200
            assert _json(response)["success"] is True

    def test_create_profile_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/voice-biometrics/profile",
                json={"user_id": "u1"},
            )
            assert response.status_code == 400

    def test_start_enrollment(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            mock_vb.return_value.start_enrollment.return_value = {"status": "started"}
            response = api_client.post(
                "/api/framework/voice-biometrics/enroll",
                json={"user_id": "u1"},
            )
            assert response.status_code == 200

    def test_start_enrollment_no_user(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/voice-biometrics/enroll",
                json={},
            )
            assert response.status_code == 400

    def test_verify_speaker(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        import base64

        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            mock_vb.return_value.verify_speaker.return_value = {"verified": True, "score": 0.95}
            audio = base64.b64encode(b"fake_audio").decode()
            response = api_client.post(
                "/api/framework/voice-biometrics/verify",
                json={"user_id": "u1", "audio_data": audio},
            )
            assert response.status_code == 200

    def test_verify_speaker_no_user(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/voice-biometrics/verify",
                json={},
            )
            assert response.status_code == 400

    def test_delete_profile_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            mock_vb.return_value.delete_profile.return_value = True
            response = api_client.delete("/api/framework/voice-biometrics/profile/u1")
            assert response.status_code == 200

    def test_delete_profile_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.voice_biometrics.get_voice_biometrics") as mock_vb:
            mock_vb.return_value.delete_profile.return_value = False
            response = api_client.delete("/api/framework/voice-biometrics/profile/bad")
            assert response.status_code == 404


# =============================================================================
# Call Quality Prediction
# =============================================================================


@pytest.mark.unit
class TestCallQualityPredictionRoutes:
    """Test call quality prediction endpoints."""

    def test_get_predictions(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_quality_prediction.get_quality_prediction") as mock_qp:
            mock_qp.return_value.active_predictions = {"call-1": {"score": 4.2}}
            response = api_client.get("/api/framework/call-quality-prediction/predictions")
            assert response.status_code == 200

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_quality_prediction.get_quality_prediction") as mock_qp:
            mock_qp.return_value.get_statistics.return_value = {"avg_score": 4.0}
            response = api_client.get("/api/framework/call-quality-prediction/statistics")
            assert response.status_code == 200

    def test_get_alerts_with_db(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_quality_prediction.get_quality_prediction") as mock_qp:
            mock_qp.return_value.db = MagicMock()
            mock_qp.return_value.db.get_active_alerts.return_value = [{"id": 1}]
            response = api_client.get("/api/framework/call-quality-prediction/alerts")
            assert response.status_code == 200
            assert len(_json(response)["alerts"]) == 1

    def test_get_alerts_no_db(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_quality_prediction.get_quality_prediction") as mock_qp:
            mock_qp.return_value.db = None
            response = api_client.get("/api/framework/call-quality-prediction/alerts")
            assert response.status_code == 200
            assert _json(response)["alerts"] == []

    def test_get_prediction_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_quality_prediction.get_quality_prediction") as mock_qp:
            mock_qp.return_value.get_prediction.return_value = {"score": 4.5}
            response = api_client.get("/api/framework/call-quality-prediction/prediction/call-1")
            assert response.status_code == 200

    def test_get_prediction_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_quality_prediction.get_quality_prediction") as mock_qp:
            mock_qp.return_value.get_prediction.return_value = None
            response = api_client.get("/api/framework/call-quality-prediction/prediction/bad")
            assert response.status_code == 404

    def test_collect_metrics_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_quality_prediction.get_quality_prediction") as mock_qp, \
             patch("pbx.features.call_quality_prediction.NetworkMetrics"):
            response = api_client.post(
                "/api/framework/call-quality-prediction/metrics",
                json={"call_id": "call-1", "packet_loss": 0.01, "jitter": 5.0},
            )
            assert response.status_code == 200

    def test_collect_metrics_no_call_id(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/call-quality-prediction/metrics",
                json={"packet_loss": 0.01},
            )
            assert response.status_code == 400

    def test_train_model_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_quality_prediction.get_quality_prediction") as mock_qp:
            response = api_client.post(
                "/api/framework/call-quality-prediction/train",
                json={"data": [{"score": 4.0}, {"score": 3.5}]},
            )
            assert response.status_code == 200
            assert _json(response)["samples_trained"] == 2

    def test_train_model_no_data(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/call-quality-prediction/train",
                json={"data": []},
            )
            assert response.status_code == 400


# =============================================================================
# Video Codec
# =============================================================================


@pytest.mark.unit
class TestVideoCodecRoutes:
    """Test video codec endpoints."""

    def test_get_codecs(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_codec.get_video_codec_manager") as mock_vc:
            mock_vc.return_value.available_codecs = ["h264", "vp8", "vp9"]
            response = api_client.get("/api/framework/video-codec/codecs")
            assert response.status_code == 200
            assert "h264" in _json(response)["codecs"]

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_codec.get_video_codec_manager") as mock_vc:
            mock_vc.return_value.get_statistics.return_value = {"sessions": 3}
            response = api_client.get("/api/framework/video-codec/statistics")
            assert response.status_code == 200

    def test_calculate_bandwidth(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.video_codec.get_video_codec_manager") as mock_vc:
            mock_vc.return_value.calculate_bandwidth.return_value = 5.0
            response = api_client.post(
                "/api/framework/video-codec/bandwidth",
                json={"resolution": [1920, 1080], "framerate": 30, "codec": "h264"},
            )
            assert response.status_code == 200
            assert _json(response)["bandwidth_mbps"] == 5.0

    def test_calculate_bandwidth_invalid_resolution(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/video-codec/bandwidth",
                json={"resolution": "invalid"},
            )
            assert response.status_code == 400


# =============================================================================
# Mobile Portability
# =============================================================================


@pytest.mark.unit
class TestMobilePortabilityRoutes:
    """Test mobile portability endpoints."""

    def test_get_mappings(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.number_mappings = {}
            response = api_client.get("/api/framework/mobile-portability/mappings")
            assert response.status_code == 200
            assert _json(response)["mappings"] == []

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.get_statistics.return_value = {"total": 5}
            response = api_client.get("/api/framework/mobile-portability/statistics")
            assert response.status_code == 200

    def test_get_mapping_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.get_mapping.return_value = {"extension": "1001"}
            response = api_client.get("/api/framework/mobile-portability/mapping/5550001")
            assert response.status_code == 200

    def test_get_mapping_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.get_mapping.return_value = None
            response = api_client.get("/api/framework/mobile-portability/mapping/bad")
            assert response.status_code == 404

    def test_create_mapping_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.map_number_to_mobile.return_value = {"success": True}
            response = api_client.post(
                "/api/framework/mobile-portability/mapping",
                json={
                    "business_number": "5550001",
                    "extension": "1001",
                    "mobile_device": "iPhone",
                },
            )
            assert response.status_code == 200

    def test_create_mapping_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/mobile-portability/mapping",
                json={"business_number": "5550001"},
            )
            assert response.status_code == 400

    def test_toggle_mapping_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.toggle_mapping.return_value = True
            response = api_client.post(
                "/api/framework/mobile-portability/mapping/5550001/toggle",
                json={"active": False},
            )
            assert response.status_code == 200

    def test_toggle_mapping_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.toggle_mapping.return_value = False
            response = api_client.post(
                "/api/framework/mobile-portability/mapping/bad/toggle",
                json={"active": True},
            )
            assert response.status_code == 404

    def test_delete_mapping_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.remove_mapping.return_value = True
            response = api_client.delete("/api/framework/mobile-portability/mapping/5550001")
            assert response.status_code == 200

    def test_delete_mapping_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.mobile_number_portability.get_mobile_number_portability") as mock_mnp:
            mock_mnp.return_value.remove_mapping.return_value = False
            response = api_client.delete("/api/framework/mobile-portability/mapping/bad")
            assert response.status_code == 404


# =============================================================================
# Recording Analytics
# =============================================================================


@pytest.mark.unit
class TestRecordingAnalyticsRoutes:
    """Test recording analytics endpoints."""

    def test_get_analyses(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_recording_analytics.get_recording_analytics") as mock_ra:
            mock_ra.return_value.analyses = {"r1": {"status": "done"}}
            response = api_client.get("/api/framework/recording-analytics/analyses")
            assert response.status_code == 200

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_recording_analytics.get_recording_analytics") as mock_ra:
            mock_ra.return_value.get_statistics.return_value = {"total": 50}
            response = api_client.get("/api/framework/recording-analytics/statistics")
            assert response.status_code == 200

    def test_get_analysis_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_recording_analytics.get_recording_analytics") as mock_ra:
            mock_ra.return_value.get_analysis.return_value = {"id": "r1"}
            response = api_client.get("/api/framework/recording-analytics/analysis/r1")
            assert response.status_code == 200

    def test_get_analysis_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_recording_analytics.get_recording_analytics") as mock_ra:
            mock_ra.return_value.get_analysis.return_value = None
            response = api_client.get("/api/framework/recording-analytics/analysis/bad")
            assert response.status_code == 404

    def test_analyze_recording_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_recording_analytics.get_recording_analytics") as mock_ra:
            mock_ra.return_value.analyze_recording.return_value = {"status": "complete"}
            response = api_client.post(
                "/api/framework/recording-analytics/analyze",
                json={"recording_id": "r1", "audio_path": "/tmp/recording.wav"},
            )
            assert response.status_code == 200

    def test_analyze_recording_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/recording-analytics/analyze",
                json={"recording_id": "r1"},
            )
            assert response.status_code == 400

    def test_search_recordings(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.call_recording_analytics.get_recording_analytics") as mock_ra:
            mock_ra.return_value.search_recordings.return_value = [{"id": "r1"}]
            response = api_client.post(
                "/api/framework/recording-analytics/search",
                json={"criteria": {"extension": "1001"}},
            )
            assert response.status_code == 200
            assert len(_json(response)["results"]) == 1


# =============================================================================
# Voicemail Drop
# =============================================================================


@pytest.mark.unit
class TestVoicemailDropRoutes:
    """Test voicemail drop endpoints."""

    def test_get_messages(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_voicemail_drop.get_voicemail_drop") as mock_vd:
            mock_vd.return_value.list_messages.return_value = [{"id": "m1"}]
            response = api_client.get("/api/framework/voicemail-drop/messages")
            assert response.status_code == 200

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_voicemail_drop.get_voicemail_drop") as mock_vd:
            mock_vd.return_value.get_statistics.return_value = {"dropped": 100}
            response = api_client.get("/api/framework/voicemail-drop/statistics")
            assert response.status_code == 200

    def test_add_message_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_voicemail_drop.get_voicemail_drop") as mock_vd:
            response = api_client.post(
                "/api/framework/voicemail-drop/message",
                json={"message_id": "m1", "name": "Greeting", "audio_path": "/tmp/msg.wav"},
            )
            assert response.status_code == 200
            assert _json(response)["message_id"] == "m1"

    def test_add_message_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/voicemail-drop/message",
                json={"message_id": "m1"},
            )
            assert response.status_code == 400

    def test_drop_voicemail_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.predictive_voicemail_drop.get_voicemail_drop") as mock_vd:
            mock_vd.return_value.drop_message.return_value = {"dropped": True}
            response = api_client.post(
                "/api/framework/voicemail-drop/drop",
                json={"call_id": "call-1", "message_id": "m1"},
            )
            assert response.status_code == 200

    def test_drop_voicemail_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/voicemail-drop/drop",
                json={"call_id": "call-1"},
            )
            assert response.status_code == 400


# =============================================================================
# DNS SRV
# =============================================================================


@pytest.mark.unit
class TestDNSSRVRoutes:
    """Test DNS SRV endpoints."""

    def test_get_records(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.dns_srv_failover.get_dns_srv_failover") as mock_dns:
            mock_dns.return_value.srv_cache = {}
            response = api_client.get("/api/framework/dns-srv/records")
            assert response.status_code == 200
            assert _json(response)["records"] == {}

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.dns_srv_failover.get_dns_srv_failover") as mock_dns:
            mock_dns.return_value.get_statistics.return_value = {"lookups": 100}
            response = api_client.get("/api/framework/dns-srv/statistics")
            assert response.status_code == 200

    def test_lookup_srv_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.dns_srv_failover.get_dns_srv_failover") as mock_dns:
            mock_dns.return_value.lookup_srv.return_value = [{"target": "sip.example.com"}]
            response = api_client.post(
                "/api/framework/dns-srv/lookup",
                json={"service": "sip", "protocol": "tcp", "domain": "example.com"},
            )
            assert response.status_code == 200

    def test_lookup_srv_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/dns-srv/lookup",
                json={"service": "sip"},
            )
            assert response.status_code == 400


# =============================================================================
# SBC (Session Border Controller)
# =============================================================================


@pytest.mark.unit
class TestSBCRoutes:
    """Test SBC endpoints."""

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.session_border_controller.get_sbc") as mock_sbc:
            mock_sbc.return_value.get_statistics.return_value = {"active_relays": 5}
            response = api_client.get("/api/framework/sbc/statistics")
            assert response.status_code == 200

    def test_get_relays(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.session_border_controller.get_sbc") as mock_sbc:
            mock_sbc.return_value.relay_sessions = {"call-1": {"codec": "PCMU"}}
            response = api_client.get("/api/framework/sbc/relays")
            assert response.status_code == 200

    def test_allocate_relay_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.session_border_controller.get_sbc") as mock_sbc:
            mock_sbc.return_value.allocate_relay.return_value = {"port": 10000}
            response = api_client.post(
                "/api/framework/sbc/relay",
                json={"call_id": "call-1", "codec": "PCMU"},
            )
            assert response.status_code == 200

    def test_allocate_relay_no_call_id(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/sbc/relay",
                json={"codec": "PCMU"},
            )
            assert response.status_code == 400


# =============================================================================
# Data Residency
# =============================================================================


@pytest.mark.unit
class TestDataResidencyRoutes:
    """Test data residency endpoints."""

    def test_get_regions(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.data_residency_controls.get_data_residency") as mock_dr:
            mock_dr.return_value.region_configs = {}
            response = api_client.get("/api/framework/data-residency/regions")
            assert response.status_code == 200
            assert _json(response)["regions"] == {}

    def test_get_statistics(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.data_residency_controls.get_data_residency") as mock_dr:
            mock_dr.return_value.get_statistics.return_value = {"regions": 3}
            response = api_client.get("/api/framework/data-residency/statistics")
            assert response.status_code == 200

    def test_get_storage_location_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN), \
             patch("pbx.features.data_residency_controls.get_data_residency") as mock_dr:
            mock_dr.return_value.get_storage_location.return_value = {"region": "us-east"}
            response = api_client.post(
                "/api/framework/data-residency/location",
                json={"category": "recordings", "user_region": "us-east"},
            )
            assert response.status_code == 200

    def test_get_storage_location_no_category(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_RETURN):
            response = api_client.post(
                "/api/framework/data-residency/location",
                json={"user_region": "us-east"},
            )
            assert response.status_code == 400
