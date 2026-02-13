#!/usr/bin/env python3
"""
Tests for security compliance checker
"""

import json
import os
import subprocess
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_compliance_checker_exists() -> None:
    """Test that compliance checker script exists and is executable"""
    print("Testing compliance checker script exists...")

    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "security_compliance_check.py"
    )

    assert os.path.exists(script_path), "Compliance checker script not found"
    assert os.access(script_path, os.X_OK), "Compliance checker script not executable"

    print("✓ Compliance checker script exists and is executable")


def test_compliance_checker_help() -> None:
    """Test that compliance checker shows help"""
    print("Testing compliance checker help...")

    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "security_compliance_check.py"
    )

    result = subprocess.run(
        [sys.executable, script_path, "--help"], capture_output=True, text=True, timeout=10
    )

    assert result.returncode == 0, "Help command should succeed"
    assert (
        "FIPS" in result.stdout or "compliance" in result.stdout.lower()
    ), "Help should mention FIPS or compliance"

    print("✓ Compliance checker shows help correctly")


def test_compliance_checker_json_output() -> None:
    """Test that compliance checker produces valid JSON"""
    print("Testing compliance checker JSON output...")

    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "security_compliance_check.py"
    )

    result = subprocess.run(
        [sys.executable, script_path, "--json"], capture_output=True, text=True, timeout=30
    )

    # Extract JSON from output (may have log messages before it)
    output_lines = result.stdout.strip().split("\n")
    json_output = None

    for i, line in enumerate(output_lines):
        if line.strip().startswith("{"):
            # Found start of JSON
            json_output = "\n".join(output_lines[i:])
            break

    assert json_output is not None, "Should produce JSON output"

    # Parse JSON
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Output was: {json_output[:500]}")
        raise

    # Validate structure
    assert "timestamp" in data, "JSON should include timestamp"
    assert "fips" in data, "JSON should include FIPS results"
    assert "soc2" in data, "JSON should include SOC2 results"
    assert "security" in data, "JSON should include security results"
    assert "overall" in data, "JSON should include overall status"

    # Validate FIPS section
    assert "compliant" in data["fips"], "FIPS section should have compliant field"
    assert "checks" in data["fips"], "FIPS section should have checks"
    assert "issues" in data["fips"], "FIPS section should have issues list"

    # Validate SOC2 section
    assert "compliant" in data["soc2"], "SOC2 section should have compliant field"
    assert "controls" in data["soc2"], "SOC2 section should have controls"
    assert "summary" in data["soc2"], "SOC2 section should have summary"

    # Validate overall section
    assert "status" in data["overall"], "Overall should have status"
    assert data["overall"]["status"] in [
        "COMPLIANT",
        "COMPLIANT_WITH_WARNINGS",
        "NON_COMPLIANT",
    ], "Status should be one of the valid values"

    print("✓ Compliance checker produces valid JSON with correct structure")
    print(f"  Status: {data['overall']['status']}")
    print(f"  FIPS Compliant: {data['overall']['fips_compliant']}")
    print(f"  SOC2 Compliant: {data['overall']['soc2_compliant']}")


def test_fips_algorithm_checks() -> None:
    """Test that FIPS algorithms are validated"""
    print("Testing FIPS algorithm validation...")

    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "security_compliance_check.py"
    )

    result = subprocess.run(
        [sys.executable, script_path, "--json"], capture_output=True, text=True, timeout=30
    )

    # Extract JSON
    output_lines = result.stdout.strip().split("\n")
    json_output = None

    for i, line in enumerate(output_lines):
        if line.strip().startswith("{"):
            json_output = "\n".join(output_lines[i:])
            break

    data = json.loads(json_output)

    # Check that algorithm checks are present
    checks = data["fips"]["checks"]

    assert "pbkdf2_sha256" in checks, "Should check PBKDF2-HMAC-SHA256"
    assert "sha256" in checks, "Should check SHA-256"
    assert "aes_256_gcm" in checks, "Should check AES-256-GCM"

    # These should pass since we have cryptography library
    assert checks["pbkdf2_sha256"] is True, "PBKDF2-HMAC-SHA256 should work"
    assert checks["sha256"] is True, "SHA-256 should work"
    assert checks["aes_256_gcm"] is True, "AES-256-GCM should work"

    print("✓ FIPS algorithm checks are working")
    print("  PBKDF2-HMAC-SHA256: ✓")
    print("  SHA-256: ✓")
    print("  AES-256-GCM: ✓")


def test_wrapper_script_exists() -> None:
    """Test that wrapper script exists"""
    print("Testing wrapper script exists...")

    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "run_compliance_check.sh"
    )

    assert os.path.exists(script_path), "Wrapper script not found"
    assert os.access(script_path, os.X_OK), "Wrapper script not executable"

    print("✓ Wrapper script exists and is executable")


def test_soc2_testing_script_exists() -> None:
    """Test that SOC 2 testing script exists and is executable"""
    print("Testing SOC 2 testing script exists...")

    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "test_soc2_controls.py")

    assert os.path.exists(script_path), "SOC 2 testing script not found"
    assert os.access(script_path, os.X_OK), "SOC 2 testing script not executable"

    print("✓ SOC 2 testing script exists and is executable")


def test_soc2_testing_script_help() -> None:
    """Test that SOC 2 testing script shows help"""
    print("Testing SOC 2 testing script help...")

    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "test_soc2_controls.py")

    result = subprocess.run(
        [sys.executable, script_path, "--help"], capture_output=True, text=True, timeout=10
    )

    assert result.returncode == 0, "Help command should succeed"
    assert "SOC 2" in result.stdout, "Help should mention SOC 2"
    assert "control" in result.stdout.lower(), "Help should mention controls"

    print("✓ SOC 2 testing script shows help correctly")


def main() -> None:
    """Run all tests"""
    print("\n" + "=" * 70)
    print("Security Compliance Checker Tests")
    print("=" * 70 + "\n")

    tests = [
        test_compliance_checker_exists,
        test_compliance_checker_help,
        test_compliance_checker_json_output,
        test_fips_algorithm_checks,
        test_wrapper_script_exists,
        test_soc2_testing_script_exists,
        test_soc2_testing_script_help,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
            print()
        except Exception as e:
            print(f"✗ FAILED: {e}")
            failed += 1
            print()

    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")

    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
