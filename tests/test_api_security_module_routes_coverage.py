"""Comprehensive tests for Security Blueprint routes (hot-desking, MFA, threat, DND)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

AUTH_ADMIN = (True, {"extension": "1001", "is_admin": True})
AUTH_USER = (True, {"extension": "1001", "is_admin": False})
AUTH_NONE = (False, None)


# ---------------------------------------------------------------------------
# Hot-Desking routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetHotDeskSessions:
    """Tests for GET /api/hot-desk/sessions."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.get_active_sessions.return_value = [
            {"device_id": "dev1", "extension": "1001"}
        ]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/sessions")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["count"] == 1

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/sessions")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.get_active_sessions.side_effect = RuntimeError("boom")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/sessions")
        assert resp.status_code == 500

    def test_unauthenticated(self, api_client: FlaskClient) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_NONE):
            resp = api_client.get("/api/hot-desk/sessions")
        assert resp.status_code == 401


@pytest.mark.unit
class TestGetHotDeskSession:
    """Tests for GET /api/hot-desk/session/<device_id>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        session_mock = MagicMock()
        session_mock.to_dict.return_value = {"device_id": "dev1", "extension": "1001"}
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.get_session.return_value = session_mock

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/session/dev1")
        assert resp.status_code == 200

    def test_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.get_session.return_value = None

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/session/dev1")
        assert resp.status_code == 404

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/session/dev1")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.get_session.side_effect = RuntimeError("boom")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/session/dev1")
        assert resp.status_code == 500


@pytest.mark.unit
class TestGetHotDeskExtension:
    """Tests for GET /api/hot-desk/extension/<extension>."""

    def test_success_logged_in(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        session_mock = MagicMock()
        session_mock.to_dict.return_value = {"device_id": "dev1", "extension": "1001"}
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.get_extension_devices.return_value = ["dev1"]
        mock_pbx_core.hot_desking.get_session.return_value = session_mock

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/extension/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["logged_in"] is True
        assert data["device_count"] == 1

    def test_not_logged_in(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.get_extension_devices.return_value = []

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/extension/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["logged_in"] is False

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/extension/1001")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.get_extension_devices.side_effect = RuntimeError("boom")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/hot-desk/extension/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestHotDeskLogin:
    """Tests for POST /api/hot-desk/login."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.login.return_value = True
        mock_pbx_core.hot_desking.get_extension_profile.return_value = {"name": "John"}

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({"extension": "1001", "device_id": "dev1", "pin": "1234"}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True

    def test_login_failed(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.login.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({"extension": "1001", "device_id": "dev1"}),
                content_type="application/json",
            )
        assert resp.status_code == 401

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({"extension": "1001", "device_id": "dev1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.login.side_effect = ValueError("bad")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({"extension": "1001", "device_id": "dev1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestHotDeskLogout:
    """Tests for POST /api/hot-desk/logout."""

    def test_logout_by_device_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.logout.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"device_id": "dev1"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_logout_by_device_no_session(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.logout.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"device_id": "dev1"}),
                content_type="application/json",
            )
        assert resp.status_code == 404

    def test_logout_by_extension(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.logout_extension.return_value = 2

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"device_id": "dev1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.hot_desking = MagicMock()
        mock_pbx_core.hot_desking.logout.side_effect = ValueError("boom")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"device_id": "dev1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# MFA routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMfaStatus:
    """Tests for GET /api/mfa/status/<extension>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.is_enabled_for_user.return_value = True
        mock_pbx_core.mfa_manager.required = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/mfa/status/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["mfa_enabled"] is True

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/mfa/status/1001")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.is_enabled_for_user.side_effect = RuntimeError("boom")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/mfa/status/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestGetMfaMethods:
    """Tests for GET /api/mfa/methods/<extension>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.get_enrolled_methods.return_value = ["totp"]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/mfa/methods/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["methods"] == ["totp"]

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/mfa/methods/1001")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.get_enrolled_methods.side_effect = RuntimeError("boom")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/mfa/methods/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestMfaEnroll:
    """Tests for POST /api/mfa/enroll."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.enroll_user.return_value = (
            True,
            "otpauth://totp/...",
            ["code1", "code2"],
        )

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "provisioning_uri" in data

    def test_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.enroll_user.return_value = (False, None, None)

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_missing_extension(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.enroll_user.side_effect = ValueError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestMfaVerifyEnrollment:
    """Tests for POST /api/mfa/verify-enrollment."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.verify_enrollment.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify-enrollment",
                data=json.dumps({"extension": "1001", "code": "123456"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_invalid_code(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.verify_enrollment.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify-enrollment",
                data=json.dumps({"extension": "1001", "code": "000000"}),
                content_type="application/json",
            )
        assert resp.status_code == 401

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify-enrollment",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify-enrollment",
                data=json.dumps({"extension": "1001", "code": "123456"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.verify_enrollment.side_effect = TypeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify-enrollment",
                data=json.dumps({"extension": "1001", "code": "123456"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestMfaVerify:
    """Tests for POST /api/mfa/verify."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.verify_code.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify",
                data=json.dumps({"extension": "1001", "code": "123456"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_invalid_code(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.verify_code.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify",
                data=json.dumps({"extension": "1001", "code": "000000"}),
                content_type="application/json",
            )
        assert resp.status_code == 401

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/verify",
                data=json.dumps({"extension": "1001", "code": "123456"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestMfaDisable:
    """Tests for POST /api/mfa/disable."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.disable_for_user.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/disable",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.disable_for_user.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/disable",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_missing_extension(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/disable",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/disable",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.disable_for_user.side_effect = ValueError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/disable",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestMfaEnrollYubikey:
    """Tests for POST /api/mfa/enroll-yubikey."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.enroll_yubikey.return_value = (True, None)

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-yubikey",
                data=json.dumps({"extension": "1001", "otp": "ccccccc...", "device_name": "MyKey"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.enroll_yubikey.return_value = (False, "Invalid OTP")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-yubikey",
                data=json.dumps({"extension": "1001", "otp": "bad"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-yubikey",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-yubikey",
                data=json.dumps({"extension": "1001", "otp": "otp"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.enroll_yubikey.side_effect = KeyError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-yubikey",
                data=json.dumps({"extension": "1001", "otp": "otp"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestMfaEnrollFido2:
    """Tests for POST /api/mfa/enroll-fido2."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.enroll_fido2.return_value = (True, None)

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-fido2",
                data=json.dumps(
                    {
                        "extension": "1001",
                        "credential_data": {"id": "abc"},
                        "device_name": "Key1",
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_failure(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()
        mock_pbx_core.mfa_manager.enroll_fido2.return_value = (False, "Invalid credential")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-fido2",
                data=json.dumps({"extension": "1001", "credential_data": {"id": "abc"}}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.mfa_manager = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-fido2",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/mfa/enroll-fido2",
                data=json.dumps({"extension": "1001", "credential_data": {"id": "abc"}}),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Threat Detection / Security routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetThreatSummary:
    """Tests for GET /api/security/threat-summary."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()
        mock_pbx_core.threat_detector.get_threat_summary.return_value = {
            "total_threats": 5,
            "blocked_ips": 3,
        }

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/threat-summary")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total_threats"] == 5

    def test_with_hours_param(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()
        mock_pbx_core.threat_detector.get_threat_summary.return_value = {}

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/threat-summary?hours=48")
        assert resp.status_code == 200
        mock_pbx_core.threat_detector.get_threat_summary.assert_called_with(48)

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "threat_detector"):
            del mock_pbx_core.threat_detector

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/threat-summary")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()
        mock_pbx_core.threat_detector.get_threat_summary.side_effect = ValueError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/threat-summary")
        assert resp.status_code == 500


@pytest.mark.unit
class TestGetSecurityComplianceStatus:
    """Tests for GET /api/security/compliance-status."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.security_monitor = MagicMock()
        mock_pbx_core.security_monitor.get_compliance_status.return_value = {"fips": True}

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/compliance-status")
        assert resp.status_code == 200

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "security_monitor"):
            del mock_pbx_core.security_monitor

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/compliance-status")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.security_monitor = MagicMock()
        mock_pbx_core.security_monitor.get_compliance_status.side_effect = RuntimeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/compliance-status")
        assert resp.status_code == 500


@pytest.mark.unit
class TestGetSecurityHealth:
    """Tests for GET /api/security/health."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.security_monitor = MagicMock()
        mock_pbx_core.security_monitor.perform_security_check.return_value = {"status": "ok"}

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/health")
        assert resp.status_code == 200

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "security_monitor"):
            del mock_pbx_core.security_monitor

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/health")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.security_monitor = MagicMock()
        mock_pbx_core.security_monitor.perform_security_check.side_effect = RuntimeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/health")
        assert resp.status_code == 500


@pytest.mark.unit
class TestCheckIp:
    """Tests for GET /api/security/check-ip/<ip>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()
        mock_pbx_core.threat_detector.is_ip_blocked.return_value = (True, "Brute force")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/check-ip/192.168.1.100")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["is_blocked"] is True

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "threat_detector"):
            del mock_pbx_core.threat_detector

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/check-ip/192.168.1.100")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()
        mock_pbx_core.threat_detector.is_ip_blocked.side_effect = RuntimeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/security/check-ip/192.168.1.100")
        assert resp.status_code == 500


@pytest.mark.unit
class TestBlockIp:
    """Tests for POST /api/security/block-ip."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({"ip_address": "10.0.0.1", "reason": "Spam", "duration": 3600}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_missing_ip(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "threat_detector"):
            del mock_pbx_core.threat_detector

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({"ip_address": "10.0.0.1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()
        mock_pbx_core.threat_detector.block_ip.side_effect = ValueError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({"ip_address": "10.0.0.1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_non_admin(self, api_client: FlaskClient) -> None:
        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({"ip_address": "10.0.0.1"}),
                content_type="application/json",
            )
        assert resp.status_code == 403


@pytest.mark.unit
class TestUnblockIp:
    """Tests for POST /api/security/unblock-ip."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/security/unblock-ip",
                data=json.dumps({"ip_address": "10.0.0.1"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_missing_ip(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/security/unblock-ip",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "threat_detector"):
            del mock_pbx_core.threat_detector

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/security/unblock-ip",
                data=json.dumps({"ip_address": "10.0.0.1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.threat_detector = MagicMock()
        mock_pbx_core.threat_detector.unblock_ip.side_effect = ValueError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_ADMIN):
            resp = api_client.post(
                "/api/security/unblock-ip",
                data=json.dumps({"ip_address": "10.0.0.1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# DND routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetDndStatus:
    """Tests for GET /api/dnd/status/<extension>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.get_status.return_value = {
            "extension": "1001",
            "dnd_active": False,
        }

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/dnd/status/1001")
        assert resp.status_code == 200

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/dnd/status/1001")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.get_status.side_effect = RuntimeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/dnd/status/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestGetDndRules:
    """Tests for GET /api/dnd/rules/<extension>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.get_rules.return_value = [{"id": "rule1"}]

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/dnd/rules/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["extension"] == "1001"

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/dnd/rules/1001")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.get_rules.side_effect = RuntimeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.get("/api/dnd/rules/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestAddDndRule:
    """Tests for POST /api/dnd/rule."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.add_rule.return_value = "rule123"

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/rule",
                data=json.dumps(
                    {
                        "extension": "1001",
                        "rule_type": "time_based",
                        "config": {"start": "22:00", "end": "08:00"},
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["rule_id"] == "rule123"

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/rule",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/rule",
                data=json.dumps({"extension": "1001", "rule_type": "time_based"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.add_rule.side_effect = TypeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/rule",
                data=json.dumps({"extension": "1001", "rule_type": "time_based"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestRegisterCalendarUser:
    """Tests for POST /api/dnd/register-calendar."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/register-calendar",
                data=json.dumps({"extension": "1001", "email": "user@example.com"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/register-calendar",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/register-calendar",
                data=json.dumps({"extension": "1001", "email": "user@example.com"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.register_calendar_user.side_effect = TypeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/register-calendar",
                data=json.dumps({"extension": "1001", "email": "user@example.com"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestDndOverride:
    """Tests for POST /api/dnd/override."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()

        with (
            patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER),
            patch("pbx.features.presence.PresenceStatus", autospec=True) as mock_status,
        ):
            mock_status.return_value = mock_status
            resp = api_client.post(
                "/api/dnd/override",
                data=json.dumps(
                    {
                        "extension": "1001",
                        "status": "do_not_disturb",
                        "duration_minutes": 60,
                    }
                ),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_invalid_status(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER), patch(
            "pbx.features.presence.PresenceStatus",
            side_effect=ValueError("invalid"),
        ):
            resp = api_client.post(
                "/api/dnd/override",
                data=json.dumps({"extension": "1001", "status": "invalid_status"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_missing_fields(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/override",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.post(
                "/api/dnd/override",
                data=json.dumps({"extension": "1001", "status": "do_not_disturb"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER), patch(
            "pbx.features.presence.PresenceStatus",
            side_effect=RuntimeError("fail"),
        ):
            resp = api_client.post(
                "/api/dnd/override",
                data=json.dumps({"extension": "1001", "status": "do_not_disturb"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestDeleteDndRule:
    """Tests for DELETE /api/dnd/rule/<rule_id>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.remove_rule.return_value = True

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.delete("/api/dnd/rule/rule123")
        assert resp.status_code == 200

    def test_not_found(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.remove_rule.return_value = False

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.delete("/api/dnd/rule/nonexistent")
        assert resp.status_code == 404

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.delete("/api/dnd/rule/rule123")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.remove_rule.side_effect = RuntimeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.delete("/api/dnd/rule/rule123")
        assert resp.status_code == 500


@pytest.mark.unit
class TestClearDndOverride:
    """Tests for DELETE /api/dnd/override/<extension>."""

    def test_success(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.delete("/api/dnd/override/1001")
        assert resp.status_code == 200

    def test_not_available(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.delete("/api/dnd/override/1001")
        assert resp.status_code == 500

    def test_exception(self, api_client: FlaskClient, mock_pbx_core: MagicMock) -> None:
        mock_pbx_core.dnd_scheduler = MagicMock()
        mock_pbx_core.dnd_scheduler.clear_manual_override.side_effect = RuntimeError("fail")

        with patch("pbx.api.utils.verify_authentication", return_value=AUTH_USER):
            resp = api_client.delete("/api/dnd/override/1001")
        assert resp.status_code == 500
