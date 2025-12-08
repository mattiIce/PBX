#!/usr/bin/env python3
"""
Test voicemail custom greeting recording and management through IVR menu

This test validates:
1. Recording a custom greeting via IVR
2. Reviewing the recorded greeting (play, re-record, delete, save)
3. Proper state transitions during greeting management
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.voicemail import VoicemailSystem, VoicemailIVR
from pbx.utils.config import Config

# Test constants
TEST_AUDIO_DATA = b'test greeting audio data'


def test_access_options_menu():
    """Test accessing the options menu from main menu"""
    print("Testing access to options menu...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox with PIN
    mailbox = vm_system.get_mailbox('1001')
    mailbox.set_pin('1234')
    
    # Create IVR instance in main menu
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU
    
    # Press 2 for options menu
    result = ivr.handle_dtmf('2')
    
    assert ivr.state == VoicemailIVR.STATE_OPTIONS_MENU, "Should be in options menu state"
    assert result['action'] == 'play_prompt', "Should play options menu prompt"
    assert result['prompt'] == 'options_menu', "Should be options menu prompt"
    
    print("✓ Successfully accessed options menu")


def test_start_greeting_recording():
    """Test starting greeting recording from options menu"""
    print("Testing start greeting recording...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox
    mailbox = vm_system.get_mailbox('1001')
    
    # Create IVR instance in options menu
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_OPTIONS_MENU
    
    # Press 1 to record greeting
    result = ivr.handle_dtmf('1')
    
    assert ivr.state == VoicemailIVR.STATE_RECORDING_GREETING, "Should be in recording greeting state"
    assert result['action'] == 'start_recording', "Should start recording"
    assert result['recording_type'] == 'greeting', "Recording type should be greeting"
    
    print("✓ Successfully started greeting recording")


def test_finish_greeting_recording():
    """Test finishing greeting recording with #"""
    print("Testing finish greeting recording...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox
    mailbox = vm_system.get_mailbox('1001')
    
    # Create IVR instance in recording state
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_RECORDING_GREETING
    
    # Press # to finish recording
    result = ivr.handle_dtmf('#')
    
    assert ivr.state == VoicemailIVR.STATE_GREETING_REVIEW, "Should be in greeting review state"
    assert result['action'] == 'stop_recording', "Should stop recording"
    assert result['save_as'] == 'greeting', "Should save as greeting"
    
    print("✓ Successfully finished greeting recording")


def test_greeting_review_playback():
    """Test playing back recorded greeting for review"""
    print("Testing greeting review playback...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox
    mailbox = vm_system.get_mailbox('1001')
    
    # Create IVR instance in review state with recorded greeting
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_GREETING_REVIEW
    ivr.recorded_greeting_data = TEST_AUDIO_DATA
    
    # Press 1 to listen to greeting
    result = ivr.handle_dtmf('1')
    
    assert result['action'] == 'play_greeting', "Should play greeting"
    assert ivr.state == VoicemailIVR.STATE_GREETING_REVIEW, "Should stay in review state"
    
    print("✓ Successfully requested greeting playback")


def test_greeting_review_rerecord():
    """Test re-recording greeting from review menu"""
    print("Testing greeting re-record...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox
    mailbox = vm_system.get_mailbox('1001')
    
    # Create IVR instance in review state
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_GREETING_REVIEW
    ivr.recorded_greeting_data = TEST_AUDIO_DATA
    
    # Press 2 to re-record
    result = ivr.handle_dtmf('2')
    
    assert ivr.state == VoicemailIVR.STATE_RECORDING_GREETING, "Should be back in recording state"
    assert result['action'] == 'start_recording', "Should start recording again"
    assert ivr.recorded_greeting_data is None, "Previous recording should be cleared"
    
    print("✓ Successfully started re-recording")


def test_greeting_review_delete():
    """Test deleting custom greeting from review menu"""
    print("Testing greeting deletion...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox with existing greeting
    mailbox = vm_system.get_mailbox('1001')
    mailbox.save_greeting(b'existing greeting data')
    
    # Create IVR instance in review state
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_GREETING_REVIEW
    ivr.recorded_greeting_data = TEST_AUDIO_DATA
    
    # Press 3 to delete and use default
    result = ivr.handle_dtmf('3')
    
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should return to main menu"
    assert result['action'] == 'play_prompt', "Should play prompt"
    assert result['prompt'] == 'greeting_deleted', "Should be greeting deleted prompt"
    assert ivr.recorded_greeting_data is None, "Recording should be cleared"
    assert not mailbox.has_custom_greeting(), "Custom greeting should be deleted"
    
    print("✓ Successfully deleted greeting")


def test_greeting_review_save():
    """Test saving recorded greeting from review menu"""
    print("Testing greeting save...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox
    mailbox = vm_system.get_mailbox('1001')
    
    # Create IVR instance in review state
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_GREETING_REVIEW
    ivr.recorded_greeting_data = TEST_AUDIO_DATA
    
    # Press * to save and return to main menu
    result = ivr.handle_dtmf('*')
    
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should return to main menu"
    assert result['action'] == 'play_prompt', "Should play prompt"
    assert result['prompt'] == 'greeting_saved', "Should be greeting saved prompt"
    assert ivr.recorded_greeting_data is None, "Recording should be cleared after saving"
    assert mailbox.has_custom_greeting(), "Custom greeting should be saved"
    
    print("✓ Successfully saved greeting")


def test_complete_greeting_workflow():
    """Test complete workflow: record -> review -> save"""
    print("Testing complete greeting workflow...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox
    mailbox = vm_system.get_mailbox('1001')
    mailbox.set_pin('1234')
    
    # Create IVR instance starting from main menu
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU
    
    # Step 1: Go to options menu
    result = ivr.handle_dtmf('2')
    assert ivr.state == VoicemailIVR.STATE_OPTIONS_MENU
    
    # Step 2: Start recording
    result = ivr.handle_dtmf('1')
    assert ivr.state == VoicemailIVR.STATE_RECORDING_GREETING
    assert result['action'] == 'start_recording'
    
    # Step 3: Simulate recording and finish with #
    ivr.save_recorded_greeting(TEST_AUDIO_DATA)
    result = ivr.handle_dtmf('#')
    assert ivr.state == VoicemailIVR.STATE_GREETING_REVIEW
    
    # Step 4: Listen to greeting
    result = ivr.handle_dtmf('1')
    assert result['action'] == 'play_greeting'
    assert ivr.get_recorded_greeting() == TEST_AUDIO_DATA
    
    # Step 5: Save and return to main menu
    result = ivr.handle_dtmf('*')
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU
    assert mailbox.has_custom_greeting()
    
    print("✓ Successfully completed greeting workflow")


def test_return_to_main_menu_from_options():
    """Test returning to main menu from options menu"""
    print("Testing return to main menu from options...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Create IVR instance in options menu
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_OPTIONS_MENU
    
    # Press * to return to main menu
    result = ivr.handle_dtmf('*')
    
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should return to main menu"
    assert result['action'] == 'play_prompt', "Should play prompt"
    assert result['prompt'] == 'main_menu', "Should be main menu prompt"
    
    print("✓ Successfully returned to main menu")


if __name__ == '__main__':
    print("=" * 60)
    print("Running Voicemail Greeting Menu Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_access_options_menu,
        test_start_greeting_recording,
        test_finish_greeting_recording,
        test_greeting_review_playback,
        test_greeting_review_rerecord,
        test_greeting_review_delete,
        test_greeting_review_save,
        test_complete_greeting_workflow,
        test_return_to_main_menu_from_options,
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
    
    sys.exit(0 if failed == 0 else 1)
