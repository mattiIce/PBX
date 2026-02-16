"""Security middleware for PBX API.

Provides security headers, rate limiting, and request validation.
"""

import threading
import time


class SecurityHeaders:
    """Add security headers to HTTP responses."""

    # Security headers for production
    SECURITY_HEADERS = {
        # Prevent clickjacking
        "X-Frame-Options": "DENY",
        # Prevent MIME type sniffing
        "X-Content-type-Options": "nosniff",
        # Enable XSS protection
        "X-XSS-Protection": "1; mode=block",
        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # Content Security Policy
        # Note: If you need 'unsafe-inline' or 'unsafe-eval' for compatibility,
        # consider using nonces or hashes for inline scripts instead
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        ),
        # Permissions policy (formerly Feature-Policy)
        "Permissions-Policy": ("geolocation=(), microphone=(), camera=(), payment=(), usb=()"),
        # HSTS (only for HTTPS)
        # "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }

    @staticmethod
    def add_headers(handler, is_https: bool = False):
        """Add security headers to response.

        Args:
            handler: HTTP request handler
            is_https: Whether connection is HTTPS
        """
        for header, value in SecurityHeaders.SECURITY_HEADERS.items():
            # Only add HSTS for HTTPS connections
            if header == "Strict-Transport-Security" and not is_https:
                continue
            handler.send_header(header, value)

        # Add HSTS for HTTPS
        if is_https:
            handler.send_header(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload"
            )


class RateLimiter:
    """Token bucket rate limiter with thread safety and memory limits."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        cleanup_interval: int = 300,
        max_tracked_ips: int = 10000,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Number of requests allowed per minute
            burst_size: Maximum burst of requests
            cleanup_interval: How often to clean up old entries (seconds)
            max_tracked_ips: Maximum number of IP addresses to track (prevents memory exhaustion)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.cleanup_interval = cleanup_interval
        self.max_tracked_ips = max_tracked_ips

        # Store buckets per client IP
        self.buckets: dict[str, dict] = {}
        self.last_cleanup = time.time()

        # Thread lock for concurrent access
        self._lock = threading.Lock()

    def _refill_tokens(self, bucket: dict) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - bucket["last_update"]

        # Add tokens based on time elapsed
        tokens_to_add = elapsed * (self.requests_per_minute / 60.0)
        bucket["tokens"] = min(self.burst_size, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now

    def _cleanup_old_entries(self) -> None:
        """Clean up old bucket entries."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove buckets not used in last hour
        cutoff = now - 3600
        old_buckets = self.buckets
        self.buckets = {
            ip: bucket for ip, bucket in old_buckets.items() if bucket["last_update"] > cutoff
        }
        self.last_cleanup = now

    def is_allowed(self, client_ip: str) -> tuple[bool, int | None]:
        """Check if request is allowed.

        Args:
            client_ip: Client IP address

        Returns:
            tuple of (allowed, retry_after_seconds)
        """
        with self._lock:
            # Check if we've hit the maximum tracked IPs
            if client_ip not in self.buckets and len(self.buckets) >= self.max_tracked_ips:
                # Force cleanup before rejecting
                self._cleanup_old_entries()

                # If still at max after cleanup, reject oldest entry
                if len(self.buckets) >= self.max_tracked_ips:
                    oldest_ip = min(
                        self.buckets.keys(),
                        key=lambda ip: self.buckets[ip]["last_update"],
                    )
                    del self.buckets[oldest_ip]

            # Get or create bucket for this IP
            if client_ip not in self.buckets:
                self.buckets[client_ip] = {
                    "tokens": self.burst_size,
                    "last_update": time.time(),
                    "request_count": 0,
                }

            bucket = self.buckets[client_ip]
            self._refill_tokens(bucket)

            # Check if we have tokens available
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                bucket["request_count"] += 1
                self._cleanup_old_entries()
                return True, None

            # Calculate retry after
            tokens_needed = 1 - bucket["tokens"]
            retry_after = int(tokens_needed / (self.requests_per_minute / 60.0))

            return False, retry_after

    def get_stats(self, client_ip: str) -> dict:
        """Get rate limit stats for client.

        Args:
            client_ip: Client IP address

        Returns:
            Dictionary with stats
        """
        with self._lock:
            bucket = self.buckets.get(client_ip)
            if not bucket:
                return {
                    "requests_remaining": self.burst_size,
                    "total_requests": 0,
                }

            self._refill_tokens(bucket)
            return {
                "requests_remaining": int(bucket["tokens"]),
                "total_requests": bucket["request_count"],
            }


class RequestValidator:
    """Validate incoming requests for security issues."""

    # Maximum request body size (10 MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024

    # Suspicious patterns in request paths
    SUSPICIOUS_PATTERNS = [
        "../",  # Path traversal
        "..\\",  # Path traversal (Windows)
        "%2e%2e",  # Encoded path traversal
        "<script",  # XSS attempt
        "javascript:",  # XSS attempt
        "onerror=",  # XSS attempt
        "onload=",  # XSS attempt
    ]

    @staticmethod
    def validate_path(path: str) -> tuple[bool, str | None]:
        """Validate request path.

        Args:
            path: Request path

        Returns:
            tuple of (valid, error_message)
        """
        # Check for suspicious patterns
        path_lower = path.lower()
        for pattern in RequestValidator.SUSPICIOUS_PATTERNS:
            if pattern in path_lower:
                return False, f"Suspicious pattern detected: {pattern}"

        return True, None

    @staticmethod
    def validate_content_length(content_length: int | None) -> tuple[bool, str | None]:
        """Validate content length.

        Args:
            content_length: Content length from request

        Returns:
            tuple of (valid, error_message)
        """
        if content_length is None:
            return True, None

        if content_length > RequestValidator.MAX_BODY_SIZE:
            return False, f"Request too large (max {RequestValidator.MAX_BODY_SIZE} bytes)"

        return True, None

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")

        # Remove dangerous characters
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")

        # Limit length
        if len(filename) > 255:
            filename = filename[:255]

        return filename


class SecretValidator:
    """Validate that secrets are properly configured."""

    REQUIRED_SECRETS = [
        "DB_PASSWORD",
        "JWT_SECRET",
    ]

    OPTIONAL_SECRETS = [
        "REDIS_PASSWORD",
        "API_KEY",
        "WEBHOOK_SECRET",
    ]

    @staticmethod
    def validate_secrets(config: dict) -> tuple[bool, list]:
        """Validate secrets configuration.

        Args:
            config: Configuration dictionary

        Returns:
            tuple of (all_valid, missing_secrets)
        """
        import os

        missing = []

        for secret in SecretValidator.REQUIRED_SECRETS:
            value = os.getenv(secret, "").strip()
            if not value or value == "changeme" or len(value) < 16:
                missing.append(secret)

        return len(missing) == 0, missing

    @staticmethod
    def check_weak_secrets(config: dict) -> list:
        """Check for weak or default secrets.

        Args:
            config: Configuration dictionary

        Returns:
            list of weak secrets found
        """
        import os

        weak = []
        weak_patterns = ["password", "changeme", "admin", "test", "123456"]

        for secret in SecretValidator.REQUIRED_SECRETS + SecretValidator.OPTIONAL_SECRETS:
            value = os.getenv(secret, "").strip().lower()
            if any(pattern in value for pattern in weak_patterns):
                weak.append(secret)

        return weak


# Global rate limiter instance
_rate_limiter = RateLimiter(
    requests_per_minute=60,  # 60 requests per minute
    burst_size=10,  # Allow bursts of up to 10 requests
)


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    return _rate_limiter


def configure_rate_limiter(requests_per_minute: int = 60, burst_size: int = 10):
    """Configure global rate limiter.

    Args:
        requests_per_minute: Number of requests allowed per minute
        burst_size: Maximum burst of requests
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
    )
