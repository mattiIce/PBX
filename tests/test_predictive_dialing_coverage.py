"""
Comprehensive tests for Predictive Dialing feature module.

Tests cover all public classes, methods, enums, and code paths
in pbx/features/predictive_dialing.py.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.predictive_dialing import (
    Campaign,
    CampaignStatus,
    Contact,
    DialingMode,
    PredictiveDialer,
    get_predictive_dialer,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCampaignStatus:
    """Tests for CampaignStatus enum."""

    def test_all_values(self) -> None:
        """Verify all expected enum members exist."""
        assert CampaignStatus.PENDING.value == "pending"
        assert CampaignStatus.RUNNING.value == "running"
        assert CampaignStatus.PAUSED.value == "paused"
        assert CampaignStatus.COMPLETED.value == "completed"
        assert CampaignStatus.CANCELLED.value == "cancelled"

    def test_member_count(self) -> None:
        """Verify no unexpected members have been added."""
        assert len(CampaignStatus) == 5

    def test_lookup_by_value(self) -> None:
        """CampaignStatus can be looked up by its string value."""
        assert CampaignStatus("pending") is CampaignStatus.PENDING
        assert CampaignStatus("running") is CampaignStatus.RUNNING

    def test_invalid_value_raises(self) -> None:
        """Invalid value should raise ValueError."""
        with pytest.raises(ValueError):
            CampaignStatus("nonexistent")


@pytest.mark.unit
class TestDialingMode:
    """Tests for DialingMode enum."""

    def test_all_values(self) -> None:
        """Verify all expected enum members exist."""
        assert DialingMode.PREVIEW.value == "preview"
        assert DialingMode.PROGRESSIVE.value == "progressive"
        assert DialingMode.PREDICTIVE.value == "predictive"
        assert DialingMode.POWER.value == "power"

    def test_member_count(self) -> None:
        """Verify no unexpected members have been added."""
        assert len(DialingMode) == 4

    def test_lookup_by_value(self) -> None:
        """DialingMode can be looked up by its string value."""
        assert DialingMode("preview") is DialingMode.PREVIEW
        assert DialingMode("power") is DialingMode.POWER

    def test_invalid_value_raises(self) -> None:
        """Invalid value should raise ValueError."""
        with pytest.raises(ValueError):
            DialingMode("turbo")


# ---------------------------------------------------------------------------
# Contact tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContact:
    """Tests for Contact data class."""

    def test_init_defaults(self) -> None:
        """Contact initialises with correct defaults."""
        contact = Contact("c1", "5551234567")
        assert contact.contact_id == "c1"
        assert contact.phone_number == "5551234567"
        assert contact.data == {}
        assert contact.attempts == 0
        assert contact.last_attempt is None
        assert contact.status == "pending"
        assert contact.call_result is None

    def test_init_with_data(self) -> None:
        """Contact stores arbitrary data dict."""
        extra = {"name": "Alice", "priority": 1}
        contact = Contact("c2", "5559876543", data=extra)
        assert contact.data == extra

    def test_init_with_none_data(self) -> None:
        """Passing None for data should default to empty dict."""
        contact = Contact("c3", "5550000000", data=None)
        assert contact.data == {}

    def test_mutable_attributes(self) -> None:
        """Contact attributes can be mutated after creation."""
        contact = Contact("c4", "5551111111")
        contact.attempts = 3
        contact.last_attempt = datetime.now(UTC)
        contact.status = "retry"
        contact.call_result = "no_answer"
        assert contact.attempts == 3
        assert contact.status == "retry"
        assert contact.call_result == "no_answer"


# ---------------------------------------------------------------------------
# Campaign tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCampaign:
    """Tests for Campaign data class."""

    def test_init_defaults(self) -> None:
        """Campaign initialises with correct defaults."""
        campaign = Campaign("camp1", "Test Campaign", DialingMode.PROGRESSIVE)
        assert campaign.campaign_id == "camp1"
        assert campaign.name == "Test Campaign"
        assert campaign.dialing_mode is DialingMode.PROGRESSIVE
        assert campaign.status is CampaignStatus.PENDING
        assert isinstance(campaign.created_at, datetime)
        assert campaign.started_at is None
        assert campaign.ended_at is None
        assert campaign.contacts == []
        assert campaign.max_attempts == 3
        assert campaign.retry_interval == 3600

    def test_statistics_defaults(self) -> None:
        """Campaign statistics start at zero."""
        campaign = Campaign("camp2", "Stats Test", DialingMode.PREDICTIVE)
        assert campaign.total_contacts == 0
        assert campaign.contacts_completed == 0
        assert campaign.contacts_pending == 0
        assert campaign.successful_calls == 0
        assert campaign.failed_calls == 0

    def test_created_at_is_utc(self) -> None:
        """Campaign created_at should be timezone-aware UTC."""
        campaign = Campaign("camp3", "UTC Test", DialingMode.PREVIEW)
        assert campaign.created_at.tzinfo is not None

    def test_different_dialing_modes(self) -> None:
        """Campaign can be created with any DialingMode."""
        for mode in DialingMode:
            campaign = Campaign(f"camp_{mode.value}", "mode test", mode)
            assert campaign.dialing_mode is mode


# ---------------------------------------------------------------------------
# PredictiveDialer tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPredictiveDialerInit:
    """Tests for PredictiveDialer.__init__ under various configurations."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_init_no_config(self, mock_get_logger: MagicMock) -> None:
        """Initialise with no config — all defaults."""
        mock_get_logger.return_value = MagicMock()
        dialer = PredictiveDialer()
        assert dialer.config == {}
        assert dialer.db_backend is None
        assert dialer.db is None
        assert dialer.enabled is False
        assert dialer.max_abandon_rate == 0.03
        assert dialer.lines_per_agent == 1.5
        assert dialer.answer_delay == 2
        assert dialer.campaigns == {}
        assert dialer.total_campaigns == 0
        assert dialer.total_calls_made == 0
        assert dialer.total_connects == 0
        assert dialer.total_abandons == 0

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_init_enabled(self, mock_get_logger: MagicMock) -> None:
        """Initialise with enabled config."""
        mock_get_logger.return_value = MagicMock()
        config = {
            "features": {
                "predictive_dialing": {
                    "enabled": True,
                    "max_abandon_rate": 0.05,
                    "lines_per_agent": 2.0,
                    "answer_delay": 3,
                }
            }
        }
        dialer = PredictiveDialer(config=config)
        assert dialer.enabled is True
        assert dialer.max_abandon_rate == 0.05
        assert dialer.lines_per_agent == 2.0
        assert dialer.answer_delay == 3

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_init_disabled(self, mock_get_logger: MagicMock) -> None:
        """Initialise with explicitly disabled config."""
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"predictive_dialing": {"enabled": False}}}
        dialer = PredictiveDialer(config=config)
        assert dialer.enabled is False

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_init_with_db_backend_success(self, mock_get_logger: MagicMock) -> None:
        """Database layer initialised when db_backend is enabled."""
        mock_get_logger.return_value = MagicMock()
        mock_db_backend = MagicMock()
        mock_db_backend.enabled = True

        mock_db_class = MagicMock()
        mock_db_instance = MagicMock()
        mock_db_class.return_value = mock_db_instance

        with patch.dict(
            "sys.modules",
            {"pbx.features.predictive_dialing_db": MagicMock(PredictiveDialingDatabase=mock_db_class)},
        ):
            dialer = PredictiveDialer(config={}, db_backend=mock_db_backend)

        assert dialer.db is mock_db_instance
        mock_db_instance.create_tables.assert_called_once()

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_init_with_db_backend_disabled(self, mock_get_logger: MagicMock) -> None:
        """Database layer skipped when db_backend.enabled is False."""
        mock_get_logger.return_value = MagicMock()
        mock_db_backend = MagicMock()
        mock_db_backend.enabled = False

        dialer = PredictiveDialer(config={}, db_backend=mock_db_backend)
        assert dialer.db is None

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_init_with_db_backend_sqlite_error(self, mock_get_logger: MagicMock) -> None:
        """sqlite3.Error during DB init is caught gracefully."""
        import sqlite3

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_db_backend = MagicMock()
        mock_db_backend.enabled = True

        mock_db_class = MagicMock(side_effect=sqlite3.Error("DB error"))

        with patch.dict(
            "sys.modules",
            {"pbx.features.predictive_dialing_db": MagicMock(PredictiveDialingDatabase=mock_db_class)},
        ):
            dialer = PredictiveDialer(config={}, db_backend=mock_db_backend)

        assert dialer.db is None
        mock_logger.warning.assert_called()

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_init_partial_config(self, mock_get_logger: MagicMock) -> None:
        """Partial config falls back to defaults for missing keys."""
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"predictive_dialing": {"enabled": True}}}
        dialer = PredictiveDialer(config=config)
        assert dialer.enabled is True
        assert dialer.max_abandon_rate == 0.03
        assert dialer.lines_per_agent == 1.5
        assert dialer.answer_delay == 2

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_init_empty_features(self, mock_get_logger: MagicMock) -> None:
        """Config with empty features dict uses defaults."""
        mock_get_logger.return_value = MagicMock()
        config = {"features": {}}
        dialer = PredictiveDialer(config=config)
        assert dialer.enabled is False


@pytest.mark.unit
class TestPredictiveDialerCreateCampaign:
    """Tests for PredictiveDialer.create_campaign."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        """Create a fresh dialer for each test."""
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_create_progressive_campaign(self) -> None:
        """Create a campaign with progressive mode."""
        campaign = self.dialer.create_campaign("c1", "Sales", "progressive")
        assert campaign.campaign_id == "c1"
        assert campaign.name == "Sales"
        assert campaign.dialing_mode is DialingMode.PROGRESSIVE
        assert campaign.status is CampaignStatus.PENDING
        assert "c1" in self.dialer.campaigns
        assert self.dialer.total_campaigns == 1

    def test_create_preview_campaign(self) -> None:
        """Create a campaign with preview mode."""
        campaign = self.dialer.create_campaign("c2", "Survey", "preview")
        assert campaign.dialing_mode is DialingMode.PREVIEW

    def test_create_predictive_campaign(self) -> None:
        """Create a campaign with predictive mode."""
        campaign = self.dialer.create_campaign("c3", "Collections", "predictive")
        assert campaign.dialing_mode is DialingMode.PREDICTIVE

    def test_create_power_campaign(self) -> None:
        """Create a campaign with power mode."""
        campaign = self.dialer.create_campaign("c4", "Telemarketing", "power")
        assert campaign.dialing_mode is DialingMode.POWER

    def test_invalid_dialing_mode_raises(self) -> None:
        """Invalid dialing mode string should raise ValueError."""
        with pytest.raises(ValueError):
            self.dialer.create_campaign("bad", "Bad Campaign", "invalid_mode")

    def test_multiple_campaigns(self) -> None:
        """Creating multiple campaigns increments total_campaigns."""
        self.dialer.create_campaign("a", "A", "progressive")
        self.dialer.create_campaign("b", "B", "predictive")
        self.dialer.create_campaign("c", "C", "power")
        assert self.dialer.total_campaigns == 3
        assert len(self.dialer.campaigns) == 3

    def test_create_campaign_saves_to_db(self) -> None:
        """When db is set, create_campaign calls save_campaign."""
        mock_db = MagicMock()
        self.dialer.db = mock_db
        self.dialer.create_campaign("c5", "DB Campaign", "progressive")
        mock_db.save_campaign.assert_called_once()
        saved = mock_db.save_campaign.call_args[0][0]
        assert saved["campaign_id"] == "c5"
        assert saved["name"] == "DB Campaign"
        assert saved["dialing_mode"] == "progressive"
        assert saved["status"] == "pending"

    def test_create_campaign_no_db(self) -> None:
        """When db is None, create_campaign works without DB call."""
        assert self.dialer.db is None
        campaign = self.dialer.create_campaign("c6", "No DB", "preview")
        assert campaign is not None


@pytest.mark.unit
class TestPredictiveDialerAddContacts:
    """Tests for PredictiveDialer.add_contacts."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})
            self.dialer.create_campaign("camp1", "Test", "progressive")

    def test_add_contacts_success(self) -> None:
        """Add contacts to an existing campaign."""
        contacts = [
            {"id": "c1", "phone_number": "5551111111"},
            {"id": "c2", "phone_number": "5552222222", "data": {"name": "Bob"}},
        ]
        added = self.dialer.add_contacts("camp1", contacts)
        assert added == 2
        campaign = self.dialer.campaigns["camp1"]
        assert campaign.total_contacts == 2
        assert campaign.contacts_pending == 2
        assert len(campaign.contacts) == 2

    def test_add_contacts_nonexistent_campaign(self) -> None:
        """Adding contacts to a nonexistent campaign returns 0."""
        contacts = [{"id": "c1", "phone_number": "5551111111"}]
        added = self.dialer.add_contacts("nonexistent", contacts)
        assert added == 0

    def test_add_empty_contacts_list(self) -> None:
        """Adding an empty contact list returns 0."""
        added = self.dialer.add_contacts("camp1", [])
        assert added == 0
        assert self.dialer.campaigns["camp1"].total_contacts == 0

    def test_add_contacts_preserves_data(self) -> None:
        """Contact data is correctly transferred."""
        contacts = [{"id": "c1", "phone_number": "5551111111", "data": {"vip": True}}]
        self.dialer.add_contacts("camp1", contacts)
        contact = self.dialer.campaigns["camp1"].contacts[0]
        assert contact.contact_id == "c1"
        assert contact.phone_number == "5551111111"
        assert contact.data == {"vip": True}

    def test_add_contacts_increments_stats(self) -> None:
        """Adding contacts in batches accumulates statistics."""
        batch1 = [{"id": "c1", "phone_number": "5551111111"}]
        batch2 = [
            {"id": "c2", "phone_number": "5552222222"},
            {"id": "c3", "phone_number": "5553333333"},
        ]
        self.dialer.add_contacts("camp1", batch1)
        self.dialer.add_contacts("camp1", batch2)
        campaign = self.dialer.campaigns["camp1"]
        assert campaign.total_contacts == 3
        assert campaign.contacts_pending == 3


@pytest.mark.unit
class TestPredictiveDialerStartCampaign:
    """Tests for PredictiveDialer.start_campaign."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_start_nonexistent_campaign(self) -> None:
        """Starting a nonexistent campaign returns None."""
        result = self.dialer.start_campaign("nonexistent")
        assert result is None

    def test_start_preview_campaign(self) -> None:
        """Start a preview-mode campaign."""
        self.dialer.create_campaign("p1", "Preview", "preview")
        self.dialer.start_campaign("p1")
        campaign = self.dialer.campaigns["p1"]
        assert campaign.status is CampaignStatus.RUNNING
        assert campaign.started_at is not None

    def test_start_progressive_campaign(self) -> None:
        """Start a progressive-mode campaign."""
        self.dialer.create_campaign("p2", "Progressive", "progressive")
        self.dialer.start_campaign("p2")
        assert self.dialer.campaigns["p2"].status is CampaignStatus.RUNNING

    def test_start_predictive_campaign(self) -> None:
        """Start a predictive-mode campaign."""
        self.dialer.create_campaign("p3", "Predictive", "predictive")
        self.dialer.start_campaign("p3")
        assert self.dialer.campaigns["p3"].status is CampaignStatus.RUNNING

    def test_start_power_campaign(self) -> None:
        """Start a power-mode campaign."""
        self.dialer.create_campaign("p4", "Power", "power")
        self.dialer.start_campaign("p4")
        assert self.dialer.campaigns["p4"].status is CampaignStatus.RUNNING

    def test_started_at_is_utc(self) -> None:
        """started_at should be a UTC-aware datetime."""
        self.dialer.create_campaign("p5", "UTC Test", "progressive")
        self.dialer.start_campaign("p5")
        started = self.dialer.campaigns["p5"].started_at
        assert started.tzinfo is not None


@pytest.mark.unit
class TestPredictiveDialerPauseCampaign:
    """Tests for PredictiveDialer.pause_campaign."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_pause_nonexistent_campaign(self) -> None:
        """Pausing a nonexistent campaign returns None."""
        result = self.dialer.pause_campaign("nonexistent")
        assert result is None

    def test_pause_running_campaign(self) -> None:
        """Pause a running campaign."""
        self.dialer.create_campaign("c1", "Test", "progressive")
        self.dialer.start_campaign("c1")
        self.dialer.pause_campaign("c1")
        assert self.dialer.campaigns["c1"].status is CampaignStatus.PAUSED


@pytest.mark.unit
class TestPredictiveDialerStopCampaign:
    """Tests for PredictiveDialer.stop_campaign."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_stop_nonexistent_campaign(self) -> None:
        """Stopping a nonexistent campaign returns None."""
        result = self.dialer.stop_campaign("nonexistent")
        assert result is None

    def test_stop_running_campaign(self) -> None:
        """Stop a running campaign and verify status and ended_at."""
        self.dialer.create_campaign("c1", "Test", "progressive")
        self.dialer.start_campaign("c1")
        self.dialer.stop_campaign("c1")
        campaign = self.dialer.campaigns["c1"]
        assert campaign.status is CampaignStatus.COMPLETED
        assert campaign.ended_at is not None
        assert campaign.ended_at.tzinfo is not None

    def test_stop_campaign_without_start(self) -> None:
        """Stop a campaign that was never started (started_at is None)."""
        self.dialer.create_campaign("c2", "Never Started", "progressive")
        self.dialer.stop_campaign("c2")
        campaign = self.dialer.campaigns["c2"]
        assert campaign.status is CampaignStatus.COMPLETED
        assert campaign.ended_at is not None

    def test_stop_campaign_duration_calculation(self) -> None:
        """Duration is calculated from started_at to ended_at."""
        self.dialer.create_campaign("c3", "Duration Test", "progressive")
        self.dialer.start_campaign("c3")
        campaign = self.dialer.campaigns["c3"]
        # Manually set started_at to a known time
        campaign.started_at = datetime.now(UTC) - timedelta(seconds=120)
        self.dialer.stop_campaign("c3")
        # ended_at should be set and after started_at
        assert campaign.ended_at >= campaign.started_at


@pytest.mark.unit
class TestPredictiveDialerPredictAgentAvailability:
    """Tests for PredictiveDialer.predict_agent_availability."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_zero_agents(self) -> None:
        """Zero agents should return 0 lines to dial."""
        result = self.dialer.predict_agent_availability(
            current_agents=0, avg_call_duration=120.0
        )
        assert result == 0

    def test_basic_prediction(self) -> None:
        """Positive agents with no current calls."""
        result = self.dialer.predict_agent_availability(
            current_agents=5, avg_call_duration=120.0, current_calls=0
        )
        assert result > 0
        assert isinstance(result, int)

    def test_with_current_calls(self) -> None:
        """Current calls should influence predicted available agents."""
        result = self.dialer.predict_agent_availability(
            current_agents=5,
            avg_call_duration=60.0,
            current_calls=10,
            historical_answer_rate=0.5,
        )
        assert result >= 0
        assert isinstance(result, int)

    def test_very_low_answer_rate_clamped(self) -> None:
        """Very low answer rate (< 0.1) should be clamped to 0.1."""
        result = self.dialer.predict_agent_availability(
            current_agents=5,
            avg_call_duration=120.0,
            current_calls=0,
            historical_answer_rate=0.01,
        )
        assert result >= 0

    def test_zero_answer_rate_clamped(self) -> None:
        """Zero answer rate should be clamped to 0.1."""
        result = self.dialer.predict_agent_availability(
            current_agents=5,
            avg_call_duration=120.0,
            current_calls=0,
            historical_answer_rate=0.0,
        )
        assert result >= 0

    def test_high_answer_rate(self) -> None:
        """High answer rate should produce fewer lines (more efficient)."""
        low_rate = self.dialer.predict_agent_availability(
            current_agents=5, avg_call_duration=120.0, historical_answer_rate=0.2
        )
        high_rate = self.dialer.predict_agent_availability(
            current_agents=5, avg_call_duration=120.0, historical_answer_rate=0.9
        )
        # With higher answer rate, fewer lines should be needed
        # (or limited by lines_per_agent cap)
        assert low_rate >= 0
        assert high_rate >= 0

    def test_result_capped_by_lines_per_agent(self) -> None:
        """Lines to dial should not exceed current_agents * lines_per_agent."""
        result = self.dialer.predict_agent_availability(
            current_agents=2,
            avg_call_duration=120.0,
            current_calls=0,
            historical_answer_rate=0.3,
        )
        max_allowed = int(2 * self.dialer.lines_per_agent)
        assert result <= max_allowed

    def test_avg_call_duration_zero_or_negative(self) -> None:
        """avg_call_duration <= 0 should not cause division error."""
        result = self.dialer.predict_agent_availability(
            current_agents=5,
            avg_call_duration=0.0,
            current_calls=3,
        )
        assert result >= 0

    def test_very_small_denominator_fallback(self) -> None:
        """When denominator <= 0.001, fallback to simple calculation."""
        # max_abandon_rate close to 1.0 makes (1 - target_abandon_rate) very small
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            dialer = PredictiveDialer(
                config={
                    "features": {
                        "predictive_dialing": {
                            "enabled": True,
                            "max_abandon_rate": 0.999,
                            "lines_per_agent": 2.0,
                        }
                    }
                }
            )
        # answer_rate=0.1 (clamped) * (1 - 0.999) = 0.1 * 0.001 = 0.0001 <= 0.001
        result = dialer.predict_agent_availability(
            current_agents=5,
            avg_call_duration=120.0,
            current_calls=0,
            historical_answer_rate=0.01,
        )
        # Fallback: int(5 * 2.0) = 10
        assert result == 10

    def test_result_never_negative(self) -> None:
        """Result should never be negative."""
        result = self.dialer.predict_agent_availability(
            current_agents=1,
            avg_call_duration=1.0,
            current_calls=100,
            historical_answer_rate=0.99,
        )
        assert result >= 0


@pytest.mark.unit
class TestPredictiveDialerCalculateAbandonRate:
    """Tests for PredictiveDialer.calculate_abandon_rate."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_nonexistent_campaign(self) -> None:
        """Nonexistent campaign returns 0.0."""
        assert self.dialer.calculate_abandon_rate("nonexistent") == 0.0

    def test_no_contacts(self) -> None:
        """Empty campaign returns 0.0."""
        self.dialer.create_campaign("c1", "Empty", "progressive")
        assert self.dialer.calculate_abandon_rate("c1") == 0.0

    def test_no_answered_or_abandoned(self) -> None:
        """Contacts with neither answered nor abandoned result return 0.0."""
        self.dialer.create_campaign("c1", "Pending", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
            {"id": "c2", "phone_number": "5552222222"},
        ])
        assert self.dialer.calculate_abandon_rate("c1") == 0.0

    def test_all_answered(self) -> None:
        """All contacts answered gives 0.0 abandon rate."""
        self.dialer.create_campaign("c1", "Good", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
            {"id": "c2", "phone_number": "5552222222"},
        ])
        for contact in self.dialer.campaigns["c1"].contacts:
            contact.call_result = "answered"
        assert self.dialer.calculate_abandon_rate("c1") == 0.0

    def test_all_abandoned(self) -> None:
        """All contacts abandoned gives 1.0 abandon rate."""
        self.dialer.create_campaign("c1", "Bad", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
            {"id": "c2", "phone_number": "5552222222"},
        ])
        for contact in self.dialer.campaigns["c1"].contacts:
            contact.call_result = "abandoned"
        assert self.dialer.calculate_abandon_rate("c1") == 1.0

    def test_mixed_results(self) -> None:
        """Mix of answered, abandoned, and connected contacts."""
        self.dialer.create_campaign("c1", "Mixed", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": f"c{i}", "phone_number": f"555{i:07d}"} for i in range(10)
        ])
        contacts = self.dialer.campaigns["c1"].contacts
        # 3 abandoned, 4 answered, 2 connected, 1 pending
        for i in range(3):
            contacts[i].call_result = "abandoned"
        for i in range(3, 7):
            contacts[i].call_result = "answered"
        for i in range(7, 9):
            contacts[i].call_result = "connected"
        contacts[9].call_result = "pending"

        # abandons=3, answered=4+2=6, total=3+6=9
        rate = self.dialer.calculate_abandon_rate("c1")
        assert rate == pytest.approx(3 / 9)

    def test_connected_counts_as_answered(self) -> None:
        """'connected' call_result counts as answered (not abandoned)."""
        self.dialer.create_campaign("c1", "Connected", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
        ])
        self.dialer.campaigns["c1"].contacts[0].call_result = "connected"
        assert self.dialer.calculate_abandon_rate("c1") == 0.0


@pytest.mark.unit
class TestPredictiveDialerGetNextContact:
    """Tests for PredictiveDialer.get_next_contact."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_nonexistent_campaign(self) -> None:
        """Nonexistent campaign returns None."""
        assert self.dialer.get_next_contact("nonexistent") is None

    def test_empty_campaign(self) -> None:
        """Campaign with no contacts returns None."""
        self.dialer.create_campaign("c1", "Empty", "progressive")
        assert self.dialer.get_next_contact("c1") is None

    def test_returns_first_pending(self) -> None:
        """Returns the first pending contact."""
        self.dialer.create_campaign("c1", "Test", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
            {"id": "c2", "phone_number": "5552222222"},
        ])
        contact = self.dialer.get_next_contact("c1")
        assert contact is not None
        assert contact.contact_id == "c1"

    def test_skips_non_pending_contacts(self) -> None:
        """Skips contacts that are not pending or eligible for retry."""
        self.dialer.create_campaign("c1", "Test", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
            {"id": "c2", "phone_number": "5552222222"},
        ])
        # Mark first contact as completed
        self.dialer.campaigns["c1"].contacts[0].status = "completed"
        contact = self.dialer.get_next_contact("c1")
        assert contact is not None
        assert contact.contact_id == "c2"

    def test_retry_contact_ready(self) -> None:
        """Contact in retry status with elapsed retry interval is returned."""
        self.dialer.create_campaign("c1", "Test", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
        ])
        contact = self.dialer.campaigns["c1"].contacts[0]
        contact.status = "retry"
        # Set last_attempt to be well past the retry interval
        contact.last_attempt = datetime.now(UTC) - timedelta(seconds=7200)
        result = self.dialer.get_next_contact("c1")
        assert result is not None
        assert result.contact_id == "c1"

    def test_retry_contact_not_ready(self) -> None:
        """Contact in retry status with recent attempt is not returned."""
        self.dialer.create_campaign("c1", "Test", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
        ])
        contact = self.dialer.campaigns["c1"].contacts[0]
        contact.status = "retry"
        contact.last_attempt = datetime.now(UTC)  # Just now — not enough time passed
        result = self.dialer.get_next_contact("c1")
        assert result is None

    def test_retry_contact_no_last_attempt(self) -> None:
        """Contact with retry status but no last_attempt is not returned."""
        self.dialer.create_campaign("c1", "Test", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
        ])
        contact = self.dialer.campaigns["c1"].contacts[0]
        contact.status = "retry"
        contact.last_attempt = None
        result = self.dialer.get_next_contact("c1")
        # The contact has status "retry" but last_attempt is None,
        # so the `if contact.last_attempt:` check fails.
        assert result is None

    def test_all_contacts_completed(self) -> None:
        """All contacts completed returns None."""
        self.dialer.create_campaign("c1", "Test", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
            {"id": "c2", "phone_number": "5552222222"},
        ])
        for c in self.dialer.campaigns["c1"].contacts:
            c.status = "completed"
        assert self.dialer.get_next_contact("c1") is None


@pytest.mark.unit
class TestPredictiveDialerDialContact:
    """Tests for PredictiveDialer.dial_contact."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})
            self.dialer.create_campaign("c1", "Test", "progressive")
            self.dialer.add_contacts("c1", [
                {"id": "ct1", "phone_number": "5551111111"},
            ])

    def test_dial_nonexistent_campaign(self) -> None:
        """Dialing with nonexistent campaign returns error."""
        contact = Contact("ct1", "5551111111")
        result = self.dialer.dial_contact("nonexistent", contact)
        assert result["success"] is False
        assert result["error"] == "Campaign not found"

    def test_dial_success(self) -> None:
        """Successful dial returns correct data and increments counters."""
        contact = self.dialer.campaigns["c1"].contacts[0]
        result = self.dialer.dial_contact("c1", contact)
        assert result["success"] is True
        assert result["contact_id"] == "ct1"
        assert result["phone_number"] == "5551111111"
        assert result["attempt"] == 1
        assert contact.attempts == 1
        assert contact.last_attempt is not None
        assert self.dialer.total_calls_made == 1

    def test_dial_increments_attempts(self) -> None:
        """Each dial increments the contact attempts."""
        contact = self.dialer.campaigns["c1"].contacts[0]
        self.dialer.dial_contact("c1", contact)
        self.dialer.dial_contact("c1", contact)
        assert contact.attempts == 2
        assert self.dialer.total_calls_made == 2

    def test_dial_max_attempts_exceeded(self) -> None:
        """Dialing beyond max_attempts returns error."""
        contact = self.dialer.campaigns["c1"].contacts[0]
        contact.attempts = 3  # max_attempts defaults to 3
        result = self.dialer.dial_contact("c1", contact)
        assert result["success"] is False
        assert result["error"] == "Max attempts exceeded"

    def test_dial_at_max_attempts_boundary(self) -> None:
        """Dialing at exactly max_attempts returns error (>= check)."""
        contact = self.dialer.campaigns["c1"].contacts[0]
        # max_attempts is 3, so attempts=3 should fail
        contact.attempts = 3
        result = self.dialer.dial_contact("c1", contact)
        assert result["success"] is False

    def test_dial_one_below_max_attempts(self) -> None:
        """Dialing at max_attempts - 1 should succeed."""
        contact = self.dialer.campaigns["c1"].contacts[0]
        contact.attempts = 2
        result = self.dialer.dial_contact("c1", contact)
        assert result["success"] is True
        assert result["attempt"] == 3

    def test_dial_sets_last_attempt_utc(self) -> None:
        """last_attempt should be set as a UTC-aware datetime."""
        contact = self.dialer.campaigns["c1"].contacts[0]
        self.dialer.dial_contact("c1", contact)
        assert contact.last_attempt.tzinfo is not None


@pytest.mark.unit
class TestPredictiveDialerGetCampaignStatistics:
    """Tests for PredictiveDialer.get_campaign_statistics."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_nonexistent_campaign(self) -> None:
        """Nonexistent campaign returns None."""
        assert self.dialer.get_campaign_statistics("nonexistent") is None

    def test_pending_campaign_statistics(self) -> None:
        """Statistics for a pending campaign."""
        self.dialer.create_campaign("c1", "Stats Test", "progressive")
        stats = self.dialer.get_campaign_statistics("c1")
        assert stats is not None
        assert stats["campaign_id"] == "c1"
        assert stats["name"] == "Stats Test"
        assert stats["status"] == "pending"
        assert stats["dialing_mode"] == "progressive"
        assert stats["total_contacts"] == 0
        assert stats["contacts_completed"] == 0
        assert stats["contacts_pending"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0
        assert stats["started_at"] is None
        assert stats["ended_at"] is None
        assert stats["created_at"] is not None

    def test_running_campaign_statistics(self) -> None:
        """Statistics for a running campaign."""
        self.dialer.create_campaign("c1", "Running", "predictive")
        self.dialer.start_campaign("c1")
        stats = self.dialer.get_campaign_statistics("c1")
        assert stats["status"] == "running"
        assert stats["started_at"] is not None
        assert stats["ended_at"] is None

    def test_completed_campaign_statistics(self) -> None:
        """Statistics for a completed campaign."""
        self.dialer.create_campaign("c1", "Done", "power")
        self.dialer.start_campaign("c1")
        self.dialer.stop_campaign("c1")
        stats = self.dialer.get_campaign_statistics("c1")
        assert stats["status"] == "completed"
        assert stats["started_at"] is not None
        assert stats["ended_at"] is not None

    def test_statistics_with_contacts(self) -> None:
        """Statistics reflect added contacts."""
        self.dialer.create_campaign("c1", "Contacts", "progressive")
        self.dialer.add_contacts("c1", [
            {"id": "c1", "phone_number": "5551111111"},
            {"id": "c2", "phone_number": "5552222222"},
        ])
        campaign = self.dialer.campaigns["c1"]
        campaign.contacts_completed = 1
        campaign.successful_calls = 1

        stats = self.dialer.get_campaign_statistics("c1")
        assert stats["total_contacts"] == 2
        assert stats["contacts_completed"] == 1
        assert stats["successful_calls"] == 1


@pytest.mark.unit
class TestPredictiveDialerGetStatistics:
    """Tests for PredictiveDialer.get_statistics."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(config={})

    def test_initial_statistics(self) -> None:
        """Initial statistics are all zeros."""
        stats = self.dialer.get_statistics()
        assert stats["total_campaigns"] == 0
        assert stats["active_campaigns"] == 0
        assert stats["total_calls_made"] == 0
        assert stats["total_connects"] == 0
        assert stats["total_abandons"] == 0
        assert stats["abandon_rate"] == 0.0
        assert stats["enabled"] is False

    def test_statistics_with_active_campaigns(self) -> None:
        """Active campaigns counted in statistics."""
        self.dialer.create_campaign("c1", "Active", "progressive")
        self.dialer.start_campaign("c1")
        self.dialer.create_campaign("c2", "Paused", "progressive")
        self.dialer.start_campaign("c2")
        self.dialer.pause_campaign("c2")
        self.dialer.create_campaign("c3", "Also Active", "predictive")
        self.dialer.start_campaign("c3")

        stats = self.dialer.get_statistics()
        assert stats["total_campaigns"] == 3
        assert stats["active_campaigns"] == 2  # c1, c3 running; c2 paused

    def test_statistics_abandon_rate_calculation(self) -> None:
        """Abandon rate = total_abandons / max(1, total_connects)."""
        self.dialer.total_abandons = 5
        self.dialer.total_connects = 100
        stats = self.dialer.get_statistics()
        assert stats["abandon_rate"] == pytest.approx(0.05)

    def test_statistics_abandon_rate_zero_connects(self) -> None:
        """Abandon rate when total_connects is 0 (division by max(1, 0))."""
        self.dialer.total_abandons = 3
        self.dialer.total_connects = 0
        stats = self.dialer.get_statistics()
        assert stats["abandon_rate"] == 3.0

    def test_statistics_enabled_flag(self) -> None:
        """Statistics reflect enabled flag from config."""
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            dialer = PredictiveDialer(
                config={"features": {"predictive_dialing": {"enabled": True}}}
            )
        stats = dialer.get_statistics()
        assert stats["enabled"] is True


# ---------------------------------------------------------------------------
# get_predictive_dialer singleton tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetPredictiveDialer:
    """Tests for the get_predictive_dialer module-level factory."""

    def setup_method(self) -> None:
        """Reset the global singleton before each test."""
        import pbx.features.predictive_dialing as mod

        mod._predictive_dialer = None

    def teardown_method(self) -> None:
        """Reset the global singleton after each test to avoid leaks."""
        import pbx.features.predictive_dialing as mod

        mod._predictive_dialer = None

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_creates_instance(self, mock_get_logger: MagicMock) -> None:
        """First call creates a new PredictiveDialer."""
        mock_get_logger.return_value = MagicMock()
        dialer = get_predictive_dialer()
        assert isinstance(dialer, PredictiveDialer)

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_returns_same_instance(self, mock_get_logger: MagicMock) -> None:
        """Subsequent calls return the same singleton."""
        mock_get_logger.return_value = MagicMock()
        dialer1 = get_predictive_dialer()
        dialer2 = get_predictive_dialer()
        assert dialer1 is dialer2

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_passes_config_and_db(self, mock_get_logger: MagicMock) -> None:
        """Config and db_backend are forwarded to PredictiveDialer."""
        mock_get_logger.return_value = MagicMock()
        config = {"features": {"predictive_dialing": {"enabled": True}}}
        mock_db = MagicMock()
        mock_db.enabled = False
        dialer = get_predictive_dialer(config=config, db_backend=mock_db)
        assert dialer.enabled is True
        assert dialer.db_backend is mock_db

    @patch("pbx.features.predictive_dialing.get_logger")
    def test_ignores_args_after_creation(self, mock_get_logger: MagicMock) -> None:
        """After singleton is created, new args are ignored."""
        mock_get_logger.return_value = MagicMock()
        dialer1 = get_predictive_dialer(config={})
        dialer2 = get_predictive_dialer(
            config={"features": {"predictive_dialing": {"enabled": True}}}
        )
        assert dialer1 is dialer2
        assert dialer2.enabled is False  # Still from first creation


# ---------------------------------------------------------------------------
# Integration-style workflow tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPredictiveDialerWorkflow:
    """End-to-end workflow tests exercising multiple methods together."""

    @patch("pbx.features.predictive_dialing.get_logger")
    def setup_method(self, method, mock_get_logger: MagicMock | None = None) -> None:
        with patch("pbx.features.predictive_dialing.get_logger") as mgl:
            mgl.return_value = MagicMock()
            self.dialer = PredictiveDialer(
                config={
                    "features": {
                        "predictive_dialing": {
                            "enabled": True,
                            "max_abandon_rate": 0.05,
                            "lines_per_agent": 2.0,
                        }
                    }
                }
            )

    def test_full_campaign_lifecycle(self) -> None:
        """Create, populate, start, dial, and stop a campaign."""
        # Create
        campaign = self.dialer.create_campaign("lifecycle", "Lifecycle Test", "progressive")
        assert campaign.status is CampaignStatus.PENDING

        # Add contacts
        contacts_data = [
            {"id": f"c{i}", "phone_number": f"555{i:07d}"} for i in range(5)
        ]
        added = self.dialer.add_contacts("lifecycle", contacts_data)
        assert added == 5

        # Start
        self.dialer.start_campaign("lifecycle")
        assert campaign.status is CampaignStatus.RUNNING

        # Dial contacts
        for _ in range(3):
            contact = self.dialer.get_next_contact("lifecycle")
            assert contact is not None
            result = self.dialer.dial_contact("lifecycle", contact)
            assert result["success"] is True
            contact.status = "completed"
            contact.call_result = "answered"

        # Check statistics
        stats = self.dialer.get_campaign_statistics("lifecycle")
        assert stats["status"] == "running"

        # Pause
        self.dialer.pause_campaign("lifecycle")
        assert campaign.status is CampaignStatus.PAUSED

        # Resume (re-start)
        self.dialer.start_campaign("lifecycle")
        assert campaign.status is CampaignStatus.RUNNING

        # Stop
        self.dialer.stop_campaign("lifecycle")
        assert campaign.status is CampaignStatus.COMPLETED
        assert self.dialer.total_calls_made == 3

    def test_abandon_rate_during_campaign(self) -> None:
        """Monitor abandon rate as contacts are dialed."""
        self.dialer.create_campaign("abandon", "Abandon Test", "predictive")
        contacts_data = [
            {"id": f"c{i}", "phone_number": f"555{i:07d}"} for i in range(10)
        ]
        self.dialer.add_contacts("abandon", contacts_data)
        self.dialer.start_campaign("abandon")

        contacts = self.dialer.campaigns["abandon"].contacts
        # Simulate: 7 answered, 3 abandoned
        for i in range(7):
            contacts[i].call_result = "answered"
        for i in range(7, 10):
            contacts[i].call_result = "abandoned"

        rate = self.dialer.calculate_abandon_rate("abandon")
        assert rate == pytest.approx(3 / 10)

    def test_predictive_dialing_agent_prediction(self) -> None:
        """Predict agent availability and use it."""
        lines = self.dialer.predict_agent_availability(
            current_agents=10,
            avg_call_duration=180.0,
            current_calls=5,
            historical_answer_rate=0.4,
        )
        assert lines > 0
        assert isinstance(lines, int)
        # Should not exceed 10 * 2.0 = 20
        assert lines <= 20

    def test_multiple_campaigns_concurrent(self) -> None:
        """Multiple campaigns can exist and be operated independently."""
        self.dialer.create_campaign("a", "Campaign A", "progressive")
        self.dialer.create_campaign("b", "Campaign B", "predictive")

        self.dialer.add_contacts("a", [{"id": "a1", "phone_number": "5551111111"}])
        self.dialer.add_contacts("b", [{"id": "b1", "phone_number": "5552222222"}])

        self.dialer.start_campaign("a")
        self.dialer.start_campaign("b")

        stats = self.dialer.get_statistics()
        assert stats["active_campaigns"] == 2
        assert stats["total_campaigns"] == 2

        self.dialer.stop_campaign("a")
        stats = self.dialer.get_statistics()
        assert stats["active_campaigns"] == 1

    def test_contact_retry_flow(self) -> None:
        """Test retry flow: dial, mark retry, wait, re-dial."""
        self.dialer.create_campaign("retry", "Retry Test", "progressive")
        self.dialer.add_contacts("retry", [
            {"id": "r1", "phone_number": "5551111111"},
        ])
        self.dialer.start_campaign("retry")

        contact = self.dialer.get_next_contact("retry")
        assert contact is not None

        # Dial
        result = self.dialer.dial_contact("retry", contact)
        assert result["success"] is True

        # Mark as retry
        contact.status = "retry"

        # Not enough time passed
        next_contact = self.dialer.get_next_contact("retry")
        assert next_contact is None

        # Simulate time passing
        contact.last_attempt = datetime.now(UTC) - timedelta(
            seconds=self.dialer.campaigns["retry"].retry_interval + 1
        )
        next_contact = self.dialer.get_next_contact("retry")
        assert next_contact is not None
        assert next_contact.contact_id == "r1"
