"""
Emergency Notification System
Provides emergency contact notifications and 911 call alerts
"""

import json
import threading
import time
from datetime import datetime
from email.utils import formatdate

from pbx.utils.logger import get_logger


class EmergencyContact:
    """Represents an emergency contact"""

    def __init__(
        self,
        name: str,
        extension: str = None,
        phone: str = None,
        email: str = None,
        priority: int = 1,
        notification_methods: list[str] = None,
    ):
        """
        Initialize emergency contact

        Args:
            name: Contact name
            extension: Internal extension (optional)
            phone: External phone number (optional)
            email: Email address (optional)
            priority: Priority level (1=highest, 5=lowest)
            notification_methods: list of methods ('call', 'sms', 'email', 'page')
        """
        self.name = name
        self.extension = extension
        self.phone = phone
        self.email = email
        self.priority = priority
        self.notification_methods = notification_methods or ["call"]
        self.id = f"{name.lower().replace(' ', '_')}_{extension or phone}"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "extension": self.extension,
            "phone": self.phone,
            "email": self.email,
            "priority": self.priority,
            "notification_methods": self.notification_methods,
        }


class EmergencyNotificationSystem:
    """
    Emergency notification system for alerting designated contacts
    during emergency situations (911 calls, panic buttons, etc.)
    """

    def __init__(self, pbx_core, config: dict = None, database=None):
        """
        Initialize emergency notification system

        Args:
            pbx_core: Reference to PBX core
            config: Configuration dictionary
            database: Optional database backend
        """
        self.pbx_core = pbx_core
        self.logger = get_logger()
        self.config = config or {}
        self.database = database

        # Emergency contacts list
        self.emergency_contacts = []

        # Emergency notification settings
        self.enabled = self.config.get("features.emergency_notification.enabled", True)
        self.notify_on_911 = self.config.get("features.emergency_notification.notify_on_911", True)
        self.notify_methods = self.config.get(
            "features.emergency_notification.methods", ["call", "page", "email"]
        )
        self.page_priority = self.config.get(
            "features.emergency_notification.page_priority", "emergency"
        )

        # Notification history
        self.notification_history = []
        self.max_history = 1000

        # Thread-safe access
        self.lock = threading.Lock()

        # Pending emergency calls tracking
        self._pending_emergency_calls = []

        # Load emergency contacts
        self._load_emergency_contacts()

        if self.enabled:
            self.logger.info("Emergency notification system initialized")
            self.logger.info(f"Emergency contacts configured: {len(self.emergency_contacts)}")
            self.logger.info(
                f"Notification methods: {', '.join(self.notify_methods)}"
            )
        else:
            self.logger.info("Emergency notification system disabled")

    def _load_emergency_contacts(self):
        """Load emergency contacts from configuration or database"""
        # Load from config
        contacts_config = self.config.get("features.emergency_notification.contacts", [])

        for contact_data in contacts_config:
            contact = EmergencyContact(
                name=contact_data.get("name"),
                extension=contact_data.get("extension"),
                phone=contact_data.get("phone"),
                email=contact_data.get("email"),
                priority=contact_data.get("priority", 1),
                notification_methods=contact_data.get("notification_methods", ["call"]),
            )
            self.emergency_contacts.append(contact)

        # Load from database if available
        if self.database and self.database.enabled:
            self._load_contacts_from_db()

    def _get_db_placeholder(self):
        """Get database-agnostic placeholder for SQL queries"""
        return "?" if self.database.db_type == "sqlite" else "%s"

    def _load_contacts_from_db(self):
        """Load emergency contacts from database"""
        try:
            query = """
                SELECT id, name, extension, phone, email, priority, notification_methods
                FROM emergency_contacts
                WHERE active = true
                ORDER BY priority ASC
            """
            results = self.database.fetch_all(query)

            for row in results:
                methods = (
                    json.loads(row["notification_methods"])
                    if row["notification_methods"]
                    else ["call"]
                )
                contact = EmergencyContact(
                    name=row["name"],
                    extension=row["extension"],
                    phone=row["phone"],
                    email=row["email"],
                    priority=row["priority"],
                    notification_methods=methods,
                )
                # Only add if not already in list from config
                if not any(c.id == contact.id for c in self.emergency_contacts):
                    self.emergency_contacts.append(contact)

            self.logger.info(
                f"Loaded {len(results)} emergency contacts from database"
            )

        except Exception as e:
            self.logger.error(f"Failed to load emergency contacts from database: {e}")

    def add_emergency_contact(
        self,
        name: str,
        extension: str = None,
        phone: str = None,
        email: str = None,
        priority: int = 1,
        notification_methods: list[str] = None,
    ) -> EmergencyContact:
        """
        Add an emergency contact

        Args:
            name: Contact name
            extension: Internal extension
            phone: External phone number
            email: Email address
            priority: Priority level (1=highest)
            notification_methods: Notification methods

        Returns:
            EmergencyContact: The created contact
        """
        with self.lock:
            contact = EmergencyContact(
                name=name,
                extension=extension,
                phone=phone,
                email=email,
                priority=priority,
                notification_methods=notification_methods,
            )

            # Check if contact already exists
            existing = next((c for c in self.emergency_contacts if c.id == contact.id), None)
            if existing:
                # Update existing contact
                self.emergency_contacts.remove(existing)

            self.emergency_contacts.append(contact)

            # Sort by priority
            self.emergency_contacts.sort(key=lambda c: c.priority)

            # Save to database if available
            if self.database and self.database.enabled:
                self._save_contact_to_db(contact)

            self.logger.info(f"Added emergency contact: {name} (priority {priority})")

            return contact

    def _save_contact_to_db(self, contact: EmergencyContact):
        """Save emergency contact to database"""
        try:
            placeholder = self._get_db_placeholder()

            # Check if contact exists (database-agnostic approach)
            check_query = f"SELECT id FROM emergency_contacts WHERE id = {placeholder}"  # nosec B608 - placeholder is safely parameterized
            existing = self.database.fetch_one(check_query, (contact.id,))

            if existing:
                # Update existing contact with database-agnostic placeholders
                if self.database.db_type == "sqlite":
                    query = """
                        UPDATE emergency_contacts
                        SET name = ?, extension = ?, phone = ?,
                            email = ?, priority = ?, notification_methods = ?,
                            active = ?
                        WHERE id = ?
                    """  # nosec B608 - placeholders are safely parameterized, not user-controlled SQL
                else:  # PostgreSQL
                    query = """
                        UPDATE emergency_contacts
                        SET name = %s, extension = %s, phone = %s,
                            email = %s, priority = %s, notification_methods = %s,
                            active = %s
                        WHERE id = %s
                    """  # nosec B608 - placeholders are safely parameterized, not user-controlled SQL
                params = (
                    contact.name,
                    contact.extension,
                    contact.phone,
                    contact.email,
                    contact.priority,
                    json.dumps(contact.notification_methods),
                    True,  # active
                    contact.id,
                )
            else:
                # Insert new contact with database-agnostic placeholders
                if self.database.db_type == "sqlite":
                    query = """
                        INSERT INTO emergency_contacts
                        (id, name, extension, phone, email, priority, notification_methods, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """  # nosec B608 - placeholders are safely parameterized, not user-controlled SQL
                else:  # PostgreSQL
                    query = """
                        INSERT INTO emergency_contacts
                        (id, name, extension, phone, email, priority, notification_methods, active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """  # nosec B608 - placeholders are safely parameterized, not user-controlled SQL
                params = (
                    contact.id,
                    contact.name,
                    contact.extension,
                    contact.phone,
                    contact.email,
                    contact.priority,
                    json.dumps(contact.notification_methods),
                    True,  # active
                )

            self.database.execute(query, params)

        except Exception as e:
            self.logger.error(f"Failed to save contact to database: {e}")

    def remove_emergency_contact(self, contact_id: str) -> bool:
        """
        Remove an emergency contact

        Args:
            contact_id: Contact ID to remove

        Returns:
            bool: True if removed
        """
        with self.lock:
            contact = next((c for c in self.emergency_contacts if c.id == contact_id), None)

            if contact:
                self.emergency_contacts.remove(contact)

                # Remove from database
                if self.database and self.database.enabled:
                    try:
                        placeholder = self._get_db_placeholder()
                        query = f"UPDATE emergency_contacts SET active = false WHERE id = {placeholder}"  # nosec B608 - placeholder is safely parameterized
                        self.database.execute(query, (contact_id,))
                    except Exception as e:
                        self.logger.error(f"Failed to remove contact from database: {e}")

                self.logger.info(f"Removed emergency contact: {contact.name}")
                return True

            return False

    def get_emergency_contacts(self, priority_filter: int = None) -> list[dict]:
        """
        Get list of emergency contacts

        Args:
            priority_filter: Optional priority level to filter

        Returns:
            list of contact dictionaries
        """
        with self.lock:
            contacts = self.emergency_contacts

            if priority_filter is not None:
                contacts = [c for c in contacts if c.priority <= priority_filter]

            return [c.to_dict() for c in contacts]

    def trigger_emergency_notification(self, trigger_type: str, details: dict) -> bool:
        """
        Trigger emergency notifications to all designated contacts

        Args:
            trigger_type: type of emergency ('911_call', 'panic_button', 'manual')
            details: Dictionary with emergency details (caller, location, etc.)

        Returns:
            bool: True if notifications were sent
        """
        if not self.enabled:
            self.logger.warning("Emergency notification system is disabled")
            return False

        with self.lock:
            notification_id = f"emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            self.logger.warning(f"🚨 EMERGENCY NOTIFICATION TRIGGERED: {trigger_type}")
            self.logger.warning(f"Details: {details}")

            # Record notification
            notification_record = {
                "id": notification_id,
                "timestamp": datetime.now().isoformat(),
                "trigger_type": trigger_type,
                "details": details,
                "contacts_notified": [],
                "methods_used": [],
            }

            # Notify all emergency contacts
            for contact in self.emergency_contacts:
                self._notify_contact(contact, trigger_type, details, notification_record)

            # Add to history
            self.notification_history.append(notification_record)
            if len(self.notification_history) > self.max_history:
                self.notification_history.pop(0)

            # Save to database
            if self.database and self.database.enabled:
                self._save_notification_to_db(notification_record)

            self.logger.info(f"Emergency notification {notification_id} completed")

            return True

    def _notify_contact(
        self, contact: EmergencyContact, trigger_type: str, details: dict, notification_record: dict
    ):
        """
        Notify a specific contact using configured methods

        Args:
            contact: Emergency contact
            trigger_type: type of emergency
            details: Emergency details
            notification_record: Notification record to update
        """
        self.logger.info(f"Notifying emergency contact: {contact.name}")

        # Call notification
        if "call" in contact.notification_methods and contact.extension:
            self._send_call_notification(contact, trigger_type, details)
            notification_record["contacts_notified"].append(contact.name)
            if "call" not in notification_record["methods_used"]:
                notification_record["methods_used"].append("call")

        # Page notification (via paging system)
        if "page" in contact.notification_methods and "page" in self.notify_methods:
            self._send_page_notification(contact, trigger_type, details)
            if "page" not in notification_record["methods_used"]:
                notification_record["methods_used"].append("page")

        # Email notification
        if "email" in contact.notification_methods and contact.email:
            self._send_email_notification(contact, trigger_type, details)
            if "email" not in notification_record["methods_used"]:
                notification_record["methods_used"].append("email")

        # SMS notification (if configured)
        if "sms" in contact.notification_methods and contact.phone:
            self._send_sms_notification(contact, trigger_type, details)
            if "sms" not in notification_record["methods_used"]:
                notification_record["methods_used"].append("sms")

    def _send_call_notification(self, contact: EmergencyContact, trigger_type: str, details: dict):
        """Send call notification to contact"""
        if not contact.extension:
            self.logger.warning(f"Cannot call {contact.name}: no extension configured")
            return

        try:
            # Check if PBX core has call initiation capability
            if hasattr(self.pbx_core, "initiate_call"):
                # Initiate call to contact's extension
                self.logger.info(
                    f"Initiating emergency call to {contact.name} at extension {contact.extension}"
                )

                # Create emergency notification call
                call_id = f"emergency-{trigger_type}-{int(time.time())}"

                # In a full implementation, this would:
                # 1. Place a call to the contact's extension
                # 2. Play a pre-recorded emergency message
                # 3. Transfer to emergency responder if needed

                # For now, log the action
                self.logger.warning(
                    f"📞 Emergency call queued: {contact.name} ({contact.extension})"
                )

                # Store notification for tracking
                if hasattr(self, "_pending_emergency_calls"):
                    self._pending_emergency_calls.append(
                        {
                            "contact": contact,
                            "trigger_type": trigger_type,
                            "details": details,
                            "timestamp": datetime.now(),
                            "call_id": call_id,
                        }
                    )
            else:
                self.logger.info(f"Would call {contact.name} at extension {contact.extension}")
                self.logger.info("Call initiation not available - logging notification only")
        except Exception as e:
            self.logger.error(f"Error initiating emergency call: {e}")

    def _send_page_notification(self, contact: EmergencyContact, trigger_type: str, details: dict):
        """Send overhead page notification"""
        if hasattr(self.pbx_core, "paging_system") and self.pbx_core.paging_system.enabled:
            # Use all-call paging for emergencies
            self.logger.warning(f"🔊 Emergency page triggered: {trigger_type}")
            # In full implementation, would trigger actual overhead paging

    def _send_email_notification(self, contact: EmergencyContact, trigger_type: str, details: dict):
        """Send email notification"""
        if not contact.email:
            self.logger.warning(f"Cannot email {contact.name}: no email configured")
            return

        try:
            # Check if email notification system is available
            if hasattr(self.pbx_core, "email_notifier") and self.pbx_core.email_notifier:
                email_notifier = self.pbx_core.email_notifier

                if not email_notifier.enabled:
                    self.logger.warning("Email notification system is disabled")
                    return

                # Build emergency email
                subject = f"🚨 EMERGENCY ALERT: {trigger_type}"

                # Build email body
                body = """EMERGENCY NOTIFICATION

type: {trigger_type}
Time: {details.get('timestamp', datetime.now())}
Contact: {contact.name}
Priority: {contact.priority}

Details:
{self._format_email_details(details)}

This is an automated emergency notification from the PBX system.
Please respond immediately.

---
PBX Emergency Notification System
"""

                # Send email using the existing email notifier
                self.logger.info(f"Sending emergency email to {contact.name} at {contact.email}")

                # Use send method if available, otherwise use SMTP directly
                if hasattr(email_notifier, "_send_email"):
                    email_notifier._send_email(to_address=contact.email, subject=subject, body=body)
                else:
                    # Fallback to direct SMTP
                    self._send_email_direct(contact.email, subject, body, email_notifier)

                self.logger.warning(f"📧 Emergency email sent: {contact.name} ({contact.email})")
            else:
                self.logger.info(f"Would email {contact.name} at {contact.email}")
                self.logger.info("Email notification system not available - logging only")
        except Exception as e:
            self.logger.error(f"Error sending emergency email: {e}")

    def _format_email_details(self, details: dict) -> str:
        """Format emergency details for email"""
        lines = []
        for key, value in details.items():
            if key != "timestamp":
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def _send_email_direct(self, to_address, subject, body, email_notifier):
        """Send email directly using SMTP"""
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg["From"] = email_notifier.from_address
        msg["To"] = to_address
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)

        msg.attach(MIMEText(body, "plain"))

        # Connect and send
        if email_notifier.use_tls:
            server = smtplib.SMTP(email_notifier.smtp_host, email_notifier.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(email_notifier.smtp_host, email_notifier.smtp_port)

        if email_notifier.username and email_notifier.password:
            server.login(email_notifier.username, email_notifier.password)

        server.send_message(msg)
        server.quit()

    def _send_sms_notification(self, contact: EmergencyContact, trigger_type: str, details: dict):
        """Send SMS notification"""
        if not contact.phone:
            self.logger.warning(f"Cannot SMS {contact.name}: no phone configured")
            return

        try:
            # Check if SMS gateway is configured in config
            sms_enabled = self.pbx_core.config.get("emergency.sms.enabled", False)

            if sms_enabled:
                sms_provider = self.pbx_core.config.get("emergency.sms.provider", "twilio")

                if sms_provider == "twilio":
                    self._send_sms_twilio(contact, trigger_type, details)
                elif sms_provider == "aws_sns":
                    self._send_sms_aws(contact, trigger_type, details)
                else:
                    self.logger.warning(f"Unsupported SMS provider: {sms_provider}")
                    self.logger.info(f"Would send SMS to {contact.name} at {contact.phone}")
            else:
                self.logger.info(f"Would send SMS to {contact.name} at {contact.phone}")
                self.logger.info(
                    "SMS gateway not configured - set emergency.sms.enabled = true in config"
                )
        except Exception as e:
            self.logger.error(f"Error sending emergency SMS: {e}")

    def _send_sms_twilio(self, contact: EmergencyContact, trigger_type: str, details: dict):
        """Send SMS via Twilio"""
        try:
            # Check if Twilio is available
            try:
                from twilio.rest import Client
            except ImportError:
                self.logger.warning(
                    "Twilio library not installed. Install with: pip install twilio"
                )
                return

            # Get Twilio credentials from config
            account_sid = self.pbx_core.config.get("emergency.sms.twilio.account_sid")
            auth_token = self.pbx_core.config.get("emergency.sms.twilio.auth_token")
            from_number = self.pbx_core.config.get("emergency.sms.twilio.from_number")

            if not all([account_sid, auth_token, from_number]):
                self.logger.warning("Twilio credentials not configured")
                return

            # Create Twilio client
            client = Client(account_sid, auth_token)

            # Build SMS message
            message_body = f"🚨 EMERGENCY: {trigger_type}\n"
            message_body += f"Time: {details.get('timestamp', datetime.now())}\n"
            message_body += f"Contact: {contact.name}\n"
            message_body += "Respond immediately."

            # Send SMS
            message = client.messages.create(body=message_body, from_=from_number, to=contact.phone)

            self.logger.warning(
                f"📱 Emergency SMS sent: {contact.name} ({contact.phone}) - SID: {message.sid}"
            )
        except Exception as e:
            self.logger.error(f"Error sending Twilio SMS: {e}")

    def _send_sms_aws(self, contact: EmergencyContact, trigger_type: str, details: dict):
        """Send SMS via AWS SNS"""
        try:
            # Check if boto3 is available
            try:
                import boto3
            except ImportError:
                self.logger.warning("boto3 library not installed. Install with: pip install boto3")
                return

            # Get AWS credentials from config
            aws_region = self.pbx_core.config.get("emergency.sms.aws.region", "us-east-1")

            # Create SNS client
            sns = boto3.client("sns", region_name=aws_region)

            # Build SMS message
            message_body = f"🚨 EMERGENCY: {trigger_type}\n"
            message_body += f"Time: {details.get('timestamp', datetime.now())}\n"
            message_body += f"Contact: {contact.name}\n"
            message_body += "Respond immediately."

            # Send SMS
            response = sns.publish(
                PhoneNumber=contact.phone,
                Message=message_body,
                MessageAttributes={
                    "AWS.SNS.SMS.SMSType": {
                        "DataType": "String",
                        "StringValue": "Transactional",  # High priority
                    }
                },
            )

            self.logger.warning(
                f"📱 Emergency SMS sent: {contact.name} ({contact.phone}) - MessageId: {response['MessageId']}"
            )
        except Exception as e:
            self.logger.error(f"Error sending AWS SNS SMS: {e}")

    def _save_notification_to_db(self, notification_record: dict):
        """Save notification record to database"""
        try:
            # Insert notification record with database-agnostic placeholders
            if self.database.db_type == "sqlite":
                query = """
                    INSERT INTO emergency_notifications
                    (id, timestamp, trigger_type, details, contacts_notified, methods_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                """  # nosec B608 - placeholders are safely parameterized
            else:  # PostgreSQL
                query = """
                    INSERT INTO emergency_notifications
                    (id, timestamp, trigger_type, details, contacts_notified, methods_used)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """  # nosec B608 - placeholders are safely parameterized

            self.database.execute(
                query,
                (
                    notification_record["id"],
                    notification_record["timestamp"],
                    notification_record["trigger_type"],
                    json.dumps(notification_record["details"]),
                    json.dumps(notification_record["contacts_notified"]),
                    json.dumps(notification_record["methods_used"]),
                ),
            )

        except Exception as e:
            self.logger.error(f"Failed to save notification to database: {e}")

    def get_notification_history(self, limit: int = 50) -> list[dict]:
        """
        Get notification history

        Args:
            limit: Maximum number of records to return

        Returns:
            list of notification records
        """
        with self.lock:
            return self.notification_history[-limit:]

    def on_911_call(self, caller_extension: str, caller_name: str, location: str = None):
        """
        Handle 911 call detection

        Args:
            caller_extension: Extension making 911 call
            caller_name: Name of caller
            location: Location information if available
        """
        if not self.notify_on_911:
            return

        self.logger.warning(f"🚨 911 CALL DETECTED from {caller_extension} ({caller_name})")

        details = {
            "caller_extension": caller_extension,
            "caller_name": caller_name,
            "location": location or "Unknown",
            "timestamp": datetime.now().isoformat(),
        }

        # Trigger emergency notifications
        self.trigger_emergency_notification("911_call", details)

    def test_emergency_notification(self) -> dict:
        """
        Test emergency notification system

        Returns:
            Dictionary with test results
        """
        self.logger.info("Testing emergency notification system...")

        details = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "message": "This is a test of the emergency notification system",
        }

        success = self.trigger_emergency_notification("test", details)

        return {
            "success": success,
            "contacts_configured": len(self.emergency_contacts),
            "notification_methods": self.notify_methods,
            "message": "Emergency notification test completed",
        }
