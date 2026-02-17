"""Comprehensive tests for EspoCRM integration (CRM, replaces Salesforce)."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestEspoCRMInit:
    """Tests for EspoCRMIntegration initialization."""

    @patch("pbx.integrations.espocrm.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)

        assert integration.enabled is None

    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_init_enabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when enabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "integrations.espocrm.enabled": True,
                "integrations.espocrm.api_url": "https://crm.example.com/api/v1",
                "integrations.espocrm.api_key": "test-api-key",
                "integrations.espocrm.api_secret": "test-secret",
                "integrations.espocrm.auto_create_contacts": True,
                "integrations.espocrm.auto_log_calls": True,
                "integrations.espocrm.screen_pop": True,
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = EspoCRMIntegration(config)

        assert integration.enabled is True
        assert integration.api_key == "test-api-key"

    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_init_api_url_without_api_suffix(self, mock_get_logger: MagicMock) -> None:
        """Test URL normalization when api/v1 is not in URL."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "integrations.espocrm.enabled": True,
                "integrations.espocrm.api_url": "https://crm.example.com",
                "integrations.espocrm.api_key": "test-api-key",
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = EspoCRMIntegration(config)

        assert integration.api_url == "https://crm.example.com/api/v1"

    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_init_api_url_with_trailing_slash(self, mock_get_logger: MagicMock) -> None:
        """Test URL normalization with trailing slash."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "integrations.espocrm.enabled": True,
                "integrations.espocrm.api_url": "https://crm.example.com/",
                "integrations.espocrm.api_key": "test-api-key",
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = EspoCRMIntegration(config)

        assert integration.api_url == "https://crm.example.com/api/v1"

    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", False)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_init_no_requests(self, mock_get_logger: MagicMock) -> None:
        """Test initialization when requests is not available."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {"integrations.espocrm.enabled": True}
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = EspoCRMIntegration(config)

        assert integration.enabled is False

    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_init_missing_credentials(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with missing credentials."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()

        def config_get(key: str, default=None):
            mapping = {
                "integrations.espocrm.enabled": True,
                "integrations.espocrm.api_url": None,
                "integrations.espocrm.api_key": None,
            }
            return mapping.get(key, default)

        config.get.side_effect = config_get
        integration = EspoCRMIntegration(config)

        assert integration.enabled is False


@pytest.mark.unit
class TestEspoCRMMakeRequest:
    """Tests for EspoCRMIntegration._make_request."""

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_make_request_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful API request."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "name": "Test"}
        mock_requests.request.return_value = mock_response

        result = integration._make_request("GET", "Contact/123")

        assert result is not None
        assert result["id"] == "123"

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_make_request_api_error(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test API request with error response."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_requests.request.return_value = mock_response

        result = integration._make_request("GET", "Contact/nonexistent")

        assert result is None

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_make_request_exception(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test API request with exception."""
        import requests as real_requests

        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_requests.request.side_effect = real_requests.RequestException("error")
        mock_requests.RequestException = real_requests.RequestException

        result = integration._make_request("GET", "Contact/123")

        assert result is None

    @patch("pbx.integrations.espocrm.get_logger")
    def test_make_request_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test API request when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        result = integration._make_request("GET", "Contact/123")

        assert result is None


@pytest.mark.unit
class TestEspoCRMFindContact:
    """Tests for EspoCRMIntegration.find_contact_by_phone."""

    @patch("pbx.integrations.espocrm.get_logger")
    def test_find_contact_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test find contact when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.find_contact_by_phone("+15551234567") is None

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_find_contact_found(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test find contact success."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": [{"id": "contact-1", "name": "John Doe"}]}
        mock_requests.request.return_value = mock_response

        result = integration.find_contact_by_phone("+1 (555) 123-4567")

        assert result is not None
        assert result["name"] == "John Doe"

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_find_contact_not_found(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test find contact when not found."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": []}
        mock_requests.request.return_value = mock_response

        result = integration.find_contact_by_phone("+15559999999")

        assert result is None


@pytest.mark.unit
class TestEspoCRMCreateContact:
    """Tests for EspoCRMIntegration.create_contact."""

    @patch("pbx.integrations.espocrm.get_logger")
    def test_create_contact_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test create contact when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.create_contact("John Doe", "5551234567") is None

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_create_contact_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful contact creation."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.auto_create_contacts = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-contact", "name": "John Doe"}
        mock_requests.request.return_value = mock_response

        result = integration.create_contact(
            "John Doe", "5551234567", email="john@example.com", company="Acme", title="Manager"
        )

        assert result is not None
        assert result["id"] == "new-contact"

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_create_contact_single_name(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test contact creation with single name."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.auto_create_contacts = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-contact"}
        mock_requests.request.return_value = mock_response

        result = integration.create_contact("Madonna", "5551234567")

        assert result is not None

    @patch("pbx.integrations.espocrm.get_logger")
    def test_create_contact_auto_create_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test create contact when auto_create is disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.auto_create_contacts = False

        assert integration.create_contact("John", "555") is None


@pytest.mark.unit
class TestEspoCRMLogCall:
    """Tests for EspoCRMIntegration.log_call."""

    @patch("pbx.integrations.espocrm.get_logger")
    def test_log_call_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test log call when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.log_call("c1", "Inbound", 120, "Held") is None

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_log_call_success(self, mock_get_logger: MagicMock, mock_requests: MagicMock) -> None:
        """Test successful call logging."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.auto_log_calls = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "call-record-1"}
        mock_requests.request.return_value = mock_response

        result = integration.log_call("contact-1", "Inbound", 120, "Held", description="Test call")

        assert result is not None


@pytest.mark.unit
class TestEspoCRMContactOperations:
    """Tests for get_contact, update_contact, search_contacts."""

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_get_contact_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test get contact by ID."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "c1", "name": "John"}
        mock_requests.request.return_value = mock_response

        result = integration.get_contact("c1")

        assert result is not None
        assert result["id"] == "c1"

    @patch("pbx.integrations.espocrm.get_logger")
    def test_get_contact_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test get contact when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.get_contact("c1") is None

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_update_contact_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test update contact."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "c1", "title": "Director"}
        mock_requests.request.return_value = mock_response

        result = integration.update_contact("c1", {"title": "Director"})

        assert result is not None

    @patch("pbx.integrations.espocrm.get_logger")
    def test_update_contact_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test update contact when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.update_contact("c1", {}) is None

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_search_contacts_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test search contacts."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": [{"id": "c1", "name": "John Doe"}]}
        mock_requests.request.return_value = mock_response

        result = integration.search_contacts("John")

        assert len(result) == 1
        assert result[0]["name"] == "John Doe"

    @patch("pbx.integrations.espocrm.get_logger")
    def test_search_contacts_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test search contacts when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.search_contacts("John") == []


@pytest.mark.unit
class TestEspoCRMOpportunity:
    """Tests for EspoCRMIntegration.create_opportunity."""

    @patch("pbx.integrations.espocrm.get_logger")
    def test_create_opportunity_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test create opportunity when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.create_opportunity("Deal", 1000.0) is None

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_create_opportunity_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful opportunity creation."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "opp-1", "name": "Big Deal"}
        mock_requests.request.return_value = mock_response

        result = integration.create_opportunity(
            "Big Deal",
            50000.0,
            contact_id="c1",
            account_id="a1",
            stage="Qualification",
            close_date="2026-06-30",
        )

        assert result is not None
        assert result["id"] == "opp-1"


@pytest.mark.unit
class TestEspoCRMActivities:
    """Tests for EspoCRMIntegration.get_recent_activities."""

    @patch("pbx.integrations.espocrm.get_logger")
    def test_get_activities_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test get activities when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.get_recent_activities("c1") == []

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_get_activities_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test successful activities retrieval."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"list": [{"id": "activity-1", "name": "Inbound Call"}]}
        mock_requests.request.return_value = mock_response

        result = integration.get_recent_activities("c1", limit=5)

        assert len(result) == 1


@pytest.mark.unit
class TestEspoCRMCallHandling:
    """Tests for EspoCRMIntegration.handle_incoming_call and handle_call_completed."""

    @patch("pbx.integrations.espocrm.get_logger")
    def test_handle_incoming_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test handle incoming call when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        result = integration.handle_incoming_call("5551234567", "1001")

        assert result["success"] is False

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_handle_incoming_existing_contact(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test handle incoming call with existing contact."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.screen_pop = True
        integration.auto_create_contacts = False
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        # find_contact_by_phone returns contact
        find_response = MagicMock()
        find_response.status_code = 200
        find_response.json.return_value = {"list": [{"id": "c1", "name": "John Doe"}]}

        # get_recent_activities returns activities
        activities_response = MagicMock()
        activities_response.status_code = 200
        activities_response.json.return_value = {"list": [{"id": "a1", "name": "Previous Call"}]}

        mock_requests.request.side_effect = [find_response, activities_response]

        result = integration.handle_incoming_call("5551234567", "1001")

        assert result["success"] is True
        assert result["contact"]["name"] == "John Doe"
        assert "screen_pop_url" in result

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_handle_incoming_auto_create_contact(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test handle incoming call auto-creates contact."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.screen_pop = True
        integration.auto_create_contacts = True
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        # find_contact_by_phone returns nothing
        find_response = MagicMock()
        find_response.status_code = 200
        find_response.json.return_value = {"list": []}

        # create_contact succeeds
        create_response = MagicMock()
        create_response.status_code = 201
        create_response.json.return_value = {"id": "new-c", "name": "Unknown - 5551234567"}

        # get_recent_activities
        activities_response = MagicMock()
        activities_response.status_code = 200
        activities_response.json.return_value = {"list": []}

        mock_requests.request.side_effect = [find_response, create_response, activities_response]

        result = integration.handle_incoming_call("5551234567", "1001")

        assert result["success"] is True

    @patch("pbx.integrations.espocrm.get_logger")
    def test_handle_call_completed_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test handle call completed when disabled."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = False

        assert integration.handle_call_completed("555", "1001", 120, "Inbound") is False

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_handle_call_completed_success(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test handle call completed with existing contact."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.auto_log_calls = True
        integration.auto_create_contacts = False
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        # find_contact_by_phone
        find_response = MagicMock()
        find_response.status_code = 200
        find_response.json.return_value = {"list": [{"id": "c1", "name": "John"}]}

        # log_call
        log_response = MagicMock()
        log_response.status_code = 201
        log_response.json.return_value = {"id": "call-1"}

        mock_requests.request.side_effect = [find_response, log_response]

        result = integration.handle_call_completed("5551234567", "1001", 120, "Inbound")

        assert result is True

    @patch("pbx.integrations.espocrm.requests")
    @patch("pbx.integrations.espocrm.REQUESTS_AVAILABLE", True)
    @patch("pbx.integrations.espocrm.get_logger")
    def test_handle_call_completed_no_contact(
        self, mock_get_logger: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test handle call completed when no contact is found and no auto-create."""
        from pbx.integrations.espocrm import EspoCRMIntegration

        config = MagicMock()
        config.get.return_value = None
        integration = EspoCRMIntegration(config)
        integration.enabled = True
        integration.auto_log_calls = True
        integration.auto_create_contacts = False
        integration.api_url = "https://crm.example.com/api/v1"
        integration.api_key = "test-key"

        find_response = MagicMock()
        find_response.status_code = 200
        find_response.json.return_value = {"list": []}
        mock_requests.request.return_value = find_response

        result = integration.handle_call_completed("5559999999", "1001", 0, "Inbound")

        assert result is False
