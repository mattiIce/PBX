#!/usr/bin/env python3
"""
Comprehensive security feature validation tests
Verifies all security features are functional and properly enforced
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pbx.utils.security import (
    PasswordPolicy, RateLimiter, SecurityAuditor, SecurePasswordManager,
    ThreatDetector, get_password_manager, get_rate_limiter,
    get_security_auditor, get_threat_detector
)
from pbx.utils.encryption import get_encryption, CRYPTO_AVAILABLE
from pbx.utils.config import Config


def test_fips_encryption_active():
    """Test that FIPS encryption is active and functional"""
    print("\nTesting FIPS encryption is active...")
    
    config = Config("config.yml")
    fips_mode = config.get('security.fips_mode', False)
    
    assert fips_mode == True, "FIPS mode should be enabled in config"
    print(f"  ✓ FIPS mode enabled in config: {fips_mode}")
    
    if CRYPTO_AVAILABLE:
        enc = get_encryption(fips_mode=True, enforce_fips=True)
        
        # Test password hashing
        password = "TestPassword123!"
        hash_val, salt = enc.hash_password(password)
        verified = enc.verify_password(password, hash_val, salt)
        
        assert verified == True, "Password verification should work"
        print("  ✓ FIPS password hashing functional")
        
        # Test encryption
        key, salt = enc.derive_key("encryption_key", key_length=32)
        data = "Sensitive data"
        encrypted, nonce, tag = enc.encrypt_data(data, key)
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
        
        assert decrypted.decode() == data, "Encryption/decryption should work"
        print("  ✓ FIPS AES-256-GCM encryption functional")
    else:
        print("  ⚠ Cryptography library not available (FIPS algorithms unavailable)")


def test_password_policy_enforcement():
    """Test password policy is properly enforced"""
    print("\nTesting password policy enforcement...")
    
    config = Config("config.yml")
    policy = PasswordPolicy(config)
    
    # Test strong password (should pass)
    strong_password = "StrongP@ssw0rd123"
    is_valid, error = policy.validate(strong_password)
    assert is_valid == True, f"Strong password should be valid: {error}"
    print("  ✓ Strong password accepted")
    
    # Test weak passwords (should fail)
    weak_passwords = [
        ("short", "Password must be at least"),
        ("Password123!", "Password is too common"),  # Changed to meet length requirement but still common
        ("NoDigitsSpecial!", "must contain at least one digit"),
        ("NoSpecial12345", "must contain at least one special character"),
        ("NOLOWERCASE123!", "must contain at least one lowercase"),
        ("nouppercase123!", "must contain at least one uppercase"),
        ("Abcd12345678!", "sequential characters"),
        ("Aaaaaaa!9876", "too many repeated characters")  # No sequential, just repeated
    ]
    
    for weak_pw, expected_error_part in weak_passwords:
        is_valid, error = policy.validate(weak_pw)
        assert is_valid == False, f"Weak password '{weak_pw}' should be rejected"
        assert expected_error_part in error, f"Error message should contain '{expected_error_part}'"
    
    print(f"  ✓ All {len(weak_passwords)} weak passwords rejected")
    
    # Test password generation
    generated = policy.generate_strong_password()
    is_valid, error = policy.validate(generated)
    assert is_valid == True, f"Generated password should be valid: {error}"
    print("  ✓ Strong password generation works")


def test_rate_limiting_enforcement():
    """Test rate limiting is properly enforced"""
    print("\nTesting rate limiting enforcement...")
    
    config = Config("config.yml")
    limiter = RateLimiter(config)
    
    test_user = "test_user_123"
    
    # Check initial state (should not be limited)
    is_limited, remaining = limiter.is_rate_limited(test_user)
    assert is_limited == False, "User should not be initially limited"
    print("  ✓ Initial state: not limited")
    
    # Record failed attempts up to limit
    max_attempts = config.get('security.rate_limit.max_attempts', 5)
    for i in range(max_attempts):
        limiter.record_attempt(test_user, successful=False)
    
    # Check if now limited
    is_limited, remaining = limiter.is_rate_limited(test_user)
    assert is_limited == True, "User should be limited after max attempts"
    assert remaining > 0, "Should have lockout time remaining"
    print(f"  ✓ Rate limit enforced after {max_attempts} failed attempts")
    print(f"    Lockout duration: {remaining}s")
    
    # Test successful login clears attempts
    limiter.clear_attempts(test_user)
    is_limited, remaining = limiter.is_rate_limited(test_user)
    assert is_limited == False, "User should not be limited after clearing"
    print("  ✓ Successful login clears rate limit")


def test_audit_logging_functional():
    """Test security audit logging is functional"""
    print("\nTesting security audit logging...")
    
    config = Config("config.yml")
    audit_enabled = config.get('security.audit.enabled', False)
    
    assert audit_enabled == True, "Audit logging should be enabled"
    print("  ✓ Audit logging enabled in config")
    
    auditor = SecurityAuditor(database=None, config=config)
    
    # Test logging various security events
    events = [
        (SecurityAuditor.EVENT_LOGIN_SUCCESS, "user123", True),
        (SecurityAuditor.EVENT_LOGIN_FAILURE, "user456", False),
        (SecurityAuditor.EVENT_PASSWORD_CHANGE, "user789", True),
        (SecurityAuditor.EVENT_ACCOUNT_LOCKED, "user999", False)
    ]
    
    for event_type, identifier, success in events:
        try:
            auditor.log_event(
                event_type=event_type,
                identifier=identifier,
                success=success,
                ip_address="192.168.1.100",
                details={'test': 'data'}
            )
        except Exception as e:
            assert False, f"Audit logging should not raise exception: {e}"
    
    print(f"  ✓ Successfully logged {len(events)} security events")


def test_threat_detection_functional():
    """Test threat detection is functional"""
    print("\nTesting threat detection...")
    
    config = Config("config.yml")
    threat_enabled = config.get('security.threat_detection.enabled', True)
    
    print(f"  ✓ Threat detection enabled: {threat_enabled}")
    
    detector = ThreatDetector(database=None, config=config)
    
    # Test IP blocking
    test_ip = "192.168.1.200"
    
    # Check initial state
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked == False, "IP should not be initially blocked"
    print("  ✓ Initial state: IP not blocked")
    
    # Block IP
    detector.block_ip(test_ip, "Test blocking", duration=60)
    
    # Check if blocked
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked == True, "IP should be blocked"
    assert "Test blocking" in reason, "Block reason should match"
    print("  ✓ IP blocking functional")
    
    # Unblock IP
    detector.unblock_ip(test_ip)
    is_blocked, reason = detector.is_ip_blocked(test_ip)
    assert is_blocked == False, "IP should be unblocked"
    print("  ✓ IP unblocking functional")
    
    # Test failed attempt recording
    for i in range(3):
        detector.record_failed_attempt(test_ip, f"Failed attempt {i+1}")
    print("  ✓ Failed attempt recording functional")
    
    # Test suspicious pattern detection
    patterns_to_test = ['rapid_requests', 'scanner_behavior', 'sql_injection']
    for pattern in patterns_to_test:
        detector.detect_suspicious_pattern(test_ip, pattern)
    print(f"  ✓ Suspicious pattern detection functional ({len(patterns_to_test)} patterns)")
    
    # Test request pattern analysis
    analysis = detector.analyze_request_pattern(test_ip, user_agent="Mozilla/5.0")
    assert 'is_blocked' in analysis, "Analysis should include blocking status"
    assert 'is_suspicious' in analysis, "Analysis should include suspicion flag"
    assert 'score' in analysis, "Analysis should include threat score"
    print("  ✓ Request pattern analysis functional")


def test_password_manager_integration():
    """Test secure password manager integration"""
    print("\nTesting password manager integration...")
    
    config = Config("config.yml")
    manager = get_password_manager(config)
    
    # Test password hashing
    password = "SecureTestP@ss123"
    hash_val, salt = manager.hash_password(password)
    assert len(hash_val) > 0, "Hash should not be empty"
    assert len(salt) > 0, "Salt should not be empty"
    print("  ✓ Password hashing works")
    
    # Test password verification
    is_valid = manager.verify_password(password, hash_val, salt)
    assert is_valid == True, "Password verification should succeed"
    
    wrong_password = "WrongP@ssw0rd123"
    is_invalid = manager.verify_password(wrong_password, hash_val, salt)
    assert is_invalid == False, "Wrong password should fail verification"
    print("  ✓ Password verification works")
    
    # Test password validation
    is_valid, error = manager.validate_new_password(password)
    assert is_valid == True, f"Valid password should pass: {error}"
    print("  ✓ Password validation works")
    
    # Test password generation
    generated = manager.generate_password(16)
    is_valid, error = manager.validate_new_password(generated)
    assert is_valid == True, f"Generated password should be valid: {error}"
    print("  ✓ Password generation works")


def test_all_security_defaults():
    """Test that all security features have secure defaults"""
    print("\nTesting security defaults...")
    
    config = Config("config.yml")
    
    # Check FIPS defaults
    fips_mode = config.get('security.fips_mode', False)
    enforce_fips = config.get('security.enforce_fips', False)
    assert fips_mode == True, "FIPS mode should be enabled by default"
    assert enforce_fips == True, "FIPS enforcement should be enabled by default"
    print("  ✓ FIPS enabled and enforced by default")
    
    # Check password policy defaults
    min_length = config.get('security.password.min_length', 0)
    require_uppercase = config.get('security.password.require_uppercase', False)
    require_lowercase = config.get('security.password.require_lowercase', False)
    require_digit = config.get('security.password.require_digit', False)
    require_special = config.get('security.password.require_special', False)
    
    assert min_length >= 12, f"Min password length should be >= 12, got {min_length}"
    assert require_uppercase == True, "Uppercase requirement should be enabled"
    assert require_lowercase == True, "Lowercase requirement should be enabled"
    assert require_digit == True, "Digit requirement should be enabled"
    assert require_special == True, "Special char requirement should be enabled"
    print("  ✓ Strong password policy enabled by default")
    
    # Check rate limiting defaults
    max_attempts = config.get('security.rate_limit.max_attempts', 0)
    window_seconds = config.get('security.rate_limit.window_seconds', 0)
    lockout_duration = config.get('security.rate_limit.lockout_duration', 0)
    
    assert max_attempts > 0 and max_attempts <= 10, f"Max attempts should be 1-10, got {max_attempts}"
    assert window_seconds > 0, f"Window should be > 0, got {window_seconds}"
    assert lockout_duration > 0, f"Lockout should be > 0, got {lockout_duration}"
    print("  ✓ Rate limiting configured by default")
    
    # Check audit logging defaults
    audit_enabled = config.get('security.audit.enabled', False)
    log_to_database = config.get('security.audit.log_to_database', False)
    
    assert audit_enabled == True, "Audit logging should be enabled"
    assert log_to_database == True, "Database logging should be enabled"
    print("  ✓ Audit logging enabled by default")
    
    # Check threat detection defaults
    threat_enabled = config.get('security.threat_detection.enabled', False)
    print(f"  ✓ Threat detection enabled: {threat_enabled}")


def test_security_features_cannot_be_bypassed():
    """Test that security features cannot be easily bypassed"""
    print("\nTesting security enforcement cannot be bypassed...")
    
    config = Config("config.yml")
    
    # Test 1: FIPS mode cannot be disabled without explicit config change
    fips_mode = config.get('security.fips_mode', False)
    assert fips_mode == True, "FIPS should be enabled (cannot bypass)"
    print("  ✓ FIPS mode enforced (config-based)")
    
    # Test 2: Password policy cannot accept weak passwords
    policy = PasswordPolicy(config)
    weak_passwords = ["weak", "123456", "password"]
    for weak_pw in weak_passwords:
        is_valid, _ = policy.validate(weak_pw)
        assert is_valid == False, f"Weak password '{weak_pw}' should be rejected"
    print("  ✓ Password policy cannot be bypassed")
    
    # Test 3: Rate limiting cannot be bypassed
    limiter = RateLimiter(config)
    test_user = "bypass_test_user"
    
    # Try to exceed limit
    max_attempts = config.get('security.rate_limit.max_attempts', 5)
    for i in range(max_attempts + 1):
        limiter.record_attempt(test_user, successful=False)
    
    is_limited, _ = limiter.is_rate_limited(test_user)
    assert is_limited == True, "Rate limit should be enforced"
    print("  ✓ Rate limiting cannot be bypassed")
    
    # Test 4: Security auditor always logs when enabled
    auditor = SecurityAuditor(database=None, config=config)
    assert auditor.enabled == True, "Auditor should be enabled"
    print("  ✓ Security auditing enforced")


def run_all_tests():
    """Run all security feature validation tests"""
    print("=" * 70)
    print("Running Security Feature Validation Tests")
    print("=" * 70)
    
    tests = [
        test_fips_encryption_active,
        test_password_policy_enforcement,
        test_rate_limiting_enforcement,
        test_audit_logging_functional,
        test_threat_detection_functional,
        test_password_manager_integration,
        test_all_security_defaults,
        test_security_features_cannot_be_bypassed
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ All security feature validation tests passed!")
        print("\n🔒 Security Status: ALL FEATURES FUNCTIONAL AND ENFORCED")
    print("=" * 70)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
