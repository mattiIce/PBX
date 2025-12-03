"""
Extension management and registry
"""
from datetime import datetime
from pbx.utils.logger import get_logger
from pbx.utils.encryption import get_encryption


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
        
        # Initialize encryption for FIPS-compliant password handling
        fips_mode = config.get('security.fips_mode', False)
        self.encryption = get_encryption(fips_mode)
        
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
    
    def reload(self):
        """Reload extensions from configuration"""
        self.config.load()
        self.extensions.clear()
        self._load_extensions()
    
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
        Authenticate extension using FIPS-compliant password verification
        
        Args:
            number: Extension number
            password: Password
            
        Returns:
            True if authenticated
        """
        extension = self.get(number)
        if extension:
            config_password = extension.config.get('password')
            
            # Check if password is already hashed (contains salt)
            password_hash = extension.config.get('password_hash')
            password_salt = extension.config.get('password_salt')
            
            if password_hash and password_salt:
                # Use FIPS-compliant verification
                try:
                    return self.encryption.verify_password(
                        password, password_hash, password_salt
                    )
                except Exception as e:
                    self.logger.error(f"Error verifying password: {e}")
                    return False
            else:
                # Fallback to plain text comparison (not recommended for production)
                # Use constant-time comparison to prevent timing attacks
                self.logger.warning(
                    f"Extension {number} using plain text password - "
                    "consider migrating to hashed passwords"
                )
                import secrets
                if isinstance(password, str):
                    password = password.encode('utf-8')
                if isinstance(config_password, str):
                    config_password = config_password.encode('utf-8')
                return secrets.compare_digest(password, config_password)
        return False
    
    def hash_extension_password(self, number, password):
        """
        Hash an extension's password using FIPS-compliant algorithm
        
        Args:
            number: Extension number
            password: Plain text password
            
        Returns:
            True if successful
        """
        extension = self.get(number)
        if extension:
            password_hash, password_salt = self.encryption.hash_password(password)
            extension.config['password_hash'] = password_hash
            extension.config['password_salt'] = password_salt
            self.logger.info(f"Hashed password for extension {number}")
            return True
        return False
