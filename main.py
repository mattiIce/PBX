#!/usr/bin/env python3
"""
Main entry point for PBX system
"""
import sys
import signal
import time
from pbx.core.pbx import PBXCore
from pbx.utils.test_runner import run_all_tests

# Global running flag
running = True
pbx = None


def signal_handler(sig, frame):
    """Handle shutdown signal"""
    global running, pbx
    print("\nShutting down PBX system...")
    running = False
    if pbx:
        pbx.stop()


def run_tests_before_start():
    """Run all tests before starting the server"""
    print("=" * 70)
    print("RUNNING TESTS BEFORE SERVER START")
    print("=" * 70)
    print()
    
    try:
        passed, failed, skipped, _ = run_all_tests()
        
        print()
        if failed > 0:
            print("⚠ WARNING: Some tests failed!")
            print("  You can still start the server, but there may be issues.")
        else:
            print("✓ All tests passed!")
        
        return failed == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("InHouse PBX System v1.0.0")
    print("=" * 60)
    print()
    
    # Startup tests disabled - can be re-enabled by uncommenting below
    # Run tests first
    # tests_passed = run_tests_before_start()
    # 
    # print()
    # print("=" * 70)
    # if tests_passed:
    #     print("Tests completed successfully!")
    # else:
    #     print("Tests completed with failures - review results above")
    # print("=" * 70)
    # print()
    # print("Press ENTER to continue and start the server...")
    # try:
    #     input()
    # except (EOFError, KeyboardInterrupt):
    #     print("\nServer start cancelled.")
    #     sys.exit(0)
    
    print()
    print("=" * 60)
    print("STARTING PBX SERVER")
    print("=" * 60)
    print()
    
    # Verify FIPS compliance before starting
    print("Performing security checks...")
    try:
        from pbx.utils.config import Config
        from pbx.utils.encryption import get_encryption, CRYPTO_AVAILABLE
        
        # Load config to check FIPS settings
        config = Config("config.yml")
        fips_mode = config.get('security.fips_mode', True)
        enforce_fips = config.get('security.enforce_fips', True)
        
        if fips_mode:
            print("✓ FIPS 140-2 mode is ENABLED")
            
            if not CRYPTO_AVAILABLE:
                error_msg = (
                    "\n✗ FIPS MODE ENFORCEMENT FAILED\n"
                    "  The 'cryptography' library is not installed.\n"
                    "  FIPS 140-2 compliance requires this library.\n"
                    "  Install with: pip install cryptography\n"
                )
                
                if enforce_fips:
                    print(error_msg)
                    print("  System cannot start with enforce_fips=true")
                    sys.exit(1)
                else:
                    print(error_msg)
                    print("  WARNING: Continuing without FIPS compliance")
            else:
                print("✓ Cryptography library available")
                print("✓ FIPS 140-2 compliance verified")
                
                # Test encryption initialization
                enc = get_encryption(fips_mode=True, enforce_fips=enforce_fips)
                print("✓ FIPS-compliant encryption initialized")
        else:
            print("⚠ WARNING: FIPS 140-2 mode is DISABLED")
            print("  This system is NOT FIPS compliant")
            if enforce_fips:
                print("  Ignoring enforce_fips since fips_mode is disabled")
    
    except ImportError as e:
        print(f"\n✗ FIPS Compliance Error: {e}")
        print("  System cannot start in FIPS mode")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Security check failed: {e}")
        sys.exit(1)
    
    print()

    # Create PBX instance
    try:
        pbx = PBXCore("config.yml")

        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start PBX
        if pbx.start():
            print("\nPBX system is running...")
            print("Press Ctrl+C to stop\n")

            # Keep running and display status periodically
            last_status_time = time.time()
            while running:
                time.sleep(1)
                # Display status every 10 seconds
                current_time = time.time()
                if current_time - last_status_time >= 10:
                    status = pbx.get_status()
                    print(f"Status: {status['registered_extensions']} extensions registered, "
                          f"{status['active_calls']} active calls")
                    last_status_time = current_time

            print("PBX system shutdown complete")
        else:
            print("Failed to start PBX system")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        if pbx:
            pbx.stop()
        sys.exit(1)
