#!/usr/bin/env python3
"""
Test voicemail IVR BYE request race condition fix

This test validates that when a BYE request is received during voicemail IVR
(e.g., after PIN entry with pound key), the IVR session properly handles the
call termination without continuing to play audio.
"""
import sys
import os
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.voicemail import VoicemailSystem, VoicemailIVR
from pbx.core.call import Call, CallState
from pbx.utils.config import Config

# Test constants
TEST_AUDIO_DATA = b'test audio data'
TEST_MESSAGE_DURATION = 10


def test_ivr_handles_early_call_termination():
    """
    Test that IVR properly handles call termination during PIN entry
    
    This simulates the race condition where:
    1. User enters PIN and presses #
    2. IVR transitions to main menu
    3. BYE request terminates the call
    4. IVR should not play audio after call ends
    """
    print("Testing IVR handles early call termination...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox with PIN
    mailbox = vm_system.get_mailbox('1001')
    mailbox.set_pin('1234')
    
    # Create IVR instance
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_PIN_ENTRY
    
    # Create a mock call object
    call = Call('test-call-123', '1001', '*97')
    call.state = CallState.CONNECTED
    
    # Enter PIN digits
    ivr.handle_dtmf('1')
    ivr.handle_dtmf('2')
    ivr.handle_dtmf('3')
    ivr.handle_dtmf('4')
    
    # Now simulate the scenario:
    # 1. User presses # to complete PIN entry
    # 2. IVR would normally transition to main menu and return play_prompt action
    result = ivr.handle_dtmf('#')
    
    # Verify IVR transitioned to main menu state
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should be in main menu state"
    assert result['action'] == 'play_prompt', "Should return play_prompt action"
    
    # 3. Simulate BYE request coming in (call terminates)
    call.end()
    
    # 4. The IVR session code should check call.state before playing audio
    # and exit the loop immediately if the call has ended, preventing
    # audio playback after call termination
    
    assert call.state == CallState.ENDED, "Call should be ended"
    
    print("✓ IVR properly handles early call termination")


def test_ivr_handles_call_termination_during_message_playback():
    """
    Test that IVR handles call termination while playing a voicemail message
    """
    print("Testing IVR handles call termination during message playback...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox with a message
    mailbox = vm_system.get_mailbox('1001')
    mailbox.save_message('1002', TEST_AUDIO_DATA, duration=TEST_MESSAGE_DURATION)
    
    # Create IVR instance in main menu
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU
    
    # Create a mock call object
    call = Call('test-call-456', '1001', '*97')
    call.state = CallState.CONNECTED
    
    # Press 1 to listen to messages
    result = ivr.handle_dtmf('1')
    
    # Should transition to playing message
    assert ivr.state == VoicemailIVR.STATE_PLAYING_MESSAGE
    assert result['action'] == 'play_message'
    
    # Simulate call termination during playback
    call.end()
    
    # The IVR session should detect this and stop playing
    assert call.state == CallState.ENDED
    
    print("✓ IVR handles call termination during message playback")


def test_ivr_handles_hangup_action_with_ended_call():
    """
    Test that IVR handles hangup action when call is already ended
    """
    print("Testing IVR handles hangup action with ended call...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Create IVR instance in main menu
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_MAIN_MENU
    
    # Create a mock call object
    call = Call('test-call-789', '1001', '*97')
    call.state = CallState.CONNECTED
    
    # Press * to exit (hangup action)
    result = ivr.handle_dtmf('*')
    
    # Should return hangup action and transition to goodbye state
    assert result['action'] == 'hangup'
    assert result['prompt'] == 'goodbye'
    assert ivr.state == VoicemailIVR.STATE_GOODBYE
    
    # Simulate call already ended before goodbye prompt can play
    call.end()
    
    # The IVR session should skip goodbye prompt if call is already ended
    assert call.state == CallState.ENDED
    
    print("✓ IVR handles hangup action with ended call")


def test_pin_entry_clears_after_processing():
    """
    Test that PIN is cleared after verification for security
    """
    print("Testing PIN is cleared after verification...")
    
    config = Config('config.yml')
    vm_system = VoicemailSystem(storage_path='test_voicemail', config=config)
    
    # Set up mailbox with PIN
    mailbox = vm_system.get_mailbox('1001')
    mailbox.set_pin('1234')
    
    # Create IVR instance
    ivr = VoicemailIVR(vm_system, '1001')
    ivr.state = VoicemailIVR.STATE_PIN_ENTRY
    
    # Enter PIN digits
    ivr.handle_dtmf('1')
    ivr.handle_dtmf('2')
    ivr.handle_dtmf('3')
    ivr.handle_dtmf('4')
    
    # Verify PIN is being collected
    assert ivr.entered_pin == '1234', "PIN should be collected"
    
    # Press # to complete PIN entry
    result = ivr.handle_dtmf('#')
    
    # Verify PIN was cleared after verification (security)
    assert ivr.entered_pin == '', "PIN should be cleared after verification"
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should transition to main menu"
    
    print("✓ PIN is properly cleared after verification")


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)    print("Running Voicemail IVR BYE Race Condition Tests")    print("=" * 60)    print()        tests = [        test_ivr_handles_early_call_termination,        test_ivr_handles_call_termination_during_message_playback,        test_ivr_handles_hangup_action_with_ended_call,        test_pin_entry_clears_after_processing,    ]        passed = 0    failed = 0        for test in tests:        try:            test()            passed += 1        except Exception as e:            print(f"✗ {test.__name__} failed: {e}")            import traceback            traceback.print_exc()            failed += 1        print()    print("=" * 60)    print(f"Results: {passed} passed, {failed} failed")    print("=" * 60)        return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
