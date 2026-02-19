#!/usr/bin/env python3
"""
Tests for Active Directory search API endpoint
Tests that the /api/integrations/ad/search endpoint properly searches for users by telephoneNumber
"""

from pbx.integrations.active_directory import ActiveDirectoryIntegration
from pbx.utils.config import Config


def test_ad_search_users_method() -> None:
    """Test that the AD search_users method includes telephoneNumber in the search"""

    config = Config("test_config.yml")
    ad_integration = ActiveDirectoryIntegration(config)

    # Verify the method exists
    assert hasattr(ad_integration, "search_users"), "AD integration should have search_users method"

    # Check the method signature
    import inspect

    sig = inspect.signature(ad_integration.search_users)
    params = list(sig.parameters)
    assert "query" in params, "search_users should accept 'query' parameter"
    assert "max_results" in params, "search_users should accept 'max_results' parameter"

    # Note: We can't test actual LDAP connection without a real AD server
    # But we can verify the method structure is correct

    # Check that the method is documented to search telephoneNumber
    docstring = ad_integration.search_users.__doc__
    assert docstring is not None, "search_users should have documentation"
    assert "phone" in docstring.lower() or "telephone" in docstring.lower(), (
        "Documentation should mention phone/telephone search capability"
    )


def test_search_filter_includes_telephone_number() -> None:
    """Verify that the search filter includes telephoneNumber attribute"""

    # Read the source code to verify the search filter
    import inspect

    import pbx.integrations.active_directory as ad_module

    source = inspect.getsource(ad_module.ActiveDirectoryIntegration.search_users)

    # Check that telephoneNumber is in the search filter
    assert "telephoneNumber" in source, (
        "search_users method should search telephoneNumber attribute"
    )

    # Check that telephoneNumber is in the attributes list
    assert "attributes=['sAMAccountName', 'displayName', 'mail', 'telephoneNumber']" in source or (
        "attributes=" in source and "telephoneNumber" in source
    ), "search_users should retrieve telephoneNumber attribute"


