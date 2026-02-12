"""
Feature initialization for PBX Core

Extracts the feature subsystem initialization logic from PBXCore.__init__
into a dedicated class for better modularity and maintainability.
"""

import uuid

from pbx.features.call_parking import CallParkingSystem
from pbx.features.call_queue import QueueSystem
from pbx.features.call_recording import CallRecordingSystem
from pbx.features.cdr import CDRSystem
from pbx.features.conference import ConferenceSystem
from pbx.features.find_me_follow_me import FindMeFollowMe
from pbx.features.fraud_detection import FraudDetectionSystem
from pbx.features.music_on_hold import MusicOnHold
from pbx.features.phone_provisioning import PhoneProvisioning
from pbx.features.presence import PresenceSystem
from pbx.features.recording_retention import RecordingRetentionManager
from pbx.features.sip_trunk import SIPTrunkSystem
from pbx.features.time_based_routing import TimeBasedRouting
from pbx.features.voicemail import VoicemailSystem


class FeatureInitializer:
    """Handles initialization of all PBX feature subsystems"""

    @staticmethod
    def initialize(pbx_core):
        """
        Initialize all feature subsystems on a PBXCore instance.

        This method sets up all the feature subsystems (voicemail, conferencing,
        recording, queues, presence, parking, CDR, music-on-hold, trunks,
        integrations, security, and more) on the given PBXCore instance.

        Args:
            pbx_core: The PBXCore instance to initialize features on
        """
        config = pbx_core.config
        logger = pbx_core.logger
        database = pbx_core.database

        # Initialize advanced features
        voicemail_path = config.get("voicemail.storage_path", "voicemail")
        pbx_core.voicemail_system = VoicemailSystem(
            storage_path=voicemail_path,
            config=config,
            database=database if hasattr(pbx_core, "database") and database.enabled else None,
        )
        pbx_core.conference_system = ConferenceSystem()
        pbx_core.recording_system = CallRecordingSystem(
            auto_record=config.get("features.call_recording", False)
        )
        pbx_core.queue_system = QueueSystem()
        pbx_core.presence_system = PresenceSystem()
        pbx_core.parking_system = CallParkingSystem()
        pbx_core.cdr_system = CDRSystem()
        pbx_core.moh_system = MusicOnHold()
        pbx_core.trunk_system = SIPTrunkSystem(config=config)

        # Initialize statistics engine for analytics
        from pbx.features.statistics import StatisticsEngine

        pbx_core.statistics_engine = StatisticsEngine(pbx_core.cdr_system)
        pbx_core._log_startup("Statistics and analytics engine initialized")
        logger.info("QoS monitoring system initialized and integrated with RTP relay")

        # Initialize auto attendant if enabled
        if config.get("features.auto_attendant", False):
            from pbx.features.auto_attendant import AutoAttendant

            pbx_core.auto_attendant = AutoAttendant(config, pbx_core)
            logger.info(
                f"Auto Attendant initialized on extension {pbx_core.auto_attendant.get_extension()}"
            )
        else:
            pbx_core.auto_attendant = None

        # Initialize phone provisioning if enabled
        if config.get("provisioning.enabled", False):
            pbx_core.phone_provisioning = PhoneProvisioning(
                config, database=database if database.enabled else None
            )
            pbx_core._load_provisioning_devices()
        else:
            pbx_core.phone_provisioning = None

        # Initialize Active Directory integration
        if config.get("integrations.active_directory.enabled", False):
            FeatureInitializer._init_active_directory(pbx_core, config)
        else:
            pbx_core.ad_integration = None

        # Initialize open-source integrations
        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)

        # Initialize phone book if enabled
        if config.get("features.phone_book.enabled", False):
            from pbx.features.phone_book import PhoneBook

            pbx_core.phone_book = PhoneBook(
                config, database=database if database.enabled else None
            )
            logger.info("Phone book feature initialized")
        else:
            pbx_core.phone_book = None

        # Initialize emergency notification system if enabled
        if config.get("features.emergency_notification.enabled", True):
            from pbx.features.emergency_notification import EmergencyNotificationSystem

            pbx_core.emergency_notification = EmergencyNotificationSystem(
                pbx_core, config=config, database=database if database.enabled else None
            )
            logger.info("Emergency notification system initialized")
        else:
            pbx_core.emergency_notification = None

        # Initialize paging system if enabled
        if config.get("features.paging.enabled", False):
            from pbx.features.paging import PagingSystem

            pbx_core.paging_system = PagingSystem(
                config, database=database if database.enabled else None
            )
            pbx_core._log_startup("Paging system initialized")
        else:
            pbx_core.paging_system = None

        # Initialize E911 location service if enabled
        if config.get("features.e911.enabled", False):
            from pbx.features.e911_location import E911LocationService

            pbx_core.e911_location = E911LocationService(config=config)
            logger.info("E911 location service initialized")
        else:
            pbx_core.e911_location = None

        # Initialize Kari's Law compliance (federal requirement for direct 911 dialing)
        if config.get("features.karis_law.enabled", True):
            from pbx.features.karis_law import KarisLawCompliance

            pbx_core.karis_law = KarisLawCompliance(pbx_core, config=config)
            logger.info("Kari's Law compliance initialized (direct 911 dialing enabled)")
        else:
            pbx_core.karis_law = None
            logger.warning("Kari's Law compliance DISABLED - not recommended for production")

        # Initialize webhook system
        from pbx.features.webhooks import WebhookSystem

        pbx_core.webhook_system = WebhookSystem(config)

        # Initialize WebRTC if enabled
        if config.get("features.webrtc.enabled", False):
            from pbx.features.webrtc import WebRTCGateway, WebRTCSignalingServer

            pbx_core.webrtc_signaling = WebRTCSignalingServer(config, pbx_core)
            pbx_core.webrtc_gateway = WebRTCGateway(pbx_core)
            logger.info("WebRTC browser calling initialized")
        else:
            pbx_core.webrtc_signaling = None
            pbx_core.webrtc_gateway = None

        # Initialize CRM integration if enabled
        if config.get("features.crm_integration.enabled", False):
            from pbx.features.crm_integration import CRMIntegration

            pbx_core.crm_integration = CRMIntegration(config, pbx_core)
            logger.info("CRM integration and screen pop initialized")
        else:
            pbx_core.crm_integration = None

        # Initialize hot-desking if enabled
        if config.get("features.hot_desking.enabled", False):
            from pbx.features.hot_desking import HotDeskingSystem

            pbx_core.hot_desking = HotDeskingSystem(config, pbx_core)
            logger.info("Hot-desking system initialized")
        else:
            pbx_core.hot_desking = None

        # Initialize Find Me/Follow Me
        pbx_core.find_me_follow_me = FindMeFollowMe(
            config=config, database=database if database.enabled else None
        )
        if pbx_core.find_me_follow_me.enabled:
            logger.info("Find Me/Follow Me initialized")

        # Initialize Time-Based Routing
        pbx_core.time_based_routing = TimeBasedRouting(config=config)
        if pbx_core.time_based_routing.enabled:
            logger.info("Time-based routing initialized")

        # Initialize Recording Retention Manager
        pbx_core.recording_retention = RecordingRetentionManager(config=config)
        if pbx_core.recording_retention.enabled:
            logger.info("Recording retention manager initialized")

        # Initialize Fraud Detection System
        pbx_core.fraud_detection = FraudDetectionSystem(config=config)
        if pbx_core.fraud_detection.enabled:
            logger.info("Fraud detection system initialized")

        # Initialize Callback Queue
        from pbx.features.callback_queue import CallbackQueue

        pbx_core.callback_queue = CallbackQueue(config=config, database=database)
        if pbx_core.callback_queue.enabled:
            logger.info("Callback queue system initialized")

        # Initialize Mobile Push Notifications
        from pbx.features.mobile_push import MobilePushNotifications

        pbx_core.mobile_push = MobilePushNotifications(config=config, database=database)
        if pbx_core.mobile_push.enabled:
            logger.info("Mobile push notifications initialized")

        # Initialize Recording Announcements
        from pbx.features.recording_announcements import RecordingAnnouncements

        pbx_core.recording_announcements = RecordingAnnouncements(
            config=config, database=database
        )
        if pbx_core.recording_announcements.enabled:
            logger.info("Recording announcements initialized")

        # Initialize MFA if enabled
        if config.get("security.mfa.enabled", False):
            from pbx.features.mfa import MFAManager

            pbx_core.mfa_manager = MFAManager(
                database=(
                    database if hasattr(pbx_core, "database") and database.enabled else None
                ),
                config=config,
            )
            logger.info("Multi-Factor Authentication (MFA) initialized")
        else:
            pbx_core.mfa_manager = None

        # Initialize enhanced threat detection if enabled
        if config.get("security.threat_detection.enabled", True):
            from pbx.utils.security import get_threat_detector

            pbx_core.threat_detector = get_threat_detector(
                database=(
                    database if hasattr(pbx_core, "database") and database.enabled else None
                ),
                config=config,
            )
            logger.info("Enhanced threat detection initialized")
        else:
            pbx_core.threat_detector = None

        # Initialize security runtime monitor (always enabled for FIPS compliance)
        # Note: webhook_system is initialized earlier, so it's always available
        from pbx.utils.security_monitor import get_security_monitor

        pbx_core.security_monitor = get_security_monitor(
            config=config, webhook_system=pbx_core.webhook_system
        )
        logger.info("Security runtime monitor initialized")

        # Initialize DND scheduler if enabled
        if config.get("features.dnd_scheduling.enabled", False):
            from pbx.features.dnd_scheduling import get_dnd_scheduler

            # Get Outlook integration if available
            outlook = None
            if (
                hasattr(pbx_core, "integrations") and "outlook" in pbx_core.integrations
            ):  # pylint: disable=no-member
                outlook = pbx_core.integrations["outlook"]  # pylint: disable=no-member

            pbx_core.dnd_scheduler = get_dnd_scheduler(
                presence_system=pbx_core.presence_system if hasattr(pbx_core, "presence_system") else None,
                outlook_integration=outlook,
                config=config,
            )
            pbx_core._log_startup("DND Scheduler initialized")
        else:
            pbx_core.dnd_scheduler = None

        # Initialize skills-based routing if enabled
        if config.get("features.skills_routing.enabled", False):
            from pbx.features.skills_routing import get_skills_router

            pbx_core.skills_router = get_skills_router(
                database=(
                    database if hasattr(pbx_core, "database") and database.enabled else None
                ),
                config=config,
            )
            logger.info("Skills-Based Routing initialized")
        else:
            pbx_core.skills_router = None

    @staticmethod
    def _init_active_directory(pbx_core, config):
        """Initialize Active Directory integration"""
        from pbx.integrations.active_directory import ActiveDirectoryIntegration

        config_file = config._config_file if hasattr(config, "_config_file") else "config.yml"

        ad_config = {
            "integrations.active_directory.enabled": config.get(
                "integrations.active_directory.enabled"
            ),
            "integrations.active_directory.server": config.get(
                "integrations.active_directory.server"
            ),
            "integrations.active_directory.base_dn": config.get(
                "integrations.active_directory.base_dn"
            ),
            "integrations.active_directory.bind_dn": config.get(
                "integrations.active_directory.bind_dn"
            ),
            "integrations.active_directory.bind_password": config.get(
                "integrations.active_directory.bind_password"
            ),
            "integrations.active_directory.use_ssl": config.get(
                "integrations.active_directory.use_ssl", True
            ),
            "integrations.active_directory.auto_provision": config.get(
                "integrations.active_directory.auto_provision", False
            ),
            "integrations.active_directory.user_search_base": config.get(
                "integrations.active_directory.user_search_base"
            ),
            "integrations.active_directory.deactivate_removed_users": config.get(
                "integrations.active_directory.deactivate_removed_users", True
            ),
            "config_file": config_file,
        }
        pbx_core.ad_integration = ActiveDirectoryIntegration(ad_config)
        if pbx_core.ad_integration.enabled:
            pbx_core._log_startup("Active Directory integration initialized")

            # Auto-sync users from AD at startup if auto_provision is
            # enabled
            if pbx_core.ad_integration.auto_provision:
                pbx_core.logger.info(
                    "Auto-provisioning enabled - syncing users from Active Directory..."
                )
                try:
                    sync_result = pbx_core.ad_integration.sync_users(
                        extension_registry=pbx_core.extension_registry,
                        extension_db=pbx_core.extension_db,
                        phone_provisioning=None,  # Will be set after provisioning init
                    )

                    # Handle both int and dict return types
                    synced_count = (
                        sync_result
                        if isinstance(sync_result, int)
                        else sync_result.get("synced_count", 0)
                    )

                    if synced_count > 0:
                        pbx_core.logger.info(
                            f"Auto-synced {synced_count} extension(s) from Active Directory at startup"
                        )
                        # Reload extension registry to ensure all synced extensions are loaded
                        pbx_core.logger.info("Reloading extension registry from database...")
                        pbx_core.extension_registry.reload()
                        pbx_core.logger.info(
                            f"Extension registry reloaded: {len(pbx_core.extension_registry.extensions)} total extensions"
                        )
                    else:
                        pbx_core.logger.warning(
                            "AD auto-sync completed but no extensions were synced"
                        )
                except Exception as e:
                    pbx_core.logger.error(
                        f"Failed to auto-sync users from Active Directory at startup: {e}"
                    )
                    import traceback

                    pbx_core.logger.debug(traceback.format_exc())
        else:
            pbx_core.logger.warning(
                "Active Directory integration enabled in config but failed to initialize"
            )
            pbx_core.ad_integration = None

    @staticmethod
    def _init_open_source_integrations(pbx_core, config, logger):
        """Initialize open-source and third-party integrations"""
        # Jitsi Meet - Video conferencing
        if config.get("integrations.jitsi.enabled", False):
            from pbx.integrations.jitsi import JitsiIntegration

            pbx_core.jitsi_integration = JitsiIntegration(config)
            if pbx_core.jitsi_integration.enabled:
                pbx_core._log_startup("Jitsi Meet video conferencing integration initialized")
        else:
            pbx_core.jitsi_integration = None

        # Matrix - Team messaging
        if config.get("integrations.matrix.enabled", False):
            from pbx.integrations.matrix import MatrixIntegration

            pbx_core.matrix_integration = MatrixIntegration(config)
            if pbx_core.matrix_integration.enabled:
                pbx_core._log_startup("Matrix team messaging integration initialized")
        else:
            pbx_core.matrix_integration = None

        # EspoCRM - Customer relationship management
        if config.get("integrations.espocrm.enabled", False):
            from pbx.integrations.espocrm import EspoCRMIntegration

            pbx_core.espocrm_integration = EspoCRMIntegration(config)
            if pbx_core.espocrm_integration.enabled:
                pbx_core._log_startup("EspoCRM integration initialized")
        else:
            pbx_core.espocrm_integration = None

        # Zoom integration (proprietary - requires license)
        if config.get("integrations.zoom.enabled", False):
            from pbx.integrations.zoom import ZoomIntegration

            pbx_core.zoom_integration = ZoomIntegration(config)
            if pbx_core.zoom_integration.enabled:
                pbx_core._log_startup("Zoom integration initialized")
        else:
            pbx_core.zoom_integration = None
