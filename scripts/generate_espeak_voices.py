#!/usr/bin/env python3
"""
Generate Voice Prompts using eSpeak (Direct)

This script generates actual VOICE prompts using espeak directly.
The generated files are in proper telephony format: 8000 Hz, 16-bit, mono WAV.

Requirements:
    sudo apt-get install espeak ffmpeg

Note: Works completely offline, no internet connection required!
      Voice quality is robotic but clear and functional.
"""
import os
import sys
import subprocess
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.utils.logger import get_logger, PBXLogger


def text_to_wav_telephony(text, output_file, speed=150, pitch=50):
    """
    Convert text to WAV file in telephony format (8000 Hz, 16-bit, mono)
    
    Args:
        text: Text to convert to speech
        output_file: Output WAV file path
        speed: Speech speed (words per minute, default 150)
        pitch: Pitch adjustment (0-99, default 50)
    
    Returns:
        bool: True if successful
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
        
        # Generate speech with espeak
        # -s speed (words per minute)
        # -p pitch (0-99, default 50)
        # -a amplitude/volume (0-200, default 100)
        # -w write to WAV file
        result = subprocess.run([
            'espeak',
            '-s', str(speed),
            '-p', str(pitch),
            '-a', '180',  # Slightly louder
            '-w', temp_wav_path,
            text
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"espeak error: {result.stderr}")
            return False
        
        # Convert to telephony format using ffmpeg (8000 Hz, mono, 16-bit)
        result = subprocess.run([
            'ffmpeg', '-y', '-i', temp_wav_path,
            '-ar', '8000',  # 8000 Hz sample rate
            '-ac', '1',      # Mono
            '-sample_fmt', 's16',  # 16-bit
            '-loglevel', 'error',  # Only show errors
            output_file
        ], capture_output=True, text=True)
        
        # Clean up temp file
        try:
            os.unlink(temp_wav_path)
        except:
            pass
        
        if result.returncode == 0:
            return True
        else:
            print(f"ffmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error generating TTS: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_auto_attendant_voices(output_dir='auto_attendant', company_name="your company"):
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
        'welcome.wav': {
            'text': f'Thank you for calling {company_name}.',
            'description': 'Welcome greeting'
        },
        'main_menu.wav': {
            'text': 'For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.',
            'description': 'Main menu options'
        },
        'invalid.wav': {
            'text': 'That is not a valid option. Please try again.',
            'description': 'Invalid option message'
        },
        'timeout.wav': {
            'text': 'We did not receive your selection. Please try again.',
            'description': 'Timeout message'
        },
        'transferring.wav': {
            'text': 'Please hold while we transfer your call.',
            'description': 'Transfer message'
        },
    }
    
    logger.info("=" * 70)
    logger.info("Auto Attendant Voice Generator (eSpeak)")
    logger.info("=" * 70)
    logger.info("")
    
    # Generate each prompt
    success_count = 0
    for filename, info in prompts.items():
        output_file = os.path.join(output_dir, filename)
        text = info['text']
        description = info['description']
        
        logger.info(f"Generating {filename}...")
        logger.info(f"  Text: \"{text}\"")
        
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


def generate_voicemail_voices(output_dir='voicemail_prompts'):
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
        'enter_pin.wav': {
            'text': 'Please enter your PIN followed by the pound key.',
            'description': 'PIN entry prompt'
        },
        'invalid_pin.wav': {
            'text': 'Invalid PIN. Please try again.',
            'description': 'Invalid PIN message'
        },
        'main_menu.wav': {
            'text': 'To listen to your messages, press 1. For options, press 2. To exit, press star.',
            'description': 'Voicemail main menu'
        },
        'message_menu.wav': {
            'text': 'To replay this message, press 1. For the next message, press 2. To delete this message, press 3. To return to the main menu, press star.',
            'description': 'Message playback menu'
        },
        'no_messages.wav': {
            'text': 'You have no new messages.',
            'description': 'No messages notification'
        },
        'you_have_messages.wav': {
            'text': 'You have new messages.',
            'description': 'Message count announcement'
        },
        'goodbye.wav': {
            'text': 'Goodbye.',
            'description': 'Goodbye message'
        },
        'leave_message.wav': {
            'text': 'Please leave a message after the tone. When you are finished, hang up or press pound.',
            'description': 'Leave message prompt'
        },
        'recording_greeting.wav': {
            'text': 'Record your greeting after the tone. When finished, press pound.',
            'description': 'Record greeting prompt'
        },
        'greeting_saved.wav': {
            'text': 'Your greeting has been saved.',
            'description': 'Greeting saved confirmation'
        },
        'message_deleted.wav': {
            'text': 'Message deleted.',
            'description': 'Message deleted confirmation'
        },
        'end_of_messages.wav': {
            'text': 'End of messages.',
            'description': 'End of messages notification'
        },
    }
    
    logger.info("=" * 70)
    logger.info("Voicemail Voice Generator (eSpeak)")
    logger.info("=" * 70)
    logger.info("")
    
    # Generate each prompt
    success_count = 0
    for filename, info in prompts.items():
        output_file = os.path.join(output_dir, filename)
        text = info['text']
        description = info['description']
        
        logger.info(f"Generating {filename}...")
        logger.info(f"  Text: \"{text}\"")
        
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
        description='Generate voice prompts using eSpeak (Offline TTS)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    Generate all voice prompts
  %(prog)s --aa-only                          Generate only auto attendant
  %(prog)s --vm-only                          Generate only voicemail
  %(prog)s --company "ABC Company"            Use custom company name
  
This script uses eSpeak to generate actual voice prompts.
Works completely offline - no internet connection required!

Voice Quality:
  - Robotic but clear and intelligible
  - Professional quality requires cloud TTS or voice actor
  
The generated files are in proper telephony format:
  - Format: WAV
  - Sample Rate: 8000 Hz
  - Bit Depth: 16-bit
  - Channels: Mono
        """
    )
    parser.add_argument(
        '--aa-only',
        action='store_true',
        help='Generate only auto attendant prompts'
    )
    parser.add_argument(
        '--vm-only',
        action='store_true',
        help='Generate only voicemail prompts'
    )
    parser.add_argument(
        '--company',
        default='Aluminum Blanking Company',
        help='Company name for auto attendant greeting'
    )
    parser.add_argument(
        '--aa-dir',
        default='auto_attendant',
        help='Output directory for auto attendant prompts (default: auto_attendant)'
    )
    parser.add_argument(
        '--vm-dir',
        default='voicemail_prompts',
        help='Output directory for voicemail prompts (default: voicemail_prompts)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    PBXLogger().setup(log_level='INFO', console=True)
    logger = get_logger()
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("PBX Voice Prompt Generator (eSpeak TTS)")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Using eSpeak (free, offline text-to-speech)")
    logger.info("Generating REAL VOICE prompts (not tones!)")
    logger.info("Works completely offline - no internet required")
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
        total_files += 12
    
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
        logger.info("  - Robotic but clear and intelligible")
        logger.info("  - Suitable for testing and basic production use")
        logger.info("")
        logger.info("For higher quality voices, consider:")
        logger.info("  - Google Cloud TTS (natural voices, $4/1M chars)")
        logger.info("  - Amazon Polly (natural voices, $4/1M chars)")
        logger.info("  - Azure TTS (neural voices, $4/1M chars)")
        logger.info("  - Professional voice actor recordings")
        logger.info("")
    else:
        logger.error(f"✗ WARNING: Only {total_success}/{total_files} prompts generated")
        logger.error("Check that espeak and ffmpeg are installed:")
        logger.error("  sudo apt-get install espeak ffmpeg")


if __name__ == '__main__':
    main()
