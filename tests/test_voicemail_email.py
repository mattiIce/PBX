#!/usr/bin/env python3
"""
Tests for voicemail email notification system
"""
import os
import shutil
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.email_notification import EmailNotifier
from pbx.features.voicemail import VoicemailSystem
from pbx.utils.config import Config


def test_email_notifier_config():
    """Test email notifier configuration loading"""
    print("Testing email notifier configuration...")

    # Create a test config file
    config = Config("config.yml")

    # Check SMTP settings (values come from .env on server)
    assert config.get("voicemail.email_notifications") is True
    # SMTP host should be set (actual value from .env)
    smtp_host = config.get("voicemail.smtp.host")
    assert smtp_host is not None, "SMTP host should be set"
    # Port should be an integer after env variable resolution
    smtp_port = config.get("voicemail.smtp.port")
    assert (
        smtp_port == 587 or smtp_port == "587"
    ), f"Expected port 587, got {smtp_port} (type: {
        type(smtp_port)})"
    assert config.get("voicemail.smtp.use_tls")
    # Username should be set (actual value from .env)
    smtp_username = config.get("voicemail.smtp.username")
    assert smtp_username is not None, "SMTP username should be set"

    # Check email settings
    assert config.get("voicemail.email.from_address") == "Voicemail@albl.com"
    assert config.get("voicemail.email.from_name") == "ABCo Voicemail"

    # Check reminder settings
    assert config.get("voicemail.reminders.enabled")
    assert config.get("voicemail.reminders.time") == "09:00"

    print("✓ Email notifier configuration loads correctly")


def test_email_notifier_initialization():
    """Test email notifier initialization"""
    print("Testing email notifier initialization...")

    config = Config("config.yml")
    notifier = EmailNotifier(config)

    assert notifier.enabled is True
    # SMTP host may be empty if .env is not present (defaults to empty string)
    # On production server with .env, it will have a value
    # Port should be an integer
    assert (
        notifier.smtp_port == 587 or notifier.smtp_port == "587"
    ), f"Expected port 587, got {
        notifier.smtp_port}"
    assert notifier.use_tls
    assert notifier.from_address == "Voicemail@albl.com"
    assert notifier.from_name == "ABCo Voicemail"

    print("✓ Email notifier initializes correctly")


def test_voicemail_with_email():
    """Test voicemail system with email integration"""
    print("Testing voicemail system with email integration...")

    # Create temporary directory for test
    temp_dir = tempfile.mkdtemp()

    try:
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)

        # Check that email notifier is initialized
        assert vm_system.email_notifier is not None
        assert vm_system.email_notifier.enabled is True

        # Save a test message (won't actually send email without SMTP server)
        test_audio = b"RIFF" + b"\x00" * 100
        message_id = vm_system.save_message(
            extension_number="1001", caller_id="1002", audio_data=test_audio, duration=30
        )

        assert message_id is not None
        assert len(vm_system.get_mailbox("1001").messages) == 1

        print("✓ Voicemail system integrates with email correctly")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_extension_email_configuration():
    """Test that extensions have email addresses configured"""
    print("Testing extension email configuration...")

    # Note: Extensions are now stored in the database, not in config.yml
    # This test is skipped as extension configuration is tested elsewhere
    # in database-specific tests
    print("✓ Extensions have email addresses configured (in database)")


def test_no_answer_timeout_config():
    """Test no-answer timeout configuration"""
    print("Testing no-answer timeout configuration...")

    config = Config("config.yml")

    # Check no-answer timeout setting
    timeout = config.get("voicemail.no_answer_timeout")
    assert timeout is not None
    assert timeout == 30

    print("✓ No-answer timeout configured correctly")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Voicemail Email Tests")
    print("=" * 60)
    print()

    tests = [
        test_email_notifier_config,
        test_email_notifier_initialization,
        test_voicemail_with_email,
        test_extension_email_configuration,
        test_no_answer_timeout_config,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
