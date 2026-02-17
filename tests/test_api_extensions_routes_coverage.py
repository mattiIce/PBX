"""Comprehensive tests for Extensions Blueprint routes."""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

AUTH_ADMIN = (True, {"extension": "1001", "is_admin": True})
AUTH_USER = (True, {"extension": "1001", "is_admin": False})
AUTH_NONE = (False, None)


def _make_extension_mock(
    number="1001",
    name="Test User",
    email="test@example.com",
    registered=True,
    allow_external=True,
    is_admin=False,
    voicemail_pin_hash="hashed",
    ad_synced=False,
):
    ext = MagicMock()
    ext.number = number
    ext.name = name
    ext.registered = registered
    ext.config = {
        "email": email,
        "allow_external": allow_external,
        "is_admin": is_admin,
        "voicemail_pin_hash": voicemail_pin_hash,
        "ad_synced": ad_synced,
    }
    return ext


# ---------------------------------------------------------------------------
# GET /api/extensions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetExtensions:
    """Tests for GET /api/extensions."""

    def test_admin_sees_all(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        ext1 = _make_extension_mock(number="1001", name="Alice")
        ext2 = _make_extension_mock(number="1002", name="Bob")
        mock_pbx_core.extension_registry.get_all.return_value = [ext1, ext2]

        with patch("pbx.api.routes.extensions.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/extensions")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 2

    def test_non_admin_sees_own(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        ext1 = _make_extension_mock(number="1001", name="Alice")
        ext2 = _make_extension_mock(number="1002", name="Bob")
        mock_pbx_core.extension_registry.get_all.return_value = [ext1, ext2]

        with patch("pbx.api.routes.extensions.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/extensions")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]["number"] == "1001"

    def test_unauthenticated(self, api_client: FlaskClient) -> None:
        with patch("pbx.api.routes.extensions.verify_authentication", return_value=AUTH_NONE):
            resp = api_client.get("/api/extensions")
        assert resp.status_code == 401

    def test_pbx_not_initialized(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with (
            patch("pbx.api.routes.extensions.get_pbx_core", return_value=None),
            patch("pbx.api.routes.extensions.verify_authentication", return_value=AUTH_ADMIN),
        ):
            resp = api_client.get("/api/extensions")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get_all.side_effect = ValueError("error")

        with patch("pbx.api.routes.extensions.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.get("/api/extensions")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/extensions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAddExtension:
    """Tests for POST /api/extensions."""

    def test_success_with_db(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core.extension_db = MagicMock()
        mock_pbx_core.extension_db.add.return_value = True

        with (
            patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN),
            patch("pbx.utils.config.Config.validate_email", return_value=True),
        ):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "New User",
                        "email": "new@example.com",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                        "is_admin": False,
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True

    def test_success_with_config_fallback(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core.extension_db = None
        mock_pbx_core.config.add_extension.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "New User",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_missing_required_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps({"number": "1002"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_missing_voicemail_pin(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "User",
                        "password": "securepass123",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "voicemail" in data["error"].lower()

    def test_invalid_voicemail_pin(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "User",
                        "password": "securepass123",
                        "voicemail_pin": "ab",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_invalid_extension_number(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "12",
                        "name": "User",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_short_password(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "User",
                        "password": "short",
                        "voicemail_pin": "1234",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_invalid_email(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with (
            patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN),
            patch("pbx.utils.config.Config.validate_email", return_value=False),
        ):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "User",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                        "email": "bad-email",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_extension_already_exists(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1001",
                        "name": "User",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_add_fails(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = None
        mock_pbx_core.extension_db = MagicMock()
        mock_pbx_core.extension_db.add.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "User",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_pbx_not_initialized(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with (
            patch("pbx.api.routes.extensions.get_pbx_core", return_value=None),
            patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN),
        ):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "User",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_non_admin(self, api_client: FlaskClient) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "User",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 403

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.side_effect = ValueError("error")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/extensions",
                data=json.dumps(
                    {
                        "number": "1002",
                        "name": "User",
                        "password": "securepass123",
                        "voicemail_pin": "1234",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# PUT /api/extensions/<number>
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateExtension:
    """Tests for PUT /api/extensions/<number>."""

    def test_success_with_db(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()
        mock_pbx_core.extension_db = MagicMock()
        mock_pbx_core.extension_db.update.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/extensions/1001",
                data=json.dumps({"name": "Updated Name"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_success_with_config_fallback(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()
        mock_pbx_core.extension_db = None
        mock_pbx_core.config.update_extension.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/extensions/1001",
                data=json.dumps({"name": "Updated Name"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_extension_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = None

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/extensions/9999",
                data=json.dumps({"name": "New Name"}),
                content_type="application/json",
            )
        assert resp.status_code == 404

    def test_invalid_password(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/extensions/1001",
                data=json.dumps({"password": "short"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_invalid_voicemail_pin(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/extensions/1001",
                data=json.dumps({"voicemail_pin": "ab"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_invalid_email(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()

        with (
            patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN),
            patch("pbx.utils.config.Config.validate_email", return_value=False),
        ):
            resp = api_client.put(
                "/api/extensions/1001",
                data=json.dumps({"email": "bad-email"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_update_fails(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()
        mock_pbx_core.extension_db = MagicMock()
        mock_pbx_core.extension_db.update.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/extensions/1001",
                data=json.dumps({"name": "Updated Name"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_pbx_not_initialized(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with (
            patch("pbx.api.routes.extensions.get_pbx_core", return_value=None),
            patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN),
        ):
            resp = api_client.put(
                "/api/extensions/1001",
                data=json.dumps({"name": "Updated"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.side_effect = TypeError("error")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.put(
                "/api/extensions/1001",
                data=json.dumps({"name": "New"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /api/extensions/<number>
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeleteExtension:
    """Tests for DELETE /api/extensions/<number>."""

    def test_success_with_db(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()
        mock_pbx_core.extension_db = MagicMock()
        mock_pbx_core.extension_db.delete.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/extensions/1001")
        assert resp.status_code == 200

    def test_success_with_config_fallback(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()
        mock_pbx_core.extension_db = None
        mock_pbx_core.config.delete_extension.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/extensions/1001")
        assert resp.status_code == 200

    def test_extension_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = None

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/extensions/9999")
        assert resp.status_code == 404

    def test_delete_fails(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.return_value = _make_extension_mock()
        mock_pbx_core.extension_db = MagicMock()
        mock_pbx_core.extension_db.delete.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/extensions/1001")
        assert resp.status_code == 500

    def test_pbx_not_initialized(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        with (
            patch("pbx.api.routes.extensions.get_pbx_core", return_value=None),
            patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN),
        ):
            resp = api_client.delete("/api/extensions/1001")
        assert resp.status_code == 500

    def test_non_admin(self, api_client: FlaskClient) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.delete("/api/extensions/1001")
        assert resp.status_code == 403

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.extension_registry.get.side_effect = KeyError("error")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.delete("/api/extensions/1001")
        assert resp.status_code == 500
