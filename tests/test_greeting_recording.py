#!/usr/bin/env python3
"""
Test voicemail greeting recording functionality
"""
import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.voicemail import VoicemailIVR, VoicemailSystem
from pbx.utils.config import Config


def create_fake_audio():
    """Helper function to create fake audio data for testing"""
    return b"RIFF" + b"\x00" * 100


def test_greeting_storage():
    """Test that greeting can be saved and retrieved"""
    print("Testing greeting storage...")

    # Create temp storage
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        mailbox = vm_system.get_mailbox("1001")

        # Initially no custom greeting
        assert not mailbox.has_custom_greeting(), "Should not have custom greeting initially"
        assert mailbox.get_greeting_path() is None, "Greeting path should be None initially"

        # Create fake audio data
        fake_audio = create_fake_audio()

        # Save greeting
        result = mailbox.save_greeting(fake_audio)
        assert result, "Should successfully save greeting"

        # Now should have custom greeting
        assert mailbox.has_custom_greeting(), "Should have custom greeting after saving"
        greeting_path = mailbox.get_greeting_path()
        assert greeting_path is not None, "Greeting path should not be None after saving"
        assert os.path.exists(greeting_path), "Greeting file should exist"

        # Verify content
        with open(greeting_path, "rb") as f:
            content = f.read()
            assert content == fake_audio, "Greeting content should match"

        print("✓ Greeting storage works")


def test_greeting_deletion():
    """Test that greeting can be deleted"""
    print("Testing greeting deletion...")

    # Create temp storage
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        mailbox = vm_system.get_mailbox("1001")

        # Save greeting
        fake_audio = create_fake_audio()
        mailbox.save_greeting(fake_audio)
        assert mailbox.has_custom_greeting(), "Should have greeting after saving"

        # Delete greeting
        result = mailbox.delete_greeting()
        assert result, "Should successfully delete greeting"
        assert not mailbox.has_custom_greeting(), "Should not have greeting after deletion"
        assert mailbox.get_greeting_path() is None, "Greeting path should be None after deletion"

        print("✓ Greeting deletion works")


def test_ivr_options_menu():
    """Test IVR options menu state"""
    print("Testing IVR options menu...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        ivr = VoicemailIVR(vm_system, "1001")

        # Set state to options menu
        ivr.state = VoicemailIVR.STATE_OPTIONS_MENU

        # Press 1 to record greeting
        result = ivr.handle_dtmf("1")
        assert result["action"] == "start_recording", "Should start recording"
        assert result["recording_type"] == "greeting", "Should record greeting"
        assert ivr.state == VoicemailIVR.STATE_RECORDING_GREETING, "Should be in recording state"

        # Press * to return to main menu
        ivr.state = VoicemailIVR.STATE_OPTIONS_MENU
        result = ivr.handle_dtmf("*")
        assert result["action"] == "play_prompt", "Should play prompt"
        assert result["prompt"] == "main_menu", "Should return to main menu"
        assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should be in main menu state"

        print("✓ IVR options menu works")


def test_ivr_greeting_recording():
    """Test IVR greeting recording state"""
    print("Testing IVR greeting recording...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        ivr = VoicemailIVR(vm_system, "1001")

        # Set state to recording greeting
        ivr.state = VoicemailIVR.STATE_RECORDING_GREETING

        # During recording, most digits are ignored
        result = ivr.handle_dtmf("5")
        assert result["action"] == "continue_recording", "Should continue recording"

        # Press # to finish recording
        result = ivr.handle_dtmf("#")
        assert result["action"] == "stop_recording", "Should stop recording"
        assert result["save_as"] == "greeting", "Should save as greeting"

        print("✓ IVR greeting recording works")


def test_ivr_save_recorded_greeting():
    """Test saving recorded greeting through IVR"""
    print("Testing IVR save recorded greeting...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        ivr = VoicemailIVR(vm_system, "1001")

        # Create fake audio data
        fake_audio = create_fake_audio()

        # Save greeting through IVR (stores temporarily)
        result = ivr.save_recorded_greeting(fake_audio)
        assert result, "Should successfully save greeting temporarily"

        # Verify greeting was stored temporarily (not yet in mailbox)
        assert ivr.get_recorded_greeting() == fake_audio, "Greeting should be stored temporarily"

        # Now simulate the user confirming the greeting by directly saving to
        # mailbox
        mailbox = vm_system.get_mailbox("1001")
        mailbox.save_greeting(fake_audio)
        assert (
            mailbox.has_custom_greeting()
        ), "Mailbox should have custom greeting after confirmation"

        print("✓ IVR save recorded greeting works")


def test_main_menu_to_options():
    """Test navigation from main menu to options"""
    print("Testing main menu to options navigation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        ivr = VoicemailIVR(vm_system, "1001")

        # Set state to main menu
        ivr.state = VoicemailIVR.STATE_MAIN_MENU

        # Press 2 to access options
        result = ivr.handle_dtmf("2")
        assert result["action"] == "play_prompt", "Should play prompt"
        assert result["prompt"] == "options_menu", "Should show options menu"
        assert ivr.state == VoicemailIVR.STATE_OPTIONS_MENU, "Should be in options menu state"

        print("✓ Main menu to options navigation works")


def test_greeting_persistence():
    """Test that greeting persists across mailbox instances"""
    print("Testing greeting persistence...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config("config.yml")

        # Create first mailbox instance and save greeting
        vm_system1 = VoicemailSystem(storage_path=temp_dir, config=config)
        mailbox1 = vm_system1.get_mailbox("1001")
        fake_audio = create_fake_audio()
        mailbox1.save_greeting(fake_audio)
        assert mailbox1.has_custom_greeting(), "First instance should have greeting"

        # Create second mailbox instance for same extension
        vm_system2 = VoicemailSystem(storage_path=temp_dir, config=config)
        mailbox2 = vm_system2.get_mailbox("1001")

        # Should still have greeting
        assert mailbox2.has_custom_greeting(), "Second instance should have greeting"
        greeting_path = mailbox2.get_greeting_path()
        assert greeting_path is not None, "Should have greeting path"

        # Verify content matches
        with open(greeting_path, "rb") as f:
            content = f.read()
            assert content == fake_audio, "Content should match original"

        print("✓ Greeting persistence works")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Voicemail Greeting Recording Tests")
    print("=" * 60)
    print()

    tests = [
        test_greeting_storage,
        test_greeting_deletion,
        test_ivr_options_menu,
        test_ivr_greeting_recording,
        test_ivr_save_recorded_greeting,
        test_main_menu_to_options,
        test_greeting_persistence,
    ]

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
