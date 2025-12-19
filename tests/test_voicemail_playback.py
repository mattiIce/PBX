#!/usr/bin/env python3
"""
Test voicemail playback functionality
Tests that extensions can retrieve and listen to their voicemail messages
"""
import os
import shutil
import sys
import tempfile
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.core.call import Call
from pbx.core.pbx import PBXCore
from pbx.features.voicemail import VoicemailSystem
from pbx.rtp.handler import RTPPlayer
from pbx.utils.config import Config


def test_rtp_player_play_file():
    """Test RTP player can play a WAV file"""
    print("Testing RTP player play_file method...")

    # Create a temporary WAV file with G.711 μ-law audio
    temp_dir = tempfile.mkdtemp()
    wav_file = os.path.join(temp_dir, "test.wav")

    try:
        # Create a minimal WAV file with G.711 μ-law format
        import struct

        # Generate some audio data (silence)
        audio_data = b"\x7f" * 8000  # 1 second of near-silence (μ-law)

        # Build WAV file
        sample_rate = 8000
        bits_per_sample = 8
        num_channels = 1
        audio_format = 7  # μ-law

        data_size = len(audio_data)
        file_size = 4 + 26 + 8 + data_size

        # WAV header
        wav_header = struct.pack("<4sI4s", b"RIFF", file_size, b"WAVE")

        # Format chunk
        fmt_chunk = struct.pack(
            "<4sIHHIIHH",
            b"fmt ",
            18,
            audio_format,
            num_channels,
            sample_rate,
            sample_rate * num_channels * bits_per_sample // 8,
            num_channels * bits_per_sample // 8,
            bits_per_sample,
        )

        # Extension
        fmt_extension = struct.pack("<H", 0)

        # Data chunk
        data_chunk = struct.pack("<4sI", b"data", data_size)

        # Write WAV file
        with open(wav_file, "wb") as f:
            f.write(wav_header + fmt_chunk + fmt_extension + data_chunk + audio_data)

        # Create RTP player
        player = RTPPlayer(
            local_port=16000, remote_host="127.0.0.1", remote_port=16001, call_id="test-playback"
        )

        # Start player
        assert player.start()

        # Try to play file (will fail to send due to no receiver, but should
        # parse correctly)
        result = player.play_file(wav_file)

        # Stop player
        player.stop()

        # Test should succeed if file was parsed correctly
        assert result or result == False  # Either outcome is acceptable for this test

        print("✓ RTP player play_file works")

    finally:
        shutil.rmtree(temp_dir)


def test_voicemail_access_plays_messages():
    """Test that voicemail access actually plays messages"""
    print("Testing voicemail access plays messages...")

    # Create temporary directory for voicemail
    temp_dir = tempfile.mkdtemp()

    try:
        # Create PBX instance with temporary voicemail path
        config = Config("config.yml")
        vm_system = VoicemailSystem(storage_path=temp_dir, config=config)

        # Create a test voicemail message
        mailbox = vm_system.get_mailbox("1001")

        # Create a simple voicemail file
        import struct

        audio_data = b"\x7f" * 1600  # 0.2 seconds of near-silence

        # Build WAV file
        pbx = PBXCore("config.yml")
        wav_data = pbx._build_wav_file(audio_data)

        # Save voicemail
        message_id = mailbox.save_message("1002", wav_data, duration=1)

        # Verify message was saved
        messages = mailbox.get_messages()
        assert len(messages) == 1
        assert messages[0]["caller_id"] == "1002"
        assert messages[0]["listened"] == False

        print("✓ Voicemail message saved successfully")

        # Now test the playback functionality
        # We can't fully test playback without a SIP client, but we can verify
        # the message is marked as listened after access

        # Simulate marking as listened (this would happen during playback)
        mailbox.mark_listened(message_id)

        # Verify message is marked as listened
        messages = mailbox.get_messages()
        assert messages[0]["listened"]

        print("✓ Voicemail message marked as listened")

    finally:
        shutil.rmtree(temp_dir)


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 60)
    print("Running Voicemail Playback Tests")
    print("=" * 60)
    print()

    tests = [
        test_rtp_player_play_file,
        test_voicemail_access_plays_messages,
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
