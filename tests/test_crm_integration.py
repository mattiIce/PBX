#!/usr/bin/env python3
"""
Test CRM integration and screen pop support
"""
import os
import sys
from datetime import datetime

from pbx.features.crm_integration import (
    ActiveDirectoryLookupProvider,
    CallerInfo,
    CRMIntegration,
    CRMLookupProvider,
    ExternalCRMLookupProvider,
    PhoneBookLookupProvider,
)

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_caller_info_creation():
    """Test CallerInfo creation and conversion"""
    print("Testing CallerInfo creation...")

    caller_info = CallerInfo('555-1234')
    caller_info.name = 'John Doe'
    caller_info.company = 'Acme Corp'
    caller_info.email = 'john@acme.com'
    caller_info.tags = ['vip', 'sales']
    caller_info.source = 'phone_book'

    # Test to_dict()
    data = caller_info.to_dict()
    assert data['phone_number'] == '555-1234', "Phone number should match"
    assert data['name'] == 'John Doe', "Name should match"
    assert data['company'] == 'Acme Corp', "Company should match"
    assert data['email'] == 'john@acme.com', "Email should match"
    assert len(data['tags']) == 2, "Should have 2 tags"
    assert data['source'] == 'phone_book', "Source should match"

    # Test from_dict()
    caller_info2 = CallerInfo.from_dict(data)
    assert caller_info2.phone_number == caller_info.phone_number, "Phone number should match"
    assert caller_info2.name == caller_info.name, "Name should match"
    assert caller_info2.company == caller_info.company, "Company should match"

    print("✓ CallerInfo creation and conversion works")
    return True


def test_phone_book_lookup_provider():
    """Test phone book lookup provider"""
    print("\nTesting PhoneBookLookupProvider...")

    # Mock phone book
    class MockPhoneBook:
        def search_contacts(self, query):
            if '555-1234' in query:
                return [{
                    'name': 'Jane Smith',
                    'company': 'Tech Inc',
                    'email': 'jane@tech.com',
                    'phone': '555-1234'
                }]
            return []

    config = {'enabled': True, 'name': 'PhoneBook'}
    provider = PhoneBookLookupProvider(config, MockPhoneBook())

    # Test successful lookup
    result = provider.lookup('555-1234')
    assert result is not None, "Should find caller"
    assert result.name == 'Jane Smith', "Name should match"
    assert result.company == 'Tech Inc', "Company should match"
    assert result.source == 'phone_book', "Source should be phone_book"

    # Test not found
    result = provider.lookup('999-9999')
    assert result is None, "Should not find caller"

    print("✓ PhoneBookLookupProvider works")
    return True


def test_active_directory_lookup_provider():
    """Test Active Directory lookup provider"""
    print("\nTesting ActiveDirectoryLookupProvider...")

    # Mock AD integration
    class MockADIntegration:
        def search_users(self, query):
            if '555-5678' in query:
                return [{
                    'displayName': 'Bob Johnson',
                    'mail': 'bob@company.com',
                    'company': 'Company Inc',
                    'telephoneNumber': '555-5678'
                }]
            return []

    config = {'enabled': True, 'name': 'ActiveDirectory'}
    provider = ActiveDirectoryLookupProvider(config, MockADIntegration())

    # Test successful lookup
    result = provider.lookup('555-5678')
    assert result is not None, "Should find user"
    assert result.name == 'Bob Johnson', "Name should match"
    assert result.email == 'bob@company.com', "Email should match"
    assert result.source == 'active_directory', "Source should be active_directory"

    # Test not found
    result = provider.lookup('999-9999')
    assert result is None, "Should not find user"

    print("✓ ActiveDirectoryLookupProvider works")
    return True


def test_crm_integration_initialization():
    """Test CRM integration initialization"""
    print("\nTesting CRM integration initialization...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.crm_integration.enabled': True,
                'features.crm_integration.cache_enabled': True,
                'features.crm_integration.cache_timeout': 3600,
                'features.crm_integration.providers': []
            }
            return config_map.get(key, default)

    config = MockConfig()
    crm = CRMIntegration(config)

    assert crm.enabled, "Should be enabled"
    assert crm.cache_enabled, "Cache should be enabled"
    assert crm.cache_timeout == 3600, "Cache timeout should be 3600"

    print("✓ CRM integration initialization works")
    return True


def test_crm_integration_lookup():
    """Test CRM integration lookup with multiple providers"""
    print("\nTesting CRM integration lookup...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.crm_integration.enabled': True,
                'features.crm_integration.cache_enabled': False,  # Disable cache for test
                'features.crm_integration.providers': []
            }
            return config_map.get(key, default)

    class MockPBXCore:
        pass

    config = MockConfig()
    pbx_core = MockPBXCore()
    crm = CRMIntegration(config, pbx_core)

    # Add mock provider
    class MockProvider(CRMLookupProvider):
        def __init__(self):
            super().__init__({'enabled': True, 'name': 'Mock'})

        def lookup(self, phone_number):
            if phone_number == '5551234':  # Normalized
                caller_info = CallerInfo(phone_number)
                caller_info.name = 'Test User'
                caller_info.source = 'mock'
                return caller_info
            return None

    crm.providers.append(MockProvider())

    # Test successful lookup
    result = crm.lookup_caller('555-1234')  # Will be normalized to 5551234
    assert result is not None, "Should find caller"
    assert result.name == 'Test User', "Name should match"
    assert result.source == 'mock', "Source should be mock"

    # Test not found
    result = crm.lookup_caller('999-9999')
    assert result is None, "Should not find caller"

    print("✓ CRM integration lookup works")
    return True


def test_crm_integration_cache():
    """Test CRM integration caching"""
    print("\nTesting CRM integration cache...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.crm_integration.enabled': True,
                'features.crm_integration.cache_enabled': True,
                'features.crm_integration.cache_timeout': 3600,
                'features.crm_integration.providers': []
            }
            return config_map.get(key, default)

    config = MockConfig()
    crm = CRMIntegration(config)

    # Add mock provider
    class MockProvider(CRMLookupProvider):
        def __init__(self):
            super().__init__({'enabled': True, 'name': 'Mock'})
            self.lookup_count = 0

        def lookup(self, phone_number):
            self.lookup_count += 1
            if phone_number == '5559999':
                caller_info = CallerInfo(phone_number)
                caller_info.name = 'Cached User'
                return caller_info
            return None

    provider = MockProvider()
    crm.providers.append(provider)

    # First lookup (should call provider)
    result1 = crm.lookup_caller('555-9999')
    assert result1 is not None, "Should find caller"
    assert provider.lookup_count == 1, "Should call provider once"

    # Second lookup (should use cache)
    result2 = crm.lookup_caller('555-9999')
    assert result2 is not None, "Should find caller"
    assert provider.lookup_count == 1, "Should not call provider again (cached)"
    assert result2.name == result1.name, "Results should match"

    # Clear cache
    crm.clear_cache()

    # Third lookup (should call provider again)
    result3 = crm.lookup_caller('555-9999')
    assert result3 is not None, "Should find caller"
    assert provider.lookup_count == 2, "Should call provider again after cache clear"

    print("✓ CRM integration cache works")
    return True


def test_screen_pop_trigger():
    """Test screen pop triggering"""
    print("\nTesting screen pop trigger...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.crm_integration.enabled': True,
                'features.crm_integration.providers': []
            }
            return config_map.get(key, default)

    class MockWebhookSystem:
        def __init__(self):
            self.last_event = None
            self.last_data = None

        def trigger_event(self, event_type, data):
            self.last_event = event_type
            self.last_data = data

    class MockPBXCore:
        def __init__(self):
            self.webhook_system = MockWebhookSystem()

    config = MockConfig()
    pbx_core = MockPBXCore()
    crm = CRMIntegration(config, pbx_core)

    # Add mock provider
    class MockProvider(CRMLookupProvider):
        def __init__(self):
            super().__init__({'enabled': True, 'name': 'Mock'})

        def lookup(self, phone_number):
            caller_info = CallerInfo(phone_number)
            caller_info.name = 'Screen Pop Test'
            return caller_info

    crm.providers.append(MockProvider())

    # Trigger screen pop
    crm.trigger_screen_pop('555-1111', 'call-123', '1001')

    # Verify webhook was triggered
    assert pbx_core.webhook_system.last_event == 'crm.screen_pop', "Should trigger screen_pop event"
    assert pbx_core.webhook_system.last_data is not None, "Should have data"
    assert pbx_core.webhook_system.last_data['call_id'] == 'call-123', "Call ID should match"
    assert pbx_core.webhook_system.last_data['phone_number'] == '555-1111', "Phone should match"
    assert pbx_core.webhook_system.last_data['extension'] == '1001', "Extension should match"
    assert pbx_core.webhook_system.last_data['caller_info'] is not None, "Should have caller info"

    print("✓ Screen pop trigger works")
    return True


def test_phone_number_normalization():
    """Test phone number normalization"""
    print("\nTesting phone number normalization...")

    class MockConfig:
        def get(self, key, default=None):
            return {}.get(key, default)

    crm = CRMIntegration(MockConfig())

    # Test various formats
    assert crm._normalize_phone_number(
        '555-1234') == '5551234', "Should remove dashes"
    assert crm._normalize_phone_number(
        '(555) 123-4567') == '5551234567', "Should remove parens and spaces"
    assert crm._normalize_phone_number(
        '+1-555-123-4567') == '15551234567', "Should remove plus and dashes"
    assert crm._normalize_phone_number(
        '555 123 4567') == '5551234567', "Should remove spaces"

    print("✓ Phone number normalization works")
    return True


def test_provider_status():
    """Test getting provider status"""
    print("\nTesting provider status...")

    class MockConfig:
        def get(self, key, default=None):
            config_map = {
                'features.crm_integration.enabled': True,
                'features.crm_integration.providers': []
            }
            return config_map.get(key, default)

    config = MockConfig()
    crm = CRMIntegration(config)

    # Add mock providers
    class MockProvider1(CRMLookupProvider):
        def __init__(self):
            super().__init__({'enabled': True, 'name': 'Provider1'})

        def lookup(self, phone_number):
            return None

    class MockProvider2(CRMLookupProvider):
        def __init__(self):
            super().__init__({'enabled': True, 'name': 'Provider2'})

        def lookup(self, phone_number):
            return None

    crm.providers.append(MockProvider1())
    crm.providers.append(MockProvider2())

    status = crm.get_provider_status()

    assert len(status) == 2, "Should have 2 providers"
    assert status[0]['name'] == 'Provider1', "First provider name should match"
    assert status[0]['enabled'], "First provider should be enabled"
    assert status[1]['name'] == 'Provider2', "Second provider name should match"

    print("✓ Provider status works")
    return True


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Testing CRM Integration and Screen Pop Support")
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
        print(
            f"✅ All CRM integration tests passed! ({len(results)}/{len(results)})")
        return True
    else:
        print(f"❌ Some tests failed ({sum(results)}/{len(results)} passed)")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
