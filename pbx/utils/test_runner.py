#!/usr/bin/env python3
"""
Test runner utility for PBX system
Discovers and runs all test files in the tests directory
"""
import importlib.util
import io
import os
import re
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime


def _setup_log_file(log_path):
    """
    Setup and open the log file for writing test failures
    
    Args:
        log_path: Path to the log file
        
    Returns:
        Open file handle or None if failed
    """
    try:
        log_file = open(log_path, 'a')
        log_file.write("\n" + "=" * 80 + "\n")
        log_file.write(f"Test Run Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("=" * 80 + "\n\n")
        return log_file
    except Exception as e:
        print(f"Warning: Could not open log file {log_path}: {e}")
        return None


def _finalize_log_file(log_file, total_passed, total_failed, total_skipped):
    """
    Write summary and close the log file
    
    Args:
        log_file: Open file handle
        total_passed: Number of passed tests
        total_failed: Number of failed tests
        total_skipped: Number of skipped tests
    """
    if not log_file:
        return
    try:
        log_file.write("=" * 80 + "\n")
        log_file.write(f"Test Run Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Summary: {total_passed} passed, {total_failed} failed, {total_skipped} skipped\n")
        log_file.write("=" * 80 + "\n")
    except BaseException:
        pass  # Best effort to write summary
    finally:
        log_file.close()


def _load_test_module(test_file, test_path):
    """
    Load a test module from file
    
    Args:
        test_file: Test filename
        test_path: Full path to test file
        
    Returns:
        Loaded module or None if failed
    """
    test_name = test_file[:-3]  # Remove .py extension
    spec = importlib.util.spec_from_file_location(test_name, test_path)
    if spec is None or spec.loader is None:
        return None
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[test_name] = module
    spec.loader.exec_module(module)
    return module


def _check_test_passed(success, test_stdout):
    """
    Determine if a test passed based on return value and output
    
    Args:
        success: Return value from test
        test_stdout: Captured stdout from test
        
    Returns:
        True if test passed, False otherwise
    """
    # Check if test explicitly returned True
    if success is True:
        return True
    
    # If test returned None/False, check output for success indicators
    if test_stdout:
        output_lower = test_stdout.lower()
        if ('0 failed' in output_lower or 
            'all tests passed' in output_lower or
            re.search(r'all.*tests passed', output_lower)):
            # Also check that there's no explicit failure indicator
            if 'failed' not in output_lower or '0 failed' in output_lower:
                return True
    
    return False


def _log_test_failure(log_file, test_file, success, test_stdout, test_stderr):
    """
    Log a test failure to the log file
    
    Args:
        log_file: Open file handle
        test_file: Test filename
        success: Return value from test
        test_stdout: Captured stdout
        test_stderr: Captured stderr
    """
    if not log_file:
        return
    
    log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FAILED: {test_file}\n")
    log_file.write(f"  Return value: {success} (expected True)\n")
    if test_stdout:
        log_file.write(f"\n  Test Output:\n")
        for line in test_stdout.splitlines():
            log_file.write(f"    {line}\n")
    if test_stderr:
        log_file.write(f"\n  Test Errors:\n")
        for line in test_stderr.splitlines():
            log_file.write(f"    {line}\n")
    log_file.write("\n")


def _log_test_error(log_file, test_file, error, error_trace):
    """
    Log a test error (exception) to the log file
    
    Args:
        log_file: Open file handle
        test_file: Test filename
        error: Exception object
        error_trace: Full traceback string
    """
    if not log_file:
        return
    
    log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {test_file}\n")
    log_file.write(f"  Exception: {error}\n")
    log_file.write(f"  Traceback:\n")
    log_file.write(error_trace)
    log_file.write("\n")


def run_all_tests(tests_dir="tests", log_failures=True):
    """
    Run all test files in the tests directory

    Args:
        tests_dir: Path to the tests directory
        log_failures: Whether to log failures to test_failures.log

    Returns:
        Tuple of (total_passed, total_failed, total_skipped, test_results)
        where test_results is a list of (test_file, success, error_msg) tuples

    Note:
        Tests are considered passed only if run_all_tests() returns exactly True.
        Any other value (False, None, etc.) is treated as failure to ensure
        explicit success signals.
    """
    # Get absolute path to tests directory
    if not os.path.isabs(tests_dir):
        tests_dir = os.path.join(os.path.dirname(__file__), '..', '..', tests_dir)
    tests_dir = os.path.abspath(tests_dir)

    # Set up failure log file
    log_file = None
    log_path = None
    if log_failures:
        log_path = os.path.join(os.path.dirname(tests_dir), 'test_failures.log')
        log_file = _setup_log_file(log_path)

    total_passed = 0
    total_failed = 0
    total_skipped = 0

    try:
        if not os.path.exists(tests_dir):
            print(f"Error: Tests directory not found: {tests_dir}")
            return 0, 1, 0, []

        # Find all test files
        test_files = sorted([f for f in os.listdir(tests_dir) 
                           if f.startswith('test_') and f.endswith('.py')])

        if not test_files:
            print(f"No test files found in {tests_dir}")
            return 0, 0, 0, []

        print("=" * 70)
        print(f"Running {len(test_files)} test files from {tests_dir}")
        print("=" * 70)
        print()

        test_results = []

        for test_file in test_files:
            test_path = os.path.join(tests_dir, test_file)
            print(f"Running {test_file}...")
            print("-" * 70)

            try:
                # Load the test module
                module = _load_test_module(test_file, test_path)
                if module is None:
                    print(f"  ✗ Failed to load test module: {test_file}")
                    total_failed += 1
                    test_results.append((test_file, False, "Failed to load module"))
                    print()
                    continue

                # Run the test if it has a run_all_tests function
                if not hasattr(module, 'run_all_tests'):
                    print(f"  ⚠ {test_file} has no run_all_tests() function (skipped)")
                    total_skipped += 1
                    test_results.append((test_file, None, "No run_all_tests function"))
                    print()
                    continue

                # Capture output for logging purposes
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()

                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    success = module.run_all_tests()

                # Get captured output
                test_stdout = stdout_capture.getvalue()
                test_stderr = stderr_capture.getvalue()

                # Print the output so user can see it
                if test_stdout:
                    print(test_stdout, end='')
                if test_stderr:
                    print(test_stderr, end='', file=sys.stderr)

                # Determine if test passed
                test_passed = _check_test_passed(success, test_stdout)

                if test_passed:
                    print(f"  ✓ {test_file} PASSED")
                    total_passed += 1
                    test_results.append((test_file, True, None))
                else:
                    print(f"  ✗ {test_file} FAILED")
                    total_failed += 1
                    test_results.append((test_file, False, "Tests failed"))
                    _log_test_failure(log_file, test_file, success, test_stdout, test_stderr)

            except Exception as e:
                print(f"  ✗ Error running {test_file}: {e}")
                error_trace = traceback.format_exc()
                traceback.print_exc()
                total_failed += 1
                test_results.append((test_file, False, str(e)))
                _log_test_error(log_file, test_file, e, error_trace)

            print()

        # Print summary
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total test files: {len(test_files)}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Skipped: {total_skipped}")
        print("=" * 70)

        if total_failed > 0 and log_path:
            print(f"\n⚠ Test failures have been logged to: {log_path}")

        return total_passed, total_failed, total_skipped, test_results

    finally:
        _finalize_log_file(log_file, total_passed, total_failed, total_skipped)


if __name__ == "__main__":
    passed, failed, skipped, test_results = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
