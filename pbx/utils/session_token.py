"""
Session token management for authentication
Provides JWT-like token generation and verification
"""

import base64
import hashlib
import json
import secrets
import time

from pbx.utils.logger import get_logger


class SessionToken:
    """
    Simple JWT-like token implementation for session management

    Token format: {header}.{payload}.{signature}
    - header: Contains algorithm info (base64-encoded JSON)
    - payload: Contains user data and expiration (base64-encoded JSON)
    - signature: HMAC-SHA256 signature of header.payload
    """

    # Token expiration time (24 hours in seconds)
    TOKEN_EXPIRATION = 24 * 60 * 60

    def __init__(self, secret_key: str | None = None) -> None:
        """
        Initialize session token manager

        Args:
            secret_key: Secret key for signing tokens (auto-generated if not provided)
        """
        self.logger = get_logger()

        # Generate or use provided secret key
        if secret_key:
            if isinstance(secret_key, str):
                self.secret_key = secret_key.encode("utf-8")
            elif isinstance(secret_key, bytes):
                self.secret_key = secret_key
            else:
                raise TypeError(f"secret_key must be str or bytes, got {type(secret_key)}")
        else:
            # Generate a cryptographically secure random secret key
            self.secret_key = secrets.token_bytes(32)
            self.logger.info("Generated new session token secret key")

    def _base64_encode(self, data: bytes) -> str:
        """Base64 encode data (URL-safe, no padding)"""
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def _base64_decode(self, data: str) -> bytes:
        """Base64 decode data (URL-safe, restore padding)"""
        # Add padding if needed
        padding = 4 - (len(data) % 4)
        if padding and padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def _sign(self, message: str) -> str:
        """Create HMAC-SHA256 signature"""
        import hmac

        signature = hmac.new(self.secret_key, message.encode("utf-8"), hashlib.sha256).digest()
        return self._base64_encode(signature)

    def generate_token(
        self, extension: str, is_admin: bool, name: str | None = None, email: str | None = None
    ) -> str:
        """
        Generate authentication token

        Args:
            extension: Extension number
            is_admin: Whether user has admin privileges
            name: User's display name
            email: User's email address

        Returns:
            JWT-like token string
        """
        # Create header
        header = {"alg": "HS256", "typ": "JWT"}
        header_json = json.dumps(header, separators=(",", ":"))
        header_encoded = self._base64_encode(header_json.encode("utf-8"))

        # Create payload
        payload = {
            "extension": extension,
            "is_admin": is_admin,
            "iat": int(time.time()),  # Issued at
            "exp": int(time.time()) + self.TOKEN_EXPIRATION,  # Expiration
        }

        if name:
            payload["name"] = name
        if email:
            payload["email"] = email

        payload_json = json.dumps(payload, separators=(",", ":"))
        payload_encoded = self._base64_encode(payload_json.encode("utf-8"))

        # Create signature
        message = f"{header_encoded}.{payload_encoded}"
        signature = self._sign(message)

        # Combine into token
        token = f"{message}.{signature}"

        self.logger.info(f"Generated session token for extension {extension} (admin: {is_admin})")
        return token

    def verify_token(self, token: str) -> tuple[bool, dict | None]:
        """
        Verify and decode token

        Args:
            token: Token string to verify

        Returns:
            tuple of (is_valid, payload_dict)
            - is_valid: True if token is valid
            - payload_dict: Decoded payload if valid, None otherwise
        """
        try:
            # Split token into parts
            parts = token.split(".")
            if len(parts) != 3:
                self.logger.warning("Invalid token format (wrong number of parts)")
                return False, None

            header_encoded, payload_encoded, signature_provided = parts

            # Verify signature
            message = f"{header_encoded}.{payload_encoded}"
            signature_expected = self._sign(message)

            if signature_provided != signature_expected:
                self.logger.warning("Token signature verification failed")
                return False, None

            # Decode payload
            payload_json = self._base64_decode(payload_encoded)
            payload = json.loads(payload_json)

            # Check expiration
            exp = payload.get("exp", 0)
            if exp < time.time():
                self.logger.warning(f"Token expired (exp: {exp}, now: {time.time()})")
                return False, None

            return True, payload

        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
            self.logger.warning(f"Token verification error: {e}")
            return False, None

    def extract_extension(self, token: str) -> str | None:
        """
        Extract extension number from token without full verification

        Args:
            token: Token string

        Returns:
            Extension number if token format is valid, None otherwise
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            payload_json = self._base64_decode(parts[1])
            payload = json.loads(payload_json)
            return payload.get("extension")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None


# Global session token manager (initialized with random key)
_session_token_manager = None


def get_session_token_manager(secret_key: str | None = None) -> SessionToken:
    """
    Get or create global session token manager

    Args:
        secret_key: Optional secret key (only used on first initialization)

    Returns:
        SessionToken instance
    """
    global _session_token_manager
    if _session_token_manager is None:
        _session_token_manager = SessionToken(secret_key)
    return _session_token_manager
