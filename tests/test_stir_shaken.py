#!/usr/bin/env python3
"""
Tests for STIR/SHAKEN caller ID authentication
"""

import base64
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.stir_shaken import (
    CRYPTO_AVAILABLE,
    AttestationLevel,
    STIRSHAKENManager,
    VerificationStatus,
    add_stir_shaken_to_invite,
    verify_stir_shaken_invite,
)
from pbx.sip.message import SIPMessage


def create_test_manager():
    """Create STIR/SHAKEN manager with test certificates"""
    if not CRYPTO_AVAILABLE:
        print("⚠ Cryptography library not available, skipping tests")
        return None

    manager = STIRSHAKENManager()

    # Generate test certificates
    temp_dir = tempfile.mkdtemp()
    cert_path, key_path = manager.generate_test_certificate(temp_dir)

    # Reload manager with certificates
    config = {
        "certificate_path": cert_path,
        "private_key_path": key_path,
        "originating_tn": "+12125551234",
        "service_provider_code": "TEST-SP",
        "enable_signing": True,
        "enable_verification": True,
    }

    manager = STIRSHAKENManager(config)
    return manager


def test_manager_initialization():
    """Test manager initializes correctly"""
    print("Testing STIR/SHAKEN manager initialization...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = STIRSHAKENManager()
    assert manager is not None, "Manager should initialize"
    assert (
        manager.enabled == CRYPTO_AVAILABLE
    ), "Manager enabled state should match crypto availability"

    print("  ✓ Manager initialized successfully")
    return True


def test_manager_with_config():
    """Test manager initialization with config"""
    print("Testing manager with config...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()
    assert manager.enabled, "Manager should be enabled"
    assert manager.private_key is not None, "Private key should be loaded"
    assert manager.certificate is not None, "Certificate should be loaded"
    assert manager.enable_signing, "Signing should be enabled"
    assert manager.enable_verification, "Verification should be enabled"

    print("  ✓ Manager configured successfully")
    return True


def test_attestation_levels():
    """Test attestation level enum"""
    print("Testing attestation levels...")

    assert AttestationLevel.FULL.value == "A", "Full attestation should be 'A'"
    assert AttestationLevel.PARTIAL.value == "B", "Partial attestation should be 'B'"
    assert AttestationLevel.GATEWAY.value == "C", "Gateway attestation should be 'C'"

    print("  ✓ Attestation levels correct")
    return True


def test_create_passport_full():
    """Test creating PASSporT with full attestation"""
    print("Testing PASSporT creation (full attestation)...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()
    passport = manager.create_passport(
        originating_tn="+12125551234",
        destination_tn="+13105555678",
        attestation=AttestationLevel.FULL,
    )

    assert passport is not None, "PASSporT should be created"
    assert len(passport.split(".")) == 3, "PASSporT should be JWT format"

    # Verify JWT structure
    header_b64, payload_b64, sig_b64 = passport.split(".")
    assert len(header_b64) > 0, "Header should exist"
    assert len(payload_b64) > 0, "Payload should exist"
    assert len(sig_b64) > 0, "Signature should exist"

    print(f"  ✓ Created PASSporT: {passport[:50]}...")
    return True


def test_create_passport_partial():
    """Test creating PASSporT with partial attestation"""
    print("Testing PASSporT creation (partial attestation)...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()
    passport = manager.create_passport(
        originating_tn="+12125551234",
        destination_tn="+13105555678",
        attestation=AttestationLevel.PARTIAL,
    )

    assert passport is not None, "PASSporT should be created"

    # Decode and check attestation level
    payload_b64 = passport.split(".")[1]
    padding = 4 - (len(payload_b64) % 4)
    if padding != 4:
        payload_b64 += "=" * padding

    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    assert payload["attest"] == "B", "Attestation should be 'B'"

    print("  ✓ Partial attestation verified")
    return True


def test_verify_valid_passport():
    """Test verifying a valid PASSporT"""
    print("Testing PASSporT verification...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()

    # Create a PASSporT
    passport = manager.create_passport(
        originating_tn="+12125551234",
        destination_tn="+13105555678",
        attestation=AttestationLevel.FULL,
    )

    # Verify it
    valid, payload, reason = manager.verify_passport(passport)

    assert valid, f"PASSporT should be valid: {reason}"
    assert payload is not None, "Payload should be returned"
    assert payload["attest"] == "A", "Attestation should be 'A'"

    print("  ✓ PASSporT verified successfully")
    return True


def test_verify_invalid_signature():
    """Test verifying PASSporT with invalid signature"""
    print("Testing invalid signature detection...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()

    # Create a PASSporT
    passport = manager.create_passport(
        originating_tn="+12125551234",
        destination_tn="+13105555678",
        attestation=AttestationLevel.FULL,
    )

    # Tamper with signature
    parts = passport.split(".")
    parts[2] = parts[2][:-5] + "XXXXX"
    tampered_passport = ".".join(parts)

    # Verify should fail
    valid, payload, reason = manager.verify_passport(tampered_passport)

    assert not valid, "Tampered PASSporT should fail verification"

    print("  ✓ Invalid signature detected")
    return True


def test_create_identity_header():
    """Test creating SIP Identity header"""
    print("Testing Identity header creation...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()
    identity = manager.create_identity_header(
        originating_tn="+12125551234",
        destination_tn="+13105555678",
        attestation=AttestationLevel.FULL,
    )

    assert identity is not None, "Identity header should be created"
    assert "info=" in identity, "Identity should contain info parameter"
    assert "alg=" in identity, "Identity should contain alg parameter"
    assert "ppt=" in identity, "Identity should contain ppt parameter"
    assert "shaken" in identity, "Identity should contain shaken"

    print(f"  ✓ Created Identity header")
    return True


def test_verify_identity_header():
    """Test verifying Identity header"""
    print("Testing Identity header verification...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()
    identity = manager.create_identity_header(
        originating_tn="+12125551234",
        destination_tn="+13105555678",
        attestation=AttestationLevel.FULL,
    )

    status, payload = manager.verify_identity_header(identity)

    assert status == VerificationStatus.VERIFIED_FULL, "Should be verified full"
    assert payload is not None, "Payload should be returned"
    assert payload["attest"] == "A", "Attestation should be 'A'"

    print("  ✓ Identity header verified")
    return True


def test_sip_integration():
    """Test integration with SIP messages"""
    print("Testing SIP INVITE integration...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()

    # Create SIP INVITE message
    sip_msg = SIPMessage()
    sip_msg.method = "INVITE"
    sip_msg.uri = "sip:+13105555678@example.com"
    sip_msg.set_header("From", "<sip:+12125551234@pbx.local>")
    sip_msg.set_header("To", "<sip:+13105555678@example.com>")

    # Add STIR/SHAKEN
    sip_msg = add_stir_shaken_to_invite(
        sip_msg, manager, "+12125551234", "+13105555678", AttestationLevel.FULL
    )

    # Check Identity header was added
    identity = sip_msg.get_header("Identity")
    assert identity is not None, "Identity header should be added"
    assert "shaken" in identity, "Identity should contain shaken"

    # Verify the signature
    status, payload = verify_stir_shaken_invite(sip_msg, manager)

    assert status == VerificationStatus.VERIFIED_FULL, "Should be verified full"
    assert payload is not None, "Payload should be returned"

    print("  ✓ SIP INVITE integration working")
    return True


def test_normalize_telephone_numbers():
    """Test telephone number normalization"""
    print("Testing telephone number normalization...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()

    # Test US number normalization
    normalized = manager._normalize_tn("2125551234")
    assert normalized == "+12125551234", "Should add +1 prefix to 10-digit number"

    # Test already normalized
    normalized = manager._normalize_tn("+12125551234")
    assert normalized == "+12125551234", "Should keep normalized number"

    # Test with formatting
    normalized = manager._normalize_tn("(212) 555-1234")
    assert normalized == "+12125551234", "Should strip formatting"

    print("  ✓ Telephone normalization working")
    return True


def test_verification_status_display():
    """Test verification status display info"""
    print("Testing verification status display...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = create_test_manager()

    # Test full verification
    info = manager.get_verification_status_display(VerificationStatus.VERIFIED_FULL)
    assert "label" in info, "Should have label"
    assert "description" in info, "Should have description"
    assert "trust_level" in info, "Should have trust level"
    assert info["trust_level"] == "high", "Full verification should be high trust"

    # Test failed verification
    info = manager.get_verification_status_display(VerificationStatus.VERIFICATION_FAILED)
    assert info["trust_level"] == "none", "Failed verification should be no trust"

    print("  ✓ Verification status display working")
    return True


def test_certificate_generation():
    """Test test certificate generation"""
    print("Testing certificate generation...")

    if not CRYPTO_AVAILABLE:
        print("  ⚠ Skipped (cryptography not available)")
        return True

    manager = STIRSHAKENManager()
    temp_dir = tempfile.mkdtemp()
    cert_path, key_path = manager.generate_test_certificate(temp_dir)

    assert os.path.exists(cert_path), "Certificate file should exist"
    assert os.path.exists(key_path), "Key file should exist"

    # Verify certificate can be loaded
    with open(cert_path, "rb") as f:
        cert_data = f.read()
        assert b"BEGIN CERTIFICATE" in cert_data, "Should be valid certificate"

    # Verify key can be loaded
    with open(key_path, "rb") as f:
        key_data = f.read()
        assert b"BEGIN PRIVATE KEY" in key_data, "Should be valid key"

    print("  ✓ Certificate generation working")
    return True


def run_all_tests():
    """Run all tests"""
    tests = [
        test_manager_initialization,
        test_manager_with_config,
        test_attestation_levels,
        test_create_passport_full,
        test_create_passport_partial,
        test_verify_valid_passport,
        test_verify_invalid_signature,
        test_create_identity_header,
        test_verify_identity_header,
        test_sip_integration,
        test_normalize_telephone_numbers,
        test_verification_status_display,
        test_certificate_generation,
    ]

    print("\n" + "=" * 70)
    print("STIR/SHAKEN Caller ID Authentication Tests")
    print("=" * 70 + "\n")

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ Test {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ Test {test.__name__} error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
