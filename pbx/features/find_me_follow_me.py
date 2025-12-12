"""
Find Me/Follow Me Call Routing
Ring multiple devices sequentially or simultaneously
"""
from datetime import datetime
from typing import Dict, List, Optional
from pbx.utils.logger import get_logger


class FindMeFollowMe:
    """Find Me/Follow Me call routing system"""
    
    def __init__(self, config=None):
        """Initialize Find Me/Follow Me"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get('features', {}).get('find_me_follow_me', {}).get('enabled', False)
        
        # User configurations
        self.user_configs = {}  # extension -> FMFM config
        
        if self.enabled:
            self.logger.info("Find Me/Follow Me system initialized")
            self._load_configs()
    
    def _load_configs(self):
        """Load FMFM configurations from config"""
        configs = self.config.get('features', {}).get('find_me_follow_me', {}).get('users', [])
        for cfg in configs:
            self.user_configs[cfg['extension']] = cfg
    
    def set_config(self, extension: str, config: Dict) -> bool:
        """
        Set Find Me/Follow Me configuration for an extension
        
        Args:
            extension: Extension number
            config: FMFM configuration
                Required: mode ('sequential' or 'simultaneous')
                Required: destinations (list of numbers with ring_time)
                Optional: enabled, no_answer_destination
                
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        required_fields = ['mode', 'destinations']
        if not all(field in config for field in required_fields):
            self.logger.error(f"Missing required FMFM fields for {extension}")
            return False
        
        if config['mode'] not in ['sequential', 'simultaneous']:
            self.logger.error(f"Invalid FMFM mode: {config['mode']}")
            return False
        
        self.user_configs[extension] = {
            **config,
            'extension': extension,
            'updated_at': datetime.now()
        }
        
        self.logger.info(f"Set FMFM config for {extension}: {config['mode']} mode with {len(config['destinations'])} destinations")
        return True
    
    def get_config(self, extension: str) -> Optional[Dict]:
        """Get FMFM configuration for an extension"""
        return self.user_configs.get(extension)
    
    def get_ring_strategy(self, extension: str, call_id: str) -> Dict:
        """
        Get ringing strategy for a call
        
        Args:
            extension: Called extension
            call_id: Call identifier
            
        Returns:
            Ring strategy information
        """
        if not self.enabled:
            return {'strategy': 'normal', 'destinations': [extension]}
        
        config = self.get_config(extension)
        if not config or not config.get('enabled', True):
            return {'strategy': 'normal', 'destinations': [extension]}
        
        mode = config['mode']
        destinations = config['destinations']
        
        if mode == 'sequential':
            # Ring destinations one at a time
            ring_plan = []
            for dest in destinations:
                ring_plan.append({
                    'destination': dest['number'],
                    'ring_time': dest.get('ring_time', 20),
                    'order': 'sequential'
                })
            
            return {
                'strategy': 'sequential',
                'destinations': ring_plan,
                'no_answer_destination': config.get('no_answer_destination'),
                'call_id': call_id
            }
        
        elif mode == 'simultaneous':
            # Ring all destinations at once
            ring_plan = []
            max_ring_time = 0
            for dest in destinations:
                ring_time = dest.get('ring_time', 30)
                ring_plan.append({
                    'destination': dest['number'],
                    'ring_time': ring_time
                })
                max_ring_time = max(max_ring_time, ring_time)
            
            return {
                'strategy': 'simultaneous',
                'destinations': ring_plan,
                'max_ring_time': max_ring_time,
                'no_answer_destination': config.get('no_answer_destination'),
                'call_id': call_id
            }
        
        return {'strategy': 'normal', 'destinations': [extension]}
    
    def add_destination(self, extension: str, number: str, ring_time: int = 20) -> bool:
        """Add a destination to an extension's FMFM list"""
        if extension not in self.user_configs:
            # Create new config
            self.user_configs[extension] = {
                'extension': extension,
                'mode': 'sequential',
                'destinations': [],
                'enabled': True
            }
        
        config = self.user_configs[extension]
        config['destinations'].append({
            'number': number,
            'ring_time': ring_time
        })
        
        self.logger.info(f"Added FMFM destination for {extension}: {number}")
        return True
    
    def remove_destination(self, extension: str, number: str) -> bool:
        """Remove a destination from an extension's FMFM list"""
        if extension not in self.user_configs:
            return False
        
        config = self.user_configs[extension]
        original_count = len(config['destinations'])
        config['destinations'] = [
            d for d in config['destinations']
            if d['number'] != number
        ]
        
        removed = original_count - len(config['destinations'])
        if removed > 0:
            self.logger.info(f"Removed {removed} FMFM destination(s) for {extension}: {number}")
            return True
        
        return False
    
    def enable_fmfm(self, extension: str) -> bool:
        """Enable FMFM for an extension"""
        if extension in self.user_configs:
            self.user_configs[extension]['enabled'] = True
            self.logger.info(f"Enabled FMFM for {extension}")
            return True
        return False
    
    def disable_fmfm(self, extension: str) -> bool:
        """Disable FMFM for an extension"""
        if extension in self.user_configs:
            self.user_configs[extension]['enabled'] = False
            self.logger.info(f"Disabled FMFM for {extension}")
            return True
        return False
    
    def list_extensions_with_fmfm(self) -> List[str]:
        """List extensions with FMFM configured"""
        return [
            ext for ext, cfg in self.user_configs.items()
            if cfg.get('enabled', True)
        ]
    
    def get_statistics(self) -> Dict:
        """Get FMFM statistics"""
        sequential_count = sum(
            1 for cfg in self.user_configs.values()
            if cfg.get('mode') == 'sequential' and cfg.get('enabled', True)
        )
        simultaneous_count = sum(
            1 for cfg in self.user_configs.values()
            if cfg.get('mode') == 'simultaneous' and cfg.get('enabled', True)
        )
        
        return {
            'enabled': self.enabled,
            'total_configs': len(self.user_configs),
            'sequential_configs': sequential_count,
            'simultaneous_configs': simultaneous_count
        }
