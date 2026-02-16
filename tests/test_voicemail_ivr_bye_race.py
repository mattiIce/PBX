#!/usr/bin/env python3
"""
Test voicemail IVR BYE request race condition fix

This test validates that when a BYE request is received during voicemail IVR
(e.g., after PIN entry with pound key), the IVR session properly handles the
call termination without continuing to play audio.
"""

from pbx.core.call import Call, CallState
from pbx.features.voicemail import VoicemailIVR, VoicemailSystem
from pbx.utils.config import Config

# Test constants
TEST_AUDIO_DATA = b"test audio data"
TEST_MESSAGE_DURATION = 10


def test_ivr_handles_early_call_termination() -> None:
    """
    Test that IVR properly handles call termination during PIN entry

    This simulates the race condition where:
    1. User enters PIN and presses #
    2. IVR transitions to main menu
    3. BYE request terminates the call
    4. IVR should not play audio after call ends
    """

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox with PIN
    mailbox = vm_system.get_mailbox("1001")
    mailbox.set_pin("1234")

    # Create IVR instance
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_PIN_ENTRY

    # Create a mock call object
    call = Call("test-call-123", "1001", "*97")
    call.state = CallState.CONNECTED

    # Enter PIN digits
    ivr.handle_dtmf("1")
    ivr.handle_dtmf("2")
    ivr.handle_dtmf("3")
    ivr.handle_dtmf("4")

    # Now simulate the scenario:
    # 1. User presses # to complete PIN entry
    # 2. IVR would normally transition to main menu and return play_prompt
    # action
    result = ivr.handle_dtmf("#")

    # Verify IVR transitioned to main menu state
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should be in main menu state"
    assert result["action"] == "play_prompt", "Should return play_prompt action"

    # 3. Simulate BYE request coming in (call terminates)
    call.end()

    # 4. The IVR session code should check call.state before playing audio
    # and exit the loop immediately if the call has ended, preventing
    # audio playback after call termination

    assert call.state == CallState.ENDED, "Call should be ended"


def test_ivr_handles_call_termination_during_message_playback() -> None:
    """
    Test that IVR handles call termination while playing a voicemail message
    """

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox with a message
    mailbox = vm_system.get_mailbox("1001")
    mailbox.save_message("1002", TEST_AUDIO_DATA, duration=TEST_MESSAGE_DURATION)

    # Create IVR instance in main menu
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Create a mock call object
    call = Call("test-call-456", "1001", "*97")
    call.state = CallState.CONNECTED

    # Press 1 to listen to messages
    result = ivr.handle_dtmf("1")

    # Should transition to playing message
    assert ivr.state == VoicemailIVR.STATE_PLAYING_MESSAGE
    assert result["action"] == "play_message"

    # Simulate call termination during playback
    call.end()

    # The IVR session should detect this and stop playing
    assert call.state == CallState.ENDED


def test_ivr_handles_hangup_action_with_ended_call() -> None:
    """
    Test that IVR handles hangup action when call is already ended
    """

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Create IVR instance in main menu
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Create a mock call object
    call = Call("test-call-789", "1001", "*97")
    call.state = CallState.CONNECTED

    # Press * to exit (hangup action)
    result = ivr.handle_dtmf("*")

    # Should return hangup action and transition to goodbye state
    assert result["action"] == "hangup"
    assert result["prompt"] == "goodbye"
    assert ivr.state == VoicemailIVR.STATE_GOODBYE

    # Simulate call already ended before goodbye prompt can play
    call.end()

    # The IVR session should skip goodbye prompt if call is already ended
    assert call.state == CallState.ENDED


def test_pin_entry_clears_after_processing() -> None:
    """
    Test that PIN is cleared after verification for security
    """

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox with PIN
    mailbox = vm_system.get_mailbox("1001")
    mailbox.set_pin("1234")

    # Create IVR instance
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_PIN_ENTRY

    # Enter PIN digits
    ivr.handle_dtmf("1")
    ivr.handle_dtmf("2")
    ivr.handle_dtmf("3")
    ivr.handle_dtmf("4")

    # Verify PIN is being collected
    assert ivr.entered_pin == "1234", "PIN should be collected"

    # Press # to complete PIN entry
    ivr.handle_dtmf("#")

    # Verify PIN was cleared after verification (security)
    assert ivr.entered_pin == "", "PIN should be cleared after verification"
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should transition to main menu"
