"""
Predictive Dialing
AI-optimized outbound campaign management
"""

import sqlite3
from datetime import UTC, datetime, timedelta
from enum import Enum

from pbx.utils.logger import get_logger
from typing import Any


class CampaignStatus(Enum):
    """Campaign status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DialingMode(Enum):
    """Dialing mode enumeration"""

    PREVIEW = "preview"  # Agent previews contact before dial
    PROGRESSIVE = "progressive"  # Dial one contact at a time when agent available
    PREDICTIVE = "predictive"  # AI predicts agent availability and dials multiple
    POWER = "power"  # Dial multiple contacts per agent


class Contact:
    """Represents a contact in a campaign"""

    def __init__(self, contact_id: str, phone_number: str, data: dict | None = None) -> None:
        """Initialize contact"""
        self.contact_id = contact_id
        self.phone_number = phone_number
        self.data = data or {}
        self.attempts = 0
        self.last_attempt = None
        self.status = "pending"
        self.call_result = None


class Campaign:
    """Represents a dialing campaign"""

    def __init__(self, campaign_id: str, name: str, dialing_mode: DialingMode) -> None:
        """Initialize campaign"""
        self.campaign_id = campaign_id
        self.name = name
        self.dialing_mode = dialing_mode
        self.status = CampaignStatus.PENDING
        self.created_at = datetime.now(UTC)
        self.started_at = None
        self.ended_at = None
        self.contacts: list[Contact] = []
        self.max_attempts = 3
        self.retry_interval = 3600  # seconds

        # Statistics
        self.total_contacts = 0
        self.contacts_completed = 0
        self.contacts_pending = 0
        self.successful_calls = 0
        self.failed_calls = 0


class PredictiveDialer:
    """
    Predictive Dialing System

    AI-optimized outbound campaign management with intelligent dialing.
    Features:
    - Multiple dialing modes (preview, progressive, predictive, power)
    - AI-based agent availability prediction
    - Automatic retry logic
    - Call abandonment rate management
    - Compliance with call regulations
    """

    def __init__(self, config: Any | None =None, db_backend: Any | None =None) -> None:
        """Initialize predictive dialer"""
        self.logger = get_logger()
        self.config = config or {}
        self.db_backend = db_backend
        self.db = None

        # Configuration
        dialer_config = self.config.get("features", {}).get("predictive_dialing", {})
        self.enabled = dialer_config.get("enabled", False)
        self.max_abandon_rate = dialer_config.get("max_abandon_rate", 0.03)  # 3% max
        self.lines_per_agent = dialer_config.get("lines_per_agent", 1.5)
        self.answer_delay = dialer_config.get("answer_delay", 2)  # seconds

        # Campaigns
        self.campaigns: dict[str, Campaign] = {}

        # Statistics
        self.total_campaigns = 0
        self.total_calls_made = 0
        self.total_connects = 0
        self.total_abandons = 0

        # Initialize database if available
        if self.db_backend and self.db_backend.enabled:
            try:
                from pbx.features.predictive_dialing_db import PredictiveDialingDatabase

                self.db = PredictiveDialingDatabase(self.db_backend)
                self.db.create_tables()
                self.logger.info("Predictive dialing database layer initialized")
            except sqlite3.Error as e:
                self.logger.warning(f"Could not initialize database layer: {e}")

        self.logger.info("Predictive dialer initialized")
        self.logger.info(f"  Max abandon rate: {self.max_abandon_rate * 100}%")
        self.logger.info(f"  Lines per agent: {self.lines_per_agent}")
        self.logger.info(f"  Enabled: {self.enabled}")

    def create_campaign(
        self, campaign_id: str, name: str, dialing_mode: str = "progressive"
    ) -> Campaign:
        """
        Create a new dialing campaign

        Args:
            campaign_id: Unique campaign identifier
            name: Campaign name
            dialing_mode: Dialing mode (preview, progressive, predictive, power)

        Returns:
            Campaign: Created campaign
        """
        mode = DialingMode(dialing_mode)
        campaign = Campaign(campaign_id, name, mode)
        self.campaigns[campaign_id] = campaign
        self.total_campaigns += 1

        # Save to database
        if self.db:
            self.db.save_campaign(
                {
                    "campaign_id": campaign_id,
                    "name": name,
                    "dialing_mode": dialing_mode,
                    "status": campaign.status.value,
                    "max_attempts": campaign.max_attempts,
                    "retry_interval": campaign.retry_interval,
                }
            )

        self.logger.info(f"Created campaign '{name}' ({campaign_id})")
        self.logger.info(f"  Dialing mode: {dialing_mode}")

        return campaign

    def add_contacts(self, campaign_id: str, contacts: list[dict]) -> int:
        """
        Add contacts to a campaign

        Args:
            campaign_id: Campaign identifier
            contacts: list of contact dictionaries

        Returns:
            int: Number of contacts added
        """
        if campaign_id not in self.campaigns:
            self.logger.error(f"Campaign {campaign_id} not found")
            return 0

        campaign = self.campaigns[campaign_id]
        added = 0

        for contact_data in contacts:
            contact = Contact(
                contact_data["id"], contact_data["phone_number"], contact_data.get("data", {})
            )
            campaign.contacts.append(contact)
            added += 1

        campaign.total_contacts += added
        campaign.contacts_pending += added

        self.logger.info(f"Added {added} contacts to campaign {campaign_id}")
        return added

    def start_campaign(self, campaign_id: str) -> dict:
        """
        Start a campaign

        Args:
            campaign_id: Campaign identifier
        """
        if campaign_id not in self.campaigns:
            self.logger.error(f"Campaign {campaign_id} not found")
            return

        campaign = self.campaigns[campaign_id]
        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = datetime.now(UTC)

        self.logger.info(f"Started campaign {campaign_id}")
        self.logger.info(f"  Mode: {campaign.dialing_mode.value}")
        self.logger.info(f"  Total contacts: {len(campaign.contacts)}")

        # Start dialing based on mode and agent availability
        # In production, this would:
        # 1. Monitor agent availability in real-time
        # 2. Predict when agents will become available
        # 3. Initiate calls at optimal times to minimize abandonment
        # 4. Adjust dialing rate based on answer rates and agent availability

        if campaign.dialing_mode == DialingMode.PREVIEW:
            # Preview mode: Agent sees contact before call is placed
            self.logger.info("  Preview mode: Contacts will be shown to agents before dialing")

        elif campaign.dialing_mode == DialingMode.PROGRESSIVE:
            # Progressive mode: Dial one contact per available agent
            self.logger.info("  Progressive mode: Dialing one contact per available agent")
            # In production: Monitor agent queue and dial when agent becomes available

        elif campaign.dialing_mode == DialingMode.PREDICTIVE:
            # Predictive mode: Use AI to predict agent availability
            self.logger.info("  Predictive mode: Using AI prediction for optimal dialing")
            # In production: Use ML model to predict:
            # - When current calls will end
            # - Answer rate probability
            # - Optimal lines per agent ratio

        elif campaign.dialing_mode == DialingMode.POWER:
            # Power mode: Dial multiple contacts per agent
            self.logger.info(f"  Power mode: Dialing {self.lines_per_agent} lines per agent")
            # In production: Dial multiple contacts simultaneously per agent

    def pause_campaign(self, campaign_id: str) -> dict:
        """Pause a campaign"""
        if campaign_id not in self.campaigns:
            return

        campaign = self.campaigns[campaign_id]
        campaign.status = CampaignStatus.PAUSED
        self.logger.info(f"Paused campaign {campaign_id}")

    def stop_campaign(self, campaign_id: str) -> dict:
        """Stop a campaign"""
        if campaign_id not in self.campaigns:
            return

        campaign = self.campaigns[campaign_id]
        campaign.status = CampaignStatus.COMPLETED
        campaign.ended_at = datetime.now(UTC)

        # Calculate campaign statistics
        duration = (
            (campaign.ended_at - campaign.started_at).total_seconds() if campaign.started_at else 0
        )

        self.logger.info(f"Stopped campaign {campaign_id}")
        self.logger.info(f"  Duration: {duration:.1f}s")
        self.logger.info(
            f"  Contacts completed: {campaign.contacts_completed}/{campaign.total_contacts}"
        )
        self.logger.info(
            f"  Success rate: {campaign.successful_calls}/{campaign.contacts_completed}"
        )

    def predict_agent_availability(
        self,
        current_agents: int,
        avg_call_duration: float,
        current_calls: int = 0,
        historical_answer_rate: float = 0.3,
    ) -> int:
        """
        Predict how many lines to dial based on agent availability using ML-inspired approach

        This implementation uses statistical prediction. In production, integrate with:
        - scikit-learn for regression models
        - TensorFlow/PyTorch for deep learning
        - Historical call data for training

        Args:
            current_agents: Number of available agents
            avg_call_duration: Average call duration in seconds
            current_calls: Number of calls currently in progress
            historical_answer_rate: Historical answer rate (0.0 to 1.0)

        Returns:
            int: Number of lines to dial
        """
        if current_agents == 0:
            return 0

        # Calculate agents that will become available soon
        # Assuming some calls will end within prediction window
        prediction_window = 30  # seconds
        estimated_calls_ending = int(
            current_calls * (prediction_window / max(avg_call_duration, 1))
        )
        predicted_available_agents = current_agents + estimated_calls_ending

        # Calculate optimal lines to dial based on:
        # 1. Available agents
        # 2. Answer rate (not all calls will be answered)
        # 3. Target abandonment rate

        # Basic predictive formula
        # lines_to_dial = agents_available / (answer_rate * (1 - target_abandon_rate))
        answer_rate = max(0.1, historical_answer_rate)  # Minimum 10% to avoid division issues
        target_abandon_rate = self.max_abandon_rate

        # Calculate denominator and check for zero
        denominator = answer_rate * (1 - target_abandon_rate)
        if denominator <= 0.001:  # Avoid division by very small numbers
            # Fallback to simple calculation
            lines_to_dial = int(current_agents * self.lines_per_agent)
        else:
            optimal_lines = int(predicted_available_agents / denominator)

            # Apply lines-per-agent multiplier based on mode
            lines_to_dial = min(optimal_lines, int(current_agents * self.lines_per_agent))

        self.logger.debug(
            f"Predicted dialing: {lines_to_dial} lines "
            f"({current_agents} agents, {answer_rate:.2f} answer rate)"
        )

        return max(0, lines_to_dial)

    def calculate_abandon_rate(self, campaign_id: str) -> float:
        """
        Calculate current abandon rate for a campaign from actual call data

        Args:
            campaign_id: Campaign identifier

        Returns:
            float: Abandon rate (0.0 to 1.0)
        """
        if campaign_id not in self.campaigns:
            return 0.0

        campaign = self.campaigns[campaign_id]

        # In production, calculate from actual call records:
        # - Calls answered by customer
        # - Calls abandoned (customer hung up before agent available)
        # - Abandonment time threshold (typically < 2 seconds)

        # Count abandons from contact results
        abandons = sum(1 for contact in campaign.contacts if contact.call_result == "abandoned")

        # Count answered calls
        answered = sum(
            1 for contact in campaign.contacts if contact.call_result in ["answered", "connected"]
        )

        total_answered_or_abandoned = abandons + answered

        if total_answered_or_abandoned == 0:
            return 0.0

        abandon_rate = abandons / total_answered_or_abandoned

        return abandon_rate

    def get_next_contact(self, campaign_id: str) -> Contact | None:
        """
        Get next contact to dial

        Args:
            campaign_id: Campaign identifier

        Returns:
            Contact | None: Next contact to dial or None
        """
        if campaign_id not in self.campaigns:
            return None

        campaign = self.campaigns[campaign_id]
        now = datetime.now(UTC)

        for contact in campaign.contacts:
            if contact.status == "pending":
                return contact
            if contact.status == "retry" and contact.last_attempt:
                retry_time = contact.last_attempt + timedelta(seconds=campaign.retry_interval)
                if now >= retry_time:
                    return contact

        return None

    def dial_contact(self, campaign_id: str, contact: Contact) -> dict:
        """
        Initiate a call to a contact

        Args:
            campaign_id: Campaign identifier
            contact: Contact to dial

        Returns:
            dict: Call initiation result
        """
        if campaign_id not in self.campaigns:
            return {"success": False, "error": "Campaign not found"}

        campaign = self.campaigns[campaign_id]

        # Check if max attempts exceeded
        if contact.attempts >= campaign.max_attempts:
            return {"success": False, "error": "Max attempts exceeded"}

        # Integrate with PBX call manager to initiate call
        # In production, this would:
        # 1. Get the call manager instance
        # 2. Find an available agent (for preview/progressive modes)
        # 3. Create an outbound call via SIP
        # 4. Bridge the call to an agent when answered
        # 5. Handle call events (answered, no-answer, busy, failed)

        # Example integration (commented):
        # from pbx.core.call_manager import get_call_manager
        # call_manager = get_call_manager()
        #
        # # Create outbound call
        # call_id = call_manager.create_outbound_call(
        #     destination=contact.phone_number,
        #     caller_id=campaign.caller_id,
        #     campaign_id=campaign_id,
        #     contact_id=contact.contact_id
        # )
        #
        # # For predictive mode, bridge to agent when answered
        # if campaign.dialing_mode == DialingMode.PREDICTIVE:
        #     call_manager.queue_for_agent(call_id, queue='outbound')

        contact.attempts += 1
        contact.last_attempt = datetime.now(UTC)
        self.total_calls_made += 1

        self.logger.info(f"Dialing contact {contact.contact_id}: {contact.phone_number}")
        self.logger.info(f"  Campaign: {campaign.name}")
        self.logger.info(f"  Mode: {campaign.dialing_mode.value}")
        self.logger.info(f"  Attempt: {contact.attempts}/{campaign.max_attempts}")

        return {
            "success": True,
            "contact_id": contact.contact_id,
            "phone_number": contact.phone_number,
            "attempt": contact.attempts,
        }

    def get_campaign_statistics(self, campaign_id: str) -> dict | None:
        """Get statistics for a campaign"""
        if campaign_id not in self.campaigns:
            return None

        campaign = self.campaigns[campaign_id]

        return {
            "campaign_id": campaign.campaign_id,
            "name": campaign.name,
            "status": campaign.status.value,
            "dialing_mode": campaign.dialing_mode.value,
            "total_contacts": campaign.total_contacts,
            "contacts_completed": campaign.contacts_completed,
            "contacts_pending": campaign.contacts_pending,
            "successful_calls": campaign.successful_calls,
            "failed_calls": campaign.failed_calls,
            "created_at": campaign.created_at.isoformat(),
            "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
            "ended_at": campaign.ended_at.isoformat() if campaign.ended_at else None,
        }

    def get_statistics(self) -> dict:
        """Get overall dialer statistics"""
        return {
            "total_campaigns": self.total_campaigns,
            "active_campaigns": len(
                [c for c in self.campaigns.values() if c.status == CampaignStatus.RUNNING]
            ),
            "total_calls_made": self.total_calls_made,
            "total_connects": self.total_connects,
            "total_abandons": self.total_abandons,
            "abandon_rate": self.total_abandons / max(1, self.total_connects),
            "enabled": self.enabled,
        }


# Global instance
_predictive_dialer = None


def get_predictive_dialer(config: Any | None =None, db_backend: Any | None =None) -> PredictiveDialer:
    """Get or create predictive dialer instance"""
    global _predictive_dialer
    if _predictive_dialer is None:
        _predictive_dialer = PredictiveDialer(config, db_backend)
    return _predictive_dialer
