"""Comprehensive tests for Security Blueprint routes (Hot-Desking, MFA, Threat Detection, DND)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient


AUTH_PATCH = "pbx.api.utils.verify_authentication"
AUTH_OK = (True, {"extension": "1001", "is_admin": True})
AUTH_NON_ADMIN = (True, {"extension": "1001", "is_admin": False})
AUTH_FAIL = (False, None)


# ---------------------------------------------------------------------------
# Hot-Desking Routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHotDeskingSessions:
    """Tests for Hot-Desking session endpoints."""

    def test_get_sessions_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.get_active_sessions.return_value = [
            {"device_id": "d1", "extension": "1001"},
        ]
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/sessions")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["count"] == 1
        assert len(data["sessions"]) == 1

    def test_get_sessions_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/sessions")
        assert resp.status_code == 500
        data = json.loads(resp.data)
        assert "error" in data

    def test_get_sessions_unauthenticated(
        self, api_client: FlaskClient
    ) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_FAIL):
            resp = api_client.get("/api/hot-desk/sessions")
        assert resp.status_code == 401

    def test_get_sessions_exception(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.get_active_sessions.side_effect = RuntimeError("DB error")
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/sessions")
        assert resp.status_code == 500


@pytest.mark.unit
class TestHotDeskingSessionByDevice:
    """Tests for Hot-Desking single session endpoints."""

    def test_get_session_found(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        session = MagicMock()
        session.to_dict.return_value = {"device_id": "d1", "extension": "1001"}
        hd = MagicMock()
        hd.get_session.return_value = session
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/session/d1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["device_id"] == "d1"

    def test_get_session_not_found(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.get_session.return_value = None
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/session/unknown")
        assert resp.status_code == 404

    def test_get_session_exception(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.get_session.side_effect = RuntimeError("fail")
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/session/d1")
        assert resp.status_code == 500


@pytest.mark.unit
class TestHotDeskingExtension:
    """Tests for Hot-Desking extension lookup endpoint."""

    def test_get_extension_with_sessions(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        session = MagicMock()
        session.to_dict.return_value = {"device_id": "d1"}
        hd = MagicMock()
        hd.get_extension_devices.return_value = ["d1"]
        hd.get_session.return_value = session
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/extension/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["extension"] == "1001"
        assert data["logged_in"] is True
        assert data["device_count"] == 1

    def test_get_extension_no_sessions(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.get_extension_devices.return_value = []
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/extension/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["logged_in"] is False

    def test_get_extension_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/hot-desk/extension/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestHotDeskingLogin:
    """Tests for Hot-Desking login endpoint."""

    def test_login_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.login.return_value = True
        hd.get_extension_profile.return_value = {"extension": "1001"}
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({
                    "extension": "1001",
                    "device_id": "d1",
                    "pin": "1234",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "profile" in data

    def test_login_failure(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.login.return_value = False
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({
                    "extension": "1001",
                    "device_id": "d1",
                    "pin": "wrong",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 401

    def test_login_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_login_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/login",
                data=json.dumps({"extension": "1001", "device_id": "d1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestHotDeskingLogout:
    """Tests for Hot-Desking logout endpoint."""

    def test_logout_by_device_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.logout.return_value = True
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"device_id": "d1"}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True

    def test_logout_by_device_no_session(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.logout.return_value = False
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"device_id": "d1"}),
                content_type="application/json",
            )
        assert resp.status_code == 404

    def test_logout_by_extension_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        hd.logout_extension.return_value = 2
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "2 device(s)" in data["message"]

    def test_logout_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        hd = MagicMock()
        mock_pbx_core.hot_desking = hd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_logout_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "hot_desking"):
            del mock_pbx_core.hot_desking

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/hot-desk/logout",
                data=json.dumps({"device_id": "d1"}),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# MFA Routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMFAStatus:
    """Tests for MFA status endpoints."""

    def test_get_mfa_status_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.is_enabled_for_user.return_value = True
        mfa.required = False
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/mfa/status/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["extension"] == "1001"
        assert data["mfa_enabled"] is True

    def test_get_mfa_status_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/mfa/status/1001")
        assert resp.status_code == 500

    def test_get_mfa_status_exception(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.is_enabled_for_user.side_effect = RuntimeError("DB down")
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/mfa/status/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestMFAMethods:
    """Tests for MFA methods endpoint."""

    def test_get_methods_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.get_enrolled_methods.return_value = ["totp", "yubikey"]
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/mfa/methods/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["extension"] == "1001"
        assert len(data["methods"]) == 2

    def test_get_methods_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "mfa_manager"):
            del mock_pbx_core.mfa_manager

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/mfa/methods/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestMFAEnroll:
    """Tests for MFA enrollment endpoints."""

    def test_enroll_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.enroll_user.return_value = (True, "otpauth://totp/...", ["code1", "code2"])
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "provisioning_uri" in data
        assert "backup_codes" in data

    def test_enroll_failure(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.enroll_user.return_value = (False, None, None)
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_enroll_missing_extension(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400


@pytest.mark.unit
class TestMFAVerify:
    """Tests for MFA verification endpoints."""

    def test_verify_enrollment_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.verify_enrollment.return_value = True
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/verify-enrollment",
                data=json.dumps({"extension": "1001", "code": "123456"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_verify_enrollment_invalid_code(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.verify_enrollment.return_value = False
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/verify-enrollment",
                data=json.dumps({"extension": "1001", "code": "000000"}),
                content_type="application/json",
            )
        assert resp.status_code == 401

    def test_verify_enrollment_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/verify-enrollment",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_verify_code_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.verify_code.return_value = True
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/verify",
                data=json.dumps({"extension": "1001", "code": "123456"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_verify_code_invalid(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.verify_code.return_value = False
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/verify",
                data=json.dumps({"extension": "1001", "code": "000000"}),
                content_type="application/json",
            )
        assert resp.status_code == 401

    def test_verify_code_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/verify",
                data=json.dumps({"code": "123456"}),
                content_type="application/json",
            )
        assert resp.status_code == 400


@pytest.mark.unit
class TestMFADisable:
    """Tests for MFA disable endpoint."""

    def test_disable_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.disable_for_user.return_value = True
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/disable",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_disable_failure(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.disable_for_user.return_value = False
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/disable",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_disable_missing_extension(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/disable",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400


@pytest.mark.unit
class TestMFAYubiKey:
    """Tests for MFA YubiKey enrollment endpoint."""

    def test_enroll_yubikey_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.enroll_yubikey.return_value = (True, None)
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll-yubikey",
                data=json.dumps({
                    "extension": "1001",
                    "otp": "cccccccfiuv...",
                    "device_name": "My YubiKey",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_enroll_yubikey_failure(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.enroll_yubikey.return_value = (False, "Invalid OTP")
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll-yubikey",
                data=json.dumps({
                    "extension": "1001",
                    "otp": "bad",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_enroll_yubikey_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll-yubikey",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400


@pytest.mark.unit
class TestMFAFIDO2:
    """Tests for MFA FIDO2/WebAuthn enrollment endpoint."""

    def test_enroll_fido2_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.enroll_fido2.return_value = (True, None)
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll-fido2",
                data=json.dumps({
                    "extension": "1001",
                    "credential_data": {"id": "cred_abc"},
                    "device_name": "USB Key",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200

    def test_enroll_fido2_failure(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mfa.enroll_fido2.return_value = (False, "Invalid credential")
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll-fido2",
                data=json.dumps({
                    "extension": "1001",
                    "credential_data": {"id": "bad"},
                }),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_enroll_fido2_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        mfa = MagicMock()
        mock_pbx_core.mfa_manager = mfa

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/mfa/enroll-fido2",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Threat Detection / Security Routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThreatDetection:
    """Tests for Threat Detection endpoints."""

    def test_get_threat_summary_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        td.get_threat_summary.return_value = {"total_threats": 5}
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/threat-summary")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["total_threats"] == 5

    def test_get_threat_summary_with_hours(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        td.get_threat_summary.return_value = {"total_threats": 0}
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/threat-summary?hours=48")
        assert resp.status_code == 200
        td.get_threat_summary.assert_called_once_with(48)

    def test_get_threat_summary_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "threat_detector"):
            del mock_pbx_core.threat_detector

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/threat-summary")
        assert resp.status_code == 500

    def test_check_ip_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        td.is_ip_blocked.return_value = (True, "Brute force")
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/check-ip/192.168.1.100")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["is_blocked"] is True
        assert data["reason"] == "Brute force"

    def test_check_ip_not_blocked(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        td.is_ip_blocked.return_value = (False, None)
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/check-ip/10.0.0.1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["is_blocked"] is False

    def test_check_ip_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "threat_detector"):
            del mock_pbx_core.threat_detector

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/check-ip/1.2.3.4")
        assert resp.status_code == 500

    def test_block_ip_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({
                    "ip_address": "192.168.1.200",
                    "reason": "Scanning",
                    "duration": 3600,
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200
        td.block_ip.assert_called_once_with("192.168.1.200", "Scanning", 3600)

    def test_block_ip_missing_address(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({"reason": "Test"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_block_ip_requires_admin(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_NON_ADMIN):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({"ip_address": "1.2.3.4"}),
                content_type="application/json",
            )
        assert resp.status_code == 403

    def test_block_ip_unauthenticated(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        with patch(AUTH_PATCH, return_value=AUTH_FAIL):
            resp = api_client.post(
                "/api/security/block-ip",
                data=json.dumps({"ip_address": "1.2.3.4"}),
                content_type="application/json",
            )
        assert resp.status_code == 401

    def test_unblock_ip_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/security/unblock-ip",
                data=json.dumps({"ip_address": "192.168.1.200"}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        td.unblock_ip.assert_called_once_with("192.168.1.200")

    def test_unblock_ip_missing_address(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/security/unblock-ip",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_unblock_ip_requires_admin(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        td = MagicMock()
        mock_pbx_core.threat_detector = td

        with patch(AUTH_PATCH, return_value=AUTH_NON_ADMIN):
            resp = api_client.post(
                "/api/security/unblock-ip",
                data=json.dumps({"ip_address": "1.2.3.4"}),
                content_type="application/json",
            )
        assert resp.status_code == 403


@pytest.mark.unit
class TestSecurityCompliance:
    """Tests for Security compliance and health endpoints."""

    def test_get_compliance_status_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        sm = MagicMock()
        sm.get_compliance_status.return_value = {"fips_enabled": True}
        mock_pbx_core.security_monitor = sm

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/compliance-status")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["fips_enabled"] is True

    def test_get_compliance_status_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "security_monitor"):
            del mock_pbx_core.security_monitor

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/compliance-status")
        assert resp.status_code == 500

    def test_get_compliance_status_exception(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        sm = MagicMock()
        sm.get_compliance_status.side_effect = RuntimeError("fail")
        mock_pbx_core.security_monitor = sm

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/compliance-status")
        assert resp.status_code == 500

    def test_get_security_health_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        sm = MagicMock()
        sm.perform_security_check.return_value = {"overall": "healthy"}
        mock_pbx_core.security_monitor = sm

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["overall"] == "healthy"

    def test_get_security_health_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "security_monitor"):
            del mock_pbx_core.security_monitor

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/health")
        assert resp.status_code == 500

    def test_get_security_health_exception(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        sm = MagicMock()
        sm.perform_security_check.side_effect = RuntimeError("fail")
        mock_pbx_core.security_monitor = sm

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/security/health")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# DND (Do Not Disturb) Routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDNDStatus:
    """Tests for DND status endpoints."""

    def test_get_dnd_status_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        dnd.get_status.return_value = {"extension": "1001", "dnd_active": True}
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/dnd/status/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["dnd_active"] is True

    def test_get_dnd_status_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/dnd/status/1001")
        assert resp.status_code == 500

    def test_get_dnd_status_exception(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        dnd.get_status.side_effect = RuntimeError("fail")
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/dnd/status/1001")
        assert resp.status_code == 500


@pytest.mark.unit
class TestDNDRules:
    """Tests for DND rules endpoints."""

    def test_get_rules_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        dnd.get_rules.return_value = [{"rule_id": "r1", "type": "time_based"}]
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/dnd/rules/1001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["extension"] == "1001"
        assert len(data["rules"]) == 1

    def test_get_rules_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.get("/api/dnd/rules/1001")
        assert resp.status_code == 500

    def test_add_rule_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        dnd.add_rule.return_value = "rule_123"
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/dnd/rule",
                data=json.dumps({
                    "extension": "1001",
                    "rule_type": "time_based",
                    "config": {"start": "18:00", "end": "08:00"},
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["rule_id"] == "rule_123"

    def test_add_rule_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/dnd/rule",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_add_rule_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/dnd/rule",
                data=json.dumps({
                    "extension": "1001",
                    "rule_type": "time_based",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_delete_rule_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        dnd.remove_rule.return_value = True
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.delete("/api/dnd/rule/rule_123")
        assert resp.status_code == 200

    def test_delete_rule_not_found(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        dnd.remove_rule.return_value = False
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.delete("/api/dnd/rule/nonexistent")
        assert resp.status_code == 404

    def test_delete_rule_exception(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        dnd.remove_rule.side_effect = RuntimeError("fail")
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.delete("/api/dnd/rule/rule_123")
        assert resp.status_code == 500


@pytest.mark.unit
class TestDNDCalendar:
    """Tests for DND calendar registration endpoint."""

    def test_register_calendar_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/dnd/register-calendar",
                data=json.dumps({
                    "extension": "1001",
                    "email": "user@example.com",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200
        dnd.register_calendar_user.assert_called_once_with("1001", "user@example.com")

    def test_register_calendar_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/dnd/register-calendar",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_register_calendar_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/dnd/register-calendar",
                data=json.dumps({
                    "extension": "1001",
                    "email": "user@example.com",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 500


@pytest.mark.unit
class TestDNDOverride:
    """Tests for DND manual override endpoints."""

    def test_set_override_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            with patch(
                "pbx.features.presence.PresenceStatus", create=True
            ) as mock_presence:
                mock_presence.return_value = MagicMock()
                resp = api_client.post(
                    "/api/dnd/override",
                    data=json.dumps({
                        "extension": "1001",
                        "status": "do_not_disturb",
                        "duration_minutes": 60,
                    }),
                    content_type="application/json",
                )
        assert resp.status_code == 200

    def test_set_override_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/dnd/override",
                data=json.dumps({"extension": "1001"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_set_override_invalid_status(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            with patch(
                "pbx.features.presence.PresenceStatus",
                side_effect=ValueError("Invalid"),
                create=True,
            ):
                resp = api_client.post(
                    "/api/dnd/override",
                    data=json.dumps({
                        "extension": "1001",
                        "status": "invalid_status",
                    }),
                    content_type="application/json",
                )
        assert resp.status_code == 400

    def test_set_override_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.post(
                "/api/dnd/override",
                data=json.dumps({
                    "extension": "1001",
                    "status": "available",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 500

    def test_clear_override_success(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.delete("/api/dnd/override/1001")
        assert resp.status_code == 200
        dnd.clear_manual_override.assert_called_once_with("1001")

    def test_clear_override_not_available(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        if hasattr(mock_pbx_core, "dnd_scheduler"):
            del mock_pbx_core.dnd_scheduler

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.delete("/api/dnd/override/1001")
        assert resp.status_code == 500

    def test_clear_override_exception(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        dnd = MagicMock()
        dnd.clear_manual_override.side_effect = RuntimeError("fail")
        mock_pbx_core.dnd_scheduler = dnd

        with patch(AUTH_PATCH, return_value=AUTH_OK):
            resp = api_client.delete("/api/dnd/override/1001")
        assert resp.status_code == 500
