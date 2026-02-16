#!/usr/bin/env python3
"""
Comprehensive Security Compliance Checker
Performs full security audit for FIPS 140-2 and SOC 2 Type 2 compliance

This script provides:
- FIPS 140-2 compliance verification
- SOC 2 Type 2 controls audit
- Cryptographic algorithm validation
- Security configuration review
- Detailed compliance reporting
"""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class SecurityComplianceChecker:
    """Comprehensive security compliance checker"""

    def __init__(self, verbose: bool = True, json_output: bool = False) -> None:
        """
        Initialize security compliance checker

        Args:
            verbose: Print detailed output
            json_output: Output results as JSON
        """
        self.verbose = verbose
        self.json_output = json_output
        self.results = {
            "timestamp": datetime.now(UTC).isoformat(),
            "fips": {},
            "soc2": {},
            "security": {},
            "overall": {},
        }

    def print_section(self, title: str) -> None:
        """Print section header"""
        if not self.verbose or self.json_output:
            return
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_status(self, test_name: str, passed: bool, details: str = "") -> None:
        """Print test status with color coding"""
        if not self.verbose or self.json_output:
            return

        status = "✓ PASS" if passed else "✗ FAIL"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{status}{reset} - {test_name}")
        if details:
            for line in details.split("\n"):
                if line.strip():
                    print(f"       {line}")

    def check_fips_compliance(self) -> dict:
        """Check FIPS 140-2 compliance"""
        self.print_section("FIPS 140-2 Compliance Check")

        fips_results = {"compliant": True, "checks": {}, "issues": []}

        # Check 1: Kernel FIPS mode
        try:
            with Path("/proc/sys/crypto/fips_enabled").open() as f:
                kernel_fips = f.read().strip() == "1"
                fips_results["checks"]["kernel_fips"] = kernel_fips
                self.print_status(
                    "Kernel FIPS mode",
                    kernel_fips,
                    f"Status: {'Enabled' if kernel_fips else 'Disabled'}",
                )
                if not kernel_fips:
                    fips_results["compliant"] = False
                    fips_results["issues"].append(
                        "Kernel FIPS mode not enabled. Run: sudo scripts/enable_fips_ubuntu.sh"
                    )
        except FileNotFoundError:
            fips_results["checks"]["kernel_fips"] = False
            fips_results["compliant"] = False
            fips_results["issues"].append("FIPS kernel module not available")
            self.print_status("Kernel FIPS mode", False, "Module not found")

        # Check 2: OpenSSL FIPS provider
        try:
            result = subprocess.run(
                ["openssl", "list", "-providers"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            openssl_fips = "fips" in result.stdout.lower()
            fips_results["checks"]["openssl_fips"] = openssl_fips
            self.print_status(
                "OpenSSL FIPS provider",
                openssl_fips,
                "FIPS provider active" if openssl_fips else "No FIPS provider",
            )
            if not openssl_fips:
                fips_results["issues"].append("OpenSSL FIPS provider not available")
        except (KeyError, OSError, TypeError, ValueError, subprocess.SubprocessError) as e:
            fips_results["checks"]["openssl_fips"] = False
            self.print_status("OpenSSL FIPS provider", False, str(e))

        # Check 3: Cryptography library
        try:
            from pbx.utils.encryption import CRYPTO_AVAILABLE

            fips_results["checks"]["crypto_library"] = CRYPTO_AVAILABLE
            self.print_status(
                "Cryptography library",
                CRYPTO_AVAILABLE,
                "Installed and available" if CRYPTO_AVAILABLE else "Not installed",
            )

            if not CRYPTO_AVAILABLE:
                fips_results["compliant"] = False
                fips_results["issues"].append(
                    "Cryptography library required. Install: pip install cryptography>=41.0.0"
                )
        except (KeyError, TypeError, ValueError) as e:
            fips_results["checks"]["crypto_library"] = False
            fips_results["compliant"] = False
            self.print_status("Cryptography library", False, str(e))

        # Check 4: PBX FIPS configuration
        try:
            from pbx.utils.config import Config

            config = Config("config.yml")
            fips_mode = config.get("security.fips_mode", False)
            enforce_fips = config.get("security.enforce_fips", False)

            fips_results["checks"]["pbx_fips_mode"] = fips_mode
            fips_results["checks"]["pbx_enforce_fips"] = enforce_fips

            self.print_status("PBX FIPS mode", fips_mode, f"security.fips_mode = {fips_mode}")

            if not fips_mode:
                fips_results["compliant"] = False
                fips_results["issues"].append(
                    "FIPS mode not enabled in config.yml. Set security.fips_mode: true"
                )
        except (KeyError, TypeError, ValueError) as e:
            fips_results["checks"]["pbx_fips_mode"] = False
            fips_results["compliant"] = False
            self.print_status("PBX FIPS configuration", False, str(e))

        # Check 5: FIPS-approved algorithms
        algorithms_ok = True
        try:
            from pbx.utils.encryption import get_encryption

            enc = get_encryption(fips_mode=True, enforce_fips=False)

            # Test PBKDF2-HMAC-SHA256
            test_password = "TestPassword123!"
            hash_result, salt = enc.hash_password(test_password)
            verify_result = enc.verify_password(test_password, hash_result, salt)

            if not verify_result:
                algorithms_ok = False
                fips_results["issues"].append("Password hashing algorithm test failed")

            fips_results["checks"]["pbkdf2_sha256"] = verify_result
            self.print_status(
                "PBKDF2-HMAC-SHA256 (600K iterations)", verify_result, "Password hashing algorithm"
            )

            # Test SHA-256
            hash_data = enc.hash_data("test")
            sha256_ok = len(hash_data) == 64  # SHA-256 produces 64 hex characters
            fips_results["checks"]["sha256"] = sha256_ok
            self.print_status("SHA-256 hashing", sha256_ok)

            if not sha256_ok:
                algorithms_ok = False
                fips_results["issues"].append("SHA-256 algorithm test failed")

            # Test AES-256-GCM (if crypto available)
            if CRYPTO_AVAILABLE:
                try:
                    key, _key_salt = enc.derive_key("encryption_password", key_length=32)
                    encrypted, nonce, tag = enc.encrypt_data("test data", key)
                    decrypted = enc.decrypt_data(encrypted, nonce, tag, key)
                    aes_ok = decrypted.decode() == "test data"

                    fips_results["checks"]["aes_256_gcm"] = aes_ok
                    self.print_status("AES-256-GCM encryption", aes_ok)

                    if not aes_ok:
                        algorithms_ok = False
                        fips_results["issues"].append("AES-256-GCM algorithm test failed")
                except (KeyError, TypeError, ValueError) as e:
                    fips_results["checks"]["aes_256_gcm"] = False
                    self.print_status("AES-256-GCM encryption", False, str(e))
                    algorithms_ok = False

        except (KeyError, TypeError, ValueError) as e:
            algorithms_ok = False
            fips_results["issues"].append(f"Algorithm testing failed: {e}")
            self.print_status("FIPS algorithms", False, str(e))

        if not algorithms_ok:
            fips_results["compliant"] = False

        self.results["fips"] = fips_results
        return fips_results

    def check_soc2_compliance(self) -> dict:
        """Check SOC 2 Type 2 compliance"""
        self.print_section("SOC 2 Type 2 Compliance Check")

        soc2_results = {"compliant": True, "controls": {}, "summary": {}, "issues": []}

        try:
            from pbx.features.compliance_framework import SOC2ComplianceEngine
            from pbx.utils.config import Config
            from pbx.utils.database import DatabaseBackend
            from pbx.utils.migrations import MigrationManager, register_all_migrations

            config = Config("config.yml")
            db = DatabaseBackend(config)

            # Connect to database
            if not db.connect():
                soc2_results["issues"].append(
                    "Database connection failed - cannot verify SOC 2 controls"
                )
                soc2_results["compliant"] = False
                self.print_status("Database connection", False, "Failed to connect to database")
                self.results["soc2"] = soc2_results
                return soc2_results

            # Run migrations to ensure tables exist
            migration_manager = MigrationManager(db)
            register_all_migrations(migration_manager)
            migration_manager.apply_migrations()

            engine = SOC2ComplianceEngine(db, config.config)

            # Get all controls
            controls = engine.get_all_controls()

            if not controls:
                soc2_results["issues"].append("No SOC 2 controls found in database")
                soc2_results["compliant"] = False

            # Analyze controls
            total = len(controls)
            implemented = sum(
                1 for c in controls if c.get("implementation_status") == "implemented"
            )
            pending = sum(1 for c in controls if c.get("implementation_status") == "pending")
            tested = sum(1 for c in controls if c.get("last_tested") is not None)

            soc2_results["summary"] = {
                "total_controls": total,
                "implemented": implemented,
                "pending": pending,
                "tested": tested,
                "compliance_percentage": (implemented / total * 100) if total > 0 else 0,
            }

            # Check by category
            categories = {}
            for control in controls:
                cat = control.get("control_category", "Unknown")
                if cat not in categories:
                    categories[cat] = {"total": 0, "implemented": 0}
                categories[cat]["total"] += 1
                if control.get("implementation_status") == "implemented":
                    categories[cat]["implemented"] += 1

            soc2_results["controls"] = categories

            # Print summary
            self.print_status("SOC 2 Controls Total", total > 0, f"Total: {total} controls")

            self.print_status(
                "Implementation Status",
                implemented == total,
                f"Implemented: {implemented}/{total} ({implemented / total * 100 if total > 0 else 0:.1f}%)",
            )

            self.print_status(
                "Testing Status",
                tested >= implemented * 0.8,  # At least 80% of implemented should be tested
                f"Tested: {tested}/{implemented} implemented controls",
            )

            # Check each category
            for category, stats in categories.items():
                category_ok = stats["implemented"] == stats["total"]
                self.print_status(
                    f"{category} Controls",
                    category_ok,
                    f"{stats['implemented']}/{stats['total']} implemented",
                )
                if not category_ok:
                    soc2_results["issues"].append(
                        f"{category}: {stats['total'] - stats['implemented']} controls not implemented"
                    )

            # Overall compliance check
            if implemented < total:
                soc2_results["compliant"] = False
                soc2_results["issues"].append(f"{total - implemented} controls not yet implemented")

            if tested < implemented * 0.8:
                soc2_results["compliant"] = False
                soc2_results["issues"].append(
                    "Less than 80% of implemented controls have been tested"
                )

        except (KeyError, TypeError, ValueError) as e:
            soc2_results["compliant"] = False
            soc2_results["issues"].append(f"SOC 2 check failed: {e}")
            self.print_status("SOC 2 Compliance Engine", False, str(e))

        self.results["soc2"] = soc2_results
        return soc2_results

    def check_security_configuration(self) -> dict:
        """Check security configuration and best practices"""
        self.print_section("Security Configuration Review")

        security_results = {"compliant": True, "checks": {}, "issues": []}

        try:
            from pbx.utils.config import Config

            config = Config("config.yml")

            # Check 1: Authentication required
            require_auth = config.get("security.require_authentication", False)
            security_results["checks"]["require_authentication"] = require_auth
            self.print_status(
                "Authentication required", require_auth, "security.require_authentication"
            )
            if not require_auth:
                security_results["issues"].append("Authentication should be required")

            # Check 2: Password policy
            min_password_length = config.get("security.password.min_length", 0)
            password_policy_ok = min_password_length >= 12
            security_results["checks"]["password_min_length"] = password_policy_ok
            self.print_status(
                "Password minimum length >= 12",
                password_policy_ok,
                f"Current: {min_password_length}",
            )
            if not password_policy_ok:
                security_results["compliant"] = False
                security_results["issues"].append(
                    f"Password minimum length too short: {min_password_length} (should be >= 12)"
                )

            # Check 3: Failed login protection
            max_failed = config.get("security.max_failed_attempts", 999)
            failed_login_ok = max_failed <= 10
            security_results["checks"]["max_failed_attempts"] = failed_login_ok
            self.print_status(
                "Failed login limit configured", failed_login_ok, f"Max attempts: {max_failed}"
            )
            if not failed_login_ok:
                security_results["issues"].append(
                    "Max failed attempts should be <= 10 for security"
                )

            # Check 4: TLS/SIPS enabled (recommended)
            enable_tls = config.get("security.enable_tls", False)
            security_results["checks"]["tls_enabled"] = enable_tls
            self.print_status(
                "TLS/SIPS enabled (recommended)", enable_tls, "For encrypted SIP signaling"
            )
            if not enable_tls:
                security_results["issues"].append("TLS not enabled - recommended for production")

            # Check 5: SRTP enabled (recommended)
            enable_srtp = config.get("security.enable_srtp", False)
            security_results["checks"]["srtp_enabled"] = enable_srtp
            self.print_status(
                "SRTP enabled (recommended)", enable_srtp, "For encrypted media streams"
            )
            if not enable_srtp:
                security_results["issues"].append("SRTP not enabled - recommended for production")

            # Check 6: API authentication
            api_auth = config.get("api.require_authentication", False)
            security_results["checks"]["api_authentication"] = api_auth
            self.print_status("API authentication enabled", api_auth, "REST API security")
            if not api_auth:
                security_results["issues"].append("API authentication not required - security risk")

        except (KeyError, TypeError, ValueError) as e:
            security_results["compliant"] = False
            security_results["issues"].append(f"Configuration check failed: {e}")
            self.print_status("Security configuration", False, str(e))

        self.results["security"] = security_results
        return security_results

    def generate_compliance_report(self) -> tuple[dict, int]:
        """Generate comprehensive compliance report"""

        # Run all checks
        fips_results = self.check_fips_compliance()
        soc2_results = self.check_soc2_compliance()
        security_results = self.check_security_configuration()

        # Calculate overall compliance
        fips_compliant = fips_results.get("compliant", False)
        soc2_compliant = soc2_results.get("compliant", False)
        security_ok = security_results.get("compliant", False)

        overall_compliant = fips_compliant and soc2_compliant

        # Determine status
        if overall_compliant and security_ok:
            status = "COMPLIANT"
            exit_code = 0
        elif overall_compliant:
            status = "COMPLIANT_WITH_WARNINGS"
            exit_code = 0
        else:
            status = "NON_COMPLIANT"
            exit_code = 1

        # Compile overall results
        self.results["overall"] = {
            "status": status,
            "fips_compliant": fips_compliant,
            "soc2_compliant": soc2_compliant,
            "security_ok": security_ok,
            "exit_code": exit_code,
        }

        return self.results, exit_code

    def print_summary(self) -> None:
        """Print compliance summary"""
        if self.json_output:
            print(json.dumps(self.results, indent=2))
            return

        self.print_section("COMPLIANCE SUMMARY")

        fips_status = (
            "✓ COMPLIANT" if self.results["overall"]["fips_compliant"] else "✗ NON-COMPLIANT"
        )
        soc2_status = (
            "✓ COMPLIANT" if self.results["overall"]["soc2_compliant"] else "✗ NON-COMPLIANT"
        )
        security_status = "✓ OK" if self.results["overall"]["security_ok"] else "⚠ ISSUES"

        fips_color = "\033[92m" if self.results["overall"]["fips_compliant"] else "\033[91m"
        soc2_color = "\033[92m" if self.results["overall"]["soc2_compliant"] else "\033[91m"
        security_color = "\033[92m" if self.results["overall"]["security_ok"] else "\033[93m"
        reset = "\033[0m"

        print(f"\n{fips_color}FIPS 140-2:        {fips_status}{reset}")
        print(f"{soc2_color}SOC 2 Type 2:      {soc2_status}{reset}")
        print(f"{security_color}Security Config:   {security_status}{reset}")

        # Print issues
        all_issues = (
            self.results["fips"].get("issues", [])
            + self.results["soc2"].get("issues", [])
            + self.results["security"].get("issues", [])
        )

        if all_issues:
            print("\n" + "=" * 80)
            print("ISSUES FOUND:")
            print("=" * 80)
            for i, issue in enumerate(all_issues, 1):
                print(f"{i}. {issue}")

        # Overall status
        print("\n" + "=" * 80)
        overall_status = self.results["overall"]["status"]

        if overall_status == "COMPLIANT":
            print("\033[92m✓ OVERALL STATUS: FULLY COMPLIANT\033[0m")
            print("\nThe system meets FIPS 140-2 and SOC 2 Type 2 requirements.")
        elif overall_status == "COMPLIANT_WITH_WARNINGS":
            print("\033[93m⚠ OVERALL STATUS: COMPLIANT WITH WARNINGS\033[0m")
            print("\nCore compliance requirements met, but some best practices need attention.")
        else:
            print("\033[91m✗ OVERALL STATUS: NON-COMPLIANT\033[0m")
            print("\nCritical compliance requirements are not met.")
            print("Please address the issues listed above.")

        print("=" * 80 + "\n")


def main() -> int:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Comprehensive Security Compliance Check (FIPS 140-2 & SOC 2)"
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress detailed output (exit code only)"
    )
    parser.add_argument("--output", type=str, help="Write JSON report to file")

    args = parser.parse_args()

    try:
        checker = SecurityComplianceChecker(verbose=not args.quiet, json_output=args.json)

        results, exit_code = checker.generate_compliance_report()

        if not args.quiet:
            checker.print_summary()

        # Write to file if requested
        if args.output:
            with Path(args.output).open("w") as f:
                json.dump(results, f, indent=2)
            if not args.quiet and not args.json:
                print(f"Report saved to: {args.output}")

        return exit_code

    except KeyboardInterrupt:
        print("\n\nCompliance check cancelled by user")
        return 130
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as e:
        print(f"\n\nError during compliance check: {e}")
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
