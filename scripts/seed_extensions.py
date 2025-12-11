#!/usr/bin/env python3
"""
Seed initial extensions into the database

This script adds default extensions to the database for initial setup.
This is the secure way to initialize extensions instead of using config.yml.

Usage:
    python scripts/seed_extensions.py [--config CONFIG_FILE]
"""
import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, ExtensionDB
from pbx.utils.logger import get_logger
from pbx.utils.encryption import get_encryption


def main():
    parser = argparse.ArgumentParser(
        description='Seed initial extensions into the database'
    )
    parser.add_argument(
        '--config',
        default='config.yml',
        help='Path to config file (default: config.yml)'
    )
    
    args = parser.parse_args()
    logger = get_logger()
    
    print("=" * 70)
    print("Extension Database Seeding")
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
        'database.type': config.get('database.type', 'sqlite'),
        'database.host': config.get('database.host', 'localhost'),
        'database.port': config.get('database.port', 5432),
        'database.name': config.get('database.name', 'pbx_system'),
        'database.user': config.get('database.user', 'pbx_user'),
        'database.password': config.get('database.password', ''),
        'database.path': config.get('database.path', 'pbx.db'),
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
    
    # Initialize extension DB and encryption
    ext_db = ExtensionDB(db)
    fips_mode = config.get('security.fips_mode', True)
    encryption = get_encryption(fips_mode)
    
    # Define default extensions to seed
    # NOTE: These are EXAMPLE extensions for initial setup/testing only.
    # Extension 'webrtc-admin' is the special extension for the browser-based webphone.
    # SECURITY: All extensions must have a voicemail PIN for secure voicemail access.
    # 
    # ⚠️  IMPORTANT: These use placeholder credentials for initial setup.
    # After seeding, you should:
    # 1. Change all passwords immediately via the admin panel
    # 2. Set unique voicemail PINs for each extension
    # 3. Update names and emails to match your organization
    default_extensions = [
        {
            'number': 'webrtc-admin',
            'name': 'Admin WebPhone',
            'email': 'admin@example.com',
            'password': 'CHANGE-THIS-PASSWORD-IMMEDIATELY',  # Will be hashed
            'allow_external': True,
            'voicemail_pin': '9999'  # Change after setup
        },
        {
            'number': '1001',
            'name': 'Extension 1001 (Operator)',
            'email': 'ext1001@example.com',
            'password': 'CHANGE-THIS-PASSWORD-IMMEDIATELY',  # Will be hashed
            'allow_external': True,
            'voicemail_pin': '1001'  # Change after setup
        },
        {
            'number': '1002',
            'name': 'Extension 1002',
            'email': 'ext1002@example.com',
            'password': 'CHANGE-THIS-PASSWORD-IMMEDIATELY',  # Will be hashed
            'allow_external': True,
            'voicemail_pin': '1002'  # Change after setup
        },
        {
            'number': '1003',
            'name': 'Extension 1003',
            'email': 'ext1003@example.com',
            'password': 'CHANGE-THIS-PASSWORD-IMMEDIATELY',  # Will be hashed
            'allow_external': False,
            'voicemail_pin': '1003'  # Change after setup
        },
        {
            'number': '1004',
            'name': 'Extension 1004',
            'email': 'ext1004@example.com',
            'password': 'CHANGE-THIS-PASSWORD-IMMEDIATELY',  # Will be hashed
            'allow_external': True,
            'voicemail_pin': '1004'  # Change after setup
        }
    ]
    
    print(f"Seeding {len(default_extensions)} default extensions...")
    print()
    
    seeded = 0
    skipped = 0
    errors = 0
    
    for ext in default_extensions:
        number = ext['number']
        name = ext['name']
        
        # Check if extension already exists
        existing = ext_db.get(number)
        
        if existing:
            print(f"⚠ Extension {number} ({name}) - Already exists, skipping")
            skipped += 1
            continue
        
        print(f"→ Extension {number} ({name})")
        print(f"  Email: {ext.get('email', '(none)')}")
        print(f"  Allow external: {ext.get('allow_external', True)}")
        
        try:
            # Hash the password using FIPS-compliant encryption
            password_hash, password_salt = encryption.hash_password(ext['password'])
            
            # Add extension to database with hashed password
            success = ext_db.add(
                number=number,
                name=name,
                password_hash=password_hash,
                email=ext.get('email'),
                allow_external=ext.get('allow_external', True),
                voicemail_pin=ext.get('voicemail_pin'),
                ad_synced=False,
                ad_username=None
            )
            
            if success:
                print(f"  ✓ Seeded successfully")
                seeded += 1
            else:
                print(f"  ✗ Failed to seed")
                errors += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors += 1
        
        print()
    
    # Summary
    print("=" * 70)
    print("Seeding Summary")
    print("=" * 70)
    print(f"Seeded:  {seeded}")
    print(f"Skipped: {skipped} (already exist)")
    print(f"Errors:  {errors}")
    print()
    
    if errors > 0:
        print("⚠ Seeding completed with errors")
        print("Check the output above for details")
        sys.exit(1)
    elif seeded > 0:
        print("✓ Seeding completed successfully!")
        print()
        print("Next steps:")
        print("  1. Verify extensions in database:")
        print("     python scripts/list_extensions_from_db.py")
        print()
        print("  2. Start the PBX system:")
        print("     python main.py")
        print()
        print("  3. Test webphone:")
        print("     Open https://localhost:8080/admin/")
        print("     Login with extension 1001")
    else:
        print("✓ All extensions already exist in database")
    
    db.disconnect()


if __name__ == '__main__':
    main()
