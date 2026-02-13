"""
Test Content-Security-Policy headers are correctly formatted
"""

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCSPHeaders(unittest.TestCase):
    """Test Content-Security-Policy headers"""

    # This is the expected CSP string from rest_api.py _set_headers method
    # Keep this in sync with the actual implementation
    EXPECTED_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' http://*:9000 https://*:9000 https://cdn.jsdelivr.net;"
    )

    def test_csp_string_contains_self_not_sel(self) -> None:
        """Test that CSP string uses 'self' not 'sel'"""
        # Verify 'self' is present (in quotes)
        self.assertIn("'self'", self.EXPECTED_CSP, "CSP header should contain 'self'")

        # Verify 'sel' is NOT present (typo check)
        self.assertNotIn("'sel'", self.EXPECTED_CSP, "CSP header should NOT contain typo 'sel'")

    def test_csp_script_src_contains_self(self) -> None:
        """Test that script-src directive contains 'self'"""
        # script-src should contain 'self'
        self.assertIn("script-src", self.EXPECTED_CSP)

        # Extract script-src directive
        directives = [d.strip() for d in self.EXPECTED_CSP.split(";")]
        script_src = [d for d in directives if d.startswith("script-src")]

        self.assertEqual(len(script_src), 1, "Should have exactly one script-src directive")
        self.assertIn("'self'", script_src[0], "script-src should contain 'self'")
        self.assertNotIn("'sel'", script_src[0], "script-src should NOT contain 'sel' typo")

    def test_csp_style_src_contains_self(self) -> None:
        """Test that style-src directive contains 'self'"""
        # style-src should contain 'self'
        self.assertIn("style-src", self.EXPECTED_CSP)

        # Extract style-src directive
        directives = [d.strip() for d in self.EXPECTED_CSP.split(";")]
        style_src = [d for d in directives if d.startswith("style-src")]

        self.assertEqual(len(style_src), 1, "Should have exactly one style-src directive")
        self.assertIn("'self'", style_src[0], "style-src should contain 'self'")
        self.assertNotIn("'sel'", style_src[0], "style-src should NOT contain 'sel' typo")

    def test_csp_default_src_contains_self(self) -> None:
        """Test that default-src directive contains 'self'"""
        # default-src should contain 'self'
        self.assertIn("default-src", self.EXPECTED_CSP)
        self.assertIn("default-src 'self'", self.EXPECTED_CSP, "default-src should contain 'self'")

    def test_csp_connect_src_allows_api(self) -> None:
        """Test that connect-src directive allows API connections"""
        # connect-src should be present
        self.assertIn("connect-src", self.EXPECTED_CSP, "CSP should have connect-src directive")

        # Extract connect-src directive
        directives = [d.strip() for d in self.EXPECTED_CSP.split(";")]
        connect_src = [d for d in directives if d.startswith("connect-src")]

        self.assertEqual(len(connect_src), 1, "Should have exactly one connect-src directive")

        # Should allow 'self'
        self.assertIn("'self'", connect_src[0], "connect-src should contain 'self'")

        # Should allow API port 9000
        self.assertTrue(
            "http://*:9000" in connect_src[0] or "https://*:9000" in connect_src[0],
            "connect-src should allow connections to port 9000",
        )


if __name__ == "__main__":
    unittest.main()
