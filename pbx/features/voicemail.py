"""
Voicemail system
"""
import os
from datetime import datetime

from pbx.utils.config import Config
from pbx.utils.logger import get_logger

try:
    from pbx.features.email_notification import EmailNotifier
    EMAIL_NOTIFIER_AVAILABLE = True
except ImportError:
    EMAIL_NOTIFIER_AVAILABLE = False

try:
    from pbx.features.voicemail_transcription import VoicemailTranscriptionService
    TRANSCRIPTION_AVAILABLE = True
except ImportError:
    TRANSCRIPTION_AVAILABLE = False


# Constants
GREETING_FILENAME = "greeting.wav"


class VoicemailBox:
    """Represents a voicemail box for an extension"""

    def __init__(
            self,
            extension_number,
            storage_path="voicemail",
            config=None,
            email_notifier=None,
            database=None,
            transcription_service=None):
        """
        Initialize voicemail box

        Args:
            extension_number: Extension number
            storage_path: Path to store voicemail files
            config: Config object
            email_notifier: EmailNotifier object
            database: DatabaseBackend object (optional)
            transcription_service: VoicemailTranscriptionService object (optional)
        """
        self.extension_number = extension_number
        self.storage_path = os.path.join(storage_path, extension_number)
        self.messages = []
        self.logger = get_logger()
        self.config = config
        self.email_notifier = email_notifier
        self.database = database
        self.transcription_service = transcription_service
        self.pin = None  # Voicemail PIN
        self.greeting_path = os.path.join(
            self.storage_path,
            GREETING_FILENAME)  # Custom greeting file

        # Load PIN from extension config if available
        if config:
            ext_config = config.get_extension(extension_number)
            if ext_config:
                self.pin = ext_config.get('voicemail_pin')

        # Create storage directory
        os.makedirs(self.storage_path, exist_ok=True)

        # Load existing messages from disk
        self._load_messages()

    def _get_db_placeholder(self):
        """Get database parameter placeholder based on database type"""
        if self.database and self.database.db_type == 'postgresql':
            return '%s'
        return '?'

    def save_message(self, caller_id, audio_data, duration=None):
        """
        Save voicemail message

        Args:
            caller_id: ID of caller
            audio_data: Audio data bytes
            duration: Duration in seconds (optional)

        Returns:
            Message ID
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        message_id = f"{caller_id}_{timestamp_str}"

        file_path = os.path.join(self.storage_path, f"{message_id}.wav")

        with open(file_path, 'wb') as f:
            f.write(audio_data)

        message = {
            'id': message_id,
            'caller_id': caller_id,
            'timestamp': timestamp,
            'file_path': file_path,
            'listened': False,
            'duration': duration
        }

        self.messages.append(message)
        self.logger.info(
            f"Voicemail saved to file system for extension {
                self.extension_number}")
        self.logger.info(f"  Message ID: {message_id}")
        self.logger.info(f"  Caller ID: {caller_id}")
        self.logger.info(f"  File path: {file_path}")
        self.logger.info(
            f"  Duration: {duration}s" if duration else "  Duration: unknown")

        # Save to database if available
        if self.database and self.database.enabled:
            self.logger.info(f"Saving voicemail metadata to database...")
            try:
                placeholder = self._get_db_placeholder()
                query = f"""
                INSERT INTO voicemail_messages
                (message_id, extension_number, caller_id, file_path, duration, listened, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """

                params = (
                    message_id,
                    self.extension_number,
                    caller_id,
                    file_path,
                    duration,
                    False,
                    timestamp
                )

                self.logger.debug(f"  Database type: {self.database.db_type}")
                self.logger.debug(
                    f"  Executing INSERT query for message_id: {message_id}")

                if self.database.execute(query, params):
                    self.logger.info(
                        f"✓ Voicemail metadata successfully saved to {
                            self.database.db_type} database")
                    self.logger.info(f"  Extension: {self.extension_number}")
                    self.logger.info(f"  Message ID: {message_id}")
                    self.logger.info(f"  Caller: {caller_id}")
                else:
                    self.logger.warning(
                        f"✗ Failed to save voicemail metadata to database for extension {
                            self.extension_number}")
                    self.logger.warning(f"  Message ID: {message_id}")
            except Exception as e:
                self.logger.error(f"✗ Error saving voicemail to database: {e}")
                self.logger.error(f"  Message ID: {message_id}")
                self.logger.error(f"  Extension: {self.extension_number}")
        else:
            self.logger.warning(
                f"Database not available - voicemail metadata NOT saved to database")
            self.logger.warning(
                f"  Message ID: {message_id} stored as file only")

        # Transcribe voicemail if enabled
        transcription_result = None
        if self.transcription_service:
            self.logger.info(f"Transcribing voicemail {message_id}...")
            transcription_result = self.transcription_service.transcribe(
                file_path)

            if transcription_result['success']:
                self.logger.info(f"✓ Voicemail transcribed successfully")
                self.logger.info(
                    f"  Confidence: {
                        transcription_result['confidence']:.2%}")
                self.logger.debug(
                    f"  Text: {transcription_result['text'][:100]}...")

                # Add transcription to message
                message['transcription'] = transcription_result['text']
                message['transcription_confidence'] = transcription_result['confidence']
                message['transcription_language'] = transcription_result['language']
                message['transcription_provider'] = transcription_result['provider']
                message['transcribed_at'] = transcription_result['timestamp']

                # Update database with transcription
                if self.database and self.database.enabled:
                    try:
                        placeholder = self._get_db_placeholder()
                        query = f"""
                        UPDATE voicemail_messages
                        SET transcription_text = {placeholder},
                            transcription_confidence = {placeholder},
                            transcription_language = {placeholder},
                            transcription_provider = {placeholder},
                            transcribed_at = {placeholder}
                        WHERE message_id = {placeholder}
                        """
                        self.database.execute(query, (
                            transcription_result['text'],
                            transcription_result['confidence'],
                            transcription_result['language'],
                            transcription_result['provider'],
                            transcription_result['timestamp'],
                            message_id
                        ))
                        self.logger.info(f"✓ Transcription saved to database")
                    except Exception as e:
                        self.logger.error(
                            f"✗ Error saving transcription to database: {e}")
            else:
                self.logger.warning(
                    f"✗ Voicemail transcription failed: {
                        transcription_result['error']}")

        # Send email notification if enabled
        transcription_text = transcription_result[
            'text'] if transcription_result and transcription_result['success'] else None
        if self.email_notifier and self.config:
            # Get extension configuration - check database first, then config
            # file
            extension_config = None
            email_address = None

            # Try database first if available
            if self.database and self.database.enabled:
                try:
                    from pbx.utils.database import ExtensionDB
                    ext_db = ExtensionDB(self.database)
                    db_extension = ext_db.get(self.extension_number)
                    if db_extension:
                        extension_config = db_extension
                        email_address = db_extension.get('email')
                        self.logger.debug(
                            f"Found email address from database for extension {
                                self.extension_number}")
                except Exception as e:
                    self.logger.error(
                        f"Error getting extension from database: {e}")

            # Fallback to config file if not found in database
            if not extension_config:
                extension_config = self.config.get_extension(
                    self.extension_number)
                if extension_config:
                    email_address = extension_config.get('email')
                    self.logger.debug(
                        f"Found email address from config for extension {
                            self.extension_number}")

            if extension_config and email_address:
                # Check if email notifier supports transcription parameter
                import inspect
                sig = inspect.signature(
                    self.email_notifier.send_voicemail_notification)

                if 'transcription' in sig.parameters:
                    # Email notifier supports transcription
                    self.email_notifier.send_voicemail_notification(
                        to_email=email_address,
                        extension_number=self.extension_number,
                        caller_id=caller_id,
                        timestamp=timestamp,
                        audio_file_path=file_path,
                        duration=duration,
                        transcription=transcription_text
                    )
                else:
                    # Older email notifier without transcription support
                    self.email_notifier.send_voicemail_notification(
                        to_email=email_address,
                        extension_number=self.extension_number,
                        caller_id=caller_id,
                        timestamp=timestamp,
                        audio_file_path=file_path,
                        duration=duration
                    )

        return message_id

    def get_messages(self, unread_only=False):
        """
        Get voicemail messages

        Args:
            unread_only: Only return unread messages

        Returns:
            List of message dictionaries
        """
        if unread_only:
            return [msg for msg in self.messages if not msg['listened']]
        return self.messages

    def mark_listened(self, message_id):
        """
        Mark message as listened

        Args:
            message_id: Message identifier
        """
        for msg in self.messages:
            if msg['id'] == message_id:
                msg['listened'] = True
                self.logger.info(f"Marked voicemail {message_id} as listened")

                # Update database if available
                if self.database and self.database.enabled:
                    self.logger.info(
                        f"Updating voicemail listened status in database...")
                    try:
                        placeholder = self._get_db_placeholder()
                        query = f"""
                        UPDATE voicemail_messages
                        SET listened = {placeholder}
                        WHERE message_id = {placeholder}
                        """
                        self.database.execute(query, (True, message_id))
                        self.logger.info(
                            f"✓ Successfully updated voicemail {message_id} as listened in {
                                self.database.db_type} database")
                    except Exception as e:
                        self.logger.error(
                            f"✗ Error updating voicemail in database: {e}")
                else:
                    self.logger.warning(
                        f"Database not available - listened status not persisted to database")

                break

    def delete_message(self, message_id):
        """
        Delete message

        Args:
            message_id: Message identifier

        Returns:
            True if deleted
        """
        for i, msg in enumerate(self.messages):
            if msg['id'] == message_id:
                self.logger.info(f"Deleting voicemail {message_id}...")

                # Delete file
                if os.path.exists(msg['file_path']):
                    os.remove(msg['file_path'])
                    self.logger.info(
                        f"  ✓ Deleted audio file: {
                            msg['file_path']}")

                # Delete from database if available
                if self.database and self.database.enabled:
                    self.logger.info(f"Deleting voicemail from database...")
                    try:
                        placeholder = self._get_db_placeholder()
                        query = f"""
                        DELETE FROM voicemail_messages
                        WHERE message_id = {placeholder}
                        """
                        self.database.execute(query, (message_id,))
                        self.logger.info(
                            f"  ✓ Successfully deleted voicemail {message_id} from {
                                self.database.db_type} database")
                    except Exception as e:
                        self.logger.error(
                            f"  ✗ Error deleting voicemail from database: {e}")
                else:
                    self.logger.warning(
                        f"  Database not available - only file deleted")

                # Remove from list
                self.messages.pop(i)
                self.logger.info(
                    f"✓ Voicemail {message_id} deleted successfully")
                return True
        return False

    def _load_messages(self):
        """Load existing voicemail messages from database or disk"""
        # Try loading from database first if available
        if self.database and self.database.enabled:
            self.logger.info(
                f"Loading voicemail messages from database for extension {
                    self.extension_number}...")
            try:
                placeholder = self._get_db_placeholder()
                # Build query safely - placeholder is only '%s' or '?' from
                # internal method
                query = """
                SELECT message_id, caller_id, file_path, duration, listened, created_at,
                       transcription_text, transcription_confidence, transcription_language,
                       transcription_provider, transcribed_at
                FROM voicemail_messages
                WHERE extension_number = {}
                ORDER BY created_at DESC
                """.format(placeholder)
                self.logger.debug(
                    f"  Query: SELECT from voicemail_messages WHERE extension_number = {
                        self.extension_number}")
                rows = self.database.fetch_all(query, (self.extension_number,))

                for row in rows:
                    # Convert created_at to datetime if it's a string
                    timestamp = row['created_at']
                    if isinstance(timestamp, str):
                        try:
                            # Try ISO format first (Python 3.7+)
                            if hasattr(datetime, 'fromisoformat'):
                                timestamp = datetime.fromisoformat(timestamp)
                            else:
                                # Fallback for Python < 3.7
                                # Try common timestamp formats
                                for fmt in [
                                        '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
                                    try:
                                        timestamp = datetime.strptime(
                                            timestamp, fmt)
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    # If parsing fails, use current time and
                                    # log warning
                                    self.logger.warning(
                                        f"Could not parse timestamp '{timestamp}' for voicemail {
                                            row['message_id']}, using current time")
                                    timestamp = datetime.now()
                        except ValueError:
                            self.logger.warning(
                                f"Invalid timestamp format for voicemail {
                                    row['message_id']}, using current time")
                            timestamp = datetime.now()

                    message = {
                        'id': row['message_id'],
                        'caller_id': row['caller_id'],
                        'timestamp': timestamp,
                        'file_path': row['file_path'],
                        'listened': bool(row['listened']),
                        'duration': row['duration']
                    }

                    # Add transcription data if available
                    if row.get('transcription_text'):
                        message['transcription'] = row['transcription_text']
                        message['transcription_confidence'] = row.get(
                            'transcription_confidence')
                        message['transcription_language'] = row.get(
                            'transcription_language')
                        message['transcription_provider'] = row.get(
                            'transcription_provider')
                        message['transcribed_at'] = row.get('transcribed_at')

                    self.messages.append(message)
                    self.logger.debug(
                        f"  Loaded message: {
                            row['message_id']} from {
                            row['caller_id']}")

                self.logger.info(
                    f"✓ Successfully loaded {
                        len(
                            self.messages)} voicemail message(s) from {
                        self.database.db_type} database")
                if len(self.messages) > 0:
                    unread_count = sum(
                        1 for m in self.messages if not m['listened'])
                    self.logger.info(
                        f"  Total: {len(self.messages)} messages ({unread_count} unread)")
                return
            except Exception as e:
                self.logger.error(
                    f"✗ Error loading voicemail messages from database: {e}")
                self.logger.warning(
                    f"  Falling back to loading from file system")
                # Fall back to loading from disk
        else:
            self.logger.warning(
                f"Database not available - loading voicemails from file system only")

        # Load from disk if database is not available or failed
        if not os.path.exists(self.storage_path):
            return

        for filename in os.listdir(self.storage_path):
            if filename.endswith('.wav'):
                file_path = os.path.join(self.storage_path, filename)
                # Parse message info from filename: {caller_id}_{timestamp}.wav
                name_without_ext = filename[:-4]
                parts = name_without_ext.split('_')

                if len(parts) >= 3:
                    caller_id = parts[0]
                    date_str = parts[1]
                    time_str = parts[2]

                    try:
                        timestamp = datetime.strptime(
                            f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")

                        message = {
                            'id': name_without_ext,
                            'caller_id': caller_id,
                            'timestamp': timestamp,
                            'file_path': file_path,
                            'listened': False,  # Assume unlistened when loaded
                            'duration': None  # Duration not stored, would need to parse WAV
                        }

                        self.messages.append(message)
                    except ValueError:
                        self.logger.warning(
                            f"Could not parse timestamp from voicemail file: {filename}")

    def set_pin(self, pin):
        """
        Set voicemail PIN

        Args:
            pin: 4-digit PIN string

        Returns:
            True if PIN was set successfully
        """
        if not pin or len(str(pin)) != 4 or not str(pin).isdigit():
            self.logger.warning(
                f"Invalid PIN format for extension {
                    self.extension_number}")
            return False

        self.pin = str(pin)
        self.logger.info(
            f"Updated voicemail PIN for extension {
                self.extension_number}")
        return True

    def verify_pin(self, pin):
        """
        Verify voicemail PIN

        Args:
            pin: PIN to verify

        Returns:
            True if PIN is correct
        """
        return self.pin and str(pin) == str(self.pin)

    def has_custom_greeting(self):
        """
        Check if a custom greeting has been recorded

        Returns:
            True if custom greeting exists
        """
        return os.path.exists(self.greeting_path)

    def save_greeting(self, audio_data):
        """
        Save custom voicemail greeting

        Args:
            audio_data: Audio data bytes (WAV format)

        Returns:
            True if greeting was saved successfully
        """
        try:
            with open(self.greeting_path, 'wb') as f:
                f.write(audio_data)
            self.logger.info(
                f"Saved custom greeting for extension {
                    self.extension_number}")
            return True
        except Exception as e:
            self.logger.error(
                f"Error saving greeting for extension {
                    self.extension_number}: {e}")
            return False

    def get_greeting_path(self):
        """
        Get path to custom greeting file

        Returns:
            Path to greeting file if it exists, None otherwise
        """
        if self.has_custom_greeting():
            return self.greeting_path
        return None

    def delete_greeting(self):
        """
        Delete custom greeting

        Returns:
            True if greeting was deleted
        """
        try:
            if os.path.exists(self.greeting_path):
                os.remove(self.greeting_path)
                self.logger.info(
                    f"Deleted custom greeting for extension {
                        self.extension_number}")
                return True
            return False
        except Exception as e:
            self.logger.error(
                f"Error deleting greeting for extension {
                    self.extension_number}: {e}")
            return False


class VoicemailSystem:
    """Manages voicemail for all extensions"""

    def __init__(self, storage_path="voicemail", config=None, database=None):
        """
        Initialize voicemail system

        Args:
            storage_path: Path to store voicemail files
            config: Config object
            database: DatabaseBackend object (optional)
        """
        self.storage_path = storage_path
        self.mailboxes = {}
        self.logger = get_logger()
        self.config = config
        self.database = database

        # Initialize email notifier if config provided
        self.email_notifier = None
        if config and EMAIL_NOTIFIER_AVAILABLE:
            try:
                self.email_notifier = EmailNotifier(config)
            except Exception as e:
                self.logger.error(f"Failed to initialize email notifier: {e}")

        os.makedirs(storage_path, exist_ok=True)

    def get_mailbox(self, extension_number):
        """
        Get or create mailbox for extension

        Args:
            extension_number: Extension number

        Returns:
            VoicemailBox object
        """
        if extension_number not in self.mailboxes:
            self.mailboxes[extension_number] = VoicemailBox(
                extension_number,
                self.storage_path,
                config=self.config,
                email_notifier=self.email_notifier,
                database=self.database
            )
        return self.mailboxes[extension_number]

    def save_message(
            self,
            extension_number,
            caller_id,
            audio_data,
            duration=None):
        """
        Save voicemail message

        Args:
            extension_number: Extension to save message for
            caller_id: Caller ID
            audio_data: Audio data
            duration: Duration in seconds (optional)

        Returns:
            Message ID
        """
        mailbox = self.get_mailbox(extension_number)
        return mailbox.save_message(caller_id, audio_data, duration)

    def send_daily_reminders(self):
        """
        Send daily reminders for unread voicemails

        Returns:
            Number of reminders sent
        """
        if not self.email_notifier or not self.config:
            return 0

        count = 0
        for extension_number, mailbox in self.mailboxes.items():
            unread_messages = mailbox.get_messages(unread_only=True)
            if unread_messages:
                extension_config = self.config.get_extension(extension_number)
                if extension_config:
                    email_address = extension_config.get('email')
                    if email_address:
                        if self.email_notifier.send_reminder(
                            email_address,
                            extension_number,
                            len(unread_messages),
                            unread_messages
                        ):
                            count += 1

        return count

    def get_message_count(self, extension_number, unread_only=True):
        """
        Get message count for extension

        Args:
            extension_number: Extension number
            unread_only: Only count unread messages

        Returns:
            Message count
        """
        mailbox = self.get_mailbox(extension_number)
        return len(mailbox.get_messages(unread_only))


class VoicemailIVR:
    """
    Interactive Voice Response system for voicemail access
    Handles DTMF-based menu navigation
    """

    # IVR States
    STATE_WELCOME = 'welcome'
    STATE_PIN_ENTRY = 'pin_entry'
    STATE_MAIN_MENU = 'main_menu'
    STATE_PLAYING_MESSAGE = 'playing_message'
    STATE_MESSAGE_MENU = 'message_menu'
    STATE_OPTIONS_MENU = 'options_menu'
    STATE_RECORDING_GREETING = 'recording_greeting'
    STATE_GREETING_REVIEW = 'greeting_review'
    STATE_GOODBYE = 'goodbye'

    def __init__(
            self,
            voicemail_system: VoicemailSystem,
            extension_number: str):
        """
        Initialize voicemail IVR for an extension

        Args:
            voicemail_system: VoicemailSystem instance
            extension_number: Extension accessing voicemail
        """
        self.voicemail_system = voicemail_system
        self.extension_number = extension_number
        self.mailbox = voicemail_system.get_mailbox(extension_number)
        self.logger = get_logger()

        # IVR state
        self.state = self.STATE_WELCOME
        self.pin_attempts = 0
        self.max_pin_attempts = 3
        self.current_message_index = 0
        self.current_messages = []
        self.entered_pin = ''  # Collect PIN digits from user
        self.recorded_greeting_data = None  # Temporary storage for recorded greeting

        self.logger.info(
            f"Voicemail IVR initialized for extension {extension_number}")

    def handle_dtmf(self, digit: str) -> dict:
        """
        Handle DTMF digit based on current state

        Args:
            digit: DTMF digit ('0'-'9', '*', '#')

        Returns:
            dict: Action to take {'action': str, 'prompt': str, ...}
        """
        self.logger.debug(f"IVR state={self.state}, digit={digit}")

        if self.state == self.STATE_WELCOME:
            return self._handle_welcome(digit)
        elif self.state == self.STATE_PIN_ENTRY:
            return self._handle_pin_entry(digit)
        elif self.state == self.STATE_MAIN_MENU:
            return self._handle_main_menu(digit)
        elif self.state == self.STATE_PLAYING_MESSAGE:
            return self._handle_playing_message(digit)
        elif self.state == self.STATE_MESSAGE_MENU:
            return self._handle_message_menu(digit)
        elif self.state == self.STATE_OPTIONS_MENU:
            return self._handle_options_menu(digit)
        elif self.state == self.STATE_RECORDING_GREETING:
            return self._handle_recording_greeting(digit)
        elif self.state == self.STATE_GREETING_REVIEW:
            return self._handle_greeting_review(digit)
        else:
            return {'action': 'unknown_state', 'prompt': 'goodbye'}

    def _handle_welcome(self, digit: str) -> dict:
        """Handle welcome state"""
        # Transition to PIN entry automatically
        self.state = self.STATE_PIN_ENTRY
        
        # If the digit is a valid PIN digit (0-9), process it immediately
        # to avoid losing the first digit
        # Note: We use explicit string check instead of isdigit() for consistency
        # with _handle_pin_entry and to avoid accepting unicode digits
        if digit in '0123456789':
            return self._handle_pin_entry(digit)
        
        # Otherwise, just prompt for PIN entry (handles initialization with '*' or other non-digit)
        return {
            'action': 'play_prompt',
            'prompt': 'enter_pin',
            'message': 'Please enter your PIN followed by pound'
        }

    def _handle_pin_entry(self, digit: str) -> dict:
        """Handle PIN entry state"""
        if digit == '#':
            # PIN entry complete - verify the entered PIN
            self.logger.info(
                f"[VM IVR PIN] # pressed, entered_pin length: {len(self.entered_pin)}")
            self.logger.debug(
                f"[VM IVR PIN] Verifying PIN for extension {self.extension_number}")
            
            pin_valid = self.mailbox.verify_pin(self.entered_pin)
            self.logger.info(
                f"[VM IVR PIN] PIN verification result: {'VALID' if pin_valid else 'INVALID'}")
            
            # Clear PIN immediately after verification for security
            self.entered_pin = ''

            if pin_valid:
                self.state = self.STATE_MAIN_MENU
                unread_count = len(self.mailbox.get_messages(unread_only=True))
                self.logger.info(
                    f"[VM IVR PIN] ✓ PIN accepted, transitioning to main menu")
                return {
                    'action': 'play_prompt',
                    'prompt': 'main_menu',
                    'message': f'You have {unread_count} new messages. Press 1 to listen, 2 for options, * to exit'
                }
            else:
                self.pin_attempts += 1
                self.logger.warning(
                    f"[VM IVR PIN] ✗ Invalid PIN attempt {self.pin_attempts}/{self.max_pin_attempts}")
                if self.pin_attempts >= self.max_pin_attempts:
                    self.state = self.STATE_GOODBYE
                    self.logger.warning(
                        f"[VM IVR PIN] Maximum PIN attempts reached, hanging up")
                    return {
                        'action': 'hangup',
                        'prompt': 'goodbye',
                        'message': 'Too many failed attempts. Goodbye.'
                    }
                return {
                    'action': 'play_prompt',
                    'prompt': 'invalid_pin',
                    'message': 'Invalid PIN. Please try again.'
                }
        elif digit in '0123456789':
            # Collect PIN digit (limit length to prevent abuse)
            if len(self.entered_pin) < 10:  # Max 10 digits
                self.entered_pin += digit
                self.logger.debug(
                    f"[VM IVR PIN] Collected digit, entered_pin length now: {len(self.entered_pin)}")
            return {
                'action': 'collect_digit',
                'prompt': 'continue'
            }
        else:
            # Invalid input, ignore
            self.logger.debug(
                f"[VM IVR PIN] Ignoring invalid digit: {digit}")
            return {
                'action': 'collect_digit',
                'prompt': 'continue'
            }

    def _handle_main_menu(self, digit: str) -> dict:
        """Handle main menu state"""
        if digit == '1':
            # Listen to messages
            self.current_messages = self.mailbox.get_messages(unread_only=True)
            if not self.current_messages:
                self.current_messages = self.mailbox.get_messages(
                    unread_only=False)

            if self.current_messages:
                self.current_message_index = 0
                self.state = self.STATE_PLAYING_MESSAGE
                msg = self.current_messages[0]
                return {
                    'action': 'play_message',
                    'message_id': msg['id'],
                    'file_path': msg['file_path'],
                    'caller_id': msg['caller_id']
                }
            else:
                return {
                    'action': 'play_prompt',
                    'prompt': 'no_messages',
                    'message': 'You have no messages'
                }

        elif digit == '2':
            # Options menu
            self.state = self.STATE_OPTIONS_MENU
            return {
                'action': 'play_prompt',
                'prompt': 'options_menu',
                'message': 'Press 1 to record greeting, * to return to main menu'}

        elif digit == '*':
            # Exit
            self.state = self.STATE_GOODBYE
            return {
                'action': 'hangup',
                'prompt': 'goodbye',
                'message': 'Goodbye'
            }

        return {
            'action': 'play_prompt',
            'prompt': 'invalid_option',
            'message': 'Invalid option. Please try again.'
        }

    def _handle_playing_message(self, digit: str) -> dict:
        """Handle message playback state"""
        # Automatically transition to message menu after playback
        self.state = self.STATE_MESSAGE_MENU
        return {
            'action': 'play_prompt',
            'prompt': 'message_menu',
            'message': 'Press 1 to replay, 2 for next message, 3 to delete, * for main menu'
        }

    def _handle_message_menu(self, digit: str) -> dict:
        """Handle message menu state"""
        if digit == '1':
            # Replay current message
            msg = self.current_messages[self.current_message_index]
            self.state = self.STATE_PLAYING_MESSAGE
            return {
                'action': 'play_message',
                'message_id': msg['id'],
                'file_path': msg['file_path'],
                'caller_id': msg['caller_id']
            }

        elif digit == '2':
            # Next message
            self.current_message_index += 1
            if self.current_message_index < len(self.current_messages):
                msg = self.current_messages[self.current_message_index]
                self.state = self.STATE_PLAYING_MESSAGE
                return {
                    'action': 'play_message',
                    'message_id': msg['id'],
                    'file_path': msg['file_path'],
                    'caller_id': msg['caller_id']
                }
            else:
                self.state = self.STATE_MAIN_MENU
                return {
                    'action': 'play_prompt',
                    'prompt': 'no_more_messages',
                    'message': 'No more messages. Returning to main menu.'
                }

        elif digit == '3':
            # Delete current message
            msg = self.current_messages[self.current_message_index]
            self.mailbox.delete_message(msg['id'])

            # Move to next message or main menu
            if self.current_message_index < len(self.current_messages) - 1:
                self.current_message_index += 1
                msg = self.current_messages[self.current_message_index]
                self.state = self.STATE_PLAYING_MESSAGE
                return {
                    'action': 'play_message',
                    'message_id': msg['id'],
                    'file_path': msg['file_path'],
                    'caller_id': msg['caller_id']
                }
            else:
                self.state = self.STATE_MAIN_MENU
                return {
                    'action': 'play_prompt',
                    'prompt': 'message_deleted',
                    'message': 'Message deleted. Returning to main menu.'
                }

        elif digit == '*':
            # Return to main menu
            self.state = self.STATE_MAIN_MENU
            unread_count = len(self.mailbox.get_messages(unread_only=True))
            return {
                'action': 'play_prompt',
                'prompt': 'main_menu',
                'message': f'You have {unread_count} new messages. Press 1 to listen, 2 for options, * to exit'
            }

        return {
            'action': 'play_prompt',
            'prompt': 'invalid_option',
            'message': 'Invalid option. Please try again.'
        }

    def _handle_options_menu(self, digit: str) -> dict:
        """Handle options menu state"""
        if digit == '1':
            # Record greeting
            self.state = self.STATE_RECORDING_GREETING
            return {
                'action': 'start_recording',
                'recording_type': 'greeting',
                'prompt': 'record_greeting',
                'message': 'Record your greeting after the tone. Press # when finished.'}

        elif digit == '*':
            # Return to main menu
            self.state = self.STATE_MAIN_MENU
            unread_count = len(self.mailbox.get_messages(unread_only=True))
            return {
                'action': 'play_prompt',
                'prompt': 'main_menu',
                'message': f'You have {unread_count} new messages. Press 1 to listen, 2 for options, * to exit'
            }

        return {
            'action': 'play_prompt',
            'prompt': 'invalid_option',
            'message': 'Invalid option. Please try again.'
        }

    def _handle_recording_greeting(self, digit: str) -> dict:
        """Handle recording greeting state"""
        if digit == '#':
            # Finish recording - transition to review state
            self.state = self.STATE_GREETING_REVIEW
            return {
                'action': 'stop_recording',
                'save_as': 'greeting',
                'prompt': 'greeting_review_menu',
                'message': 'Greeting recorded. Press 1 to listen, 2 to re-record, 3 to delete and use default, * to save and return to main menu'
            }

        # During recording, other digits are ignored
        return {
            'action': 'continue_recording',
            'prompt': 'continue'
        }

    def _handle_greeting_review(self, digit: str) -> dict:
        """Handle greeting review state after recording"""
        if digit == '1':
            # Play back the recorded greeting
            return {
                'action': 'play_greeting',
                'prompt': 'greeting_playback',
                'message': 'Playing your greeting...'
            }

        elif digit == '2':
            # Re-record the greeting
            self.recorded_greeting_data = None  # Clear previous recording
            self.state = self.STATE_RECORDING_GREETING
            return {
                'action': 'start_recording',
                'recording_type': 'greeting',
                'prompt': 'record_greeting',
                'message': 'Record your greeting after the tone. Press # when finished.'}

        elif digit == '3':
            # Delete greeting and use default
            self.recorded_greeting_data = None
            if self.mailbox.has_custom_greeting():
                self.mailbox.delete_greeting()
            self.state = self.STATE_MAIN_MENU
            unread_count = len(self.mailbox.get_messages(unread_only=True))
            return {
                'action': 'play_prompt',
                'prompt': 'greeting_deleted',
                'message': f'Custom greeting deleted, using default. You have {unread_count} new messages. Press 1 to listen, 2 for options, * to exit'
            }

        elif digit == '*':
            # Save the greeting and return to main menu
            if self.recorded_greeting_data:
                try:
                    success = self.mailbox.save_greeting(
                        self.recorded_greeting_data)
                    if success:
                        self.recorded_greeting_data = None  # Clear only on successful save
                        self.state = self.STATE_MAIN_MENU
                        unread_count = len(
                            self.mailbox.get_messages(
                                unread_only=True))
                        return {
                            'action': 'play_prompt',
                            'prompt': 'greeting_saved',
                            'message': f'Greeting saved. You have {unread_count} new messages. Press 1 to listen, 2 for options, * to exit'
                        }
                    else:
                        self.logger.error(
                            f"Failed to save greeting for extension {
                                self.extension_number}")
                        return {
                            'action': 'play_prompt',
                            'prompt': 'error',
                            'message': 'Error saving greeting. Press 2 to try again or 3 to cancel.'}
                except Exception as e:
                    self.logger.error(f"Error saving greeting: {e}")
                    return {
                        'action': 'play_prompt',
                        'prompt': 'error',
                        'message': 'Error saving greeting. Press 2 to try again or 3 to cancel.'}
            self.state = self.STATE_MAIN_MENU
            unread_count = len(self.mailbox.get_messages(unread_only=True))
            return {
                'action': 'play_prompt',
                'prompt': 'main_menu',
                'message': f'You have {unread_count} new messages. Press 1 to listen, 2 for options, * to exit'
            }

        return {
            'action': 'play_prompt',
            'prompt': 'invalid_option',
            'message': 'Invalid option. Press 1 to listen, 2 to re-record, 3 to delete, * to save.'
        }

    def save_recorded_greeting(self, audio_data):
        """
        Save the recorded greeting temporarily for review

        Args:
            audio_data: Audio data bytes

        Returns:
            True if greeting was stored successfully
        """
        self.recorded_greeting_data = audio_data
        return True

    def get_recorded_greeting(self):
        """
        Get the temporarily stored greeting for playback

        Returns:
            bytes: Audio data or None
        """
        return self.recorded_greeting_data
