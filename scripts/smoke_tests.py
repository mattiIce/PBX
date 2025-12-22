#!/usr/bin/env python3
"""
Production smoke tests - quick validation after deployment.

These tests verify that core functionality is working after deployment
without running the full test suite. Designed to run quickly (< 2 minutes).
"""

import json
import os
import sys
import time
import urllib.request
from typing import Tuple, Dict, Any


class SmokeTestRunner:
    """Run smoke tests against a deployed PBX system."""

    def __init__(self, api_url: str = "http://localhost:8080"):
        """
        Initialize smoke test runner.

        Args:
            api_url: Base URL for PBX API
        """
        self.api_url = api_url.rstrip("/")
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def run_all_tests(self) -> bool:
        """
        Run all smoke tests.

        Returns:
            True if all tests passed, False otherwise
        """
        print("=" * 70)
        print("PBX Production Smoke Tests")
        print("=" * 70)
        print(f"API URL: {self.api_url}")
        print()

        # Critical tests (must pass)
        critical_tests = [
            ("Health Check", self.test_health_check),
            ("Liveness Probe", self.test_liveness),
            ("Readiness Probe", self.test_readiness),
            ("API Status", self.test_api_status),
        ]

        # Important tests (should pass)
        important_tests = [
            ("Detailed Health", self.test_detailed_health),
            ("Metrics Endpoint", self.test_metrics),
            ("Extensions API", self.test_extensions),
            ("Configuration API", self.test_configuration),
        ]

        # Optional tests (nice to have)
        optional_tests = [
            ("Statistics API", self.test_statistics),
            ("QoS Monitoring", self.test_qos),
        ]

        # Run critical tests
        print("CRITICAL TESTS (must pass):")
        print("-" * 70)
        critical_passed = self._run_test_suite(critical_tests)
        print()

        # Run important tests
        print("IMPORTANT TESTS (should pass):")
        print("-" * 70)
        self._run_test_suite(important_tests)
        print()

        # Run optional tests
        print("OPTIONAL TESTS (nice to have):")
        print("-" * 70)
        self._run_test_suite(optional_tests)
        print()

        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        total = self.passed + self.failed
        print(f"Passed:   {self.passed}/{total} tests")
        print(f"Failed:   {self.failed}/{total} tests")
        print(f"Warnings: {self.warnings}")
        print()

        if self.failed == 0:
            print("✓ All smoke tests passed!")
            return True
        else:
            print("✗ Some smoke tests failed")
            if not critical_passed:
                print("  CRITICAL: Core functionality is broken!")
            return False

    def _run_test_suite(self, tests: list) -> bool:
        """Run a suite of tests."""
        all_passed = True

        for name, test_func in tests:
            try:
                passed, message = test_func()

                if passed:
                    print(f"  ✓ {name}")
                    self.passed += 1
                else:
                    print(f"  ✗ {name}: {message}")
                    self.failed += 1
                    all_passed = False
            except Exception as e:
                print(f"  ✗ {name}: ERROR - {e}")
                self.failed += 1
                all_passed = False

        return all_passed

    def test_health_check(self) -> Tuple[bool, str]:
        """Test /health endpoint."""
        try:
            status, data = self._get_json("/health")

            if status != 200:
                return False, f"HTTP {status}"

            if data.get("status") != "ready":
                return False, f"Status is {data.get('status')}, expected 'ready'"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_liveness(self) -> Tuple[bool, str]:
        """Test /live endpoint."""
        try:
            status, data = self._get_json("/live")

            if status != 200:
                return False, f"HTTP {status}"

            if data.get("status") != "alive":
                return False, f"Status is {data.get('status')}, expected 'alive'"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_readiness(self) -> Tuple[bool, str]:
        """Test /ready endpoint."""
        try:
            status, data = self._get_json("/ready")

            if status != 200:
                return False, f"HTTP {status}"

            if data.get("status") != "ready":
                # Get details about what's not ready
                checks = data.get("checks", {})
                failed_checks = [k for k, v in checks.items() if v.get("status") != "operational"]
                return False, f"Not ready. Failed checks: {', '.join(failed_checks)}"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_api_status(self) -> Tuple[bool, str]:
        """Test /api/status endpoint."""
        try:
            status, data = self._get_json("/api/status")

            if status != 200:
                return False, f"HTTP {status}"

            # Check for expected fields
            required_fields = ["registered_extensions", "active_calls"]
            missing = [f for f in required_fields if f not in data]

            if missing:
                return False, f"Missing fields: {', '.join(missing)}"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_detailed_health(self) -> Tuple[bool, str]:
        """Test /api/health/detailed endpoint."""
        try:
            status, data = self._get_json("/api/health/detailed")

            if status != 200:
                return False, f"HTTP {status}"

            overall = data.get("overall_status")
            if overall != "healthy":
                return False, f"Overall status is '{overall}'"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_metrics(self) -> Tuple[bool, str]:
        """Test /metrics endpoint (Prometheus format)."""
        try:
            status, text = self._get_text("/metrics")

            if status != 200:
                return False, f"HTTP {status}"

            if "pbx_health" not in text:
                return False, "Missing pbx_health metric"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_extensions(self) -> Tuple[bool, str]:
        """Test /api/extensions endpoint."""
        try:
            # Note: This endpoint requires authentication in production
            # For smoke test, we just verify it returns 401 (not 500)
            status, data = self._get_json("/api/extensions")

            # Either 200 (if auth disabled) or 401 (auth required)
            if status not in [200, 401]:
                return False, f"Unexpected HTTP {status}"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_configuration(self) -> Tuple[bool, str]:
        """Test /api/config endpoint."""
        try:
            status, data = self._get_json("/api/config")

            if status != 200:
                return False, f"HTTP {status}"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_statistics(self) -> Tuple[bool, str]:
        """Test /api/statistics endpoint."""
        try:
            status, data = self._get_json("/api/statistics")

            if status != 200:
                return False, f"HTTP {status}"

            return True, ""

        except Exception as e:
            return False, str(e)

    def test_qos(self) -> Tuple[bool, str]:
        """Test QoS monitoring endpoints."""
        try:
            status, data = self._get_json("/api/qos/statistics")

            if status != 200:
                return False, f"HTTP {status}"

            return True, ""

        except Exception as e:
            return False, str(e)

    def _get_json(self, path: str) -> Tuple[int, Dict[str, Any]]:
        """
        Make GET request and parse JSON response.

        Args:
            path: API path

        Returns:
            Tuple of (status_code, parsed_json)
        """
        url = f"{self.api_url}{path}"
        req = urllib.request.Request(url, method="GET")

        try:
            with urllib.request.urlopen(
                req, timeout=5
            ) as response:  # nosec B310 - Controlled URL for smoke tests
                data = json.loads(response.read().decode())
                return response.status, data
        except urllib.error.HTTPError as e:
            # Still try to parse error response
            try:
                data = json.loads(e.read().decode())
                return e.code, data
            except Exception:
                return e.code, {"error": str(e)}
        except urllib.error.URLError as e:
            raise Exception(f"Connection failed: {e}")

    def _get_text(self, path: str) -> Tuple[int, str]:
        """
        Make GET request and return text response.

        Args:
            path: API path

        Returns:
            Tuple of (status_code, text_content)
        """
        url = f"{self.api_url}{path}"
        req = urllib.request.Request(url, method="GET")

        try:
            with urllib.request.urlopen(
                req, timeout=5
            ) as response:  # nosec B310 - Controlled URL for smoke tests
                text = response.read().decode()
                return response.status, text
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()
        except urllib.error.URLError as e:
            raise Exception(f"Connection failed: {e}")


def main():
    """Main entry point."""
    # Check if API URL is provided
    api_url = os.environ.get("PBX_API_URL", "http://localhost:8080")

    if len(sys.argv) > 1:
        api_url = sys.argv[1]

    # Run smoke tests
    runner = SmokeTestRunner(api_url)

    # Wait a moment for service to be ready
    print("Waiting for service to be ready...")
    time.sleep(2)

    success = runner.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
