"""
Voicemail system
"""
import os
from datetime import datetime
from pbx.utils.logger import get_logger
from pbx.utils.config import Config

try:
    from pbx.features.email_notification import EmailNotifier
    EMAIL_NOTIFIER_AVAILABLE = True
except ImportError:
    EMAIL_NOTIFIER_AVAILABLE = False


class VoicemailBox:
    """Represents a voicemail box for an extension"""

    def __init__(self, extension_number, storage_path="voicemail", config=None, email_notifier=None):
        """
        Initialize voicemail box

        Args:
            extension_number: Extension number
            storage_path: Path to store voicemail files
            config: Config object
            email_notifier: EmailNotifier object
        """
        self.extension_number = extension_number
        self.storage_path = os.path.join(storage_path, extension_number)
        self.messages = []
        self.logger = get_logger()
        self.config = config
        self.email_notifier = email_notifier
        self.pin = None  # Voicemail PIN

        # Load PIN from extension config if available
        if config:
            ext_config = config.get_extension(extension_number)
            if ext_config:
                self.pin = ext_config.get('voicemail_pin')

        # Create storage directory
        os.makedirs(self.storage_path, exist_ok=True)

        # Load existing messages from disk
        self._load_messages()

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
        self.logger.info(f"Saved voicemail for extension {self.extension_number}")

        # Send email notification if enabled
        if self.email_notifier and self.config:
            extension_config = self.config.get_extension(self.extension_number)
            if extension_config:
                email_address = extension_config.get('email')
                if email_address:
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
                # Delete file
                if os.path.exists(msg['file_path']):
                    os.remove(msg['file_path'])

                # Remove from list
                self.messages.pop(i)
                self.logger.info(f"Deleted voicemail {message_id}")
                return True
        return False

    def _load_messages(self):
        """Load existing voicemail messages from disk"""
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
                        timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")

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
                        self.logger.warning(f"Could not parse timestamp from voicemail file: {filename}")

    def set_pin(self, pin):
        """
        Set voicemail PIN

        Args:
            pin: 4-digit PIN string

        Returns:
            True if PIN was set successfully
        """
        if not pin or len(str(pin)) != 4 or not str(pin).isdigit():
            self.logger.warning(f"Invalid PIN format for extension {self.extension_number}")
            return False

        self.pin = str(pin)
        self.logger.info(f"Updated voicemail PIN for extension {self.extension_number}")
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


class VoicemailSystem:
    """Manages voicemail for all extensions"""

    def __init__(self, storage_path="voicemail", config=None):
        """
        Initialize voicemail system

        Args:
            storage_path: Path to store voicemail files
            config: Config object
        """
        self.storage_path = storage_path
        self.mailboxes = {}
        self.logger = get_logger()
        self.config = config

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
                email_notifier=self.email_notifier
            )
        return self.mailboxes[extension_number]

    def save_message(self, extension_number, caller_id, audio_data, duration=None):
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
