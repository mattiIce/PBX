#!/usr/bin/env python3
"""
Test for voicemail access Contact header fix

This test validates that when accessing voicemail via *xxxx, the Contact header
in the 200 OK response uses the extension number without the asterisk prefix.
"""

import os


def test_voicemail_access_contact_header_code_review() -> None:
    """
    Test that the voicemail access code uses correct Contact header

    This test verifies the code in _handle_voicemail_access uses target_ext
    (without asterisk) instead of to_ext (with asterisk) in the Contact header.
    """

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


def test_contact_header_pattern_consistency() -> None:
    """
    Test that Contact headers follow consistent pattern across voicemail features
    """

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
                else:
                break

        if not has_contact:
