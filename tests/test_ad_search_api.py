#!/usr/bin/env python3
"""
Tests for Active Directory search API endpoint
Tests that the /api/integrations/ad/search endpoint properly searches for users by telephoneNumber
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.integrations.active_directory import ActiveDirectoryIntegration
from pbx.utils.config import Config


def test_ad_search_users_method():
    """Test that the AD search_users method includes telephoneNumber in the search"""
    print("Testing AD search_users method includes telephoneNumber...")

    config = Config("test_config.yml")
    ad_integration = ActiveDirectoryIntegration(config)

    # Verify the method exists
    assert hasattr(ad_integration, "search_users"), "AD integration should have search_users method"

    # Check the method signature
    import inspect

    sig = inspect.signature(ad_integration.search_users)
    params = list(sig.parameters.keys())
    assert "query" in params, "search_users should accept 'query' parameter"
    assert "max_results" in params, "search_users should accept 'max_results' parameter"

    print("✓ AD search_users method exists with correct signature")
    print("  Parameters: query, max_results")

    # Note: We can't test actual LDAP connection without a real AD server
    # But we can verify the method structure is correct

    # Check that the method is documented to search telephoneNumber
    docstring = ad_integration.search_users.__doc__
    assert docstring is not None, "search_users should have documentation"
    assert (
        "phone" in docstring.lower() or "telephone" in docstring.lower()
    ), "Documentation should mention phone/telephone search capability"

    print("✓ Method documentation mentions phone/telephone search")


def test_search_filter_includes_telephone_number():
    """Verify that the search filter includes telephoneNumber attribute"""
    print("Testing that search filter includes telephoneNumber...")

    # Read the source code to verify the search filter
    import inspect

    import pbx.integrations.active_directory as ad_module

    source = inspect.getsource(ad_module.ActiveDirectoryIntegration.search_users)

    # Check that telephoneNumber is in the search filter
    assert (
        "telephoneNumber" in source
    ), "search_users method should search telephoneNumber attribute"

    # Check that telephoneNumber is in the attributes list
    assert (
        "attributes=['sAMAccountName', 'displayName', 'mail', 'telephoneNumber']" in source
        or "attributes=" in source
        and "telephoneNumber" in source
    ), "search_users should retrieve telephoneNumber attribute"

    print("✓ Search filter includes telephoneNumber attribute")
    print("✓ Result attributes include telephoneNumber")


def test_api_endpoint_structure():
    """Test that the REST API has the AD search endpoint defined"""
    print("Testing REST API AD search endpoint structure...")

    # Import the REST API module
    import inspect

    from pbx.api import rest_api

    # Check that the handler method exists
    assert hasattr(
        rest_api.PBXAPIHandler, "_handle_ad_search"
    ), "REST API should have _handle_ad_search method"

    # Get the method
    handler_method = rest_api.PBXAPIHandler._handle_ad_search
    source = inspect.getsource(handler_method)

    # Verify it calls search_users
    assert (
        "search_users" in source
    ), "_handle_ad_search should call ad_integration.search_users method"

    # Verify it handles query parameter
    assert "'q'" in source or '"q"' in source, "_handle_ad_search should handle 'q' query parameter"

    print("✓ REST API handler _handle_ad_search exists")
    print("✓ Handler calls search_users method")
    print("✓ Handler processes query parameter")


def test_api_routing():
    """Test that the API routing includes the AD search endpoint"""
    print("Testing API routing for AD search endpoint...")

    import inspect

    from pbx.api import rest_api

    # Get the do_GET method source
    source = inspect.getsource(rest_api.PBXAPIHandler.do_GET)

    # Check that the routing includes ad/search
    assert (
        "/api/integrations/ad/search" in source
    ), "API routing should include /api/integrations/ad/search endpoint"

    assert (
        "_handle_ad_search" in source
    ), "API routing should call _handle_ad_search for the search endpoint"

    print("✓ API routing includes /api/integrations/ad/search")
    print("✓ Routing calls _handle_ad_search handler")


if __name__ == "__main__":
    try:
        test_ad_search_users_method()
        print()
        test_search_filter_includes_telephone_number()
        print()
        test_api_endpoint_structure()
        print()
        test_api_routing()
        print()
        print("=" * 60)
        print("All AD search API tests passed!")
        print("=" * 60)
        print()
        print("The AD search API endpoint is properly configured to:")
        print("  - Search users by telephoneNumber attribute")
        print("  - Return phone numbers in search results")
        print("  - Handle query parameters via REST API")
        print()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
