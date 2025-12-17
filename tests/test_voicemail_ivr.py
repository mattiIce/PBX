#!/usr/bin/env python3
"""
Test voicemail IVR functionality
Tests that voicemail prompts and menu navigation work correctly
"""
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.voicemail import VoicemailBox, VoicemailIVR, VoicemailSystem
from pbx.utils.audio import generate_voice_prompt
from pbx.utils.config import Config



def test_voice_prompt_generation():
    """Test that voice prompts are generated correctly"""
    print("Testing voice prompt generation...")

    # Test various prompt types
    prompt_types = [
        'leave_message',
        'enter_pin',
        'main_menu',
        'message_menu',
        'no_messages',
        'goodbye',
        'invalid_option',
        'you_have_messages'
    ]

    for prompt_type in prompt_types:
        prompt = generate_voice_prompt(prompt_type)

        # Verify it's a valid WAV file
        assert prompt.startswith(
            b'RIFF'), f"Prompt {prompt_type} doesn't have RIFF header"
        assert b'WAVE' in prompt[:
                                 20], f"Prompt {prompt_type} doesn't have WAVE marker"
        assert len(prompt) > 100, f"Prompt {prompt_type} is too short"

        print(f"  ✓ {prompt_type} prompt: {len(prompt)} bytes")

    print("✓ Voice prompt generation works")


def test_voicemail_ivr_initialization():
    """Test that VoicemailIVR can be initialized"""
    print("Testing VoicemailIVR initialization...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    # Create IVR for extension 1001
    ivr = VoicemailIVR(vm_system, '1001')

    assert ivr.extension_number == '1001'
    assert ivr.state == VoicemailIVR.STATE_WELCOME
    assert ivr.current_message_index == 0

    print("✓ VoicemailIVR initialization works")


def test_voicemail_ivr_welcome_state():
    """Test IVR welcome state handling"""
    print("Testing VoicemailIVR welcome state...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Test 1: Non-digit input should transition to PIN entry and prompt
    ivr = VoicemailIVR(vm_system, '1001')
    result = ivr.handle_dtmf('*')
    assert result['action'] == 'play_prompt'
    assert result['prompt'] == 'enter_pin'
    assert ivr.state == VoicemailIVR.STATE_PIN_ENTRY

    # Test 2: Digit input should transition to PIN entry and collect the digit
    ivr.state = VoicemailIVR.STATE_WELCOME  # Reset to welcome state
    ivr.entered_pin = ''  # Clear any collected digits
    
    result = ivr.handle_dtmf('1')
    assert result['action'] == 'collect_digit'
    assert ivr.state == VoicemailIVR.STATE_PIN_ENTRY
    assert ivr.entered_pin == '1'  # First digit should be collected

    print("✓ VoicemailIVR welcome state works")


def test_voicemail_ivr_pin_entry():
    """Test IVR PIN entry"""
    print("Testing VoicemailIVR PIN entry...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    # Get mailbox and set PIN
    mailbox = vm_system.get_mailbox('1001')
    mailbox.set_pin('1234')

    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_PIN_ENTRY

    # Enter correct PIN digits
    ivr.handle_dtmf('1')
    ivr.handle_dtmf('2')
    ivr.handle_dtmf('3')
    ivr.handle_dtmf('4')
    result = ivr.handle_dtmf('#')  # Complete PIN entry

    # Should transition to main menu
    assert result['action'] == 'play_prompt'
    assert result['prompt'] == 'main_menu'
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU

    print("✓ VoicemailIVR PIN entry works")


def test_voicemail_ivr_invalid_pin():
    """Test IVR invalid PIN handling"""
    print("Testing VoicemailIVR invalid PIN...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    # Get mailbox and set PIN
    mailbox = vm_system.get_mailbox('1001')
    mailbox.set_pin('1234')

    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_PIN_ENTRY

    # Enter wrong PIN
    ivr.handle_dtmf('9')
    ivr.handle_dtmf('9')
    ivr.handle_dtmf('9')
    ivr.handle_dtmf('9')
    result = ivr.handle_dtmf('#')

    # Should reject and stay in PIN entry
    assert result['action'] == 'play_prompt'
    assert result['prompt'] == 'invalid_pin'
    assert ivr.state == VoicemailIVR.STATE_PIN_ENTRY
    assert ivr.pin_attempts == 1

    print("✓ VoicemailIVR invalid PIN handling works")


def test_voicemail_ivr_main_menu():
    """Test IVR main menu navigation"""
    print("Testing VoicemailIVR main menu...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    # Create a voicemail message
    mailbox = vm_system.get_mailbox('1001')
    mailbox.save_message('1002', b'test audio data', duration=5)

    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Press 1 to listen to messages
    result = ivr.handle_dtmf('1')

    # Should start playing first message
    assert result['action'] == 'play_message'
    assert 'message_id' in result
    assert 'file_path' in result
    assert ivr.state == VoicemailIVR.STATE_PLAYING_MESSAGE

    print("✓ VoicemailIVR main menu works")


def test_voicemail_ivr_message_menu():
    """Test IVR message menu navigation"""
    print("Testing VoicemailIVR message menu...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    # Create voicemail messages
    mailbox = vm_system.get_mailbox('1001')
    mailbox.save_message('1002', b'test audio 1', duration=5)
    mailbox.save_message('1003', b'test audio 2', duration=5)

    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Navigate to playing first message
    ivr.handle_dtmf('1')

    # Simulate message playback completion - transition to message menu
    ivr.state = VoicemailIVR.STATE_MESSAGE_MENU

    # Press 2 for next message
    result = ivr.handle_dtmf('2')

    # Should play next message
    assert result['action'] == 'play_message'
    assert ivr.current_message_index == 1

    print("✓ VoicemailIVR message menu works")


def test_voicemail_ivr_delete_message():
    """Test IVR message deletion"""
    print("Testing VoicemailIVR message deletion...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    # Create voicemail messages
    mailbox = vm_system.get_mailbox('1001')
    msg1_id = mailbox.save_message('1002', b'test audio 1', duration=5)
    msg2_id = mailbox.save_message('1003', b'test audio 2', duration=5)

    initial_count = len(mailbox.get_messages())

    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Navigate to playing first message
    ivr.handle_dtmf('1')
    ivr.state = VoicemailIVR.STATE_MESSAGE_MENU

    # Press 3 to delete message
    result = ivr.handle_dtmf('3')

    # Should delete and move to next or main menu
    final_count = len(mailbox.get_messages())
    assert final_count == initial_count - 1, "Message should be deleted"

    print("✓ VoicemailIVR message deletion works")


def test_voicemail_ivr_no_messages():
    """Test IVR when there are no messages"""
    print("Testing VoicemailIVR with no messages...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    # Empty mailbox
    mailbox = vm_system.get_mailbox('1005')

    ivr = VoicemailIVR(vm_system, '1005')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Press 1 to listen to messages
    result = ivr.handle_dtmf('1')

    # Should indicate no messages
    assert result['action'] == 'play_prompt'
    assert result['prompt'] == 'no_messages'

    print("✓ VoicemailIVR no messages handling works")


def test_voicemail_ivr_exit():
    """Test IVR exit functionality"""
    print("Testing VoicemailIVR exit...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Press * to exit
    result = ivr.handle_dtmf('*')

    # Should hangup
    assert result['action'] == 'hangup'
    assert result['prompt'] == 'goodbye'
    assert ivr.state == VoicemailIVR.STATE_GOODBYE

    print("✓ VoicemailIVR exit works")


def test_voicemail_ivr_pin_entry_from_welcome():
    """Test IVR PIN entry starting from welcome state (verifies first digit not lost)"""
    print("Testing VoicemailIVR PIN entry from welcome state...")

    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)

    # Get mailbox and set PIN
    mailbox = vm_system.get_mailbox('1001')
    mailbox.set_pin('1234')

    # Create IVR in WELCOME state
    ivr = VoicemailIVR(vm_system, '1001')
    assert ivr.state == VoicemailIVR.STATE_WELCOME

    # Enter PIN starting from welcome state: 1234#
    # First digit '1' should trigger transition AND be collected
    result1 = ivr.handle_dtmf('1')
    assert ivr.state == VoicemailIVR.STATE_PIN_ENTRY
    assert ivr.entered_pin == '1', f"Expected entered_pin='1', got '{ivr.entered_pin}'"

    # Continue entering remaining digits
    ivr.handle_dtmf('2')
    assert ivr.entered_pin == '12'
    
    ivr.handle_dtmf('3')
    assert ivr.entered_pin == '123'
    
    ivr.handle_dtmf('4')
    assert ivr.entered_pin == '1234'
    
    # Press # to complete PIN entry
    result = ivr.handle_dtmf('#')

    # Should successfully authenticate and transition to main menu
    assert result['action'] == 'play_prompt'
    assert result['prompt'] == 'main_menu'
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU
    assert ivr.entered_pin == '', "PIN should be cleared after verification"

    print("✓ VoicemailIVR PIN entry from welcome state works (first digit not lost)")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Voicemail IVR Tests")
    print("=" * 60)
    print()

    tests = [
        test_voice_prompt_generation,
        test_voicemail_ivr_initialization,
        test_voicemail_ivr_welcome_state,
        test_voicemail_ivr_pin_entry,
        test_voicemail_ivr_invalid_pin,
        test_voicemail_ivr_pin_entry_from_welcome,  # New test for the fix
        test_voicemail_ivr_main_menu,
        test_voicemail_ivr_message_menu,
        test_voicemail_ivr_delete_message,
        test_voicemail_ivr_no_messages,
        test_voicemail_ivr_exit,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
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
