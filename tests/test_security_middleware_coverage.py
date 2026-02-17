#!/usr/bin/env python3
"""Comprehensive tests for the security_middleware module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from pbx.utils.security_middleware import (
    RateLimiter,
    RequestValidator,
    SecretValidator,
    SecurityHeaders,
    configure_rate_limiter,
    get_rate_limiter,
)


@pytest.mark.unit
class TestSecurityHeaders:
    """Tests for SecurityHeaders class."""

    def test_security_headers_defined(self) -> None:
        headers = SecurityHeaders.SECURITY_HEADERS
        assert "X-Frame-Options" in headers
        assert "X-Content-type-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Referrer-Policy" in headers
        assert "Content-Security-Policy" in headers
        assert "Permissions-Policy" in headers

    def test_x_frame_options_deny(self) -> None:
        assert SecurityHeaders.SECURITY_HEADERS["X-Frame-Options"] == "DENY"

    def test_x_content_type_nosniff(self) -> None:
        assert SecurityHeaders.SECURITY_HEADERS["X-Content-type-Options"] == "nosniff"

    def test_xss_protection_enabled(self) -> None:
        assert "1; mode=block" in SecurityHeaders.SECURITY_HEADERS["X-XSS-Protection"]

    def test_add_headers_http(self) -> None:
        handler = MagicMock()
        SecurityHeaders.add_headers(handler, is_https=False)

        # Check that standard headers were added
        call_args_list = handler.send_header.call_args_list
        header_names = [call[0][0] for call in call_args_list]

        assert "X-Frame-Options" in header_names
        assert "X-Content-type-Options" in header_names
        assert "X-XSS-Protection" in header_names
        assert "Referrer-Policy" in header_names
        assert "Content-Security-Policy" in header_names
        assert "Permissions-Policy" in header_names
        # HSTS should NOT be added for HTTP
        assert "Strict-Transport-Security" not in header_names

    def test_add_headers_https(self) -> None:
        handler = MagicMock()
        SecurityHeaders.add_headers(handler, is_https=True)

        call_args_list = handler.send_header.call_args_list
        header_names = [call[0][0] for call in call_args_list]

        assert "X-Frame-Options" in header_names
        assert "Strict-Transport-Security" in header_names

        # Check HSTS value
        hsts_calls = [c for c in call_args_list if c[0][0] == "Strict-Transport-Security"]
        assert len(hsts_calls) >= 1
        hsts_value = hsts_calls[-1][0][1]
        assert "max-age=31536000" in hsts_value
        assert "includeSubDomains" in hsts_value
        assert "preload" in hsts_value

    def test_add_headers_default_http(self) -> None:
        handler = MagicMock()
        SecurityHeaders.add_headers(handler)

        call_args_list = handler.send_header.call_args_list
        header_names = [call[0][0] for call in call_args_list]
        assert "Strict-Transport-Security" not in header_names

    def test_csp_header_content(self) -> None:
        csp = SecurityHeaders.SECURITY_HEADERS["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_permissions_policy_content(self) -> None:
        pp = SecurityHeaders.SECURITY_HEADERS["Permissions-Policy"]
        assert "geolocation=()" in pp
        assert "microphone=()" in pp
        assert "camera=()" in pp


@pytest.mark.unit
class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_default_init(self) -> None:
        limiter = RateLimiter()
        assert limiter.requests_per_minute == 60
        assert limiter.burst_size == 10
        assert limiter.cleanup_interval == 300
        assert limiter.max_tracked_ips == 10000
        assert limiter.buckets == {}

    def test_custom_init(self) -> None:
        limiter = RateLimiter(
            requests_per_minute=120,
            burst_size=20,
            cleanup_interval=600,
            max_tracked_ips=5000,
        )
        assert limiter.requests_per_minute == 120
        assert limiter.burst_size == 20
        assert limiter.cleanup_interval == 600
        assert limiter.max_tracked_ips == 5000


@pytest.mark.unit
class TestRateLimiterIsAllowed:
    """Tests for RateLimiter.is_allowed method."""

    def test_first_request_allowed(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        allowed, retry_after = limiter.is_allowed("192.168.1.1")
        assert allowed is True
        assert retry_after is None

    def test_multiple_requests_within_burst(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst_size=5)
        for _ in range(5):
            allowed, retry_after = limiter.is_allowed("192.168.1.1")
            assert allowed is True
            assert retry_after is None

    def test_request_exceeds_burst(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst_size=3)
        for _ in range(3):
            limiter.is_allowed("192.168.1.1")
        # 4th request should be denied
        allowed, retry_after = limiter.is_allowed("192.168.1.1")
        assert allowed is False
        assert retry_after is not None
        assert retry_after >= 0

    def test_different_ips_independent(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst_size=2)
        # Exhaust IP1
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.1")
        allowed, _ = limiter.is_allowed("192.168.1.1")
        assert allowed is False

        # IP2 should still work
        allowed, retry_after = limiter.is_allowed("192.168.1.2")
        assert allowed is True
        assert retry_after is None

    def test_tokens_refill_over_time(self) -> None:
        limiter = RateLimiter(requests_per_minute=6000, burst_size=1)
        # Use the one token
        allowed, _ = limiter.is_allowed("192.168.1.1")
        assert allowed is True

        # Should be denied immediately
        allowed, _ = limiter.is_allowed("192.168.1.1")
        assert allowed is False

        # Wait for token to refill (6000/min = 100/sec)
        time.sleep(0.02)
        allowed, _ = limiter.is_allowed("192.168.1.1")
        assert allowed is True

    def test_request_count_tracked(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.1")

        assert limiter.buckets["192.168.1.1"]["request_count"] == 3

    def test_max_tracked_ips_eviction(self) -> None:
        limiter = RateLimiter(
            requests_per_minute=60,
            burst_size=10,
            max_tracked_ips=3,
            cleanup_interval=99999,  # Prevent auto-cleanup
        )
        # Fill up to max
        limiter.is_allowed("10.0.0.1")
        time.sleep(0.01)
        limiter.is_allowed("10.0.0.2")
        time.sleep(0.01)
        limiter.is_allowed("10.0.0.3")

        # Next new IP should evict the oldest
        limiter.is_allowed("10.0.0.4")
        assert len(limiter.buckets) <= 3

    def test_max_tracked_ips_cleanup_triggered(self) -> None:
        limiter = RateLimiter(
            requests_per_minute=60,
            burst_size=10,
            max_tracked_ips=2,
            cleanup_interval=0,  # Always cleanup
        )
        limiter.is_allowed("10.0.0.1")
        limiter.is_allowed("10.0.0.2")

        # Force buckets to be "old" for cleanup
        for bucket in limiter.buckets.values():
            bucket["last_update"] = time.time() - 7200

        # New IP triggers cleanup then eviction if needed
        limiter.is_allowed("10.0.0.3")
        # After cleanup of old entries and addition, should be within limits
        assert len(limiter.buckets) <= 2


@pytest.mark.unit
class TestRateLimiterRefillTokens:
    """Tests for RateLimiter._refill_tokens method."""

    def test_tokens_capped_at_burst_size(self) -> None:
        limiter = RateLimiter(requests_per_minute=6000, burst_size=5)
        bucket = {"tokens": 5, "last_update": time.time() - 10}
        limiter._refill_tokens(bucket)
        assert bucket["tokens"] == 5  # Capped at burst_size

    def test_tokens_increase_over_time(self) -> None:
        limiter = RateLimiter(requests_per_minute=600, burst_size=100)
        bucket = {"tokens": 0, "last_update": time.time() - 1}
        limiter._refill_tokens(bucket)
        assert bucket["tokens"] > 0  # Should have gained tokens


@pytest.mark.unit
class TestRateLimiterCleanup:
    """Tests for RateLimiter._cleanup_old_entries method."""

    def test_cleanup_removes_old_entries(self) -> None:
        limiter = RateLimiter(cleanup_interval=0)
        limiter.buckets = {
            "old_ip": {"tokens": 5, "last_update": time.time() - 7200, "request_count": 10},
            "new_ip": {"tokens": 5, "last_update": time.time(), "request_count": 1},
        }
        limiter.last_cleanup = 0

        limiter._cleanup_old_entries()

        assert "old_ip" not in limiter.buckets
        assert "new_ip" in limiter.buckets

    def test_cleanup_respects_interval(self) -> None:
        limiter = RateLimiter(cleanup_interval=300)
        limiter.buckets = {
            "old_ip": {"tokens": 5, "last_update": time.time() - 7200, "request_count": 10},
        }
        limiter.last_cleanup = time.time()  # Just cleaned up

        limiter._cleanup_old_entries()

        # Should not have cleaned up (too recent)
        assert "old_ip" in limiter.buckets


@pytest.mark.unit
class TestRateLimiterGetStats:
    """Tests for RateLimiter.get_stats method."""

    def test_stats_unknown_ip(self) -> None:
        limiter = RateLimiter(burst_size=10)
        stats = limiter.get_stats("192.168.1.1")
        assert stats["requests_remaining"] == 10
        assert stats["total_requests"] == 0

    def test_stats_after_requests(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.1")

        stats = limiter.get_stats("192.168.1.1")
        assert stats["total_requests"] == 2
        assert stats["requests_remaining"] <= 8

    def test_stats_exhausted_tokens(self) -> None:
        limiter = RateLimiter(requests_per_minute=60, burst_size=2)
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.1")

        stats = limiter.get_stats("192.168.1.1")
        assert stats["requests_remaining"] <= 0
        assert stats["total_requests"] == 2


@pytest.mark.unit
class TestRequestValidatorValidatePath:
    """Tests for RequestValidator.validate_path method."""

    def test_valid_path(self) -> None:
        valid, error = RequestValidator.validate_path("/api/v1/extensions")
        assert valid is True
        assert error is None

    def test_path_traversal_unix(self) -> None:
        valid, error = RequestValidator.validate_path("/api/../../../etc/passwd")
        assert valid is False
        assert error is not None
        assert "../" in error

    def test_path_traversal_windows(self) -> None:
        valid, error = RequestValidator.validate_path("/api/..\\..\\windows\\system32")
        assert valid is False
        assert error is not None

    def test_encoded_path_traversal(self) -> None:
        valid, error = RequestValidator.validate_path("/api/%2e%2e/secret")
        assert valid is False
        assert error is not None

    def test_xss_script_tag(self) -> None:
        valid, error = RequestValidator.validate_path("/api?name=<script>alert(1)</script>")
        assert valid is False
        assert error is not None

    def test_xss_javascript_protocol(self) -> None:
        valid, error = RequestValidator.validate_path("/api?url=javascript:alert(1)")
        assert valid is False
        assert error is not None

    def test_xss_onerror(self) -> None:
        valid, error = RequestValidator.validate_path('/api?img=x onerror=alert(1)')
        assert valid is False
        assert error is not None

    def test_xss_onload(self) -> None:
        valid, error = RequestValidator.validate_path('/api?body=x onload=alert(1)')
        assert valid is False
        assert error is not None

    def test_case_insensitive_check(self) -> None:
        valid, error = RequestValidator.validate_path("/api/<SCRIPT>alert(1)</SCRIPT>")
        assert valid is False

    def test_empty_path(self) -> None:
        valid, error = RequestValidator.validate_path("")
        assert valid is True
        assert error is None

    def test_root_path(self) -> None:
        valid, error = RequestValidator.validate_path("/")
        assert valid is True
        assert error is None

    def test_complex_valid_path(self) -> None:
        valid, error = RequestValidator.validate_path(
            "/api/v2/extensions/1001/voicemail?page=1&limit=10"
        )
        assert valid is True
        assert error is None


@pytest.mark.unit
class TestRequestValidatorValidateContentLength:
    """Tests for RequestValidator.validate_content_length method."""

    def test_none_content_length(self) -> None:
        valid, error = RequestValidator.validate_content_length(None)
        assert valid is True
        assert error is None

    def test_valid_content_length(self) -> None:
        valid, error = RequestValidator.validate_content_length(1024)
        assert valid is True
        assert error is None

    def test_zero_content_length(self) -> None:
        valid, error = RequestValidator.validate_content_length(0)
        assert valid is True
        assert error is None

    def test_exactly_max_content_length(self) -> None:
        valid, error = RequestValidator.validate_content_length(
            RequestValidator.MAX_BODY_SIZE
        )
        assert valid is True
        assert error is None

    def test_exceeds_max_content_length(self) -> None:
        valid, error = RequestValidator.validate_content_length(
            RequestValidator.MAX_BODY_SIZE + 1
        )
        assert valid is False
        assert error is not None
        assert "too large" in error.lower()

    def test_max_body_size_value(self) -> None:
        assert RequestValidator.MAX_BODY_SIZE == 10 * 1024 * 1024


@pytest.mark.unit
class TestRequestValidatorSanitizeFilename:
    """Tests for RequestValidator.sanitize_filename method."""

    def test_normal_filename(self) -> None:
        result = RequestValidator.sanitize_filename("document.pdf")
        assert result == "document.pdf"

    def test_filename_with_path_separators(self) -> None:
        result = RequestValidator.sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result
        assert result == ".._.._etc_passwd"

    def test_filename_with_backslash(self) -> None:
        result = RequestValidator.sanitize_filename("..\\..\\windows\\system32")
        assert "\\" not in result

    def test_filename_with_special_chars(self) -> None:
        result = RequestValidator.sanitize_filename("file<>|name?.txt")
        # Only alphanumeric, ., _, -, and space are allowed
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result
        assert "?" not in result

    def test_filename_too_long(self) -> None:
        long_name = "a" * 300 + ".txt"
        result = RequestValidator.sanitize_filename(long_name)
        assert len(result) <= 255

    def test_filename_exactly_255(self) -> None:
        name = "a" * 251 + ".txt"  # 255 chars
        result = RequestValidator.sanitize_filename(name)
        assert len(result) == 255

    def test_empty_filename(self) -> None:
        result = RequestValidator.sanitize_filename("")
        assert result == ""

    def test_filename_with_spaces(self) -> None:
        result = RequestValidator.sanitize_filename("my file name.txt")
        assert result == "my file name.txt"

    def test_filename_with_dashes_underscores(self) -> None:
        result = RequestValidator.sanitize_filename("my-file_name.txt")
        assert result == "my-file_name.txt"

    def test_filename_unicode_kept_if_alnum(self) -> None:
        # Python's isalnum() returns True for Unicode alphanumeric chars like e
        result = RequestValidator.sanitize_filename("file\u00e9name.txt")
        assert "\u00e9" in result
        assert result == "file\u00e9name.txt"

    def test_filename_non_alnum_unicode_stripped(self) -> None:
        # Non-alphanumeric unicode chars like \u2603 (snowman) should be stripped
        result = RequestValidator.sanitize_filename("file\u2603name.txt")
        assert "\u2603" not in result
        assert result == "filename.txt"


@pytest.mark.unit
class TestSecretValidatorValidateSecrets:
    """Tests for SecretValidator.validate_secrets method."""

    def test_required_secrets_defined(self) -> None:
        assert "DB_PASSWORD" in SecretValidator.REQUIRED_SECRETS
        assert "JWT_SECRET" in SecretValidator.REQUIRED_SECRETS

    def test_optional_secrets_defined(self) -> None:
        assert "REDIS_PASSWORD" in SecretValidator.OPTIONAL_SECRETS
        assert "API_KEY" in SecretValidator.OPTIONAL_SECRETS
        assert "WEBHOOK_SECRET" in SecretValidator.OPTIONAL_SECRETS

    @patch("pbx.utils.security_middleware.SecretValidator.validate_secrets")
    def test_all_secrets_valid(self, mock_validate) -> None:
        mock_validate.return_value = (True, [])
        valid, missing = SecretValidator.validate_secrets({})
        assert valid is True
        assert missing == []

    def test_missing_secrets(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            valid, missing = SecretValidator.validate_secrets({})
            assert valid is False
            assert "DB_PASSWORD" in missing
            assert "JWT_SECRET" in missing

    def test_changeme_secret_rejected(self) -> None:
        with patch.dict(
            "os.environ",
            {"DB_PASSWORD": "changeme", "JWT_SECRET": "a_valid_secret_key_1234"},
            clear=True,
        ):
            valid, missing = SecretValidator.validate_secrets({})
            assert "DB_PASSWORD" in missing

    def test_short_secret_rejected(self) -> None:
        with patch.dict(
            "os.environ",
            {"DB_PASSWORD": "short", "JWT_SECRET": "a_valid_secret_key_1234"},
            clear=True,
        ):
            valid, missing = SecretValidator.validate_secrets({})
            assert "DB_PASSWORD" in missing

    def test_valid_long_secrets(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DB_PASSWORD": "a_very_secure_password_123",
                "JWT_SECRET": "another_secure_key_456",
            },
            clear=True,
        ):
            valid, missing = SecretValidator.validate_secrets({})
            assert valid is True
            assert missing == []

    def test_whitespace_only_secret_rejected(self) -> None:
        with patch.dict(
            "os.environ",
            {"DB_PASSWORD": "                    ", "JWT_SECRET": "a_valid_secret_key_1234"},
            clear=True,
        ):
            valid, missing = SecretValidator.validate_secrets({})
            assert "DB_PASSWORD" in missing


@pytest.mark.unit
class TestSecretValidatorCheckWeakSecrets:
    """Tests for SecretValidator.check_weak_secrets method."""

    def test_no_weak_secrets(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DB_PASSWORD": "a_very_unique_value_xyz",
                "JWT_SECRET": "another_unique_value_abc",
                "REDIS_PASSWORD": "redis_unique_val_456",
                "API_KEY": "api_unique_key_789",
                "WEBHOOK_SECRET": "webhook_unique_val",
            },
            clear=True,
        ):
            weak = SecretValidator.check_weak_secrets({})
            assert len(weak) == 0

    def test_weak_password_pattern(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DB_PASSWORD": "my_password_here",
                "JWT_SECRET": "a_very_unique_value_xyz",
            },
            clear=True,
        ):
            weak = SecretValidator.check_weak_secrets({})
            assert "DB_PASSWORD" in weak

    def test_weak_changeme_pattern(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DB_PASSWORD": "please_changeme_now",
                "JWT_SECRET": "a_very_unique_value_xyz",
            },
            clear=True,
        ):
            weak = SecretValidator.check_weak_secrets({})
            assert "DB_PASSWORD" in weak

    def test_weak_admin_pattern(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET": "admin_default_key_xyz",
            },
            clear=True,
        ):
            weak = SecretValidator.check_weak_secrets({})
            assert "JWT_SECRET" in weak

    def test_weak_test_pattern(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DB_PASSWORD": "this_is_a_test_value",
                "JWT_SECRET": "a_very_unique_value_xyz",
            },
            clear=True,
        ):
            weak = SecretValidator.check_weak_secrets({})
            assert "DB_PASSWORD" in weak

    def test_weak_123456_pattern(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DB_PASSWORD": "val_123456_here",
                "JWT_SECRET": "a_very_unique_value_xyz",
            },
            clear=True,
        ):
            weak = SecretValidator.check_weak_secrets({})
            assert "DB_PASSWORD" in weak

    def test_optional_secrets_also_checked(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "REDIS_PASSWORD": "password_redis_val",
            },
            clear=True,
        ):
            weak = SecretValidator.check_weak_secrets({})
            assert "REDIS_PASSWORD" in weak

    def test_empty_secrets_not_flagged(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            weak = SecretValidator.check_weak_secrets({})
            # Empty string doesn't contain weak patterns
            assert len(weak) == 0


@pytest.mark.unit
class TestGlobalRateLimiter:
    """Tests for global rate limiter functions."""

    def test_get_rate_limiter_returns_instance(self) -> None:
        limiter = get_rate_limiter()
        assert isinstance(limiter, RateLimiter)

    def test_get_rate_limiter_default_config(self) -> None:
        import pbx.utils.security_middleware as mod

        # Save original
        original = mod._rate_limiter
        try:
            mod._rate_limiter = RateLimiter(requests_per_minute=60, burst_size=10)
            limiter = get_rate_limiter()
            assert limiter.requests_per_minute == 60
            assert limiter.burst_size == 10
        finally:
            mod._rate_limiter = original

    def test_configure_rate_limiter(self) -> None:
        import pbx.utils.security_middleware as mod

        original = mod._rate_limiter
        try:
            configure_rate_limiter(requests_per_minute=120, burst_size=20)
            limiter = get_rate_limiter()
            assert limiter.requests_per_minute == 120
            assert limiter.burst_size == 20
        finally:
            mod._rate_limiter = original

    def test_configure_rate_limiter_default_args(self) -> None:
        import pbx.utils.security_middleware as mod

        original = mod._rate_limiter
        try:
            configure_rate_limiter()
            limiter = get_rate_limiter()
            assert limiter.requests_per_minute == 60
            assert limiter.burst_size == 10
        finally:
            mod._rate_limiter = original


@pytest.mark.unit
class TestRateLimiterThreadSafety:
    """Tests for RateLimiter thread safety."""

    def test_concurrent_access(self) -> None:
        import threading

        limiter = RateLimiter(requests_per_minute=6000, burst_size=100)
        results = []
        errors = []

        def make_requests() -> None:
            try:
                for _ in range(10):
                    allowed, _ = limiter.is_allowed("192.168.1.1")
                    results.append(allowed)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=make_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 50

    def test_concurrent_stats_access(self) -> None:
        import threading

        limiter = RateLimiter(requests_per_minute=6000, burst_size=100)
        errors = []

        def access_stats() -> None:
            try:
                for _ in range(10):
                    limiter.is_allowed("192.168.1.1")
                    limiter.get_stats("192.168.1.1")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_stats) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


@pytest.mark.unit
class TestSuspiciousPatterns:
    """Tests for RequestValidator suspicious patterns list."""

    def test_all_patterns_detected(self) -> None:
        for pattern in RequestValidator.SUSPICIOUS_PATTERNS:
            valid, error = RequestValidator.validate_path(f"/api/{pattern}test")
            assert valid is False, f"Pattern '{pattern}' was not detected"
            assert error is not None

    def test_patterns_list_contents(self) -> None:
        patterns = RequestValidator.SUSPICIOUS_PATTERNS
        assert "../" in patterns
        assert "..\\" in patterns
        assert "%2e%2e" in patterns
        assert "<script" in patterns
        assert "javascript:" in patterns
        assert "onerror=" in patterns
        assert "onload=" in patterns
