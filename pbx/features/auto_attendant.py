"""
Auto Attendant (IVR) System for PBX
Provides automated call answering and menu navigation
"""

import os
import sqlite3
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
    - Database persistence for configuration
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

        # Database connection
        self.db_path = config.get("database", {}).get("path", "pbx.db") if config else "pbx.db"
        self._init_database()

        # Get auto attendant configuration - try database first, then config file
        aa_config = config.get("auto_attendant", {}) if config else {}

        # Load from database if available, otherwise use config defaults
        db_config = self._load_config_from_db()
        if db_config:
            self.enabled = db_config.get("enabled", True)
            self.extension = db_config.get("extension", "0")
            self.timeout = db_config.get("timeout", 10)
            self.max_retries = db_config.get("max_retries", 3)
            self.audio_path = db_config.get("audio_path", "auto_attendant")
        else:
            # Use config file defaults and save to database
            self.enabled = aa_config.get("enabled", True)
            self.extension = aa_config.get("extension", "0")
            self.timeout = aa_config.get("timeout", 10)
            self.max_retries = aa_config.get("max_retries", 3)
            self.audio_path = aa_config.get("audio_path", "auto_attendant")
            self._save_config_to_db()

        # Menu options mapping - load from database
        self.menu_options = {}
        self._load_menu_options_from_db()

        # If no menu options in database, load from config and save
        if not self.menu_options:
            menu_items = aa_config.get("menu_options", [])
            for item in menu_items:
                digit = str(item.get("digit"))
                destination = item.get("destination")
                description = item.get("description", "")
                self.menu_options[digit] = {"destination": destination, "description": description}
            # Save to database
            if self.menu_options:
                for digit, option in self.menu_options.items():
                    self._save_menu_option_to_db(
                        digit, option["destination"], option["description"]
                    )

        # Create audio directory if it doesn't exist
        if not os.path.exists(self.audio_path):
            os.makedirs(self.audio_path)
            self.logger.info(
                f"Created auto attendant audio directory: {
                    self.audio_path}"
            )

        self.logger.info(
            f"Auto Attendant initialized on extension {
                self.extension}"
        )
        self.logger.info(f"Menu options: {len(self.menu_options)}")

    def _init_database(self):
        """Initialize database tables for auto attendant persistence"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create auto_attendant_config table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_attendant_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled BOOLEAN DEFAULT 1,
                    extension TEXT DEFAULT '0',
                    timeout INTEGER DEFAULT 10,
                    max_retries INTEGER DEFAULT 3,
                    audio_path TEXT DEFAULT 'auto_attendant',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create auto_attendant_menu_options table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_attendant_menu_options (
                    digit TEXT PRIMARY KEY,
                    destination TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()
            conn.close()
            self.logger.info("Auto attendant database tables initialized")
        except Exception as e:
            self.logger.error(f"Error initializing auto attendant database: {e}")

    def _load_config_from_db(self):
        """Load configuration from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT enabled, extension, timeout, max_retries, audio_path FROM auto_attendant_config WHERE id = 1"
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "enabled": bool(row[0]),
                    "extension": row[1],
                    "timeout": row[2],
                    "max_retries": row[3],
                    "audio_path": row[4],
                }
            return None
        except Exception as e:
            self.logger.error(f"Error loading auto attendant config from database: {e}")
            return None

    def _save_config_to_db(self):
        """Save configuration to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Use INSERT OR REPLACE to handle both insert and update
            cursor.execute(
                """
                INSERT OR REPLACE INTO auto_attendant_config (id, enabled, extension, timeout, max_retries, audio_path, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (self.enabled, self.extension, self.timeout, self.max_retries, self.audio_path),
            )

            conn.commit()
            conn.close()
            self.logger.info("Auto attendant config saved to database")
        except Exception as e:
            self.logger.error(f"Error saving auto attendant config to database: {e}")

    def _load_menu_options_from_db(self):
        """Load menu options from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT digit, destination, description FROM auto_attendant_menu_options"
            )
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                self.menu_options[row[0]] = {"destination": row[1], "description": row[2] or ""}

            if rows:
                self.logger.info(f"Loaded {len(rows)} menu options from database")
        except Exception as e:
            self.logger.error(f"Error loading menu options from database: {e}")

    def _save_menu_option_to_db(self, digit, destination, description=""):
        """Save a menu option to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO auto_attendant_menu_options (digit, destination, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (digit, destination, description),
            )

            conn.commit()
            conn.close()
            self.logger.info(f"Menu option {digit} saved to database")
        except Exception as e:
            self.logger.error(f"Error saving menu option to database: {e}")

    def _delete_menu_option_from_db(self, digit):
        """Delete a menu option from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auto_attendant_menu_options WHERE digit = ?", (digit,))
            conn.commit()
            conn.close()
            self.logger.info(f"Menu option {digit} deleted from database")
        except Exception as e:
            self.logger.error(f"Error deleting menu option from database: {e}")

    def update_config(self, **kwargs):
        """Update configuration and persist to database"""
        if "enabled" in kwargs:
            self.enabled = bool(kwargs["enabled"])
        if "extension" in kwargs:
            self.extension = str(kwargs["extension"])
        if "timeout" in kwargs:
            self.timeout = int(kwargs["timeout"])
        if "max_retries" in kwargs:
            self.max_retries = int(kwargs["max_retries"])
        if "audio_path" in kwargs:
            self.audio_path = str(kwargs["audio_path"])

        # Save to database
        self._save_config_to_db()

    def add_menu_option(self, digit, destination, description=""):
        """Add or update a menu option and persist to database"""
        if not self.enabled:
            self.logger.error(f"Cannot add menu option: Auto attendant feature is not enabled")
            return False

        self.menu_options[digit] = {"destination": destination, "description": description}
        self._save_menu_option_to_db(digit, destination, description)
        return True

    def remove_menu_option(self, digit):
        """Remove a menu option and delete from database"""
        if not self.enabled:
            self.logger.error(f"Cannot remove menu option: Auto attendant feature is not enabled")
            return False

        if digit in self.menu_options:
            del self.menu_options[digit]
            self._delete_menu_option_from_db(digit)
            return True
        return False

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
        self.logger.info(
            f"Starting auto attendant session for call {call_id} from {from_extension}"
        )

        # Initialize session state - start in MAIN_MENU to accept DTMF input
        session = {
            "state": AAState.MAIN_MENU,
            "call_id": call_id,
            "from_extension": from_extension,
            "retry_count": 0,
            "last_input_time": time.time(),
        }

        # Return welcome greeting action
        return {
            "action": "play",
            "file": self._get_audio_file("welcome"),
            "next_state": AAState.MAIN_MENU,
            "session": session,
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
        current_state = session.get("state")
        self.logger.debug(f"Auto Attendant DTMF: {digit} in state {current_state}")

        # Update input time
        session["last_input_time"] = time.time()

        if current_state == AAState.MAIN_MENU:
            return self._handle_menu_input(session, digit)

        elif current_state == AAState.INVALID:
            # After invalid input, any key returns to menu
            session["state"] = AAState.MAIN_MENU
            return {"action": "play", "file": self._get_audio_file("main_menu"), "session": session}

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
        self.logger.warning(
            f"Auto attendant timeout for call {
                session.get('call_id')}"
        )

        session["retry_count"] += 1

        if session["retry_count"] >= self.max_retries:
            # Too many retries, transfer to operator or disconnect
            session["state"] = AAState.ENDED
            operator_ext = self.config.get("auto_attendant.operator_extension", "1001")

            return {
                "action": "transfer",
                "destination": operator_ext,
                "reason": "timeout",
                "session": session,
            }

        # Play timeout message and return to menu
        session["state"] = AAState.MAIN_MENU
        return {"action": "play", "file": self._get_audio_file("timeout"), "session": session}

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
            destination = option["destination"]

            self.logger.info(f"Auto attendant: transferring to {destination}")
            session["state"] = AAState.TRANSFERRING

            return {"action": "transfer", "destination": destination, "session": session}

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
        session["retry_count"] += 1

        if session["retry_count"] >= self.max_retries:
            # Too many invalid attempts
            session["state"] = AAState.ENDED
            operator_ext = self.config.get("auto_attendant.operator_extension", "1001")

            return {
                "action": "transfer",
                "destination": operator_ext,
                "reason": "invalid_input",
                "session": session,
            }

        session["state"] = AAState.INVALID
        return {"action": "play", "file": self._get_audio_file("invalid"), "session": session}

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
        call_id = session.get("call_id")
        self.logger.info(f"Ending auto attendant session for call {call_id}")
        session["state"] = AAState.ENDED


def generate_auto_attendant_prompts(output_dir="auto_attendant"):
    """
    Generate audio prompts for auto attendant

    NOTE: This function generates tone-based prompts as a fallback.
    For REAL VOICE prompts, use: scripts/generate_espeak_voices.py

    Args:
        output_dir: Directory to save audio files
    """
    import math
    import struct

    from pbx.utils.audio import build_wav_header, generate_voice_prompt

    logger = get_logger()

    logger.warning("This function generates TONE prompts (not voice).")
    logger.warning("For REAL VOICE prompts, use: python3 scripts/generate_espeak_voices.py")
    logger.warning("Continuing with tone generation...")

    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory: {output_dir}")

    # Define prompts to generate
    prompts = {
        "welcome": "auto_attendant_welcome",
        "main_menu": "auto_attendant_menu",
        "invalid": "invalid_option",
        "timeout": "timeout",
        "transferring": "transferring",
    }

    for prompt_name, prompt_type in prompts.items():
        output_file = os.path.join(output_dir, f"{prompt_name}.wav")

        try:
            # Generate the prompt
            wav_data = generate_voice_prompt(prompt_type)

            # Write to file
            with open(output_file, "wb") as f:
                f.write(wav_data)

            logger.info(f"Generated {output_file}")
        except Exception as e:
            logger.error(f"Error generating {prompt_name}: {e}")

    logger.info(f"Auto attendant prompts generated in {output_dir}")
    logger.info("NOTE: These are tone-based placeholders (not real voice).")
    logger.info("For REAL VOICE, run: python3 scripts/generate_espeak_voices.py")
