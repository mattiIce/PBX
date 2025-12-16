"""
Mobile Number Portability
Use business number on mobile device
"""
from typing import Dict, Optional
from datetime import datetime
from pbx.utils.logger import get_logger


class MobileNumberPortability:
    """
    Mobile Number Portability
    
    Allows users to use their business phone number on their mobile device.
    Features:
    - DID mapping to mobile devices
    - Simultaneous ring (desk phone + mobile)
    - Mobile-first routing
    - Business hours routing rules
    - BYOD (Bring Your Own Device) support
    
    Requires:
    - Mobile SIP client registration
    - DID routing configuration
    - Mobile app with SIP support
    """
    
    def __init__(self, config=None):
        """Initialize mobile number portability"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        mnp_config = self.config.get('features', {}).get('mobile_number_portability', {})
        self.enabled = mnp_config.get('enabled', False)
        self.sim_ring_enabled = mnp_config.get('simultaneous_ring', True)
        self.mobile_first = mnp_config.get('mobile_first', False)
        
        # Number mappings
        self.number_mappings: Dict[str, Dict] = {}
        
        # Statistics
        self.total_mappings = 0
        self.calls_to_mobile = 0
        self.calls_to_desk = 0
        
        self.logger.info("Mobile number portability initialized")
        self.logger.info(f"  Simultaneous ring: {self.sim_ring_enabled}")
        self.logger.info(f"  Mobile first: {self.mobile_first}")
        self.logger.info(f"  Enabled: {self.enabled}")
    
    def map_number_to_mobile(self, business_number: str, extension: str,
                            mobile_device_id: str, settings: Dict = None) -> Dict:
        """
        Map business number to mobile device
        
        Args:
            business_number: Business DID/number
            extension: User's extension
            mobile_device_id: Mobile device identifier
            settings: Additional settings
            
        Returns:
            Dict: Mapping result
        """
        settings = settings or {}
        
        mapping = {
            'business_number': business_number,
            'extension': extension,
            'mobile_device_id': mobile_device_id,
            'simultaneous_ring': settings.get('simultaneous_ring', self.sim_ring_enabled),
            'mobile_first': settings.get('mobile_first', self.mobile_first),
            'business_hours_only': settings.get('business_hours_only', False),
            'created_at': datetime.now(),
            'active': True
        }
        
        self.number_mappings[business_number] = mapping
        self.total_mappings += 1
        
        self.logger.info(f"Mapped {business_number} to mobile device {mobile_device_id}")
        self.logger.info(f"  Extension: {extension}")
        self.logger.info(f"  Simultaneous ring: {mapping['simultaneous_ring']}")
        
        return {
            'success': True,
            'business_number': business_number,
            'mapping_id': business_number
        }
    
    def route_call(self, business_number: str, caller_id: str) -> Dict:
        """
        Route incoming call based on number mapping
        
        Args:
            business_number: Called business number
            caller_id: Caller's number
            
        Returns:
            Dict: Routing decision
        """
        if business_number not in self.number_mappings:
            return {
                'route_to': 'desk_phone',
                'reason': 'No mobile mapping'
            }
        
        mapping = self.number_mappings[business_number]
        
        if not mapping['active']:
            return {
                'route_to': 'desk_phone',
                'reason': 'Mapping inactive'
            }
        
        # Check business hours if required
        if mapping['business_hours_only']:
            if not self._is_business_hours():
                return {
                    'route_to': 'desk_phone',
                    'reason': 'Outside business hours'
                }
        
        # Determine routing
        if mapping['simultaneous_ring']:
            self.calls_to_mobile += 1
            self.calls_to_desk += 1
            return {
                'route_to': 'both',
                'targets': [
                    {'type': 'desk_phone', 'extension': mapping['extension']},
                    {'type': 'mobile', 'device_id': mapping['mobile_device_id']}
                ],
                'strategy': 'first_answer'
            }
        elif mapping['mobile_first']:
            self.calls_to_mobile += 1
            return {
                'route_to': 'mobile',
                'device_id': mapping['mobile_device_id'],
                'failover_to': 'desk_phone',
                'failover_extension': mapping['extension']
            }
        else:
            self.calls_to_desk += 1
            return {
                'route_to': 'desk_phone',
                'extension': mapping['extension']
            }
    
    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours"""
        # Check against configured business hours
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()  # 0 = Monday, 6 = Sunday
        
        # Get business hours from config
        mnp_config = self.config.get('features', {}).get('mobile_number_portability', {})
        business_hours = mnp_config.get('business_hours', {})
        
        # Default to Mon-Fri 9am-5pm if not configured
        start_hour = business_hours.get('start_hour', 9)
        start_minute = business_hours.get('start_minute', 0)
        end_hour = business_hours.get('end_hour', 17)
        end_minute = business_hours.get('end_minute', 0)
        work_days = business_hours.get('work_days', [0, 1, 2, 3, 4])  # Mon-Fri
        
        # Check if today is a work day
        if weekday not in work_days:
            return False
        
        # Convert times to minutes for easier comparison
        current_time_minutes = hour * 60 + minute
        start_time_minutes = start_hour * 60 + start_minute
        end_time_minutes = end_hour * 60 + end_minute
        
        # Check if current time is within business hours
        if current_time_minutes < start_time_minutes or current_time_minutes >= end_time_minutes:
            return False
        
        return True
    
    def toggle_mapping(self, business_number: str, active: bool) -> bool:
        """
        Activate or deactivate number mapping
        
        Args:
            business_number: Business number
            active: Active state
            
        Returns:
            bool: Success
        """
        if business_number not in self.number_mappings:
            return False
        
        self.number_mappings[business_number]['active'] = active
        
        self.logger.info(f"{'Activated' if active else 'Deactivated'} mapping for {business_number}")
        return True
    
    def remove_mapping(self, business_number: str) -> bool:
        """Remove number mapping"""
        if business_number in self.number_mappings:
            del self.number_mappings[business_number]
            self.logger.info(f"Removed mapping for {business_number}")
            return True
        return False
    
    def get_mapping(self, business_number: str) -> Optional[Dict]:
        """Get mapping for a business number"""
        return self.number_mappings.get(business_number)
    
    def get_user_mappings(self, extension: str) -> list:
        """Get all mappings for a user"""
        return [
            mapping for mapping in self.number_mappings.values()
            if mapping['extension'] == extension
        ]
    
    def get_statistics(self) -> Dict:
        """Get MNP statistics"""
        active_mappings = sum(
            1 for m in self.number_mappings.values() if m['active']
        )
        
        return {
            'enabled': self.enabled,
            'total_mappings': len(self.number_mappings),
            'active_mappings': active_mappings,
            'calls_to_mobile': self.calls_to_mobile,
            'calls_to_desk': self.calls_to_desk,
            'simultaneous_ring_enabled': self.sim_ring_enabled
        }


# Global instance
_mobile_number_portability = None


def get_mobile_number_portability(config=None) -> MobileNumberPortability:
    """Get or create mobile number portability instance"""
    global _mobile_number_portability
    if _mobile_number_portability is None:
        _mobile_number_portability = MobileNumberPortability(config)
    return _mobile_number_portability
