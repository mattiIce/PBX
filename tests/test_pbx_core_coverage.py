"""
Comprehensive tests for pbx/core/pbx.py - PBXCore central coordinator.

Tests all public classes and methods with mocked external dependencies.
"""

import struct
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: build a fully-mocked PBXCore *without* running __init__
# ---------------------------------------------------------------------------
def _make_pbx_core_shell() -> Any:
    """Return a PBXCore instance whose __init__ was completely skipped.

    Every attribute that __init__ would have created is set to a MagicMock
    so that the *methods* under test can be exercised in isolation.
    """
    from pbx.core.pbx import PBXCore

    obj = object.__new__(PBXCore)

    # Logging / config
    obj.logger = MagicMock()
    obj.config = MagicMock()
    obj.quiet_startup = False
    obj.start_time = datetime.now(UTC)

    # Database layer
    obj.database = MagicMock()
    obj.database.enabled = True
    obj.database.db_type = "sqlite"
    obj.registered_phones_db = MagicMock()
    obj.extension_db = MagicMock()

    # Core subsystems
    obj.extension_registry = MagicMock()
    obj.call_manager = MagicMock()
    obj.rtp_relay = MagicMock()
    obj.sip_server = MagicMock()
    obj.api_server = MagicMock()

    # Feature subsystems (set by FeatureInitializer)
    obj.voicemail_system = MagicMock()
    obj.conference_system = MagicMock()
    obj.recording_system = MagicMock()
    obj.queue_system = MagicMock()
    obj.presence_system = MagicMock()
    obj.parking_system = MagicMock()
    obj.cdr_system = MagicMock()
    obj.moh_system = MagicMock()
    obj.trunk_system = MagicMock()
    obj.webhook_system = MagicMock()
    obj.phone_provisioning = MagicMock()
    obj.ad_integration = MagicMock()
    obj.dnd_scheduler = MagicMock()
    obj.qos_monitor = MagicMock()
    obj.phone_book = MagicMock()

    # Handler delegates
    obj._call_router = MagicMock()
    obj._voicemail_handler = MagicMock()
    obj._auto_attendant_handler = MagicMock()
    obj._emergency_handler = MagicMock()
    obj._paging_handler = MagicMock()

    # Security
    obj.security_monitor = MagicMock()

    obj.running = False
    return obj


# =========================================================================
# Tests for PBXCore.__init__
# =========================================================================
@pytest.mark.unit
class TestPBXCoreInit:
    """Tests for PBXCore construction / initialization."""

    @patch("pbx.core.pbx.PagingHandler")
    @patch("pbx.core.pbx.EmergencyHandler")
    @patch("pbx.core.pbx.AutoAttendantHandler")
    @patch("pbx.core.pbx.VoicemailHandler")
    @patch("pbx.core.pbx.CallRouter")
    @patch("pbx.core.pbx.PBXFlaskServer")
    @patch("pbx.core.pbx.FeatureInitializer")
    @patch("pbx.core.pbx.SIPServer")
    @patch("pbx.core.pbx.RTPRelay")
    @patch("pbx.core.pbx.CallManager")
    @patch("pbx.core.pbx.ExtensionRegistry")
    @patch("pbx.core.pbx.RegisteredPhonesDB")
    @patch("pbx.core.pbx.DatabaseBackend")
    @patch("pbx.core.pbx.get_logger")
    @patch("pbx.core.pbx.PBXLogger")
    @patch("pbx.core.pbx.Config")
    def test_init_with_database_success(
        self,
        mock_config_cls: MagicMock,
        mock_pbx_logger: MagicMock,
        mock_get_logger: MagicMock,
        mock_db_backend: MagicMock,
        mock_reg_phones_db: MagicMock,
        mock_ext_registry: MagicMock,
        mock_call_manager: MagicMock,
        mock_rtp_relay: MagicMock,
        mock_sip_server: MagicMock,
        mock_feature_init: MagicMock,
        mock_flask_server: MagicMock,
        mock_call_router: MagicMock,
        mock_vm_handler: MagicMock,
        mock_aa_handler: MagicMock,
        mock_emergency_handler: MagicMock,
        mock_paging_handler: MagicMock,
    ) -> None:
        """PBXCore initialises all subsystems when database connects."""
        from pbx.core.pbx import PBXCore

        # Setup config mock
        config_inst = MagicMock()
        config_inst.get.return_value = None

        def _cfg(key: str, default: Any = None) -> Any:
            lookup: dict[str, Any] = {
                "logging": {},
                "logging.quiet_startup": False,
                "server.rtp_port_range_start": 10000,
                "server.rtp_port_range_end": 20000,
                "server.sip_host": "0.0.0.0",
                "server.sip_port": 5060,
                "api.host": "0.0.0.0",
                "api.port": 9000,
            }
            return lookup.get(key, default)

        config_inst.get.side_effect = _cfg
        mock_config_cls.return_value = config_inst

        # Database connects successfully
        db_inst = MagicMock()
        db_inst.connect.return_value = True
        db_inst.enabled = True
        db_inst.db_type = "sqlite"
        mock_db_backend.return_value = db_inst

        # Registered phones cleanup
        reg_phones_inst = MagicMock()
        reg_phones_inst.cleanup_incomplete_registrations.return_value = (True, 2)
        mock_reg_phones_db.return_value = reg_phones_inst

        # ExtensionDB mock
        mock_ext_db_inst = MagicMock()
        mock_ext_db_inst.get.return_value = {"number": "0"}  # extensions already exist

        # QoS monitor mock (imported dynamically inside __init__)
        mock_qos_module = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "pbx.features.qos_monitoring": mock_qos_module,
                "pbx.utils.database": MagicMock(
                    ExtensionDB=MagicMock(return_value=mock_ext_db_inst)
                ),
            },
        ), patch("pbx.utils.encryption.get_encryption") as mock_get_enc:
            enc_inst = MagicMock()
            enc_inst.hash_password.return_value = ("hashed", "salt")
            mock_get_enc.return_value = enc_inst

            pbx = PBXCore("test_config.yml")

        # Verify core subsystems were set up
        assert pbx.running is False
        mock_config_cls.assert_called_once_with("test_config.yml")
        db_inst.connect.assert_called_once()
        db_inst.create_tables.assert_called_once()
        mock_feature_init.initialize.assert_called_once_with(pbx)

    @patch("pbx.core.pbx.PagingHandler")
    @patch("pbx.core.pbx.EmergencyHandler")
    @patch("pbx.core.pbx.AutoAttendantHandler")
    @patch("pbx.core.pbx.VoicemailHandler")
    @patch("pbx.core.pbx.CallRouter")
    @patch("pbx.core.pbx.PBXFlaskServer")
    @patch("pbx.core.pbx.FeatureInitializer")
    @patch("pbx.core.pbx.SIPServer")
    @patch("pbx.core.pbx.RTPRelay")
    @patch("pbx.core.pbx.CallManager")
    @patch("pbx.core.pbx.ExtensionRegistry")
    @patch("pbx.core.pbx.RegisteredPhonesDB")
    @patch("pbx.core.pbx.DatabaseBackend")
    @patch("pbx.core.pbx.get_logger")
    @patch("pbx.core.pbx.PBXLogger")
    @patch("pbx.core.pbx.Config")
    def test_init_without_database(
        self,
        mock_config_cls: MagicMock,
        mock_pbx_logger: MagicMock,
        mock_get_logger: MagicMock,
        mock_db_backend: MagicMock,
        mock_reg_phones_db: MagicMock,
        mock_ext_registry: MagicMock,
        mock_call_manager: MagicMock,
        mock_rtp_relay: MagicMock,
        mock_sip_server: MagicMock,
        mock_feature_init: MagicMock,
        mock_flask_server: MagicMock,
        mock_call_router: MagicMock,
        mock_vm_handler: MagicMock,
        mock_aa_handler: MagicMock,
        mock_emergency_handler: MagicMock,
        mock_paging_handler: MagicMock,
    ) -> None:
        """PBXCore handles database connection failure gracefully."""
        from pbx.core.pbx import PBXCore

        config_inst = MagicMock()

        def _cfg(key: str, default: Any = None) -> Any:
            mapping: dict[str, Any] = {
                "logging": {},
                "logging.quiet_startup": False,
                "server.rtp_port_range_start": 10000,
                "server.rtp_port_range_end": 20000,
                "server.sip_host": "0.0.0.0",
                "server.sip_port": 5060,
                "api.host": "0.0.0.0",
                "api.port": 9000,
            }
            return mapping.get(key, default)

        config_inst.get.side_effect = _cfg
        mock_config_cls.return_value = config_inst

        db_inst = MagicMock()
        db_inst.connect.return_value = False
        db_inst.enabled = False
        mock_db_backend.return_value = db_inst

        with patch.dict(
            "sys.modules",
            {"pbx.features.qos_monitoring": MagicMock()},
        ):
            pbx = PBXCore("test_config.yml")

        assert pbx.registered_phones_db is None
        assert pbx.extension_db is None
        assert pbx.running is False


# =========================================================================
# Tests for _log_startup
# =========================================================================
@pytest.mark.unit
class TestLogStartup:
    """Tests for PBXCore._log_startup."""

    def test_log_startup_normal_info(self) -> None:
        """INFO messages are logged normally when quiet_startup is False."""
        pbx = _make_pbx_core_shell()
        pbx.quiet_startup = False
        pbx._log_startup("hello")
        pbx.logger.info.assert_called_once_with("hello")

    def test_log_startup_quiet_info_becomes_debug(self) -> None:
        """INFO messages become DEBUG when quiet_startup is True."""
        pbx = _make_pbx_core_shell()
        pbx.quiet_startup = True
        pbx._log_startup("hello")
        pbx.logger.debug.assert_called_once_with("[STARTUP] hello")
        pbx.logger.info.assert_not_called()

    def test_log_startup_warning_not_suppressed(self) -> None:
        """WARNING messages are never suppressed by quiet_startup."""
        pbx = _make_pbx_core_shell()
        pbx.quiet_startup = True
        pbx._log_startup("danger", level="warning")
        pbx.logger.warning.assert_called_once_with("danger")

    def test_log_startup_error_level(self) -> None:
        """ERROR level messages are logged directly."""
        pbx = _make_pbx_core_shell()
        pbx._log_startup("boom", level="error")
        pbx.logger.error.assert_called_once_with("boom")


# =========================================================================
# Tests for _auto_seed_critical_extensions
# =========================================================================
@pytest.mark.unit
class TestAutoSeedCriticalExtensions:
    """Tests for PBXCore._auto_seed_critical_extensions."""

    def test_no_extension_db_returns_early(self) -> None:
        """If extension_db is None, method returns immediately."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db = None
        pbx._auto_seed_critical_extensions()
        # No logger calls for seeding
        pbx.logger.info.assert_not_called()

    @patch("pbx.utils.encryption.get_encryption")
    def test_seed_skips_existing_extensions(self, mock_get_enc: MagicMock) -> None:
        """Extensions that already exist are not re-seeded."""
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = False

        # extension_db.get returns a truthy value (extension exists)
        pbx.extension_db.get.return_value = {"number": "0", "name": "Existing"}

        pbx._auto_seed_critical_extensions()

        # add should never have been called
        pbx.extension_db.add.assert_not_called()

    @patch("pbx.utils.encryption.get_encryption")
    def test_seed_creates_missing_extensions(self, mock_get_enc: MagicMock) -> None:
        """Missing critical extensions are created in the database."""
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = False

        enc_inst = MagicMock()
        enc_inst.hash_password.return_value = ("hashed_pw", "salt")
        mock_get_enc.return_value = enc_inst

        # First call (ext "0") -> not found; second call (ext "1001") -> not found
        pbx.extension_db.get.return_value = None
        pbx.extension_db.add.return_value = True

        pbx._auto_seed_critical_extensions()

        # add was called twice (for "0" and "1001")
        assert pbx.extension_db.add.call_count == 2

    @patch("pbx.utils.encryption.get_encryption")
    def test_seed_handles_add_failure(self, mock_get_enc: MagicMock) -> None:
        """When encryption.hash_password raises, the error is logged."""
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = False

        enc_inst = MagicMock()
        enc_inst.hash_password.side_effect = ValueError("bad password")
        mock_get_enc.return_value = enc_inst

        pbx.extension_db.get.return_value = None

        pbx._auto_seed_critical_extensions()

        # Errors should have been logged
        assert pbx.logger.error.call_count >= 1


# =========================================================================
# Tests for _load_provisioning_devices
# =========================================================================
@pytest.mark.unit
class TestLoadProvisioningDevices:
    """Tests for PBXCore._load_provisioning_devices."""

    def test_no_provisioning_returns_early(self) -> None:
        """Returns immediately if phone_provisioning is None/falsy."""
        pbx = _make_pbx_core_shell()
        pbx.phone_provisioning = None
        pbx._load_provisioning_devices()
        pbx.config.get.assert_not_called()

    def test_loads_valid_devices(self) -> None:
        """Valid device configs are registered with provisioning system."""
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = [
            {"mac": "AA:BB:CC:DD:EE:FF", "extension": "1001", "vendor": "Yealink", "model": "T46S"},
        ]
        pbx._load_provisioning_devices()
        pbx.phone_provisioning.register_device.assert_called_once_with(
            "AA:BB:CC:DD:EE:FF", "1001", "Yealink", "T46S"
        )

    def test_skips_incomplete_devices(self) -> None:
        """Devices missing required fields are silently skipped."""
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = [
            {"mac": "AA:BB:CC:DD:EE:FF", "extension": "1001"},  # missing vendor, model
        ]
        pbx._load_provisioning_devices()
        pbx.phone_provisioning.register_device.assert_not_called()

    def test_handles_registration_exception(self) -> None:
        """Exceptions from register_device are caught and logged."""
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = [
            {"mac": "AA:BB:CC:DD:EE:FF", "extension": "1001", "vendor": "Yealink", "model": "T46S"},
        ]
        pbx.phone_provisioning.register_device.side_effect = RuntimeError("fail")
        pbx._load_provisioning_devices()
        pbx.logger.error.assert_called_once()


# =========================================================================
# Tests for start / stop
# =========================================================================
@pytest.mark.unit
class TestStartStop:
    """Tests for PBXCore.start and PBXCore.stop."""

    def test_start_success(self) -> None:
        """start() returns True when SIP server starts."""
        pbx = _make_pbx_core_shell()
        pbx.security_monitor.enforce_security_requirements.return_value = True
        pbx.sip_server.start.return_value = True
        pbx.api_server.start.return_value = True
        pbx.dnd_scheduler = MagicMock()

        result = pbx.start()

        assert result is True
        assert pbx.running is True
        pbx.sip_server.start.assert_called_once()
        pbx.api_server.start.assert_called_once()
        pbx.trunk_system.register_all.assert_called_once()
        pbx.dnd_scheduler.start.assert_called_once()

    def test_start_security_failure(self) -> None:
        """start() returns False when security enforcement fails."""
        pbx = _make_pbx_core_shell()
        pbx.security_monitor.enforce_security_requirements.return_value = False

        result = pbx.start()

        assert result is False
        assert pbx.running is False

    def test_start_sip_failure(self) -> None:
        """start() returns False when SIP server fails to start."""
        pbx = _make_pbx_core_shell()
        pbx.security_monitor.enforce_security_requirements.return_value = True
        pbx.sip_server.start.return_value = False

        result = pbx.start()

        assert result is False

    def test_start_api_failure_noncritical(self) -> None:
        """API server failure is non-critical; start() still returns True."""
        pbx = _make_pbx_core_shell()
        pbx.security_monitor.enforce_security_requirements.return_value = True
        pbx.sip_server.start.return_value = True
        pbx.api_server.start.return_value = False

        result = pbx.start()

        assert result is True
        assert pbx.running is True

    def test_start_no_security_monitor(self) -> None:
        """start() works when security_monitor attribute doesn't exist."""
        pbx = _make_pbx_core_shell()
        del pbx.security_monitor
        pbx.sip_server.start.return_value = True
        pbx.api_server.start.return_value = True

        result = pbx.start()

        assert result is True

    def test_start_no_dnd_scheduler(self) -> None:
        """start() works when dnd_scheduler is None."""
        pbx = _make_pbx_core_shell()
        pbx.security_monitor.enforce_security_requirements.return_value = True
        pbx.sip_server.start.return_value = True
        pbx.api_server.start.return_value = True
        pbx.dnd_scheduler = None

        result = pbx.start()

        assert result is True

    def test_stop_ends_active_calls(self) -> None:
        """stop() ends all active calls and releases RTP relays."""
        pbx = _make_pbx_core_shell()
        pbx.running = True

        mock_call = MagicMock()
        mock_call.call_id = "call-1"
        pbx.call_manager.get_active_calls.return_value = [mock_call]
        pbx.recording_system.is_recording.return_value = True

        pbx.stop()

        assert pbx.running is False
        pbx.call_manager.end_call.assert_called_once_with("call-1")
        pbx.rtp_relay.release_relay.assert_called_once_with("call-1")
        pbx.recording_system.stop_recording.assert_called_once_with("call-1")
        pbx.security_monitor.stop.assert_called_once()
        pbx.api_server.stop.assert_called_once()
        pbx.sip_server.stop.assert_called_once()

    def test_stop_without_security_monitor(self) -> None:
        """stop() works when security_monitor attribute doesn't exist."""
        pbx = _make_pbx_core_shell()
        del pbx.security_monitor
        pbx.running = True
        pbx.call_manager.get_active_calls.return_value = []
        pbx.dnd_scheduler = None

        pbx.stop()

        assert pbx.running is False

    def test_stop_skips_recording_stop_when_not_recording(self) -> None:
        """stop() does not stop recording if call is not being recorded."""
        pbx = _make_pbx_core_shell()
        pbx.running = True

        mock_call = MagicMock()
        mock_call.call_id = "call-2"
        pbx.call_manager.get_active_calls.return_value = [mock_call]
        pbx.recording_system.is_recording.return_value = False

        pbx.stop()

        pbx.recording_system.stop_recording.assert_not_called()


# =========================================================================
# Tests for register_extension
# =========================================================================
@pytest.mark.unit
class TestRegisterExtension:
    """Tests for PBXCore.register_extension."""

    def test_register_extension_from_database(self) -> None:
        """Extension found in database is registered successfully."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.return_value = {"number": "1001", "name": "Test"}
        pbx.extension_registry.get.return_value = MagicMock()

        result = pbx.register_extension(
            '"Test" <sip:1001@192.168.1.1>',
            ("192.168.1.100", 5060),
            user_agent="Yealink SIP-T46S",
            contact="<sip:1001@192.168.1.100:5060>",
        )

        assert result is True
        pbx.extension_registry.register.assert_called_once_with("1001", ("192.168.1.100", 5060))
        pbx.webhook_system.trigger_event.assert_called_once()

    def test_register_extension_from_config_fallback(self) -> None:
        """Extension not in DB falls back to config lookup."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.return_value = None
        pbx.config.get_extension.return_value = {"number": "1001"}

        result = pbx.register_extension(
            "<sip:1001@host>",
            ("10.0.0.1", 5060),
        )

        assert result is True
        pbx.config.get_extension.assert_called_once_with("1001")

    def test_register_unknown_extension(self) -> None:
        """Unknown extension number returns False."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.return_value = None
        pbx.config.get_extension.return_value = None

        result = pbx.register_extension("<sip:9999@host>", ("10.0.0.1", 5060))

        assert result is False

    def test_register_bad_from_header(self) -> None:
        """Unparseable From header returns False."""
        pbx = _make_pbx_core_shell()

        result = pbx.register_extension("garbage header", ("10.0.0.1", 5060))

        assert result is False

    def test_register_stores_phone_registration(self) -> None:
        """Successful registration stores data in registered_phones_db."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.return_value = {"number": "1001"}
        pbx.extension_registry.get.return_value = MagicMock()
        pbx.registered_phones_db.register_phone.return_value = (True, "aabbccddeeff")

        result = pbx.register_extension(
            "<sip:1001@host>",
            ("10.0.0.1", 5060),
            user_agent="TestPhone",
            contact="<sip:1001@10.0.0.1:5060>",
        )

        assert result is True
        pbx.registered_phones_db.register_phone.assert_called_once()

    def test_register_stores_phone_no_mac(self) -> None:
        """Registration with no MAC address still succeeds."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.return_value = {"number": "1001"}
        pbx.extension_registry.get.return_value = MagicMock()
        pbx.registered_phones_db.register_phone.return_value = (True, None)

        result = pbx.register_extension(
            "<sip:1001@host>",
            ("10.0.0.1", 5060),
        )

        assert result is True

    def test_register_handles_db_store_exception(self) -> None:
        """Exception in database storage is caught and logged."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.return_value = {"number": "1001"}
        pbx.extension_registry.get.return_value = MagicMock()
        pbx.registered_phones_db.register_phone.side_effect = RuntimeError("db error")

        result = pbx.register_extension(
            "<sip:1001@host>",
            ("10.0.0.1", 5060),
        )

        assert result is True  # still returns True
        assert pbx.logger.error.call_count >= 1

    def test_register_no_registered_phones_db(self) -> None:
        """No registered_phones_db still returns True."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.return_value = {"number": "1001"}
        pbx.extension_registry.get.return_value = MagicMock()
        pbx.registered_phones_db = None

        result = pbx.register_extension(
            "<sip:1001@host>",
            ("10.0.0.1", 5060),
        )

        assert result is True

    def test_register_loads_extension_from_db_to_registry(self) -> None:
        """When extension is in DB but not in registry, it is loaded into registry."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.return_value = {"number": "1001", "name": "Test"}
        pbx.extension_registry.get.return_value = None  # Not in registry

        with patch("pbx.core.pbx.ExtensionRegistry") as mock_er:
            mock_er.create_extension_from_db.return_value = MagicMock()
            pbx.extension_registry.extensions = {}

            result = pbx.register_extension(
                "<sip:1001@host>",
                ("10.0.0.1", 5060),
            )

        assert result is True

    def test_register_handles_extension_db_error(self) -> None:
        """Database errors during extension lookup are handled gracefully."""
        pbx = _make_pbx_core_shell()
        pbx.extension_db.get.side_effect = TypeError("db issue")
        pbx.config.get_extension.return_value = {"number": "1001"}

        result = pbx.register_extension(
            "<sip:1001@host>",
            ("10.0.0.1", 5060),
        )

        assert result is True


# =========================================================================
# Tests for _extract_mac_address
# =========================================================================
@pytest.mark.unit
class TestExtractMacAddress:
    """Tests for PBXCore._extract_mac_address."""

    def test_mac_from_contact_colon_format(self) -> None:
        """Extracts MAC from Contact header (colon-separated)."""
        pbx = _make_pbx_core_shell()
        result = pbx._extract_mac_address("<sip:1001@10.0.0.1;mac=00:11:22:33:44:55>", None)
        assert result == "001122334455"

    def test_mac_from_contact_dash_format(self) -> None:
        """Extracts MAC from Contact header (dash-separated)."""
        pbx = _make_pbx_core_shell()
        result = pbx._extract_mac_address("<sip:1001@10.0.0.1;mac=00-11-22-33-44-55>", None)
        assert result == "001122334455"

    def test_mac_from_instance_uuid(self) -> None:
        """Extracts MAC from sip.instance UUID in Contact header."""
        pbx = _make_pbx_core_shell()
        contact = (
            '<sip:1001@10.0.0.1>;+sip.instance="<urn:uuid:00112233-4455-6677-8899-aabbccddeeff>"'
        )
        result = pbx._extract_mac_address(contact, None)
        # Last 12 hex chars: "aabbccddeeff"
        assert result == "aabbccddeeff"

    def test_mac_from_user_agent(self) -> None:
        """Extracts MAC from User-Agent header."""
        pbx = _make_pbx_core_shell()
        result = pbx._extract_mac_address(None, "Yealink SIP-T46S 66.85.0.5 00:15:65:12:34:56")
        assert result == "001565123456"

    def test_no_mac_found(self) -> None:
        """Returns None when no MAC can be found."""
        pbx = _make_pbx_core_shell()
        result = pbx._extract_mac_address("<sip:1001@10.0.0.1>", "Generic SIP Phone")
        assert result is None

    def test_none_inputs(self) -> None:
        """Returns None when both inputs are None."""
        pbx = _make_pbx_core_shell()
        result = pbx._extract_mac_address(None, None)
        assert result is None

    def test_mac_contact_takes_priority_over_user_agent(self) -> None:
        """Contact MAC is preferred over User-Agent MAC."""
        pbx = _make_pbx_core_shell()
        result = pbx._extract_mac_address(
            "<sip:1001@10.0.0.1;mac=AA:BB:CC:DD:EE:FF>",
            "SIP Phone 11:22:33:44:55:66",
        )
        assert result == "aabbccddeeff"


# =========================================================================
# Tests for _detect_phone_model
# =========================================================================
@pytest.mark.unit
class TestDetectPhoneModel:
    """Tests for PBXCore._detect_phone_model."""

    def test_detect_zip33g(self) -> None:
        pbx = _make_pbx_core_shell()
        assert pbx._detect_phone_model("Zultys ZIP33G 1.0") == "ZIP33G"

    def test_detect_zip33g_space(self) -> None:
        pbx = _make_pbx_core_shell()
        assert pbx._detect_phone_model("Zultys ZIP 33G 1.0") == "ZIP33G"

    def test_detect_zip37g(self) -> None:
        pbx = _make_pbx_core_shell()
        assert pbx._detect_phone_model("Zultys ZIP37G") == "ZIP37G"

    def test_detect_zip37g_space(self) -> None:
        pbx = _make_pbx_core_shell()
        assert pbx._detect_phone_model("Zultys ZIP 37G") == "ZIP37G"

    def test_detect_unknown_phone(self) -> None:
        pbx = _make_pbx_core_shell()
        assert pbx._detect_phone_model("Yealink SIP-T46S") is None

    def test_detect_none_user_agent(self) -> None:
        pbx = _make_pbx_core_shell()
        assert pbx._detect_phone_model(None) is None


# =========================================================================
# Tests for _get_codecs_for_phone_model
# =========================================================================
@pytest.mark.unit
class TestGetCodecsForPhoneModel:
    """Tests for PBXCore._get_codecs_for_phone_model."""

    def test_zip37g_codecs(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 101
        codecs = pbx._get_codecs_for_phone_model("ZIP37G")
        assert codecs == ["0", "8", "101"]

    def test_zip33g_codecs(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 101
        codecs = pbx._get_codecs_for_phone_model("ZIP33G")
        assert codecs == ["2", "18", "9", "114", "113", "112", "101"]

    def test_unknown_phone_uses_default_codecs(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 101
        default = ["0", "8"]
        codecs = pbx._get_codecs_for_phone_model(None, default_codecs=default)
        assert codecs == ["0", "8"]

    def test_unknown_phone_ultimate_fallback(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 101
        codecs = pbx._get_codecs_for_phone_model(None)
        assert codecs == ["0", "8", "9", "18", "2", "101"]

    def test_custom_dtmf_payload_type(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 96
        codecs = pbx._get_codecs_for_phone_model("ZIP37G")
        assert "96" in codecs


# =========================================================================
# Tests for _get_phone_user_agent
# =========================================================================
@pytest.mark.unit
class TestGetPhoneUserAgent:
    """Tests for PBXCore._get_phone_user_agent."""

    def test_returns_user_agent_from_db(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.database.db_type = "sqlite"
        pbx.database.fetch_one.return_value = {"user_agent": "Yealink SIP-T46S"}

        result = pbx._get_phone_user_agent("1001")

        assert result == "Yealink SIP-T46S"

    def test_returns_none_when_no_db(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.registered_phones_db = None

        result = pbx._get_phone_user_agent("1001")

        assert result is None

    def test_returns_none_when_no_database(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.database = None

        result = pbx._get_phone_user_agent("1001")

        assert result is None

    def test_returns_none_when_no_result(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.database.db_type = "sqlite"
        pbx.database.fetch_one.return_value = None

        result = pbx._get_phone_user_agent("1001")

        assert result is None

    def test_returns_none_on_exception(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.database.db_type = "sqlite"
        pbx.database.fetch_one.side_effect = TypeError("broken")

        result = pbx._get_phone_user_agent("1001")

        assert result is None

    def test_postgresql_query_uses_percent_s(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.database.db_type = "postgresql"
        pbx.database.fetch_one.return_value = {"user_agent": "TestUA"}

        result = pbx._get_phone_user_agent("1001")

        assert result == "TestUA"
        # Verify the query used %s placeholder
        query_arg = pbx.database.fetch_one.call_args[0][0]
        assert "%s" in query_arg
        assert "?" not in query_arg

    def test_sqlite_query_uses_question_mark(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.database.db_type = "sqlite"
        pbx.database.fetch_one.return_value = {"user_agent": "TestUA"}

        result = pbx._get_phone_user_agent("1001")

        assert result == "TestUA"
        query_arg = pbx.database.fetch_one.call_args[0][0]
        assert "?" in query_arg


# =========================================================================
# Tests for _get_dtmf_payload_type and _get_ilbc_mode
# =========================================================================
@pytest.mark.unit
class TestConfigGetters:
    """Tests for simple config accessor methods."""

    def test_get_dtmf_payload_type_default(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 101
        assert pbx._get_dtmf_payload_type() == 101

    def test_get_dtmf_payload_type_custom(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 96
        assert pbx._get_dtmf_payload_type() == 96

    def test_get_ilbc_mode_default(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 30
        assert pbx._get_ilbc_mode() == 30

    def test_get_ilbc_mode_custom(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = 20
        assert pbx._get_ilbc_mode() == 20


# =========================================================================
# Tests for route_call
# =========================================================================
@pytest.mark.unit
class TestRouteCall:
    """Tests for PBXCore.route_call."""

    def test_route_call_delegates_to_call_router(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._call_router.route_call.return_value = True
        msg = MagicMock()

        result = pbx.route_call("from", "to", "call-1", msg, ("10.0.0.1", 5060))

        assert result is True
        pbx._call_router.route_call.assert_called_once_with(
            "from", "to", "call-1", msg, ("10.0.0.1", 5060)
        )

    def test_route_call_returns_false_on_failure(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._call_router.route_call.return_value = False

        result = pbx.route_call("from", "to", "c1", MagicMock(), ("1.2.3.4", 5060))

        assert result is False


# =========================================================================
# Tests for _get_server_ip
# =========================================================================
@pytest.mark.unit
class TestGetServerIp:
    """Tests for PBXCore._get_server_ip."""

    def test_returns_configured_external_ip(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = "203.0.113.1"

        result = pbx._get_server_ip()

        assert result == "203.0.113.1"

    @patch("socket.socket")
    def test_falls_back_to_socket_detection(self, mock_socket_cls: MagicMock) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = None

        sock_inst = MagicMock()
        sock_inst.getsockname.return_value = ("192.168.1.50", 0)
        mock_socket_cls.return_value = sock_inst

        result = pbx._get_server_ip()

        assert result == "192.168.1.50"
        sock_inst.close.assert_called_once()

    @patch("socket.socket")
    def test_returns_localhost_on_socket_error(self, mock_socket_cls: MagicMock) -> None:
        pbx = _make_pbx_core_shell()
        pbx.config.get.return_value = None

        mock_socket_cls.return_value.connect.side_effect = OSError("no network")

        result = pbx._get_server_ip()

        assert result == "127.0.0.1"


# =========================================================================
# Tests for handle_callee_answer
# =========================================================================
@pytest.mark.unit
class TestHandleCalleeAnswer:
    """Tests for PBXCore.handle_callee_answer."""

    def test_no_call_found(self) -> None:
        """Returns early when call is not found."""
        pbx = _make_pbx_core_shell()
        pbx.call_manager.get_call.return_value = None

        pbx.handle_callee_answer("nonexistent", MagicMock(), ("1.2.3.4", 5060))

        pbx.logger.error.assert_called_once()

    @patch("pbx.core.pbx.SDPBuilder", create=True)
    @patch("pbx.core.pbx.SDPSession", create=True)
    @patch("pbx.core.pbx.SIPMessageBuilder", create=True)
    def test_callee_answer_full_flow(
        self,
        mock_sip_builder: MagicMock,
        mock_sdp_session: MagicMock,
        mock_sdp_builder: MagicMock,
    ) -> None:
        """Full callee answer flow with SDP, RTP relay, and 200 OK."""
        pbx = _make_pbx_core_shell()

        mock_call = MagicMock()
        mock_call.call_id = "call-42"
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        mock_call.caller_rtp = {"address": "10.0.0.1", "port": 20000, "formats": ["0", "8"]}
        mock_call.callee_rtp = None
        mock_call.rtp_ports = (30000, 30001)
        mock_call.caller_addr = ("10.0.0.1", 5060)
        mock_call.no_answer_timer = MagicMock()
        mock_call.original_invite = MagicMock()
        pbx.call_manager.get_call.return_value = mock_call

        response_msg = MagicMock()
        response_msg.body = "v=0\r\no=- 0 0 IN IP4 10.0.0.2\r\n"

        # SDP parsing
        with (
            patch.dict(
                "sys.modules",
                {
                    "pbx.sip.message": MagicMock(),
                    "pbx.sip.sdp": MagicMock(),
                },
            ),
            # Mock the SDP and SIP builder imports inside the method
            patch("pbx.core.pbx.SDPSession", create=True) as mock_sdp_cls,
            patch("pbx.core.pbx.SDPBuilder", create=True) as mock_sdp_build,
            patch("pbx.core.pbx.SIPMessageBuilder", create=True) as mock_sip_build,
        ):
                sdp_inst = MagicMock()
                sdp_inst.get_audio_info.return_value = {"address": "10.0.0.2", "port": 20002}
                mock_sdp_cls.return_value = sdp_inst

                mock_sdp_build.build_audio_sdp.return_value = "v=0\r\n..."

                ok_msg = MagicMock()
                mock_sip_build.build_response.return_value = ok_msg

                pbx.config.get.side_effect = lambda k, d=None: {
                    "server.external_ip": "10.0.0.100",
                    "features.dtmf.payload_type": 101,
                    "codecs.ilbc.mode": 30,
                    "server.sip_port": 5060,
                }.get(k, d)

                pbx._get_phone_user_agent = MagicMock(return_value=None)
                pbx._detect_phone_model = MagicMock(return_value=None)
                pbx._get_codecs_for_phone_model = MagicMock(return_value=["0", "8", "101"])
                pbx._get_dtmf_payload_type = MagicMock(return_value=101)
                pbx._get_ilbc_mode = MagicMock(return_value=30)
                pbx._get_server_ip = MagicMock(return_value="10.0.0.100")

                pbx.handle_callee_answer("call-42", response_msg, ("10.0.0.2", 5060))

        # Call should be marked as connected
        mock_call.connect.assert_called_once()
        pbx.cdr_system.mark_answered.assert_called_once_with("call-42")
        mock_call.no_answer_timer.cancel.assert_called_once()

    def test_callee_answer_no_body(self) -> None:
        """Handle callee answer when response has no SDP body."""
        pbx = _make_pbx_core_shell()

        mock_call = MagicMock()
        mock_call.call_id = "call-99"
        mock_call.caller_rtp = None
        mock_call.callee_rtp = None
        mock_call.rtp_ports = None
        mock_call.no_answer_timer = None
        mock_call.original_invite = None
        mock_call.caller_addr = None
        pbx.call_manager.get_call.return_value = mock_call

        response_msg = MagicMock()
        response_msg.body = None

        pbx.handle_callee_answer("call-99", response_msg, ("1.2.3.4", 5060))

        mock_call.connect.assert_called_once()
        pbx.cdr_system.mark_answered.assert_called_once_with("call-99")


# =========================================================================
# Tests for end_call
# =========================================================================
@pytest.mark.unit
class TestEndCall:
    """Tests for PBXCore.end_call."""

    def test_end_call_basic(self) -> None:
        """Basic call ending releases resources."""
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.call_id = "call-1"
        mock_call.routed_to_voicemail = False
        pbx.call_manager.get_call.return_value = mock_call

        pbx.end_call("call-1")

        pbx.call_manager.end_call.assert_called_once_with("call-1")
        pbx.rtp_relay.release_relay.assert_called_once_with("call-1")
        pbx.cdr_system.end_record.assert_called_once_with("call-1", hangup_cause="normal_clearing")

    def test_end_call_not_found(self) -> None:
        """end_call does nothing if call not found."""
        pbx = _make_pbx_core_shell()
        pbx.call_manager.get_call.return_value = None

        pbx.end_call("nonexistent")

        pbx.call_manager.end_call.assert_not_called()

    def test_end_call_with_voicemail(self) -> None:
        """Voicemail recording is completed on call end."""
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.call_id = "call-vm"
        mock_call.routed_to_voicemail = True
        mock_call.to_extension = "1002"
        mock_call.from_extension = "1001"

        recorder = MagicMock()
        recorder.running = True
        recorder.get_recorded_audio.return_value = b"\x80" * 1000
        recorder.get_duration.return_value = 5.0
        mock_call.voicemail_recorder = recorder

        timer = MagicMock()
        mock_call.voicemail_timer = timer

        pbx.call_manager.get_call.return_value = mock_call

        # Mock _build_wav_file
        pbx._build_wav_file = MagicMock(return_value=b"RIFF...")

        pbx.end_call("call-vm")

        timer.cancel.assert_called_once()
        recorder.stop.assert_called_once()
        pbx.voicemail_system.save_message.assert_called_once()
        pbx.call_manager.end_call.assert_called_once_with("call-vm")

    def test_end_call_voicemail_no_audio(self) -> None:
        """Voicemail with no recorded audio logs a warning."""
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.call_id = "call-vm2"
        mock_call.routed_to_voicemail = True

        recorder = MagicMock()
        recorder.running = True
        recorder.get_recorded_audio.return_value = b""
        recorder.get_duration.return_value = 0.0
        mock_call.voicemail_recorder = recorder
        mock_call.voicemail_timer = None

        pbx.call_manager.get_call.return_value = mock_call

        pbx.end_call("call-vm2")

        pbx.logger.warning.assert_called()

    def test_end_call_voicemail_recorder_not_running(self) -> None:
        """Voicemail recorder that is not running is not stopped again."""
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.call_id = "call-vm3"
        mock_call.routed_to_voicemail = True

        recorder = MagicMock()
        recorder.running = False
        mock_call.voicemail_recorder = recorder
        mock_call.voicemail_timer = None

        pbx.call_manager.get_call.return_value = mock_call

        pbx.end_call("call-vm3")

        recorder.stop.assert_not_called()


# =========================================================================
# Tests for handle_dtmf_info
# =========================================================================
@pytest.mark.unit
class TestHandleDtmfInfo:
    """Tests for PBXCore.handle_dtmf_info."""

    def test_dtmf_call_not_found(self) -> None:
        """DTMF for unknown call is silently ignored."""
        pbx = _make_pbx_core_shell()
        pbx.call_manager.get_call.return_value = None

        pbx.handle_dtmf_info("unknown-call", "5")

        pbx.logger.debug.assert_called()

    def test_dtmf_queued_for_normal_call(self) -> None:
        """DTMF digit is queued on the call object."""
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.dtmf_info_queue = []
        mock_call.voicemail_ivr = False
        mock_call.auto_attendant = False
        pbx.call_manager.get_call.return_value = mock_call

        pbx.handle_dtmf_info("call-1", "5")

        assert mock_call.dtmf_info_queue == ["5"]

    def test_dtmf_queued_for_voicemail_ivr(self) -> None:
        """DTMF for voicemail IVR call logs specific message."""
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.dtmf_info_queue = []
        mock_call.voicemail_ivr = True
        mock_call.auto_attendant = False
        pbx.call_manager.get_call.return_value = mock_call

        pbx.handle_dtmf_info("call-1", "#")

        assert mock_call.dtmf_info_queue == ["#"]
        pbx.logger.info.assert_called()

    def test_dtmf_queued_for_auto_attendant(self) -> None:
        """DTMF for auto-attendant call logs specific message."""
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.dtmf_info_queue = []
        mock_call.voicemail_ivr = False
        mock_call.auto_attendant = True
        pbx.call_manager.get_call.return_value = mock_call

        pbx.handle_dtmf_info("call-1", "1")

        assert mock_call.dtmf_info_queue == ["1"]
        pbx.logger.info.assert_called()

    def test_dtmf_creates_queue_if_missing(self) -> None:
        """Queue is created if not already present on call object."""
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock(spec=[])  # No attributes by default
        # Manually clear the attribute so hasattr returns False initially
        pbx.call_manager.get_call.return_value = mock_call

        # Use a real object without dtmf_info_queue attribute
        class FakeCall:
            voicemail_ivr = False
            auto_attendant = False

        fake_call = FakeCall()
        pbx.call_manager.get_call.return_value = fake_call

        pbx.handle_dtmf_info("call-1", "9")

        assert hasattr(fake_call, "dtmf_info_queue")
        assert fake_call.dtmf_info_queue == ["9"]


# =========================================================================
# Tests for transfer_call
# =========================================================================
@pytest.mark.unit
class TestTransferCall:
    """Tests for PBXCore.transfer_call."""

    def test_transfer_call_not_found(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.call_manager.get_call.return_value = None

        result = pbx.transfer_call("c1", "2001")

        assert result is False

    def test_transfer_destination_not_registered(self) -> None:
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        pbx.call_manager.get_call.return_value = mock_call
        pbx.extension_registry.is_registered.return_value = False

        result = pbx.transfer_call("c1", "2001")

        assert result is False

    def test_transfer_no_address(self) -> None:
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.caller_addr = None
        mock_call.callee_addr = None
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        pbx.call_manager.get_call.return_value = mock_call
        pbx.extension_registry.is_registered.return_value = True

        result = pbx.transfer_call("c1", "2001")

        assert result is False

    @patch("pbx.core.pbx.SIPMessageBuilder", create=True)
    def test_transfer_success(self, mock_sip_builder: MagicMock) -> None:
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_call.caller_addr = ("10.0.0.1", 5060)
        mock_call.from_extension = "1001"
        mock_call.to_extension = "1002"
        mock_call.call_id = "c1"
        pbx.call_manager.get_call.return_value = mock_call
        pbx.extension_registry.is_registered.return_value = True
        pbx.config.get.return_value = 5060
        pbx._get_server_ip = MagicMock(return_value="10.0.0.100")

        refer_msg = MagicMock()
        mock_sip_builder.build_request.return_value = refer_msg

        with patch.dict(
            "sys.modules", {"pbx.sip.message": MagicMock(SIPMessageBuilder=mock_sip_builder)}
        ):
            result = pbx.transfer_call("c1", "2001")

        assert result is True
        assert mock_call.transferred is True
        assert mock_call.transfer_destination == "2001"
        pbx.sip_server._send_message.assert_called_once()


# =========================================================================
# Tests for hold_call / resume_call
# =========================================================================
@pytest.mark.unit
class TestHoldResume:
    """Tests for PBXCore.hold_call and PBXCore.resume_call."""

    def test_hold_call_success(self) -> None:
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        pbx.call_manager.get_call.return_value = mock_call

        result = pbx.hold_call("c1")

        assert result is True
        mock_call.hold.assert_called_once()

    def test_hold_call_not_found(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.call_manager.get_call.return_value = None

        result = pbx.hold_call("c1")

        assert result is False

    def test_resume_call_success(self) -> None:
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        pbx.call_manager.get_call.return_value = mock_call

        result = pbx.resume_call("c1")

        assert result is True
        mock_call.resume.assert_called_once()

    def test_resume_call_not_found(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx.call_manager.get_call.return_value = None

        result = pbx.resume_call("c1")

        assert result is False


# =========================================================================
# Tests for delegate methods (_check_dialplan, _send_cancel_to_callee, etc.)
# =========================================================================
@pytest.mark.unit
class TestDelegateMethods:
    """Tests for methods that delegate to handler classes."""

    def test_check_dialplan(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._call_router._check_dialplan.return_value = True
        assert pbx._check_dialplan("1001") is True
        pbx._call_router._check_dialplan.assert_called_once_with("1001")

    def test_send_cancel_to_callee(self) -> None:
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        pbx._send_cancel_to_callee(mock_call, "c1")
        pbx._call_router._send_cancel_to_callee.assert_called_once_with(mock_call, "c1")

    def test_answer_call_for_voicemail(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._call_router._answer_call_for_voicemail.return_value = True
        mock_call = MagicMock()
        result = pbx._answer_call_for_voicemail(mock_call, "c1")
        assert result is True

    def test_handle_no_answer(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._handle_no_answer("c1")
        pbx._call_router._handle_no_answer.assert_called_once_with("c1")

    def test_monitor_voicemail_dtmf(self) -> None:
        pbx = _make_pbx_core_shell()
        mock_call = MagicMock()
        mock_rec = MagicMock()
        pbx._monitor_voicemail_dtmf("c1", mock_call, mock_rec)
        pbx._voicemail_handler.monitor_voicemail_dtmf.assert_called_once_with(
            "c1", mock_call, mock_rec
        )

    def test_complete_voicemail_recording(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._complete_voicemail_recording("c1")
        pbx._voicemail_handler.complete_voicemail_recording.assert_called_once_with("c1")

    def test_handle_auto_attendant(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._auto_attendant_handler.handle_auto_attendant.return_value = True
        msg = MagicMock()
        result = pbx._handle_auto_attendant("1001", "0", "c1", msg, ("1.2.3.4", 5060))
        assert result is True

    def test_auto_attendant_session(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._auto_attendant_session("c1", MagicMock(), MagicMock())
        pbx._auto_attendant_handler._auto_attendant_session.assert_called_once()

    def test_handle_voicemail_access(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._voicemail_handler.handle_voicemail_access.return_value = True
        msg = MagicMock()
        result = pbx._handle_voicemail_access("1001", "*1002", "c1", msg, ("1.2.3.4", 5060))
        assert result is True

    def test_handle_paging(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._paging_handler.handle_paging.return_value = True
        msg = MagicMock()
        result = pbx._handle_paging("1001", "700", "c1", msg, ("1.2.3.4", 5060))
        assert result is True

    def test_paging_session(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._paging_session("c1", MagicMock(), {}, {})
        pbx._paging_handler._paging_session.assert_called_once()

    def test_playback_voicemails(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._playback_voicemails("c1", MagicMock(), MagicMock(), [])
        pbx._voicemail_handler._playback_voicemails.assert_called_once()

    def test_voicemail_ivr_session(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._voicemail_ivr_session("c1", MagicMock(), MagicMock(), MagicMock())
        pbx._voicemail_handler._voicemail_ivr_session.assert_called_once()

    def test_handle_emergency_call(self) -> None:
        pbx = _make_pbx_core_shell()
        pbx._emergency_handler.handle_emergency_call.return_value = True
        msg = MagicMock()
        result = pbx._handle_emergency_call("1001", "911", "c1", msg, ("1.2.3.4", 5060))
        assert result is True


# =========================================================================
# Tests for _build_wav_file
# =========================================================================
@pytest.mark.unit
class TestBuildWavFile:
    """Tests for PBXCore._build_wav_file."""

    def test_builds_valid_wav_header(self) -> None:
        """WAV file starts with RIFF header and WAVE marker."""
        pbx = _make_pbx_core_shell()
        audio_data = b"\x80" * 100

        wav = pbx._build_wav_file(audio_data)

        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert wav[12:16] == b"fmt "
        # data chunk marker
        assert b"data" in wav

    def test_wav_contains_audio_data(self) -> None:
        """WAV file ends with the original audio data."""
        pbx = _make_pbx_core_shell()
        audio_data = b"\xaa\xbb\xcc\xdd"

        wav = pbx._build_wav_file(audio_data)

        assert wav.endswith(audio_data)

    def test_wav_correct_data_size(self) -> None:
        """Data chunk size in header matches audio data length."""
        pbx = _make_pbx_core_shell()
        audio_data = b"\x00" * 256

        wav = pbx._build_wav_file(audio_data)

        # The data chunk is: "data" (4 bytes) + size (4 bytes LE) + audio
        # Find "data" marker
        data_idx = wav.index(b"data")
        data_size = struct.unpack("<I", wav[data_idx + 4 : data_idx + 8])[0]
        assert data_size == 256

    def test_wav_audio_format_mulaw(self) -> None:
        """Audio format is set to 7 (G.711 mu-law)."""
        pbx = _make_pbx_core_shell()
        wav = pbx._build_wav_file(b"\x00" * 10)

        # fmt chunk starts at offset 12, chunk size at 16 (4 bytes)
        # audio_format is at offset 20 (2 bytes)
        audio_format = struct.unpack("<H", wav[20:22])[0]
        assert audio_format == 7

    def test_wav_sample_rate_8000(self) -> None:
        """Sample rate is 8000 Hz."""
        pbx = _make_pbx_core_shell()
        wav = pbx._build_wav_file(b"\x00" * 10)

        # sample_rate at offset 24 (4 bytes)
        sample_rate = struct.unpack("<I", wav[24:28])[0]
        assert sample_rate == 8000

    def test_wav_empty_audio(self) -> None:
        """WAV file with empty audio data is still valid."""
        pbx = _make_pbx_core_shell()
        wav = pbx._build_wav_file(b"")

        assert wav[:4] == b"RIFF"
        data_idx = wav.index(b"data")
        data_size = struct.unpack("<I", wav[data_idx + 4 : data_idx + 8])[0]
        assert data_size == 0


# =========================================================================
# Tests for get_status
# =========================================================================
@pytest.mark.unit
class TestGetStatus:
    """Tests for PBXCore.get_status."""

    def test_get_status_structure(self) -> None:
        """get_status returns all expected keys."""
        pbx = _make_pbx_core_shell()
        pbx.running = True
        pbx.extension_registry.get_registered_count.return_value = 5
        pbx.call_manager.get_active_calls.return_value = [MagicMock(), MagicMock()]
        pbx.call_manager.call_history = [MagicMock()] * 10
        pbx.recording_system.active_recordings = {"r1": MagicMock()}
        pbx.conference_system.get_active_rooms.return_value = ["room1"]
        pbx.parking_system.get_parked_calls.return_value = []

        q = MagicMock()
        q.queue = [1, 2, 3]
        pbx.queue_system.queues = {"sales": q}

        status = pbx.get_status()

        assert status["running"] is True
        assert status["registered_extensions"] == 5
        assert status["active_calls"] == 2
        assert status["total_calls"] == 10
        assert status["active_recordings"] == 1
        assert status["active_conferences"] == 1
        assert status["parked_calls"] == 0
        assert status["queued_calls"] == 3

    def test_get_status_when_not_running(self) -> None:
        """get_status correctly reports running as False."""
        pbx = _make_pbx_core_shell()
        pbx.running = False
        pbx.extension_registry.get_registered_count.return_value = 0
        pbx.call_manager.get_active_calls.return_value = []
        pbx.call_manager.call_history = []
        pbx.recording_system.active_recordings = {}
        pbx.conference_system.get_active_rooms.return_value = []
        pbx.parking_system.get_parked_calls.return_value = []
        pbx.queue_system.queues = {}

        status = pbx.get_status()

        assert status["running"] is False
        assert status["active_calls"] == 0


# =========================================================================
# Tests for get_ad_integration_status
# =========================================================================
@pytest.mark.unit
class TestGetAdIntegrationStatus:
    """Tests for PBXCore.get_ad_integration_status."""

    def test_ad_not_configured(self) -> None:
        """Returns disabled status when ad_integration is None."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration = None

        status = pbx.get_ad_integration_status()

        assert status["enabled"] is False
        assert status["connected"] is False
        assert status["synced_users"] == 0

    def test_ad_configured_and_connected(self) -> None:
        """Returns connected status with synced user count."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.connect.return_value = True
        pbx.ad_integration.enabled = True
        pbx.ad_integration.auto_provision = False
        pbx.ad_integration.ldap_server = "dc.example.com"
        pbx.extension_db.get_ad_synced.return_value = [{"number": "1001"}, {"number": "1002"}]

        status = pbx.get_ad_integration_status()

        assert status["enabled"] is True
        assert status["connected"] is True
        assert status["synced_users"] == 2
        assert status["server"] == "dc.example.com"
        assert status["error"] is None

    def test_ad_connect_exception(self) -> None:
        """Connection exceptions are captured in error field."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.connect.side_effect = ConnectionError("timeout")
        pbx.ad_integration.enabled = True
        pbx.ad_integration.auto_provision = False
        pbx.ad_integration.ldap_server = "dc.example.com"
        pbx.extension_db = None

        status = pbx.get_ad_integration_status()

        assert status["connected"] is False
        assert status["error"] == "timeout"

    def test_ad_synced_count_exception(self) -> None:
        """Exception in get_ad_synced returns 0 synced users."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.connect.return_value = True
        pbx.ad_integration.enabled = True
        pbx.ad_integration.auto_provision = False
        pbx.ad_integration.ldap_server = "dc.example.com"
        pbx.extension_db.get_ad_synced.side_effect = RuntimeError("db error")

        status = pbx.get_ad_integration_status()

        assert status["synced_users"] == 0


# =========================================================================
# Tests for sync_ad_users
# =========================================================================
@pytest.mark.unit
class TestSyncAdUsers:
    """Tests for PBXCore.sync_ad_users."""

    def test_sync_no_ad_integration(self) -> None:
        """Returns error when AD integration is not configured."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration = None

        result = pbx.sync_ad_users()

        assert result["success"] is False
        assert "not enabled" in result["error"]

    def test_sync_ad_disabled(self) -> None:
        """Returns error when AD integration is disabled."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.enabled = False

        result = pbx.sync_ad_users()

        assert result["success"] is False
        assert "disabled" in result["error"]

    def test_sync_ad_success_int_result(self) -> None:
        """Handles legacy integer return from sync_users."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.enabled = True
        pbx.ad_integration.sync_users.return_value = 5
        pbx.phone_book = None

        result = pbx.sync_ad_users()

        assert result["success"] is True
        assert result["synced_count"] == 5
        pbx.extension_registry.reload.assert_called_once()

    def test_sync_ad_success_dict_result(self) -> None:
        """Handles dict return from sync_users with extensions_to_reboot."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.enabled = True
        pbx.ad_integration.sync_users.return_value = {
            "synced_count": 3,
            "extensions_to_reboot": ["1001", "1002"],
        }
        pbx.phone_provisioning.reboot_phone.return_value = True
        pbx.phone_book = None

        result = pbx.sync_ad_users()

        assert result["success"] is True
        assert result["synced_count"] == 3
        assert result["rebooted_count"] == 2

    def test_sync_ad_with_phone_book_sync(self) -> None:
        """Phone book is auto-synced from AD if enabled."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.enabled = True
        pbx.ad_integration.sync_users.return_value = 2
        pbx.phone_book.enabled = True
        pbx.phone_book.auto_sync_from_ad = True
        pbx.phone_book.sync_from_ad.return_value = 10

        result = pbx.sync_ad_users()

        assert result["success"] is True
        assert result["phone_book_synced"] == 10

    def test_sync_ad_exception(self) -> None:
        """Exception during sync is caught and reported."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.enabled = True
        pbx.ad_integration.sync_users.side_effect = RuntimeError("LDAP connection failed")

        result = pbx.sync_ad_users()

        assert result["success"] is False
        assert "LDAP connection failed" in result["error"]
        assert result["synced_count"] == 0

    def test_sync_ad_reboot_failure(self) -> None:
        """Failed phone reboots are logged but don't break sync."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.enabled = True
        pbx.ad_integration.sync_users.return_value = {
            "synced_count": 1,
            "extensions_to_reboot": ["1001"],
        }
        pbx.phone_provisioning.reboot_phone.side_effect = RuntimeError("reboot failed")
        pbx.phone_book = None

        result = pbx.sync_ad_users()

        assert result["success"] is True
        assert result["rebooted_count"] == 0

    def test_sync_ad_no_phone_provisioning(self) -> None:
        """Sync works when phone_provisioning is not available."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.enabled = True
        pbx.ad_integration.sync_users.return_value = {
            "synced_count": 2,
            "extensions_to_reboot": ["1001"],
        }
        pbx.phone_provisioning = None
        pbx.phone_book = None

        result = pbx.sync_ad_users()

        assert result["success"] is True
        assert result["rebooted_count"] == 0

    def test_sync_ad_phone_book_not_enabled(self) -> None:
        """Phone book sync is skipped when phone_book is disabled."""
        pbx = _make_pbx_core_shell()
        pbx.ad_integration.enabled = True
        pbx.ad_integration.sync_users.return_value = 1
        pbx.phone_book.enabled = False

        result = pbx.sync_ad_users()

        assert result["success"] is True
        assert result["phone_book_synced"] == 0
