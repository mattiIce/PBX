"""Comprehensive tests for pbx.integrations.outlook module."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pbx.integrations.outlook import OutlookIntegration

# Ensure msal is available as a mock in the module namespace before import
_mock_msal = MagicMock()
sys.modules.setdefault("msal", _mock_msal)


@pytest.mark.unit
class TestOutlookIntegrationInit:
    """Tests for OutlookIntegration initialization."""

    @patch("pbx.integrations.outlook.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with integration disabled."""
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        assert integration.enabled is False
        assert integration.access_token is None
        assert integration.msal_app is None

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", False)
    @patch("pbx.integrations.outlook.get_logger")
    def test_init_enabled_no_requests(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when requests library is unavailable."""
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": True,
            "integrations.outlook.tenant_id": "tid",
            "integrations.outlook.client_id": "cid",
            "integrations.outlook.client_secret": "secret",
            "integrations.outlook.sync_interval": 300,
            "integrations.outlook.auto_dnd_in_meetings": True,
            "integrations.outlook.scopes": ["https://graph.microsoft.com/.default"],
        }.get(key, default)

        integration = OutlookIntegration(config)
        assert integration.enabled is False

    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", False)
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.get_logger")
    def test_init_enabled_no_msal(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when msal library is unavailable."""
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": True,
            "integrations.outlook.tenant_id": "tid",
            "integrations.outlook.client_id": "cid",
            "integrations.outlook.client_secret": "secret",
            "integrations.outlook.sync_interval": 300,
            "integrations.outlook.auto_dnd_in_meetings": True,
            "integrations.outlook.scopes": ["https://graph.microsoft.com/.default"],
        }.get(key, default)

        integration = OutlookIntegration(config)
        assert integration.enabled is False

    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.get_logger")
    def test_init_enabled_with_all_dependencies(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with all dependencies available."""
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": True,
            "integrations.outlook.tenant_id": "tid",
            "integrations.outlook.client_id": "cid",
            "integrations.outlook.client_secret": "secret",
            "integrations.outlook.sync_interval": 300,
            "integrations.outlook.auto_dnd_in_meetings": True,
            "integrations.outlook.scopes": ["https://graph.microsoft.com/.default"],
        }.get(key, default)

        integration = OutlookIntegration(config)
        assert integration.enabled is True
        assert integration.tenant_id == "tid"
        assert integration.client_id == "cid"
        assert integration.client_secret == "secret"
        assert integration.sync_interval == 300

    @patch("pbx.integrations.outlook.get_logger")
    def test_init_default_config_values(self, mock_get_logger: MagicMock) -> None:
        """Test default configuration values when not specified."""
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        assert integration.sync_interval == 300
        assert integration.auto_dnd_in_meetings is True
        assert integration.graph_endpoint == "https://graph.microsoft.com/v1.0"


@pytest.mark.unit
class TestInitializeMsal:
    """Tests for _initialize_msal method."""

    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.get_logger")
    def test_initialize_msal_missing_credentials(self, mock_get_logger: MagicMock) -> None:
        """Test MSAL initialization with missing credentials."""
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
            "integrations.outlook.tenant_id": None,
            "integrations.outlook.client_id": None,
            "integrations.outlook.client_secret": None,
        }.get(key, default)

        integration = OutlookIntegration(config)
        integration.enabled = True
        integration.tenant_id = None
        integration._initialize_msal()
        assert integration.msal_app is None

    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.get_logger")
    def test_initialize_msal_exception(self, mock_get_logger: MagicMock) -> None:
        """Test MSAL initialization when exception occurs."""
        import pbx.integrations.outlook as outlook_mod
        from pbx.integrations.outlook import OutlookIntegration

        # Temporarily make msal.ConfidentialClientApplication raise
        original_msal = getattr(outlook_mod, "msal", None)
        mock_msal_mod = MagicMock()
        mock_msal_mod.ConfidentialClientApplication.side_effect = Exception("MSAL err")
        outlook_mod.msal = mock_msal_mod

        try:
            config = MagicMock()
            config.get.side_effect = lambda key, default=None: {
                "integrations.outlook.enabled": True,
                "integrations.outlook.tenant_id": "tid",
                "integrations.outlook.client_id": "cid",
                "integrations.outlook.client_secret": "secret",
                "integrations.outlook.sync_interval": 300,
                "integrations.outlook.auto_dnd_in_meetings": True,
                "integrations.outlook.scopes": ["https://graph.microsoft.com/.default"],
            }.get(key, default)

            integration = OutlookIntegration(config)
            assert integration.msal_app is None
        finally:
            if original_msal is not None:
                outlook_mod.msal = original_msal


@pytest.mark.unit
class TestAuthenticate:
    """Tests for authenticate method."""

    def _make_integration(self) -> OutlookIntegration:
        """Create a minimally configured integration for auth testing."""
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        return integration

    @patch("pbx.integrations.outlook.get_logger")
    def test_authenticate_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test authentication when integration is disabled."""
        integration = self._make_integration()
        integration.enabled = False
        assert integration.authenticate() is False

    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.get_logger")
    def test_authenticate_no_msal_app_init_fails(self, mock_get_logger: MagicMock) -> None:
        """Test authentication when MSAL app is None and re-init fails."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = None
        integration.tenant_id = None  # will cause _initialize_msal to bail
        assert integration.authenticate() is False

    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_authenticate_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful authentication."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}

        result = integration.authenticate()
        assert result is True
        assert integration.access_token == "token123"

    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_authenticate_failure(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test authentication failure (no access_token in response)."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Bad credentials",
        }

        result = integration.authenticate()
        assert result is False
        assert integration.access_token is None

    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_authenticate_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test authentication with exception."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.side_effect = KeyError("fail")

        # Ensure requests.RequestException is a real exception class for the handler
        mock_requests.RequestException = Exception

        result = integration.authenticate()
        assert result is False


@pytest.mark.unit
class TestGetCalendarEvents:
    """Tests for get_calendar_events method."""

    def _make_integration(self) -> OutlookIntegration:
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        return integration

    @patch("pbx.integrations.outlook.get_logger")
    def test_get_calendar_events_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test calendar events retrieval when integration is disabled."""
        integration = self._make_integration()
        integration.enabled = False
        result = integration.get_calendar_events("user@example.com")
        assert result == []

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_get_calendar_events_auth_fails(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test calendar events when authentication fails."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"error": "fail"}
        mock_requests.RequestException = Exception

        result = integration.get_calendar_events("user@example.com")
        assert result == []

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_get_calendar_events_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful calendar events retrieval."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "subject": "Team Meeting",
                    "start": {"dateTime": "2026-01-01T10:00:00"},
                    "end": {"dateTime": "2026-01-01T11:00:00"},
                    "location": {"displayName": "Room A"},
                    "organizer": {"emailAddress": {"name": "Alice"}},
                    "isAllDay": False,
                    "isCancelled": False,
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        result = integration.get_calendar_events(
            "user@example.com", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
        )
        assert len(result) == 1
        assert result[0]["subject"] == "Team Meeting"
        assert result[0]["location"] == "Room A"
        assert result[0]["organizer"] == "Alice"

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_get_calendar_events_default_times(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test calendar events with default start/end times."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": []}
        mock_requests.get.return_value = mock_response

        result = integration.get_calendar_events("user@example.com")
        assert result == []

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_get_calendar_events_api_error(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test calendar events with API error response."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_requests.get.return_value = mock_response

        result = integration.get_calendar_events("user@example.com")
        assert result == []

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_get_calendar_events_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test calendar events with exception during request."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.get.side_effect = TypeError("type error")
        mock_requests.RequestException = Exception

        result = integration.get_calendar_events("user@example.com")
        assert result == []


@pytest.mark.unit
class TestCheckUserAvailability:
    """Tests for check_user_availability method."""

    def _make_integration(self) -> OutlookIntegration:
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        return integration

    @patch("pbx.integrations.outlook.get_logger")
    def test_check_availability_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test availability check when disabled."""
        integration = self._make_integration()
        integration.enabled = False
        result = integration.check_user_availability("user@example.com")
        assert result == "unknown"

    @patch("pbx.integrations.outlook.get_logger")
    def test_check_availability_busy(self, mock_get_logger: MagicMock) -> None:
        """Test availability check returns busy when in meeting."""
        integration = self._make_integration()
        integration.enabled = True

        now = datetime.now(UTC)
        events = [
            {
                "subject": "Meeting",
                "start": (now - timedelta(minutes=30)).isoformat(),
                "end": (now + timedelta(minutes=30)).isoformat(),
                "is_cancelled": False,
            }
        ]

        with (
            patch.object(integration, "get_calendar_events", return_value=events),
            patch.object(integration, "get_out_of_office_status", return_value=None),
        ):
            result = integration.check_user_availability("user@example.com")
            assert result == "busy"

    @patch("pbx.integrations.outlook.get_logger")
    def test_check_availability_available(self, mock_get_logger: MagicMock) -> None:
        """Test availability check returns available when no events."""
        integration = self._make_integration()
        integration.enabled = True

        with (
            patch.object(integration, "get_calendar_events", return_value=[]),
            patch.object(integration, "get_out_of_office_status", return_value=None),
        ):
            result = integration.check_user_availability("user@example.com")
            assert result == "available"

    @patch("pbx.integrations.outlook.get_logger")
    def test_check_availability_out_of_office(self, mock_get_logger: MagicMock) -> None:
        """Test availability check returns out_of_office."""
        integration = self._make_integration()
        integration.enabled = True

        with (
            patch.object(integration, "get_calendar_events", return_value=[]),
            patch.object(
                integration,
                "get_out_of_office_status",
                return_value={"status": "scheduled"},
            ),
        ):
            result = integration.check_user_availability("user@example.com")
            assert result == "out_of_office"

    @patch("pbx.integrations.outlook.get_logger")
    def test_check_availability_cancelled_event(self, mock_get_logger: MagicMock) -> None:
        """Test availability check ignores cancelled events."""
        integration = self._make_integration()
        integration.enabled = True

        now = datetime.now(UTC)
        events = [
            {
                "subject": "Cancelled Meeting",
                "start": (now - timedelta(minutes=30)).isoformat(),
                "end": (now + timedelta(minutes=30)).isoformat(),
                "is_cancelled": True,
            }
        ]

        with (
            patch.object(integration, "get_calendar_events", return_value=events),
            patch.object(integration, "get_out_of_office_status", return_value=None),
        ):
            result = integration.check_user_availability("user@example.com")
            assert result == "available"


@pytest.mark.unit
class TestSyncContacts:
    """Tests for sync_contacts method."""

    def _make_integration(self) -> OutlookIntegration:
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        return integration

    @patch("pbx.integrations.outlook.get_logger")
    def test_sync_contacts_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test contact sync when integration is disabled."""
        integration = self._make_integration()
        integration.enabled = False
        result = integration.sync_contacts("user@example.com")
        assert result == []

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_sync_contacts_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful contact sync."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "displayName": "Bob Smith",
                    "emailAddresses": [{"address": "bob@example.com"}],
                    "businessPhones": ["+15551234567"],
                    "mobilePhone": "+15559876543",
                    "homePhones": ["+15551111111"],
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        result = integration.sync_contacts("user@example.com")
        assert len(result) == 1
        assert result[0]["name"] == "Bob Smith"
        assert result[0]["email"] == "bob@example.com"
        assert result[0]["business_phone"] == "+15551234567"
        assert result[0]["mobile_phone"] == "+15559876543"
        assert result[0]["home_phone"] == "+15551111111"

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_sync_contacts_empty_phones(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test contact sync with empty phone lists."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "displayName": "Jane Doe",
                    "emailAddresses": [],
                    "businessPhones": [],
                    "mobilePhone": None,
                    "homePhones": [],
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        result = integration.sync_contacts("user@example.com")
        assert len(result) == 1
        assert result[0]["email"] is None
        assert result[0]["business_phone"] is None
        assert result[0]["home_phone"] is None

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_sync_contacts_api_error(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test contact sync with API error."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_requests.get.return_value = mock_response

        result = integration.sync_contacts("user@example.com")
        assert result == []

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_sync_contacts_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test contact sync with exception."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.get.side_effect = KeyError("fail")
        mock_requests.RequestException = Exception

        result = integration.sync_contacts("user@example.com")
        assert result == []


@pytest.mark.unit
class TestLogCallToCalendar:
    """Tests for log_call_to_calendar method."""

    def _make_integration(self) -> OutlookIntegration:
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        return integration

    @patch("pbx.integrations.outlook.get_logger")
    def test_log_call_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test log call when disabled."""
        integration = self._make_integration()
        integration.enabled = False
        result = integration.log_call_to_calendar("user@example.com", {})
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_log_call_success(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test successful call logging."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_requests.post.return_value = mock_response

        call_details = {
            "from": "1001",
            "to": "1002",
            "duration": 120,
            "timestamp": datetime.now(UTC).isoformat(),
            "direction": "inbound",
        }

        result = integration.log_call_to_calendar("user@example.com", call_details)
        assert result is True

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_log_call_outbound(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test call logging for outbound call."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_requests.post.return_value = mock_response

        call_details = {
            "from": "1001",
            "to": "1002",
            "duration": 60,
            "direction": "outbound",
        }

        result = integration.log_call_to_calendar("user@example.com", call_details)
        assert result is True

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_log_call_defaults(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test call logging with default values."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_requests.post.return_value = mock_response

        # Minimal call details - should use defaults
        call_details = {}

        result = integration.log_call_to_calendar("user@example.com", call_details)
        assert result is True

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_log_call_non_string_timestamp(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test call logging with non-string timestamp (uses now)."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_requests.post.return_value = mock_response

        call_details = {
            "from": "1001",
            "to": "1002",
            "duration": 60,
            "timestamp": 12345,  # Not a string
        }

        result = integration.log_call_to_calendar("user@example.com", call_details)
        assert result is True

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_log_call_api_failure(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test call logging with API failure."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.post.return_value = mock_response

        result = integration.log_call_to_calendar("user@example.com", {"from": "1001"})
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_log_call_exception(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test call logging with exception."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.post.side_effect = TypeError("error")
        mock_requests.RequestException = Exception

        result = integration.log_call_to_calendar("user@example.com", {"from": "1001"})
        assert result is False


@pytest.mark.unit
class TestGetOutOfOfficeStatus:
    """Tests for get_out_of_office_status method."""

    def _make_integration(self) -> OutlookIntegration:
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        return integration

    @patch("pbx.integrations.outlook.get_logger")
    def test_get_ooo_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test OOO status when disabled."""
        integration = self._make_integration()
        integration.enabled = False
        result = integration.get_out_of_office_status("user@example.com")
        assert result is None

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_get_ooo_success(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test successful OOO status retrieval."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "scheduled",
            "externalReplyMessage": "I am out of office.",
            "internalReplyMessage": "OOO internal.",
            "scheduledStartDateTime": {"dateTime": "2026-01-01T00:00:00"},
            "scheduledEndDateTime": {"dateTime": "2026-01-05T00:00:00"},
        }
        mock_requests.get.return_value = mock_response

        result = integration.get_out_of_office_status("user@example.com")
        assert result is not None
        assert result["status"] == "scheduled"
        assert result["external_reply"] == "I am out of office."

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_get_ooo_api_error(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test OOO status with API error."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_requests.get.return_value = mock_response

        result = integration.get_out_of_office_status("user@example.com")
        assert result is None

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_get_ooo_exception(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test OOO status with exception."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.get.side_effect = ValueError("fail")
        mock_requests.RequestException = Exception

        result = integration.get_out_of_office_status("user@example.com")
        assert result is None


@pytest.mark.unit
class TestSendMeetingReminder:
    """Tests for send_meeting_reminder method."""

    def _make_integration(self) -> OutlookIntegration:
        from pbx.integrations.outlook import OutlookIntegration

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "integrations.outlook.enabled": False,
        }.get(key, default)

        integration = OutlookIntegration(config)
        return integration

    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test reminder when integration is disabled."""
        integration = self._make_integration()
        integration.enabled = False
        result = integration.send_meeting_reminder("user@example.com", "meet1")
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_auth_fails(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test reminder when authentication fails."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"error": "fail"}
        mock_requests.RequestException = Exception

        result = integration.send_meeting_reminder("user@example.com", "meet1")
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_meeting_fetch_fails(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test reminder when meeting fetch fails."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        result = integration.send_meeting_reminder("user@example.com", "meet1")
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_no_start_time(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test reminder when meeting has no start time."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subject": "Meeting",
            "start": {},
        }
        mock_requests.get.return_value = mock_response

        result = integration.send_meeting_reminder("user@example.com", "meet1")
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_past_time(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test reminder when meeting time has passed."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        past_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subject": "Past Meeting",
            "start": {"dateTime": past_time},
        }
        mock_requests.get.return_value = mock_response

        result = integration.send_meeting_reminder("user@example.com", "meet1")
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_no_pbx_core(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test reminder without PBX core logs warning and returns False."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subject": "Future Meeting",
            "start": {"dateTime": future_time},
        }
        mock_requests.get.return_value = mock_response

        result = integration.send_meeting_reminder("user@example.com", "meet1", pbx_core=None)
        assert result is False

    @patch("threading.Timer")
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_with_pbx_core_and_extension(
        self,
        mock_get_logger: MagicMock,
        mock_requests: MagicMock,
        mock_timer_cls: MagicMock,
    ) -> None:
        """Test reminder with PBX core and extension number."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subject": "Future Meeting",
            "start": {"dateTime": future_time},
        }
        mock_requests.get.return_value = mock_response

        mock_timer_instance = MagicMock()
        mock_timer_cls.return_value = mock_timer_instance

        mock_pbx = MagicMock()

        result = integration.send_meeting_reminder(
            "user@example.com",
            "meet1",
            pbx_core=mock_pbx,
            extension_number="1001",
        )
        assert result is True
        mock_timer_instance.start.assert_called_once()

    @patch("threading.Timer")
    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_with_pbx_core_lookup_extension(
        self,
        mock_get_logger: MagicMock,
        mock_requests: MagicMock,
        mock_timer_cls: MagicMock,
    ) -> None:
        """Test reminder with PBX core looking up extension by email."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subject": "Future Meeting",
            "start": {"dateTime": future_time},
        }
        mock_requests.get.return_value = mock_response

        mock_timer_instance = MagicMock()
        mock_timer_cls.return_value = mock_timer_instance

        mock_ext = MagicMock()
        mock_ext.config = {"email": "user@example.com"}

        mock_pbx = MagicMock()
        mock_pbx.extension_registry.extensions = {"1001": mock_ext}

        result = integration.send_meeting_reminder(
            "user@example.com",
            "meet1",
            pbx_core=mock_pbx,
        )
        assert result is True

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_no_extension_found(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test reminder when no extension found for email."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subject": "Future Meeting",
            "start": {"dateTime": future_time},
        }
        mock_requests.get.return_value = mock_response

        mock_pbx = MagicMock()
        mock_pbx.extension_registry.extensions = {}

        result = integration.send_meeting_reminder(
            "user@example.com",
            "meet1",
            pbx_core=mock_pbx,
        )
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_invalid_start_time(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test reminder with invalid start time format."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.RequestException = Exception

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subject": "Meeting",
            "start": {"dateTime": "not-a-valid-date"},
        }
        mock_requests.get.return_value = mock_response

        result = integration.send_meeting_reminder("user@example.com", "meet1")
        assert result is False

    @patch("pbx.integrations.outlook.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.outlook.MSAL_AVAILABLE", True)
    @patch("pbx.integrations.outlook.requests")
    @patch("pbx.integrations.outlook.get_logger")
    def test_reminder_exception(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test reminder with general exception."""
        integration = self._make_integration()
        integration.enabled = True
        integration.msal_app = MagicMock()
        integration.msal_app.acquire_token_for_client.return_value = {"access_token": "token123"}
        mock_requests.get.side_effect = RuntimeError("unexpected")

        result = integration.send_meeting_reminder("user@example.com", "meet1")
        assert result is False
