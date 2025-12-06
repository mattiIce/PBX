"""
Security utilities for PBX system
Provides password management, rate limiting, and security validation
"""
import re
import hashlib
import secrets
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from pbx.utils.logger import get_logger
from pbx.utils.encryption import get_encryption


class PasswordPolicy:
    """Password complexity and validation policies"""
    
    # Default password requirements
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Common weak passwords to block (case will be normalized during check)
    COMMON_PASSWORDS = {
        'password', 'password123', 'password123!', 'password1', 'password1!',
        'admin', 'admin123', '12345678', '123456789', '1234567890',
        'qwerty', 'qwerty123', 'letmein', 'welcome', 'welcome1', 'monkey',
        'passw0rd', 'p@ssword', 'p@ssw0rd'
    }
    
    def __init__(self, config: dict = None):
        """
        Initialize password policy
        
        Args:
            config: Optional configuration overrides
        """
        self.logger = get_logger()
        self.config = config or {}
        
        # Load policy from config
        self.min_length = self.config.get('security.password.min_length', self.MIN_LENGTH)
        self.max_length = self.config.get('security.password.max_length', self.MAX_LENGTH)
        self.require_uppercase = self.config.get('security.password.require_uppercase', self.REQUIRE_UPPERCASE)
        self.require_lowercase = self.config.get('security.password.require_lowercase', self.REQUIRE_LOWERCASE)
        self.require_digit = self.config.get('security.password.require_digit', self.REQUIRE_DIGIT)
        self.require_special = self.config.get('security.password.require_special', self.REQUIRE_SPECIAL)
    
    def validate(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password against policy
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password cannot be empty"
        
        # Check length
        if len(password) < self.min_length:
            return False, f"Password must be at least {self.min_length} characters"
        
        if len(password) > self.max_length:
            return False, f"Password must be no more than {self.max_length} characters"
        
        # Check for common weak passwords (case-insensitive)
        common_passwords_lower = {p.lower() for p in self.COMMON_PASSWORDS}
        if password.lower() in common_passwords_lower:
            return False, "Password is too common and easily guessed"
        
        # Check complexity requirements
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if self.require_digit and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if self.require_special and not re.search(f'[{re.escape(self.SPECIAL_CHARS)}]', password):
            return False, f"Password must contain at least one special character: {self.SPECIAL_CHARS}"
        
        # Check for sequential characters (4 or more in sequence)
        if self._has_sequential_chars(password, min_sequence=4):
            return False, "Password contains sequential characters (e.g., '1234', 'abcd')"
        
        # Check for repeated characters (4 or more repeated)
        if self._has_repeated_chars(password, max_repeat=4):
            return False, "Password contains too many repeated characters"
        
        return True, None
    
    def _has_sequential_chars(self, password: str, min_sequence: int = 3) -> bool:
        """Check for sequential characters like '123' or 'abc'"""
        for i in range(len(password) - min_sequence + 1):
            # Check numeric sequences
            if password[i:i+min_sequence].isdigit():
                nums = [int(c) for c in password[i:i+min_sequence]]
                if all(nums[j+1] == nums[j] + 1 for j in range(len(nums)-1)):
                    return True
            
            # Check alphabetic sequences
            if password[i:i+min_sequence].isalpha():
                chars = [ord(c.lower()) for c in password[i:i+min_sequence]]
                if all(chars[j+1] == chars[j] + 1 for j in range(len(chars)-1)):
                    return True
        
        return False
    
    def _has_repeated_chars(self, password: str, max_repeat: int = 3) -> bool:
        """Check for repeated characters like 'aaa' or '111'"""
        for i in range(len(password) - max_repeat + 1):
            if len(set(password[i:i+max_repeat])) == 1:
                return True
        return False
    
    def generate_strong_password(self, length: int = 16) -> str:
        """
        Generate a strong random password
        
        Args:
            length: Password length (default 16)
            
        Returns:
            Strong random password meeting all requirements
        """
        if length < self.min_length:
            length = self.min_length
        
        # Ensure we have all required character types
        chars = []
        if self.require_uppercase:
            chars.append(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        if self.require_lowercase:
            chars.append(secrets.choice('abcdefghijklmnopqrstuvwxyz'))
        if self.require_digit:
            chars.append(secrets.choice('0123456789'))
        if self.require_special:
            chars.append(secrets.choice(self.SPECIAL_CHARS))
        
        # Fill remaining length with random characters
        all_chars = ''
        if self.require_uppercase:
            all_chars += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if self.require_lowercase:
            all_chars += 'abcdefghijklmnopqrstuvwxyz'
        if self.require_digit:
            all_chars += '0123456789'
        if self.require_special:
            all_chars += self.SPECIAL_CHARS
        
        while len(chars) < length:
            chars.append(secrets.choice(all_chars))
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(chars)
        
        return ''.join(chars)


class RateLimiter:
    """Rate limiting for authentication attempts"""
    
    def __init__(self, config: dict = None):
        """
        Initialize rate limiter
        
        Args:
            config: Optional configuration
        """
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        self.max_attempts = self.config.get('security.rate_limit.max_attempts', 5)
        self.window_seconds = self.config.get('security.rate_limit.window_seconds', 300)  # 5 minutes
        self.lockout_duration = self.config.get('security.rate_limit.lockout_duration', 900)  # 15 minutes
        
        # In-memory storage for attempts
        # Format: {identifier: [(timestamp1, timestamp2, ...)]}
        self.attempts = {}
        self.lockouts = {}
    
    def is_rate_limited(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if identifier is rate limited
        
        Args:
            identifier: User identifier (username, IP, etc.)
            
        Returns:
            Tuple of (is_limited, seconds_until_unlock)
        """
        now = time.time()
        
        # Check if currently locked out
        if identifier in self.lockouts:
            lockout_time = self.lockouts[identifier]
            if now < lockout_time:
                remaining = int(lockout_time - now)
                return True, remaining
            else:
                # Lockout expired
                del self.lockouts[identifier]
                if identifier in self.attempts:
                    del self.attempts[identifier]
        
        # Clean old attempts outside window
        if identifier in self.attempts:
            cutoff = now - self.window_seconds
            self.attempts[identifier] = [t for t in self.attempts[identifier] if t > cutoff]
            
            # Check if over limit
            if len(self.attempts[identifier]) >= self.max_attempts:
                # Initiate lockout
                self.lockouts[identifier] = now + self.lockout_duration
                self.logger.warning(f"Rate limit exceeded for {identifier}. Locked out for {self.lockout_duration} seconds")
                return True, self.lockout_duration
        
        return False, None
    
    def record_attempt(self, identifier: str, successful: bool = False):
        """
        Record an authentication attempt
        
        Args:
            identifier: User identifier
            successful: Whether attempt was successful
        """
        now = time.time()
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Record the attempt
        self.attempts[identifier].append(now)
        
        # If successful, clear the attempts
        if successful:
            if identifier in self.attempts:
                del self.attempts[identifier]
            if identifier in self.lockouts:
                del self.lockouts[identifier]
    
    def clear_attempts(self, identifier: str):
        """Clear all attempts for an identifier"""
        if identifier in self.attempts:
            del self.attempts[identifier]
        if identifier in self.lockouts:
            del self.lockouts[identifier]


class SecurityAuditor:
    """Security event audit logging"""
    
    EVENT_LOGIN_SUCCESS = 'login_success'
    EVENT_LOGIN_FAILURE = 'login_failure'
    EVENT_PASSWORD_CHANGE = 'password_change'
    EVENT_PASSWORD_RESET = 'password_reset'
    EVENT_ACCOUNT_LOCKED = 'account_locked'
    EVENT_ACCOUNT_UNLOCKED = 'account_unlocked'
    EVENT_PERMISSION_DENIED = 'permission_denied'
    EVENT_CONFIG_CHANGE = 'config_change'
    EVENT_SUSPICIOUS_ACTIVITY = 'suspicious_activity'
    
    def __init__(self, database=None, config: dict = None):
        """
        Initialize security auditor
        
        Args:
            database: Optional database backend for persistent logging
            config: Optional configuration
        """
        self.logger = get_logger()
        self.database = database
        self.config = config or {}
        self.enabled = self.config.get('security.audit.enabled', True)
    
    def log_event(self, event_type: str, identifier: str, details: dict = None, 
                  success: bool = True, ip_address: str = None):
        """
        Log a security event
        
        Args:
            event_type: Type of security event
            identifier: User/extension identifier
            details: Additional event details
            success: Whether action was successful
            ip_address: IP address of request
        """
        if not self.enabled:
            return
        
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'identifier': identifier,
            'success': success,
            'ip_address': ip_address,
            'details': details or {}
        }
        
        # Log to standard logger
        level = 'INFO' if success else 'WARNING'
        log_msg = f"SECURITY: {event_type} - {identifier}"
        if ip_address:
            log_msg += f" from {ip_address}"
        log_msg += f" - {'SUCCESS' if success else 'FAILED'}"
        
        if level == 'INFO':
            self.logger.info(log_msg)
        else:
            self.logger.warning(log_msg)
        
        # Store in database if available
        if self.database and self.database.enabled:
            try:
                self._store_audit_log(log_entry)
            except Exception as e:
                self.logger.error(f"Failed to store audit log: {e}")
    
    def _store_audit_log(self, log_entry: dict):
        """Store audit log in database"""
        import json
        
        query = """
        INSERT INTO security_audit (timestamp, event_type, identifier, ip_address, success, details)
        VALUES (%s, %s, %s, %s, %s, %s)
        """ if self.database.db_type == 'postgresql' else """
        INSERT INTO security_audit (timestamp, event_type, identifier, ip_address, success, details)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        params = (
            log_entry['timestamp'],
            log_entry['event_type'],
            log_entry['identifier'],
            log_entry.get('ip_address'),
            log_entry['success'],
            json.dumps(log_entry.get('details', {}))
        )
        
        self.database.execute(query, params)


class SecurePasswordManager:
    """Secure password storage and verification"""
    
    def __init__(self, config: dict = None):
        """
        Initialize password manager
        
        Args:
            config: Optional configuration
        """
        self.logger = get_logger()
        self.config = config or {}
        
        # Get FIPS mode from config - default to True for security
        fips_mode = self.config.get('security.fips_mode', True)
        
        # Enforce FIPS mode if explicitly enabled in config
        enforce_fips = fips_mode and self.config.get('security.enforce_fips', True)
        
        if fips_mode:
            self.logger.info("Initializing password manager with FIPS 140-2 compliance")
        
        self.encryption = get_encryption(fips_mode, enforce_fips)
        self.policy = PasswordPolicy(config)
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """
        Hash password for secure storage
        
        Args:
            password: Plain text password
            
        Returns:
            Tuple of (hashed_password, salt) as base64 strings
        """
        return self.encryption.hash_password(password)
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Plain text password
            hashed_password: Base64-encoded hash
            salt: Base64-encoded salt
            
        Returns:
            True if password matches
        """
        return self.encryption.verify_password(password, hashed_password, salt)
    
    def validate_new_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate new password against policy
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.policy.validate(password)
    
    def generate_password(self, length: int = 16) -> str:
        """
        Generate a strong random password
        
        Args:
            length: Password length
            
        Returns:
            Strong random password
        """
        return self.policy.generate_strong_password(length)


def get_rate_limiter(config: dict = None) -> RateLimiter:
    """Get rate limiter instance"""
    return RateLimiter(config)


def get_security_auditor(database=None, config: dict = None) -> SecurityAuditor:
    """Get security auditor instance"""
    return SecurityAuditor(database, config)


def get_password_manager(config: dict = None) -> SecurePasswordManager:
    """Get password manager instance"""
    return SecurePasswordManager(config)
