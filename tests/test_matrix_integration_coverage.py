"""Comprehensive tests for the Matrix integration module."""

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pbx.integrations.matrix import MatrixIntegration


class MockConfig:
    """Mock config object that mimics Config class behavior."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val if val is not None else default


def _make_enabled_config(
    homeserver_url: str = "https://matrix.example.com",
    bot_username: str = "pbx-bot",
    bot_password: str = "bot-secret",
    notification_room: str = "!room1:example.com",
    voicemail_room: str = "!voicemail:example.com",
    missed_call_notifications: bool = True,
) -> MockConfig:
    """Create a standard enabled Matrix config."""
    return MockConfig(
        {
            "integrations": {
                "matrix": {
                    "enabled": True,
                    "homeserver_url": homeserver_url,
                    "bot_username": bot_username,
                    "bot_password": bot_password,
                    "notification_room": notification_room,
                    "voicemail_room": voicemail_room,
                    "missed_call_notifications": missed_call_notifications,
                }
            }
        }
    )


def _make_disabled_config() -> MockConfig:
    """Create a disabled Matrix config."""
    return MockConfig({"integrations": {"matrix": {"enabled": False}}})


def _create_integration_with_token(config: MockConfig | None = None) -> MatrixIntegration:
    """Create an enabled integration with a pre-set access token (bypass auth)."""
    with patch("pbx.integrations.matrix.requests") as mock_requests:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test-token-abc"}
        mock_requests.post.return_value = mock_response

        if config is None:
            config = _make_enabled_config()
        integration = MatrixIntegration(config)

    # Ensure the token is set even if auth mock wasn't triggered
    integration.bot_access_token = "test-token-abc"
    return integration


@pytest.mark.unit
class TestMatrixIntegrationInit:
    """Tests for Matrix integration initialization."""

    @patch("pbx.integrations.matrix.requests")
    def test_init_enabled_with_full_config(self, mock_requests: MagicMock) -> None:
        """Test initialization with a complete and valid config."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "tok-123"}
        mock_requests.post.return_value = mock_response

        config = _make_enabled_config()
        integration = MatrixIntegration(config)

        assert integration.enabled is True
        assert integration.homeserver_url == "https://matrix.example.com"
        assert integration.bot_username == "pbx-bot"
        assert integration.bot_password == "bot-secret"
        assert integration.notification_room == "!room1:example.com"
        assert integration.voicemail_room == "!voicemail:example.com"
        assert integration.missed_call_notifications is True
        assert integration.bot_access_token == "tok-123"

    def test_init_disabled(self) -> None:
        """Test initialization when integration is disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        assert integration.enabled is False
        assert integration.bot_access_token is None

    def test_init_missing_bot_username_disables(self) -> None:
        """Test that missing bot_username disables the integration."""
        config = MockConfig(
            {
                "integrations": {
                    "matrix": {
                        "enabled": True,
                        "homeserver_url": "https://matrix.example.com",
                        "bot_password": "secret",
                    }
                }
            }
        )
        integration = MatrixIntegration(config)
        assert integration.enabled is False

    def test_init_missing_bot_password_disables(self) -> None:
        """Test that missing bot_password disables the integration."""
        config = MockConfig(
            {
                "integrations": {
                    "matrix": {
                        "enabled": True,
                        "homeserver_url": "https://matrix.example.com",
                        "bot_username": "bot",
                    }
                }
            }
        )
        integration = MatrixIntegration(config)
        assert integration.enabled is False

    @patch("pbx.integrations.matrix.REQUESTS_AVAILABLE", False)
    def test_init_requests_unavailable_disables(self) -> None:
        """Test that missing requests library disables the integration."""
        config = _make_enabled_config()
        integration = MatrixIntegration(config)
        assert integration.enabled is False

    def test_init_default_homeserver_url(self) -> None:
        """Test that default homeserver URL is matrix.org."""
        config = MockConfig(
            {
                "integrations": {
                    "matrix": {
                        "enabled": True,
                        "bot_username": "bot",
                        "bot_password": "pass",
                    }
                }
            }
        )
        # Even with defaults, homeserver_url should default to matrix.org
        # but bot credentials are set, so auth will be called
        with patch("pbx.integrations.matrix.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"access_token": "t"}
            mock_req.post.return_value = mock_resp
            integration = MatrixIntegration(config)

        assert integration.homeserver_url == "https://matrix.org"

    def test_init_empty_config(self) -> None:
        """Test initialization with empty config dict."""
        config = MockConfig({})
        integration = MatrixIntegration(config)
        assert integration.enabled is False


@pytest.mark.unit
class TestAuthenticate:
    """Tests for the _authenticate method."""

    @patch("pbx.integrations.matrix.requests")
    def test_authenticate_success(self, mock_requests: MagicMock) -> None:
        """Test successful bot authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "valid-token"}
        mock_requests.post.return_value = mock_response

        config = _make_enabled_config()
        integration = MatrixIntegration(config)

        assert integration.bot_access_token == "valid-token"
        mock_requests.post.assert_called_once()
        call_kwargs = mock_requests.post.call_args
        assert "/_matrix/client/r0/login" in call_kwargs.args[0]

    @patch("pbx.integrations.matrix.requests")
    def test_authenticate_failure(self, mock_requests: MagicMock) -> None:
        """Test failed authentication (non-200 status)."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_requests.post.return_value = mock_response

        config = _make_enabled_config()
        integration = MatrixIntegration(config)

        assert integration.bot_access_token is None

    @patch("pbx.integrations.matrix.requests")
    def test_authenticate_network_error(self, mock_requests: MagicMock) -> None:
        """Test authentication with network error."""
        mock_requests.post.side_effect = mock_requests.RequestException("Connection failed")

        config = _make_enabled_config()
        integration = MatrixIntegration(config)

        assert integration.bot_access_token is None

    def test_authenticate_disabled(self) -> None:
        """Test _authenticate when disabled returns False."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration._authenticate()

        assert result is False

    @patch("pbx.integrations.matrix.REQUESTS_AVAILABLE", False)
    def test_authenticate_requests_not_available(self) -> None:
        """Test _authenticate when requests library is not available."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)
        # Force enabled to test the guard
        integration.enabled = True

        result = integration._authenticate()

        # REQUESTS_AVAILABLE is False, so should return False
        assert result is False


@pytest.mark.unit
class TestMakeRequest:
    """Tests for the _make_request method."""

    @patch("pbx.integrations.matrix.requests")
    def test_make_request_get_success(self, mock_requests: MagicMock) -> None:
        """Test a successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration._make_request("GET", "rooms/!r1:example.com/members")

        assert result == {"data": "test"}
        mock_requests.request.assert_called_once()
        call_kwargs = mock_requests.request.call_args
        assert "Bearer test-token-abc" in str(call_kwargs)

    @patch("pbx.integrations.matrix.requests")
    def test_make_request_post_success(self, mock_requests: MagicMock) -> None:
        """Test a successful POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"room_id": "!new:example.com"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration._make_request("POST", "createRoom", data={"name": "Test"})

        assert result == {"room_id": "!new:example.com"}

    @patch("pbx.integrations.matrix.requests")
    def test_make_request_api_error(self, mock_requests: MagicMock) -> None:
        """Test handling of non-200/201 HTTP response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration._make_request("GET", "some/endpoint")

        assert result is None

    @patch("pbx.integrations.matrix.requests")
    def test_make_request_network_error(self, mock_requests: MagicMock) -> None:
        """Test handling of network exception."""
        mock_requests.request.side_effect = mock_requests.RequestException("Timeout")

        integration = _create_integration_with_token()

        result = integration._make_request("GET", "some/endpoint")

        assert result is None

    def test_make_request_disabled(self) -> None:
        """Test _make_request when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration._make_request("GET", "test")

        assert result is None

    def test_make_request_no_access_token(self) -> None:
        """Test _make_request when no access token is set."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)
        integration.enabled = True  # Force enabled but no token

        result = integration._make_request("GET", "test")

        assert result is None

    @patch("pbx.integrations.matrix.requests")
    def test_make_request_constructs_correct_url(self, mock_requests: MagicMock) -> None:
        """Test that the URL is constructed correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        integration._make_request("GET", "rooms/test/members")

        call_kwargs = mock_requests.request.call_args
        assert call_kwargs.kwargs["url"] == (
            "https://matrix.example.com/_matrix/client/r0/rooms/test/members"
        )


@pytest.mark.unit
class TestSendMessage:
    """Tests for send_message."""

    @patch("pbx.integrations.matrix.requests")
    def test_send_message_success(self, mock_requests: MagicMock) -> None:
        """Test successfully sending a message."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$evt123"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_message("!room:example.com", "Hello World")

        assert result == "$evt123"
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["msgtype"] == "m.text"
        assert data["body"] == "Hello World"
        assert data["format"] == "org.matrix.custom.html"

    @patch("pbx.integrations.matrix.requests")
    def test_send_message_custom_type(self, mock_requests: MagicMock) -> None:
        """Test sending a message with custom msg_type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$evt456"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_message("!room:example.com", "Notice", msg_type="m.notice")

        assert result == "$evt456"
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["msgtype"] == "m.notice"

    @patch("pbx.integrations.matrix.requests")
    def test_send_message_failure(self, mock_requests: MagicMock) -> None:
        """Test send_message when API returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_message("!room:example.com", "Hello")

        assert result is None

    def test_send_message_disabled(self) -> None:
        """Test send_message when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration.send_message("!room:example.com", "Hello")

        assert result is None

    @patch("pbx.integrations.matrix.requests")
    def test_send_message_uses_put_method(self, mock_requests: MagicMock) -> None:
        """Test that send_message uses PUT method for sending."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$e"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        integration.send_message("!room:example.com", "test")

        call_kwargs = mock_requests.request.call_args
        assert call_kwargs.kwargs["method"] == "PUT"

    @patch("pbx.integrations.matrix.requests")
    def test_send_message_includes_html_formatted_body(self, mock_requests: MagicMock) -> None:
        """Test that formatted_body contains HTML conversion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$e"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        integration.send_message("!room:example.com", "**bold** text")

        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert "<strong>bold</strong>" in data["formatted_body"]


@pytest.mark.unit
class TestSendNotification:
    """Tests for send_notification."""

    @patch("pbx.integrations.matrix.requests")
    def test_send_notification_default_room(self, mock_requests: MagicMock) -> None:
        """Test sending notification to default room."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$n1"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_notification("Test notification")

        assert result is True

    @patch("pbx.integrations.matrix.requests")
    def test_send_notification_custom_room(self, mock_requests: MagicMock) -> None:
        """Test sending notification to a custom room."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$n2"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_notification("Alert!", room_id="!custom:example.com")

        assert result is True
        call_kwargs = mock_requests.request.call_args
        assert "!custom:example.com" in call_kwargs.kwargs["url"]

    def test_send_notification_no_room_configured(self) -> None:
        """Test send_notification when no room is configured."""
        config = MockConfig(
            {
                "integrations": {
                    "matrix": {
                        "enabled": True,
                        "homeserver_url": "https://matrix.example.com",
                        "bot_username": "bot",
                        "bot_password": "pass",
                    }
                }
            }
        )
        with patch("pbx.integrations.matrix.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"access_token": "t"}
            mock_req.post.return_value = mock_resp
            integration = MatrixIntegration(config)

        integration.bot_access_token = "t"

        result = integration.send_notification("Test")

        assert result is False

    @patch("pbx.integrations.matrix.requests")
    def test_send_notification_send_failure(self, mock_requests: MagicMock) -> None:
        """Test send_notification when sending fails."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_notification("Test")

        assert result is False


@pytest.mark.unit
class TestSendMissedCallAlert:
    """Tests for send_missed_call_alert."""

    @patch("pbx.integrations.matrix.requests")
    def test_send_missed_call_alert_success(self, mock_requests: MagicMock) -> None:
        """Test sending a missed call alert."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$mc1"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        ts = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = integration.send_missed_call_alert("1001", "+15551234567", ts)

        assert result is True

    def test_send_missed_call_alert_disabled(self) -> None:
        """Test send_missed_call_alert when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        ts = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = integration.send_missed_call_alert("1001", "+15551234567", ts)

        assert result is False

    def test_send_missed_call_alert_notifications_disabled(self) -> None:
        """Test send_missed_call_alert when missed_call_notifications is False."""
        config = _make_enabled_config(missed_call_notifications=False)
        with patch("pbx.integrations.matrix.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"access_token": "t"}
            mock_req.post.return_value = mock_resp
            integration = MatrixIntegration(config)

        ts = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = integration.send_missed_call_alert("1001", "+15551234567", ts)

        assert result is False


@pytest.mark.unit
class TestSendVoicemailNotification:
    """Tests for send_voicemail_notification."""

    @patch("pbx.integrations.matrix.requests")
    def test_send_voicemail_notification_with_transcription(
        self, mock_requests: MagicMock
    ) -> None:
        """Test voicemail notification with transcription."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$vm1"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_voicemail_notification(
            extension="1001",
            caller_id="+15551234567",
            duration=30,
            transcription="Hi, this is a test message.",
        )

        assert result is True

    @patch("pbx.integrations.matrix.requests")
    def test_send_voicemail_notification_without_transcription(
        self, mock_requests: MagicMock
    ) -> None:
        """Test voicemail notification without transcription."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$vm2"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_voicemail_notification(
            extension="1001",
            caller_id="+15551234567",
            duration=15,
        )

        assert result is True

    def test_send_voicemail_notification_disabled(self) -> None:
        """Test send_voicemail_notification when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration.send_voicemail_notification("1001", "+155", 10)

        assert result is False

    @patch("pbx.integrations.matrix.requests")
    def test_send_voicemail_notification_uses_voicemail_room(
        self, mock_requests: MagicMock
    ) -> None:
        """Test that voicemail notifications use the voicemail room."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$vm3"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        integration.send_voicemail_notification("1001", "+155", 10)

        call_kwargs = mock_requests.request.call_args
        url = call_kwargs.kwargs["url"]
        assert "!voicemail:example.com" in url

    @patch("pbx.integrations.matrix.requests")
    def test_send_voicemail_notification_falls_back_to_notification_room(
        self, mock_requests: MagicMock
    ) -> None:
        """Test fallback to notification room when voicemail room not set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$vm4"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()
        integration.voicemail_room = None

        integration.send_voicemail_notification("1001", "+155", 10)

        call_kwargs = mock_requests.request.call_args
        url = call_kwargs.kwargs["url"]
        assert "!room1:example.com" in url

    def test_send_voicemail_notification_no_room(self) -> None:
        """Test voicemail notification when no rooms are configured."""
        integration = _create_integration_with_token()
        integration.voicemail_room = None
        integration.notification_room = None

        result = integration.send_voicemail_notification("1001", "+155", 10)

        assert result is False


@pytest.mark.unit
class TestCreateRoom:
    """Tests for create_room."""

    @patch("pbx.integrations.matrix.requests")
    def test_create_room_success(self, mock_requests: MagicMock) -> None:
        """Test successfully creating a room."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"room_id": "!newroom:example.com"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.create_room("Test Room")

        assert result == "!newroom:example.com"

    @patch("pbx.integrations.matrix.requests")
    def test_create_room_with_topic_and_invites(self, mock_requests: MagicMock) -> None:
        """Test creating a room with topic and invitees."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"room_id": "!new:example.com"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.create_room(
            "Project Room",
            topic="Project discussion",
            invite_users=["@alice:example.com", "@bob:example.com"],
        )

        assert result == "!new:example.com"
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["name"] == "Project Room"
        assert data["topic"] == "Project discussion"
        assert data["invite"] == ["@alice:example.com", "@bob:example.com"]
        assert data["preset"] == "private_chat"

    @patch("pbx.integrations.matrix.requests")
    def test_create_room_minimal(self, mock_requests: MagicMock) -> None:
        """Test creating a room with only a name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"room_id": "!min:example.com"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.create_room("Simple Room")

        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert "topic" not in data
        assert "invite" not in data

    @patch("pbx.integrations.matrix.requests")
    def test_create_room_failure(self, mock_requests: MagicMock) -> None:
        """Test create_room when API fails."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.create_room("Test Room")

        assert result is None

    def test_create_room_disabled(self) -> None:
        """Test create_room when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration.create_room("Test Room")

        assert result is None


@pytest.mark.unit
class TestInviteToRoom:
    """Tests for invite_to_room."""

    @patch("pbx.integrations.matrix.requests")
    def test_invite_to_room_success(self, mock_requests: MagicMock) -> None:
        """Test successfully inviting a user to a room."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.invite_to_room("!room:example.com", "@user:example.com")

        assert result is True
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["user_id"] == "@user:example.com"

    @patch("pbx.integrations.matrix.requests")
    def test_invite_to_room_failure(self, mock_requests: MagicMock) -> None:
        """Test invite_to_room when API fails."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.invite_to_room("!room:example.com", "@user:example.com")

        assert result is False

    def test_invite_to_room_disabled(self) -> None:
        """Test invite_to_room when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration.invite_to_room("!room:example.com", "@user:example.com")

        assert result is False


@pytest.mark.unit
class TestUploadFile:
    """Tests for upload_file."""

    @patch("pbx.integrations.matrix.requests")
    @patch("pbx.integrations.matrix.Path")
    def test_upload_file_success(self, mock_path_cls: MagicMock, mock_requests: MagicMock) -> None:
        """Test successfully uploading a file."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content_uri": "mxc://example.com/abc123"}
        mock_requests.post.return_value = mock_response

        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"file content"
        mock_path_instance.open.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_path_instance.open.return_value.__exit__ = MagicMock(return_value=False)
        mock_path_cls.return_value = mock_path_instance

        integration = _create_integration_with_token()

        result = integration.upload_file("/tmp/test.wav")

        assert result == "mxc://example.com/abc123"

    @patch("pbx.integrations.matrix.Path")
    def test_upload_file_not_found(self, mock_path_cls: MagicMock) -> None:
        """Test upload_file when file does not exist."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        integration = _create_integration_with_token()

        result = integration.upload_file("/tmp/nonexistent.wav")

        assert result is None

    @patch("pbx.integrations.matrix.requests")
    @patch("pbx.integrations.matrix.Path")
    def test_upload_file_api_failure(
        self, mock_path_cls: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test upload_file when API returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.post.return_value = mock_response

        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"data"
        mock_path_instance.open.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_path_instance.open.return_value.__exit__ = MagicMock(return_value=False)
        mock_path_cls.return_value = mock_path_instance

        integration = _create_integration_with_token()

        result = integration.upload_file("/tmp/test.wav")

        assert result is None

    def test_upload_file_disabled(self) -> None:
        """Test upload_file when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration.upload_file("/tmp/test.wav")

        assert result is None

    def test_upload_file_no_access_token(self) -> None:
        """Test upload_file when no access token."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)
        integration.enabled = True

        result = integration.upload_file("/tmp/test.wav")

        assert result is None


@pytest.mark.unit
class TestSendFile:
    """Tests for send_file."""

    @patch("pbx.integrations.matrix.Path")
    @patch.object(MatrixIntegration, "upload_file")
    @patch("pbx.integrations.matrix.requests")
    def test_send_file_success(
        self,
        mock_requests: MagicMock,
        mock_upload: MagicMock,
        mock_path_cls: MagicMock,
    ) -> None:
        """Test successfully sending a file to a room."""
        mock_upload.return_value = "mxc://example.com/file1"

        mock_path_instance = MagicMock()
        mock_path_instance.name = "test.wav"
        mock_path_instance.stat.return_value.st_size = 1024
        mock_path_cls.return_value = mock_path_instance

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$file1"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_file("!room:example.com", "/tmp/test.wav")

        assert result == "$file1"

    @patch.object(MatrixIntegration, "upload_file")
    def test_send_file_upload_failure(self, mock_upload: MagicMock) -> None:
        """Test send_file when upload fails."""
        mock_upload.return_value = None

        integration = _create_integration_with_token()

        result = integration.send_file("!room:example.com", "/tmp/test.wav")

        assert result is None

    @patch("pbx.integrations.matrix.Path")
    @patch.object(MatrixIntegration, "upload_file")
    @patch("pbx.integrations.matrix.requests")
    def test_send_file_custom_filename(
        self,
        mock_requests: MagicMock,
        mock_upload: MagicMock,
        mock_path_cls: MagicMock,
    ) -> None:
        """Test send_file with custom filename."""
        mock_upload.return_value = "mxc://example.com/file2"

        mock_path_instance = MagicMock()
        mock_path_instance.name = "original.wav"
        mock_path_instance.stat.return_value.st_size = 2048
        mock_path_cls.return_value = mock_path_instance

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"event_id": "$file2"}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.send_file(
            "!room:example.com", "/tmp/original.wav", filename="custom.wav"
        )

        assert result == "$file2"
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["body"] == "custom.wav"

    def test_send_file_disabled(self) -> None:
        """Test send_file when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration.send_file("!room:example.com", "/tmp/test.wav")

        assert result is None


@pytest.mark.unit
class TestMarkdownToHtml:
    """Tests for _markdown_to_html."""

    def test_bold_conversion(self) -> None:
        """Test bold markdown to HTML conversion."""
        integration = _create_integration_with_token()

        result = integration._markdown_to_html("**bold text**")

        assert result == "<strong>bold text</strong>"

    def test_italic_conversion(self) -> None:
        """Test italic markdown to HTML conversion."""
        integration = _create_integration_with_token()

        result = integration._markdown_to_html("*italic text*")

        assert result == "<em>italic text</em>"

    def test_code_conversion(self) -> None:
        """Test code markdown to HTML conversion."""
        integration = _create_integration_with_token()

        result = integration._markdown_to_html("`code here`")

        assert result == "<code>code here</code>"

    def test_newline_conversion(self) -> None:
        """Test newline to br conversion."""
        integration = _create_integration_with_token()

        result = integration._markdown_to_html("line1\nline2")

        assert result == "line1<br/>line2"

    def test_combined_markdown(self) -> None:
        """Test multiple markdown elements together."""
        integration = _create_integration_with_token()

        result = integration._markdown_to_html("**bold** and *italic* with `code`")

        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result
        assert "<code>code</code>" in result

    def test_plain_text_unchanged(self) -> None:
        """Test that plain text passes through unchanged."""
        integration = _create_integration_with_token()

        result = integration._markdown_to_html("plain text here")

        assert result == "plain text here"


@pytest.mark.unit
class TestGetRoomMembers:
    """Tests for get_room_members."""

    @patch("pbx.integrations.matrix.requests")
    def test_get_room_members_success(self, mock_requests: MagicMock) -> None:
        """Test successfully getting room members."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chunk": [
                {
                    "type": "m.room.member",
                    "state_key": "@alice:example.com",
                    "membership": "join",
                },
                {
                    "type": "m.room.member",
                    "state_key": "@bob:example.com",
                    "membership": "join",
                },
                {
                    "type": "m.room.member",
                    "state_key": "@charlie:example.com",
                    "membership": "leave",
                },
                {
                    "type": "m.room.other_event",
                    "state_key": "@other:example.com",
                    "membership": "join",
                },
            ]
        }
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.get_room_members("!room:example.com")

        assert "@alice:example.com" in result
        assert "@bob:example.com" in result
        assert "@charlie:example.com" not in result
        assert "@other:example.com" not in result
        assert len(result) == 2

    @patch("pbx.integrations.matrix.requests")
    def test_get_room_members_empty(self, mock_requests: MagicMock) -> None:
        """Test get_room_members with no members."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"chunk": []}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.get_room_members("!room:example.com")

        assert result == []

    @patch("pbx.integrations.matrix.requests")
    def test_get_room_members_no_chunk_key(self, mock_requests: MagicMock) -> None:
        """Test get_room_members when response has no 'chunk' key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.get_room_members("!room:example.com")

        assert result == []

    def test_get_room_members_disabled(self) -> None:
        """Test get_room_members when disabled."""
        config = _make_disabled_config()
        integration = MatrixIntegration(config)

        result = integration.get_room_members("!room:example.com")

        assert result == []

    @patch("pbx.integrations.matrix.requests")
    def test_get_room_members_api_error(self, mock_requests: MagicMock) -> None:
        """Test get_room_members when API returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_requests.request.return_value = mock_response

        integration = _create_integration_with_token()

        result = integration.get_room_members("!room:example.com")

        assert result == []
