#!/usr/bin/env python3
"""
Generate Auto Attendant Audio Prompts

This script generates tone-based audio prompts for the auto attendant system.

NOTE: For production use, these tone-based prompts should be replaced with
professionally recorded voice prompts. You can:
1. Record your own prompts and save as WAV files
2. Use Text-to-Speech (TTS) services (Google TTS, Amazon Polly, Azure TTS)
3. Hire a professional voice actor

File format: WAV, 8000 Hz, 16-bit, mono
"""
import os
import sys

# Add parent directory to path so we can import pbx modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.utils.audio import generate_voice_prompt
from pbx.utils.logger import get_logger, PBXLogger

def generate_auto_attendant_prompts(output_dir='auto_attendant'):
    """
    Generate tone-based audio prompts for auto attendant
    
    Args:
        output_dir: Directory to save audio files
    """
    # Setup logging
    PBXLogger().setup(log_level='INFO', console=True)
    logger = get_logger()
    
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory: {output_dir}")
    
    # Define prompts to generate
    # Each prompt maps to a tone sequence defined in pbx/utils/audio.py
    prompts = {
        'welcome.wav': {
            'type': 'auto_attendant_welcome',
            'description': 'Welcome greeting - "Thank you for calling..."'
        },
        'main_menu.wav': {
            'type': 'auto_attendant_menu',
            'description': 'Main menu - "Press 1 for Sales, Press 2 for Support..."'
        },
        'invalid.wav': {
            'type': 'invalid_option',
            'description': 'Invalid option - "Invalid option, please try again"'
        },
        'timeout.wav': {
            'type': 'timeout',
            'description': 'Timeout - "We did not receive your selection"'
        },
        'transferring.wav': {
            'type': 'transferring',
            'description': 'Transferring - "Please hold while we transfer your call"'
        },
    }
    
    logger.info("=" * 60)
    logger.info("Auto Attendant Prompt Generator")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Generating tone-based audio prompts...")
    logger.info(f"Output directory: {output_dir}")
    logger.info("")
    
    # Generate each prompt
    success_count = 0
    for filename, info in prompts.items():
        output_file = os.path.join(output_dir, filename)
        prompt_type = info['type']
        description = info['description']
        
        try:
            # Generate the prompt
            wav_data = generate_voice_prompt(prompt_type)
            
            # Write to file
            with open(output_file, 'wb') as f:
                f.write(wav_data)
            
            file_size = len(wav_data)
            logger.info(f"✓ {filename:20s} ({file_size:6d} bytes) - {description}")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ {filename:20s} - ERROR: {e}")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Generated {success_count}/{len(prompts)} prompts successfully")
    logger.info("=" * 60)
    logger.info("")
    logger.info("IMPORTANT NOTES:")
    logger.info("  - These are TONE-BASED placeholders")
    logger.info("  - For production, replace with VOICE RECORDINGS")
    logger.info("")
    logger.info("To create professional voice prompts:")
    logger.info("  1. Record WAV files at 8000 Hz, 16-bit, mono")
    logger.info("  2. Name files: welcome.wav, main_menu.wav, invalid.wav, etc.")
    logger.info("  3. Place in 'auto_attendant' directory")
    logger.info("")
    logger.info("Example menu recording script:")
    logger.info("  'Thank you for calling. Press 1 for Sales,")
    logger.info("   Press 2 for Support, Press 3 for Accounting,")
    logger.info("   or Press 0 for the Operator.'")
    logger.info("")
    logger.info("Text-to-Speech (TTS) options:")
    logger.info("  - Google Cloud TTS: https://cloud.google.com/text-to-speech")
    logger.info("  - Amazon Polly: https://aws.amazon.com/polly/")
    logger.info("  - Azure TTS: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/")
    logger.info("  - Free TTS: espeak, festival, pyttsx3")
    logger.info("")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate auto attendant audio prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Generate prompts in ./auto_attendant
  %(prog)s -o /var/pbx/aa_audio     Generate prompts in custom directory
  
The generated files are tone-based placeholders. For production use,
replace these with professionally recorded voice prompts.
        """
    )
    parser.add_argument(
        '-o', '--output',
        default='auto_attendant',
        help='Output directory for audio files (default: auto_attendant)'
    )
    
    args = parser.parse_args()
    
    generate_auto_attendant_prompts(args.output)
