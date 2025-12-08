#!/usr/bin/env python3
"""
Test runner utility for PBX system
Discovers and runs all test files in the tests directory
"""
import sys
import os
import importlib.util
import traceback


def run_all_tests(tests_dir="tests"):
    """
    Run all test files in the tests directory
    
    Args:
        tests_dir: Path to the tests directory
        
    Returns:
        Tuple of (total_passed, total_failed, test_results)
    """
    # Get absolute path to tests directory
    if not os.path.isabs(tests_dir):
        tests_dir = os.path.join(os.path.dirname(__file__), '..', '..', tests_dir)
    tests_dir = os.path.abspath(tests_dir)
    
    if not os.path.exists(tests_dir):
        print(f"Error: Tests directory not found: {tests_dir}")
        return 0, 1, []
    
    # Find all test files
    test_files = []
    for filename in sorted(os.listdir(tests_dir)):
        if filename.startswith('test_') and filename.endswith('.py'):
            test_files.append(filename)
    
    if not test_files:
        print(f"No test files found in {tests_dir}")
        return 0, 0, []
    
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
                success = module.run_all_tests()
                
                # Handle return value - should be boolean True for success
                if success is True:
                    print(f"  ✓ {test_file} PASSED")
                    total_passed += 1
                    test_results.append((test_file, True, None))
                else:
                    # Treat any non-True return (False, None, etc.) as failure
                    print(f"  ✗ {test_file} FAILED")
                    total_failed += 1
                    test_results.append((test_file, False, "Tests failed"))
            else:
                print(f"  ⚠ {test_file} has no run_all_tests() function (skipped)")
                total_skipped += 1
                test_results.append((test_file, None, "No run_all_tests function"))
                
        except Exception as e:
            print(f"  ✗ Error running {test_file}: {e}")
            traceback.print_exc()
            total_failed += 1
            test_results.append((test_file, False, str(e)))
        
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
    
    return total_passed, total_failed, test_results


if __name__ == "__main__":
    passed, failed, _ = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
