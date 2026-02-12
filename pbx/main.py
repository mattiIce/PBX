#!/usr/bin/env python3
"""
PBX server entry point module.

Provides the main() function used by the pbx-server console script
defined in pyproject.toml.
"""
import logging
import sys
import time

# Load .env file BEFORE importing any PBX modules
from pbx.utils.env_loader import load_env_file

load_env_file(".env")

from pbx.core.pbx import PBXCore
from pbx.utils.graceful_shutdown import setup_graceful_shutdown

logger = logging.getLogger(__name__)

# Global state
running = True
pbx = None


def signal_handler(sig, frame):  # pylint: disable=unused-argument
    """Handle shutdown signal"""
    global running
    print("\nShutting down PBX system...")
    running = False
    if pbx:
        pbx.stop()


def main():
    """Main entry point for the PBX server."""
    global running, pbx

    print("=" * 60)
    print("Warden Voip System v1.0.0")
    print("=" * 60)

    # Check dependencies
    print("\nChecking dependencies...")
    try:
        from pbx.utils.dependency_checker import check_and_report

        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        if not check_and_report(verbose=verbose, strict=True):
            print("\n✗ Dependency check failed. Install missing packages and try again.")
            sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not check dependencies: {e}")
        print("Continuing anyway...")

    print("\n" + "=" * 60)
    print("STARTING PBX SERVER")
    print("=" * 60)

    # Security checks
    print("\nPerforming security checks...")
    try:
        from pbx.utils.config import Config
        from pbx.utils.config_validator import validate_config_on_startup
        from pbx.utils.encryption import CRYPTO_AVAILABLE, get_encryption

        config = Config("config.yml")

        print("\nValidating configuration...")
        if not validate_config_on_startup(config.config):
            print("\n✗ Configuration validation failed")
            sys.exit(1)

        fips_mode = config.get("security.fips_mode", True)
        enforce_fips = config.get("security.enforce_fips", True)

        if fips_mode:
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
                print("✓ FIPS 140-2 compliance verified")
                get_encryption(fips_mode=True, enforce_fips=enforce_fips)
        else:
            print("⚠ FIPS 140-2 mode: DISABLED")

    except ImportError as e:
        print(f"\n✗ FIPS Compliance Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Security check failed: {e}")
        sys.exit(1)

    # Start PBX
    try:
        pbx = PBXCore("config.yml")
        shutdown_handler = setup_graceful_shutdown(pbx, timeout=30)
        logger.info("Graceful shutdown handlers configured")

        if pbx.start():
            print("\nPBX system is running...")
            print("Press Ctrl+C to stop\n")

            last_status_time = time.time()
            while running:
                time.sleep(1)
                current_time = time.time()
                if current_time - last_status_time >= 600:
                    status = pbx.get_status()
                    print(
                        f"Status: {status['registered_extensions']} extensions registered, "
                        f"{status['active_calls']} active calls"
                    )
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
