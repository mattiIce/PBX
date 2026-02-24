"""Comprehensive tests for Provisioning Blueprint routes."""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

AUTH_ADMIN = (True, {"extension": "1001", "is_admin": True})
AUTH_USER = (True, {"extension": "1001", "is_admin": False})
AUTH_NONE = (False, None)


def _make_device_mock(
    mac="AA:BB:CC:DD:EE:FF",
    extension_number="1001",
    vendor="yealink",
    model="t54w",
    config_url="http://example.com/cfg",
):
    d = MagicMock()
    d.mac_address = mac
    d.extension_number = extension_number
    d.vendor = vendor
    d.model = model
    d.config_url = config_url
    d.to_dict.return_value = {
        "mac_address": mac,
        "extension_number": extension_number,
        "vendor": vendor,
        "model": model,
    }
    return d


# ---------------------------------------------------------------------------
# GET /api/provisioning/devices
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProvisioningDevices:
    """Tests for GET /api/provisioning/devices."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        device = _make_device_mock()
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_all_devices.return_value = [device]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/devices")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]["mac_address"] == "AA:BB:CC:DD:EE:FF"

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/devices")
        assert resp.status_code == 500

    def test_unauthenticated(self, api_client: FlaskClient) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_NONE):
            resp = api_client.get("/api/provisioning/devices")
        assert resp.status_code == 401

    def test_non_admin(self, api_client: FlaskClient) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/provisioning/devices")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/provisioning/atas
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProvisioningAtas:
    """Tests for GET /api/provisioning/atas."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        ata = _make_device_mock(vendor="grandstream", model="ht802")
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_atas.return_value = [ata]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/atas")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/atas")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/provisioning/phones
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProvisioningPhones:
    """Tests for GET /api/provisioning/phones."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        phone = _make_device_mock()
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_phones.return_value = [phone]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/phones")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/phones")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/registered-atas
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRegisteredAtas:
    """Tests for GET /api/registered-atas."""

    def test_success_with_provisioned_atas(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        ata = _make_device_mock(extension_number="1001", vendor="grandstream", model="ht802")
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.list_all.return_value = [
            {"extension_number": "1001", "ip_address": "192.168.1.50"}
        ]
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_atas.return_value = [ata]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/registered-atas")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]["device_type"] == "ata"
        assert data[0]["vendor"] == "grandstream"

    def test_no_database(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = None

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/registered-atas")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []

    def test_database_error(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.list_all.side_effect = ValueError("db error")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/registered-atas")
        assert resp.status_code == 500

    def test_no_provisioning_attribute(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.list_all.return_value = [{"extension_number": "1001"}]
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/registered-atas")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []


# ---------------------------------------------------------------------------
# GET /api/provisioning/vendors
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProvisioningVendors:
    """Tests for GET /api/provisioning/vendors."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_supported_vendors.return_value = ["yealink"]
        mock_pbx_core.phone_provisioning.get_supported_models.return_value = ["t54w"]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/vendors")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["vendors"] == ["yealink"]
        assert data["models"] == ["t54w"]

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/vendors")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_supported_vendors.side_effect = RuntimeError("boom")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/vendors")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/provisioning/templates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProvisioningTemplates:
    """Tests for GET /api/provisioning/templates."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.list_all_templates.return_value = [
            {"vendor": "yealink", "model": "t54w"}
        ]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/templates")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total"] == 1

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/templates")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/provisioning/templates/<vendor>/<model>
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetTemplateContent:
    """Tests for GET /api/provisioning/templates/<vendor>/<model>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_template_content.return_value = "<config>...</config>"

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/templates/yealink/t54w")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["vendor"] == "yealink"
        assert data["model"] == "t54w"
        assert data["content"] == "<config>...</config>"
        assert "placeholders" in data

    def test_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_template_content.return_value = None

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/templates/yealink/t54w")
        assert resp.status_code == 404

    def test_invalid_vendor(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/templates/../../etc/passwd")
        assert resp.status_code in (400, 404)

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/templates/yealink/t54w")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/provisioning/diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProvisioningDiagnostics:
    """Tests for GET /api/provisioning/diagnostics."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        prov = MagicMock()
        prov.devices = [_make_device_mock()]
        prov.templates = {"yealink_t54w": "tpl"}
        prov.provision_requests = [{"success": True}, {"success": False}]
        prov.get_all_devices.return_value = [_make_device_mock()]
        prov.get_supported_vendors.return_value = ["yealink"]
        prov.get_supported_models.return_value = ["t54w"]
        prov.get_request_history.return_value = []
        mock_pbx_core.phone_provisioning = prov

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/diagnostics")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["enabled"] is True
        assert data["statistics"]["total_devices"] == 1
        assert data["statistics"]["successful_requests"] == 1
        assert data["statistics"]["failed_requests"] == 1

    def test_with_warnings_no_devices(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        prov = MagicMock()
        prov.devices = []
        prov.templates = {}
        prov.provision_requests = []
        prov.get_all_devices.return_value = []
        prov.get_supported_vendors.return_value = []
        prov.get_supported_models.return_value = []
        prov.get_request_history.return_value = []
        mock_pbx_core.phone_provisioning = prov
        # Make external_ip return "Not configured"
        mock_pbx_core.config.get.side_effect = lambda k, d=None: (
            "Not configured" if k == "server.external_ip" else d
        )

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/diagnostics")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data["warnings"]) > 0

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/diagnostics")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/provisioning/requests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProvisioningRequests:
    """Tests for GET /api/provisioning/requests."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        prov = MagicMock()
        prov.provision_requests = [{"success": True}]
        prov.get_request_history.return_value = [{"success": True}]
        mock_pbx_core.phone_provisioning = prov

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/requests")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total"] == 1

    def test_with_limit(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        prov = MagicMock()
        prov.provision_requests = []
        prov.get_request_history.return_value = []
        mock_pbx_core.phone_provisioning = prov

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/requests?limit=10")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["limit"] == 10

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/provisioning/requests")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/registered-phones
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRegisteredPhones:
    """Tests for GET /api/registered-phones."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.list_all.return_value = [
            {"extension_number": "1001", "ip_address": "192.168.1.50"}
        ]

        resp = api_client.get("/api/registered-phones")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1

    def test_no_database(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = None

        resp = api_client.get("/api/registered-phones")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []

    def test_database_error(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.list_all.side_effect = RuntimeError("db error")

        resp = api_client.get("/api/registered-phones")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/registered-phones/with-mac
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRegisteredPhonesWithMac:
    """Tests for GET /api/registered-phones/with-mac."""

    def test_success_with_provisioning_data(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        device = _make_device_mock(extension_number="1001")
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.list_all.return_value = [
            {"extension_number": "1001", "ip_address": "192.168.1.50"}
        ]
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.get_all_devices.return_value = [device]

        resp = api_client.get("/api/registered-phones/with-mac")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]["mac_source"] == "provisioning"
        assert data[0]["mac_address"] == "AA:BB:CC:DD:EE:FF"

    def test_with_existing_mac_from_sip(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.list_all.return_value = [
            {"extension_number": "1001", "mac_address": "11:22:33:44:55:66"}
        ]
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        resp = api_client.get("/api/registered-phones/with-mac")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data[0]["mac_source"] == "sip_registration"

    def test_no_pbx_core(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch("pbx.api.routes.provisioning.get_pbx_core", return_value=None):
            resp = api_client.get("/api/registered-phones/with-mac")
        assert resp.status_code == 500

    def test_no_database(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = None
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        resp = api_client.get("/api/registered-phones/with-mac")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []


# ---------------------------------------------------------------------------
# GET /api/registered-phones/extension/<number>
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRegisteredPhonesByExtension:
    """Tests for GET /api/registered-phones/extension/<number>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.get_by_extension.return_value = [
            {"extension_number": "1001", "ip_address": "192.168.1.50"}
        ]

        resp = api_client.get("/api/registered-phones/extension/1001")
        assert resp.status_code == 200

    def test_no_database(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = None

        resp = api_client.get("/api/registered-phones/extension/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []

    def test_database_error(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.get_by_extension.side_effect = RuntimeError("err")

        resp = api_client.get("/api/registered-phones/extension/1001")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /provision/<mac>.cfg
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProvisioningRequest:
    """Tests for GET /provision/<mac>.cfg."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        prov = MagicMock()
        prov.generate_config.return_value = ("<config/>", "text/xml")
        device = _make_device_mock()
        prov.get_device.return_value = device
        mock_pbx_core.phone_provisioning = prov
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.register_phone.return_value = (True, "AABBCCDDEEFF")

        with patch(
            "pbx.api.routes.provisioning.normalize_mac_address", return_value="AABBCCDDEEFF"
        ):
            resp = api_client.get("/provision/AABBCCDDEEFF.cfg")
        assert resp.status_code == 200
        assert b"<config/>" in resp.data

    def test_mac_placeholder_detected(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        resp = api_client.get("/provision/{mac}.cfg")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "placeholder" in data["error"].lower()

    def test_mac_placeholder_yealink_user_agent(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        resp = api_client.get("/provision/{mac}.cfg", headers={"User-Agent": "Yealink SIP-T54W"})
        assert resp.status_code == 400

    def test_mac_placeholder_cisco_user_agent(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        resp = api_client.get("/provision/{mac}.cfg", headers={"User-Agent": "Cisco SPA504G"})
        assert resp.status_code == 400

    def test_mac_placeholder_polycom_user_agent(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        resp = api_client.get("/provision/{mac}.cfg", headers={"User-Agent": "Polycom VVX-300"})
        assert resp.status_code == 400

    def test_mac_placeholder_grandstream_user_agent(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        resp = api_client.get("/provision/{mac}.cfg", headers={"User-Agent": "Grandstream GXP2170"})
        assert resp.status_code == 400

    def test_mac_placeholder_zultys_user_agent(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        resp = api_client.get("/provision/{mac}.cfg", headers={"User-Agent": "Zultys ZIP36G"})
        assert resp.status_code == 400

    def test_mac_placeholder_unknown_user_agent(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        resp = api_client.get("/provision/{mac}.cfg", headers={"User-Agent": "UnknownPhoneBrand"})
        assert resp.status_code == 400

    def test_device_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.generate_config.return_value = (None, None)

        resp = api_client.get("/provision/AABBCCDDEEFF.cfg")
        assert resp.status_code == 404

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        resp = api_client.get("/provision/AABBCCDDEEFF.cfg")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.generate_config.side_effect = ValueError("fail")

        resp = api_client.get("/provision/AABBCCDDEEFF.cfg")
        assert resp.status_code == 500

    def test_success_no_registered_phones_db(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        prov = MagicMock()
        prov.generate_config.return_value = ("<config/>", "text/xml")
        mock_pbx_core.phone_provisioning = prov
        mock_pbx_core.registered_phones_db = None

        resp = api_client.get("/provision/AABBCCDDEEFF.cfg")
        assert resp.status_code == 200

    def test_success_db_register_fails(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        prov = MagicMock()
        prov.generate_config.return_value = ("<config/>", "text/xml")
        prov.get_device.return_value = _make_device_mock()
        mock_pbx_core.phone_provisioning = prov
        mock_pbx_core.registered_phones_db = MagicMock()
        mock_pbx_core.registered_phones_db.register_phone.side_effect = ValueError("db fail")

        with patch(
            "pbx.api.routes.provisioning.normalize_mac_address", return_value="AABBCCDDEEFF"
        ):
            resp = api_client.get("/provision/AABBCCDDEEFF.cfg")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /provision/<name>.cfg — common config files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCommonConfigRequest:
    """Tests for fleet-wide common config file requests (Zultys/Yealink boot sequence)."""

    def test_zultys_zip37g_common(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        resp = api_client.get("/provision/zip37g_common.cfg")
        assert resp.status_code == 200
        assert b"#!version:1.0.0.1" in resp.data
        # Should NOT call generate_config for common files
        mock_pbx_core.phone_provisioning.generate_config.assert_not_called()

    def test_zultys_zip33g_common(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        resp = api_client.get("/provision/zip33g_common.cfg")
        assert resp.status_code == 200
        assert b"#!version:1.0.0.1" in resp.data

    def test_zultys_zip33i_common(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        resp = api_client.get("/provision/zip33i_common.cfg")
        assert resp.status_code == 200

    def test_yealink_universal_common(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        resp = api_client.get("/provision/y000000000000.cfg")
        assert resp.status_code == 200
        assert b"#!version:1.0.0.1" in resp.data

    def test_yealink_model_common(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        # y000000000028 is the T46G model-common config
        mock_pbx_core.phone_provisioning = MagicMock()
        resp = api_client.get("/provision/y000000000028.cfg")
        assert resp.status_code == 200

    def test_real_mac_not_treated_as_common(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """Ensure actual MAC addresses are not caught by common config detection."""
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.generate_config.return_value = (None, None)
        resp = api_client.get("/provision/000bea85bc14.cfg")
        # Should fall through to normal MAC handling (404 because device not registered)
        assert resp.status_code == 404
        mock_pbx_core.phone_provisioning.generate_config.assert_called_once()


# ---------------------------------------------------------------------------
# GET /provision/<name>.boot — boot files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBootFileRequest:
    """Tests for Yealink/Zultys boot file requests."""

    def test_universal_boot_file(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        resp = api_client.get("/provision/y000000000000.boot")
        assert resp.status_code == 200

    def test_mac_boot_file(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        resp = api_client.get("/provision/000bea85bc14.boot")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/provisioning/devices
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisterDevice:
    """Tests for POST /api/provisioning/devices."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        device = _make_device_mock()
        prov = MagicMock()
        prov.register_device.return_value = device
        prov.reboot_phone.return_value = True
        mock_pbx_core.phone_provisioning = prov

        ext = MagicMock()
        ext.registered = True
        mock_pbx_core.extension_registry.get.return_value = ext

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices",
                data=json.dumps(
                    {
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                        "extension_number": "1001",
                        "vendor": "yealink",
                        "model": "t54w",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert data["reboot_triggered"] is True

    def test_success_no_reboot(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        device = _make_device_mock()
        prov = MagicMock()
        prov.register_device.return_value = device
        mock_pbx_core.phone_provisioning = prov
        mock_pbx_core.extension_registry.get.return_value = None

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices",
                data=json.dumps(
                    {
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                        "extension_number": "1001",
                        "vendor": "yealink",
                        "model": "t54w",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["reboot_triggered"] is False

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices",
                data=json.dumps({"mac_address": "AA:BB:CC:DD:EE:FF"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices",
                data=json.dumps(
                    {
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                        "extension_number": "1001",
                        "vendor": "yealink",
                        "model": "t54w",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_register_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.register_device.side_effect = ValueError("duplicate")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices",
                data=json.dumps(
                    {
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                        "extension_number": "1001",
                        "vendor": "yealink",
                        "model": "t54w",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_reboot_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        device = _make_device_mock()
        prov = MagicMock()
        prov.register_device.return_value = device
        prov.reboot_phone.side_effect = ValueError("reboot fail")
        mock_pbx_core.phone_provisioning = prov

        ext = MagicMock()
        ext.registered = True
        mock_pbx_core.extension_registry.get.return_value = ext

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices",
                data=json.dumps(
                    {
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                        "extension_number": "1001",
                        "vendor": "yealink",
                        "model": "t54w",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["reboot_triggered"] is False


# ---------------------------------------------------------------------------
# POST /api/provisioning/templates/<vendor>/<model>/export
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportTemplate:
    """Tests for POST /api/provisioning/templates/<vendor>/<model>/export."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.export_template_to_file.return_value = (
            True,
            "Exported",
            "/tmp/template.cfg",
        )

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post("/api/provisioning/templates/yealink/t54w/export")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True

    def test_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.export_template_to_file.return_value = (
            False,
            "Not found",
            None,
        )

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post("/api/provisioning/templates/yealink/t54w/export")
        assert resp.status_code == 404

    def test_invalid_vendor(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post("/api/provisioning/templates/INVALID!/t54w/export")
        assert resp.status_code == 400

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post("/api/provisioning/templates/yealink/t54w/export")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/provisioning/reload-templates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReloadTemplates:
    """Tests for POST /api/provisioning/reload-templates."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.reload_templates.return_value = (
            True,
            "Reloaded",
            {"loaded": 5},
        )

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post("/api/provisioning/reload-templates")
        assert resp.status_code == 200

    def test_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.reload_templates.return_value = (
            False,
            "Error loading",
            {},
        )

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post("/api/provisioning/reload-templates")
        assert resp.status_code == 500

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post("/api/provisioning/reload-templates")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/provisioning/devices/<mac>/static-ip
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSetStaticIp:
    """Tests for POST /api/provisioning/devices/<mac>/static-ip."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.set_static_ip.return_value = (True, "IP set")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices/AABBCCDDEEFF/static-ip",
                data=json.dumps({"static_ip": "192.168.1.100"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.set_static_ip.return_value = (False, "Invalid IP")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices/AABBCCDDEEFF/static-ip",
                data=json.dumps({"static_ip": "bad"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_missing_field(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices/AABBCCDDEEFF/static-ip",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices/AABBCCDDEEFF/static-ip",
                data=json.dumps({"static_ip": "192.168.1.100"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.set_static_ip.side_effect = ValueError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/provisioning/devices/AABBCCDDEEFF/static-ip",
                data=json.dumps({"static_ip": "192.168.1.100"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# PUT /api/provisioning/templates/<vendor>/<model>
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateTemplate:
    """Tests for PUT /api/provisioning/templates/<vendor>/<model>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.update_template.return_value = (True, "Updated")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/provisioning/templates/yealink/t54w",
                data=json.dumps({"content": "<config>new</config>"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.update_template.return_value = (False, "Error")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/provisioning/templates/yealink/t54w",
                data=json.dumps({"content": "<config>new</config>"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_missing_content(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/provisioning/templates/yealink/t54w",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_invalid_vendor(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/provisioning/templates/INVALID!/t54w",
                data=json.dumps({"content": "x"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/provisioning/templates/yealink/t54w",
                data=json.dumps({"content": "<config/>"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.update_template.side_effect = TypeError("bad")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/provisioning/templates/yealink/t54w",
                data=json.dumps({"content": "x"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /api/provisioning/devices/<mac>
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnregisterDevice:
    """Tests for DELETE /api/provisioning/devices/<mac>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.unregister_device.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/provisioning/devices/AABBCCDDEEFF")
        assert resp.status_code == 200

    def test_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.unregister_device.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/provisioning/devices/AABBCCDDEEFF")
        assert resp.status_code == 404

    def test_not_enabled(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "phone_provisioning"):
            del mock_pbx_core.phone_provisioning

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/provisioning/devices/AABBCCDDEEFF")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.phone_provisioning = MagicMock()
        mock_pbx_core.phone_provisioning.unregister_device.side_effect = RuntimeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/provisioning/devices/AABBCCDDEEFF")
        assert resp.status_code == 500
