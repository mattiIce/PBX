#!/usr/bin/env python3
"""
Migrate Extension Passwords to Secure Database Storage

This script migrates extension passwords from config.yml to the database
with FIPS-compliant hashing for secure storage.

Usage:
    python scripts/migrate_passwords_to_database.py
    python scripts/migrate_passwords_to_database.py --dry-run
    python scripts/migrate_passwords_to_database.py --config custom_config.yml
"""
import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend
from pbx.utils.logger import get_logger
from pbx.utils.security import get_password_manager


def migrate_passwords(config_file="config.yml", dry_run=False):
    """
    Migrate passwords from config.yml to database

    Args:
        config_file: Path to configuration file
        dry_run: If True, show what would be done without making changes
    """
    logger = get_logger()

    print("=" * 70)
    print("Extension Password Migration to Secure Database Storage")
    print("=" * 70)
    print()

    # Load configuration
    try:
        config = Config(config_file)
        logger.info(f"Loaded configuration from {config_file}")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False

    # Get security configuration
    db_config = {
        "database.type": config.get("database.type", "sqlite"),
        "database.host": config.get("database.host", "localhost"),
        "database.port": config.get("database.port", 5432),
        "database.name": config.get("database.name", "pbx_system"),
        "database.user": config.get("database.user", "pbx_user"),
        "database.password": config.get("database.password", ""),
        "database.path": config.get("database.path", "pbx.db"),
        "security.fips_mode": config.get("security.fips_mode", False),
    }

    # Connect to database
    db = DatabaseBackend(db_config)
    if not db.connect():
        print("✗ Failed to connect to database")
        return False

    print("✓ Connected to database")
    print()

    # Ensure tables exist
    if not db.create_tables():
        print("✗ Failed to create database tables")
        db.disconnect()
        return False

    print("✓ Database tables ready")
    print()

    # Initialize password manager
    password_mgr = get_password_manager(db_config)

    # Get extensions from config
    extensions = config.get_extensions()
    if not extensions:
        print("✗ No extensions found in configuration")
        db.disconnect()
        return False

    print(f"Found {len(extensions)} extensions in configuration")
    print()

    # Migrate each extension
    migrated = 0
    skipped = 0
    errors = 0

    for ext_config in extensions:
        number = ext_config.get("number")
        name = ext_config.get("name", "")
        password = ext_config.get("password", "")
        email = ext_config.get("email", "")
        allow_external = ext_config.get("allow_external", True)
        voicemail_pin = ext_config.get("voicemail_pin", "")

        print(f"Processing extension {number} ({name})...")

        if not password:
            print("  ⚠ No password found, skipping")
            skipped += 1
            continue

        try:
            # Check if extension already exists in database
            check_query = (
                "SELECT number, password_salt FROM extensions WHERE number = %s"
                if db.db_type == "postgresql"
                else "SELECT number, password_salt FROM extensions WHERE number = ?"
            )
            existing = db.fetch_one(check_query, (number,))

            if existing and existing.get("password_salt"):
                print("  ℹ Already migrated (has salt), skipping")
                skipped += 1
                continue

            # Hash password
            password_hash, password_salt = password_mgr.hash_password(password)
            print("  ✓ Password hashed successfully")

            # Hash voicemail PIN if provided
            vm_pin_hash = None
            vm_pin_salt = None
            if voicemail_pin:
                vm_pin_hash, vm_pin_salt = password_mgr.hash_password(voicemail_pin)
                print("  ✓ Voicemail PIN hashed successfully")

            if dry_run:
                print("  [DRY RUN] Would store hashed credentials in database")
                migrated += 1
                continue

            # Insert or update in database
            if existing:
                # Update existing
                update_query = (
                    """
                UPDATE extensions
                SET name = %s, email = %s, password_hash = %s, password_salt = %s,
                    allow_external = %s, voicemail_pin_hash = %s, voicemail_pin_salt = %s,
                    password_changed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE number = %s
                """
                    if db.db_type == "postgresql"
                    else """
                UPDATE extensions
                SET name = ?, email = ?, password_hash = ?, password_salt = ?,
                    allow_external = ?, voicemail_pin_hash = ?, voicemail_pin_salt = ?,
                    password_changed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE number = ?
                """
                )
                params = (
                    name,
                    email,
                    password_hash,
                    password_salt,
                    allow_external,
                    vm_pin_hash,
                    vm_pin_salt,
                    number,
                )
            else:
                # Insert new
                insert_query = (
                    """
                INSERT INTO extensions (number, name, email, password_hash, password_salt,
                                      allow_external, voicemail_pin_hash, voicemail_pin_salt,
                                      password_changed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """
                    if db.db_type == "postgresql"
                    else """
                INSERT INTO extensions (number, name, email, password_hash, password_salt,
                                      allow_external, voicemail_pin_hash, voicemail_pin_salt,
                                      password_changed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """
                )
                params = (
                    number,
                    name,
                    email,
                    password_hash,
                    password_salt,
                    allow_external,
                    vm_pin_hash,
                    vm_pin_salt,
                )

            if db.execute(insert_query if not existing else update_query, params):
                print("  ✓ Migrated successfully")
                migrated += 1
            else:
                print("  ✗ Failed to store in database")
                errors += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors += 1

        print()

    # Disconnect
    db.disconnect()

    # Summary
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"Total extensions: {len(extensions)}")
    print(f"Migrated: {migrated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print()

    if dry_run:
        print("DRY RUN: No changes were made to the database")
        print("Run without --dry-run to perform actual migration")
    elif errors == 0:
        print("✓ Migration completed successfully!")
        print()
        print("Next steps:")
        print("  1. Test extension authentication to verify migration")
        print("  2. Backup config.yml before removing passwords")
        print("  3. Remove plaintext passwords from config.yml")
        print("  4. Restart PBX system to use database authentication")
    else:
        print("⚠ Migration completed with errors")
        print("  Review error messages above and retry failed extensions")

    print()
    return errors == 0


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Migrate extension passwords to secure database storage"
    )
    parser.add_argument(
        "--config", default="config.yml", help="Path to configuration file (default: config.yml)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    success = migrate_passwords(args.config, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
