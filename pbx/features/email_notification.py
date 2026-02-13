"""
Email notification system for voicemail
"""

import os
import smtplib
import threading
import time
from datetime import datetime, timezone
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from pbx.utils.logger import get_logger


class EmailNotifier:
    """Handles email notifications for voicemail"""

    def __init__(self, config):
        """
        Initialize email notifier

        Args:
            config: Config object
        """
        self.config = config
        self.logger = get_logger()
        self.enabled = config.get("voicemail.email_notifications", False)

        if self.enabled:
            # SMTP settings
            self.smtp_host = config.get("voicemail.smtp.host")
            self.smtp_port = config.get("voicemail.smtp.port", 587)
            self.use_tls = config.get("voicemail.smtp.use_tls", True)
            self.username = config.get("voicemail.smtp.username")
            self.password = config.get("voicemail.smtp.password")

            # Email settings
            self.from_address = config.get("voicemail.email.from_address")
            self.from_name = config.get("voicemail.email.from_name", "PBX Voicemail")
            self.subject_template = config.get(
                "voicemail.email.subject_template", "New Voicemail from {caller_id}"
            )
            self.include_attachment = config.get("voicemail.email.include_attachment", True)
            self.send_immediately = config.get("voicemail.email.send_immediately", True)

            # Reminder settings
            self.reminders_enabled = config.get("voicemail.reminders.enabled", False)
            self.reminder_time = config.get("voicemail.reminders.time", "09:00")
            self.reminders_unread_only = config.get("voicemail.reminders.unread_only", True)

            # Validate required SMTP settings
            if not self.smtp_host or not self.from_address:
                self.logger.warning(
                    "Email notifications enabled but SMTP host or from_address not configured!"
                )
                self.logger.warning("Please configure SMTP settings in .env file or config.yml")
                self.logger.warning("  Required: voicemail.smtp.host, voicemail.email.from_address")
                self.logger.warning(
                    "  Optional: voicemail.smtp.username, voicemail.smtp.password (for authenticated SMTP)"
                )
            else:
                self.logger.info(
                    f"Email notifications enabled - SMTP: {self.smtp_host}:{self.smtp_port}, From: {self.from_address}"
                )

            # Start reminder thread if enabled
            if self.reminders_enabled:
                self._start_reminder_thread()
        else:
            self.logger.info("Email notifications disabled")

    def send_voicemail_notification(
        self, to_email, extension_number, caller_id, timestamp, audio_file_path=None, duration=None
    ):
        """
        Send voicemail notification email

        Args:
            to_email: Recipient email address
            extension_number: Extension that received the voicemail
            caller_id: Caller ID
            timestamp: Timestamp of the voicemail
            audio_file_path: Path to audio file (optional)
            duration: Duration of the message in seconds (optional)

        Returns:
            True if email sent successfully
        """
        if not self.enabled:
            return False

        if not to_email:
            self.logger.warning(
                f"No email address configured for extension {extension_number} - cannot send notification"
            )
            return False

        # Validate SMTP configuration before attempting to send
        if not self.smtp_host or not self.from_address:
            self.logger.warning(
                f"Cannot send email notification - SMTP not properly configured (host: {self.smtp_host}, from: {self.from_address})"
            )
            return False

        self.logger.info(
            f"Attempting to send voicemail notification to {to_email} for extension {extension_number}"
        )

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_address}>"
            msg["To"] = to_email
            msg["Date"] = formatdate(localtime=True)

            # Format subject
            subject = self.subject_template.format(
                caller_id=caller_id,
                timestamp=(
                    timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(timestamp, datetime)
                    else timestamp
                ),
                extension=extension_number,
            )
            msg["Subject"] = subject

            # Create email body
            body = self._create_email_body(extension_number, caller_id, timestamp, duration)
            msg.attach(MIMEText(body, "plain"))

            # Attach audio file if requested and available
            if self.include_attachment and audio_file_path and os.path.exists(audio_file_path):
                try:
                    with open(audio_file_path, "rb") as f:
                        audio_data = f.read()

                    audio = MIMEAudio(audio_data, "wav")
                    audio.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=os.path.basename(audio_file_path),
                    )
                    msg.attach(audio)
                    self.logger.debug(f"Attached audio file: {audio_file_path}")
                except OSError as e:
                    self.logger.error(f"Failed to attach audio file: {e}")

            # Send email
            try:
                self._send_email(msg)
                self.logger.info(f"Sent voicemail notification to {to_email}")
                return True
            except Exception as e:
                self.logger.warning(f"Could not send email notification: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to prepare voicemail notification: {e}")
            return False

    def send_reminder(self, to_email, extension_number, unread_count, messages):
        """
        Send daily reminder about unread voicemails

        Args:
            to_email: Recipient email address
            extension_number: Extension number
            unread_count: Number of unread messages
            messages: list of message dictionaries

        Returns:
            True if email sent successfully
        """
        if not self.enabled or not self.reminders_enabled:
            return False

        if not to_email or unread_count == 0:
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_address}>"
            msg["To"] = to_email
            msg["Date"] = formatdate(localtime=True)
            msg["Subject"] = (
                f"Voicemail Reminder: {unread_count} Unread Message{'s' if unread_count > 1 else ''}"
            )

            # Create body
            body = "Hello,\n\n"
            body += f"You have {unread_count} unread voicemail message{'s' if unread_count > 1 else ''} "
            body += f"in your mailbox (Extension {extension_number}):\n\n"

            for i, msg_info in enumerate(messages, 1):
                caller = msg_info.get("caller_id", "Unknown")
                ts = msg_info.get("timestamp")
                if isinstance(ts, datetime):
                    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    ts_str = str(ts)
                body += f"{i}. From: {caller}, Received: {ts_str}\n"

            body += f"\nPlease check your voicemail by dialing *{extension_number}\n\n"
            body += "Best regards,\n"
            body += f"{self.from_name}"

            msg.attach(MIMEText(body, "plain"))

            # Send email
            self._send_email(msg)
            self.logger.info(f"Sent voicemail reminder to {to_email}")
            return True

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to send voicemail reminder: {e}")
            return False

    def _create_email_body(self, extension_number, caller_id, timestamp, duration=None):
        """
        Create email body text

        Args:
            extension_number: Extension number
            caller_id: Caller ID
            timestamp: Timestamp
            duration: Duration in seconds

        Returns:
            Email body text
        """
        body = "Hello,\n\n"
        body += "You have received a new voicemail message.\n\n"
        body += "Message Details:\n"
        body += f"  Extension: {extension_number}\n"
        body += f"  From: {caller_id}\n"

        if isinstance(timestamp, datetime):
            body += f"  Received: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        else:
            body += f"  Received: {timestamp}\n"

        if duration:
            mins = int(duration // 60)
            secs = int(duration % 60)
            body += f"  Duration: {mins}:{secs:02d}\n"

        body += f"\nTo listen to this message, please dial *{extension_number}\n"
        body += "\nBest regards,\n"
        body += f"{self.from_name}\n"

        return body

    def _send_email(self, msg):
        """
        Send email via SMTP

        Args:
            msg: MIMEMultipart message object
        """
        try:
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)

            # Enable TLS if configured
            if self.use_tls:
                server.starttls()

            # Login if credentials provided
            if self.username and self.password:
                server.login(self.username, self.password)

            # Send email
            server.send_message(msg)
            server.quit()

        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error: {e}")
            raise
        except OSError as e:
            self.logger.error(f"Network error sending email: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            raise

    def _start_reminder_thread(self):
        """Start background thread for daily reminders"""

        def reminder_loop():
            self.logger.info("Started daily reminder thread")
            while self.reminders_enabled:
                try:
                    # Check if it's time to send reminders
                    now = datetime.now(timezone.utc)
                    reminder_hour, reminder_min = map(int, self.reminder_time.split(":"))

                    if now.hour == reminder_hour and now.minute == reminder_min:
                        self.logger.info("Sending daily voicemail reminders")
                        self._send_all_reminders()
                        # Sleep for 61 seconds to avoid sending multiple times
                        # in same minute
                        time.sleep(61)
                    else:
                        # Check every 30 seconds
                        time.sleep(30)
                except Exception as e:
                    self.logger.error(f"Error in reminder thread: {e}")
                    time.sleep(60)

        thread = threading.Thread(target=reminder_loop, daemon=True)
        thread.start()

    def _send_all_reminders(self):
        """
        Send reminders to all extensions with unread voicemails

        Note: This method is a placeholder for integration with VoicemailSystem.
        The actual reminder sending is triggered by VoicemailSystem.send_daily_reminders()
        which iterates through mailboxes and calls send_reminder() for each extension.
        """
        # This is intentionally minimal - the VoicemailSystem class handles
        # the iteration and calls send_reminder() for each extension with
        # unread messages
        self.logger.debug("Reminder time reached - VoicemailSystem will send reminders")
