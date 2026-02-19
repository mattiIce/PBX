#!/usr/bin/env python3
"""
Database initialization script for PBX system
"""

import os
import sys

import psycopg2


# Database configuration
# NOTE: For production use, set these environment variables:
#   - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
def get_db_config() -> dict[str, str | int]:
    """Get database configuration from environment variables with validation."""
    try:
        port = int(os.environ.get("DB_PORT", "5432"))
    except ValueError:
        print("✗ Error: DB_PORT must be a valid integer")
        sys.exit(1)

    password = os.environ.get("DB_PASSWORD")
    if not password:
        print("⚠️  Warning: Using default password from script.")
        print("   For production, set DB_PASSWORD environment variable!")
        password = "YourSecurePassword123!"  # Default for testing only

    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": port,
        "database": os.environ.get("DB_NAME", "pbx_system"),
        "user": os.environ.get("DB_USER", "pbx_user"),
        "password": password,
    }


DB_CONFIG = get_db_config()


def test_connection() -> bool:
    """Test database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print("✓ Connected to PostgreSQL")
        print(f"  Version: {version[0]}")
        cur.close()
        conn.close()
        return True
    except (psycopg2.Error, KeyError, TypeError, ValueError) as e:
        print(f"✗ Connection failed: {e}")
        return False


def verify_tables() -> bool:
    """Verify all tables exist."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        tables = ["vip_callers", "call_records", "voicemail_messages", "extension_settings"]

        for table in tables:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                );
            """,
                (table,),
            )
            exists = cur.fetchone()[0]
            if exists:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' NOT FOUND")

        cur.close()
        conn.close()
        return True
    except (psycopg2.Error, KeyError, TypeError, ValueError) as e:
        print(f"✗ Verification failed: {e}")
        return False


def add_sample_data() -> bool:
    """Add sample VIP caller data for testing."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Insert sample VIP callers
        # Note: Extension 1001 removed as it was a false/test entry
        vip_data = [
            ("+15559876543", "Jane Doe", "XYZ Inc", 2, "VVIP - Board member", "1000", True),
            ("+15555555555", "Bob Johnson", "Tech Ltd", 1, "Regular VIP", "1002", False),
        ]

        for caller_id, name, company, priority, notes, extension, skip_queue in vip_data:
            cur.execute(
                """
                INSERT INTO vip_callers
                (caller_id, name, company, priority_level, notes, direct_extension, skip_queue)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (caller_id) DO NOTHING;
            """,
                (caller_id, name, company, priority, notes, extension, skip_queue),
            )

        conn.commit()
        print(f"✓ Added {len(vip_data)} sample VIP callers")

        cur.close()
        conn.close()
        return True
    except (psycopg2.Error, KeyError, TypeError, ValueError) as e:
        print(f"✗ Sample data insertion failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PBX Database Initialization")
    print("=" * 60)

    if test_connection():
        print("\n" + "=" * 60)
        if verify_tables():
            print("\n" + "=" * 60)
            if add_sample_data():
                print("\n✅ Database initialization complete!")
            else:
                print("\n⚠️  Sample data insertion failed")
        else:
            print("\n⚠️  Table verification failed")
    else:
        print("\n❌ Database connection failed")
        sys.exit(1)
