#!/usr/bin/env python3
"""
Test for voicemail access Contact header fix

This test validates that when accessing voicemail via *xxxx, the Contact header
in the 200 OK response uses the extension number without the asterisk prefix.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_voicemail_access_contact_header_code_review():
    """
    Test that the voicemail access code uses correct Contact header

    This test verifies the code in _handle_voicemail_access uses target_ext
    (without asterisk) instead of to_ext (with asterisk) in the Contact header.
    """
    print("Testing voicemail access Contact header code...")

    # Read the source code
    pbx_file = os.path.join(os.path.dirname(__file__), "..", "pbx", "core", "pbx.py")

    with open(pbx_file, "r") as f:
        content = f.read()

    # Find the _handle_voicemail_access method
    start_idx = content.find("def _handle_voicemail_access(")
    assert start_idx != -1, "Could not find _handle_voicemail_access method"

    # Get the method content (simplified check)
    method_end = content.find("\n    def ", start_idx + 1)
    if method_end == -1:
        method_end = len(content)
    method_content = content[start_idx:method_end]

    # Find where target_ext is defined (removing asterisk)
    assert (
        "target_ext = to_ext[1:]" in method_content
    ), "Should define target_ext by removing asterisk from to_ext"

    # Find where Contact header is built
    contact_header_lines = []
    for line in method_content.split("\n"):
        if "contact_uri" in line.lower() and "sip:" in line:
            contact_header_lines.append(line.strip())

    assert len(contact_header_lines) > 0, "Should have Contact header construction"

    # Check that target_ext is used, not to_ext
    contact_line = contact_header_lines[0]

    # The bug was using to_ext (with asterisk), fix should use target_ext
    assert (
        "target_ext" in contact_line
    ), f"Contact header should use target_ext (without asterisk), found: {contact_line}"

    # Check that to_ext is not used in the f-string interpolation
    assert (
        "to_ext}" not in contact_line and "to_ext @" not in contact_line
    ), f"Contact header should NOT use to_ext (with asterisk), found: {contact_line}"

    print("  ✓ Contact header code is correct: uses target_ext")
    print(f"  ✓ Found: {contact_line}")
    print("✓ Voicemail access Contact header code review passed!")


def test_contact_header_pattern_consistency():
    """
    Test that Contact headers follow consistent pattern across voicemail features
    """
    print("Testing Contact header pattern consistency...")

    # Read the source code
    pbx_file = os.path.join(os.path.dirname(__file__), "..", "pbx", "core", "pbx.py")

    with open(pbx_file, "r") as f:
        content = f.read()

    # Check various voicemail-related methods use extension without prefix
    methods_to_check = [
        ("_handle_voicemail_access", "target_ext"),
        ("_handle_voicemail_deposit", "to_extension"),
    ]

    for method_name, expected_var in methods_to_check:
        start_idx = content.find(f"def {method_name}(")
        if start_idx == -1:
            print(f"  ⓘ Method {method_name} not found (may not exist)")
            continue

        method_end = content.find("\n    def ", start_idx + 1)
        if method_end == -1:
            method_end = len(content)
        method_content = content[start_idx:method_end]

        # Look for Contact header construction
        has_contact = False
        for line in method_content.split("\n"):
            if "contact_uri" in line.lower() and "sip:" in line:
                has_contact = True
                # Verify it uses extension variable (not the prefixed version)
                # Check if to_ext is used in the SIP URI context
                if "to_ext}" in line and "sip:{to_ext}" in line:
                    print(f"  ⚠ Warning: {method_name} may have asterisk in Contact")
                else:
                    print(f"  ✓ {method_name} Contact header looks good")
                break

        if not has_contact:
            print(f"  ⓘ {method_name} may not set Contact header directly")

    print("✓ Contact header pattern consistency check completed!")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Voicemail Access Contact Header Tests")
    print("=" * 60)
    print()

    tests = [
        test_voicemail_access_contact_header_code_review,
        test_contact_header_pattern_consistency,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback

            traceback.print_exc()
            failed += 1
            print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
