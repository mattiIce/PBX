#!/usr/bin/env python3
"""
Tests for security compliance checker
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_compliance_checker_exists() -> None:
    """Test that compliance checker script exists and is executable"""

    script_path = str(Path(__file__).parent.parent / "scripts" / "security_compliance_check.py")

    assert Path(script_path).exists(), "Compliance checker script not found"
    assert os.access(script_path, os.X_OK), "Compliance checker script not executable"


def test_compliance_checker_help() -> None:
    """Test that compliance checker shows help"""

    script_path = str(Path(__file__).parent.parent / "scripts" / "security_compliance_check.py")

    result = subprocess.run(
        [sys.executable, script_path, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, "Help command should succeed"
    assert "FIPS" in result.stdout or "compliance" in result.stdout.lower(), (
        "Help should mention FIPS or compliance"
    )


def test_compliance_checker_json_output() -> None:
    """Test that compliance checker produces valid JSON"""

    script_path = str(Path(__file__).parent.parent / "scripts" / "security_compliance_check.py")

    result = subprocess.run(
        [sys.executable, script_path, "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
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
    except json.JSONDecodeError:
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


def test_fips_algorithm_checks() -> None:
    """Test that FIPS algorithms are validated"""

    script_path = str(Path(__file__).parent.parent / "scripts" / "security_compliance_check.py")

    result = subprocess.run(
        [sys.executable, script_path, "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
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


def test_wrapper_script_exists() -> None:
    """Test that wrapper script exists"""

    script_path = str(Path(__file__).parent.parent / "scripts" / "run_compliance_check.sh")

    assert Path(script_path).exists(), "Wrapper script not found"
    assert os.access(script_path, os.X_OK), "Wrapper script not executable"


def test_soc2_testing_script_exists() -> None:
    """Test that SOC 2 testing script exists and is executable"""

    script_path = str(Path(__file__).parent.parent / "scripts" / "test_soc2_controls.py")

    assert Path(script_path).exists(), "SOC 2 testing script not found"
    assert os.access(script_path, os.X_OK), "SOC 2 testing script not executable"


def test_soc2_testing_script_help() -> None:
    """Test that SOC 2 testing script shows help"""

    script_path = str(Path(__file__).parent.parent / "scripts" / "test_soc2_controls.py")

    result = subprocess.run(
        [sys.executable, script_path, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, "Help command should succeed"
    assert "SOC 2" in result.stdout, "Help should mention SOC 2"
    assert "control" in result.stdout.lower(), "Help should mention controls"


def main() -> None:
    """Run all tests"""

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
        except Exception:
            failed += 1

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)
