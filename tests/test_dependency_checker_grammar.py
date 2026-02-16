#!/usr/bin/env python3
"""
Test Dependency Checker Grammar
Tests that the dependency checker uses correct singular/plural forms
"""

import io
import sys
from collections.abc import Callable

from pbx.utils.dependency_checker import print_dependency_report


def capture_output(func: Callable[[], None]) -> str:
    """Capture stdout from a function"""
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        func()
        return buffer.getvalue()
    finally:
        sys.stdout = old_stdout


def test_singular_dependency() -> bool:
    """Test that 1 missing dependency uses singular form"""

    report = {
        "missing_core": [],
        "missing_optional": [{"package": "test-package", "feature": "Test feature"}],
        "available_optional": [],
    }

    output = capture_output(lambda: print_dependency_report(report, verbose=False))

    # Check that it uses "dependency" (singular) not "dependencies"
    if "1 optional dependency missing" in output:
        return True
    if "1 optional dependencies missing" in output:
        return False
    return False


def test_plural_dependencies() -> bool:
    """Test that 2+ missing dependencies use plural form"""

    report = {
        "missing_core": [],
        "missing_optional": [
            {"package": "test-package1", "feature": "Test feature 1"},
            {"package": "test-package2", "feature": "Test feature 2"},
        ],
        "available_optional": [],
    }

    output = capture_output(lambda: print_dependency_report(report, verbose=False))

    # Check that it uses "dependencies" (plural)
    if "2 optional dependencies missing" in output:
        return True
    if "2 optional dependency missing" in output:
        return False
    return False


def test_zero_dependencies() -> bool:
    """Test that 0 missing dependencies shows no warning"""

    report = {"missing_core": [], "missing_optional": [], "available_optional": []}

    output = capture_output(lambda: print_dependency_report(report, verbose=False))

    # Should not show any warning about missing optional dependencies
    return bool("optional" not in output.lower() or "missing" not in output.lower())


def main() -> bool:
    """Run all tests"""

    tests = [
        test_zero_dependencies,
        test_singular_dependency,
        test_plural_dependencies,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception:
            import traceback

            traceback.print_exc()
            failed += 1

    return failed == 0
