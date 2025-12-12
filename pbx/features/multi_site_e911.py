"""
Multi-Site E911 Support
Per-location emergency routing for multi-office deployments
"""
from datetime import datetime
from typing import Dict, Optional, List
from pbx.utils.logger import get_logger


class MultiSiteE911:
    """Multi-site E911 management for distributed offices"""
    
    def __init__(self, config=None):
        """Initialize multi-site E911"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get('features', {}).get('multi_site_e911', {}).get('enabled', False)
        
        # Site database
        self.sites = {}  # site_id -> site info
        self.device_site_map = {}  # device_id -> site_id
        
        if self.enabled:
            self.logger.info("Multi-site E911 initialized")
            self._load_sites()
    
    def _load_sites(self):
        """Load site configurations"""
        # Load from config if available
        sites_config = self.config.get('features', {}).get('multi_site_e911', {}).get('sites', [])
        for site in sites_config:
            self.register_site(site['site_id'], site)
    
    def register_site(self, site_id: str, site_info: Dict) -> bool:
        """
        Register a new site
        
        Args:
            site_id: Unique site identifier
            site_info: Site information
                Required: name, address, city, state, zip_code
                Optional: emergency_trunk, psap_phone, building_info
                
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        required_fields = ['name', 'address', 'city', 'state', 'zip_code']
        if not all(field in site_info for field in required_fields):
            self.logger.error(f"Missing required fields for site {site_id}")
            return False
        
        self.sites[site_id] = {
            **site_info,
            'site_id': site_id,
            'registered_at': datetime.now(),
            'devices': []
        }
        
        self.logger.info(f"Registered site {site_id}: {site_info['name']}")
        self.logger.info(f"  Location: {site_info['address']}, {site_info['city']}, {site_info['state']}")
        if 'emergency_trunk' in site_info:
            self.logger.info(f"  Emergency trunk: {site_info['emergency_trunk']}")
        
        return True
    
    def assign_device_to_site(self, device_id: str, site_id: str) -> bool:
        """Assign a device to a specific site"""
        if site_id not in self.sites:
            self.logger.error(f"Site {site_id} not found")
            return False
        
        self.device_site_map[device_id] = site_id
        self.sites[site_id]['devices'].append(device_id)
        
        self.logger.info(f"Assigned device {device_id} to site {site_id}")
        return True
    
    def get_device_site(self, device_id: str) -> Optional[str]:
        """Get the site ID for a device"""
        return self.device_site_map.get(device_id)
    
    def get_site_info(self, site_id: str) -> Optional[Dict]:
        """Get information about a site"""
        return self.sites.get(site_id)
    
    def get_emergency_routing(self, device_id: str) -> Dict:
        """
        Get emergency routing information for a device
        
        Args:
            device_id: Device identifier
            
        Returns:
            Routing information including site and trunk
        """
        if not self.enabled:
            return {'error': 'Multi-site E911 not enabled'}
        
        site_id = self.get_device_site(device_id)
        if not site_id:
            return {
                'error': 'Device not assigned to any site',
                'device_id': device_id
            }
        
        site = self.get_site_info(site_id)
        if not site:
            return {'error': f'Site {site_id} not found'}
        
        return {
            'device_id': device_id,
            'site_id': site_id,
            'site_name': site['name'],
            'location': {
                'address': site['address'],
                'city': site['city'],
                'state': site['state'],
                'zip_code': site['zip_code'],
                'building_info': site.get('building_info', '')
            },
            'emergency_trunk': site.get('emergency_trunk', 'default_emergency'),
            'psap_phone': site.get('psap_phone', '911'),
            'dispatchable_location': self._format_dispatchable_location(site)
        }
    
    def _format_dispatchable_location(self, site: Dict) -> str:
        """Format site as dispatchable location"""
        parts = [site['address']]
        
        if 'building_info' in site:
            parts.append(site['building_info'])
        
        parts.extend([
            site['city'],
            site['state'],
            site['zip_code']
        ])
        
        return ', '.join(parts)
    
    def list_sites(self) -> List[Dict]:
        """List all registered sites"""
        return [
            {
                'site_id': site_id,
                'name': site['name'],
                'location': f"{site['address']}, {site['city']}, {site['state']}",
                'device_count': len(site['devices'])
            }
            for site_id, site in self.sites.items()
        ]
    
    def get_site_devices(self, site_id: str) -> List[str]:
        """Get list of devices at a site"""
        site = self.sites.get(site_id)
        return site['devices'] if site else []
    
    def get_statistics(self) -> Dict:
        """Get multi-site E911 statistics"""
        total_devices = sum(len(site['devices']) for site in self.sites.values())
        return {
            'enabled': self.enabled,
            'total_sites': len(self.sites),
            'total_devices': total_devices,
            'sites_with_emergency_trunk': sum(1 for site in self.sites.values() if 'emergency_trunk' in site)
        }
