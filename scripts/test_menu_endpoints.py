#!/usr/bin/env python3
"""
Test script to verify auto-attendant menu API endpoints are working.
Run this on the server to diagnose API issues.

Usage:
    python3 test_menu_endpoints.py [--host localhost] [--port 9000]
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def test_endpoint(base_url, endpoint, method="GET", data=None, expected_status=200, timeout=10):
    """Test a single API endpoint."""
    url = f"{base_url}{endpoint}"

    try:
        if data:
            data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Content-Type", "application/json")
        else:
            req = urllib.request.Request(url, method=method)

        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8")

            if status == expected_status:
                print(f"✓ {method} {endpoint}")
                try:
                    data = json.loads(body)
                    if isinstance(data, dict) and "menus" in data:
                        print(f"  → Found {len(data['menus'])} menu(s)")
                    elif isinstance(data, dict) and "items" in data:
                        print(f"  → Found {len(data['items'])} item(s)")
                    elif isinstance(data, dict) and "menu_tree" in data:
                        print("  → Menu tree loaded")
                except json.JSONDecodeError:
                    # Response body is not valid JSON; ignore and continue without extra details.
                    pass
                return True
            else:
                print(f"✗ {method} {endpoint} - Got status {status}, expected {expected_status}")
                return False

    except urllib.error.HTTPError as e:
        status = e.code
        try:
            error_body = e.read().decode("utf-8")
            error_data = json.loads(error_body)
            error_msg = error_data.get("error", "Unknown error")
        except (json.JSONDecodeError, UnicodeDecodeError):
            # If we can't parse the error body, use the HTTP error string
            error_msg = str(e)

        if status == expected_status:
            print(f"✓ {method} {endpoint} (expected {expected_status})")
            return True
        else:
            print(f"✗ {method} {endpoint} - HTTP {status}: {error_msg}")
            return False
    except urllib.error.URLError as e:
        print(f"✗ {method} {endpoint} - Connection error: {e}")
        return False
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
        print(f"✗ {method} {endpoint} - Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test auto-attendant menu API endpoints")
    parser.add_argument("--host", default="localhost", help="API server host (default: localhost)")
    parser.add_argument("--port", default="9000", help="API server port (default: 9000)")
    parser.add_argument(
        "--protocol",
        default="http",
        choices=["http", "https"],
        help="Protocol to use (default: http)",
    )
    parser.add_argument(
        "--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)"
    )
    args = parser.parse_args()

    base_url = f"{args.protocol}://{args.host}:{args.port}"

    print(f"Testing auto-attendant menu endpoints at {base_url}")
    print("=" * 70)

    results = []

    # Test GET endpoints
    print("\nGET Endpoints:")
    print("-" * 70)
    results.append(test_endpoint(base_url, "/api/auto-attendant/menus", timeout=args.timeout))
    results.append(test_endpoint(base_url, "/api/auto-attendant/menus/main", timeout=args.timeout))
    results.append(
        test_endpoint(base_url, "/api/auto-attendant/menus/main/items", timeout=args.timeout)
    )
    results.append(test_endpoint(base_url, "/api/auto-attendant/menu-tree", timeout=args.timeout))
    results.append(test_endpoint(base_url, "/api/auto-attendant/config", timeout=args.timeout))
    results.append(test_endpoint(base_url, "/api/auto-attendant/prompts", timeout=args.timeout))

    # Test a non-existent menu (should return 404)
    print("\nNegative Tests (should fail with 404):")
    print("-" * 70)
    results.append(
        test_endpoint(
            base_url,
            "/api/auto-attendant/menus/nonexistent",
            expected_status=404,
            timeout=args.timeout,
        )
    )

    # Summary
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All endpoints are working correctly!")
        return 0
    else:
        print("✗ Some endpoints are not working. Check the errors above.")
        print("\nTroubleshooting steps:")
        print("1. Ensure the PBX service is running:")
        print("   sudo systemctl status pbx")
        print("2. Restart the service if needed:")
        print("   sudo systemctl restart pbx")
        print("3. Check the logs for errors:")
        print("   sudo journalctl -u pbx -n 50")
        print("4. Verify the code is up to date:")
        print("   git log --oneline -1 -- pbx/api/rest_api.py")
        print("\nSee TROUBLESHOOTING_AUTO_ATTENDANT_MENUS.md for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
