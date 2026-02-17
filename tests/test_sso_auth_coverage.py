#!/usr/bin/env python3
"""
Comprehensive tests for SSO Authentication service (pbx/features/sso_auth.py)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestSSOAuthServiceInit:
    """Tests for SSOAuthService initialization"""

    def test_init_defaults_no_config(self) -> None:
        """Test initialization with no config"""
        with patch("pbx.features.sso_auth.get_logger"):
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService()

        assert service.enabled is False
        assert service.provider == "saml"
        assert service.session_timeout == 3600
        assert service.active_sessions == {}
        assert service.oauth_client_id is None
        assert service.oauth_client_secret is None
        assert service.oauth_provider_url is None
        assert service.saml_settings == {}

    def test_init_with_none_config(self) -> None:
        """Test initialization with explicit None config"""
        with patch("pbx.features.sso_auth.get_logger"):
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService(config=None)

        assert service.config == {}
        assert service.enabled is False

    def test_init_with_empty_config(self) -> None:
        """Test initialization with empty config dict"""
        with patch("pbx.features.sso_auth.get_logger"):
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService(config={})

        assert service.enabled is False
        assert service.provider == "saml"

    def test_init_enabled_saml_provider(self) -> None:
        """Test initialization with SAML provider enabled"""
        config = {
            "features": {
                "sso": {
                    "enabled": True,
                    "provider": "saml",
                    "session_timeout": 7200,
                    "saml_settings": {"idp_url": "https://idp.example.com"},
                }
            }
        }
        with patch("pbx.features.sso_auth.get_logger") as mock_logger_fn:
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService(config=config)

        assert service.enabled is True
        assert service.provider == "saml"
        assert service.session_timeout == 7200
        assert service.saml_settings == {"idp_url": "https://idp.example.com"}
        mock_logger.info.assert_any_call("SSO authentication service initialized")

    def test_init_enabled_oauth_provider(self) -> None:
        """Test initialization with OAuth provider enabled"""
        config = {
            "features": {
                "sso": {
                    "enabled": True,
                    "provider": "oauth",
                    "oauth_client_id": "client123",
                    "oauth_client_secret": "secret456",
                    "oauth_provider_url": "https://auth.example.com",
                }
            }
        }
        with patch("pbx.features.sso_auth.get_logger"):
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService(config=config)

        assert service.enabled is True
        assert service.provider == "oauth"
        assert service.oauth_client_id == "client123"
        assert service.oauth_client_secret == "secret456"
        assert service.oauth_provider_url == "https://auth.example.com"

    def test_init_enabled_oidc_provider(self) -> None:
        """Test initialization with OIDC provider"""
        config = {
            "features": {
                "sso": {
                    "enabled": True,
                    "provider": "oidc",
                }
            }
        }
        with patch("pbx.features.sso_auth.get_logger"):
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService(config=config)

        assert service.provider == "oidc"

    def test_init_saml_not_available_warning(self) -> None:
        """Test warning when SAML library not available"""
        config = {
            "features": {
                "sso": {
                    "enabled": True,
                    "provider": "saml",
                }
            }
        }
        with (
            patch("pbx.features.sso_auth.get_logger") as mock_logger_fn,
            patch("pbx.features.sso_auth.SAML_AVAILABLE", False),
        ):
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService(config=config)

        assert service.enabled is True
        mock_logger.warning.assert_called_once_with(
            "SAML provider selected but python3-saml not installed"
        )

    def test_init_disabled_no_warnings(self) -> None:
        """Test that disabled SSO does not produce info or warning logs"""
        config = {
            "features": {
                "sso": {
                    "enabled": False,
                    "provider": "saml",
                }
            }
        }
        with patch("pbx.features.sso_auth.get_logger") as mock_logger_fn:
            mock_logger = MagicMock()
            mock_logger_fn.return_value = mock_logger
            from pbx.features.sso_auth import SSOAuthService

            SSOAuthService(config=config)

        # Should NOT log "SSO authentication service initialized"
        for call in mock_logger.info.call_args_list:
            assert "SSO authentication service initialized" not in str(call)


@pytest.mark.unit
class TestSSOAuthServiceSAML:
    """Tests for SAML authentication methods"""

    def _make_service(self, enabled=True, provider="saml", saml_available=True, **kwargs):
        """Helper to create configured SSO service"""
        config = {
            "features": {
                "sso": {
                    "enabled": enabled,
                    "provider": provider,
                    "saml_settings": kwargs.get(
                        "saml_settings", {"idp_url": "https://idp.example.com"}
                    ),
                    **kwargs,
                }
            }
        }
        with (
            patch("pbx.features.sso_auth.get_logger") as mock_logger_fn,
            patch("pbx.features.sso_auth.SAML_AVAILABLE", saml_available),
        ):
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.sso_auth import SSOAuthService

            return SSOAuthService(config=config)

    def test_initiate_saml_auth_success(self) -> None:
        """Test successful SAML auth initiation"""
        service = self._make_service()
        result = service.initiate_saml_auth({"callback_url": "/my/callback"})

        assert "auth_url" in result
        assert "request_id" in result
        assert "callback_url" in result
        assert result["auth_url"] == "https://idp.example.com/sso"
        assert result["callback_url"] == "/my/callback"
        assert len(result["request_id"]) > 0

    def test_initiate_saml_auth_default_callback(self) -> None:
        """Test SAML auth with default callback URL"""
        service = self._make_service()
        result = service.initiate_saml_auth({})

        assert result["callback_url"] == "/auth/saml/callback"

    def test_initiate_saml_auth_not_enabled(self) -> None:
        """Test SAML auth when SSO not enabled"""
        service = self._make_service(enabled=False)
        result = service.initiate_saml_auth({})

        assert result == {"error": "SAML not enabled"}

    def test_initiate_saml_auth_wrong_provider(self) -> None:
        """Test SAML auth when provider is oauth"""
        service = self._make_service(provider="oauth")
        result = service.initiate_saml_auth({})

        assert result == {"error": "SAML not enabled"}

    def test_initiate_saml_auth_library_not_available(self) -> None:
        """Test SAML auth when library not available"""
        service = self._make_service(saml_available=False)
        with patch("pbx.features.sso_auth.SAML_AVAILABLE", False):
            result = service.initiate_saml_auth({})

        assert result == {"error": "SAML library not available"}

    def test_initiate_saml_auth_empty_idp_url(self) -> None:
        """Test SAML auth with empty IDP URL"""
        service = self._make_service(saml_settings={})
        result = service.initiate_saml_auth({})

        assert result["auth_url"] == "/sso"

    def test_handle_saml_response_success(self) -> None:
        """Test successful SAML response handling"""
        service = self._make_service()
        result = service.handle_saml_response("<saml>response</saml>")

        assert "session_id" in result
        assert "user_info" in result
        assert result["user_info"]["user_id"] == "user@example.com"
        assert result["user_info"]["email"] == "user@example.com"
        assert result["user_info"]["name"] == "John Doe"
        assert "admins" in result["user_info"]["groups"]
        # Session should be stored
        assert result["session_id"] in service.active_sessions

    def test_handle_saml_response_not_enabled(self) -> None:
        """Test SAML response when SSO disabled"""
        service = self._make_service(enabled=False)
        result = service.handle_saml_response("<saml>response</saml>")

        assert result == {"error": "SAML not enabled"}

    def test_handle_saml_response_wrong_provider(self) -> None:
        """Test SAML response when provider is oauth"""
        service = self._make_service(provider="oauth")
        result = service.handle_saml_response("<saml>response</saml>")

        assert result == {"error": "SAML not enabled"}


@pytest.mark.unit
class TestSSOAuthServiceOAuth:
    """Tests for OAuth authentication methods"""

    def _make_service(self, enabled=True, provider="oauth", **kwargs):
        """Helper to create configured SSO service"""
        config = {
            "features": {
                "sso": {
                    "enabled": enabled,
                    "provider": provider,
                    "oauth_client_id": kwargs.get("oauth_client_id", "client123"),
                    "oauth_client_secret": kwargs.get("oauth_client_secret", "secret456"),
                    "oauth_provider_url": kwargs.get(
                        "oauth_provider_url", "https://auth.example.com"
                    ),
                    **kwargs,
                }
            }
        }
        with patch("pbx.features.sso_auth.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.sso_auth import SSOAuthService

            return SSOAuthService(config=config)

    def test_initiate_oauth_auth_success(self) -> None:
        """Test successful OAuth auth initiation"""
        service = self._make_service()
        result = service.initiate_oauth_auth("https://myapp.com/callback")

        assert "auth_url" in result
        assert "state" in result
        assert "client123" in result["auth_url"]
        assert "https://myapp.com/callback" in result["auth_url"]
        assert "openid profile email" in result["auth_url"]
        assert result["state"] in result["auth_url"]
        assert result["auth_url"].startswith("https://auth.example.com/authorize")

    def test_initiate_oauth_auth_not_enabled(self) -> None:
        """Test OAuth auth when SSO not enabled"""
        service = self._make_service(enabled=False)
        result = service.initiate_oauth_auth("https://myapp.com/callback")

        assert result == {"error": "OAuth not enabled"}

    def test_initiate_oauth_auth_wrong_provider(self) -> None:
        """Test OAuth auth when provider is saml"""
        service = self._make_service(provider="saml")
        result = service.initiate_oauth_auth("https://myapp.com/callback")

        assert result == {"error": "OAuth not enabled"}

    def test_handle_oauth_callback_success(self) -> None:
        """Test successful OAuth callback handling"""
        service = self._make_service()
        result = service.handle_oauth_callback("auth_code_123", "state_abc")

        assert "session_id" in result
        assert "user_info" in result
        assert result["user_info"]["user_id"] == "user@example.com"
        assert result["session_id"] in service.active_sessions

    def test_handle_oauth_callback_not_enabled(self) -> None:
        """Test OAuth callback when SSO disabled"""
        service = self._make_service(enabled=False)
        result = service.handle_oauth_callback("code", "state")

        assert result == {"error": "OAuth not enabled"}

    def test_handle_oauth_callback_wrong_provider(self) -> None:
        """Test OAuth callback when provider is saml"""
        service = self._make_service(provider="saml")
        result = service.handle_oauth_callback("code", "state")

        assert result == {"error": "OAuth not enabled"}


@pytest.mark.unit
class TestSSOAuthServiceSessionManagement:
    """Tests for session management methods"""

    def _make_service(self, session_timeout=3600):
        """Helper to create enabled SSO service"""
        config = {
            "features": {
                "sso": {
                    "enabled": True,
                    "provider": "saml",
                    "session_timeout": session_timeout,
                    "saml_settings": {"idp_url": "https://idp.example.com"},
                }
            }
        }
        with patch("pbx.features.sso_auth.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.sso_auth import SSOAuthService

            return SSOAuthService(config=config)

    def test_create_session(self) -> None:
        """Test internal session creation"""
        service = self._make_service()
        user_info = {"user_id": "test@example.com", "name": "Test User"}

        session_id = service._create_session(user_info)

        assert session_id is not None
        assert len(session_id) > 0
        assert session_id in service.active_sessions
        session = service.active_sessions[session_id]
        assert session["user_info"] == user_info
        assert "created_at" in session
        assert "expires_at" in session
        assert "last_activity" in session
        assert session["expires_at"] > session["created_at"]

    def test_validate_session_valid(self) -> None:
        """Test validating a valid session"""
        service = self._make_service()
        user_info = {"user_id": "test@example.com", "name": "Test User"}
        session_id = service._create_session(user_info)

        result = service.validate_session(session_id)

        assert result is not None
        assert result["user_id"] == "test@example.com"

    def test_validate_session_nonexistent(self) -> None:
        """Test validating a nonexistent session"""
        service = self._make_service()

        result = service.validate_session("nonexistent_session_id")

        assert result is None

    def test_validate_session_expired(self) -> None:
        """Test validating an expired session"""
        service = self._make_service(session_timeout=1)
        user_info = {"user_id": "test@example.com"}
        session_id = service._create_session(user_info)

        # Manually set expiry to the past
        service.active_sessions[session_id]["expires_at"] = datetime.now(UTC) - timedelta(
            seconds=10
        )

        result = service.validate_session(session_id)

        assert result is None
        assert session_id not in service.active_sessions

    def test_validate_session_updates_last_activity(self) -> None:
        """Test that validating session updates last_activity"""
        service = self._make_service()
        user_info = {"user_id": "test@example.com"}
        session_id = service._create_session(user_info)

        old_activity = service.active_sessions[session_id]["last_activity"]

        # Small delay so timestamps differ
        import time

        time.sleep(0.01)

        service.validate_session(session_id)
        new_activity = service.active_sessions[session_id]["last_activity"]

        assert new_activity >= old_activity

    def test_logout_existing_session(self) -> None:
        """Test logging out an existing session"""
        service = self._make_service()
        user_info = {"user_id": "test@example.com"}
        session_id = service._create_session(user_info)

        result = service.logout(session_id)

        assert result is True
        assert session_id not in service.active_sessions

    def test_logout_nonexistent_session(self) -> None:
        """Test logging out a nonexistent session"""
        service = self._make_service()

        result = service.logout("nonexistent_session_id")

        assert result is False

    def test_logout_logs_user_id(self) -> None:
        """Test that logout logs the user_id"""
        service = self._make_service()
        user_info = {"user_id": "admin@example.com"}
        session_id = service._create_session(user_info)

        service.logout(session_id)

        service.logger.info.assert_any_call("Logged out SSO session for admin@example.com")

    def test_cleanup_expired_sessions_removes_expired(self) -> None:
        """Test cleanup removes expired sessions"""
        service = self._make_service()

        # Create two sessions, one expired, one valid
        user_info1 = {"user_id": "user1@example.com"}
        user_info2 = {"user_id": "user2@example.com"}
        sid1 = service._create_session(user_info1)
        sid2 = service._create_session(user_info2)

        # Expire the first session
        service.active_sessions[sid1]["expires_at"] = datetime.now(UTC) - timedelta(seconds=10)

        service.cleanup_expired_sessions()

        assert sid1 not in service.active_sessions
        assert sid2 in service.active_sessions

    def test_cleanup_expired_sessions_no_expired(self) -> None:
        """Test cleanup with no expired sessions"""
        service = self._make_service()
        user_info = {"user_id": "user@example.com"}
        sid = service._create_session(user_info)

        service.cleanup_expired_sessions()

        assert sid in service.active_sessions

    def test_cleanup_expired_sessions_all_expired(self) -> None:
        """Test cleanup when all sessions are expired"""
        service = self._make_service()
        user_info1 = {"user_id": "user1@example.com"}
        user_info2 = {"user_id": "user2@example.com"}
        sid1 = service._create_session(user_info1)
        sid2 = service._create_session(user_info2)

        # Expire both sessions
        for sid in [sid1, sid2]:
            service.active_sessions[sid]["expires_at"] = datetime.now(UTC) - timedelta(seconds=10)

        service.cleanup_expired_sessions()

        assert len(service.active_sessions) == 0

    def test_cleanup_expired_sessions_logs_count(self) -> None:
        """Test cleanup logs count of expired sessions"""
        service = self._make_service()
        user_info = {"user_id": "user@example.com"}
        sid = service._create_session(user_info)
        service.active_sessions[sid]["expires_at"] = datetime.now(UTC) - timedelta(seconds=10)

        service.cleanup_expired_sessions()

        service.logger.info.assert_any_call("Cleaned up 1 expired SSO sessions")

    def test_multiple_sessions_created(self) -> None:
        """Test creating multiple sessions"""
        service = self._make_service()
        user_info1 = {"user_id": "user1@example.com"}
        user_info2 = {"user_id": "user2@example.com"}

        sid1 = service._create_session(user_info1)
        sid2 = service._create_session(user_info2)

        assert sid1 != sid2
        assert len(service.active_sessions) == 2


@pytest.mark.unit
class TestSSOAuthServiceStatistics:
    """Tests for get_statistics method"""

    def test_get_statistics_disabled(self) -> None:
        """Test statistics when disabled"""
        with patch("pbx.features.sso_auth.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService()

        stats = service.get_statistics()

        assert stats["enabled"] is False
        assert stats["provider"] == "saml"
        assert stats["active_sessions"] == 0
        assert "saml_available" in stats

    def test_get_statistics_with_sessions(self) -> None:
        """Test statistics with active sessions"""
        config = {
            "features": {
                "sso": {
                    "enabled": True,
                    "provider": "oauth",
                    "saml_settings": {},
                }
            }
        }
        with patch("pbx.features.sso_auth.get_logger") as mock_logger_fn:
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService(config=config)

        service._create_session({"user_id": "u1"})
        service._create_session({"user_id": "u2"})

        stats = service.get_statistics()

        assert stats["enabled"] is True
        assert stats["provider"] == "oauth"
        assert stats["active_sessions"] == 2

    def test_get_statistics_saml_available_flag(self) -> None:
        """Test that statistics includes SAML availability"""
        with (
            patch("pbx.features.sso_auth.get_logger") as mock_logger_fn,
            patch("pbx.features.sso_auth.SAML_AVAILABLE", True),
        ):
            mock_logger_fn.return_value = MagicMock()
            from pbx.features.sso_auth import SSOAuthService

            service = SSOAuthService()

        stats = service.get_statistics()
        assert stats["saml_available"] is True
