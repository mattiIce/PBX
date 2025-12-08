#!/usr/bin/env python3
"""
Test Runner for PBX System
Runs all tests and logs failures to test_failures.log
"""
import sys
import os
import subprocess
import datetime
from pathlib import Path

# Test directory
TESTS_DIR = Path(__file__).parent / "tests"
LOG_FILE = Path(__file__).parent / "test_failures.log"


def run_test_file(test_file):
    """
    Run a single test file and capture output
    Returns: (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(TESTS_DIR.parent)
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Test timed out after 60 seconds"
    except Exception as e:
        return False, "", f"Error running test: {str(e)}"


def get_all_test_files():
    """Get all test files from the tests directory"""
    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    return test_files


def run_all_tests():
    """
    Run all tests and collect failures
    Returns: (total, passed, failed, failures_dict)
    """
    test_files = get_all_test_files()
    
    print("=" * 70)
    print(f"Running {len(test_files)} test files...")
    print("=" * 70)
    print()
    
    total = 0
    passed = 0
    failed = 0
    failures = {}
    
    for test_file in test_files:
        test_name = test_file.name
        print(f"Running {test_name}...", end=" ", flush=True)
        
        success, stdout, stderr = run_test_file(test_file)
        total += 1
        
        if success:
            print("✓ PASSED")
            passed += 1
        else:
            print("✗ FAILED")
            failed += 1
            failures[test_name] = {
                'stdout': stdout,
                'stderr': stderr
            }
    
    print()
    print("=" * 70)
    print(f"Results: {passed}/{total} passed, {failed}/{total} failed")
    print("=" * 70)
    
    return total, passed, failed, failures


def write_failures_log(total, passed, failed, failures):
    """Write test failures to log file"""
    with open(LOG_FILE, 'w') as f:
        # Write header
        f.write("=" * 70 + "\n")
        f.write("PBX System Test Failures Log\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Tests: {total}\n")
        f.write(f"Passed: {passed}\n")
        f.write(f"Failed: {failed}\n")
        f.write("=" * 70 + "\n")
        f.write("\n")
        
        if failed == 0:
            f.write("✅ All tests passed!\n")
        else:
            f.write(f"❌ {failed} test(s) failed:\n\n")
            
            for test_name, output in failures.items():
                f.write("-" * 70 + "\n")
                f.write(f"Test: {test_name}\n")
                f.write("-" * 70 + "\n")
                
                if output['stdout']:
                    f.write("\n=== STDOUT ===\n")
                    f.write(output['stdout'])
                    f.write("\n")
                
                if output['stderr']:
                    f.write("\n=== STDERR ===\n")
                    f.write(output['stderr'])
                    f.write("\n")
                
                f.write("\n")
    
    print(f"\n✓ Failures logged to: {LOG_FILE}")


def commit_log_file():
    """Commit the test failures log file to git"""
    try:
        # Check if git is available and we're in a repo
        subprocess.run(['git', 'status'], capture_output=True, check=True, cwd=str(LOG_FILE.parent))
        
        # Add the log file
        subprocess.run(['git', 'add', LOG_FILE.name], cwd=str(LOG_FILE.parent), check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet', LOG_FILE.name],
            cwd=str(LOG_FILE.parent),
            capture_output=True
        )
        
        if result.returncode != 0:  # There are changes
            # Commit the file
            commit_msg = f"Update test failures log - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=str(LOG_FILE.parent),
                check=True,
                capture_output=True
            )
            print(f"✓ Log file committed to git")
        else:
            print(f"ℹ No changes to commit")
            
    except subprocess.CalledProcessError as e:
        print(f"⚠ Warning: Could not commit log file: {e}")
    except Exception as e:
        print(f"⚠ Warning: Error committing log file: {e}")


def main():
    """Main entry point"""
    # Check if tests directory exists
    if not TESTS_DIR.exists():
        print(f"Error: Tests directory not found: {TESTS_DIR}")
        return 1
    
    # Run all tests
    total, passed, failed, failures = run_all_tests()
    
    # Write failures to log
    write_failures_log(total, passed, failed, failures)
    
    # Commit the log file
    commit_log_file()
    
    # Return exit code based on test results
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
