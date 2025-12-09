"""
Text-to-Speech utilities for PBX voice prompt generation
Uses gTTS (Google Text-to-Speech) for natural American English voices
"""
import os
import tempfile
from pbx.utils.logger import get_logger

# Try to import TTS dependencies
try:
    from gtts import gTTS
    from pydub import AudioSegment
    GTTS_AVAILABLE = True
except ImportError as e:
    GTTS_AVAILABLE = False
    GTTS_IMPORT_ERROR = str(e)

logger = get_logger()


def is_tts_available():
    """Check if TTS dependencies are available"""
    return GTTS_AVAILABLE


def get_tts_requirements():
    """Get installation instructions for TTS dependencies"""
    return "pip install gTTS pydub"


def text_to_wav_telephony(text, output_file, language='en', tld='com', slow=False):
    """
    Convert text to WAV file in telephony format (8000 Hz, 16-bit, mono)
    using gTTS (Google Text-to-Speech)
    
    Args:
        text: Text to convert to speech
        output_file: Output WAV file path
        language: Language code (default 'en' for English)
        tld: Top-level domain (default 'com' for US English accent)
        slow: Whether to use slow speech rate (default False for natural speed)
    
    Returns:
        bool: True if successful
        
    Raises:
        ImportError: If gTTS or pydub are not installed
        Exception: For other TTS generation errors
    """
    if not GTTS_AVAILABLE:
        raise ImportError(
            f"TTS dependencies not available: {GTTS_IMPORT_ERROR}\n"
            f"Install with: {get_tts_requirements()}"
        )
    
    try:
        # Create TTS with optimal settings for American English
        # tld='com' uses google.com which provides US English accent
        # lang='en' specifies English language
        # slow=False provides natural speaking speed for professional sound
        tts = gTTS(text=text, tld=tld, lang=language, slow=slow)
        
        # Save to temporary MP3 file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3:
            temp_mp3_path = temp_mp3.name
            tts.save(temp_mp3_path)
        
        # Convert to telephony format WAV (8000 Hz, mono, 16-bit)
        audio = AudioSegment.from_mp3(temp_mp3_path)
        audio = audio.set_channels(1)  # Mono
        audio = audio.set_frame_rate(8000)  # 8000 Hz
        audio = audio.set_sample_width(2)  # 16-bit
        
        # Export as WAV
        audio.export(output_file, format='wav')
        
        # Clean up temp file
        os.unlink(temp_mp3_path)
        
        return True
    except Exception as e:
        logger.error(f"Error generating TTS for '{text}': {e}")
        raise


def generate_prompts(prompts, output_dir, company_name=None):
    """
    Generate multiple voice prompts from text
    
    Args:
        prompts: Dict of {filename: text} to generate
        output_dir: Directory to save audio files
        company_name: Optional company name to substitute in text
        
    Returns:
        tuple: (success_count, total_count)
    """
    if not GTTS_AVAILABLE:
        raise ImportError(
            f"TTS dependencies not available: {GTTS_IMPORT_ERROR}\n"
            f"Install with: {get_tts_requirements()}"
        )
    
    # Create output directory if needed
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory: {output_dir}")
    
    success_count = 0
    total_count = len(prompts)
    
    for filename, text in prompts.items():
        # Substitute company name if present
        if company_name and '{company_name}' in text:
            text = text.replace('{company_name}', company_name)
        
        output_file = os.path.join(output_dir, filename if filename.endswith('.wav') else f'{filename}.wav')
        
        try:
            if text_to_wav_telephony(text, output_file):
                file_size = os.path.getsize(output_file)
                logger.info(f"Generated {filename}: {file_size:,} bytes")
                success_count += 1
        except Exception as e:
            logger.error(f"Failed to generate {filename}: {e}")
    
    return success_count, total_count
