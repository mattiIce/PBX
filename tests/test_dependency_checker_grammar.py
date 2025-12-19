#!/usr/bin/env python3
"""
Test Dependency Checker Grammar
Tests that the dependency checker uses correct singular/plural forms
"""
import io
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.utils.dependency_checker import print_dependency_report


def capture_output(func):
    """Capture stdout from a function"""
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        func()
        return buffer.getvalue()
    finally:
        sys.stdout = old_stdout


def test_singular_dependency():
    """Test that 1 missing dependency uses singular form"""
    print("=" * 60)
    print("Test: Singular Dependency (count=1)")
    print("=" * 60)

    report = {
        "missing_core": [],
        "missing_optional": [{"package": "test-package", "feature": "Test feature"}],
        "available_optional": [],
    }

    output = capture_output(lambda: print_dependency_report(report, verbose=False))

    # Check that it uses "dependency" (singular) not "dependencies"
    if "1 optional dependency missing" in output:
        print("  ✓ Correct: Uses 'dependency' (singular)")
        return True
    elif "1 optional dependencies missing" in output:
        print("  ✗ FAIL: Uses 'dependencies' (plural) - should be singular!")
        return False
    else:
        print("  ✗ FAIL: Unexpected output format")
        print(f"  Output: {output}")
        return False


def test_plural_dependencies():
    """Test that 2+ missing dependencies use plural form"""
    print("=" * 60)
    print("Test: Plural Dependencies (count=2)")
    print("=" * 60)

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
        print("  ✓ Correct: Uses 'dependencies' (plural)")
        return True
    elif "2 optional dependency missing" in output:
        print("  ✗ FAIL: Uses 'dependency' (singular) - should be plural!")
        return False
    else:
        print("  ✗ FAIL: Unexpected output format")
        print(f"  Output: {output}")
        return False


def test_zero_dependencies():
    """Test that 0 missing dependencies shows no warning"""
    print("=" * 60)
    print("Test: Zero Dependencies (count=0)")
    print("=" * 60)

    report = {"missing_core": [], "missing_optional": [], "available_optional": []}

    output = capture_output(lambda: print_dependency_report(report, verbose=False))

    # Should not show any warning about missing optional dependencies
    if "optional" not in output.lower() or "missing" not in output.lower():
        print("  ✓ Correct: No warning displayed")
        return True
    else:
        print("  ✗ FAIL: Warning displayed when there are no missing dependencies")
        print(f"  Output: {output}")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("=" * 60)
    print("Dependency Checker Grammar Tests")
    print("=" * 60)
    print()

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
            print()
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            failed += 1
            print()

    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print()

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
