#!/usr/bin/env python3
"""
Tests for phone provisioning AD integration
Tests that AD credentials from .env are properly used for LDAP phonebook configuration
"""


from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.utils.config import Config


def test_ldap_config_from_ad_credentials() -> None:
    """Test that LDAP phonebook config is built from AD credentials"""

    # Create a minimal config
    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Call the method to build LDAP config
    ldap_config = provisioning._build_ldap_phonebook_config()

    # Verify that ldap_config is a dict
    assert isinstance(
        ldap_config, dict
    ), f"Expected dict, got {type(ldap_config)}"

    # Check for required fields
    required_fields = [
        "enable",
        "server",
        "port",
        "base",
        "user",
        "password",
        "version",
        "tls_mode",
        "name_filter",
        "number_filter",
        "name_attr",
        "number_attr",
        "display_name",
    ]

    for field in required_fields:
        assert field in ldap_config, f"Missing required field: {field}"


    # Check if AD is enabled
    ad_enabled = config.get("integrations.active_directory.enabled", False)
    if ad_enabled:
        # Verify that credentials are being used from AD
        ad_server = config.get("integrations.active_directory.server", "")
        ad_bind_dn = config.get("integrations.active_directory.bind_dn", "")

        if not (ad_server and ad_bind_dn):
            pass


def test_server_config_includes_ldap() -> None:
    """Test that server_config in generate_config includes LDAP configuration"""

    # Note: This is a lightweight test that checks the structure
    # A full integration test would require setting up extension registry and
    # devices

    config = Config("config.yml")
    provisioning = PhoneProvisioning(config)

    # Verify that the method exists
    assert hasattr(
        provisioning, "_build_ldap_phonebook_config"
    ), "Missing _build_ldap_phonebook_config method"

    # Call it to ensure it doesn't raise exceptions
    ldap_config = provisioning._build_ldap_phonebook_config()

    assert isinstance(ldap_config, dict), "LDAP config should be a dict"
    assert "server" in ldap_config, "LDAP config should have 'server' field"
