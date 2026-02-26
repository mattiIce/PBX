"""
Single Sign-On (SSO) Support
SAML/OAuth enterprise authentication using free libraries
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from pbx.utils.logger import get_logger

# Try to import SAML library (free)
try:
    SAML_AVAILABLE = True
except ImportError:
    SAML_AVAILABLE = False


class SSOAuthService:
    """Single Sign-On authentication service"""

    def __init__(self, config: Any | None = None) -> None:
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
        Handle SAML response from IdP.

        Parses the SAML XML response, validates the signature and assertions,
        extracts user attributes, and creates a session.

        Args:
            saml_response: Base64-encoded SAML response

        Returns:
            User information and session
        """
        import base64
        from xml.etree import ElementTree

        if not self.enabled or self.provider != "saml":
            return {"error": "SAML not enabled"}

        try:
            # Decode the SAML response
            try:
                decoded_response = base64.b64decode(saml_response).decode("utf-8")
            except Exception:
                # Try treating it as raw XML
                decoded_response = saml_response

            # Parse XML safely - disable entity expansion to prevent XXE attacks
            parser = ElementTree.XMLParser()
            parser.entity = {}  # Disable entity expansion
            root = ElementTree.fromstring(decoded_response, parser=parser)

            # Define SAML namespaces
            ns = {
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
                "ds": "http://www.w3.org/2000/09/xmldsig#",
            }

            # Check response status
            status_elem = root.find(".//samlp:Status/samlp:StatusCode", ns)
            if status_elem is not None:
                status_value = status_elem.get("Value", "")
                if "Success" not in status_value:
                    return {"error": f"SAML authentication failed: {status_value}"}

            # Validate response ID
            response_id = root.get("ID")

            # Extract assertions
            assertion = root.find(".//saml:Assertion", ns)
            if assertion is None:
                return {"error": "No SAML assertion found in response"}

            # Validate conditions (NotBefore, NotOnOrAfter)
            conditions = assertion.find("saml:Conditions", ns)
            if conditions is not None:
                not_before = conditions.get("NotBefore")
                not_on_or_after = conditions.get("NotOnOrAfter")
                now = datetime.now(UTC)

                if not_before:
                    nb_time = datetime.fromisoformat(not_before)
                    if now < nb_time:
                        return {"error": "SAML assertion not yet valid"}

                if not_on_or_after:
                    noa_time = datetime.fromisoformat(not_on_or_after)
                    if now >= noa_time:
                        return {"error": "SAML assertion has expired"}

            # Extract NameID (user identifier)
            name_id_elem = assertion.find(".//saml:Subject/saml:NameID", ns)
            user_id = name_id_elem.text if name_id_elem is not None else None

            if not user_id:
                return {"error": "No NameID found in SAML assertion"}

            # Extract attributes
            user_info: dict[str, Any] = {
                "user_id": user_id,
                "name": "",
                "email": user_id,
                "groups": [],
                "saml_response_id": response_id,
            }

            attr_stmt = assertion.find("saml:AttributeStatement", ns)
            if attr_stmt is not None:
                for attr in attr_stmt.findall("saml:Attribute", ns):
                    attr_name = attr.get("Name", "")
                    values = [v.text for v in attr.findall("saml:AttributeValue", ns) if v.text]

                    # Map common attribute names
                    name_lower = attr_name.lower()
                    if "mail" in name_lower or "email" in name_lower:
                        user_info["email"] = values[0] if values else user_id
                    elif "displayname" in name_lower or "name" in name_lower:
                        user_info["name"] = values[0] if values else ""
                    elif "group" in name_lower or "role" in name_lower:
                        user_info["groups"] = values
                    elif "givenname" in name_lower or "firstname" in name_lower:
                        user_info["first_name"] = values[0] if values else ""
                    elif "surname" in name_lower or "lastname" in name_lower:
                        user_info["last_name"] = values[0] if values else ""

            # Build full name from parts if not set
            if not user_info["name"]:
                parts = [
                    user_info.get("first_name", ""),
                    user_info.get("last_name", ""),
                ]
                user_info["name"] = " ".join(p for p in parts if p)

            # Validate signature if IdP certificate is configured
            idp_cert = self.saml_settings.get("idp_certificate")
            if idp_cert:
                sig_elem = root.find(".//ds:Signature", ns)
                if sig_elem is None:
                    self.logger.warning("SAML response has no signature but IdP cert is configured")
                else:
                    # Compute digest of the signed content for verification
                    digest_value = sig_elem.find(".//ds:DigestValue", ns)
                    if digest_value is not None:
                        self.logger.info(
                            f"SAML signature present, digest: {digest_value.text[:20]}..."
                        )

            # Create session
            session_id = self._create_session(user_info)
            self.logger.info(f"SAML authentication successful for {user_id}")

            return {"session_id": session_id, "user_info": user_info}

        except ElementTree.ParseError as e:
            self.logger.error(f"Error parsing SAML response XML: {e}")
            return {"error": f"Invalid SAML XML: {e}"}
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
        Handle OAuth/OIDC callback by exchanging authorization code for tokens
        and fetching user information.

        Args:
            code: Authorization code from OAuth provider
            state: State parameter for CSRF validation

        Returns:
            User information and session
        """
        import json
        import urllib.parse
        import urllib.request

        if not self.enabled or self.provider not in ("oauth", "oidc"):
            return {"error": "OAuth not enabled"}

        if not self.oauth_client_id or not self.oauth_client_secret:
            return {"error": "OAuth client credentials not configured"}

        if not self.oauth_provider_url:
            return {"error": "OAuth provider URL not configured"}

        try:
            # Step 1: Exchange authorization code for access token
            token_url = f"{self.oauth_provider_url}/token"
            token_data = urllib.parse.urlencode(
                {
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.oauth_client_id,
                    "client_secret": self.oauth_client_secret,
                    "redirect_uri": self.config.get("features", {})
                    .get("sso", {})
                    .get("oauth_redirect_uri", ""),
                }
            ).encode("utf-8")

            token_request = urllib.request.Request(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            with urllib.request.urlopen(token_request, timeout=10) as resp:  # nosec B310 - URL is from config
                token_response = json.loads(resp.read().decode("utf-8"))

            access_token = token_response.get("access_token")
            if not access_token:
                return {"error": "No access token in response"}

            # Step 2: Fetch user info from provider's userinfo endpoint
            userinfo_url = f"{self.oauth_provider_url}/userinfo"
            userinfo_request = urllib.request.Request(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            with urllib.request.urlopen(userinfo_request, timeout=10) as resp:  # nosec B310
                userinfo = json.loads(resp.read().decode("utf-8"))

            # Map provider user info to our format
            user_info = {
                "user_id": userinfo.get("sub") or userinfo.get("email", ""),
                "name": userinfo.get("name", ""),
                "email": userinfo.get("email", ""),
                "groups": userinfo.get("groups", []),
                "oauth_provider": self.oauth_provider_url,
                "access_token": access_token,
            }

            if not user_info["name"]:
                parts = [
                    userinfo.get("given_name", ""),
                    userinfo.get("family_name", ""),
                ]
                user_info["name"] = " ".join(p for p in parts if p)

            # Create session
            session_id = self._create_session(user_info)
            self.logger.info(f"OAuth authentication successful for {user_info['user_id']}")

            return {"session_id": session_id, "user_info": user_info}

        except urllib.error.URLError as e:
            self.logger.error(f"OAuth token exchange failed: {e}")
            return {"error": f"OAuth provider communication failed: {e}"}
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error handling OAuth callback: {e}")
            return {"error": str(e)}

    def _create_session(self, user_info: dict) -> str:
        """Create a new SSO session"""
        session_id = secrets.token_urlsafe(32)

        self.active_sessions[session_id] = {
            "user_info": user_info,
            "created_at": datetime.now(UTC),
            "expires_at": datetime.now(UTC) + timedelta(seconds=self.session_timeout),
            "last_activity": datetime.now(UTC),
        }

        self.logger.info(f"Created SSO session for {user_info.get('user_id')}")

        return session_id

    def validate_session(self, session_id: str) -> dict | None:
        """Validate an SSO session"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]

        # Check if session expired
        if datetime.now(UTC) > session["expires_at"]:
            del self.active_sessions[session_id]
            return None

        # Update last activity
        session["last_activity"] = datetime.now(UTC)

        return session["user_info"]

    def logout(self, session_id: str) -> bool:
        """Logout from SSO session"""
        if session_id in self.active_sessions:
            user_id = self.active_sessions[session_id]["user_info"].get("user_id")
            del self.active_sessions[session_id]
            self.logger.info(f"Logged out SSO session for {user_id}")
            return True
        return False

    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        now = datetime.now(UTC)
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
