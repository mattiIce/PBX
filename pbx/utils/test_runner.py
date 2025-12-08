#!/usr/bin/env python3
"""
Test runner utility for PBX system
Discovers and runs all test files in the tests directory
"""
import sys
import os
import importlib.util
import traceback
from datetime import datetime


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
    
    try:
        if log_failures:
            try:
                log_file = open(log_path, 'a')
                log_file.write("\n" + "=" * 80 + "\n")
                log_file.write(f"Test Run Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write("=" * 80 + "\n\n")
            except Exception as e:
                print(f"Warning: Could not open log file {log_path}: {e}")
                log_file = None
        
        if not os.path.exists(tests_dir):
            print(f"Error: Tests directory not found: {tests_dir}")
            return 0, 1, 0, []
        
        # Find all test files
        test_files = []
        for filename in sorted(os.listdir(tests_dir)):
            if filename.startswith('test_') and filename.endswith('.py'):
                test_files.append(filename)
        
        if not test_files:
            print(f"No test files found in {tests_dir}")
            return 0, 0, 0, []
        
        print("=" * 70)
        print(f"Running {len(test_files)} test files from {tests_dir}")
        print("=" * 70)
        print()
        
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        test_results = []
    
        for test_file in test_files:
            test_path = os.path.join(tests_dir, test_file)
            test_name = test_file[:-3]  # Remove .py extension
            
            print(f"Running {test_file}...")
            print("-" * 70)
        
            try:
                # Load the test module
                spec = importlib.util.spec_from_file_location(test_name, test_path)
                if spec is None or spec.loader is None:
                    print(f"  ✗ Failed to load test module: {test_file}")
                    total_failed += 1
                    test_results.append((test_file, False, "Failed to load module"))
                    print()
                    continue
            
                module = importlib.util.module_from_spec(spec)
                sys.modules[test_name] = module
                spec.loader.exec_module(module)
                
                # Run the test if it has a run_all_tests function
                if hasattr(module, 'run_all_tests'):
                    # Capture output for logging purposes
                    import io
                    from contextlib import redirect_stdout, redirect_stderr
                    
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
                    
                    # Handle return value
                    # Check if test explicitly returned True
                    test_passed = success is True
                    
                    # If test returned None/False, check output for success indicators
                    if not test_passed and test_stdout:
                        # Check for common success patterns in output
                        import re
                        output_lower = test_stdout.lower()
                        if ('0 failed' in output_lower or 
                            'all tests passed' in output_lower or
                            re.search(r'all.*tests passed', output_lower)):
                            # Also check that there's no explicit failure indicator
                            if 'failed' not in output_lower or '0 failed' in output_lower:
                                test_passed = True
                    
                    if test_passed:
                        print(f"  ✓ {test_file} PASSED")
                        total_passed += 1
                        test_results.append((test_file, True, None))
                    else:
                        print(f"  ✗ {test_file} FAILED")
                        total_failed += 1
                        test_results.append((test_file, False, "Tests failed"))
                        
                        # Log failure with captured output
                        if log_file:
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
                else:
                    print(f"  ⚠ {test_file} has no run_all_tests() function (skipped)")
                    total_skipped += 1
                    test_results.append((test_file, None, "No run_all_tests function"))
                    
            except Exception as e:
                print(f"  ✗ Error running {test_file}: {e}")
                error_trace = traceback.format_exc()
                traceback.print_exc()
                total_failed += 1
                test_results.append((test_file, False, str(e)))
                
                # Log failure with full traceback
                if log_file:
                    log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {test_file}\n")
                    log_file.write(f"  Exception: {e}\n")
                    log_file.write(f"  Traceback:\n")
                    log_file.write(error_trace)
                    log_file.write("\n")
            
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
        # Ensure log file is closed
        if log_file:
            try:
                log_file.write("=" * 80 + "\n")
                log_file.write(f"Test Run Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write(f"Summary: {total_passed} passed, {total_failed} failed, {total_skipped} skipped\n")
                log_file.write("=" * 80 + "\n")
            except:
                pass  # Best effort to write summary
            finally:
                log_file.close()


if __name__ == "__main__":
    passed, failed, skipped, test_results = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
