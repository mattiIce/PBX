#!/usr/bin/env python3
"""Test license admin login functionality.

Note: The license admin credentials (extension 9322, username ICE, PIN 26697647)
are documented in multiple places in the codebase including:
- LICENSE_ADMIN_QUICKREF.md
- LICENSE_ADMIN_INTERFACE.md
- IMPLEMENTATION_SUMMARY_LICENSE_ADMIN.md
- pbx/utils/license_admin.py

These are not secret credentials but system defaults that can be verified
through the triple-layer encryption system (SHA256, PBKDF2, HMAC).
"""

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.utils.license_admin import (
    LICENSE_ADMIN_EXTENSION,
    LICENSE_ADMIN_USERNAME,
    is_license_admin_extension,
    verify_license_admin_credentials,
)


class TestLicenseAdminLogin(unittest.TestCase):
    """Test license admin authentication."""

    def test_is_license_admin_extension(self):
        """Test identifying the license admin extension."""
        self.assertTrue(is_license_admin_extension("9322"))
        self.assertFalse(is_license_admin_extension("1001"))
        self.assertFalse(is_license_admin_extension(""))

    def test_license_admin_credentials_valid(self):
        """Test license admin login with valid credentials."""
        # Valid credentials
        result = verify_license_admin_credentials(
            extension="9322", username="ICE", pin="26697647"
        )
        self.assertTrue(result, "License admin login should succeed with correct credentials")

    def test_license_admin_credentials_case_insensitive_username(self):
        """Test that username is case insensitive."""
        # Test lowercase
        result = verify_license_admin_credentials(
            extension="9322", username="ice", pin="26697647"
        )
        self.assertTrue(result, "License admin login should succeed with lowercase username")

        # Test mixed case
        result = verify_license_admin_credentials(
            extension="9322", username="Ice", pin="26697647"
        )
        self.assertTrue(result, "License admin login should succeed with mixed case username")

    def test_license_admin_credentials_wrong_extension(self):
        """Test license admin login with wrong extension."""
        result = verify_license_admin_credentials(
            extension="1001", username="ICE", pin="26697647"
        )
        self.assertFalse(result, "License admin login should fail with wrong extension")

    def test_license_admin_credentials_wrong_username(self):
        """Test license admin login with wrong username."""
        result = verify_license_admin_credentials(
            extension="9322", username="ADMIN", pin="26697647"
        )
        self.assertFalse(result, "License admin login should fail with wrong username")

    def test_license_admin_credentials_wrong_pin(self):
        """Test license admin login with wrong PIN."""
        result = verify_license_admin_credentials(
            extension="9322", username="ICE", pin="00000000"
        )
        self.assertFalse(result, "License admin login should fail with wrong PIN")

    def test_license_admin_credentials_empty_fields(self):
        """Test license admin login with empty fields."""
        result = verify_license_admin_credentials(
            extension="", username="ICE", pin="26697647"
        )
        self.assertFalse(result, "License admin login should fail with empty extension")

        result = verify_license_admin_credentials(
            extension="9322",
            username="",
            pin="26697647"
        )
        self.assertFalse(result, "License admin login should fail with empty username")


if __name__ == '__main__':
    unittest.main()
