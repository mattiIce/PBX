"""Integration tests for the API authentication flow.

Exercises the login endpoint, token-based access to protected routes,
and admin-only endpoint restrictions using the Flask test client
provided by the ``api_client`` fixture in conftest.py.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from pbx.utils.session_token import SessionToken

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_json(
    client: FlaskClient, url: str, data: dict[str, Any], headers: dict[str, str] | None = None
) -> TestResponse:
    """POST JSON to the test client and return the parsed response."""
    all_headers = {"Content-Type": "application/json"}
    if headers:
        all_headers.update(headers)
    resp = client.post(url, data=json.dumps(data), headers=all_headers)
    return resp


def _auth_header(token: str) -> dict[str, str]:
    """Return an Authorization header dict for the given token."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestLoginEndpoint:
    """Test that the /api/auth/login endpoint returns a token."""

    def test_login_returns_token_for_valid_credentials(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """A valid extension + password should yield a token."""
        # Set up extension_db to return a known extension record
        mock_pbx_core.extension_db.get.return_value = {
            "number": "1001",
            "name": "Test User",
            "email": "test@example.com",
            "is_admin": False,
            "voicemail_pin_hash": "1234",
            "voicemail_pin_salt": None,  # plain-text legacy mode
        }

        resp = _post_json(
            api_client,
            "/api/auth/login",
            {
                "extension": "1001",
                "password": "1234",
            },
        )

        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data["success"] is True
        assert "token" in data
        assert data["extension"] == "1001"

    def test_login_rejects_wrong_password(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """An incorrect password should return 401."""
        mock_pbx_core.extension_db.get.return_value = {
            "number": "1001",
            "name": "Test User",
            "email": "test@example.com",
            "is_admin": False,
            "voicemail_pin_hash": "1234",
            "voicemail_pin_salt": None,
        }

        resp = _post_json(
            api_client,
            "/api/auth/login",
            {
                "extension": "1001",
                "password": "wrong-pin",
            },
        )

        assert resp.status_code == 401

    def test_login_rejects_missing_fields(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """Omitting extension or password should return 400."""
        resp = _post_json(
            api_client,
            "/api/auth/login",
            {
                "extension": "1001",
                # no password
            },
        )

        assert resp.status_code == 400

    def test_login_rejects_unknown_extension(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """An extension not in the database should return 401."""
        mock_pbx_core.extension_db.get.return_value = None

        resp = _post_json(
            api_client,
            "/api/auth/login",
            {
                "extension": "9999",
                "password": "1234",
            },
        )

        assert resp.status_code == 401


@pytest.mark.integration
class TestProtectedEndpoints:
    """Test that protected endpoints reject unauthenticated requests."""

    def test_extensions_rejects_no_token(self, api_client: FlaskClient) -> None:
        """GET /api/extensions without a token should return 401."""
        resp = api_client.get("/api/extensions")
        assert resp.status_code == 401

    def test_extensions_rejects_invalid_token(self, api_client: FlaskClient) -> None:
        """A garbage token should be rejected with 401."""
        resp = api_client.get(
            "/api/extensions",
            headers=_auth_header("this.is.not.a.valid.token"),
        )
        assert resp.status_code == 401

    def test_extensions_accepts_valid_token(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """A valid token should grant access to /api/extensions."""
        # First, obtain a real token through the login flow
        mock_pbx_core.extension_db.get.return_value = {
            "number": "1001",
            "name": "Test User",
            "email": "test@example.com",
            "is_admin": False,
            "voicemail_pin_hash": "5678",
            "voicemail_pin_salt": None,
        }

        login_resp = _post_json(
            api_client,
            "/api/auth/login",
            {
                "extension": "1001",
                "password": "5678",
            },
        )
        token = json.loads(login_resp.data)["token"]

        # Now use the token to access a protected endpoint
        resp = api_client.get(
            "/api/extensions",
            headers=_auth_header(token),
        )

        assert resp.status_code == 200


@pytest.mark.integration
class TestAdminOnlyEndpoints:
    """Test that admin-only endpoints reject non-admin users."""

    def _login_as(
        self,
        client: FlaskClient,
        mock_pbx_core: MagicMock,
        extension: str,
        pin: str,
        is_admin: bool,
    ) -> str:
        """Helper: log in and return the token string."""
        mock_pbx_core.extension_db.get.return_value = {
            "number": extension,
            "name": "Test",
            "email": "t@example.com",
            "is_admin": is_admin,
            "voicemail_pin_hash": pin,
            "voicemail_pin_salt": None,
        }
        resp = _post_json(
            client,
            "/api/auth/login",
            {
                "extension": extension,
                "password": pin,
            },
        )
        return json.loads(resp.data)["token"]

    def test_admin_endpoint_rejects_non_admin(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """POST /api/extensions (admin-only) should return 403 for non-admin."""
        token = self._login_as(api_client, mock_pbx_core, "1001", "pin1", is_admin=False)

        resp = _post_json(
            api_client,
            "/api/extensions",
            {"number": "2001", "name": "New Ext"},
            headers=_auth_header(token),
        )

        assert resp.status_code == 403

    def test_admin_endpoint_accepts_admin(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """POST /api/extensions should succeed for an admin user."""
        token = self._login_as(api_client, mock_pbx_core, "1001", "admin-pin", is_admin=True)

        # The actual creation may fail due to missing subsystems, but we
        # should get past the auth check (i.e., NOT 401 or 403).
        resp = _post_json(
            api_client,
            "/api/extensions",
            {"number": "2001", "name": "New Ext"},
            headers=_auth_header(token),
        )

        # Accept any status that is not 401 or 403 -- the important thing
        # is that authentication and authorization passed.
        assert resp.status_code not in (401, 403)

    def test_provisioning_devices_rejects_non_admin(
        self, api_client: FlaskClient, mock_pbx_core: MagicMock
    ) -> None:
        """GET /api/provisioning/devices (admin-only) returns 403 for regular user."""
        token = self._login_as(api_client, mock_pbx_core, "1002", "pin2", is_admin=False)

        resp = api_client.get(
            "/api/provisioning/devices",
            headers=_auth_header(token),
        )

        assert resp.status_code == 403
