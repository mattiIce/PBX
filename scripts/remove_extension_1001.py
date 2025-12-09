#!/usr/bin/env python3
"""
Remove extension 1001 from the database

This script removes the test/false extension 1001 from various database tables
where it may exist as sample data.
"""
import psycopg2
import sys
import os

def get_db_config():
    """Get database configuration from environment variables"""
    try:
        port = int(os.environ.get('DB_PORT', 5432))
    except ValueError:
        print("✗ Error: DB_PORT must be a valid integer")
        sys.exit(1)
    
    password = os.environ.get('DB_PASSWORD')
    if not password:
        print("⚠️  Warning: Using default password from script.")
        password = 'YourSecurePassword123!'  # Default for testing only
    
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': port,
        'database': os.environ.get('DB_NAME', 'pbx_system'),
        'user': os.environ.get('DB_USER', 'pbx_user'),
        'password': password
    }

DB_CONFIG = get_db_config()

def remove_extension_1001():
    """Remove extension 1001 from database tables"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("Checking for extension 1001 in database...")
        print()
        
        # Check and remove from vip_callers table
        cur.execute("""
            SELECT caller_id, name, company 
            FROM vip_callers 
            WHERE direct_extension = '1001'
        """)
        vip_results = cur.fetchall()
        
        if vip_results:
            print(f"Found {len(vip_results)} VIP caller(s) with extension 1001:")
            for caller_id, name, company in vip_results:
                print(f"  - {name} ({company}): {caller_id}")
            
            cur.execute("DELETE FROM vip_callers WHERE direct_extension = '1001'")
            print(f"✓ Removed {len(vip_results)} VIP caller(s) with extension 1001")
        else:
            print("  No VIP callers found with extension 1001")
        
        # Check and remove from extensions table if it exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'extensions'
        """)
        if cur.fetchone():
            cur.execute("""
                SELECT extension_number, name 
                FROM extensions 
                WHERE extension_number = '1001'
            """)
            ext_results = cur.fetchall()
            
            if ext_results:
                print(f"\nFound {len(ext_results)} extension(s) with number 1001:")
                for ext_num, name in ext_results:
                    print(f"  - Extension {ext_num}: {name}")
                
                cur.execute("DELETE FROM extensions WHERE extension_number = '1001'")
                print(f"✓ Removed {len(ext_results)} extension(s) with number 1001")
            else:
                print("  No extensions found with number 1001")
        
        # Check and remove from voicemail mailboxes if exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'voicemail_mailboxes'
        """)
        if cur.fetchone():
            cur.execute("""
                SELECT extension 
                FROM voicemail_mailboxes 
                WHERE extension = '1001'
            """)
            vm_results = cur.fetchall()
            
            if vm_results:
                print(f"\nFound {len(vm_results)} voicemail mailbox(es) for extension 1001")
                cur.execute("DELETE FROM voicemail_mailboxes WHERE extension = '1001'")
                print(f"✓ Removed {len(vm_results)} voicemail mailbox(es) for extension 1001")
            else:
                print("  No voicemail mailboxes found for extension 1001")
        
        conn.commit()
        print()
        print("=" * 60)
        print("✓ Successfully cleaned up extension 1001 from database")
        print("=" * 60)
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error removing extension 1001: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Remove Extension 1001 from Database")
    print("=" * 60)
    print()
    
    if remove_extension_1001():
        sys.exit(0)
    else:
        sys.exit(1)
