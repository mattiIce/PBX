"""
Auto Attendant (IVR) System for PBX
Provides automated call answering and menu navigation
"""
import os
import threading
import time
from enum import Enum
from pbx.utils.logger import get_logger


class AAState(Enum):
    """Auto Attendant states"""
    WELCOME = "welcome"
    MAIN_MENU = "main_menu"
    TRANSFERRING = "transferring"
    INVALID = "invalid"
    TIMEOUT = "timeout"
    ENDED = "ended"


class AutoAttendant:
    """
    Auto Attendant system that answers calls and provides menu options
    
    Features:
    - Welcome greeting
    - Menu options (press 1 for sales, 2 for support, etc.)
    - DTMF input handling
    - Call transfer to extensions/queues
    - Timeout handling
    """
    
    def __init__(self, config=None, pbx_core=None):
        """
        Initialize Auto Attendant
        
        Args:
            config: Configuration object
            pbx_core: Reference to PBX core for call transfers
        """
        self.logger = get_logger()
        self.config = config
        self.pbx_core = pbx_core
        
        # Get auto attendant configuration
        aa_config = config.get('auto_attendant', {}) if config else {}
        self.enabled = aa_config.get('enabled', True)
        self.extension = aa_config.get('extension', '0')
        self.timeout = aa_config.get('timeout', 10)  # seconds to wait for input
        self.max_retries = aa_config.get('max_retries', 3)
        self.audio_path = aa_config.get('audio_path', 'auto_attendant')
        
        # Menu options mapping
        # Key: DTMF digit, Value: (destination, description)
        self.menu_options = {}
        menu_items = aa_config.get('menu_options', [])
        for item in menu_items:
            digit = str(item.get('digit'))
            destination = item.get('destination')
            description = item.get('description', '')
            self.menu_options[digit] = {
                'destination': destination,
                'description': description
            }
        
        # Create audio directory if it doesn't exist
        if not os.path.exists(self.audio_path):
            os.makedirs(self.audio_path)
            self.logger.info(f"Created auto attendant audio directory: {self.audio_path}")
        
        self.logger.info(f"Auto Attendant initialized on extension {self.extension}")
        self.logger.info(f"Menu options: {len(self.menu_options)}")
    
    def is_enabled(self):
        """Check if auto attendant is enabled"""
        return self.enabled
    
    def get_extension(self):
        """Get the auto attendant extension number"""
        return self.extension
    
    def start_session(self, call_id, from_extension):
        """
        Start an auto attendant session for a call
        
        Args:
            call_id: Call identifier
            from_extension: Calling extension
            
        Returns:
            dict: Initial action with audio file to play
        """
        self.logger.info(f"Starting auto attendant session for call {call_id} from {from_extension}")
        
        # Initialize session state - start in MAIN_MENU to accept DTMF input
        session = {
            'state': AAState.MAIN_MENU,
            'call_id': call_id,
            'from_extension': from_extension,
            'retry_count': 0,
            'last_input_time': time.time()
        }
        
        # Return welcome greeting action
        return {
            'action': 'play',
            'file': self._get_audio_file('welcome'),
            'next_state': AAState.MAIN_MENU,
            'session': session
        }
    
    def handle_dtmf(self, session, digit):
        """
        Handle DTMF input during auto attendant session
        
        Args:
            session: Current session state
            digit: DTMF digit pressed
            
        Returns:
            dict: Action to take (play audio, transfer, etc.)
        """
        current_state = session.get('state')
        self.logger.debug(f"Auto Attendant DTMF: {digit} in state {current_state}")
        
        # Update input time
        session['last_input_time'] = time.time()
        
        if current_state == AAState.MAIN_MENU:
            return self._handle_menu_input(session, digit)
        
        elif current_state == AAState.INVALID:
            # After invalid input, any key returns to menu
            session['state'] = AAState.MAIN_MENU
            return {
                'action': 'play',
                'file': self._get_audio_file('main_menu'),
                'session': session
            }
        
        # Default: invalid input
        return self._handle_invalid_input(session)
    
    def handle_timeout(self, session):
        """
        Handle timeout (no input received)
        
        Args:
            session: Current session state
            
        Returns:
            dict: Action to take
        """
        self.logger.warning(f"Auto attendant timeout for call {session.get('call_id')}")
        
        session['retry_count'] += 1
        
        if session['retry_count'] >= self.max_retries:
            # Too many retries, transfer to operator or disconnect
            session['state'] = AAState.ENDED
            operator_ext = self.config.get('auto_attendant.operator_extension', '1001')
            
            return {
                'action': 'transfer',
                'destination': operator_ext,
                'reason': 'timeout',
                'session': session
            }
        
        # Play timeout message and return to menu
        session['state'] = AAState.MAIN_MENU
        return {
            'action': 'play',
            'file': self._get_audio_file('timeout'),
            'session': session
        }
    
    def _handle_menu_input(self, session, digit):
        """
        Handle menu input
        
        Args:
            session: Current session
            digit: DTMF digit
            
        Returns:
            dict: Action to take
        """
        if digit in self.menu_options:
            option = self.menu_options[digit]
            destination = option['destination']
            
            self.logger.info(f"Auto attendant: transferring to {destination}")
            session['state'] = AAState.TRANSFERRING
            
            return {
                'action': 'transfer',
                'destination': destination,
                'session': session
            }
        
        # Invalid option
        return self._handle_invalid_input(session)
    
    def _handle_invalid_input(self, session):
        """
        Handle invalid input
        
        Args:
            session: Current session
            
        Returns:
            dict: Action to play invalid message
        """
        session['retry_count'] += 1
        
        if session['retry_count'] >= self.max_retries:
            # Too many invalid attempts
            session['state'] = AAState.ENDED
            operator_ext = self.config.get('auto_attendant.operator_extension', '1001')
            
            return {
                'action': 'transfer',
                'destination': operator_ext,
                'reason': 'invalid_input',
                'session': session
            }
        
        session['state'] = AAState.INVALID
        return {
            'action': 'play',
            'file': self._get_audio_file('invalid'),
            'session': session
        }
    
    def _get_audio_file(self, prompt_type):
        """
        Get path to audio file for prompt
        
        Args:
            prompt_type: Type of prompt (welcome, main_menu, invalid, etc.)
            
        Returns:
            str: Path to audio file, or None if not found
        """
        # Try to find recorded audio file first
        wav_file = os.path.join(self.audio_path, f"{prompt_type}.wav")
        if os.path.exists(wav_file):
            return wav_file
        
        # If no recorded file, we'll generate tone-based prompt
        # This will be handled by the audio utils
        self.logger.debug(f"No audio file found for {prompt_type}, will use generated prompt")
        return None
    
    def get_menu_text(self):
        """
        Get text description of menu options
        
        Returns:
            str: Text description of menu
        """
        lines = ["Auto Attendant Menu:"]
        for digit, option in sorted(self.menu_options.items()):
            lines.append(f"  Press {digit}: {option['description']}")
        return "\n".join(lines)
    
    def end_session(self, session):
        """
        End auto attendant session
        
        Args:
            session: Session to end
        """
        call_id = session.get('call_id')
        self.logger.info(f"Ending auto attendant session for call {call_id}")
        session['state'] = AAState.ENDED


def generate_auto_attendant_prompts(output_dir='auto_attendant'):
    """
    Generate tone-based audio prompts for auto attendant
    
    This creates basic tone sequences for each prompt type.
    In production, these should be replaced with professionally recorded prompts.
    
    Args:
        output_dir: Directory to save audio files
    """
    from pbx.utils.audio import generate_voice_prompt, build_wav_header
    import struct
    import math
    
    logger = get_logger()
    
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory: {output_dir}")
    
    # Define prompts to generate
    prompts = {
        'welcome': 'auto_attendant_welcome',
        'main_menu': 'auto_attendant_menu',
        'invalid': 'invalid_option',
        'timeout': 'timeout',
        'transferring': 'transferring'
    }
    
    for prompt_name, prompt_type in prompts.items():
        output_file = os.path.join(output_dir, f"{prompt_name}.wav")
        
        try:
            # Generate the prompt
            wav_data = generate_voice_prompt(prompt_type)
            
            # Write to file
            with open(output_file, 'wb') as f:
                f.write(wav_data)
            
            logger.info(f"Generated {output_file}")
        except Exception as e:
            logger.error(f"Error generating {prompt_name}: {e}")
    
    logger.info(f"Auto attendant prompts generated in {output_dir}")
    logger.info("NOTE: These are tone-based placeholders.")
    logger.info("For production, replace with professionally recorded voice prompts.")
