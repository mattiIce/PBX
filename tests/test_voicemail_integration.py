#!/usr/bin/env python3
"""
Integration test for voicemail recording and playback
Tests the complete voicemail flow: recording -> storage -> retrieval -> playback
"""
import os
import shutil
import sys
import tempfile
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pbx.core.call import Call, CallState
from pbx.core.pbx import PBXCore
from pbx.features.voicemail import VoicemailSystem
from pbx.utils.config import Config



def test_complete_voicemail_flow():
    """Test complete voicemail flow from recording to playback"""
    print("Testing complete voicemail flow...")

    # Create temporary directory for voicemail
    temp_dir = tempfile.mkdtemp()

    try:
        # Step 1: Setup PBX and voicemail system
        config = Config('config.yml')
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        pbx = PBXCore('config.yml')
        pbx.voicemail_system = vm_system

        print("  ✓ PBX and voicemail system initialized")

        # Step 2: Simulate recording a voicemail
        # Create test audio data
        import struct
        audio_data = b'\x7F' * 8000  # 1 second of near-silence (μ-law)
        wav_data = pbx._build_wav_file(audio_data)

        # Save voicemail for extension 1001
        message_id = vm_system.save_message(
            '1001', '1002', wav_data, duration=1)

        print("  ✓ Voicemail recorded and saved")

        # Step 3: Verify voicemail was saved
        mailbox = vm_system.get_mailbox('1001')
        messages = mailbox.get_messages(unread_only=False)

        assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
        assert messages[0]['caller_id'] == '1002'
        assert messages[0]['listened'] == False
        assert messages[0]['id'] == message_id

        print("  ✓ Voicemail stored correctly in mailbox")

        # Step 4: Verify voicemail file exists
        assert os.path.exists(messages[0]['file_path'])

        # Verify it's a valid WAV file
        with open(messages[0]['file_path'], 'rb') as f:
            wav_content = f.read()
        assert wav_content.startswith(b'RIFF')
        assert b'WAVE' in wav_content[:20]

        print("  ✓ Voicemail file is valid WAV format")

        # Step 5: Simulate voicemail access (playback)
        # In a real scenario, _handle_voicemail_access would be called
        # For this test, we'll verify the mailbox can be accessed
        unread_count = vm_system.get_message_count('1001', unread_only=True)
        total_count = vm_system.get_message_count('1001', unread_only=False)

        assert unread_count == 1, f"Expected 1 unread message, got {unread_count}"
        assert total_count == 1, f"Expected 1 total message, got {total_count}"

        print("  ✓ Voicemail counts are correct")

        # Step 6: Mark message as listened (simulating playback)
        mailbox.mark_listened(message_id)

        # Verify message is now marked as listened
        messages = mailbox.get_messages(unread_only=False)
        assert messages[0]['listened']

        unread_count = vm_system.get_message_count('1001', unread_only=True)
        assert unread_count == 0, f"Expected 0 unread messages, got {unread_count}"

        print("  ✓ Message marked as listened after playback")

        # Step 7: Test voicemail retrieval
        # Verify we can retrieve messages multiple times
        messages_again = mailbox.get_messages(unread_only=False)
        assert len(messages_again) == 1
        assert messages_again[0]['listened']

        print("  ✓ Voicemail can be retrieved multiple times")

        # Step 8: Test message deletion
        deleted = mailbox.delete_message(message_id)
        assert deleted

        messages_after_delete = mailbox.get_messages(unread_only=False)
        assert len(messages_after_delete) == 0

        print("  ✓ Voicemail deletion works")

        print("\n✓ Complete voicemail flow test passed!")

    finally:
        shutil.rmtree(temp_dir)


def test_multiple_voicemails():
    """Test handling multiple voicemail messages"""
    print("Testing multiple voicemail messages...")

    # Create temporary directory for voicemail
    temp_dir = tempfile.mkdtemp()

    try:
        config = Config('config.yml')
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)
        pbx = PBXCore('config.yml')
        pbx.voicemail_system = vm_system

        # Create multiple voicemail messages
        import struct
        audio_data = b'\x7F' * 8000  # 1 second
        wav_data = pbx._build_wav_file(audio_data)

        # Save 3 voicemails from different callers
        msg1 = vm_system.save_message('1001', '1002', wav_data, duration=1)
        time.sleep(0.1)  # Small delay to ensure different timestamps
        msg2 = vm_system.save_message('1001', '1003', wav_data, duration=1)
        time.sleep(0.1)
        msg3 = vm_system.save_message('1001', '1004', wav_data, duration=1)

        # Verify all messages were saved
        mailbox = vm_system.get_mailbox('1001')
        messages = mailbox.get_messages(unread_only=False)

        assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"

        # Verify all are unread
        unread = mailbox.get_messages(unread_only=True)
        assert len(unread) == 3

        print("  ✓ Multiple voicemails saved correctly")

        # Mark first message as listened
        mailbox.mark_listened(msg1)

        # Verify counts
        unread = mailbox.get_messages(unread_only=True)
        assert len(unread) == 2

        messages = mailbox.get_messages(unread_only=False)
        assert len(messages) == 3

        print("  ✓ Multiple voicemail tracking works correctly")

    finally:
        shutil.rmtree(temp_dir)


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Voicemail Integration Tests")
    print("=" * 60)
    print()

    tests = [
        test_complete_voicemail_flow,
        test_multiple_voicemails,
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
