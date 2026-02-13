"""
Single Sign-On (SSO) Support
SAML/OAuth enterprise authentication using free libraries
"""

import secrets
from datetime import datetime, timedelta, timezone

from pbx.utils.logger import get_logger

# Try to import SAML library (free)
try:
    pass

    SAML_AVAILABLE = True
except ImportError:
    SAML_AVAILABLE = False


class SSOAuthService:
    """Single Sign-On authentication service"""

    def __init__(self, config=None):
        """Initialize SSO service"""
        self.logger = get_logger()
        self.config = config or {}

        # SSO configuration
        sso_config = self.config.get("features", {}).get("sso", {})
        self.enabled = sso_config.get("enabled", False)
        self.provider = sso_config.get("provider", "saml")  # saml, oauth, oidc

        # Session management
        self.active_sessions = {}  # session_id -> session_info
        self.session_timeout = sso_config.get("session_timeout", 3600)  # 1 hour

        # OAuth/OIDC settings
        self.oauth_client_id = sso_config.get("oauth_client_id")
        self.oauth_client_secret = sso_config.get("oauth_client_secret")
        self.oauth_provider_url = sso_config.get("oauth_provider_url")

        # SAML settings
        self.saml_settings = sso_config.get("saml_settings", {})

        if self.enabled:
            self.logger.info("SSO authentication service initialized")
            self.logger.info(f"  Provider: {self.provider}")
            if self.provider == "saml" and not SAML_AVAILABLE:
                self.logger.warning("SAML provider selected but python3-saml not installed")
                self.logger.info("  Install with: pip install python3-saml")

    def initiate_saml_auth(self, request_data: dict) -> dict:
        """
        Initiate SAML authentication

        Args:
            request_data: Request data including callback URL

        Returns:
            Authentication URL and request ID
        """
        if not self.enabled or self.provider != "saml":
            return {"error": "SAML not enabled"}

        if not SAML_AVAILABLE:
            return {"error": "SAML library not available"}

        try:
            # Create SAML auth request
            auth_url = f"{self.saml_settings.get('idp_url', '')}/sso"
            request_id = secrets.token_urlsafe(32)

            self.logger.info(f"Initiated SAML auth request: {request_id}")

            return {
                "auth_url": auth_url,
                "request_id": request_id,
                "callback_url": request_data.get("callback_url", "/auth/saml/callback"),
            }
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error initiating SAML auth: {e}")
            return {"error": str(e)}

    def handle_saml_response(self, saml_response: str) -> dict:
        """
        Handle SAML response from IdP

        Args:
            saml_response: SAML response XML

        Returns:
            User information and session
        """
        if not self.enabled or self.provider != "saml":
            return {"error": "SAML not enabled"}

        # Stub implementation - in production would validate SAML response
        try:
            # Parse and validate SAML response
            user_info = {
                "user_id": "user@example.com",
                "name": "John Doe",
                "email": "user@example.com",
                "groups": ["users", "admins"],
            }

            # Create session
            session_id = self._create_session(user_info)

            return {"session_id": session_id, "user_info": user_info}
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error handling SAML response: {e}")
            return {"error": str(e)}

    def initiate_oauth_auth(self, redirect_uri: str) -> dict:
        """
        Initiate OAuth authentication

        Args:
            redirect_uri: Redirect URI after authentication

        Returns:
            Authorization URL and state
        """
        if not self.enabled or self.provider != "oauth":
            return {"error": "OAuth not enabled"}

        state = secrets.token_urlsafe(32)

        auth_url = (
            f"{self.oauth_provider_url}/authorize"
            f"?client_id={self.oauth_client_id}"
            f"&redirect_uri={redirect_uri}"
            "&response_type=code"
            f"&state={state}"
            "&scope=openid profile email"
        )

        self.logger.info(f"Initiated OAuth auth with state: {state}")

        return {"auth_url": auth_url, "state": state}

    def handle_oauth_callback(self, code: str, state: str) -> dict:
        """
        Handle OAuth callback

        Args:
            code: Authorization code
            state: State parameter for validation

        Returns:
            User information and session
        """
        if not self.enabled or self.provider != "oauth":
            return {"error": "OAuth not enabled"}

        # Stub implementation - in production would exchange code for token
        try:
            # Exchange code for access token
            # Fetch user info from provider
            user_info = {
                "user_id": "user@example.com",
                "name": "John Doe",
                "email": "user@example.com",
            }

            # Create session
            session_id = self._create_session(user_info)

            return {"session_id": session_id, "user_info": user_info}
        except Exception as e:
            self.logger.error(f"Error handling OAuth callback: {e}")
            return {"error": str(e)}

    def _create_session(self, user_info: dict) -> str:
        """Create a new SSO session"""
        session_id = secrets.token_urlsafe(32)

        self.active_sessions[session_id] = {
            "user_info": user_info,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=self.session_timeout),
            "last_activity": datetime.now(timezone.utc),
        }

        self.logger.info(f"Created SSO session for {user_info.get('user_id')}")

        return session_id

    def validate_session(self, session_id: str) -> dict | None:
        """Validate an SSO session"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]

        # Check if session expired
        if datetime.now(timezone.utc) > session["expires_at"]:
            del self.active_sessions[session_id]
            return None

        # Update last activity
        session["last_activity"] = datetime.now(timezone.utc)

        return session["user_info"]

    def logout(self, session_id: str) -> bool:
        """Logout from SSO session"""
        if session_id in self.active_sessions:
            user_id = self.active_sessions[session_id]["user_info"].get("user_id")
            del self.active_sessions[session_id]
            self.logger.info(f"Logged out SSO session for {user_id}")
            return True
        return False

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now(timezone.utc)
        expired = [
            sid for sid, session in self.active_sessions.items() if now > session["expires_at"]
        ]

        for session_id in expired:
            del self.active_sessions[session_id]

        if expired:
            self.logger.info(f"Cleaned up {len(expired)} expired SSO sessions")

    def get_statistics(self) -> dict:
        """Get SSO statistics"""
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "active_sessions": len(self.active_sessions),
            "saml_available": SAML_AVAILABLE,
        }
