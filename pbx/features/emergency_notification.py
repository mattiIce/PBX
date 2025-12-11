"""
Emergency Notification System
Provides emergency contact notifications and 911 call alerts
"""
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional

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
            notification_methods: List[str] = None):
        """
        Initialize emergency contact

        Args:
            name: Contact name
            extension: Internal extension (optional)
            phone: External phone number (optional)
            email: Email address (optional)
            priority: Priority level (1=highest, 5=lowest)
            notification_methods: List of methods ('call', 'sms', 'email', 'page')
        """
        self.name = name
        self.extension = extension
        self.phone = phone
        self.email = email
        self.priority = priority
        self.notification_methods = notification_methods or ['call']
        self.id = f"{name.lower().replace(' ', '_')}_{extension or phone}"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'extension': self.extension,
            'phone': self.phone,
            'email': self.email,
            'priority': self.priority,
            'notification_methods': self.notification_methods
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
        self.enabled = self.config.get(
            'features.emergency_notification.enabled', True)
        self.notify_on_911 = self.config.get(
            'features.emergency_notification.notify_on_911', True)
        self.notify_methods = self.config.get(
            'features.emergency_notification.methods', [
                'call', 'page', 'email'])
        self.page_priority = self.config.get(
            'features.emergency_notification.page_priority', 'emergency')

        # Notification history
        self.notification_history = []
        self.max_history = 1000

        # Thread-safe access
        self.lock = threading.Lock()

        # Load emergency contacts
        self._load_emergency_contacts()

        if self.enabled:
            self.logger.info("Emergency notification system initialized")
            self.logger.info(
                f"Emergency contacts configured: {len(self.emergency_contacts)}")
            self.logger.info(
                f"Notification methods: {
                    ', '.join(
                        self.notify_methods)}")
        else:
            self.logger.info("Emergency notification system disabled")

    def _load_emergency_contacts(self):
        """Load emergency contacts from configuration or database"""
        # Load from config
        contacts_config = self.config.get(
            'features.emergency_notification.contacts', [])

        for contact_data in contacts_config:
            contact = EmergencyContact(
                name=contact_data.get('name'),
                extension=contact_data.get('extension'),
                phone=contact_data.get('phone'),
                email=contact_data.get('email'),
                priority=contact_data.get(
                    'priority',
                    1),
                notification_methods=contact_data.get(
                    'notification_methods',
                    ['call']))
            self.emergency_contacts.append(contact)

        # Load from database if available
        if self.database and self.database.enabled:
            self._load_contacts_from_db()

    def _get_db_placeholder(self):
        """Get database-agnostic placeholder for SQL queries"""
        return '?' if self.database.db_type == 'sqlite' else '%s'

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
                methods = json.loads(
                    row['notification_methods']) if row['notification_methods'] else ['call']
                contact = EmergencyContact(
                    name=row['name'],
                    extension=row['extension'],
                    phone=row['phone'],
                    email=row['email'],
                    priority=row['priority'],
                    notification_methods=methods
                )
                # Only add if not already in list from config
                if not any(
                        c.id == contact.id for c in self.emergency_contacts):
                    self.emergency_contacts.append(contact)

            self.logger.info(
                f"Loaded {
                    len(results)} emergency contacts from database")

        except Exception as e:
            self.logger.error(
                f"Failed to load emergency contacts from database: {e}")

    def add_emergency_contact(
            self,
            name: str,
            extension: str = None,
            phone: str = None,
            email: str = None,
            priority: int = 1,
            notification_methods: List[str] = None) -> EmergencyContact:
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
                notification_methods=notification_methods
            )

            # Check if contact already exists
            existing = next(
                (c for c in self.emergency_contacts if c.id == contact.id), None)
            if existing:
                # Update existing contact
                self.emergency_contacts.remove(existing)

            self.emergency_contacts.append(contact)

            # Sort by priority
            self.emergency_contacts.sort(key=lambda c: c.priority)

            # Save to database if available
            if self.database and self.database.enabled:
                self._save_contact_to_db(contact)

            self.logger.info(
                f"Added emergency contact: {name} (priority {priority})")

            return contact

    def _save_contact_to_db(self, contact: EmergencyContact):
        """Save emergency contact to database"""
        try:
            placeholder = self._get_db_placeholder()

            # Check if contact exists (database-agnostic approach)
            check_query = f"SELECT id FROM emergency_contacts WHERE id = {placeholder}"
            existing = self.database.fetch_one(check_query, (contact.id,))

            if existing:
                # Update existing contact - use placeholder list for clarity
                placeholders = ', '.join(
                    [placeholder] * 6)  # 6 fields to update
                query = f"""
                    UPDATE emergency_contacts
                    SET name = {placeholder}, extension = {placeholder}, phone = {placeholder},
                        email = {placeholder}, priority = {placeholder}, notification_methods = {placeholder},
                        active = true
                    WHERE id = {placeholder}
                """
                params = (
                    contact.name,
                    contact.extension,
                    contact.phone,
                    contact.email,
                    contact.priority,
                    json.dumps(contact.notification_methods),
                    contact.id
                )
            else:
                # Insert new contact - use placeholder list for clarity
                placeholders = ', '.join([placeholder] * 7)  # 7 fields
                query = f"""
                    INSERT INTO emergency_contacts
                    (id, name, extension, phone, email, priority, notification_methods, active)
                    VALUES ({placeholders}, true)
                """
                params = (
                    contact.id,
                    contact.name,
                    contact.extension,
                    contact.phone,
                    contact.email,
                    contact.priority,
                    json.dumps(contact.notification_methods)
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
            contact = next(
                (c for c in self.emergency_contacts if c.id == contact_id), None)

            if contact:
                self.emergency_contacts.remove(contact)

                # Remove from database
                if self.database and self.database.enabled:
                    try:
                        placeholder = self._get_db_placeholder()
                        query = f"UPDATE emergency_contacts SET active = false WHERE id = {placeholder}"
                        self.database.execute(query, (contact_id,))
                    except Exception as e:
                        self.logger.error(
                            f"Failed to remove contact from database: {e}")

                self.logger.info(f"Removed emergency contact: {contact.name}")
                return True

            return False

    def get_emergency_contacts(
            self, priority_filter: int = None) -> List[Dict]:
        """
        Get list of emergency contacts

        Args:
            priority_filter: Optional priority level to filter

        Returns:
            List of contact dictionaries
        """
        with self.lock:
            contacts = self.emergency_contacts

            if priority_filter is not None:
                contacts = [
                    c for c in contacts if c.priority <= priority_filter]

            return [c.to_dict() for c in contacts]

    def trigger_emergency_notification(
            self, trigger_type: str, details: Dict) -> bool:
        """
        Trigger emergency notifications to all designated contacts

        Args:
            trigger_type: Type of emergency ('911_call', 'panic_button', 'manual')
            details: Dictionary with emergency details (caller, location, etc.)

        Returns:
            bool: True if notifications were sent
        """
        if not self.enabled:
            self.logger.warning("Emergency notification system is disabled")
            return False

        with self.lock:
            notification_id = f"emergency_{
                datetime.now().strftime('%Y%m%d_%H%M%S')}"

            self.logger.warning(
                f"🚨 EMERGENCY NOTIFICATION TRIGGERED: {trigger_type}")
            self.logger.warning(f"Details: {details}")

            # Record notification
            notification_record = {
                'id': notification_id,
                'timestamp': datetime.now().isoformat(),
                'trigger_type': trigger_type,
                'details': details,
                'contacts_notified': [],
                'methods_used': []
            }

            # Notify all emergency contacts
            for contact in self.emergency_contacts:
                self._notify_contact(
                    contact, trigger_type, details, notification_record)

            # Add to history
            self.notification_history.append(notification_record)
            if len(self.notification_history) > self.max_history:
                self.notification_history.pop(0)

            # Save to database
            if self.database and self.database.enabled:
                self._save_notification_to_db(notification_record)

            self.logger.info(
                f"Emergency notification {notification_id} completed")

            return True

    def _notify_contact(self, contact: EmergencyContact, trigger_type: str,
                        details: Dict, notification_record: Dict):
        """
        Notify a specific contact using configured methods

        Args:
            contact: Emergency contact
            trigger_type: Type of emergency
            details: Emergency details
            notification_record: Notification record to update
        """
        self.logger.info(f"Notifying emergency contact: {contact.name}")

        # Call notification
        if 'call' in contact.notification_methods and contact.extension:
            self._send_call_notification(contact, trigger_type, details)
            notification_record['contacts_notified'].append(contact.name)
            if 'call' not in notification_record['methods_used']:
                notification_record['methods_used'].append('call')

        # Page notification (via paging system)
        if 'page' in contact.notification_methods and 'page' in self.notify_methods:
            self._send_page_notification(contact, trigger_type, details)
            if 'page' not in notification_record['methods_used']:
                notification_record['methods_used'].append('page')

        # Email notification
        if 'email' in contact.notification_methods and contact.email:
            self._send_email_notification(contact, trigger_type, details)
            if 'email' not in notification_record['methods_used']:
                notification_record['methods_used'].append('email')

        # SMS notification (if configured)
        if 'sms' in contact.notification_methods and contact.phone:
            self._send_sms_notification(contact, trigger_type, details)
            if 'sms' not in notification_record['methods_used']:
                notification_record['methods_used'].append('sms')

    def _send_call_notification(
            self,
            contact: EmergencyContact,
            trigger_type: str,
            details: Dict):
        """Send call notification to contact"""
        # TODO: Initiate automated call to contact's extension
        self.logger.info(
            f"Would call {
                contact.name} at extension {
                contact.extension}")
        # In a full implementation, this would:
        # 1. Place a call to the contact's extension
        # 2. Play a pre-recorded emergency message
        # 3. Transfer to emergency responder if needed

    def _send_page_notification(
            self,
            contact: EmergencyContact,
            trigger_type: str,
            details: Dict):
        """Send overhead page notification"""
        if hasattr(
                self.pbx_core,
                'paging_system') and self.pbx_core.paging_system.enabled:
            # Use all-call paging for emergencies
            self.logger.warning(f"🔊 Emergency page triggered: {trigger_type}")
            # In full implementation, would trigger actual overhead paging

    def _send_email_notification(
            self,
            contact: EmergencyContact,
            trigger_type: str,
            details: Dict):
        """Send email notification"""
        self.logger.info(f"Would email {contact.name} at {contact.email}")
        # TODO: Use email notification system to send emergency alert
        # In full implementation, would send email with emergency details

    def _send_sms_notification(
            self,
            contact: EmergencyContact,
            trigger_type: str,
            details: Dict):
        """Send SMS notification"""
        self.logger.info(
            f"Would send SMS to {
                contact.name} at {
                contact.phone}")
        # TODO: Integrate with SMS gateway (Twilio, etc.)
        # In full implementation, would send SMS alert

    def _save_notification_to_db(self, notification_record: Dict):
        """Save notification record to database"""
        try:
            placeholder = self._get_db_placeholder()
            placeholders = ', '.join([placeholder] * 6)  # 6 fields
            query = f"""
                INSERT INTO emergency_notifications
                (id, timestamp, trigger_type, details, contacts_notified, methods_used)
                VALUES ({placeholders})
            """

            self.database.execute(query, (
                notification_record['id'],
                notification_record['timestamp'],
                notification_record['trigger_type'],
                json.dumps(notification_record['details']),
                json.dumps(notification_record['contacts_notified']),
                json.dumps(notification_record['methods_used'])
            ))

        except Exception as e:
            self.logger.error(f"Failed to save notification to database: {e}")

    def get_notification_history(self, limit: int = 50) -> List[Dict]:
        """
        Get notification history

        Args:
            limit: Maximum number of records to return

        Returns:
            List of notification records
        """
        with self.lock:
            return self.notification_history[-limit:]

    def on_911_call(
            self,
            caller_extension: str,
            caller_name: str,
            location: str = None):
        """
        Handle 911 call detection

        Args:
            caller_extension: Extension making 911 call
            caller_name: Name of caller
            location: Location information if available
        """
        if not self.notify_on_911:
            return

        self.logger.warning(
            f"🚨 911 CALL DETECTED from {caller_extension} ({caller_name})")

        details = {
            'caller_extension': caller_extension,
            'caller_name': caller_name,
            'location': location or 'Unknown',
            'timestamp': datetime.now().isoformat()
        }

        # Trigger emergency notifications
        self.trigger_emergency_notification('911_call', details)

    def test_emergency_notification(self) -> Dict:
        """
        Test emergency notification system

        Returns:
            Dictionary with test results
        """
        self.logger.info("Testing emergency notification system...")

        details = {
            'test': True,
            'timestamp': datetime.now().isoformat(),
            'message': 'This is a test of the emergency notification system'
        }

        success = self.trigger_emergency_notification('test', details)

        return {
            'success': success,
            'contacts_configured': len(self.emergency_contacts),
            'notification_methods': self.notify_methods,
            'message': 'Emergency notification test completed'
        }
