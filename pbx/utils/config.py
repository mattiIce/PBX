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
    
    def save(self):
        """Save current configuration to YAML file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            return True
        except PermissionError as e:
            print(f"Error saving config: Permission denied - {e}")
            return False
        except OSError as e:
            print(f"Error saving config: Disk error - {e}")
            return False
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def add_extension(self, number, name, email, password, allow_external=True):
        """
        Add a new extension to configuration
        
        Args:
            number: Extension number
            name: Display name
            email: Email address
            password: Password
            allow_external: Allow external calls
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if 'extensions' not in self.config:
                self.config['extensions'] = []
            
            # Check if extension already exists
            for ext in self.config['extensions']:
                if ext.get('number') == str(number):
                    return False
            
            # Validate email format if provided
            if email and '@' not in email:
                print(f"Error adding extension: Invalid email format")
                return False
            
            # Add new extension
            new_ext = {
                'number': str(number),
                'name': name,
                'password': password,
                'allow_external': allow_external
            }
            
            if email:
                new_ext['email'] = email
            
            self.config['extensions'].append(new_ext)
            return self.save()
        except Exception as e:
            print(f"Error adding extension: {e}")
            return False
    
    def update_extension(self, number, name=None, email=None, password=None, allow_external=None):
        """
        Update an existing extension
        
        Args:
            number: Extension number
            name: New display name (optional)
            email: New email address (optional)
            password: New password (optional)
            allow_external: New allow_external setting (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if 'extensions' not in self.config:
                return False
            
            # Validate email format if provided
            if email is not None and email and '@' not in email:
                print(f"Error updating extension: Invalid email format")
                return False
            
            # Find and update extension
            for ext in self.config['extensions']:
                if ext.get('number') == str(number):
                    if name is not None:
                        ext['name'] = name
                    if email is not None:
                        ext['email'] = email
                    if password is not None:
                        ext['password'] = password
                    if allow_external is not None:
                        ext['allow_external'] = allow_external
                    return self.save()
            
            return False
        except Exception as e:
            print(f"Error updating extension: {e}")
            return False
    
    def delete_extension(self, number):
        """
        Delete an extension from configuration
        
        Args:
            number: Extension number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if 'extensions' not in self.config:
                return False
            
            # Find and remove extension
            original_length = len(self.config['extensions'])
            self.config['extensions'] = [
                ext for ext in self.config['extensions']
                if ext.get('number') != str(number)
            ]
            
            if len(self.config['extensions']) < original_length:
                return self.save()
            
            return False
        except Exception as e:
            print(f"Error deleting extension: {e}")
            return False
    
    def update_email_config(self, config_data):
        """
        Update email/SMTP configuration
        
        Args:
            config_data: Dictionary with email configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if 'voicemail' not in self.config:
                self.config['voicemail'] = {}
            
            # Update SMTP settings
            if 'smtp' in config_data:
                if 'smtp' not in self.config['voicemail']:
                    self.config['voicemail']['smtp'] = {}
                
                smtp = config_data['smtp']
                if 'host' in smtp:
                    self.config['voicemail']['smtp']['host'] = smtp['host']
                if 'port' in smtp:
                    self.config['voicemail']['smtp']['port'] = smtp['port']
                if 'username' in smtp:
                    self.config['voicemail']['smtp']['username'] = smtp['username']
                if 'password' in smtp:
                    self.config['voicemail']['smtp']['password'] = smtp['password']
            
            # Update email settings
            if 'email' in config_data:
                if 'email' not in self.config['voicemail']:
                    self.config['voicemail']['email'] = {}
                
                email = config_data['email']
                if 'from_address' in email:
                    self.config['voicemail']['email']['from_address'] = email['from_address']
            
            # Update email notifications flag
            if 'email_notifications' in config_data:
                self.config['voicemail']['email_notifications'] = config_data['email_notifications']
            
            return self.save()
        except Exception as e:
            print(f"Error updating email config: {e}")
            return False
