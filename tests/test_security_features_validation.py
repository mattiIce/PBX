#!/usr/bin/env python3
"""
Comprehensive security feature validation tests
Verifies all security features are functional and properly enforced
"""


from pbx.utils.config import Config
from pbx.utils.encryption import CRYPTO_AVAILABLE, get_encryption
from pbx.utils.security import (
    PasswordPolicy,
    RateLimiter,
    SecurityAuditor,
    ThreatDetector,
    get_password_manager,
)


def test_fips_encryption_active() -> None:
    """Test that FIPS encryption is active and functional"""

    config = Config("config.yml")
    fips_mode = config.get("security.fips_mode", False)

    assert fips_mode is True, "FIPS mode should be enabled in config"

    if CRYPTO_AVAILABLE:
        enc = get_encryption(fips_mode=True, enforce_fips=True)

        # Test password hashing
        password = "TestPassword123!"
        hash_val, salt = enc.hash_password(password)
        verified = enc.verify_password(password, hash_val, salt)

        assert verified is True, "Password verification should work"

        # Test encryption
        key, salt = enc.derive_key("encryption_key", key_length=32)
        data = "Sensitive data"
        encrypted, nonce, tag = enc.encrypt_data(data, key)
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key)

        assert decrypted.decode() == data, "Encryption/decryption should work"
    else:
        pass


def test_password_policy_enforcement() -> None:
    """Test password policy is properly enforced"""

    config = Config("config.yml")
    policy = PasswordPolicy(config)

    # Test strong password (should pass)
    strong_password = "StrongP@ssw0rd123"
    is_valid, error = policy.validate(strong_password)
    assert is_valid is True, f"Strong password should be valid: {error}"

    # Test weak passwords (should fail)
    weak_passwords = [
        ("short", "Password must be at least"),
        (
            "Password123!",
            "Password is too common",
        ),  # Changed to meet length requirement but still common
        ("NoDigitsSpecial!", "must contain at least one digit"),
        ("NoSpecial12345", "must contain at least one special character"),
        ("NOLOWERCASE123!", "must contain at least one lowercase"),
        ("nouppercase123!", "must contain at least one uppercase"),
        ("Abcd12345678!", "sequential characters"),
        ("Aaaaaaa!9876", "too many repeated characters"),  # No sequential, just repeated
    ]

    for weak_pw, expected_error_part in weak_passwords:
        is_valid, error = policy.validate(weak_pw)
        assert is_valid is False, f"Weak password '{weak_pw}' should be rejected"
        assert expected_error_part in error, f"Error message should contain '{expected_error_part}'"


    # Test password generation
    generated = policy.generate_strong_password()
    is_valid, error = policy.validate(generated)
    assert is_valid is True, f"Generated password should be valid: {error}"


def test_rate_limiting_enforcement() -> None:
    """Test rate limiting is properly enforced"""

    config = Config("config.yml")
    limiter = RateLimiter(config)

    test_user = "test_user_123"

    # Check initial state (should not be limited)
    is_limited, remaining = limiter.is_rate_limited(test_user)
    assert is_limited is False, "User should not be initially limited"

    # Record failed attempts up to limit
    max_attempts = config.get("security.rate_limit.max_attempts", 5)
    for i in range(max_attempts):
        limiter.record_attempt(test_user, successful=False)

    # Check if now limited
    is_limited, remaining = limiter.is_rate_limited(test_user)
    assert is_limited is True, "User should be limited after max attempts"
    assert remaining > 0, "Should have lockout time remaining"

    # Test successful login clears attempts
    limiter.clear_attempts(test_user)
    is_limited, remaining = limiter.is_rate_limited(test_user)
    assert is_limited is False, "User should not be limited after clearing"


def test_audit_logging_functional() -> None:
    """Test security audit logging is functional"""

    config = Config("config.yml")
    audit_enabled = config.get("security.audit.enabled", False)

    assert audit_enabled is True, "Audit logging should be enabled"

    auditor = SecurityAuditor(database=None, config=config)

    # Test logging various security events
    events = [
        (SecurityAuditor.EVENT_LOGIN_SUCCESS, "user123", True),
        (SecurityAuditor.EVENT_LOGIN_FAILURE, "user456", False),
        (SecurityAuditor.EVENT_PASSWORD_CHANGE, "user789", True),
        (SecurityAuditor.EVENT_ACCOUNT_LOCKED, "user999", False),
    ]

    for event_type, identifier, success in events:
        try:
            auditor.log_event(
                event_type=event_type,
                identifier=identifier,
                success=success,
                ip_address="192.168.1.100",
                details={"test": "data"},
            )
        except Exception as e:
            assert False, f"Audit logging should not raise exception: {e}"


def test_threat_detection_functional() -> None:
    """Test threat detection is functional"""

    config = Config("config.yml")
    threat_enabled = config.get("security.threat_detection.enabled", True)


    detector = ThreatDetector(database=None, config=config)

    # Test IP blocking
    test_ip = "192.168.1.200"

    # Check initial state
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked is False, "IP should not be initially blocked"

    # Block IP
    detector.block_ip(test_ip, "Test blocking", duration=60)

    # Check if blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked is True, "IP should be blocked"
    assert "Test blocking" in reason, "Block reason should match"

    # Unblock IP
    detector.unblock_ip(test_ip)
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked is False, "IP should be unblocked"

    # Test failed attempt recording
    for i in range(3):
        detector.record_failed_attempt(test_ip, f"Failed attempt {i + 1}")

    # Test suspicious pattern detection
    patterns_to_test = ["rapid_requests", "scanner_behavior", "sql_injection"]
    for pattern in patterns_to_test:
        detector.detect_suspicious_pattern(test_ip, pattern)

    # Test request pattern analysis
    analysis = detector.analyze_request_pattern(test_ip, user_agent="Mozilla/5.0")
    assert "is_blocked" in analysis, "Analysis should include blocking status"
    assert "is_suspicious" in analysis, "Analysis should include suspicion flag"
    assert "score" in analysis, "Analysis should include threat score"


def test_password_manager_integration() -> None:
    """Test secure password manager integration"""

    config = Config("config.yml")
    manager = get_password_manager(config)

    # Test password hashing
    password = "SecureTestP@ss123"
    hash_val, salt = manager.hash_password(password)
    assert len(hash_val) > 0, "Hash should not be empty"
    assert len(salt) > 0, "Salt should not be empty"

    # Test password verification
    is_valid = manager.verify_password(password, hash_val, salt)
    assert is_valid is True, "Password verification should succeed"

    wrong_password = "WrongP@ssw0rd123"
    is_invalid = manager.verify_password(wrong_password, hash_val, salt)
    assert is_invalid is False, "Wrong password should fail verification"

    # Test password validation
    is_valid, error = manager.validate_new_password(password)
    assert is_valid is True, f"Valid password should pass: {error}"

    # Test password generation
    generated = manager.generate_password(16)
    is_valid, error = manager.validate_new_password(generated)
    assert is_valid is True, f"Generated password should be valid: {error}"


def test_all_security_defaults() -> None:
    """Test that all security features have secure defaults"""

    config = Config("config.yml")

    # Check FIPS defaults
    fips_mode = config.get("security.fips_mode", False)
    enforce_fips = config.get("security.enforce_fips", False)
    assert fips_mode is True, "FIPS mode should be enabled by default"
    assert enforce_fips is True, "FIPS enforcement should be enabled by default"

    # Check password policy defaults
    min_length = config.get("security.password.min_length", 0)
    require_uppercase = config.get("security.password.require_uppercase", False)
    require_lowercase = config.get("security.password.require_lowercase", False)
    require_digit = config.get("security.password.require_digit", False)
    require_special = config.get("security.password.require_special", False)

    assert min_length >= 12, f"Min password length should be >= 12, got {min_length}"
    assert require_uppercase is True, "Uppercase requirement should be enabled"
    assert require_lowercase is True, "Lowercase requirement should be enabled"
    assert require_digit is True, "Digit requirement should be enabled"
    assert require_special is True, "Special char requirement should be enabled"

    # Check rate limiting defaults
    max_attempts = config.get("security.rate_limit.max_attempts", 0)
    window_seconds = config.get("security.rate_limit.window_seconds", 0)
    lockout_duration = config.get("security.rate_limit.lockout_duration", 0)

    assert (
        max_attempts > 0 and max_attempts <= 10
    ), f"Max attempts should be 1-10, got {max_attempts}"
    assert window_seconds > 0, f"Window should be > 0, got {window_seconds}"
    assert lockout_duration > 0, f"Lockout should be > 0, got {lockout_duration}"

    # Check audit logging defaults
    audit_enabled = config.get("security.audit.enabled", False)
    log_to_database = config.get("security.audit.log_to_database", False)

    assert audit_enabled is True, "Audit logging should be enabled"
    assert log_to_database is True, "Database logging should be enabled"

    # Check threat detection defaults
    threat_enabled = config.get("security.threat_detection.enabled", False)


def test_security_features_cannot_be_bypassed() -> None:
    """Test that security features cannot be easily bypassed"""

    config = Config("config.yml")

    # Test 1: FIPS mode cannot be disabled without explicit config change
    fips_mode = config.get("security.fips_mode", False)
    assert fips_mode is True, "FIPS should be enabled (cannot bypass)"

    # Test 2: Password policy cannot accept weak passwords
    policy = PasswordPolicy(config)
    weak_passwords = ["weak", "123456", "password"]
    for weak_pw in weak_passwords:
        is_valid, _ = policy.validate(weak_pw)
        assert is_valid is False, f"Weak password '{weak_pw}' should be rejected"

    # Test 3: Rate limiting cannot be bypassed
    limiter = RateLimiter(config)
    test_user = "bypass_test_user"

    # Try to exceed limit
    max_attempts = config.get("security.rate_limit.max_attempts", 5)
    for i in range(max_attempts + 1):
        limiter.record_attempt(test_user, successful=False)

    is_limited, _ = limiter.is_rate_limited(test_user)
    assert is_limited is True, "Rate limit should be enforced"

    # Test 4: Security auditor always logs when enabled
    auditor = SecurityAuditor(database=None, config=config)
    assert auditor.enabled is True, "Auditor should be enabled"
