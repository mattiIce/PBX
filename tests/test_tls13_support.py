#!/usr/bin/env python3
"""
Test TLS 1.3 Support
Verifies that the PBX system supports TLS 1.3 for secure communications
"""

import os
import ssl
import sys
import tempfile
import time
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config
from pbx.utils.tls_support import TLSManager


def generate_test_certificate():
    """Generate a test certificate for TLS testing"""
    try:
        from datetime import datetime, timedelta, timezone

        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("cryptography module not available, skipping certificate generation")
        return None, None

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Generate certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Test"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Test"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    # Write to temporary files
    cert_file = tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".crt")
    key_file = tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".key")

    cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
    cert_file.close()

    key_file.write(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_file.close()

    return cert_file.name, key_file.name


def test_tls_version_availability():
    """Test that TLS 1.3 is available in Python ssl module"""
    print("=" * 60)
    print("Test 1: TLS 1.3 Availability")
    print("=" * 60)

    # Check if TLS 1.3 is available
    has_tls13 = hasattr(ssl.TLSVersion, "TLSv1_3")
    print(f"  TLS 1.3 available in ssl module: {has_tls13}")

    if has_tls13:
        print("  ✓ TLS 1.3 is supported (ssl.TLSVersion.TLSv1_3)")
    else:
        print("  ✗ TLS 1.3 is not supported")
        return False

    # List all available TLS versions
    tls_versions = [attr for attr in dir(ssl.TLSVersion) if attr.startswith("TLS")]
    print(f"  Available TLS versions: {', '.join(tls_versions)}")

    print()
    return True


def test_tls_manager_context():
    """Test TLSManager creates context that supports TLS 1.3"""
    print("=" * 60)
    print("Test 2: TLSManager TLS 1.3 Support")
    print("=" * 60)

    # Generate test certificate
    cert_file, key_file = generate_test_certificate()
    if not cert_file or not key_file:
        print("  ⚠ Could not generate test certificate, skipping test")
        return True

    try:
        # Test with FIPS mode disabled
        print("  Testing TLSManager (FIPS mode: disabled)...")
        tls_manager = TLSManager(cert_file=cert_file, key_file=key_file, fips_mode=False)

        if not tls_manager.is_available():
            print("  ✗ TLS context not created")
            return False

        # Check SSL context configuration
        ctx = tls_manager.ssl_context
        print("  ✓ SSL context created")
        print(f"  Minimum TLS version: {ctx.minimum_version}")

        # Verify minimum version is at least TLS 1.2
        if ctx.minimum_version < ssl.TLSVersion.TLSv1_2:
            print("  ✗ Minimum TLS version should be at least 1.2")
            return False

        print(f"  ✓ Minimum TLS version is {ctx.minimum_version.name}")

        # Check that no maximum version is set (allows TLS 1.3)
        max_version = getattr(ctx, "maximum_version", ssl.TLSVersion.MAXIMUM_SUPPORTED)
        print(f"  Maximum TLS version: {max_version}")

        if max_version == ssl.TLSVersion.MAXIMUM_SUPPORTED:
            print("  ✓ TLS 1.3 is allowed (no maximum version restriction)")
        else:
            print(f"  ⚠ Maximum TLS version is restricted to {max_version.name}")

        # Test with FIPS mode enabled
        print("\n  Testing TLSManager (FIPS mode: enabled)...")
        tls_manager_fips = TLSManager(cert_file=cert_file, key_file=key_file, fips_mode=True)

        if not tls_manager_fips.is_available():
            print("  ✗ TLS context not created with FIPS mode")
            return False

        ctx_fips = tls_manager_fips.ssl_context
        print("  ✓ SSL context created with FIPS mode")
        print(f"  Minimum TLS version: {ctx_fips.minimum_version}")

        if ctx_fips.minimum_version < ssl.TLSVersion.TLSv1_2:
            print("  ✗ Minimum TLS version should be at least 1.2 in FIPS mode")
            return False

        print(f"  ✓ FIPS mode minimum TLS version is {ctx_fips.minimum_version.name}")

    finally:
        # Clean up temporary files
        if cert_file:
            os.unlink(cert_file)
        if key_file:
            os.unlink(key_file)

    print()
    return True


def test_api_server_tls13_support():
    """Test that API server supports TLS 1.3"""
    print("=" * 60)
    print("Test 3: API Server TLS 1.3 Support")
    print("=" * 60)

    # Generate test certificate
    cert_file, key_file = generate_test_certificate()
    if not cert_file or not key_file:
        print("  ⚠ Could not generate test certificate, skipping test")
        return True

    try:
        # Create mock PBX core with mock config
        class MockConfig:
            """Mock config for testing"""

            def get(self, key, default=None):
                """Mock get method that returns appropriate values for SSL testing"""
                if key == "api.ssl":
                    return {
                        "enabled": True,
                        "cert_file": cert_file,
                        "key_file": key_file,
                        "ca": {"enabled": False},
                    }
                # Return defaults for other config values
                return default

        class MockPBXCore:
            def __init__(self):
                self.config = MockConfig()

            def get_status(self):
                return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}

        mock_pbx = MockPBXCore()

        # Create API server
        print("  Creating API server with SSL...")
        api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=9999)

        if not api_server.ssl_enabled:
            print("  ✗ SSL should be enabled")
            return False

        if api_server.ssl_context is None:
            print("  ✗ SSL context should be created")
            return False

        print("  ✓ API server created with SSL enabled")

        # Check SSL context configuration
        ctx = api_server.ssl_context
        print(f"  Minimum TLS version: {ctx.minimum_version}")

        if ctx.minimum_version < ssl.TLSVersion.TLSv1_2:
            print("  ✗ Minimum TLS version should be at least 1.2")
            return False

        print(f"  ✓ Minimum TLS version is {ctx.minimum_version.name}")

        # Check that TLS 1.3 is allowed
        max_version = getattr(ctx, "maximum_version", ssl.TLSVersion.MAXIMUM_SUPPORTED)
        print(f"  Maximum TLS version: {max_version}")

        if max_version == ssl.TLSVersion.MAXIMUM_SUPPORTED:
            print("  ✓ TLS 1.3 is allowed (no maximum version restriction)")
        else:
            print(f"  ⚠ Maximum TLS version is restricted to {max_version.name}")

        print("  ✓ API server SSL context supports TLS 1.2-1.3")

    finally:
        # Clean up temporary files
        if cert_file:
            os.unlink(cert_file)
        if key_file:
            os.unlink(key_file)

    print()
    return True


def test_ssl_context_security_options():
    """Test that SSL context has proper security options set"""
    print("=" * 60)
    print("Test 4: SSL Context Security Options")
    print("=" * 60)

    # Generate test certificate
    cert_file, key_file = generate_test_certificate()
    if not cert_file or not key_file:
        print("  ⚠ Could not generate test certificate, skipping test")
        return True

    try:
        tls_manager = TLSManager(cert_file=cert_file, key_file=key_file, fips_mode=False)

        if not tls_manager.is_available():
            print("  ✗ TLS context not created")
            return False

        ctx = tls_manager.ssl_context

        # Check that insecure protocols are disabled
        options = ctx.options

        # These options should be set (if available in the ssl module)
        # Note: OP_NO_SSLv2 might not be available or set in modern OpenSSL
        # as SSLv2 is completely removed from newer versions
        required_options = [
            (ssl.OP_NO_SSLv3, "OP_NO_SSLv3"),
            (ssl.OP_NO_TLSv1, "OP_NO_TLSv1"),
            (ssl.OP_NO_TLSv1_1, "OP_NO_TLSv1_1"),
        ]

        all_set = True
        for option, name in required_options:
            if options & option:
                print(f"  ✓ {name} is set (insecure protocol disabled)")
            else:
                print(f"  ✗ {name} is not set")
                all_set = False

        # Check OP_NO_SSLv2 separately as it may not be set in modern OpenSSL
        if hasattr(ssl, "OP_NO_SSLv2"):
            if options & ssl.OP_NO_SSLv2:
                print("  ✓ OP_NO_SSLv2 is set (insecure protocol disabled)")
            else:
                # This is not a failure - modern OpenSSL may not have SSLv2 at all
                print("  ℹ OP_NO_SSLv2 not set (likely SSLv2 is not compiled in OpenSSL)")

        if not all_set:
            return False

        print("  ✓ All critical insecure protocols (SSLv3, TLSv1, TLSv1.1) are disabled")

    finally:
        # Clean up temporary files
        if cert_file:
            os.unlink(cert_file)
        if key_file:
            os.unlink(key_file)

    print()
    return True


def main():
    """Run all TLS 1.3 support tests"""
    print("\n" + "=" * 60)
    print("TLS 1.3 Support Tests")
    print("=" * 60)
    print()

    tests = [
        ("TLS 1.3 Availability", test_tls_version_availability),
        ("TLSManager TLS 1.3 Support", test_tls_manager_context),
        ("API Server TLS 1.3 Support", test_api_server_tls13_support),
        ("SSL Security Options", test_ssl_context_security_options),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} passed\n")
            else:
                failed += 1
                print(f"✗ {test_name} failed\n")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} error: {e}\n")
            traceback.print_exc()

    print("=" * 60)
    print(f"Tests completed: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
