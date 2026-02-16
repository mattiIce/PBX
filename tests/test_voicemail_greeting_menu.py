#!/usr/bin/env python3
"""
Test voicemail custom greeting recording and management through IVR menu

This test validates:
1. Recording a custom greeting via IVR
2. Reviewing the recorded greeting (play, re-record, delete, save)
3. Proper state transitions during greeting management
"""

from pbx.features.voicemail import VoicemailIVR, VoicemailSystem
from pbx.utils.config import Config

# Test constants
TEST_AUDIO_DATA = b"test greeting audio data"


def test_access_options_menu() -> None:
    """Test accessing the options menu from main menu"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox with PIN
    mailbox = vm_system.get_mailbox("1001")
    mailbox.set_pin("1234")

    # Create IVR instance in main menu
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Press 2 for options menu
    result = ivr.handle_dtmf("2")

    assert ivr.state == VoicemailIVR.STATE_OPTIONS_MENU, "Should be in options menu state"
    assert result["action"] == "play_prompt", "Should play options menu prompt"
    assert result["prompt"] == "options_menu", "Should be options menu prompt"


def test_start_greeting_recording() -> None:
    """Test starting greeting recording from options menu"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox
    vm_system.get_mailbox("1001")

    # Create IVR instance in options menu
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_OPTIONS_MENU

    # Press 1 to record greeting
    result = ivr.handle_dtmf("1")

    assert ivr.state == VoicemailIVR.STATE_RECORDING_GREETING, (
        "Should be in recording greeting state"
    )
    assert result["action"] == "start_recording", "Should start recording"
    assert result["recording_type"] == "greeting", "Recording type should be greeting"


def test_finish_greeting_recording() -> None:
    """Test finishing greeting recording with #"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox
    vm_system.get_mailbox("1001")

    # Create IVR instance in recording state
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_RECORDING_GREETING

    # Press # to finish recording
    result = ivr.handle_dtmf("#")

    assert ivr.state == VoicemailIVR.STATE_GREETING_REVIEW, "Should be in greeting review state"
    assert result["action"] == "stop_recording", "Should stop recording"
    assert result["save_as"] == "greeting", "Should save as greeting"


def test_greeting_review_playback() -> None:
    """Test playing back recorded greeting for review"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox
    vm_system.get_mailbox("1001")

    # Create IVR instance in review state with recorded greeting
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_GREETING_REVIEW
    ivr.recorded_greeting_data = TEST_AUDIO_DATA

    # Press 1 to listen to greeting
    result = ivr.handle_dtmf("1")

    assert result["action"] == "play_greeting", "Should play greeting"
    assert ivr.state == VoicemailIVR.STATE_GREETING_REVIEW, "Should stay in review state"


def test_greeting_review_rerecord() -> None:
    """Test re-recording greeting from review menu"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox
    vm_system.get_mailbox("1001")

    # Create IVR instance in review state
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_GREETING_REVIEW
    ivr.recorded_greeting_data = TEST_AUDIO_DATA

    # Press 2 to re-record
    result = ivr.handle_dtmf("2")

    assert ivr.state == VoicemailIVR.STATE_RECORDING_GREETING, "Should be back in recording state"
    assert result["action"] == "start_recording", "Should start recording again"
    assert ivr.recorded_greeting_data is None, "Previous recording should be cleared"


def test_greeting_review_delete() -> None:
    """Test deleting custom greeting from review menu"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox with existing greeting
    mailbox = vm_system.get_mailbox("1001")
    mailbox.save_greeting(b"existing greeting data")

    # Create IVR instance in review state
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_GREETING_REVIEW
    ivr.recorded_greeting_data = TEST_AUDIO_DATA

    # Press 3 to delete and use default
    result = ivr.handle_dtmf("3")

    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should return to main menu"
    assert result["action"] == "play_prompt", "Should play prompt"
    assert result["prompt"] == "greeting_deleted", "Should be greeting deleted prompt"
    assert ivr.recorded_greeting_data is None, "Recording should be cleared"
    assert not mailbox.has_custom_greeting(), "Custom greeting should be deleted"


def test_greeting_review_save() -> None:
    """Test saving recorded greeting from review menu"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox
    mailbox = vm_system.get_mailbox("1001")

    # Create IVR instance in review state
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_GREETING_REVIEW
    ivr.recorded_greeting_data = TEST_AUDIO_DATA

    # Press * to save and return to main menu
    result = ivr.handle_dtmf("*")

    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should return to main menu"
    assert result["action"] == "play_prompt", "Should play prompt"
    assert result["prompt"] == "greeting_saved", "Should be greeting saved prompt"
    assert ivr.recorded_greeting_data is None, "Recording should be cleared after saving"
    assert mailbox.has_custom_greeting(), "Custom greeting should be saved"


def test_complete_greeting_workflow() -> None:
    """Test complete workflow: record -> review -> save"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Set up mailbox
    mailbox = vm_system.get_mailbox("1001")
    mailbox.set_pin("1234")

    # Create IVR instance starting from main menu
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Step 1: Go to options menu
    result = ivr.handle_dtmf("2")
    assert ivr.state == VoicemailIVR.STATE_OPTIONS_MENU

    # Step 2: Start recording
    result = ivr.handle_dtmf("1")
    assert ivr.state == VoicemailIVR.STATE_RECORDING_GREETING
    assert result["action"] == "start_recording"

    # Step 3: Simulate recording and finish with #
    ivr.save_recorded_greeting(TEST_AUDIO_DATA)
    result = ivr.handle_dtmf("#")
    assert ivr.state == VoicemailIVR.STATE_GREETING_REVIEW

    # Step 4: Listen to greeting
    result = ivr.handle_dtmf("1")
    assert result["action"] == "play_greeting"
    assert ivr.get_recorded_greeting() == TEST_AUDIO_DATA

    # Step 5: Save and return to main menu
    result = ivr.handle_dtmf("*")
    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU
    assert mailbox.has_custom_greeting()


def test_return_to_main_menu_from_options() -> None:
    """Test returning to main menu from options menu"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Create IVR instance in options menu
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_OPTIONS_MENU

    # Press * to return to main menu
    result = ivr.handle_dtmf("*")

    assert ivr.state == VoicemailIVR.STATE_MAIN_MENU, "Should return to main menu"
    assert result["action"] == "play_prompt", "Should play prompt"
    assert result["prompt"] == "main_menu", "Should be main menu prompt"
