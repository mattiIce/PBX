"""
Test PCM to G.711 μ-law conversion functionality
"""
import struct
import tempfile
import os


def test_pcm16_to_ulaw_conversion():
    """Test PCM 16-bit to μ-law conversion"""
    from pbx.utils.audio import pcm16_to_ulaw
    
    # Create a simple test PCM signal (16-bit little-endian signed)
    # Let's create a few samples with known values
    test_samples = [0, 1000, -1000, 8000, -8000, 16000, -16000, 32767, -32768]
    pcm_data = b''
    for sample in test_samples:
        pcm_data += struct.pack('<h', sample)
    
    # Convert to μ-law
    ulaw_data = pcm16_to_ulaw(pcm_data)
    
    # Verify output characteristics
    assert len(ulaw_data) == len(test_samples), "μ-law data should have one byte per sample"
    assert isinstance(ulaw_data, bytes), "μ-law data should be bytes"
    
    # μ-law values should be in valid range (0-255)
    for byte_val in ulaw_data:
        assert 0 <= byte_val <= 255, f"μ-law byte {byte_val} out of range"
    
    print(f"✓ Successfully converted {len(test_samples)} PCM samples to μ-law")
    print(f"  PCM data size: {len(pcm_data)} bytes")
    print(f"  μ-law data size: {len(ulaw_data)} bytes")
    print(f"  Compression ratio: {len(pcm_data) / len(ulaw_data):.1f}x")


def test_pcm_wav_to_ulaw_with_rtp():
    """Test playing a PCM WAV file via RTP (with conversion)"""
    from pbx.rtp.handler import RTPPlayer
    from pbx.utils.audio import build_wav_header, generate_beep_tone
    
    # Create a temporary PCM WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
        
        # Generate test audio (16-bit PCM)
        pcm_data = generate_beep_tone(frequency=1000, duration_ms=100, sample_rate=8000)
        
        # Build WAV header for PCM format (audio_format=1)
        header = build_wav_header(len(pcm_data), sample_rate=8000, channels=1, bits_per_sample=16)
        
        # Write complete WAV file
        temp_file.write(header + pcm_data)
    
    try:
        # Create RTP player (won't actually send anywhere since remote_host is None)
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
        # This should automatically convert PCM to μ-law
        result = player.play_file(temp_path)
        
        # Stop the player
        player.stop()
        
        # The conversion should succeed
        assert result is True, "Playing PCM WAV file should succeed after conversion to μ-law"
        
        print(f"✓ Successfully played PCM WAV file with automatic conversion to G.711 μ-law")
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_ulaw_wav_still_works():
    """Test that μ-law WAV files still work correctly (no conversion needed)"""
    from pbx.rtp.handler import RTPPlayer
    import struct
    
    # Create a temporary μ-law WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
        
        # Create some dummy μ-law audio data
        ulaw_data = bytes([0xFF, 0xFE, 0xFD, 0xFC] * 100)  # 400 bytes of μ-law data
        
        # Build WAV header for μ-law format (audio_format=7)
        header = b'RIFF'
        header += struct.pack('<I', 36 + len(ulaw_data))  # File size - 8
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<I', 18)  # Subchunk1Size (18 for non-PCM formats)
        header += struct.pack('<H', 7)  # AudioFormat (7 for μ-law)
        header += struct.pack('<H', 1)  # NumChannels (mono)
        header += struct.pack('<I', 8000)  # SampleRate
        header += struct.pack('<I', 8000)  # ByteRate (sample_rate * channels * bytes_per_sample)
        header += struct.pack('<H', 1)  # BlockAlign (channels * bytes_per_sample)
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


if __name__ == '__main__':
    print("Testing PCM to G.711 μ-law conversion...")
    print("-" * 60)
    test_pcm16_to_ulaw_conversion()
    print()
    test_pcm_wav_to_ulaw_with_rtp()
    print()
    test_ulaw_wav_still_works()
    print("-" * 60)
    print("All tests passed! ✓")
