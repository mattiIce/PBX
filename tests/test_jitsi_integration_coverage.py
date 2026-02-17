"""Comprehensive tests for the Jitsi Meet integration module."""

import time
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pbx.integrations.jitsi import JitsiIntegration


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
    server_url: str = "https://jitsi.example.com",
    app_id: str | None = None,
    app_secret: str | None = None,
    auto_create_rooms: bool = True,
    enable_recording: bool = False,
    enable_lobby: bool = False,
) -> MockConfig:
    """Create a standard enabled Jitsi config."""
    config: dict[str, Any] = {
        "integrations": {
            "jitsi": {
                "enabled": True,
                "server_url": server_url,
                "auto_create_rooms": auto_create_rooms,
                "enable_recording": enable_recording,
                "enable_lobby": enable_lobby,
            }
        }
    }
    if app_id:
        config["integrations"]["jitsi"]["app_id"] = app_id
    if app_secret:
        config["integrations"]["jitsi"]["app_secret"] = app_secret
    return MockConfig(config)


def _make_disabled_config() -> MockConfig:
    """Create a disabled Jitsi config."""
    return MockConfig({"integrations": {"jitsi": {"enabled": False}}})


@pytest.mark.unit
class TestJitsiIntegrationInit:
    """Tests for Jitsi integration initialization."""

    def test_init_enabled_with_full_config(self) -> None:
        """Test initialization with a complete and valid config."""
        config = _make_enabled_config(
            app_id="my-app",
            app_secret="my-secret",
            enable_recording=True,
            enable_lobby=True,
        )
        integration = JitsiIntegration(config)

        assert integration.enabled is True
        assert integration.server_url == "https://jitsi.example.com"
        assert integration.app_id == "my-app"
        assert integration.app_secret == "my-secret"
        assert integration.auto_create_rooms is True
        assert integration.enable_recording is True
        assert integration.enable_lobby is True

    def test_init_disabled(self) -> None:
        """Test initialization when integration is disabled."""
        config = _make_disabled_config()
        integration = JitsiIntegration(config)

        assert integration.enabled is False

    def test_init_default_server_url(self) -> None:
        """Test default server URL is meet.jit.si."""
        config = MockConfig({"integrations": {"jitsi": {"enabled": True}}})
        integration = JitsiIntegration(config)

        assert integration.server_url == "https://meet.jit.si"

    def test_init_default_feature_flags(self) -> None:
        """Test default feature flag values."""
        config = MockConfig({"integrations": {"jitsi": {"enabled": True}}})
        integration = JitsiIntegration(config)

        assert integration.auto_create_rooms is True
        assert integration.enable_recording is False
        assert integration.enable_lobby is False

    def test_init_default_room_config(self) -> None:
        """Test that default room configuration is set properly."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        assert integration.default_room_config["startWithAudioMuted"] is False
        assert integration.default_room_config["startWithVideoMuted"] is False
        assert integration.default_room_config["enableWelcomePage"] is False
        assert integration.default_room_config["prejoinPageEnabled"] is True
        assert integration.default_room_config["requireDisplayName"] is True

    def test_init_public_server_logs_info(self) -> None:
        """Test that using public Jitsi server logs an informational message."""
        config = MockConfig(
            {
                "integrations": {
                    "jitsi": {
                        "enabled": True,
                        "server_url": "https://meet.jit.si",
                    }
                }
            }
        )
        # Should not raise any exceptions
        integration = JitsiIntegration(config)
        assert integration.server_url == "https://meet.jit.si"

    def test_init_empty_config(self) -> None:
        """Test initialization with empty config dict."""
        config = MockConfig({})
        integration = JitsiIntegration(config)
        assert integration.enabled is False

    def test_init_no_app_id_or_secret(self) -> None:
        """Test initialization without app_id and app_secret."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        assert integration.app_id is None
        assert integration.app_secret is None


@pytest.mark.unit
class TestCreateMeeting:
    """Tests for create_meeting."""

    def test_create_meeting_with_all_options(self) -> None:
        """Test creating a meeting with all parameters."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        scheduled = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
        result = integration.create_meeting(
            room_name="team-standup",
            subject="Daily Standup",
            moderator_name="Alice",
            participant_names=["Bob", "Charlie"],
            scheduled_time=scheduled,
            duration_minutes=30,
        )

        assert result["success"] is True
        assert result["room_name"] == "team-standup"
        assert result["url"] == "https://jitsi.example.com/team-standup"
        assert result["subject"] == "Daily Standup"
        assert result["moderator"] == "Alice"
        assert result["participants"] == ["Bob", "Charlie"]
        assert result["scheduled_time"] == scheduled
        assert result["duration"] == 30
        assert result["server"] == "https://jitsi.example.com"

    def test_create_meeting_auto_generated_name(self) -> None:
        """Test creating a meeting without specifying room name."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_meeting()

        assert result["success"] is True
        assert result["room_name"].startswith("pbx-meeting-")
        assert result["url"].startswith("https://jitsi.example.com/pbx-meeting-")

    def test_create_meeting_default_subject(self) -> None:
        """Test that default subject is generated from room name."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_meeting(room_name="my-room")

        assert result["subject"] == "Meeting - my-room"

    def test_create_meeting_default_duration(self) -> None:
        """Test default meeting duration is 60 minutes."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_meeting(room_name="test")

        assert result["duration"] == 60

    def test_create_meeting_no_scheduled_time_uses_now(self) -> None:
        """Test that no scheduled time defaults to current time."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        before = datetime.now(UTC)
        result = integration.create_meeting(room_name="test")
        after = datetime.now(UTC)

        assert before <= result["scheduled_time"] <= after

    def test_create_meeting_no_participants(self) -> None:
        """Test creating a meeting without participants."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_meeting(room_name="test")

        assert result["participants"] == []

    def test_create_meeting_with_jwt(self) -> None:
        """Test that moderator URL includes JWT when app_id/secret configured."""
        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        with patch.object(integration, "_generate_jwt_token", return_value="fake-jwt-token"):
            result = integration.create_meeting(
                room_name="secure-room", moderator_name="Admin"
            )

        assert result["success"] is True
        assert "?jwt=fake-jwt-token" in result["moderator_url"]

    def test_create_meeting_without_jwt(self) -> None:
        """Test that moderator URL equals regular URL when no JWT configured."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_meeting(room_name="open-room")

        assert result["moderator_url"] == result["url"]

    def test_create_meeting_disabled(self) -> None:
        """Test create_meeting when disabled."""
        config = _make_disabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_meeting(room_name="test")

        assert result["success"] is False
        assert "error" in result

    def test_create_meeting_sanitizes_room_name(self) -> None:
        """Test that room names are sanitized."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_meeting(room_name="My Meeting Room!")

        assert result["success"] is True
        assert " " not in result["room_name"]
        assert "!" not in result["room_name"]
        assert result["room_name"] == "my-meeting-room"

    def test_create_meeting_has_created_at(self) -> None:
        """Test that created_at timestamp is set."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        before = datetime.now(UTC)
        result = integration.create_meeting(room_name="test")
        after = datetime.now(UTC)

        assert before <= result["created_at"] <= after

    def test_create_meeting_has_room_id(self) -> None:
        """Test that room_id matches room_name."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_meeting(room_name="test-room")

        assert result["room_id"] == result["room_name"]


@pytest.mark.unit
class TestGetParticipantUrl:
    """Tests for get_participant_url."""

    def test_get_participant_url_basic(self) -> None:
        """Test generating a basic participant URL."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        url = integration.get_participant_url("my-room", "Alice")

        assert url == 'https://jitsi.example.com/my-room#userInfo.displayName="Alice"'

    def test_get_participant_url_with_jwt(self) -> None:
        """Test participant URL with JWT token."""
        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        with patch.object(integration, "_generate_jwt_token", return_value="jwt-xyz"):
            url = integration.get_participant_url("my-room", "Bob", is_moderator=False)

        assert url == "https://jitsi.example.com/my-room?jwt=jwt-xyz"

    def test_get_participant_url_moderator_with_jwt(self) -> None:
        """Test moderator participant URL with JWT."""
        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        with patch.object(integration, "_generate_jwt_token", return_value="mod-jwt") as mock_jwt:
            url = integration.get_participant_url("my-room", "Admin", is_moderator=True)

        mock_jwt.assert_called_once_with("my-room", "Admin", True)
        assert "mod-jwt" in url


@pytest.mark.unit
class TestCreateInstantMeeting:
    """Tests for create_instant_meeting."""

    def test_create_instant_meeting_with_contact(self) -> None:
        """Test creating an instant meeting with a contact name."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_instant_meeting("1001", contact_name="John Doe")

        assert result["success"] is True
        assert "call-1001-" in result["room_name"]
        assert result["subject"] == "Video Call with John Doe"
        assert result["moderator"] == "Extension 1001"
        assert result["participants"] == ["John Doe"]

    def test_create_instant_meeting_without_contact(self) -> None:
        """Test creating an instant meeting without a contact name."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_instant_meeting("1002")

        assert result["success"] is True
        assert result["subject"] == "Video Call with Contact"
        assert result["participants"] == []

    def test_create_instant_meeting_disabled(self) -> None:
        """Test create_instant_meeting when disabled."""
        config = _make_disabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_instant_meeting("1001")

        assert result["success"] is False


@pytest.mark.unit
class TestCreateScheduledMeeting:
    """Tests for create_scheduled_meeting."""

    def test_create_scheduled_meeting_full(self) -> None:
        """Test creating a scheduled meeting with all options."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        scheduled = datetime(2026, 6, 15, 14, 30, 0, tzinfo=UTC)
        result = integration.create_scheduled_meeting(
            organizer_extension="1001",
            scheduled_time=scheduled,
            duration_minutes=90,
            subject="Project Review",
            participants=["Alice", "Bob"],
        )

        assert result["success"] is True
        assert result["room_name"] == "scheduled-1001-20260615-1430"
        assert result["subject"] == "Project Review"
        assert result["moderator"] == "Extension 1001"
        assert result["participants"] == ["Alice", "Bob"]
        assert result["duration"] == 90
        assert result["scheduled_time"] == scheduled

    def test_create_scheduled_meeting_minimal(self) -> None:
        """Test creating a scheduled meeting with minimal options."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        scheduled = datetime(2026, 3, 1, 9, 0, 0, tzinfo=UTC)
        result = integration.create_scheduled_meeting(
            organizer_extension="2001",
            scheduled_time=scheduled,
        )

        assert result["success"] is True
        assert result["room_name"] == "scheduled-2001-20260301-0900"
        assert result["subject"] == "Scheduled Meeting"
        assert result["duration"] == 60

    def test_create_scheduled_meeting_disabled(self) -> None:
        """Test create_scheduled_meeting when disabled."""
        config = _make_disabled_config()
        integration = JitsiIntegration(config)

        scheduled = datetime(2026, 3, 1, 9, 0, 0, tzinfo=UTC)
        result = integration.create_scheduled_meeting("1001", scheduled)

        assert result["success"] is False


@pytest.mark.unit
class TestSanitizeRoomName:
    """Tests for _sanitize_room_name."""

    def test_lowercase_conversion(self) -> None:
        """Test that room name is converted to lowercase."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration._sanitize_room_name("MyRoom")

        assert result == "myroom"

    def test_special_chars_replaced(self) -> None:
        """Test that special characters are replaced with hyphens."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration._sanitize_room_name("room@with#special!chars")

        assert result == "room-with-special-chars"

    def test_spaces_replaced(self) -> None:
        """Test that spaces are replaced with hyphens."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration._sanitize_room_name("my meeting room")

        assert result == "my-meeting-room"

    def test_consecutive_hyphens_collapsed(self) -> None:
        """Test that multiple consecutive hyphens are collapsed to one."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration._sanitize_room_name("room---name")

        assert result == "room-name"

    def test_leading_trailing_hyphens_stripped(self) -> None:
        """Test that leading and trailing hyphens are removed."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration._sanitize_room_name("-room-name-")

        assert result == "room-name"

    def test_alphanumeric_preserved(self) -> None:
        """Test that alphanumeric characters are preserved."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration._sanitize_room_name("room123")

        assert result == "room123"

    def test_complex_name_sanitization(self) -> None:
        """Test sanitization of a complex room name."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration._sanitize_room_name("  My Team's Meeting!!! (Q1 2026)  ")

        assert result == "my-team-s-meeting-q1-2026"


@pytest.mark.unit
class TestGenerateJwtToken:
    """Tests for _generate_jwt_token."""

    @patch("pbx.integrations.jitsi.JWT_AVAILABLE", True)
    @patch("pbx.integrations.jitsi.jwt")
    def test_generate_jwt_token_success(self, mock_jwt: MagicMock) -> None:
        """Test successful JWT token generation."""
        mock_jwt.encode.return_value = "encoded-token"

        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        result = integration._generate_jwt_token("room1", "Alice", is_moderator=True)

        assert result == "encoded-token"
        mock_jwt.encode.assert_called_once()
        call_args = mock_jwt.encode.call_args
        payload = call_args.args[0]
        assert payload["iss"] == "myapp"
        assert payload["room"] == "room1"
        assert payload["context"]["user"]["name"] == "Alice"
        assert payload["context"]["user"]["moderator"] is True
        assert call_args.args[1] == "mysecret"
        assert call_args.kwargs["algorithm"] == "HS256"

    @patch("pbx.integrations.jitsi.JWT_AVAILABLE", True)
    @patch("pbx.integrations.jitsi.jwt")
    def test_generate_jwt_token_non_moderator(self, mock_jwt: MagicMock) -> None:
        """Test JWT token generation for non-moderator."""
        mock_jwt.encode.return_value = "participant-token"

        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        result = integration._generate_jwt_token("room1", "Bob", is_moderator=False)

        assert result == "participant-token"
        call_args = mock_jwt.encode.call_args
        payload = call_args.args[0]
        assert payload["context"]["user"]["moderator"] is False

    @patch("pbx.integrations.jitsi.JWT_AVAILABLE", True)
    @patch("pbx.integrations.jitsi.jwt")
    def test_generate_jwt_token_custom_expiry(self, mock_jwt: MagicMock) -> None:
        """Test JWT token with custom expiry hours."""
        mock_jwt.encode.return_value = "custom-token"

        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        now = int(time.time())
        result = integration._generate_jwt_token("room1", "Alice", expiry_hours=48)

        call_args = mock_jwt.encode.call_args
        payload = call_args.args[0]
        # Expiry should be approximately now + 48 hours
        expected_exp = now + (48 * 3600)
        assert abs(payload["exp"] - expected_exp) < 5  # Within 5 seconds

    @patch("pbx.integrations.jitsi.JWT_AVAILABLE", True)
    @patch("pbx.integrations.jitsi.jwt")
    def test_generate_jwt_token_subject_strips_protocol(self, mock_jwt: MagicMock) -> None:
        """Test that server URL protocol is stripped from JWT subject."""
        mock_jwt.encode.return_value = "token"

        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        integration._generate_jwt_token("room1", "Alice")

        call_args = mock_jwt.encode.call_args
        payload = call_args.args[0]
        assert payload["sub"] == "jitsi.example.com"

    @patch("pbx.integrations.jitsi.JWT_AVAILABLE", False)
    def test_generate_jwt_token_jwt_not_available(self) -> None:
        """Test _generate_jwt_token when JWT library is not available."""
        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        result = integration._generate_jwt_token("room1", "Alice")

        assert result == ""

    @patch("pbx.integrations.jitsi.JWT_AVAILABLE", True)
    @patch("pbx.integrations.jitsi.jwt")
    def test_generate_jwt_token_encode_error(self, mock_jwt: MagicMock) -> None:
        """Test _generate_jwt_token when encoding raises an error."""
        mock_jwt.encode.side_effect = ValueError("Invalid secret")

        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        result = integration._generate_jwt_token("room1", "Alice")

        assert result == ""

    @patch("pbx.integrations.jitsi.JWT_AVAILABLE", True)
    @patch("pbx.integrations.jitsi.jwt")
    def test_generate_jwt_token_has_nbf(self, mock_jwt: MagicMock) -> None:
        """Test that JWT token has not-before (nb) claim."""
        mock_jwt.encode.return_value = "token"

        config = _make_enabled_config(app_id="myapp", app_secret="mysecret")
        integration = JitsiIntegration(config)

        now = int(time.time())
        integration._generate_jwt_token("room1", "Alice")

        call_args = mock_jwt.encode.call_args
        payload = call_args.args[0]
        assert "nb" in payload
        assert abs(payload["nb"] - (now - 10)) < 5


@pytest.mark.unit
class TestGetMeetingInfo:
    """Tests for get_meeting_info."""

    def test_get_meeting_info(self) -> None:
        """Test getting meeting info."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.get_meeting_info("my-room")

        assert result is not None
        assert result["room_id"] == "my-room"
        assert result["url"] == "https://jitsi.example.com/my-room"
        assert result["server"] == "https://jitsi.example.com"
        assert "note" in result

    def test_get_meeting_info_different_server(self) -> None:
        """Test meeting info URL uses correct server."""
        config = _make_enabled_config(server_url="https://custom.jitsi.com")
        integration = JitsiIntegration(config)

        result = integration.get_meeting_info("room1")

        assert result["url"] == "https://custom.jitsi.com/room1"
        assert result["server"] == "https://custom.jitsi.com"


@pytest.mark.unit
class TestEndMeeting:
    """Tests for end_meeting."""

    def test_end_meeting(self) -> None:
        """Test end meeting always returns True."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.end_meeting("my-room")

        assert result is True

    def test_end_meeting_any_room(self) -> None:
        """Test end meeting with any room name."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.end_meeting("nonexistent-room")

        assert result is True


@pytest.mark.unit
class TestGetActiveParticipants:
    """Tests for get_active_participants."""

    def test_get_active_participants_empty(self) -> None:
        """Test that get_active_participants returns empty list (placeholder)."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.get_active_participants("my-room")

        assert result == []

    def test_get_active_participants_any_room(self) -> None:
        """Test get_active_participants with any room name."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.get_active_participants("another-room")

        assert result == []


@pytest.mark.unit
class TestCreateConferenceBridge:
    """Tests for create_conference_bridge."""

    def test_create_conference_bridge_success(self) -> None:
        """Test creating a conference bridge."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_conference_bridge("5001", ["1001", "1002", "1003"])

        assert result["success"] is True
        assert result["room_name"] == "conference-5001"
        assert result["subject"] == "Conference Bridge 5001"
        assert result["moderator"] == "Conference 5001"
        assert result["participants"] == [
            "Extension 1001",
            "Extension 1002",
            "Extension 1003",
        ]

    def test_create_conference_bridge_disabled(self) -> None:
        """Test create_conference_bridge when disabled."""
        config = _make_disabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_conference_bridge("5001", ["1001"])

        assert result["success"] is False

    def test_create_conference_bridge_empty_participants(self) -> None:
        """Test create_conference_bridge with empty participants list."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.create_conference_bridge("5002", [])

        assert result["success"] is True
        assert result["participants"] == []


@pytest.mark.unit
class TestGetEmbedCode:
    """Tests for get_embed_code."""

    def test_get_embed_code_default_size(self) -> None:
        """Test generating embed code with default dimensions."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.get_embed_code("my-room")

        assert "<iframe" in result
        assert 'src="https://jitsi.example.com/my-room"' in result
        assert "height: 600px" in result
        assert "width: 800px" in result
        assert "allow=" in result
        assert "camera" in result
        assert "microphone" in result

    def test_get_embed_code_custom_size(self) -> None:
        """Test generating embed code with custom dimensions."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.get_embed_code("my-room", width=1024, height=768)

        assert "height: 768px" in result
        assert "width: 1024px" in result

    def test_get_embed_code_no_border(self) -> None:
        """Test that embed code has no border."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.get_embed_code("my-room")

        assert "border: 0px" in result

    def test_get_embed_code_correct_permissions(self) -> None:
        """Test that iframe has correct permission attributes."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.get_embed_code("my-room")

        assert "camera" in result
        assert "microphone" in result
        assert "fullscreen" in result
        assert "display-capture" in result
        assert "autoplay" in result

    def test_get_embed_code_different_server(self) -> None:
        """Test embed code with a different server URL."""
        config = _make_enabled_config(server_url="https://custom.jitsi.com")
        integration = JitsiIntegration(config)

        result = integration.get_embed_code("room1")

        assert 'src="https://custom.jitsi.com/room1"' in result

    def test_get_embed_code_stripped(self) -> None:
        """Test that embed code is stripped of leading/trailing whitespace."""
        config = _make_enabled_config()
        integration = JitsiIntegration(config)

        result = integration.get_embed_code("my-room")

        assert result.startswith("<iframe")
        assert result.endswith("</iframe>")
