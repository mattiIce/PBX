"""Comprehensive tests for pbx/features/emergency_notification.py"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _patch_logger():
    """Patch the logger used by the emergency_notification module."""
    with patch("pbx.features.emergency_notification.get_logger") as mock_logger_fn:
        mock_logger_fn.return_value = MagicMock()
        yield


@pytest.fixture
def mock_pbx_core():
    """Provide a mock PBX core."""
    pbx = MagicMock()
    pbx.config = MagicMock()
    pbx.config.get.return_value = None
    pbx.email_notifier = None
    pbx.paging_system = MagicMock()
    pbx.paging_system.enabled = False
    return pbx


@pytest.fixture
def mock_database():
    """Provide a mock database backend."""
    db = MagicMock()
    db.enabled = True
    db.db_type = "sqlite"
    db.execute.return_value = True
    db.fetch_all.return_value = []
    db.fetch_one.return_value = None
    return db


@pytest.fixture
def base_config():
    """Provide a base configuration dictionary."""
    config = MagicMock()

    def config_get(key, default=None):
        mapping = {
            "features.emergency_notification.enabled": True,
            "features.emergency_notification.notify_on_911": True,
            "features.emergency_notification.methods": ["call", "page", "email"],
            "features.emergency_notification.page_priority": "emergency",
            "features.emergency_notification.contacts": [
                {
                    "name": "Admin",
                    "extension": "1001",
                    "phone": "+15551234567",
                    "email": "admin@example.com",
                    "priority": 1,
                    "notification_methods": ["call", "email", "sms", "page"],
                },
                {
                    "name": "Manager",
                    "extension": "1002",
                    "email": "manager@example.com",
                    "priority": 2,
                    "notification_methods": ["call", "email"],
                },
            ],
        }
        return mapping.get(key, default)

    config.get.side_effect = config_get
    return config


@pytest.fixture
def ens(mock_pbx_core, base_config):
    """Provide an EmergencyNotificationSystem instance."""
    from pbx.features.emergency_notification import EmergencyNotificationSystem

    return EmergencyNotificationSystem(pbx_core=mock_pbx_core, config=base_config)


# =============================================================================
# EmergencyContact Tests
# =============================================================================


@pytest.mark.unit
class TestEmergencyContact:
    """Tests for EmergencyContact class."""

    def test_init_basic(self) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(name="Admin", extension="1001")
        assert contact.name == "Admin"
        assert contact.extension == "1001"
        assert contact.phone is None
        assert contact.email is None
        assert contact.priority == 1
        assert contact.notification_methods == ["call"]
        assert contact.id == "admin_1001"

    def test_init_with_all_fields(self) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(
            name="John Doe",
            extension="1001",
            phone="+15551234567",
            email="john@example.com",
            priority=2,
            notification_methods=["call", "email", "sms"],
        )
        assert contact.name == "John Doe"
        assert contact.phone == "+15551234567"
        assert contact.email == "john@example.com"
        assert contact.priority == 2
        assert contact.notification_methods == ["call", "email", "sms"]
        assert contact.id == "john_doe_1001"

    def test_init_with_phone_only(self) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(name="External", phone="+15559876543")
        assert contact.id == "external_+15559876543"

    def test_to_dict(self) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(
            name="Admin",
            extension="1001",
            phone="+15551234567",
            email="admin@example.com",
            priority=1,
            notification_methods=["call", "email"],
        )
        d = contact.to_dict()
        assert d["id"] == "admin_1001"
        assert d["name"] == "Admin"
        assert d["extension"] == "1001"
        assert d["phone"] == "+15551234567"
        assert d["email"] == "admin@example.com"
        assert d["priority"] == 1
        assert d["notification_methods"] == ["call", "email"]


# =============================================================================
# EmergencyNotificationSystem Init Tests
# =============================================================================


@pytest.mark.unit
class TestEmergencyNotificationSystemInit:
    """Tests for EmergencyNotificationSystem initialization."""

    def test_init_enabled(self, ens) -> None:
        assert ens.enabled is True
        assert ens.notify_on_911 is True
        assert len(ens.emergency_contacts) == 2
        assert ens.notification_history == []

    def test_init_disabled(self, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyNotificationSystem

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "features.emergency_notification.enabled": False,
            "features.emergency_notification.notify_on_911": False,
            "features.emergency_notification.methods": [],
            "features.emergency_notification.page_priority": "normal",
            "features.emergency_notification.contacts": [],
        }.get(key, default)

        ens = EmergencyNotificationSystem(pbx_core=mock_pbx_core, config=config)
        assert ens.enabled is False

    def test_init_no_config(self, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyNotificationSystem

        ens = EmergencyNotificationSystem(pbx_core=mock_pbx_core, config=None)
        assert ens.enabled is True  # defaults
        assert ens.emergency_contacts == []

    def test_init_with_database_contacts(self, mock_pbx_core, base_config, mock_database) -> None:
        from pbx.features.emergency_notification import EmergencyNotificationSystem

        mock_database.fetch_all.return_value = [
            {
                "id": "db_contact_3001",
                "name": "DB Contact",
                "extension": "3001",
                "phone": None,
                "email": "db@example.com",
                "priority": 3,
                "notification_methods": '["call", "email"]',
            }
        ]

        ens = EmergencyNotificationSystem(
            pbx_core=mock_pbx_core, config=base_config, database=mock_database
        )
        # Should have config contacts + db contact
        assert len(ens.emergency_contacts) >= 3

    def test_init_db_contacts_null_methods(self, mock_pbx_core, base_config, mock_database) -> None:
        from pbx.features.emergency_notification import EmergencyNotificationSystem

        mock_database.fetch_all.return_value = [
            {
                "id": "db_null_3001",
                "name": "DB Null",
                "extension": "3001",
                "phone": None,
                "email": None,
                "priority": 3,
                "notification_methods": None,
            }
        ]

        ens = EmergencyNotificationSystem(
            pbx_core=mock_pbx_core, config=base_config, database=mock_database
        )
        # Contact from db with null methods gets default ["call"]
        db_contact = next((c for c in ens.emergency_contacts if c.name == "DB Null"), None)
        assert db_contact is not None
        assert db_contact.notification_methods == ["call"]

    def test_init_db_contacts_duplicate_not_added(
        self, mock_pbx_core, base_config, mock_database
    ) -> None:
        from pbx.features.emergency_notification import EmergencyNotificationSystem

        # Return a contact with same id as config contact
        mock_database.fetch_all.return_value = [
            {
                "id": "admin_1001",
                "name": "Admin",
                "extension": "1001",
                "phone": None,
                "email": "admin@example.com",
                "priority": 1,
                "notification_methods": '["call"]',
            }
        ]

        ens = EmergencyNotificationSystem(
            pbx_core=mock_pbx_core, config=base_config, database=mock_database
        )
        # Should NOT add duplicate
        assert len(ens.emergency_contacts) == 2

    def test_init_db_load_error(self, mock_pbx_core, base_config, mock_database) -> None:
        from pbx.features.emergency_notification import EmergencyNotificationSystem

        mock_database.fetch_all.side_effect = Exception("db error")

        ens = EmergencyNotificationSystem(
            pbx_core=mock_pbx_core, config=base_config, database=mock_database
        )
        # Should still have config contacts
        assert len(ens.emergency_contacts) == 2


# =============================================================================
# Add/Remove Emergency Contact Tests
# =============================================================================


@pytest.mark.unit
class TestEmergencyContactManagement:
    """Tests for adding and removing contacts."""

    def test_add_emergency_contact(self, ens) -> None:
        contact = ens.add_emergency_contact(
            name="New Contact",
            extension="2001",
            email="new@example.com",
            priority=3,
        )
        assert contact.name == "New Contact"
        assert len(ens.emergency_contacts) == 3

    def test_add_emergency_contact_with_all_fields(self, ens) -> None:
        contact = ens.add_emergency_contact(
            name="Full Contact",
            extension="3001",
            phone="+15559999999",
            email="full@example.com",
            priority=1,
            notification_methods=["call", "email", "sms", "page"],
        )
        assert contact.notification_methods == ["call", "email", "sms", "page"]

    def test_add_emergency_contact_replaces_existing(self, ens) -> None:
        initial_count = len(ens.emergency_contacts)
        ens.add_emergency_contact(
            name="Admin",
            extension="1001",
            email="updated_admin@example.com",
            priority=1,
        )
        assert len(ens.emergency_contacts) == initial_count  # same count

    def test_add_contact_sorts_by_priority(self, ens) -> None:
        ens.add_emergency_contact(name="Priority Zero", extension="9001", priority=0)
        assert ens.emergency_contacts[0].name == "Priority Zero"

    def test_add_contact_saves_to_database(self, ens, mock_database) -> None:
        ens.database = mock_database
        ens.add_emergency_contact(name="DB Contact", extension="4001", priority=2)
        mock_database.execute.assert_called()

    def test_add_contact_db_update_existing(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.fetch_one.return_value = {"id": "existing_4001"}
        ens.add_emergency_contact(name="Existing", extension="4001", priority=2)
        mock_database.execute.assert_called()

    def test_add_contact_db_insert_sqlite(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.db_type = "sqlite"
        mock_database.fetch_one.return_value = None
        ens.add_emergency_contact(name="New DB", extension="5001", priority=3)
        mock_database.execute.assert_called()

    def test_add_contact_db_insert_postgresql(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.db_type = "postgresql"
        mock_database.fetch_one.return_value = None
        ens.add_emergency_contact(name="New PG", extension="5001", priority=3)
        mock_database.execute.assert_called()

    def test_add_contact_db_update_postgresql(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.db_type = "postgresql"
        mock_database.fetch_one.return_value = {"id": "existing_5001"}
        ens.add_emergency_contact(name="Existing PG", extension="5001", priority=2)
        mock_database.execute.assert_called()

    def test_save_contact_db_error(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.execute.side_effect = Exception("db error")
        # Should not raise
        ens.add_emergency_contact(name="Error Contact", extension="6001", priority=3)

    def test_remove_emergency_contact(self, ens) -> None:
        result = ens.remove_emergency_contact("admin_1001")
        assert result is True
        assert len(ens.emergency_contacts) == 1

    def test_remove_nonexistent_contact(self, ens) -> None:
        result = ens.remove_emergency_contact("nonexistent_id")
        assert result is False

    def test_remove_contact_from_database(self, ens, mock_database) -> None:
        ens.database = mock_database
        result = ens.remove_emergency_contact("admin_1001")
        assert result is True
        mock_database.execute.assert_called()

    def test_remove_contact_db_error(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.execute.side_effect = Exception("db error")
        result = ens.remove_emergency_contact("admin_1001")
        assert result is True  # still removed from memory

    def test_get_emergency_contacts(self, ens) -> None:
        contacts = ens.get_emergency_contacts()
        assert len(contacts) == 2
        assert contacts[0]["name"] == "Admin"

    def test_get_emergency_contacts_priority_filter(self, ens) -> None:
        contacts = ens.get_emergency_contacts(priority_filter=1)
        assert len(contacts) == 1
        assert contacts[0]["name"] == "Admin"

    def test_get_emergency_contacts_no_filter(self, ens) -> None:
        contacts = ens.get_emergency_contacts(priority_filter=None)
        assert len(contacts) == 2


# =============================================================================
# Trigger Emergency Notification Tests
# =============================================================================


@pytest.mark.unit
class TestTriggerEmergencyNotification:
    """Tests for trigger_emergency_notification."""

    def test_trigger_notification_disabled(self, ens) -> None:
        ens.enabled = False
        result = ens.trigger_emergency_notification("911_call", {"caller": "1001"})
        assert result is False

    def test_trigger_notification_basic(self, ens) -> None:
        result = ens.trigger_emergency_notification("911_call", {"caller": "1001"})
        assert result is True
        assert len(ens.notification_history) == 1

    def test_trigger_notification_record_structure(self, ens) -> None:
        ens.trigger_emergency_notification("panic_button", {"location": "Building A"})
        record = ens.notification_history[0]
        assert "id" in record
        assert record["trigger_type"] == "panic_button"
        assert "contacts_notified" in record
        assert "methods_used" in record

    def test_trigger_notification_saves_to_db(self, ens, mock_database) -> None:
        ens.database = mock_database
        ens.trigger_emergency_notification("911_call", {"caller": "1001"})
        mock_database.execute.assert_called()

    def test_trigger_notification_db_save_error(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.execute.side_effect = Exception("db error")
        result = ens.trigger_emergency_notification("911_call", {"caller": "1001"})
        assert result is True  # still succeeds in memory

    def test_trigger_notification_db_save_sqlite(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.db_type = "sqlite"
        ens.trigger_emergency_notification("911_call", {"caller": "1001"})
        mock_database.execute.assert_called()

    def test_trigger_notification_db_save_postgresql(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.db_type = "postgresql"
        ens.trigger_emergency_notification("911_call", {"caller": "1001"})
        mock_database.execute.assert_called()

    def test_trigger_notification_history_limit(self, ens) -> None:
        ens.max_history = 3
        for i in range(5):
            ens.trigger_emergency_notification("test", {"iteration": i})
        assert len(ens.notification_history) == 3

    def test_notification_contacts_notified(self, ens) -> None:
        # Admin has call + email + sms + page, Manager has call + email
        ens.trigger_emergency_notification("911_call", {"caller": "1001"})
        record = ens.notification_history[0]
        assert "Admin" in record["contacts_notified"]

    def test_notification_methods_used(self, ens) -> None:
        ens.trigger_emergency_notification("911_call", {"caller": "1001"})
        record = ens.notification_history[0]
        assert "call" in record["methods_used"]


# =============================================================================
# Notification Method Tests
# =============================================================================


@pytest.mark.unit
class TestNotifyContact:
    """Tests for individual notification methods."""

    def test_send_call_notification_with_pbx_core(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.initiate_call = MagicMock()
        contact = EmergencyContact(name="Test", extension="1001", notification_methods=["call"])
        record = {"contacts_notified": [], "methods_used": []}
        ens._notify_contact(contact, "911_call", {"caller": "ext"}, record)
        assert "Test" in record["contacts_notified"]
        assert "call" in record["methods_used"]

    def test_send_call_notification_no_initiate_call(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        del mock_pbx_core.initiate_call
        contact = EmergencyContact(name="Test", extension="1001", notification_methods=["call"])
        record = {"contacts_notified": [], "methods_used": []}
        ens._notify_contact(contact, "911_call", {}, record)
        assert "Test" in record["contacts_notified"]

    def test_send_call_notification_no_extension(self, ens) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(name="NoExt", notification_methods=["call"])
        record = {"contacts_notified": [], "methods_used": []}
        ens._notify_contact(contact, "911_call", {}, record)
        # Should not be added since no extension
        assert "NoExt" not in record["contacts_notified"]

    def test_send_call_notification_error(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.initiate_call = MagicMock(side_effect=TypeError("error"))
        contact = EmergencyContact(name="ErrTest", extension="1001", notification_methods=["call"])
        _record = {"contacts_notified": [], "methods_used": []}
        # _send_call_notification catches error
        ens._send_call_notification(contact, "911_call", {})

    def test_send_page_notification_enabled(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.paging_system.enabled = True
        contact = EmergencyContact(name="Test", extension="1001", notification_methods=["page"])
        record = {"contacts_notified": [], "methods_used": []}
        ens._notify_contact(contact, "911_call", {}, record)
        assert "page" in record["methods_used"]

    def test_send_page_notification_disabled(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.paging_system.enabled = False
        # Remove "page" from ens.notify_methods so the condition in _notify_contact is False
        ens.notify_methods = ["call", "email"]
        contact = EmergencyContact(name="Test", extension="1001", notification_methods=["page"])
        record = {"contacts_notified": [], "methods_used": []}
        ens._notify_contact(contact, "911_call", {}, record)
        # page not added when page not in notify_methods
        assert "page" not in record["methods_used"]

    def test_send_email_notification_with_notifier(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        email_notifier = MagicMock()
        email_notifier.enabled = True
        email_notifier._send_email = MagicMock()
        mock_pbx_core.email_notifier = email_notifier

        contact = EmergencyContact(
            name="Test", email="test@example.com", notification_methods=["email"]
        )
        record = {"contacts_notified": [], "methods_used": []}
        ens._notify_contact(contact, "911_call", {}, record)
        assert "email" in record["methods_used"]
        email_notifier._send_email.assert_called_once()

    def test_send_email_notification_no_email(self, ens) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(name="NoEmail", notification_methods=["email"])
        record = {"contacts_notified": [], "methods_used": []}
        ens._notify_contact(contact, "911_call", {}, record)
        assert "email" not in record["methods_used"]

    def test_send_email_notification_notifier_disabled(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        email_notifier = MagicMock()
        email_notifier.enabled = False
        mock_pbx_core.email_notifier = email_notifier

        contact = EmergencyContact(
            name="Test", email="test@example.com", notification_methods=["email"]
        )
        ens._send_email_notification(contact, "911_call", {})
        # Should not send since disabled

    def test_send_email_notification_no_notifier(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.email_notifier = None
        contact = EmergencyContact(
            name="Test", email="test@example.com", notification_methods=["email"]
        )
        # Should not raise
        ens._send_email_notification(contact, "911_call", {})

    def test_send_email_notification_direct_fallback(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        email_notifier = MagicMock()
        email_notifier.enabled = True
        # Remove _send_email to trigger direct fallback
        del email_notifier._send_email
        email_notifier.from_address = "pbx@example.com"
        email_notifier.use_tls = False
        email_notifier.smtp_host = "localhost"
        email_notifier.smtp_port = 25
        email_notifier.username = None
        email_notifier.password = None
        mock_pbx_core.email_notifier = email_notifier

        contact = EmergencyContact(
            name="Test", email="test@example.com", notification_methods=["email"]
        )
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server
            ens._send_email_notification(contact, "911_call", {})
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()

    def test_send_email_direct_with_tls(self, ens) -> None:
        email_notifier = MagicMock()
        email_notifier.from_address = "pbx@example.com"
        email_notifier.use_tls = True
        email_notifier.smtp_host = "smtp.example.com"
        email_notifier.smtp_port = 587
        email_notifier.username = "user"
        email_notifier.password = "pass"

        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server
            ens._send_email_direct("test@example.com", "Subject", "Body", email_notifier)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user", "pass")
            mock_server.send_message.assert_called_once()

    def test_send_email_direct_no_tls(self, ens) -> None:
        email_notifier = MagicMock()
        email_notifier.from_address = "pbx@example.com"
        email_notifier.use_tls = False
        email_notifier.smtp_host = "localhost"
        email_notifier.smtp_port = 25
        email_notifier.username = None
        email_notifier.password = None

        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server
            ens._send_email_direct("test@example.com", "Subject", "Body", email_notifier)
            mock_server.starttls.assert_not_called()
            mock_server.login.assert_not_called()

    def test_send_email_notification_error(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        email_notifier = MagicMock()
        email_notifier.enabled = True
        email_notifier._send_email = MagicMock(side_effect=TypeError("email error"))
        mock_pbx_core.email_notifier = email_notifier

        contact = EmergencyContact(
            name="Test", email="test@example.com", notification_methods=["email"]
        )
        # Should not raise
        ens._send_email_notification(contact, "911_call", {})

    def test_send_sms_notification_no_phone(self, ens) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(name="NoPhone", notification_methods=["sms"])
        ens._send_sms_notification(contact, "911_call", {})
        # Should just log warning, no error

    def test_send_sms_notification_not_enabled(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.config.get.return_value = False
        contact = EmergencyContact(name="Test", phone="+15551234567", notification_methods=["sms"])
        ens._send_sms_notification(contact, "911_call", {})

    def test_send_sms_notification_twilio(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        def config_get(key, default=None):
            mapping = {
                "emergency.sms.enabled": True,
                "emergency.sms.provider": "twilio",
                "emergency.sms.twilio.account_sid": "test_sid",
                "emergency.sms.twilio.auth_token": "test_token",
                "emergency.sms.twilio.from_number": "+15550001111",
            }
            return mapping.get(key, default)

        mock_pbx_core.config.get.side_effect = config_get

        contact = EmergencyContact(name="Test", phone="+15551234567", notification_methods=["sms"])

        with (
            patch.dict("sys.modules", {"twilio": MagicMock(), "twilio.rest": MagicMock()}),
            patch(
                "pbx.features.emergency_notification.EmergencyNotificationSystem._send_sms_twilio"
            ) as mock_twilio,
        ):
            ens._send_sms_notification(contact, "911_call", {})
            mock_twilio.assert_called_once()

    def test_send_sms_notification_aws(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        def config_get(key, default=None):
            mapping = {
                "emergency.sms.enabled": True,
                "emergency.sms.provider": "aws_sns",
            }
            return mapping.get(key, default)

        mock_pbx_core.config.get.side_effect = config_get

        contact = EmergencyContact(name="Test", phone="+15551234567", notification_methods=["sms"])

        with patch.object(ens, "_send_sms_aws") as mock_aws:
            ens._send_sms_notification(contact, "911_call", {})
            mock_aws.assert_called_once()

    def test_send_sms_notification_unsupported_provider(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        def config_get(key, default=None):
            mapping = {
                "emergency.sms.enabled": True,
                "emergency.sms.provider": "unsupported_provider",
            }
            return mapping.get(key, default)

        mock_pbx_core.config.get.side_effect = config_get

        contact = EmergencyContact(name="Test", phone="+15551234567", notification_methods=["sms"])
        # Should not raise
        ens._send_sms_notification(contact, "911_call", {})

    def test_send_sms_notification_error(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.config.get.side_effect = KeyError("config missing")
        contact = EmergencyContact(name="Test", phone="+15551234567", notification_methods=["sms"])
        # Should catch the error
        ens._send_sms_notification(contact, "911_call", {})

    def test_send_sms_twilio_no_library(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(name="Test", phone="+15551234567")
        with patch.dict("sys.modules", {"twilio": None, "twilio.rest": None}):
            # Should handle ImportError gracefully
            ens._send_sms_twilio(contact, "911_call", {})

    def test_send_sms_twilio_missing_credentials(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.config.get.return_value = None
        contact = EmergencyContact(name="Test", phone="+15551234567")

        with patch.dict("sys.modules", {"twilio": MagicMock(), "twilio.rest": MagicMock()}):
            ens._send_sms_twilio(contact, "911_call", {})

    def test_send_sms_twilio_error(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.config.get.side_effect = TypeError("config err")
        contact = EmergencyContact(name="Test", phone="+15551234567")
        ens._send_sms_twilio(contact, "911_call", {})

    def test_send_sms_aws_no_library(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        contact = EmergencyContact(name="Test", phone="+15551234567")
        with patch.dict("sys.modules", {"boto3": None}):
            ens._send_sms_aws(contact, "911_call", {})

    def test_send_sms_aws_error(self, ens, mock_pbx_core) -> None:
        from pbx.features.emergency_notification import EmergencyContact

        mock_pbx_core.config.get.side_effect = TypeError("config err")
        contact = EmergencyContact(name="Test", phone="+15551234567")
        ens._send_sms_aws(contact, "911_call", {})


# =============================================================================
# Format Email Details Tests
# =============================================================================


@pytest.mark.unit
class TestFormatEmailDetails:
    """Tests for _format_email_details."""

    def test_format_email_details_basic(self, ens) -> None:
        details = {"caller": "1001", "location": "Building A", "timestamp": "2025-01-01"}
        result = ens._format_email_details(details)
        assert "caller: 1001" in result
        assert "location: Building A" in result
        # timestamp key is excluded
        assert "timestamp:" not in result

    def test_format_email_details_empty(self, ens) -> None:
        result = ens._format_email_details({})
        assert result == ""

    def test_format_email_details_only_timestamp(self, ens) -> None:
        result = ens._format_email_details({"timestamp": "2025-01-01"})
        assert result == ""


# =============================================================================
# 911 Call Handler Tests
# =============================================================================


@pytest.mark.unit
class TestOn911Call:
    """Tests for on_911_call handler."""

    def test_on_911_call(self, ens) -> None:
        ens.on_911_call("1001", "John Doe", "Floor 2")
        assert len(ens.notification_history) == 1
        record = ens.notification_history[0]
        assert record["trigger_type"] == "911_call"

    def test_on_911_call_no_location(self, ens) -> None:
        ens.on_911_call("1001", "John Doe")
        record = ens.notification_history[0]
        assert record["details"]["location"] == "Unknown"

    def test_on_911_call_disabled(self, ens) -> None:
        ens.notify_on_911 = False
        ens.on_911_call("1001", "John Doe")
        assert len(ens.notification_history) == 0


# =============================================================================
# Notification History Tests
# =============================================================================


@pytest.mark.unit
class TestNotificationHistory:
    """Tests for notification history retrieval."""

    def test_get_notification_history_empty(self, ens) -> None:
        history = ens.get_notification_history()
        assert history == []

    def test_get_notification_history(self, ens) -> None:
        ens.trigger_emergency_notification("test1", {"data": 1})
        ens.trigger_emergency_notification("test2", {"data": 2})
        history = ens.get_notification_history()
        assert len(history) == 2

    def test_get_notification_history_limit(self, ens) -> None:
        for i in range(5):
            ens.trigger_emergency_notification("test", {"iteration": i})
        history = ens.get_notification_history(limit=2)
        assert len(history) == 2


# =============================================================================
# Test Emergency Notification Tests
# =============================================================================


@pytest.mark.unit
class TestTestEmergencyNotification:
    """Tests for test_emergency_notification method."""

    def test_test_notification(self, ens) -> None:
        result = ens.test_emergency_notification()
        assert result["success"] is True
        assert result["contacts_configured"] == 2
        assert "notification_methods" in result

    def test_test_notification_disabled(self, ens) -> None:
        ens.enabled = False
        result = ens.test_emergency_notification()
        assert result["success"] is False


# =============================================================================
# DB Placeholder Tests
# =============================================================================


@pytest.mark.unit
class TestGetDbPlaceholder:
    """Tests for _get_db_placeholder."""

    def test_sqlite_placeholder(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.db_type = "sqlite"
        assert ens._get_db_placeholder() == "?"

    def test_postgresql_placeholder(self, ens, mock_database) -> None:
        ens.database = mock_database
        mock_database.db_type = "postgresql"
        assert ens._get_db_placeholder() == "%s"
