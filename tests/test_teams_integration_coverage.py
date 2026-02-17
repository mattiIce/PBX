"""Comprehensive tests for Microsoft Teams integration."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestTeamsIntegrationInit:
    """Tests for TeamsIntegration initialization."""

    @patch("pbx.integrations.teams.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when integration is disabled."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)

        assert integration.enabled is None
        assert integration.access_token is None
        assert integration.msal_app is None

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_init_enabled_with_all_dependencies(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when enabled with all deps available."""
        import sys

        mock_msal = MagicMock()
        sys.modules["msal"] = mock_msal

        try:
            import importlib

            import pbx.integrations.teams as teams_mod

            teams_mod.msal = mock_msal

            config = MagicMock()

            def config_get(key: str, default=None):
                mapping = {
                    "integrations.microsoft_teams.enabled": True,
                    "integrations.microsoft_teams.tenant_id": "tenant-123",
                    "integrations.microsoft_teams.client_id": "client-123",
                    "integrations.microsoft_teams.client_secret": "secret-123",
                    "integrations.microsoft_teams.direct_routing_domain": "sip.contoso.com",
                }
                return mapping.get(key, default)

            config.get.side_effect = config_get

            mock_msal.ConfidentialClientApplication.return_value = MagicMock()
            integration = teams_mod.TeamsIntegration(config)

            assert integration.enabled is True
            assert integration.tenant_id == "tenant-123"
            assert integration.client_id == "client-123"
            assert integration.msal_app is not None
        finally:
            if "msal" in sys.modules and isinstance(sys.modules["msal"], MagicMock):
                del sys.modules["msal"]
            if hasattr(teams_mod, "msal") and isinstance(teams_mod.msal, MagicMock):
                delattr(teams_mod, "msal")

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", False)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_init_enabled_no_msal(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when msal is not available."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "integrations.microsoft_teams.enabled": True,
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = TeamsIntegration(config)

        assert integration.enabled is False

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", False)
    @patch("pbx.integrations.teams.get_logger")
    def test_init_enabled_no_requests(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when requests is not available."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "integrations.microsoft_teams.enabled": True,
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = TeamsIntegration(config)

        assert integration.enabled is False

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_init_msal_missing_credentials(self, mock_get_logger: MagicMock) -> None:
        """Test MSAL initialization with missing credentials."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "integrations.microsoft_teams.enabled": True,
                "integrations.microsoft_teams.tenant_id": None,
                "integrations.microsoft_teams.client_id": None,
                "integrations.microsoft_teams.client_secret": None,
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = TeamsIntegration(config)

        assert integration.msal_app is None

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_init_msal_exception(self, mock_get_logger: MagicMock) -> None:
        """Test MSAL initialization handles exceptions."""
        import sys

        mock_msal = MagicMock()
        sys.modules["msal"] = mock_msal

        try:
            import pbx.integrations.teams as teams_mod

            teams_mod.msal = mock_msal

            config = MagicMock()

            def config_get(key: str, default=None):
                mapping = {
                    "integrations.microsoft_teams.enabled": True,
                    "integrations.microsoft_teams.tenant_id": "tenant-123",
                    "integrations.microsoft_teams.client_id": "client-123",
                    "integrations.microsoft_teams.client_secret": "secret-123",
                }
                return mapping.get(key, default)

            config.get.side_effect = config_get

            mock_msal.ConfidentialClientApplication.side_effect = Exception("MSAL init error")
            integration = teams_mod.TeamsIntegration(config)

            assert integration.msal_app is None
        finally:
            if "msal" in sys.modules and isinstance(sys.modules["msal"], MagicMock):
                del sys.modules["msal"]
            if hasattr(teams_mod, "msal") and isinstance(teams_mod.msal, MagicMock):
                delattr(teams_mod, "msal")


@pytest.mark.unit
class TestTeamsAuthenticate:
    """Tests for TeamsIntegration.authenticate."""

    @patch("pbx.integrations.teams.get_logger")
    def test_authenticate_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test authenticate when disabled."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = False

        assert integration.authenticate() is False

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_authenticate_success(self, mock_get_logger: MagicMock) -> None:
        """Test successful authentication."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {
            "access_token": "test-token-123"
        }

        result = integration.authenticate()

        assert result is True
        assert integration.access_token == "test-token-123"

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_authenticate_failure(self, mock_get_logger: MagicMock) -> None:
        """Test authentication failure."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "bad credentials",
        }

        result = integration.authenticate()

        assert result is False

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_authenticate_no_msal_app_reinitializes(self, mock_get_logger: MagicMock) -> None:
        """Test authenticate re-initializes MSAL if app is None."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = None

        result = integration.authenticate()

        assert result is False

    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_authenticate_exception(self, mock_get_logger: MagicMock) -> None:
        """Test authenticate handles exceptions."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.side_effect = ValueError("token error")

        result = integration.authenticate()

        assert result is False


@pytest.mark.unit
class TestTeamsSyncPresence:
    """Tests for TeamsIntegration.sync_presence."""

    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_sync_presence_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test sync_presence when disabled."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = False

        assert integration.sync_presence("user1", "available") is False

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_sync_presence_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful presence sync."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.access_token = "test-token"
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        result = integration.sync_presence("user@contoso.com", "busy")

        assert result is True

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_sync_presence_status_mapping(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test presence status mapping."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.access_token = "test-token"
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        for pbx_status in ["available", "busy", "away", "dnd", "offline", "in_call", "in_meeting"]:
            result = integration.sync_presence("user@contoso.com", pbx_status)
            assert result is True

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_sync_presence_api_error(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test presence sync with API error."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.access_token = "test-token"
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_requests.post.return_value = mock_response

        result = integration.sync_presence("user@contoso.com", "available")

        assert result is False

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_sync_presence_request_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test presence sync with request exception."""
        import requests as real_requests

        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.access_token = "test-token"
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        mock_requests.post.side_effect = real_requests.RequestException("Network error")
        mock_requests.RequestException = real_requests.RequestException

        result = integration.sync_presence("user@contoso.com", "available")

        assert result is False


@pytest.mark.unit
class TestTeamsRouteCall:
    """Tests for TeamsIntegration.route_call_to_teams."""

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test routing when disabled."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = False

        assert integration.route_call_to_teams("1001", "user@contoso.com") is False

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_no_domain(self, mock_get_logger: MagicMock) -> None:
        """Test routing with no direct routing domain."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.direct_routing_domain = None

        assert integration.route_call_to_teams("1001", "user@contoso.com") is False

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_with_at_sign(self, mock_get_logger: MagicMock) -> None:
        """Test routing when user already has domain."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.direct_routing_domain = "sip.contoso.com"

        result = integration.route_call_to_teams("1001", "user@contoso.com")

        assert result is False  # No pbx_core provided

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_without_at_sign(self, mock_get_logger: MagicMock) -> None:
        """Test routing when user doesn't have domain."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.direct_routing_domain = "sip.contoso.com"

        result = integration.route_call_to_teams("1001", "user1")

        assert result is False  # No pbx_core provided

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_with_pbx_core_trunk_found(self, mock_get_logger: MagicMock) -> None:
        """Test routing with PBX core and matching trunk."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.direct_routing_domain = "sip.contoso.com"

        trunk = MagicMock()
        trunk.name = "Teams Trunk"
        trunk.host = "sip.contoso.com"
        trunk.can_make_call.return_value = True
        trunk.allocate_channel.return_value = True

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks = {"teams": trunk}

        result = integration.route_call_to_teams("1001", "user@contoso.com", pbx_core)

        assert result is True

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_trunk_cannot_make_call(self, mock_get_logger: MagicMock) -> None:
        """Test routing when trunk cannot make call."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.direct_routing_domain = "sip.contoso.com"

        trunk = MagicMock()
        trunk.name = "Teams Trunk"
        trunk.host = "sip.contoso.com"
        trunk.can_make_call.return_value = False

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks = {"teams": trunk}

        result = integration.route_call_to_teams("1001", "user@contoso.com", pbx_core)

        assert result is False

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_allocate_channel_fails(self, mock_get_logger: MagicMock) -> None:
        """Test routing when channel allocation fails."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.direct_routing_domain = "sip.contoso.com"

        trunk = MagicMock()
        trunk.name = "Teams Trunk"
        trunk.host = "sip.contoso.com"
        trunk.can_make_call.return_value = True
        trunk.allocate_channel.return_value = False

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks = {"teams": trunk}

        result = integration.route_call_to_teams("1001", "user@contoso.com", pbx_core)

        assert result is False

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_no_trunk_found(self, mock_get_logger: MagicMock) -> None:
        """Test routing when no Teams trunk is found."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.direct_routing_domain = "sip.contoso.com"

        trunk = MagicMock()
        trunk.name = "Regular Trunk"
        trunk.host = "other-domain.com"

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks = {"regular": trunk}

        result = integration.route_call_to_teams("1001", "user@contoso.com", pbx_core)

        assert result is False

    @patch("pbx.integrations.teams.get_logger")
    def test_route_call_exception_in_trunk(self, mock_get_logger: MagicMock) -> None:
        """Test routing handles exceptions in trunk system."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.direct_routing_domain = "sip.contoso.com"

        pbx_core = MagicMock()
        pbx_core.trunk_system.trunks.values.side_effect = RuntimeError("trunk error")

        result = integration.route_call_to_teams("1001", "user@contoso.com", pbx_core)

        assert result is False


@pytest.mark.unit
class TestTeamsSendChat:
    """Tests for TeamsIntegration.send_chat_message."""

    @patch("pbx.integrations.teams.get_logger")
    def test_send_chat_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test sending chat when disabled."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = False

        assert integration.send_chat_message("user1", "Hello") is False

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_send_chat_success_create_chat(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test sending chat with new chat creation."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        chat_response = MagicMock()
        chat_response.status_code = 201
        chat_response.json.return_value = {"id": "chat-123"}

        message_response = MagicMock()
        message_response.status_code = 201

        mock_requests.post.side_effect = [chat_response, message_response]

        result = integration.send_chat_message("user@contoso.com", "Hello Teams!")

        assert result is True

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_send_chat_find_existing_chat(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test sending chat by finding existing chat."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        chat_create_response = MagicMock()
        chat_create_response.status_code = 409  # Conflict - chat already exists

        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "value": [
                {
                    "chatType": "oneOnOne",
                    "id": "existing-chat-123",
                    "members": [{"userId": "user@contoso.com"}],
                }
            ]
        }

        message_response = MagicMock()
        message_response.status_code = 201

        mock_requests.post.side_effect = [chat_create_response, message_response]
        mock_requests.get.return_value = search_response

        result = integration.send_chat_message("user@contoso.com", "Hello!")

        assert result is True

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_send_chat_no_chat_found(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test sending chat when no chat can be created or found."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        chat_create_response = MagicMock()
        chat_create_response.status_code = 500

        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = {"value": []}

        mock_requests.post.return_value = chat_create_response
        mock_requests.get.return_value = search_response

        result = integration.send_chat_message("user@contoso.com", "Hello!")

        assert result is False

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_send_chat_message_send_fails(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test sending chat when message sending fails."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        chat_response = MagicMock()
        chat_response.status_code = 201
        chat_response.json.return_value = {"id": "chat-123"}

        message_response = MagicMock()
        message_response.status_code = 500
        message_response.text = "Internal Server Error"

        mock_requests.post.side_effect = [chat_response, message_response]

        result = integration.send_chat_message("user@contoso.com", "Hello!")

        assert result is False


@pytest.mark.unit
class TestTeamsCreateMeeting:
    """Tests for TeamsIntegration.create_meeting_from_call."""

    @patch("pbx.integrations.teams.get_logger")
    def test_create_meeting_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test create meeting when disabled."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = False

        assert integration.create_meeting_from_call("call-1") is None

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_create_meeting_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful meeting creation."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "meeting-123",
            "joinWebUrl": "https://teams.microsoft.com/meet/123",
            "subject": "Test Meeting",
            "startDateTime": "2026-01-01T00:00:00Z",
            "endDateTime": "2026-01-01T01:00:00Z",
        }
        mock_requests.post.return_value = mock_response

        result = integration.create_meeting_from_call(
            "call-1", subject="Test Meeting", participants=["user1@contoso.com"]
        )

        assert result is not None
        assert result["meeting_id"] == "meeting-123"
        assert result["join_url"] == "https://teams.microsoft.com/meet/123"

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_create_meeting_default_subject(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test meeting creation with default subject."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "meeting-123",
            "joinWebUrl": "https://teams.microsoft.com/meet/123",
            "subject": "Escalated Call call-1",
        }
        mock_requests.post.return_value = mock_response

        result = integration.create_meeting_from_call("call-1")

        assert result is not None

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_create_meeting_api_failure(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test meeting creation with API failure."""
        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_requests.post.return_value = mock_response

        result = integration.create_meeting_from_call("call-1")

        assert result is None

    @patch("pbx.integrations.teams.requests")
    @patch("pbx.integrations.teams.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.teams.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.teams.get_logger")
    def test_create_meeting_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test meeting creation with exception."""
        import requests as real_requests

        from pbx.integrations.teams import TeamsIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = TeamsIntegration(config)
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "test-token"}

        mock_requests.post.side_effect = real_requests.RequestException("Connection error")
        mock_requests.RequestException = real_requests.RequestException

        result = integration.create_meeting_from_call("call-1")

        assert result is None
