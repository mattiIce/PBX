"""
Predictive Dialing
AI-optimized outbound campaign management
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pbx.utils.logger import get_logger


class CampaignStatus(Enum):
    """Campaign status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DialingMode(Enum):
    """Dialing mode enumeration"""
    PREVIEW = "preview"      # Agent previews contact before dial
    PROGRESSIVE = "progressive"  # Dial one contact at a time when agent available
    PREDICTIVE = "predictive"    # AI predicts agent availability and dials multiple
    POWER = "power"          # Dial multiple contacts per agent


class Contact:
    """Represents a contact in a campaign"""
    
    def __init__(self, contact_id: str, phone_number: str, data: Dict = None):
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
    
    def __init__(self, campaign_id: str, name: str, dialing_mode: DialingMode):
        """Initialize campaign"""
        self.campaign_id = campaign_id
        self.name = name
        self.dialing_mode = dialing_mode
        self.status = CampaignStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.ended_at = None
        self.contacts: List[Contact] = []
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
    
    def __init__(self, config=None):
        """Initialize predictive dialer"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        dialer_config = self.config.get('features', {}).get('predictive_dialing', {})
        self.enabled = dialer_config.get('enabled', False)
        self.max_abandon_rate = dialer_config.get('max_abandon_rate', 0.03)  # 3% max
        self.lines_per_agent = dialer_config.get('lines_per_agent', 1.5)
        self.answer_delay = dialer_config.get('answer_delay', 2)  # seconds
        
        # Campaigns
        self.campaigns: Dict[str, Campaign] = {}
        
        # Statistics
        self.total_campaigns = 0
        self.total_calls_made = 0
        self.total_connects = 0
        self.total_abandons = 0
        
        self.logger.info("Predictive dialer initialized")
        self.logger.info(f"  Max abandon rate: {self.max_abandon_rate*100}%")
        self.logger.info(f"  Lines per agent: {self.lines_per_agent}")
        self.logger.info(f"  Enabled: {self.enabled}")
    
    def create_campaign(self, campaign_id: str, name: str, 
                       dialing_mode: str = "progressive") -> Campaign:
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
        
        self.logger.info(f"Created campaign '{name}' ({campaign_id})")
        self.logger.info(f"  Dialing mode: {dialing_mode}")
        
        return campaign
    
    def add_contacts(self, campaign_id: str, contacts: List[Dict]) -> int:
        """
        Add contacts to a campaign
        
        Args:
            campaign_id: Campaign identifier
            contacts: List of contact dictionaries
            
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
                contact_data['id'],
                contact_data['phone_number'],
                contact_data.get('data', {})
            )
            campaign.contacts.append(contact)
            added += 1
        
        campaign.total_contacts += added
        campaign.contacts_pending += added
        
        self.logger.info(f"Added {added} contacts to campaign {campaign_id}")
        return added
    
    def start_campaign(self, campaign_id: str):
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
        campaign.started_at = datetime.now()
        
        self.logger.info(f"Started campaign {campaign_id}")
        # TODO: Start dialing based on mode and agent availability
    
    def pause_campaign(self, campaign_id: str):
        """Pause a campaign"""
        if campaign_id not in self.campaigns:
            return
        
        campaign = self.campaigns[campaign_id]
        campaign.status = CampaignStatus.PAUSED
        self.logger.info(f"Paused campaign {campaign_id}")
    
    def stop_campaign(self, campaign_id: str):
        """Stop a campaign"""
        if campaign_id not in self.campaigns:
            return
        
        campaign = self.campaigns[campaign_id]
        campaign.status = CampaignStatus.COMPLETED
        campaign.ended_at = datetime.now()
        self.logger.info(f"Stopped campaign {campaign_id}")
    
    def predict_agent_availability(self, current_agents: int, 
                                   avg_call_duration: float) -> int:
        """
        Predict how many lines to dial based on agent availability
        
        Args:
            current_agents: Number of available agents
            avg_call_duration: Average call duration in seconds
            
        Returns:
            int: Number of lines to dial
        """
        # TODO: Implement ML-based prediction
        # This is a simple placeholder
        if current_agents == 0:
            return 0
        
        return max(1, int(current_agents * self.lines_per_agent))
    
    def calculate_abandon_rate(self, campaign_id: str) -> float:
        """
        Calculate current abandon rate for a campaign
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            float: Abandon rate (0.0 to 1.0)
        """
        if campaign_id not in self.campaigns:
            return 0.0
        
        # TODO: Calculate from actual call data
        return self.total_abandons / max(1, self.total_connects)
    
    def get_next_contact(self, campaign_id: str) -> Optional[Contact]:
        """
        Get next contact to dial
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            Optional[Contact]: Next contact to dial or None
        """
        if campaign_id not in self.campaigns:
            return None
        
        campaign = self.campaigns[campaign_id]
        now = datetime.now()
        
        for contact in campaign.contacts:
            if contact.status == "pending":
                return contact
            elif contact.status == "retry":
                if contact.last_attempt:
                    retry_time = contact.last_attempt + timedelta(
                        seconds=campaign.retry_interval
                    )
                    if now >= retry_time:
                        return contact
        
        return None
    
    def dial_contact(self, campaign_id: str, contact: Contact) -> Dict:
        """
        Initiate a call to a contact
        
        Args:
            campaign_id: Campaign identifier
            contact: Contact to dial
            
        Returns:
            Dict: Call initiation result
        """
        # TODO: Integrate with PBX call manager to initiate call
        contact.attempts += 1
        contact.last_attempt = datetime.now()
        self.total_calls_made += 1
        
        self.logger.info(f"Dialing contact {contact.contact_id}: {contact.phone_number}")
        
        return {
            'success': True,
            'contact_id': contact.contact_id,
            'phone_number': contact.phone_number,
            'attempt': contact.attempts
        }
    
    def get_campaign_statistics(self, campaign_id: str) -> Optional[Dict]:
        """Get statistics for a campaign"""
        if campaign_id not in self.campaigns:
            return None
        
        campaign = self.campaigns[campaign_id]
        
        return {
            'campaign_id': campaign.campaign_id,
            'name': campaign.name,
            'status': campaign.status.value,
            'dialing_mode': campaign.dialing_mode.value,
            'total_contacts': campaign.total_contacts,
            'contacts_completed': campaign.contacts_completed,
            'contacts_pending': campaign.contacts_pending,
            'successful_calls': campaign.successful_calls,
            'failed_calls': campaign.failed_calls,
            'created_at': campaign.created_at.isoformat(),
            'started_at': campaign.started_at.isoformat() if campaign.started_at else None,
            'ended_at': campaign.ended_at.isoformat() if campaign.ended_at else None
        }
    
    def get_statistics(self) -> Dict:
        """Get overall dialer statistics"""
        return {
            'total_campaigns': self.total_campaigns,
            'active_campaigns': len([c for c in self.campaigns.values() 
                                    if c.status == CampaignStatus.RUNNING]),
            'total_calls_made': self.total_calls_made,
            'total_connects': self.total_connects,
            'total_abandons': self.total_abandons,
            'abandon_rate': self.total_abandons / max(1, self.total_connects),
            'enabled': self.enabled
        }


# Global instance
_predictive_dialer = None


def get_predictive_dialer(config=None) -> PredictiveDialer:
    """Get or create predictive dialer instance"""
    global _predictive_dialer
    if _predictive_dialer is None:
        _predictive_dialer = PredictiveDialer(config)
    return _predictive_dialer
