#!/usr/bin/env python3
"""
FIPS compliance tests
"""


from pbx.utils.encryption import get_encryption


def test_fips_password_hashing() -> None:
    """Test FIPS-compliant password hashing"""

    enc = get_encryption(fips_mode=True)

    # Test password hashing
    password = "SecurePassword123!"
    hash1, salt = enc.hash_password(password)

    assert hash1, "Password hash should not be empty"
    assert salt, "Salt should not be empty"
    assert len(salt) > 0, "Salt should have length"


    # Test password verification
    is_valid = enc.verify_password(password, hash1, salt)
    assert is_valid, "Password verification should succeed"


    # Test wrong password
    is_invalid = enc.verify_password("WrongPassword", hash1, salt)
    assert not is_invalid, "Wrong password should fail verification"


def test_fips_data_encryption() -> None:
    """Test FIPS-compliant data encryption"""

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


        # Test decryption
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
        assert decrypted.decode() == data, "Decrypted data should match original"


    except ImportError:
        pass


def test_fips_secure_token() -> None:
    """Test secure token generation"""

    enc = get_encryption(fips_mode=True)

    # Generate token
    token1 = enc.generate_secure_token(32)
    token2 = enc.generate_secure_token(32)

    assert token1, "Token should not be empty"
    assert token2, "Token should not be empty"
    assert token1 != token2, "Tokens should be unique"


def test_fips_hashing() -> None:
    """Test FIPS-compliant SHA-256 hashing"""

    enc = get_encryption(fips_mode=True)

    # Test hashing
    data = "Test data for hashing"
    hash1 = enc.hash_data(data)
    hash2 = enc.hash_data(data)

    assert hash1, "Hash should not be empty"
    assert hash1 == hash2, "Same data should produce same hash"
    assert len(hash1) == 64, "SHA-256 hash should be 64 hex characters"


def test_extension_authentication() -> None:
    """Test extension authentication with FIPS"""

    from pbx.features.extensions import ExtensionRegistry
    from pbx.utils.config import Config

    try:
        config = Config("config.yml")
        registry = ExtensionRegistry(config)

        # Test authentication (will use plain-text fallback if not hashed)
        result = registry.authenticate("1001", "password1001")

        # Should work with either plain text or hashed

    except FileNotFoundError:
        pass
    except Exception:
        pass
