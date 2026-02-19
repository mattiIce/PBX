"""Comprehensive tests for pbx/features/crm_integrations.py module."""

from unittest.mock import MagicMock, patch

import pytest

from pbx.features.crm_integrations import HubSpotIntegration, ZendeskIntegration

# ---------------------------------------------------------------------------
# Helper to build a mock db_backend
# ---------------------------------------------------------------------------


def _make_db(db_type: str = "sqlite") -> MagicMock:
    """Create a mock database backend."""
    db = MagicMock()
    db.db_type = db_type
    db.execute.return_value = None
    return db


# ---------------------------------------------------------------------------
# HubSpotIntegration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHubSpotIntegrationInit:
    """Tests for HubSpotIntegration initialization."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_init(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        config = {"api_key": "test"}
        integration = HubSpotIntegration(db, config)
        assert integration.db is db
        assert integration.config is config
        assert integration.enabled is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_init_none_db(self, mock_logger: MagicMock) -> None:
        integration = HubSpotIntegration(None, {})
        assert integration.db is None


@pytest.mark.unit
class TestHubSpotGetConfig:
    """Tests for HubSpotIntegration.get_config."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_returns_dict(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        # Simulate a row: id=1, enabled=1, api_key_encrypted=xxx, portal_id=123,
        # sync_contacts=1, sync_deals=1, auto_create_contacts=0, last_sync=None
        db.execute.return_value = [(1, 1, "encrypted_key", "12345", 1, 1, 0, None)]
        integration = HubSpotIntegration(db, {})
        config = integration.get_config()
        assert config is not None
        assert config["enabled"] is True
        assert config["portal_id"] == "12345"
        assert config["sync_contacts"] is True
        assert config["sync_deals"] is True
        assert config["auto_create_contacts"] is False
        assert config["last_sync"] is None
        assert integration.enabled is True

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_empty_result(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = []
        integration = HubSpotIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_none_result(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = None
        integration = HubSpotIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_with_empty_first_row(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = [()]
        integration = HubSpotIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_sqlite_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = Exception("db error")
        integration = HubSpotIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_type_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = TypeError("type error")
        integration = HubSpotIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_key_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = KeyError("key error")
        integration = HubSpotIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_value_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = ValueError("value error")
        integration = HubSpotIntegration(db, {})
        config = integration.get_config()
        assert config is None


@pytest.mark.unit
class TestHubSpotUpdateConfig:
    """Tests for HubSpotIntegration.update_config."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_insert_new_sqlite(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        db.execute.return_value = []  # No existing config
        integration = HubSpotIntegration(db, {})
        result = integration.update_config(
            {
                "enabled": True,
                "api_key_encrypted": "enc_key",
                "portal_id": "12345",
                "sync_contacts": True,
                "sync_deals": False,
                "auto_create_contacts": True,
            }
        )
        assert result is True
        assert integration.enabled is True
        # Second call is the INSERT
        assert db.execute.call_count == 2

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_update_existing_sqlite(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        # First call from get_config returns a row
        db.execute.return_value = [(1, 1, "key", "12345", 1, 1, 0, None)]
        integration = HubSpotIntegration(db, {})
        result = integration.update_config({"enabled": False})
        assert result is True
        assert integration.enabled is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_insert_new_postgres(self, mock_logger: MagicMock) -> None:
        db = _make_db("postgresql")
        db.execute.return_value = []  # No existing config
        integration = HubSpotIntegration(db, {})
        result = integration.update_config({"enabled": True, "portal_id": "999"})
        assert result is True

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_update_existing_postgres(self, mock_logger: MagicMock) -> None:
        db = _make_db("postgresql")
        db.execute.return_value = [(1, 1, "key", "12345", 1, 1, 0, None)]
        integration = HubSpotIntegration(db, {})
        result = integration.update_config({"enabled": True})
        assert result is True

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = Exception("db error")
        integration = HubSpotIntegration(db, {})
        result = integration.update_config({"enabled": True})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_defaults(self, mock_logger: MagicMock) -> None:
        """Test that defaults are used when config keys are missing."""
        db = _make_db("sqlite")
        db.execute.return_value = []  # no existing config
        integration = HubSpotIntegration(db, {})
        result = integration.update_config({})
        assert result is True
        assert integration.enabled is False


@pytest.mark.unit
class TestHubSpotSyncContact:
    """Tests for HubSpotIntegration.sync_contact."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_disabled(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = False
        result = integration.sync_contact({"email": "test@example.com"})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_no_config(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = []
        integration = HubSpotIntegration(db, {})
        integration.enabled = True
        result = integration.sync_contact({"email": "test@example.com"})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_no_api_key(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = [(1, 1, "key", "12345", 1, 1, 0, None)]
        integration = HubSpotIntegration(db, {})
        integration.enabled = True
        # get_config returns dict without api_key
        result = integration.sync_contact({"email": "test@example.com"})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_direct_api_success(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "api_key": "test_key",
            "portal_id": "12345",
        }

        mock_response = MagicMock()
        mock_response.status_code = 201

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity") as mock_log,
        ):
            result = integration.sync_contact(
                {
                    "email": "user@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone": "5551234",
                    "company": "ACME",
                }
            )

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "hubapi.com" in call_args[0][0]
        mock_log.assert_called_once()

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_webhook_success(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "api_key": "test_key",
            "webhook_url": "https://hooks.example.com/hubspot",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.sync_contact({"email": "user@example.com"})

        assert result is True
        call_url = mock_post.call_args[0][0]
        assert call_url == "https://hooks.example.com/hubspot"

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_api_error_status(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.sync_contact({"email": "user@example.com"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_request_exception(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}

        import requests as requests_lib

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch(
                "requests.post",
                side_effect=requests_lib.exceptions.ConnectionError("timeout"),
            ),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.sync_contact({"email": "user@example.com"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_key_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        # get_config returns a config that will cause a KeyError downstream
        mock_config = {"api_key": "test_key", "portal_id": "12345"}

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch(
                "requests.post",
                side_effect=KeyError("missing key"),
            ),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.sync_contact({"email": "user@example.com"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_sync_contact_empty_contact_data(self, mock_logger: MagicMock) -> None:
        """Sync with empty contact data -- should still try API call."""
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}
        mock_response = MagicMock()
        mock_response.status_code = 201

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.sync_contact({})

        assert result is True


@pytest.mark.unit
class TestHubSpotCreateDeal:
    """Tests for HubSpotIntegration.create_deal."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_disabled(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = False
        result = integration.create_deal({"dealname": "Test Deal"})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_no_config(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = []
        integration = HubSpotIntegration(db, {})
        integration.enabled = True
        result = integration.create_deal({"dealname": "Test Deal"})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_no_api_key(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = [(1, 1, "key", "12345", 1, 1, 0, None)]
        integration = HubSpotIntegration(db, {})
        integration.enabled = True
        result = integration.create_deal({"dealname": "Test Deal"})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_direct_api_success(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}
        mock_response = MagicMock()
        mock_response.status_code = 201

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_deal(
                {
                    "dealname": "Big Deal",
                    "amount": 10000,
                    "dealstage": "closedwon",
                    "pipeline": "default",
                    "closedate": "2026-01-01",
                }
            )

        assert result is True
        call_url = mock_post.call_args[0][0]
        assert "hubapi.com" in call_url
        assert "deals" in call_url

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_with_contact_association(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}
        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_deal(
                {
                    "dealname": "Deal with Contact",
                    "contact_id": "456",
                }
            )

        assert result is True
        payload = mock_post.call_args[1]["json"]
        assert "associations" in payload
        assert payload["associations"][0]["to"]["id"] == "456"

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_webhook_success(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "api_key": "test_key",
            "webhook_url": "https://hooks.example.com/deals",
        }
        mock_response = MagicMock()
        mock_response.status_code = 201

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_deal({"dealname": "Webhook Deal"})

        assert result is True
        call_url = mock_post.call_args[0][0]
        assert call_url == "https://hooks.example.com/deals"

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_api_error_status(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_deal({"dealname": "Fail Deal"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_request_exception(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}

        import requests as requests_lib

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch(
                "requests.post",
                side_effect=requests_lib.exceptions.Timeout("timeout"),
            ),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_deal({"dealname": "Timeout Deal"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_type_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch(
                "requests.post",
                side_effect=TypeError("type error"),
            ),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_deal({"dealname": "Error Deal"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_deal_empty_deal_data(self, mock_logger: MagicMock) -> None:
        """No properties set -- should still attempt API call."""
        db = _make_db()
        integration = HubSpotIntegration(db, {})
        integration.enabled = True

        mock_config = {"api_key": "test_key", "portal_id": "12345"}
        mock_response = MagicMock()
        mock_response.status_code = 201

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_deal({})

        assert result is True


@pytest.mark.unit
class TestHubSpotLogActivity:
    """Tests for HubSpotIntegration._log_activity."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_log_activity_sqlite(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        integration = HubSpotIntegration(db, {})
        integration._log_activity("hubspot", "sync_contact", "success", "details")
        db.execute.assert_called_once()
        call_args = db.execute.call_args
        assert "?" in call_args[0][0]

    @patch("pbx.features.crm_integrations.get_logger")
    def test_log_activity_postgres(self, mock_logger: MagicMock) -> None:
        db = _make_db("postgresql")
        integration = HubSpotIntegration(db, {})
        integration._log_activity("hubspot", "sync_contact", "success", "details")
        db.execute.assert_called_once()
        call_args = db.execute.call_args
        assert "%s" in call_args[0][0]

    @patch("pbx.features.crm_integrations.get_logger")
    def test_log_activity_db_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = Exception("log error")
        integration = HubSpotIntegration(db, {})
        # Should not raise
        integration._log_activity("hubspot", "action", "error", "details")


# ---------------------------------------------------------------------------
# ZendeskIntegration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestZendeskIntegrationInit:
    """Tests for ZendeskIntegration initialization."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_init(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        config = {"subdomain": "test"}
        integration = ZendeskIntegration(db, config)
        assert integration.db is db
        assert integration.config is config
        assert integration.enabled is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_init_none_db(self, mock_logger: MagicMock) -> None:
        integration = ZendeskIntegration(None, {})
        assert integration.db is None


@pytest.mark.unit
class TestZendeskGetConfig:
    """Tests for ZendeskIntegration.get_config."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_returns_dict(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        # Row: id=1, enabled=1, subdomain=test, api_token_encrypted=x, email=a@b.com,
        # auto_create_tickets=1, default_priority=high
        db.execute.return_value = [
            (1, 1, "testco", "encrypted_token", "admin@testco.com", 1, "high")
        ]
        integration = ZendeskIntegration(db, {})
        config = integration.get_config()
        assert config is not None
        assert config["enabled"] is True
        assert config["subdomain"] == "testco"
        assert config["email"] == "admin@testco.com"
        assert config["auto_create_tickets"] is True
        assert config["default_priority"] == "high"
        assert integration.enabled is True

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_empty_result(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = []
        integration = ZendeskIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_none_result(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = None
        integration = ZendeskIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_empty_first_row(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = [()]
        integration = ZendeskIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_sqlite_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = Exception("db error")
        integration = ZendeskIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_type_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = TypeError("type error")
        integration = ZendeskIntegration(db, {})
        config = integration.get_config()
        assert config is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_config_key_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = KeyError("key error")
        integration = ZendeskIntegration(db, {})
        config = integration.get_config()
        assert config is None


@pytest.mark.unit
class TestZendeskUpdateConfig:
    """Tests for ZendeskIntegration.update_config."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_insert_new_sqlite(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        db.execute.return_value = []  # No existing config
        integration = ZendeskIntegration(db, {})
        result = integration.update_config(
            {
                "enabled": True,
                "subdomain": "testco",
                "api_token_encrypted": "enc_token",
                "email": "admin@testco.com",
                "auto_create_tickets": True,
                "default_priority": "high",
            }
        )
        assert result is True
        assert integration.enabled is True
        assert db.execute.call_count == 2

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_update_existing_sqlite(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        db.execute.return_value = [(1, 1, "testco", "tok", "a@b.com", 1, "high")]
        integration = ZendeskIntegration(db, {})
        result = integration.update_config({"enabled": False})
        assert result is True
        assert integration.enabled is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_insert_new_postgres(self, mock_logger: MagicMock) -> None:
        db = _make_db("postgresql")
        db.execute.return_value = []  # No existing config
        integration = ZendeskIntegration(db, {})
        result = integration.update_config({"enabled": True, "subdomain": "testco"})
        assert result is True

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_update_existing_postgres(self, mock_logger: MagicMock) -> None:
        db = _make_db("postgresql")
        db.execute.return_value = [(1, 1, "testco", "tok", "a@b.com", 1, "high")]
        integration = ZendeskIntegration(db, {})
        result = integration.update_config({"enabled": True})
        assert result is True

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = Exception("db error")
        integration = ZendeskIntegration(db, {})
        result = integration.update_config({"enabled": True})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_config_defaults(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        db.execute.return_value = []
        integration = ZendeskIntegration(db, {})
        result = integration.update_config({})
        assert result is True
        assert integration.enabled is False


@pytest.mark.unit
class TestZendeskCreateTicket:
    """Tests for ZendeskIntegration.create_ticket."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_disabled(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = False
        result = integration.create_ticket({"subject": "Test"})
        assert result is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_no_config(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = []
        integration = ZendeskIntegration(db, {})
        integration.enabled = True
        result = integration.create_ticket({"subject": "Test"})
        assert result is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_direct_api_success(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
            "default_priority": "normal",
        }

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"ticket": {"id": 12345}}

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_ticket(
                {
                    "subject": "Call from 5551234",
                    "description": "Incoming call from customer",
                    "requester_email": "customer@example.com",
                    "priority": "high",
                    "tags": ["phone", "incoming"],
                }
            )

        assert result == "12345"
        call_url = mock_post.call_args[0][0]
        assert "testco.zendesk.com" in call_url

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_with_requester_name(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"ticket": {"id": 99}}

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_ticket(
                {
                    "subject": "Call",
                    "requester_name": "John Doe",
                }
            )

        assert result == "99"
        payload = mock_post.call_args[1]["json"]
        assert payload["ticket"]["requester"]["name"] == "John Doe"

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_webhook_success(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
            "webhook_url": "https://hooks.example.com/zendesk",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ticket": {"id": 777}}

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_ticket({"subject": "Webhook Ticket"})

        assert result == "777"
        call_url = mock_post.call_args[0][0]
        assert call_url == "https://hooks.example.com/zendesk"

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_api_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Unprocessable Entity"

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_ticket({"subject": "Fail Ticket"})

        assert result is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_request_exception(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        import requests as requests_lib

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch(
                "requests.post",
                side_effect=requests_lib.exceptions.Timeout("timeout"),
            ),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_ticket({"subject": "Timeout Ticket"})

        assert result is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_value_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch(
                "requests.post",
                side_effect=ValueError("value err"),
            ),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_ticket({"subject": "Value Error Ticket"})

        assert result is None

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_defaults(self, mock_logger: MagicMock) -> None:
        """Ticket with defaults for subject, description, priority."""
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
            "default_priority": "low",
        }

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"ticket": {"id": 42}}

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response) as mock_post,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_ticket({})

        assert result == "42"
        payload = mock_post.call_args[1]["json"]
        assert payload["ticket"]["subject"] == "Phone Call"
        assert payload["ticket"]["comment"]["body"] == "Ticket created from phone call"
        assert payload["ticket"]["priority"] == "low"

    @patch("pbx.features.crm_integrations.get_logger")
    def test_create_ticket_missing_ticket_id_in_response(self, mock_logger: MagicMock) -> None:
        """Response has no ticket id -- returns empty string."""
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {}

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.post", return_value=mock_response),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.create_ticket({"subject": "No ID"})

        assert result == ""


@pytest.mark.unit
class TestZendeskUpdateTicket:
    """Tests for ZendeskIntegration.update_ticket."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_ticket_disabled(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = False
        result = integration.update_ticket("123", {"status": "closed"})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_ticket_no_config(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = []
        integration = ZendeskIntegration(db, {})
        integration.enabled = True
        result = integration.update_ticket("123", {"status": "closed"})
        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_ticket_direct_api_success(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.put", return_value=mock_response) as mock_put,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.update_ticket(
                "123",
                {
                    "status": "solved",
                    "priority": "urgent",
                    "comment": "Issue resolved",
                    "assignee_id": "456",
                },
            )

        assert result is True
        call_url = mock_put.call_args[0][0]
        assert "testco.zendesk.com" in call_url
        assert "123" in call_url

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_ticket_webhook_success(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
            "webhook_url": "https://hooks.example.com/zendesk",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.put", return_value=mock_response) as mock_put,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.update_ticket("123", {"status": "solved"})

        assert result is True
        call_url = mock_put.call_args[0][0]
        assert "hooks.example.com" in call_url
        assert "123" in call_url

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_ticket_api_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.put", return_value=mock_response),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.update_ticket("999", {"status": "solved"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_ticket_request_exception(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        import requests as requests_lib

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch(
                "requests.put",
                side_effect=requests_lib.exceptions.ConnectionError("connection refused"),
            ),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.update_ticket("123", {"status": "solved"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_ticket_key_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch(
                "requests.put",
                side_effect=KeyError("missing"),
            ),
            patch.object(integration, "_log_activity"),
        ):
            result = integration.update_ticket("123", {"status": "solved"})

        assert result is False

    @patch("pbx.features.crm_integrations.get_logger")
    def test_update_ticket_empty_update_data(self, mock_logger: MagicMock) -> None:
        """Empty update data -- sends empty ticket dict."""
        db = _make_db()
        integration = ZendeskIntegration(db, {})
        integration.enabled = True

        mock_config = {
            "subdomain": "testco",
            "email": "admin@testco.com",
            "api_token": "tok123",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch.object(integration, "get_config", return_value=mock_config),
            patch("requests.put", return_value=mock_response) as mock_put,
            patch.object(integration, "_log_activity"),
        ):
            result = integration.update_ticket("123", {})

        assert result is True
        payload = mock_put.call_args[1]["json"]
        assert payload["ticket"] == {}


@pytest.mark.unit
class TestZendeskLogActivity:
    """Tests for ZendeskIntegration._log_activity."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_log_activity_sqlite(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        integration = ZendeskIntegration(db, {})
        integration._log_activity("zendesk", "create_ticket", "success", "Ticket 123")
        db.execute.assert_called_once()
        call_args = db.execute.call_args
        assert "?" in call_args[0][0]

    @patch("pbx.features.crm_integrations.get_logger")
    def test_log_activity_postgres(self, mock_logger: MagicMock) -> None:
        db = _make_db("postgresql")
        integration = ZendeskIntegration(db, {})
        integration._log_activity("zendesk", "create_ticket", "success", "Ticket 123")
        db.execute.assert_called_once()
        call_args = db.execute.call_args
        assert "%s" in call_args[0][0]

    @patch("pbx.features.crm_integrations.get_logger")
    def test_log_activity_db_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = Exception("log error")
        integration = ZendeskIntegration(db, {})
        # Should not raise
        integration._log_activity("zendesk", "action", "error", "details")


@pytest.mark.unit
class TestZendeskGetActivityLog:
    """Tests for ZendeskIntegration.get_activity_log."""

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_activity_log_sqlite(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        db.execute.return_value = [
            (1, "zendesk", "create_ticket", "success", "Ticket 100", "2026-01-01T00:00:00"),
            (2, "zendesk", "update_ticket", "error", "API error: 500", "2026-01-02T00:00:00"),
        ]
        integration = ZendeskIntegration(db, {})
        activities = integration.get_activity_log(limit=50)
        assert len(activities) == 2
        assert activities[0]["integration_type"] == "zendesk"
        assert activities[0]["action"] == "create_ticket"
        assert activities[0]["status"] == "success"
        assert activities[0]["details"] == "Ticket 100"
        assert activities[0]["created_at"] == "2026-01-01T00:00:00"
        assert activities[1]["action"] == "update_ticket"

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_activity_log_postgres(self, mock_logger: MagicMock) -> None:
        db = _make_db("postgresql")
        db.execute.return_value = [
            (1, "hubspot", "sync_contact", "success", "Synced", "2026-01-01T00:00:00"),
        ]
        integration = ZendeskIntegration(db, {})
        activities = integration.get_activity_log()
        assert len(activities) == 1
        # Check the SQL uses %s placeholder
        call_args = db.execute.call_args
        assert "%s" in call_args[0][0]

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_activity_log_empty(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = []
        integration = ZendeskIntegration(db, {})
        activities = integration.get_activity_log()
        assert activities == []

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_activity_log_none_result(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.return_value = None
        integration = ZendeskIntegration(db, {})
        activities = integration.get_activity_log()
        assert activities == []

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_activity_log_db_error(self, mock_logger: MagicMock) -> None:
        db = _make_db()
        db.execute.side_effect = Exception("db error")
        integration = ZendeskIntegration(db, {})
        activities = integration.get_activity_log()
        assert activities == []

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_activity_log_default_limit(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        db.execute.return_value = []
        integration = ZendeskIntegration(db, {})
        integration.get_activity_log()
        call_args = db.execute.call_args
        assert call_args[0][1] == (100,)

    @patch("pbx.features.crm_integrations.get_logger")
    def test_get_activity_log_custom_limit(self, mock_logger: MagicMock) -> None:
        db = _make_db("sqlite")
        db.execute.return_value = []
        integration = ZendeskIntegration(db, {})
        integration.get_activity_log(limit=25)
        call_args = db.execute.call_args
        assert call_args[0][1] == (25,)
