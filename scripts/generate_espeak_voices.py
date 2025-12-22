#!/usr/bin/env python3
"""
Generate Voice Prompts using gTTS (Google Text-to-Speech)

This script generates actual VOICE prompts using Google Text-to-Speech (gTTS).
The generated files are in proper telephony format: 8000 Hz, 16-bit, mono WAV.

Requirements:
    pip install gTTS pydub

Note: Requires internet connection to use Google TTS API (free, no API key needed)
      Voice quality is natural and professional-sounding.
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
    print(f"Please install required packages:")
    print(f"  {get_tts_requirements()}")
    print("")
    print("After installation, run this script again.")
    print("=" * 70)
    sys.exit(1)


def generate_auto_attendant_voices(output_dir="auto_attendant", company_name="your company"):
    """
    Generate voice prompts for auto attendant

    Args:
        output_dir: Directory to save audio files
        company_name: Company name to use in greeting

    Returns:
        int: Number of files successfully generated
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

    logger.info("=" * 70)
    logger.info("Auto Attendant Voice Generator (gTTS)")
    logger.info("=" * 70)
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
            if text_to_wav_telephony(text, output_file):
                file_size = os.path.getsize(output_file)
                logger.info(f"  ✓ SUCCESS - Generated ({file_size:,} bytes)")
                success_count += 1
            else:
                logger.error(f"  ✗ FAILED to generate")
        except Exception as e:
            logger.error(f"  ✗ ERROR: {e}")

        logger.info("")

    logger.info(f"Generated {success_count}/{len(prompts)} auto attendant prompts")
    logger.info("")

    return success_count


def generate_voicemail_voices(output_dir="voicemail_prompts"):
    """
    Generate voice prompts for voicemail system

    Args:
        output_dir: Directory to save audio files

    Returns:
        int: Number of files successfully generated
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

    logger.info("=" * 70)
    logger.info("Voicemail Voice Generator (gTTS)")
    logger.info("=" * 70)
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
            if text_to_wav_telephony(text, output_file):
                file_size = os.path.getsize(output_file)
                logger.info(f"  ✓ SUCCESS - Generated ({file_size:,} bytes)")
                success_count += 1
            else:
                logger.error(f"  ✗ FAILED to generate")
        except Exception as e:
            logger.error(f"  ✗ ERROR: {e}")

        logger.info("")

    logger.info(f"Generated {success_count}/{len(prompts)} voicemail prompts")
    logger.info("")

    return success_count


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate voice prompts using gTTS (Google Text-to-Speech)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    Generate all voice prompts
  %(prog)s --aa-only                          Generate only auto attendant
  %(prog)s --vm-only                          Generate only voicemail
  %(prog)s --company "ABC Company"            Use custom company name

This script uses Google Text-to-Speech (gTTS) to generate actual voice prompts.
Requires internet connection but no API key needed - completely free.

Voice Quality:
  - Natural and professional-sounding
  - Sounds like a real person speaking

The generated files are in proper telephony format:
  - Format: WAV
  - Sample Rate: 8000 Hz
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
        default="Aluminum Blanking Company",
        help="Company name for auto attendant greeting",
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

    args = parser.parse_args()

    # Setup logging
    PBXLogger().setup(log_level="INFO", console=True)
    logger = get_logger()

    logger.info("")
    logger.info("=" * 70)
    logger.info("PBX Voice Prompt Generator (gTTS)")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Using Google Text-to-Speech (gTTS)")
    logger.info("Generating REAL VOICE prompts (not tones!)")
    logger.info("Requires internet connection but no API key needed")
    logger.info("")

    total_success = 0
    total_files = 0

    # Generate auto attendant prompts
    if not args.vm_only:
        aa_count = generate_auto_attendant_voices(args.aa_dir, args.company)
        total_success += aa_count
        total_files += 5

    # Generate voicemail prompts
    if not args.aa_only:
        vm_count = generate_voicemail_voices(args.vm_dir)
        total_success += vm_count
        total_files += 13

    logger.info("=" * 70)
    logger.info(f"TOTAL: Generated {total_success}/{total_files} VOICE prompts")
    logger.info("=" * 70)
    logger.info("")

    if total_success == total_files:
        logger.info("✓ SUCCESS! Real voice prompts with actual speech generated!")
        logger.info("")
        logger.info("Files are in proper telephony format:")
        logger.info("  - WAV format, 8000 Hz, 16-bit, mono")
        logger.info("  - Ready to use with your PBX system")
        logger.info("")
        logger.info("Voice Quality:")
        logger.info("  - Natural and professional-sounding")
        logger.info("  - Suitable for production use")
        logger.info("")
        logger.info("gTTS is the recommended option for voice generation!")
        logger.info("")
    else:
        logger.error(f"✗ WARNING: Only {total_success}/{total_files} prompts generated")
        logger.error("Check that gTTS and pydub are installed:")
        logger.error("  pip install gTTS pydub")
        logger.error("Also ensure you have internet connectivity for gTTS")


if __name__ == "__main__":
    main()
