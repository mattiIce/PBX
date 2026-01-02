#!/usr/bin/env python3
"""
Database Verification and Diagnostic Tool for Warden Voip System

This script verifies that the PostgreSQL database is properly configured
and accessible. It provides detailed diagnostic information to help
troubleshoot database connectivity issues.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text):
    """Print a formatted section header"""
    print(f"\n{text}")
    print("-" * 70)


def check_psycopg2():
    """Check if psycopg2 is installed"""
    print_section("1. Checking PostgreSQL Driver (psycopg2)")
    try:
        import psycopg2

        print("✓ psycopg2 is installed")
        print(f"  Version: {psycopg2.__version__}")
        return True
    except ImportError:
        print("✗ psycopg2 is NOT installed")
        print("\n  To install, run:")
        print("  pip install psycopg2-binary")
        return False


def check_config():
    """Check database configuration"""
    print_section("2. Checking Database Configuration")
    try:
        config = Config("config.yml")
        db_config = {
            "type": config.get("database.type"),
            "host": config.get("database.host"),
            "port": config.get("database.port"),
            "name": config.get("database.name"),
            "user": config.get("database.user"),
        }

        print("✓ Configuration loaded successfully")
        print(f"  Database Type: {db_config['type']}")
        print(f"  Host: {db_config['host']}")
        print(f"  Port: {db_config['port']}")
        print(f"  Database Name: {db_config['name']}")
        print(f"  Username: {db_config['user']}")

        return config, db_config
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return None, None


def check_connection(config):
    """Check database connection"""
    print_section("3. Testing Database Connection")
    try:
        db = DatabaseBackend(config)

        if db.db_type == "postgresql":
            print("  Attempting to connect to PostgreSQL...")
        else:
            print(f"  Connecting to {db.db_type}...")

        connected = db.connect()

        if connected:
            print(f"✓ Successfully connected to {db.db_type} database")
            print(f"  Database enabled: {db.enabled}")

            # Check tables
            print_section("4. Checking Database Tables")
            if db.db_type == "postgresql":
                query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            else:
                query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"

            tables = db.fetch_all(query)
            if tables:
                print(f"✓ Found {len(tables)} tables:")
                for table in tables:
                    table_name = table.get("table_name") or table.get("name")
                    print(f"  - {table_name}")

                # Check specifically for voicemail_messages table
                table_names = [t.get("table_name") or t.get("name") for t in tables]
                if "voicemail_messages" in table_names:
                    print("\n✓ voicemail_messages table exists")

                    # Check voicemail count
                    count_result = db.fetch_one("SELECT COUNT(*) as count FROM voicemail_messages")
                    if count_result:
                        count = count_result["count"]
                        print(f"  Total voicemail records in database: {count}")
                else:
                    print("\n⚠ voicemail_messages table does NOT exist")
                    print("  Tables will be created automatically when PBX starts")
            else:
                print("⚠ No tables found in database")
                print("  Tables may need to be created")

            db.disconnect()
            return True
        else:
            print("✗ Failed to connect to database")
            print(f"  Database enabled: {db.enabled}")
            return False

    except Exception as e:
        print(f"✗ Connection error: {e}")
        import traceback

        traceback.print_exc()
        return False


def provide_recommendations(psycopg2_ok, config_ok, connection_ok):
    """Provide recommendations based on test results"""
    print_header("RECOMMENDATIONS")

    if psycopg2_ok and config_ok and connection_ok:
        print("\n✓ All checks passed! Your database is properly configured and accessible.")
        print("\n  Voicemails WILL be saved to the database with metadata:")
        print("  - caller_id, timestamp, duration, listened status")
        print("\n  Audio files will be stored on the file system:")
        print("  - Large WAV files in the voicemail/ directory")
        print("\n  This is the correct and efficient architecture.")
        return True

    print("\n✗ Issues detected with database configuration:\n")

    if not psycopg2_ok:
        print("1. Install PostgreSQL driver:")
        print("   pip install psycopg2-binary\n")

    if not config_ok:
        print("2. Fix configuration file (config.yml)")
        print("   Ensure database section is properly configured\n")

    if not connection_ok:
        print("3. Database connection failed. Possible causes:")
        print("   a) PostgreSQL server is not running")
        print("      - Start PostgreSQL: sudo systemctl start postgresql")
        print("      - Or: sudo service postgresql start\n")
        print("   b) Database doesn't exist")
        print("      - Create database: createdb pbx_system")
        print("      - Or: sudo -u postgres createdb pbx_system\n")
        print("   c) Incorrect credentials")
        print("      - Check username/password in config.yml")
        print("      - Verify PostgreSQL user exists and has access\n")
        print("   d) PostgreSQL not accepting connections")
        print("      - Check pg_hba.conf allows local connections")
        print("      - Check postgresql.conf has listen_addresses set\n")
        print("   e) Firewall blocking port 5432")
        print("      - Check firewall rules: sudo ufw status\n")

    print("\nIf you want to use SQLite instead (for testing):")
    print("  Change database.type in config.yml from 'postgresql' to 'sqlite'")
    print("  Add database.path: 'pbx.db'")

    return False


def main():
    """Main execution"""
    print_header("PBX DATABASE VERIFICATION TOOL")
    print("\nThis tool verifies that your database is properly configured")
    print("for storing voicemail metadata (caller ID, duration, etc.)")
    print("\nNote: Audio files are always stored on the file system,")
    print("only metadata is stored in the database.")

    # Run checks
    psycopg2_ok = check_psycopg2()
    config, db_config = check_config()
    config_ok = config is not None

    connection_ok = False
    if config_ok:
        connection_ok = check_connection(config)

    # Provide recommendations
    all_ok = provide_recommendations(psycopg2_ok, config_ok, connection_ok)

    print_header("SUMMARY")
    print(f"\n  psycopg2 installed: {'✓' if psycopg2_ok else '✗'}")
    print(f"  Configuration valid: {'✓' if config_ok else '✗'}")
    print(f"  Database connection: {'✓' if connection_ok else '✗'}")

    if all_ok:
        print("\n  Status: READY ✓")
        sys.exit(0)
    else:
        print("\n  Status: NEEDS ATTENTION ✗")
        sys.exit(1)


if __name__ == "__main__":
    main()
