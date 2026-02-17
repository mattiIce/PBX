"""Comprehensive tests for the Lansweeper integration module."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests as real_requests

from pbx.integrations.lansweeper import LansweeperIntegration


def _make_enabled_config(
    api_url: str = "https://lansweeper-server:81/api",
    api_token: str = "test-token",
    username: str | None = None,
    password: str | None = None,
    cache_ttl_seconds: int = 3600,
) -> dict[str, Any]:
    """Create a standard enabled Lansweeper config dict."""
    config: dict[str, Any] = {
        "integrations": {
            "lansweeper": {
                "enabled": True,
                "api_url": api_url,
                "api_token": api_token,
                "cache_ttl_seconds": cache_ttl_seconds,
            }
        }
    }
    if username:
        config["integrations"]["lansweeper"]["username"] = username
    if password:
        config["integrations"]["lansweeper"]["password"] = password
    return config


def _make_disabled_config() -> dict[str, Any]:
    """Create a disabled Lansweeper config dict."""
    return {"integrations": {"lansweeper": {"enabled": False}}}


@pytest.mark.unit
class TestLansweeperIntegrationInit:
    """Tests for Lansweeper integration initialization."""

    def test_init_enabled_with_full_config(self) -> None:
        """Test initialization with a complete and valid config."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        assert integration.enabled is True
        assert integration.api_url == "https://lansweeper-server:81/api"
        assert integration.api_token == "test-token"
        assert integration.cache_ttl == 3600
        assert integration.asset_cache == {}
        assert integration.phone_assets == {}

    def test_init_disabled(self) -> None:
        """Test initialization when integration is disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        assert integration.enabled is False

    def test_init_none_config(self) -> None:
        """Test initialization with None config."""
        integration = LansweeperIntegration(None)

        assert integration.enabled is False
        assert integration.config == {}

    def test_init_empty_config(self) -> None:
        """Test initialization with empty config dict."""
        integration = LansweeperIntegration({})

        assert integration.enabled is False

    def test_init_default_api_url(self) -> None:
        """Test default API URL when not specified."""
        config = {"integrations": {"lansweeper": {"enabled": True}}}
        integration = LansweeperIntegration(config)

        assert integration.api_url == "https://lansweeper-server:81/api"

    def test_init_default_cache_ttl(self) -> None:
        """Test default cache TTL value."""
        config = {"integrations": {"lansweeper": {"enabled": True, "api_token": "tok"}}}
        integration = LansweeperIntegration(config)

        assert integration.cache_ttl == 3600

    @patch("pbx.integrations.lansweeper.REQUESTS_AVAILABLE", False)
    def test_init_requests_unavailable_logs_warning(self) -> None:
        """Test that missing requests library logs a warning."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        # Still enabled = True since it only warns, doesn't disable
        assert integration.enabled is True

    def test_init_with_http_url_logs_warning(self) -> None:
        """Test that HTTP (non-HTTPS) URL triggers a warning."""
        config = _make_enabled_config(api_url="http://lansweeper:81/api")
        integration = LansweeperIntegration(config)

        assert integration.enabled is True
        assert integration.api_url == "http://lansweeper:81/api"

    def test_init_with_username_and_password(self) -> None:
        """Test initialization with username/password auth."""
        config = _make_enabled_config(username="admin", password="secret")
        integration = LansweeperIntegration(config)

        assert integration.username == "admin"
        assert integration.password == "secret"


@pytest.mark.unit
class TestMakeRequest:
    """Tests for the _make_request method."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_get_success(self, mock_requests: MagicMock) -> None:
        """Test a successful GET request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"AssetName": "Phone1"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration._make_request("asset/mac/001122334455")

        assert result == {"AssetName": "Phone1"}
        mock_requests.get.assert_called_once()

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_post_success(self, mock_requests: MagicMock) -> None:
        """Test a successful POST request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration._make_request(
            "asset/customfield", method="POST", data={"field": "value"}
        )

        assert result == {"success": True}
        mock_requests.post.assert_called_once()

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_unsupported_method(self, mock_requests: MagicMock) -> None:
        """Test _make_request with unsupported HTTP method."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration._make_request("endpoint", method="DELETE")

        assert result is None

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_with_api_token_auth(self, mock_requests: MagicMock) -> None:
        """Test that API token is sent in headers."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config(api_token="my-token")
        integration = LansweeperIntegration(config)

        integration._make_request("test")

        call_kwargs = mock_requests.get.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["Authorization"] == "Token my-token"

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_with_basic_auth(self, mock_requests: MagicMock) -> None:
        """Test request with username/password auth."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config(username="admin", password="pass")
        integration = LansweeperIntegration(config)

        integration._make_request("test")

        call_kwargs = mock_requests.get.call_args
        assert call_kwargs.kwargs["auth"] == ("admin", "pass")

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_no_basic_auth_without_username(self, mock_requests: MagicMock) -> None:
        """Test request without username does not send basic auth."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        integration._make_request("test")

        call_kwargs = mock_requests.get.call_args
        assert call_kwargs.kwargs["auth"] is None

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_network_error(self, mock_requests: MagicMock) -> None:
        """Test handling of network exception."""
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.RequestException("Timeout")

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration._make_request("test")

        assert result is None

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_http_error(self, mock_requests: MagicMock) -> None:
        """Test handling of HTTP error status."""
        mock_requests.exceptions = real_requests.exceptions
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = real_requests.exceptions.RequestException(
            "404"
        )
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration._make_request("test")

        assert result is None

    @patch("pbx.integrations.lansweeper.REQUESTS_AVAILABLE", False)
    def test_make_request_requests_not_available(self) -> None:
        """Test _make_request when requests library is not available."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration._make_request("test")

        assert result is None

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_no_token_no_auth_header(self, mock_requests: MagicMock) -> None:
        """Test that no Authorization header is set when no api_token."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = {"integrations": {"lansweeper": {"enabled": True}}}
        integration = LansweeperIntegration(config)

        integration._make_request("test")

        call_kwargs = mock_requests.get.call_args
        headers = call_kwargs.kwargs["headers"]
        assert "Authorization" not in headers

    @patch("pbx.integrations.lansweeper.requests")
    def test_make_request_constructs_correct_url(self, mock_requests: MagicMock) -> None:
        """Test that URL is constructed correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        integration._make_request("asset/mac/AABBCCDDEEFF")

        call_kwargs = mock_requests.get.call_args
        assert call_kwargs.args[0] == "https://lansweeper-server:81/api/asset/mac/AABBCCDDEEFF"


@pytest.mark.unit
class TestGetAssetByMac:
    """Tests for get_asset_by_mac."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_asset_by_mac_success(self, mock_requests: MagicMock) -> None:
        """Test successfully getting asset by MAC address."""
        asset_data = {"AssetName": "Polycom VVX", "IPAddress": "10.0.0.1"}
        mock_response = MagicMock()
        mock_response.json.return_value = asset_data
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_asset_by_mac("00:11:22:33:44:55")

        assert result == asset_data

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_asset_by_mac_normalizes_address(self, mock_requests: MagicMock) -> None:
        """Test that MAC address is normalized (uppercase, no separators)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"AssetName": "Phone"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        integration.get_asset_by_mac("aa:bb:cc:dd:ee:ff")

        call_kwargs = mock_requests.get.call_args
        assert "AABBCCDDEEFF" in call_kwargs.args[0]

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_asset_by_mac_normalizes_hyphens(self, mock_requests: MagicMock) -> None:
        """Test that hyphens in MAC address are removed."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"AssetName": "Phone"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        integration.get_asset_by_mac("AA-BB-CC-DD-EE-FF")

        call_kwargs = mock_requests.get.call_args
        assert "AABBCCDDEEFF" in call_kwargs.args[0]

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_asset_by_mac_caching(self, mock_requests: MagicMock) -> None:
        """Test that results are cached and reused."""
        asset_data = {"AssetName": "Phone"}
        mock_response = MagicMock()
        mock_response.json.return_value = asset_data
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        # First call: fetches from API
        result1 = integration.get_asset_by_mac("00:11:22:33:44:55")
        assert result1 == asset_data

        # Second call: should use cache
        result2 = integration.get_asset_by_mac("00:11:22:33:44:55")
        assert result2 == asset_data

        # API should only be called once
        assert mock_requests.get.call_count == 1

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_asset_by_mac_cache_expired(self, mock_requests: MagicMock) -> None:
        """Test that expired cache entries are refetched."""
        asset_data = {"AssetName": "Phone"}
        mock_response = MagicMock()
        mock_response.json.return_value = asset_data
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config(cache_ttl_seconds=1)
        integration = LansweeperIntegration(config)

        # Manually place expired cache entry
        mac_normalized = "001122334455"
        integration.asset_cache[mac_normalized] = {
            "data": {"AssetName": "OldPhone"},
            "cached_at": datetime.now(UTC) - timedelta(hours=2),
        }

        # Should refetch because cache is expired
        result = integration.get_asset_by_mac("00:11:22:33:44:55")

        assert result == asset_data
        mock_requests.get.assert_called_once()

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_asset_by_mac_not_found(self, mock_requests: MagicMock) -> None:
        """Test get_asset_by_mac when asset is not found."""
        mock_requests.exceptions = real_requests.exceptions
        mock_response = MagicMock()
        mock_response.json.return_value = None
        mock_response.raise_for_status.side_effect = real_requests.exceptions.RequestException(
            "404"
        )
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_asset_by_mac("FF:FF:FF:FF:FF:FF")

        assert result is None

    def test_get_asset_by_mac_disabled(self) -> None:
        """Test get_asset_by_mac when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_asset_by_mac("00:11:22:33:44:55")

        assert result is None


@pytest.mark.unit
class TestGetAssetByIp:
    """Tests for get_asset_by_ip."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_asset_by_ip_success(self, mock_requests: MagicMock) -> None:
        """Test getting asset by IP address."""
        asset_data = {"AssetName": "Phone", "IPAddress": "10.0.0.1"}
        mock_response = MagicMock()
        mock_response.json.return_value = asset_data
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_asset_by_ip("10.0.0.1")

        assert result == asset_data

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_asset_by_ip_not_found(self, mock_requests: MagicMock) -> None:
        """Test get_asset_by_ip when not found."""
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.RequestException("404")

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_asset_by_ip("10.0.0.99")

        assert result is None

    def test_get_asset_by_ip_disabled(self) -> None:
        """Test get_asset_by_ip when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_asset_by_ip("10.0.0.1")

        assert result is None


@pytest.mark.unit
class TestGetPhoneInfo:
    """Tests for get_phone_info."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_phone_info_success(self, mock_requests: MagicMock) -> None:
        """Test getting phone info with full asset data."""
        asset_data = {
            "AssetName": "Polycom VVX 411",
            "Model": "VVX 411",
            "Manufacturer": "Polycom",
            "Location": "Building A, Floor 2",
            "Building": "Building A",
            "Room": "Conference 201",
            "UserName": "jdoe",
            "Department": "IT",
            "IPAddress": "10.0.0.50",
            "LastSeen": "2026-02-15T10:00:00",
            "SerialNumber": "SN123456",
        }
        mock_response = MagicMock()
        mock_response.json.return_value = asset_data
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_phone_info("00:11:22:33:44:55")

        assert result["mac_address"] == "00:11:22:33:44:55"
        assert result["asset_name"] == "Polycom VVX 411"
        assert result["model"] == "VVX 411"
        assert result["manufacturer"] == "Polycom"
        assert result["location"] == "Building A, Floor 2"
        assert result["building"] == "Building A"
        assert result["room"] == "Conference 201"
        assert result["assigned_user"] == "jdoe"
        assert result["department"] == "IT"
        assert result["ip_address"] == "10.0.0.50"
        assert result["serial_number"] == "SN123456"

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_phone_info_asset_not_found(self, mock_requests: MagicMock) -> None:
        """Test get_phone_info when asset is not in Lansweeper."""
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.RequestException("404")

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_phone_info("FF:FF:FF:FF:FF:FF")

        assert result == {"error": "Asset not found in Lansweeper"}

    def test_get_phone_info_disabled(self) -> None:
        """Test get_phone_info when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_phone_info("00:11:22:33:44:55")

        assert result == {"error": "Lansweeper integration not enabled"}

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_phone_info_missing_fields_default_to_unknown(
        self, mock_requests: MagicMock
    ) -> None:
        """Test that missing asset fields default to 'Unknown'."""
        mock_response = MagicMock()
        # Return a non-empty dict so get_asset_by_mac considers it truthy
        mock_response.json.return_value = {"id": 1}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_phone_info("00:11:22:33:44:55")

        assert result["asset_name"] == "Unknown"
        assert result["model"] == "Unknown"
        assert result["building"] == "Unknown"


@pytest.mark.unit
class TestLinkPhoneToExtension:
    """Tests for link_phone_to_extension."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_link_phone_success(self, mock_requests: MagicMock) -> None:
        """Test linking a phone to an extension."""
        asset_data = {"AssetName": "Polycom VVX"}
        mock_response = MagicMock()
        mock_response.json.return_value = asset_data
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.link_phone_to_extension("1001", "00:11:22:33:44:55")

        assert result is True
        assert "1001" in integration.phone_assets
        assert integration.phone_assets["1001"]["mac_address"] == "00:11:22:33:44:55"
        assert integration.phone_assets["1001"]["asset_info"] == asset_data

    @patch("pbx.integrations.lansweeper.requests")
    def test_link_phone_asset_not_found(self, mock_requests: MagicMock) -> None:
        """Test link_phone when asset is not found."""
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.RequestException("404")

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.link_phone_to_extension("1001", "FF:FF:FF:FF:FF:FF")

        assert result is False
        assert "1001" not in integration.phone_assets

    def test_link_phone_disabled(self) -> None:
        """Test link_phone when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.link_phone_to_extension("1001", "00:11:22:33:44:55")

        assert result is False


@pytest.mark.unit
class TestGetExtensionLocation:
    """Tests for get_extension_location."""

    def test_get_extension_location_success(self) -> None:
        """Test getting location of a linked extension."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        # Manually set up phone_assets
        integration.phone_assets["1001"] = {
            "mac_address": "00:11:22:33:44:55",
            "asset_info": {
                "Building": "Main Office",
                "Floor": "2",
                "Room": "201",
                "Location": "Main Office, Floor 2, Room 201",
                "Address": "123 Main St",
            },
            "linked_at": datetime.now(UTC),
        }

        result = integration.get_extension_location("1001")

        assert result is not None
        assert result["building"] == "Main Office"
        assert result["floor"] == "2"
        assert result["room"] == "201"
        assert result["address"] == "123 Main St"

    def test_get_extension_location_not_linked(self) -> None:
        """Test getting location of an extension not linked."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_extension_location("9999")

        assert result is None

    def test_get_extension_location_missing_fields(self) -> None:
        """Test that missing asset fields default to 'Unknown'."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        integration.phone_assets["1001"] = {
            "mac_address": "00:11:22:33:44:55",
            "asset_info": {},
            "linked_at": datetime.now(UTC),
        }

        result = integration.get_extension_location("1001")

        assert result is not None
        assert result["building"] == "Unknown"
        assert result["floor"] == "Unknown"


@pytest.mark.unit
class TestUpdateAssetCustomField:
    """Tests for update_asset_custom_field."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_update_custom_field_success(self, mock_requests: MagicMock) -> None:
        """Test updating a custom field successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.update_asset_custom_field("00:11:22:33:44:55", "PBX_Extension", "1001")

        assert result is True
        call_kwargs = mock_requests.post.call_args
        data = call_kwargs.kwargs["json"]
        assert data["mac_address"] == "001122334455"
        assert data["field_name"] == "PBX_Extension"
        assert data["value"] == "1001"

    @patch("pbx.integrations.lansweeper.requests")
    def test_update_custom_field_api_failure(self, mock_requests: MagicMock) -> None:
        """Test update_asset_custom_field when API fails."""
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.post.side_effect = real_requests.exceptions.RequestException("Error")

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.update_asset_custom_field("00:11:22:33:44:55", "field", "value")

        assert result is False

    def test_update_custom_field_disabled(self) -> None:
        """Test update_asset_custom_field when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.update_asset_custom_field("00:11:22:33:44:55", "field", "value")

        assert result is False


@pytest.mark.unit
class TestSyncPhoneExtension:
    """Tests for sync_phone_extension."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_sync_phone_extension_success(self, mock_requests: MagicMock) -> None:
        """Test syncing phone extension data to Lansweeper."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.sync_phone_extension("1001", "00:11:22:33:44:55", "Polycom VVX 411")

        assert result is True
        assert mock_requests.post.call_count == 3  # Three custom fields updated

    @patch("pbx.integrations.lansweeper.requests")
    def test_sync_phone_extension_partial_failure(self, mock_requests: MagicMock) -> None:
        """Test sync_phone_extension when some updates fail."""
        mock_requests.exceptions = real_requests.exceptions
        call_count = 0

        def post_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise real_requests.exceptions.RequestException("Fail")
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"success": True}
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_requests.post.side_effect = post_side_effect

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.sync_phone_extension("1001", "00:11:22:33:44:55", "Polycom VVX 411")

        assert result is False

    def test_sync_phone_extension_disabled(self) -> None:
        """Test sync_phone_extension when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.sync_phone_extension("1001", "00:11:22:33:44:55", "Polycom")

        assert result is False


@pytest.mark.unit
class TestGetAllPhones:
    """Tests for get_all_phones."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_all_phones_success(self, mock_requests: MagicMock) -> None:
        """Test getting all phone assets."""
        phones = [{"AssetName": "Phone1"}, {"AssetName": "Phone2"}]
        mock_response = MagicMock()
        mock_response.json.return_value = phones
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_all_phones()

        assert result == phones

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_all_phones_empty(self, mock_requests: MagicMock) -> None:
        """Test get_all_phones with no phones."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_all_phones()

        assert result == []

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_all_phones_non_list_response(self, mock_requests: MagicMock) -> None:
        """Test get_all_phones when API returns a dict instead of list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "unexpected"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_all_phones()

        assert result == []

    def test_get_all_phones_disabled(self) -> None:
        """Test get_all_phones when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_all_phones()

        assert result == []


@pytest.mark.unit
class TestGetUserAssets:
    """Tests for get_user_assets."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_user_assets_success(self, mock_requests: MagicMock) -> None:
        """Test getting assets assigned to a user."""
        assets = [{"AssetName": "Laptop"}, {"AssetName": "Phone"}]
        mock_response = MagicMock()
        mock_response.json.return_value = assets
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_user_assets("jdoe")

        assert result == assets

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_user_assets_empty(self, mock_requests: MagicMock) -> None:
        """Test get_user_assets with no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_user_assets("nobody")

        assert result == []

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_user_assets_non_list(self, mock_requests: MagicMock) -> None:
        """Test get_user_assets when response is not a list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "not found"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_user_assets("jdoe")

        assert result == []

    def test_get_user_assets_disabled(self) -> None:
        """Test get_user_assets when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_user_assets("jdoe")

        assert result == []


@pytest.mark.unit
class TestSearchAssets:
    """Tests for search_assets."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_search_assets_success(self, mock_requests: MagicMock) -> None:
        """Test searching assets."""
        assets = [{"AssetName": "Phone1"}]
        mock_response = MagicMock()
        mock_response.json.return_value = assets
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.search_assets("Polycom")

        assert result == assets

    @patch("pbx.integrations.lansweeper.requests")
    def test_search_assets_no_results(self, mock_requests: MagicMock) -> None:
        """Test search_assets with no matches."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.search_assets("Nonexistent")

        assert result == []

    @patch("pbx.integrations.lansweeper.requests")
    def test_search_assets_non_list(self, mock_requests: MagicMock) -> None:
        """Test search_assets when response is not a list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.search_assets("Test")

        assert result == []

    def test_search_assets_disabled(self) -> None:
        """Test search_assets when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.search_assets("Phone")

        assert result == []


@pytest.mark.unit
class TestGetBuildingPhones:
    """Tests for get_building_phones."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_building_phones_success(self, mock_requests: MagicMock) -> None:
        """Test getting phones filtered by building."""
        phones = [
            {"AssetName": "Phone1", "Building": "Main"},
            {"AssetName": "Phone2", "Building": "Annex"},
            {"AssetName": "Phone3", "Building": "main"},
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = phones
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_building_phones("Main")

        assert len(result) == 2
        assert all(p["Building"].lower() == "main" for p in result)

    @patch("pbx.integrations.lansweeper.requests")
    def test_get_building_phones_no_match(self, mock_requests: MagicMock) -> None:
        """Test get_building_phones with no matching building."""
        phones = [{"AssetName": "Phone1", "Building": "Other"}]
        mock_response = MagicMock()
        mock_response.json.return_value = phones
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_building_phones("Main")

        assert result == []

    def test_get_building_phones_disabled(self) -> None:
        """Test get_building_phones when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        result = integration.get_building_phones("Main")

        assert result == []


@pytest.mark.unit
class TestGenerateE911Report:
    """Tests for generate_e911_report."""

    @patch("pbx.integrations.lansweeper.requests")
    def test_generate_e911_report_success(self, mock_requests: MagicMock) -> None:
        """Test generating a full E911 report."""
        phones = [
            {
                "AssetName": "Phone1",
                "MAC": "AA:BB:CC:DD:EE:01",
                "Building": "Main",
                "Floor": "1",
                "Room": "101",
                "Location": "Main Office",
                "IPAddress": "10.0.0.1",
                "UserName": "user1",
            },
            {
                "AssetName": "Phone2",
                "MAC": "AA:BB:CC:DD:EE:02",
                "Building": "Main",
                "Floor": "2",
                "Room": "201",
                "Location": "Main Office",
                "IPAddress": "10.0.0.2",
                "UserName": "user2",
            },
            {
                "AssetName": "Phone3",
                "MAC": "AA:BB:CC:DD:EE:03",
                "UserName": "user3",
                "IPAddress": "10.0.0.3",
            },
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = phones
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        report = integration.generate_e911_report()

        assert report["total_phones"] == 3
        assert "Main" in report["by_building"]
        assert report["by_building"]["Main"] == 2
        assert len(report["phones"]) == 3
        # Phone3 has no Building or Location
        assert len(report["missing_location"]) == 1
        assert report["missing_location"][0]["asset_name"] == "Phone3"
        assert "generated_at" in report

    @patch("pbx.integrations.lansweeper.requests")
    def test_generate_e911_report_no_phones(self, mock_requests: MagicMock) -> None:
        """Test E911 report with no phones."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        report = integration.generate_e911_report()

        assert report["total_phones"] == 0
        assert report["by_building"] == {}
        assert report["missing_location"] == []
        assert report["phones"] == []

    def test_generate_e911_report_disabled(self) -> None:
        """Test E911 report when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        report = integration.generate_e911_report()

        assert report == {"error": "Lansweeper integration not enabled"}


@pytest.mark.unit
class TestClearCache:
    """Tests for clear_cache."""

    def test_clear_cache(self) -> None:
        """Test clearing the asset cache."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        # Populate cache
        integration.asset_cache["TEST"] = {"data": {}, "cached_at": datetime.now(UTC)}

        integration.clear_cache()

        assert integration.asset_cache == {}

    def test_clear_cache_already_empty(self) -> None:
        """Test clearing an already empty cache."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        integration.clear_cache()

        assert integration.asset_cache == {}


@pytest.mark.unit
class TestGetStatistics:
    """Tests for get_statistics."""

    def test_get_statistics_enabled(self) -> None:
        """Test statistics when enabled."""
        config = _make_enabled_config()
        integration = LansweeperIntegration(config)

        # Add some data
        integration.asset_cache["MAC1"] = {"data": {}, "cached_at": datetime.now(UTC)}
        integration.phone_assets["1001"] = {"mac_address": "MAC1"}

        stats = integration.get_statistics()

        assert stats["enabled"] is True
        assert stats["cached_assets"] == 1
        assert stats["linked_phones"] == 1
        assert stats["api_url"] == "https://lansweeper-server:81/api"

    def test_get_statistics_disabled(self) -> None:
        """Test statistics when disabled."""
        config = _make_disabled_config()
        integration = LansweeperIntegration(config)

        stats = integration.get_statistics()

        assert stats["enabled"] is False
        assert stats["cached_assets"] == 0
        assert stats["linked_phones"] == 0
        assert stats["api_url"] is None
