"""
Text-to-Speech utilities for PBX voice prompt generation
Uses gTTS (Google Text-to-Speech) for natural American English voices
"""

import os
import subprocess
import tempfile

from pbx.utils.logger import get_logger
from pathlib import Path

# Try to import TTS dependencies
try:
    from gtts import gTTS
    from pydub import AudioSegment

    GTTS_AVAILABLE = True
    GTTS_IMPORT_ERROR = None
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


def _generate_mp3(text, language, tld, slow):
    """
    Generate MP3 file from text using gTTS

    Args:
        text: Text to convert
        language: Language code
        tld: Top-level domain for accent
        slow: Slow speech rate flag

    Returns:
        Path to temporary MP3 file
    """
    tts = gTTS(text=text, tld=tld, lang=language, slow=slow)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3:
        temp_mp3_path = temp_mp3.name
        tts.save(temp_mp3_path)
    return temp_mp3_path


def _convert_to_telephony_audio(mp3_path, sample_rate):
    """
    Convert MP3 to telephony format audio (16-bit, mono, specified sample rate)

    Args:
        mp3_path: Path to MP3 file
        sample_rate: Target sample rate in Hz

    Returns:
        AudioSegment in telephony format
    """
    audio = AudioSegment.from_mp3(mp3_path)
    audio = audio.set_channels(1)  # Mono
    audio = audio.set_frame_rate(sample_rate)
    audio = audio.set_sample_width(2)  # 16-bit
    return audio


def _encode_g722_with_ffmpeg(pcm_wav_path, output_file, sample_rate):
    """
    Encode PCM WAV to G.722 using ffmpeg

    Args:
        pcm_wav_path: Path to PCM WAV file
        output_file: Output G.722 file path
        sample_rate: Sample rate in Hz

    Returns:
        True if successful, False otherwise
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i",
                pcm_wav_path,  # Input PCM WAV
                "-ar",
                str(sample_rate),  # Sample rate
                "-ac",
                "1",  # Mono
                "-acodec",
                "g722",  # G.722 codec
                output_file,  # Output file
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.debug(f"ffmpeg G.722 encoding failed (full error): {result.stderr}")
            logger.warning(f"ffmpeg G.722 encoding failed: {result.stderr[:200]}...")
            return False

        logger.debug("Successfully encoded to G.722 using ffmpeg")
        return True

    except subprocess.TimeoutExpired as e:
        logger.warning(f"ffmpeg G.722 encoding timed out after 30s: {e}")
        return False
    except FileNotFoundError:
        logger.warning("ffmpeg not found. Install ffmpeg for G.722 support.")
        return False
    except (KeyError, OSError, TypeError, ValueError, subprocess.SubprocessError) as e:
        logger.warning(f"G.722 encoding error: {e}, falling back to PCM")
        logger.debug(f"Full error details: {e}", exc_info=True)
        return False


def _export_audio(audio, output_file, convert_to_g722, sample_rate):
    """
    Export audio to output file, optionally converting to G.722

    Args:
        audio: AudioSegment to export
        output_file: Output file path
        convert_to_g722: Whether to convert to G.722
        sample_rate: Sample rate in Hz

    Returns:
        Path to temporary PCM WAV file (if created) or None
    """
    temp_wav_path = None

    if convert_to_g722:
        # Export to temporary PCM WAV first
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            audio.export(temp_wav_path, format="wav")

        # Try to encode to G.722, fallback to PCM if fails
        if not _encode_g722_with_ffmpeg(temp_wav_path, output_file, sample_rate):
            logger.warning("Falling back to PCM WAV format")
            audio.export(output_file, format="wav")
    else:
        # Export as PCM WAV directly (recommended for maximum quality)
        audio.export(output_file, format="wav")

    return temp_wav_path


def text_to_wav_telephony(
    text, output_file, language="en", tld="com", slow=False, sample_rate=8000, convert_to_g722=False
):
    """
    Convert text to WAV file in telephony format using gTTS (Google Text-to-Speech)

    By default, generates high-quality PCM WAV files. G.722 encoding is available
    if ffmpeg is installed with G.722 codec support.

    Args:
        text: Text to convert to speech
        output_file: Output WAV file path
        language: Language code (default 'en' for English)
        tld: Top-level domain (default 'com' for US English accent)
        slow: Whether to use slow speech rate (default False for natural speed)
        sample_rate: Sample rate in Hz (default 8000 Hz for PCMU/G.711 audio)
                    Can be 8000 Hz for narrowband or 16000 Hz for wideband
        convert_to_g722: Convert output to G.722 format using ffmpeg (default False)
                        Requires ffmpeg with G.722 codec support. Falls back to PCM
                        if G.722 encoding fails. PCM provides better quality than G.722.

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

    temp_mp3_path = None
    temp_wav_path = None

    try:
        # Generate MP3 from text
        temp_mp3_path = _generate_mp3(text, language, tld, slow)

        # Convert to telephony audio format
        audio = _convert_to_telephony_audio(temp_mp3_path, sample_rate)

        # Export audio (with optional G.722 encoding)
        temp_wav_path = _export_audio(audio, output_file, convert_to_g722, sample_rate)

        return True

    except Exception as e:
        logger.error(f"Error generating TTS for '{text}': {e}")
        raise
    finally:
        # Clean up temp files
        if temp_mp3_path and Path(temp_mp3_path).exists():
            os.unlink(temp_mp3_path)
        if temp_wav_path and Path(temp_wav_path).exists():
            os.unlink(temp_wav_path)


def generate_prompts(prompts, output_dir, company_name=None, sample_rate=8000):
    """
    Generate multiple voice prompts from text

    Args:
        prompts: dict of {filename: text} to generate
        output_dir: Directory to save audio files
        company_name: Optional company name to substitute in text
        sample_rate: Sample rate in Hz (default 8000 Hz for PCMU/G.711 audio)

    Returns:
        tuple: (success_count, total_count)
    """
    if not GTTS_AVAILABLE:
        raise ImportError(
            f"TTS dependencies not available: {GTTS_IMPORT_ERROR}\n"
            f"Install with: {get_tts_requirements()}"
        )

    # Create output directory if needed
    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {output_dir}")

    success_count = 0
    total_count = len(prompts)

    for filename, text in prompts.items():
        # Substitute company name if present
        if company_name and "{company_name}" in text:
            text = text.replace("{company_name}", company_name)

        wav_name = filename if filename.endswith(".wav") else f"{filename}.wav"
        output_file = Path(output_dir) / wav_name

        try:
            if text_to_wav_telephony(text, output_file, sample_rate=sample_rate):
                file_size = Path(output_file).stat().st_size
                logger.info(f"Generated {filename}: {file_size:,} bytes")
                success_count += 1
        except OSError as e:
            logger.error(f"Failed to generate {filename}: {e}")

    return success_count, total_count
