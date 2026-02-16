#!/usr/bin/env python3
"""PBX server entry point module.

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


def signal_handler(sig: int, frame: object) -> None:
    """Handle shutdown signal."""
    global running
    logger.info("Shutting down PBX system...")
    running = False
    if pbx:
        pbx.stop()


def main() -> None:
    """Main entry point for the PBX server."""
    global running, pbx

    logger.info("=" * 60)
    logger.info("Warden VoIP System v1.0.0")
    logger.info("=" * 60)

    # Check dependencies
    logger.info("Checking dependencies...")
    try:
        from pbx.utils.dependency_checker import check_and_report

        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        if not check_and_report(verbose=verbose, strict=True):
            logger.error("Dependency check failed. Install missing packages and try again.")
            sys.exit(1)
    except Exception as e:
        logger.warning("Could not check dependencies: %s", e)
        logger.warning("Continuing anyway...")

    logger.info("=" * 60)
    logger.info("STARTING PBX SERVER")
    logger.info("=" * 60)

    # Security checks
    logger.info("Performing security checks...")
    try:
        from pbx.utils.config import Config
        from pbx.utils.config_validator import validate_config_on_startup
        from pbx.utils.encryption import CRYPTO_AVAILABLE, get_encryption

        config = Config("config.yml")

        logger.info("Validating configuration...")
        if not validate_config_on_startup(config.config):
            logger.error("Configuration validation failed")
            sys.exit(1)

        fips_mode = config.get("security.fips_mode", True)
        enforce_fips = config.get("security.enforce_fips", True)

        if fips_mode:
            if not CRYPTO_AVAILABLE:
                error_msg = (
                    "FIPS MODE ENFORCEMENT FAILED: "
                    "The 'cryptography' library is not installed. "
                    "FIPS 140-2 compliance requires this library. "
                    "Install with: pip install cryptography"
                )
                if enforce_fips:
                    logger.error(error_msg)
                    logger.error("System cannot start with enforce_fips=true")
                    sys.exit(1)
                else:
                    logger.warning(error_msg)
                    logger.warning("Continuing without FIPS compliance")
            else:
                logger.info("FIPS 140-2 compliance verified")
                get_encryption(fips_mode=True, enforce_fips=enforce_fips)
        else:
            logger.warning("FIPS 140-2 mode: DISABLED")

    except ImportError as e:
        logger.error("FIPS Compliance Error: %s", e)
        sys.exit(1)
    except (KeyError, TypeError, ValueError) as e:
        logger.error("Security check failed: %s", e)
        sys.exit(1)

    # Start PBX
    try:
        pbx = PBXCore("config.yml")
        setup_graceful_shutdown(pbx, timeout=30)
        logger.info("Graceful shutdown handlers configured")

        if pbx.start():
            logger.info("PBX system is running. Press Ctrl+C to stop.")

            last_status_time = time.time()
            while running:
                time.sleep(1)
                current_time = time.time()
                if current_time - last_status_time >= 600:
                    status = pbx.get_status()
                    logger.info(
                        "Status: %d extensions registered, %d active calls",
                        status["registered_extensions"],
                        status["active_calls"],
                    )
                    last_status_time = current_time

            logger.info("PBX system shutdown complete")
        else:
            logger.error("Failed to start PBX system")
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)
    except Exception:
        logger.exception("Fatal error during PBX startup")
        if pbx:
            pbx.stop()
        sys.exit(1)
