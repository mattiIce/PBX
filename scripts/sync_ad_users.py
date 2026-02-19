#!/usr/bin/env python3
"""
Active Directory User Synchronization Script

This script synchronizes users from Active Directory to the PBX system.
It creates/updates extensions based on AD user information.

Usage:
    python scripts/sync_ad_users.py [--dry-run] [--test-users USERNAME1 USERNAME2]

Options:
    --dry-run       Show what would be synced without making changes
    --test-users    Only sync specific test users (comma-separated)
    --verbose       Show detailed output

Configuration:
    Edit config.yml and set:
    - integrations.active_directory.enabled: true
    - integrations.active_directory.auto_provision: true

    Or use environment variables:
    - AD_SERVER: LDAP server address
    - AD_BIND_DN: Service account DN
    - AD_BIND_PASSWORD: Service account password
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


from pbx.features.extensions import ExtensionRegistry
from pbx.integrations.active_directory import ActiveDirectoryIntegration
from pbx.utils.config import Config


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize users from Active Directory to PBX")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be synced without making changes"
    )
    parser.add_argument("--test-users", nargs="+", help="Only sync specific test users")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument(
        "--config", default="config.yml", help="Path to config file (default: config.yml)"
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config(args.config)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)

    # Check if AD integration is enabled
    if not config.get("integrations.active_directory.enabled", False):
        print("=" * 70)
        print("WARNING: Active Directory integration is DISABLED")
        print("=" * 70)
        print()
        print("To enable AD synchronization, edit config.yml and set:")
        print("  integrations.active_directory.enabled: true")
        print("  integrations.active_directory.auto_provision: true")
        print()
        response = input("Enable now and continue? (yes/no): ")
        if response.lower() in ["yes", "y"]:
            config.config["integrations"]["active_directory"]["enabled"] = True
            config.config["integrations"]["active_directory"]["auto_provision"] = True
            config.save()
            print("✓ AD integration enabled")
        else:
            print("Exiting...")
            sys.exit(0)

    if not config.get("integrations.active_directory.auto_provision", False):
        print("=" * 70)
        print("WARNING: Auto-provisioning is DISABLED")
        print("=" * 70)
        print()
        print("To enable auto-provisioning, edit config.yml and set:")
        print("  integrations.active_directory.auto_provision: true")
        print()
        sys.exit(1)

    # Initialize AD integration
    print("=" * 70)
    print("Active Directory User Synchronization")
    print("=" * 70)
    print()

    # Create a simple config dict wrapper
    ad_config = {
        "integrations.active_directory.enabled": config.get(
            "integrations.active_directory.enabled"
        ),
        "integrations.active_directory.server": config.get("integrations.active_directory.server"),
        "integrations.active_directory.base_dn": config.get(
            "integrations.active_directory.base_dn"
        ),
        "integrations.active_directory.bind_dn": config.get(
            "integrations.active_directory.bind_dn"
        ),
        "integrations.active_directory.bind_password": config.get(
            "integrations.active_directory.bind_password"
        ),
        "integrations.active_directory.use_ssl": config.get(
            "integrations.active_directory.use_ssl", True
        ),
        "integrations.active_directory.auto_provision": config.get(
            "integrations.active_directory.auto_provision"
        ),
        "integrations.active_directory.user_search_base": config.get(
            "integrations.active_directory.user_search_base"
        ),
        "integrations.active_directory.deactivate_removed_users": config.get(
            "integrations.active_directory.deactivate_removed_users", True
        ),
        "config_file": args.config,
    }

    ad = ActiveDirectoryIntegration(ad_config)

    if not ad.enabled:
        print("Error: Active Directory integration could not be initialized")
        sys.exit(1)

    # Test connection
    print("Testing connection to Active Directory...")
    if not ad.connect():
        print("✗ Failed to connect to Active Directory")
        print()
        print("Please check:")
        print("  - Server address is correct")
        print("  - Network connectivity")
        print("  - Bind credentials are valid")
        sys.exit(1)

    print("✓ Connected to Active Directory")
    print()

    # Show configuration
    print("Configuration:")
    print(f"  Server: {ad.ldap_server}")
    print(f"  Base DN: {ad.base_dn}")
    print(f"  User Search Base: {ad_config.get('integrations.active_directory.user_search_base')}")
    print(f"  Auto-provision: {ad.auto_provision}")
    print()

    if args.dry_run:
        print("DRY RUN MODE: No changes will be made")
        print()

    # Perform synchronization
    print("Synchronizing users...")
    print()

    try:
        # Initialize database backend
        from pbx.utils.database import DatabaseBackend, ExtensionDB

        db_config = {
            "database.type": config.get("database.type", "postgresql"),
            "database.host": config.get("database.host", "localhost"),
            "database.port": config.get("database.port", 5432),
            "database.name": config.get("database.name", "pbx_system"),
            "database.user": config.get("database.user", "pbx_user"),
            "database.password": config.get("database.password", ""),
            "database.path": config.get("database.path", "pbx.db"),
        }

        database = DatabaseBackend(db_config)
        extension_db = None

        if database.connect():
            database.create_tables()
            extension_db = ExtensionDB(database)
            print("✓ Connected to database - extensions will be synced to database")
        else:
            print("⚠ Database not available - extensions will be synced to config.yml")
            database = None  # Set to None if connection failed

        print()

        # Initialize extension registry for live updates
        # Check both database exists and is enabled before passing
        extension_registry = ExtensionRegistry(
            config, database=database if (database and database.enabled) else None
        )

        # Run sync
        synced_count = ad.sync_users(
            extension_registry=extension_registry, extension_db=extension_db
        )

        print()
        print("=" * 70)
        print(f"Synchronization Complete: {synced_count} users synchronized")
        print("=" * 70)

        if synced_count > 0:
            print()
            print("Next steps:")
            print("  1. Review the synced extensions in config.yml")
            print("  2. Test SIP registration with one of the synced extensions")
            print("  3. Check logs for any errors or warnings")
            print()
            print("Test users provided: cmattinson, bsautter")
            print("Check their extension numbers in config.yml")

    except (KeyError, TypeError, ValueError) as e:
        print(f"Error during synchronization: {e}")
        import traceback

        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
