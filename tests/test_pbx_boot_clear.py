#!/usr/bin/env python3
"""
Integration test to verify PBX clears registered phones on boot
"""
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.core.pbx import PBXCore
from pbx.utils.database import RegisteredPhonesDB


def test_pbx_clears_phones_on_boot():
    """Test that PBX clears registered phones table on boot"""
    print("Testing PBX clears phones on boot...")
    
    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    
    try:
        # Create a minimal test config
        config_content = f"""
server:
  sip_host: 127.0.0.1
  sip_port: 15060
  rtp_port_range_start: 20000
  rtp_port_range_end: 20100

database:
  type: sqlite
  path: {db_path}

api:
  host: 127.0.0.1
  port: 18080

logging:
  level: INFO
  console: false
  file: {os.path.join(temp_dir, 'test.log')}

extensions: []
"""
        config_path = os.path.join(temp_dir, 'test_config.yml')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Create first PBX instance and register some phones
        pbx1 = PBXCore(config_path)
        
        # Verify database is available
        assert pbx1.database.enabled, "Database not enabled"
        assert pbx1.registered_phones_db is not None, "Registered phones DB not initialized"
        
        # Register some phones directly in the database
        pbx1.registered_phones_db.register_phone("1001", "192.168.1.100", "001565123456")
        pbx1.registered_phones_db.register_phone("1002", "192.168.1.101", "001565123457")
        
        # Verify phones were registered
        phones = pbx1.registered_phones_db.list_all()
        assert len(phones) == 2, f"Expected 2 phones, got {len(phones)}"
        print(f"  Registered {len(phones)} phones")
        
        # Stop the PBX (simulating shutdown)
        pbx1.stop()
        
        # Create a new PBX instance (simulating server restart)
        pbx2 = PBXCore(config_path)
        
        # Start the PBX (this should clear the phones table)
        success = pbx2.start()
        assert success, "Failed to start PBX"
        
        # Verify phones table was cleared
        phones = pbx2.registered_phones_db.list_all()
        assert len(phones) == 0, f"Expected 0 phones after boot, got {len(phones)}"
        print(f"  Phones cleared on boot: {len(phones)} phones remaining")
        
        # Stop the PBX
        pbx2.stop()
        
        print("✓ PBX clears registered phones on boot")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("Running PBX Boot Clear Integration Test")
    print("=" * 60)
    
    try:
        test_pbx_clears_phones_on_boot()
        
        print("=" * 60)
        print("Results: 1 passed, 0 failed")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
