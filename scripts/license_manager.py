#!/usr/bin/env python3
"""License Management CLI Tool.

Command-line utility for generating, installing, and managing licenses.

Usage:
    python scripts/license_manager.py --help
    python scripts/license_manager.py generate --type professional --org "Example Corp"
    python scripts/license_manager.py install license.json
    python scripts/license_manager.py status
    python scripts/license_manager.py enable
    python scripts/license_manager.py disable
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pbx.utils.licensing import LicenseManager, LicenseType


def setup_config() -> dict:
    """Load configuration for license manager."""
    # Try to load from config.yml
    try:
        import yaml

        config_path = str(Path(__file__).parent.parent / "config.yml")
        if Path(config_path).exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return config.get("licensing", {})
    except (KeyError, OSError, TypeError, ValueError) as e:
        print(f"Warning: Could not load config.yml: {e}")

    return {}


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate a new license."""
    config = setup_config()
    lm = LicenseManager(config)

    # Parse license type
    try:
        license_type = LicenseType(args.type)
    except ValueError:
        print(f"Error: Invalid license type '{args.type}'")
        print(f"Valid types: {', '.join([t.value for t in LicenseType])}")
        return 1

    # Parse custom features if provided
    custom_features = None
    if args.features:
        custom_features = args.features.split(",")

    # Generate license
    print(f"Generating {license_type.value} license for '{args.org}'...")

    license_data = lm.generate_license_key(
        license_type=license_type,
        issued_to=args.org,
        max_extensions=args.max_extensions,
        max_concurrent_calls=args.max_calls,
        expiration_days=args.days,
        custom_features=custom_features,
    )

    # Save to file
    import re

    safe_org = re.sub(r"[^a-zA-Z0-9_-]", "_", args.org).lower()
    output_file = args.output or f"license_{safe_org}_{datetime.now(UTC).strftime('%Y%m%d')}.json"

    with open(output_file, "w") as f:
        json.dump(license_data, f, indent=2)
    print("\n✓ License generated successfully!")
    print(f"\nLicense Key: {license_data['key']}")
    print(f"Type: {license_data['type']}")
    print(f"Issued To: {license_data['issued_to']}")
    print(f"Issued Date: {license_data['issued_date']}")
    print(f"Expiration: {license_data.get('expiration', 'Never (Perpetual)')}")
    print(f"\nLicense saved to: {output_file}")
    print(f"\nTo install: python {__file__} install {output_file}")

    return 0


def cmd_install(args: argparse.Namespace) -> int:
    """Install a license file."""
    config = setup_config()
    lm = LicenseManager(config)

    # Load license file
    if not Path(args.license_file).exists():
        print(f"Error: License file not found: {args.license_file}")
        return 1

    try:
        with open(args.license_file) as f:
            license_data = json.load(f)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: Failed to load license file: {e}")
        return 1

    # Determine if enforcement is requested
    enforce_licensing = args.enforce if hasattr(args, "enforce") else False

    # Install license
    print(f"Installing license from {args.license_file}...")
    if enforce_licensing:
        print("⚠️  Enforcement mode: License lock file will be created")
        print("    Licensing cannot be disabled once lock file exists")

    if lm.save_license(license_data, enforce_licensing=enforce_licensing):
        print("\n✓ License installed successfully!")

        if enforce_licensing:
            print("✓ License lock file created - licensing enforcement is mandatory")

        # Show status
        status, message = lm.get_license_status()
        print(f"\nStatus: {status.value}")
        print(f"Message: {message}")

        return 0
    print("\n✗ Failed to install license")
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Show license status."""
    config = setup_config()
    lm = LicenseManager(config)

    info = lm.get_license_info()

    print("=" * 60)
    print("LICENSE STATUS")
    print("=" * 60)

    print(f"\nLicensing Enabled: {info['enabled']}")
    print(f"Status: {info['status']}")
    print(f"Message: {info['message']}")

    if info.get("type"):
        print(f"\nLicense Type: {info['type']}")

    if info.get("issued_to"):
        print(f"Issued To: {info['issued_to']}")
        print(f"Issued Date: {info['issued_date']}")
        print(f"Expiration: {info.get('expiration', 'Never')}")
        print(f"License Key: {info.get('key', 'N/A')}")

    if info.get("limits"):
        print("\nLimits:")
        for limit_name, limit_value in info["limits"].items():
            display_value = "Unlimited" if limit_value is None else limit_value
            print(f"  {limit_name}: {display_value}")

    print()
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    """Revoke current license."""
    config = setup_config()
    lm = LicenseManager(config)

    if not args.yes:
        response = input(
            "Are you sure you want to revoke the current license? Type 'yes' to confirm: "
        )
        if response.strip().lower() != "yes":
            print("Aborted.")
            return 0

    print("Revoking license...")

    if lm.revoke_license():
        print("✓ License revoked successfully")
        return 0
    print("✗ Failed to revoke license")
    return 1


def cmd_enable(args: argparse.Namespace) -> int:
    """Enable licensing enforcement."""
    # Update environment file
    env_file = str(Path(__file__).parent.parent / ".env")

    print("Enabling licensing enforcement...")

    # Read existing .env
    env_lines = []
    if Path(env_file).exists():
        with open(env_file) as f:
            env_lines = f.readlines()

    # Update or add PBX_LICENSING_ENABLED
    found = False
    for i, line in enumerate(env_lines):
        if line.startswith("PBX_LICENSING_ENABLED="):
            env_lines[i] = "PBX_LICENSING_ENABLED=true\n"
            found = True
            break

    if not found:
        env_lines.append("\n# Licensing\nPBX_LICENSING_ENABLED=true\n")

    # Write back
    with open(env_file, "w") as f:
        f.writelines(env_lines)

    print("✓ Licensing enabled in .env file")
    print("\nNote: Restart the PBX system for changes to take effect:")
    print("  sudo systemctl restart pbx")

    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    """Disable licensing enforcement."""
    # Update environment file
    env_file = str(Path(__file__).parent.parent / ".env")

    print("Disabling licensing enforcement...")

    # Read existing .env
    env_lines = []
    if Path(env_file).exists():
        with open(env_file) as f:
            env_lines = f.readlines()

    # Check for license lock file
    lock_path = str(Path(__file__).parent.parent / ".license_lock")
    if Path(lock_path).exists():
        print("✗ Cannot disable licensing - license lock file exists")
        print("\nTo disable licensing, first remove the lock file:")
        print(f"  python {__file__} remove-lock")
        return 1

    # Update or add PBX_LICENSING_ENABLED
    found = False
    for i, line in enumerate(env_lines):
        if line.startswith("PBX_LICENSING_ENABLED="):
            env_lines[i] = "PBX_LICENSING_ENABLED=false\n"
            found = True
            break

    if not found:
        env_lines.append("\n# Licensing\nPBX_LICENSING_ENABLED=false\n")

    # Write back
    with open(env_file, "w") as f:
        f.writelines(env_lines)

    print("✓ Licensing disabled in .env file (all features unlocked)")
    print("\nNote: Restart the PBX system for changes to take effect:")
    print("  sudo systemctl restart pbx")

    return 0


def cmd_remove_lock(args: argparse.Namespace) -> int:
    """Remove license lock file."""
    config = setup_config()
    lm = LicenseManager(config)

    if not args.yes:
        response = input(
            "Remove license lock file? This will allow licensing to be disabled. Type 'yes' to confirm: "
        )
        if response.strip().lower() != "yes":
            print("Aborted.")
            return 0

    print("Removing license lock file...")

    if lm.remove_license_lock():
        print("✓ License lock file removed")
        print("\nLicensing can now be disabled via:")
        print(f"  python {__file__} disable")
        return 0
    print("✗ License lock file does not exist or could not be removed")
    return 1


def cmd_features(args: argparse.Namespace) -> int:
    """List available features for current license."""
    config = setup_config()
    lm = LicenseManager(config)

    if not lm.enabled:
        print("Licensing is DISABLED - all features are available")
        return 0

    # Get license type
    if lm.current_license:
        license_type = lm.current_license.get("type", "trial")
    else:
        license_type = "trial"

    # Get features
    features = lm.features.get(license_type, [])

    if license_type == "custom" and lm.current_license:
        features = lm.current_license.get("custom_features", [])

    print(f"\nAvailable Features ({license_type} license):")
    print("=" * 60)

    # Separate features and limits
    feature_list = []
    limits = {}

    for feature in features:
        if ":" in feature and any(
            feature.startswith(f"{limit}:") for limit in ["max_extensions", "max_concurrent_calls"]
        ):
            limit_name, limit_value = feature.split(":", 1)
            limits[limit_name] = None if limit_value == "unlimited" else int(limit_value)
        else:
            feature_list.append(feature)

    # Print features
    for feature in sorted(feature_list):
        print(f"  ✓ {feature}")

    # Print limits
    if limits:
        print("\nLimits:")
        for limit_name, limit_value in limits.items():
            display_value = "Unlimited" if limit_value is None else f"{limit_value:,}"
            print(f"  • {limit_name.replace('_', ' ').title()}: {display_value}")

    print()
    return 0


def cmd_batch_generate(args: argparse.Namespace) -> int:
    """Generate multiple licenses from a configuration file."""
    config = setup_config()
    lm = LicenseManager(config)

    # Load batch configuration
    if not Path(args.batch_file).exists():
        print(f"Error: Batch file not found: {args.batch_file}")
        return 1

    try:
        with open(args.batch_file) as f:
            if args.batch_file.endswith(".json"):
                import json

                batch_config = json.load(f)
            else:
                import yaml

                batch_config = yaml.safe_load(f)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: Failed to load batch file: {e}")
        return 1

    # Validate batch config
    if "licenses" not in batch_config:
        print("Error: Batch file must contain 'licenses' array")
        return 1

    licenses_to_generate = batch_config["licenses"]
    output_dir = args.output_dir or "generated_licenses"

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(licenses_to_generate)} licenses...")
    print(f"Output directory: {output_dir}")
    print()

    generated_count = 0
    errors = []

    for i, license_spec in enumerate(licenses_to_generate, 1):
        try:
            # Parse license type
            license_type = LicenseType(license_spec.get("type", "basic"))
            issued_to = license_spec.get("issued_to")

            if not issued_to:
                errors.append(f"License {i}: Missing 'issued_to' field")
                continue

            # Generate license
            print(
                f"[{i}/{len(licenses_to_generate)}] Generating {license_type.value} license for '{issued_to}'..."
            )

            custom_features = None
            if license_spec.get("features"):
                if isinstance(license_spec["features"], str):
                    custom_features = license_spec["features"].split(",")
                else:
                    custom_features = license_spec["features"]

            license_data = lm.generate_license_key(
                license_type=license_type,
                issued_to=issued_to,
                max_extensions=license_spec.get("max_extensions"),
                max_concurrent_calls=license_spec.get("max_concurrent_calls"),
                expiration_days=license_spec.get("expiration_days"),
                custom_features=custom_features,
            )

            # Save to file
            import re

            safe_org = re.sub(r"[^a-zA-Z0-9_-]", "_", issued_to).lower()
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            output_file = Path(output_dir) / f"license_{safe_org}_{timestamp}_{i}.json"

            with open(output_file, "w") as f:
                json.dump(license_data, f, indent=2)

            print(f"  ✓ Saved to: {output_file}")
            generated_count += 1

        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as e:
            error_msg = f"License {i} ({license_spec.get('issued_to', 'unknown')}): {e!s}"
            errors.append(error_msg)
            print(f"  ✗ Error: {e}")

    # Summary
    print()
    print("=" * 60)
    print("Batch generation complete!")
    print(f"Successfully generated: {generated_count}/{len(licenses_to_generate)} licenses")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
        return 1

    return 0


def main() -> int:
    """Run the license management CLI tool."""
    parser = argparse.ArgumentParser(
        description="License Management CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a professional license
  python scripts/license_manager.py generate --type professional --org "Acme Corp" --days 365

  # Generate an enterprise license (unlimited, 1 year)
  python scripts/license_manager.py generate --type enterprise --org "BigCo Inc" --days 365

  # Generate a perpetual license (never expires)
  python scripts/license_manager.py generate --type perpetual --org "Example LLC"

  # Batch generate multiple licenses from a config file
  python scripts/license_manager.py batch-generate examples/batch_licenses.json
  python scripts/license_manager.py batch-generate examples/batch_licenses.yml --output-dir /path/to/output

  # Install a license
  python scripts/license_manager.py install license_acme_corp_20251222.json

  # Install a license with enforcement (creates lock file - for commercial deployments)
  python scripts/license_manager.py install license_acme_corp_20251222.json --enforce

  # Check license status
  python scripts/license_manager.py status

  # List available features
  python scripts/license_manager.py features

  # Enable licensing
  python scripts/license_manager.py enable

  # Disable licensing (free/open-source mode)
  python scripts/license_manager.py disable

  # Remove license lock file (allows disabling licensing)
  python scripts/license_manager.py remove-lock

  # Revoke current license
  python scripts/license_manager.py revoke
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate a new license")
    gen_parser.add_argument(
        "--type",
        required=True,
        help="License type (trial, basic, professional, enterprise, perpetual, custom)",
    )
    gen_parser.add_argument("--org", required=True, help="Organization/person name")
    gen_parser.add_argument("--days", type=int, help="Days until expiration (omit for perpetual)")
    gen_parser.add_argument("--max-extensions", type=int, help="Maximum extensions")
    gen_parser.add_argument("--max-calls", type=int, help="Maximum concurrent calls")
    gen_parser.add_argument("--features", help="Custom features (comma-separated, for custom type)")
    gen_parser.add_argument("--output", "-o", help="Output file path")

    # Batch generate command
    batch_parser = subparsers.add_parser(
        "batch-generate", help="Generate multiple licenses from a configuration file"
    )
    batch_parser.add_argument("batch_file", help="Path to batch configuration file (JSON or YAML)")
    batch_parser.add_argument(
        "--output-dir", help="Output directory for generated licenses (default: generated_licenses)"
    )

    # Install command
    install_parser = subparsers.add_parser("install", help="Install a license file")
    install_parser.add_argument("license_file", help="Path to license JSON file")
    install_parser.add_argument(
        "--enforce",
        action="store_true",
        help="Create license lock file to prevent disabling (for commercial deployments)",
    )

    # Status command
    subparsers.add_parser("status", help="Show license status")

    # Features command
    subparsers.add_parser("features", help="List available features")

    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke current license")
    revoke_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    # Enable command
    subparsers.add_parser("enable", help="Enable licensing enforcement")

    # Disable command
    subparsers.add_parser("disable", help="Disable licensing enforcement")

    # Remove lock command
    remove_lock_parser = subparsers.add_parser("remove-lock", help="Remove license lock file")
    remove_lock_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    try:
        if args.command == "generate":
            return cmd_generate(args)
        if args.command == "batch-generate":
            return cmd_batch_generate(args)
        if args.command == "install":
            return cmd_install(args)
        if args.command == "status":
            return cmd_status(args)
        if args.command == "features":
            return cmd_features(args)
        if args.command == "revoke":
            return cmd_revoke(args)
        if args.command == "enable":
            return cmd_enable(args)
        if args.command == "disable":
            return cmd_disable(args)
        if args.command == "remove-lock":
            return cmd_remove_lock(args)
        parser.print_help()
        return 1

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
