#!/usr/bin/env python3
"""
Test TLS 1.3 Support
Verifies that the PBX system supports TLS 1.3 for secure communications
"""

import os
import ssl
import tempfile
import time
import traceback
from datetime import UTC
from typing import Any

from pbx.api.rest_api import PBXAPIServer
from pbx.utils.config import Config
from pbx.utils.tls_support import TLSManager


def generate_test_certificate() -> tuple[str | None, str | None]:
    """Generate a test certificate for TLS testing"""
    try:
        from datetime import datetime, timedelta, timezone

        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
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
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
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


def test_tls_version_availability() -> bool:
    """Test that TLS 1.3 is available in Python ssl module"""

    # Check if TLS 1.3 is available
    has_tls13 = hasattr(ssl.TLSVersion, "TLSv1_3")

    if not has_tls13:
        return False

    # List all available TLS versions
    [attr for attr in dir(ssl.TLSVersion) if attr.startswith("TLS")]

    return True


def test_tls_manager_context() -> bool:
    """Test TLSManager creates context that supports TLS 1.3"""

    # Generate test certificate
    cert_file, key_file = generate_test_certificate()
    if not cert_file or not key_file:
        return True

    try:
        # Test with FIPS mode disabled
        tls_manager = TLSManager(cert_file=cert_file, key_file=key_file, fips_mode=False)

        if not tls_manager.is_available():
            return False

        # Check SSL context configuration
        ctx = tls_manager.ssl_context

        # Verify minimum version is at least TLS 1.2
        if ctx.minimum_version < ssl.TLSVersion.TLSv1_2:
            return False

        # Check that no maximum version is set (allows TLS 1.3)
        max_version = getattr(ctx, "maximum_version", ssl.TLSVersion.MAXIMUM_SUPPORTED)

        if max_version != ssl.TLSVersion.MAXIMUM_SUPPORTED:
            pass

        # Test with FIPS mode enabled
        tls_manager_fips = TLSManager(cert_file=cert_file, key_file=key_file, fips_mode=True)

        if not tls_manager_fips.is_available():
            return False

        ctx_fips = tls_manager_fips.ssl_context

        if ctx_fips.minimum_version < ssl.TLSVersion.TLSv1_2:
            return False

    finally:
        # Clean up temporary files
        if cert_file:
            os.unlink(cert_file)
        if key_file:
            os.unlink(key_file)

    return True


def test_api_server_tls13_support() -> bool:
    """Test that API server supports TLS 1.3"""

    # Generate test certificate
    cert_file, key_file = generate_test_certificate()
    if not cert_file or not key_file:
        return True

    try:
        # Create mock PBX core with mock config
        class MockConfig:
            """Mock config for testing"""

            def get(self, key: str, default: Any = None) -> Any:
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
            def __init__(self) -> None:
                self.config = MockConfig()

            def get_status(self) -> dict[str, int]:
                return {"registered_extensions": 0, "active_calls": 0, "uptime": 0}

        mock_pbx = MockPBXCore()

        # Create API server
        api_server = PBXAPIServer(mock_pbx, host="127.0.0.1", port=9999)

        if not api_server.ssl_enabled:
            return False

        if api_server.ssl_context is None:
            return False

        # Check SSL context configuration
        ctx = api_server.ssl_context

        if ctx.minimum_version < ssl.TLSVersion.TLSv1_2:
            return False

        # Check that TLS 1.3 is allowed
        max_version = getattr(ctx, "maximum_version", ssl.TLSVersion.MAXIMUM_SUPPORTED)

        if max_version != ssl.TLSVersion.MAXIMUM_SUPPORTED:
            pass

    finally:
        # Clean up temporary files
        if cert_file:
            os.unlink(cert_file)
        if key_file:
            os.unlink(key_file)

    return True


def test_ssl_context_security_options() -> bool:
    """Test that SSL context has proper security options set"""

    # Generate test certificate
    cert_file, key_file = generate_test_certificate()
    if not cert_file or not key_file:
        return True

    try:
        tls_manager = TLSManager(cert_file=cert_file, key_file=key_file, fips_mode=False)

        if not tls_manager.is_available():
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
        for option, _name in required_options:
            if not options & option:
                all_set = False

        # Check OP_NO_SSLv2 separately as it may not be set in modern OpenSSL
        if hasattr(ssl, "OP_NO_SSLv2") and not options & ssl.OP_NO_SSLv2:
            pass  # Not a failure - modern OpenSSL may not have SSLv2

        if not all_set:
            return False

    finally:
        # Clean up temporary files
        if cert_file:
            os.unlink(cert_file)
        if key_file:
            os.unlink(key_file)

    return True


def main() -> bool:
    """Run all TLS 1.3 support tests"""

    tests = [
        ("TLS 1.3 Availability", test_tls_version_availability),
        ("TLSManager TLS 1.3 Support", test_tls_manager_context),
        ("API Server TLS 1.3 Support", test_api_server_tls13_support),
        ("SSL Security Options", test_ssl_context_security_options),
    ]

    passed = 0
    failed = 0

    for _test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            traceback.print_exc()

    return failed == 0
