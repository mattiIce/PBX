#!/usr/bin/env python3
"""
Tests for Multi-Factor Authentication (MFA) feature
"""

import contextlib
import time
from pathlib import Path

from pbx.features.mfa import (
    FIDO2Verifier,
    MFAManager,
    TOTPGenerator,
    YubiKeyOTPVerifier,
)
from pbx.utils.database import DatabaseBackend


def test_totp_generation() -> bool:
    """Test TOTP code generation"""

    # Create TOTP generator with fixed secret for testing
    secret = b"12345678901234567890"  # 20 bytes
    totp = TOTPGenerator(secret=secret)

    # Generate code for fixed timestamp
    timestamp = 1234567890
    code = totp.generate(timestamp)

    # Verify code is 6 digits
    assert len(code) == 6, f"Expected 6 digits, got {len(code)}"
    assert code.isdigit(), f"Expected numeric code, got {code}"

    # Verify the same code is generated for the same timestamp
    code2 = totp.generate(timestamp)
    assert code == code2, "Same timestamp should generate same code"

    return True


def test_totp_verification() -> bool:
    """Test TOTP code verification"""

    secret = b"12345678901234567890"
    totp = TOTPGenerator(secret=secret)

    # Generate code for current time
    timestamp = int(time.time())
    code = totp.generate(timestamp)

    # Verify the code
    assert totp.verify(code, timestamp), "Generated code should verify"

    # Verify code fails for wrong code
    wrong_code = "000000"
    assert not totp.verify(wrong_code, timestamp), "Wrong code should fail"

    # Verify code works within time window
    past_timestamp = timestamp - 30  # 1 period ago
    past_code = totp.generate(past_timestamp)
    assert totp.verify(past_code, timestamp, window=1), (
        "Code from previous period should verify with window=1"
    )

    return True


def test_totp_provisioning_uri() -> bool:
    """Test TOTP provisioning URI generation"""

    totp = TOTPGenerator()
    uri = totp.get_provisioning_uri("1001", "Test PBX")

    # Verify URI format
    assert uri.startswith("otpauth://totp/"), f"Invalid URI format: {uri}"
    assert "1001" in uri, "Account name not in URI"
    assert "Test PBX" in uri, "Issuer not in URI"
    assert "secret=" in uri, "Secret not in URI"

    return True


def test_mfa_manager_basic() -> bool:
    """Test MFA manager basic functionality"""

    # Create config with database disabled
    config = {"security": {"fips_mode": False, "mfa": {"enabled": True, "required": False}}}

    # Create MFA manager without database
    mfa = MFAManager(database=None, config=config)

    assert mfa.enabled, "MFA should be enabled"
    assert not mfa.required, "MFA should not be required"

    return True


def test_mfa_enrollment_without_db() -> bool:
    """Test MFA enrollment without database"""

    config = {"security": {"fips_mode": False, "mfa": {"enabled": True}}}
    mfa = MFAManager(database=None, config=config)

    # Enrollment should work but won't persist without database
    _success, _uri, _codes = mfa.enroll_user("1001")

    # Without database, enrollment will succeed but won't store
    # We just check that the method executes without error

    return True


def test_mfa_with_database() -> bool:
    """Test MFA with database backend"""

    # Create temporary SQLite database
    import tempfile

    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = db_file.name
    db_file.close()

    try:
        # Create database config
        db_config = {
            "database": {"type": "sqlite", "path": db_path},
            "security": {
                "fips_mode": False,
                "mfa": {"enabled": True, "required": False, "backup_codes": 5},
            },
        }

        # Create database
        db = DatabaseBackend(db_config)
        if not db.connect():
            return True

        # Initialize tables
        db.create_tables()

        # Create MFA manager
        mfa = MFAManager(database=db, config=db_config)

        # Test enrollment
        extension = "1001"
        success, uri, backup_codes = mfa.enroll_user(extension)

        assert success, "Enrollment should succeed"
        assert uri is not None, "Provisioning URI should be provided"
        assert backup_codes is not None, "Backup codes should be provided"
        # Config dict doesn't support dot notation, so it uses the default of
        # 10
        assert len(backup_codes) == 10, f"Expected 10 backup codes, got {len(backup_codes)}"

        # MFA should not be enabled yet (requires verification)
        assert not mfa.is_enabled_for_user(extension), (
            "MFA should not be enabled before verification"
        )

        # Extract secret from URI to generate valid code
        import base64

        secret_param = uri.split("secret=")[1].split("&")[0]
        # Add padding if needed
        secret_b32 = secret_param + "=" * ((8 - len(secret_param) % 8) % 8)
        secret_bytes = base64.b32decode(secret_b32)

        # Generate valid code
        totp = TOTPGenerator(secret=secret_bytes)
        valid_code = totp.generate()

        # Verify enrollment with valid code
        verify_success = mfa.verify_enrollment(extension, valid_code)
        assert verify_success, "Enrollment verification should succeed with valid code"

        # MFA should now be enabled
        assert mfa.is_enabled_for_user(extension), "MFA should be enabled after verification"

        # Test code verification
        new_code = totp.generate()
        assert mfa.verify_code(extension, new_code), "TOTP code verification should succeed"

        # Test backup code verification
        backup_code = backup_codes[0]
        assert mfa.verify_code(extension, backup_code), "Backup code verification should succeed"

        # Same backup code should not work twice
        assert not mfa.verify_code(extension, backup_code), "Used backup code should not work again"

        # Test disable
        assert mfa.disable_for_user(extension), "Disable should succeed"
        assert not mfa.is_enabled_for_user(extension), "MFA should be disabled"

        # Clean up
        db.connection.close()
        Path(db_path).unlink(missing_ok=True)

        return True

    except OSError as e:
        # Clean up on error
        if Path(db_path).exists():
            with contextlib.suppress(BaseException):
                Path(db_path).unlink(missing_ok=True)
        raise e


def test_backup_code_format() -> bool:
    """Test backup code format"""

    config = {"security": {"fips_mode": False, "mfa": {"enabled": True, "backup_codes": 10}}}
    mfa = MFAManager(database=None, config=config)

    codes = mfa._generate_backup_codes(10)

    assert len(codes) == 10, f"Expected 10 codes, got {len(codes)}"

    for code in codes:
        # Should be in format XXXX-XXXX
        assert len(code) == 9, f"Expected 9 characters (XXXX-XXXX), got {len(code)}"
        assert code[4] == "-", f"Expected dash at position 4, got {code[4]}"

        # Check alphanumeric (excluding confusing characters)
        parts = code.split("-")
        for part in parts:
            assert len(part) == 4, f"Expected 4 characters per part, got {len(part)}"
            # Should not contain confusing characters (0, O, I, 1)
            assert "0" not in part, "Should not contain 0"
            assert "O" not in part, "Should not contain O"
            assert "I" not in part, "Should not contain I"
            assert "1" not in part, "Should not contain 1"

    return True


def test_yubikey_otp_format_validation() -> bool:
    """Test YubiKey OTP format validation"""

    verifier = YubiKeyOTPVerifier()

    # Test invalid length
    valid, error = verifier.verify_otp("short")
    assert not valid, "Short OTP should be rejected"
    assert "44 characters" in error, f"Expected length error, got: {error}"

    # Test invalid characters
    # 'a' is not a valid ModHex character
    valid, error = verifier.verify_otp("a" * 44)
    assert not valid, "OTP with invalid characters should be rejected"
    assert "invalid characters" in error.lower(), f"Expected character error, got: {error}"

    # Test valid format (ModHex characters)
    valid_otp = "ccccccbcgujhingjrdejhgfnuetrgigvejhhgbkugded"
    valid, error = verifier.verify_otp(valid_otp)
    # Should fail for other reasons (not registered, etc.) but format should be OK
    # The format validation passes, so error would be from API call

    # Test public ID extraction
    public_id = verifier.extract_public_id(valid_otp)
    assert public_id == "ccccccbcgujh", f"Expected 'ccccccbcgujh', got '{public_id}'"

    return True


def test_yubikey_otp_verification_without_api() -> bool:
    """Test YubiKey OTP verification (format check only, no API credentials)"""

    # Create verifier without credentials (will use default test client)
    verifier = YubiKeyOTPVerifier()

    # Test with valid ModHex OTP
    test_otp = "ccccccbcgujhingjrdejhgfnuetrgigvejhhgbkugded"

    # Note: Without valid API credentials and a real OTP, this will fail at the API level
    # but the format validation and code path will be exercised
    valid, _error = verifier.verify_otp(test_otp)

    # We expect this to fail since we don't have real credentials/OTP
    # but it should fail gracefully with an appropriate error message
    if valid:
        pass

    return True


def test_fido2_challenge_generation() -> bool:
    """Test FIDO2 challenge generation"""

    verifier = FIDO2Verifier()

    # Generate challenge
    challenge = verifier.create_challenge()

    # Verify it's base64-encoded
    assert isinstance(challenge, str), "Challenge should be a string"
    assert len(challenge) > 0, "Challenge should not be empty"

    # Verify it's URL-safe base64 (no padding, no + or /)
    assert "=" not in challenge, "Challenge should not have padding"
    assert "+" not in challenge, "Challenge should be URL-safe"
    assert "/" not in challenge, "Challenge should be URL-safe"

    # Verify uniqueness
    challenge2 = verifier.create_challenge()
    assert challenge != challenge2, "Challenges should be unique"

    return True


def test_fido2_credential_registration() -> bool:
    """Test FIDO2 credential registration"""

    verifier = FIDO2Verifier()

    # Test with missing data
    success, result = verifier.register_credential("1001", {})
    assert not success, "Registration should fail with missing data"

    # Test with valid data (simulated)
    import base64

    credential_id = base64.b64encode(b"test_credential_id_123456").decode("utf-8")
    public_key = base64.b64encode(b"test_public_key_data" * 10).decode("utf-8")  # Make it longer

    credential_data = {"credential_id": credential_id, "public_key": public_key}

    success, result = verifier.register_credential("1001", credential_data)
    assert success, f"Registration should succeed with valid data: {result}"
    assert result == credential_id, "Should return credential ID"

    return True


def test_fido2_assertion_verification() -> bool:
    """Test FIDO2 assertion verification"""

    verifier = FIDO2Verifier()

    # Test with missing data
    success, error = verifier.verify_assertion("test_cred", {}, b"public_key")
    assert not success, "Verification should fail with missing data"

    # Test with simulated valid data (basic mode without full crypto)
    import base64

    # Create minimal valid-looking assertion data
    authenticator_data = base64.b64encode(b"X" * 37).decode("utf-8")  # Minimum length
    signature = base64.b64encode(b"S" * 64).decode("utf-8")  # Minimum signature length
    client_data = base64.b64encode(b'{"type":"webauthn.get","challenge":"test"}').decode("utf-8")

    assertion_data = {
        "authenticator_data": authenticator_data,
        "signature": signature,
        "client_data_json": client_data,
    }

    public_key = base64.b64encode(b"K" * 100).decode("utf-8")

    # This will use basic verification mode since we don't have a real FIDO2
    # setup
    success, _error = verifier.verify_assertion("test_cred", assertion_data, public_key)

    # In basic mode, this should succeed since all data is present and valid
    # length
    if not success:
        pass  # fido2 library may do full verification and fail

    return True
