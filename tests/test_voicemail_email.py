#!/usr/bin/env python3
"""
Tests for voicemail email notification system
"""
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.utils.config import Config
from pbx.features.voicemail import VoicemailSystem
from pbx.features.email_notification import EmailNotifier


def test_email_notifier_config():
    """Test email notifier configuration loading"""
    print("Testing email notifier configuration...")
    
    # Create a test config file
    config = Config('config.yml')
    
    # Check SMTP settings
    assert config.get('voicemail.email_notifications') == True
    assert config.get('voicemail.smtp.host') == "192.168.1.75"
    assert config.get('voicemail.smtp.port') == 587
    assert config.get('voicemail.smtp.use_tls') == True
    assert config.get('voicemail.smtp.username') == "cmattinson"
    
    # Check email settings
    assert config.get('voicemail.email.from_address') == "Voicemail@albl.com"
    assert config.get('voicemail.email.from_name') == "ABCo Voicemail"
    
    # Check reminder settings
    assert config.get('voicemail.reminders.enabled') == True
    assert config.get('voicemail.reminders.time') == "09:00"
    
    print("✓ Email notifier configuration loads correctly")


def test_email_notifier_initialization():
    """Test email notifier initialization"""
    print("Testing email notifier initialization...")
    
    config = Config('config.yml')
    notifier = EmailNotifier(config)
    
    assert notifier.enabled == True
    assert notifier.smtp_host == "192.168.1.75"
    assert notifier.smtp_port == 587
    assert notifier.use_tls == True
    assert notifier.from_address == "Voicemail@albl.com"
    assert notifier.from_name == "ABCo Voicemail"
    
    print("✓ Email notifier initializes correctly")


def test_voicemail_with_email():
    """Test voicemail system with email integration"""
    print("Testing voicemail system with email integration...")
    
    # Create temporary directory for test
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = Config('config.yml')
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        
        # Check that email notifier is initialized
        assert vm_system.email_notifier is not None
        assert vm_system.email_notifier.enabled == True
        
        # Save a test message (won't actually send email without SMTP server)
        test_audio = b'RIFF' + b'\x00' * 100
        message_id = vm_system.save_message(
            extension_number="1001",
            caller_id="1002",
            audio_data=test_audio,
            duration=30
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
    
    config = Config('config.yml')
    
    # Check that extensions have email addresses
    ext1001 = config.get_extension("1001")
    assert ext1001 is not None
    assert 'email' in ext1001
    assert ext1001['email'] == "ext1001@albl.com"
    
    ext1002 = config.get_extension("1002")
    assert ext1002 is not None
    assert 'email' in ext1002
    assert ext1002['email'] == "ext1002@albl.com"
    
    print("✓ Extensions have email addresses configured")


def test_no_answer_timeout_config():
    """Test no-answer timeout configuration"""
    print("Testing no-answer timeout configuration...")
    
    config = Config('config.yml')
    
    # Check no-answer timeout setting
    timeout = config.get('voicemail.no_answer_timeout')
    assert timeout is not None
    assert timeout == 30
    
    print("✓ No-answer timeout configured correctly")


if __name__ == '__main__':
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
    
    sys.exit(0 if failed == 0 else 1)
