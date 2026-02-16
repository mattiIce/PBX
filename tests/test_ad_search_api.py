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


def test_api_endpoint_structure() -> None:
    """Test that the REST API has the AD search endpoint defined"""

    # Import the REST API module
    import inspect

    from pbx.api import rest_api

    # Check that the handler method exists
    assert hasattr(rest_api.PBXAPIHandler, "_handle_ad_search"), (
        "REST API should have _handle_ad_search method"
    )

    # Get the method
    handler_method = rest_api.PBXAPIHandler._handle_ad_search
    source = inspect.getsource(handler_method)

    # Verify it calls search_users
    assert "search_users" in source, (
        "_handle_ad_search should call ad_integration.search_users method"
    )

    # Verify it handles query parameter
    assert "'q'" in source or '"q"' in source, "_handle_ad_search should handle 'q' query parameter"


def test_api_routing() -> None:
    """Test that the API routing includes the AD search endpoint"""

    import inspect

    from pbx.api import rest_api

    # Get the do_GET method source
    source = inspect.getsource(rest_api.PBXAPIHandler.do_GET)

    # Check that the routing includes ad/search
    assert "/api/integrations/ad/search" in source, (
        "API routing should include /api/integrations/ad/search endpoint"
    )

    assert "_handle_ad_search" in source, (
        "API routing should call _handle_ad_search for the search endpoint"
    )
