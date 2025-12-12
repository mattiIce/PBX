"""
Nomadic E911 Support
Location-based emergency routing with custom implementation
"""
from datetime import datetime
from typing import Dict, Optional, List
from pbx.utils.logger import get_logger


class E911LocationService:
    """Service for managing E911 locations and routing"""
    
    def __init__(self, config=None):
        """Initialize E911 location service"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get('features', {}).get('e911', {}).get('enabled', False)
        
        # Location database (in production, would use external PSAP database)
        self.locations = {}  # extension/device -> location info
        self.psap_database = {}  # zip_code -> PSAP info
        self.emergency_calls = []  # Log of emergency calls
        
        if self.enabled:
            self.logger.info("E911 location service initialized")
            self._load_psap_database()
    
    def _load_psap_database(self):
        """Load PSAP (Public Safety Answering Point) database"""
        # Stub - in production would load from external database
        # Format: zip_code -> PSAP contact info
        self.psap_database = {
            '12345': {
                'name': 'City Emergency Services',
                'phone': '911',
                'address': '123 Main St',
                'city': 'Anytown',
                'state': 'ST'
            }
        }
        self.logger.info(f"Loaded {len(self.psap_database)} PSAP entries")
    
    def register_location(self, device_id: str, location: Dict) -> bool:
        """
        Register a location for a device/extension
        
        Args:
            device_id: Device or extension identifier
            location: Location information dictionary
                Required fields: address, city, state, zip_code
                Optional: building, floor, room, latitude, longitude
                
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        required_fields = ['address', 'city', 'state', 'zip_code']
        if not all(field in location for field in required_fields):
            self.logger.error(f"Missing required location fields for {device_id}")
            return False
        
        self.locations[device_id] = {
            **location,
            'registered_at': datetime.now(),
            'last_updated': datetime.now()
        }
        
        self.logger.info(f"Registered E911 location for {device_id}: "
                        f"{location['address']}, {location['city']}, {location['state']}")
        return True
    
    def update_location(self, device_id: str, location: Dict) -> bool:
        """Update location for a device (for nomadic users)"""
        if device_id in self.locations:
            self.locations[device_id].update(location)
            self.locations[device_id]['last_updated'] = datetime.now()
            self.logger.info(f"Updated E911 location for {device_id}")
            return True
        return False
    
    def get_location(self, device_id: str) -> Optional[Dict]:
        """Get registered location for a device"""
        return self.locations.get(device_id)
    
    def get_psap_for_location(self, zip_code: str) -> Optional[Dict]:
        """Get PSAP information for a zip code"""
        return self.psap_database.get(zip_code)
    
    def route_emergency_call(self, device_id: str, caller_info: Dict) -> Dict:
        """
        Route an emergency call with location information
        
        Args:
            device_id: Device making the call
            caller_info: Caller information
            
        Returns:
            Routing information with PSAP and location
        """
        if not self.enabled:
            return {'error': 'E911 not enabled'}
        
        location = self.get_location(device_id)
        if not location:
            self.logger.error(f"No E911 location registered for {device_id}")
            return {
                'error': 'No location registered',
                'device_id': device_id
            }
        
        psap = self.get_psap_for_location(location['zip_code'])
        if not psap:
            self.logger.warning(f"No PSAP found for zip {location['zip_code']}")
        
        # Log emergency call
        call_record = {
            'device_id': device_id,
            'caller_info': caller_info,
            'location': location,
            'psap': psap,
            'timestamp': datetime.now()
        }
        self.emergency_calls.append(call_record)
        
        self.logger.critical(f"EMERGENCY CALL from {device_id}")
        self.logger.critical(f"  Location: {location['address']}, {location['city']}, {location['state']}")
        if 'building' in location:
            self.logger.critical(f"  Building: {location['building']}")
        if 'floor' in location:
            self.logger.critical(f"  Floor: {location['floor']}")
        if 'room' in location:
            self.logger.critical(f"  Room: {location['room']}")
        
        return {
            'device_id': device_id,
            'location': location,
            'psap': psap,
            'dispatchable_location': self._format_dispatchable_location(location),
            'routing': 'emergency_trunk'
        }
    
    def _format_dispatchable_location(self, location: Dict) -> str:
        """Format location as dispatchable location string (Ray Baum's Act)"""
        parts = [location['address']]
        
        if 'building' in location:
            parts.append(f"Building {location['building']}")
        if 'floor' in location:
            parts.append(f"Floor {location['floor']}")
        if 'room' in location:
            parts.append(f"Room {location['room']}")
        
        parts.extend([
            location['city'],
            location['state'],
            location['zip_code']
        ])
        
        return ', '.join(parts)
    
    def get_emergency_call_history(self, device_id: Optional[str] = None) -> List[Dict]:
        """Get history of emergency calls"""
        if device_id:
            return [call for call in self.emergency_calls if call['device_id'] == device_id]
        return self.emergency_calls
    
    def get_statistics(self) -> Dict:
        """Get E911 service statistics"""
        return {
            'enabled': self.enabled,
            'registered_locations': len(self.locations),
            'psap_entries': len(self.psap_database),
            'emergency_calls': len(self.emergency_calls)
        }
