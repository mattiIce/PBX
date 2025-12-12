"""
Test Phase 3 Authentication and Authorization
"""
import unittest
from unittest.mock import MagicMock, patch

from pbx.utils.session_token import SessionToken, get_session_token_manager


class TestSessionToken(unittest.TestCase):
    """Test session token generation and verification"""

    def setUp(self):
        """Set up test session token manager"""
        self.token_manager = SessionToken(secret_key="test_secret_key_32_bytes_long!")

    def test_generate_token(self):
        """Test token generation"""
        token = self.token_manager.generate_token(
            extension="1001",
            is_admin=True,
            name="Admin User",
            email="admin@example.com"
        )
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        # Token should have 3 parts separated by dots (header.payload.signature)
        self.assertEqual(len(token.split('.')), 3)

    def test_verify_valid_token(self):
        """Test verification of valid token"""
        token = self.token_manager.generate_token(
            extension="1001",
            is_admin=True,
            name="Admin User"
        )
        
        is_valid, payload = self.token_manager.verify_token(token)
        
        self.assertTrue(is_valid)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['extension'], "1001")
        self.assertTrue(payload['is_admin'])
        self.assertEqual(payload['name'], "Admin User")

    def test_verify_invalid_signature(self):
        """Test verification fails with tampered token"""
        token = self.token_manager.generate_token(
            extension="1001",
            is_admin=False,
            name="Regular User"
        )
        
        # Tamper with the token
        parts = token.split('.')
        tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"
        
        is_valid, payload = self.token_manager.verify_token(tampered_token)
        
        self.assertFalse(is_valid)
        self.assertIsNone(payload)

    def test_verify_malformed_token(self):
        """Test verification fails with malformed token"""
        is_valid, payload = self.token_manager.verify_token("not.a.valid.token.format")
        
        self.assertFalse(is_valid)
        self.assertIsNone(payload)

    def test_admin_vs_regular_user(self):
        """Test distinguishing admin from regular user"""
        admin_token = self.token_manager.generate_token(
            extension="1001",
            is_admin=True,
            name="Admin"
        )
        
        user_token = self.token_manager.generate_token(
            extension="1002",
            is_admin=False,
            name="User"
        )
        
        _, admin_payload = self.token_manager.verify_token(admin_token)
        _, user_payload = self.token_manager.verify_token(user_token)
        
        self.assertTrue(admin_payload['is_admin'])
        self.assertFalse(user_payload['is_admin'])

    def test_extract_extension(self):
        """Test extracting extension from token"""
        token = self.token_manager.generate_token(
            extension="1001",
            is_admin=True
        )
        
        extension = self.token_manager.extract_extension(token)
        self.assertEqual(extension, "1001")

    def test_global_token_manager(self):
        """Test global token manager singleton"""
        manager1 = get_session_token_manager()
        manager2 = get_session_token_manager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)


class TestAuthenticationEndpoint(unittest.TestCase):
    """Test authentication API endpoint"""

    @patch('pbx.api.rest_api.PBXAPIHandler')
    def test_login_success(self, mock_handler):
        """Test successful login"""
        # This is a placeholder - actual integration test would require
        # full PBX initialization and database
        # For now, we verify the token generation works
        
        token_manager = SessionToken(secret_key="test_key")
        token = token_manager.generate_token(
            extension="1001",
            is_admin=True,
            name="Test User",
            email="test@example.com"
        )
        
        is_valid, payload = token_manager.verify_token(token)
        
        self.assertTrue(is_valid)
        self.assertEqual(payload['extension'], "1001")
        self.assertTrue(payload['is_admin'])

    def test_authorization_levels(self):
        """Test different authorization levels"""
        token_manager = SessionToken(secret_key="test_key")
        
        # Admin user
        admin_token = token_manager.generate_token(
            extension="1001",
            is_admin=True,
            name="Admin"
        )
        
        # Regular user
        user_token = token_manager.generate_token(
            extension="1002",
            is_admin=False,
            name="User"
        )
        
        # Verify admin token
        is_valid, admin_payload = token_manager.verify_token(admin_token)
        self.assertTrue(is_valid)
        self.assertTrue(admin_payload['is_admin'])
        
        # Verify user token
        is_valid, user_payload = token_manager.verify_token(user_token)
        self.assertTrue(is_valid)
        self.assertFalse(user_payload['is_admin'])


if __name__ == '__main__':
    unittest.main()
