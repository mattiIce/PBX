"""
Test PCM to G.722 conversion functionality
"""
import os
import struct
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_pcm16_to_g722_conversion():
    """Test PCM 16-bit to G.722 conversion"""
    from pbx.utils.audio import pcm16_to_g722

    # Create a simple test PCM signal (16-bit little-endian signed)
    # Let's create a few samples with known values
    test_samples = [0, 1000, -1000, 8000, -8000, 16000, -16000, 32767, -32768]
    pcm_data = b''
    for sample in test_samples:
        pcm_data += struct.pack('<h', sample)

    # Convert to G.722 at 8kHz (will be upsampled to 16kHz)
    g722_data = pcm16_to_g722(pcm_data, sample_rate=8000)

    # Verify output characteristics
    assert isinstance(g722_data, bytes), "G.722 data should be bytes"
    assert len(g722_data) > 0, "G.722 data should not be empty"

    # G.722 compresses approximately 2:1 (but after upsampling 8kHz->16kHz)
    # After upsampling, PCM data doubles, then G.722 compresses by ~2x
    # So final size should be similar to original

    print(f"✓ Successfully converted {len(test_samples)} PCM samples to G.722")
    print(f"  PCM data size: {len(pcm_data)} bytes")
    print(f"  G.722 data size: {len(g722_data)} bytes")
    print(f"  Compression ratio: {len(pcm_data) / len(g722_data):.1f}x")


def test_pcm_wav_to_g722_with_rtp():
    """Test playing a PCM WAV file via RTP (with conversion to G.722)"""
    from pbx.rtp.handler import RTPPlayer
    from pbx.utils.audio import build_wav_header, generate_beep_tone

    # Create a temporary PCM WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name

        # Generate test audio (16-bit PCM)
        pcm_data = generate_beep_tone(
            frequency=1000, duration_ms=100, sample_rate=8000)

        # Build WAV header for PCM format (audio_format=1)
        header = build_wav_header(
            len(pcm_data),
            sample_rate=8000,
            channels=1,
            bits_per_sample=16)

        # Write complete WAV file
        temp_file.write(header + pcm_data)

    try:
        # Create RTP player (won't actually send anywhere since remote_host is
        # None)
        player = RTPPlayer(
            local_port=20000,
            remote_host='127.0.0.1',
            remote_port=20002,
            call_id='test_pcm_conversion'
        )

        # Start the player
        started = player.start()
        assert started, "RTP player should start successfully"

        # Attempt to play the PCM WAV file
        # This should automatically convert PCM to G.722
        result = player.play_file(temp_path)

        # Stop the player
        player.stop()

        # The conversion should succeed
        assert result is True, "Playing PCM WAV file should succeed after conversion to G.722"

        print(f"✓ Successfully played PCM WAV file with automatic conversion to G.722")

    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_ulaw_wav_still_works():
    """Test that μ-law WAV files still work correctly (no conversion needed)"""
    import struct

    from pbx.rtp.handler import RTPPlayer

    # Create a temporary μ-law WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name

        # Create some dummy μ-law audio data
        # 400 bytes of μ-law data
        ulaw_data = bytes([0xFF, 0xFE, 0xFD, 0xFC] * 100)

        # Build WAV header for μ-law format (audio_format=7)
        header = b'RIFF'
        header += struct.pack('<I', 36 + len(ulaw_data))  # File size - 8
        header += b'WAVE'
        header += b'fmt '
        # Subchunk1Size (18 for non-PCM formats)
        header += struct.pack('<I', 18)
        header += struct.pack('<H', 7)  # AudioFormat (7 for μ-law)
        header += struct.pack('<H', 1)  # NumChannels (mono)
        header += struct.pack('<I', 8000)  # SampleRate
        # ByteRate (sample_rate * channels * bytes_per_sample)
        header += struct.pack('<I', 8000)
        # BlockAlign (channels * bytes_per_sample)
        header += struct.pack('<H', 1)
        header += struct.pack('<H', 8)  # BitsPerSample (8 for μ-law)
        header += struct.pack('<H', 0)  # ExtraParamSize (0 for μ-law)
        header += b'data'
        header += struct.pack('<I', len(ulaw_data))  # Data chunk size

        # Write complete WAV file
        temp_file.write(header + ulaw_data)

    try:
        # Create RTP player
        player = RTPPlayer(
            local_port=20004,
            remote_host='127.0.0.1',
            remote_port=20006,
            call_id='test_ulaw_playback'
        )

        # Start the player
        started = player.start()
        assert started, "RTP player should start successfully"

        # Play the μ-law WAV file (should not require conversion)
        result = player.play_file(temp_path)

        # Stop the player
        player.stop()

        # Should succeed without conversion
        assert result is True, "Playing μ-law WAV file should succeed without conversion"

        print(f"✓ Successfully played μ-law WAV file (no conversion needed)")

    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def run_all_tests():
    """Run all tests in this module"""
    print("Testing PCM to G.722 conversion...")
    print("-" * 60)
    test_pcm16_to_g722_conversion()
    print()
    test_pcm_wav_to_g722_with_rtp()
    print()
    test_ulaw_wav_still_works()
    print("-" * 60)
    print("All tests passed! ✓")
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
