"""
Phone Provisioning Module
Provides auto-configuration for IP phones (SIP phones)
"""
import os
import hashlib
from datetime import datetime
from pbx.utils.logger import get_logger


class PhoneTemplate:
    """Represents a phone configuration template"""
    
    def __init__(self, vendor, model, template_content):
        """
        Initialize phone template
        
        Args:
            vendor: Phone vendor (e.g., 'yealink', 'polycom')
            model: Phone model (e.g., 't46s', 'vvx450')
            template_content: Template string with placeholders
        """
        self.vendor = vendor.lower()
        self.model = model.lower()
        self.template_content = template_content
    
    def generate_config(self, extension_config, server_config):
        """
        Generate configuration from template
        
        Args:
            extension_config: Extension configuration dict
            server_config: Server configuration dict
            
        Returns:
            Generated configuration string
        """
        # Replace placeholders in template
        config = self.template_content
        
        # Extension information
        config = config.replace('{{EXTENSION_NUMBER}}', str(extension_config.get('number', '')))
        config = config.replace('{{EXTENSION_NAME}}', str(extension_config.get('name', '')))
        config = config.replace('{{EXTENSION_PASSWORD}}', str(extension_config.get('password', '')))
        
        # Server information
        config = config.replace('{{SIP_SERVER}}', str(server_config.get('sip_host', '')))
        config = config.replace('{{SIP_PORT}}', str(server_config.get('sip_port', '5060')))
        config = config.replace('{{SERVER_NAME}}', str(server_config.get('server_name', 'PBX')))
        
        return config


def normalize_mac_address(mac):
    """
    Normalize MAC address to consistent format
    
    Args:
        mac: MAC address in various formats
        
    Returns:
        Normalized MAC (lowercase, no separators)
    """
    # Remove common separators
    normalized = mac.lower().replace(':', '').replace('-', '').replace('.', '')
    return normalized


class ProvisioningDevice:
    """Represents a provisioned phone device"""
    
    def __init__(self, mac_address, extension_number, vendor, model, config_url=None):
        """
        Initialize provisioning device
        
        Args:
            mac_address: Device MAC address (normalized format)
            extension_number: Associated extension number
            vendor: Phone vendor
            model: Phone model
            config_url: URL where config can be fetched
        """
        self.mac_address = normalize_mac_address(mac_address)
        self.extension_number = extension_number
        self.vendor = vendor.lower()
        self.model = model.lower()
        self.config_url = config_url
        self.created_at = datetime.now()
        self.last_provisioned = None
    
    def mark_provisioned(self):
        """Mark device as provisioned"""
        self.last_provisioned = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'mac_address': self.mac_address,
            'extension_number': self.extension_number,
            'vendor': self.vendor,
            'model': self.model,
            'config_url': self.config_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_provisioned': self.last_provisioned.isoformat() if self.last_provisioned else None
        }


class PhoneProvisioning:
    """Phone provisioning management"""
    
    def __init__(self, config):
        """
        Initialize phone provisioning
        
        Args:
            config: Config object
        """
        self.config = config
        self.logger = get_logger()
        self.devices = {}  # MAC address -> ProvisioningDevice
        self.templates = {}  # (vendor, model) -> PhoneTemplate
        
        # Initialize built-in templates
        self._load_builtin_templates()
        
        # Load custom templates if configured
        self._load_custom_templates()
        
        self.logger.info("Phone provisioning initialized")
    
    def _load_builtin_templates(self):
        """Load built-in phone templates"""
        
        # ZIP 33G template (basic SIP phone)
        zip_33g_template = """# ZIP 33G Configuration File

# SIP Account Configuration
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server_host = {{SIP_SERVER}}
account.1.sip_server_port = {{SIP_PORT}}
account.1.reg_interval = 3600

# Audio Codecs
audio.codec.1 = PCMU
audio.codec.2 = PCMA
audio.codec.3 = G729

# Network Settings
network.dhcp = 1

# Time Zone
time.timezone = GMT-8

# Basic Phone Settings
phone.volume.ring = 8
phone.volume.handset = 6
"""
        self.add_template('zip', '33g', zip_33g_template)
        
        # ZIP 37G template (advanced SIP phone with more features)
        zip_37g_template = """# ZIP 37G Configuration File

# SIP Account Configuration
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server_host = {{SIP_SERVER}}
account.1.sip_server_port = {{SIP_PORT}}
account.1.reg_interval = 3600
account.1.outbound_proxy = 
account.1.transport = UDP

# Audio Codecs
audio.codec.1 = PCMU
audio.codec.2 = PCMA
audio.codec.3 = G729

# Network Settings
network.dhcp = 1
network.vlan.enable = 0

# Time Zone
time.timezone = GMT-8
time.ntp_server = pool.ntp.org

# Phone Features
phone.volume.ring = 8
phone.volume.handset = 6
phone.backlight.timeout = 60
phone.screensaver.enable = 1

# Call Features
call.hold_music = 1
call.call_waiting = 1
call.transfer.enable = 1

# Advanced Settings
security.user_password = admin
"""
        self.add_template('zip', '37g', zip_37g_template)
        
        self.logger.info(f"Loaded {len(self.templates)} built-in phone templates")
    
    def _load_custom_templates(self):
        """Load custom templates from configuration"""
        custom_templates_dir = self.config.get('provisioning.custom_templates_dir', None)
        
        if custom_templates_dir and os.path.exists(custom_templates_dir):
            try:
                for filename in os.listdir(custom_templates_dir):
                    if filename.endswith('.template'):
                        filepath = os.path.join(custom_templates_dir, filename)
                        # Parse filename: vendor_model.template
                        parts = filename.replace('.template', '').split('_')
                        if len(parts) >= 2:
                            vendor = parts[0]
                            model = '_'.join(parts[1:])
                            
                            with open(filepath, 'r') as f:
                                template_content = f.read()
                            
                            self.add_template(vendor, model, template_content)
                            self.logger.info(f"Loaded custom template for {vendor} {model}")
            except Exception as e:
                self.logger.error(f"Error loading custom templates: {e}")
    
    def add_template(self, vendor, model, template_content):
        """
        Add a phone template
        
        Args:
            vendor: Phone vendor
            model: Phone model
            template_content: Template string
        """
        key = (vendor.lower(), model.lower())
        self.templates[key] = PhoneTemplate(vendor, model, template_content)
    
    def get_template(self, vendor, model):
        """
        Get phone template
        
        Args:
            vendor: Phone vendor
            model: Phone model
            
        Returns:
            PhoneTemplate or None
        """
        key = (vendor.lower(), model.lower())
        return self.templates.get(key)
    
    def register_device(self, mac_address, extension_number, vendor, model):
        """
        Register a device for provisioning
        
        Args:
            mac_address: Device MAC address
            extension_number: Associated extension number
            vendor: Phone vendor
            model: Phone model
            
        Returns:
            ProvisioningDevice
        """
        device = ProvisioningDevice(mac_address, extension_number, vendor, model)
        
        # Generate config URL based on MAC
        provisioning_url_format = self.config.get('provisioning.url_format', 
                                                  'http://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg')
        config_url = provisioning_url_format.replace('{mac}', device.mac_address)
        config_url = config_url.replace('{{SERVER_IP}}', 
                                       self.config.get('server.external_ip', '127.0.0.1'))
        config_url = config_url.replace('{{PORT}}', 
                                       str(self.config.get('api.port', '8080')))
        
        device.config_url = config_url
        self.devices[device.mac_address] = device
        
        self.logger.info(f"Registered device {mac_address} for extension {extension_number}")
        return device
    
    def unregister_device(self, mac_address):
        """
        Unregister a device
        
        Args:
            mac_address: Device MAC address
            
        Returns:
            bool: True if device was found and removed
        """
        normalized_mac = normalize_mac_address(mac_address)
        
        if normalized_mac in self.devices:
            del self.devices[normalized_mac]
            self.logger.info(f"Unregistered device {mac_address}")
            return True
        return False
    
    def get_device(self, mac_address):
        """
        Get device by MAC address
        
        Args:
            mac_address: Device MAC address
            
        Returns:
            ProvisioningDevice or None
        """
        normalized_mac = normalize_mac_address(mac_address)
        return self.devices.get(normalized_mac)
    
    def get_all_devices(self):
        """
        Get all registered devices
        
        Returns:
            List of ProvisioningDevice objects
        """
        return list(self.devices.values())
    
    def generate_config(self, mac_address, extension_registry):
        """
        Generate configuration for a device
        
        Args:
            mac_address: Device MAC address
            extension_registry: ExtensionRegistry instance
            
        Returns:
            tuple: (config_string, content_type) or (None, None)
        """
        device = self.get_device(mac_address)
        if not device:
            self.logger.warning(f"Device {mac_address} not found for provisioning")
            return None, None
        
        # Get template
        template = self.get_template(device.vendor, device.model)
        if not template:
            self.logger.warning(f"Template not found for {device.vendor} {device.model}")
            return None, None
        
        # Get extension configuration
        extension = extension_registry.get(device.extension_number)
        if not extension:
            self.logger.warning(f"Extension {device.extension_number} not found")
            return None, None
        
        # Build extension config dict
        extension_config = {
            'number': extension.number,
            'name': extension.name,
            'password': extension.config.get('password', '')
        }
        
        # Build server config dict
        server_config = {
            'sip_host': self.config.get('server.external_ip', '127.0.0.1'),
            'sip_port': self.config.get('server.sip_port', 5060),
            'server_name': self.config.get('server.server_name', 'PBX')
        }
        
        # Generate configuration
        config_content = template.generate_config(extension_config, server_config)
        
        # Determine content type based on vendor
        content_type = 'text/plain'
        if device.vendor == 'zip':
            content_type = 'text/plain'
        
        # Mark device as provisioned
        device.mark_provisioned()
        
        self.logger.info(f"Generated config for device {mac_address}")
        return config_content, content_type
    
    def get_supported_vendors(self):
        """
        Get list of supported vendors
        
        Returns:
            List of vendor names
        """
        vendors = set()
        for vendor, model in self.templates.keys():
            vendors.add(vendor)
        return sorted(list(vendors))
    
    def get_supported_models(self, vendor=None):
        """
        Get list of supported models
        
        Args:
            vendor: Optional vendor filter
            
        Returns:
            List of models or dict of vendor -> models
        """
        if vendor:
            models = []
            vendor = vendor.lower()
            for v, m in self.templates.keys():
                if v == vendor:
                    models.append(m)
            return sorted(models)
        else:
            # Return dict of vendor -> models
            result = {}
            for v, m in self.templates.keys():
                if v not in result:
                    result[v] = []
                result[v].append(m)
            # Sort each vendor's models
            for v in result:
                result[v] = sorted(result[v])
            return result
