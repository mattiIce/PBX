"""Integration tests for device provisioning.

Covers provisioning template CRUD operations and the phone
registration flow using mock PBXCore subsystems.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from pbx.features.phone_provisioning import (
    PhoneProvisioning,
    PhoneTemplate,
    ProvisioningDevice,
    normalize_mac_address,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_json(
    client: FlaskClient, url: str, data: dict[str, Any], headers: dict[str, str] | None = None
) -> TestResponse:
    all_headers = {"Content-Type": "application/json"}
    if headers:
        all_headers.update(headers)
    return client.post(url, data=json.dumps(data), headers=all_headers)


def _put_json(
    client: FlaskClient, url: str, data: dict[str, Any], headers: dict[str, str] | None = None
) -> TestResponse:
    all_headers = {"Content-Type": "application/json"}
    if headers:
        all_headers.update(headers)
    return client.put(url, data=json.dumps(data), headers=all_headers)


def _admin_token(client: FlaskClient, mock_pbx_core: MagicMock) -> dict[str, str]:
    """Log in as an admin and return the Bearer header dict."""
    mock_pbx_core.extension_db.get.return_value = {
        "number": "1001",
        "name": "Admin",
        "email": "admin@example.com",
        "is_admin": True,
        "voicemail_pin_hash": "admin-pin",
        "voicemail_pin_salt": None,
    }
    resp = _post_json(
        client,
        "/api/auth/login",
        {
            "extension": "1001",
            "password": "admin-pin",
        },
    )
    token = json.loads(resp.data)["token"]
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# Template CRUD (unit-level, exercising PhoneProvisioning directly)
# =========================================================================


@pytest.mark.integration
class TestProvisioningTemplateCRUD:
    """Test provisioning template create / read / update / delete operations."""

    @pytest.fixture
    def provisioning(self, mock_config: MagicMock) -> PhoneProvisioning:
        """Create a PhoneProvisioning instance with no database."""
        return PhoneProvisioning(mock_config, database=None)

    # -- Read built-in templates ------------------------------------------

    def test_builtin_templates_loaded(self, provisioning: PhoneProvisioning) -> None:
        """After init the built-in templates should be available."""
        templates = provisioning.list_all_templates()
        assert len(templates) > 0

        vendors = provisioning.get_supported_vendors()
        assert "yealink" in vendors
        assert "polycom" in vendors

    def test_get_template_by_vendor_model(self, provisioning: PhoneProvisioning) -> None:
        """Fetch a specific template by vendor and model."""
        template = provisioning.get_template("yealink", "t46s")
        assert template is not None
        assert isinstance(template, PhoneTemplate)
        assert "{{EXTENSION_NUMBER}}" in template.template_content

    def test_get_nonexistent_template_returns_none(self, provisioning: PhoneProvisioning) -> None:
        """Requesting a template for an unknown vendor/model returns None."""
        assert provisioning.get_template("unknown", "phone") is None

    # -- Create (add) templates -------------------------------------------

    def test_add_custom_template(self, provisioning: PhoneProvisioning) -> None:
        """Adding a custom template should make it retrievable."""
        custom_content = "custom config for {{EXTENSION_NUMBER}}"
        provisioning.add_template("acme", "rocket", custom_content)

        template = provisioning.get_template("acme", "rocket")
        assert template is not None
        assert template.vendor == "acme"
        assert template.model == "rocket"
        assert "{{EXTENSION_NUMBER}}" in template.template_content

    # -- Update templates -------------------------------------------------

    def test_update_template_content(self, provisioning: PhoneProvisioning) -> None:
        """Updating a template replaces its content in memory."""
        # Add a template first
        provisioning.add_template("acme", "rocket", "original content")

        # update_template writes to disk -- mock the filesystem part
        with (
            patch("builtins.open", MagicMock()),
            patch("os.path.exists", return_value=True),
            patch("os.makedirs"),
        ):
            success, _msg = provisioning.update_template("acme", "rocket", "updated content")

        assert success is True
        template = provisioning.get_template("acme", "rocket")
        assert template.template_content == "updated content"

    # -- Delete (reload clears custom) ------------------------------------

    def test_reload_restores_builtins(self, provisioning: PhoneProvisioning) -> None:
        """Reloading templates should restore built-in templates."""
        original_count = len(provisioning.templates)

        # Add a custom template
        provisioning.add_template("acme", "rocket", "custom")
        assert len(provisioning.templates) == original_count + 1

        # Reload -- custom template (in-memory only) is gone
        success, _msg, _stats = provisioning.reload_templates()
        assert success is True
        assert provisioning.get_template("acme", "rocket") is None
        assert len(provisioning.templates) == original_count

    # -- Template generate_config -----------------------------------------

    def test_template_generates_config_with_placeholders(
        self, provisioning: PhoneProvisioning
    ) -> None:
        """PhoneTemplate.generate_config should replace placeholders."""
        template = provisioning.get_template("yealink", "t46s")
        ext_config = {"number": "1001", "name": "Alice", "password": "s3cret"}
        srv_config = {
            "sip_host": "10.0.0.1",
            "sip_port": 5060,
            "server_name": "PBX",
            "ldap_phonebook": {},
            "remote_phonebook": {},
            "dtmf": {},
        }

        output = template.generate_config(ext_config, srv_config)
        assert "1001" in output
        assert "Alice" in output
        assert "10.0.0.1" in output
        assert "{{EXTENSION_NUMBER}}" not in output


# =========================================================================
# Phone registration flow (unit-level)
# =========================================================================


@pytest.mark.integration
class TestPhoneRegistrationFlow:
    """Test registering, querying, and unregistering phone devices."""

    @pytest.fixture
    def provisioning(self, mock_config: MagicMock) -> PhoneProvisioning:
        """Create a PhoneProvisioning instance with no database."""
        return PhoneProvisioning(mock_config, database=None)

    def test_register_device(self, provisioning: PhoneProvisioning) -> None:
        """Registering a device should store it and return the object."""
        device = provisioning.register_device(
            mac_address="AA:BB:CC:DD:EE:FF",
            extension_number="1001",
            vendor="yealink",
            model="t46s",
        )

        assert device is not None
        assert device.mac_address == "aabbccddeeff"
        assert device.extension_number == "1001"
        assert device.vendor == "yealink"
        assert device.model == "t46s"

    def test_get_device_by_mac(self, provisioning: PhoneProvisioning) -> None:
        """A registered device should be retrievable by MAC address."""
        provisioning.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")

        device = provisioning.get_device("AA:BB:CC:DD:EE:FF")
        assert device is not None
        assert device.extension_number == "1001"

    def test_get_device_normalizes_mac(self, provisioning: PhoneProvisioning) -> None:
        """MAC formats with various separators should match."""
        provisioning.register_device("aa:bb:cc:dd:ee:ff", "1001", "yealink", "t46s")

        # Query with different separators
        assert provisioning.get_device("AA-BB-CC-DD-EE-FF") is not None
        assert provisioning.get_device("aabb.ccdd.eeff") is not None
        assert provisioning.get_device("aabbccddeeff") is not None

    def test_get_all_devices(self, provisioning: PhoneProvisioning) -> None:
        """get_all_devices returns every registered device."""
        provisioning.register_device("AA:BB:CC:DD:EE:01", "1001", "yealink", "t46s")
        provisioning.register_device("AA:BB:CC:DD:EE:02", "1002", "polycom", "vvx450")

        devices = provisioning.get_all_devices()
        assert len(devices) == 2

    def test_unregister_device(self, provisioning: PhoneProvisioning) -> None:
        """Unregistering a device removes it from the store."""
        provisioning.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")

        removed = provisioning.unregister_device("AA:BB:CC:DD:EE:FF")
        assert removed is True
        assert provisioning.get_device("AA:BB:CC:DD:EE:FF") is None

    def test_unregister_nonexistent_device(self, provisioning: PhoneProvisioning) -> None:
        """Unregistering an unknown device returns False."""
        removed = provisioning.unregister_device("00:00:00:00:00:00")
        assert removed is False

    def test_generate_config_for_registered_device(self, provisioning: PhoneProvisioning) -> None:
        """Full round-trip: register device then generate its config."""
        provisioning.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")

        # Build a mock extension registry
        ext = MagicMock()
        ext.number = "1001"
        ext.name = "Alice"
        ext.config = {"password": "s3cret"}
        registry = MagicMock()
        registry.get.return_value = ext
        registry.get_all.return_value = [ext]

        config_content, content_type = provisioning.generate_config("AA:BB:CC:DD:EE:FF", registry)

        assert config_content is not None
        assert "1001" in config_content
        assert "Alice" in config_content
        assert content_type == "text/plain"

    def test_generate_config_missing_device_returns_none(
        self, provisioning: PhoneProvisioning
    ) -> None:
        """Generating config for an unregistered MAC returns (None, None)."""
        registry = MagicMock()
        config, ctype = provisioning.generate_config("00:00:00:00:00:00", registry)
        assert config is None
        assert ctype is None

    def test_device_marked_provisioned_after_config_generation(
        self, provisioning: PhoneProvisioning
    ) -> None:
        """After generate_config the device should have last_provisioned set."""
        provisioning.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")

        ext = MagicMock()
        ext.number = "1001"
        ext.name = "Alice"
        ext.config = {"password": "s3cret"}
        registry = MagicMock()
        registry.get.return_value = ext
        registry.get_all.return_value = [ext]

        provisioning.generate_config("AA:BB:CC:DD:EE:FF", registry)

        device = provisioning.get_device("AA:BB:CC:DD:EE:FF")
        assert device.last_provisioned is not None


# =========================================================================
# API-level provisioning tests (via Flask test client)
# =========================================================================


@pytest.mark.integration
class TestProvisioningAPI:
    """Test provisioning endpoints through the Flask test client."""

    def test_register_device_via_api(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """POST /api/provisioning/devices should register a device."""
        # Set up phone_provisioning on the mock
        mock_pbx_core.phone_provisioning = PhoneProvisioning(mock_pbx_core.config, database=None)

        headers = _admin_token(api_client, mock_pbx_core)

        resp = _post_json(
            api_client,
            "/api/provisioning/devices",
            {
                "mac_address": "11:22:33:44:55:66",
                "extension_number": "1001",
                "vendor": "yealink",
                "model": "t46s",
            },
            headers=headers,
        )

        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["device"]["mac_address"] == "112233445566"

    def test_get_templates_via_api(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        """GET /api/provisioning/templates should list templates."""
        mock_pbx_core.phone_provisioning = PhoneProvisioning(mock_pbx_core.config, database=None)

        headers = _admin_token(api_client, mock_pbx_core)

        # Templates endpoint requires @require_auth (not admin)
        resp = api_client.get("/api/provisioning/templates", headers=headers)

        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert "templates" in data
        assert data["total"] > 0
