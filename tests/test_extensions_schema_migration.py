#!/usr/bin/env python3
"""
Tests for extensions table schema migration
Tests that voicemail_pin_hash and voicemail_pin_salt columns are added during migration
"""
import os
import sqlite3
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend



def test_extensions_columns_migration():
    """Test that missing voicemail PIN columns are added during migration"""
    print("Testing extensions table schema migration...")

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # First, create an old version of the extensions table without
        # voicemail_pin columns
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()

        # Create old schema without voicemail_pin_hash and voicemail_pin_salt
        cursor.execute("""
        CREATE TABLE extensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            password_hash VARCHAR(255) NOT NULL,
            allow_external BOOLEAN DEFAULT 1,
            ad_synced BOOLEAN DEFAULT 0,
            ad_username VARCHAR(100),
            password_changed_at TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            account_locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()

        # Verify columns don't exist yet
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(extensions)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        print(f"  Initial columns: {columns}")
        assert 'voicemail_pin_hash' not in columns, "voicemail_pin_hash should not exist initially"
        assert 'voicemail_pin_salt' not in columns, "voicemail_pin_salt should not exist initially"
        assert 'password_salt' not in columns, "password_salt should not exist initially"
        print("  ✓ Old schema confirmed (missing voicemail PIN columns)")

        # Now connect with DatabaseBackend which should trigger migration
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        print("  ✓ Connected to database")

        # Create tables (this will run migrations)
        assert db.create_tables() is True
        print("  ✓ Tables created/migrated")

        db.disconnect()

        # Verify that the columns were added
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(extensions)")
        columns_after = [row[1] for row in cursor.fetchall()]
        conn.close()

        print(f"  Columns after migration: {columns_after}")
        assert 'voicemail_pin_hash' in columns_after, "voicemail_pin_hash should exist after migration"
        assert 'voicemail_pin_salt' in columns_after, "voicemail_pin_salt should exist after migration"
        assert 'password_salt' in columns_after, "password_salt should exist after migration"
        print("  ✓ Migration added missing columns")

        print("✓ Extensions table schema migration test passed")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_extensions_columns_already_exist():
    """Test that migration handles existing columns gracefully"""
    print("Testing extensions migration with existing columns...")

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # Create a test config for SQLite
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True

        # Create tables with all columns
        assert db.create_tables() is True
        print("  ✓ Tables created with all columns")

        # Verify columns exist
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(extensions)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert 'voicemail_pin_hash' in columns
        assert 'voicemail_pin_salt' in columns
        assert 'password_salt' in columns
        print(f"  Columns present: {columns}")

        # Run create_tables again - should not fail (migration runs internally)
        result = db.create_tables()
        assert result is True
        print("  ✓ Migration ran without errors on existing schema")

        db.disconnect()
        print("✓ Migration handles existing columns gracefully")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def test_insert_with_voicemail_pin():
    """Test that we can insert extensions with voicemail PIN after migration"""
    print("Testing extension insertion with voicemail PIN...")

    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # First, create old schema without voicemail_pin columns
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE extensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            password_hash VARCHAR(255) NOT NULL,
            allow_external BOOLEAN DEFAULT 1,
            ad_synced BOOLEAN DEFAULT 0,
            ad_username VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()

        # Connect with DatabaseBackend to trigger migration
        test_config = Config('config.yml')
        test_config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }

        db = DatabaseBackend(test_config)
        assert db.connect() is True
        assert db.create_tables() is True
        print("  ✓ Migration completed")

        # Now try to insert an extension with voicemail PIN columns
        query = """
        INSERT INTO extensions (number, name, email, password_hash, allow_external,
                              voicemail_pin_hash, voicemail_pin_salt, ad_synced, ad_username)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = ('1001', 'Test User', 'test@example.com', 'hash123', 1,
                  'pin_hash', 'pin_salt', 0, None)

        result = db.execute(query, params)
        assert result is True, "Should be able to insert with voicemail PIN columns"
        print("  ✓ Successfully inserted extension with voicemail PIN")

        # Verify the data was inserted
        verify_query = "SELECT number, name, voicemail_pin_hash, voicemail_pin_salt FROM extensions WHERE number = ?"
        row = db.fetch_one(verify_query, ('1001',))
        assert row is not None, "Extension should be found"
        assert row['number'] == '1001'
        assert row['voicemail_pin_hash'] == 'pin_hash'
        assert row['voicemail_pin_salt'] == 'pin_salt'
        print("  ✓ Data verified in database")

        db.disconnect()
        print("✓ Extension insertion test passed")

    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Running Extensions Table Schema Migration Tests")
    print("=" * 70)
    print()

    tests = [
        test_extensions_columns_migration,
        test_extensions_columns_already_exist,
        test_insert_with_voicemail_pin,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
