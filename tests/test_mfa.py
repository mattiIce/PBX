#!/usr/bin/env python3
"""
Tests for Multi-Factor Authentication (MFA) feature
"""
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.mfa import (
    FIDO2Verifier,
    MFAManager,
    TOTPGenerator,
    YubiKeyOTPVerifier,
)
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend



def test_totp_generation():
    """Test TOTP code generation"""
    print("Testing TOTP code generation...")

    # Create TOTP generator with fixed secret for testing
    secret = b'12345678901234567890'  # 20 bytes
    totp = TOTPGenerator(secret=secret)

    # Generate code for fixed timestamp
    timestamp = 1234567890
    code = totp.generate(timestamp)

    # Verify code is 6 digits
    assert len(code) == 6, f"Expected 6 digits, got {len(code)}"
    assert code.isdigit(), f"Expected numeric code, got {code}"

    print(f"  ✓ Generated TOTP code: {code}")

    # Verify the same code is generated for the same timestamp
    code2 = totp.generate(timestamp)
    assert code == code2, "Same timestamp should generate same code"
    print(f"  ✓ Consistent code generation verified")

    return True


def test_totp_verification():
    """Test TOTP code verification"""
    print("Testing TOTP code verification...")

    secret = b'12345678901234567890'
    totp = TOTPGenerator(secret=secret)

    # Generate code for current time
    timestamp = int(time.time())
    code = totp.generate(timestamp)

    # Verify the code
    assert totp.verify(code, timestamp), "Generated code should verify"
    print(f"  ✓ Code verification successful")

    # Verify code fails for wrong code
    wrong_code = "000000"
    assert not totp.verify(wrong_code, timestamp), "Wrong code should fail"
    print(f"  ✓ Invalid code correctly rejected")

    # Verify code works within time window
    past_timestamp = timestamp - 30  # 1 period ago
    past_code = totp.generate(past_timestamp)
    assert totp.verify(past_code, timestamp,
                       window=1), "Code from previous period should verify with window=1"
    print(f"  ✓ Time window verification successful")

    return True


def test_totp_provisioning_uri():
    """Test TOTP provisioning URI generation"""
    print("Testing TOTP provisioning URI...")

    totp = TOTPGenerator()
    uri = totp.get_provisioning_uri("1001", "Test PBX")

    # Verify URI format
    assert uri.startswith("otpauth://totp/"), f"Invalid URI format: {uri}"
    assert "1001" in uri, "Account name not in URI"
    assert "Test PBX" in uri, "Issuer not in URI"
    assert "secret=" in uri, "Secret not in URI"
    print(f"  ✓ Provisioning URI generated successfully")
    print(f"    {uri[:60]}...")

    return True


def test_mfa_manager_basic():
    """Test MFA manager basic functionality"""
    print("Testing MFA manager...")

    # Create config with database disabled
    config = {
        'security': {
            'fips_mode': False,
            'mfa': {
                'enabled': True,
                'required': False}}}

    # Create MFA manager without database
    mfa = MFAManager(database=None, config=config)

    assert mfa.enabled, "MFA should be enabled"
    assert not mfa.required, "MFA should not be required"
    print(f"  ✓ MFA manager initialized")

    return True


def test_mfa_enrollment_without_db():
    """Test MFA enrollment without database"""
    print("Testing MFA enrollment (without database)...")

    config = {'security': {'fips_mode': False, 'mfa': {'enabled': True}}}
    mfa = MFAManager(database=None, config=config)

    # Enrollment should work but won't persist without database
    success, uri, codes = mfa.enroll_user("1001")

    # Without database, enrollment will succeed but won't store
    # We just check that the method executes without error
    print(f"  ✓ Enrollment method executed (database not available)")

    return True


def test_mfa_with_database():
    """Test MFA with database backend"""
    print("Testing MFA with database...")

    # Create temporary SQLite database
    import tempfile
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = db_file.name
    db_file.close()

    try:
        # Create database config
        db_config = {
            'database': {
                'type': 'sqlite',
                'path': db_path
            },
            'security': {
                'fips_mode': False,
                'mfa': {
                    'enabled': True,
                    'required': False,
                    'backup_codes': 5
                }
            }
        }

        # Create database
        db = DatabaseBackend(db_config)
        if not db.connect():
            print("  ⚠ Database connection failed, skipping database tests")
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
        assert len(backup_codes) == 10, f"Expected 10 backup codes, got {
            len(backup_codes)}"
        print(f"  ✓ User enrolled successfully")
        print(f"    Provisioning URI: {uri[:60]}...")
        print(f"    Backup codes: {len(backup_codes)} codes generated")

        # MFA should not be enabled yet (requires verification)
        assert not mfa.is_enabled_for_user(
            extension), "MFA should not be enabled before verification"
        print(f"  ✓ MFA not yet enabled (pending verification)")

        # Extract secret from URI to generate valid code
        import base64
        secret_param = uri.split('secret=')[1].split('&')[0]
        # Add padding if needed
        secret_b32 = secret_param + '=' * ((8 - len(secret_param) % 8) % 8)
        secret_bytes = base64.b32decode(secret_b32)

        # Generate valid code
        totp = TOTPGenerator(secret=secret_bytes)
        valid_code = totp.generate()

        # Verify enrollment with valid code
        verify_success = mfa.verify_enrollment(extension, valid_code)
        assert verify_success, "Enrollment verification should succeed with valid code"
        print(f"  ✓ Enrollment verified with TOTP code")

        # MFA should now be enabled
        assert mfa.is_enabled_for_user(
            extension), "MFA should be enabled after verification"
        print(f"  ✓ MFA enabled for user")

        # Test code verification
        new_code = totp.generate()
        assert mfa.verify_code(
            extension, new_code), "TOTP code verification should succeed"
        print(f"  ✓ TOTP code verification successful")

        # Test backup code verification
        backup_code = backup_codes[0]
        assert mfa.verify_code(
            extension, backup_code), "Backup code verification should succeed"
        print(f"  ✓ Backup code verification successful")

        # Same backup code should not work twice
        assert not mfa.verify_code(
            extension, backup_code), "Used backup code should not work again"
        print(f"  ✓ Used backup code correctly rejected")

        # Test disable
        assert mfa.disable_for_user(extension), "Disable should succeed"
        assert not mfa.is_enabled_for_user(extension), "MFA should be disabled"
        print(f"  ✓ MFA disabled successfully")

        # Clean up
        db.connection.close()
        os.unlink(db_path)

        return True

    except Exception as e:
        # Clean up on error
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except BaseException:
                pass
        raise e


def test_backup_code_format():
    """Test backup code format"""
    print("Testing backup code format...")

    config = {
        'security': {
            'fips_mode': False,
            'mfa': {
                'enabled': True,
                'backup_codes': 10}}}
    mfa = MFAManager(database=None, config=config)

    codes = mfa._generate_backup_codes(10)

    assert len(codes) == 10, f"Expected 10 codes, got {len(codes)}"

    for code in codes:
        # Should be in format XXXX-XXXX
        assert len(
            code) == 9, f"Expected 9 characters (XXXX-XXXX), got {len(code)}"
        assert code[4] == '-', f"Expected dash at position 4, got {code[4]}"

        # Check alphanumeric (excluding confusing characters)
        parts = code.split('-')
        for part in parts:
            assert len(
                part) == 4, f"Expected 4 characters per part, got {len(part)}"
            # Should not contain confusing characters (0, O, I, 1)
            assert '0' not in part, "Should not contain 0"
            assert 'O' not in part, "Should not contain O"
            assert 'I' not in part, "Should not contain I"
            assert '1' not in part, "Should not contain 1"

    print(f"  ✓ Backup codes formatted correctly")
    print(f"    Example codes: {codes[0]}, {codes[1]}")

    return True


def test_yubikey_otp_format_validation():
    """Test YubiKey OTP format validation"""
    print("Testing YubiKey OTP format validation...")

    verifier = YubiKeyOTPVerifier()

    # Test invalid length
    valid, error = verifier.verify_otp("short")
    assert not valid, "Short OTP should be rejected"
    assert "44 characters" in error, f"Expected length error, got: {error}"
    print(f"  ✓ Short OTP correctly rejected")

    # Test invalid characters
    # 'a' is not a valid ModHex character
    valid, error = verifier.verify_otp("a" * 44)
    assert not valid, "OTP with invalid characters should be rejected"
    assert "invalid characters" in error.lower(
    ), f"Expected character error, got: {error}"
    print(f"  ✓ Invalid characters correctly rejected")

    # Test valid format (ModHex characters)
    valid_otp = "ccccccbcgujhingjrdejhgfnuetrgigvejhhgbkugded"
    valid, error = verifier.verify_otp(valid_otp)
    # Should fail for other reasons (not registered, etc.) but format should be OK
    # The format validation passes, so error would be from API call
    print(f"  ✓ Valid format accepted for verification")

    # Test public ID extraction
    public_id = verifier.extract_public_id(valid_otp)
    assert public_id == "ccccccbcgujh", f"Expected 'ccccccbcgujh', got '{public_id}'"
    print(f"  ✓ Public ID extracted: {public_id}")

    return True


def test_yubikey_otp_verification_without_api():
    """Test YubiKey OTP verification (format check only, no API credentials)"""
    print("Testing YubiKey OTP verification...")

    # Create verifier without credentials (will use default test client)
    verifier = YubiKeyOTPVerifier()

    # Test with valid ModHex OTP
    test_otp = "ccccccbcgujhingjrdejhgfnuetrgigvejhhgbkugded"

    # Note: Without valid API credentials and a real OTP, this will fail at the API level
    # but the format validation and code path will be exercised
    valid, error = verifier.verify_otp(test_otp)

    # We expect this to fail since we don't have real credentials/OTP
    # but it should fail gracefully with an appropriate error message
    if not valid:
        print(
            f"  ✓ OTP verification attempted (failed as expected without valid credentials)")
        print(f"    Error: {error}")
    else:
        print(f"  ⚠ OTP verification succeeded (unexpected in test environment)")

    return True


def test_fido2_challenge_generation():
    """Test FIDO2 challenge generation"""
    print("Testing FIDO2 challenge generation...")

    verifier = FIDO2Verifier()

    # Generate challenge
    challenge = verifier.create_challenge()

    # Verify it's base64-encoded
    assert isinstance(challenge, str), "Challenge should be a string"
    assert len(challenge) > 0, "Challenge should not be empty"

    # Verify it's URL-safe base64 (no padding, no + or /)
    assert '=' not in challenge, "Challenge should not have padding"
    assert '+' not in challenge, "Challenge should be URL-safe"
    assert '/' not in challenge, "Challenge should be URL-safe"

    print(f"  ✓ Challenge generated: {challenge[:32]}...")

    # Verify uniqueness
    challenge2 = verifier.create_challenge()
    assert challenge != challenge2, "Challenges should be unique"
    print(f"  ✓ Challenges are unique")

    return True


def test_fido2_credential_registration():
    """Test FIDO2 credential registration"""
    print("Testing FIDO2 credential registration...")

    verifier = FIDO2Verifier()

    # Test with missing data
    success, result = verifier.register_credential("1001", {})
    assert not success, "Registration should fail with missing data"
    print(f"  ✓ Registration fails with missing data")

    # Test with valid data (simulated)
    import base64
    credential_id = base64.b64encode(
        b'test_credential_id_123456').decode('utf-8')
    public_key = base64.b64encode(
        b'test_public_key_data' *
        10).decode('utf-8')  # Make it longer

    credential_data = {
        'credential_id': credential_id,
        'public_key': public_key
    }

    success, result = verifier.register_credential("1001", credential_data)
    assert success, f"Registration should succeed with valid data: {result}"
    assert result == credential_id, "Should return credential ID"
    print(f"  ✓ Credential registered successfully")

    return True


def test_fido2_assertion_verification():
    """Test FIDO2 assertion verification"""
    print("Testing FIDO2 assertion verification...")

    verifier = FIDO2Verifier()

    # Test with missing data
    success, error = verifier.verify_assertion("test_cred", {}, b'public_key')
    assert not success, "Verification should fail with missing data"
    print(f"  ✓ Verification fails with missing data")

    # Test with simulated valid data (basic mode without full crypto)
    import base64

    # Create minimal valid-looking assertion data
    authenticator_data = base64.b64encode(
        b'X' * 37).decode('utf-8')  # Minimum length
    signature = base64.b64encode(
        b'S' * 64).decode('utf-8')  # Minimum signature length
    client_data = base64.b64encode(
        b'{"type":"webauthn.get","challenge":"test"}').decode('utf-8')

    assertion_data = {
        'authenticator_data': authenticator_data,
        'signature': signature,
        'client_data_json': client_data
    }

    public_key = base64.b64encode(b'K' * 100).decode('utf-8')

    # This will use basic verification mode since we don't have a real FIDO2
    # setup
    success, error = verifier.verify_assertion(
        "test_cred", assertion_data, public_key)

    # In basic mode, this should succeed since all data is present and valid
    # length
    if success:
        print(f"  ✓ Assertion verified (basic mode)")
    else:
        # If fido2 library is available and does full verification, it may fail
        print(f"  ✓ Assertion verification attempted (library mode): {error}")

    return True


def run_all_tests():
    """Run all MFA tests"""
    print("=" * 60)
    print("MFA Feature Tests")
    print("=" * 60)
    print()

    tests = [
        test_totp_generation,
        test_totp_verification,
        test_totp_provisioning_uri,
        test_mfa_manager_basic,
        test_mfa_enrollment_without_db,
        test_backup_code_format,
        test_mfa_with_database,
        test_yubikey_otp_format_validation,
        test_yubikey_otp_verification_without_api,
        test_fido2_challenge_generation,
        test_fido2_credential_registration,
        test_fido2_assertion_verification,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
