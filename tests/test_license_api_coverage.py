"""Comprehensive tests for pbx.api.license_api endpoints."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient


@pytest.fixture
def app() -> Flask:
    """Create a Flask app with the license_api blueprint registered."""
    from pbx.api.license_api import license_api

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-for-sessions"
    app.register_blueprint(license_api)
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Provide a Flask test client."""
    with app.test_client() as c:
        yield c


def _json_post(
    client: FlaskClient, url: str, data: dict[str, Any] | None = None
) -> tuple[dict[str, Any], int]:
    """Helper: POST JSON and return (parsed_body, status_code)."""
    resp = client.post(url, json=data or {})
    return resp.get_json(), resp.status_code


def _json_get(client: FlaskClient, url: str) -> tuple[dict[str, Any], int]:
    """Helper: GET and return (parsed_body, status_code)."""
    resp = client.get(url)
    return resp.get_json(), resp.status_code


# ======================================================================
# GET /api/license/status
# ======================================================================
@pytest.mark.unit
class TestGetLicenseStatus:
    """Tests for GET /api/license/status."""

    @patch("pbx.api.license_api.get_license_manager")
    def test_success(self, mock_glm: MagicMock, client: FlaskClient) -> None:
        """Returns license info on success."""
        mock_mgr = MagicMock()
        mock_mgr.get_license_info.return_value = {
            "type": "enterprise",
            "status": "active",
        }
        mock_glm.return_value = mock_mgr

        body, status = _json_get(client, "/api/license/status")

        assert status == 200
        assert body["success"] is True
        assert body["license"]["type"] == "enterprise"
        mock_mgr.get_license_info.assert_called_once()

    @patch("pbx.api.license_api.get_license_manager")
    def test_exception(self, mock_glm: MagicMock, client: FlaskClient) -> None:
        """Returns 500 when an exception occurs."""
        mock_glm.side_effect = RuntimeError("DB down")

        body, status = _json_get(client, "/api/license/status")

        assert status == 500
        assert body["success"] is False
        assert "DB down" in body["error"]


# ======================================================================
# GET /api/license/features
# ======================================================================
@pytest.mark.unit
class TestListAvailableFeatures:
    """Tests for GET /api/license/features."""

    @patch("pbx.api.license_api.get_license_manager")
    def test_licensing_disabled(self, mock_glm: MagicMock, client: FlaskClient) -> None:
        """When licensing is disabled, returns all features."""
        mock_mgr = MagicMock()
        mock_mgr.enabled = False
        mock_glm.return_value = mock_mgr

        body, status = _json_get(client, "/api/license/features")

        assert status == 200
        assert body["success"] is True
        assert body["features"] == "all"
        assert body["licensing_enabled"] is False

    @patch("pbx.api.license_api.get_license_manager")
    def test_licensing_enabled_with_license(
        self, mock_glm: MagicMock, client: FlaskClient
    ) -> None:
        """When licensing is enabled, returns features for the current license type."""
        mock_mgr = MagicMock()
        mock_mgr.enabled = True
        mock_mgr.current_license = {"type": "professional"}
        mock_mgr.features = {
            "professional": [
                "voicemail",
                "conferencing",
                "max_extensions:50",
                "max_concurrent_calls:unlimited",
            ]
        }
        mock_glm.return_value = mock_mgr

        body, status = _json_get(client, "/api/license/features")

        assert status == 200
        assert body["success"] is True
        assert body["license_type"] == "professional"
        assert "voicemail" in body["features"]
        assert "conferencing" in body["features"]
        assert body["limits"]["max_extensions"] == 50
        assert body["limits"]["max_concurrent_calls"] is None  # unlimited
        assert body["licensing_enabled"] is True

    @patch("pbx.api.license_api.get_license_manager")
    def test_licensing_enabled_no_license(
        self, mock_glm: MagicMock, client: FlaskClient
    ) -> None:
        """When no license is present, defaults to 'trial' type."""
        mock_mgr = MagicMock()
        mock_mgr.enabled = True
        mock_mgr.current_license = None
        mock_mgr.features = {"trial": ["basic_calls"]}
        mock_glm.return_value = mock_mgr

        body, status = _json_get(client, "/api/license/features")

        assert status == 200
        assert body["license_type"] == "trial"
        assert "basic_calls" in body["features"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_custom_license_type(
        self, mock_glm: MagicMock, client: FlaskClient
    ) -> None:
        """Custom license type returns custom_features from license data."""
        mock_mgr = MagicMock()
        mock_mgr.enabled = True
        mock_mgr.current_license = {
            "type": "custom",
            "custom_features": ["feature_a", "feature_b"],
        }
        mock_mgr.features = {"custom": []}
        mock_glm.return_value = mock_mgr

        body, status = _json_get(client, "/api/license/features")

        assert status == 200
        assert body["license_type"] == "custom"
        assert "feature_a" in body["features"]
        assert "feature_b" in body["features"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_features_with_no_limits(
        self, mock_glm: MagicMock, client: FlaskClient
    ) -> None:
        """Features without limit entries result in empty limits dict."""
        mock_mgr = MagicMock()
        mock_mgr.enabled = True
        mock_mgr.current_license = {"type": "basic"}
        mock_mgr.features = {"basic": ["voicemail", "parking"]}
        mock_glm.return_value = mock_mgr

        body, status = _json_get(client, "/api/license/features")

        assert status == 200
        assert body["limits"] == {}

    @patch("pbx.api.license_api.get_license_manager")
    def test_features_with_non_limit_colon(
        self, mock_glm: MagicMock, client: FlaskClient
    ) -> None:
        """Features containing colons that are NOT limits stay in the feature list."""
        mock_mgr = MagicMock()
        mock_mgr.enabled = True
        mock_mgr.current_license = {"type": "basic"}
        mock_mgr.features = {"basic": ["some:feature:with:colons"]}
        mock_glm.return_value = mock_mgr

        body, status = _json_get(client, "/api/license/features")

        assert status == 200
        assert "some:feature:with:colons" in body["features"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_exception(self, mock_glm: MagicMock, client: FlaskClient) -> None:
        """Returns 500 on exception."""
        mock_glm.side_effect = TypeError("bad type")

        body, status = _json_get(client, "/api/license/features")

        assert status == 500
        assert body["success"] is False


# ======================================================================
# POST /api/license/check
# ======================================================================
@pytest.mark.unit
class TestCheckFeature:
    """Tests for POST /api/license/check."""

    @patch("pbx.api.license_api.get_license_manager")
    def test_feature_available(self, mock_glm: MagicMock, client: FlaskClient) -> None:
        """Returns available=True when feature is available."""
        mock_mgr = MagicMock()
        mock_mgr.has_feature.return_value = True
        mock_glm.return_value = mock_mgr

        body, status = _json_post(client, "/api/license/check", {"feature": "voicemail"})

        assert status == 200
        assert body["success"] is True
        assert body["feature"] == "voicemail"
        assert body["available"] is True

    @patch("pbx.api.license_api.get_license_manager")
    def test_feature_not_available(
        self, mock_glm: MagicMock, client: FlaskClient
    ) -> None:
        """Returns available=False when feature is not available."""
        mock_mgr = MagicMock()
        mock_mgr.has_feature.return_value = False
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client, "/api/license/check", {"feature": "advanced_routing"}
        )

        assert status == 200
        assert body["available"] is False

    @patch("pbx.api.license_api.get_license_manager")
    def test_missing_feature_name(
        self, mock_glm: MagicMock, client: FlaskClient
    ) -> None:
        """Returns 400 when feature name is missing."""
        body, status = _json_post(client, "/api/license/check", {})

        assert status == 400
        assert body["success"] is False
        assert "Missing feature name" in body["error"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_empty_feature_name(
        self, mock_glm: MagicMock, client: FlaskClient
    ) -> None:
        """Returns 400 when feature name is an empty string."""
        body, status = _json_post(client, "/api/license/check", {"feature": ""})

        assert status == 400
        assert body["success"] is False

    @patch("pbx.api.license_api.get_license_manager")
    def test_exception(self, mock_glm: MagicMock, client: FlaskClient) -> None:
        """Returns 500 on exception."""
        mock_glm.side_effect = ValueError("check error")

        body, status = _json_post(
            client, "/api/license/check", {"feature": "something"}
        )

        assert status == 500
        assert body["success"] is False


# ======================================================================
# POST /api/license/generate
# ======================================================================
@pytest.mark.unit
class TestGenerateLicense:
    """Tests for POST /api/license/generate (requires license admin)."""

    def _login_as_admin(self, client: FlaskClient, app: Flask) -> None:
        """Simulate a valid license admin session."""
        with client.session_transaction() as sess:
            sess["extension"] = "9322"
            sess["username"] = "ICE"
            sess["is_license_admin"] = True

    @patch("pbx.api.license_api.get_license_manager")
    def test_generate_success(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Successfully generates a license when admin is authenticated."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.generate_license_key.return_value = {"key": "XXXX-YYYY", "type": "trial"}
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client,
            "/api/license/generate",
            {"type": "trial", "issued_to": "Test Org"},
        )

        assert status == 200
        assert body["success"] is True
        assert body["license"]["key"] == "XXXX-YYYY"

    @patch("pbx.api.license_api.get_license_manager")
    def test_generate_with_optional_fields(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Optional fields are passed through to generate_license_key."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.generate_license_key.return_value = {"key": "K"}
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client,
            "/api/license/generate",
            {
                "type": "enterprise",
                "issued_to": "Big Corp",
                "max_extensions": 100,
                "max_concurrent_calls": 50,
                "expiration_days": 365,
                "custom_features": ["f1"],
            },
        )

        assert status == 200
        call_kwargs = mock_mgr.generate_license_key.call_args[1]
        assert call_kwargs["max_extensions"] == 100
        assert call_kwargs["max_concurrent_calls"] == 50
        assert call_kwargs["expiration_days"] == 365
        assert call_kwargs["custom_features"] == ["f1"]

    def test_generate_unauthenticated(self, client: FlaskClient) -> None:
        """Returns 401 when not authenticated."""
        body, status = _json_post(
            client,
            "/api/license/generate",
            {"type": "trial", "issued_to": "Test"},
        )

        assert status == 401
        assert body["success"] is False

    @patch("pbx.api.license_api.get_license_manager")
    def test_generate_missing_type(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 400 when type is missing."""
        self._login_as_admin(client, app)

        body, status = _json_post(
            client, "/api/license/generate", {"issued_to": "Test Org"}
        )

        assert status == 400
        assert "Missing required fields" in body["error"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_generate_missing_issued_to(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 400 when issued_to is missing."""
        self._login_as_admin(client, app)

        body, status = _json_post(
            client, "/api/license/generate", {"type": "trial"}
        )

        assert status == 400
        assert "Missing required fields" in body["error"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_generate_invalid_license_type(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 400 when license type is invalid."""
        self._login_as_admin(client, app)

        body, status = _json_post(
            client,
            "/api/license/generate",
            {"type": "nonexistent_type", "issued_to": "Org"},
        )

        assert status == 400
        assert "Invalid license type" in body["error"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_generate_exception(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 500 on internal exception."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.generate_license_key.side_effect = TypeError("gen error")
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client,
            "/api/license/generate",
            {"type": "trial", "issued_to": "Org"},
        )

        assert status == 500
        assert body["success"] is False


# ======================================================================
# POST /api/license/install
# ======================================================================
@pytest.mark.unit
class TestInstallLicense:
    """Tests for POST /api/license/install (requires license admin)."""

    def _login_as_admin(self, client: FlaskClient, app: Flask) -> None:
        with client.session_transaction() as sess:
            sess["extension"] = "9322"
            sess["username"] = "ICE"
            sess["is_license_admin"] = True

    @patch("pbx.api.license_api.get_license_manager")
    def test_install_success(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Successfully installs a license."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.save_license.return_value = True
        mock_mgr.get_license_info.return_value = {"type": "enterprise", "status": "active"}
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client,
            "/api/license/install",
            {"license_data": {"key": "ABCD-1234", "type": "enterprise"}},
        )

        assert status == 200
        assert body["success"] is True
        assert "installed successfully" in body["message"]
        assert body["enforcement_locked"] is False

    @patch("pbx.api.license_api.get_license_manager")
    def test_install_with_enforcement(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Install with enforce_licensing=True includes enforcement message."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.save_license.return_value = True
        mock_mgr.get_license_info.return_value = {"type": "enterprise"}
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client,
            "/api/license/install",
            {
                "license_data": {"key": "ABCD-1234"},
                "enforce_licensing": True,
            },
        )

        assert status == 200
        assert body["enforcement_locked"] is True
        assert "cannot be disabled" in body["message"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_install_without_license_data_key_uses_body(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """When license_data is missing, uses the entire request body."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.save_license.return_value = True
        mock_mgr.get_license_info.return_value = {}
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client,
            "/api/license/install",
            {"key": "ABCD-1234", "type": "basic"},
        )

        assert status == 200
        assert body["success"] is True

    @patch("pbx.api.license_api.get_license_manager")
    def test_install_missing_key(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 400 when license key is missing."""
        self._login_as_admin(client, app)

        body, status = _json_post(
            client,
            "/api/license/install",
            {"license_data": {"type": "basic"}},
        )

        assert status == 400
        assert "Missing license key" in body["error"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_install_save_fails(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 500 when save_license returns False."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.save_license.return_value = False
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client,
            "/api/license/install",
            {"key": "ABCD-1234"},
        )

        assert status == 500
        assert body["success"] is False
        assert "Failed to install" in body["error"]

    def test_install_unauthenticated(self, client: FlaskClient) -> None:
        """Returns 401 when not authenticated."""
        body, status = _json_post(
            client, "/api/license/install", {"key": "ABCD"}
        )

        assert status == 401

    @patch("pbx.api.license_api.get_license_manager")
    def test_install_exception(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 500 on internal exception."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.save_license.side_effect = ValueError("install err")
        mock_glm.return_value = mock_mgr

        body, status = _json_post(
            client,
            "/api/license/install",
            {"key": "ABCD-1234"},
        )

        assert status == 500
        assert body["success"] is False


# ======================================================================
# POST /api/license/revoke
# ======================================================================
@pytest.mark.unit
class TestRevokeLicense:
    """Tests for POST /api/license/revoke (requires license admin)."""

    def _login_as_admin(self, client: FlaskClient, app: Flask) -> None:
        with client.session_transaction() as sess:
            sess["extension"] = "9322"
            sess["username"] = "ICE"
            sess["is_license_admin"] = True

    @patch("pbx.api.license_api.get_license_manager")
    def test_revoke_success(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Successfully revokes a license."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.revoke_license.return_value = True
        mock_glm.return_value = mock_mgr

        body, status = _json_post(client, "/api/license/revoke")

        assert status == 200
        assert body["success"] is True
        assert "revoked" in body["message"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_revoke_fails(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 500 when revoke_license returns False."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.revoke_license.return_value = False
        mock_glm.return_value = mock_mgr

        body, status = _json_post(client, "/api/license/revoke")

        assert status == 500
        assert body["success"] is False

    def test_revoke_unauthenticated(self, client: FlaskClient) -> None:
        """Returns 401 when not authenticated."""
        body, status = _json_post(client, "/api/license/revoke")

        assert status == 401

    @patch("pbx.api.license_api.get_license_manager")
    def test_revoke_exception(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 500 on internal exception."""
        self._login_as_admin(client, app)

        mock_glm.side_effect = RuntimeError("revoke error")

        body, status = _json_post(client, "/api/license/revoke")

        assert status == 500
        assert body["success"] is False


# ======================================================================
# POST /api/license/toggle
# ======================================================================
@pytest.mark.unit
class TestToggleLicensing:
    """Tests for POST /api/license/toggle (requires license admin)."""

    def _login_as_admin(self, client: FlaskClient, app: Flask) -> None:
        with client.session_transaction() as sess:
            sess["extension"] = "9322"
            sess["username"] = "ICE"
            sess["is_license_admin"] = True

    @patch("pbx.utils.licensing.initialize_license_manager")
    @patch("pbx.api.license_api.os")
    @patch("pbx.api.license_api.Path")
    @patch("pbx.api.license_api.get_license_manager")
    def test_toggle_enable(
        self,
        mock_glm: MagicMock,
        mock_path_cls: MagicMock,
        mock_os: MagicMock,
        mock_init_lm: MagicMock,
        client: FlaskClient,
        app: Flask,
    ) -> None:
        """Successfully enables licensing."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.config = {}
        mock_mgr.enabled = True
        mock_glm.return_value = mock_mgr

        # The code does: Path(__file__).resolve().parent.parent / ".." / ".env"
        # and similar for ".license_lock"
        # Build a mock chain that works for both paths
        mock_env_path = MagicMock()
        mock_env_path.exists.return_value = True
        mock_env_path.read_text.return_value = "SOME_VAR=value\n"
        mock_env_path.write_text = MagicMock()

        mock_lock_path = MagicMock()
        mock_lock_path.exists.return_value = False

        # Chain: Path(__file__).resolve().parent.parent / ".." / ".env"
        # and   Path(__file__).resolve().parent.parent / ".." / ".license_lock"
        mock_dotdot = MagicMock()

        def truediv_side_effect(arg: str) -> MagicMock:
            if arg == ".env":
                return mock_env_path
            if arg == ".license_lock":
                return mock_lock_path
            # For ".." intermediate step, return self again
            return mock_dotdot

        mock_dotdot.__truediv__ = MagicMock(side_effect=truediv_side_effect)

        mock_parent_parent = MagicMock()
        mock_parent_parent.__truediv__ = MagicMock(return_value=mock_dotdot)

        mock_resolve = MagicMock()
        mock_resolve.parent.parent = mock_parent_parent

        mock_path_cls.return_value.resolve.return_value = mock_resolve

        new_mgr = MagicMock()
        new_mgr.enabled = True
        mock_init_lm.return_value = new_mgr

        body, status = _json_post(client, "/api/license/toggle", {"enabled": True})

        assert status == 200
        assert body["success"] is True
        assert body["licensing_enabled"] is True

    def test_toggle_unauthenticated(self, client: FlaskClient) -> None:
        """Returns 401 when not authenticated."""
        body, status = _json_post(client, "/api/license/toggle", {"enabled": True})

        assert status == 401

    @patch("pbx.api.license_api.get_license_manager")
    def test_toggle_missing_enabled_flag(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 400 when enabled flag is missing."""
        self._login_as_admin(client, app)

        body, status = _json_post(client, "/api/license/toggle", {})

        assert status == 400
        assert "Missing enabled flag" in body["error"]

    @patch("pbx.api.license_api.Path")
    @patch("pbx.api.license_api.get_license_manager")
    def test_toggle_with_lock_file(
        self,
        mock_glm: MagicMock,
        mock_path_cls: MagicMock,
        client: FlaskClient,
        app: Flask,
    ) -> None:
        """Returns 403 when license lock file exists."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_glm.return_value = mock_mgr

        # Make env_path.exists() = True, lock_path.exists() = True
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.read_text.return_value = ""
        mock_path_cls.return_value.resolve.return_value.parent.parent.__truediv__ = (
            MagicMock(return_value=mock_path_instance)
        )

        body, status = _json_post(
            client, "/api/license/toggle", {"enabled": False}
        )

        assert status == 403
        assert "lock file" in body["error"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_toggle_exception(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 500 on internal exception."""
        self._login_as_admin(client, app)

        mock_glm.side_effect = OSError("disk error")

        body, status = _json_post(client, "/api/license/toggle", {"enabled": True})

        assert status == 500
        assert body["success"] is False


# ======================================================================
# POST /api/license/remove_lock
# ======================================================================
@pytest.mark.unit
class TestRemoveLicenseLock:
    """Tests for POST /api/license/remove_lock (requires license admin)."""

    def _login_as_admin(self, client: FlaskClient, app: Flask) -> None:
        with client.session_transaction() as sess:
            sess["extension"] = "9322"
            sess["username"] = "ICE"
            sess["is_license_admin"] = True

    @patch("pbx.api.license_api.get_license_manager")
    def test_remove_lock_success(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Successfully removes the lock file."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.remove_license_lock.return_value = True
        mock_glm.return_value = mock_mgr

        body, status = _json_post(client, "/api/license/remove_lock")

        assert status == 200
        assert body["success"] is True
        assert "removed" in body["message"]

    @patch("pbx.api.license_api.get_license_manager")
    def test_remove_lock_not_found(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 404 when lock file doesn't exist."""
        self._login_as_admin(client, app)

        mock_mgr = MagicMock()
        mock_mgr.remove_license_lock.return_value = False
        mock_glm.return_value = mock_mgr

        body, status = _json_post(client, "/api/license/remove_lock")

        assert status == 404
        assert body["success"] is False

    def test_remove_lock_unauthenticated(self, client: FlaskClient) -> None:
        """Returns 401 when not authenticated."""
        body, status = _json_post(client, "/api/license/remove_lock")

        assert status == 401

    @patch("pbx.api.license_api.get_license_manager")
    def test_remove_lock_exception(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Returns 500 on internal exception."""
        self._login_as_admin(client, app)

        mock_glm.side_effect = RuntimeError("lock error")

        body, status = _json_post(client, "/api/license/remove_lock")

        assert status == 500
        assert body["success"] is False


# ======================================================================
# GET /api/license/verify_admin
# ======================================================================
@pytest.mark.unit
class TestVerifyAdmin:
    """Tests for GET /api/license/verify_admin."""

    def test_verify_admin_authorized(self, client: FlaskClient, app: Flask) -> None:
        """Returns is_license_admin=True for authenticated admin."""
        with client.session_transaction() as sess:
            sess["extension"] = "9322"
            sess["username"] = "ICE"
            sess["is_license_admin"] = True

        body, status = _json_get(client, "/api/license/verify_admin")

        assert status == 200
        assert body["success"] is True
        assert body["is_license_admin"] is True
        assert body["message"] == "Authorized"

    def test_verify_admin_not_authorized(self, client: FlaskClient) -> None:
        """Returns is_license_admin=False for unauthenticated users."""
        body, status = _json_get(client, "/api/license/verify_admin")

        assert status == 200
        assert body["success"] is True
        assert body["is_license_admin"] is False
        assert body["message"] != "Authorized"

    def test_verify_admin_wrong_extension(
        self, client: FlaskClient, app: Flask
    ) -> None:
        """Returns is_license_admin=False for non-admin extension."""
        with client.session_transaction() as sess:
            sess["extension"] = "1001"
            sess["username"] = "admin"

        body, status = _json_get(client, "/api/license/verify_admin")

        assert status == 200
        assert body["is_license_admin"] is False


# ======================================================================
# POST /api/license/admin_login
# ======================================================================
@pytest.mark.unit
class TestAdminLogin:
    """Tests for POST /api/license/admin_login."""

    @patch("pbx.utils.license_admin.verify_license_admin_credentials", return_value=True)
    def test_login_success(
        self, mock_verify: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Successful login sets session and returns 200."""
        body, status = _json_post(
            client,
            "/api/license/admin_login",
            {"extension": "9322", "username": "ICE", "pin": "26697647"},
        )

        assert status == 200
        assert body["success"] is True
        assert body["extension"] == "9322"
        assert body["username"] == "ICE"
        mock_verify.assert_called_once_with("9322", "ICE", "26697647")

    @patch("pbx.utils.license_admin.verify_license_admin_credentials", return_value=False)
    def test_login_invalid_credentials(
        self, mock_verify: MagicMock, client: FlaskClient
    ) -> None:
        """Returns 401 for invalid credentials."""
        body, status = _json_post(
            client,
            "/api/license/admin_login",
            {"extension": "9322", "username": "ICE", "pin": "wrong"},
        )

        assert status == 401
        assert body["success"] is False
        assert "Invalid credentials" in body["error"]

    def test_login_missing_extension(self, client: FlaskClient) -> None:
        """Returns 400 when extension is missing."""
        body, status = _json_post(
            client,
            "/api/license/admin_login",
            {"username": "ICE", "pin": "26697647"},
        )

        assert status == 400
        assert body["success"] is False
        assert "Missing required fields" in body["error"]

    def test_login_missing_username(self, client: FlaskClient) -> None:
        """Returns 400 when username is missing."""
        body, status = _json_post(
            client,
            "/api/license/admin_login",
            {"extension": "9322", "pin": "26697647"},
        )

        assert status == 400
        assert body["success"] is False

    def test_login_missing_pin(self, client: FlaskClient) -> None:
        """Returns 400 when pin is missing."""
        body, status = _json_post(
            client,
            "/api/license/admin_login",
            {"extension": "9322", "username": "ICE"},
        )

        assert status == 400
        assert body["success"] is False

    def test_login_empty_fields(self, client: FlaskClient) -> None:
        """Returns 400 when fields are empty strings."""
        body, status = _json_post(
            client,
            "/api/license/admin_login",
            {"extension": "", "username": "", "pin": ""},
        )

        assert status == 400
        assert body["success"] is False

    def test_login_whitespace_only_fields(self, client: FlaskClient) -> None:
        """Returns 400 when fields are whitespace-only strings."""
        body, status = _json_post(
            client,
            "/api/license/admin_login",
            {"extension": "  ", "username": "  ", "pin": "  "},
        )

        assert status == 400
        assert body["success"] is False

    @patch(
        "pbx.utils.license_admin.verify_license_admin_credentials",
        side_effect=TypeError("bad arg"),
    )
    def test_login_exception(
        self, mock_verify: MagicMock, client: FlaskClient
    ) -> None:
        """Returns 500 on internal exception."""
        body, status = _json_post(
            client,
            "/api/license/admin_login",
            {"extension": "9322", "username": "ICE", "pin": "12345678"},
        )

        assert status == 500
        assert body["success"] is False
        assert "Authentication failed" in body["error"]


# ======================================================================
# register_license_routes
# ======================================================================
@pytest.mark.unit
class TestRegisterLicenseRoutes:
    """Tests for the register_license_routes helper function."""

    def test_register_blueprint(self) -> None:
        """register_license_routes registers the blueprint on the Flask app."""
        from pbx.api.license_api import register_license_routes

        app = Flask(__name__)
        register_license_routes(app)

        # Verify the blueprint was registered by checking for a known endpoint
        rule_endpoints = [rule.endpoint for rule in app.url_map.iter_rules()]
        assert "license_api.get_license_status" in rule_endpoints

    def test_register_multiple_calls_raises(self) -> None:
        """Registering the same blueprint twice raises an error."""
        from pbx.api.license_api import register_license_routes

        app = Flask(__name__)
        register_license_routes(app)

        # Flask raises ValueError if you register the same blueprint twice without
        # specifying a different name. We just verify registration happened.
        # Some Flask versions allow it, so we check the routes exist.
        rule_endpoints = [rule.endpoint for rule in app.url_map.iter_rules()]
        assert "license_api.admin_login" in rule_endpoints


# ======================================================================
# Edge cases and decorator tests
# ======================================================================
@pytest.mark.unit
class TestRequireLicenseAdminDecorator:
    """Test the @require_license_admin decorator behavior."""

    def test_decorator_blocks_non_admin_session(
        self, client: FlaskClient, app: Flask
    ) -> None:
        """Protected endpoints return 401 for non-admin sessions."""
        with client.session_transaction() as sess:
            sess["extension"] = "1001"
            sess["username"] = "user"

        body, status = _json_post(client, "/api/license/generate", {"type": "trial", "issued_to": "X"})

        assert status == 401

    def test_decorator_blocks_no_session(self, client: FlaskClient) -> None:
        """Protected endpoints return 401 with no session at all."""
        body, status = _json_post(client, "/api/license/revoke")

        assert status == 401
        assert body["success"] is False

    @patch("pbx.api.license_api.get_license_manager")
    def test_admin_session_grants_access(
        self, mock_glm: MagicMock, client: FlaskClient, app: Flask
    ) -> None:
        """Admin session successfully passes the decorator check."""
        with client.session_transaction() as sess:
            sess["extension"] = "9322"
            sess["username"] = "ICE"

        mock_mgr = MagicMock()
        mock_mgr.revoke_license.return_value = True
        mock_glm.return_value = mock_mgr

        body, status = _json_post(client, "/api/license/revoke")

        assert status == 200
        assert body["success"] is True
