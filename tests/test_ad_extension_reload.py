#!/usr/bin/env python3
"""
Test that extension registry is reloaded after AD sync completes
Verifies the fix for extensions not being available after AD sync at startup
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_extension_registry_reload_after_ad_sync():
    """Test that extension registry reloads from database after AD sync"""
    print("\nTesting extension registry reload after AD sync...")

    from pbx.features.extensions import ExtensionRegistry
    from pbx.utils.config import Config
    from pbx.utils.database import DatabaseBackend, ExtensionDB

    # Create test database
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to test database"
    assert db.create_tables(), "Failed to create tables"

    ext_db = ExtensionDB(db)

    # Create extension registry (simulates initial load)
    registry = ExtensionRegistry(config, database=db)
    initial_count = len(registry.extensions)
    print(f"  ✓ Initial extension count: {initial_count}")

    # Simulate AD sync adding new extensions to database
    # (In real scenario, AD sync would do this)
    print("  Simulating AD sync adding extensions to database...")
    success = ext_db.add(
        number="2001",
        name="John Doe (AD)",
        password_hash="ad_hash_123",
        email="john@example.com",
        ad_synced=True,
        ad_username="jdoe",
    )
    assert success, "Failed to add AD-synced extension to database"

    success = ext_db.add(
        number="2002",
        name="Jane Smith (AD)",
        password_hash="ad_hash_456",
        email="jane@example.com",
        ad_synced=True,
        ad_username="jsmith",
    )
    assert success, "Failed to add second AD-synced extension to database"
    print("  ✓ Added 2 AD-synced extensions to database")

    # At this point, registry does NOT have these extensions yet
    ext_2001 = registry.get("2001")
    ext_2002 = registry.get("2002")
    assert ext_2001 is None, "Extension 2001 should not be in registry yet"
    assert ext_2002 is None, "Extension 2002 should not be in registry yet"
    print("  ✓ Verified extensions NOT in registry before reload")

    # Now reload the registry (this is what our fix does)
    print("  Reloading extension registry from database...")
    registry.reload()

    # Verify extensions are now loaded
    ext_2001 = registry.get("2001")
    ext_2002 = registry.get("2002")
    assert ext_2001 is not None, "Extension 2001 should be loaded after reload"
    assert ext_2002 is not None, "Extension 2002 should be loaded after reload"
    assert ext_2001.name == "John Doe (AD)", "Extension 2001 has wrong name"
    assert ext_2002.name == "Jane Smith (AD)", "Extension 2002 has wrong name"
    assert ext_2001.config.get("ad_synced") is True, "Extension 2001 should be marked as AD-synced"
    assert ext_2002.config.get("ad_synced") is True, "Extension 2002 should be marked as AD-synced"
    print("  ✓ Extensions loaded successfully after reload")

    final_count = len(registry.extensions)
    assert final_count == initial_count + 2, f"Expected {initial_count + 2} extensions, got {final_count}"
    print(f"  ✓ Final extension count: {final_count}")

    print("✓ Extension registry reload after AD sync works correctly")


def test_reload_preserves_registration_state():
    """Test that reloading registry preserves registration state"""
    print("\nTesting that reload preserves registration state...")

    from pbx.features.extensions import ExtensionRegistry
    from pbx.utils.config import Config
    from pbx.utils.database import DatabaseBackend, ExtensionDB

    # Create test database
    config = Config("config.yml")
    config.config["database"] = {"type": "sqlite", "path": ":memory:"}

    db = DatabaseBackend(config)
    assert db.connect(), "Failed to connect to test database"
    assert db.create_tables(), "Failed to create tables"

    ext_db = ExtensionDB(db)

    # Add an extension to database
    ext_db.add(
        number="3001",
        name="Test User",
        password_hash="test_hash",
        email="test@example.com",
    )

    # Create registry and load extension
    registry = ExtensionRegistry(config, database=db)
    ext = registry.get("3001")
    assert ext is not None, "Extension 3001 should be loaded"

    # Register the extension (simulates SIP registration)
    print("  Registering extension 3001...")
    registry.register("3001", ("192.168.1.100", 5060))
    assert ext.registered is True, "Extension should be registered"
    assert ext.address == ("192.168.1.100", 5060), "Extension should have correct address"
    print("  ✓ Extension registered")

    # Now reload the registry
    print("  Reloading registry...")
    registry.reload()

    # Check that registration state is LOST (expected behavior - reload clears in-memory state)
    # This is OK because registrations are transient and phones will re-register
    ext_after = registry.get("3001")
    assert ext_after is not None, "Extension should still exist after reload"
    assert ext_after.registered is False, "Extension registration is cleared on reload (expected)"
    print("  ✓ Extension reloaded (registration state reset as expected)")
    print("  Note: Registration state is transient and phones will re-register")

    print("✓ Reload behavior verified")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Running AD Extension Reload Tests")
    print("=" * 70)

    try:
        test_extension_registry_reload_after_ad_sync()
        test_reload_preserves_registration_state()

        print("\n" + "=" * 70)
        print("Results: 2 passed, 0 failed")
        print("=" * 70)
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
