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


class ThreatDetector:
    """
    Enhanced threat detection system
    Provides advanced pattern detection, IP blocking, and anomaly detection
    """
    
    def __init__(self, database=None, config: dict = None):
        """
        Initialize threat detector
        
        Args:
            database: Database backend for persistent storage
            config: Optional configuration
        """
        self.logger = get_logger()
        self.database = database
        self.config = config or {}
        
        # Threat detection configuration
        # Support both nested dict and dot notation
        self.enabled = self._get_config('security.threat_detection.enabled', True)
        self.ip_block_duration = self._get_config('security.threat_detection.ip_block_duration', 3600)  # 1 hour
        self.failed_login_threshold = self._get_config('security.threat_detection.failed_login_threshold', 10)
        self.suspicious_pattern_threshold = self._get_config('security.threat_detection.suspicious_pattern_threshold', 5)
        
        # In-memory storage for threat tracking
        self.blocked_ips = {}  # {ip: block_until_timestamp}
        self.failed_attempts = {}  # {ip: [(timestamp, reason), ...]}
        self.suspicious_patterns = {}  # {ip: {pattern: count}}
        
        # Initialize database schema if available
        if self.database and self.database.enabled:
            self._initialize_schema()
    
    def _get_config(self, key: str, default=None):
        """
        Get config value supporting both dot notation and nested dicts
        
        Args:
            key: Config key (e.g., 'security.threat_detection.enabled')
            default: Default value if not found
            
        Returns:
            Config value or default
        """
        # Try dot notation first (Config object)
        if hasattr(self.config, 'get') and '.' in key:
            value = self.config.get(key, None)
            if value is not None:
                return value
        
        # Try nested dict navigation
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value if value is not None else default
    
    def _initialize_schema(self):
        """Initialize threat detection database tables"""
        # Blocked IPs table
        blocked_ips_table = """
        CREATE TABLE IF NOT EXISTS security_blocked_ips (
            id SERIAL PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL,
            reason TEXT,
            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            blocked_until TIMESTAMP NOT NULL,
            unblocked_at TIMESTAMP,
            auto_unblocked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.database.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS security_blocked_ips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            reason TEXT,
            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            blocked_until TIMESTAMP NOT NULL,
            unblocked_at TIMESTAMP,
            auto_unblocked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Threat events table
        threat_events_table = """
        CREATE TABLE IF NOT EXISTS security_threat_events (
            id SERIAL PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """ if self.database.db_type == 'postgresql' else """
        CREATE TABLE IF NOT EXISTS security_threat_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        try:
            self.database.execute(blocked_ips_table)
            self.database.execute(threat_events_table)
            self.logger.info("Threat detection database schema initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize threat detection schema: {e}")
    
    def is_ip_blocked(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if IP address is blocked
        
        Args:
            ip_address: IP address to check
            
        Returns:
            Tuple of (is_blocked, reason)
        """
        if not self.enabled:
            return False, None
        
        now = time.time()
        
        # Check in-memory cache
        if ip_address in self.blocked_ips:
            block_until = self.blocked_ips[ip_address]['until']
            if now < block_until:
                return True, self.blocked_ips[ip_address].get('reason', 'IP blocked')
            else:
                # Block expired
                del self.blocked_ips[ip_address]
                self._auto_unblock_ip(ip_address)
        
        # Check database for persistent blocks
        if self.database and self.database.enabled:
            query = """
            SELECT reason, blocked_until 
            FROM security_blocked_ips 
            WHERE ip_address = %s AND blocked_until > CURRENT_TIMESTAMP AND unblocked_at IS NULL
            ORDER BY blocked_at DESC LIMIT 1
            """ if self.database.db_type == 'postgresql' else """
            SELECT reason, blocked_until 
            FROM security_blocked_ips 
            WHERE ip_address = ? AND blocked_until > datetime('now') AND unblocked_at IS NULL
            ORDER BY blocked_at DESC LIMIT 1
            """
            result = self.database.fetch_one(query, (ip_address,))
            
            if result:
                return True, result.get('reason', 'IP blocked')
        
        return False, None
    
    def block_ip(self, ip_address: str, reason: str, duration: int = None):
        """
        Block an IP address
        
        Args:
            ip_address: IP address to block
            reason: Reason for blocking
            duration: Block duration in seconds (uses default if not provided)
        """
        if not self.enabled:
            return
        
        if duration is None:
            duration = self.ip_block_duration
        
        now = time.time()
        block_until = now + duration
        
        # Add to in-memory cache
        self.blocked_ips[ip_address] = {
            'until': block_until,
            'reason': reason
        }
        
        # Store in database
        if self.database and self.database.enabled:
            from datetime import datetime as dt, timedelta
            blocked_until_dt = dt.now() + timedelta(seconds=duration)
            
            insert_query = """
            INSERT INTO security_blocked_ips (ip_address, reason, blocked_until)
            VALUES (%s, %s, %s)
            """ if self.database.db_type == 'postgresql' else """
            INSERT INTO security_blocked_ips (ip_address, reason, blocked_until)
            VALUES (?, ?, ?)
            """
            self.database.execute(insert_query, (ip_address, reason, blocked_until_dt))
        
        self.logger.warning(f"IP {ip_address} blocked: {reason} (duration: {duration}s)")
        self._log_threat_event(ip_address, 'ip_blocked', 'high', reason)
    
    def unblock_ip(self, ip_address: str):
        """
        Manually unblock an IP address
        
        Args:
            ip_address: IP address to unblock
        """
        # Remove from cache
        if ip_address in self.blocked_ips:
            del self.blocked_ips[ip_address]
        
        # Update database
        if self.database and self.database.enabled:
            update_query = """
            UPDATE security_blocked_ips 
            SET unblocked_at = CURRENT_TIMESTAMP 
            WHERE ip_address = %s AND unblocked_at IS NULL
            """ if self.database.db_type == 'postgresql' else """
            UPDATE security_blocked_ips 
            SET unblocked_at = datetime('now')
            WHERE ip_address = ? AND unblocked_at IS NULL
            """
            self.database.execute(update_query, (ip_address,))
        
        self.logger.info(f"IP {ip_address} manually unblocked")
    
    def _auto_unblock_ip(self, ip_address: str):
        """Auto-unblock IP when duration expires"""
        if self.database and self.database.enabled:
            update_query = """
            UPDATE security_blocked_ips 
            SET unblocked_at = CURRENT_TIMESTAMP, auto_unblocked = %s
            WHERE ip_address = %s AND unblocked_at IS NULL
            """ if self.database.db_type == 'postgresql' else """
            UPDATE security_blocked_ips 
            SET unblocked_at = datetime('now'), auto_unblocked = ?
            WHERE ip_address = ? AND unblocked_at IS NULL
            """
            self.database.execute(update_query, (True, ip_address))
    
    def record_failed_attempt(self, ip_address: str, reason: str):
        """
        Record failed authentication attempt
        
        Args:
            ip_address: IP address
            reason: Reason for failure
        """
        if not self.enabled:
            return
        
        now = time.time()
        
        # Initialize tracking for IP
        if ip_address not in self.failed_attempts:
            self.failed_attempts[ip_address] = []
        
        # Add attempt
        self.failed_attempts[ip_address].append((now, reason))
        
        # Clean old attempts (older than 1 hour)
        cutoff = now - 3600
        self.failed_attempts[ip_address] = [
            (t, r) for t, r in self.failed_attempts[ip_address] if t > cutoff
        ]
        
        # Check if threshold exceeded
        if len(self.failed_attempts[ip_address]) >= self.failed_login_threshold:
            self.block_ip(ip_address, f"Excessive failed login attempts ({len(self.failed_attempts[ip_address])})")
            self.failed_attempts[ip_address] = []  # Reset counter
        
        # Log threat event
        self._log_threat_event(ip_address, 'failed_auth', 'medium', reason)
    
    def detect_suspicious_pattern(self, ip_address: str, pattern: str) -> bool:
        """
        Detect suspicious patterns in behavior
        
        Args:
            ip_address: IP address
            pattern: Pattern identifier (e.g., 'rapid_requests', 'scanner_behavior', 'sql_injection')
            
        Returns:
            True if pattern is considered threatening
        """
        if not self.enabled:
            return False
        
        # Initialize tracking for IP
        if ip_address not in self.suspicious_patterns:
            self.suspicious_patterns[ip_address] = {}
        
        # Increment pattern count
        if pattern not in self.suspicious_patterns[ip_address]:
            self.suspicious_patterns[ip_address][pattern] = 0
        
        self.suspicious_patterns[ip_address][pattern] += 1
        count = self.suspicious_patterns[ip_address][pattern]
        
        # Check if threshold exceeded
        if count >= self.suspicious_pattern_threshold:
            self.block_ip(ip_address, f"Suspicious pattern detected: {pattern} (count: {count})")
            self.suspicious_patterns[ip_address][pattern] = 0  # Reset
            return True
        
        # Log threat event
        self._log_threat_event(ip_address, 'suspicious_pattern', 'low', f"{pattern} (count: {count})")
        
        return False
    
    def analyze_request_pattern(self, ip_address: str, user_agent: str = None) -> Dict[str, any]:
        """
        Analyze request patterns for anomalies
        
        Args:
            ip_address: IP address
            user_agent: User agent string
            
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            'is_blocked': False,
            'is_suspicious': False,
            'threats': [],
            'score': 0  # 0-100, higher is more threatening
        }
        
        if not self.enabled:
            return analysis
        
        # Check if blocked
        is_blocked, reason = self.is_ip_blocked(ip_address)
        if is_blocked:
            analysis['is_blocked'] = True
            analysis['threats'].append(f"IP blocked: {reason}")
            analysis['score'] = 100
            return analysis
        
        # Check for scanner patterns in user agent
        if user_agent:
            scanner_keywords = ['nmap', 'nikto', 'sqlmap', 'masscan', 'zap', 'burp', 'w3af', 'metasploit']
            user_agent_lower = user_agent.lower()
            
            for keyword in scanner_keywords:
                if keyword in user_agent_lower:
                    analysis['is_suspicious'] = True
                    analysis['threats'].append(f"Scanner detected in user agent: {keyword}")
                    analysis['score'] += 30
                    self.detect_suspicious_pattern(ip_address, f'scanner_{keyword}')
        
        # Check failed attempt history
        if ip_address in self.failed_attempts:
            recent_failures = len(self.failed_attempts[ip_address])
            if recent_failures > 3:
                analysis['is_suspicious'] = True
                analysis['threats'].append(f"Recent failed attempts: {recent_failures}")
                analysis['score'] += min(recent_failures * 5, 50)
        
        return analysis
    
    def _log_threat_event(self, ip_address: str, event_type: str, severity: str, details: str):
        """Log threat event to database"""
        if not self.database or not self.database.enabled:
            return
        
        try:
            insert_query = """
            INSERT INTO security_threat_events (ip_address, event_type, severity, details)
            VALUES (%s, %s, %s, %s)
            """ if self.database.db_type == 'postgresql' else """
            INSERT INTO security_threat_events (ip_address, event_type, severity, details)
            VALUES (?, ?, ?, ?)
            """
            self.database.execute(insert_query, (ip_address, event_type, severity, details))
        except Exception as e:
            self.logger.error(f"Failed to log threat event: {e}")
    
    def get_threat_summary(self, hours: int = 24) -> Dict:
        """
        Get summary of recent threats
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with threat statistics
        """
        summary = {
            'total_events': 0,
            'blocked_ips': 0,
            'suspicious_patterns': 0,
            'failed_auths': 0,
            'severity_counts': {'low': 0, 'medium': 0, 'high': 0}
        }
        
        if not self.database or not self.database.enabled:
            # Return in-memory stats
            summary['blocked_ips'] = len(self.blocked_ips)
            return summary
        
        try:
            # Count events by type
            if self.database.db_type == 'postgresql':
                query = """
                SELECT event_type, severity, COUNT(*) as count
                FROM security_threat_events
                WHERE timestamp > (CURRENT_TIMESTAMP - INTERVAL '%s hours')
                GROUP BY event_type, severity
                """
                results = self.database.fetch_all(query, (hours,))
            else:
                # SQLite: build the interval string manually
                query = f"""
                SELECT event_type, severity, COUNT(*) as count
                FROM security_threat_events
                WHERE timestamp > datetime('now', '-{hours} hours')
                GROUP BY event_type, severity
                """
                results = self.database.fetch_all(query)
            
            for row in results:
                event_type = row['event_type']
                severity = row['severity']
                count = row['count']
                
                summary['total_events'] += count
                summary['severity_counts'][severity] = summary['severity_counts'].get(severity, 0) + count
                
                if event_type == 'ip_blocked':
                    summary['blocked_ips'] += count
                elif event_type == 'suspicious_pattern':
                    summary['suspicious_patterns'] += count
                elif event_type == 'failed_auth':
                    summary['failed_auths'] += count
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get threat summary: {e}")
            return summary


def get_threat_detector(database=None, config: dict = None) -> ThreatDetector:
    """Get threat detector instance"""
    return ThreatDetector(database, config)
