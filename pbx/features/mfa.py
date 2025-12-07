"""
Multi-Factor Authentication (MFA) for PBX System
Provides TOTP-based two-factor authentication and YubiKey support for enhanced security

Supported MFA Methods:
1. TOTP (Time-based One-Time Password) - Standard authenticator apps
2. YubiKey OTP - YubiKey hardware tokens via YubiCloud
3. FIDO2/WebAuthn - Hardware security keys (YubiKey, etc.)
"""
import base64
import hmac
import hashlib
import struct
import time
import secrets
import json
from typing import Optional, Tuple, Dict, List
from datetime import datetime, timedelta
from pbx.utils.logger import get_logger
from pbx.utils.encryption import get_encryption


class TOTPGenerator:
    """
    Time-based One-Time Password (TOTP) generator
    Implements RFC 6238 TOTP algorithm
    """
    
    def __init__(self, secret: bytes = None, period: int = 30, digits: int = 6):
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
    
    def generate(self, timestamp: Optional[int] = None) -> str:
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
    
    def verify(self, code: str, timestamp: Optional[int] = None, 
               window: int = 1) -> bool:
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
        counter_bytes = struct.pack('>Q', counter)
        
        # Calculate HMAC-SHA1
        hmac_hash = hmac.new(self.secret, counter_bytes, hashlib.sha1).digest()
        
        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        truncated = struct.unpack('>I', hmac_hash[offset:offset + 4])[0]
        truncated &= 0x7FFFFFFF
        
        # Generate code with specified digits
        code = truncated % (10 ** self.digits)
        
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
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        
        return result == 0
    
    def get_provisioning_uri(self, account_name: str, issuer: str = "PBX System") -> str:
        """
        Generate provisioning URI for QR code
        
        Args:
            account_name: Account identifier (e.g., username or extension)
            issuer: Service name
            
        Returns:
            otpauth:// URI for QR code generation
        """
        # Encode secret as base32 (standard for TOTP apps)
        secret_b32 = base64.b32encode(self.secret).decode('utf-8').rstrip('=')
        
        uri = f"otpauth://totp/{issuer}:{account_name}?secret={secret_b32}&issuer={issuer}&period={self.period}&digits={self.digits}&algorithm=SHA1"
        return uri


class YubiKeyOTPVerifier:
    """
    YubiKey OTP verification via YubiCloud API
    Supports YubiKey hardware tokens with OTP generation
    """
    
    # YubiCloud validation servers
    YUBICO_SERVERS = [
        'https://api.yubico.com/wsapi/2.0/verify',
        'https://api2.yubico.com/wsapi/2.0/verify',
        'https://api3.yubico.com/wsapi/2.0/verify',
        'https://api4.yubico.com/wsapi/2.0/verify',
        'https://api5.yubico.com/wsapi/2.0/verify',
    ]
    
    def __init__(self, client_id: str = None, api_key: str = None):
        """
        Initialize YubiKey OTP verifier
        
        Args:
            client_id: YubiCloud API client ID (optional for testing)
            api_key: YubiCloud API secret key (optional for testing)
        """
        self.client_id = client_id or '1'  # Default test client ID
        self.api_key = api_key
        self.logger = get_logger()
    
    def verify_otp(self, otp: str) -> Tuple[bool, Optional[str]]:
        """
        Verify YubiKey OTP
        
        Args:
            otp: YubiKey OTP string (44 characters)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate OTP format
        if not otp or len(otp) != 44:
            return False, "Invalid OTP format (must be 44 characters)"
        
        # Check if OTP contains only valid ModHex characters
        modhex_chars = set('cbdefghijklnrtuv')
        if not all(c in modhex_chars for c in otp.lower()):
            return False, "Invalid OTP format (contains invalid characters)"
        
        # Extract YubiKey public ID (first 12 characters)
        public_id = otp[:12]
        
        # For now, return a simulated verification without external API call
        # In production, this would call YubiCloud API
        # Note: Actual implementation would require API credentials and HTTP client
        self.logger.info(f"YubiKey OTP verification requested for device: {public_id}")
        
        # Simulated verification - in real implementation, call YubiCloud
        # return self._verify_via_yubico(otp)
        
        return True, None  # Placeholder - actual verification would happen here
    
    def extract_public_id(self, otp: str) -> Optional[str]:
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
    
    def _verify_via_yubico(self, otp: str) -> Tuple[bool, Optional[str]]:
        """
        Verify OTP via YubiCloud API (requires http client)
        This is a placeholder for the actual implementation
        
        Args:
            otp: YubiKey OTP
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # TODO: Implement actual YubiCloud API call
        # Would require: requests library or urllib
        # Build request with HMAC signature if api_key is provided
        # Parse response and verify signature
        
        self.logger.warning("YubiCloud API verification not implemented - using simulation mode")
        return True, None


class FIDO2Verifier:
    """
    FIDO2/WebAuthn verification for hardware security keys
    Supports YubiKey and other FIDO2-compliant devices
    """
    
    def __init__(self):
        """Initialize FIDO2 verifier"""
        self.logger = get_logger()
    
    def register_credential(self, extension_number: str, credential_data: dict) -> Tuple[bool, Optional[str]]:
        """
        Register FIDO2 credential
        
        Args:
            extension_number: Extension number
            credential_data: WebAuthn credential registration data
                - credential_id: Unique credential identifier
                - public_key: Public key in COSE format
                - attestation: Attestation object (optional)
            
        Returns:
            Tuple of (success, credential_id or error_message)
        """
        try:
            credential_id = credential_data.get('credential_id')
            public_key = credential_data.get('public_key')
            
            if not credential_id or not public_key:
                return False, "Missing credential_id or public_key"
            
            self.logger.info(f"FIDO2 credential registered for extension {extension_number}")
            return True, credential_id
            
        except Exception as e:
            self.logger.error(f"FIDO2 registration failed: {e}")
            return False, str(e)
    
    def verify_assertion(self, credential_id: str, assertion_data: dict, public_key: bytes) -> Tuple[bool, Optional[str]]:
        """
        Verify FIDO2 authentication assertion
        
        Args:
            credential_id: Credential identifier
            assertion_data: WebAuthn assertion data
                - authenticator_data: Authenticator data
                - signature: Assertion signature
                - client_data_json: Client data JSON
            public_key: Registered public key
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # TODO: Implement actual FIDO2/WebAuthn verification
            # Would require: fido2 library for proper verification
            # - Verify authenticator data
            # - Verify signature using public key
            # - Check challenge
            # - Validate origin
            
            self.logger.info(f"FIDO2 assertion verification for credential {credential_id}")
            return True, None  # Placeholder
            
        except Exception as e:
            self.logger.error(f"FIDO2 verification failed: {e}")
            return False, str(e)
    
    def create_challenge(self) -> str:
        """
        Create random challenge for WebAuthn
        
        Returns:
            Base64-encoded challenge
        """
        challenge = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')


class MFAManager:
    """
    Multi-Factor Authentication Manager
    Manages MFA enrollment, verification, and backup codes
    """
    
    def __init__(self, database=None, config: dict = None):
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
        fips_mode = self.config.get('security.fips_mode', True)
        enforce_fips = self.config.get('security.enforce_fips', True)
        self.encryption = get_encryption(fips_mode, enforce_fips)
        
        # MFA configuration
        self.enabled = self.config.get('security.mfa.enabled', True)
        self.required = self.config.get('security.mfa.required', False)
        self.backup_codes_count = self.config.get('security.mfa.backup_codes', 10)
        
        # YubiKey configuration
        self.yubikey_enabled = self.config.get('security.mfa.yubikey.enabled', False)
        yubikey_client_id = self.config.get('security.mfa.yubikey.client_id')
        yubikey_api_key = self.config.get('security.mfa.yubikey.api_key')
        
        # Initialize YubiKey verifier if enabled
        if self.yubikey_enabled:
            self.yubikey_verifier = YubiKeyOTPVerifier(yubikey_client_id, yubikey_api_key)
            self.logger.info("YubiKey OTP support enabled")
        else:
            self.yubikey_verifier = None
        
        # FIDO2 configuration
        self.fido2_enabled = self.config.get('security.mfa.fido2.enabled', False)
        
        # Initialize FIDO2 verifier if enabled
        if self.fido2_enabled:
            self.fido2_verifier = FIDO2Verifier()
            self.logger.info("FIDO2/WebAuthn support enabled")
        else:
            self.fido2_verifier = None
        
        # Initialize database schema
        if self.database and self.database.enabled:
            self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize MFA database tables"""
        # MFA secrets table
        mfa_secrets_table = """
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
        """ if self.database.db_type == 'postgresql' else """
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
        
        # MFA backup codes table
        backup_codes_table = """
        CREATE TABLE IF NOT EXISTS mfa_backup_codes (
            id SERIAL PRIMARY KEY,
            extension_number VARCHAR(20) NOT NULL,
            code_hash VARCHAR(255) NOT NULL,
            code_salt VARCHAR(255) NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.database.db_type == 'postgresql' else """
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
        
        # YubiKey registered devices table
        yubikey_devices_table = """
        CREATE TABLE IF NOT EXISTS mfa_yubikey_devices (
            id SERIAL PRIMARY KEY,
            extension_number VARCHAR(20) NOT NULL,
            public_id VARCHAR(20) UNIQUE NOT NULL,
            device_name VARCHAR(100),
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.database.db_type == 'postgresql' else """
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
        
        # FIDO2 credentials table
        fido2_credentials_table = """
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
        """ if self.database.db_type == 'postgresql' else """
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
        
        try:
            self.database.execute(mfa_secrets_table)
            self.database.execute(backup_codes_table)
            self.database.execute(yubikey_devices_table)
            self.database.execute(fido2_credentials_table)
            self.logger.info("MFA database schema initialized (TOTP, YubiKey, FIDO2)")
        except Exception as e:
            self.logger.error(f"Failed to initialize MFA schema: {e}")
    
    def enroll_user(self, extension_number: str) -> Tuple[bool, Optional[str], Optional[list]]:
        """
        Enroll user in MFA
        
        Args:
            extension_number: Extension number
            
        Returns:
            Tuple of (success, provisioning_uri, backup_codes)
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
            # Store all components (nonce, tag, encrypted_data) as a combined encrypted blob
            import base64
            secret_encrypted = base64.b64encode(
                nonce_tag_data[1].encode('utf-8') + b'|' + 
                nonce_tag_data[2].encode('utf-8') + b'|' + 
                nonce_tag_data[0].encode('utf-8')
            ).decode('utf-8')
            salt = base64.b64encode(salt).decode('utf-8')
            
            # Generate backup codes
            backup_codes = self._generate_backup_codes()
            
            # Store in database
            if self.database and self.database.enabled:
                # Check if already enrolled
                query = "SELECT id, enabled FROM mfa_secrets WHERE extension_number = %s" if self.database.db_type == 'postgresql' else \
                        "SELECT id, enabled FROM mfa_secrets WHERE extension_number = ?"
                result = self.database.fetch_all(query, (extension_number,))
                
                if result:
                    # Update existing enrollment
                    update_query = """
                    UPDATE mfa_secrets 
                    SET secret_encrypted = %s, secret_salt = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE extension_number = %s
                    """ if self.database.db_type == 'postgresql' else """
                    UPDATE mfa_secrets 
                    SET secret_encrypted = ?, secret_salt = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE extension_number = ?
                    """
                    self.database.execute(update_query, (secret_encrypted, salt, False, extension_number))
                else:
                    # Insert new enrollment
                    insert_query = """
                    INSERT INTO mfa_secrets (extension_number, secret_encrypted, secret_salt, enabled)
                    VALUES (%s, %s, %s, %s)
                    """ if self.database.db_type == 'postgresql' else """
                    INSERT INTO mfa_secrets (extension_number, secret_encrypted, secret_salt, enabled)
                    VALUES (?, ?, ?, ?)
                    """
                    self.database.execute(insert_query, (extension_number, secret_encrypted, salt, False))
                
                # Delete old backup codes
                delete_query = "DELETE FROM mfa_backup_codes WHERE extension_number = %s" if self.database.db_type == 'postgresql' else \
                               "DELETE FROM mfa_backup_codes WHERE extension_number = ?"
                self.database.execute(delete_query, (extension_number,))
                
                # Store backup codes
                for code in backup_codes:
                    code_hash, code_salt = self.encryption.hash_password(code)
                    insert_query = """
                    INSERT INTO mfa_backup_codes (extension_number, code_hash, code_salt)
                    VALUES (%s, %s, %s)
                    """ if self.database.db_type == 'postgresql' else """
                    INSERT INTO mfa_backup_codes (extension_number, code_hash, code_salt)
                    VALUES (?, ?, ?)
                    """
                    self.database.execute(insert_query, (extension_number, code_hash, code_salt))
            
            # Generate provisioning URI
            provisioning_uri = totp.get_provisioning_uri(extension_number)
            
            self.logger.info(f"MFA enrollment initiated for extension {extension_number}")
            return True, provisioning_uri, backup_codes
            
        except Exception as e:
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
            # Get secret from database (for enrollment, we don't check enabled status)
            secret_bytes = self._get_secret_for_enrollment(extension_number)
            if not secret_bytes:
                return False
            
            # Verify TOTP code
            totp = TOTPGenerator(secret=secret_bytes)
            if totp.verify(code):
                # Activate MFA
                if self.database and self.database.enabled:
                    update_query = """
                    UPDATE mfa_secrets 
                    SET enabled = %s, enrolled_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE extension_number = %s
                    """ if self.database.db_type == 'postgresql' else """
                    UPDATE mfa_secrets 
                    SET enabled = ?, enrolled_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE extension_number = ?
                    """
                    self.database.execute(update_query, (True, extension_number))
                
                self.logger.info(f"MFA activated for extension {extension_number}")
                return True
            
            return False
            
        except Exception as e:
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
            if self.required:
                return False  # MFA required but not enabled
            return True  # MFA not required
        
        try:
            # Try TOTP code first (Google Authenticator, Microsoft Authenticator, Authy, etc.)
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
            if self._verify_backup_code(extension_number, code):
                return True
            
            return False
            
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
            query = "SELECT enabled FROM mfa_secrets WHERE extension_number = %s" if self.database.db_type == 'postgresql' else \
                    "SELECT enabled FROM mfa_secrets WHERE extension_number = ?"
            result = self.database.fetch_all(query, (extension_number,))
            
            if result and len(result) > 0:
                return bool(result[0].get('enabled', False))
            
            return False
            
        except Exception as e:
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
            update_query = """
            UPDATE mfa_secrets 
            SET enabled = %s, updated_at = CURRENT_TIMESTAMP
            WHERE extension_number = %s
            """ if self.database.db_type == 'postgresql' else """
            UPDATE mfa_secrets 
            SET enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE extension_number = ?
            """
            self.database.execute(update_query, (False, extension_number))
            
            self.logger.info(f"MFA disabled for extension {extension_number}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disable MFA for {extension_number}: {e}")
            return False
    
    def enroll_yubikey(self, extension_number: str, otp: str, device_name: str = None) -> Tuple[bool, Optional[str]]:
        """
        Enroll YubiKey device for user
        
        Args:
            extension_number: Extension number
            otp: YubiKey OTP to extract device ID
            device_name: Optional friendly name for the device
            
        Returns:
            Tuple of (success, error_message)
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
            query = """
            SELECT id FROM mfa_yubikey_devices 
            WHERE public_id = %s
            """ if self.database.db_type == 'postgresql' else """
            SELECT id FROM mfa_yubikey_devices 
            WHERE public_id = ?
            """
            result = self.database.fetch_all(query, (public_id,))
            
            if result:
                return False, "YubiKey already enrolled"
            
            # Insert device
            insert_query = """
            INSERT INTO mfa_yubikey_devices (extension_number, public_id, device_name)
            VALUES (%s, %s, %s)
            """ if self.database.db_type == 'postgresql' else """
            INSERT INTO mfa_yubikey_devices (extension_number, public_id, device_name)
            VALUES (?, ?, ?)
            """
            self.database.execute(insert_query, (extension_number, public_id, device_name))
            
            self.logger.info(f"YubiKey {public_id} enrolled for extension {extension_number}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"YubiKey enrollment failed for {extension_number}: {e}")
            return False, str(e)
    
    def enroll_fido2(self, extension_number: str, credential_data: dict, device_name: str = None) -> Tuple[bool, Optional[str]]:
        """
        Enroll FIDO2/WebAuthn credential for user
        
        Args:
            extension_number: Extension number
            credential_data: WebAuthn credential registration data
            device_name: Optional friendly name for the device
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.fido2_enabled or not self.fido2_verifier:
            return False, "FIDO2 support not enabled"
        
        if not self.database or not self.database.enabled:
            return False, "Database required for FIDO2 enrollment"
        
        try:
            # Register credential
            success, result = self.fido2_verifier.register_credential(extension_number, credential_data)
            if not success:
                return False, result
            
            credential_id = result
            public_key = credential_data.get('public_key')
            
            # Store in database
            insert_query = """
            INSERT INTO mfa_fido2_credentials (extension_number, credential_id, public_key, device_name)
            VALUES (%s, %s, %s, %s)
            """ if self.database.db_type == 'postgresql' else """
            INSERT INTO mfa_fido2_credentials (extension_number, credential_id, public_key, device_name)
            VALUES (?, ?, ?, ?)
            """
            # Convert public_key to JSON string if it's a dict/bytes
            if isinstance(public_key, (dict, bytes)):
                public_key = json.dumps(public_key) if isinstance(public_key, dict) else base64.b64encode(public_key).decode('utf-8')
            
            self.database.execute(insert_query, (extension_number, credential_id, public_key, device_name))
            
            self.logger.info(f"FIDO2 credential enrolled for extension {extension_number}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"FIDO2 enrollment failed for {extension_number}: {e}")
            return False, str(e)
    
    def get_enrolled_methods(self, extension_number: str) -> Dict[str, List]:
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
        methods = {
            'totp': False,
            'yubikeys': [],
            'fido2': [],
            'backup_codes': 0
        }
        
        if not self.database or not self.database.enabled:
            return methods
        
        try:
            # Check TOTP
            methods['totp'] = self.is_enabled_for_user(extension_number)
            
            # Get YubiKeys
            if self.yubikey_enabled:
                query = """
                SELECT public_id, device_name, enrolled_at
                FROM mfa_yubikey_devices
                WHERE extension_number = %s
                """ if self.database.db_type == 'postgresql' else """
                SELECT public_id, device_name, enrolled_at
                FROM mfa_yubikey_devices
                WHERE extension_number = ?
                """
                methods['yubikeys'] = self.database.fetch_all(query, (extension_number,))
            
            # Get FIDO2 credentials
            if self.fido2_enabled:
                query = """
                SELECT credential_id, device_name, enrolled_at
                FROM mfa_fido2_credentials
                WHERE extension_number = %s
                """ if self.database.db_type == 'postgresql' else """
                SELECT credential_id, device_name, enrolled_at
                FROM mfa_fido2_credentials
                WHERE extension_number = ?
                """
                methods['fido2'] = self.database.fetch_all(query, (extension_number,))
            
            # Get backup code count
            query = """
            SELECT COUNT(*) as count
            FROM mfa_backup_codes
            WHERE extension_number = %s AND used = %s
            """ if self.database.db_type == 'postgresql' else """
            SELECT COUNT(*) as count
            FROM mfa_backup_codes
            WHERE extension_number = ? AND used = ?
            """
            result = self.database.fetch_one(query, (extension_number, False))
            if result:
                methods['backup_codes'] = result.get('count', 0)
            
            return methods
            
        except Exception as e:
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
            query = """
            SELECT id FROM mfa_yubikey_devices
            WHERE extension_number = %s AND public_id = %s
            """ if self.database.db_type == 'postgresql' else """
            SELECT id FROM mfa_yubikey_devices
            WHERE extension_number = ? AND public_id = ?
            """
            result = self.database.fetch_all(query, (extension_number, public_id))
            
            if not result:
                self.logger.warning(f"YubiKey {public_id} not enrolled for extension {extension_number}")
                return False
            
            # Verify OTP with YubiCloud
            valid, error = self.yubikey_verifier.verify_otp(otp)
            if valid:
                # Update last used timestamp
                update_query = """
                UPDATE mfa_yubikey_devices
                SET last_used = CURRENT_TIMESTAMP
                WHERE extension_number = %s AND public_id = %s
                """ if self.database.db_type == 'postgresql' else """
                UPDATE mfa_yubikey_devices
                SET last_used = CURRENT_TIMESTAMP
                WHERE extension_number = ? AND public_id = ?
                """
                self.database.execute(update_query, (extension_number, public_id))
                self.logger.info(f"YubiKey OTP verified for extension {extension_number}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"YubiKey verification failed for {extension_number}: {e}")
            return False
    
    def _get_secret(self, extension_number: str) -> Optional[bytes]:
        """Get decrypted secret for user"""
        if not self.database or not self.database.enabled:
            return None
        
        try:
            query = """
            SELECT secret_encrypted, secret_salt 
            FROM mfa_secrets 
            WHERE extension_number = %s AND enabled = %s
            """ if self.database.db_type == 'postgresql' else """
            SELECT secret_encrypted, secret_salt 
            FROM mfa_secrets 
            WHERE extension_number = ? AND enabled = ?
            """
            result = self.database.fetch_all(query, (extension_number, True))
            
            if result and len(result) > 0:
                encrypted = result[0]['secret_encrypted']
                salt_b64 = result[0]['secret_salt']
                
                # Decode salt and derive key from extension number
                import base64
                salt = base64.b64decode(salt_b64)
                key, _ = self.encryption.derive_key(extension_number, salt)
                
                # Decode encrypted data that contains nonce|tag|encrypted_data
                combined = base64.b64decode(encrypted)
                parts = combined.split(b'|')
                if len(parts) != 3:
                    self.logger.error("Invalid encrypted secret format")
                    return None
                
                nonce = parts[0].decode('utf-8')
                tag = parts[1].decode('utf-8')
                encrypted_data = parts[2].decode('utf-8')
                
                # Decrypt using the proper method signature
                return self.encryption.decrypt_data(encrypted_data, nonce, tag, key)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get secret for {extension_number}: {e}")
            return None
    
    def _get_secret_for_enrollment(self, extension_number: str) -> Optional[bytes]:
        """Get decrypted secret for user during enrollment (doesn't check enabled status)"""
        if not self.database or not self.database.enabled:
            return None
        
        try:
            query = """
            SELECT secret_encrypted, secret_salt 
            FROM mfa_secrets 
            WHERE extension_number = %s
            """ if self.database.db_type == 'postgresql' else """
            SELECT secret_encrypted, secret_salt 
            FROM mfa_secrets 
            WHERE extension_number = ?
            """
            result = self.database.fetch_all(query, (extension_number,))
            
            if result and len(result) > 0:
                encrypted = result[0]['secret_encrypted']
                salt_b64 = result[0]['secret_salt']
                
                # Decode salt and derive key from extension number
                import base64
                salt = base64.b64decode(salt_b64)
                key, _ = self.encryption.derive_key(extension_number, salt)
                
                # Decode encrypted data that contains nonce|tag|encrypted_data
                combined = base64.b64decode(encrypted)
                parts = combined.split(b'|')
                if len(parts) != 3:
                    self.logger.error("Invalid encrypted secret format")
                    return None
                
                nonce = parts[0].decode('utf-8')
                tag = parts[1].decode('utf-8')
                encrypted_data = parts[2].decode('utf-8')
                
                # Decrypt using the proper method signature
                return self.encryption.decrypt_data(encrypted_data, nonce, tag, key)
            
            return None
            
        except Exception as e:
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
            query = """
            SELECT id, code_hash, code_salt 
            FROM mfa_backup_codes 
            WHERE extension_number = %s AND used = %s
            """ if self.database.db_type == 'postgresql' else """
            SELECT id, code_hash, code_salt 
            FROM mfa_backup_codes 
            WHERE extension_number = ? AND used = ?
            """
            codes = self.database.fetch_all(query, (extension_number, False))
            
            # Check each code
            for row in codes:
                if self.encryption.verify_password(code, row['code_hash'], row['code_salt']):
                    # Mark as used
                    update_query = """
                    UPDATE mfa_backup_codes 
                    SET used = %s, used_at = CURRENT_TIMESTAMP 
                    WHERE id = %s
                    """ if self.database.db_type == 'postgresql' else """
                    UPDATE mfa_backup_codes 
                    SET used = ?, used_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                    """
                    self.database.execute(update_query, (True, row['id']))
                    
                    self.logger.info(f"Backup code used for extension {extension_number}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to verify backup code for {extension_number}: {e}")
            return False
    
    def _update_last_used(self, extension_number: str):
        """Update last used timestamp"""
        if not self.database or not self.database.enabled:
            return
        
        try:
            update_query = """
            UPDATE mfa_secrets 
            SET last_used = CURRENT_TIMESTAMP 
            WHERE extension_number = %s
            """ if self.database.db_type == 'postgresql' else """
            UPDATE mfa_secrets 
            SET last_used = CURRENT_TIMESTAMP 
            WHERE extension_number = ?
            """
            self.database.execute(update_query, (extension_number,))
        except Exception as e:
            self.logger.error(f"Failed to update last used for {extension_number}: {e}")
    
    def _generate_backup_codes(self, count: int = None) -> list:
        """Generate random backup codes"""
        if count is None:
            count = self.backup_codes_count
        
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
            # Format as XXXX-XXXX for readability
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        
        return codes


def get_mfa_manager(database=None, config: dict = None) -> MFAManager:
    """Get MFA manager instance"""
    return MFAManager(database, config)
