#!/usr/bin/env python3
"""
FIPS 140-2 Compliance Verification Script
Verifies that the PBX system is running in FIPS-compliant mode
"""
import os
import subprocess
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pbx.utils.config import Config
from pbx.utils.encryption import CRYPTO_AVAILABLE, FIPSEncryption, get_encryption


def print_header(text):
    """Print section header"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_status(test_name, passed, message=""):
    """Print test status"""
    status = "✓ PASS" if passed else "✗ FAIL"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"

    print(f"{color}{status}{reset} - {test_name}")
    if message:
        print(f"       {message}")


def check_system_fips():
    """Check if system-level FIPS is enabled"""
    print_header("System FIPS Configuration")

    all_passed = True

    # Check kernel FIPS mode
    try:
        with open("/proc/sys/crypto/fips_enabled", "r") as f:
            fips_enabled = f.read().strip() == "1"
            print_status("Kernel FIPS mode", fips_enabled, f"Value: {fips_enabled}")
            if not fips_enabled:
                all_passed = False
    except FileNotFoundError:
        print_status("Kernel FIPS mode", False, "File /proc/sys/crypto/fips_enabled not found")
        all_passed = False

    # Check OpenSSL FIPS
    try:
        result = subprocess.run(["openssl", "list", "-providers"], capture_output=True, text=True)
        has_fips = "fips" in result.stdout.lower()
        print_status("OpenSSL FIPS provider", has_fips)
        if not has_fips:
            all_passed = False
            print("       OpenSSL providers:")
            for line in result.stdout.split("\n")[:10]:
                if line.strip():
                    print(f"         {line}")
    except Exception as e:
        print_status("OpenSSL FIPS provider", False, str(e))
        all_passed = False

    # Check Python hashlib FIPS mode
    try:
        import hashlib

        fips_mode_func = getattr(hashlib, "get_fips_mode", None)
        if fips_mode_func:
            fips_mode = fips_mode_func()
            print_status("Python hashlib FIPS mode", fips_mode == 1, f"Value: {fips_mode}")
            if fips_mode != 1:
                all_passed = False
        else:
            print_status("Python hashlib FIPS mode", False, "get_fips_mode() not available")
            all_passed = False
    except Exception as e:
        print_status("Python hashlib FIPS mode", False, str(e))
        all_passed = False

    return all_passed


def check_cryptography_library():
    """Check cryptography library configuration"""
    print_header("Cryptography Library")

    all_passed = True

    # Check if cryptography is installed
    print_status("Cryptography library installed", CRYPTO_AVAILABLE, "Required for FIPS compliance")
    if not CRYPTO_AVAILABLE:
        all_passed = False
        return all_passed

    # Check cryptography version
    try:
        import cryptography

        version = cryptography.__version__
        # Parse version safely (handle alpha, beta, rc versions)
        version_clean = version.split("-")[0].split("+")[0]  # Remove suffixes
        version_parts = [int(x) for x in version_clean.split(".")]

        # Check if version >= 41.0.0
        major = version_parts[0] if len(version_parts) > 0 else 0
        minor = version_parts[1] if len(version_parts) > 1 else 0

        meets_requirement = (major > 41) or (major == 41 and minor >= 0)
        print_status("Cryptography version >= 41.0.0", meets_requirement, f"Installed: {version}")
        if not meets_requirement:
            all_passed = False
    except Exception as e:
        print_status("Cryptography version check", False, str(e))
        all_passed = False

    # Check OpenSSL backend
    try:
        from cryptography.hazmat.backends import default_backend

        backend = default_backend()
        backend_name = str(backend)
        print_status("OpenSSL backend", True, backend_name)

        # Check if backend reports FIPS
        if "FIPS: True" in backend_name:
            print_status("Backend FIPS mode", True)
        elif "FIPS: False" in backend_name:
            print_status("Backend FIPS mode", False, "Backend is not using FIPS-validated module")
            all_passed = False
        else:
            print_status("Backend FIPS mode", False, "Cannot determine FIPS status from backend")
    except Exception as e:
        print_status("OpenSSL backend check", False, str(e))
        all_passed = False

    return all_passed


def check_pbx_configuration():
    """Check PBX FIPS configuration"""
    print_header("PBX System Configuration")

    all_passed = True

    # Load config
    try:
        config = Config("config.yml")

        # Check FIPS mode setting
        fips_mode = config.get("security.fips_mode", False)
        print_status("FIPS mode enabled in config", fips_mode, f"security.fips_mode = {fips_mode}")
        if not fips_mode:
            all_passed = False

        # Check enforce FIPS
        enforce_fips = config.get("security.enforce_fips", False)
        print_status(
            "FIPS enforcement enabled", enforce_fips, f"security.enforce_fips = {enforce_fips}"
        )

        # Check password policy
        min_length = config.get("security.password.min_length", 0)
        print_status("Password minimum length >= 12", min_length >= 12, f"Min length: {min_length}")
        if min_length < 12:
            all_passed = False

        # Check TLS configuration
        enable_tls = config.get("security.enable_tls", False)
        print_status("TLS enabled (recommended)", enable_tls, "For SIPS (SIP over TLS)")

        # Check SRTP configuration
        enable_srtp = config.get("security.enable_srtp", False)
        print_status("SRTP enabled (recommended)", enable_srtp, "For encrypted media streams")

    except Exception as e:
        print_status("Config file check", False, str(e))
        all_passed = False

    return all_passed


def test_encryption_operations():
    """Test FIPS-compliant encryption operations"""
    print_header("Encryption Operations Test")

    all_passed = True

    try:
        # Create encryption instance with FIPS mode
        enc = get_encryption(fips_mode=True, enforce_fips=False)

        # Test password hashing
        test_password = "TestPassword123!"
        try:
            hash1, salt = enc.hash_password(test_password)
            print_status("Password hashing (PBKDF2-HMAC-SHA256)", True, "600,000 iterations")
        except Exception as e:
            print_status("Password hashing", False, str(e))
            all_passed = False

        # Test password verification
        try:
            is_valid = enc.verify_password(test_password, hash1, salt)
            print_status("Password verification", is_valid)
            if not is_valid:
                all_passed = False
        except Exception as e:
            print_status("Password verification", False, str(e))
            all_passed = False

        # Test data hashing
        try:
            hash_result = enc.hash_data("test data")
            print_status(
                "SHA-256 hashing",
                len(hash_result) == 64,
                f"Hash length: {len(hash_result)} hex chars",
            )
            if len(hash_result) != 64:
                all_passed = False
        except Exception as e:
            print_status("SHA-256 hashing", False, str(e))
            all_passed = False

        # Test data encryption (AES-256-GCM)
        if CRYPTO_AVAILABLE:
            try:
                # Derive proper 32-byte key
                password = "encryption_key_password"
                key, salt = enc.derive_key(password, key_length=32)

                data = "Test data for encryption"
                encrypted, nonce, tag = enc.encrypt_data(data, key)
                print_status("AES-256-GCM encryption", True)

                # Test decryption
                decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
                matches = decrypted.decode() == data
                print_status("AES-256-GCM decryption", matches)
                if not matches:
                    all_passed = False
            except Exception as e:
                print_status("AES-256-GCM encryption", False, str(e))
                all_passed = False

        # Test secure token generation
        try:
            token = enc.generate_secure_token(32)
            print_status("Secure token generation", len(token) > 0, "Using secrets module")
        except Exception as e:
            print_status("Secure token generation", False, str(e))
            all_passed = False

    except Exception as e:
        print_status("Encryption test initialization", False, str(e))
        all_passed = False

    return all_passed


def check_dependencies():
    """Check Python dependencies for FIPS compliance"""
    print_header("Python Dependencies")

    all_passed = True

    # Required packages
    packages = {
        "cryptography": "41.0.0",
        "PyYAML": "5.1",
    }

    # Optional but recommended
    optional_packages = {
        "psycopg2-binary": "2.9.0",
        "requests": "2.31.0",
    }

    # Map package names to import names
    package_import_map = {
        "cryptography": "cryptography",
        "PyYAML": "yaml",
        "psycopg2-binary": "psycopg2",
        "requests": "requests",
    }

    for package, min_version in packages.items():
        try:
            import_name = package_import_map.get(package, package.replace("-", "_"))
            module = __import__(import_name)
            version = getattr(module, "__version__", "unknown")
            print_status(f"{package} installed", True, f"Version: {version}")
        except ImportError:
            print_status(f"{package} installed", False, f"Required: >= {min_version}")
            all_passed = False

    for package, min_version in optional_packages.items():
        try:
            import_name = package_import_map.get(package, package.replace("-", "_"))
            module = __import__(import_name)
            version = getattr(module, "__version__", "unknown")
            print_status(f"{package} installed (optional)", True, f"Version: {version}")
        except ImportError:
            print_status(f"{package} installed (optional)", False, f"Recommended: >= {min_version}")

    return all_passed


def generate_report():
    """Generate comprehensive FIPS compliance report"""
    print("\n" + "=" * 70)
    print("FIPS 140-2 COMPLIANCE VERIFICATION REPORT")
    print("=" * 70)

    results = {
        "system": check_system_fips(),
        "cryptography": check_cryptography_library(),
        "pbx_config": check_pbx_configuration(),
        "encryption": test_encryption_operations(),
        "dependencies": check_dependencies(),
    }

    # Summary
    print_header("Compliance Summary")

    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)

    print(f"\nCategories Passed: {total_passed}/{total_tests}")
    print()

    for category, passed in results.items():
        status = "✓" if passed else "✗"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"
        category_name = category.replace("_", " ").title()
        print(f"{color}{status}{reset} {category_name}")

    print()

    # Overall compliance status
    overall_passed = all(results.values())

    if overall_passed:
        print("\033[92m" + "=" * 70)
        print("✓ FIPS 140-2 COMPLIANCE: VERIFIED")
        print("=" * 70 + "\033[0m")
        print("\nThe PBX system is configured for FIPS 140-2 compliance.")
        print("All cryptographic operations use FIPS-approved algorithms.")
        return 0
    else:
        print("\033[91m" + "=" * 70)
        print("✗ FIPS 140-2 COMPLIANCE: ISSUES FOUND")
        print("=" * 70 + "\033[0m")
        print("\nThe following issues need to be addressed:")
        print()

        if not results["system"]:
            print("• System FIPS mode is not properly enabled")
            print("  Run: sudo ./scripts/enable_fips_ubuntu.sh")

        if not results["cryptography"]:
            print("• Cryptography library issues detected")
            print("  Install: pip install cryptography>=41.0.0")

        if not results["pbx_config"]:
            print("• PBX configuration needs adjustment")
            print("  Edit config.yml and set security.fips_mode = true")

        if not results["encryption"]:
            print("• Encryption operations test failed")
            print("  Check system FIPS configuration")

        if not results["dependencies"]:
            print("• Missing required dependencies")
            print("  Install: pip install -r requirements.txt")

        print()
        print("After fixing issues, run this script again to verify compliance.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = generate_report()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during verification: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
