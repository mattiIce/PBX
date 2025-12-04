"""
Audio utilities for PBX system
Provides audio generation and processing functions
"""
import struct
import math


def generate_beep_tone(frequency=1000, duration_ms=500, sample_rate=8000):
    """
    Generate a simple beep tone in raw PCM format
    
    Args:
        frequency: Frequency in Hz (default 1000 Hz)
        duration_ms: Duration in milliseconds (default 500ms)
        sample_rate: Sample rate in Hz (default 8000 Hz for telephony)
    
    Returns:
        bytes: Raw PCM audio data (16-bit signed, little-endian)
    """
    num_samples = int(sample_rate * duration_ms / 1000)
    samples = []
    
    for i in range(num_samples):
        # Generate sine wave
        t = i / sample_rate
        value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack('<h', value))  # 16-bit signed little-endian
    
    return b''.join(samples)


def build_wav_header(data_size, sample_rate=8000, channels=1, bits_per_sample=16):
    """
    Build a WAV file header
    
    Args:
        data_size: Size of PCM data in bytes
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        bits_per_sample: Bits per sample (8 or 16)
    
    Returns:
        bytes: WAV header
    """
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    
    header = b'RIFF'
    header += struct.pack('<I', 36 + data_size)  # File size - 8
    header += b'WAVE'
    header += b'fmt '
    header += struct.pack('<I', 16)  # Subchunk1Size (16 for PCM)
    header += struct.pack('<H', 1)  # AudioFormat (1 for PCM)
    header += struct.pack('<H', channels)
    header += struct.pack('<I', sample_rate)
    header += struct.pack('<I', byte_rate)
    header += struct.pack('<H', block_align)
    header += struct.pack('<H', bits_per_sample)
    header += b'data'
    header += struct.pack('<I', data_size)
    
    return header


def generate_voicemail_beep():
    """
    Generate a voicemail beep tone (single beep, 1000 Hz, 500ms)
    
    Returns:
        bytes: Complete WAV file with beep tone
    """
    pcm_data = generate_beep_tone(frequency=1000, duration_ms=500, sample_rate=8000)
    header = build_wav_header(len(pcm_data), sample_rate=8000)
    return header + pcm_data


def generate_ring_tone(rings=1):
    """
    Generate a ring tone (2 seconds ring, 4 seconds silence, repeated)
    
    Args:
        rings: Number of rings to generate
    
    Returns:
        bytes: Complete WAV file with ring tone
    """
    sample_rate = 8000
    ring_duration_ms = 2000  # 2 seconds ring
    silence_duration_ms = 4000  # 4 seconds silence
    
    # Generate ring sound (dual tone: 440 Hz + 480 Hz)
    ring_samples = int(sample_rate * ring_duration_ms / 1000)
    silence_samples = int(sample_rate * silence_duration_ms / 1000)
    
    pcm_data = b''
    
    for _ in range(rings):
        # Ring sound
        for i in range(ring_samples):
            t = i / sample_rate
            # Mix two frequencies
            value = int(32767 * 0.3 * (
                math.sin(2 * math.pi * 440 * t) + 
                math.sin(2 * math.pi * 480 * t)
            ))
            pcm_data += struct.pack('<h', value)
        
        # Silence
        pcm_data += b'\x00\x00' * silence_samples
    
    header = build_wav_header(len(pcm_data), sample_rate=sample_rate)
    return header + pcm_data


def generate_busy_tone():
    """
    Generate a busy tone (500 Hz, pulsed)
    
    Returns:
        bytes: Complete WAV file with busy tone
    """
    sample_rate = 8000
    tone_duration_ms = 500  # 500ms on
    silence_duration_ms = 500  # 500ms off
    repeats = 3
    
    pcm_data = b''
    
    for _ in range(repeats):
        # Tone
        tone_samples = int(sample_rate * tone_duration_ms / 1000)
        for i in range(tone_samples):
            t = i / sample_rate
            value = int(32767 * 0.5 * math.sin(2 * math.pi * 500 * t))
            pcm_data += struct.pack('<h', value)
        
        # Silence
        silence_samples = int(sample_rate * silence_duration_ms / 1000)
        pcm_data += b'\x00\x00' * silence_samples
    
    header = build_wav_header(len(pcm_data), sample_rate=sample_rate)
    return header + pcm_data
