#!/usr/bin/env python3
"""
Test script to verify the integration quick setup functionality
"""

import json
from pathlib import Path

import yaml


def test_config_structure() -> bool:
    """Test that config.yml has the correct structure for integrations"""
    config_path = Path(__file__).parent.parent / "config.yml"

    if not config_path.exists():
        return False

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Check integrations section exists
    if "integrations" not in config:
        return False


    # Check each integration
    required_integrations = ["jitsi", "matrix", "espocrm"]
    for integration in required_integrations:
        if integration not in config["integrations"]:
        else:
            int_config = config["integrations"][integration]
            if "enabled" in int_config:
                status = "enabled" if int_config["enabled"] else "disabled"

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

    for integration, config in defaults.items():
        print(json.dumps(config, indent=2))

    return True


def test_env_example() -> bool:
    """Test that .env.example has the required variables"""
    env_example_path = Path(__file__).parent.parent / ".env.example"

    if not env_example_path.exists():
        return False

    with open(env_example_path, "r") as f:
        content = f.read()

    required_vars = ["MATRIX_BOT_PASSWORD", "ESPOCRM_API_KEY"]
    missing = []

    for var in required_vars:
        if var in content:
        else:
            missing.append(var)

    return len(missing) == 0


def test_admin_html() -> bool:
    """Test that admin/index.html has the quick setup elements"""
    admin_html_path = Path(__file__).parent.parent / "admin" / "index.html"

    if not admin_html_path.exists():
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
        else:
            missing.append(element)

    return len(missing) == 0


def test_javascript() -> bool:
    """Test that opensource_integrations.js has the quick setup functions"""
    js_path = Path(__file__).parent.parent / "admin" / "js" / "opensource_integrations.js"

    if not js_path.exists():
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
        else:
            missing.append(func)

    # Check for correct API endpoint
    if "/api/config/section" in content:
    else:

    return len(missing) == 0


def main() -> int:
    """Run all tests"""

    tests = [
        ("Config Structure", test_config_structure),
        ("Default Configurations", test_default_configs),
        ("Environment Variables", test_env_example),
        ("Admin HTML Elements", test_admin_html),
        ("JavaScript Functions", test_javascript),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Summary

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"


    if passed == total:
        return 0
    else:
        return 1
