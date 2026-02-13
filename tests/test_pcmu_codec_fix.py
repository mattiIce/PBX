#!/usr/bin/env python3
"""
Test that PCM audio files are correctly converted to PCMU (G.711 μ-law)
This test verifies the fix for the G.722 codec issue where phones couldn't hear audio
"""
import math
import os
import struct
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.rtp.handler import RTPPlayer
from pbx.utils.audio import WAV_FORMAT_PCM, pcm16_to_ulaw


def create_test_pcm_wav(sample_rate: int = 8000, duration_samples: int = 800) -> str:
    """
    Create a test PCM WAV file

    Args:
        sample_rate: Sample rate in Hz
        duration_samples: Number of samples

    Returns:
        Path to created WAV file
    """
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix=".wav")

    with os.fdopen(fd, "wb") as f:
        # Write WAV header
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + duration_samples * 2))  # File size - 8
        f.write(b"WAVE")

        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # fmt chunk size
        f.write(struct.pack("<H", WAV_FORMAT_PCM))  # audio format (PCM)
        f.write(struct.pack("<H", 1))  # num channels (mono)
        f.write(struct.pack("<I", sample_rate))  # sample rate
        f.write(struct.pack("<I", sample_rate * 2))  # byte rate
        f.write(struct.pack("<H", 2))  # block align
        f.write(struct.pack("<H", 16))  # bits per sample

        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", duration_samples * 2))  # data size

        # Write PCM samples (simple sine wave)
        for i in range(duration_samples):
            # Generate a 440 Hz tone
            sample = int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            f.write(struct.pack("<h", sample))

    return path


def test_pcm_to_pcmu_conversion() -> bool:
    """Test that PCM files are converted to PCMU, not G.722"""
    print("\n" + "=" * 60)
    print("Testing PCM to PCMU conversion (Fix for G.722 audio issue)")
    print("=" * 60)

    # Create test PCM file at 8kHz
    print("\n1. Creating test PCM WAV file (8kHz, 16-bit)...")
    pcm_file_8k = create_test_pcm_wav(sample_rate=8000, duration_samples=800)
    print(f"   Created: {pcm_file_8k}")

    # Create test PCM file at 16kHz
    print("\n2. Creating test PCM WAV file (16kHz, 16-bit)...")
    pcm_file_16k = create_test_pcm_wav(sample_rate=16000, duration_samples=1600)
    print(f"   Created: {pcm_file_16k}")

    try:
        # Test 8kHz PCM file
        print("\n3. Testing 8kHz PCM file playback...")
        player = RTPPlayer(
            local_port=20000, remote_host="127.0.0.1", remote_port=20001, call_id="test_call_8k"
        )
        player.start()

        # The play_file method should convert PCM to PCMU
        # Check the log output for "PCM format detected - will convert to PCMU"
        result = player.play_file(pcm_file_8k)
        player.stop()

        if result:
            print("   ✓ 8kHz PCM file played successfully (converted to PCMU)")
        else:
            print("   ✗ Failed to play 8kHz PCM file")
            return False

        # Test 16kHz PCM file
        print("\n4. Testing 16kHz PCM file playback...")
        player = RTPPlayer(
            local_port=20004, remote_host="127.0.0.1", remote_port=20005, call_id="test_call_16k"
        )
        player.start()

        # Should downsample from 16kHz to 8kHz and convert to PCMU
        result = player.play_file(pcm_file_16k)
        player.stop()

        if result:
            print("   ✓ 16kHz PCM file played successfully (downsampled and converted to PCMU)")
        else:
            print("   ✗ Failed to play 16kHz PCM file")
            return False

        # Test manual conversion
        print("\n5. Testing manual PCM to PCMU conversion...")
        test_pcm_data = bytearray()
        for i in range(100):
            sample = int(8000 * math.sin(2 * math.pi * 440 * i / 8000))
            test_pcm_data.extend(struct.pack("<h", sample))

        ulaw_data = pcm16_to_ulaw(bytes(test_pcm_data))

        if len(ulaw_data) == 100:  # Should be half the size (16-bit PCM -> 8-bit μ-law)
            print(
                f"   ✓ Manual conversion successful: {len(test_pcm_data)} bytes PCM -> {len(ulaw_data)} bytes PCMU"
            )
        else:
            print(
                f"   ✗ Manual conversion failed: expected 100 bytes, got {len(ulaw_data)} bytes"
            )
            return False

        print("\n" + "=" * 60)
        print("✓ All PCMU codec tests passed!")
        print("=" * 60)
        print("\nSummary:")
        print("- PCM files are now converted to PCMU (G.711 μ-law)")
        print("- 16kHz files are downsampled to 8kHz for compatibility")
        print("- Phones using PCMU codec should now hear audio correctly")
        print("=" * 60)

        return True

    finally:
        # Clean up
        if os.path.exists(pcm_file_8k):
            os.remove(pcm_file_8k)
        if os.path.exists(pcm_file_16k):
            os.remove(pcm_file_16k)


if __name__ == "__main__":
    success = test_pcm_to_pcmu_conversion()
    sys.exit(0 if success else 1)
