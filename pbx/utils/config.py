"""
Configuration management for PBX system
"""
import yaml
import os


class Config:
    """Configuration manager for PBX"""
    
    def __init__(self, config_file="config.yml"):
        """
        Initialize configuration
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config = {}
        self.load()
    
    def load(self):
        """Load configuration from YAML file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        else:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
    
    def get(self, key, default=None):
        """
        Get configuration value
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'server.sip_port')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_extensions(self):
        """Get all configured extensions"""
        return self.config.get('extensions', [])
    
    def get_extension(self, number):
        """
        Get extension by number
        
        Args:
            number: Extension number
            
        Returns:
            Extension configuration or None
        """
        extensions = self.get_extensions()
        for ext in extensions:
            if ext.get('number') == str(number):
                return ext
        return None
