"""
Core PBX implementation
Central coordinator for all PBX functionality
"""

import re
import struct
import threading
import time
import traceback
import uuid
from datetime import datetime

from pbx.api.rest_api import PBXAPIServer
from pbx.core.call import CallManager
from pbx.features.call_parking import CallParkingSystem
from pbx.features.call_queue import QueueSystem
from pbx.features.call_recording import CallRecordingSystem
from pbx.features.cdr import CDRSystem
from pbx.features.conference import ConferenceSystem
from pbx.features.extensions import ExtensionRegistry
from pbx.features.find_me_follow_me import FindMeFollowMe
from pbx.features.fraud_detection import FraudDetectionSystem
from pbx.features.music_on_hold import MusicOnHold
from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.features.presence import PresenceSystem
from pbx.features.recording_retention import RecordingRetentionManager
from pbx.features.sip_trunk import SIPTrunkSystem
from pbx.features.time_based_routing import TimeBasedRouting
from pbx.features.voicemail import VoicemailSystem
from pbx.features.webhooks import WebhookEvent
from pbx.rtp.handler import RTPRelay
from pbx.sip.server import SIPServer
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB
from pbx.utils.logger import PBXLogger, get_logger


class PBXCore:
    """Main PBX system coordinator"""

    def __init__(self, config_file="config.yml"):
        """
        Initialize PBX core

        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_file)

        # Setup logging
        log_config = self.config.get("logging", {})
        PBXLogger().setup(
            log_level=log_config.get("level", "INFO"),
            log_file=log_config.get("file", "logs/pbx.log"),
            console=log_config.get("console", True),
        )
        self.logger = get_logger()

        # Check if quiet startup is enabled
        self.quiet_startup = self.config.get("logging.quiet_startup", False)

        # Track system start time for uptime calculation
        self.start_time = datetime.now()

        # Initialize database backend
        self.database = DatabaseBackend(self.config)
        self.registered_phones_db = None
        self.extension_db = None
        if self.database.connect():
            self.database.create_tables()
            from pbx.utils.database import ExtensionDB

            self.registered_phones_db = RegisteredPhonesDB(self.database)
            self.extension_db = ExtensionDB(self.database)
            self._log_startup(
                f"Database backend initialized successfully ({
                    self.database.db_type})"
            )
            self._log_startup(
                "Extensions, voicemail metadata, and phone registrations will be stored in database"
            )

            # Auto-seed critical extensions if they don't exist
            self._auto_seed_critical_extensions()

            # Clean up incomplete phone registrations at startup
            # Only phones with MAC, IP, and Extension should be retained
            success, count = self.registered_phones_db.cleanup_incomplete_registrations()
            if success and count > 0:
                self._log_startup(
                    f"Startup cleanup: Removed {count} incomplete phone registration(s)"
                )
        else:
            self.logger.warning("Database backend not available - running without database")
            self.logger.warning("Extensions will be loaded from config.yml only")
            self.logger.warning("Voicemails will be stored ONLY as files (no database metadata)")
            self.logger.warning("Phone registrations will not be persisted")

        # Initialize core components
        # Pass database to extension registry so it can load extensions from DB
        self.extension_registry = ExtensionRegistry(
            self.config, database=self.database if self.database.enabled else None
        )
        self.call_manager = CallManager()

        # Initialize QoS monitoring system first (needed by RTP relay)
        from pbx.features.qos_monitoring import QoSMonitor

        self.qos_monitor = QoSMonitor(self)

        self.rtp_relay = RTPRelay(
            self.config.get("server.rtp_port_range_start", 10000),
            self.config.get("server.rtp_port_range_end", 20000),
            qos_monitor=self.qos_monitor,
        )

        # Initialize SIP server
        self.sip_server = SIPServer(
            host=self.config.get(
                "server.sip_host", "0.0.0.0"
            ),  # nosec B104 - SIP server needs to bind to all interfaces
            port=self.config.get("server.sip_port", 5060),
            pbx_core=self,
        )

        # Initialize advanced features
        voicemail_path = self.config.get("voicemail.storage_path", "voicemail")
        self.voicemail_system = VoicemailSystem(
            storage_path=voicemail_path,
            config=self.config,
            database=self.database if hasattr(self, "database") and self.database.enabled else None,
        )
        self.conference_system = ConferenceSystem()
        self.recording_system = CallRecordingSystem(
            auto_record=self.config.get("features.call_recording", False)
        )
        self.queue_system = QueueSystem()
        self.presence_system = PresenceSystem()
        self.parking_system = CallParkingSystem()
        self.cdr_system = CDRSystem()
        self.moh_system = MusicOnHold()
        self.trunk_system = SIPTrunkSystem(config=self.config)

        # Initialize statistics engine for analytics
        from pbx.features.statistics import StatisticsEngine

        self.statistics_engine = StatisticsEngine(self.cdr_system)
        self._log_startup("Statistics and analytics engine initialized")
        self.logger.info("QoS monitoring system initialized and integrated with RTP relay")

        # Initialize auto attendant if enabled
        if self.config.get("features.auto_attendant", False):
            from pbx.features.auto_attendant import AutoAttendant

            self.auto_attendant = AutoAttendant(self.config, self)
            self.logger.info(
                f"Auto Attendant initialized on extension {
                    self.auto_attendant.get_extension()}"
            )
        else:
            self.auto_attendant = None

        # Initialize phone provisioning if enabled
        if self.config.get("provisioning.enabled", False):
            self.phone_provisioning = PhoneProvisioning(
                self.config, database=self.database if self.database.enabled else None
            )
            self._load_provisioning_devices()
        else:
            self.phone_provisioning = None

        # Initialize Active Directory integration
        if self.config.get("integrations.active_directory.enabled", False):
            from pbx.integrations.active_directory import ActiveDirectoryIntegration

            ad_config = {
                "integrations.active_directory.enabled": self.config.get(
                    "integrations.active_directory.enabled"
                ),
                "integrations.active_directory.server": self.config.get(
                    "integrations.active_directory.server"
                ),
                "integrations.active_directory.base_dn": self.config.get(
                    "integrations.active_directory.base_dn"
                ),
                "integrations.active_directory.bind_dn": self.config.get(
                    "integrations.active_directory.bind_dn"
                ),
                "integrations.active_directory.bind_password": self.config.get(
                    "integrations.active_directory.bind_password"
                ),
                "integrations.active_directory.use_ssl": self.config.get(
                    "integrations.active_directory.use_ssl", True
                ),
                "integrations.active_directory.auto_provision": self.config.get(
                    "integrations.active_directory.auto_provision", False
                ),
                "integrations.active_directory.user_search_base": self.config.get(
                    "integrations.active_directory.user_search_base"
                ),
                "integrations.active_directory.deactivate_removed_users": self.config.get(
                    "integrations.active_directory.deactivate_removed_users", True
                ),
                "config_file": config_file,
            }
            self.ad_integration = ActiveDirectoryIntegration(ad_config)
            if self.ad_integration.enabled:
                self._log_startup("Active Directory integration initialized")

                # Auto-sync users from AD at startup if auto_provision is
                # enabled
                if self.ad_integration.auto_provision:
                    self.logger.info(
                        "Auto-provisioning enabled - syncing users from Active Directory..."
                    )
                    try:
                        sync_result = self.ad_integration.sync_users(
                            extension_registry=self.extension_registry,
                            extension_db=self.extension_db,
                            phone_provisioning=None,  # Will be set after provisioning init
                        )

                        # Handle both int and dict return types
                        synced_count = (
                            sync_result
                            if isinstance(sync_result, int)
                            else sync_result.get("synced_count", 0)
                        )

                        if synced_count > 0:
                            self.logger.info(
                                f"Auto-synced {synced_count} extension(s) from Active Directory at startup"
                            )
                        else:
                            self.logger.warning(
                                "AD auto-sync completed but no extensions were synced"
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to auto-sync users from Active Directory at startup: {e}"
                        )
                        import traceback

                        self.logger.debug(traceback.format_exc())
            else:
                self.logger.warning(
                    "Active Directory integration enabled in config but failed to initialize"
                )
                self.ad_integration = None
        else:
            self.ad_integration = None

        # Initialize open-source integrations
        # Jitsi Meet - Video conferencing
        if self.config.get("integrations.jitsi.enabled", False):
            from pbx.integrations.jitsi import JitsiIntegration

            self.jitsi_integration = JitsiIntegration(self.config)
            if self.jitsi_integration.enabled:
                self._log_startup("Jitsi Meet video conferencing integration initialized")
        else:
            self.jitsi_integration = None

        # Matrix - Team messaging
        if self.config.get("integrations.matrix.enabled", False):
            from pbx.integrations.matrix import MatrixIntegration

            self.matrix_integration = MatrixIntegration(self.config)
            if self.matrix_integration.enabled:
                self._log_startup("Matrix team messaging integration initialized")
        else:
            self.matrix_integration = None

        # EspoCRM - Customer relationship management
        if self.config.get("integrations.espocrm.enabled", False):
            from pbx.integrations.espocrm import EspoCRMIntegration

            self.espocrm_integration = EspoCRMIntegration(self.config)
            if self.espocrm_integration.enabled:
                self._log_startup("EspoCRM integration initialized")
        else:
            self.espocrm_integration = None

        # Zoom integration (proprietary - requires license)
        if self.config.get("integrations.zoom.enabled", False):
            from pbx.integrations.zoom import ZoomIntegration

            self.zoom_integration = ZoomIntegration(self.config)
            if self.zoom_integration.enabled:
                self._log_startup("Zoom integration initialized")
        else:
            self.zoom_integration = None

        # Initialize phone book if enabled
        if self.config.get("features.phone_book.enabled", False):
            from pbx.features.phone_book import PhoneBook

            self.phone_book = PhoneBook(
                self.config, database=self.database if self.database.enabled else None
            )
            self.logger.info("Phone book feature initialized")
        else:
            self.phone_book = None

        # Initialize emergency notification system if enabled
        if self.config.get("features.emergency_notification.enabled", True):
            from pbx.features.emergency_notification import EmergencyNotificationSystem

            self.emergency_notification = EmergencyNotificationSystem(
                self, config=self.config, database=self.database if self.database.enabled else None
            )
            self.logger.info("Emergency notification system initialized")
        else:
            self.emergency_notification = None

        # Initialize paging system if enabled
        if self.config.get("features.paging.enabled", False):
            from pbx.features.paging import PagingSystem

            self.paging_system = PagingSystem(
                self.config, database=self.database if self.database.enabled else None
            )
            self._log_startup("Paging system initialized")
        else:
            self.paging_system = None

        # Initialize E911 location service if enabled
        if self.config.get("features.e911.enabled", False):
            from pbx.features.e911_location import E911LocationService

            self.e911_location = E911LocationService(config=self.config)
            self.logger.info("E911 location service initialized")
        else:
            self.e911_location = None

        # Initialize Kari's Law compliance (federal requirement for direct 911 dialing)
        if self.config.get("features.karis_law.enabled", True):
            from pbx.features.karis_law import KarisLawCompliance

            self.karis_law = KarisLawCompliance(self, config=self.config)
            self.logger.info("Kari's Law compliance initialized (direct 911 dialing enabled)")
        else:
            self.karis_law = None
            self.logger.warning("Kari's Law compliance DISABLED - not recommended for production")

        # Initialize webhook system
        from pbx.features.webhooks import WebhookSystem

        self.webhook_system = WebhookSystem(self.config)

        # Initialize WebRTC if enabled
        if self.config.get("features.webrtc.enabled", False):
            from pbx.features.webrtc import WebRTCGateway, WebRTCSignalingServer

            self.webrtc_signaling = WebRTCSignalingServer(self.config, self)
            self.webrtc_gateway = WebRTCGateway(self)
            self.logger.info("WebRTC browser calling initialized")
        else:
            self.webrtc_signaling = None
            self.webrtc_gateway = None

        # Initialize CRM integration if enabled
        if self.config.get("features.crm_integration.enabled", False):
            from pbx.features.crm_integration import CRMIntegration

            self.crm_integration = CRMIntegration(self.config, self)
            self.logger.info("CRM integration and screen pop initialized")
        else:
            self.crm_integration = None

        # Initialize hot-desking if enabled
        if self.config.get("features.hot_desking.enabled", False):
            from pbx.features.hot_desking import HotDeskingSystem

            self.hot_desking = HotDeskingSystem(self.config, self)
            self.logger.info("Hot-desking system initialized")
        else:
            self.hot_desking = None

        # Initialize Find Me/Follow Me
        self.find_me_follow_me = FindMeFollowMe(
            config=self.config, database=self.database if self.database.enabled else None
        )
        if self.find_me_follow_me.enabled:
            self.logger.info("Find Me/Follow Me initialized")

        # Initialize Time-Based Routing
        self.time_based_routing = TimeBasedRouting(config=self.config)
        if self.time_based_routing.enabled:
            self.logger.info("Time-based routing initialized")

        # Initialize Recording Retention Manager
        self.recording_retention = RecordingRetentionManager(config=self.config)
        if self.recording_retention.enabled:
            self.logger.info("Recording retention manager initialized")

        # Initialize Fraud Detection System
        self.fraud_detection = FraudDetectionSystem(config=self.config)
        if self.fraud_detection.enabled:
            self.logger.info("Fraud detection system initialized")

        # Initialize Callback Queue
        from pbx.features.callback_queue import CallbackQueue

        self.callback_queue = CallbackQueue(config=self.config, database=self.database)
        if self.callback_queue.enabled:
            self.logger.info("Callback queue system initialized")

        # Initialize Mobile Push Notifications
        from pbx.features.mobile_push import MobilePushNotifications

        self.mobile_push = MobilePushNotifications(config=self.config, database=self.database)
        if self.mobile_push.enabled:
            self.logger.info("Mobile push notifications initialized")

        # Initialize Recording Announcements
        from pbx.features.recording_announcements import RecordingAnnouncements

        self.recording_announcements = RecordingAnnouncements(
            config=self.config, database=self.database
        )
        if self.recording_announcements.enabled:
            self.logger.info("Recording announcements initialized")

        # Initialize MFA if enabled
        if self.config.get("security.mfa.enabled", False):
            from pbx.features.mfa import MFAManager

            self.mfa_manager = MFAManager(
                database=(
                    self.database if hasattr(self, "database") and self.database.enabled else None
                ),
                config=self.config,
            )
            self.logger.info("Multi-Factor Authentication (MFA) initialized")
        else:
            self.mfa_manager = None

        # Initialize enhanced threat detection if enabled
        if self.config.get("security.threat_detection.enabled", True):
            from pbx.utils.security import get_threat_detector

            self.threat_detector = get_threat_detector(
                database=(
                    self.database if hasattr(self, "database") and self.database.enabled else None
                ),
                config=self.config,
            )
            self.logger.info("Enhanced threat detection initialized")
        else:
            self.threat_detector = None

        # Initialize security runtime monitor (always enabled for FIPS compliance)
        # Note: webhook_system is initialized earlier, so it's always available
        from pbx.utils.security_monitor import get_security_monitor

        self.security_monitor = get_security_monitor(
            config=self.config, webhook_system=self.webhook_system
        )
        self.logger.info("Security runtime monitor initialized")

        # Initialize DND scheduler if enabled
        if self.config.get("features.dnd_scheduling.enabled", False):
            from pbx.features.dnd_scheduling import get_dnd_scheduler

            # Get Outlook integration if available
            outlook = None
            if hasattr(self, "integrations") and "outlook" in self.integrations:
                outlook = self.integrations["outlook"]

            self.dnd_scheduler = get_dnd_scheduler(
                presence_system=self.presence_system if hasattr(self, "presence_system") else None,
                outlook_integration=outlook,
                config=self.config,
            )
            self._log_startup("DND Scheduler initialized")
        else:
            self.dnd_scheduler = None

        # Initialize skills-based routing if enabled
        if self.config.get("features.skills_routing.enabled", False):
            from pbx.features.skills_routing import get_skills_router

            self.skills_router = get_skills_router(
                database=(
                    self.database if hasattr(self, "database") and self.database.enabled else None
                ),
                config=self.config,
            )
            self.logger.info("Skills-Based Routing initialized")
        else:
            self.skills_router = None

        # Initialize API server
        api_host = self.config.get(
            "api.host", "0.0.0.0"
        )  # nosec B104 - API server needs to bind to all interfaces
        api_port = self.config.get("api.port", 8080)
        self.api_server = PBXAPIServer(self, api_host, api_port)

        self.running = False

        self.logger.info("PBX Core initialized with all features")

    def _log_startup(self, message: str, level: str = "info"):
        """
        Log a startup message, respecting quiet_startup setting

        Args:
            message: The message to log
            level: Log level ('info', 'warning', 'error', 'debug')
        """
        if self.quiet_startup and level == "info":
            # In quiet mode, log INFO messages as DEBUG
            self.logger.debug(f"[STARTUP] {message}")
        else:
            # Normal logging
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(message)

    def _auto_seed_critical_extensions(self):
        """
        Auto-seed critical extensions at startup if they don't exist

        This ensures essential extensions (auto-attendant, webrtc-admin, operator)
        are always available without manual setup.
        """
        if not self.extension_db:
            return

        from pbx.utils.encryption import get_encryption

        # Initialize encryption for password hashing
        fips_mode = self.config.get("security.fips_mode", False)
        encryption = get_encryption(fips_mode)

        # Define critical extensions that should always exist
        # These use secure default passwords that MUST be changed after first
        # login
        critical_extensions = [
            {
                "number": "0",
                "name": "Auto Attendant",
                "email": "autoattendant@pbx.local",
                # Random secure default
                "password": "ChangeMe-AutoAttendant-" + str(uuid.uuid4())[:8],
                "allow_external": True,
                "voicemail_pin": "0000",
                "is_admin": False,
                "description": "Automated greeting and call routing system",
            },
            {
                "number": "1001",
                "name": "Operator / WebAdmin Phone",
                "email": "operator@pbx.local",
                # Random secure default
                "password": "ChangeMe-Operator-" + str(uuid.uuid4())[:8],
                "allow_external": True,
                "voicemail_pin": "1001",
                "is_admin": True,
                "description": "Primary operator extension and web-based admin phone",
            },
        ]

        seeded_count = 0

        for ext_config in critical_extensions:
            number = ext_config["number"]

            # Check if extension already exists
            existing = self.extension_db.get(number)
            if existing:
                continue  # Skip if already exists

            try:
                # Hash the password
                password_hash, _ = encryption.hash_password(ext_config["password"])

                # Add extension to database
                success = self.extension_db.add(
                    number=number,
                    name=ext_config["name"],
                    password_hash=password_hash,
                    email=ext_config.get("email"),
                    allow_external=ext_config.get("allow_external", True),
                    voicemail_pin=ext_config.get("voicemail_pin"),
                    ad_synced=False,
                    ad_username=None,
                    is_admin=ext_config.get("is_admin", False),
                )

                if success:
                    self.logger.info(
                        f"Auto-seeded critical extension {number}: {ext_config['name']}"
                    )
                    seeded_count += 1

                    # Log password for first-time setup
                    if number == "1001":
                        self.logger.warning("=" * 70)
                        self.logger.warning("FIRST-TIME SETUP - EXTENSION 1001 CREDENTIALS")
                        self.logger.warning("=" * 70)
                        self.logger.warning(f"Extension: 1001")
                        self.logger.warning(
                            f"Password:  {
                                ext_config['password']}"
                        )
                        self.logger.warning(
                            f"Voicemail PIN: {
                                ext_config['voicemail_pin']}"
                        )
                        self.logger.warning("")
                        self.logger.warning("⚠️  CHANGE THIS PASSWORD IMMEDIATELY via admin panel!")
                        self.logger.warning(
                            "   Access admin panel: https://<your-server-ip>:8080/admin/"
                        )
                        self.logger.warning("=" * 70)

            except Exception as e:
                self.logger.error(f"Failed to auto-seed extension {number}: {e}")

        if seeded_count > 0:
            self.logger.info(f"Auto-seeded {seeded_count} critical extension(s) at startup")

    def _load_provisioning_devices(self):
        """Load provisioning devices from configuration"""
        if not self.phone_provisioning:
            return

        devices_config = self.config.get("provisioning.devices", [])
        for device_config in devices_config:
            mac = device_config.get("mac")
            extension = device_config.get("extension")
            vendor = device_config.get("vendor")
            model = device_config.get("model")

            if all([mac, extension, vendor, model]):
                try:
                    self.phone_provisioning.register_device(mac, extension, vendor, model)
                    self.logger.info(f"Loaded provisioning device {mac} for extension {extension}")
                except Exception as e:
                    self.logger.error(f"Failed to load provisioning device {mac}: {e}")

    def start(self):
        """Start PBX system"""
        self.logger.info("Starting PBX system...")

        # Enforce security requirements before starting
        if hasattr(self, "security_monitor"):
            self.logger.info("Enforcing security requirements...")
            if not self.security_monitor.enforce_security_requirements():
                self.logger.error("CRITICAL: Security enforcement failed - system cannot start")
                return False
            self.logger.info("✓ Security requirements verified")

        # Start SIP server
        if not self.sip_server.start():
            self.logger.error("Failed to start SIP server")
            return False

        # Start API server
        if not self.api_server.start():
            self.logger.warning("Failed to start API server (non-critical)")

        # Start DND scheduler
        if self.dnd_scheduler:
            self.dnd_scheduler.start()

        # Register SIP trunks
        self.trunk_system.register_all()

        # Start security runtime monitor
        if hasattr(self, "security_monitor"):
            self.security_monitor.start()
            self.logger.info("Security runtime monitoring active")

        self.running = True
        self.logger.info("PBX system started successfully")
        return True

    def stop(self):
        """Stop PBX system"""
        self.logger.info("Stopping PBX system...")
        self.running = False

        # Stop security monitor
        if hasattr(self, "security_monitor"):
            self.security_monitor.stop()

        # Stop DND scheduler
        if self.dnd_scheduler:
            self.dnd_scheduler.stop()

        # Stop API server
        self.api_server.stop()

        # Stop SIP server
        self.sip_server.stop()

        # End all active calls
        for call in self.call_manager.get_active_calls():
            self.call_manager.end_call(call.call_id)
            self.rtp_relay.release_relay(call.call_id)

            # Stop any recordings
            if self.recording_system.is_recording(call.call_id):
                self.recording_system.stop_recording(call.call_id)

        self.logger.info("PBX system stopped")

    def register_extension(self, from_header, addr, user_agent=None, contact=None):
        """
        Register extension and store phone information

        Args:
            from_header: SIP From header
            addr: Network address (host, port)
            user_agent: User-Agent header from SIP REGISTER
            contact: Contact header from SIP REGISTER

        Returns:
            True if registration successful
        """
        # Parse extension number from header
        # Format: "Display Name" <sip:1001@host>
        match = re.search(r"sip:(\d+)@", from_header)
        if match:
            extension_number = match.group(1)

            # Verify extension exists - check database first, then config
            extension_exists = False

            # Check extensions database table first (if available)
            if self.extension_db:
                try:
                    db_extension = self.extension_db.get(extension_number)
                    if db_extension:
                        extension_exists = True
                        self.logger.debug(f"Extension {extension_number} found in database")

                        # Ensure extension is loaded in registry (if not
                        # already)
                        if not self.extension_registry.get(extension_number):
                            # Create Extension object from database data using
                            # helper method
                            extension_obj = ExtensionRegistry.create_extension_from_db(db_extension)
                            self.extension_registry.extensions[extension_number] = extension_obj
                            self.logger.debug(
                                f"Loaded extension {extension_number} into registry from database"
                            )
                except Exception as e:
                    self.logger.debug(f"Error checking extension in database: {e}")

            # Fall back to config if not found in database or database not
            # available
            if not extension_exists:
                extension = self.config.get_extension(extension_number)
                if extension:
                    extension_exists = True
                    self.logger.debug(f"Extension {extension_number} found in config")

            if extension_exists:
                self.extension_registry.register(extension_number, addr)
                self.logger.info(f"Extension {extension_number} registered from {addr}")

                # Store phone registration in database
                if self.registered_phones_db:
                    ip_address = addr[0]  # Extract IP from (host, port) tuple

                    # Try to extract MAC address from Contact URI or User-Agent
                    # Common patterns:
                    # - Contact: <sip:1001@192.168.1.100:5060;mac=00:11:22:33:44:55>
                    # - Contact: <sip:1001@192.168.1.100:5060>;+sip.instance="<urn:uuid:00112233-4455-6677-8899-aabbccddeeff>"
                    # - User-Agent: Yealink SIP-T46S 66.85.0.5 00:15:65:12:34:56
                    mac_address = self._extract_mac_address(contact, user_agent)

                    try:
                        _, stored_mac = self.registered_phones_db.register_phone(
                            extension_number=extension_number,
                            ip_address=ip_address,
                            mac_address=mac_address,
                            user_agent=user_agent,
                            contact_uri=contact,
                        )

                        if stored_mac:
                            self.logger.info(
                                f"Stored phone registration: ext={extension_number}, ip={ip_address}, mac={stored_mac}"
                            )
                        else:
                            self.logger.info(
                                f"Stored phone registration: ext={extension_number}, ip={ip_address} (no MAC)"
                            )
                    except Exception as e:
                        self.logger.error(f"Failed to store phone registration in database: {e}")
                        self.logger.error(f"  Extension: {extension_number}")
                        self.logger.error(f"  IP Address: {ip_address}")
                        self.logger.error(f"  MAC Address: {mac_address}")
                        self.logger.error(f"  User Agent: {user_agent}")
                        self.logger.error(f"  Contact URI: {contact}")
                        self.logger.error(
                            f"  Traceback: {
                                traceback.format_exc()}"
                        )

                # Trigger webhook event
                self.webhook_system.trigger_event(
                    WebhookEvent.EXTENSION_REGISTERED,
                    {
                        "extension": extension_number,
                        "ip_address": addr[0],
                        "port": addr[1],
                        "user_agent": user_agent,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                return True
            else:
                self.logger.warning(f"Unknown extension {extension_number} attempted registration")
                return False

        self.logger.warning(f"Could not parse extension from {from_header}")
        return False

    def _extract_mac_address(self, contact, user_agent):
        """
        Extract MAC address from SIP headers

        Args:
            contact: Contact header
            user_agent: User-Agent header

        Returns:
            MAC address string or None
        """
        mac_address = None

        # Try to extract from Contact header
        if contact:
            # Pattern 1: mac=XX:XX:XX:XX:XX:XX or mac=XX-XX-XX-XX-XX-XX
            mac_match = re.search(r"mac=([0-9a-fA-F:]{17}|[0-9a-fA-F-]{17})", contact)
            if mac_match:
                mac_address = mac_match.group(1).lower()

            # Pattern 2: Instance ID that may contain MAC
            # <urn:uuid:00112233-4455-6677-8899-aabbccddeeff>
            instance_match = re.search(
                r'sip\.instance="<urn:uuid:([0-9a-f-]+)>"', contact, re.IGNORECASE
            )
            if not mac_address and instance_match:
                # Some devices use UUID derived from MAC
                uuid_str = instance_match.group(1).replace("-", "")
                # Last 12 chars might be MAC
                if len(uuid_str) >= 12:
                    potential_mac = uuid_str[-12:]
                    # Format as MAC: XX:XX:XX:XX:XX:XX
                    mac_address = ":".join([potential_mac[i : i + 2] for i in range(0, 12, 2)])

        # Try to extract from User-Agent
        if not mac_address and user_agent:
            # Pattern: User-Agent might end with MAC like "...
            # 00:15:65:12:34:56"
            mac_match = re.search(r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", user_agent)
            if mac_match:
                mac_address = mac_match.group(0).lower()

        # Normalize MAC address format (remove separators, lowercase)
        if mac_address:
            mac_address = mac_address.replace(":", "").replace("-", "").lower()

        return mac_address

    def _detect_phone_model(self, user_agent):
        """
        Detect phone model from User-Agent string

        Args:
            user_agent: User-Agent header string

        Returns:
            Phone model identifier string or None
            Possible values: 'ZIP33G', 'ZIP37G', or None for unknown/other
        """
        if not user_agent:
            return None

        user_agent_upper = user_agent.upper()

        # Check for Zultys ZIP33G
        if "ZIP33G" in user_agent_upper or "ZIP 33G" in user_agent_upper:
            return "ZIP33G"

        # Check for Zultys ZIP37G
        if "ZIP37G" in user_agent_upper or "ZIP 37G" in user_agent_upper:
            return "ZIP37G"

        return None

    def _get_codecs_for_phone_model(self, phone_model, default_codecs=None):
        """
        Get appropriate codec list for a specific phone model

        Args:
            phone_model: Phone model identifier (from _detect_phone_model)
            default_codecs: Default codecs to use if no specific requirement

        Returns:
            List of codec payload types as strings
        """
        # Get DTMF payload type from config (default 101)
        dtmf_payload_type = self.config.get("features.dtmf.payload_type", 101)
        dtmf_pt_str = str(dtmf_payload_type)

        if phone_model == "ZIP37G":
            # ZIP37G: Use PCMU/PCMA only
            # Payload types: 0=PCMU, 8=PCMA
            codecs = ["0", "8", dtmf_pt_str]
            self.logger.debug(f"Using ZIP37G codec set: PCMU/PCMA ({codecs})")
            return codecs

        elif phone_model == "ZIP33G":
            # ZIP33G: Use G726, G729, G722
            # Payload types: 2=G726-32, 18=G729, 9=G722
            # Also include G726 variants: 112=G726-16, 113=G726-24, 114=G726-40
            codecs = ["2", "18", "9", "114", "113", "112", dtmf_pt_str]
            self.logger.debug(f"Using ZIP33G codec set: G726/G729/G722 ({codecs})")
            return codecs

        # For unknown or other phones, use default behavior
        if default_codecs:
            self.logger.debug(f"Using default codec set for unknown phone: {default_codecs}")
            return default_codecs

        # Ultimate fallback - standard codec list
        return ["0", "8", "9", "18", "2", dtmf_pt_str]

    def _get_phone_user_agent(self, extension_number):
        """
        Get User-Agent string for a registered phone by extension number

        Args:
            extension_number: Extension number string

        Returns:
            User-Agent string or None if not found
        """
        if not self.registered_phones_db or not self.database:
            return None

        try:
            # Query registered_phones table for this extension
            # Build query with appropriate placeholder for database type
            if self.database.db_type == "postgresql":
                query = """
                SELECT user_agent FROM registered_phones 
                WHERE extension_number = %s
                ORDER BY last_registered DESC
                LIMIT 1
                """
            else:
                query = """
                SELECT user_agent FROM registered_phones 
                WHERE extension_number = ?
                ORDER BY last_registered DESC
                LIMIT 1
                """

            result = self.database.fetch_one(query, (extension_number,))
            if result and result.get("user_agent"):
                return result["user_agent"]
        except Exception as e:
            self.logger.debug(f"Error retrieving User-Agent for extension {extension_number}: {e}")

        return None

    def _get_dtmf_payload_type(self):
        """
        Get DTMF payload type from configuration

        Returns:
            DTMF payload type as integer (default: 101)
        """
        return self.config.get("features.dtmf.payload_type", 101)

    def _get_ilbc_mode(self):
        """
        Get iLBC mode from configuration

        Returns:
            iLBC mode (20 or 30 ms) as integer (default: 30)
        """
        return self.config.get("codecs.ilbc.mode", 30)

    def route_call(self, from_header, to_header, call_id, message, from_addr):
        """
        Route call from one extension to another

        Args:
            from_header: From SIP header
            to_header: To SIP header
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Address tuple of caller

        Returns:
            True if call was routed successfully
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        # Parse extension numbers - handle both regular extensions and special
        # patterns
        from_match = re.search(r"sip:(\d+)@", from_header)
        # Allow * prefix for voicemail access (e.g., *1001), but validate
        # format
        to_match = re.search(r"sip:(\*?\d+)@", to_header)

        if not from_match or not to_match:
            self.logger.warning(f"Could not parse extensions from headers")
            return False

        from_ext = from_match.group(1)
        to_ext = to_match.group(1)

        # Check if this is an emergency call (911) - Kari's Law compliance
        # Must be handled first for immediate routing
        if self.karis_law and self.karis_law.is_emergency_number(to_ext):
            return self._handle_emergency_call(from_ext, to_ext, call_id, message, from_addr)

        # Check if this is an auto attendant call (extension 0)
        if self.auto_attendant and to_ext == self.auto_attendant.get_extension():
            return self._handle_auto_attendant(from_ext, to_ext, call_id, message, from_addr)

        # Check if this is a voicemail access call (*xxxx pattern)
        # Validate format: must be * followed by exactly 3 or 4 digits
        if (
            to_ext.startswith("*")
            and len(to_ext) >= 4
            and len(to_ext) <= 5
            and to_ext[1:].isdigit()
        ):
            return self._handle_voicemail_access(from_ext, to_ext, call_id, message, from_addr)

        # Check if this is a paging call (7xx pattern or all-call)
        if self.paging_system and self.paging_system.is_paging_extension(to_ext):
            return self._handle_paging(from_ext, to_ext, call_id, message, from_addr)

        # Check if destination extension is registered
        if not self.extension_registry.is_registered(to_ext):
            self.logger.warning(f"Extension {to_ext} is not registered")
            return False

        # Check dialplan
        if not self._check_dialplan(to_ext):
            self.logger.warning(f"Extension {to_ext} not allowed by dialplan")
            return False

        # Parse SDP from caller's INVITE
        caller_sdp = None
        caller_codecs = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()

            if caller_sdp:
                self.logger.info(
                    f"Caller RTP: {
                        caller_sdp['address']}:{
                        caller_sdp['port']}"
                )
                # Extract caller's codec list to maintain codec compatibility
                caller_codecs = caller_sdp.get("formats", None)
                if caller_codecs:
                    self.logger.info(f"Caller codecs: {caller_codecs}")

        # Create call
        call = self.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message  # Store original INVITE for later response

        # Start CDR record for analytics
        self.cdr_system.start_record(call_id, from_ext, to_ext)

        # Trigger webhook event
        self.webhook_system.trigger_event(
            WebhookEvent.CALL_STARTED,
            {
                "call_id": call_id,
                "from_extension": from_ext,
                "to_extension": to_ext,
                "timestamp": call.start_time.isoformat() if call.start_time else None,
            },
        )

        # Allocate RTP relay
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports

            # Store caller's RTP info and set endpoint immediately to avoid
            # dropping early packets
            if caller_sdp:
                call.caller_rtp = caller_sdp
                call.caller_addr = from_addr

                # Set caller's endpoint immediately to enable early RTP packet learning
                # This prevents dropping packets that arrive before the 200 OK
                # response
                caller_endpoint = (caller_sdp["address"], caller_sdp["port"])
                relay_info = self.rtp_relay.active_relays.get(call_id)
                if relay_info:
                    handler = relay_info["handler"]
                    # Set only endpoint A for now; endpoint B will be set after
                    # 200 OK
                    handler.set_endpoints(caller_endpoint, None)
                    self.logger.info(
                        f"RTP relay allocated on port {
                            rtp_ports[0]}, caller endpoint set to {caller_endpoint}"
                    )

        # Get destination extension's address
        dest_ext_obj = self.extension_registry.get(to_ext)
        if not dest_ext_obj or not dest_ext_obj.address:
            self.logger.error(f"Cannot get address for extension {to_ext}")
            return False

        # Check if destination is a WebRTC extension
        is_webrtc_destination = (
            dest_ext_obj.address
            and isinstance(dest_ext_obj.address, tuple)
            and len(dest_ext_obj.address) == 2
            and dest_ext_obj.address[0] == "webrtc"
        )

        if is_webrtc_destination:
            # Route call to WebRTC client
            # Extract session ID from address tuple
            session_id = dest_ext_obj.address[1]
            self.logger.info(f"Routing call to WebRTC extension {to_ext} (session: {session_id})")

            if self.webrtc_gateway:
                # Get caller's SDP if available
                caller_sdp_str = message.body if message.body else None

                # Route the call through WebRTC gateway
                success = self.webrtc_gateway.receive_call(
                    session_id=session_id,
                    call_id=call_id,
                    caller_sdp=caller_sdp_str,
                    webrtc_signaling=(
                        self.webrtc_signaling if hasattr(self, "webrtc_signaling") else None
                    ),
                )

                if success:
                    self.logger.info(f"Call {call_id} routed to WebRTC session {session_id}")
                    # Note: The WebRTC client will be notified via the signaling channel
                    # and should send an answer when the user accepts the call
                    return True
                else:
                    self.logger.error(f"Failed to route call to WebRTC session {session_id}")
                    return False
            else:
                self.logger.error("WebRTC gateway not available for routing call")
                return False

        # Build SDP for forwarding INVITE to callee
        # Use the server's external IP address for SDP
        server_ip = self._get_server_ip()

        if rtp_ports:
            # Determine which codecs to offer based on callee's phone model
            # Get callee's User-Agent to detect phone model
            callee_user_agent = self._get_phone_user_agent(to_ext)
            callee_phone_model = self._detect_phone_model(callee_user_agent)

            # Select appropriate codecs for the callee's phone
            # - ZIP37G: PCMU/PCMA only
            # - ZIP33G: G726/G729/G722 only
            # - Other phones: use caller's codecs (existing behavior)
            codecs_for_callee = self._get_codecs_for_phone_model(
                callee_phone_model, default_codecs=caller_codecs
            )

            if callee_phone_model:
                self.logger.info(
                    f"Detected callee phone model: {callee_phone_model}, "
                    f"offering codecs: {codecs_for_callee}"
                )

            # Create new INVITE with PBX's RTP endpoint in SDP
            # Get DTMF payload type from config
            dtmf_payload_type = self._get_dtmf_payload_type()
            ilbc_mode = self._get_ilbc_mode()
            callee_sdp_body = SDPBuilder.build_audio_sdp(
                server_ip,
                rtp_ports[0],
                session_id=call_id,
                codecs=codecs_for_callee,
                dtmf_payload_type=dtmf_payload_type,
                ilbc_mode=ilbc_mode,
            )

            # Forward INVITE to callee
            invite_to_callee = SIPMessageBuilder.build_request(
                method="INVITE",
                uri=f"sip:{to_ext}@{server_ip}",
                from_addr=from_header,
                to_addr=to_header,
                call_id=call_id,
                cseq=int(message.get_header("CSeq").split()[0]),
                body=callee_sdp_body,
            )

            # Add required headers
            invite_to_callee.set_header("Via", message.get_header("Via"))
            invite_to_callee.set_header(
                "Contact",
                f"<sip:{from_ext}@{server_ip}:{self.config.get('server.sip_port', 5060)}>",
            )
            invite_to_callee.set_header("Content-Type", "application/sdp")
            
            # Add caller ID headers (P-Asserted-Identity and Remote-Party-ID) if configured
            if self.config.get("sip.caller_id.send_p_asserted_identity", True) or \
               self.config.get("sip.caller_id.send_remote_party_id", True):
                # Get caller's display name from extension
                caller_ext_obj = self.extension_registry.get(from_ext)
                display_name = from_ext  # Default to extension number
                if caller_ext_obj:
                    # Try to get name from extension object
                    display_name = getattr(caller_ext_obj, 'name', from_ext)
                    if not display_name or display_name == "":
                        display_name = from_ext
                
                # Add caller ID headers for line identification
                SIPMessageBuilder.add_caller_id_headers(
                    invite_to_callee,
                    from_ext,
                    display_name,
                    server_ip
                )
                self.logger.debug(f"Added caller ID headers: {display_name} <{from_ext}>")
            
            # Add MAC address header if configured
            if self.config.get("sip.device.send_mac_address", True):
                # Try to get MAC address from registered phones database
                mac_address = None
                if self.registered_phones_db:
                    try:
                        phone_info = self.registered_phones_db.get_phone_by_extension(from_ext)
                        if phone_info and phone_info.get('mac_address'):
                            mac_address = phone_info['mac_address']
                    except Exception as e:
                        self.logger.debug(f"Could not retrieve MAC for extension {from_ext}: {e}")
                
                # Also check if MAC was sent in the original INVITE
                if not mac_address and self.config.get("sip.device.accept_mac_in_invite", True):
                    x_mac = message.get_header("X-MAC-Address")
                    if x_mac:
                        mac_address = x_mac
                        self.logger.debug(f"Using MAC from incoming INVITE: {mac_address}")
                
                # Add MAC header if we found one
                if mac_address:
                    SIPMessageBuilder.add_mac_address_header(invite_to_callee, mac_address)
                    self.logger.debug(f"Added X-MAC-Address header: {mac_address}")

            # Send to destination
            self.sip_server._send_message(invite_to_callee.build(), dest_ext_obj.address)

            # Store callee address for later use (e.g., to send CANCEL if
            # routing to voicemail)
            call.callee_addr = dest_ext_obj.address
            call.callee_invite = invite_to_callee  # Store the INVITE for CANCEL reference

            self.logger.info(
                f"Forwarded INVITE to {to_ext} at {
                    dest_ext_obj.address}"
            )
            self.logger.info(
                f"Routing call {call_id}: {from_ext} -> {to_ext} via RTP relay {rtp_ports[0]}"
            )

            # Start no-answer timer to route to voicemail if not answered
            no_answer_timeout = self.config.get("voicemail.no_answer_timeout", 30)
            call.no_answer_timer = threading.Timer(
                no_answer_timeout, self._handle_no_answer, args=(call_id,)
            )
            call.no_answer_timer.start()
            self.logger.info(f"Started no-answer timer ({no_answer_timeout}s) for call {call_id}")

        return True

    def _get_server_ip(self):
        """
        Get server's IP address for SDP

        Returns:
            Server IP address as string
        """
        # First, try to get configured external IP
        external_ip = self.config.get("server.external_ip")
        if external_ip:
            return external_ip

        # Fallback: try to detect local IP
        import socket

        try:
            # Create a socket to determine the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"  # Last resort fallback

    def handle_callee_answer(self, call_id, response_message, callee_addr):
        """
        Handle when callee answers the call

        Args:
            call_id: Call identifier
            response_message: 200 OK response from callee
            callee_addr: Callee's address
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.error(f"Call {call_id} not found")
            return

        # Parse callee's SDP from 200 OK
        callee_sdp = None
        if response_message.body:
            callee_sdp_obj = SDPSession()
            callee_sdp_obj.parse(response_message.body)
            callee_sdp = callee_sdp_obj.get_audio_info()

            if callee_sdp:
                self.logger.info(
                    f"Callee RTP: {
                        callee_sdp['address']}:{
                        callee_sdp['port']}"
                )
                call.callee_rtp = callee_sdp
                call.callee_addr = callee_addr

        # Now we have both endpoints, complete the RTP relay setup
        # Note: caller endpoint (A) was already set when INVITE was received
        if call.caller_rtp and call.callee_rtp and call.rtp_ports:
            caller_endpoint = (call.caller_rtp["address"], call.caller_rtp["port"])
            callee_endpoint = (call.callee_rtp["address"], call.callee_rtp["port"])

            # Set both endpoints (caller was already set, but setting again is safe)
            # This ensures callee endpoint (B) is now known for bidirectional
            # relay
            self.rtp_relay.set_endpoints(call_id, caller_endpoint, callee_endpoint)
            self.logger.info(f"RTP relay connected for call {call_id}")

        # Cancel no-answer timer if it's running
        if call and call.no_answer_timer:
            call.no_answer_timer.cancel()
            self.logger.info(f"Cancelled no-answer timer for call {call_id}")

        # Mark call as connected
        call.connect()

        # Mark CDR as answered for analytics
        self.cdr_system.mark_answered(call_id)

        # Send 200 OK back to caller with PBX's RTP endpoint
        server_ip = self._get_server_ip()

        if call.rtp_ports and call.caller_addr:
            # Determine which codecs to offer based on caller's phone model
            # Get caller's User-Agent to detect phone model
            caller_user_agent = self._get_phone_user_agent(call.from_extension)
            caller_phone_model = self._detect_phone_model(caller_user_agent)

            # Extract caller's codecs from the original INVITE
            caller_codecs = call.caller_rtp.get("formats", None) if call.caller_rtp else None

            # Select appropriate codecs for the caller's phone
            # - ZIP37G: PCMU/PCMA only
            # - ZIP33G: G726/G729/G722 only
            # - Other phones: use caller's codecs (existing behavior)
            codecs_for_caller = self._get_codecs_for_phone_model(
                caller_phone_model, default_codecs=caller_codecs
            )

            if caller_phone_model:
                self.logger.info(
                    f"Detected caller phone model: {caller_phone_model}, "
                    f"offering codecs in 200 OK: {codecs_for_caller}"
                )

            # Build SDP for caller (with PBX RTP endpoint)
            # Get DTMF payload type from config
            dtmf_payload_type = self._get_dtmf_payload_type()
            ilbc_mode = self._get_ilbc_mode()
            caller_response_sdp = SDPBuilder.build_audio_sdp(
                server_ip,
                call.rtp_ports[0],
                session_id=call_id,
                codecs=codecs_for_caller,
                dtmf_payload_type=dtmf_payload_type,
                ilbc_mode=ilbc_mode,
            )

            # Build 200 OK for caller using original INVITE
            if call.original_invite:
                ok_response = SIPMessageBuilder.build_response(
                    200, "OK", call.original_invite, body=caller_response_sdp
                )
                ok_response.set_header("Content-Type", "application/sdp")

                # Build Contact header
                sip_port = self.config.get("server.sip_port", 5060)
                contact_uri = f"<sip:{
                    call.to_extension}@{server_ip}:{sip_port}>"
                ok_response.set_header("Contact", contact_uri)

                # Send to caller
                self.sip_server._send_message(ok_response.build(), call.caller_addr)
                self.logger.info(f"Sent 200 OK to caller for call {call_id}")

    def end_call(self, call_id):
        """
        End call

        Args:
            call_id: Call identifier
        """
        call = self.call_manager.get_call(call_id)
        if call:
            self.logger.info(f"Ending call {call_id}")

            # If this is a voicemail recording, complete it first
            if call.routed_to_voicemail and hasattr(call, "voicemail_recorder"):
                # Cancel the timer if it exists
                if hasattr(call, "voicemail_timer") and call.voicemail_timer:
                    call.voicemail_timer.cancel()

                # Get the recorder
                recorder = call.voicemail_recorder
                if recorder and recorder.running:
                    # Stop recording
                    recorder.stop()

                    # Get recorded audio
                    audio_data = recorder.get_recorded_audio()
                    duration = recorder.get_duration()

                    if audio_data and len(audio_data) > 0:
                        # Build proper WAV file header for the recorded audio
                        wav_data = self._build_wav_file(audio_data)

                        # Save to voicemail system
                        self.voicemail_system.save_message(
                            extension_number=call.to_extension,
                            caller_id=call.from_extension,
                            audio_data=wav_data,
                            duration=duration,
                        )
                        self.logger.info(
                            f"Saved voicemail (on hangup) for extension {
                                call.to_extension} from {
                                call.from_extension}, duration: {duration}s"
                        )
                    else:
                        self.logger.warning(f"No audio recorded for voicemail on call {call_id}")

            self.call_manager.end_call(call_id)
            self.rtp_relay.release_relay(call_id)

            # End CDR record for analytics
            self.cdr_system.end_record(call_id, hangup_cause="normal_clearing")

    def handle_dtmf_info(self, call_id, dtmf_digit):
        """
        Handle DTMF digit received via SIP INFO message

        This method queues DTMF digits received via out-of-band SIP INFO
        signaling for processing by IVR systems (voicemail, auto-attendant).

        Args:
            call_id: Call identifier
            dtmf_digit: DTMF digit ('0'-'9', '*', '#', 'A'-'D')

        Note:
            INFRASTRUCTURE ONLY - IVR Integration Pending:
            The IVR session loops (_voicemail_ivr_session, _auto_attendant_session)
            need to be updated to check call.dtmf_info_queue in addition to in-band
            DTMF detection. This method provides the queueing infrastructure.

            To complete SIP INFO DTMF support, update IVR loops to:
            1. Check if hasattr(call, 'dtmf_info_queue') and call.dtmf_info_queue
            2. Pop digit from queue: digit = call.dtmf_info_queue.pop(0)
            3. Fall back to in-band detection if queue is empty
        """
        call = self.call_manager.get_call(call_id)
        if not call:
            # Silently ignore DTMF for calls that have already ended
            # This is common when phones buffer DTMF and send it after BYE
            self.logger.debug(f"Received DTMF INFO for ended/unknown call {call_id} - ignoring")
            return

        # Create DTMF queue if it doesn't exist
        if not hasattr(call, "dtmf_info_queue"):
            call.dtmf_info_queue = []

        # Queue the DTMF digit for processing
        call.dtmf_info_queue.append(dtmf_digit)

        # Log based on call type
        if hasattr(call, "voicemail_ivr") and call.voicemail_ivr:
            self.logger.info(
                f"Queued DTMF '{dtmf_digit}' from SIP INFO for voicemail IVR on call {call_id}"
            )
        elif hasattr(call, "auto_attendant") and call.auto_attendant:
            self.logger.info(
                f"Queued DTMF '{dtmf_digit}' from SIP INFO for auto-attendant on call {call_id}"
            )
        else:
            self.logger.debug(f"Queued DTMF '{dtmf_digit}' from SIP INFO for call {call_id}")

    def transfer_call(self, call_id, new_destination):
        """
        Transfer call to new destination using SIP REFER

        Args:
            call_id: Call identifier
            new_destination: New destination extension

        Returns:
            True if transfer initiated
        """
        from pbx.sip.message import SIPMessageBuilder

        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.error(f"Call {call_id} not found for transfer")
            return False

        # Verify new destination exists
        if not self.extension_registry.is_registered(new_destination):
            self.logger.error(f"Transfer destination {new_destination} not registered")
            return False

        self.logger.info(
            f"Transferring call {call_id} from {
                call.from_extension} to {new_destination}"
        )

        # Determine which party to send REFER to (typically the caller)
        refer_to_addr = call.caller_addr if call.caller_addr else call.callee_addr
        if not refer_to_addr:
            self.logger.error(f"No address found for REFER in call {call_id}")
            return False

        # Build REFER message
        server_ip = self._get_server_ip()
        sip_port = self.config.get("server.sip_port", 5060)

        refer_msg = SIPMessageBuilder.build_request(
            method="REFER",
            uri=f"sip:{call.from_extension}@{server_ip}",
            from_addr=f"<sip:{call.to_extension}@{server_ip}>",
            to_addr=f"<sip:{call.from_extension}@{server_ip}>",
            call_id=call_id,
            cseq=1,
        )

        # Add Refer-To header with new destination
        refer_msg.set_header("Refer-To", f"<sip:{new_destination}@{server_ip}>")

        # Add Referred-By header
        refer_msg.set_header("Referred-By", f"<sip:{call.to_extension}@{server_ip}>")

        # Add Contact header
        refer_msg.set_header(
            "Contact",
            f"<sip:{
                call.to_extension}@{server_ip}:{sip_port}>",
        )

        # Send REFER message
        self.sip_server._send_message(refer_msg.build(), refer_to_addr)
        self.logger.info(
            f"Sent REFER to {refer_to_addr} for call {call_id} to transfer to {new_destination}"
        )

        # Mark call as transferred
        call.transferred = True
        call.transfer_destination = new_destination

        return True

    def hold_call(self, call_id):
        """
        Put call on hold

        Args:
            call_id: Call identifier

        Returns:
            True if call put on hold
        """
        call = self.call_manager.get_call(call_id)
        if call:
            call.hold()
            self.logger.info(f"Call {call_id} put on hold")
            return True
        return False

    def resume_call(self, call_id):
        """
        Resume call from hold

        Args:
            call_id: Call identifier

        Returns:
            True if call resumed
        """
        call = self.call_manager.get_call(call_id)
        if call:
            call.resume()
            self.logger.info(f"Call {call_id} resumed")
            return True
        return False

    def _check_dialplan(self, extension):
        """
        Check if extension matches dialplan rules

        Args:
            extension: Extension number

        Returns:
            True if allowed by dialplan
        """
        dialplan = self.config.get("dialplan", {})

        # Check emergency pattern (Kari's Law - direct 911 dialing)
        # Always allow 911 and legacy formats (9911, 9-911)
        emergency_pattern = dialplan.get("emergency_pattern", "^9?-?911$")
        if re.match(emergency_pattern, extension):
            return True

        # Check internal pattern
        internal_pattern = dialplan.get("internal_pattern", "^1[0-9]{3}$")
        if re.match(internal_pattern, extension):
            return True

        # Check conference pattern
        conference_pattern = dialplan.get("conference_pattern", "^2[0-9]{3}$")
        if re.match(conference_pattern, extension):
            return True

        # Check voicemail pattern
        voicemail_pattern = dialplan.get("voicemail_pattern", "^\\*[0-9]{3,4}$")
        if re.match(voicemail_pattern, extension):
            return True

        # Check auto attendant pattern
        auto_attendant_pattern = dialplan.get("auto_attendant_pattern", "^0$")
        if re.match(auto_attendant_pattern, extension):
            return True

        # Check parking pattern
        parking_pattern = dialplan.get("parking_pattern", "^7[0-9]$")
        if re.match(parking_pattern, extension):
            return True

        # Check queue pattern
        queue_pattern = dialplan.get("queue_pattern", "^8[0-9]{3}$")
        if re.match(queue_pattern, extension):
            return True

        return False

    def _handle_no_answer(self, call_id):
        """
        Handle no-answer timeout - route call to voicemail

        Args:
            call_id: Call identifier
        """
        from pbx.rtp.handler import RTPPlayer, RTPRecorder
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder

        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.warning(f"No-answer timeout for non-existent call {call_id}")
            return

        # Check if call was already answered
        from pbx.core.call import CallState

        if call.state == CallState.CONNECTED:
            self.logger.debug(f"Call {call_id} already answered, ignoring no-answer timeout")
            return

        if call.routed_to_voicemail:
            self.logger.debug(f"Call {call_id} already routed to voicemail")
            return

        call.routed_to_voicemail = True
        self.logger.info(f"No answer for call {call_id}, routing to voicemail")

        # Send CANCEL to the callee to stop their phone from ringing
        if (
            hasattr(call, "callee_addr")
            and call.callee_addr
            and hasattr(call, "callee_invite")
            and call.callee_invite
        ):
            cancel_request = SIPMessageBuilder.build_request(
                method="CANCEL",
                uri=call.callee_invite.uri,
                from_addr=call.callee_invite.get_header("From"),
                to_addr=call.callee_invite.get_header("To"),
                call_id=call_id,
                cseq=int(call.callee_invite.get_header("CSeq").split()[0]),
            )
            cancel_request.set_header("Via", call.callee_invite.get_header("Via"))

            self.sip_server._send_message(cancel_request.build(), call.callee_addr)
            self.logger.info(
                f"Sent CANCEL to callee {
                    call.to_extension} to stop ringing"
            )

        # Answer the call to allow voicemail recording
        if call.original_invite and call.caller_addr and call.caller_rtp and call.rtp_ports:
            server_ip = self._get_server_ip()

            # Determine which codecs to offer based on caller's phone model
            # Get caller's User-Agent to detect phone model
            caller_user_agent = self._get_phone_user_agent(call.from_extension)
            caller_phone_model = self._detect_phone_model(caller_user_agent)

            # Extract caller's codecs from the stored RTP info
            caller_codecs = call.caller_rtp.get("formats", None) if call.caller_rtp else None

            # Select appropriate codecs for the caller's phone
            codecs_for_caller = self._get_codecs_for_phone_model(
                caller_phone_model, default_codecs=caller_codecs
            )

            if caller_phone_model:
                self.logger.info(
                    f"Voicemail: Detected caller phone model: {caller_phone_model}, "
                    f"offering codecs: {codecs_for_caller}"
                )

            # Build SDP for the voicemail recording endpoint
            # Get DTMF payload type from config
            dtmf_payload_type = self._get_dtmf_payload_type()
            ilbc_mode = self._get_ilbc_mode()
            voicemail_sdp = SDPBuilder.build_audio_sdp(
                server_ip,
                call.rtp_ports[0],
                session_id=call_id,
                codecs=codecs_for_caller,
                dtmf_payload_type=dtmf_payload_type,
                ilbc_mode=ilbc_mode,
            )

            # Send 200 OK to answer the call for voicemail recording
            ok_response = SIPMessageBuilder.build_response(
                200, "OK", call.original_invite, body=voicemail_sdp
            )
            ok_response.set_header("Content-Type", "application/sdp")

            # Build Contact header
            sip_port = self.config.get("server.sip_port", 5060)
            contact_uri = f"<sip:{call.to_extension}@{server_ip}:{sip_port}>"
            ok_response.set_header("Contact", contact_uri)

            # Send to caller
            self.sip_server._send_message(ok_response.build(), call.caller_addr)
            self.logger.info(f"Answered call {call_id} for voicemail recording")

            # Mark call as connected
            call.connect()

            # Play voicemail greeting and beep tone to caller
            if call.caller_rtp:
                try:
                    import os
                    import tempfile

                    from pbx.utils.audio import get_prompt_audio

                    # Create RTP player to send audio to caller
                    # Use the same port as the RTPRecorder since both bind to 0.0.0.0
                    # and can handle bidirectional RTP communication
                    player = RTPPlayer(
                        # Same port as RTPRecorder
                        local_port=call.rtp_ports[0],
                        remote_host=call.caller_rtp["address"],
                        remote_port=call.caller_rtp["port"],
                        call_id=call_id,
                    )
                    if player.start():
                        # Check for custom greeting first
                        mailbox = self.voicemail_system.get_mailbox(call.to_extension)
                        custom_greeting_path = mailbox.get_greeting_path()
                        greeting_file = None
                        temp_file_created = False

                        if custom_greeting_path:
                            # Use custom greeting
                            greeting_file = custom_greeting_path
                            self.logger.info(
                                f"Using custom greeting for extension {
                                    call.to_extension}: {custom_greeting_path}"
                            )
                            # Verify file exists and is readable
                            if os.path.exists(custom_greeting_path):
                                file_size = os.path.getsize(custom_greeting_path)
                                self.logger.info(f"Custom greeting file exists ({file_size} bytes)")
                            else:
                                self.logger.warning(
                                    f"Custom greeting file not found at {custom_greeting_path}, using default"
                                )
                                custom_greeting_path = None  # Fall back to default

                        if not custom_greeting_path:
                            # Use default prompt: "Please leave a message after the tone"
                            # Try to load from
                            # voicemail_prompts/leave_message.wav, fallback to
                            # tone generation
                            greeting_prompt = get_prompt_audio("leave_message")
                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(greeting_prompt)
                                greeting_file = temp_file.name
                                temp_file_created = True
                            self.logger.info(
                                f"Using default greeting for extension {
                                    call.to_extension}"
                            )

                        try:
                            player.play_file(greeting_file)
                            import time

                            time.sleep(0.3)  # Brief pause before beep
                        finally:
                            # Clean up temp file only if we created one
                            if temp_file_created:
                                try:
                                    os.unlink(greeting_file)
                                except (OSError, FileNotFoundError) as e:
                                    self.logger.debug(f"Could not delete temp greeting file: {e}")

                        # Play beep tone (1000 Hz, 500ms)
                        player.play_beep(frequency=1000, duration_ms=500)
                        player.stop()
                        self.logger.info(f"Played voicemail greeting and beep for call {call_id}")
                    else:
                        self.logger.warning(
                            f"Failed to start RTP player for greeting on call {call_id}"
                        )
                except Exception as e:
                    self.logger.error(f"Error playing voicemail greeting: {e}")

            # Start RTP recorder on the allocated port
            recorder = RTPRecorder(call.rtp_ports[0], call_id)
            if recorder.start():
                # Store recorder in call object for later retrieval
                call.voicemail_recorder = recorder

                # Set recording timeout (max voicemail duration)
                max_duration = self.config.get("voicemail.max_message_duration", 180)

                # Schedule voicemail completion after max duration
                voicemail_timer = threading.Timer(
                    max_duration, self._complete_voicemail_recording, args=(call_id,)
                )
                voicemail_timer.start()
                call.voicemail_timer = voicemail_timer

                # Start DTMF monitoring thread to detect # key press
                dtmf_monitor_thread = threading.Thread(
                    target=self._monitor_voicemail_dtmf, args=(call_id, call, recorder)
                )
                dtmf_monitor_thread.daemon = True
                dtmf_monitor_thread.start()

                self.logger.info(
                    f"Started voicemail recording for call {call_id}, max duration: {max_duration}s"
                )
            else:
                self.logger.error(f"Failed to start voicemail recorder for call {call_id}")
                self.end_call(call_id)
        else:
            self.logger.error(
                f"Cannot route call {call_id} to voicemail - missing required information"
            )
            # Fallback to ending the call
            self.end_call(call_id)

    def _monitor_voicemail_dtmf(self, call_id, call, recorder):
        """
        Monitor for DTMF # key press during voicemail recording
        When # is detected, complete the voicemail recording early

        Args:
            call_id: Call identifier
            call: Call object
            recorder: RTPRecorder instance
        """
        from pbx.utils.dtmf import DTMFDetector

        try:
            # Create DTMF detector
            dtmf_detector = DTMFDetector(sample_rate=8000)

            # Constants for DTMF detection
            DTMF_DETECTION_PACKETS = 40  # 40 packets * 20ms = 0.8s of audio
            # Minimum audio data needed for reliable DTMF detection
            MIN_AUDIO_BYTES_FOR_DTMF = 1600

            self.logger.info(f"Started DTMF monitoring for voicemail recording on call {call_id}")

            # Monitor for # key press
            while recorder.running and call.state.value != "ended":
                time.sleep(0.1)

                # Check for recorded audio (DTMF tones from caller)
                if hasattr(recorder, "recorded_data") and recorder.recorded_data:
                    # Get recent audio data
                    if len(recorder.recorded_data) > 0:
                        # Collect last portion of audio for DTMF detection
                        recent_audio = b"".join(recorder.recorded_data[-DTMF_DETECTION_PACKETS:])

                        if len(recent_audio) > MIN_AUDIO_BYTES_FOR_DTMF:
                            # Convert bytes to audio samples for DTMF detection
                            # G.711 μ-law is 8-bit samples, one byte per sample
                            # Use struct.unpack for efficient batch conversion
                            samples = []
                            # Process in chunks for efficiency
                            chunk_size = min(len(recent_audio), 8192)  # Process up to 8KB at once
                            for i in range(0, len(recent_audio), chunk_size):
                                chunk = recent_audio[i : i + chunk_size]
                                # Unpack bytes and convert to float samples
                                unpacked = struct.unpack(f"{len(chunk)}B", chunk)
                                # Convert unsigned byte to signed float (-1.0
                                # to 1.0)
                                samples.extend([(b - 128) / 128.0 for b in unpacked])

                            # Detect DTMF
                            digit = dtmf_detector.detect_tone(samples)

                            if digit == "#":
                                self.logger.info(
                                    f"Detected # key press during voicemail recording on call {call_id}"
                                )
                                # Complete the voicemail recording
                                self._complete_voicemail_recording(call_id)
                                return

            self.logger.debug(f"DTMF monitoring ended for voicemail recording on call {call_id}")

        except Exception as e:
            self.logger.error(f"Error in voicemail DTMF monitoring: {e}")
            self.logger.error(traceback.format_exc())

    def _complete_voicemail_recording(self, call_id):
        """
        Complete voicemail recording and save the message

        Args:
            call_id: Call identifier
        """
        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.warning(f"Cannot complete voicemail for non-existent call {call_id}")
            return

        # Get the recorder if it exists
        recorder = getattr(call, "voicemail_recorder", None)
        if recorder:
            # Stop recording
            recorder.stop()

            # Get recorded audio
            audio_data = recorder.get_recorded_audio()
            duration = recorder.get_duration()

            if audio_data and len(audio_data) > 0:
                # Build proper WAV file header for the recorded audio
                wav_data = self._build_wav_file(audio_data)

                # Save to voicemail system
                self.voicemail_system.save_message(
                    extension_number=call.to_extension,
                    caller_id=call.from_extension,
                    audio_data=wav_data,
                    duration=duration,
                )
                self.logger.info(
                    f"Saved voicemail for extension {
                        call.to_extension} from {
                        call.from_extension}, duration: {duration}s"
                )
            else:
                self.logger.warning(f"No audio recorded for voicemail on call {call_id}")
                # Still create a minimal voicemail to indicate the attempt
                placeholder_audio = self._build_wav_file(b"")
                self.voicemail_system.save_message(
                    extension_number=call.to_extension,
                    caller_id=call.from_extension,
                    audio_data=placeholder_audio,
                    duration=0,
                )

        # End the call
        self.end_call(call_id)

    def _handle_auto_attendant(self, from_ext, to_ext, call_id, message, from_addr):
        """
        Handle auto attendant calls (extension 0)

        Args:
            from_ext: Calling extension
            to_ext: Destination (auto attendant extension, typically '0')
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Caller address

        Returns:
            True if call was handled
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        self.logger.info(f"Auto attendant call: {from_ext} -> {to_ext}")

        # Parse SDP from caller's INVITE
        caller_sdp = None
        caller_codecs = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()
            if caller_sdp:
                # Extract caller's codec list for negotiation
                caller_codecs = caller_sdp.get("formats", None)
                if caller_codecs:
                    self.logger.info(f"Auto attendant: Caller codecs: {caller_codecs}")

        # Create call for auto attendant
        call = self.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.auto_attendant_active = True

        # Start CDR record for analytics
        self.cdr_system.start_record(call_id, from_ext, to_ext)

        # Allocate RTP port for audio communication
        # For auto attendant, we don't need a relay (which forwards between two endpoints).
        # Instead, we directly play audio to the caller and listen for DTMF.
        # Find an available port from the RTP port pool.
        try:
            rtp_port = self.rtp_relay.port_pool.pop(0)
        except IndexError:
            self.logger.error(f"No available RTP ports for auto attendant {call_id}")
            return False

        rtcp_port = rtp_port + 1
        call.rtp_ports = (rtp_port, rtcp_port)
        self.logger.info(
            f"Allocated RTP port {rtp_port} for auto attendant {call_id} (no relay needed)"
        )

        # Store port allocation for cleanup
        call.aa_rtp_port = rtp_port

        # Send 180 Ringing first to provide ring-back tone to caller
        server_ip = self._get_server_ip()
        ringing_response = SIPMessageBuilder.build_response(180, "Ringing", call.original_invite)

        # Build Contact header for ringing response
        sip_port = self.config.get("server.sip_port", 5060)
        contact_uri = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ringing_response.set_header("Contact", contact_uri)

        # Send ringing response to caller
        self.sip_server._send_message(ringing_response.build(), call.caller_addr)
        self.logger.info(f"Sent 180 Ringing for auto attendant call {call_id}")

        # Brief delay to allow ring-back tone to be established
        time.sleep(0.5)

        # Answer the call

        # Determine which codecs to offer based on caller's phone model
        # Get caller's User-Agent to detect phone model
        caller_user_agent = self._get_phone_user_agent(from_ext)
        caller_phone_model = self._detect_phone_model(caller_user_agent)

        # Select appropriate codecs for the caller's phone
        codecs_for_caller = self._get_codecs_for_phone_model(
            caller_phone_model, default_codecs=caller_codecs
        )

        if caller_phone_model:
            self.logger.info(
                f"Auto attendant: Detected caller phone model: {caller_phone_model}, "
                f"offering codecs: {codecs_for_caller}"
            )

        # Build SDP for answering, using phone-model-specific codecs
        # Get DTMF payload type from config
        dtmf_payload_type = self._get_dtmf_payload_type()
        ilbc_mode = self._get_ilbc_mode()
        aa_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id,
            codecs=codecs_for_caller,
            dtmf_payload_type=dtmf_payload_type,
            ilbc_mode=ilbc_mode,
        )

        # Send 200 OK to answer the call
        ok_response = SIPMessageBuilder.build_response(200, "OK", call.original_invite, body=aa_sdp)
        ok_response.set_header("Content-Type", "application/sdp")

        # Build Contact header
        sip_port = self.config.get("server.sip_port", 5060)
        contact_uri = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header("Contact", contact_uri)

        # Send to caller
        self.sip_server._send_message(ok_response.build(), call.caller_addr)
        self.logger.info(f"Answered auto attendant call {call_id}")

        # Mark call as connected
        call.connect()

        # Start auto attendant session
        session = self.auto_attendant.start_session(call_id, from_ext)
        call.aa_session = session

        # Start auto attendant interaction thread
        aa_thread = threading.Thread(
            target=self._auto_attendant_session, args=(call_id, call, session)
        )
        aa_thread.daemon = True
        aa_thread.start()

        return True

    def _auto_attendant_session(self, call_id, call, session):
        """
        Handle auto attendant session with menu and DTMF input

        Args:
            call_id: Call identifier
            call: Call object
            session: Auto attendant session
        """
        import os
        import tempfile
        import time

        from pbx.rtp.handler import RTPDTMFListener, RTPPlayer
        from pbx.utils.audio import get_prompt_audio

        try:
            # Wait for RTP to stabilize
            time.sleep(0.5)

            if not call.caller_rtp:
                self.logger.warning(f"No caller RTP info for auto attendant {call_id}")
                return

            # ============================================================
            # RTP SETUP FOR AUTO ATTENDANT - BIDIRECTIONAL AUDIO
            # ============================================================
            # This section sets up RTP for interactive auto attendant:
            # 1. RTPPlayer: Sends audio prompts/menus to the caller (server -> client)
            # 2. RTPDTMFListener: Receives audio and detects DTMF tones (client -> server)
            # Both use the same local port (call.rtp_ports[0]) allocated by RTP relay.
            # This creates a full-duplex audio channel for the auto attendant system.
            # ============================================================

            # Create RTP player for sending audio prompts to the caller
            player = RTPPlayer(
                local_port=call.rtp_ports[0],
                remote_host=call.caller_rtp["address"],
                remote_port=call.caller_rtp["port"],
                call_id=call_id,
            )

            if not player.start():
                self.logger.error(f"Failed to start RTP player for auto attendant {call_id}")
                return

            # Create DTMF listener for receiving and detecting user input
            dtmf_listener = RTPDTMFListener(call.rtp_ports[0])
            if not dtmf_listener.start():
                self.logger.error(f"Failed to start DTMF listener for auto attendant {call_id}")
                player.stop()
                return
            self.logger.info(
                f"Auto attendant RTP setup complete - bidirectional audio channel established"
            )

            # Play welcome greeting
            action = session.get("session")
            audio_file = session.get("file")

            self.logger.info(f"[Auto Attendant] Starting audio playback for call {call_id}")
            audio_played = False

            if audio_file and os.path.exists(audio_file):
                self.logger.info(f"[Auto Attendant] Playing welcome file: {audio_file}")
                audio_played = player.play_file(audio_file)
                if audio_played:
                    self.logger.info(f"[Auto Attendant] ✓ Welcome audio played successfully")
                else:
                    self.logger.error(f"[Auto Attendant] ✗ Failed to play welcome audio")
            else:
                # Try to load from auto_attendant/welcome.wav, fallback to tone
                # generation
                self.logger.info(f"[Auto Attendant] Generating welcome prompt audio")
                prompt_data = get_prompt_audio("welcome", prompt_dir="auto_attendant")
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file.write(prompt_data)
                    temp_file_path = temp_file.name
                try:
                    audio_played = player.play_file(temp_file_path)
                    if audio_played:
                        self.logger.info(
                            f"[Auto Attendant] ✓ Generated welcome audio played successfully"
                        )
                    else:
                        self.logger.error(
                            f"[Auto Attendant] ✗ Failed to play generated welcome audio"
                        )
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except BaseException:
                        pass

            time.sleep(0.5)

            # Play main menu
            self.logger.info(f"[Auto Attendant] Playing main menu for call {call_id}")
            menu_audio = self.auto_attendant._get_audio_file("main_menu")
            if menu_audio and os.path.exists(menu_audio):
                self.logger.info(f"[Auto Attendant] Playing menu file: {menu_audio}")
                audio_played = player.play_file(menu_audio)
                if audio_played:
                    self.logger.info(f"[Auto Attendant] ✓ Menu audio played successfully")
                else:
                    self.logger.error(f"[Auto Attendant] ✗ Failed to play menu audio")
            else:
                # Try to load from auto_attendant/main_menu.wav, fallback to
                # tone generation
                self.logger.info(f"[Auto Attendant] Generating menu prompt audio")
                prompt_data = get_prompt_audio("main_menu", prompt_dir="auto_attendant")
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file.write(prompt_data)
                    temp_file_path = temp_file.name
                try:
                    audio_played = player.play_file(temp_file_path)
                    if audio_played:
                        self.logger.info(
                            f"[Auto Attendant] ✓ Generated menu audio played successfully"
                        )
                    else:
                        self.logger.error(f"[Auto Attendant] ✗ Failed to play generated menu audio")
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except BaseException:
                        pass

            # Main loop - wait for DTMF input
            session_active = True
            timeout = self.auto_attendant.timeout
            start_time = time.time()

            while session_active and (time.time() - start_time) < timeout:
                # Check for DTMF input from SIP INFO or in-band
                digit = None

                # Priority 1: Check SIP INFO queue
                if hasattr(call, "dtmf_info_queue") and call.dtmf_info_queue:
                    digit = call.dtmf_info_queue.pop(0)
                    self.logger.info(f"Auto attendant received DTMF from SIP INFO: {digit}")
                else:
                    # Priority 2: Check in-band DTMF
                    digit = dtmf_listener.get_digit(timeout=1.0)
                    if digit:
                        self.logger.info(
                            f"Auto attendant received DTMF from in-band audio: {digit}"
                        )

                if digit:
                    self.logger.info(f"Auto attendant received DTMF: {digit}")

                    # Handle the input
                    result = self.auto_attendant.handle_dtmf(session["session"], digit)
                    action = result.get("action")

                    if action == "transfer":
                        destination = result.get("destination")
                        self.logger.info(f"Auto attendant transferring to {destination}")

                        # Play transfer message
                        transfer_audio = self.auto_attendant._get_audio_file("transferring")
                        if transfer_audio and os.path.exists(transfer_audio):
                            player.play_file(transfer_audio)
                        else:
                            # Try to load from auto_attendant/transferring.wav,
                            # fallback to tone generation
                            prompt_data = get_prompt_audio(
                                "transferring", prompt_dir="auto_attendant"
                            )
                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(prompt_data)
                                temp_file_path = temp_file.name
                            try:
                                player.play_file(temp_file_path)
                            finally:
                                try:
                                    os.unlink(temp_file_path)
                                except BaseException:
                                    pass

                        time.sleep(0.5)

                        # Transfer the call using existing transfer_call method
                        if call_id:
                            success = self.transfer_call(call_id, destination)
                            if not success:
                                self.logger.warning(
                                    f"Failed to transfer call {call_id} to {destination}"
                                )
                        else:
                            self.logger.warning("Cannot transfer call: no call_id available")
                        session_active = False

                    elif action == "play":
                        # Play the requested audio
                        audio_file = result.get("file")
                        if audio_file and os.path.exists(audio_file):
                            player.play_file(audio_file)

                        # Reset timeout
                        start_time = time.time()

                    # Update session
                    if "session" in result:
                        session["session"] = result["session"]

            # Timeout - handle it
            if time.time() - start_time >= timeout:
                result = self.auto_attendant.handle_timeout(session["session"])
                action = result.get("action")

                if action == "transfer":
                    destination = result.get("destination")
                    self.logger.info(f"Auto attendant timeout, transferring to {destination}")
                    if call_id:
                        success = self.transfer_call(call_id, destination)
                        if not success:
                            self.logger.warning(
                                f"Failed to transfer call {call_id} to {destination} on timeout"
                            )

            # Clean up
            player.stop()
            dtmf_listener.stop()

            # Return port to pool
            if hasattr(call, "aa_rtp_port"):
                self.rtp_relay.port_pool.append(call.aa_rtp_port)
                self.rtp_relay.port_pool.sort()
                self.logger.info(
                    f"Returned RTP port {
                        call.aa_rtp_port} to pool"
                )

        except Exception as e:
            self.logger.error(f"Error in auto attendant session: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

            # Ensure port is returned even on error
            if hasattr(call, "aa_rtp_port"):
                try:
                    self.rtp_relay.port_pool.append(call.aa_rtp_port)
                    self.rtp_relay.port_pool.sort()
                except Exception:
                    pass
        finally:
            # End the call
            time.sleep(1)
            self.end_call(call_id)

    def _handle_voicemail_access(self, from_ext, to_ext, call_id, message, from_addr):
        """
        Handle voicemail access calls (*xxxx pattern)

        Args:
            from_ext: Calling extension
            to_ext: Destination (e.g., *1001)
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Caller address

        Returns:
            True if call was handled
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        # Extract the target extension from *xxxx pattern
        target_ext = to_ext[1:]  # Remove the * prefix

        self.logger.info(f"=" * 70)
        self.logger.info(f"VOICEMAIL ACCESS INITIATED")
        self.logger.info(f"  Call ID: {call_id}")
        self.logger.info(f"  From Extension: {from_ext}")
        self.logger.info(f"  Target Extension: {target_ext}")
        self.logger.info(f"  Caller Address: {from_addr}")
        self.logger.info(f"=" * 70)

        # Verify the target extension exists (check both database and config)
        self.logger.info(f"[VM Access] Step 1: Verifying target extension {target_ext} exists")
        extension_exists = False

        # Check extension registry first (includes both database and config
        # extensions)
        if self.extension_registry.get(target_ext):
            extension_exists = True
            self.logger.info(f"[VM Access] ✓ Extension {target_ext} found in registry")
        # Fallback to config check for backwards compatibility
        elif self.config.get_extension(target_ext):
            extension_exists = True
            self.logger.info(f"[VM Access] ✓ Extension {target_ext} found in config file")

        if not extension_exists:
            self.logger.warning(
                f"[VM Access] ✗ Extension {target_ext} not found - rejecting voicemail access"
            )
            return False

        # Get the voicemail box
        self.logger.info(f"[VM Access] Step 2: Loading voicemail box for extension {target_ext}")
        mailbox = self.voicemail_system.get_mailbox(target_ext)
        self.logger.info(f"[VM Access] ✓ Voicemail box loaded")

        # Parse SDP from caller's INVITE
        self.logger.info(f"[VM Access] Step 3: Parsing SDP from caller INVITE")
        caller_sdp = None
        caller_codecs = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()
            if caller_sdp:
                self.logger.info(
                    f"[VM Access] ✓ Caller SDP parsed: address={
                        caller_sdp.get('address')}, port={
                        caller_sdp.get('port')}, formats={
                        caller_sdp.get('formats')}"
                )
                # Extract caller's codec list for negotiation
                caller_codecs = caller_sdp.get("formats", None)
            else:
                self.logger.warning(f"[VM Access] ⚠ No audio info found in caller SDP")
        else:
            self.logger.warning(f"[VM Access] ⚠ No SDP body in INVITE message")

        # Create call for voicemail access
        self.logger.info(f"[VM Access] Step 4: Creating call object in call manager")
        call = self.call_manager.create_call(call_id, from_ext, f"*{target_ext}")
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.voicemail_access = True
        call.voicemail_extension = target_ext
        self.logger.info(
            f"[VM Access] ✓ Call object created with state: {
                call.state}"
        )

        # Start CDR record for analytics
        self.logger.info(f"[VM Access] Step 5: Starting CDR record for analytics")
        self.cdr_system.start_record(call_id, from_ext, f"*{target_ext}")

        # Allocate RTP ports for bidirectional audio communication
        # These ports will be used by RTPPlayer (sending prompts) and RTPRecorder (receiving DTMF)
        # in the IVR session thread. The RTP relay handler manages the socket
        # binding and packet forwarding.
        self.logger.info(f"[VM Access] Step 6: Allocating RTP relay ports")
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
            self.logger.info(f"[VM Access] ✓ RTP ports allocated: {rtp_ports[0]}/{rtp_ports[1]}")
        else:
            self.logger.error(
                f"[VM Access] ✗ Failed to allocate RTP ports - aborting voicemail access"
            )
            return False

        # Answer the call
        self.logger.info(f"[VM Access] Step 7: Building SIP 200 OK response")
        server_ip = self._get_server_ip()
        self.logger.info(f"[VM Access] Server IP: {server_ip}")

        # Determine which codecs to offer based on caller's phone model
        # Get caller's User-Agent to detect phone model
        caller_user_agent = self._get_phone_user_agent(from_ext)
        caller_phone_model = self._detect_phone_model(caller_user_agent)

        # Select appropriate codecs for the caller's phone
        codecs_for_caller = self._get_codecs_for_phone_model(
            caller_phone_model, default_codecs=caller_codecs
        )

        if caller_phone_model:
            self.logger.info(
                f"[VM Access] Detected caller phone model: {caller_phone_model}, "
                f"offering codecs: {codecs_for_caller}"
            )

        # Build SDP for answering, using phone-model-specific codecs
        # Get DTMF payload type from config
        dtmf_payload_type = self._get_dtmf_payload_type()
        ilbc_mode = self._get_ilbc_mode()
        voicemail_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id,
            codecs=codecs_for_caller,
            dtmf_payload_type=dtmf_payload_type,
            ilbc_mode=ilbc_mode,
        )
        self.logger.info(
            f"[VM Access] ✓ SDP built for response (RTP port: {
                call.rtp_ports[0]})"
        )

        # Send 200 OK to answer the call
        self.logger.info(f"[VM Access] Step 8: Building and sending 200 OK response")
        ok_response = SIPMessageBuilder.build_response(
            200, "OK", call.original_invite, body=voicemail_sdp
        )
        ok_response.set_header("Content-Type", "application/sdp")

        # Build Contact header
        sip_port = self.config.get("server.sip_port", 5060)
        contact_uri = f"<sip:{target_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header("Contact", contact_uri)
        self.logger.info(f"[VM Access] Contact header: {contact_uri}")

        # Send to caller
        self.sip_server._send_message(ok_response.build(), call.caller_addr)
        self.logger.info(f"[VM Access] ✓ 200 OK sent to {call.caller_addr}")

        # Mark call as connected
        call.connect()
        self.logger.info(f"[VM Access] ✓ Call state changed to: {call.state}")

        # Create VoicemailIVR for this call
        self.logger.info(f"[VM Access] Step 9: Initializing Voicemail IVR")
        from pbx.features.voicemail import VoicemailIVR

        voicemail_ivr = VoicemailIVR(self.voicemail_system, target_ext)
        call.voicemail_ivr = voicemail_ivr
        self.logger.info(f"[VM Access] ✓ Voicemail IVR created for extension {target_ext}")

        # Get message count
        self.logger.info(f"[VM Access] Step 10: Checking voicemail message count")
        messages = mailbox.get_messages(unread_only=False)
        unread = mailbox.get_messages(unread_only=True)
        self.logger.info(
            f"[VM Access] ✓ Mailbox status: {
                len(unread)} unread, {
                len(messages)} total messages"
        )

        # Start IVR-based voicemail management
        # This runs in a separate thread so it doesn't block
        self.logger.info(f"[VM Access] Step 11: Starting IVR session thread")
        playback_thread = threading.Thread(
            target=self._voicemail_ivr_session, args=(call_id, call, mailbox, voicemail_ivr)
        )
        playback_thread.daemon = True
        playback_thread.start()
        self.logger.info(f"[VM Access] ✓ IVR session thread started (daemon)")

        self.logger.info(f"=" * 70)
        self.logger.info(f"VOICEMAIL ACCESS SETUP COMPLETE")
        self.logger.info(f"  Call ID: {call_id}")
        self.logger.info(f"  Extension: {target_ext}")
        self.logger.info(f"  State: {call.state}")
        self.logger.info(f"  Ready for user interaction")
        self.logger.info(f"=" * 70)

        return True

    def _handle_paging(self, from_ext, to_ext, call_id, message, from_addr):
        """
        Handle paging system calls (7xx pattern or all-call)

        Args:
            from_ext: Calling extension
            to_ext: Paging extension (e.g., 700, 701, 702)
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Caller address

        Returns:
            True if call was handled
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        self.logger.info(f"Paging call: {from_ext} -> {to_ext}")

        # Initiate the page through the paging system
        page_id = self.paging_system.initiate_page(from_ext, to_ext)
        if not page_id:
            self.logger.error(f"Failed to initiate page from {from_ext} to {to_ext}")
            return False

        # Get zone information
        page_info = self.paging_system.get_page_info(page_id)
        if not page_info:
            self.logger.error(f"Failed to get page info for {page_id}")
            return False

        # Parse SDP from caller's INVITE
        caller_sdp = None
        caller_codecs = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()

            if caller_sdp:
                self.logger.info(
                    f"Paging caller RTP: {
                        caller_sdp['address']}:{
                        caller_sdp['port']}"
                )
                # Extract caller's codec list for negotiation
                caller_codecs = caller_sdp.get("formats", None)

        # Create call for paging
        call = self.call_manager.create_call(call_id, from_ext, to_ext)
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.paging_active = True
        call.page_id = page_id
        call.paging_zones = page_info.get("zone_names", "Unknown")

        # Start CDR record for analytics
        self.cdr_system.start_record(call_id, from_ext, to_ext)

        # Allocate RTP ports
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports
        else:
            self.logger.error(f"Failed to allocate RTP ports for paging {call_id}")
            self.paging_system.end_page(page_id)
            return False

        # Get configured paging gateway device
        zones = page_info.get("zones", [])
        if not zones:
            self.logger.error(f"No zones configured for paging extension {to_ext}")
            self.paging_system.end_page(page_id)
            return False

        # For now, use the first zone's DAC device
        zone = zones[0]
        dac_device_id = zone.get("dac_device")

        if not dac_device_id:
            self.logger.warning(
                f"No DAC device configured for zone {
                    zone.get('name')}"
            )
            # Continue anyway - this allows testing without hardware

        # Find the DAC device configuration
        dac_device = None
        for device in self.paging_system.get_dac_devices():
            if device.get("device_id") == dac_device_id:
                dac_device = device
                break

        # Answer the call immediately (auto-answer for paging)
        server_ip = self._get_server_ip()

        # Determine which codecs to offer based on caller's phone model
        # Get caller's User-Agent to detect phone model
        caller_user_agent = self._get_phone_user_agent(from_ext)
        caller_phone_model = self._detect_phone_model(caller_user_agent)

        # Select appropriate codecs for the caller's phone
        codecs_for_caller = self._get_codecs_for_phone_model(
            caller_phone_model, default_codecs=caller_codecs
        )

        if caller_phone_model:
            self.logger.info(
                f"Paging: Detected caller phone model: {caller_phone_model}, "
                f"offering codecs: {codecs_for_caller}"
            )

        # Build SDP for answering, using phone-model-specific codecs
        # Get DTMF payload type from config
        dtmf_payload_type = self._get_dtmf_payload_type()
        ilbc_mode = self._get_ilbc_mode()
        paging_sdp = SDPBuilder.build_audio_sdp(
            server_ip,
            call.rtp_ports[0],
            session_id=call_id,
            codecs=codecs_for_caller,
            dtmf_payload_type=dtmf_payload_type,
            ilbc_mode=ilbc_mode,
        )

        # Send 200 OK to answer the call
        ok_response = SIPMessageBuilder.build_response(
            200, "OK", call.original_invite, body=paging_sdp
        )
        ok_response.set_header("Content-Type", "application/sdp")

        # Build Contact header
        sip_port = self.config.get("server.sip_port", 5060)
        contact_uri = f"<sip:{to_ext}@{server_ip}:{sip_port}>"
        ok_response.set_header("Contact", contact_uri)

        # Send to caller
        self.sip_server._send_message(ok_response.build(), call.caller_addr)
        self.logger.info(f"Answered paging call {call_id} - Paging {page_info.get('zone_names')}")

        # Mark call as connected
        call.connect()

        # If we have a DAC device configured, route audio to it
        if dac_device:
            # Start paging session thread to handle audio routing
            paging_thread = threading.Thread(
                target=self._paging_session, args=(call_id, call, dac_device, page_info)
            )
            paging_thread.daemon = True
            paging_thread.start()
        else:
            # No hardware - just maintain the call for testing
            self.logger.warning(f"Paging call {call_id} connected but no DAC device available")
            self.logger.info(
                f"Audio from {from_ext} would be routed to {
                    page_info.get('zone_names')}"
            )

        return True

    def _paging_session(self, call_id, call, dac_device, page_info):
        """
        Handle paging session with audio routing to DAC device

        Args:
            call_id: Call identifier
            call: Call object
            dac_device: DAC device configuration
            page_info: Paging information dictionary
        """
        import time

        try:
            self.logger.info(f"Paging session started for {call_id}")
            self.logger.info(
                f"DAC device: {
                    dac_device.get('device_id')} ({
                    dac_device.get('device_type')})"
            )
            self.logger.info(f"Paging zones: {page_info.get('zone_names')}")

            # Get DAC device SIP information
            dac_sip_uri = dac_device.get("sip_uri")
            dac_ip = dac_device.get("ip_address")
            dac_port = dac_device.get("port", 5060)

            if not dac_sip_uri or not dac_ip:
                self.logger.error(
                    f"DAC device {
                        dac_device.get('device_id')} missing SIP configuration"
                )
                return

            # Note: Full DAC integration requires hardware
            # When implemented, this will:
            # 1. Establish SIP connection to the DAC gateway device
            # 2. Set up RTP relay to forward audio from caller to DAC
            # 3. Handle zone selection (if multi-zone gateway)
            # 4. Monitor the call and end when caller hangs up
            # See GitHub issue #XX for hardware integration tracking

            # For now, log the routing information
            self.logger.info(f"Would route RTP audio to {dac_ip}:{dac_port}")

            if call.caller_rtp:
                self.logger.info(
                    f"Caller RTP: {
                        call.caller_rtp['address']}:{
                        call.caller_rtp['port']}"
                )
                self.logger.info(f"Audio relay: Caller -> PBX:{call.rtp_ports[0]} -> DAC:{dac_ip}")

            # Monitor the call until it ends
            while call.state.value != "ended":
                time.sleep(1)

            self.logger.info(f"Paging session ended for {call_id}")

            # End the page
            self.paging_system.end_page(call.page_id)

        except Exception as e:
            self.logger.error(f"Error in paging session {call_id}: {e}")
            self.logger.debug("Paging session error details", exc_info=True)

    def _playback_voicemails(self, call_id, call, mailbox, messages):
        """
        Play voicemail messages to caller

        Args:
            call_id: Call identifier
            call: Call object
            mailbox: VoicemailBox object
            messages: List of message dictionaries
        """
        import time

        from pbx.rtp.handler import RTPPlayer

        try:
            # Wait a moment for RTP to stabilize
            time.sleep(0.5)

            # Create RTP player to send audio to caller
            if not call.caller_rtp:
                self.logger.warning(f"No caller RTP info for voicemail playback {call_id}")
                # End call after short delay
                time.sleep(2)
                self.end_call(call_id)
                return

            # Use the same port as allocated for the call for proper RTP
            # communication
            player = RTPPlayer(
                local_port=call.rtp_ports[0],
                remote_host=call.caller_rtp["address"],
                remote_port=call.caller_rtp["port"],
                call_id=call_id,
            )

            if not player.start():
                self.logger.error(f"Failed to start RTP player for voicemail playback {call_id}")
                time.sleep(2)
                self.end_call(call_id)
                return

            try:
                # Play each voicemail message
                if not messages:
                    # No messages - play short beep and hang up
                    self.logger.info(
                        f"No voicemail messages for {
                            call.voicemail_extension}"
                    )
                    player.play_beep(frequency=400, duration_ms=500)
                    time.sleep(2)
                else:
                    # Play messages
                    self.logger.info(
                        f"Playing {
                            len(messages)} voicemail messages for {
                            call.voicemail_extension}"
                    )

                    for idx, message in enumerate(messages):
                        # Play a beep between messages
                        if idx > 0:
                            time.sleep(0.5)
                            player.play_beep(frequency=800, duration_ms=300)
                            time.sleep(0.5)

                        # Play the voicemail message
                        file_path = message["file_path"]
                        self.logger.info(
                            f"Playing voicemail {idx + 1}/{len(messages)}: {file_path}"
                        )

                        if player.play_file(file_path):
                            # Mark message as listened
                            mailbox.mark_listened(message["id"])
                            self.logger.info(
                                f"Marked voicemail {
                                    message['id']} as listened"
                            )
                        else:
                            self.logger.warning(f"Failed to play voicemail: {file_path}")

                        # Pause between messages
                        time.sleep(1)

                    self.logger.info(
                        f"Finished playing all voicemails for {
                            call.voicemail_extension}"
                    )
                    time.sleep(1)

            finally:
                player.stop()

            # End the call after playback
            self.end_call(call_id)

        except Exception as e:
            self.logger.error(f"Error in voicemail playback: {e}")
            import traceback

            traceback.print_exc()
            # Ensure call is ended even if there's an error
            try:
                self.end_call(call_id)
            except Exception as e:
                self.logger.error(f"Error ending call during cleanup: {e}")

    def _voicemail_ivr_session(self, call_id, call, mailbox, voicemail_ivr):
        """
        Interactive voicemail management session with IVR menu

        Args:
            call_id: Call identifier
            call: Call object
            mailbox: VoicemailBox object
            voicemail_ivr: VoicemailIVR object
        """
        import os
        import tempfile
        import time

        from pbx.core.call import CallState
        from pbx.rtp.handler import RTPPlayer, RTPRecorder
        from pbx.utils.audio import get_prompt_audio
        from pbx.utils.dtmf import DTMFDetector

        self.logger.info(f"")
        self.logger.info(f"{'=' * 70}")
        self.logger.info(f"VOICEMAIL IVR SESSION STARTING")
        self.logger.info(f"  Call ID: {call_id}")
        self.logger.info(f"  Extension: {call.voicemail_extension}")
        self.logger.info(f"  Call State: {call.state}")
        self.logger.info(f"{'=' * 70}")

        try:
            # Wait a moment for RTP to stabilize
            self.logger.info(f"[VM IVR] Waiting 0.5s for RTP to stabilize...")
            time.sleep(0.5)

            # Check if call was terminated during RTP stabilization
            if call.state == CallState.ENDED:
                self.logger.info(f"")
                self.logger.info(f"[VM IVR] ✗ call ended before IVR could start")
                self.logger.info(f"[VM IVR] Extension: {call.voicemail_extension}")
                self.logger.info(f"[VM IVR] State: {call.state}")
                self.logger.info(f"[VM IVR] Exiting IVR session")
                self.logger.info(f"")
                return

            self.logger.info(f"[VM IVR] Checking caller RTP information...")
            if not call.caller_rtp:
                self.logger.warning(f"[VM IVR] ✗ No caller RTP info available - cannot proceed")
                time.sleep(2)
                self.end_call(call_id)
                return
            self.logger.info(
                f"[VM IVR] ✓ Caller RTP: {
                    call.caller_rtp['address']}:{
                    call.caller_rtp['port']}"
            )

            # ============================================================
            # RTP SETUP FOR VOICEMAIL IVR - BIDIRECTIONAL AUDIO
            # ============================================================
            # This section sets up RTP for interactive voicemail access:
            # 1. RTPPlayer: Sends audio prompts to the caller (server -> client)
            # 2. RTPRecorder: Receives audio from caller for DTMF detection (client -> server)
            # Both use the same local port (call.rtp_ports[0]) allocated by RTP relay.
            # This creates a full-duplex audio channel for the IVR system.
            # ============================================================

            # Create RTP player for sending audio prompts to the caller
            # This sends voicemail prompts, menus, and messages to the user
            self.logger.info(f"[VM IVR] Creating RTP player for audio prompts...")
            self.logger.info(f"[VM IVR]   Local port: {call.rtp_ports[0]}")
            self.logger.info(
                f"[VM IVR]   Remote: {
                    call.caller_rtp['address']}:{
                    call.caller_rtp['port']}"
            )
            player = RTPPlayer(
                local_port=call.rtp_ports[0],
                remote_host=call.caller_rtp["address"],
                remote_port=call.caller_rtp["port"],
                call_id=call_id,
            )

            if not player.start():
                self.logger.error(f"[VM IVR] ✗ Failed to start RTP player")
                time.sleep(2)
                self.end_call(call_id)
                return
            self.logger.info(f"[VM IVR] ✓ RTP player started successfully")

            # Create DTMF detector for processing user input (menu selections,
            # PIN, etc.)
            self.logger.info(f"[VM IVR] Creating DTMF detector (sample_rate=8000Hz)...")
            dtmf_detector = DTMFDetector(sample_rate=8000)
            self.logger.info(f"[VM IVR] ✓ DTMF detector created")

            # Create RTP recorder to receive audio from caller for DTMF detection
            # This listens on the same port, captures incoming RTP packets, and
            # extracts audio
            self.logger.info(
                f"[VM IVR] Creating RTP recorder for DTMF detection (port {
                    call.rtp_ports[0]})..."
            )
            recorder = RTPRecorder(call.rtp_ports[0], call_id)
            if not recorder.start():
                self.logger.error(f"[VM IVR] ✗ Failed to start RTP recorder")
                player.stop()
                time.sleep(2)
                self.end_call(call_id)
                return
            self.logger.info(f"[VM IVR] ✓ RTP recorder started successfully")
            self.logger.info(
                f"[VM IVR] ✓ RTP setup complete - bidirectional audio channel established"
            )

            try:
                # Start the IVR flow - transition from WELCOME to PIN_ENTRY state
                # Use '*' which won't be collected as part of PIN (only 0-9 are
                # collected)
                self.logger.info(f"[VM IVR] Initializing IVR state machine...")
                initial_action = voicemail_ivr.handle_dtmf("*")

                # Play the PIN entry prompt that the IVR returned
                if not isinstance(initial_action, dict):
                    self.logger.error(
                        f"[VM IVR] ✗ IVR handle_dtmf returned unexpected type: {
                            type(initial_action)}"
                    )
                    initial_action = {"action": "play_prompt", "prompt": "enter_pin"}

                self.logger.info(
                    f"[VM IVR] ✓ IVR initialized - Action: {
                        initial_action.get('action')}, Prompt: {
                        initial_action.get('prompt')}"
                )

                prompt_type = initial_action.get("prompt", "enter_pin")
                # Try to load from voicemail_prompts/ directory, fallback to
                # tone generation
                self.logger.info(f"[VM IVR] Loading audio prompt: {prompt_type}")
                pin_prompt = get_prompt_audio(prompt_type)
                self.logger.info(
                    f"[VM IVR] ✓ Prompt audio loaded ({
                        len(pin_prompt)} bytes)"
                )

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file.write(pin_prompt)
                    prompt_file = temp_file.name

                try:
                    self.logger.info(
                        f"[VM IVR] Playing PIN entry prompt (call state: {
                            call.state})..."
                    )
                    player.play_file(prompt_file)
                    self.logger.info(
                        f"[VM IVR] ✓ Finished playing PIN entry prompt (call state: {
                            call.state})"
                    )
                finally:
                    try:
                        os.unlink(prompt_file)
                    except Exception:
                        pass

                time.sleep(0.5)
                self.logger.info(f"[VM IVR] Post-prompt pause complete, checking call state...")

                # Check if call was terminated early (e.g., immediate BYE after answering)
                # Log the actual call state for debugging
                self.logger.info(
                    f"[VM IVR] Call state check: call_id={call_id}, state={
                        call.state}, state.value={
                        call.state.value if hasattr(
                            call.state, 'value') else 'N/A'}"
                )

                if call.state == CallState.ENDED:
                    self.logger.info(f"")
                    self.logger.info(f"[VM IVR] ✗ call ended before IVR could start")
                    self.logger.info(
                        f"[VM IVR] Extension: {
                            call.voicemail_extension}"
                    )
                    self.logger.info(f"[VM IVR] State: {call.state}")
                    self.logger.info(f"[VM IVR] Exiting IVR session")
                    self.logger.info(f"")
                    return

                self.logger.info(f"")
                self.logger.info(f"[VM IVR] ✓ IVR fully started and ready for user input")
                self.logger.info(
                    f"[VM IVR] Extension: {
                        call.voicemail_extension}"
                )
                self.logger.info(f"[VM IVR] State: {call.state}")
                self.logger.info(f"[VM IVR] Waiting for PIN entry...")
                self.logger.info(f"")

                # Main IVR loop - listen for DTMF input
                ivr_active = True
                last_audio_check = time.time()

                # DTMF debouncing: track last detected digit and time to
                # prevent duplicates
                last_detected_digit = None
                last_detection_time = 0
                DTMF_DEBOUNCE_SECONDS = 0.5  # Ignore same digit within 500ms

                # Constants for DTMF detection
                # ~0.5s of audio at 160 bytes per 20ms RTP packet
                DTMF_DETECTION_PACKETS = 40  # 40 packets * 20ms = 0.8s of audio
                # Minimum audio data needed for reliable DTMF detection
                MIN_AUDIO_BYTES_FOR_DTMF = 1600

                while ivr_active:
                    # Check if call is still active
                    if call.state == CallState.ENDED:
                        self.logger.info(f"[VM IVR] Call {call_id} ended - exiting IVR loop")
                        break

                    # Detect DTMF from either SIP INFO (out-of-band) or in-band
                    # audio
                    digit = None

                    # Priority 1: Check for DTMF from SIP INFO messages (most
                    # reliable)
                    if hasattr(call, "dtmf_info_queue") and call.dtmf_info_queue:
                        digit = call.dtmf_info_queue.pop(0)
                        self.logger.info(f"[VM IVR] >>> DTMF RECEIVED (SIP INFO): '{digit}' <<<")
                    else:
                        # Priority 2: Fall back to in-band DTMF detection from
                        # audio
                        time.sleep(0.1)

                        # Check for recorded audio (DTMF tones from user)
                        if hasattr(recorder, "recorded_data") and recorder.recorded_data:
                            # Get recent audio data
                            if len(recorder.recorded_data) > 0:
                                # Collect last portion of audio for DTMF
                                # detection
                                recent_audio = b"".join(
                                    recorder.recorded_data[-DTMF_DETECTION_PACKETS:]
                                )

                                if (
                                    len(recent_audio) > MIN_AUDIO_BYTES_FOR_DTMF
                                ):  # Need sufficient audio for DTMF
                                    try:
                                        # Detect DTMF in audio with error
                                        # handling
                                        digit = dtmf_detector.detect(recent_audio)
                                    except Exception as e:
                                        self.logger.error(f"Error detecting DTMF: {e}")
                                        digit = None

                                    if digit:
                                        # Debounce: ignore duplicate detections
                                        # of same digit within debounce period
                                        current_time = time.time()
                                        if (
                                            digit == last_detected_digit
                                            and (current_time - last_detection_time)
                                            < DTMF_DEBOUNCE_SECONDS
                                        ):
                                            # Same digit detected too soon,
                                            # likely echo or lingering tone
                                            self.logger.debug(
                                                f"[VM IVR] DTMF '{digit}' debounced (duplicate within {DTMF_DEBOUNCE_SECONDS}s)"
                                            )
                                            continue

                                        # Update debounce tracking
                                        last_detected_digit = digit
                                        last_detection_time = current_time
                                        self.logger.info(
                                            f"[VM IVR] >>> DTMF RECEIVED (In-band audio): '{digit}' <<<"
                                        )

                    # Process detected DTMF digit (from either SIP INFO or
                    # in-band)
                    if digit:
                        # Handle DTMF input through IVR
                        self.logger.info(
                            f"[VM IVR] Processing DTMF '{digit}' through IVR state machine..."
                        )
                        self.logger.info(
                            f"[VM IVR] Current IVR state: {
                                voicemail_ivr.state}"
                        )
                        action = voicemail_ivr.handle_dtmf(digit)
                        self.logger.info(
                            f"[VM IVR] IVR returned action: {
                                action.get('action')}"
                        )
                        self.logger.info(
                            f"[VM IVR] New IVR state: {
                                voicemail_ivr.state}"
                        )

                        # Process IVR action
                        if action["action"] == "play_message":
                            # Check if call is still active before playing
                            if call.state == CallState.ENDED:
                                self.logger.info(
                                    f"[VM IVR] Call {call_id} ended, skipping message playback"
                                )
                                break
                            # Play the voicemail message
                            file_path = action.get("file_path")
                            message_id = action.get("message_id")
                            caller_id = action.get("caller_id")
                            self.logger.info(
                                f"[VM IVR] Playing voicemail message: {message_id} from {caller_id}"
                            )
                            if file_path and os.path.exists(file_path):
                                player.play_file(file_path)
                                mailbox.mark_listened(message_id)
                                self.logger.info(
                                    f"[VM IVR] ✓ Voicemail {message_id} played and marked as listened"
                                )
                            else:
                                self.logger.warning(
                                    f"[VM IVR] ✗ Voicemail file not found: {file_path}"
                                )
                            time.sleep(0.5)

                        elif action["action"] == "play_prompt":
                            # Check if call is still active before playing
                            if call.state == CallState.ENDED:
                                self.logger.info(
                                    f"[VM IVR] Call {call_id} ended, skipping prompt playback"
                                )
                                break
                            # Play a prompt
                            prompt_type = action.get("prompt", "main_menu")
                            self.logger.info(f"[VM IVR] Playing prompt: {prompt_type}")
                            # Try to load from voicemail_prompts/ directory,
                            # fallback to tone generation
                            prompt_audio = get_prompt_audio(prompt_type)

                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(prompt_audio)
                                prompt_file = temp_file.name

                            try:
                                player.play_file(prompt_file)
                                self.logger.info(f"[VM IVR] ✓ Prompt '{prompt_type}' played")
                            finally:
                                try:
                                    os.unlink(prompt_file)
                                except OSError:
                                    pass  # File already deleted or doesn't exist

                            time.sleep(0.3)

                        elif action["action"] == "hangup":
                            # Check if call is still active before playing
                            # goodbye
                            if call.state == CallState.ENDED:
                                self.logger.info(
                                    f"[VM IVR] Call {call_id} already ended, skipping goodbye prompt"
                                )
                                ivr_active = False
                                break
                            self.logger.info(
                                f"[VM IVR] User requested hangup - playing goodbye and ending call"
                            )
                            # Play goodbye and end call
                            # Try to load from voicemail_prompts/ directory,
                            # fallback to tone generation
                            goodbye_prompt = get_prompt_audio("goodbye")
                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(goodbye_prompt)
                                prompt_file = temp_file.name

                            try:
                                player.play_file(prompt_file)
                            finally:
                                try:
                                    os.unlink(prompt_file)
                                except OSError:
                                    pass  # File already deleted or doesn't exist

                            time.sleep(1)
                            ivr_active = False

                        elif action["action"] == "start_recording":
                            # Start recording greeting
                            if call.state == CallState.ENDED:
                                self.logger.info(f"Call {call_id} ended, cannot start recording")
                                break

                            self.logger.info(
                                f"Starting greeting recording for extension {
                                    call.voicemail_extension}"
                            )

                            # Play beep tone
                            beep_prompt = get_prompt_audio("beep")
                            with tempfile.NamedTemporaryFile(
                                suffix=".wav", delete=False
                            ) as temp_file:
                                temp_file.write(beep_prompt)
                                beep_file = temp_file.name

                            try:
                                player.play_file(beep_file)
                            finally:
                                try:
                                    os.unlink(beep_file)
                                except OSError:
                                    pass

                            time.sleep(0.2)

                            # Start recording
                            recorder.recorded_data = []  # Clear previous recording
                            recording_start_time = time.time()
                            max_recording_time = 120  # 2 minutes max

                            # Wait for # to stop recording or timeout
                            recording = True
                            while recording and ivr_active:
                                if call.state == CallState.ENDED:
                                    self.logger.info(f"Call {call_id} ended during recording")
                                    recording = False
                                    break

                                # Check for timeout
                                if time.time() - recording_start_time > max_recording_time:
                                    self.logger.info(
                                        f"Recording timed out after {max_recording_time}s"
                                    )
                                    recording = False
                                    break

                                time.sleep(0.1)

                                # Check for DTMF # to stop recording (SIP INFO
                                # or in-band)
                                stop_digit = None

                                # Priority 1: Check SIP INFO queue
                                if hasattr(call, "dtmf_info_queue") and call.dtmf_info_queue:
                                    stop_digit = call.dtmf_info_queue.pop(0)
                                    self.logger.info(
                                        f"Received DTMF from SIP INFO during recording: {stop_digit}"
                                    )
                                # Priority 2: Check in-band audio
                                elif hasattr(recorder, "recorded_data") and recorder.recorded_data:
                                    recent_audio = b"".join(
                                        recorder.recorded_data[-DTMF_DETECTION_PACKETS:]
                                    )
                                    if len(recent_audio) > MIN_AUDIO_BYTES_FOR_DTMF:
                                        try:
                                            stop_digit = dtmf_detector.detect(recent_audio)
                                            if stop_digit:
                                                self.logger.info(
                                                    f"Received DTMF from in-band audio during recording: {stop_digit}"
                                                )
                                        except Exception as e:
                                            self.logger.error(
                                                f"Error detecting DTMF during recording: {e}"
                                            )
                                            stop_digit = None

                                if stop_digit == "#":
                                    self.logger.info(f"Recording stopped by user (#)")
                                    recording = False
                                    # Process through IVR to transition state
                                    action = voicemail_ivr.handle_dtmf("#")
                                    # Save recorded audio - convert to WAV format
                                    if (
                                        hasattr(recorder, "recorded_data")
                                        and recorder.recorded_data
                                    ):
                                        greeting_audio_raw = b"".join(recorder.recorded_data)
                                        # Convert raw audio to WAV format before saving
                                        greeting_audio_wav = self._build_wav_file(
                                            greeting_audio_raw
                                        )
                                        voicemail_ivr.save_recorded_greeting(greeting_audio_wav)
                                        self.logger.info(
                                            f"Saved recorded greeting as WAV ({
                                                len(greeting_audio_wav)} bytes, {
                                                len(greeting_audio_raw)} bytes raw audio)"
                                        )
                                    # Handle the returned action
                                    if action.get("action") == "play_prompt":
                                        # Play greeting review menu prompt
                                        prompt_type = action.get("prompt", "greeting_review_menu")
                                        prompt_audio = get_prompt_audio(prompt_type)
                                        with tempfile.NamedTemporaryFile(
                                            suffix=".wav", delete=False
                                        ) as temp_file:
                                            temp_file.write(prompt_audio)
                                            prompt_file = temp_file.name
                                        try:
                                            player.play_file(prompt_file)
                                        finally:
                                            try:
                                                os.unlink(prompt_file)
                                            except OSError:
                                                pass
                                    elif action.get("action") == "stop_recording":
                                        # Also valid, just log it
                                        self.logger.info(
                                            f"IVR returned stop_recording action, continuing"
                                        )
                                    else:
                                        # Unexpected action type
                                        self.logger.warning(
                                            f"Unexpected action from IVR after #: {
                                                action.get('action')}"
                                        )
                                    # Clear recorder after saving
                                    recorder.recorded_data = []
                                    break

                        elif action["action"] == "play_greeting":
                            # Play back the recorded greeting for review
                            if call.state == CallState.ENDED:
                                self.logger.info(f"Call {call_id} ended, cannot play greeting")
                                break

                            greeting_data = voicemail_ivr.get_recorded_greeting()
                            if greeting_data:
                                self.logger.info(
                                    f"Playing recorded greeting for review ({
                                        len(greeting_data)} bytes)"
                                )

                                # Greeting is already in WAV format (converted when recorded)
                                with tempfile.NamedTemporaryFile(
                                    suffix=".wav", delete=False
                                ) as temp_file:
                                    temp_file.write(greeting_data)
                                    greeting_file = temp_file.name

                                try:
                                    player.play_file(greeting_file)
                                finally:
                                    try:
                                        os.unlink(greeting_file)
                                    except OSError:
                                        pass

                                time.sleep(0.5)

                                # Play review menu again
                                review_prompt = get_prompt_audio("greeting_review_menu")
                                with tempfile.NamedTemporaryFile(
                                    suffix=".wav", delete=False
                                ) as temp_file:
                                    temp_file.write(review_prompt)
                                    prompt_file = temp_file.name

                                try:
                                    player.play_file(prompt_file)
                                finally:
                                    try:
                                        os.unlink(prompt_file)
                                    except OSError:
                                        pass
                            else:
                                self.logger.warning(
                                    f"No recorded greeting data available for playback"
                                )

                        elif action["action"] == "collect_digit":
                            # Digit is being collected (e.g., PIN entry)
                            # No additional action needed - digit is already stored in IVR state
                            # Just continue the loop to wait for more digits
                            self.logger.debug(
                                f"[VM IVR] Collecting digit, waiting for more input..."
                            )

                        else:
                            # Unknown action type
                            self.logger.warning(
                                f"[VM IVR] Unknown action type: {action.get('action')} - continuing"
                            )

                        # Clear audio buffer after processing DTMF
                        # Note: Directly modifying internal state - consider
                        # adding clear() method to RTPRecorder
                        if hasattr(recorder, "recorded_data"):
                            recorder.recorded_data = []

                    # Timeout after 60 seconds of no activity
                    if time.time() - last_audio_check > 60:
                        self.logger.info(
                            f"Voicemail IVR timeout for {
                                call.voicemail_extension}"
                        )
                        ivr_active = False

                self.logger.info(f"")
                self.logger.info(f"{'=' * 70}")
                self.logger.info(f"VOICEMAIL IVR SESSION COMPLETED")
                self.logger.info(f"  Call ID: {call_id}")
                self.logger.info(f"  Extension: {call.voicemail_extension}")
                self.logger.info(f"  Final State: {call.state}")
                self.logger.info(f"{'=' * 70}")

            finally:
                self.logger.info(f"[VM IVR] Cleaning up RTP player and recorder...")
                player.stop()
                recorder.stop()
                self.logger.info(f"[VM IVR] ✓ RTP resources released")

            # End the call
            self.logger.info(f"[VM IVR] Ending call {call_id}...")
            self.end_call(call_id)
            self.logger.info(f"[VM IVR] ✓ Call ended")

        except Exception as e:
            self.logger.error(f"")
            self.logger.error(f"{'=' * 70}")
            self.logger.error(f"ERROR IN VOICEMAIL IVR SESSION")
            self.logger.error(f"  Call ID: {call_id}")
            self.logger.error(f"  Error: {e}")
            self.logger.error(f"{'=' * 70}")
            import traceback

            traceback.print_exc()
            try:
                self.end_call(call_id)
            except Exception as e:
                self.logger.error(f"[VM IVR] Error ending call during cleanup: {e}")

    def _build_wav_file(self, audio_data):
        """
        Build a proper WAV file from raw audio data
        Assumes G.711 μ-law (PCMU) codec at 8kHz

        Args:
            audio_data: Raw audio payload data

        Returns:
            bytes: Complete WAV file
        """
        # WAV file format for G.711 μ-law
        sample_rate = 8000
        bits_per_sample = 8
        num_channels = 1
        audio_format = 7  # μ-law

        # Calculate sizes
        # RIFF header: 12 bytes (RIFF + size + WAVE)
        # fmt chunk: 26 bytes (chunk header + fmt data + extension)
        # data chunk header: 8 bytes (data + size)
        # Total header size: 46 bytes
        data_size = len(audio_data)
        # File size for RIFF header is total size minus 8 bytes (RIFF + size
        # field itself)
        file_size = 4 + 26 + 8 + data_size  # WAVE + fmt chunk + data chunk header + data

        # Build WAV header (12 bytes)
        wav_header = struct.pack("<4sI4s", b"RIFF", file_size, b"WAVE")

        # Format chunk (24 bytes + 2 bytes extension = 26 bytes)
        fmt_chunk = struct.pack(
            "<4sIHHIIHH",
            b"fmt ",
            18,
            # Chunk size (18 for non-PCM formats like
            # μ-law)
            audio_format,
            num_channels,
            sample_rate,
            sample_rate * num_channels * bits_per_sample // 8,  # Byte rate
            num_channels * bits_per_sample // 8,  # Block align
            bits_per_sample,
        )

        # Add extension size (2 bytes, value 0 for G.711)
        fmt_extension = struct.pack("<H", 0)

        # Data chunk header (8 bytes)
        data_chunk = struct.pack("<4sI", b"data", data_size)

        # Combine all parts
        return wav_header + fmt_chunk + fmt_extension + data_chunk + audio_data

    def _handle_emergency_call(self, from_ext, to_ext, call_id, message, from_addr):
        """
        Handle emergency call (911) according to Kari's Law

        Federal law requires direct 911 dialing without prefix and immediate routing.

        Args:
            from_ext: Calling extension
            to_ext: Dialed number (911, 9911, etc.)
            call_id: Call ID
            message: SIP INVITE message
            from_addr: Caller address

        Returns:
            True if emergency call was handled
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder, SDPSession

        self.logger.critical("=" * 70)
        self.logger.critical("🚨 EMERGENCY CALL INITIATED")
        self.logger.critical("=" * 70)

        # Handle via Kari's Law compliance module
        success, routing_info = self.karis_law.handle_emergency_call(
            caller_extension=from_ext, dialed_number=to_ext, call_id=call_id, from_addr=from_addr
        )

        if not success:
            self.logger.error(
                f"Emergency call handling failed: {routing_info.get('error', 'Unknown error')}"
            )
            return False

        if not routing_info.get("success"):
            self.logger.error(
                f"Emergency call routing failed: {routing_info.get('error', 'No trunk available')}"
            )
            # Still return True because the call was processed (notification sent)
            # but log the routing failure critically
            self.logger.critical("⚠️  EMERGENCY CALL COULD NOT BE ROUTED TO 911")
            return True

        # Parse SDP from caller's INVITE
        caller_sdp = None
        if message.body:
            caller_sdp_obj = SDPSession()
            caller_sdp_obj.parse(message.body)
            caller_sdp = caller_sdp_obj.get_audio_info()

            if caller_sdp:
                self.logger.critical(f"Caller RTP: {caller_sdp['address']}:{caller_sdp['port']}")

        # Create call record for tracking
        normalized_number = routing_info.get("destination", "911")
        call = self.call_manager.create_call(call_id, from_ext, normalized_number)
        call.start()
        call.original_invite = message
        call.caller_addr = from_addr
        call.caller_rtp = caller_sdp
        call.is_emergency = True
        call.emergency_routing = routing_info

        # Start CDR record
        self.cdr_system.start_record(call_id, from_ext, normalized_number)

        # Allocate RTP relay for the call
        rtp_ports = self.rtp_relay.allocate_relay(call_id)
        if rtp_ports:
            call.rtp_ports = rtp_ports

            # Set caller's endpoint if we have RTP info
            if caller_sdp:
                caller_endpoint = (caller_sdp["address"], caller_sdp["port"])
                relay_info = self.rtp_relay.active_relays.get(call_id)
                if relay_info:
                    handler = relay_info["handler"]
                    handler.set_endpoint1(caller_endpoint)
                    self.logger.info(f"Emergency call RTP relay configured")

        # In production, this would:
        # 1. Route the call through the emergency trunk to 911
        # 2. Provide location information (Ray Baum's Act)
        # 3. Maintain the call until disconnected
        # 4. Log all details for regulatory compliance

        # For now, send 200 OK to acknowledge the call was processed
        # The trunk system will handle actual routing
        server_ip = self._get_server_ip()

        # Build SDP for response
        sdp_builder = SDPBuilder()
        if caller_sdp:
            caller_codecs = caller_sdp.get("formats", None)
            sdp_builder.set_media(
                "audio",
                rtp_ports[0] if rtp_ports else 10000,
                "RTP/AVP",
                caller_codecs if caller_codecs else ["0", "8"],
            )
        else:
            sdp_builder.set_media(
                "audio", rtp_ports[0] if rtp_ports else 10000, "RTP/AVP", ["0", "8"]
            )

        sdp_builder.set_connection(server_ip)
        response_sdp = sdp_builder.build()

        # Send 200 OK
        ok_response = SIPMessageBuilder.build_response(
            code=200,
            reason="OK",
            to_addr=message.get_header("From"),
            from_addr=message.get_header("To"),
            call_id=call_id,
            cseq=message.get_header("CSeq"),
            via=message.get_header("Via"),
            contact=f"sip:{from_ext}@{server_ip}:{self.sip_server.port}",
            body=response_sdp,
        )

        self.sip_server._send_message(ok_response.build(), from_addr)

        self.logger.critical("Emergency call acknowledged and routed")
        self.logger.critical(f"Trunk: {routing_info.get('trunk_name', 'Unknown')}")
        self.logger.critical("=" * 70)

        return True

    def get_status(self):
        """
        Get PBX status

        Returns:
            Dictionary with status information
        """
        return {
            "running": self.running,
            "registered_extensions": self.extension_registry.get_registered_count(),
            "active_calls": len(self.call_manager.get_active_calls()),
            "total_calls": len(self.call_manager.call_history),
            "active_recordings": len(self.recording_system.active_recordings),
            "active_conferences": len(self.conference_system.get_active_rooms()),
            "parked_calls": len(self.parking_system.get_parked_calls()),
            "queued_calls": sum(len(q.queue) for q in self.queue_system.queues.values()),
        }

    def get_ad_integration_status(self):
        """
        Get Active Directory integration status

        Returns:
            Dictionary with AD integration status
        """
        if not self.ad_integration:
            return {
                "enabled": False,
                "connected": False,
                "auto_provision": False,
                "server": None,
                "last_sync": None,
                "synced_users": 0,
                "error": None,
            }

        # Try to connect to check status
        connected = False
        error = None
        try:
            connected = self.ad_integration.connect()
        except Exception as e:
            error = str(e)

        # Get count of AD-synced extensions
        synced_count = 0
        if self.extension_db:
            try:
                synced_extensions = self.extension_db.get_ad_synced()
                synced_count = len(synced_extensions)
            except Exception as e:
                self.logger.error(f"Error getting AD-synced extension count: {e}")

        return {
            "enabled": self.ad_integration.enabled,
            "connected": connected,
            "auto_provision": self.ad_integration.auto_provision,
            "server": self.ad_integration.ldap_server,
            "synced_users": synced_count,
            "error": error,
        }

    def sync_ad_users(self):
        """
        Manually trigger Active Directory user synchronization

        Returns:
            dict: Sync results with count and status
        """
        if not self.ad_integration:
            return {
                "success": False,
                "error": "Active Directory integration is not enabled",
                "synced_count": 0,
            }

        if not self.ad_integration.enabled:
            return {
                "success": False,
                "error": "Active Directory integration is disabled",
                "synced_count": 0,
            }

        try:
            self.logger.info("Manual AD user sync triggered")
            sync_result = self.ad_integration.sync_users(
                extension_registry=self.extension_registry,
                extension_db=self.extension_db,
                phone_provisioning=(
                    self.phone_provisioning if hasattr(self, "phone_provisioning") else None
                ),
            )

            # Handle both old (int) and new (dict) return types for backward
            # compatibility
            if isinstance(sync_result, int):
                synced_count = sync_result
                extensions_to_reboot = []
            else:
                synced_count = sync_result.get("synced_count", 0)
                extensions_to_reboot = sync_result.get("extensions_to_reboot", [])

            # Reload extensions after sync
            self.extension_registry.reload()

            # Automatically sync phone book from AD if enabled
            phone_book_synced = 0
            if hasattr(self, "phone_book") and self.phone_book and self.phone_book.enabled:
                if self.phone_book.auto_sync_from_ad:
                    self.logger.info(
                        "Auto-syncing phone book from Active Directory after AD user sync"
                    )
                    phone_book_synced = self.phone_book.sync_from_ad(
                        self.ad_integration, self.extension_registry
                    )
                    self.logger.info(
                        f"Phone book synced {phone_book_synced} entries from Active Directory"
                    )

            # Automatically trigger phone reboots for updated extensions
            rebooted_count = 0
            if (
                extensions_to_reboot
                and hasattr(self, "phone_provisioning")
                and self.phone_provisioning
            ):
                self.logger.info(
                    f"Auto-provisioning: Automatically rebooting {
                        len(extensions_to_reboot)} phones after AD sync"
                )
                for extension_number in extensions_to_reboot:
                    try:
                        if self.phone_provisioning.reboot_phone(extension_number, self.sip_server):
                            rebooted_count += 1
                    except Exception as reboot_error:
                        self.logger.warning(
                            f"Could not reboot phone for extension {extension_number}: {reboot_error}"
                        )

                if rebooted_count > 0:
                    self.logger.info(
                        f"Auto-provisioning: Successfully triggered reboot for {rebooted_count} phones"
                    )

            return {
                "success": True,
                "synced_count": synced_count,
                "rebooted_count": rebooted_count,
                "phone_book_synced": phone_book_synced,
                "error": None,
            }
        except Exception as e:
            self.logger.error(f"Error during AD sync: {e}")
            import traceback

            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0,
                "rebooted_count": 0,
                "phone_book_synced": 0,
            }
