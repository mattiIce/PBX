#!/usr/bin/env python3
"""
Quick check script to verify where voicemails are being stored

This script checks the current PBX configuration and reports whether
voicemails are being saved to the database or file system only.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def main():
    print("=" * 70)
    print("  VOICEMAIL STORAGE CHECK")
    print("=" * 70)

    # Load configuration
    config = Config("config.yml")
    db_type = config.get("database.type")

    print(f"\nConfigured database type: {db_type}")

    # Try to connect
    db = DatabaseBackend(config)
    connected = db.connect()

    print(f"Database connection: {'✓ CONNECTED' if connected else '✗ FAILED'}")
    print(f"Database enabled: {db.enabled}")

    if connected and db.enabled:
        print("\n" + "=" * 70)
        print("✅ VOICEMAILS ARE BEING SAVED TO DATABASE")
        print("=" * 70)
        print("\nWhat this means:")
        print("  • Voicemail metadata is stored in the database")
        print("  • Audio files are stored on the file system")
        print("  • This is the CORRECT and EFFICIENT architecture")
        print("\nDatabase stores:")
        print("  - Caller ID")
        print("  - Timestamp")
        print("  - Duration")
        print("  - Listened status")
        print("  - File path reference")
        print("\nFile system stores:")
        print("  - Actual WAV audio files")

        # Check if tables exist and get voicemail count
        try:
            if db.db_type == "postgresql":
                table_check = db.fetch_one(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'voicemail_messages')"
                )
                table_exists = list(table_check.values())[0] if table_check else False
            else:
                table_check = db.fetch_one(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='voicemail_messages'"
                )
                table_exists = table_check is not None

            if table_exists:
                count_result = db.fetch_one("SELECT COUNT(*) as count FROM voicemail_messages")
                count = count_result["count"] if count_result else 0
                print(f"\nCurrent voicemail records in database: {count}")
            else:
                print("\n⚠ Note: voicemail_messages table doesn't exist yet")
                print("  It will be created automatically when PBX starts")
        except Exception as e:
            print(f"\n⚠ Could not check voicemail count: {e}")

        db.disconnect()

    else:
        print("\n" + "=" * 70)
        print("⚠ VOICEMAILS ARE BEING SAVED TO FILE SYSTEM ONLY")
        print("=" * 70)
        print("\nWhat this means:")
        print("  • Voicemails are saved ONLY as files")
        print("  • No database metadata is being stored")
        print("  • Limited query and search capabilities")
        print("\nWhy this is happening:")
        if db_type == "postgresql":
            print("  • PostgreSQL is configured but not accessible")
            print("  • Database connection failed")
        else:
            print("  • Database is not properly configured")

        print("\nTo fix this:")
        print("  1. Run diagnostics:")
        print("     python scripts/verify_database.py")
        print("\n  2. See detailed setup guide:")
        print("     cat VOICEMAIL_DATABASE_SETUP.md")
        print("\n  3. For PostgreSQL:")
        print("     - Ensure PostgreSQL is running")
        print("     - Verify database exists")
        print("     - Check credentials in config.yml")
        print("\n  4. Quick test with SQLite:")
        print("     - Edit config.yml: database.type: sqlite")
        print("     - Add: database.path: pbx.db")

    print("\n" + "=" * 70)
    print("For more information:")
    print("  • Setup guide: VOICEMAIL_DATABASE_SETUP.md")
    print("  • Diagnostics: python scripts/verify_database.py")
    print("  • Demo: python scripts/demo_database_voicemail.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
