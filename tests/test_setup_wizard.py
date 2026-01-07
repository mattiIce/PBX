#!/usr/bin/env python3
"""
Tests for the Ubuntu setup wizard

These tests validate the basic functionality of the setup_ubuntu.py script
without actually running system commands or making system changes.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import the setup wizard
from setup_ubuntu import SetupWizard


def test_setup_wizard_initialization():
    """Test that SetupWizard initializes correctly"""
    print("Testing SetupWizard initialization...")

    wizard = SetupWizard()

    assert wizard.project_root is not None, "project_root should be set"
    assert wizard.venv_path is not None, "venv_path should be set"
    assert wizard.env_file is not None, "env_file should be set"
    assert wizard.config_file is not None, "config_file should be set"
    assert isinstance(wizard.errors, list), "errors should be a list"
    assert isinstance(wizard.warnings, list), "warnings should be a list"
    assert isinstance(wizard.db_config, dict), "db_config should be a dict"

    print("✓ SetupWizard initialization works")


def test_check_python_version():
    """Test Python version checking"""
    print("Testing Python version checking...")

    wizard = SetupWizard()

    # Should pass for Python 3.12+
    result = wizard.check_python_version()
    if sys.version_info.major == 3 and sys.version_info.minor >= 12:
        assert result is True, "Should pass for Python 3.12+"
    else:
        assert result is False, "Should fail for Python < 3.12"

    print("✓ Python version checking works")


def test_check_root_non_root():
    """Test root checking when not running as root"""
    print("Testing root checking (non-root)...")

    wizard = SetupWizard()

    # Mock os.geteuid to return non-zero (not root)
    with patch("os.geteuid", return_value=1000):
        result = wizard.check_root()
        assert result is False, "Should return False when not root"
        assert len(wizard.errors) > 0, "Should have recorded an error"

    print("✓ Root checking works (non-root)")


def test_check_root_as_root():
    """Test root checking when running as root"""
    print("Testing root checking (as root)...")

    wizard = SetupWizard()

    # Mock os.geteuid to return zero (root)
    with patch("os.geteuid", return_value=0):
        result = wizard.check_root()
        assert result is True, "Should return True when root"

    print("✓ Root checking works (as root)")


def test_print_methods():
    """Test print methods for colored output"""
    print("Testing print methods...")

    wizard = SetupWizard()

    # Test print_success (should not raise errors)
    wizard.print_success("Test success message")

    # Test print_error (should add to errors list)
    initial_error_count = len(wizard.errors)
    wizard.print_error("Test error message")
    assert len(wizard.errors) == initial_error_count + 1, "Should have added error"

    # Test print_warning (should add to warnings list)
    initial_warning_count = len(wizard.warnings)
    wizard.print_warning("Test warning message")
    assert len(wizard.warnings) == initial_warning_count + 1, "Should have added warning"

    # Test print_info (should not raise errors)
    wizard.print_info("Test info message")

    # Test print_header (should not raise errors)
    wizard.print_header("Test Header")

    print("✓ Print methods work")


def test_run_command_success():
    """Test run_command with successful execution"""
    print("Testing run_command (success)...")

    wizard = SetupWizard()

    # Mock subprocess.run to return success
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        ret, stdout, stderr = wizard.run_command("echo test", "Test command", check=False)

        assert ret == 0, "Should return success code"
        assert stdout == "Success output", "Should return stdout"
        assert stderr == "", "Should return stderr"

    print("✓ run_command works (success)")


def test_run_command_failure():
    """Test run_command with failed execution"""
    print("Testing run_command (failure)...")

    wizard = SetupWizard()

    # Mock subprocess.run to return failure
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error output"
        mock_run.return_value = mock_result

        ret, stdout, stderr = wizard.run_command("false", "Test failing command", check=False)

        assert ret == 1, "Should return error code"
        assert stderr == "Error output", "Should return stderr"

    print("✓ run_command works (failure)")


def test_setup_environment_file():
    """Test environment file creation"""
    print("Testing environment file creation...")

    wizard = SetupWizard()

    # Set up test database configuration
    wizard.db_config = {
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
    }

    # Create a proper temporary directory instead of file
    import tempfile

    temp_dir = tempfile.mkdtemp()
    wizard.env_file = Path(temp_dir) / "test.env"

    try:
        result = wizard.setup_environment_file()
        assert result is True, "Should succeed in creating env file"

        # Verify file was created
        assert wizard.env_file.exists(), "Env file should exist"

        # Verify file contents
        with open(wizard.env_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "DB_NAME=test_db" in content, "Should contain database name"
            assert "DB_USER=test_user" in content, "Should contain database user"
            assert "DB_PASSWORD=test_password" in content, "Should contain password"
            assert "DB_HOST=localhost" in content, "Should contain host"

        # Verify file permissions are restrictive (600)
        file_mode = os.stat(wizard.env_file).st_mode & 0o777
        assert file_mode == 0o600, f"File should have 600 permissions, got {oct(file_mode)}"

    finally:
        # Clean up
        import shutil

        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)

    print("✓ Environment file creation works")


def test_check_ubuntu_version_with_mock():
    """Test Ubuntu version checking with mocked file"""
    print("Testing Ubuntu version checking (mocked)...")

    wizard = SetupWizard()

    # Test with Ubuntu 24.04
    ubuntu_2404_content = """
NAME="Ubuntu"
VERSION="24.04 LTS (Noble Numbat)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 24.04 LTS"
VERSION_ID="24.04"
"""
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = ubuntu_2404_content
        result = wizard.check_ubuntu_version()
        assert result is True, "Should pass for Ubuntu 24.04"

    # Reset errors/warnings
    wizard.errors = []
    wizard.warnings = []

    # Test with other Ubuntu version
    ubuntu_2204_content = """
NAME="Ubuntu"
VERSION="22.04 LTS (Jammy Jellyfish)"
ID=ubuntu
VERSION_ID="22.04"
"""
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = ubuntu_2204_content
        result = wizard.check_ubuntu_version()
        assert result is True, "Should pass for other Ubuntu versions"
        assert len(wizard.warnings) > 0, "Should have warning for non-24.04"

    print("✓ Ubuntu version checking works (mocked)")


def run_all_tests():
    """Run all tests"""
    tests = [
        test_setup_wizard_initialization,
        test_check_python_version,
        test_check_root_non_root,
        test_check_root_as_root,
        test_print_methods,
        test_run_command_success,
        test_run_command_failure,
        test_setup_environment_file,
        test_check_ubuntu_version_with_mock,
    ]

    print("=" * 70)
    print("Running Setup Wizard Tests")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
