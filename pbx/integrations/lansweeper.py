"""
Lansweeper Integration
Integration with Lansweeper IT asset management system (free API)
"""
from datetime import datetime
from typing import Dict, List, Optional
from pbx.utils.logger import get_logger
import json

# Try to import requests (free)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class LansweeperIntegration:
    """Integration with Lansweeper IT asset management"""
    
    def __init__(self, config=None):
        """Initialize Lansweeper integration"""
        self.logger = get_logger()
        self.config = config or {}
        
        # Configuration
        lansweeper_config = self.config.get('integrations', {}).get('lansweeper', {})
        self.enabled = lansweeper_config.get('enabled', False)
        self.api_url = lansweeper_config.get('api_url', 'https://lansweeper-server:81/api')
        self.api_token = lansweeper_config.get('api_token')
        self.username = lansweeper_config.get('username')
        self.password = lansweeper_config.get('password')
        
        # Cache for asset data
        self.asset_cache = {}  # mac_address -> asset info
        self.phone_assets = {}  # extension -> Lansweeper asset
        self.cache_ttl = lansweeper_config.get('cache_ttl_seconds', 3600)  # 1 hour
        
        if self.enabled and not REQUESTS_AVAILABLE:
            self.logger.warning("Lansweeper integration enabled but requests library not installed")
            self.logger.info("  Install with: pip install requests")
        elif self.enabled:
            self.logger.info("Lansweeper integration initialized")
            self.logger.info(f"  API URL: {self.api_url}")
            if self.api_url.startswith('http://'):
                self.logger.warning("  WARNING: Using HTTP (not HTTPS) - API credentials sent in plaintext!")
    
    def _make_request(self, endpoint: str, method: str = 'GET', 
                     data: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request to Lansweeper"""
        if not REQUESTS_AVAILABLE:
            return None
        
        url = f"{self.api_url}/{endpoint}"
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add authentication
        if self.api_token:
            headers['Authorization'] = f"Token {self.api_token}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, 
                                       auth=(self.username, self.password) if self.username else None,
                                       timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data,
                                        auth=(self.username, self.password) if self.username else None,
                                        timeout=10)
            else:
                self.logger.error(f"Unsupported method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Lansweeper API error: {e}")
            return None
    
    def get_asset_by_mac(self, mac_address: str) -> Optional[Dict]:
        """
        Get asset information by MAC address
        
        Args:
            mac_address: MAC address of device
            
        Returns:
            Asset information or None
        """
        if not self.enabled:
            return None
        
        # Normalize MAC address
        mac_normalized = mac_address.replace(':', '').replace('-', '').upper()
        
        # Check cache
        if mac_normalized in self.asset_cache:
            cached = self.asset_cache[mac_normalized]
            if (datetime.now() - cached['cached_at']).seconds < self.cache_ttl:
                return cached['data']
        
        # Query Lansweeper API
        # Note: Actual API endpoint depends on Lansweeper version
        result = self._make_request(f"asset/mac/{mac_normalized}")
        
        if result:
            # Cache result
            self.asset_cache[mac_normalized] = {
                'data': result,
                'cached_at': datetime.now()
            }
            
            self.logger.info(f"Retrieved asset info for MAC {mac_address}")
            return result
        
        return None
    
    def get_asset_by_ip(self, ip_address: str) -> Optional[Dict]:
        """Get asset information by IP address"""
        if not self.enabled:
            return None
        
        result = self._make_request(f"asset/ip/{ip_address}")
        
        if result:
            self.logger.info(f"Retrieved asset info for IP {ip_address}")
            return result
        
        return None
    
    def get_phone_info(self, mac_address: str) -> Dict:
        """
        Get phone information from Lansweeper
        
        Args:
            mac_address: Phone MAC address
            
        Returns:
            Phone information including location, user, model
        """
        if not self.enabled:
            return {'error': 'Lansweeper integration not enabled'}
        
        asset = self.get_asset_by_mac(mac_address)
        
        if not asset:
            return {'error': 'Asset not found in Lansweeper'}
        
        # Extract relevant phone information
        phone_info = {
            'mac_address': mac_address,
            'asset_name': asset.get('AssetName', 'Unknown'),
            'model': asset.get('Model', 'Unknown'),
            'manufacturer': asset.get('Manufacturer', 'Unknown'),
            'location': asset.get('Location', 'Unknown'),
            'building': asset.get('Building', 'Unknown'),
            'room': asset.get('Room', 'Unknown'),
            'assigned_user': asset.get('UserName', 'Unknown'),
            'department': asset.get('Department', 'Unknown'),
            'ip_address': asset.get('IPAddress', 'Unknown'),
            'last_seen': asset.get('LastSeen', 'Unknown'),
            'serial_number': asset.get('SerialNumber', 'Unknown')
        }
        
        return phone_info
    
    def link_phone_to_extension(self, extension: str, mac_address: str) -> bool:
        """
        Link a phone asset to an extension
        
        Args:
            extension: Extension number
            mac_address: Phone MAC address
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        # Get asset info
        asset = self.get_asset_by_mac(mac_address)
        
        if not asset:
            self.logger.warning(f"Cannot link extension {extension}: asset not found for MAC {mac_address}")
            return False
        
        self.phone_assets[extension] = {
            'mac_address': mac_address,
            'asset_info': asset,
            'linked_at': datetime.now()
        }
        
        self.logger.info(f"Linked extension {extension} to Lansweeper asset {asset.get('AssetName', 'Unknown')}")
        return True
    
    def get_extension_location(self, extension: str) -> Optional[Dict]:
        """
        Get physical location of an extension from Lansweeper
        
        Args:
            extension: Extension number
            
        Returns:
            Location information
        """
        if extension not in self.phone_assets:
            return None
        
        phone = self.phone_assets[extension]
        asset = phone['asset_info']
        
        return {
            'building': asset.get('Building', 'Unknown'),
            'floor': asset.get('Floor', 'Unknown'),
            'room': asset.get('Room', 'Unknown'),
            'location': asset.get('Location', 'Unknown'),
            'address': asset.get('Address', 'Unknown')
        }
    
    def update_asset_custom_field(self, mac_address: str, 
                                 field_name: str, value: str) -> bool:
        """
        Update custom field in Lansweeper asset
        
        Args:
            mac_address: Asset MAC address
            field_name: Custom field name
            value: Value to set
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        # Normalize MAC
        mac_normalized = mac_address.replace(':', '').replace('-', '').upper()
        
        data = {
            'mac_address': mac_normalized,
            'field_name': field_name,
            'value': value
        }
        
        result = self._make_request('asset/customfield', method='POST', data=data)
        
        if result:
            self.logger.info(f"Updated Lansweeper asset {mac_address}: {field_name}={value}")
            return True
        
        return False
    
    def sync_phone_extension(self, extension: str, mac_address: str, 
                           phone_model: str) -> bool:
        """
        Sync phone extension to Lansweeper as custom field
        
        Args:
            extension: Extension number
            mac_address: Phone MAC address  
            phone_model: Phone model
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        # Update custom fields in Lansweeper
        success = True
        success &= self.update_asset_custom_field(mac_address, 'PBX_Extension', extension)
        success &= self.update_asset_custom_field(mac_address, 'PBX_Model', phone_model)
        success &= self.update_asset_custom_field(mac_address, 'PBX_Sync_Date', 
                                                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return success
    
    def get_all_phones(self) -> List[Dict]:
        """
        Get all IP phone assets from Lansweeper
        
        Returns:
            List of phone assets
        """
        if not self.enabled:
            return []
        
        # Query for all IP phones
        # Note: Query depends on how phones are categorized in Lansweeper
        result = self._make_request('assets?type=phone')
        
        if result and isinstance(result, list):
            self.logger.info(f"Retrieved {len(result)} phones from Lansweeper")
            return result
        
        return []
    
    def get_user_assets(self, username: str) -> List[Dict]:
        """
        Get all assets assigned to a user
        
        Args:
            username: Username to query
            
        Returns:
            List of assets
        """
        if not self.enabled:
            return []
        
        result = self._make_request(f'assets/user/{username}')
        
        if result and isinstance(result, list):
            return result
        
        return []
    
    def search_assets(self, query: str) -> List[Dict]:
        """
        Search for assets by name, IP, MAC, etc.
        
        Args:
            query: Search query
            
        Returns:
            List of matching assets
        """
        if not self.enabled:
            return []
        
        result = self._make_request(f'assets/search?q={query}')
        
        if result and isinstance(result, list):
            return result
        
        return []
    
    def get_building_phones(self, building: str) -> List[Dict]:
        """
        Get all phones in a specific building
        
        Args:
            building: Building name/ID
            
        Returns:
            List of phones in building
        """
        if not self.enabled:
            return []
        
        all_phones = self.get_all_phones()
        
        # Filter by building
        building_phones = [
            phone for phone in all_phones
            if phone.get('Building', '').lower() == building.lower()
        ]
        
        return building_phones
    
    def generate_e911_report(self) -> Dict:
        """
        Generate E911 report from Lansweeper data
        
        Returns:
            Report with phone locations
        """
        if not self.enabled:
            return {'error': 'Lansweeper integration not enabled'}
        
        phones = self.get_all_phones()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_phones': len(phones),
            'by_building': {},
            'missing_location': [],
            'phones': []
        }
        
        for phone in phones:
            building = phone.get('Building', 'Unknown')
            
            # Count by building
            if building not in report['by_building']:
                report['by_building'][building] = 0
            report['by_building'][building] += 1
            
            # Check for missing location
            if not phone.get('Location') or not phone.get('Building'):
                report['missing_location'].append({
                    'asset_name': phone.get('AssetName', 'Unknown'),
                    'mac_address': phone.get('MAC', 'Unknown'),
                    'ip_address': phone.get('IPAddress', 'Unknown')
                })
            
            # Add to phones list
            report['phones'].append({
                'asset_name': phone.get('AssetName', 'Unknown'),
                'mac_address': phone.get('MAC', 'Unknown'),
                'building': building,
                'floor': phone.get('Floor', 'Unknown'),
                'room': phone.get('Room', 'Unknown'),
                'user': phone.get('UserName', 'Unknown')
            })
        
        self.logger.info(f"Generated E911 report: {len(phones)} phones, {len(report['missing_location'])} missing location")
        
        return report
    
    def clear_cache(self):
        """Clear asset cache"""
        self.asset_cache.clear()
        self.logger.info("Cleared Lansweeper asset cache")
    
    def get_statistics(self) -> Dict:
        """Get Lansweeper integration statistics"""
        return {
            'enabled': self.enabled,
            'requests_available': REQUESTS_AVAILABLE,
            'cached_assets': len(self.asset_cache),
            'linked_phones': len(self.phone_assets),
            'api_url': self.api_url if self.enabled else None
        }
