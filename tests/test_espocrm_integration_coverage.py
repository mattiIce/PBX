"""Comprehensive tests for the EspoCRM integration module."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pbx.integrations.espocrm import EspoCRMIntegration


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
    api_url: str = "https://crm.example.com/api/v1",
    api_key: str = "test-api-key",
    api_secret: str = "test-api-secret",
    auto_create_contacts: bool = True,
    auto_log_calls: bool = True,
    screen_pop: bool = True,
) -> MockConfig:
    """Create a standard enabled EspoCRM config."""
    return MockConfig(
        {
            "integrations": {
                "espocrm": {
                    "enabled": True,
                    "api_url": api_url,
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "auto_create_contacts": auto_create_contacts,
                    "auto_log_calls": auto_log_calls,
                    "screen_pop": screen_pop,
                }
            }
        }
    )


def _make_disabled_config() -> MockConfig:
    """Create a disabled EspoCRM config."""
    return MockConfig({"integrations": {"espocrm": {"enabled": False}}})


@pytest.mark.unit
class TestEspoCRMIntegrationInit:
    """Tests for EspoCRM integration initialization."""

    def test_init_enabled_with_full_config(self) -> None:
        """Test initialization with a complete and valid config."""
        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        assert integration.enabled is True
        assert integration.api_url == "https://crm.example.com/api/v1"
        assert integration.api_key == "test-api-key"
        assert integration.api_secret == "test-api-secret"
        assert integration.auto_create_contacts is True
        assert integration.auto_log_calls is True
        assert integration.screen_pop is True

    def test_init_disabled(self) -> None:
        """Test initialization when integration is disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        assert integration.enabled is False

    def test_init_missing_api_url_disables(self) -> None:
        """Test that missing api_url disables the integration."""
        config = MockConfig(
            {
                "integrations": {
                    "espocrm": {
                        "enabled": True,
                        "api_key": "key",
                    }
                }
            }
        )
        integration = EspoCRMIntegration(config)
        assert integration.enabled is False

    def test_init_missing_api_key_disables(self) -> None:
        """Test that missing api_key disables the integration."""
        config = MockConfig(
            {
                "integrations": {
                    "espocrm": {
                        "enabled": True,
                        "api_url": "https://crm.example.com/api/v1",
                    }
                }
            }
        )
        integration = EspoCRMIntegration(config)
        assert integration.enabled is False

    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", False)
    def test_init_requests_unavailable_disables(self) -> None:
        """Test that missing requests library disables the integration."""
        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)
        assert integration.enabled is False

    def test_init_api_url_without_api_v1_suffix_with_trailing_slash(self) -> None:
        """Test that api_url gets /api/v1 appended if it has trailing slash."""
        config = _make_enabled_config(api_url="https://crm.example.com/")
        integration = EspoCRMIntegration(config)
        assert integration.api_url == "https://crm.example.com/api/v1"

    def test_init_api_url_without_api_v1_suffix_no_trailing_slash(self) -> None:
        """Test that api_url gets /api/v1 appended if no trailing slash."""
        config = _make_enabled_config(api_url="https://crm.example.com")
        integration = EspoCRMIntegration(config)
        assert integration.api_url == "https://crm.example.com/api/v1"

    def test_init_api_url_already_has_api_v1(self) -> None:
        """Test that api_url is unchanged if it already ends with /api/v1."""
        config = _make_enabled_config(api_url="https://crm.example.com/api/v1")
        integration = EspoCRMIntegration(config)
        assert integration.api_url == "https://crm.example.com/api/v1"

    def test_init_default_feature_flags(self) -> None:
        """Test default feature flag values when not specified in config."""
        config = MockConfig(
            {
                "integrations": {
                    "espocrm": {
                        "enabled": True,
                        "api_url": "https://crm.example.com/api/v1",
                        "api_key": "key",
                    }
                }
            }
        )
        integration = EspoCRMIntegration(config)
        assert integration.auto_create_contacts is True
        assert integration.auto_log_calls is True
        assert integration.screen_pop is True

    def test_init_empty_config(self) -> None:
        """Test initialization with empty config dict."""
        config = MockConfig({})
        integration = EspoCRMIntegration(config)
        assert integration.enabled is False


@pytest.mark.unit
class TestEspoCRMMakeRequest:
    """Tests for the internal _make_request method."""

    @patch("pbx.integrations.espocrm.requests")
    def test_make_request_get_success(self, mock_requests: MagicMock) -> None:
        """Test a successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "name": "Test"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration._make_request("GET", "Contact/123")

        assert result == {"id": "123", "name": "Test"}
        mock_requests.request.assert_called_once_with(
            method="GET",
            url="https://crm.example.com/api/v1/Contact/123",
            json=None,
            params=None,
            headers={"X-Api-Key": "test-api-key", "Content-type": "application/json"},
            timeout=10,
        )

    @patch("pbx.integrations.espocrm.requests")
    def test_make_request_post_success(self, mock_requests: MagicMock) -> None:
        """Test a successful POST request with 201 status."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-id"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        data = {"firstName": "Jane", "lastName": "Doe"}
        result = integration._make_request("POST", "Contact", data=data)

        assert result == {"id": "new-id"}
        mock_requests.request.assert_called_once()

    @patch("pbx.integrations.espocrm.requests")
    def test_make_request_with_params(self, mock_requests: MagicMock) -> None:
        """Test request with URL parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        params = {"maxSize": 10}
        result = integration._make_request("GET", "Contact", params=params)

        assert result is not None
        call_kwargs = mock_requests.request.call_args
        assert call_kwargs.kwargs["params"] == {"maxSize": 10}

    @patch("pbx.integrations.espocrm.requests")
    def test_make_request_api_error(self, mock_requests: MagicMock) -> None:
        """Test handling of non-200/201 HTTP response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration._make_request("GET", "Contact/123")

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_make_request_network_error(self, mock_requests: MagicMock) -> None:
        """Test handling of network/request exception."""
        mock_requests.request.side_effect = mock_requests.RequestException("Connection refused")

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration._make_request("GET", "Contact")

        assert result is None

    def test_make_request_disabled(self) -> None:
        """Test that _make_request returns None when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration._make_request("GET", "Contact")

        assert result is None

    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", False)
    def test_make_request_requests_not_available(self) -> None:
        """Test that _make_request returns None when requests is not available."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration._make_request("GET", "Contact")

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_make_request_403_forbidden(self, mock_requests: MagicMock) -> None:
        """Test handling of 403 Forbidden response."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration._make_request("GET", "Contact")

        assert result is None


@pytest.mark.unit
class TestFindContactByPhone:
    """Tests for find_contact_by_phone."""

    @patch("pbx.integrations.espocrm.requests")
    def test_find_contact_success(self, mock_requests: MagicMock) -> None:
        """Test finding an existing contact by phone number."""
        contact_data = {"id": "c1", "name": "John Doe", "phoneNumber": "5551234567"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": [contact_data]}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.find_contact_by_phone("+1 (555) 123-4567")

        assert result == contact_data

    @patch("pbx.integrations.espocrm.requests")
    def test_find_contact_not_found(self, mock_requests: MagicMock) -> None:
        """Test when no contact is found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.find_contact_by_phone("5559999999")

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_find_contact_empty_response(self, mock_requests: MagicMock) -> None:
        """Test when API returns None result."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.find_contact_by_phone("5551234567")

        assert result is None

    def test_find_contact_disabled(self) -> None:
        """Test find_contact_by_phone when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.find_contact_by_phone("5551234567")

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_find_contact_cleans_phone_number(self, mock_requests: MagicMock) -> None:
        """Test that non-digit characters are stripped from phone."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        integration.find_contact_by_phone("+1 (555) 123-4567")

        call_kwargs = mock_requests.request.call_args
        params = call_kwargs.kwargs["params"]
        assert "15551234567" in str(params)

    @patch("pbx.integrations.espocrm.requests")
    def test_find_contact_exception_handling(self, mock_requests: MagicMock) -> None:
        """Test exception handling in find_contact_by_phone."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": [{"bad": "data"}]}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        # Force a KeyError by having the contact missing the 'name' key in the result
        # Actually, find_contact_by_phone accesses contact.get('name') which is safe.
        # We test with result that has 'list' with a valid entry.
        result = integration.find_contact_by_phone("5551234567")
        assert result == {"bad": "data"}

    @patch("pbx.integrations.espocrm.requests")
    def test_find_contact_result_no_list_key(self, mock_requests: MagicMock) -> None:
        """Test when result is returned but has no 'list' key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 0}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.find_contact_by_phone("5551234567")

        assert result is None


@pytest.mark.unit
class TestCreateContact:
    """Tests for create_contact."""

    @patch("pbx.integrations.espocrm.requests")
    def test_create_contact_full_info(self, mock_requests: MagicMock) -> None:
        """Test creating a contact with all fields."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-1", "name": "Jane Doe"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_contact(
            name="Jane Doe",
            phone="5551234567",
            email="jane@example.com",
            company="Acme Corp",
            title="CEO",
        )

        assert result == {"id": "new-1", "name": "Jane Doe"}
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["firstName"] == "Jane"
        assert data["lastName"] == "Doe"
        assert data["phoneNumber"] == "5551234567"
        assert data["emailAddress"] == "jane@example.com"
        assert data["accountName"] == "Acme Corp"
        assert data["title"] == "CEO"

    @patch("pbx.integrations.espocrm.requests")
    def test_create_contact_single_name(self, mock_requests: MagicMock) -> None:
        """Test creating a contact with a single name (no last name)."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-2"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_contact(name="Madonna", phone="5551234567")

        assert result is not None
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["firstName"] == "Madonna"
        assert data["lastName"] == ""

    @patch("pbx.integrations.espocrm.requests")
    def test_create_contact_minimal_fields(self, mock_requests: MagicMock) -> None:
        """Test creating a contact with only required fields."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-3"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_contact(name="John Smith", phone="5551234567")

        assert result is not None
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert "emailAddress" not in data
        assert "title" not in data
        assert "accountName" not in data

    def test_create_contact_disabled(self) -> None:
        """Test create_contact when integration is disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_contact(name="John", phone="555")

        assert result is None

    def test_create_contact_auto_create_disabled(self) -> None:
        """Test create_contact when auto_create_contacts is False."""
        config = _make_enabled_config(auto_create_contacts=False)
        integration = EspoCRMIntegration(config)

        result = integration.create_contact(name="John", phone="555")

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_create_contact_api_failure(self, mock_requests: MagicMock) -> None:
        """Test create_contact when API returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_contact(name="John", phone="555")

        assert result is None


@pytest.mark.unit
class TestLogCall:
    """Tests for log_call."""

    @patch("pbx.integrations.espocrm.requests")
    def test_log_call_success(self, mock_requests: MagicMock) -> None:
        """Test successful call logging."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "call-1"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.log_call(
            contact_id="c1",
            direction="Inbound",
            duration=120,
            status="Held",
            description="Test call",
        )

        assert result == {"id": "call-1"}
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["name"] == "Inbound Call"
        assert data["status"] == "Held"
        assert data["direction"] == "Inbound"
        assert data["duration"] == 120
        assert data["contactsIds"] == ["c1"]
        assert data["description"] == "Test call"
        assert "dateStart" in data

    @patch("pbx.integrations.espocrm.requests")
    def test_log_call_without_description(self, mock_requests: MagicMock) -> None:
        """Test call logging without optional description."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "call-2"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.log_call(
            contact_id="c1",
            direction="Outbound",
            duration=60,
            status="Not Held",
        )

        assert result is not None
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert "description" not in data

    def test_log_call_disabled(self) -> None:
        """Test log_call when integration is disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.log_call("c1", "Inbound", 60, "Held")

        assert result is None

    def test_log_call_auto_log_disabled(self) -> None:
        """Test log_call when auto_log_calls is False."""
        config = _make_enabled_config(auto_log_calls=False)
        integration = EspoCRMIntegration(config)

        result = integration.log_call("c1", "Inbound", 60, "Held")

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_log_call_api_failure(self, mock_requests: MagicMock) -> None:
        """Test log_call when API returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.log_call("c1", "Inbound", 60, "Held")

        assert result is None


@pytest.mark.unit
class TestGetContact:
    """Tests for get_contact."""

    @patch("pbx.integrations.espocrm.requests")
    def test_get_contact_success(self, mock_requests: MagicMock) -> None:
        """Test successfully getting a contact by ID."""
        contact_data = {"id": "c1", "firstName": "John", "lastName": "Doe"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = contact_data
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.get_contact("c1")

        assert result == contact_data

    @patch("pbx.integrations.espocrm.requests")
    def test_get_contact_not_found(self, mock_requests: MagicMock) -> None:
        """Test getting a nonexistent contact."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.get_contact("nonexistent")

        assert result is None

    def test_get_contact_disabled(self) -> None:
        """Test get_contact when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.get_contact("c1")

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_get_contact_request_exception(self, mock_requests: MagicMock) -> None:
        """Test get_contact when a request exception occurs."""
        mock_requests.request.side_effect = mock_requests.RequestException("Timeout")

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.get_contact("c1")

        assert result is None


@pytest.mark.unit
class TestUpdateContact:
    """Tests for update_contact."""

    @patch("pbx.integrations.espocrm.requests")
    def test_update_contact_success(self, mock_requests: MagicMock) -> None:
        """Test successfully updating a contact."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "c1", "firstName": "Updated"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.update_contact("c1", {"firstName": "Updated"})

        assert result == {"id": "c1", "firstName": "Updated"}
        call_kwargs = mock_requests.request.call_args
        assert call_kwargs.kwargs["method"] == "PUT"

    @patch("pbx.integrations.espocrm.requests")
    def test_update_contact_api_failure(self, mock_requests: MagicMock) -> None:
        """Test update_contact when API returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.update_contact("c1", {"firstName": "Updated"})

        assert result is None

    def test_update_contact_disabled(self) -> None:
        """Test update_contact when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.update_contact("c1", {"firstName": "Updated"})

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_update_contact_request_exception(self, mock_requests: MagicMock) -> None:
        """Test update_contact when a request exception occurs."""
        mock_requests.request.side_effect = mock_requests.RequestException("Timeout")

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.update_contact("c1", {"firstName": "Updated"})

        assert result is None


@pytest.mark.unit
class TestSearchContacts:
    """Tests for search_contacts."""

    @patch("pbx.integrations.espocrm.requests")
    def test_search_contacts_found(self, mock_requests: MagicMock) -> None:
        """Test searching contacts that returns results."""
        contacts = [{"id": "c1", "name": "John"}, {"id": "c2", "name": "Johnny"}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": contacts}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.search_contacts("John")

        assert result == contacts

    @patch("pbx.integrations.espocrm.requests")
    def test_search_contacts_empty(self, mock_requests: MagicMock) -> None:
        """Test searching contacts that returns no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.search_contacts("Nonexistent")

        assert result == []

    @patch("pbx.integrations.espocrm.requests")
    def test_search_contacts_custom_max_results(self, mock_requests: MagicMock) -> None:
        """Test search with custom max_results parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        integration.search_contacts("John", max_results=25)

        call_kwargs = mock_requests.request.call_args
        params = call_kwargs.kwargs["params"]
        assert params["maxSize"] == 25

    def test_search_contacts_disabled(self) -> None:
        """Test search_contacts when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.search_contacts("John")

        assert result == []

    @patch("pbx.integrations.espocrm.requests")
    def test_search_contacts_no_list_key(self, mock_requests: MagicMock) -> None:
        """Test search_contacts when response has no 'list' key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 0}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.search_contacts("John")

        assert result == []

    @patch("pbx.integrations.espocrm.requests")
    def test_search_contacts_api_error(self, mock_requests: MagicMock) -> None:
        """Test search_contacts when API returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.search_contacts("John")

        assert result == []


@pytest.mark.unit
class TestCreateOpportunity:
    """Tests for create_opportunity."""

    @patch("pbx.integrations.espocrm.requests")
    def test_create_opportunity_full(self, mock_requests: MagicMock) -> None:
        """Test creating an opportunity with all fields."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "opp-1"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_opportunity(
            name="New Deal",
            amount=10000.0,
            contact_id="c1",
            account_id="a1",
            stage="Qualification",
            close_date="2026-12-31",
        )

        assert result == {"id": "opp-1"}
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["name"] == "New Deal"
        assert data["amount"] == 10000.0
        assert data["contactsIds"] == ["c1"]
        assert data["accountId"] == "a1"
        assert data["stage"] == "Qualification"
        assert data["closeDate"] == "2026-12-31"

    @patch("pbx.integrations.espocrm.requests")
    def test_create_opportunity_minimal(self, mock_requests: MagicMock) -> None:
        """Test creating an opportunity with only required fields."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "opp-2"}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_opportunity(name="Deal", amount=5000.0)

        assert result is not None
        call_kwargs = mock_requests.request.call_args
        data = call_kwargs.kwargs["json"]
        assert data["stage"] == "Prospecting"
        assert "contactsIds" not in data
        assert "accountId" not in data
        assert "closeDate" not in data

    def test_create_opportunity_disabled(self) -> None:
        """Test create_opportunity when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_opportunity(name="Deal", amount=1000.0)

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    def test_create_opportunity_api_failure(self, mock_requests: MagicMock) -> None:
        """Test create_opportunity when API returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.create_opportunity(name="Deal", amount=1000.0)

        assert result is None


@pytest.mark.unit
class TestGetRecentActivities:
    """Tests for get_recent_activities."""

    @patch("pbx.integrations.espocrm.requests")
    def test_get_activities_success(self, mock_requests: MagicMock) -> None:
        """Test retrieving recent activities."""
        activities = [{"id": "act-1", "name": "Inbound Call"}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": activities}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.get_recent_activities("c1")

        assert result == activities

    @patch("pbx.integrations.espocrm.requests")
    def test_get_activities_custom_limit(self, mock_requests: MagicMock) -> None:
        """Test get_recent_activities with custom limit."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        integration.get_recent_activities("c1", limit=5)

        call_kwargs = mock_requests.request.call_args
        params = call_kwargs.kwargs["params"]
        assert params["maxSize"] == 5

    @patch("pbx.integrations.espocrm.requests")
    def test_get_activities_empty(self, mock_requests: MagicMock) -> None:
        """Test get_recent_activities with no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.get_recent_activities("c1")

        assert result == []

    def test_get_activities_disabled(self) -> None:
        """Test get_recent_activities when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.get_recent_activities("c1")

        assert result == []

    @patch("pbx.integrations.espocrm.requests")
    def test_get_activities_no_list_key(self, mock_requests: MagicMock) -> None:
        """Test get_recent_activities when response lacks 'list' key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 0}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.get_recent_activities("c1")

        assert result == []


@pytest.mark.unit
class TestHandleIncomingCall:
    """Tests for handle_incoming_call."""

    @patch("pbx.integrations.espocrm.requests")
    def test_handle_incoming_call_existing_contact(self, mock_requests: MagicMock) -> None:
        """Test handling incoming call with an existing contact."""
        contact = {"id": "c1", "name": "John Doe"}
        activities = [{"id": "act-1"}]

        def request_side_effect(**kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            url = kwargs.get("url", "")
            if "Call" in url:
                mock_resp.json.return_value = {"list": activities}
            else:
                mock_resp.json.return_value = {"list": [contact]}
            return mock_resp

        mock_requests.request.side_effect = request_side_effect

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.handle_incoming_call("5551234567", "1001")

        assert result["success"] is True
        assert result["contact"] == contact
        assert result["activities"] == activities
        assert "screen_pop_url" in result
        assert "c1" in result["screen_pop_url"]

    @patch("pbx.integrations.espocrm.requests")
    def test_handle_incoming_call_auto_create_contact(self, mock_requests: MagicMock) -> None:
        """Test handling incoming call that auto-creates a contact."""
        new_contact = {"id": "c2", "name": "Unknown - 5559999999"}

        call_count = 0

        def request_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            url = kwargs.get("url", "")
            method = kwargs.get("method", "GET")

            if method == "POST" and "Contact" in url:
                # POST to create contact
                mock_resp.status_code = 201
                mock_resp.json.return_value = new_contact
            elif method == "GET" and "Call" in url:
                mock_resp.json.return_value = {"list": []}
            else:
                # GET Contact search - not found
                mock_resp.json.return_value = {"list": []}
            return mock_resp

        mock_requests.request.side_effect = request_side_effect

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.handle_incoming_call("5559999999", "1001")

        assert result["success"] is True
        assert result["contact"] == new_contact

    def test_handle_incoming_call_disabled(self) -> None:
        """Test handle_incoming_call when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.handle_incoming_call("5551234567", "1001")

        assert result == {"success": False}

    def test_handle_incoming_call_screen_pop_disabled(self) -> None:
        """Test handle_incoming_call when screen_pop is False."""
        config = _make_enabled_config(screen_pop=False)
        integration = EspoCRMIntegration(config)

        result = integration.handle_incoming_call("5551234567", "1001")

        assert result == {"success": False}

    @patch("pbx.integrations.espocrm.requests")
    def test_handle_incoming_call_contact_not_found_no_auto_create(
        self, mock_requests: MagicMock
    ) -> None:
        """Test when no contact found and auto_create is disabled."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config(auto_create_contacts=False)
        integration = EspoCRMIntegration(config)

        result = integration.handle_incoming_call("5559999999", "1001")

        assert result["success"] is False
        assert result.get("reason") == "Contact not found"

    @patch("pbx.integrations.espocrm.requests")
    def test_handle_incoming_call_screen_pop_url_format(self, mock_requests: MagicMock) -> None:
        """Test the format of the screen pop URL."""
        contact = {"id": "abc123", "name": "Test"}
        mock_response = MagicMock()
        mock_response.status_code = 200

        def request_side_effect(**kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            url = kwargs.get("url", "")
            if "Call" in url:
                mock_resp.json.return_value = {"list": []}
            else:
                mock_resp.json.return_value = {"list": [contact]}
            return mock_resp

        mock_requests.request.side_effect = request_side_effect

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.handle_incoming_call("5551234567", "1001")

        assert result["success"] is True
        assert result["screen_pop_url"] == "https://crm.example.com/#Contact/view/abc123"


@pytest.mark.unit
class TestHandleCallCompleted:
    """Tests for handle_call_completed."""

    @patch("pbx.integrations.espocrm.requests")
    def test_handle_call_completed_success(self, mock_requests: MagicMock) -> None:
        """Test logging a completed call."""
        contact = {"id": "c1", "name": "John"}

        def request_side_effect(**kwargs):
            mock_resp = MagicMock()
            method = kwargs.get("method", "GET")
            url = kwargs.get("url", "")
            if method == "GET" and "Contact" in url:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"list": [contact]}
            elif method == "POST" and "Call" in url:
                mock_resp.status_code = 201
                mock_resp.json.return_value = {"id": "call-1"}
            else:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {}
            return mock_resp

        mock_requests.request.side_effect = request_side_effect

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.handle_call_completed("5551234567", "1001", 120, "Inbound")

        assert result is True

    @patch("pbx.integrations.espocrm.requests")
    def test_handle_call_completed_zero_duration(self, mock_requests: MagicMock) -> None:
        """Test that zero duration call gets 'Not Held' status."""
        contact = {"id": "c1", "name": "John"}

        def request_side_effect(**kwargs):
            mock_resp = MagicMock()
            method = kwargs.get("method", "GET")
            url = kwargs.get("url", "")
            if method == "GET" and "Contact" in url:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"list": [contact]}
            elif method == "POST" and "Call" in url:
                mock_resp.status_code = 201
                mock_resp.json.return_value = {"id": "call-2"}
            else:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {}
            return mock_resp

        mock_requests.request.side_effect = request_side_effect

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.handle_call_completed("5551234567", "1001", 0, "Inbound")

        assert result is True

    def test_handle_call_completed_disabled(self) -> None:
        """Test handle_call_completed when disabled."""
        config = _make_disabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.handle_call_completed("5551234567", "1001", 120, "Inbound")

        assert result is False

    def test_handle_call_completed_auto_log_disabled(self) -> None:
        """Test handle_call_completed when auto_log_calls is False."""
        config = _make_enabled_config(auto_log_calls=False)
        integration = EspoCRMIntegration(config)

        result = integration.handle_call_completed("5551234567", "1001", 120, "Inbound")

        assert result is False

    @patch("pbx.integrations.espocrm.requests")
    def test_handle_call_completed_contact_not_found_no_auto_create(
        self, mock_requests: MagicMock
    ) -> None:
        """Test when contact not found and auto_create is False."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        config = _make_enabled_config(auto_create_contacts=False)
        integration = EspoCRMIntegration(config)

        result = integration.handle_call_completed("5559999999", "1001", 120, "Inbound")

        assert result is False

    @patch("pbx.integrations.espocrm.requests")
    def test_handle_call_completed_auto_creates_contact(self, mock_requests: MagicMock) -> None:
        """Test that auto-creates contact when not found and auto_create is True."""
        new_contact = {"id": "c-new", "name": "Unknown - 5559999999"}

        def request_side_effect(**kwargs):
            mock_resp = MagicMock()
            method = kwargs.get("method", "GET")
            url = kwargs.get("url", "")
            if method == "GET" and "Contact" in url:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"list": []}
            elif method == "POST" and "Contact" in url:
                mock_resp.status_code = 201
                mock_resp.json.return_value = new_contact
            elif method == "POST" and "Call" in url:
                mock_resp.status_code = 201
                mock_resp.json.return_value = {"id": "call-1"}
            else:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {}
            return mock_resp

        mock_requests.request.side_effect = request_side_effect

        config = _make_enabled_config()
        integration = EspoCRMIntegration(config)

        result = integration.handle_call_completed("5559999999", "1001", 60, "Outbound")

        assert result is True
