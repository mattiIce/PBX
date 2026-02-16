#!/usr/bin/env python3
"""
Test that the options menu prompt is available and working correctly
This test validates the fix for the missing options menu voice prompt issue
"""

from pathlib import Path

from pbx.features.voicemail import VoicemailIVR, VoicemailSystem
from pbx.utils.config import Config


def test_options_menu_prompt_file_exists() -> None:
    """Test that options_menu.wav file exists"""

    options_menu_path = Path("voicemail_prompts") / "options_menu.wav"
    assert Path(options_menu_path).exists(), f"options_menu.wav should exist at {options_menu_path}"

    # Verify it's a valid file with non-zero size
    file_size = Path(options_menu_path).stat().st_size
    assert file_size > 0, "options_menu.wav should not be empty"


def test_options_menu_message_returned() -> None:
    """Test that pressing 2 from main menu returns the options menu message"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Create IVR instance in main menu
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Press 2 for options menu
    result = ivr.handle_dtmf("2")

    # Verify the state changed to options menu
    assert ivr.state == VoicemailIVR.STATE_OPTIONS_MENU, "Should be in options menu state"

    # Verify the action is play_prompt
    assert result["action"] == "play_prompt", "Should play options menu prompt"

    # Verify the prompt is options_menu
    assert result["prompt"] == "options_menu", "Should be options_menu prompt"

    # Verify the message field exists and is not empty
    assert "message" in result, "Result should include a 'message' field"
    assert result["message"], "Message should not be empty"

    # Verify the message contains expected content
    message = result["message"]
    assert "record" in message.lower() or "greeting" in message.lower(), (
        "Message should mention recording or greeting"
    )
    assert "press 1" in message.lower() or "press star" in message.lower(), (
        "Message should provide menu options"
    )


def test_options_menu_complete_flow() -> None:
    """Test complete flow: main menu -> press 2 -> options menu -> press 1 -> record greeting"""

    config = Config("config.yml")
    vm_system = VoicemailSystem(storage_path="test_voicemail", config=config)

    # Create IVR instance
    ivr = VoicemailIVR(vm_system, "1001")
    ivr.state = VoicemailIVR.STATE_MAIN_MENU

    # Step 1: Press 2 from main menu
    result = ivr.handle_dtmf("2")
    assert ivr.state == VoicemailIVR.STATE_OPTIONS_MENU
    assert result["action"] == "play_prompt"
    assert result["prompt"] == "options_menu"
    assert "message" in result

    # Step 2: Press 1 to record greeting
    result = ivr.handle_dtmf("1")
    assert ivr.state == VoicemailIVR.STATE_RECORDING_GREETING
    assert result["action"] == "start_recording"
