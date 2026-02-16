"""
Multi-Factor Authentication (MFA) for Warden Voip System
Provides TOTP-based two-factor authentication and YubiKey support for enhanced security

Supported MFA Methods:
1. TOTP (Time-based One-Time Password) - Standard authenticator apps
2. YubiKey OTP - YubiKey hardware tokens via YubiCloud
3. FIDO2/WebAuthn - Hardware security keys (YubiKey, etc.)
"""

import base64
import hashlib
import hmac
import json
import random
import secrets
import sqlite3
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from pbx.utils.encryption import get_encryption
from pbx.utils.logger import get_logger


class TOTPGenerator:
    """
    Time-based One-Time Password (TOTP) generator
    Implements RFC 6238 TOTP algorithm
    """

    def __init__(self, secret: bytes | None = None, period: int = 30, digits: int = 6) -> None:
        """
        Initialize TOTP generator

        Args:
            secret: Secret key (generates random if not provided)
            period: Time step in seconds (default 30)
            digits: Number of digits in OTP (default 6)
        """
        self.secret = secret or secrets.token_bytes(20)  # 160-bit secret
        self.period = period
        self.digits = digits
        self.logger = get_logger()

    def generate(self, timestamp: int | None = None) -> str:
        """
        Generate TOTP code for given timestamp

        Args:
            timestamp: Unix timestamp (uses current time if not provided)

        Returns:
            TOTP code as string
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Calculate time counter
        counter = timestamp // self.period

        # Generate HOTP
        return self._hotp(counter)

    def verify(self, code: str, timestamp: int | None = None, window: int = 1) -> bool:
        """
        Verify TOTP code with time window

        Args:
            code: TOTP code to verify
            timestamp: Unix timestamp (uses current time if not provided)
            window: Number of periods to check before/after (default 1)

        Returns:
            True if code is valid
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Check current period and adjacent periods (for clock skew)
        counter = timestamp // self.period

        for i in range(-window, window + 1):
            expected = self._hotp(counter + i)
            if self._constant_time_compare(code, expected):
                return True

        return False

    def _hotp(self, counter: int) -> str:
        """
        Generate HMAC-based One-Time Password (HOTP)

        Args:
            counter: Counter value

        Returns:
            HOTP code as string
        """
        # Convert counter to 8-byte big-endian
        counter_bytes = struct.pack(">Q", counter)

        # Calculate HMAC-SHA1
        hmac_hash = hmac.new(self.secret, counter_bytes, hashlib.sha1).digest()

        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        truncated = struct.unpack(">I", hmac_hash[offset : offset + 4])[0]
        truncated &= 0x7FFFFFFF

        # Generate code with specified digits
        code = truncated % (10**self.digits)

        # Pad with leading zeros
        return str(code).zfill(self.digits)

    def _constant_time_compare(self, a: str, b: str) -> bool:
        """
        Constant-time string comparison to prevent timing attacks

        Args:
            a: First string
            b: Second string

        Returns:
            True if strings are equal
        """
        if len(a) != len(b):
            return False

        result = 0
        for x, y in zip(a, b, strict=False):
            result |= ord(x) ^ ord(y)

        return result == 0

    def get_provisioning_uri(self, account_name: str, issuer: str = "Warden Voip") -> str:
        """
        Generate provisioning URI for QR code

        Args:
            account_name: Account identifier (e.g., username or extension)
            issuer: Service name

        Returns:
            otpauth:// URI for QR code generation
        """
        # Encode secret as base32 (standard for TOTP apps)
        secret_b32 = base64.b32encode(self.secret).decode("utf-8").rstrip("=")

        uri = f"otpauth://totp/{issuer}:{account_name}?secret={secret_b32}&issuer={issuer}&period={self.period}&digits={self.digits}&algorithm=SHA1"
        return uri


class YubiKeyOTPVerifier:
    """
    YubiKey OTP verification via YubiCloud API
    Supports YubiKey hardware tokens with OTP generation
    """

    # YubiCloud validation servers
    YUBICO_SERVERS = [
        "https://api.yubico.com/wsapi/2.0/verify",
        "https://api2.yubico.com/wsapi/2.0/verify",
        "https://api3.yubico.com/wsapi/2.0/verify",
        "https://api4.yubico.com/wsapi/2.0/verify",
        "https://api5.yubico.com/wsapi/2.0/verify",
    ]

    def __init__(self, client_id: str | None = None, api_key: str | None = None) -> None:
        """
        Initialize YubiKey OTP verifier

        Args:
            client_id: YubiCloud API client ID (optional for testing)
            api_key: YubiCloud API secret key (optional for testing)
        """
        self.client_id = client_id or "1"  # Default test client ID
        self.api_key = api_key
        self.logger = get_logger()

    def verify_otp(self, otp: str) -> tuple[bool, str | None]:
        """
        Verify YubiKey OTP

        Args:
            otp: YubiKey OTP string (44 characters)

        Returns:
            tuple of (is_valid, error_message)
        """
        # Validate OTP format
        if not otp or len(otp) != 44:
            return False, "Invalid OTP format (must be 44 characters)"

        # Check if OTP contains only valid ModHex characters
        modhex_chars = set("cbdefghijklnrtuv")
        if not all(c in modhex_chars for c in otp.lower()):
            return False, "Invalid OTP format (contains invalid characters)"

        # Extract YubiKey public ID (first 12 characters)
        public_id = otp[:12]

        self.logger.info(f"YubiKey OTP verification requested for device: {public_id}")

        # Verify via YubiCloud API
        return self._verify_via_yubico(otp)

    def extract_public_id(self, otp: str) -> str | None:
        """
        Extract YubiKey public ID from OTP

        Args:
            otp: YubiKey OTP string

        Returns:
            Public ID (first 12 characters)
        """
        if not otp or len(otp) < 12:
            return None
        return otp[:12]

    def _build_yubico_params(self, otp: str, nonce: str) -> dict:
        """Build YubiCloud API request parameters"""
        params = {
            "id": self.client_id,
            "otp": otp,
            "nonce": nonce,
            "timestamp": "1",  # Request timestamp in response
            "sl": "50",  # Sync level - percentage of servers that must sync
        }

        # Add HMAC signature if API key is provided
        if self.api_key:
            # Sort parameters alphabetically for signature
            sorted_params = sorted(params.items())
            param_string = "&".join(f"{k}={v}" for k, v in sorted_params)

            # Generate HMAC-SHA1 signature
            api_key_bytes = base64.b64decode(self.api_key)
            signature = hmac.new(api_key_bytes, param_string.encode("utf-8"), hashlib.sha1)
            signature_b64 = base64.b64encode(signature.digest()).decode("utf-8")
            params["h"] = signature_b64

        return params

    def _verify_yubico_response_signature(self, response_dict: dict, nonce: str) -> bool:
        """Verify HMAC signature in YubiCloud response"""
        # Verify nonce matches
        if response_dict.get("nonce") != nonce:
            self.logger.warning("Nonce mismatch in YubiCloud response")
            return False

        # Verify HMAC signature if we have an API key
        if self.api_key and "h" in response_dict:
            response_signature = response_dict.pop("h")

            # Sort response parameters for signature verification
            sorted_response = sorted(response_dict.items())
            response_string = "&".join(f"{k}={v}" for k, v in sorted_response)

            # Calculate expected signature
            api_key_bytes = base64.b64decode(self.api_key)
            expected_signature = hmac.new(
                api_key_bytes, response_string.encode("utf-8"), hashlib.sha1
            )
            expected_signature_b64 = base64.b64encode(expected_signature.digest()).decode("utf-8")

            if response_signature != expected_signature_b64:
                self.logger.warning("HMAC signature mismatch in YubiCloud response")
                return False

        return True

    def _query_yubico_server(self, server_url: str, params: dict) -> dict | None:
        """Query a single YubiCloud validation server"""
        try:
            # Build full URL with parameters
            query_string = urllib.parse.urlencode(params)
            full_url = f"{server_url}?{query_string}"

            # Make HTTP request with timeout
            request = urllib.request.Request(full_url)
            with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310 - URL is from configured MFA provider
                response_data = response.read().decode("utf-8")

            # Parse response (key=value pairs separated by newlines)
            response_dict = {}
            for line in response_data.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    response_dict[key.strip()] = value.strip()

            return response_dict
        except OSError as e:
            self.logger.debug(f"Failed to query {server_url}: {e}")
            return None

    def _verify_via_yubico(self, otp: str) -> tuple[bool, str | None]:
        """
        Verify OTP via YubiCloud API
        Implements YubiCloud Validation Protocol 2.0

        Args:
            otp: YubiKey OTP

        Returns:
            tuple of (is_valid, error_message)
        """
        try:
            # Generate random nonce for replay protection
            nonce = base64.b64encode(secrets.token_bytes(16)).decode("utf-8")

            # Build request parameters
            params = self._build_yubico_params(otp, nonce)

            # Try each validation server (for redundancy)
            servers = self.YUBICO_SERVERS.copy()
            random.shuffle(servers)  # Random order for load balancing

            last_error = None
            for server_url in servers:
                response_dict = self._query_yubico_server(server_url, params)
                if response_dict is None:
                    continue

                # Verify response signature and nonce
                if not self._verify_yubico_response_signature(response_dict, nonce):
                    continue

                # Check status
                status = response_dict.get("status")

                if status == "OK":
                    # Verify OTP matches
                    if response_dict.get("otp") == otp:
                        self.logger.info(f"YubiKey OTP verified successfully via {server_url}")
                        return True, None
                    return False, "OTP mismatch in response"
                if status == "REPLAYED_OTP":
                    return False, "OTP has been used before (replay detected)"
                if status == "BAD_OTP":
                    return False, "Invalid OTP format or signature"
                if status == "NO_SUCH_CLIENT":
                    return False, "Invalid client ID"
                if status == "BAD_SIGNATURE":
                    return False, "Invalid request signature"
                if status == "MISSING_PARAMETER":
                    return False, "Missing required parameter"
                if status == "OPERATION_NOT_ALLOWED":
                    return False, "Operation not allowed for this client"
                # Backend errors - try next server
                last_error = f"Backend error: {status}"
                self.logger.warning(f"YubiCloud server {server_url} returned: {status}")
                continue

            # If we get here, all servers failed
            return False, last_error or "All YubiCloud servers unavailable"

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"YubiCloud verification failed: {e}")
            return False, str(e)


class FIDO2Verifier:
    """
    FIDO2/WebAuthn verification for hardware security keys
    Supports YubiKey and other FIDO2-compliant devices
    """

    def __init__(self, rp_id: str = "pbx.local", rp_name: str = "Warden Voip") -> None:
        """
        Initialize FIDO2 verifier

        Args:
            rp_id: Relying Party ID (domain name)
            rp_name: Relying Party name (human-readable)
        """
        self.logger = get_logger()
        self.rp_id = rp_id
        self.rp_name = rp_name

        # Import FIDO2 library components
        try:
            from fido2.server import Fido2Server
            from fido2.webauthn import PublicKeyCredentialRpEntity

            self.Fido2Server = Fido2Server
            self.PublicKeyCredentialRpEntity = PublicKeyCredentialRpEntity
            self.fido2_available = True
        except ImportError:
            self.logger.warning(
                "fido2 library not available - FIDO2 verification will use basic mode"
            )
            self.fido2_available = False

    def register_credential(
        self, extension_number: str, credential_data: dict
    ) -> tuple[bool, str | None]:
        """
        Register FIDO2 credential

        Args:
            extension_number: Extension number
            credential_data: WebAuthn credential registration data
                - credential_id: Unique credential identifier (base64-encoded)
                - public_key: Public key in COSE format (base64-encoded or dict)
                - attestation: Attestation object (optional, base64-encoded)
                - client_data: Client data JSON (optional)

        Returns:
            tuple of (success, credential_id or error_message)
        """
        try:
            credential_id = credential_data.get("credential_id")
            public_key = credential_data.get("public_key")

            if not credential_id or not public_key:
                return False, "Missing credential_id or public_key"

            # If FIDO2 library is available, validate the credential more
            # thoroughly
            if self.fido2_available:
                try:
                    # Decode credential_id if it's base64
                    if isinstance(credential_id, str):
                        credential_id_bytes = base64.b64decode(credential_id)
                    else:
                        credential_id_bytes = credential_id

                    # Validate credential ID length (typical range: 16-1024
                    # bytes)
                    if len(credential_id_bytes) < 16 or len(credential_id_bytes) > 1024:
                        return False, "Invalid credential_id length"

                    self.logger.info(
                        f"FIDO2 credential validated and registered for extension {extension_number}"
                    )
                except Exception as e:
                    return False, f"Invalid credential format: {e!s}"
            else:
                self.logger.info(
                    f"FIDO2 credential registered for extension {extension_number} (basic mode)"
                )

            return True, credential_id

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"FIDO2 registration failed: {e}")
            return False, str(e)

    def verify_assertion(
        self,
        credential_id: str,
        assertion_data: dict,
        public_key: bytes,
        challenge: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Verify FIDO2 authentication assertion

        Args:
            credential_id: Credential identifier (base64-encoded)
            assertion_data: WebAuthn assertion data
                - authenticator_data: Authenticator data (base64-encoded bytes)
                - signature: Assertion signature (base64-encoded bytes)
                - client_data_json: Client data JSON (base64-encoded string)
            public_key: Registered public key (COSE format, bytes or base64)
            challenge: Expected challenge (base64-encoded, optional for backward compatibility)

        Returns:
            tuple of (is_valid, error_message)
        """
        try:
            # Extract assertion components
            authenticator_data = assertion_data.get("authenticator_data")
            signature = assertion_data.get("signature")
            client_data_json = assertion_data.get("client_data_json")

            if not all([authenticator_data, signature, client_data_json]):
                return (
                    False,
                    "Missing required assertion data (authenticator_data, signature, or client_data_json)",
                )

            # Decode base64-encoded data
            try:
                if isinstance(authenticator_data, str):
                    authenticator_data = base64.b64decode(authenticator_data)
                if isinstance(signature, str):
                    signature = base64.b64decode(signature)
                if isinstance(client_data_json, str):
                    try:
                        # Try to decode as base64 first
                        client_data_json = base64.b64decode(client_data_json)
                    except Exception:
                        # If that fails, assume it's already a JSON string
                        client_data_json = client_data_json.encode("utf-8")
                if isinstance(public_key, str):
                    public_key = base64.b64decode(public_key)
            except Exception as e:
                return False, f"Failed to decode assertion data: {e!s}"

            # If FIDO2 library is available, perform full verification
            if self.fido2_available:
                try:
                    import json as json_lib

                    from fido2.cose import CoseKey
                    from fido2.webauthn import AuthenticatorData

                    # Parse client data
                    try:
                        client_data = json_lib.loads(client_data_json)
                    except (json_lib.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
                        return (
                            False,
                            f"Invalid client_data_json format: {e!s}",
                        )

                    # Verify challenge if provided
                    if challenge:
                        received_challenge = client_data.get("challenge", "")
                        if received_challenge != challenge:
                            return False, "Challenge mismatch"

                    # Verify origin (check if it matches rp_id)
                    origin = client_data.get("origin", "")
                    if self.rp_id not in origin:
                        self.logger.warning(f"Origin {origin} does not match RP ID {self.rp_id}")

                    # Parse authenticator data
                    auth_data = AuthenticatorData(authenticator_data)

                    # Verify RP ID hash
                    expected_rp_id_hash = hashlib.sha256(self.rp_id.encode("utf-8")).digest()
                    if auth_data.rp_id_hash != expected_rp_id_hash:
                        return False, "RP ID hash mismatch"

                    # Check user presence (UP flag)
                    if not (auth_data.flags & 0x01):  # UP flag is bit 0
                        return False, "User presence flag not set"

                    # Parse public key as COSE
                    try:
                        cose_key = CoseKey.parse(public_key)
                    except Exception as e:
                        # If parsing fails, return error
                        return False, f"Invalid public key format: {e!s}"

                    # Verify signature
                    # The signed data is: authenticator_data ||
                    # hash(client_data_json)
                    client_data_hash = hashlib.sha256(client_data_json).digest()
                    signed_data = authenticator_data + client_data_hash

                    try:
                        cose_key.verify(signed_data, signature)
                        self.logger.info(
                            f"FIDO2 assertion verified successfully for credential {credential_id}"
                        )
                        return True, None
                    except Exception as e:
                        return (
                            False,
                            f"Signature verification failed: {e!s}",
                        )

                except (KeyError, TypeError, ValueError) as e:
                    self.logger.error(f"FIDO2 verification error: {e}")
                    return False, f"Verification error: {e!s}"
            else:
                # Basic verification without fido2 library
                # At minimum, check that all required data is present and looks
                # valid
                if (
                    len(authenticator_data) < 37
                ):  # Minimum size: 32 (RP ID hash) + 1 (flags) + 4 (counter)
                    return False, "Invalid authenticator_data length"

                if len(signature) < 64:  # Minimum reasonable signature length
                    return False, "Invalid signature length"

                self.logger.info(
                    f"FIDO2 assertion verified (basic mode) for credential {credential_id}"
                )
                return True, None

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"FIDO2 verification failed: {e}")
            return False, str(e)

    def create_challenge(self) -> str:
        """
        Create random challenge for WebAuthn

        Returns:
            Base64-encoded challenge (URL-safe, no padding)
        """
        challenge = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")


class MFAManager:
    """
    Multi-Factor Authentication Manager
    Manages MFA enrollment, verification, and backup codes
    """

    def __init__(self, database: Any | None = None, config: dict | None = None) -> None:
        """
        Initialize MFA manager

        Args:
            database: Database backend for persistent storage
            config: Optional configuration
        """
        self.logger = get_logger()
        self.database = database
        self.config = config or {}

        # Get FIPS mode from config
        fips_mode = self.config.get("security.fips_mode", True)
        enforce_fips = self.config.get("security.enforce_fips", True)
        self.encryption = get_encryption(fips_mode, enforce_fips)

        # MFA configuration
        self.enabled = self.config.get("security.mfa.enabled", True)
        self.required = self.config.get("security.mfa.required", False)
        self.backup_codes_count = self.config.get("security.mfa.backup_codes", 10)

        # YubiKey configuration
        self.yubikey_enabled = self.config.get("security.mfa.yubikey.enabled", False)
        yubikey_client_id = self.config.get("security.mfa.yubikey.client_id")
        yubikey_api_key = self.config.get("security.mfa.yubikey.api_key")

        # Initialize YubiKey verifier if enabled
        if self.yubikey_enabled:
            self.yubikey_verifier = YubiKeyOTPVerifier(yubikey_client_id, yubikey_api_key)
            self.logger.info("YubiKey OTP support enabled")
        else:
            self.yubikey_verifier = None

        # FIDO2 configuration
        self.fido2_enabled = self.config.get("security.mfa.fido2.enabled", False)

        # Initialize FIDO2 verifier if enabled
        if self.fido2_enabled:
            self.fido2_verifier = FIDO2Verifier()
            self.logger.info("FIDO2/WebAuthn support enabled")
        else:
            self.fido2_verifier = None

        # Initialize database schema
        if self.database and self.database.enabled:
            self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Initialize MFA database tables"""
        # MFA secrets table
        mfa_secrets_table = (
            """
        CREATE TABLE IF NOT EXISTS mfa_secrets (
            id SERIAL PRIMARY KEY,
            extension_number VARCHAR(20) UNIQUE NOT NULL,
            secret_encrypted TEXT NOT NULL,
            secret_salt VARCHAR(255) NOT NULL,
            enabled BOOLEAN DEFAULT FALSE,
            enrolled_at TIMESTAMP,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
            if self.database.db_type == "postgresql"
            else """
        CREATE TABLE IF NOT EXISTS mfa_secrets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension_number VARCHAR(20) UNIQUE NOT NULL,
            secret_encrypted TEXT NOT NULL,
            secret_salt VARCHAR(255) NOT NULL,
            enabled BOOLEAN DEFAULT 0,
            enrolled_at TIMESTAMP,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # MFA backup codes table
        backup_codes_table = (
            """
        CREATE TABLE IF NOT EXISTS mfa_backup_codes (
            id SERIAL PRIMARY KEY,
            extension_number VARCHAR(20) NOT NULL,
            code_hash VARCHAR(255) NOT NULL,
            code_salt VARCHAR(255) NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
            if self.database.db_type == "postgresql"
            else """
        CREATE TABLE IF NOT EXISTS mfa_backup_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension_number VARCHAR(20) NOT NULL,
            code_hash VARCHAR(255) NOT NULL,
            code_salt VARCHAR(255) NOT NULL,
            used BOOLEAN DEFAULT 0,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # YubiKey registered devices table
        yubikey_devices_table = (
            """
        CREATE TABLE IF NOT EXISTS mfa_yubikey_devices (
            id SERIAL PRIMARY KEY,
            extension_number VARCHAR(20) NOT NULL,
            public_id VARCHAR(20) UNIQUE NOT NULL,
            device_name VARCHAR(100),
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
            if self.database.db_type == "postgresql"
            else """
        CREATE TABLE IF NOT EXISTS mfa_yubikey_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension_number VARCHAR(20) NOT NULL,
            public_id VARCHAR(20) UNIQUE NOT NULL,
            device_name VARCHAR(100),
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # FIDO2 credentials table
        fido2_credentials_table = (
            """
        CREATE TABLE IF NOT EXISTS mfa_fido2_credentials (
            id SERIAL PRIMARY KEY,
            extension_number VARCHAR(20) NOT NULL,
            credential_id VARCHAR(255) UNIQUE NOT NULL,
            public_key TEXT NOT NULL,
            device_name VARCHAR(100),
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
            if self.database.db_type == "postgresql"
            else """
        CREATE TABLE IF NOT EXISTS mfa_fido2_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension_number VARCHAR(20) NOT NULL,
            credential_id VARCHAR(255) UNIQUE NOT NULL,
            public_key TEXT NOT NULL,
            device_name VARCHAR(100),
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        try:
            self.database.execute(mfa_secrets_table)
            self.database.execute(backup_codes_table)
            self.database.execute(yubikey_devices_table)
            self.database.execute(fido2_credentials_table)
            self.logger.info("MFA database schema initialized (TOTP, YubiKey, FIDO2)")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize MFA schema: {e}")

    def enroll_user(self, extension_number: str) -> tuple[bool, str | None, list | None]:
        """
        Enroll user in MFA

        Args:
            extension_number: Extension number

        Returns:
            tuple of (success, provisioning_uri, backup_codes)
        """
        if not self.enabled:
            return False, None, None

        try:
            # Generate TOTP secret
            totp = TOTPGenerator()
            secret_bytes = totp.secret

            # Encrypt secret for storage using extension number as password
            # Derive encryption key from extension number
            key, salt = self.encryption.derive_key(extension_number)
            nonce_tag_data = self.encryption.encrypt_data(secret_bytes, key)
            # encrypt_data returns tuple: (encrypted_data, nonce, tag)
            # Store all components as a combined encrypted blob in format:
            # nonce|tag|encrypted_data
            import base64

            encrypted_data, nonce, tag = nonce_tag_data  # Explicit unpacking for clarity
            secret_encrypted = base64.b64encode(
                nonce.encode("utf-8")
                + b"|"
                + tag.encode("utf-8")
                + b"|"
                + encrypted_data.encode("utf-8")
            ).decode("utf-8")
            salt = base64.b64encode(salt).decode("utf-8")

            # Generate backup codes
            backup_codes = self._generate_backup_codes()

            # Store in database
            if self.database and self.database.enabled:
                # Check if already enrolled
                query = (
                    "SELECT id, enabled FROM mfa_secrets WHERE extension_number = %s"
                    if self.database.db_type == "postgresql"
                    else "SELECT id, enabled FROM mfa_secrets WHERE extension_number = ?"
                )
                result = self.database.fetch_all(query, (extension_number,))

                if result:
                    # Update existing enrollment
                    update_query = (
                        """
                    UPDATE mfa_secrets
                    SET secret_encrypted = %s, secret_salt = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE extension_number = %s
                    """
                        if self.database.db_type == "postgresql"
                        else """
                    UPDATE mfa_secrets
                    SET secret_encrypted = ?, secret_salt = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE extension_number = ?
                    """
                    )
                    self.database.execute(
                        update_query, (secret_encrypted, salt, False, extension_number)
                    )
                else:
                    # Insert new enrollment
                    insert_query = (
                        """
                    INSERT INTO mfa_secrets (extension_number, secret_encrypted, secret_salt, enabled)
                    VALUES (%s, %s, %s, %s)
                    """
                        if self.database.db_type == "postgresql"
                        else """
                    INSERT INTO mfa_secrets (extension_number, secret_encrypted, secret_salt, enabled)
                    VALUES (?, ?, ?, ?)
                    """
                    )
                    self.database.execute(
                        insert_query, (extension_number, secret_encrypted, salt, False)
                    )

                # Delete old backup codes
                delete_query = (
                    "DELETE FROM mfa_backup_codes WHERE extension_number = %s"
                    if self.database.db_type == "postgresql"
                    else "DELETE FROM mfa_backup_codes WHERE extension_number = ?"
                )
                self.database.execute(delete_query, (extension_number,))

                # Store backup codes
                for code in backup_codes:
                    code_hash, code_salt = self.encryption.hash_password(code)
                    insert_query = (
                        """
                    INSERT INTO mfa_backup_codes (extension_number, code_hash, code_salt)
                    VALUES (%s, %s, %s)
                    """
                        if self.database.db_type == "postgresql"
                        else """
                    INSERT INTO mfa_backup_codes (extension_number, code_hash, code_salt)
                    VALUES (?, ?, ?)
                    """
                    )
                    self.database.execute(insert_query, (extension_number, code_hash, code_salt))

            # Generate provisioning URI
            provisioning_uri = totp.get_provisioning_uri(extension_number)

            self.logger.info(f"MFA enrollment initiated for extension {extension_number}")
            return True, provisioning_uri, backup_codes

        except sqlite3.Error as e:
            self.logger.error(f"MFA enrollment failed for {extension_number}: {e}")
            return False, None, None

    def verify_enrollment(self, extension_number: str, code: str) -> bool:
        """
        Verify enrollment by checking first TOTP code
        Activates MFA for the user

        Args:
            extension_number: Extension number
            code: TOTP code to verify

        Returns:
            True if code is valid and MFA is activated
        """
        if not self.enabled:
            return False

        try:
            # Get secret from database (for enrollment, we don't check enabled
            # status)
            secret_bytes = self._get_secret_for_enrollment(extension_number)
            if not secret_bytes:
                return False

            # Verify TOTP code
            totp = TOTPGenerator(secret=secret_bytes)
            if totp.verify(code):
                # Activate MFA
                if self.database and self.database.enabled:
                    update_query = (
                        """
                    UPDATE mfa_secrets
                    SET enabled = %s, enrolled_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE extension_number = %s
                    """
                        if self.database.db_type == "postgresql"
                        else """
                    UPDATE mfa_secrets
                    SET enabled = ?, enrolled_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE extension_number = ?
                    """
                    )
                    self.database.execute(update_query, (True, extension_number))

                self.logger.info(f"MFA activated for extension {extension_number}")
                return True

            return False

        except sqlite3.Error as e:
            self.logger.error(f"MFA enrollment verification failed for {extension_number}: {e}")
            return False

    def verify_code(self, extension_number: str, code: str) -> bool:
        """
        Verify MFA code (TOTP or backup code)

        Args:
            extension_number: Extension number
            code: MFA code to verify

        Returns:
            True if code is valid
        """
        if not self.enabled:
            return True  # MFA disabled, allow access

        # Check if user has MFA enabled
        if not self.is_enabled_for_user(extension_number):
            return not self.required  # False if MFA required but not enabled

        try:
            # Try TOTP code first (Google Authenticator, Microsoft
            # Authenticator, Authy, etc.)
            secret_bytes = self._get_secret(extension_number)
            if secret_bytes:
                totp = TOTPGenerator(secret=secret_bytes)
                if totp.verify(code):
                    # Update last used timestamp
                    self._update_last_used(extension_number)
                    return True

            # Try YubiKey OTP (44 character code)
            if self.yubikey_enabled and len(code) == 44:
                if self._verify_yubikey_otp(extension_number, code):
                    return True

            # Try backup code
            return bool(self._verify_backup_code(extension_number, code))

        except Exception as e:
            self.logger.error(f"MFA verification failed for {extension_number}: {e}")
            return False

    def is_enabled_for_user(self, extension_number: str) -> bool:
        """
        Check if MFA is enabled for user

        Args:
            extension_number: Extension number

        Returns:
            True if MFA is enabled for user
        """
        if not self.enabled or not self.database or not self.database.enabled:
            return False

        try:
            query = (
                "SELECT enabled FROM mfa_secrets WHERE extension_number = %s"
                if self.database.db_type == "postgresql"
                else "SELECT enabled FROM mfa_secrets WHERE extension_number = ?"
            )
            result = self.database.fetch_all(query, (extension_number,))

            if result and len(result) > 0:
                return bool(result[0].get("enabled", False))

            return False

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to check MFA status for {extension_number}: {e}")
            return False

    def disable_for_user(self, extension_number: str) -> bool:
        """
        Disable MFA for user

        Args:
            extension_number: Extension number

        Returns:
            True if successful
        """
        if not self.database or not self.database.enabled:
            return False

        try:
            update_query = (
                """
            UPDATE mfa_secrets
            SET enabled = %s, updated_at = CURRENT_TIMESTAMP
            WHERE extension_number = %s
            """
                if self.database.db_type == "postgresql"
                else """
            UPDATE mfa_secrets
            SET enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE extension_number = ?
            """
            )
            self.database.execute(update_query, (False, extension_number))

            self.logger.info(f"MFA disabled for extension {extension_number}")
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Failed to disable MFA for {extension_number}: {e}")
            return False

    def enroll_yubikey(
        self, extension_number: str, otp: str, device_name: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Enroll YubiKey device for user

        Args:
            extension_number: Extension number
            otp: YubiKey OTP to extract device ID
            device_name: Optional friendly name for the device

        Returns:
            tuple of (success, error_message)
        """
        if not self.yubikey_enabled or not self.yubikey_verifier:
            return False, "YubiKey support not enabled"

        if not self.database or not self.database.enabled:
            return False, "Database required for YubiKey enrollment"

        try:
            # Verify OTP first
            valid, error = self.yubikey_verifier.verify_otp(otp)
            if not valid:
                return False, error or "Invalid YubiKey OTP"

            # Extract public ID
            public_id = self.yubikey_verifier.extract_public_id(otp)
            if not public_id:
                return False, "Could not extract YubiKey public ID"

            # Check if already enrolled
            query = (
                """
            SELECT id FROM mfa_yubikey_devices
            WHERE public_id = %s
            """
                if self.database.db_type == "postgresql"
                else """
            SELECT id FROM mfa_yubikey_devices
            WHERE public_id = ?
            """
            )
            result = self.database.fetch_all(query, (public_id,))

            if result:
                return False, "YubiKey already enrolled"

            # Insert device
            insert_query = (
                """
            INSERT INTO mfa_yubikey_devices (extension_number, public_id, device_name)
            VALUES (%s, %s, %s)
            """
                if self.database.db_type == "postgresql"
                else """
            INSERT INTO mfa_yubikey_devices (extension_number, public_id, device_name)
            VALUES (?, ?, ?)
            """
            )
            self.database.execute(insert_query, (extension_number, public_id, device_name))

            self.logger.info(f"YubiKey {public_id} enrolled for extension {extension_number}")
            return True, None

        except sqlite3.Error as e:
            self.logger.error(f"YubiKey enrollment failed for {extension_number}: {e}")
            return False, str(e)

    def enroll_fido2(
        self, extension_number: str, credential_data: dict, device_name: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Enroll FIDO2/WebAuthn credential for user

        Args:
            extension_number: Extension number
            credential_data: WebAuthn credential registration data
            device_name: Optional friendly name for the device

        Returns:
            tuple of (success, error_message)
        """
        if not self.fido2_enabled or not self.fido2_verifier:
            return False, "FIDO2 support not enabled"

        if not self.database or not self.database.enabled:
            return False, "Database required for FIDO2 enrollment"

        try:
            # Register credential
            success, result = self.fido2_verifier.register_credential(
                extension_number, credential_data
            )
            if not success:
                return False, result

            credential_id = result
            public_key = credential_data.get("public_key")

            # Store in database
            insert_query = (
                """
            INSERT INTO mfa_fido2_credentials (extension_number, credential_id, public_key, device_name)
            VALUES (%s, %s, %s, %s)
            """
                if self.database.db_type == "postgresql"
                else """
            INSERT INTO mfa_fido2_credentials (extension_number, credential_id, public_key, device_name)
            VALUES (?, ?, ?, ?)
            """
            )
            # Convert public_key to JSON string if it's a dict/bytes
            if isinstance(public_key, (dict, bytes)):
                public_key = (
                    json.dumps(public_key)
                    if isinstance(public_key, dict)
                    else base64.b64encode(public_key).decode("utf-8")
                )

            self.database.execute(
                insert_query, (extension_number, credential_id, public_key, device_name)
            )

            self.logger.info(f"FIDO2 credential enrolled for extension {extension_number}")
            return True, None

        except (KeyError, TypeError, ValueError, json.JSONDecodeError, sqlite3.Error) as e:
            self.logger.error(f"FIDO2 enrollment failed for {extension_number}: {e}")
            return False, str(e)

    def get_enrolled_methods(self, extension_number: str) -> dict[str, list]:
        """
        Get all enrolled MFA methods for user

        Args:
            extension_number: Extension number

        Returns:
            Dictionary with lists of enrolled methods:
            {
                'totp': bool,
                'yubikeys': [{'public_id': ..., 'device_name': ..., 'enrolled_at': ...}],
                'fido2': [{'credential_id': ..., 'device_name': ..., 'enrolled_at': ...}],
                'backup_codes': int (count of unused codes)
            }
        """
        methods = {"totp": False, "yubikeys": [], "fido2": [], "backup_codes": 0}

        if not self.database or not self.database.enabled:
            return methods

        try:
            # Check TOTP
            methods["totp"] = self.is_enabled_for_user(extension_number)

            # Get YubiKeys
            if self.yubikey_enabled:
                query = (
                    """
                SELECT public_id, device_name, enrolled_at
                FROM mfa_yubikey_devices
                WHERE extension_number = %s
                """
                    if self.database.db_type == "postgresql"
                    else """
                SELECT public_id, device_name, enrolled_at
                FROM mfa_yubikey_devices
                WHERE extension_number = ?
                """
                )
                methods["yubikeys"] = self.database.fetch_all(query, (extension_number,))

            # Get FIDO2 credentials
            if self.fido2_enabled:
                query = (
                    """
                SELECT credential_id, device_name, enrolled_at
                FROM mfa_fido2_credentials
                WHERE extension_number = %s
                """
                    if self.database.db_type == "postgresql"
                    else """
                SELECT credential_id, device_name, enrolled_at
                FROM mfa_fido2_credentials
                WHERE extension_number = ?
                """
                )
                methods["fido2"] = self.database.fetch_all(query, (extension_number,))

            # Get backup code count
            query = (
                """
            SELECT COUNT(*) as count
            FROM mfa_backup_codes
            WHERE extension_number = %s AND used = %s
            """
                if self.database.db_type == "postgresql"
                else """
            SELECT COUNT(*) as count
            FROM mfa_backup_codes
            WHERE extension_number = ? AND used = ?
            """
            )
            result = self.database.fetch_one(query, (extension_number, False))
            if result:
                methods["backup_codes"] = result.get("count", 0)

            return methods

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get enrolled methods for {extension_number}: {e}")
            return methods

    def _verify_yubikey_otp(self, extension_number: str, otp: str) -> bool:
        """Verify YubiKey OTP for user"""
        if not self.yubikey_enabled or not self.yubikey_verifier:
            return False

        if not self.database or not self.database.enabled:
            return False

        try:
            # Extract public ID from OTP
            public_id = self.yubikey_verifier.extract_public_id(otp)
            if not public_id:
                return False

            # Check if device is enrolled for this user
            query = (
                """
            SELECT id FROM mfa_yubikey_devices
            WHERE extension_number = %s AND public_id = %s
            """
                if self.database.db_type == "postgresql"
                else """
            SELECT id FROM mfa_yubikey_devices
            WHERE extension_number = ? AND public_id = ?
            """
            )
            result = self.database.fetch_all(query, (extension_number, public_id))

            if not result:
                self.logger.warning(
                    f"YubiKey {public_id} not enrolled for extension {extension_number}"
                )
                return False

            # Verify OTP with YubiCloud
            valid, _error = self.yubikey_verifier.verify_otp(otp)
            if valid:
                # Update last used timestamp
                update_query = (
                    """
                UPDATE mfa_yubikey_devices
                SET last_used = CURRENT_TIMESTAMP
                WHERE extension_number = %s AND public_id = %s
                """
                    if self.database.db_type == "postgresql"
                    else """
                UPDATE mfa_yubikey_devices
                SET last_used = CURRENT_TIMESTAMP
                WHERE extension_number = ? AND public_id = ?
                """
                )
                self.database.execute(update_query, (extension_number, public_id))
                self.logger.info(f"YubiKey OTP verified for extension {extension_number}")
                return True

            return False

        except sqlite3.Error as e:
            self.logger.error(f"YubiKey verification failed for {extension_number}: {e}")
            return False

    def _get_secret(self, extension_number: str) -> bytes | None:
        """Get decrypted secret for user"""
        if not self.database or not self.database.enabled:
            return None

        try:
            query = (
                """
            SELECT secret_encrypted, secret_salt
            FROM mfa_secrets
            WHERE extension_number = %s AND enabled = %s
            """
                if self.database.db_type == "postgresql"
                else """
            SELECT secret_encrypted, secret_salt
            FROM mfa_secrets
            WHERE extension_number = ? AND enabled = ?
            """
            )
            result = self.database.fetch_all(query, (extension_number, True))

            if result and len(result) > 0:
                encrypted = result[0]["secret_encrypted"]
                salt_b64 = result[0]["secret_salt"]

                # Decode salt and derive key from extension number
                import base64

                salt = base64.b64decode(salt_b64)
                key, _ = self.encryption.derive_key(extension_number, salt)

                # Decode encrypted data that contains nonce|tag|encrypted_data
                combined = base64.b64decode(encrypted)
                parts = combined.split(b"|")
                if len(parts) != 3:
                    self.logger.error("Invalid encrypted secret format")
                    return None

                nonce = parts[0].decode("utf-8")
                tag = parts[1].decode("utf-8")
                encrypted_data = parts[2].decode("utf-8")

                # Decrypt using the proper method signature
                return self.encryption.decrypt_data(encrypted_data, nonce, tag, key)

            return None

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get secret for {extension_number}: {e}")
            return None

    def _get_secret_for_enrollment(self, extension_number: str) -> bytes | None:
        """Get decrypted secret for user during enrollment (doesn't check enabled status)"""
        if not self.database or not self.database.enabled:
            return None

        try:
            query = (
                """
            SELECT secret_encrypted, secret_salt
            FROM mfa_secrets
            WHERE extension_number = %s
            """
                if self.database.db_type == "postgresql"
                else """
            SELECT secret_encrypted, secret_salt
            FROM mfa_secrets
            WHERE extension_number = ?
            """
            )
            result = self.database.fetch_all(query, (extension_number,))

            if result and len(result) > 0:
                encrypted = result[0]["secret_encrypted"]
                salt_b64 = result[0]["secret_salt"]

                # Decode salt and derive key from extension number
                import base64

                salt = base64.b64decode(salt_b64)
                key, _ = self.encryption.derive_key(extension_number, salt)

                # Decode encrypted data that contains nonce|tag|encrypted_data
                combined = base64.b64decode(encrypted)
                parts = combined.split(b"|")
                if len(parts) != 3:
                    self.logger.error("Invalid encrypted secret format")
                    return None

                nonce = parts[0].decode("utf-8")
                tag = parts[1].decode("utf-8")
                encrypted_data = parts[2].decode("utf-8")

                # Decrypt using the proper method signature
                return self.encryption.decrypt_data(encrypted_data, nonce, tag, key)

            return None

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to get secret for enrollment {extension_number}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _verify_backup_code(self, extension_number: str, code: str) -> bool:
        """Verify backup code"""
        if not self.database or not self.database.enabled:
            return False

        try:
            # Get unused backup codes
            query = (
                """
            SELECT id, code_hash, code_salt
            FROM mfa_backup_codes
            WHERE extension_number = %s AND used = %s
            """
                if self.database.db_type == "postgresql"
                else """
            SELECT id, code_hash, code_salt
            FROM mfa_backup_codes
            WHERE extension_number = ? AND used = ?
            """
            )
            codes = self.database.fetch_all(query, (extension_number, False))

            # Check each code
            for row in codes:
                if self.encryption.verify_password(code, row["code_hash"], row["code_salt"]):
                    # Mark as used
                    update_query = (
                        """
                    UPDATE mfa_backup_codes
                    SET used = %s, used_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """
                        if self.database.db_type == "postgresql"
                        else """
                    UPDATE mfa_backup_codes
                    SET used = ?, used_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """
                    )
                    self.database.execute(update_query, (True, row["id"]))

                    self.logger.info(f"Backup code used for extension {extension_number}")
                    return True

            return False

        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            self.logger.error(f"Failed to verify backup code for {extension_number}: {e}")
            return False

    def _update_last_used(self, extension_number: str) -> None:
        """Update last used timestamp"""
        if not self.database or not self.database.enabled:
            return

        try:
            update_query = (
                """
            UPDATE mfa_secrets
            SET last_used = CURRENT_TIMESTAMP
            WHERE extension_number = %s
            """
                if self.database.db_type == "postgresql"
                else """
            UPDATE mfa_secrets
            SET last_used = CURRENT_TIMESTAMP
            WHERE extension_number = ?
            """
            )
            self.database.execute(update_query, (extension_number,))
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update last used for {extension_number}: {e}")

    def _generate_backup_codes(self, count: int | None = None) -> list:
        """Generate random backup codes"""
        if count is None:
            count = self.backup_codes_count

        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            # Excludes potentially confusing characters: 0 (zero), O (letter O), I (letter I), 1 (one)
            # This prevents user confusion when manually entering codes
            code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
            # Format as XXXX-XXXX for readability
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)

        return codes


def get_mfa_manager(database: Any | None = None, config: dict | None = None) -> MFAManager:
    """Get MFA manager instance"""
    return MFAManager(database, config)
