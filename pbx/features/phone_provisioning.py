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
        self.mac_address = self._normalize_mac(mac_address)
        self.extension_number = extension_number
        self.vendor = vendor.lower()
        self.model = model.lower()
        self.config_url = config_url
        self.created_at = datetime.now()
        self.last_provisioned = None
    
    def _normalize_mac(self, mac):
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
        
        # Yealink T4x series template
        yealink_t4x_template = """#!version:1.0.0.1

# Account configuration
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600

# Codec settings
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = PCMU
account.1.codec.2.enable = 1
account.1.codec.2.payload_type = PCMA
account.1.codec.3.enable = 0

# Local settings
local_time.time_zone = -8
local_time.time_zone_name = US-Pacific

# Phone settings
phone_setting.backlight_time = 60
phone_setting.ring_type = Ring1.wav
"""
        self.add_template('yealink', 't46s', yealink_t4x_template)
        self.add_template('yealink', 't48s', yealink_t4x_template)
        self.add_template('yealink', 't42s', yealink_t4x_template)
        
        # Polycom VVX series template
        polycom_vvx_template = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<PHONE_CONFIG>
    <ALL>
        <!-- Registration -->
        <reg reg.1.displayName="{{EXTENSION_NAME}}" 
             reg.1.address="{{EXTENSION_NUMBER}}" 
             reg.1.auth.userId="{{EXTENSION_NUMBER}}"
             reg.1.auth.password="{{EXTENSION_PASSWORD}}"
             reg.1.server.1.address="{{SIP_SERVER}}"
             reg.1.server.1.port="{{SIP_PORT}}"
             reg.1.server.1.expires="3600"/>
        
        <!-- Codec Configuration -->
        <voice voice.codecPref.G711_Mu="1"
               voice.codecPref.G711_A="2"
               voice.codecPref.G729_AB="0"/>
        
        <!-- Time Settings -->
        <tcpIpApp tcpIpApp.sntp.gmtOffset="-28800"/>
        
        <!-- Call Settings -->
        <call call.hold.localReminder.enabled="1"
              call.callsPerLineKey="1"/>
    </ALL>
</PHONE_CONFIG>
"""
        self.add_template('polycom', 'vvx450', polycom_vvx_template)
        self.add_template('polycom', 'vvx350', polycom_vvx_template)
        self.add_template('polycom', 'vvx250', polycom_vvx_template)
        
        # Cisco SPA series template
        cisco_spa_template = """<flat-profile>
<Line_1_>
  <Display_Name_1_ ua="na">{{EXTENSION_NAME}}</Display_Name_1_>
  <User_ID_1_ ua="na">{{EXTENSION_NUMBER}}</User_ID_1_>
  <Password_1_ ua="na">{{EXTENSION_PASSWORD}}</Password_1_>
  <Authentication_ID_1_ ua="na">{{EXTENSION_NUMBER}}</Authentication_ID_1_>
  <Proxy_1_ ua="na">{{SIP_SERVER}}</Proxy_1_>
  <Register_1_ ua="na">Yes</Register_1_>
  <Register_Expires_1_ ua="na">3600</Register_Expires_1_>
</Line_1_>

<Provisioning>
  <Profile_Rule ua="na"></Profile_Rule>
  <Resync_On_Reset ua="na">Yes</Resync_On_Reset>
</Provisioning>

<Regional>
  <Time_Zone ua="na">GMT-08:00</Time_Zone>
</Regional>

<Attended_Transfer ua="na">Yes</Attended_Transfer>
<Blind_Transfer ua="na">Yes</Blind_Transfer>
</flat-profile>
"""
        self.add_template('cisco', 'spa504g', cisco_spa_template)
        self.add_template('cisco', 'spa525g', cisco_spa_template)
        
        # Grandstream GXP series template
        grandstream_gxp_template = """# Grandstream Configuration File

# Account 1 Settings
P270 = {{EXTENSION_NUMBER}}
P271 = {{EXTENSION_NAME}}
P2 = {{SIP_SERVER}}
P4 = {{SIP_PORT}}
P34 = {{EXTENSION_NUMBER}}
P35 = {{EXTENSION_NUMBER}}
P36 = {{EXTENSION_PASSWORD}}
P401 = 1

# Codec Settings
P57 = 0  # PCMU
P58 = 8  # PCMA
P59 = 18 # G729

# Time Zone
P64 = -8

# Auto Answer
P298 = 0
"""
        self.add_template('grandstream', 'gxp2160', grandstream_gxp_template)
        self.add_template('grandstream', 'gxp2140', grandstream_gxp_template)
        self.add_template('grandstream', 'gxp1628', grandstream_gxp_template)
        
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
        device = ProvisioningDevice(mac_address, '', '', '')  # Just to normalize MAC
        normalized_mac = device.mac_address
        
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
        device = ProvisioningDevice(mac_address, '', '', '')  # Just to normalize MAC
        normalized_mac = device.mac_address
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
        if device.vendor == 'polycom':
            content_type = 'application/xml'
        elif device.vendor in ['yealink', 'cisco', 'grandstream']:
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
