"""Comprehensive tests for Flask app factory (pbx/api/app.py)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


@pytest.mark.unit
class TestCreateApp:
    """Tests for create_app factory function."""

    def test_creates_flask_app(self) -> None:
        from pbx.api.app import create_app

        app = create_app(None)
        assert isinstance(app, Flask)

    def test_sets_pbx_core_in_config(self, mock_pbx_core: MagicMock) -> None:
        from pbx.api.app import create_app

        app = create_app(mock_pbx_core)
        assert app.config["PBX_CORE"] is mock_pbx_core

    def test_sets_admin_dir(self) -> None:
        from pbx.api.app import create_app

        app = create_app(None)
        assert "ADMIN_DIR" in app.config
        assert "admin" in app.config["ADMIN_DIR"]

    def test_none_pbx_core(self) -> None:
        from pbx.api.app import create_app

        app = create_app(None)
        assert app.config["PBX_CORE"] is None

    def test_no_static_folder(self) -> None:
        from pbx.api.app import create_app

        app = create_app(None)
        assert app.static_folder is None

    def test_security_headers_added(self, mock_pbx_core: MagicMock) -> None:
        from pbx.api.app import create_app

        app = create_app(mock_pbx_core)
        app.config["TESTING"] = True

        with app.test_client() as client:
            # Use a known route; the health endpoint is simple
            resp = client.get("/api/health")
            assert resp.headers.get("X-Content-type-Options") == "nosniff"
            assert resp.headers.get("X-Frame-Options") == "DENY"
            assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
            assert "strict-origin-when-cross-origin" in resp.headers.get("Referrer-Policy", "")
            assert "Access-Control-Allow-Origin" in resp.headers
            assert "Content-Security-Policy" in resp.headers
            assert "Permissions-Policy" in resp.headers

    def test_cors_headers(self, mock_pbx_core: MagicMock) -> None:
        from pbx.api.app import create_app

        app = create_app(mock_pbx_core)
        app.config["TESTING"] = True

        with app.test_client() as client:
            resp = client.get("/api/health")
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"
            assert "GET" in resp.headers.get("Access-Control-Allow-Methods", "")
            assert "POST" in resp.headers.get("Access-Control-Allow-Methods", "")
            assert "PUT" in resp.headers.get("Access-Control-Allow-Methods", "")
            assert "DELETE" in resp.headers.get("Access-Control-Allow-Methods", "")

    def test_error_handler_404(self, mock_pbx_core: MagicMock) -> None:
        from pbx.api.app import create_app

        app = create_app(mock_pbx_core)
        app.config["TESTING"] = True

        with app.test_client() as client:
            resp = client.get("/api/nonexistent-route-xyz")
            assert resp.status_code == 404
            data = json.loads(resp.data)
            assert "error" in data

    def test_error_handler_405(self, mock_pbx_core: MagicMock) -> None:
        from pbx.api.app import create_app

        app = create_app(mock_pbx_core)
        app.config["TESTING"] = True

        with app.test_client() as client:
            # /health only supports GET, so DELETE should be 405
            resp = client.delete("/health")
            assert resp.status_code == 405
            data = json.loads(resp.data)
            assert "error" in data


@pytest.mark.unit
class TestRegisterBlueprints:
    """Tests for blueprint registration."""

    def test_all_blueprints_registered(self, mock_pbx_core: MagicMock) -> None:
        from pbx.api.app import create_app

        app = create_app(mock_pbx_core)

        expected_blueprints = [
            "health",
            "auth",
            "extensions",
            "calls",
            "provisioning",
            "phones",
            "config",
            "voicemail",
            "webrtc",
            "integrations",
            "phone_book",
            "paging",
            "webhooks",
            "emergency",
            "security",
            "qos",
            "features",
            "framework",
            "static_files",
            "license",
            "compat",
            "docs",
        ]

        registered = set(app.blueprints.keys())
        for bp_name in expected_blueprints:
            assert bp_name in registered, f"Blueprint '{bp_name}' not registered"

    def test_has_provisioning_routes(self, mock_pbx_core: MagicMock) -> None:
        from pbx.api.app import create_app

        app = create_app(mock_pbx_core)

        # Verify a sample of known routes exist
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/api/provisioning/devices" in rules
        assert "/api/extensions" in rules
        assert "/health" in rules


@pytest.mark.unit
class TestAdminDir:
    """Tests for ADMIN_DIR constant."""

    def test_admin_dir_is_absolute(self) -> None:
        from pbx.api.app import ADMIN_DIR

        assert ADMIN_DIR.startswith("/")

    def test_admin_dir_ends_with_admin(self) -> None:
        from pbx.api.app import ADMIN_DIR

        assert ADMIN_DIR.endswith("admin")
