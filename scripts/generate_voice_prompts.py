#!/usr/bin/env python3
"""
Generate All Voice Prompts for PBX System

This script generates tone-based audio prompts for:
- Auto Attendant (IVR)
- Voicemail System

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
    
    Returns:
        int: Number of files successfully generated
    """
    logger = get_logger()
    
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory: {output_dir}")
    
    # Define prompts to generate
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
    logger.info(f"Generated {success_count}/{len(prompts)} auto attendant prompts")
    logger.info("")
    
    return success_count


def generate_voicemail_prompts(output_dir='voicemail_prompts'):
    """
    Generate tone-based audio prompts for voicemail system
    
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
    
    # Define prompts to generate
    prompts = {
        'enter_pin.wav': {
            'type': 'enter_pin',
            'description': 'PIN entry - "Please enter your PIN followed by pound"'
        },
        'invalid_pin.wav': {
            'type': 'invalid_option',
            'description': 'Invalid PIN - "Invalid PIN, please try again"'
        },
        'main_menu.wav': {
            'type': 'main_menu',
            'description': 'Main menu - "Press 1 to listen, 2 for options, * to exit"'
        },
        'message_menu.wav': {
            'type': 'message_menu',
            'description': 'Message menu - "Press 1 to replay, 2 for next, 3 to delete"'
        },
        'no_messages.wav': {
            'type': 'no_messages',
            'description': 'No messages - "You have no messages"'
        },
        'you_have_messages.wav': {
            'type': 'you_have_messages',
            'description': 'Message count - "You have X new messages"'
        },
        'goodbye.wav': {
            'type': 'goodbye',
            'description': 'Goodbye - "Goodbye"'
        },
        'leave_message.wav': {
            'type': 'leave_message',
            'description': 'Leave message - "Please leave a message after the tone"'
        },
        'recording_greeting.wav': {
            'type': 'recording_greeting',
            'description': 'Record greeting - "Record your greeting after the tone, press # when done"'
        },
        'greeting_saved.wav': {
            'type': 'greeting_saved',
            'description': 'Greeting saved - "Your greeting has been saved"'
        },
        'message_deleted.wav': {
            'type': 'message_deleted',
            'description': 'Message deleted - "Message deleted"'
        },
        'end_of_messages.wav': {
            'type': 'end_of_messages',
            'description': 'End of messages - "End of messages"'
        },
    }
    
    logger.info("=" * 60)
    logger.info("Voicemail System Prompt Generator")
    logger.info("=" * 60)
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
            logger.info(f"✓ {filename:25s} ({file_size:6d} bytes) - {description}")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ {filename:25s} - ERROR: {e}")
    
    logger.info("")
    logger.info(f"Generated {success_count}/{len(prompts)} voicemail prompts")
    logger.info("")
    
    return success_count


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate all voice prompts for PBX system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              Generate all prompts
  %(prog)s --aa-only                    Generate only auto attendant prompts
  %(prog)s --vm-only                    Generate only voicemail prompts
  %(prog)s --aa-dir custom_aa           Use custom directory for AA prompts
  %(prog)s --vm-dir custom_vm           Use custom directory for VM prompts
  
The generated files are tone-based placeholders. For production use,
replace these with professionally recorded voice prompts.

Recording Scripts:
  Auto Attendant Welcome:
    "Thank you for calling [Company Name]. For Sales, press 1. 
     For Support, press 2. For Accounting, press 3. 
     Or press 0 to speak with an operator."
  
  Voicemail Main Menu:
    "You have X new messages. To listen to your messages, press 1. 
     For options, press 2. To exit, press star."
  
  Voicemail Message Menu:
    "To replay this message, press 1. For the next message, press 2. 
     To delete this message, press 3. To return to the main menu, press star."
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
    logger.info("=" * 60)
    logger.info("PBX Voice Prompt Generator")
    logger.info("=" * 60)
    logger.info("")
    
    total_success = 0
    total_files = 0
    
    # Generate auto attendant prompts
    if not args.vm_only:
        aa_count = generate_auto_attendant_prompts(args.aa_dir)
        total_success += aa_count
        total_files += 5  # Number of AA prompts
    
    # Generate voicemail prompts
    if not args.aa_only:
        vm_count = generate_voicemail_prompts(args.vm_dir)
        total_success += vm_count
        total_files += 12  # Number of VM prompts
    
    logger.info("=" * 60)
    logger.info(f"TOTAL: Generated {total_success}/{total_files} prompts successfully")
    logger.info("=" * 60)
    logger.info("")
    logger.info("IMPORTANT NOTES:")
    logger.info("  - These are TONE-BASED placeholders")
    logger.info("  - For production, replace with VOICE RECORDINGS")
    logger.info("")
    logger.info("To create professional voice prompts:")
    logger.info("  1. Record WAV files at 8000 Hz, 16-bit, mono")
    logger.info("  2. Name files according to the list above")
    logger.info("  3. Place in respective directories")
    logger.info("")
    logger.info("Text-to-Speech (TTS) options:")
    logger.info("  - Google Cloud TTS: https://cloud.google.com/text-to-speech")
    logger.info("  - Amazon Polly: https://aws.amazon.com/polly/")
    logger.info("  - Azure TTS: https://azure.microsoft.com/services/cognitive-services/text-to-speech/")
    logger.info("  - Free TTS: espeak, festival, pyttsx3")
    logger.info("")


if __name__ == '__main__':
    main()
