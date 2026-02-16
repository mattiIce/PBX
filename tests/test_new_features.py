#!/usr/bin/env python3
"""
Test newly implemented PBX features
"""

import struct
import tempfile
from pathlib import Path

from pbx.rtp.handler import RTPPlayer


def test_wav_file_playback() -> bool:
    """Test WAV file playback functionality"""

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

        # Note: This will log a warning about play_file not working because
        # we're not actually connected to anything, but it tests the parsing
        # The actual RTP sending will fail gracefully
        player.play_file(wav_file)

        # Stop player
        player.stop()

        # Clean up
        Path(wav_file).unlink(missing_ok=True)

        return True

    except OSError:
        import traceback

        traceback.print_exc()
        if Path(wav_file).exists():
            Path(wav_file).unlink(missing_ok=True)
        return False


def test_call_transfer_message_building() -> bool:
    """Test that call transfer REFER messages can be built"""

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

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False
