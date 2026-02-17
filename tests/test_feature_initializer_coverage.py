"""Comprehensive tests for pbx.core.feature_initializer.FeatureInitializer."""

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_pbx_core(
    config_overrides: dict[str, Any] | None = None,
    database_enabled: bool = True,
) -> MagicMock:
    """Create a mock PBXCore with a functional config.get() side-effect."""
    pbx_core = MagicMock()
    pbx_core.logger = logging.getLogger("test_feature_initializer")

    cfg: dict[str, Any] = {
        "voicemail.storage_path": "voicemail",
        "features.call_recording": False,
        "features.auto_attendant": False,
        "provisioning.enabled": False,
        "integrations.active_directory.enabled": False,
        "integrations.jitsi.enabled": False,
        "integrations.matrix.enabled": False,
        "integrations.espocrm.enabled": False,
        "integrations.zoom.enabled": False,
        "features.phone_book.enabled": False,
        "features.emergency_notification.enabled": False,
        "features.paging.enabled": False,
        "features.e911.enabled": False,
        "features.karis_law.enabled": False,
        "features.webrtc.enabled": False,
        "features.crm_integration.enabled": False,
        "features.hot_desking.enabled": False,
        "features.dnd_scheduling.enabled": False,
        "features.skills_routing.enabled": False,
        "security.mfa.enabled": False,
        "security.threat_detection.enabled": False,
    }
    if config_overrides:
        cfg.update(config_overrides)

    def config_get(key: str, default: Any = None) -> Any:
        return cfg.get(key, default)

    config_mock = MagicMock()
    config_mock.get = MagicMock(side_effect=config_get)
    pbx_core.config = config_mock

    database_mock = MagicMock()
    database_mock.enabled = database_enabled
    pbx_core.database = database_mock

    pbx_core._log_startup = MagicMock()
    pbx_core._load_provisioning_devices = MagicMock()

    return pbx_core


# These are the top-level imports in feature_initializer (can be patched on the module)
_TOP_LEVEL_PATCHES = {
    "VoicemailSystem": "pbx.core.feature_initializer.VoicemailSystem",
    "ConferenceSystem": "pbx.core.feature_initializer.ConferenceSystem",
    "CallRecordingSystem": "pbx.core.feature_initializer.CallRecordingSystem",
    "QueueSystem": "pbx.core.feature_initializer.QueueSystem",
    "PresenceSystem": "pbx.core.feature_initializer.PresenceSystem",
    "CallParkingSystem": "pbx.core.feature_initializer.CallParkingSystem",
    "CDRSystem": "pbx.core.feature_initializer.CDRSystem",
    "MusicOnHold": "pbx.core.feature_initializer.MusicOnHold",
    "SIPTrunkSystem": "pbx.core.feature_initializer.SIPTrunkSystem",
    "FindMeFollowMe": "pbx.core.feature_initializer.FindMeFollowMe",
    "TimeBasedRouting": "pbx.core.feature_initializer.TimeBasedRouting",
    "RecordingRetentionManager": "pbx.core.feature_initializer.RecordingRetentionManager",
    "FraudDetectionSystem": "pbx.core.feature_initializer.FraudDetectionSystem",
    "PhoneProvisioning": "pbx.core.feature_initializer.PhoneProvisioning",
}

# These are lazy imports inside initialize() -- must be patched at their source
_LAZY_PATCHES = {
    "StatisticsEngine": "pbx.features.statistics.StatisticsEngine",
    "WebhookSystem": "pbx.features.webhooks.WebhookSystem",
    "get_security_monitor": "pbx.utils.security_monitor.get_security_monitor",
    "CallbackQueue": "pbx.features.callback_queue.CallbackQueue",
    "MobilePushNotifications": "pbx.features.mobile_push.MobilePushNotifications",
    "RecordingAnnouncements": "pbx.features.recording_announcements.RecordingAnnouncements",
}


def _run_initialize_with_all_patches(
    pbx_core: MagicMock,
    extra_patches: dict[str, MagicMock] | None = None,
) -> dict[str, MagicMock]:
    """Run FeatureInitializer.initialize() with every import patched.

    Returns a dict of name -> mock for assertions in the caller.
    """
    from pbx.core.feature_initializer import FeatureInitializer

    mocks: dict[str, MagicMock] = {}
    patchers = []

    for name, target in {**_TOP_LEVEL_PATCHES, **_LAZY_PATCHES}.items():
        p = patch(target)
        mock_obj = p.start()
        mocks[name] = mock_obj
        patchers.append(p)

    # Apply any caller-supplied extra patches (for conditional lazy imports)
    extra_patchers = []
    if extra_patches:
        for target, mock_obj in extra_patches.items():
            p = patch(target, mock_obj)
            p.start()
            extra_patchers.append(p)

    try:
        FeatureInitializer.initialize(pbx_core)
    finally:
        for p in patchers + extra_patchers:
            p.stop()

    return mocks


@pytest.mark.unit
class TestFeatureInitializerInitialize:
    """Test FeatureInitializer.initialize() with all feature subsystems."""

    def test_initialize_core_subsystems(self) -> None:
        """Verify all unconditionally-created subsystems are assigned to pbx_core."""
        pbx_core = _make_pbx_core()
        mocks = _run_initialize_with_all_patches(pbx_core)

        # Unconditional subsystems
        mocks["VoicemailSystem"].assert_called_once()
        assert pbx_core.voicemail_system == mocks["VoicemailSystem"].return_value

        mocks["ConferenceSystem"].assert_called_once()
        assert pbx_core.conference_system == mocks["ConferenceSystem"].return_value

        mocks["CallRecordingSystem"].assert_called_once_with(auto_record=False)
        assert pbx_core.recording_system == mocks["CallRecordingSystem"].return_value

        mocks["QueueSystem"].assert_called_once()
        assert pbx_core.queue_system == mocks["QueueSystem"].return_value

        mocks["PresenceSystem"].assert_called_once()
        assert pbx_core.presence_system == mocks["PresenceSystem"].return_value

        mocks["CallParkingSystem"].assert_called_once()
        assert pbx_core.parking_system == mocks["CallParkingSystem"].return_value

        mocks["CDRSystem"].assert_called_once()
        assert pbx_core.cdr_system == mocks["CDRSystem"].return_value

        mocks["MusicOnHold"].assert_called_once()
        assert pbx_core.moh_system == mocks["MusicOnHold"].return_value

        mocks["SIPTrunkSystem"].assert_called_once()
        assert pbx_core.trunk_system == mocks["SIPTrunkSystem"].return_value

        mocks["FindMeFollowMe"].assert_called_once()
        assert pbx_core.find_me_follow_me == mocks["FindMeFollowMe"].return_value

        mocks["TimeBasedRouting"].assert_called_once()
        assert pbx_core.time_based_routing == mocks["TimeBasedRouting"].return_value

        mocks["RecordingRetentionManager"].assert_called_once()
        assert pbx_core.recording_retention == mocks["RecordingRetentionManager"].return_value

        mocks["FraudDetectionSystem"].assert_called_once()
        assert pbx_core.fraud_detection == mocks["FraudDetectionSystem"].return_value

    def test_voicemail_with_database_enabled(self) -> None:
        """Voicemail receives the database reference when database.enabled is True."""
        pbx_core = _make_pbx_core(database_enabled=True)
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["VoicemailSystem"].assert_called_once_with(
            storage_path="voicemail",
            config=pbx_core.config,
            database=pbx_core.database,
        )

    def test_voicemail_with_database_disabled(self) -> None:
        """Voicemail receives None for database when database.enabled is False."""
        pbx_core = _make_pbx_core(database_enabled=False)
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["VoicemailSystem"].assert_called_once_with(
            storage_path="voicemail",
            config=pbx_core.config,
            database=None,
        )

    def test_custom_voicemail_path(self) -> None:
        """Voicemail uses a custom storage path from config."""
        pbx_core = _make_pbx_core(config_overrides={"voicemail.storage_path": "/custom/vm/path"})
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["VoicemailSystem"].assert_called_once_with(
            storage_path="/custom/vm/path",
            config=pbx_core.config,
            database=pbx_core.database,
        )

    def test_call_recording_enabled(self) -> None:
        """CallRecordingSystem receives auto_record=True from config."""
        pbx_core = _make_pbx_core(config_overrides={"features.call_recording": True})
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["CallRecordingSystem"].assert_called_once_with(auto_record=True)

    # ------------------------------------------------------------------ #
    # Optional features: auto_attendant
    # ------------------------------------------------------------------ #
    def test_auto_attendant_enabled(self) -> None:
        """Auto attendant is created when feature flag is True."""
        mock_aa_cls = MagicMock()
        mock_aa_cls.return_value.get_extension.return_value = "100"

        pbx_core = _make_pbx_core(config_overrides={"features.auto_attendant": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={"pbx.features.auto_attendant.AutoAttendant": mock_aa_cls},
        )

        mock_aa_cls.assert_called_once_with(pbx_core.config, pbx_core)
        assert pbx_core.auto_attendant == mock_aa_cls.return_value

    def test_auto_attendant_disabled(self) -> None:
        """Auto attendant is None when feature flag is False."""
        pbx_core = _make_pbx_core(config_overrides={"features.auto_attendant": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.auto_attendant is None

    # ------------------------------------------------------------------ #
    # Optional features: phone provisioning
    # ------------------------------------------------------------------ #
    def test_provisioning_enabled_with_db(self) -> None:
        """PhoneProvisioning is created with database when enabled."""
        pbx_core = _make_pbx_core(
            config_overrides={"provisioning.enabled": True},
            database_enabled=True,
        )

        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["PhoneProvisioning"].assert_called_once_with(
            pbx_core.config, database=pbx_core.database
        )
        pbx_core._load_provisioning_devices.assert_called_once()

    def test_provisioning_enabled_without_db(self) -> None:
        """PhoneProvisioning receives None for database when db disabled."""
        pbx_core = _make_pbx_core(
            config_overrides={"provisioning.enabled": True},
            database_enabled=False,
        )

        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["PhoneProvisioning"].assert_called_once_with(pbx_core.config, database=None)

    def test_provisioning_disabled(self) -> None:
        """Phone provisioning is None when not enabled."""
        pbx_core = _make_pbx_core(config_overrides={"provisioning.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.phone_provisioning is None

    # ------------------------------------------------------------------ #
    # Optional features: phone book
    # ------------------------------------------------------------------ #
    def test_phone_book_enabled(self) -> None:
        """PhoneBook is created when feature flag is True."""
        mock_pb_cls = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.phone_book.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={"pbx.features.phone_book.PhoneBook": mock_pb_cls},
        )

        mock_pb_cls.assert_called_once()
        assert pbx_core.phone_book == mock_pb_cls.return_value

    def test_phone_book_disabled(self) -> None:
        """PhoneBook is None when feature flag is False."""
        pbx_core = _make_pbx_core(config_overrides={"features.phone_book.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.phone_book is None

    # ------------------------------------------------------------------ #
    # Optional features: emergency notification
    # ------------------------------------------------------------------ #
    def test_emergency_notification_enabled(self) -> None:
        """EmergencyNotificationSystem is created when enabled."""
        mock_en_cls = MagicMock()
        pbx_core = _make_pbx_core(
            config_overrides={"features.emergency_notification.enabled": True}
        )

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={
                "pbx.features.emergency_notification.EmergencyNotificationSystem": mock_en_cls,
            },
        )

        mock_en_cls.assert_called_once()
        assert pbx_core.emergency_notification == mock_en_cls.return_value

    def test_emergency_notification_disabled(self) -> None:
        """EmergencyNotificationSystem is None when disabled."""
        pbx_core = _make_pbx_core(
            config_overrides={"features.emergency_notification.enabled": False}
        )
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.emergency_notification is None

    # ------------------------------------------------------------------ #
    # Optional features: paging
    # ------------------------------------------------------------------ #
    def test_paging_enabled(self) -> None:
        """PagingSystem is created when enabled."""
        mock_paging_cls = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.paging.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={"pbx.features.paging.PagingSystem": mock_paging_cls},
        )

        mock_paging_cls.assert_called_once()
        assert pbx_core.paging_system == mock_paging_cls.return_value
        pbx_core._log_startup.assert_any_call("Paging system initialized")

    def test_paging_disabled(self) -> None:
        """PagingSystem is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"features.paging.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.paging_system is None

    # ------------------------------------------------------------------ #
    # Optional features: E911
    # ------------------------------------------------------------------ #
    def test_e911_enabled(self) -> None:
        """E911LocationService is created when enabled."""
        mock_e911_cls = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.e911.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={
                "pbx.features.e911_location.E911LocationService": mock_e911_cls,
            },
        )

        mock_e911_cls.assert_called_once_with(config=pbx_core.config)
        assert pbx_core.e911_location == mock_e911_cls.return_value

    def test_e911_disabled(self) -> None:
        """E911 is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"features.e911.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.e911_location is None

    # ------------------------------------------------------------------ #
    # Optional features: Kari's Law
    # ------------------------------------------------------------------ #
    def test_karis_law_enabled(self) -> None:
        """KarisLawCompliance is created when enabled."""
        mock_kl_cls = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.karis_law.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={"pbx.features.karis_law.KarisLawCompliance": mock_kl_cls},
        )

        mock_kl_cls.assert_called_once_with(pbx_core, config=pbx_core.config)
        assert pbx_core.karis_law == mock_kl_cls.return_value

    def test_karis_law_disabled(self) -> None:
        """Karis Law is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"features.karis_law.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.karis_law is None

    # ------------------------------------------------------------------ #
    # Optional features: WebRTC
    # ------------------------------------------------------------------ #
    def test_webrtc_enabled(self) -> None:
        """WebRTC gateway and signaling server are created when enabled."""
        mock_ws_cls = MagicMock()
        mock_gw_cls = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.webrtc.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={
                "pbx.features.webrtc.WebRTCSignalingServer": mock_ws_cls,
                "pbx.features.webrtc.WebRTCGateway": mock_gw_cls,
            },
        )

        mock_ws_cls.assert_called_once_with(pbx_core.config, pbx_core)
        mock_gw_cls.assert_called_once_with(pbx_core)
        assert pbx_core.webrtc_signaling == mock_ws_cls.return_value
        assert pbx_core.webrtc_gateway == mock_gw_cls.return_value

    def test_webrtc_disabled(self) -> None:
        """WebRTC fields are None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"features.webrtc.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.webrtc_signaling is None
        assert pbx_core.webrtc_gateway is None

    # ------------------------------------------------------------------ #
    # Optional features: CRM integration
    # ------------------------------------------------------------------ #
    def test_crm_integration_enabled(self) -> None:
        """CRM integration is created when enabled."""
        mock_crm_cls = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.crm_integration.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={
                "pbx.features.crm_integration.CRMIntegration": mock_crm_cls,
            },
        )

        mock_crm_cls.assert_called_once_with(pbx_core.config, pbx_core)
        assert pbx_core.crm_integration == mock_crm_cls.return_value

    def test_crm_integration_disabled(self) -> None:
        """CRM integration is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"features.crm_integration.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.crm_integration is None

    # ------------------------------------------------------------------ #
    # Optional features: hot desking
    # ------------------------------------------------------------------ #
    def test_hot_desking_enabled(self) -> None:
        """HotDeskingSystem is created when enabled."""
        mock_hd_cls = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.hot_desking.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={
                "pbx.features.hot_desking.HotDeskingSystem": mock_hd_cls,
            },
        )

        mock_hd_cls.assert_called_once_with(pbx_core.config, pbx_core)
        assert pbx_core.hot_desking == mock_hd_cls.return_value

    def test_hot_desking_disabled(self) -> None:
        """HotDesking is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"features.hot_desking.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.hot_desking is None

    # ------------------------------------------------------------------ #
    # Optional features: MFA
    # ------------------------------------------------------------------ #
    def test_mfa_enabled_with_db(self) -> None:
        """MFA manager is created with database when enabled."""
        mock_mfa_cls = MagicMock()
        pbx_core = _make_pbx_core(
            config_overrides={"security.mfa.enabled": True},
            database_enabled=True,
        )

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={"pbx.features.mfa.MFAManager": mock_mfa_cls},
        )

        mock_mfa_cls.assert_called_once_with(
            database=pbx_core.database,
            config=pbx_core.config,
        )
        assert pbx_core.mfa_manager == mock_mfa_cls.return_value

    def test_mfa_enabled_without_db(self) -> None:
        """MFA manager receives None for database when db disabled."""
        mock_mfa_cls = MagicMock()
        pbx_core = _make_pbx_core(
            config_overrides={"security.mfa.enabled": True},
            database_enabled=False,
        )

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={"pbx.features.mfa.MFAManager": mock_mfa_cls},
        )

        mock_mfa_cls.assert_called_once_with(
            database=None,
            config=pbx_core.config,
        )

    def test_mfa_disabled(self) -> None:
        """MFA manager is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"security.mfa.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.mfa_manager is None

    # ------------------------------------------------------------------ #
    # Optional features: threat detection
    # ------------------------------------------------------------------ #
    def test_threat_detection_enabled(self) -> None:
        """Threat detector is created when enabled."""
        mock_td_fn = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"security.threat_detection.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={"pbx.utils.security.get_threat_detector": mock_td_fn},
        )

        mock_td_fn.assert_called_once()
        assert pbx_core.threat_detector == mock_td_fn.return_value

    def test_threat_detection_disabled(self) -> None:
        """Threat detector is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"security.threat_detection.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.threat_detector is None

    # ------------------------------------------------------------------ #
    # Optional features: DND scheduling
    # ------------------------------------------------------------------ #
    def test_dnd_scheduling_enabled_with_outlook(self) -> None:
        """DND scheduler is created with Outlook integration when available."""
        mock_dnd_fn = MagicMock()
        mock_outlook = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.dnd_scheduling.enabled": True})
        pbx_core.integrations = {"outlook": mock_outlook}

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={
                "pbx.features.dnd_scheduling.get_dnd_scheduler": mock_dnd_fn,
            },
        )

        mock_dnd_fn.assert_called_once()
        call_kwargs = mock_dnd_fn.call_args[1]
        assert call_kwargs["outlook_integration"] == mock_outlook
        pbx_core._log_startup.assert_any_call("DND Scheduler initialized")

    def test_dnd_scheduling_enabled_without_outlook(self) -> None:
        """DND scheduler is created with outlook=None when no outlook integration."""
        mock_dnd_fn = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.dnd_scheduling.enabled": True})
        # Remove integrations attribute entirely
        if hasattr(pbx_core, "integrations"):
            del pbx_core.integrations

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={
                "pbx.features.dnd_scheduling.get_dnd_scheduler": mock_dnd_fn,
            },
        )

        call_kwargs = mock_dnd_fn.call_args[1]
        assert call_kwargs["outlook_integration"] is None

    def test_dnd_scheduling_disabled(self) -> None:
        """DND scheduler is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"features.dnd_scheduling.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.dnd_scheduler is None

    # ------------------------------------------------------------------ #
    # Optional features: skills routing
    # ------------------------------------------------------------------ #
    def test_skills_routing_enabled(self) -> None:
        """Skills router is created when enabled."""
        mock_sr_fn = MagicMock()
        pbx_core = _make_pbx_core(config_overrides={"features.skills_routing.enabled": True})

        _run_initialize_with_all_patches(
            pbx_core,
            extra_patches={
                "pbx.features.skills_routing.get_skills_router": mock_sr_fn,
            },
        )

        mock_sr_fn.assert_called_once()
        assert pbx_core.skills_router == mock_sr_fn.return_value

    def test_skills_routing_disabled(self) -> None:
        """Skills router is None when disabled."""
        pbx_core = _make_pbx_core(config_overrides={"features.skills_routing.enabled": False})
        _run_initialize_with_all_patches(pbx_core)
        assert pbx_core.skills_router is None

    # ------------------------------------------------------------------ #
    # Always-initialized lazy subsystems
    # ------------------------------------------------------------------ #
    def test_statistics_engine_initialized(self) -> None:
        """StatisticsEngine is always created with the CDR system."""
        pbx_core = _make_pbx_core()
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["StatisticsEngine"].assert_called_once_with(mocks["CDRSystem"].return_value)
        assert pbx_core.statistics_engine == mocks["StatisticsEngine"].return_value
        pbx_core._log_startup.assert_any_call("Statistics and analytics engine initialized")

    def test_webhook_system_always_initialized(self) -> None:
        """WebhookSystem is always created."""
        pbx_core = _make_pbx_core()
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["WebhookSystem"].assert_called_once_with(pbx_core.config)
        assert pbx_core.webhook_system == mocks["WebhookSystem"].return_value

    def test_security_monitor_always_initialized(self) -> None:
        """Security monitor is always initialized (FIPS compliance)."""
        pbx_core = _make_pbx_core()
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["get_security_monitor"].assert_called_once_with(
            config=pbx_core.config,
            webhook_system=mocks["WebhookSystem"].return_value,
        )
        assert pbx_core.security_monitor == mocks["get_security_monitor"].return_value

    def test_callback_queue_always_initialized(self) -> None:
        """CallbackQueue is always created."""
        pbx_core = _make_pbx_core()
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["CallbackQueue"].assert_called_once_with(
            config=pbx_core.config, database=pbx_core.database
        )
        assert pbx_core.callback_queue == mocks["CallbackQueue"].return_value

    def test_mobile_push_always_initialized(self) -> None:
        """MobilePushNotifications is always created."""
        pbx_core = _make_pbx_core()
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["MobilePushNotifications"].assert_called_once_with(
            config=pbx_core.config, database=pbx_core.database
        )
        assert pbx_core.mobile_push == mocks["MobilePushNotifications"].return_value

    def test_recording_announcements_always_initialized(self) -> None:
        """RecordingAnnouncements is always created."""
        pbx_core = _make_pbx_core()
        mocks = _run_initialize_with_all_patches(pbx_core)

        mocks["RecordingAnnouncements"].assert_called_once_with(
            config=pbx_core.config, database=pbx_core.database
        )
        assert pbx_core.recording_announcements == mocks["RecordingAnnouncements"].return_value

    # ------------------------------------------------------------------ #
    # All optional features disabled at once
    # ------------------------------------------------------------------ #
    def test_all_optional_features_disabled(self) -> None:
        """When all optional features are disabled, their fields are None."""
        pbx_core = _make_pbx_core()
        _run_initialize_with_all_patches(pbx_core)

        assert pbx_core.auto_attendant is None
        assert pbx_core.phone_provisioning is None
        assert pbx_core.ad_integration is None
        assert pbx_core.phone_book is None
        assert pbx_core.emergency_notification is None
        assert pbx_core.paging_system is None
        assert pbx_core.e911_location is None
        assert pbx_core.karis_law is None
        assert pbx_core.webrtc_signaling is None
        assert pbx_core.webrtc_gateway is None
        assert pbx_core.crm_integration is None
        assert pbx_core.hot_desking is None
        assert pbx_core.mfa_manager is None
        assert pbx_core.threat_detector is None
        assert pbx_core.dnd_scheduler is None
        assert pbx_core.skills_router is None


@pytest.mark.unit
class TestFeatureInitializerActiveDirectory:
    """Test FeatureInitializer._init_active_directory."""

    def _make_pbx_core(self, ad_config: dict[str, Any] | None = None) -> MagicMock:
        """Create a mock PBXCore for AD tests."""
        pbx_core = MagicMock()
        pbx_core.logger = logging.getLogger("test_ad_init")

        defaults: dict[str, Any] = {
            "integrations.active_directory.enabled": True,
            "integrations.active_directory.server": "ldap://ad.example.com",
            "integrations.active_directory.base_dn": "dc=example,dc=com",
            "integrations.active_directory.bind_dn": "cn=admin",
            "integrations.active_directory.bind_password": "secret",
            "integrations.active_directory.use_ssl": True,
            "integrations.active_directory.auto_provision": False,
            "integrations.active_directory.user_search_base": "ou=users",
            "integrations.active_directory.deactivate_removed_users": True,
        }
        if ad_config:
            defaults.update(ad_config)

        config = MagicMock()
        config.get = MagicMock(side_effect=lambda key, default=None: defaults.get(key, default))
        config._config_file = "config.yml"
        pbx_core.config = config

        pbx_core.extension_registry = MagicMock()
        pbx_core.extension_db = MagicMock()
        pbx_core._log_startup = MagicMock()

        return pbx_core

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_enabled_and_initialized(self, mock_ad_cls: MagicMock) -> None:
        """AD integration is created and startup logged when enabled=True."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = True
        mock_ad.auto_provision = False
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)

        mock_ad_cls.assert_called_once()
        assert pbx_core.ad_integration == mock_ad
        pbx_core._log_startup.assert_called_once_with("Active Directory integration initialized")

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_auto_provision_syncs_users_int_result(self, mock_ad_cls: MagicMock) -> None:
        """Auto-provisioning syncs users when sync_users returns an int."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = True
        mock_ad.auto_provision = True
        mock_ad.sync_users.return_value = 5
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)

        mock_ad.sync_users.assert_called_once()
        pbx_core.extension_registry.reload.assert_called_once()

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_auto_provision_syncs_users_dict_result(self, mock_ad_cls: MagicMock) -> None:
        """Auto-provisioning handles dict return from sync_users."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = True
        mock_ad.auto_provision = True
        mock_ad.sync_users.return_value = {"synced_count": 3, "errors": []}
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)

        pbx_core.extension_registry.reload.assert_called_once()

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_auto_provision_zero_synced(self, mock_ad_cls: MagicMock) -> None:
        """Warning logged when auto-provision syncs zero extensions."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = True
        mock_ad.auto_provision = True
        mock_ad.sync_users.return_value = 0
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)

        # reload should NOT be called when synced_count is 0
        pbx_core.extension_registry.reload.assert_not_called()

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_auto_provision_zero_synced_dict(self, mock_ad_cls: MagicMock) -> None:
        """Warning logged when dict sync result has synced_count=0."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = True
        mock_ad.auto_provision = True
        mock_ad.sync_users.return_value = {"synced_count": 0}
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)

        pbx_core.extension_registry.reload.assert_not_called()

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_auto_provision_sync_key_error(self, mock_ad_cls: MagicMock) -> None:
        """KeyError from sync_users is caught and logged."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = True
        mock_ad.auto_provision = True
        mock_ad.sync_users.side_effect = KeyError("missing_field")
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        # Should not raise
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)
        pbx_core.extension_registry.reload.assert_not_called()

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_auto_provision_sync_type_error(self, mock_ad_cls: MagicMock) -> None:
        """TypeError from sync_users is caught and logged."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = True
        mock_ad.auto_provision = True
        mock_ad.sync_users.side_effect = TypeError("bad type")
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)
        pbx_core.extension_registry.reload.assert_not_called()

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_auto_provision_sync_value_error(self, mock_ad_cls: MagicMock) -> None:
        """ValueError from sync_users is caught and logged."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = True
        mock_ad.auto_provision = True
        mock_ad.sync_users.side_effect = ValueError("bad value")
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)
        pbx_core.extension_registry.reload.assert_not_called()

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_enabled_but_failed_to_init(self, mock_ad_cls: MagicMock) -> None:
        """When AD integration init returns enabled=False, it gets set to None."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = False
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)

        assert pbx_core.ad_integration is None

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_config_file_fallback(self, mock_ad_cls: MagicMock) -> None:
        """Config file defaults to 'config.yml' when _config_file is absent."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = False
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        del pbx_core.config._config_file  # Remove the attribute

        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)

        # The ad_config dict should have config_file="config.yml"
        call_args = mock_ad_cls.call_args[0][0]
        assert call_args["config_file"] == "config.yml"

    @patch("pbx.integrations.active_directory.ActiveDirectoryIntegration")
    def test_ad_config_builds_correct_dict(self, mock_ad_cls: MagicMock) -> None:
        """Verify all AD config keys are passed to ActiveDirectoryIntegration."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_ad = MagicMock()
        mock_ad.enabled = False
        mock_ad_cls.return_value = mock_ad

        pbx_core = self._make_pbx_core()
        FeatureInitializer._init_active_directory(pbx_core, pbx_core.config)

        call_args = mock_ad_cls.call_args[0][0]
        expected_keys = {
            "integrations.active_directory.enabled",
            "integrations.active_directory.server",
            "integrations.active_directory.base_dn",
            "integrations.active_directory.bind_dn",
            "integrations.active_directory.bind_password",
            "integrations.active_directory.use_ssl",
            "integrations.active_directory.auto_provision",
            "integrations.active_directory.user_search_base",
            "integrations.active_directory.deactivate_removed_users",
            "config_file",
        }
        assert set(call_args.keys()) == expected_keys


@pytest.mark.unit
class TestFeatureInitializerOpenSourceIntegrations:
    """Test FeatureInitializer._init_open_source_integrations."""

    def _make_pbx_core_and_config(
        self,
        jitsi: bool = False,
        matrix: bool = False,
        espocrm: bool = False,
        zoom: bool = False,
    ) -> tuple[MagicMock, MagicMock]:
        """Create mocks for open-source integration tests."""
        pbx_core = MagicMock()
        pbx_core._log_startup = MagicMock()

        cfg = {
            "integrations.jitsi.enabled": jitsi,
            "integrations.matrix.enabled": matrix,
            "integrations.espocrm.enabled": espocrm,
            "integrations.zoom.enabled": zoom,
        }
        config = MagicMock()
        config.get = MagicMock(side_effect=lambda key, default=None: cfg.get(key, default))

        return pbx_core, config

    @patch("pbx.integrations.jitsi.JitsiIntegration")
    def test_jitsi_enabled(self, mock_jitsi_cls: MagicMock) -> None:
        """Jitsi integration is created when enabled."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_jitsi = MagicMock()
        mock_jitsi.enabled = True
        mock_jitsi_cls.return_value = mock_jitsi

        pbx_core, config = self._make_pbx_core_and_config(jitsi=True)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)

        mock_jitsi_cls.assert_called_once_with(config)
        assert pbx_core.jitsi_integration == mock_jitsi
        pbx_core._log_startup.assert_any_call(
            "Jitsi Meet video conferencing integration initialized"
        )

    def test_jitsi_disabled(self) -> None:
        """Jitsi integration is None when disabled."""
        from pbx.core.feature_initializer import FeatureInitializer

        pbx_core, config = self._make_pbx_core_and_config(jitsi=False)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)
        assert pbx_core.jitsi_integration is None

    @patch("pbx.integrations.matrix.MatrixIntegration")
    def test_matrix_enabled(self, mock_matrix_cls: MagicMock) -> None:
        """Matrix integration is created when enabled."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_matrix = MagicMock()
        mock_matrix.enabled = True
        mock_matrix_cls.return_value = mock_matrix

        pbx_core, config = self._make_pbx_core_and_config(matrix=True)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)

        mock_matrix_cls.assert_called_once_with(config)
        assert pbx_core.matrix_integration == mock_matrix

    def test_matrix_disabled(self) -> None:
        """Matrix integration is None when disabled."""
        from pbx.core.feature_initializer import FeatureInitializer

        pbx_core, config = self._make_pbx_core_and_config(matrix=False)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)
        assert pbx_core.matrix_integration is None

    @patch("pbx.integrations.espocrm.EspoCRMIntegration")
    def test_espocrm_enabled(self, mock_espo_cls: MagicMock) -> None:
        """EspoCRM integration is created when enabled."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_espo = MagicMock()
        mock_espo.enabled = True
        mock_espo_cls.return_value = mock_espo

        pbx_core, config = self._make_pbx_core_and_config(espocrm=True)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)

        mock_espo_cls.assert_called_once_with(config)
        assert pbx_core.espocrm_integration == mock_espo

    def test_espocrm_disabled(self) -> None:
        """EspoCRM integration is None when disabled."""
        from pbx.core.feature_initializer import FeatureInitializer

        pbx_core, config = self._make_pbx_core_and_config(espocrm=False)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)
        assert pbx_core.espocrm_integration is None

    @patch("pbx.integrations.zoom.ZoomIntegration")
    def test_zoom_enabled(self, mock_zoom_cls: MagicMock) -> None:
        """Zoom integration is created when enabled."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_zoom = MagicMock()
        mock_zoom.enabled = True
        mock_zoom_cls.return_value = mock_zoom

        pbx_core, config = self._make_pbx_core_and_config(zoom=True)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)

        mock_zoom_cls.assert_called_once_with(config)
        assert pbx_core.zoom_integration == mock_zoom

    def test_zoom_disabled(self) -> None:
        """Zoom integration is None when disabled."""
        from pbx.core.feature_initializer import FeatureInitializer

        pbx_core, config = self._make_pbx_core_and_config(zoom=False)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)
        assert pbx_core.zoom_integration is None

    @patch("pbx.integrations.jitsi.JitsiIntegration")
    def test_jitsi_enabled_but_init_failed(self, mock_jitsi_cls: MagicMock) -> None:
        """When Jitsi init returns enabled=False, _log_startup is not called for it."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_jitsi = MagicMock()
        mock_jitsi.enabled = False
        mock_jitsi_cls.return_value = mock_jitsi

        pbx_core, config = self._make_pbx_core_and_config(jitsi=True)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)

        assert pbx_core.jitsi_integration == mock_jitsi
        # _log_startup should NOT be called for jitsi since it failed to initialize
        for c in pbx_core._log_startup.call_args_list:
            assert "Jitsi" not in str(c)

    @patch("pbx.integrations.matrix.MatrixIntegration")
    def test_matrix_enabled_but_init_failed(self, mock_matrix_cls: MagicMock) -> None:
        """When Matrix init returns enabled=False, _log_startup is not called for it."""
        from pbx.core.feature_initializer import FeatureInitializer

        mock_matrix = MagicMock()
        mock_matrix.enabled = False
        mock_matrix_cls.return_value = mock_matrix

        pbx_core, config = self._make_pbx_core_and_config(matrix=True)
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)

        for c in pbx_core._log_startup.call_args_list:
            assert "Matrix" not in str(c)

    def test_all_integrations_disabled(self) -> None:
        """When all integrations are disabled, all fields are None."""
        from pbx.core.feature_initializer import FeatureInitializer

        pbx_core, config = self._make_pbx_core_and_config()
        logger = logging.getLogger("test")

        FeatureInitializer._init_open_source_integrations(pbx_core, config, logger)

        assert pbx_core.jitsi_integration is None
        assert pbx_core.matrix_integration is None
        assert pbx_core.espocrm_integration is None
        assert pbx_core.zoom_integration is None
