"""Dependency Checker for Warden VoIP System.

Verifies that all required and optional dependencies are installed at startup.
Reads dependencies from requirements.txt.
"""

import importlib
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Map package names to module names (when they differ)
PACKAGE_TO_MODULE = {
    "PyYAML": "yaml",
    "psycopg2-binary": "psycopg2",
}

# Features enabled by optional dependencies
OPTIONAL_FEATURES = {
    "psycopg2-binary": "PostgreSQL database backend",
    "psycopg2": "PostgreSQL database backend",
    "msal": "Microsoft Teams/Outlook integration",
    "fido2": "FIDO2/WebAuthn authentication",
    "opuslib": "Opus codec support",
    "vosk": "Voicemail transcription (offline)",
    "sounddevice": "Audio I/O (requires PortAudio system library)",
}

# Core dependencies (required for basic PBX operation)
CORE_PACKAGES = {"PyYAML", "cryptography"}


def parse_requirements_txt(requirements_path: str = "requirements.txt") -> dict[str, str]:
    """Parse requirements.txt file.

    Returns:
        Dictionary mapping package names to version specs (without comments).
    """
    requirements = {}
    req_path = Path(requirements_path)

    if not req_path.exists():
        return requirements

    for line in req_path.read_text().splitlines():
        stripped_line = line.strip()

        # Skip empty lines and comments
        if not stripped_line or stripped_line.startswith("#"):
            continue

        # Remove inline comments
        if "#" in stripped_line:
            stripped_line = stripped_line.split("#")[0].strip()

        # Parse package name and version spec
        match = re.match(r"^([a-zA-Z0-9_.-]+)([>=<!=]+.*)?", stripped_line)
        if match:
            package_name = match.group(1)
            version_spec = match.group(2) or ""
            requirements[package_name] = package_name + version_spec

    return requirements


def get_module_name(package_name: str) -> str:
    """Convert package name to module name."""
    return PACKAGE_TO_MODULE.get(package_name, package_name.lower().replace("-", "_"))


def check_module(module_name: str) -> bool:
    """Check if a Python module is installed."""
    try:
        importlib.import_module(module_name)
    except ImportError:
        return False
    except OSError:
        # Some modules like sounddevice raise OSError when system libraries
        # (e.g., PortAudio) are not installed, even though the Python package is installed
        return False
    else:
        return True


def check_dependencies(
    verbose: bool = False, requirements_path: str = "requirements.txt"
) -> tuple[bool, dict[str, list]]:
    """Check all dependencies from requirements.txt.

    Args:
        verbose: If True, log detailed information.
        requirements_path: Path to requirements.txt file.

    Returns:
        tuple of (all_core_ok, report_dict).
    """
    missing_core = []
    missing_optional = []
    available_optional = []

    requirements = parse_requirements_txt(requirements_path)

    if not requirements:
        if verbose:
            logger.warning("No requirements found in %s", requirements_path)
        return True, {
            "missing_core": [],
            "missing_optional": [],
            "available_optional": [],
        }

    for package_name, package_spec in requirements.items():
        module_name = get_module_name(package_name)
        is_core = package_name in CORE_PACKAGES

        if not check_module(module_name):
            if is_core:
                missing_core.append(package_spec)
                if verbose:
                    logger.error("Missing CORE: %s", package_spec)
            else:
                feature = OPTIONAL_FEATURES.get(package_name, "Additional features")
                missing_optional.append({"package": package_spec, "feature": feature})
                if verbose:
                    logger.warning("Missing optional: %s - enables %s", package_spec, feature)
        elif verbose:
            if is_core:
                logger.info("Core: %s", package_name)
            else:
                feature = OPTIONAL_FEATURES.get(package_name, "Additional features")
                available_optional.append({"package": package_spec, "feature": feature})
                logger.info("Optional: %s - %s", package_name, feature)

    report = {
        "missing_core": missing_core,
        "missing_optional": missing_optional,
        "available_optional": available_optional,
    }

    return len(missing_core) == 0, report


def print_dependency_report(report: dict[str, list], verbose: bool = False) -> None:
    """Log a formatted dependency report."""
    missing_core = report["missing_core"]
    missing_optional = report["missing_optional"]
    available_optional = report["available_optional"]

    if missing_core:
        logger.error("MISSING REQUIRED DEPENDENCIES:")
        for package in missing_core:
            logger.error("  - %s", package)
        logger.error("Install missing dependencies with: pip install %s", " ".join(missing_core))
    else:
        logger.info("All core dependencies satisfied")

    if missing_optional:
        if verbose:
            logger.warning("MISSING OPTIONAL DEPENDENCIES:")
            for dep in missing_optional:
                logger.warning("  - %s (Feature: %s)", dep["package"], dep["feature"])
            packages = " ".join([dep["package"] for dep in missing_optional])
            logger.warning("To enable these features: pip install %s", packages)
        else:
            count = len(missing_optional)
            dependency_word = "dependency" if count == 1 else "dependencies"
            logger.info(
                "%d optional %s missing (use --verbose to see details)", count, dependency_word
            )
    elif verbose:
        logger.info("All optional dependencies installed")

    if available_optional and verbose:
        logger.info("ENABLED OPTIONAL FEATURES:")
        for dep in available_optional:
            logger.info("  - %s", dep["feature"])


def check_and_report(
    verbose: bool = False, strict: bool = True, requirements_path: str = "requirements.txt"
) -> bool:
    """Check dependencies and log report.

    Args:
        verbose: Show detailed information including optional dependencies.
        strict: If True, fail if core dependencies are missing.
        requirements_path: Path to requirements.txt file.

    Returns:
        True if all required dependencies are satisfied (or strict=False).
    """
    all_core_ok, report = check_dependencies(verbose=verbose, requirements_path=requirements_path)

    print_dependency_report(report, verbose=verbose)

    if not all_core_ok and strict:
        logger.error("Cannot start: Missing required dependencies")
        return False

    return True


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    strict = "--strict" in sys.argv or "-s" in sys.argv

    success = check_and_report(verbose=verbose, strict=strict)
    sys.exit(0 if success else 1)
