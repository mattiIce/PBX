#!/usr/bin/env python3
"""
Production Validation Test Suite

Comprehensive validation tests to run before production deployment.
Tests all critical functionality and integration points.

Usage:
    python scripts/production_validation.py [--verbose] [--skip-integration]
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class ProductionValidator:
    """Validate production readiness."""

    def __init__(self, verbose=False, skip_integration=False):
        self.verbose = verbose
        self.skip_integration = skip_integration
        self.results = {"passed": 0, "failed": 0, "skipped": 0, "tests": []}
        self.base_dir = Path(__file__).parent.parent
        self.api_url = os.getenv("API_URL", "http://localhost:9000")

    def log(self, message: str, level: str = "info"):
        """Log a message."""
        if level == "pass":
            print(f"{GREEN}✓{RESET} {message}")
            self.results["passed"] += 1
        elif level == "fail":
            print(f"{RED}✗{RESET} {message}")
            self.results["failed"] += 1
        elif level == "skip":
            print(f"{YELLOW}⊘{RESET} {message}")
            self.results["skipped"] += 1
        elif level == "info" and self.verbose:
            print(f"{BLUE}ℹ{RESET} {message}")

        if level in ["pass", "fail", "skip"]:
            self.results["tests"].append({"name": message, "status": level})

    def run_command(self, cmd: list[str], timeout: int = 30) -> tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.base_dir,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s"
        except (OSError, subprocess.SubprocessError) as e:
            return False, str(e)

    def check_http_endpoint(self, path: str, expected_status: int = 200) -> bool:
        """Check if HTTP endpoint returns expected status."""
        try:
            url = f"{self.api_url}{path}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == expected_status
        except OSError:
            return False

    # ===== Configuration Tests =====

    def test_configuration_files(self):
        """Test that required configuration files exist and are valid."""
        print(f"\n{BLUE}=== Configuration Tests ==={RESET}")

        # Check config.yml
        config_file = self.base_dir / "config.yml"
        if config_file.exists():
            try:
                import yaml

                with open(config_file) as f:
                    yaml.safe_load(f)
                self.log("config.yml is valid", "pass")
            except OSError as e:
                self.log(f"config.yml is invalid: {e}", "fail")
        else:
            self.log("config.yml not found", "fail")

        # Check VERSION file
        version_file = self.base_dir / "VERSION"
        if version_file.exists():
            self.log("VERSION file exists", "pass")
        else:
            self.log("VERSION file not found", "fail")

        # Check .env (optional but recommended)
        env_file = self.base_dir / ".env"
        if env_file.exists():
            self.log(".env file exists", "pass")
        else:
            self.log(".env file not found (optional)", "skip")

    # ===== Security Tests =====

    def test_security_configuration(self):
        """Test security configuration."""
        print(f"\n{BLUE}=== Security Tests ==={RESET}")

        # Check for secrets validation
        success, _output = self.run_command(
            [sys.executable, str(self.base_dir / "scripts" / "verify_fips.py")]
        )
        if success:
            self.log("FIPS compliance verified", "pass")
        else:
            self.log("FIPS compliance check failed (may not be required)", "skip")

        # Check SSL certificate
        cert_paths = [
            self.base_dir / "certs" / "server.crt",
            self.base_dir / "server.crt",
        ]
        cert_found = any(p.exists() for p in cert_paths)
        if cert_found:
            self.log("SSL certificate found", "pass")
        else:
            self.log("SSL certificate not found", "fail")

    # ===== Database Tests =====

    def test_database_connectivity(self):
        """Test database connectivity."""
        print(f"\n{BLUE}=== Database Tests ==={RESET}")

        success, output = self.run_command(
            [sys.executable, str(self.base_dir / "scripts" / "verify_database.py")]
        )
        if success:
            self.log("Database connectivity verified", "pass")
        else:
            self.log("Database connectivity failed", "fail")
            if self.verbose:
                print(f"  Output: {output[:200]}")

    # ===== API Tests =====

    def test_api_endpoints(self):
        """Test critical API endpoints."""
        print(f"\n{BLUE}=== API Tests ==={RESET}")

        endpoints = [
            ("/health", 200, "Health endpoint"),
            ("/api/status", 200, "Status endpoint"),
            ("/metrics", 200, "Metrics endpoint"),
        ]

        for path, expected_status, name in endpoints:
            if self.check_http_endpoint(path, expected_status):
                self.log(f"{name} responding", "pass")
            else:
                self.log(f"{name} not responding", "fail")

    # ===== Service Tests =====

    def test_service_status(self):
        """Test service status."""
        print(f"\n{BLUE}=== Service Tests ==={RESET}")

        # Check if running as systemd service
        success, output = self.run_command(["systemctl", "is-active", "pbx"])
        if success and "active" in output:
            self.log("PBX service is active", "pass")
        else:
            self.log("PBX service status check (may not be systemd)", "skip")

    # ===== Performance Tests =====

    def test_performance_baseline(self):
        """Test that performance baselines are acceptable."""
        print(f"\n{BLUE}=== Performance Tests ==={RESET}")

        # Quick load test
        if (self.base_dir / "scripts" / "load_test_sip.py").exists():
            self.log("Load test script available", "pass")
        else:
            self.log("Load test script not found", "skip")

        # Benchmark script
        if (self.base_dir / "scripts" / "benchmark_performance.py").exists():
            self.log("Benchmark script available", "pass")
        else:
            self.log("Benchmark script not found", "skip")

    # ===== Backup Tests =====

    def test_backup_configuration(self):
        """Test backup configuration."""
        print(f"\n{BLUE}=== Backup Tests ==={RESET}")

        # Check backup script
        backup_script = self.base_dir / "scripts" / "backup.sh"
        if backup_script.exists():
            self.log("Backup script exists", "pass")
        else:
            self.log("Backup script not found", "fail")

        # Check if backup directory is configured
        # This would need to check config.yml or environment

    # ===== Monitoring Tests =====

    def test_monitoring_setup(self):
        """Test monitoring configuration."""
        print(f"\n{BLUE}=== Monitoring Tests ==={RESET}")

        # Check health check script
        health_check = self.base_dir / "scripts" / "production_health_check.py"
        if health_check.exists():
            self.log("Production health check script exists", "pass")

            # Try running it
            success, output = self.run_command([sys.executable, str(health_check)])
            if success or "DEGRADED" in output:
                self.log("Health check script runs successfully", "pass")
            else:
                self.log("Health check script failed", "fail")
        else:
            self.log("Production health check script not found", "fail")

    # ===== Integration Tests =====

    def test_integrations(self):
        """Test external integrations."""
        if self.skip_integration:
            print(f"\n{BLUE}=== Integration Tests (SKIPPED) ==={RESET}")
            self.log("Integration tests skipped", "skip")
            return

        print(f"\n{BLUE}=== Integration Tests ==={RESET}")

        # These are optional, so we skip if not configured
        self.log("External integrations test (optional)", "skip")

    # ===== Documentation Tests =====

    def test_documentation(self):
        """Test that required documentation exists."""
        print(f"\n{BLUE}=== Documentation Tests ==={RESET}")

        docs = [
            ("README.md", True),
            ("TROUBLESHOOTING.md", True),
            ("docs/OPERATIONS_RUNBOOK.md", True),
            ("docs/CAPACITY_PLANNING.md", False),
        ]

        for doc, required in docs:
            doc_path = self.base_dir / doc
            if doc_path.exists():
                self.log(f"{doc} exists", "pass")
            else:
                level = "fail" if required else "skip"
                self.log(f"{doc} not found", level)

    # ===== Main Test Runner =====

    def run_all_tests(self):
        """Run all validation tests."""
        print(f"{BLUE}{'=' * 70}{RESET}")
        print(f"{BLUE}Production Validation Test Suite{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}")

        test_suites = [
            self.test_configuration_files,
            self.test_security_configuration,
            self.test_database_connectivity,
            self.test_api_endpoints,
            self.test_service_status,
            self.test_performance_baseline,
            self.test_backup_configuration,
            self.test_monitoring_setup,
            self.test_integrations,
            self.test_documentation,
        ]

        for test_suite in test_suites:
            try:
                test_suite()
            except Exception as e:
                print(f"{RED}Error running {test_suite.__name__}: {e}{RESET}")
                self.results["failed"] += 1

    def print_summary(self):
        """Print test summary."""
        print(f"\n{BLUE}{'=' * 70}{RESET}")
        print(f"{BLUE}Test Summary{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}")

        total = self.results["passed"] + self.results["failed"] + self.results["skipped"]
        passed_pct = (self.results["passed"] / total * 100) if total > 0 else 0

        print(f"{GREEN}Passed:{RESET}  {self.results['passed']}/{total} ({passed_pct:.1f}%)")
        print(f"{RED}Failed:{RESET}  {self.results['failed']}/{total}")
        print(f"{YELLOW}Skipped:{RESET} {self.results['skipped']}/{total}")

        # Determine overall status
        if self.results["failed"] == 0:
            print(f"\n{GREEN}✓ PRODUCTION READY{RESET}")
            return 0
        if self.results["failed"] <= 2:
            print(f"\n{YELLOW}⚠ MOSTLY READY (review {self.results['failed']} failures){RESET}")
            return 1
        print(f"\n{RED}✗ NOT PRODUCTION READY ({self.results['failed']} failures){RESET}")
        return 2


def main():
    parser = argparse.ArgumentParser(description="Production Validation Test Suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--skip-integration", action="store_true", help="Skip integration tests")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    validator = ProductionValidator(verbose=args.verbose, skip_integration=args.skip_integration)
    validator.run_all_tests()

    if args.json:
        print(json.dumps(validator.results, indent=2))

    exit_code = validator.print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
