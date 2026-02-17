"""Comprehensive tests for pbx.utils.encryption module."""

import base64
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestFIPSEncryptionInit:
    """Tests for FIPSEncryption initialization."""

    @patch("pbx.utils.encryption.get_logger")
    def test_init_fips_disabled(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with FIPS mode disabled."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        assert enc.fips_mode is False

    @patch("pbx.utils.encryption.get_logger")
    def test_init_fips_enabled_with_crypto(self, mock_get_logger: MagicMock) -> None:
        """Test initialization with FIPS mode enabled and crypto available."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        assert enc.fips_mode is True

    @patch("pbx.utils.encryption.CRYPTO_AVAILABLE", False)
    @patch("pbx.utils.encryption.get_logger")
    def test_init_fips_enabled_no_crypto_no_enforce(self, mock_get_logger: MagicMock) -> None:
        """Test FIPS mode enabled without crypto library (no enforce)."""
        from pbx.utils.encryption import FIPSEncryption

        # Should not raise, just warn
        enc = FIPSEncryption(fips_mode=True, enforce_fips=False)
        assert enc.fips_mode is True

    @patch("pbx.utils.encryption.CRYPTO_AVAILABLE", False)
    @patch("pbx.utils.encryption.get_logger")
    def test_init_fips_enabled_no_crypto_enforce(self, mock_get_logger: MagicMock) -> None:
        """Test FIPS mode enabled without crypto library (enforce)."""
        from pbx.utils.encryption import FIPSEncryption

        with pytest.raises(ImportError, match="FIPS mode enforcement failed"):
            FIPSEncryption(fips_mode=True, enforce_fips=True)


@pytest.mark.unit
class TestPadPassword:
    """Tests for _pad_password method."""

    @patch("pbx.utils.encryption.get_logger")
    def test_pad_short_password(self, mock_get_logger: MagicMock) -> None:
        """Test padding a short password."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        salt = b"a" * 32
        short_pass = b"short"
        padded = enc._pad_password(short_pass, salt)
        assert len(padded) >= enc.MIN_PASSWORD_LENGTH

    @patch("pbx.utils.encryption.get_logger")
    def test_pad_long_password_unchanged(self, mock_get_logger: MagicMock) -> None:
        """Test that a sufficiently long password is not padded."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        salt = b"a" * 32
        long_pass = b"this_is_a_long_enough_password"
        padded = enc._pad_password(long_pass, salt)
        assert padded == long_pass

    @patch("pbx.utils.encryption.get_logger")
    def test_pad_exact_min_length(self, mock_get_logger: MagicMock) -> None:
        """Test password at exact minimum length."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        salt = b"a" * 32
        exact_pass = b"a" * enc.MIN_PASSWORD_LENGTH
        padded = enc._pad_password(exact_pass, salt)
        assert padded == exact_pass


@pytest.mark.unit
class TestHashPassword:
    """Tests for hash_password method."""

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_password_non_fips(self, mock_get_logger: MagicMock) -> None:
        """Test password hashing in non-FIPS mode."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        hashed, salt = enc.hash_password("test_password")
        assert isinstance(hashed, str)
        assert isinstance(salt, str)
        # Verify base64 encoding
        base64.b64decode(hashed)
        base64.b64decode(salt)

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_password_fips(self, mock_get_logger: MagicMock) -> None:
        """Test password hashing in FIPS mode."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        hashed, salt = enc.hash_password("test_password_fips_long_enough")
        assert isinstance(hashed, str)
        assert isinstance(salt, str)

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_password_with_provided_salt(self, mock_get_logger: MagicMock) -> None:
        """Test password hashing with provided salt."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        salt = b"fixed_salt_for_testing_purposes!"
        hashed1, _ = enc.hash_password("password", salt)
        hashed2, _ = enc.hash_password("password", salt)
        assert hashed1 == hashed2

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_password_with_string_salt(self, mock_get_logger: MagicMock) -> None:
        """Test password hashing with string salt."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        hashed, _salt = enc.hash_password("password", "string_salt_value!!")
        assert isinstance(hashed, str)

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_password_with_bytes_input(self, mock_get_logger: MagicMock) -> None:
        """Test password hashing with bytes password."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        hashed, _salt = enc.hash_password(b"bytes_password")
        assert isinstance(hashed, str)

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_password_different_passwords_different_hashes(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test that different passwords produce different hashes."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        salt = b"shared_salt_value_for_test!!!!"
        hash1, _ = enc.hash_password("password1", salt)
        hash2, _ = enc.hash_password("password2", salt)
        assert hash1 != hash2


@pytest.mark.unit
class TestVerifyPassword:
    """Tests for verify_password method."""

    @patch("pbx.utils.encryption.get_logger")
    def test_verify_password_correct(self, mock_get_logger: MagicMock) -> None:
        """Test password verification with correct password."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        hashed, salt = enc.hash_password("my_secure_password")
        assert enc.verify_password("my_secure_password", hashed, salt) is True

    @patch("pbx.utils.encryption.get_logger")
    def test_verify_password_incorrect(self, mock_get_logger: MagicMock) -> None:
        """Test password verification with incorrect password."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        hashed, salt = enc.hash_password("my_secure_password")
        assert enc.verify_password("wrong_password", hashed, salt) is False

    @patch("pbx.utils.encryption.get_logger")
    def test_verify_password_fips_mode(self, mock_get_logger: MagicMock) -> None:
        """Test password verification in FIPS mode."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        hashed, salt = enc.hash_password("secure_password_long_enough")
        assert enc.verify_password("secure_password_long_enough", hashed, salt) is True
        assert enc.verify_password("wrong_password_here!", hashed, salt) is False

    @patch("pbx.utils.encryption.get_logger")
    def test_verify_password_with_bytes_hash(self, mock_get_logger: MagicMock) -> None:
        """Test password verification with bytes hash and salt."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        hashed_str, salt_str = enc.hash_password("test_password")

        # Provide as bytes (already base64-encoded)
        hashed_bytes = base64.b64decode(hashed_str)
        salt_bytes = base64.b64decode(salt_str)

        assert enc.verify_password("test_password", hashed_bytes, salt_bytes) is True


@pytest.mark.unit
class TestEncryptData:
    """Tests for encrypt_data method."""

    @patch("pbx.utils.encryption.get_logger")
    def test_encrypt_data_string(self, mock_get_logger: MagicMock) -> None:
        """Test encrypting string data."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        key = b"0123456789abcdef0123456789abcdef"  # 32 bytes
        encrypted, nonce, tag = enc.encrypt_data("Hello, World!", key)
        assert isinstance(encrypted, str)
        assert isinstance(nonce, str)
        assert isinstance(tag, str)
        # Verify base64 encoding
        base64.b64decode(encrypted)
        base64.b64decode(nonce)
        base64.b64decode(tag)

    @patch("pbx.utils.encryption.get_logger")
    def test_encrypt_data_bytes(self, mock_get_logger: MagicMock) -> None:
        """Test encrypting bytes data."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        key = b"0123456789abcdef0123456789abcdef"
        encrypted, _nonce, _tag = enc.encrypt_data(b"bytes data", key)
        assert isinstance(encrypted, str)

    @patch("pbx.utils.encryption.get_logger")
    def test_encrypt_data_string_key(self, mock_get_logger: MagicMock) -> None:
        """Test encrypting with string key."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        key = "0123456789abcdef0123456789abcdef"  # 32 chars
        encrypted, _nonce, _tag = enc.encrypt_data("Hello", key)
        assert isinstance(encrypted, str)

    @patch("pbx.utils.encryption.get_logger")
    def test_encrypt_data_invalid_key_length(self, mock_get_logger: MagicMock) -> None:
        """Test encrypting with invalid key length raises ValueError."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        with pytest.raises(ValueError, match="must be exactly 32 bytes"):
            enc.encrypt_data("Hello", b"short_key")

    @patch("pbx.utils.encryption.CRYPTO_AVAILABLE", False)
    @patch("pbx.utils.encryption.get_logger")
    def test_encrypt_data_no_crypto(self, mock_get_logger: MagicMock) -> None:
        """Test encrypting without crypto library raises ImportError."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        with pytest.raises(ImportError, match="cryptography library"):
            enc.encrypt_data("Hello", b"0123456789abcdef0123456789abcdef")


@pytest.mark.unit
class TestDecryptData:
    """Tests for decrypt_data method."""

    @patch("pbx.utils.encryption.get_logger")
    def test_decrypt_data_roundtrip(self, mock_get_logger: MagicMock) -> None:
        """Test encrypting then decrypting data."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        key = b"0123456789abcdef0123456789abcdef"
        original = "Secret message here!"

        encrypted, nonce, tag = enc.encrypt_data(original, key)
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
        assert decrypted == original.encode("utf-8")

    @patch("pbx.utils.encryption.get_logger")
    def test_decrypt_data_with_string_key(self, mock_get_logger: MagicMock) -> None:
        """Test decrypting with string key."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        key_bytes = b"0123456789abcdef0123456789abcdef"
        key_str = "0123456789abcdef0123456789abcdef"

        encrypted, nonce, tag = enc.encrypt_data("Hello", key_bytes)
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key_str)
        assert decrypted == b"Hello"

    @patch("pbx.utils.encryption.get_logger")
    def test_decrypt_data_invalid_key_length(self, mock_get_logger: MagicMock) -> None:
        """Test decrypting with invalid key length raises ValueError."""
        import base64

        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        # Provide valid base64-encoded strings so decoding works, but a short key
        fake_data = base64.b64encode(b"ciphertext").decode()
        fake_nonce = base64.b64encode(b"nonce123456!").decode()
        fake_tag = base64.b64encode(b"tag_value_16byte").decode()
        with pytest.raises(ValueError, match="must be exactly 32 bytes"):
            enc.decrypt_data(fake_data, fake_nonce, fake_tag, b"short_key_not_32")

    @patch("pbx.utils.encryption.CRYPTO_AVAILABLE", False)
    @patch("pbx.utils.encryption.get_logger")
    def test_decrypt_data_no_crypto(self, mock_get_logger: MagicMock) -> None:
        """Test decrypting without crypto library raises ImportError."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        with pytest.raises(ImportError, match="cryptography library"):
            enc.decrypt_data("data", "nonce", "tag", b"0123456789abcdef0123456789abcdef")

    @patch("pbx.utils.encryption.get_logger")
    def test_decrypt_bytes_data(self, mock_get_logger: MagicMock) -> None:
        """Test encrypting and decrypting bytes data."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        key = b"0123456789abcdef0123456789abcdef"
        original = b"\x00\x01\x02\x03\xff\xfe\xfd"

        encrypted, nonce, tag = enc.encrypt_data(original, key)
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
        assert decrypted == original


@pytest.mark.unit
class TestGenerateSecureToken:
    """Tests for generate_secure_token method."""

    @patch("pbx.utils.encryption.get_logger")
    def test_generate_token_default_length(self, mock_get_logger: MagicMock) -> None:
        """Test generating token with default length."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        token = enc.generate_secure_token()
        assert isinstance(token, str)
        # 32 bytes -> 44 base64 chars (with padding)
        decoded = base64.b64decode(token)
        assert len(decoded) == 32

    @patch("pbx.utils.encryption.get_logger")
    def test_generate_token_custom_length(self, mock_get_logger: MagicMock) -> None:
        """Test generating token with custom length."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        token = enc.generate_secure_token(length=16)
        decoded = base64.b64decode(token)
        assert len(decoded) == 16

    @patch("pbx.utils.encryption.get_logger")
    def test_generate_tokens_unique(self, mock_get_logger: MagicMock) -> None:
        """Test that generated tokens are unique."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        tokens = {enc.generate_secure_token() for _ in range(100)}
        assert len(tokens) == 100


@pytest.mark.unit
class TestDeriveKey:
    """Tests for derive_key method."""

    @patch("pbx.utils.encryption.get_logger")
    def test_derive_key_non_fips(self, mock_get_logger: MagicMock) -> None:
        """Test key derivation in non-FIPS mode."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        key, salt = enc.derive_key("my_password")
        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)
        assert len(key) == 32
        assert len(salt) == 32

    @patch("pbx.utils.encryption.get_logger")
    def test_derive_key_fips(self, mock_get_logger: MagicMock) -> None:
        """Test key derivation in FIPS mode."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        key, _salt = enc.derive_key("my_password_long_enough")
        assert isinstance(key, bytes)
        assert len(key) == 32

    @patch("pbx.utils.encryption.get_logger")
    def test_derive_key_with_provided_salt(self, mock_get_logger: MagicMock) -> None:
        """Test key derivation with provided salt."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        salt = b"fixed_salt_value_for_this_test!!"
        key1, _ = enc.derive_key("password", salt)
        key2, _ = enc.derive_key("password", salt)
        assert key1 == key2

    @patch("pbx.utils.encryption.get_logger")
    def test_derive_key_with_string_salt(self, mock_get_logger: MagicMock) -> None:
        """Test key derivation with string salt."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        key, salt = enc.derive_key("password", "string_salt")
        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)

    @patch("pbx.utils.encryption.get_logger")
    def test_derive_key_with_bytes_password(self, mock_get_logger: MagicMock) -> None:
        """Test key derivation with bytes password."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        key, _salt = enc.derive_key(b"bytes_password")
        assert isinstance(key, bytes)
        assert len(key) == 32

    @patch("pbx.utils.encryption.get_logger")
    def test_derive_key_custom_length(self, mock_get_logger: MagicMock) -> None:
        """Test key derivation with custom key length."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        key, _salt = enc.derive_key("password", key_length=16)
        assert len(key) == 16

    @patch("pbx.utils.encryption.get_logger")
    def test_derive_key_different_passwords_different_keys(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Test that different passwords produce different keys."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        salt = b"shared_salt_value_for_testing!!!"
        key1, _ = enc.derive_key("password1", salt)
        key2, _ = enc.derive_key("password2", salt)
        assert key1 != key2


@pytest.mark.unit
class TestHashData:
    """Tests for hash_data method."""

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_data_string_non_fips(self, mock_get_logger: MagicMock) -> None:
        """Test hashing string data in non-FIPS mode."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        result = enc.hash_data("test data")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex digest length

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_data_bytes_non_fips(self, mock_get_logger: MagicMock) -> None:
        """Test hashing bytes data in non-FIPS mode."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        result = enc.hash_data(b"test data")
        assert isinstance(result, str)
        assert len(result) == 64

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_data_fips(self, mock_get_logger: MagicMock) -> None:
        """Test hashing data in FIPS mode."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)
        result = enc.hash_data("test data fips")
        assert isinstance(result, str)
        assert len(result) == 64

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_data_consistent(self, mock_get_logger: MagicMock) -> None:
        """Test that hashing is consistent (same input -> same output)."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        hash1 = enc.hash_data("same input")
        hash2 = enc.hash_data("same input")
        assert hash1 == hash2

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_data_different_inputs(self, mock_get_logger: MagicMock) -> None:
        """Test that different inputs produce different hashes."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        hash1 = enc.hash_data("input one")
        hash2 = enc.hash_data("input two")
        assert hash1 != hash2

    @patch("pbx.utils.encryption.get_logger")
    def test_hash_data_fips_vs_non_fips_same_result(self, mock_get_logger: MagicMock) -> None:
        """Test FIPS and non-FIPS produce same SHA-256 hash."""
        from pbx.utils.encryption import FIPSEncryption

        enc_fips = FIPSEncryption(fips_mode=True)
        enc_non_fips = FIPSEncryption(fips_mode=False)
        result_fips = enc_fips.hash_data("test")
        result_non_fips = enc_non_fips.hash_data("test")
        assert result_fips == result_non_fips


@pytest.mark.unit
class TestGetEncryption:
    """Tests for get_encryption module-level function."""

    def test_get_encryption_singleton(self) -> None:
        """Test get_encryption returns same instance."""
        import pbx.utils.encryption as enc_module

        # Reset the global instance
        enc_module._encryption_instance = None

        with patch("pbx.utils.encryption.get_logger"):
            instance1 = enc_module.get_encryption(fips_mode=False)
            instance2 = enc_module.get_encryption(fips_mode=True)
            assert instance1 is instance2

        # Clean up
        enc_module._encryption_instance = None

    def test_get_encryption_creates_instance(self) -> None:
        """Test get_encryption creates new instance when None."""
        import pbx.utils.encryption as enc_module

        enc_module._encryption_instance = None

        with patch("pbx.utils.encryption.get_logger"):
            instance = enc_module.get_encryption(fips_mode=False)
            assert instance is not None

        enc_module._encryption_instance = None


@pytest.mark.unit
class TestEncryptDecryptIntegration:
    """Integration tests for full encrypt-decrypt flow."""

    @patch("pbx.utils.encryption.get_logger")
    def test_full_encrypt_decrypt_flow(self, mock_get_logger: MagicMock) -> None:
        """Test full encryption and decryption flow using derived key."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=True)

        # Derive key from password
        key, _salt = enc.derive_key("my_secure_password_here!")

        # Encrypt data
        original = "Sensitive PBX configuration data"
        encrypted, nonce, tag = enc.encrypt_data(original, key)

        # Decrypt data
        decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
        assert decrypted.decode("utf-8") == original

    @patch("pbx.utils.encryption.get_logger")
    def test_password_hash_verify_flow(self, mock_get_logger: MagicMock) -> None:
        """Test full password hash and verify flow."""
        from pbx.utils.encryption import FIPSEncryption

        enc = FIPSEncryption(fips_mode=False)
        password = "voicemail_pin_1234"

        hashed, salt = enc.hash_password(password)
        assert enc.verify_password(password, hashed, salt) is True
        assert enc.verify_password("wrong_pin", hashed, salt) is False

    @patch("pbx.utils.encryption.get_logger")
    def test_min_password_length_constant(self, mock_get_logger: MagicMock) -> None:
        """Test MIN_PASSWORD_LENGTH is set correctly."""
        from pbx.utils.encryption import FIPSEncryption

        assert FIPSEncryption.MIN_PASSWORD_LENGTH == 14
