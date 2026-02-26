"""
Core PBX implementation
Central coordinator for all PBX functionality
"""

import re
import struct
import threading
import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

from pbx.core.auto_attendant_handler import AutoAttendantHandler
from pbx.core.call import CallManager
from pbx.core.call_router import CallRouter
from pbx.core.emergency_handler import EmergencyHandler
from pbx.core.feature_initializer import FeatureInitializer
from pbx.core.paging_handler import PagingHandler
from pbx.core.voicemail_handler import VoicemailHandler
from pbx.features.extensions import ExtensionRegistry
from pbx.features.webhooks import WebhookEvent
from pbx.rtp.handler import RTPRelay
from pbx.sip.server import SIPServer
from pbx.utils.config import Config
from pbx.utils.database import DatabaseBackend, RegisteredPhonesDB
from pbx.utils.logger import PBXLogger, get_logger


class PBXCore:
    """Main PBX system coordinator"""

    def __init__(self, config_file: str = "config.yml") -> None:
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
        self.start_time = datetime.now(UTC)

        # Initialize database backend
        self.database = DatabaseBackend(self.config)
        self.registered_phones_db = None
        self.extension_db = None
        if self.database.connect():
            self._run_alembic_migrations()
            self.database.create_tables()
            from pbx.utils.database import ExtensionDB

            self.registered_phones_db = RegisteredPhonesDB(self.database)
            self.extension_db = ExtensionDB(self.database)
            self._log_startup(
                f"Database backend initialized successfully ({self.database.db_type})"
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
            host=self.config.get("server.sip_host", "0.0.0.0"),  # nosec B104 - SIP server needs to bind to all interfaces
            port=self.config.get("server.sip_port", 5060),
            pbx_core=self,
        )

        # Initialize all feature subsystems via FeatureInitializer
        FeatureInitializer.initialize(self)

        # Initialize Prometheus metrics exporter
        self.metrics_exporter = None
        self._metrics_running = False
        self._metrics_thread: threading.Thread | None = None
        if self.config.get("monitoring.prometheus.enabled", False):
            from pbx.utils.prometheus_exporter import PBXMetricsExporter

            self.metrics_exporter = PBXMetricsExporter()
            self.metrics_exporter.set_system_info(
                version=self.config.get("server.version", "1.0.0"),
                server_name=self.config.get("server.server_name", "Warden VoIP"),
            )
            self._log_startup("Prometheus metrics exporter initialized")

        # Initialize API server
        api_host = self.config.get("api.host", "0.0.0.0")  # nosec B104 - API server needs to bind to all interfaces
        api_port = self.config.get("api.port", 9000)
        from pbx.api.server import PBXFlaskServer

        self.api_server = PBXFlaskServer(self, api_host, api_port)

        # Initialize handler classes for delegated functionality
        self._call_router = CallRouter(self)
        self._voicemail_handler = VoicemailHandler(self)
        self._auto_attendant_handler = AutoAttendantHandler(self)
        self._emergency_handler = EmergencyHandler(self)
        self._paging_handler = PagingHandler(self)

        self.running = False

        self.logger.info("PBX Core initialized with all features")

    def _log_startup(self, message: str, level: str = "info") -> None:
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

    def _run_alembic_migrations(self) -> None:
        """
        Run pending Alembic database migrations before starting the application.

        Called during startup after the database connection is established but
        before create_tables(). This ensures schema migrations from new deployments
        (git pull + systemctl restart) are applied automatically.

        Non-fatal: if Alembic is unavailable or migrations fail, the app logs a
        warning and continues (create_tables will handle missing tables via
        CREATE TABLE IF NOT EXISTS).
        """
        try:
            from alembic.command import upgrade
            from alembic.config import Config as AlembicConfig

            alembic_cfg = AlembicConfig("alembic.ini")

            # Build database URL from the same config the app uses
            db_host = self.config.get("database.host", "localhost")
            db_port = self.config.get("database.port", 5432)
            db_name = self.config.get("database.name", "pbx")
            db_user = self.config.get("database.user", "pbx")
            db_password = self.config.get("database.password", "")
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)

            upgrade(alembic_cfg, "head")
            self._log_startup("Alembic database migrations applied successfully")
        except Exception as e:
            self.logger.warning(f"Alembic migration skipped or failed: {e}")

    def _auto_seed_critical_extensions(self) -> None:
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
                        self.logger.warning("Extension: 1001")
                        self.logger.warning(f"Password:  {ext_config['password']}")
                        self.logger.warning(f"Voicemail PIN: {ext_config['voicemail_pin']}")
                        self.logger.warning("")
                        self.logger.warning("⚠️  CHANGE THIS PASSWORD IMMEDIATELY via admin panel!")
                        self.logger.warning(
                            "   Access admin panel: https://<your-server-ip>:9000/admin/"
                        )
                        self.logger.warning("=" * 70)

            except (KeyError, TypeError, ValueError) as e:
                self.logger.error(f"Failed to auto-seed extension {number}: {e}")

        if seeded_count > 0:
            self.logger.info(f"Auto-seeded {seeded_count} critical extension(s) at startup")

    def _start_metrics_collector(self) -> None:
        """Start background thread for periodic system resource metrics."""
        if not self.metrics_exporter:
            return
        self._metrics_running = True
        interval = self.config.get("monitoring.prometheus.resource_collection_interval", 15)
        self._metrics_interval = max(1, int(interval) if interval else 15)
        self._metrics_thread = threading.Thread(
            target=self._metrics_collection_loop,
            name="MetricsCollector",
            daemon=True,
        )
        self._metrics_thread.start()
        self._log_startup("Prometheus metrics collector started")

    def _stop_metrics_collector(self) -> None:
        """Stop background metrics collection thread."""
        self._metrics_running = False
        if self._metrics_thread and self._metrics_thread.is_alive():
            self._metrics_thread.join(timeout=5)
        self._metrics_thread = None

    def _metrics_collection_loop(self) -> None:
        """Periodically collect system resource metrics."""
        import time

        import psutil

        while self._metrics_running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                self.metrics_exporter.update_system_resources(
                    cpu_percent=cpu,
                    memory_bytes=mem.used,
                )

                disk = psutil.disk_usage("/")
                self.metrics_exporter.disk_usage_bytes.labels(mount_point="/").set(disk.used)

                self.metrics_exporter.update_extensions(
                    self.extension_registry.get_registered_count()
                )
                self.metrics_exporter.active_calls.set(len(self.call_manager.get_active_calls()))

                if hasattr(self, "conference_system") and self.conference_system:
                    self.metrics_exporter.conferences_active.set(
                        len(self.conference_system.get_active_rooms())
                    )

            except Exception as e:
                self.logger.debug(f"Metrics collection error: {e}")

            # Sleep in small increments so stop is responsive
            for _ in range(self._metrics_interval):
                if not self._metrics_running:
                    break
                time.sleep(1)

    def _load_provisioning_devices(self) -> None:
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

    def start(self) -> bool:
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

        # Start Prometheus metrics collector
        self._start_metrics_collector()

        self.logger.info("PBX system started successfully")
        return True

    def stop(self) -> None:
        """Stop PBX system"""
        self.logger.info("Stopping PBX system...")
        self.running = False

        # Stop Prometheus metrics collector
        self._stop_metrics_collector()

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

    def register_extension(
        self,
        from_header: str,
        addr: tuple[str, int],
        user_agent: str | None = None,
        contact: str | None = None,
    ) -> bool:
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
                except (KeyError, TypeError, ValueError) as e:
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
                        self.logger.error(f"  Traceback: {traceback.format_exc()}")

                # Record successful registration metric
                if self.metrics_exporter:
                    self.metrics_exporter.record_extension_registration("success")

                # Trigger webhook event
                self.webhook_system.trigger_event(
                    WebhookEvent.EXTENSION_REGISTERED,
                    {
                        "extension": extension_number,
                        "ip_address": addr[0],
                        "port": addr[1],
                        "user_agent": user_agent,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

                return True
            # Record failed registration metric
            if self.metrics_exporter:
                self.metrics_exporter.record_extension_registration("failure")
            self.logger.warning(f"Unknown extension {extension_number} attempted registration")
            return False

        self.logger.warning(f"Could not parse extension from {from_header}")
        return False

    def _extract_mac_address(self, contact: str | None, user_agent: str | None) -> str | None:
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

    def _detect_phone_model(self, user_agent: str | None) -> str | None:
        """
        Detect phone model from User-Agent string

        Args:
            user_agent: User-Agent header string

        Returns:
            Phone model identifier string or None.
            Possible values: 'YEALINK_T33G', 'ZIP33G', 'ZIP37G', or None for unknown/other
        """
        if not user_agent:
            return None

        user_agent_upper = user_agent.upper()

        # Check for Yealink T33G (before ZIP checks to avoid substring matches)
        # Typical UA: "Yealink SIP-T33G 124.86.0.40 00:15:65:XX:XX:XX"
        if "T33G" in user_agent_upper and "ZIP" not in user_agent_upper:
            return "YEALINK_T33G"

        # Check for Zultys ZIP33G (OEM rebrand of Yealink T28G)
        if "ZIP33G" in user_agent_upper or "ZIP 33G" in user_agent_upper:
            return "ZIP33G"

        # Check for Zultys ZIP37G (OEM rebrand of Yealink T46G)
        if "ZIP37G" in user_agent_upper or "ZIP 37G" in user_agent_upper:
            return "ZIP37G"

        return None

    def _get_codecs_for_phone_model(
        self, phone_model: str | None, default_codecs: list[str] | None = None
    ) -> list[str]:
        """
        Get appropriate codec list for a specific phone model

        Args:
            phone_model: Phone model identifier (from _detect_phone_model)
            default_codecs: Default codecs to use if no specific requirement

        Returns:
            list of codec payload types as strings
        """
        # Get DTMF payload type from config (default 101)
        dtmf_payload_type = self.config.get("features.dtmf.payload_type", 101)
        dtmf_pt_str = str(dtmf_payload_type)

        if phone_model == "YEALINK_T33G":
            # Yealink T33G: supports G.711 (PCMU/PCMA), G.722, G.729
            # Payload types: 0=PCMU, 8=PCMA, 9=G722, 18=G729
            codecs = ["0", "8", "9", "18", dtmf_pt_str]
            self.logger.debug(f"Using Yealink T33G codec set: PCMU/PCMA/G722/G729 ({codecs})")
            return codecs

        if phone_model == "ZIP37G":
            # ZIP37G: Use PCMU/PCMA only
            # Payload types: 0=PCMU, 8=PCMA
            codecs = ["0", "8", dtmf_pt_str]
            self.logger.debug(f"Using ZIP37G codec set: PCMU/PCMA ({codecs})")
            return codecs

        if phone_model == "ZIP33G":
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

    def _get_compatible_codecs(
        self, phone_model: str | None, answered_codecs: list[str] | None
    ) -> list[str]:
        """
        Compute codecs compatible with both the phone model and the answered codec set.

        When the PBX relays RTP without transcoding, both call legs must use the
        same codec.  This method intersects the callee's answered codecs with the
        phone-model-specific set (if any) so the 200 OK sent to the caller only
        offers codecs that both sides support.

        Args:
            phone_model: Phone model identifier (from _detect_phone_model)
            answered_codecs: Codecs the remote side actually selected (from SDP answer)

        Returns:
            list of codec payload types as strings
        """
        dtmf_payload_type = self.config.get("features.dtmf.payload_type", 101)
        dtmf_pt_str = str(dtmf_payload_type)

        model_codecs = self._get_codecs_for_phone_model(phone_model)

        if not answered_codecs:
            return model_codecs

        # Build intersection preserving the answered codec order (callee's preference)
        model_set = set(model_codecs)
        compatible = [c for c in answered_codecs if c in model_set]

        # Always include DTMF telephone-event if both sides have it
        if dtmf_pt_str in model_set and dtmf_pt_str not in compatible:
            compatible.append(dtmf_pt_str)

        # Ensure the intersection has at least one audio codec (not just DTMF)
        has_audio_codec = any(c != dtmf_pt_str for c in compatible)
        if compatible and has_audio_codec:
            self.logger.debug(
                f"Compatible codecs for {phone_model or 'unknown'}: {compatible}"
            )
            return compatible

        # If intersection is empty, fall back to the answered codecs to avoid
        # a completely empty SDP.  The phone will 488 if truly incompatible.
        self.logger.warning(
            f"No codec overlap between model {phone_model} and answered {answered_codecs}, "
            f"falling back to answered codecs"
        )
        return answered_codecs

    def _get_phone_user_agent(self, extension_number: str) -> str | None:
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
            query = """
            SELECT user_agent FROM registered_phones
            WHERE extension_number = %s
            ORDER BY last_registered DESC
            LIMIT 1
            """

            result = self.database.fetch_one(query, (extension_number,))
            if result and result.get("user_agent"):
                return result["user_agent"]
        except (KeyError, TypeError, ValueError) as e:
            self.logger.debug(f"Error retrieving User-Agent for extension {extension_number}: {e}")

        return None

    def _get_dtmf_payload_type(self) -> int:
        """
        Get DTMF payload type from configuration

        Returns:
            DTMF payload type as integer (default: 101)
        """
        return self.config.get("features.dtmf.payload_type", 101)

    def _get_ilbc_mode(self) -> int:
        """
        Get iLBC mode from configuration

        Returns:
            iLBC mode (20 or 30 ms) as integer (default: 30)
        """
        return self.config.get("codecs.ilbc.mode", 30)

    def route_call(
        self,
        from_header: str,
        to_header: str,
        call_id: str,
        message: Any,
        from_addr: tuple[str, int],
    ) -> bool:
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
        return self._call_router.route_call(from_header, to_header, call_id, message, from_addr)

    def _get_server_ip(self) -> str:
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
        except OSError:
            return "127.0.0.1"  # Last resort fallback

    def handle_callee_answer(
        self, call_id: str, response_message: Any, callee_addr: tuple[str, int]
    ) -> None:
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
                self.logger.info(f"Callee RTP: {callee_sdp['address']}:{callee_sdp['port']}")
                call.callee_rtp = callee_sdp
                call.callee_addr = callee_addr

        # Now we have both endpoints, complete the RTP relay setup
        # Cancel no-answer timer if it's running
        if call and call.no_answer_timer:
            call.no_answer_timer.cancel()
            self.logger.info(f"Cancelled no-answer timer for call {call_id}")

        # Check if this is a WebRTC-originated call
        webrtc_session_id = getattr(call, "webrtc_session_id", None)

        if webrtc_session_id and call.callee_rtp and call.rtp_ports:
            # --- WebRTC caller: start aiortc ↔ RTP media bridge ---
            callee_endpoint = (call.callee_rtp["address"], call.callee_rtp["port"])

            if hasattr(self, "webrtc_signaling") and self.webrtc_signaling:
                session = self.webrtc_signaling.get_session(webrtc_session_id)
                if session:
                    self.webrtc_signaling.start_media_bridge(
                        session, call.rtp_ports[0], callee_endpoint
                    )
                    self.logger.info(
                        f"WebRTC media bridge started for call {call_id}"
                    )

            # Mark call as connected
            call.connect()
            self.cdr_system.mark_answered(call_id)
            self.logger.info(f"WebRTC call {call_id} connected")
            return

        # --- Regular SIP-to-SIP path ---
        # Note: caller endpoint (A) was already set when INVITE was received
        if call.caller_rtp and call.callee_rtp and call.rtp_ports:
            caller_endpoint = (call.caller_rtp["address"], call.caller_rtp["port"])
            callee_endpoint = (call.callee_rtp["address"], call.callee_rtp["port"])

            # set both endpoints (caller was already set, but setting again is safe)
            # This ensures callee endpoint (B) is now known for bidirectional
            # relay
            self.rtp_relay.set_endpoints(call_id, caller_endpoint, callee_endpoint)
            self.logger.info(f"RTP relay connected for call {call_id}")

        # Mark call as connected
        call.connect()

        # Mark CDR as answered for analytics
        self.cdr_system.mark_answered(call_id)

        # Send 200 OK back to caller with PBX's RTP endpoint
        server_ip = self._get_server_ip()

        if call.rtp_ports and call.caller_addr:
            # Extract the callee's answered codecs from their 200 OK SDP.
            # The callee's 200 OK contains the codec(s) they actually selected,
            # so we must reflect those back to the caller to ensure both sides
            # use the same codec. The RTP relay does not transcode — if we offer
            # the caller their original full codec list they may pick a different
            # codec than the callee chose, resulting in no audio.
            callee_answered_codecs: list[str] | None = None
            if callee_sdp:
                callee_answered_codecs = callee_sdp.get("formats", None)
                if callee_answered_codecs:
                    self.logger.info(
                        f"Callee answered with codecs: {callee_answered_codecs}"
                    )

            # Get caller's phone model for any model-specific filtering
            caller_user_agent = self._get_phone_user_agent(call.from_extension)
            caller_phone_model = self._detect_phone_model(caller_user_agent)

            # Use the callee's answered codecs so both sides agree on the codec.
            # Fall back to the caller's original codecs only if the callee's
            # 200 OK had no SDP (shouldn't happen in practice).
            caller_codecs = call.caller_rtp.get("formats", None) if call.caller_rtp else None
            answered_codecs = callee_answered_codecs or caller_codecs

            # For phones with model-specific codec requirements, compute the
            # intersection of the callee's answered codecs and the phone model's
            # supported codecs.  This ensures the caller gets a codec it supports
            # that the callee has already committed to.
            codecs_for_caller = self._get_compatible_codecs(
                caller_phone_model, answered_codecs
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
                ok_response.set_header("Content-type", "application/sdp")

                # Build Contact header
                sip_port = self.config.get("server.sip_port", 5060)
                contact_uri = f"<sip:{call.to_extension}@{server_ip}:{sip_port}>"
                ok_response.set_header("Contact", contact_uri)

                # Send to caller
                self.sip_server._send_message(ok_response.build(), call.caller_addr)
                self.logger.info(f"Sent 200 OK to caller for call {call_id}")

    def end_call(self, call_id: str) -> None:
        """
        End call

        Args:
            call_id: Call identifier
        """
        call = self.call_manager.get_call(call_id)
        if call:
            self.logger.info(f"Ending call {call_id}")

            # Cancel no-answer timer if still running
            if call.no_answer_timer:
                call.no_answer_timer.cancel()
                call.no_answer_timer = None

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
                            f"Saved voicemail (on hangup) for extension {call.to_extension} from {call.from_extension}, duration: {duration}s"
                        )
                    else:
                        self.logger.warning(f"No audio recorded for voicemail on call {call_id}")

            # Record call end metric
            if self.metrics_exporter:
                call_duration = call.get_duration() if hasattr(call, "get_duration") else 0.0
                self.metrics_exporter.record_call_end(
                    duration=call_duration,
                    status="completed",
                    direction=getattr(call, "direction", "inbound"),
                )

            self.call_manager.end_call(call_id)
            self.rtp_relay.release_relay(call_id)

            # End CDR record for analytics
            self.cdr_system.end_record(call_id, hangup_cause="normal_clearing")

    def handle_dtmf_info(self, call_id: str, dtmf_digit: str) -> None:
        """
        Handle DTMF digit received via SIP INFO message

        This method queues DTMF digits received via out-of-band SIP INFO
        signaling for processing by IVR systems (voicemail, auto-attendant).

        Args:
            call_id: Call identifier
            dtmf_digit: DTMF digit ('0'-'9', '*', '#', 'A'-'D')

        Note:
            IVR loops (voicemail_handler, auto_attendant_handler) check
            call.dtmf_info_queue for queued SIP INFO digits and fall back
            to in-band DTMF detection when the queue is empty.
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
        elif hasattr(call, "auto_attendant_active") and call.auto_attendant_active:
            self.logger.info(
                f"Queued DTMF '{dtmf_digit}' from SIP INFO for auto-attendant on call {call_id}"
            )
        else:
            self.logger.debug(f"Queued DTMF '{dtmf_digit}' from SIP INFO for call {call_id}")

    def transfer_call(self, call_id: str, new_destination: str) -> bool:
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
            f"Transferring call {call_id} from {call.from_extension} to {new_destination}"
        )

        # Determine which party to send REFER to (typically the caller)
        refer_to_addr = call.caller_addr or call.callee_addr
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
            f"<sip:{call.to_extension}@{server_ip}:{sip_port}>",
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

    def blind_transfer(self, call_id: str, destination: str) -> bool:
        """
        Perform blind (unattended) transfer.

        The transferring party's call leg is immediately terminated and the
        remaining party is connected to the new destination via a new INVITE.

        Args:
            call_id: Call identifier
            destination: Destination extension to transfer to

        Returns:
            True if transfer initiated successfully
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder

        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.error(f"Call {call_id} not found for blind transfer")
            return False

        if not self.extension_registry.is_registered(destination):
            self.logger.error(f"Blind transfer destination {destination} not registered")
            return False

        dest_addr = self.extension_registry.get_address(destination)
        if not dest_addr:
            self.logger.error(f"No address for blind transfer destination {destination}")
            return False

        self.logger.info(f"Blind transfer: call {call_id} to {destination}")

        # Set call state to transferring
        from pbx.core.call import CallState

        call.state = CallState.TRANSFERRING
        call.transferred = True
        call.transfer_destination = destination

        # Build new INVITE to the transfer destination
        server_ip = self._get_server_ip()
        sip_port = self.config.get("server.sip_port", 5060)
        new_call_id = str(uuid.uuid4())

        invite_msg = SIPMessageBuilder.build_request(
            method="INVITE",
            uri=f"sip:{destination}@{dest_addr[0]}:{dest_addr[1]}",
            from_addr=f"<sip:{call.from_extension}@{server_ip}>",
            to_addr=f"<sip:{destination}@{server_ip}>",
            call_id=new_call_id,
            cseq=1,
        )
        invite_msg.set_header("Contact", f"<sip:{call.from_extension}@{server_ip}:{sip_port}>")

        # Include SDP with the existing RTP relay ports
        if call.rtp_ports:
            transfer_sdp = SDPBuilder.build_audio_sdp(
                server_ip, call.rtp_ports[0], session_id=new_call_id
            )
            invite_msg.body = transfer_sdp
            invite_msg.set_header("Content-type", "application/sdp")
            invite_msg.set_header("Content-Length", str(len(transfer_sdp.encode("utf-8"))))

        # Send INVITE to new destination
        self.sip_server._send_message(invite_msg.build(), dest_addr)

        # Create new call record for the transferred leg
        new_call = self.call_manager.create_call(new_call_id, call.from_extension, destination)
        new_call.start()
        new_call.caller_rtp = call.caller_rtp
        new_call.caller_addr = call.caller_addr
        new_call.rtp_ports = call.rtp_ports

        # Transfer RTP relay ownership from old call to new call before ending
        # the old call (end_call releases the relay, which would kill audio)
        relay_info = self.rtp_relay.active_relays.pop(call_id, None)
        if relay_info:
            self.rtp_relay.active_relays[new_call_id] = relay_info

        # Send BYE to the transferring party (the party that initiated transfer)
        if call.callee_addr:
            bye_msg = SIPMessageBuilder.build_request(
                method="BYE",
                uri=f"sip:{call.to_extension}@{call.callee_addr[0]}:{call.callee_addr[1]}",
                from_addr=f"<sip:{call.from_extension}@{server_ip}>",
                to_addr=f"<sip:{call.to_extension}@{server_ip}>",
                call_id=call_id,
                cseq=2,
            )
            self.sip_server._send_message(bye_msg.build(), call.callee_addr)

        # End the original call (relay already transferred, so release_relay is a no-op)
        self.call_manager.end_call(call_id)
        self.cdr_system.end_record(call_id, hangup_cause="blind_transfer")

        self.logger.info(f"Blind transfer complete: {call_id} -> {destination}")

        # Trigger webhook
        self.webhook_system.trigger_event(
            WebhookEvent.CALL_TRANSFERRED,
            {
                "call_id": call_id,
                "new_call_id": new_call_id,
                "from_extension": call.from_extension,
                "to_extension": call.to_extension,
                "transfer_destination": destination,
                "transfer_type": "blind",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        return True

    def attended_transfer(self, call_id: str, consultation_call_id: str) -> bool:
        """
        Perform attended (consultative) transfer.

        The transferring party has already established a consultation call with
        the transfer destination. This method bridges the original caller with
        the consultation call's far end.

        Args:
            call_id: Original call identifier (caller on hold)
            consultation_call_id: Consultation call identifier

        Returns:
            True if transfer completed successfully
        """
        from pbx.sip.message import SIPMessageBuilder

        original_call = self.call_manager.get_call(call_id)
        consult_call = self.call_manager.get_call(consultation_call_id)

        if not original_call:
            self.logger.error(f"Original call {call_id} not found for attended transfer")
            return False

        if not consult_call:
            self.logger.error(
                f"Consultation call {consultation_call_id} not found for attended transfer"
            )
            return False

        self.logger.info(
            f"Attended transfer: bridging {original_call.from_extension} "
            f"with {consult_call.to_extension}"
        )

        from pbx.core.call import CallState

        original_call.state = CallState.TRANSFERRING
        original_call.transferred = True
        original_call.transfer_destination = consult_call.to_extension

        # Re-point the RTP relay: connect original caller with consultation
        # call's far end
        server_ip = self._get_server_ip()

        if original_call.caller_rtp and consult_call.callee_rtp:
            caller_endpoint = (
                original_call.caller_rtp["address"],
                original_call.caller_rtp["port"],
            )
            new_dest_endpoint = (
                consult_call.callee_rtp["address"],
                consult_call.callee_rtp["port"],
            )

            # Update the RTP relay for the original call to point to new
            # destination
            if original_call.rtp_ports:
                self.rtp_relay.set_endpoints(call_id, caller_endpoint, new_dest_endpoint)
                self.logger.info(f"RTP relay re-bridged: {caller_endpoint} <-> {new_dest_endpoint}")

        # Resume the original call from hold
        original_call.state = CallState.CONNECTED
        original_call.on_hold = False
        original_call.to_extension = consult_call.to_extension
        original_call.callee_addr = consult_call.callee_addr
        original_call.callee_rtp = consult_call.callee_rtp

        # Send BYE to the transferring party (consultation call's A-leg)
        if consult_call.caller_addr:
            bye_msg = SIPMessageBuilder.build_request(
                method="BYE",
                uri=f"sip:{consult_call.from_extension}@{consult_call.caller_addr[0]}:{consult_call.caller_addr[1]}",
                from_addr=f"<sip:{consult_call.to_extension}@{server_ip}>",
                to_addr=f"<sip:{consult_call.from_extension}@{server_ip}>",
                call_id=consultation_call_id,
                cseq=2,
            )
            self.sip_server._send_message(bye_msg.build(), consult_call.caller_addr)

        # Release consultation call's RTP relay and end it
        self.rtp_relay.release_relay(consultation_call_id)
        self.call_manager.end_call(consultation_call_id)
        self.cdr_system.end_record(consultation_call_id, hangup_cause="attended_transfer")

        self.logger.info(
            f"Attended transfer complete: {original_call.from_extension} "
            f"now connected to {consult_call.to_extension}"
        )

        # Trigger webhook
        self.webhook_system.trigger_event(
            WebhookEvent.CALL_TRANSFERRED,
            {
                "call_id": call_id,
                "consultation_call_id": consultation_call_id,
                "from_extension": original_call.from_extension,
                "transfer_destination": consult_call.to_extension,
                "transfer_type": "attended",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        return True

    def consultation_transfer_start(self, call_id: str, destination: str) -> str | None:
        """
        Start a consultative transfer by placing the original call on hold
        and initiating a new call to the destination.

        Args:
            call_id: Original call identifier
            destination: Destination extension to consult with

        Returns:
            New consultation call ID, or None if failed
        """
        from pbx.sip.message import SIPMessageBuilder
        from pbx.sip.sdp import SDPBuilder

        call = self.call_manager.get_call(call_id)
        if not call:
            self.logger.error(f"Call {call_id} not found for consultation transfer")
            return None

        if not self.extension_registry.is_registered(destination):
            self.logger.error(f"Consultation destination {destination} not registered")
            return None

        dest_addr = self.extension_registry.get_address(destination)
        if not dest_addr:
            self.logger.error(f"No address for consultation destination {destination}")
            return None

        # Place original call on hold
        self.hold_call(call_id)

        # Allocate new RTP ports for the consultation call
        consult_call_id = str(uuid.uuid4())
        rtp_ports = self.rtp_relay.allocate_relay(consult_call_id)
        if not rtp_ports:
            self.logger.error("Failed to allocate RTP ports for consultation call")
            self.resume_call(call_id)
            return None

        # Create consultation call
        consult_call = self.call_manager.create_call(
            consult_call_id, call.to_extension, destination
        )
        consult_call.start()
        consult_call.rtp_ports = rtp_ports

        # Build and send INVITE for consultation
        server_ip = self._get_server_ip()
        sip_port = self.config.get("server.sip_port", 5060)

        consult_sdp = SDPBuilder.build_audio_sdp(
            server_ip, rtp_ports[0], session_id=consult_call_id
        )

        invite_msg = SIPMessageBuilder.build_request(
            method="INVITE",
            uri=f"sip:{destination}@{dest_addr[0]}:{dest_addr[1]}",
            from_addr=f"<sip:{call.to_extension}@{server_ip}>",
            to_addr=f"<sip:{destination}@{server_ip}>",
            call_id=consult_call_id,
            cseq=1,
            body=consult_sdp,
        )
        invite_msg.set_header("Content-type", "application/sdp")
        invite_msg.set_header("Contact", f"<sip:{call.to_extension}@{server_ip}:{sip_port}>")

        self.sip_server._send_message(invite_msg.build(), dest_addr)
        self.logger.info(f"Consultation call initiated: {consult_call_id} to {destination}")

        # Start CDR for consultation call
        self.cdr_system.start_record(consult_call_id, call.to_extension, destination)

        return consult_call_id

    def hold_call(self, call_id: str) -> bool:
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

    def resume_call(self, call_id: str) -> bool:
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

    def _check_dialplan(self, extension: str) -> bool:
        """Check if extension matches dialplan rules"""
        return self._call_router._check_dialplan(extension)

    def _send_cancel_to_callee(self, call: Any, call_id: str) -> None:
        """Send CANCEL to callee to stop their phone from ringing"""
        return self._call_router._send_cancel_to_callee(call, call_id)

    def _answer_call_for_voicemail(self, call: Any, call_id: str) -> bool:
        """Answer call for voicemail recording"""
        return self._call_router._answer_call_for_voicemail(call, call_id)

    def _handle_no_answer(self, call_id: str) -> None:
        """Handle no-answer timeout - route call to voicemail"""
        return self._call_router._handle_no_answer(call_id)

    def _monitor_voicemail_dtmf(self, call_id: str, call: Any, recorder: Any) -> None:
        """Monitor for DTMF # key press during voicemail recording"""
        return self._voicemail_handler.monitor_voicemail_dtmf(call_id, call, recorder)

    def _complete_voicemail_recording(self, call_id: str) -> None:
        """Complete voicemail recording and save the message"""
        return self._voicemail_handler.complete_voicemail_recording(call_id)

    def _handle_auto_attendant(
        self, from_ext: str, to_ext: str, call_id: str, message: Any, from_addr: tuple[str, int]
    ) -> bool:
        """Handle auto attendant calls (extension 0)"""
        return self._auto_attendant_handler.handle_auto_attendant(
            from_ext, to_ext, call_id, message, from_addr
        )

    def _auto_attendant_session(self, call_id: str, call: Any, session: Any) -> None:
        """Handle auto attendant session with menu and DTMF input"""
        return self._auto_attendant_handler._auto_attendant_session(call_id, call, session)

    def _handle_voicemail_access(
        self, from_ext: str, to_ext: str, call_id: str, message: Any, from_addr: tuple[str, int]
    ) -> bool:
        """Handle voicemail access calls (*xxxx pattern)"""
        return self._voicemail_handler.handle_voicemail_access(
            from_ext, to_ext, call_id, message, from_addr
        )

    def _handle_paging(
        self, from_ext: str, to_ext: str, call_id: str, message: Any, from_addr: tuple[str, int]
    ) -> bool:
        """Handle paging system calls (7xx pattern or all-call)"""
        return self._paging_handler.handle_paging(from_ext, to_ext, call_id, message, from_addr)

    def _paging_session(
        self, call_id: str, call: Any, dac_device: dict[str, Any], page_info: dict[str, Any]
    ) -> None:
        """Handle paging session with audio routing to DAC device"""
        return self._paging_handler._paging_session(call_id, call, dac_device, page_info)

    def _playback_voicemails(
        self, call_id: str, call: Any, mailbox: Any, messages: list[dict[str, Any]]
    ) -> None:
        """Play voicemail messages to caller"""
        return self._voicemail_handler._playback_voicemails(call_id, call, mailbox, messages)

    def _voicemail_ivr_session(
        self, call_id: str, call: Any, mailbox: Any, voicemail_ivr: Any
    ) -> None:
        """Interactive voicemail management session with IVR menu"""
        return self._voicemail_handler._voicemail_ivr_session(call_id, call, mailbox, voicemail_ivr)

    def _handle_emergency_call(
        self, from_ext: str, to_ext: str, call_id: str, message: Any, from_addr: tuple[str, int]
    ) -> bool:
        """Handle emergency call (911) according to Kari's Law"""
        return self._emergency_handler.handle_emergency_call(
            from_ext, to_ext, call_id, message, from_addr
        )

    def _build_wav_file(self, audio_data: bytes) -> bytes:
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

    def get_status(self) -> dict[str, Any]:
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

    def get_ad_integration_status(self) -> dict[str, Any]:
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

    def sync_ad_users(self) -> dict[str, Any]:
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
            if (
                hasattr(self, "phone_book")
                and self.phone_book
                and self.phone_book.enabled
                and self.phone_book.auto_sync_from_ad
            ):
                self.logger.info("Auto-syncing phone book from Active Directory after AD user sync")
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
                    f"Auto-provisioning: Automatically rebooting {len(extensions_to_reboot)} phones after AD sync"
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
