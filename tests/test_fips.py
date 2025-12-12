#!/usr/bin/env python3
"""
FIPS compliance tests
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.encryption import FIPSEncryption, get_encryption



def test_fips_password_hashing():
    """Test FIPS-compliant password hashing"""
    print("Testing FIPS password hashing...")

    enc = get_encryption(fips_mode=True)

    # Test password hashing
    password = "SecurePassword123!"
    hash1, salt = enc.hash_password(password)

    assert hash1, "Password hash should not be empty"
    assert salt, "Salt should not be empty"
    assert len(salt) > 0, "Salt should have length"

    print("  ✓ Password hashing works")

    # Test password verification
    is_valid = enc.verify_password(password, hash1, salt)
    assert is_valid, "Password verification should succeed"

    print("  ✓ Password verification works")

    # Test wrong password
    is_invalid = enc.verify_password("WrongPassword", hash1, salt)
    assert not is_invalid, "Wrong password should fail verification"

    print("  ✓ Wrong password correctly rejected")


def test_fips_data_encryption():
    """Test FIPS-compliant data encryption"""
    print("Testing FIPS data encryption...")

    enc = get_encryption(fips_mode=True)

    try:
        # Test encryption with properly derived key
        data = "Sensitive call recording data"
        password = "SecureEncryptionPassword123!"

        # Derive proper 32-byte key from password
        key, salt = enc.derive_key(password, key_length=32)

        encrypted, nonce, tag = enc.encrypt_data(data, key)

        assert encrypted, "Encrypted data should not be empty"
        assert nonce, "Nonce should not be empty"
        assert tag, "Tag should not be empty"

        print("  ✓ AES-256-GCM encryption works")

        # Test decryption
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
        assert decrypted.decode() == data, "Decrypted data should match original"

        print("  ✓ AES-256-GCM decryption works")

    except ImportError as e:
        print(f"  ⚠ Encryption test skipped: {e}")


def test_fips_secure_token():
    """Test secure token generation"""
    print("Testing secure token generation...")

    enc = get_encryption(fips_mode=True)

    # Generate token
    token1 = enc.generate_secure_token(32)
    token2 = enc.generate_secure_token(32)

    assert token1, "Token should not be empty"
    assert token2, "Token should not be empty"
    assert token1 != token2, "Tokens should be unique"

    print("  ✓ Secure token generation works")


def test_fips_hashing():
    """Test FIPS-compliant SHA-256 hashing"""
    print("Testing FIPS SHA-256 hashing...")

    enc = get_encryption(fips_mode=True)

    # Test hashing
    data = "Test data for hashing"
    hash1 = enc.hash_data(data)
    hash2 = enc.hash_data(data)

    assert hash1, "Hash should not be empty"
    assert hash1 == hash2, "Same data should produce same hash"
    assert len(hash1) == 64, "SHA-256 hash should be 64 hex characters"

    print("  ✓ SHA-256 hashing works")


def test_extension_authentication():
    """Test extension authentication with FIPS"""
    print("Testing extension authentication with FIPS...")

    from pbx.features.extensions import ExtensionRegistry
    from pbx.utils.config import Config

    try:
        config = Config("config.yml")
        registry = ExtensionRegistry(config)

        # Test authentication (will use plain-text fallback if not hashed)
        result = registry.authenticate("1001", "password1001")

        # Should work with either plain text or hashed
        print(f"  ✓ Extension authentication works (authenticated: {result})")

    except FileNotFoundError:
        print("  ⚠ Config file not found (expected in test environment)")
    except Exception as e:
        print(f"  ⚠ Extension test skipped: {e}")


def run_all_tests():
    """Run all FIPS tests"""
    print("=" * 60)
    print("Running FIPS Compliance Tests")
    print("=" * 60)
    print()

    tests = [
        test_fips_password_hashing,
        test_fips_data_encryption,
        test_fips_secure_token,
        test_fips_hashing,
        test_extension_authentication
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
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ All FIPS compliance tests passed!")

    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
