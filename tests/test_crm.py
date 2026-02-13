#!/usr/bin/env python3
"""
Comprehensive CRM Integration Tests
Tests CRM integration framework, screen pop support, and specific integrations (HubSpot, Zendesk)
"""

import os
import sys
import unittest
from typing import Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.crm_integration import (
    ActiveDirectoryLookupProvider,
    CallerInfo,
    CRMIntegration,
    CRMLookupProvider,
    PhoneBookLookupProvider,
)
from pbx.features.crm_integrations import HubSpotIntegration, ZendeskIntegration

# ============================================================================
# CRM Framework Tests
# ============================================================================


def test_caller_info_creation() -> bool:
    """Test CallerInfo creation and conversion"""
    print("Testing CallerInfo creation...")

    caller_info = CallerInfo("555-1234")
    caller_info.name = "John Doe"
    caller_info.company = "Acme Corp"
    caller_info.email = "john@acme.com"
    caller_info.tags = ["vip", "sales"]
    caller_info.source = "phone_book"

    # Test to_dict()
    data = caller_info.to_dict()
    assert data["phone_number"] == "555-1234", "Phone number should match"
    assert data["name"] == "John Doe", "Name should match"
    assert data["company"] == "Acme Corp", "Company should match"
    assert data["email"] == "john@acme.com", "Email should match"
    assert len(data["tags"]) == 2, "Should have 2 tags"
    assert data["source"] == "phone_book", "Source should match"

    # Test from_dict()
    caller_info2 = CallerInfo.from_dict(data)
    assert caller_info2.phone_number == caller_info.phone_number, "Phone number should match"
    assert caller_info2.name == caller_info.name, "Name should match"
    assert caller_info2.company == caller_info.company, "Company should match"

    print("✓ CallerInfo creation and conversion works")
    return True


def test_phone_book_lookup_provider() -> bool:
    """Test phone book lookup provider"""
    print("\nTesting PhoneBookLookupProvider...")

    # Mock phone book
    class MockPhoneBook:
        def search_contacts(self, query: str) -> list[dict[str, str]]:
            if "555-1234" in query:
                return [
                    {
                        "name": "Jane Smith",
                        "company": "Tech Inc",
                        "email": "jane@tech.com",
                        "phone": "555-1234",
                    }
                ]
            return []

    config = {"enabled": True, "name": "PhoneBook"}
    provider = PhoneBookLookupProvider(config, MockPhoneBook())

    # Test successful lookup
    result = provider.lookup("555-1234")
    assert result is not None, "Should find caller"
    assert result.name == "Jane Smith", "Name should match"
    assert result.company == "Tech Inc", "Company should match"
    assert result.source == "phone_book", "Source should be phone_book"

    # Test not found
    result = provider.lookup("999-9999")
    assert result is None, "Should not find caller"

    print("✓ PhoneBookLookupProvider works")
    return True


def test_active_directory_lookup_provider() -> bool:
    """Test Active Directory lookup provider"""
    print("\nTesting ActiveDirectoryLookupProvider...")

    # Mock AD integration
    class MockADIntegration:
        def search_users(self, query: str) -> list[dict[str, str]]:
            if "555-5678" in query:
                return [
                    {
                        "displayName": "Bob Johnson",
                        "mail": "bob@company.com",
                        "company": "Company Inc",
                        "telephoneNumber": "555-5678",
                    }
                ]
            return []

    config = {"enabled": True, "name": "ActiveDirectory"}
    provider = ActiveDirectoryLookupProvider(config, MockADIntegration())

    # Test successful lookup
    result = provider.lookup("555-5678")
    assert result is not None, "Should find user"
    assert result.name == "Bob Johnson", "Name should match"
    assert result.email == "bob@company.com", "Email should match"
    assert result.source == "active_directory", "Source should be active_directory"

    # Test not found
    result = provider.lookup("999-9999")
    assert result is None, "Should not find user"

    print("✓ ActiveDirectoryLookupProvider works")
    return True


def test_crm_integration_initialization() -> bool:
    """Test CRM integration initialization"""
    print("\nTesting CRM integration initialization...")

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.crm_integration.enabled": True,
                "features.crm_integration.cache_enabled": True,
                "features.crm_integration.cache_timeout": 3600,
                "features.crm_integration.providers": [],
            }
            return config_map.get(key, default)

    config = MockConfig()
    crm = CRMIntegration(config)

    assert crm.enabled, "Should be enabled"
    assert crm.cache_enabled, "Cache should be enabled"
    assert crm.cache_timeout == 3600, "Cache timeout should be 3600"

    print("✓ CRM integration initialization works")
    return True


def test_crm_integration_lookup() -> bool:
    """Test CRM integration lookup with multiple providers"""
    print("\nTesting CRM integration lookup...")

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.crm_integration.enabled": True,
                "features.crm_integration.cache_enabled": False,  # Disable cache for test
                "features.crm_integration.providers": [],
            }
            return config_map.get(key, default)

    class MockPBXCore:
        pass

    config = MockConfig()
    pbx_core = MockPBXCore()
    crm = CRMIntegration(config, pbx_core)

    # Add mock provider
    class MockProvider(CRMLookupProvider):
        def __init__(self) -> None:
            super().__init__({"enabled": True, "name": "Mock"})

        def lookup(self, phone_number: str) -> CallerInfo | None:
            if phone_number == "5551234":  # Normalized
                caller_info = CallerInfo(phone_number)
                caller_info.name = "Test User"
                caller_info.source = "mock"
                return caller_info
            return None

    crm.providers.append(MockProvider())

    # Test successful lookup
    result = crm.lookup_caller("555-1234")  # Will be normalized to 5551234
    assert result is not None, "Should find caller"
    assert result.name == "Test User", "Name should match"
    assert result.source == "mock", "Source should be mock"

    # Test not found
    result = crm.lookup_caller("999-9999")
    assert result is None, "Should not find caller"

    print("✓ CRM integration lookup works")
    return True


def test_crm_integration_cache() -> bool:
    """Test CRM integration caching"""
    print("\nTesting CRM integration cache...")

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.crm_integration.enabled": True,
                "features.crm_integration.cache_enabled": True,
                "features.crm_integration.cache_timeout": 3600,
                "features.crm_integration.providers": [],
            }
            return config_map.get(key, default)

    config = MockConfig()
    crm = CRMIntegration(config)

    # Add mock provider
    class MockProvider(CRMLookupProvider):
        def __init__(self) -> None:
            super().__init__({"enabled": True, "name": "Mock"})
            self.lookup_count = 0

        def lookup(self, phone_number: str) -> CallerInfo | None:
            self.lookup_count += 1
            if phone_number == "5559999":
                caller_info = CallerInfo(phone_number)
                caller_info.name = "Cached User"
                return caller_info
            return None

    provider = MockProvider()
    crm.providers.append(provider)

    # First lookup (should call provider)
    result1 = crm.lookup_caller("555-9999")
    assert result1 is not None, "Should find caller"
    assert provider.lookup_count == 1, "Should call provider once"

    # Second lookup (should use cache)
    result2 = crm.lookup_caller("555-9999")
    assert result2 is not None, "Should find caller"
    assert provider.lookup_count == 1, "Should not call provider again (cached)"
    assert result2.name == result1.name, "Results should match"

    # Clear cache
    crm.clear_cache()

    # Third lookup (should call provider again)
    result3 = crm.lookup_caller("555-9999")
    assert result3 is not None, "Should find caller"
    assert provider.lookup_count == 2, "Should call provider again after cache clear"

    print("✓ CRM integration cache works")
    return True


def test_screen_pop_trigger() -> bool:
    """Test screen pop triggering"""
    print("\nTesting screen pop trigger...")

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.crm_integration.enabled": True,
                "features.crm_integration.providers": [],
            }
            return config_map.get(key, default)

    class MockWebhookSystem:
        def __init__(self) -> None:
            self.last_event: str | None = None
            self.last_data: dict[str, Any] | None = None

        def trigger_event(self, event_type: str, data: dict[str, Any]) -> None:
            self.last_event = event_type
            self.last_data = data

    class MockPBXCore:
        def __init__(self) -> None:
            self.webhook_system = MockWebhookSystem()

    config = MockConfig()
    pbx_core = MockPBXCore()
    crm = CRMIntegration(config, pbx_core)

    # Add mock provider
    class MockProvider(CRMLookupProvider):
        def __init__(self) -> None:
            super().__init__({"enabled": True, "name": "Mock"})

        def lookup(self, phone_number: str) -> CallerInfo:
            caller_info = CallerInfo(phone_number)
            caller_info.name = "Screen Pop Test"
            return caller_info

    crm.providers.append(MockProvider())

    # Trigger screen pop
    crm.trigger_screen_pop("555-1111", "call-123", "1001")

    # Verify webhook was triggered
    assert pbx_core.webhook_system.last_event == "crm.screen_pop", "Should trigger screen_pop event"
    assert pbx_core.webhook_system.last_data is not None, "Should have data"
    assert pbx_core.webhook_system.last_data["call_id"] == "call-123", "Call ID should match"
    assert pbx_core.webhook_system.last_data["phone_number"] == "555-1111", "Phone should match"
    assert pbx_core.webhook_system.last_data["extension"] == "1001", "Extension should match"
    assert pbx_core.webhook_system.last_data["caller_info"] is not None, "Should have caller info"

    print("✓ Screen pop trigger works")
    return True


def test_phone_number_normalization() -> bool:
    """Test phone number normalization"""
    print("\nTesting phone number normalization...")

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            return {}.get(key, default)

    crm = CRMIntegration(MockConfig())

    # Test various formats
    assert crm._normalize_phone_number("555-1234") == "5551234", "Should remove dashes"
    assert (
        crm._normalize_phone_number("(555) 123-4567") == "5551234567"
    ), "Should remove parens and spaces"
    assert (
        crm._normalize_phone_number("+1-555-123-4567") == "15551234567"
    ), "Should remove plus and dashes"
    assert crm._normalize_phone_number("555 123 4567") == "5551234567", "Should remove spaces"

    print("✓ Phone number normalization works")
    return True


def test_provider_status() -> bool:
    """Test getting provider status"""
    print("\nTesting provider status...")

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            config_map = {
                "features.crm_integration.enabled": True,
                "features.crm_integration.providers": [],
            }
            return config_map.get(key, default)

    config = MockConfig()
    crm = CRMIntegration(config)

    # Add mock providers
    class MockProvider1(CRMLookupProvider):
        def __init__(self) -> None:
            super().__init__({"enabled": True, "name": "Provider1"})

        def lookup(self, phone_number: str) -> None:
            return None

    class MockProvider2(CRMLookupProvider):
        def __init__(self) -> None:
            super().__init__({"enabled": True, "name": "Provider2"})

        def lookup(self, phone_number: str) -> None:
            return None

    crm.providers.append(MockProvider1())
    crm.providers.append(MockProvider2())

    status = crm.get_provider_status()

    assert len(status) == 2, "Should have 2 providers"
    assert status[0]["name"] == "Provider1", "First provider name should match"
    assert status[0]["enabled"], "First provider should be enabled"
    assert status[1]["name"] == "Provider2", "Second provider name should match"

    print("✓ Provider status works")
    return True


# ============================================================================
# Specific CRM Integration Tests (HubSpot, Zendesk)
# ============================================================================


class TestHubSpotIntegration(unittest.TestCase):
    """Test HubSpot integration functionality"""

    def setUp(self) -> None:
        """Set up test database"""
        import sqlite3

        class MockDB:
            def __init__(self) -> None:
                self.db_type = "sqlite"
                self.conn = sqlite3.connect(":memory:")
                self.enabled = True

            def execute(self, query: str, params: Any = None) -> list[Any]:
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor.fetchall()

            def disconnect(self) -> None:
                self.conn.close()

        self.db = MockDB()

        # Create tables
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS hubspot_integration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled INTEGER DEFAULT 0,
                api_key_encrypted TEXT,
                portal_id TEXT,
                sync_contacts INTEGER DEFAULT 0,
                sync_deals INTEGER DEFAULT 0,
                auto_create_contacts INTEGER DEFAULT 0,
                webhook_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS integration_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration_type TEXT,
                action TEXT,
                status TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.config = {}
        self.integration = HubSpotIntegration(self.db, self.config)

    def tearDown(self) -> None:
        """Clean up test database"""
        self.db.disconnect()

    def test_initialization(self) -> None:
        """Test integration initialization"""
        self.assertIsNotNone(self.integration)
        self.assertFalse(self.integration.enabled)

    def test_update_config(self) -> None:
        """Test updating configuration"""
        config = {
            "enabled": True,
            "api_key": "test-key-123",
            "portal_id": "12345",
            "webhook_url": "https://webhook.example.com/hubspot",
        }

        result = self.integration.update_config(config)
        self.assertTrue(result)

    def test_get_config(self) -> None:
        """Test retrieving configuration"""
        # First create a config
        config = {"enabled": True, "api_key": "test-key-456", "portal_id": "67890"}
        self.integration.update_config(config)

        # Now retrieve it
        retrieved = self.integration.get_config()
        self.assertIsNotNone(retrieved)
        self.assertTrue(retrieved["enabled"])
        self.assertEqual(retrieved["portal_id"], "67890")

    def test_sync_contact_disabled(self) -> None:
        """Test sync contact when integration is disabled"""
        contact = {"email": "test@example.com", "first_name": "John", "last_name": "Doe"}

        result = self.integration.sync_contact(contact)
        self.assertFalse(result)

    def test_create_deal_disabled(self) -> None:
        """Test create deal when integration is disabled"""
        deal = {"dealname": "Test Deal", "amount": 1000}

        result = self.integration.create_deal(deal)
        self.assertFalse(result)


class TestZendeskIntegration(unittest.TestCase):
    """Test Zendesk integration functionality"""

    def setUp(self) -> None:
        """Set up test database"""
        import sqlite3

        class MockDB:
            def __init__(self) -> None:
                self.db_type = "sqlite"
                self.conn = sqlite3.connect(":memory:")
                self.enabled = True

            def execute(self, query: str, params: Any = None) -> list[Any]:
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor.fetchall()

            def disconnect(self) -> None:
                self.conn.close()

        self.db = MockDB()

        # Create tables
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS zendesk_integration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled INTEGER DEFAULT 0,
                subdomain TEXT,
                api_token_encrypted TEXT,
                email TEXT,
                auto_create_tickets INTEGER DEFAULT 0,
                default_priority TEXT DEFAULT 'normal',
                webhook_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS integration_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration_type TEXT,
                action TEXT,
                status TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.config = {}
        self.integration = ZendeskIntegration(self.db, self.config)

    def tearDown(self) -> None:
        """Clean up test database"""
        self.db.disconnect()

    def test_initialization(self) -> None:
        """Test integration initialization"""
        self.assertIsNotNone(self.integration)
        self.assertFalse(self.integration.enabled)

    def test_update_config(self) -> None:
        """Test updating configuration"""
        config = {
            "enabled": True,
            "subdomain": "testcompany",
            "api_token": "test-token-123",
            "email": "admin@example.com",
            "default_priority": "high",
            "webhook_url": "https://webhook.example.com/zendesk",
        }

        result = self.integration.update_config(config)
        self.assertTrue(result)

    def test_get_config(self) -> None:
        """Test retrieving configuration"""
        # First create a config
        config = {
            "enabled": True,
            "subdomain": "mycompany",
            "api_token": "token-456",
            "email": "support@example.com",
        }
        self.integration.update_config(config)

        # Now retrieve it
        retrieved = self.integration.get_config()
        self.assertIsNotNone(retrieved)
        self.assertTrue(retrieved["enabled"])
        self.assertEqual(retrieved["subdomain"], "mycompany")

    def test_create_ticket_disabled(self) -> None:
        """Test create ticket when integration is disabled"""
        ticket = {
            "subject": "Test Ticket",
            "description": "This is a test",
            "requester_email": "customer@example.com",
        }

        result = self.integration.create_ticket(ticket)
        self.assertIsNone(result)

    def test_update_ticket_disabled(self) -> None:
        """Test update ticket when integration is disabled"""
        result = self.integration.update_ticket("123", {"status": "solved"})
        self.assertFalse(result)

    def test_activity_logging(self) -> None:
        """Test that integration activity is logged"""
        # Enable integration
        config = {
            "enabled": True,
            "subdomain": "testco",
            "api_token": "token",
            "email": "test@test.com",
        }
        self.integration.update_config(config)

        # Try to create a ticket (will fail without real API, but should log)
        ticket = {"subject": "Test", "description": "Test ticket"}
        self.integration.create_ticket(ticket)

        # Check activity log
        logs = self.db.execute("SELECT * FROM integration_activity_log")
        self.assertGreater(len(logs), 0)


# ============================================================================
# Test Runner
# ============================================================================


def run_framework_tests() -> bool:
    """Run CRM framework tests"""
    print("=" * 70)
    print("Testing CRM Integration Framework")
    print("=" * 70)

    results = []
    results.append(test_caller_info_creation())
    results.append(test_phone_book_lookup_provider())
    results.append(test_active_directory_lookup_provider())
    results.append(test_crm_integration_initialization())
    results.append(test_crm_integration_lookup())
    results.append(test_crm_integration_cache())
    results.append(test_screen_pop_trigger())
    results.append(test_phone_number_normalization())
    results.append(test_provider_status())

    print("\n" + "=" * 70)
    if all(results):
        print(f"✅ All CRM framework tests passed! ({len(results)}/{len(results)})")
        return True
    else:
        print(f"❌ Some tests failed ({sum(results)}/{len(results)} passed)")
        return False


def run_integration_tests() -> bool:
    """Run specific CRM integration tests (HubSpot, Zendesk)"""
    print("\n" + "=" * 70)
    print("Testing Specific CRM Integrations (HubSpot, Zendesk)")
    print("=" * 70 + "\n")

    # Create test suite
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHubSpotIntegration))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestZendeskIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    # Run framework tests
    framework_success = run_framework_tests()

    # Run integration tests
    integration_success = run_integration_tests()

    # Exit with appropriate code
    success = framework_success and integration_success
    sys.exit(0 if success else 1)
