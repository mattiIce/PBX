"""
Test Phase 3 Authentication and Authorization
"""

import unittest
from unittest.mock import MagicMock, patch


from pbx.utils.session_token import SessionToken, get_session_token_manager


class TestSessionToken:
    """Test session token generation and verification"""

    def setup_method(self) -> None:
        """Set up test session token manager"""
        self.token_manager = SessionToken(secret_key="test_secret_key_32_bytes_long!")

    def test_generate_token(self) -> None:
        """Test token generation"""
        token = self.token_manager.generate_token(
            extension="1001", is_admin=True, name="Admin User", email="admin@example.com"
        )

        assert token is not None
        assert isinstance(token, str)
        # Token should have 3 parts separated by dots (header.payload.signature)
        assert len(token.split(".")) == 3

    def test_verify_valid_token(self) -> None:
        """Test verification of valid token"""
        token = self.token_manager.generate_token(
            extension="1001", is_admin=True, name="Admin User"
        )

        is_valid, payload = self.token_manager.verify_token(token)

        assert is_valid
        assert payload is not None
        assert payload["extension"] == "1001"
        assert payload["is_admin"]
        assert payload["name"] == "Admin User"

    def test_verify_invalid_signature(self) -> None:
        """Test verification fails with tampered token"""
        token = self.token_manager.generate_token(
            extension="1001", is_admin=False, name="Regular User"
        )

        # Tamper with the token
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"

        is_valid, payload = self.token_manager.verify_token(tampered_token)

        assert not is_valid
        assert payload is None

    def test_verify_malformed_token(self) -> None:
        """Test verification fails with malformed token"""
        is_valid, payload = self.token_manager.verify_token("not.a.valid.token.format")

        assert not is_valid
        assert payload is None

    def test_admin_vs_regular_user(self) -> None:
        """Test distinguishing admin from regular user"""
        admin_token = self.token_manager.generate_token(
            extension="1001", is_admin=True, name="Admin"
        )

        user_token = self.token_manager.generate_token(
            extension="1002", is_admin=False, name="User"
        )

        _, admin_payload = self.token_manager.verify_token(admin_token)
        _, user_payload = self.token_manager.verify_token(user_token)

        assert admin_payload["is_admin"]
        assert not user_payload["is_admin"]

    def test_extract_extension(self) -> None:
        """Test extracting extension from token"""
        token = self.token_manager.generate_token(extension="1001", is_admin=True)

        extension = self.token_manager.extract_extension(token)
        assert extension == "1001"

    def test_global_token_manager(self) -> None:
        """Test global token manager singleton"""
        manager1 = get_session_token_manager()
        manager2 = get_session_token_manager()

        # Should be the same instance
        assert manager1 is manager2

    def test_auto_generated_key_entropy(self) -> None:
        """Test that auto-generated secret keys have sufficient entropy"""
        # Create a token manager with auto-generated key
        manager = SessionToken()

        # Verify key has sufficient length (32 bytes minimum for security)
        assert len(manager.secret_key) >= 32
        # Create multiple managers and verify they generate different keys
        manager2 = SessionToken()
        assert manager.secret_key != manager2.secret_key

class TestAuthenticationEndpoint:
    """Test authentication API endpoint"""

    @patch("pbx.api.rest_api.PBXAPIHandler")

    def test_login_success(self, mock_handler: MagicMock) -> None:
        """Test successful login"""
        # This is a placeholder - actual integration test would require
        # full PBX initialization and database
        # For now, we verify the token generation works

        token_manager = SessionToken(secret_key="test_key")
        token = token_manager.generate_token(
            extension="1001", is_admin=True, name="Test User", email="test@example.com"
        )

        is_valid, payload = token_manager.verify_token(token)

        assert is_valid
        assert payload["extension"] == "1001"
        assert payload["is_admin"]

    def test_authorization_levels(self) -> None:
        """Test different authorization levels"""
        token_manager = SessionToken(secret_key="test_key")

        # Admin user
        admin_token = token_manager.generate_token(extension="1001", is_admin=True, name="Admin")

        # Regular user
        user_token = token_manager.generate_token(extension="1002", is_admin=False, name="User")

        # Verify admin token
        is_valid, admin_payload = token_manager.verify_token(admin_token)
        assert is_valid
        assert admin_payload["is_admin"]
        # Verify user token
        is_valid, user_payload = token_manager.verify_token(user_token)
        assert is_valid
        assert not user_payload["is_admin"]
