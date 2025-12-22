#!/usr/bin/env python3
"""
List Extensions from Database

This script lists all extensions stored in the database.

Usage:
    python scripts/list_extensions_from_db.py [--config CONFIG_FILE] [--ad-only]
"""
import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, ExtensionDB


def main():
    parser = argparse.ArgumentParser(description="List extensions from database")
    parser.add_argument(
        "--config", default="config.yml", help="Path to config file (default: config.yml)"
    )
    parser.add_argument("--ad-only", action="store_true", help="Show only AD-synced extensions")

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config(args.config)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)

    # Initialize database
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
        print("Error: Failed to connect to database")
        sys.exit(1)

    ext_db = ExtensionDB(db)

    # Get extensions
    if args.ad_only:
        extensions = ext_db.get_ad_synced()
        title = "AD-Synced Extensions"
    else:
        extensions = ext_db.get_all()
        title = "All Extensions"

    print("=" * 80)
    print(f"{title} ({len(extensions)} total)")
    print("=" * 80)
    print()

    if not extensions:
        print("No extensions found in database")
        print()
        print("To migrate extensions from config.yml:")
        print("  python scripts/migrate_extensions_to_db.py")
        sys.exit(0)

    # Print table header
    print(f"{'Number':<10} {'Name':<25} {'Email':<30} {'Ext':<6} {'AD':<4}")
    print("-" * 80)

    # Print each extension
    for ext in extensions:
        number = ext["number"]
        name = ext["name"][:24] if len(ext["name"]) > 24 else ext["name"]
        email = (
            ext["email"][:29] if ext["email"] and len(ext["email"]) > 29 else (ext["email"] or "")
        )
        allow_ext = "Yes" if ext["allow_external"] else "No"
        ad_synced = "Yes" if ext["ad_synced"] else "No"

        print(f"{number:<10} {name:<25} {email:<30} {allow_ext:<6} {ad_synced:<4}")

    print()
    print(f"Total: {len(extensions)} extensions")

    # Show AD sync stats
    if not args.ad_only:
        ad_synced_count = sum(1 for ext in extensions if ext["ad_synced"])
        manual_count = len(extensions) - ad_synced_count
        print(f"  - {ad_synced_count} synced from Active Directory")
        print(f"  - {manual_count} created manually")

    db.disconnect()


if __name__ == "__main__":
    main()
