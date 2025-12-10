"""
Audio utilities for PBX system
Provides audio generation and processing functions
"""
import struct
import math
import warnings
import os


# Audio generation constants
MAX_16BIT_SIGNED = 32767  # Maximum value for 16-bit signed integer
DEFAULT_AMPLITUDE = 0.5  # Default amplitude (50% of maximum)


def pcm16_to_ulaw(pcm_data):
    """
    Convert 16-bit PCM audio data to G.711 μ-law format
    
    Args:
        pcm_data: Raw 16-bit PCM audio data (little-endian signed)
    
    Returns:
        bytes: G.711 μ-law encoded audio data (8-bit per sample)
    
    Note:
        This function uses Python's audioop module which is deprecated in Python 3.11+
        and will be removed in Python 3.13. For production use, consider using an
        alternative library like 'pydub' or implementing the conversion algorithm directly.
    """
    try:
        import audioop
        # Suppress deprecation warning for audioop
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            # Convert 16-bit linear PCM to μ-law (1 = mono, 2 bytes per sample for 16-bit)
            ulaw_data = audioop.lin2ulaw(pcm_data, 2)
        return ulaw_data
    except ImportError:
        # Fallback: implement μ-law encoding manually if audioop is not available
        # This is a simplified implementation of μ-law encoding
        ulaw_data = bytearray()
        
        # μ-law constants
        BIAS = 0x84
        CLIP = 32635
        
        for i in range(0, len(pcm_data), 2):
            # Read 16-bit little-endian sample
            if i + 1 >= len(pcm_data):
                break
            sample = struct.unpack('<h', pcm_data[i:i+2])[0]
            
            # Get sign and magnitude
            sign = 0x80 if sample < 0 else 0x00
            sample = abs(sample)
            
            # Clip the sample
            if sample > CLIP:
                sample = CLIP
            
            # Add bias
            sample = sample + BIAS
            
            # Find exponent (position of highest set bit in range)
            # Start from highest exponent and work down
            exponent = 0
            for exp in range(7, -1, -1):
                if sample & (1 << (exp + 3)):
                    exponent = exp
                    break
            
            mantissa = (sample >> (exponent + 3)) & 0x0F
            
            # Compose μ-law byte
            ulaw_byte = ~(sign | (exponent << 4) | mantissa) & 0xFF
            ulaw_data.append(ulaw_byte)
        
        return bytes(ulaw_data)


def pcm16_to_g722(pcm_data, sample_rate=8000):
    """
    Convert 16-bit PCM audio data to G.722 format
    
    G.722 is a wideband codec that operates at 16kHz. If the input is at 8kHz,
    it will be upsampled to 16kHz before encoding.
    
    Args:
        pcm_data: Raw 16-bit PCM audio data (little-endian signed)
        sample_rate: Sample rate of input PCM data (8000 or 16000 Hz)
    
    Returns:
        bytes: G.722 encoded audio data
    
    Note:
        This uses the G722Codec class which currently has a stub implementation.
        For production use with actual G.722 encoding, integrate a native G.722 library.
    """
    # Import G.722 codec
    from pbx.features.g722_codec import G722Codec
    
    # Upsample from 8kHz to 16kHz if needed
    if sample_rate == 8000:
        # Simple linear interpolation upsampling (2x)
        # For each sample, insert an interpolated sample between current and next
        upsampled = bytearray()
        num_samples = len(pcm_data) // 2
        
        for i in range(num_samples - 1):
            # Read current and next sample
            current = struct.unpack('<h', pcm_data[i*2:(i+1)*2])[0]
            next_sample = struct.unpack('<h', pcm_data[(i+1)*2:(i+2)*2])[0]
            
            # Add current sample
            upsampled.extend(struct.pack('<h', current))
            
            # Add interpolated sample (average of current and next)
            interpolated = (current + next_sample) // 2
            upsampled.extend(struct.pack('<h', interpolated))
        
        # Add the last sample
        if num_samples > 0:
            last_sample = struct.unpack('<h', pcm_data[(num_samples-1)*2:num_samples*2])[0]
            upsampled.extend(struct.pack('<h', last_sample))
            upsampled.extend(struct.pack('<h', last_sample))  # Duplicate last sample
        
        pcm_data = bytes(upsampled)
    
    # Create G.722 encoder
    codec = G722Codec(bitrate=64000)
    
    # Encode PCM to G.722
    g722_data = codec.encode(pcm_data)
    
    return g722_data if g722_data is not None else b''


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
        value = int(MAX_16BIT_SIGNED * DEFAULT_AMPLITUDE * math.sin(2 * math.pi * frequency * t))
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


def generate_voice_prompt(prompt_type, sample_rate=8000):
    """
    Generate a voice-like prompt using tone sequences
    
    Since we don't have TTS, we use distinctive tone patterns to represent different prompts.
    These tones are designed to be recognizable and indicate specific messages.
    
    Args:
        prompt_type: Type of prompt to generate:
            - 'leave_message': "Please leave a message after the tone"
            - 'enter_pin': "Please enter your PIN"
            - 'main_menu': "Main menu. Press 1 to listen to messages..."
            - 'message_menu': "Press 1 to replay, 2 for next, 3 to delete..."
            - 'no_messages': "You have no messages"
            - 'goodbye': "Goodbye"
        sample_rate: Sample rate in Hz
    
    Returns:
        bytes: Complete WAV file with prompt tones
    
    Note: In production, these would be replaced with actual recorded voice prompts
    """
    # Define tone sequences for different prompts
    # Format: [(frequency_hz, duration_ms), ...]
    tone_sequences = {
        'leave_message': [
            # Ascending tones to indicate "please leave a message"
            (600, 200), (700, 200), (800, 200), (900, 300),
        ],
        'enter_pin': [
            # Short repeating tone for PIN entry
            (1000, 150), (0, 100), (1000, 150), (0, 100), (1000, 150),
        ],
        'main_menu': [
            # Two-tone pattern for menu
            (800, 200), (600, 200), (800, 200),
        ],
        'message_menu': [
            # Quick triple beep for options
            (900, 100), (0, 50), (900, 100), (0, 50), (900, 100),
        ],
        'no_messages': [
            # Descending tones for "no messages"
            (800, 200), (600, 200), (400, 300),
        ],
        'goodbye': [
            # Descending dual tone for goodbye
            (700, 250), (500, 300),
        ],
        'invalid_option': [
            # Low buzz for invalid option
            (300, 400),
        ],
        'you_have_messages': [
            # Cheerful ascending tones
            (600, 150), (750, 150), (900, 200),
        ],
        'auto_attendant_welcome': [
            # Welcoming ascending tones
            (500, 250), (650, 250), (800, 250), (950, 350),
        ],
        'auto_attendant_menu': [
            # Menu option tones - distinctive pattern
            (700, 200), (0, 100), (800, 200), (0, 100), (700, 200), (0, 100), (900, 300),
        ],
        'timeout': [
            # Warning tone for timeout
            (400, 300), (0, 150), (400, 300),
        ],
        'transferring': [
            # Success tone for transfer
            (800, 150), (1000, 150), (1200, 200),
        ],
        'invalid_pin': [
            # Error tone for invalid PIN
            (300, 400), (0, 100), (300, 400),
        ],
        'recording_greeting': [
            # Recording prompt tones
            (700, 200), (900, 200), (1100, 300),
        ],
        'greeting_saved': [
            # Success confirmation
            (1000, 200), (1200, 200), (1000, 200),
        ],
        'message_deleted': [
            # Deletion confirmation - descending
            (900, 150), (700, 150), (500, 200),
        ],
        'end_of_messages': [
            # End notification - neutral tone
            (600, 300), (500, 300),
        ],
    }
    
    sequence = tone_sequences.get(prompt_type, [(800, 300)])  # Default tone
    
    pcm_data = b''
    for frequency, duration_ms in sequence:
        if frequency == 0:
            # Silence
            num_samples = int(sample_rate * duration_ms / 1000)
            pcm_data += b'\x00\x00' * num_samples
        else:
            # Generate tone
            num_samples = int(sample_rate * duration_ms / 1000)
            for i in range(num_samples):
                t = i / sample_rate
                value = int(MAX_16BIT_SIGNED * DEFAULT_AMPLITUDE * math.sin(2 * math.pi * frequency * t))
                pcm_data += struct.pack('<h', value)
    
    header = build_wav_header(len(pcm_data), sample_rate=sample_rate)
    return header + pcm_data


def load_prompt_file(prompt_type, prompt_dir='voicemail_prompts'):
    """
    Load a voice prompt WAV file from disk
    
    Args:
        prompt_type: Type of prompt (e.g., 'enter_pin', 'main_menu', 'goodbye')
        prompt_dir: Directory containing prompt files (default: 'voicemail_prompts')
    
    Returns:
        bytes: WAV file contents if file exists, None otherwise
    
    Note: This function attempts to load actual recorded voice prompts.
          If the file doesn't exist, the caller should fall back to generate_voice_prompt()
    """
    # Build path to prompt file
    prompt_file = os.path.join(prompt_dir, f"{prompt_type}.wav")
    
    # Check if file exists
    if os.path.exists(prompt_file):
        try:
            with open(prompt_file, 'rb') as f:
                return f.read()
        except (IOError, OSError) as e:
            # If we can't read the file (permission issues, disk errors, etc.),
            # return None so caller can use fallback tone generation
            # In production, consider logging this error for debugging
            import warnings
            warnings.warn(f"Failed to read prompt file {prompt_file}: {e}")
            return None
    
    return None


def get_prompt_audio(prompt_type, prompt_dir='voicemail_prompts', sample_rate=8000):
    """
    Get voice prompt audio, trying to load from file first, then generating tones as fallback
    
    This is a convenience function that combines load_prompt_file() and generate_voice_prompt().
    It first attempts to load a recorded WAV file, and if that fails, generates tone-based prompts.
    
    Args:
        prompt_type: Type of prompt (e.g., 'enter_pin', 'main_menu', 'goodbye')
        prompt_dir: Directory containing prompt files (default: 'voicemail_prompts')
        sample_rate: Sample rate for generated prompts if file not found
    
    Returns:
        bytes: Complete WAV file data (either from file or generated)
    """
    # Try to load from file first
    audio_data = load_prompt_file(prompt_type, prompt_dir)
    
    if audio_data is not None:
        return audio_data
    
    # Fallback to generated tone prompts
    return generate_voice_prompt(prompt_type, sample_rate)
