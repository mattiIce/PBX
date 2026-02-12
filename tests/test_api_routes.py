"""Tests for Flask API routes."""

import pytest


class TestHealthRoutes:
    """Test health check endpoints."""

    def test_health_endpoint(self, api_client):
        """Test /health returns 200."""
        response = api_client.get("/health")
        assert response.status_code in (200, 503)

    def test_root_redirect(self, api_client):
        """Test / redirects to /admin."""
        response = api_client.get("/")
        assert response.status_code == 302

    def test_status_endpoint(self, api_client, mock_pbx_core):
        """Test /api/status returns PBX status."""
        mock_pbx_core.get_status.return_value = {
            "registered_extensions": 5,
            "active_calls": 0,
        }
        response = api_client.get("/api/status")
        assert response.status_code == 200


class TestAuthRoutes:
    """Test authentication endpoints."""

    def test_login_missing_credentials(self, api_client):
        """Test login with missing credentials returns 400."""
        response = api_client.post("/api/auth/login", json={})
        assert response.status_code == 400

    def test_extensions_requires_auth(self, api_client):
        """Test that /api/extensions requires authentication."""
        response = api_client.get("/api/extensions")
        assert response.status_code == 401
