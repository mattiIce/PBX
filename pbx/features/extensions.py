"""
Extension management and registry
"""
from datetime import datetime
from pbx.utils.logger import get_logger


class Extension:
    """Represents a registered extension"""
    
    def __init__(self, number, name, config):
        """
        Initialize extension
        
        Args:
            number: Extension number
            name: Display name
            config: Extension configuration dict
        """
        self.number = number
        self.name = name
        self.config = config
        self.registered = False
        self.address = None
        self.registration_time = None
    
    def register(self, address):
        """
        Register extension
        
        Args:
            address: Network address (host, port)
        """
        self.registered = True
        self.address = address
        self.registration_time = datetime.now()
    
    def unregister(self):
        """Unregister extension"""
        self.registered = False
        self.address = None
        self.registration_time = None
    
    def __str__(self):
        status = "registered" if self.registered else "unregistered"
        return f"Extension {self.number} ({self.name}) - {status}"


class ExtensionRegistry:
    """Registry of all extensions"""
    
    def __init__(self, config):
        """
        Initialize extension registry
        
        Args:
            config: Config object
        """
        self.config = config
        self.logger = get_logger()
        self.extensions = {}
        
        # Load extensions from configuration
        self._load_extensions()
    
    def _load_extensions(self):
        """Load extensions from configuration"""
        extension_configs = self.config.get_extensions()
        
        for ext_config in extension_configs:
            number = ext_config.get('number')
            name = ext_config.get('name', f"Extension {number}")
            
            extension = Extension(number, name, ext_config)
            self.extensions[number] = extension
            
            self.logger.info(f"Loaded extension {number} ({name})")
    
    def get(self, number):
        """
        Get extension by number
        
        Args:
            number: Extension number
            
        Returns:
            Extension object or None
        """
        return self.extensions.get(str(number))
    
    def register(self, number, address):
        """
        Register extension
        
        Args:
            number: Extension number
            address: Network address
            
        Returns:
            True if registered successfully
        """
        extension = self.get(number)
        if extension:
            extension.register(address)
            self.logger.info(f"Extension {number} registered from {address}")
            return True
        return False
    
    def unregister(self, number):
        """
        Unregister extension
        
        Args:
            number: Extension number
            
        Returns:
            True if unregistered successfully
        """
        extension = self.get(number)
        if extension:
            extension.unregister()
            self.logger.info(f"Extension {number} unregistered")
            return True
        return False
    
    def is_registered(self, number):
        """
        Check if extension is registered
        
        Args:
            number: Extension number
            
        Returns:
            True if registered
        """
        extension = self.get(number)
        return extension.registered if extension else False
    
    def get_registered(self):
        """
        Get all registered extensions
        
        Returns:
            List of registered Extension objects
        """
        return [ext for ext in self.extensions.values() if ext.registered]
    
    def get_registered_count(self):
        """Get count of registered extensions"""
        return len(self.get_registered())
    
    def get_all(self):
        """Get all extensions"""
        return list(self.extensions.values())
    
    def authenticate(self, number, password):
        """
        Authenticate extension
        
        Args:
            number: Extension number
            password: Password
            
        Returns:
            True if authenticated
        """
        extension = self.get(number)
        if extension:
            config_password = extension.config.get('password')
            return password == config_password
        return False
