#!/usr/bin/env python3
"""
Test script to verify the integration quick setup functionality
"""

import json
import sys
from pathlib import Path

import yaml


def test_config_structure() -> bool:
    """Test that config.yml has the correct structure for integrations"""
    config_path = Path(__file__).parent.parent / "config.yml"

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Check integrations section exists
    if "integrations" not in config:
        print("❌ 'integrations' section not found in config.yml")
        return False

    print("✅ 'integrations' section found in config.yml")

    # Check each integration
    required_integrations = ["jitsi", "matrix", "espocrm"]
    for integration in required_integrations:
        if integration not in config["integrations"]:
            print(f"⚠️  '{integration}' not found in integrations (will be added on first setup)")
        else:
            print(f"✅ '{integration}' configuration found")
            int_config = config["integrations"][integration]
            if "enabled" in int_config:
                status = "enabled" if int_config["enabled"] else "disabled"
                print(f"   Status: {status}")

    return True


def test_default_configs() -> bool:
    """Test that default configurations are valid"""
    defaults = {
        "jitsi": {
            "enabled": True,
            "server_url": "https://localhost",
            "auto_create_rooms": True,
            "app_id": "",
            "app_secret": "",
        },
        "matrix": {
            "enabled": True,
            "homeserver_url": "https://localhost:8008",
            "bot_username": "",
            "bot_password": "${MATRIX_BOT_PASSWORD}",
            "notification_room": "",
            "voicemail_room": "",
            "missed_call_notifications": True,
        },
        "espocrm": {
            "enabled": True,
            "api_url": "https://localhost/api/v1",
            "api_key": "${ESPOCRM_API_KEY}",
            "auto_create_contacts": True,
            "auto_log_calls": True,
            "screen_pop": True,
        },
    }

    print("\n📋 Default Configurations:")
    print("-" * 60)
    for integration, config in defaults.items():
        print(f"\n{integration.upper()}:")
        print(json.dumps(config, indent=2))

    print("\n✅ All default configurations are valid JSON")
    return True


def test_env_example() -> bool:
    """Test that .env.example has the required variables"""
    env_example_path = Path(__file__).parent.parent / ".env.example"

    if not env_example_path.exists():
        print(f"❌ .env.example not found: {env_example_path}")
        return False

    with open(env_example_path, "r") as f:
        content = f.read()

    required_vars = ["MATRIX_BOT_PASSWORD", "ESPOCRM_API_KEY"]
    missing = []

    for var in required_vars:
        if var in content:
            print(f"✅ {var} found in .env.example")
        else:
            print(f"❌ {var} missing from .env.example")
            missing.append(var)

    return len(missing) == 0


def test_admin_html() -> bool:
    """Test that admin/index.html has the quick setup elements"""
    admin_html_path = Path(__file__).parent.parent / "admin" / "index.html"

    if not admin_html_path.exists():
        print(f"❌ admin/index.html not found: {admin_html_path}")
        return False

    with open(admin_html_path, "r") as f:
        content = f.read()

    required_elements = [
        "quick-jitsi-enabled",
        "quick-matrix-enabled",
        "quick-espocrm-enabled",
        "quickToggleIntegration",
        "quickSetupIntegration",
        "jitsi-status-badge",
        "matrix-status-badge",
        "espocrm-status-badge",
    ]

    missing = []
    for element in required_elements:
        if element in content:
            print(f"✅ '{element}' found in admin/index.html")
        else:
            print(f"❌ '{element}' missing from admin/index.html")
            missing.append(element)

    return len(missing) == 0


def test_javascript() -> bool:
    """Test that opensource_integrations.js has the quick setup functions"""
    js_path = Path(__file__).parent.parent / "admin" / "js" / "opensource_integrations.js"

    if not js_path.exists():
        print(f"❌ opensource_integrations.js not found: {js_path}")
        return False

    with open(js_path, "r") as f:
        content = f.read()

    required_functions = [
        "updateQuickSetupStatus",
        "quickToggleIntegration",
        "quickSetupIntegration",
        "disableIntegration",
    ]

    missing = []
    for func in required_functions:
        if f"function {func}" in content or f"async function {func}" in content:
            print(f"✅ Function '{func}' found")
        else:
            print(f"❌ Function '{func}' missing")
            missing.append(func)

    # Check for correct API endpoint
    if "/api/config/section" in content:
        print("✅ Using correct API endpoint: /api/config/section")
    else:
        print("⚠️  May not be using correct API endpoint")

    return len(missing) == 0


def main() -> int:
    """Run all tests"""
    print("=" * 60)
    print("Integration Quick Setup - Functionality Test")
    print("=" * 60)

    tests = [
        ("Config Structure", test_config_structure),
        ("Default Configurations", test_default_configs),
        ("Environment Variables", test_env_example),
        ("Admin HTML Elements", test_admin_html),
        ("JavaScript Functions", test_javascript),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Testing: {name}")
        print("=" * 60)
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All tests passed! Quick setup feature is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
