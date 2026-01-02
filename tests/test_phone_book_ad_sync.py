#!/usr/bin/env python3
"""
Test phone book auto-sync from Active Directory
Tests that phone book automatically syncs after AD user sync completes
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_phone_book_auto_sync_after_ad_sync():
    """Test that phone book automatically syncs after AD user sync"""
    print("\nTesting phone book auto-sync after AD user sync...")

    # Create mock components
    class MockDatabase:
        def __init__(self):
            self.enabled = True
            self.db_type = "sqlite"
            self.extensions = []

        def fetch_all(self, query, params=None):
            """Mock fetch_all for extensions table"""
            if "extensions" in query and "ad_synced" in query:
                # Return AD-synced extensions
                return [
                    {
                        "number": "1001",
                        "name": "John Doe",
                        "email": "john@example.com",
                        "ad_synced": True,
                    },
                    {
                        "number": "1002",
                        "name": "Jane Smith",
                        "email": "jane@example.com",
                        "ad_synced": True,
                    },
                ]
            elif "phone_book" in query:
                # Return existing phone book entries
                return []
            return []

        def execute(self, query, params=None):
            """Mock execute for INSERT/UPDATE"""
            return True

        def _execute_with_context(self, query, context, params=None, critical=True):
            """Mock execute with context"""
            return True

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                "features.phone_book.enabled": True,
                "features.phone_book.auto_sync_from_ad": True,
            }
            return config_map.get(key, default)

    class MockExtensionRegistry:
        def __init__(self):
            self.extensions = {}

        def get_all(self):
            return []

    class MockADIntegration:
        def __init__(self):
            self.enabled = True

    # Test the phone book initialization and sync
    from pbx.features.phone_book import PhoneBook

    database = MockDatabase()
    config = MockConfig()
    phone_book = PhoneBook(config, database)

    # Verify phone book is enabled and auto_sync_from_ad is True
    assert phone_book.enabled, "Phone book should be enabled"
    assert phone_book.auto_sync_from_ad, "Auto sync from AD should be enabled"

    # Simulate AD sync completing and triggering phone book sync
    ad_integration = MockADIntegration()
    extension_registry = MockExtensionRegistry()

    synced_count = phone_book.sync_from_ad(ad_integration, extension_registry)

    # Verify that phone book synced entries
    assert synced_count == 2, f"Should have synced 2 entries, got {synced_count}"
    assert (
        len(phone_book.entries) == 2
    ), f"Should have 2 entries in phone book, got {
        len(
            phone_book.entries)}"

    # Verify the entries are correct
    assert "1001" in phone_book.entries, "Extension 1001 should be in phone book"
    assert "1002" in phone_book.entries, "Extension 1002 should be in phone book"
    assert phone_book.entries["1001"]["name"] == "John Doe", "Name should match"
    assert phone_book.entries["1002"]["name"] == "Jane Smith", "Name should match"

    print("✓ Phone book auto-sync after AD sync works correctly")
    return True


def test_phone_book_sync_disabled():
    """Test that phone book sync doesn't happen when auto_sync_from_ad is disabled"""
    print("\nTesting phone book sync when auto_sync_from_ad is disabled...")

    class MockDatabase:
        def __init__(self):
            self.enabled = True
            self.db_type = "sqlite"

        def fetch_all(self, query, params=None):
            return []

        def execute(self, query, params=None):
            return True

        def _execute_with_context(self, query, context, params=None, critical=True):
            return True

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                "features.phone_book.enabled": True,
                "features.phone_book.auto_sync_from_ad": False,  # Disabled
            }
            return config_map.get(key, default)

    class MockExtensionRegistry:
        def get_all(self):
            return []

    class MockADIntegration:
        def __init__(self):
            self.enabled = True

    from pbx.features.phone_book import PhoneBook

    database = MockDatabase()
    config = MockConfig()
    phone_book = PhoneBook(config, database)

    # Verify auto_sync_from_ad is disabled
    assert phone_book.auto_sync_from_ad is False, "Auto sync should be disabled"

    # Try to sync - should return 0
    ad_integration = MockADIntegration()
    extension_registry = MockExtensionRegistry()

    synced_count = phone_book.sync_from_ad(ad_integration, extension_registry)

    # Should return 0 when auto_sync_from_ad is disabled
    assert synced_count == 0, f"Should return 0 when disabled, got {synced_count}"

    print("✓ Phone book respects auto_sync_from_ad setting")
    return True


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Testing Phone Book Auto-Sync from Active Directory")
    print("=" * 70)

    results = []
    results.append(test_phone_book_auto_sync_after_ad_sync())
    results.append(test_phone_book_sync_disabled())

    print("\n" + "=" * 70)
    if all(results):
        print(f"✅ All phone book AD sync tests passed! ({len(results)}/{len(results)})")
        return True
    else:
        print(f"❌ Some tests failed ({sum(results)}/{len(results)} passed)")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
