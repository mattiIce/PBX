#!/usr/bin/env python3
"""
Tests for security features
"""
import os
import sys
import tempfile
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.database import DatabaseBackend
from pbx.utils.security import (
    PasswordPolicy,
    RateLimiter,
    SecurityAuditor,
    get_password_manager,
)


def test_password_policy():
    """Test password policy validation"""
    print("Testing password policy...")

    policy = PasswordPolicy()

    # Test valid password
    valid, error = policy.validate("SecurePass123!")
    assert valid, f"Valid password rejected: {error}"

    # Test too short
    valid, error = policy.validate("Short1!")
    assert not valid, "Too short password accepted"
    assert "at least" in error.lower()

    # Test no uppercase
    valid, error = policy.validate("lowercase123!")
    assert not valid, "Password without uppercase accepted"
    assert "uppercase" in error.lower()

    # Test no lowercase
    valid, error = policy.validate("UPPERCASE123!")
    assert not valid, "Password without lowercase accepted"
    assert "lowercase" in error.lower()

    # Test no digit
    valid, error = policy.validate("SecurePass!")
    assert not valid, "Password without digit accepted"
    assert "digit" in error.lower()

    # Test no special character
    valid, error = policy.validate("SecurePass123")
    assert not valid, "Password without special char accepted"
    assert "special" in error.lower()

    # Test common password
    valid, error = policy.validate("Password123!")
    assert not valid, "Common password accepted"
    assert "common" in error.lower()

    # Test sequential characters (4+ in sequence)
    valid, error = policy.validate("Abcde1234!")
    assert not valid, "Password with sequential chars accepted"
    assert "sequential" in error.lower()

    # Test repeated characters (4+ repeated)
    valid, error = policy.validate("Aaaaa123!")
    assert not valid, "Password with repeated chars accepted"
    assert "repeated" in error.lower()

    print("✓ Password policy validation works")


def test_password_generation():
    """Test password generation"""
    print("Testing password generation...")

    policy = PasswordPolicy()

    # Generate passwords and validate them
    for _ in range(10):
        password = policy.generate_strong_password()
        valid, error = policy.validate(password)
        assert valid, f"Generated password failed validation: {error}"
        assert len(password) >= 16, "Generated password too short"

    # Test custom length
    password = policy.generate_strong_password(20)
    assert len(password) == 20, "Custom length not respected"

    print("✓ Password generation works")


def test_rate_limiter():
    """Test rate limiting"""
    print("Testing rate limiter...")

    config = {
        "security.rate_limit.max_attempts": 3,
        "security.rate_limit.window_seconds": 10,
        "security.rate_limit.lockout_duration": 5,
    }

    limiter = RateLimiter(config)

    # Test normal operation
    is_limited, remaining = limiter.is_rate_limited("test_user")
    assert not is_limited, "User incorrectly rate limited"

    # Record failed attempts
    for i in range(3):
        limiter.record_attempt("test_user", successful=False)

    # Should now be rate limited
    is_limited, remaining = limiter.is_rate_limited("test_user")
    assert is_limited, "User not rate limited after max attempts"
    assert remaining is not None and remaining > 0, "No lockout duration returned"

    # Test successful login clears attempts
    limiter2 = RateLimiter(config)
    limiter2.record_attempt("test_user2", successful=False)
    limiter2.record_attempt("test_user2", successful=True)
    is_limited, _ = limiter2.is_rate_limited("test_user2")
    assert not is_limited, "Successful login didn't clear attempts"

    # Test lockout expiry
    limiter3 = RateLimiter(config)
    for i in range(3):
        limiter3.record_attempt("test_user3", successful=False)

    is_limited, remaining = limiter3.is_rate_limited("test_user3")
    assert is_limited, "User not locked out"

    # Wait for lockout to expire
    time.sleep(6)  # Wait longer than lockout_duration
    is_limited, _ = limiter3.is_rate_limited("test_user3")
    assert not is_limited, "Lockout didn't expire"

    print("✓ Rate limiter works")


def test_security_auditor():
    """Test security audit logging"""
    print("Testing security auditor...")

    config = {"security.audit.enabled": True}
    auditor = SecurityAuditor(database=None, config=config)

    # Test logging (to logger only, no database)
    auditor.log_event(
        SecurityAuditor.EVENT_LOGIN_SUCCESS,
        "test_user",
        {"method": "password"},
        success=True,
        ip_address="192.168.1.100",
    )

    auditor.log_event(
        SecurityAuditor.EVENT_LOGIN_FAILURE,
        "test_user",
        {"reason": "invalid_password"},
        success=False,
        ip_address="192.168.1.100",
    )

    # Test with database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_config = {"database.type": "sqlite", "database.path": os.path.join(tmpdir, "test.db")}

        db = DatabaseBackend(db_config)
        assert db.connect(), "Failed to connect to test database"
        assert db.create_tables(), "Failed to create tables"

        auditor_db = SecurityAuditor(database=db, config=config)
        auditor_db.log_event(
            SecurityAuditor.EVENT_PASSWORD_CHANGE,
            "test_user",
            {"changed_by": "admin"},
            success=True,
        )

        # Verify log was stored
        query = "SELECT COUNT(*) as count FROM security_audit WHERE identifier = ?"
        result = db.fetch_one(query, ("test_user",))
        assert result and result["count"] == 1, "Audit log not stored in database"

        db.disconnect()

    print("✓ Security auditor works")


def test_password_manager():
    """Test secure password manager"""
    print("Testing password manager...")

    config = {"security.fips_mode": False}
    mgr = get_password_manager(config)

    # Test password hashing
    password = "SecureTest123!"
    hashed, salt = mgr.hash_password(password)

    assert hashed, "Password hash empty"
    assert salt, "Salt empty"
    assert isinstance(hashed, str), "Hash not string"
    assert isinstance(salt, str), "Salt not string"

    # Test password verification
    assert mgr.verify_password(password, hashed, salt), "Password verification failed"
    assert not mgr.verify_password("WrongPass123!", hashed, salt), "Wrong password verified"

    # Test password validation
    valid, error = mgr.validate_new_password("SecurePass123!")
    assert valid, f"Valid password rejected: {error}"

    valid, error = mgr.validate_new_password("weak")
    assert not valid, "Weak password accepted"

    # Test password generation
    generated = mgr.generate_password()
    assert len(generated) >= 16, "Generated password too short"
    valid, error = mgr.validate_new_password(generated)
    assert valid, f"Generated password invalid: {error}"

    print("✓ Password manager works")


def test_password_migration_compatibility():
    """Test that hashed passwords work with existing systems"""
    print("Testing password migration compatibility...")

    config = {"security.fips_mode": False}
    mgr = get_password_manager(config)

    # Simulate migration
    plaintext_passwords = {
        "1001": "password1001",
        "1002": "TestPass123!",
        "1003": "AnotherSecure456#",
    }

    migrated_data = {}
    for ext_num, password in plaintext_passwords.items():
        hashed, salt = mgr.hash_password(password)
        migrated_data[ext_num] = {"hash": hashed, "salt": salt}

    # Verify all passwords can be authenticated
    for ext_num, password in plaintext_passwords.items():
        data = migrated_data[ext_num]
        assert mgr.verify_password(
            password, data["hash"], data["salt"]
        ), f"Migrated password for {ext_num} failed verification"

    # Verify wrong passwords don't authenticate
    for ext_num in plaintext_passwords.keys():
        data = migrated_data[ext_num]
        assert not mgr.verify_password(
            "wrong_password", data["hash"], data["salt"]
        ), f"Wrong password verified for {ext_num}"

    print("✓ Password migration compatibility verified")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running Security Tests")
    print("=" * 60)
    print()

    tests = [
        test_password_policy,
        test_password_generation,
        test_rate_limiter,
        test_security_auditor,
        test_password_manager,
        test_password_migration_compatibility,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test.__name__}")
            print(f"  Error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
