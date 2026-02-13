#!/usr/bin/env python3
"""
Generate Voice Prompts using Text-to-Speech

This script generates actual VOICE prompts (not tones) using Google Text-to-Speech (gTTS).
The generated files are in proper telephony format: 8000 Hz, 16-bit, mono WAV.

Requirements:
    pip install gTTS pydub

Note: Requires internet connection to use Google TTS API (free, no API key needed)
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import dependencies with helpful error messages
try:
    from pbx.utils.logger import PBXLogger, get_logger
    from pbx.utils.tts import get_tts_requirements, is_tts_available, text_to_wav_telephony
except ImportError as e:
    print(f"Error: Could not import PBX utilities: {e}")
    print("Make sure you're running this script from the PBX directory")
    sys.exit(1)

# Check if TTS dependencies are available
if not is_tts_available():
    print("=" * 70)
    print("ERROR: TTS dependencies not installed!")
    print("=" * 70)
    print("")
    print("Please install required packages:")
    print(f"  {get_tts_requirements()}")
    print("")
    print("After installation, run this script again.")
    print("=" * 70)
    sys.exit(1)


def generate_auto_attendant_tts(
    output_dir="auto_attendant", company_name="your company", sample_rate=8000
):
    """
    Generate TTS voice prompts for auto attendant

    Args:
        output_dir: Directory to save audio files
        company_name: Company name to use in greeting
        sample_rate: Sample rate in Hz (default 8000 Hz for PCMU/G.711 audio)

    Returns:
        int: Number of files successfully generated

    Note:
        Generates PCM WAV files (not G.722) for maximum audio quality and compatibility.
    """
    logger = get_logger()

    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory: {output_dir}")

    # Define prompts with actual text
    prompts = {
        "welcome.wav": {
            "text": f"Thank you for calling {company_name}.",
            "description": "Welcome greeting",
        },
        "main_menu.wav": {
            "text": "For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.",
            "description": "Main menu options",
        },
        "invalid.wav": {
            "text": "That is not a valid option. Please try again.",
            "description": "Invalid option message",
        },
        "timeout.wav": {
            "text": "We did not receive your selection. Please try again.",
            "description": "Timeout message",
        },
        "transferring.wav": {
            "text": "Please hold while we transfer your call.",
            "description": "Transfer message",
        },
    }

    logger.info("=" * 60)
    logger.info("Auto Attendant TTS Generator")
    logger.info("=" * 60)
    logger.info("")

    # Generate each prompt
    success_count = 0
    for filename, info in prompts.items():
        output_file = os.path.join(output_dir, filename)
        text = info["text"]
        description = info["description"]

        logger.info(f"Generating {filename}...")
        logger.info(f'  Text: "{text}"')

        try:
            if text_to_wav_telephony(text, output_file, sample_rate=sample_rate):
                file_size = os.path.getsize(output_file)
                logger.info(f"  ✓ Generated ({file_size:,} bytes) - {description}")
                success_count += 1
            else:
                logger.error(f"  ✗ Failed to generate {filename}")
        except OSError as e:
            logger.error(f"  ✗ Error: {e}")

        logger.info("")

    logger.info(f"Generated {success_count}/{len(prompts)} auto attendant prompts")
    logger.info("")

    return success_count


def generate_voicemail_tts(output_dir="voicemail_prompts", sample_rate=8000):
    """
    Generate TTS voice prompts for voicemail system

    Args:
        output_dir: Directory to save audio files
        sample_rate: Sample rate in Hz (default 8000 Hz for PCMU/G.711 audio)

    Returns:
        int: Number of files successfully generated

    Note:
        Generates PCM WAV files (not G.722) for maximum audio quality and compatibility.
    """
    logger = get_logger()

    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory: {output_dir}")

    # Define prompts with actual text
    prompts = {
        "enter_pin.wav": {
            "text": "Please enter your PIN followed by the pound key.",
            "description": "PIN entry prompt",
        },
        "invalid_pin.wav": {
            "text": "Invalid PIN. Please try again.",
            "description": "Invalid PIN message",
        },
        "main_menu.wav": {
            "text": "To listen to your messages, press 1. For options, press 2. To exit, press star.",
            "description": "Voicemail main menu",
        },
        "options_menu.wav": {
            "text": "Press 1 to record greeting. Press star to return to main menu.",
            "description": "Options menu",
        },
        "message_menu.wav": {
            "text": "To replay this message, press 1. For the next message, press 2. To delete this message, press 3. To return to the main menu, press star.",
            "description": "Message playback menu",
        },
        "no_messages.wav": {
            "text": "You have no new messages.",
            "description": "No messages notification",
        },
        "you_have_messages.wav": {
            "text": "You have new messages.",
            "description": "Message count announcement",
        },
        "goodbye.wav": {"text": "Goodbye.", "description": "Goodbye message"},
        "leave_message.wav": {
            "text": "Please leave a message after the tone. When you are finished, hang up or press pound.",
            "description": "Leave message prompt",
        },
        "recording_greeting.wav": {
            "text": "Record your greeting after the tone. When finished, press pound.",
            "description": "Record greeting prompt",
        },
        "greeting_saved.wav": {
            "text": "Your greeting has been saved.",
            "description": "Greeting saved confirmation",
        },
        "message_deleted.wav": {
            "text": "Message deleted.",
            "description": "Message deleted confirmation",
        },
        "end_of_messages.wav": {
            "text": "End of messages.",
            "description": "End of messages notification",
        },
    }

    logger.info("=" * 60)
    logger.info("Voicemail TTS Generator")
    logger.info("=" * 60)
    logger.info("")

    # Generate each prompt
    success_count = 0
    for filename, info in prompts.items():
        output_file = os.path.join(output_dir, filename)
        text = info["text"]
        description = info["description"]

        logger.info(f"Generating {filename}...")
        logger.info(f'  Text: "{text}"')

        try:
            if text_to_wav_telephony(text, output_file, sample_rate=sample_rate):
                file_size = os.path.getsize(output_file)
                logger.info(f"  ✓ Generated ({file_size:,} bytes) - {description}")
                success_count += 1
            else:
                logger.error(f"  ✗ Failed to generate {filename}")
        except OSError as e:
            logger.error(f"  ✗ Error: {e}")

        logger.info("")

    logger.info(f"Generated {success_count}/{len(prompts)} voicemail prompts")
    logger.info("")

    return success_count


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate voice prompts using Text-to-Speech",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    Generate all voice prompts (16kHz wideband)
  %(prog)s --aa-only                          Generate only auto attendant
  %(prog)s --vm-only                          Generate only voicemail
  %(prog)s --company "ABC Company"            Use custom company name
  %(prog)s --aa-dir custom_aa                 Custom output directory
  %(prog)s --sample-rate 8000                 Use 8kHz for narrowband audio

This script uses Google Text-to-Speech (gTTS) to generate actual voice prompts.
Requires internet connection but no API key needed - completely free.

The generated files are in proper telephony format:
  - Format: WAV (PCM)
  - Sample Rate: 8000 Hz (narrowband/PCMU) or 16000 Hz (wideband/G.722)
  - Bit Depth: 16-bit
  - Channels: Mono
        """,
    )
    parser.add_argument(
        "--aa-only", action="store_true", help="Generate only auto attendant prompts"
    )
    parser.add_argument("--vm-only", action="store_true", help="Generate only voicemail prompts")
    parser.add_argument(
        "--company",
        default="your company",
        help='Company name for auto attendant greeting (default: "your company")',
    )
    parser.add_argument(
        "--aa-dir",
        default="auto_attendant",
        help="Output directory for auto attendant prompts (default: auto_attendant)",
    )
    parser.add_argument(
        "--vm-dir",
        default="voicemail_prompts",
        help="Output directory for voicemail prompts (default: voicemail_prompts)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=8000,
        choices=[8000, 16000],
        help="Sample rate in Hz: 8000 for narrowband (PCMU/G.711), 16000 for wideband (default: 8000)",
    )

    args = parser.parse_args()

    # Setup logging
    PBXLogger().setup(log_level="INFO", console=True)
    logger = get_logger()

    logger.info("")
    logger.info("=" * 60)
    logger.info("PBX Voice Prompt Generator (Text-to-Speech)")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Using Google Text-to-Speech (gTTS)")
    logger.info("Generating REAL VOICE prompts (not tones)")
    logger.info(
        f"Sample Rate: {args.sample_rate} Hz ({'Wideband/G.722' if args.sample_rate == 16000 else 'Narrowband/PCMU'})"
    )
    logger.info("Format: PCM WAV (16-bit, mono)")
    logger.info("")

    total_success = 0
    total_files = 0

    # Generate auto attendant prompts
    if not args.vm_only:
        aa_count = generate_auto_attendant_tts(args.aa_dir, args.company, args.sample_rate)
        total_success += aa_count
        total_files += 5

    # Generate voicemail prompts
    if not args.aa_only:
        vm_count = generate_voicemail_tts(args.vm_dir, args.sample_rate)
        total_success += vm_count
        total_files += 13

    logger.info("=" * 60)
    logger.info(f"TOTAL: Generated {total_success}/{total_files} voice prompts")
    logger.info("=" * 60)
    logger.info("")
    logger.info("SUCCESS! Real voice prompts have been generated.")
    logger.info("The files are now in proper telephony format:")
    logger.info(f"  - PCM WAV format, {args.sample_rate} Hz, 16-bit, mono")
    logger.info("  - Ready to use with your PBX system")
    logger.info("")
    if args.sample_rate == 16000:
        logger.info("These files use wideband audio (16kHz) for G.722 codec.")
    else:
        logger.info("These files use narrowband audio (8kHz) for PCMU/G.711 codec.")
    logger.info("")
    logger.info("To customize the voice or language:")
    logger.info("  - Edit this script and change the 'language' parameter")
    logger.info("  - Supported languages: en, es, fr, de, it, pt, and many more")
    logger.info("  - See: https://gtts.readthedocs.io/en/latest/module.html#languages")
    logger.info("")

    if total_success < total_files:
        logger.warning(f"Warning: Only {total_success}/{total_files} prompts generated")
        logger.warning("Check that you have internet connection (required for gTTS)")


if __name__ == "__main__":
    main()
