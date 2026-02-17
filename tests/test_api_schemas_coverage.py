"""Comprehensive tests for API Pydantic schemas (extensions, auth, common, config, provisioning)."""

from typing import Any

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Extension Schemas
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtensionCreate:
    """Tests for ExtensionCreate schema validation."""

    def test_valid_extension_create(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        ext = ExtensionCreate(
            extension="1001",
            name="Alice",
            password="secret123",
        )
        assert ext.extension == "1001"
        assert ext.name == "Alice"
        assert ext.password == "secret123"
        assert ext.email is None
        assert ext.voicemail_enabled is True
        assert ext.voicemail_pin is None
        assert ext.is_admin is False

    def test_valid_extension_create_all_fields(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        ext = ExtensionCreate(
            extension="2001",
            name="Bob",
            password="pass1234",
            email="bob@example.com",
            voicemail_enabled=False,
            voicemail_pin="5678",
            is_admin=True,
        )
        assert ext.email == "bob@example.com"
        assert ext.voicemail_enabled is False
        assert ext.voicemail_pin == "5678"
        assert ext.is_admin is True

    def test_extension_must_be_digits(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError) as exc_info:
            ExtensionCreate(extension="abc", name="Test", password="pass")
        errors = exc_info.value.errors()
        assert any("digits" in str(e["msg"]).lower() for e in errors)

    def test_extension_cannot_be_empty(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate(extension="", name="Test", password="pass")

    def test_extension_too_long(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate(
                extension="1" * 21,
                name="Test",
                password="pass",
            )

    def test_name_cannot_be_empty(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate(extension="1001", name="", password="pass")

    def test_name_too_long(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate(
                extension="1001",
                name="A" * 101,
                password="pass",
            )

    def test_password_too_short(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate(extension="1001", name="Test", password="abc")

    def test_voicemail_pin_must_be_digits(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError) as exc_info:
            ExtensionCreate(
                extension="1001",
                name="Test",
                password="pass1234",
                voicemail_pin="abcd",
            )
        errors = exc_info.value.errors()
        assert any(
            "pin" in str(e["msg"]).lower() or "digits" in str(e["msg"]).lower() for e in errors
        )

    def test_voicemail_pin_too_short(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate(
                extension="1001",
                name="Test",
                password="pass1234",
                voicemail_pin="12",
            )

    def test_voicemail_pin_too_long(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate(
                extension="1001",
                name="Test",
                password="pass1234",
                voicemail_pin="1" * 11,
            )

    def test_voicemail_pin_none_is_valid(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        ext = ExtensionCreate(
            extension="1001",
            name="Test",
            password="pass1234",
            voicemail_pin=None,
        )
        assert ext.voicemail_pin is None

    def test_email_too_long(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate(
                extension="1001",
                name="Test",
                password="pass1234",
                email="a" * 256,
            )

    def test_missing_required_fields(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        with pytest.raises(ValidationError):
            ExtensionCreate()  # type: ignore[call-arg]


@pytest.mark.unit
class TestExtensionUpdate:
    """Tests for ExtensionUpdate schema validation."""

    def test_valid_all_none(self) -> None:
        from pbx.api.schemas.extensions import ExtensionUpdate

        update = ExtensionUpdate()
        assert update.name is None
        assert update.password is None
        assert update.email is None
        assert update.voicemail_enabled is None

    def test_valid_partial_update(self) -> None:
        from pbx.api.schemas.extensions import ExtensionUpdate

        update = ExtensionUpdate(name="New Name", dnd_enabled=True)
        assert update.name == "New Name"
        assert update.dnd_enabled is True
        assert update.password is None

    def test_valid_all_fields(self) -> None:
        from pbx.api.schemas.extensions import ExtensionUpdate

        update = ExtensionUpdate(
            name="Updated",
            password="newpass",
            email="new@example.com",
            voicemail_enabled=True,
            voicemail_pin="9999",
            is_admin=True,
            caller_id="Updated Caller",
            dnd_enabled=False,
            forward_enabled=True,
            forward_destination="5551234",
        )
        assert update.name == "Updated"
        assert update.forward_destination == "5551234"

    def test_name_too_long(self) -> None:
        from pbx.api.schemas.extensions import ExtensionUpdate

        with pytest.raises(ValidationError):
            ExtensionUpdate(name="A" * 101)

    def test_password_too_short(self) -> None:
        from pbx.api.schemas.extensions import ExtensionUpdate

        with pytest.raises(ValidationError):
            ExtensionUpdate(password="ab")

    def test_caller_id_too_long(self) -> None:
        from pbx.api.schemas.extensions import ExtensionUpdate

        with pytest.raises(ValidationError):
            ExtensionUpdate(caller_id="C" * 101)

    def test_forward_destination_too_long(self) -> None:
        from pbx.api.schemas.extensions import ExtensionUpdate

        with pytest.raises(ValidationError):
            ExtensionUpdate(forward_destination="1" * 21)


@pytest.mark.unit
class TestExtensionResponse:
    """Tests for ExtensionResponse schema."""

    def test_valid_minimal(self) -> None:
        from pbx.api.schemas.extensions import ExtensionResponse

        resp = ExtensionResponse(extension="1001", name="Alice")
        assert resp.extension == "1001"
        assert resp.name == "Alice"
        assert resp.registered is False
        assert resp.voicemail_enabled is True
        assert resp.is_admin is False
        assert resp.dnd_enabled is False
        assert resp.forward_enabled is False

    def test_valid_all_fields(self) -> None:
        from pbx.api.schemas.extensions import ExtensionResponse

        resp = ExtensionResponse(
            extension="2001",
            name="Bob",
            email="bob@example.com",
            registered=True,
            voicemail_enabled=False,
            is_admin=True,
            caller_id="Bob Line",
            dnd_enabled=True,
            forward_enabled=True,
            forward_destination="5551234",
        )
        assert resp.registered is True
        assert resp.caller_id == "Bob Line"

    def test_missing_required_fields(self) -> None:
        from pbx.api.schemas.extensions import ExtensionResponse

        with pytest.raises(ValidationError):
            ExtensionResponse()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoginRequest:
    """Tests for LoginRequest schema validation."""

    def test_valid_login(self) -> None:
        from pbx.api.schemas.auth import LoginRequest

        req = LoginRequest(extension="1001", password="secret")
        assert req.extension == "1001"
        assert req.password == "secret"

    def test_extension_must_be_digits(self) -> None:
        from pbx.api.schemas.auth import LoginRequest

        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(extension="abc", password="secret")
        errors = exc_info.value.errors()
        assert any("digits" in str(e["msg"]).lower() for e in errors)

    def test_extension_cannot_be_empty(self) -> None:
        from pbx.api.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(extension="", password="secret")

    def test_extension_too_long(self) -> None:
        from pbx.api.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(extension="1" * 21, password="secret")

    def test_password_cannot_be_empty(self) -> None:
        from pbx.api.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(extension="1001", password="")

    def test_missing_fields(self) -> None:
        from pbx.api.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest()  # type: ignore[call-arg]


@pytest.mark.unit
class TestLoginResponse:
    """Tests for LoginResponse schema."""

    def test_valid_response(self) -> None:
        from pbx.api.schemas.auth import LoginResponse

        resp = LoginResponse(token="abc123", extension="1001")
        assert resp.token == "abc123"
        assert resp.extension == "1001"
        assert resp.name is None
        assert resp.is_admin is False
        assert resp.expires_in == 86400

    def test_valid_response_all_fields(self) -> None:
        from pbx.api.schemas.auth import LoginResponse

        resp = LoginResponse(
            token="xyz",
            extension="1001",
            name="Alice",
            is_admin=True,
            expires_in=3600,
        )
        assert resp.name == "Alice"
        assert resp.is_admin is True
        assert resp.expires_in == 3600

    def test_missing_required_fields(self) -> None:
        from pbx.api.schemas.auth import LoginResponse

        with pytest.raises(ValidationError):
            LoginResponse()  # type: ignore[call-arg]


@pytest.mark.unit
class TestLogoutResponse:
    """Tests for LogoutResponse schema."""

    def test_default_values(self) -> None:
        from pbx.api.schemas.auth import LogoutResponse

        resp = LogoutResponse()
        assert resp.success is True
        assert resp.message == "Logged out successfully"

    def test_custom_values(self) -> None:
        from pbx.api.schemas.auth import LogoutResponse

        resp = LogoutResponse(success=False, message="Session expired")
        assert resp.success is False
        assert resp.message == "Session expired"


# ---------------------------------------------------------------------------
# Common Schemas
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorDetail:
    """Tests for ErrorDetail schema."""

    def test_valid_error_detail(self) -> None:
        from pbx.api.schemas.common import ErrorDetail

        detail = ErrorDetail(code="NOT_FOUND", message="Resource not found", status=404)
        assert detail.code == "NOT_FOUND"
        assert detail.message == "Resource not found"
        assert detail.status == 404

    def test_missing_required_fields(self) -> None:
        from pbx.api.schemas.common import ErrorDetail

        with pytest.raises(ValidationError):
            ErrorDetail()  # type: ignore[call-arg]


@pytest.mark.unit
class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_valid_error_response(self) -> None:
        from pbx.api.schemas.common import ErrorDetail, ErrorResponse

        error = ErrorDetail(code="SERVER_ERROR", message="Internal error", status=500)
        resp = ErrorResponse(error=error)
        assert resp.error.code == "SERVER_ERROR"
        assert resp.error.status == 500

    def test_missing_error(self) -> None:
        from pbx.api.schemas.common import ErrorResponse

        with pytest.raises(ValidationError):
            ErrorResponse()  # type: ignore[call-arg]


@pytest.mark.unit
class TestSuccessResponse:
    """Tests for SuccessResponse schema."""

    def test_default_values(self) -> None:
        from pbx.api.schemas.common import SuccessResponse

        resp = SuccessResponse()
        assert resp.success is True
        assert resp.message is None

    def test_with_message(self) -> None:
        from pbx.api.schemas.common import SuccessResponse

        resp = SuccessResponse(message="Done")
        assert resp.success is True
        assert resp.message == "Done"

    def test_custom_success_false(self) -> None:
        from pbx.api.schemas.common import SuccessResponse

        resp = SuccessResponse(success=False, message="Failed")
        assert resp.success is False


@pytest.mark.unit
class TestPaginatedResponse:
    """Tests for PaginatedResponse schema."""

    def test_default_values(self) -> None:
        from pbx.api.schemas.common import PaginatedResponse

        resp = PaginatedResponse()
        assert resp.items == []
        assert resp.total == 0
        assert resp.limit == 50
        assert resp.offset == 0
        assert resp.has_more is False

    def test_custom_values(self) -> None:
        from pbx.api.schemas.common import PaginatedResponse

        resp = PaginatedResponse(
            items=["a", "b", "c"],
            total=100,
            limit=3,
            offset=10,
            has_more=True,
        )
        assert len(resp.items) == 3
        assert resp.total == 100
        assert resp.has_more is True

    def test_empty_items_list(self) -> None:
        from pbx.api.schemas.common import PaginatedResponse

        resp = PaginatedResponse(items=[], total=0)
        assert resp.items == []
        assert resp.total == 0


# ---------------------------------------------------------------------------
# Config Schemas
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigUpdate:
    """Tests for ConfigUpdate schema."""

    def test_valid_config_update(self) -> None:
        from pbx.api.schemas.config import ConfigUpdate

        update = ConfigUpdate(section="sip", values={"port": 5060})
        assert update.section == "sip"
        assert update.values == {"port": 5060}

    def test_empty_values(self) -> None:
        from pbx.api.schemas.config import ConfigUpdate

        update = ConfigUpdate(section="rtp", values={})
        assert update.values == {}

    def test_missing_required_fields(self) -> None:
        from pbx.api.schemas.config import ConfigUpdate

        with pytest.raises(ValidationError):
            ConfigUpdate()  # type: ignore[call-arg]


@pytest.mark.unit
class TestSSLConfig:
    """Tests for SSLConfig schema."""

    def test_default_values(self) -> None:
        from pbx.api.schemas.config import SSLConfig

        ssl = SSLConfig()
        assert ssl.enabled is False
        assert ssl.cert_path is None
        assert ssl.key_path is None
        assert ssl.auto_generate is False

    def test_enabled_with_paths(self) -> None:
        from pbx.api.schemas.config import SSLConfig

        ssl = SSLConfig(
            enabled=True,
            cert_path="/etc/ssl/cert.pem",
            key_path="/etc/ssl/key.pem",
        )
        assert ssl.enabled is True
        assert ssl.cert_path == "/etc/ssl/cert.pem"

    def test_auto_generate(self) -> None:
        from pbx.api.schemas.config import SSLConfig

        ssl = SSLConfig(enabled=True, auto_generate=True)
        assert ssl.auto_generate is True


@pytest.mark.unit
class TestNetworkConfig:
    """Tests for NetworkConfig schema."""

    def test_default_values(self) -> None:
        from pbx.api.schemas.config import NetworkConfig

        net = NetworkConfig()
        assert net.sip_port == 5060
        assert net.rtp_port_start == 10000
        assert net.rtp_port_end == 20000
        assert net.api_port == 9000
        assert net.bind_address == "0.0.0.0"

    def test_custom_values(self) -> None:
        from pbx.api.schemas.config import NetworkConfig

        net = NetworkConfig(
            sip_port=5061,
            rtp_port_start=20000,
            rtp_port_end=30000,
            api_port=8080,
            bind_address="127.0.0.1",
        )
        assert net.sip_port == 5061
        assert net.bind_address == "127.0.0.1"

    def test_port_below_minimum(self) -> None:
        from pbx.api.schemas.config import NetworkConfig

        with pytest.raises(ValidationError):
            NetworkConfig(sip_port=80)

    def test_port_above_maximum(self) -> None:
        from pbx.api.schemas.config import NetworkConfig

        with pytest.raises(ValidationError):
            NetworkConfig(sip_port=70000)

    def test_rtp_port_end_must_be_greater_than_start(self) -> None:
        from pbx.api.schemas.config import NetworkConfig

        with pytest.raises(ValidationError) as exc_info:
            NetworkConfig(rtp_port_start=20000, rtp_port_end=10000)
        errors = exc_info.value.errors()
        assert any("greater" in str(e["msg"]).lower() for e in errors)

    def test_rtp_port_end_equal_to_start(self) -> None:
        from pbx.api.schemas.config import NetworkConfig

        with pytest.raises(ValidationError):
            NetworkConfig(rtp_port_start=15000, rtp_port_end=15000)

    def test_api_port_below_minimum(self) -> None:
        from pbx.api.schemas.config import NetworkConfig

        with pytest.raises(ValidationError):
            NetworkConfig(api_port=100)


# ---------------------------------------------------------------------------
# Provisioning Schemas
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProvisionDevice:
    """Tests for ProvisionDevice schema."""

    def test_valid_mac_with_colons(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        dev = ProvisionDevice(
            mac_address="AA:BB:CC:DD:EE:FF",
            model="Polycom VVX 450",
            extension="1001",
        )
        assert dev.mac_address == "AABBCCDDEEFF"

    def test_valid_mac_with_dashes(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        dev = ProvisionDevice(
            mac_address="AA-BB-CC-DD-EE-FF",
            model="Polycom VVX 450",
            extension="1001",
        )
        assert dev.mac_address == "AABBCCDDEEFF"

    def test_valid_mac_with_dots(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        dev = ProvisionDevice(
            mac_address="AABB.CCDD.EEFF",
            model="Polycom VVX 450",
            extension="1001",
        )
        assert dev.mac_address == "AABBCCDDEEFF"

    def test_valid_mac_raw(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        dev = ProvisionDevice(
            mac_address="aabbccddeeff",
            model="Polycom VVX 450",
            extension="1001",
        )
        assert dev.mac_address == "AABBCCDDEEFF"

    def test_valid_with_all_fields(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        dev = ProvisionDevice(
            mac_address="AABBCCDDEEFF",
            model="Polycom VVX 450",
            extension="1001",
            template="polycom_vvx",
            label="Lobby Phone",
        )
        assert dev.template == "polycom_vvx"
        assert dev.label == "Lobby Phone"

    def test_invalid_mac_address_short(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        with pytest.raises(ValidationError):
            ProvisionDevice(
                mac_address="AABB",
                model="Polycom",
                extension="1001",
            )

    def test_invalid_mac_address_chars(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        with pytest.raises(ValidationError) as exc_info:
            ProvisionDevice(
                mac_address="GGHHIIJJKKLL",
                model="Polycom",
                extension="1001",
            )
        errors = exc_info.value.errors()
        assert any(
            "mac" in str(e["msg"]).lower() or "invalid" in str(e["msg"]).lower() for e in errors
        )

    def test_model_cannot_be_empty(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        with pytest.raises(ValidationError):
            ProvisionDevice(
                mac_address="AABBCCDDEEFF",
                model="",
                extension="1001",
            )

    def test_extension_cannot_be_empty(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        with pytest.raises(ValidationError):
            ProvisionDevice(
                mac_address="AABBCCDDEEFF",
                model="Polycom",
                extension="",
            )

    def test_missing_required_fields(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        with pytest.raises(ValidationError):
            ProvisionDevice()  # type: ignore[call-arg]

    def test_label_too_long(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        with pytest.raises(ValidationError):
            ProvisionDevice(
                mac_address="AABBCCDDEEFF",
                model="Polycom",
                extension="1001",
                label="L" * 101,
            )


@pytest.mark.unit
class TestRegisterPhone:
    """Tests for RegisterPhone schema."""

    def test_valid_registration(self) -> None:
        from pbx.api.schemas.provisioning import RegisterPhone

        phone = RegisterPhone(
            mac_address="AABBCCDDEEFF",
            ip_address="192.168.1.100",
            extension="1001",
        )
        assert phone.mac_address == "AABBCCDDEEFF"
        assert phone.ip_address == "192.168.1.100"
        assert phone.extension == "1001"
        assert phone.model is None
        assert phone.firmware is None

    def test_valid_with_all_fields(self) -> None:
        from pbx.api.schemas.provisioning import RegisterPhone

        phone = RegisterPhone(
            mac_address="AABBCCDDEEFF",
            ip_address="192.168.1.100",
            extension="1001",
            model="VVX 450",
            firmware="5.9.6",
        )
        assert phone.model == "VVX 450"
        assert phone.firmware == "5.9.6"

    def test_missing_required_fields(self) -> None:
        from pbx.api.schemas.provisioning import RegisterPhone

        with pytest.raises(ValidationError):
            RegisterPhone()  # type: ignore[call-arg]

    def test_extension_too_long(self) -> None:
        from pbx.api.schemas.provisioning import RegisterPhone

        with pytest.raises(ValidationError):
            RegisterPhone(
                mac_address="AABBCCDDEEFF",
                ip_address="10.0.0.1",
                extension="1" * 21,
            )


@pytest.mark.unit
class TestProvisioningTemplate:
    """Tests for ProvisioningTemplate schema."""

    def test_valid_template(self) -> None:
        from pbx.api.schemas.provisioning import ProvisioningTemplate

        tmpl = ProvisioningTemplate(
            name="Polycom VVX",
            manufacturer="Polycom",
            template_content="<config>{{EXTENSION}}</config>",
        )
        assert tmpl.name == "Polycom VVX"
        assert tmpl.manufacturer == "Polycom"
        assert tmpl.model_pattern is None
        assert tmpl.content_type == "text/xml"

    def test_valid_with_all_fields(self) -> None:
        from pbx.api.schemas.provisioning import ProvisioningTemplate

        tmpl = ProvisioningTemplate(
            name="Grandstream GXP",
            manufacturer="Grandstream",
            model_pattern="GXP*",
            template_content="<cfg>content</cfg>",
            content_type="application/xml",
        )
        assert tmpl.model_pattern == "GXP*"
        assert tmpl.content_type == "application/xml"

    def test_missing_required_fields(self) -> None:
        from pbx.api.schemas.provisioning import ProvisioningTemplate

        with pytest.raises(ValidationError):
            ProvisioningTemplate()  # type: ignore[call-arg]

    def test_name_cannot_be_empty(self) -> None:
        from pbx.api.schemas.provisioning import ProvisioningTemplate

        with pytest.raises(ValidationError):
            ProvisioningTemplate(
                name="",
                manufacturer="Polycom",
                template_content="content",
            )

    def test_manufacturer_cannot_be_empty(self) -> None:
        from pbx.api.schemas.provisioning import ProvisioningTemplate

        with pytest.raises(ValidationError):
            ProvisioningTemplate(
                name="Test",
                manufacturer="",
                template_content="content",
            )

    def test_name_too_long(self) -> None:
        from pbx.api.schemas.provisioning import ProvisioningTemplate

        with pytest.raises(ValidationError):
            ProvisioningTemplate(
                name="N" * 101,
                manufacturer="Polycom",
                template_content="content",
            )

    def test_content_type_too_long(self) -> None:
        from pbx.api.schemas.provisioning import ProvisioningTemplate

        with pytest.raises(ValidationError):
            ProvisioningTemplate(
                name="Test",
                manufacturer="Polycom",
                template_content="content",
                content_type="x" * 51,
            )


# ---------------------------------------------------------------------------
# Schema Serialization Round-Trip Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSchemaRoundTrip:
    """Tests for serialization and deserialization round-trips."""

    def test_extension_create_model_dump(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        ext = ExtensionCreate(
            extension="1001",
            name="Alice",
            password="secret",
        )
        data = ext.model_dump()
        assert isinstance(data, dict)
        assert data["extension"] == "1001"
        assert "password" in data

    def test_extension_create_from_dict(self) -> None:
        from pbx.api.schemas.extensions import ExtensionCreate

        data: dict[str, Any] = {
            "extension": "2001",
            "name": "Bob",
            "password": "pass1234",
        }
        ext = ExtensionCreate(**data)
        assert ext.extension == "2001"

    def test_login_request_model_dump(self) -> None:
        from pbx.api.schemas.auth import LoginRequest

        req = LoginRequest(extension="1001", password="secret")
        data = req.model_dump()
        assert data["extension"] == "1001"
        assert data["password"] == "secret"

    def test_paginated_response_model_dump(self) -> None:
        from pbx.api.schemas.common import PaginatedResponse

        resp = PaginatedResponse(
            items=[1, 2, 3],
            total=100,
            limit=3,
            offset=0,
            has_more=True,
        )
        data = resp.model_dump()
        assert data["total"] == 100
        assert data["has_more"] is True

    def test_network_config_model_dump(self) -> None:
        from pbx.api.schemas.config import NetworkConfig

        net = NetworkConfig(sip_port=5061)
        data = net.model_dump()
        assert data["sip_port"] == 5061
        assert data["rtp_port_start"] == 10000

    def test_provision_device_model_dump(self) -> None:
        from pbx.api.schemas.provisioning import ProvisionDevice

        dev = ProvisionDevice(
            mac_address="AA:BB:CC:DD:EE:FF",
            model="Polycom",
            extension="1001",
        )
        data = dev.model_dump()
        assert data["mac_address"] == "AABBCCDDEEFF"
