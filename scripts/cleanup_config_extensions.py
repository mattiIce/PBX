#!/usr/bin/env python3
"""
Clean up Extensions from config.yml

This script removes the extensions section from config.yml after they have been
migrated to the database. It creates a backup and optionally adds commented-out
versions for reference.

Usage:
    python scripts/cleanup_config_extensions.py [--config CONFIG_FILE] [--backup]

Options:
    --config    Path to config file (default: config.yml)
    --backup    Create a backup before modifying (default: True)
    --no-backup Don't create a backup
"""

import argparse
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove extensions from config.yml (after migration to database)"
    )
    parser.add_argument(
        "--config", default="config.yml", help="Path to config file (default: config.yml)"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup before modifying (default: True)",
    )
    parser.add_argument(
        "--no-backup", action="store_false", dest="backup", help="Do not create backup"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Config.yml Extension Cleanup")
    print("=" * 70)
    print()

    config_file = args.config

    if not Path(config_file).exists():
        print(f"Error: Configuration file '{config_file}' not found")
        sys.exit(1)

    # Load current config
    with open(config_file) as f:
        config = yaml.safe_load(f)

    # Check if extensions exist
    if "extensions" not in config or not config["extensions"]:
        print(f"No extensions found in {config_file}")
        print("Extensions may have already been removed.")
        sys.exit(0)

    extensions = config["extensions"]
    print(f"Found {len(extensions)} extensions in {config_file}")
    print()

    # Show extensions that will be removed
    print("Extensions that will be removed from config:")
    for ext in extensions:
        number = ext.get("number", "unknown")
        name = ext.get("name", "unknown")
        print(f"  - {number}: {name}")
    print()

    # Confirm
    response = input("Remove these extensions from config.yml? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Cancelled.")
        sys.exit(0)

    # Create backup if requested
    if args.backup:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_file = f"{config_file}.backup_{timestamp}"
        shutil.copy2(config_file, backup_file)
        print(f"✓ Created backup: {backup_file}")

    # Remove extensions from config
    del config["extensions"]

    # Add comment explaining where extensions are stored
    comment = """# Extensions are now stored in the database
# To view extensions: python scripts/list_extensions_from_db.py
# To add extensions: Use the admin web interface at https://YOUR_SERVER_IP:9000/admin/
# (replace YOUR_SERVER_IP with your server address, e.g., localhost)
# or the API endpoint: POST /api/extensions
"""

    # Write updated config
    with open(config_file, "w") as f:
        # Write the comment first
        f.write(comment)
        f.write("\n")
        # Write the config
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"✓ Removed extensions section from {config_file}")
    print()
    print("=" * 70)
    print("Cleanup Complete")
    print("=" * 70)
    print()
    print("Extensions have been removed from config.yml")
    print("They are now managed exclusively through the database.")
    print()
    print("Next steps:")
    print("  1. Verify the PBX still works:")
    print("     python main.py")
    print()
    print("  2. Access the admin interface:")
    print("     https://YOUR_SERVER_IP:9000/admin/")
    print("     (replace YOUR_SERVER_IP with your server address)")
    print()
    print("  3. Extensions will be loaded from the database automatically")


if __name__ == "__main__":
    main()
