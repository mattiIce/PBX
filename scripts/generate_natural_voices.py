#!/usr/bin/env python3
"""
Generate Natural-Sounding Voice Prompts

This script provides multiple options for generating more human-sounding voice prompts:
1. eSpeak with better voice variants (en-us, en-gb, etc.)
2. eSpeak-ng (next generation with better quality)
3. Festival TTS (more natural than basic eSpeak)
4. Option to guide user to cloud TTS services

Requirements vary by method - see usage below.
"""
import os
import sys
import subprocess
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pbx.utils.logger import get_logger, PBXLogger


def check_tts_availability():
    """Check which TTS engines are available"""
    engines = {}
    
    # Check for espeak
    try:
        result = subprocess.run(['espeak', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            engines['espeak'] = True
    except FileNotFoundError:
        engines['espeak'] = False
    
    # Check for espeak-ng (next generation)
    try:
        result = subprocess.run(['espeak-ng', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            engines['espeak-ng'] = True
    except FileNotFoundError:
        engines['espeak-ng'] = False
    
    # Check for festival
    try:
        result = subprocess.run(['festival', '--version'], capture_output=True, text=True)
        engines['festival'] = result.returncode == 0
    except FileNotFoundError:
        engines['festival'] = False
    
    # Check for ffmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        engines['ffmpeg'] = result.returncode == 0
    except FileNotFoundError:
        engines['ffmpeg'] = False
    
    return engines


def text_to_wav_espeak_enhanced(text, output_file, voice='en-us', speed=150, pitch=50, gap=10):
    """
    Convert text to WAV using eSpeak with enhanced voice quality
    
    Args:
        text: Text to convert
        output_file: Output WAV file
        voice: Voice variant (en-us, en-gb, en-sc, en-rp, en-wm)
        speed: Speed (default 150)
        pitch: Pitch (default 50)
        gap: Word gap in 10ms units (default 10 = 100ms gaps)
    
    Returns:
        bool: Success
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
        
        # Use enhanced voice variants
        # en-us: American English (clearer than default)
        # en-gb: British English
        # en-sc: Scottish English
        # en-rp: Received Pronunciation (BBC English)
        result = subprocess.run([
            'espeak',
            '-v', voice,
            '-s', str(speed),
            '-p', str(pitch),
            '-g', str(gap),  # Add gaps between words for clarity
            '-a', '180',
            '-w', temp_wav_path,
            text
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return False
        
        # Convert to telephony format
        result = subprocess.run([
            'ffmpeg', '-y', '-i', temp_wav_path,
            '-ar', '8000', '-ac', '1', '-sample_fmt', 's16',
            '-loglevel', 'error',
            output_file
        ], capture_output=True, text=True)
        
        try:
            os.unlink(temp_wav_path)
        except:
            pass
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def text_to_wav_espeak_ng(text, output_file, voice='en-us', speed=150, pitch=50):
    """
    Convert text to WAV using eSpeak-NG (next generation - better quality)
    
    Args:
        text: Text to convert
        output_file: Output WAV file
        voice: Voice variant
        speed: Speed
        pitch: Pitch
    
    Returns:
        bool: Success
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
        
        result = subprocess.run([
            'espeak-ng',
            '-v', voice,
            '-s', str(speed),
            '-p', str(pitch),
            '-a', '180',
            '-w', temp_wav_path,
            text
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return False
        
        result = subprocess.run([
            'ffmpeg', '-y', '-i', temp_wav_path,
            '-ar', '8000', '-ac', '1', '-sample_fmt', 's16',
            '-loglevel', 'error',
            output_file
        ], capture_output=True, text=True)
        
        try:
            os.unlink(temp_wav_path)
        except:
            pass
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def text_to_wav_festival(text, output_file):
    """
    Convert text to WAV using Festival TTS (more natural than basic eSpeak)
    
    Args:
        text: Text to convert
        output_file: Output WAV file
    
    Returns:
        bool: Success
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
        
        # Create festival script
        festival_script = f'(voice_cmu_us_slt_arctic_hts)\n(utt.save.wave (utt.synth (Utterance Text "{text}")) "{temp_wav_path}")'
        
        result = subprocess.run(
            ['festival'],
            input=festival_script,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or not os.path.exists(temp_wav_path):
            return False
        
        result = subprocess.run([
            'ffmpeg', '-y', '-i', temp_wav_path,
            '-ar', '8000', '-ac', '1', '-sample_fmt', 's16',
            '-loglevel', 'error',
            output_file
        ], capture_output=True, text=True)
        
        try:
            os.unlink(temp_wav_path)
        except:
            pass
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def generate_prompts(output_dir_aa='auto_attendant', output_dir_vm='voicemail_prompts', 
                     company_name='Aluminum Blanking Company', engine='espeak-enhanced',
                     voice='en-us'):
    """
    Generate all prompts with specified TTS engine
    
    Args:
        output_dir_aa: Auto attendant output directory
        output_dir_vm: Voicemail output directory
        company_name: Company name
        engine: TTS engine ('espeak-enhanced', 'espeak-ng', 'festival')
        voice: Voice variant (for espeak engines)
    
    Returns:
        tuple: (success_count, total_count)
    """
    logger = get_logger()
    
    # Create output directories
    os.makedirs(output_dir_aa, exist_ok=True)
    os.makedirs(output_dir_vm, exist_ok=True)
    
    # Define all prompts
    aa_prompts = {
        'welcome.wav': f'Thank you for calling {company_name}.',
        'main_menu.wav': 'For Sales, press 1. For Support, press 2. For Accounting, press 3. Or press 0 to speak with an operator.',
        'invalid.wav': 'That is not a valid option. Please try again.',
        'timeout.wav': 'We did not receive your selection. Please try again.',
        'transferring.wav': 'Please hold while we transfer your call.',
    }
    
    vm_prompts = {
        'enter_pin.wav': 'Please enter your PIN followed by the pound key.',
        'invalid_pin.wav': 'Invalid PIN. Please try again.',
        'main_menu.wav': 'To listen to your messages, press 1. For options, press 2. To exit, press star.',
        'message_menu.wav': 'To replay this message, press 1. For the next message, press 2. To delete this message, press 3. To return to the main menu, press star.',
        'no_messages.wav': 'You have no new messages.',
        'you_have_messages.wav': 'You have new messages.',
        'goodbye.wav': 'Goodbye.',
        'leave_message.wav': 'Please leave a message after the tone. When you are finished, hang up or press pound.',
        'recording_greeting.wav': 'Record your greeting after the tone. When finished, press pound.',
        'greeting_saved.wav': 'Your greeting has been saved.',
        'message_deleted.wav': 'Message deleted.',
        'end_of_messages.wav': 'End of messages.',
    }
    
    success = 0
    total = 0
    
    # Choose TTS function
    if engine == 'espeak-ng':
        tts_func = lambda text, file: text_to_wav_espeak_ng(text, file, voice=voice)
    elif engine == 'festival':
        tts_func = lambda text, file: text_to_wav_festival(text, file)
    else:  # espeak-enhanced
        tts_func = lambda text, file: text_to_wav_espeak_enhanced(text, file, voice=voice)
    
    # Generate AA prompts
    logger.info(f"Generating Auto Attendant prompts with {engine}...")
    for filename, text in aa_prompts.items():
        output_file = os.path.join(output_dir_aa, filename)
        total += 1
        logger.info(f"  {filename}...")
        if tts_func(text, output_file):
            size = os.path.getsize(output_file)
            logger.info(f"    ✓ Generated ({size:,} bytes)")
            success += 1
        else:
            logger.error(f"    ✗ Failed")
    
    # Generate VM prompts
    logger.info(f"\nGenerating Voicemail prompts with {engine}...")
    for filename, text in vm_prompts.items():
        output_file = os.path.join(output_dir_vm, filename)
        total += 1
        logger.info(f"  {filename}...")
        if tts_func(text, output_file):
            size = os.path.getsize(output_file)
            logger.info(f"    ✓ Generated ({size:,} bytes)")
            success += 1
        else:
            logger.error(f"    ✗ Failed")
    
    return success, total


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate natural-sounding voice prompts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voice Quality Comparison (Best to Basic):
  1. Cloud TTS (Google/Amazon/Azure) - Most natural, costs $4/1M chars
  2. Festival - More natural than eSpeak, free offline
  3. eSpeak-NG - Improved eSpeak, free offline
  4. eSpeak Enhanced - Better than basic eSpeak, free offline
  5. Basic eSpeak - Most robotic, free offline

Installation Commands:
  # For eSpeak Enhanced (already installed):
  sudo apt-get install espeak ffmpeg
  
  # For eSpeak-NG (better quality):
  sudo apt-get install espeak-ng ffmpeg
  
  # For Festival (most natural offline option):
  sudo apt-get install festival festvox-us-slt-hts ffmpeg

Examples:
  # Enhanced eSpeak with American voice (default)
  %(prog)s
  
  # eSpeak-NG (better quality if installed)
  %(prog)s --engine espeak-ng
  
  # Festival (most natural offline if installed)
  %(prog)s --engine festival
  
  # British accent
  %(prog)s --voice en-gb
  
  # Custom company name
  %(prog)s --company "Your Company"

Voice Variants (eSpeak/eSpeak-NG):
  en-us  - American English (clearest)
  en-gb  - British English
  en-rp  - Received Pronunciation (BBC English)
  en-sc  - Scottish English
  en-wm  - West Midlands English
        """
    )
    
    parser.add_argument('--engine', choices=['espeak-enhanced', 'espeak-ng', 'festival'],
                       default='espeak-enhanced', help='TTS engine to use')
    parser.add_argument('--voice', default='en-us', 
                       help='Voice variant (for espeak engines)')
    parser.add_argument('--company', default='Aluminum Blanking Company',
                       help='Company name for greeting')
    parser.add_argument('--check', action='store_true',
                       help='Check which TTS engines are available')
    
    args = parser.parse_args()
    
    # Setup logging
    PBXLogger().setup(log_level='INFO', console=True)
    logger = get_logger()
    
    # Check availability if requested
    if args.check:
        logger.info("Checking TTS engine availability...")
        logger.info("")
        engines = check_tts_availability()
        
        logger.info(f"eSpeak:     {'✓ Installed' if engines['espeak'] else '✗ Not installed (sudo apt-get install espeak)'}")
        logger.info(f"eSpeak-NG:  {'✓ Installed' if engines['espeak-ng'] else '✗ Not installed (sudo apt-get install espeak-ng)'}")
        logger.info(f"Festival:   {'✓ Installed' if engines['festival'] else '✗ Not installed (sudo apt-get install festival festvox-us-slt-hts)'}")
        logger.info(f"ffmpeg:     {'✓ Installed' if engines['ffmpeg'] else '✗ Not installed (sudo apt-get install ffmpeg)'}")
        logger.info("")
        
        if engines['festival']:
            logger.info("✓ BEST OPTION: Festival is installed (most natural offline voice)")
        elif engines['espeak-ng']:
            logger.info("✓ GOOD OPTION: eSpeak-NG is installed (improved quality)")
        elif engines['espeak']:
            logger.info("✓ BASIC OPTION: eSpeak is installed (robotic but functional)")
        else:
            logger.error("✗ No TTS engine installed!")
        
        logger.info("")
        logger.info("For even better quality, consider cloud TTS:")
        logger.info("  - Google Cloud TTS: Very natural, $4 per 1M characters")
        logger.info("  - Amazon Polly: Very natural, $4 per 1M characters")
        logger.info("  - Azure TTS: Neural voices, $4 per 1M characters")
        logger.info("")
        logger.info("See VOICE_PROMPTS_GUIDE.md for cloud TTS instructions")
        return
    
    # Check if selected engine is available
    engines = check_tts_availability()
    
    if args.engine == 'espeak-ng' and not engines['espeak-ng']:
        logger.error("eSpeak-NG not installed!")
        logger.error("Install with: sudo apt-get install espeak-ng")
        logger.info("Falling back to enhanced eSpeak...")
        args.engine = 'espeak-enhanced'
    
    if args.engine == 'festival' and not engines['festival']:
        logger.error("Festival not installed!")
        logger.error("Install with: sudo apt-get install festival festvox-us-slt-hts")
        logger.info("Falling back to enhanced eSpeak...")
        args.engine = 'espeak-enhanced'
    
    if not engines['ffmpeg']:
        logger.error("ffmpeg not installed!")
        logger.error("Install with: sudo apt-get install ffmpeg")
        return
    
    # Generate prompts
    logger.info("=" * 70)
    logger.info("Natural Voice Prompt Generator")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Engine: {args.engine}")
    if args.engine in ['espeak-enhanced', 'espeak-ng']:
        logger.info(f"Voice: {args.voice}")
    logger.info(f"Company: {args.company}")
    logger.info("")
    
    success, total = generate_prompts(
        company_name=args.company,
        engine=args.engine,
        voice=args.voice
    )
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"Generated {success}/{total} voice prompts")
    logger.info("=" * 70)
    logger.info("")
    
    if success == total:
        logger.info("✓ SUCCESS! Voice prompts generated")
        logger.info("")
        logger.info("Voice Quality Tips:")
        if args.engine == 'festival':
            logger.info("  ✓ Using Festival - good quality for offline TTS")
        elif args.engine == 'espeak-ng':
            logger.info("  ✓ Using eSpeak-NG - improved over basic eSpeak")
        else:
            logger.info("  • Using enhanced eSpeak settings")
            logger.info("  • For better quality, try: --engine festival")
        
        logger.info("")
        logger.info("For professional quality:")
        logger.info("  1. Use cloud TTS (Google/Amazon/Azure) - see VOICE_PROMPTS_GUIDE.md")
        logger.info("  2. Hire professional voice actor - $50-$500")
        logger.info("  3. Record yourself - see VOICE_PROMPTS_GUIDE.md")
    else:
        logger.error(f"Warning: Only {success}/{total} prompts generated")


if __name__ == '__main__':
    main()
