#!/usr/bin/env python3
"""
FIPS Health Check Script
Performs continuous monitoring of FIPS compliance status
Can be run as a cron job or service health check
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check_kernel_fips():
    """Check if kernel FIPS mode is enabled"""
    try:
        with open("/proc/sys/crypto/fips_enabled", "r") as f:
            return f.read().strip() == "1"
    except FileNotFoundError:
        return False


def check_python_fips():
    """Check if Python hashlib is in FIPS mode"""
    try:
        import hashlib

        fips_mode_func = getattr(hashlib, "get_fips_mode", None)
        if fips_mode_func:
            return fips_mode_func() == 1
        return False
    except Exception:
        return False


def check_cryptography():
    """Check if cryptography library is FIPS-enabled"""
    try:
        from cryptography.hazmat.backends import default_backend

        backend = default_backend()
        backend_str = str(backend)
        return "FIPS: True" in backend_str
    except (KeyError, TypeError, ValueError):
        return False


def check_pbx_config():
    """Check if PBX is configured for FIPS mode"""
    try:
        from pbx.utils.config import Config

        config = Config("config.yml")
        fips_mode = config.get("security.fips_mode", False)
        enforce_fips = config.get("security.enforce_fips", False)
        return fips_mode, enforce_fips
    except (KeyError, TypeError, ValueError):
        return False, False


def check_encryption_operations():
    """Test basic encryption operations"""
    try:
        from pbx.utils.encryption import get_encryption

        enc = get_encryption(fips_mode=True, enforce_fips=False)

        # Test password hashing
        test_password = "TestPass123!"
        hash1, salt = enc.hash_password(test_password)
        is_valid = enc.verify_password(test_password, hash1, salt)

        return is_valid
    except Exception:
        return False


def generate_health_report():
    """Generate health check report"""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Perform all checks
    kernel_fips = check_kernel_fips()
    python_fips = check_python_fips()
    crypto_fips = check_cryptography()
    fips_mode, enforce_fips = check_pbx_config()
    encryption_ok = check_encryption_operations()

    # Calculate overall health with weighted checks
    # Critical checks have higher weight
    check_weights = {
        "kernel_fips": 2.0,  # Critical: System FIPS mode
        "python_fips": 1.5,  # Important: Python FIPS
        "crypto_fips": 2.0,  # Critical: Crypto library FIPS
        "fips_mode": 1.5,  # Important: Config setting
        "encryption_ok": 2.0,  # Critical: Encryption works
    }

    weighted_score = 0
    total_weight = 0

    weighted_score += 2.0 if kernel_fips else 0
    weighted_score += 1.5 if python_fips else 0
    weighted_score += 2.0 if crypto_fips else 0
    weighted_score += 1.5 if fips_mode else 0
    weighted_score += 2.0 if encryption_ok else 0
    total_weight = sum(check_weights.values())

    health_score = (weighted_score / total_weight) * 100

    # Count passed checks
    checks_list = [kernel_fips, python_fips, crypto_fips, fips_mode, encryption_ok]
    passed_checks = sum(1 for c in checks_list if c)
    total_checks = len(checks_list)

    # Determine status
    if health_score == 100:
        status = "HEALTHY"
        exit_code = 0
    elif health_score >= 80:
        status = "WARNING"
        exit_code = 1
    else:
        status = "CRITICAL"
        exit_code = 2

    report = {
        "timestamp": timestamp,
        "status": status,
        "health_score": health_score,
        "checks": {
            "kernel_fips": kernel_fips,
            "python_fips": python_fips,
            "cryptography_fips": crypto_fips,
            "pbx_fips_mode": fips_mode,
            "pbx_enforce_fips": enforce_fips,
            "encryption_operations": encryption_ok,
        },
        "summary": {"passed": passed_checks, "total": total_checks},
    }

    return report, exit_code


def print_report(report):
    """Print human-readable report"""
    print("\n" + "=" * 60)
    print("FIPS HEALTH CHECK REPORT")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Status: {report['status']}")
    print(f"Health Score: {report['health_score']:.1f}%")
    print()

    print("Checks:")
    for check, passed in report["checks"].items():
        status = "✓ PASS" if passed else "✗ FAIL"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"
        check_name = check.replace("_", " ").title()
        print(f"  {color}{status}{reset} - {check_name}")

    print()
    print(f"Summary: {report['summary']['passed']}/{report['summary']['total']} checks passed")
    print("=" * 60 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="FIPS Health Check")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--quiet", action="store_true", help="Suppress output (use exit code only)")
    args = parser.parse_args()

    try:
        report, exit_code = generate_health_report()

        if args.json:
            print(json.dumps(report, indent=2))
        elif not args.quiet:
            print_report(report)

        return exit_code

    except Exception as e:
        if not args.quiet:
            print(f"Error during health check: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
