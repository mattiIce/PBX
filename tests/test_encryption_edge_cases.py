"""
Test encryption edge cases for authentication
"""

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.encryption import FIPSEncryption


class TestEncryptionEdgeCases(unittest.TestCase):
    """Test encryption utility edge cases"""

    def setUp(self):
        """Set up test encryption instance"""
        self.encryption = FIPSEncryption(fips_mode=False)

    def test_verify_password_with_none_inputs(self):
        """Test that verify_password handles None inputs gracefully"""
        # Hash a valid password first
        password = "test123"
        hashed, salt = self.encryption.hash_password(password)

        # Test None password
        result = self.encryption.verify_password(None, hashed, salt)
        self.assertFalse(result)

        # Test None hash
        result = self.encryption.verify_password(password, None, salt)
        self.assertFalse(result)

        # Test None salt
        result = self.encryption.verify_password(password, hashed, None)
        self.assertFalse(result)

    def test_verify_password_with_empty_strings(self):
        """Test that verify_password handles empty strings gracefully"""
        # Hash a valid password first
        password = "test123"
        hashed, salt = self.encryption.hash_password(password)

        # Test empty password
        result = self.encryption.verify_password("", hashed, salt)
        self.assertFalse(result)

        # Test empty hash
        result = self.encryption.verify_password(password, "", salt)
        self.assertFalse(result)

        # Test empty salt
        result = self.encryption.verify_password(password, hashed, "")
        self.assertFalse(result)

    def test_verify_password_with_invalid_base64(self):
        """Test that verify_password handles invalid base64 encoding gracefully"""
        password = "test123"
        _, salt = self.encryption.hash_password(password)

        # Test invalid base64 in hash
        result = self.encryption.verify_password(password, "not-valid-base64!", salt)
        self.assertFalse(result)

        # Test invalid base64 in salt
        hashed, _ = self.encryption.hash_password(password)
        result = self.encryption.verify_password(password, hashed, "not-valid-base64!")
        self.assertFalse(result)

    def test_verify_password_correct_credentials(self):
        """Test that verify_password works correctly with valid inputs"""
        password = "test123"
        hashed, salt = self.encryption.hash_password(password)

        # Correct password should verify
        result = self.encryption.verify_password(password, hashed, salt)
        self.assertTrue(result)

        # Wrong password should not verify
        result = self.encryption.verify_password("wrongpassword", hashed, salt)
        self.assertFalse(result)

    def test_verify_password_no_exceptions(self):
        """Test that verify_password never raises exceptions"""
        test_cases = [
            (None, None, None),
            ("", "", ""),
            ("password", None, None),
            (None, "hash", "salt"),
            ("password", "invalid-base64!", "salt"),
            ("password", "hash", "invalid-base64!"),
        ]

        for password, hashed, salt in test_cases:
            try:
                # Should not raise any exceptions
                result = self.encryption.verify_password(password, hashed, salt)
                # Result should always be False for invalid inputs
                self.assertFalse(result)
            except Exception as e:
                self.fail(
                    f"verify_password raised an exception for inputs ({password}, {hashed}, {salt}): {e}"
                )


if __name__ == "__main__":
    unittest.main()
