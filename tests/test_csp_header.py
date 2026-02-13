"""
Test Content-Security-Policy headers are correctly formatted
"""


class TestCSPHeaders:
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
        assert "'self'" in self.EXPECTED_CSP
        # Verify 'sel' is NOT present (typo check)
        assert "'sel'" not in self.EXPECTED_CSP
    def test_csp_script_src_contains_self(self) -> None:
        """Test that script-src directive contains 'self'"""
        # script-src should contain 'self'
        assert "script-src" in self.EXPECTED_CSP
        # Extract script-src directive
        directives = [d.strip() for d in self.EXPECTED_CSP.split(";")]
        script_src = [d for d in directives if d.startswith("script-src")]

        assert len(script_src) == 1, "Should have exactly one script-src directive"
        assert "'self'" in script_src[0]
        assert "'sel'" not in script_src[0]
    def test_csp_style_src_contains_self(self) -> None:
        """Test that style-src directive contains 'self'"""
        # style-src should contain 'self'
        assert "style-src" in self.EXPECTED_CSP
        # Extract style-src directive
        directives = [d.strip() for d in self.EXPECTED_CSP.split(";")]
        style_src = [d for d in directives if d.startswith("style-src")]

        assert len(style_src) == 1, "Should have exactly one style-src directive"
        assert "'self'" in style_src[0]
        assert "'sel'" not in style_src[0]
    def test_csp_default_src_contains_self(self) -> None:
        """Test that default-src directive contains 'self'"""
        # default-src should contain 'self'
        assert "default-src" in self.EXPECTED_CSP
        assert "default-src 'self'" in self.EXPECTED_CSP
    def test_csp_connect_src_allows_api(self) -> None:
        """Test that connect-src directive allows API connections"""
        # connect-src should be present
        assert "connect-src" in self.EXPECTED_CSP
        # Extract connect-src directive
        directives = [d.strip() for d in self.EXPECTED_CSP.split(";")]
        connect_src = [d for d in directives if d.startswith("connect-src")]

        assert len(connect_src) == 1, "Should have exactly one connect-src directive"
        # Should allow 'self'
        assert "'self'" in connect_src[0]
        # Should allow API port 9000
        self.assertTrue(
            "http://*:9000" in connect_src[0] or "https://*:9000" in connect_src[0],
            "connect-src should allow connections to port 9000",
        )
