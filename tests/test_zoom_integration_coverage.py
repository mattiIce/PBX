"""Comprehensive tests for Zoom integration."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestZoomIntegrationInit:
    """Tests for ZoomIntegration initialization."""

    @patch("pbx.integrations.zoom.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when integration is disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)

        assert integration.enabled is None
        assert integration.access_token is None
        assert integration.token_expiry is None

    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_init_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when enabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "integrations.zoom.enabled": True,
                "integrations.zoom.account_id": "acc-123",
                "integrations.zoom.client_id": "client-123",
                "integrations.zoom.client_secret": "secret-123",
                "integrations.zoom.phone_enabled": True,
                "integrations.zoom.api_base_url": "https://api.zoom.us/v2",
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = ZoomIntegration(config)

        assert integration.enabled is True
        assert integration.account_id == "acc-123"
        assert integration.phone_enabled is True

    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", False)
    @patch("pbx.integrations.zoom.get_logger")
    def test_init_enabled_no_requests(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when requests is not available."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {"integrations.zoom.enabled": True}
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = ZoomIntegration(config)

        assert integration.enabled is False


@pytest.mark.unit
class TestZoomAuthenticate:
    """Tests for ZoomIntegration.authenticate."""

    @patch("pbx.integrations.zoom.get_logger")
    def test_authenticate_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test authenticate when disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = False

        assert integration.authenticate() is False

    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_authenticate_token_still_valid(self, mock_get_logger: MagicMock) -> None:
        """Test authenticate when token is still valid."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.access_token = "valid-token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        assert integration.authenticate() is True

    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_authenticate_missing_credentials(self, mock_get_logger: MagicMock) -> None:
        """Test authenticate with missing credentials."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.account_id = None
        integration.client_id = None
        integration.client_secret = None

        assert integration.authenticate() is False

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_authenticate_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful authentication."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.account_id = "acc-123"
        integration.client_id = "client-123"
        integration.client_secret = "secret-123"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "zoom-token-123",
            "expires_in": 3600,
        }
        mock_requests.post.return_value = mock_response

        result = integration.authenticate()

        assert result is True
        assert integration.access_token == "zoom-token-123"
        assert integration.token_expiry is not None

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_authenticate_api_failure(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test authentication API failure."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.account_id = "acc-123"
        integration.client_id = "client-123"
        integration.client_secret = "secret-123"

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_requests.post.return_value = mock_response

        result = integration.authenticate()

        assert result is False

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_authenticate_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test authentication handles exceptions."""
        import requests as real_requests

        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.account_id = "acc-123"
        integration.client_id = "client-123"
        integration.client_secret = "secret-123"

        mock_requests.post.side_effect = real_requests.RequestException("Network error")
        mock_requests.RequestException = real_requests.RequestException

        result = integration.authenticate()

        assert result is False


@pytest.mark.unit
class TestZoomCreateMeeting:
    """Tests for ZoomIntegration.create_meeting."""

    @patch("pbx.integrations.zoom.get_logger")
    def test_create_meeting_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test create meeting when disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = False

        assert integration.create_meeting("Test") is None

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_create_meeting_success_instant(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test creating an instant meeting."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 12345,
            "join_url": "https://zoom.us/j/12345",
            "start_url": "https://zoom.us/s/12345",
            "password": "abc123",
            "topic": "Test Meeting",
            "start_time": None,
            "duration": 60,
        }
        mock_requests.post.return_value = mock_response

        result = integration.create_meeting("Test Meeting", duration_minutes=60)

        assert result is not None
        assert result["meeting_id"] == 12345
        assert result["join_url"] == "https://zoom.us/j/12345"
        assert result["password"] == "abc123"

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_create_meeting_success_scheduled(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test creating a scheduled meeting."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 12345,
            "join_url": "https://zoom.us/j/12345",
            "start_url": "https://zoom.us/s/12345",
            "password": "abc123",
            "topic": "Scheduled Meeting",
            "start_time": "2026-02-20T10:00:00Z",
            "duration": 30,
        }
        mock_requests.post.return_value = mock_response

        result = integration.create_meeting(
            "Scheduled Meeting",
            start_time="2026-02-20T10:00:00Z",
            duration_minutes=30,
            timezone="America/Chicago",
        )

        assert result is not None
        assert result["topic"] == "Scheduled Meeting"

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_create_meeting_api_failure(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test create meeting API failure."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.post.return_value = mock_response

        result = integration.create_meeting("Test")

        assert result is None

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_create_meeting_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test create meeting with exception."""
        import requests as real_requests

        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_requests.post.side_effect = real_requests.RequestException("Connection error")
        mock_requests.RequestException = real_requests.RequestException

        result = integration.create_meeting("Test")

        assert result is None


@pytest.mark.unit
class TestZoomInstantMeeting:
    """Tests for ZoomIntegration.start_instant_meeting."""

    @patch("pbx.integrations.zoom.get_logger")
    def test_instant_meeting_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test instant meeting when disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = False

        assert integration.start_instant_meeting("1001") is None

    @patch("pbx.integrations.zoom.get_logger")
    def test_instant_meeting_phone_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test instant meeting when phone is disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = False

        assert integration.start_instant_meeting("1001") is None

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_instant_meeting_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful instant meeting creation."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 99999,
            "join_url": "https://zoom.us/j/99999",
            "start_url": "https://zoom.us/s/99999",
            "password": "xyz",
            "topic": "Instant Meeting - Extension 1001",
            "start_time": None,
            "duration": 60,
        }
        mock_requests.post.return_value = mock_response

        result = integration.start_instant_meeting("1001")

        assert result is not None
        assert result["meeting_id"] == 99999


@pytest.mark.unit
class TestZoomRouteToPhone:
    """Tests for ZoomIntegration.route_to_zoom_phone."""

    @patch("pbx.integrations.zoom.get_logger")
    def test_route_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test route when disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = False

        assert integration.route_to_zoom_phone("1001", "+15551234567") is False

    @patch("pbx.integrations.zoom.get_logger")
    def test_route_phone_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test route when phone is disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = False

        assert integration.route_to_zoom_phone("1001", "+15551234567") is False

    @patch("pbx.integrations.zoom.get_logger")
    def test_route_no_pbx_core(self, mock_get_logger: MagicMock) -> None:
        """Test route without PBX core."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True

        assert integration.route_to_zoom_phone("1001", "+15551234567") is False

    @patch("pbx.integrations.zoom.get_logger")
    def test_route_with_trunk_success(self, mock_get_logger: MagicMock) -> None:
        """Test route with matching trunk."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True

        trunk = MagicMock()
        trunk.name = "Zoom Phone"
        trunk.host = "pbx.zoom.us"
        trunk.can_make_call.return_value = True
        trunk.allocate_channel.return_value = True

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks = {"zoom": trunk}

        result = integration.route_to_zoom_phone("1001", "+15551234567", pbx_core)

        assert result is True

    @patch("pbx.integrations.zoom.get_logger")
    def test_route_trunk_allocate_fails(self, mock_get_logger: MagicMock) -> None:
        """Test route when trunk allocation fails."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True

        trunk = MagicMock()
        trunk.name = "Zoom Phone"
        trunk.host = "pbx.zoom.us"
        trunk.can_make_call.return_value = True
        trunk.allocate_channel.return_value = False

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks = {"zoom": trunk}

        result = integration.route_to_zoom_phone("1001", "+15551234567", pbx_core)

        assert result is False

    @patch("pbx.integrations.zoom.get_logger")
    def test_route_no_zoom_trunk(self, mock_get_logger: MagicMock) -> None:
        """Test route when no zoom trunk is found."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True

        trunk = MagicMock()
        trunk.name = "Regular Trunk"
        trunk.host = "other.com"

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks = {"regular": trunk}

        result = integration.route_to_zoom_phone("1001", "+15551234567", pbx_core)

        assert result is False

    @patch("pbx.integrations.zoom.get_logger")
    def test_route_exception(self, mock_get_logger: MagicMock) -> None:
        """Test route handles exceptions."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks.values.side_effect = RuntimeError("error")

        result = integration.route_to_zoom_phone("1001", "+15551234567", pbx_core)

        assert result is False


@pytest.mark.unit
class TestZoomGetPhoneUserStatus:
    """Tests for ZoomIntegration.get_phone_user_status."""

    @patch("pbx.integrations.zoom.get_logger")
    def test_get_status_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test get status when disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = False

        assert integration.get_phone_user_status("user-1") is None

    @patch("pbx.integrations.zoom.get_logger")
    def test_get_status_phone_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test get status when phone is disabled."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = False

        assert integration.get_phone_user_status("user-1") is None

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_get_status_success_with_calling_plans(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test get status with calling plans."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calling_plans": [{"status": "active"}],
            "extension_number": "1001",
            "phone_numbers": ["+15551234567"],
        }
        mock_requests.get.return_value = mock_response

        result = integration.get_phone_user_status("user-1")

        assert result is not None
        assert result["status"] == "active"
        assert result["extension_number"] == "1001"

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_get_status_success_no_calling_plans(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test get status without calling plans."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calling_plans": [],
            "extension_number": "1001",
            "phone_numbers": [],
        }
        mock_requests.get.return_value = mock_response

        result = integration.get_phone_user_status("user-1")

        assert result is not None
        assert result["status"] == "unknown"

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_get_status_api_failure(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test get status API failure."""
        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_requests.get.return_value = mock_response

        result = integration.get_phone_user_status("user-1")

        assert result is None

    @patch("pbx.integrations.zoom.requests")
    @patch("pbx.integrations.zoom.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.zoom.get_logger")
    def test_get_status_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test get status handles exceptions."""
        import requests as real_requests

        from pbx.integrations.zoom import ZoomIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = ZoomIntegration(config)
        integration.enabled = True
        integration.phone_enabled = True
        integration.access_token = "token"
        integration.token_expiry = datetime.now(UTC) + timedelta(hours=1)

        mock_requests.get.side_effect = real_requests.RequestException("error")
        mock_requests.RequestException = real_requests.RequestException

        result = integration.get_phone_user_status("user-1")

        assert result is None
