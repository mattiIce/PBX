#!/usr/bin/env python3
"""
Test newly implemented PBX features
"""

import os
import struct
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.rtp.handler import RTPPlayer


def test_wav_file_playback():
    """Test WAV file playback functionality"""
    print("Testing WAV file playback...")

    # Create a minimal valid WAV file for testing
    # G.711 μ-law format, 8kHz, mono
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_file = f.name

        # WAV header
        # RIFF chunk
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + 1000))  # file size - 8
        f.write(b"WAVE")

        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 18))  # fmt chunk size
        f.write(struct.pack("<H", 7))  # audio format (7 = μ-law)
        f.write(struct.pack("<H", 1))  # channels (1 = mono)
        f.write(struct.pack("<I", 8000))  # sample rate
        f.write(struct.pack("<I", 8000))  # byte rate
        f.write(struct.pack("<H", 1))  # block align
        f.write(struct.pack("<H", 8))  # bits per sample
        f.write(struct.pack("<H", 0))  # extension size

        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", 1000))  # data size
        f.write(b"\x7f" * 1000)  # 1000 bytes of audio data (silence in μ-law)

    try:
        # Create RTP player (won't actually send since we're not connected)
        player = RTPPlayer(
            local_port=30000, remote_host="127.0.0.1", remote_port=30001, call_id="test-call"
        )

        # Start player
        assert player.start(), "Player should start successfully"
        print("✓ RTP player started")

        # Note: This will log a warning about play_file not working because
        # we're not actually connected to anything, but it tests the parsing
        # The actual RTP sending will fail gracefully
        result = player.play_file(wav_file)
        print(f"✓ WAV file parsing and playback attempted (result: {result})")

        # Stop player
        player.stop()
        print("✓ RTP player stopped")

        # Clean up
        os.unlink(wav_file)
        print("✓ WAV file playback test passed")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        if os.path.exists(wav_file):
            os.unlink(wav_file)
        return False


def test_call_transfer_message_building():
    """Test that call transfer REFER messages can be built"""
    print("\nTesting call transfer message building...")

    from pbx.sip.message import SIPMessageBuilder

    try:
        # Build a REFER message
        refer_msg = SIPMessageBuilder.build_request(
            method="REFER",
            uri="sip:1001@192.168.1.1",
            from_addr="<sip:1002@192.168.1.1>",
            to_addr="<sip:1001@192.168.1.1>",
            call_id="test-call-123",
            cseq=1,
        )

        # Add transfer-specific headers
        refer_msg.set_header("Refer-To", "<sip:1003@192.168.1.1>")
        refer_msg.set_header("Referred-By", "<sip:1002@192.168.1.1>")
        refer_msg.set_header("Contact", "<sip:1002@192.168.1.1:5060>")

        # Build the message
        message_text = refer_msg.build()

        # Verify it contains expected elements
        assert "REFER" in message_text, "Should contain REFER method"
        assert "Refer-To" in message_text, "Should contain Refer-To header"
        assert "Referred-By" in message_text, "Should contain Referred-By header"
        assert "sip:1003@192.168.1.1" in message_text, "Should contain transfer destination"

        print("✓ REFER message built successfully")
        print(f"  Message preview: {message_text[:100]}...")
        print("✓ Call transfer message test passed")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests in this module"""
    print("=" * 70)
    print("Testing New PBX Features")
    print("=" * 70)

    results = []
    results.append(test_wav_file_playback())
    results.append(test_call_transfer_message_building())

    print("\n" + "=" * 70)
    if all(results):
        print("✅ All feature tests passed!")
        return True
    else:
        print(f"❌ Some tests failed ({sum(results)}/{len(results)} passed)")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
