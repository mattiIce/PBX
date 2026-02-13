#!/usr/bin/env python3
"""
Migrate Extensions from config.yml to Database

This script migrates existing extensions from config.yml to the database.
It preserves all extension data and marks them appropriately.

Usage:
    python scripts/migrate_extensions_to_db.py [--config CONFIG_FILE] [--dry-run]

Options:
    --config    Path to config file (default: config.yml)
    --dry-run   Show what would be migrated without making changes
"""

import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, ExtensionDB


def main():
    parser = argparse.ArgumentParser(description="Migrate extensions from config.yml to database")
    parser.add_argument(
        "--config", default="config.yml", help="Path to config file (default: config.yml)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be migrated without making changes"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Extension Migration: config.yml → Database")
    print("=" * 70)
    print()

    # Load configuration
    try:
        config = Config(args.config)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)

    # Initialize database
    print("Connecting to database...")
    db_config = {
        "database.type": config.get("database.type", "sqlite"),
        "database.host": config.get("database.host", "localhost"),
        "database.port": config.get("database.port", 5432),
        "database.name": config.get("database.name", "pbx_system"),
        "database.user": config.get("database.user", "pbx_user"),
        "database.password": config.get("database.password", ""),
        "database.path": config.get("database.path", "pbx.db"),
    }

    db = DatabaseBackend(db_config)

    if not db.connect():
        print("✗ Failed to connect to database")
        print()
        print("Please ensure:")
        print("  1. Database is running (if using PostgreSQL)")
        print("  2. Database credentials are correct in config.yml")
        print("  3. Database has been initialized: python scripts/init_database.py")
        sys.exit(1)

    print("✓ Connected to database")
    print()

    # Create tables if they don't exist
    print("Ensuring database tables exist...")
    db.create_tables()
    print("✓ Database tables ready")
    print()

    # Initialize extension DB
    ext_db = ExtensionDB(db)

    # Get extensions from config.yml
    extensions = config.get_extensions()

    if not extensions:
        print("No extensions found in config.yml")
        sys.exit(0)

    print(f"Found {len(extensions)} extensions in config.yml")
    print()

    if args.dry_run:
        print("DRY RUN MODE: No changes will be made")
        print()

    # Migrate each extension
    migrated = 0
    skipped = 0
    errors = 0

    for ext in extensions:
        number = ext.get("number")
        name = ext.get("name", f"Extension {number}")
        email = ext.get("email", "")
        password = ext.get("password", "")
        allow_external = ext.get("allow_external", True)
        voicemail_pin = ext.get("voicemail_pin", "")
        ad_synced = ext.get("ad_synced", False)

        # Check if extension already exists in database
        existing = ext_db.get(number)

        if existing:
            print(f"⚠ Extension {number} ({name}) - Already in database, skipping")
            skipped += 1
            continue

        print(f"→ Extension {number} ({name})")
        print(f"  Email: {email or '(none)'}")
        print(f"  Allow external: {allow_external}")
        print(f"  AD synced: {ad_synced}")

        if not args.dry_run:
            # Note: Passwords from config.yml are stored as-is during migration
            # The authentication system handles password verification
            # NOTE: For production, use FIPS-compliant hashing:
            #   from pbx.utils.encryption import FIPSEncryption
            #   encryption = FIPSEncryption(fips_mode=True)
            #   password_hash, salt = encryption.hash_password(password)
            # Currently storing plain password; system supports both plain and hashed passwords
            password_hash = password

            try:
                success = ext_db.add(
                    number=number,
                    name=name,
                    password_hash=password_hash,
                    email=email if email else None,
                    allow_external=allow_external,
                    voicemail_pin=voicemail_pin if voicemail_pin else None,
                    ad_synced=ad_synced,
                    ad_username=None,
                )

                if success:
                    print("  ✓ Migrated successfully")
                    migrated += 1
                else:
                    print("  ✗ Failed to migrate")
                    errors += 1
            except (KeyError, TypeError, ValueError) as e:
                print(f"  ✗ Error: {e}")
                errors += 1
        else:
            print("  (would migrate)")
            migrated += 1

        print()

    # Summary
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"Migrated: {migrated}")
    print(f"Skipped:  {skipped} (already in database)")
    print(f"Errors:   {errors}")
    print()

    if args.dry_run:
        print("This was a dry run. Run without --dry-run to perform migration.")
    elif errors > 0:
        print("⚠ Migration completed with errors")
        print("Check the output above for details")
        sys.exit(1)
    elif migrated > 0:
        print("✓ Migration completed successfully!")
        print()
        print("Next steps:")
        print("  1. Verify extensions in database:")
        print("     python scripts/list_extensions_from_db.py")
        print()
        print("  2. Test the admin interface:")
        print("     python main.py")
        print("     Open https://localhost:8080/admin/")
        print()
        print("  3. OPTIONAL: Backup and clean up config.yml")
        print("     - Extensions will now be loaded from database")
        print("     - You can remove extensions from config.yml or keep as backup")
    else:
        print("✓ All extensions already in database")

    db.disconnect()


if __name__ == "__main__":
    main()
