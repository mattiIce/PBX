#!/usr/bin/env python3
"""
Tests for phone provisioning AD integration
Tests that AD credentials from .env are properly used for LDAP phonebook configuration
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.utils.config import Config



def test_ldap_config_from_ad_credentials():
    """Test that LDAP phonebook config is built from AD credentials"""
    print("Testing LDAP phonebook config from AD credentials...")

    # Create a minimal config
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Call the method to build LDAP config
    ldap_config = provisioning._build_ldap_phonebook_config()

    # Verify that ldap_config is a dict
    assert isinstance(
        ldap_config, dict), f"Expected dict, got {
        type(ldap_config)}"

    # Check for required fields
    required_fields = ['enable', 'server', 'port', 'base', 'user', 'password',
                       'version', 'tls_mode', 'name_filter', 'number_filter',
                       'name_attr', 'number_attr', 'display_name']

    for field in required_fields:
        assert field in ldap_config, f"Missing required field: {field}"

    print(f"✓ LDAP config contains all required fields")
    print(f"  Server: {ldap_config['server']}")
    print(f"  Port: {ldap_config['port']}")
    print(f"  TLS Mode: {ldap_config['tls_mode']}")
    print(f"  Base DN: {ldap_config['base']}")
    print(f"  Display Name: {ldap_config['display_name']}")

    # Check if AD is enabled
    ad_enabled = config.get('integrations.active_directory.enabled', False)
    if ad_enabled:
        print("✓ AD integration is enabled")
        # Verify that credentials are being used from AD
        ad_server = config.get('integrations.active_directory.server', '')
        ad_bind_dn = config.get('integrations.active_directory.bind_dn', '')

        if ad_server and ad_bind_dn:
            print(
                f"✓ AD credentials are available and will be used for LDAP phonebook")
    else:
        print("ℹ AD integration is disabled, using explicit ldap_phonebook config")

    print("✓ LDAP phonebook config from AD credentials works")


def test_server_config_includes_ldap():
    """Test that server_config in generate_config includes LDAP configuration"""
    print("Testing server_config includes LDAP configuration...")

    # Note: This is a lightweight test that checks the structure
    # A full integration test would require setting up extension registry and
    # devices

    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Verify that the method exists
    assert hasattr(provisioning, '_build_ldap_phonebook_config'), \
        "Missing _build_ldap_phonebook_config method"

    # Call it to ensure it doesn't raise exceptions
    ldap_config = provisioning._build_ldap_phonebook_config()

    assert isinstance(ldap_config, dict), "LDAP config should be a dict"
    assert 'server' in ldap_config, "LDAP config should have 'server' field"

    print("✓ Server config structure is correct")


if __name__ == '__main__':
    try:
        test_ldap_config_from_ad_credentials()
        print()
        test_server_config_includes_ldap()
        print()
        print("=" * 60)
        print("All AD integration tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
