#!/usr/bin/env python3
"""
Test voicemail IVR functionality
Tests that voicemail prompts and menu navigation work correctly
"""
import os
import sys
import time
import importlib
import io
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.features.voicemail import VoicemailBox, VoicemailIVR, VoicemailSystem
from pbx.utils.audio import generate_voice_prompt
from pbx.utils.config import Config


# Helper function for DEBUG_VM_PIN tests to manage environment and module reloading
def reload_voicemail_module():
    """Reload the voicemail module to pick up environment changes"""
    from pbx.features import voicemail
    importlib.reload(voicemail)
    return voicemail


def restore_debug_vm_pin_env(original_value):
    """Restore the DEBUG_VM_PIN environment variable to its original state"""
    if original_value is not None:
        os.environ['DEBUG_VM_PIN'] = original_value
    elif 'DEBUG_VM_PIN' in os.environ:
        del os.environ['DEBUG_VM_PIN']
    # Reload module to restore original state
    reload_voicemail_module()


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


def test_debug_pin_flag_disabled_by_default():
    """Test that DEBUG_VM_PIN flag is disabled by default"""
    print("Testing DEBUG_VM_PIN flag disabled by default...")
    
    # Save original value
    original_value = os.environ.get('DEBUG_VM_PIN')
    
    try:
        # Ensure DEBUG_VM_PIN is not set
        if 'DEBUG_VM_PIN' in os.environ:
            del os.environ['DEBUG_VM_PIN']
        
        # Reload the module to pick up the environment change
        voicemail = reload_voicemail_module()
        
        # Check that the flag is False
        assert voicemail._DEBUG_PIN_LOGGING_ENABLED is False, \
            "DEBUG_PIN_LOGGING should be False when DEBUG_VM_PIN is not set"
        
        config = Config('config.yml')
        vm_system = voicemail.VoicemailSystem(storage_path='test_voicemail', config=config)
        ivr = voicemail.VoicemailIVR(vm_system, '1001')
        
        # Verify the IVR instance has debug_pin_logging disabled
        assert ivr.debug_pin_logging is False, \
            "VoicemailIVR.debug_pin_logging should be False by default"
        
        print("✓ DEBUG_VM_PIN flag is disabled by default")
    
    finally:
        restore_debug_vm_pin_env(original_value)


def test_debug_pin_flag_enabled_when_set():
    """Test that DEBUG_VM_PIN flag is enabled when environment variable is set"""
    print("Testing DEBUG_VM_PIN flag enabled when set...")
    
    # Save original value
    original_value = os.environ.get('DEBUG_VM_PIN')
    
    try:
        # Test various truthy values
        for truthy_value in ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES']:
            os.environ['DEBUG_VM_PIN'] = truthy_value
            
            # Reload the module to pick up the environment change
            voicemail = reload_voicemail_module()
            
            # Check that the flag is True
            assert voicemail._DEBUG_PIN_LOGGING_ENABLED is True, \
                f"DEBUG_PIN_LOGGING should be True when DEBUG_VM_PIN='{truthy_value}'"
            
            config = Config('config.yml')
            vm_system = voicemail.VoicemailSystem(storage_path='test_voicemail', config=config)
            ivr = voicemail.VoicemailIVR(vm_system, '1001')
            
            # Verify the IVR instance has debug_pin_logging enabled
            assert ivr.debug_pin_logging is True, \
                f"VoicemailIVR.debug_pin_logging should be True when DEBUG_VM_PIN='{truthy_value}'"
        
        # Test falsy values
        for falsy_value in ['false', 'False', 'FALSE', '0', 'no', 'No', 'NO', '']:
            os.environ['DEBUG_VM_PIN'] = falsy_value
            
            # Reload the module to pick up the environment change
            voicemail = reload_voicemail_module()
            
            # Check that the flag is False
            assert voicemail._DEBUG_PIN_LOGGING_ENABLED is False, \
                f"DEBUG_PIN_LOGGING should be False when DEBUG_VM_PIN='{falsy_value}'"
        
        print("✓ DEBUG_VM_PIN flag enabled/disabled correctly based on environment variable")
    
    finally:
        restore_debug_vm_pin_env(original_value)


def test_debug_pin_logging_suppressed_when_disabled():
    """Test that debug PIN logging is suppressed when DEBUG_VM_PIN is disabled"""
    print("Testing debug PIN logging suppressed when disabled...")
    
    # Save original value
    original_value = os.environ.get('DEBUG_VM_PIN')
    
    try:
        # Ensure DEBUG_VM_PIN is disabled
        os.environ['DEBUG_VM_PIN'] = 'false'
        
        # Reload the module to pick up the environment change
        voicemail = reload_voicemail_module()
        
        config = Config('config.yml')
        vm_system = voicemail.VoicemailSystem(storage_path='test_voicemail', config=config)
        
        # Get mailbox and set PIN
        mailbox = vm_system.get_mailbox('1001')
        mailbox.set_pin('1234')
        
        ivr = voicemail.VoicemailIVR(vm_system, '1001')
        ivr.state = voicemail.VoicemailIVR.STATE_PIN_ENTRY
        
        # Capture log output by checking the logger
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        ivr.logger.addHandler(handler)
        
        # Enter PIN digits
        ivr.handle_dtmf('1')
        ivr.handle_dtmf('2')
        ivr.handle_dtmf('3')
        ivr.handle_dtmf('4')
        ivr.handle_dtmf('#')
        
        # Get log output
        log_output = log_capture.getvalue()
        
        # Remove handler
        ivr.logger.removeHandler(handler)
        
        # Verify that sensitive PIN debug messages are NOT in the log
        assert 'PIN DEBUG' not in log_output, \
            "PIN DEBUG messages should not appear when DEBUG_VM_PIN is disabled"
        assert "TESTING ONLY - Digit" not in log_output, \
            "Debug digit collection should not appear when DEBUG_VM_PIN is disabled"
        assert "TESTING ONLY - Entered PIN:" not in log_output, \
            "Entered PIN should not be logged when DEBUG_VM_PIN is disabled"
        
        # But regular PIN verification messages should still be there
        assert 'PIN verification result' in log_output, \
            "Regular PIN verification logging should still work"
        
        print("✓ Debug PIN logging is suppressed when DEBUG_VM_PIN is disabled")
    
    finally:
        restore_debug_vm_pin_env(original_value)


def test_debug_pin_logging_emitted_when_enabled():
    """Test that debug PIN logging is emitted when DEBUG_VM_PIN is enabled"""
    print("Testing debug PIN logging emitted when enabled...")
    
    # Save original value
    original_value = os.environ.get('DEBUG_VM_PIN')
    
    try:
        # Enable DEBUG_VM_PIN
        os.environ['DEBUG_VM_PIN'] = 'true'
        
        # Reload the module to pick up the environment change
        voicemail = reload_voicemail_module()
        
        config = Config('config.yml')
        vm_system = voicemail.VoicemailSystem(storage_path='test_voicemail', config=config)
        
        # Get mailbox and set PIN
        mailbox = vm_system.get_mailbox('1001')
        mailbox.set_pin('1234')
        
        # Capture log output - we need to set up handler BEFORE creating IVR
        # to capture initialization warnings
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)  # Capture all log levels
        
        # We need to get the VM_IVR logger to capture init warnings
        temp_logger = logging.getLogger('PBX.VM_IVR')
        temp_logger.addHandler(handler)
        
        ivr = voicemail.VoicemailIVR(vm_system, '1001')
        ivr.state = voicemail.VoicemailIVR.STATE_PIN_ENTRY
        
        # Enter PIN digits
        ivr.handle_dtmf('1')
        ivr.handle_dtmf('2')
        ivr.handle_dtmf('3')
        ivr.handle_dtmf('4')
        ivr.handle_dtmf('#')
        
        # Get log output
        log_output = log_capture.getvalue()
        
        # Remove handler
        temp_logger.removeHandler(handler)
        
        # Verify that sensitive PIN debug messages ARE in the log
        assert 'PIN DEBUG LOGGING ENABLED' in log_output, \
            "Initialization warning should appear when DEBUG_VM_PIN is enabled"
        assert 'PIN DEBUG' in log_output, \
            "PIN DEBUG messages should appear when DEBUG_VM_PIN is enabled"
        assert "TESTING ONLY - Digit '1' collected, current PIN buffer: '1'" in log_output, \
            "Debug digit collection should show first digit"
        assert "TESTING ONLY - Digit '4' collected, current PIN buffer: '1234'" in log_output, \
            "Debug digit collection should show complete PIN buffer"
        assert "TESTING ONLY - Entered PIN: '1234'" in log_output, \
            "Entered PIN should be logged when DEBUG_VM_PIN is enabled"
        assert "TESTING ONLY - Expected PIN: '1234'" in log_output, \
            "Expected PIN should be logged when DEBUG_VM_PIN is enabled"
        
        print("✓ Debug PIN logging is emitted when DEBUG_VM_PIN is enabled")
    
    finally:
        restore_debug_vm_pin_env(original_value)


def test_debug_pin_module_level_caching():
    """Test that the DEBUG_VM_PIN flag is cached at module level"""
    print("Testing DEBUG_VM_PIN module-level caching...")
    
    # Save original value
    original_value = os.environ.get('DEBUG_VM_PIN')
    
    try:
        # Set DEBUG_VM_PIN to true
        os.environ['DEBUG_VM_PIN'] = 'true'
        
        # Reload the module to pick up the environment change
        voicemail = reload_voicemail_module()
        
        # Verify it's enabled
        assert voicemail._DEBUG_PIN_LOGGING_ENABLED is True, \
            "DEBUG_PIN_LOGGING should be True initially"
        
        # Now change the environment variable (simulating runtime change)
        os.environ['DEBUG_VM_PIN'] = 'false'
        
        # The module-level flag should NOT change (it's cached)
        assert voicemail._DEBUG_PIN_LOGGING_ENABLED is True, \
            "Module-level DEBUG_PIN_LOGGING should remain True (cached, not re-read from env)"
        
        # Create a new IVR - it should still use the cached True value
        config = Config('config.yml')
        vm_system = voicemail.VoicemailSystem(storage_path='test_voicemail', config=config)
        ivr = voicemail.VoicemailIVR(vm_system, '1001')
        
        assert ivr.debug_pin_logging is True, \
            "New IVR should use cached module-level flag value"
        
        print("✓ DEBUG_VM_PIN flag is cached at module level")
    
    finally:
        restore_debug_vm_pin_env(original_value)


def test_voicemail_pin_from_database():
    """Test that voicemail PIN is loaded from database and verified correctly"""
    print("Testing voicemail PIN from database...")
    
    import tempfile
    from pbx.utils.database import DatabaseBackend, ExtensionDB
    
    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        # Create test config with SQLite
        config = Config('config.yml')
        config.config['database'] = {
            'type': 'sqlite',
            'path': temp_db.name
        }
        
        # Initialize database
        db = DatabaseBackend(config)
        assert db.connect() is True
        assert db.create_tables() is True
        
        # Add extension with voicemail PIN to database
        ext_db = ExtensionDB(db)
        ext_db.add(
            number='1537',
            name='Test User',
            password_hash='test_hash',
            email='test@example.com',
            voicemail_pin='4655'  # This will be hashed
        )
        
        # Create voicemail system with database
        vm_system = VoicemailSystem(
            storage_path='test_voicemail',
            config=config,
            database=db
        )
        
        # Get mailbox - should load PIN from database
        mailbox = vm_system.get_mailbox('1537')
        
        # Verify PIN hash and salt were loaded
        assert mailbox.pin_hash is not None, "PIN hash should be loaded from database"
        assert mailbox.pin_salt is not None, "PIN salt should be loaded from database"
        assert mailbox.pin is None, "Plaintext PIN should not be set when using database"
        
        # Verify correct PIN
        assert mailbox.verify_pin('4655') is True, "Correct PIN should verify successfully"
        
        # Verify incorrect PIN
        assert mailbox.verify_pin('0000') is False, "Incorrect PIN should fail verification"
        assert mailbox.verify_pin('') is False, "Empty PIN should fail verification"
        
        # Test with IVR
        ivr = VoicemailIVR(vm_system, '1537')
        ivr.state = VoicemailIVR.STATE_PIN_ENTRY
        
        # Enter correct PIN
        ivr.handle_dtmf('4')
        ivr.handle_dtmf('6')
        ivr.handle_dtmf('5')
        ivr.handle_dtmf('5')
        result = ivr.handle_dtmf('#')
        
        # Should accept PIN and transition to main menu
        assert result['action'] == 'play_prompt', f"Expected play_prompt, got {result['action']}"
        assert result['prompt'] == 'main_menu', f"Expected main_menu, got {result['prompt']}"
        assert ivr.state == VoicemailIVR.STATE_MAIN_MENU
        
        db.disconnect()
        print("✓ Voicemail PIN from database works correctly")
        
    finally:
        # Cleanup
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


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
        test_voicemail_pin_from_database,  # New test for database PIN verification
        # DEBUG_VM_PIN tests
        test_debug_pin_flag_disabled_by_default,
        test_debug_pin_flag_enabled_when_set,
        test_debug_pin_logging_suppressed_when_disabled,
        test_debug_pin_logging_emitted_when_enabled,
        test_debug_pin_module_level_caching,
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
