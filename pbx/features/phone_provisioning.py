"""
Phone Provisioning Module
Provides auto-configuration for IP phones (SIP phones)

Note: The system automatically triggers phone reboots when needed:
- After device registration (if extension is currently registered)
- After AD sync updates extension names
This ensures phones always fetch fresh configuration with updated settings.

Manual reboot options if needed:
- Power cycle phone or use phone menu
- API: POST /api/phones/reboot or POST /api/phones/{extension}/reboot
"""
import os
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
        self.provision_requests = []  # Track provisioning requests for troubleshooting
        self.max_request_history = 100  # Keep last 100 requests

        # Initialize built-in templates
        self._load_builtin_templates()

        # Load custom templates if configured
        self._load_custom_templates()

        self.logger.info("Phone provisioning initialized")
        self.logger.info(f"Provisioning URL format: {self.config.get('provisioning.url_format', 'Not configured')}")
        self.logger.info(f"Server external IP: {self.config.get('server.external_ip', 'Not configured')}")
        self.logger.info(f"API port: {self.config.get('api.port', 'Not configured')}")

    def _load_builtin_templates(self):
        """Load built-in phone templates"""

        # Zultys ZIP 33G template (basic SIP phone)
        zultys_zip33g_template = """# Zultys ZIP 33G Configuration File

# Auto Provision Settings
# These settings ensure the phone automatically applies configuration changes
auto_provision.power_on.enable = 1
auto_provision.repeat.enable = 1
auto_provision.repeat.minutes = 1440
auto_provision.mode = 1

# SIP Account Configuration
# Line Active
account.1.enable = 1
# Label
account.1.label = {{EXTENSION_NAME}}
# Display Name
account.1.display_name = {{EXTENSION_NAME}}
# Register Name
account.1.register_name = {{EXTENSION_NAME}}
# User Name
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
# Password
account.1.password = {{EXTENSION_PASSWORD}}
# SIP Server 1
account.1.sip_server_host = {{SIP_SERVER}}
account.1.sip_server_port = {{SIP_PORT}}
# Transport
account.1.transport = UDP
# Server Expires
account.1.reg_interval = 600
# Server Retry Counts
account.1.retry_counts = 3
# SIP Server 2
account.1.sip_server2_host = 
account.1.sip_server2_port = 5060
account.1.sip_server2_transport = UDP
account.1.sip_server2_expires = 3600
account.1.sip_server2_retry_counts = 3
# Enable Outbound Proxy Server
account.1.outbound_proxy_enable = 0
# Outbound Proxy Server 1
account.1.outbound_proxy_host = 
account.1.outbound_proxy_port = 5060
# Outbound Proxy Server 2
account.1.outbound_proxy2_host = 
account.1.outbound_proxy2_port = 5060
# Proxy Fallback Interval
account.1.proxy_fallback_interval = 3600
# NAT
account.1.nat.enable = 0

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
        self.add_template('zultys', 'zip33g', zultys_zip33g_template)

        # Zultys ZIP 37G template (advanced SIP phone with more features)
        zultys_zip37g_template = """# Zultys ZIP 37G Configuration File

# Auto Provision Settings
# These settings ensure the phone automatically applies configuration changes
auto_provision.power_on.enable = 1
auto_provision.repeat.enable = 1
auto_provision.repeat.minutes = 1440
auto_provision.mode = 1

# SIP Account Configuration
# Account Active
account.1.enable = 1
# Label
account.1.label = {{EXTENSION_NAME}}
# Name
account.1.name = {{EXTENSION_NAME}}
# Register Name
account.1.register_name = {{EXTENSION_NAME}}
# Display Name
account.1.display_name = {{EXTENSION_NAME}}
# User Name
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
# Password
account.1.password = {{EXTENSION_PASSWORD}}
# SIP Server
account.1.sip_server_host = {{SIP_SERVER}}
account.1.sip_server_port = {{SIP_PORT}}
# Login Expire (seconds)
account.1.reg_interval = 600
# Retry Max Count
account.1.retry_counts = 2
# Backup SIP Server
account.1.sip_server2_host = 
account.1.sip_server2_port = 5060
account.1.sip_server2_expires = 3600
account.1.sip_server2_retry_counts = 2
# Enable Outbound Proxy Server
account.1.outbound_proxy_enable = 0
# Outbound Proxy Server
account.1.outbound_proxy_host = 
account.1.outbound_proxy_port = 5060
# Transport
account.1.transport = UDP
# Backup Outbound Proxy Server
account.1.outbound_proxy2_host = 
account.1.outbound_proxy2_port = 5060
# NAT Traversal
account.1.nat.enable = 0
# STUN Server
account.1.stun_server = 
account.1.stun_port = 3478
# Voice Mail
account.1.voicemail = *1001
# Proxy Require
account.1.proxy_require = 
# Anonymous Call
account.1.anonymous_call = 0
account.1.anonymous_call_oncode = 
account.1.anonymous_call_offcode = 
# Anonymous Call Rejection
account.1.anonymous_call_rejection = 1
account.1.anonymous_call_rejection_oncode = 
account.1.anonymous_call_rejection_offcode = 
# Missed Call Log
account.1.missed_call_log = 1
# Auto Answer
account.1.auto_answer = 0
# XML Idle Screen
account.1.xml_idle_screen_enable = 0
account.1.xml_idle_screen_url = 
# Ring Tones
account.1.ring_tone = common

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
        self.add_template('zultys', 'zip37g', zultys_zip37g_template)

        # Yealink T46S template (popular business phone)
        yealink_t46s_template = """#!version:1.0.0.1

# Yealink T46S Configuration File

# Account 1
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600

# Codecs
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = PCMU
account.1.codec.2.enable = 1
account.1.codec.2.payload_type = PCMA
account.1.codec.3.enable = 1
account.1.codec.3.payload_type = G729

# Network
network.internet_port.type = 0
network.internet_port.dhcp = 1

# Time
local_time.time_zone = -8
local_time.ntp_server1 = pool.ntp.org
"""
        self.add_template('yealink', 't46s', yealink_t46s_template)

        # Polycom VVX 450 template
        polycom_vvx450_template = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!-- Polycom VVX 450 Configuration -->
<polycomConfig>
  <reg reg.1.displayName="{{EXTENSION_NAME}}"
       reg.1.address="{{EXTENSION_NUMBER}}"
       reg.1.auth.userId="{{EXTENSION_NUMBER}}"
       reg.1.auth.password="{{EXTENSION_PASSWORD}}"
       reg.1.server.1.address="{{SIP_SERVER}}"
       reg.1.server.1.port="{{SIP_PORT}}"
       reg.1.server.1.expires="3600"/>
  
  <voice voice.codecPref.G711_Mu="1"
         voice.codecPref.G711_A="2"
         voice.codecPref.G729_AB="3"/>
  
  <tcpIpApp tcpIpApp.sntp.address="pool.ntp.org"
            tcpIpApp.sntp.gmtOffset="-28800"/>
</polycomConfig>
"""
        self.add_template('polycom', 'vvx450', polycom_vvx450_template)

        # Cisco SPA504G template
        cisco_spa504g_template = """# Cisco SPA504G Configuration

# Line 1
Line_Enable_1_ : Yes
Display_Name_1_ : {{EXTENSION_NAME}}
User_ID_1_ : {{EXTENSION_NUMBER}}
Password_1_ : {{EXTENSION_PASSWORD}}
Proxy_1_ : {{SIP_SERVER}}
Register_Expires_1_ : 3600

# Codecs
Preferred_Codec_1_ : G711u
Preferred_Codec_2_ : G711a
Preferred_Codec_3_ : G729a

# Network
Internet_Connection_Type : DHCP

# Regional
Time_Zone : GMT-08:00
Primary_NTP_Server : pool.ntp.org
"""
        self.add_template('cisco', 'spa504g', cisco_spa504g_template)

        # Grandstream GXP2170 template
        grandstream_gxp2170_template = """# Grandstream GXP2170 Configuration

# Account 1
P270 = {{EXTENSION_NUMBER}}
P271 = {{EXTENSION_NAME}}
P35 = {{EXTENSION_NUMBER}}
P34 = {{EXTENSION_PASSWORD}}
P47 = {{SIP_SERVER}}
P48 = {{SIP_PORT}}
P2 = 3600

# Codecs
P57 = 0    # PCMU
P58 = 8    # PCMA
P46 = 18   # G729

# Network
P8 = 0     # DHCP enabled

# Time
P64 = pool.ntp.org
P30 = 13   # GMT-8
"""
        self.add_template('grandstream', 'gxp2170', grandstream_gxp2170_template)

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

    def generate_config(self, mac_address, extension_registry, request_info=None):
        """
        Generate configuration for a device

        Args:
            mac_address: Device MAC address
            extension_registry: ExtensionRegistry instance
            request_info: Optional dict with request details (ip, user_agent, etc.)

        Returns:
            tuple: (config_string, content_type) or (None, None)
        """
        # Log the provisioning request for troubleshooting
        request_log = {
            'timestamp': datetime.now().isoformat(),
            'mac_address': mac_address,
            'normalized_mac': normalize_mac_address(mac_address),
            'ip_address': request_info.get('ip') if request_info else None,
            'user_agent': request_info.get('user_agent') if request_info else None,
            'success': False,
            'error': None
        }
        
        self.logger.info(f"Provisioning request received for MAC: {mac_address}")
        if request_info:
            self.logger.info(f"  Request from IP: {request_info.get('ip', 'Unknown')}")
            self.logger.info(f"  User-Agent: {request_info.get('user_agent', 'Unknown')}")
        
        device = self.get_device(mac_address)
        if not device:
            normalized = normalize_mac_address(mac_address)
            error_msg = f"Device {mac_address} not registered in provisioning system"
            self.logger.warning(error_msg)
            self.logger.warning(f"  Normalized MAC: {normalized}")
            self.logger.warning(f"  Registered devices: {list(self.devices.keys())}")
            
            # Provide helpful guidance
            self.logger.warning(f"  → Device needs to be registered first")
            self.logger.warning(f"  → Register via API: POST /api/provisioning/devices")
            self.logger.warning(f"  → Example:")
            self.logger.warning(f"     curl -X POST http://YOUR_PBX_IP:8080/api/provisioning/devices \\")
            self.logger.warning(f"       -H 'Content-Type: application/json' \\")
            self.logger.warning(f"       -d '{{\"mac_address\":\"{mac_address}\",\"extension_number\":\"XXXX\",\"vendor\":\"VENDOR\",\"model\":\"MODEL\"}}'")
            self.logger.warning(f"  → Available vendors: yealink, polycom, cisco, grandstream, zultys")
            
            # Check if there are similar MACs (might be a format issue)
            mac_prefix = normalized[:6]  # First 6 chars (OUI)
            similar_macs = [m for m in self.devices.keys() if m.startswith(mac_prefix)]
            if similar_macs:
                self.logger.warning(f"  → Similar MACs found (same vendor): {similar_macs}")
                self.logger.warning(f"     This might be a typo in the MAC address")
            
            request_log['error'] = error_msg
            self._add_request_log(request_log)
            return None, None

        self.logger.info(f"  Found device: vendor={device.vendor}, model={device.model}, extension={device.extension_number}")
        
        # Get template
        template = self.get_template(device.vendor, device.model)
        if not template:
            error_msg = f"Template not found for {device.vendor} {device.model}"
            self.logger.warning(error_msg)
            self.logger.warning(f"  Available templates: {list(self.templates.keys())}")
            request_log['error'] = error_msg
            self._add_request_log(request_log)
            return None, None

        # Get extension configuration
        extension = extension_registry.get(device.extension_number)
        if not extension:
            error_msg = f"Extension {device.extension_number} not found"
            self.logger.warning(error_msg)
            self.logger.warning(f"  Available extensions: {[e.number for e in extension_registry.get_all()]}")
            request_log['error'] = error_msg
            self._add_request_log(request_log)
            return None, None

        self.logger.info(f"  Extension found: {extension.number} ({extension.name})")
        
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

        self.logger.info(f"  Server config: SIP={server_config['sip_host']}:{server_config['sip_port']}")
        
        # Generate configuration
        config_content = template.generate_config(extension_config, server_config)

        # Determine content type based on vendor
        # Mapping of vendors to their content types
        vendor_content_types = {
            'polycom': 'application/xml',
        }
        content_type = vendor_content_types.get(device.vendor, 'text/plain')

        # Mark device as provisioned
        device.mark_provisioned()

        self.logger.info(f"✓ Successfully generated config for device {mac_address}")
        self.logger.info(f"  Config size: {len(config_content)} bytes, Content-Type: {content_type}")
        
        request_log['success'] = True
        request_log['vendor'] = device.vendor
        request_log['model'] = device.model
        request_log['extension'] = device.extension_number
        request_log['config_size'] = len(config_content)
        self._add_request_log(request_log)
        
        return config_content, content_type
    
    def _add_request_log(self, request_log):
        """Add request to history, keeping only recent requests"""
        self.provision_requests.append(request_log)
        # Keep only the last N requests
        if len(self.provision_requests) > self.max_request_history:
            self.provision_requests = self.provision_requests[-self.max_request_history:]
    
    def get_request_history(self, limit=None):
        """
        Get provisioning request history
        
        Args:
            limit: Optional limit on number of requests to return
            
        Returns:
            List of request log dicts
        """
        if limit:
            return self.provision_requests[-limit:]
        return self.provision_requests

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

    def reboot_phone(self, extension_number, sip_server):
        """
        Send SIP NOTIFY to reboot a phone

        Args:
            extension_number: Extension number
            sip_server: SIPServer instance to send NOTIFY

        Returns:
            bool: True if NOTIFY was sent successfully
        """
        from pbx.sip.message import SIPMessageBuilder

        # Find the extension to get its registered address
        extension = sip_server.pbx_core.extension_registry.get(extension_number)
        if not extension or not extension.registered or not extension.address:
            self.logger.warning(f"Extension {extension_number} not registered, cannot reboot phone")
            return False

        try:
            # Build SIP NOTIFY for check-sync event (triggers phone reboot/config reload)
            server_ip = sip_server.pbx_core.config.get('server.external_ip', '127.0.0.1')
            sip_port = sip_server.pbx_core.config.get('server.sip_port', 5060)

            notify_msg = SIPMessageBuilder.build_request(
                method='NOTIFY',
                uri=f"sip:{extension_number}@{extension.address[0]}:{extension.address[1]}",
                from_addr=f"<sip:{server_ip}:{sip_port}>",
                to_addr=f"<sip:{extension_number}@{server_ip}>",
                call_id=f"notify-reboot-{extension_number}-{datetime.now().timestamp()}",
                cseq=1
            )

            # Add NOTIFY-specific headers
            notify_msg.set_header('Event', 'check-sync')
            notify_msg.set_header('Subscription-State', 'terminated')
            notify_msg.set_header('Content-Length', '0')

            # Send the NOTIFY message
            sip_server._send_message(notify_msg.build(), extension.address)

            self.logger.info(f"Sent reboot NOTIFY to extension {extension_number} at {extension.address}")
            return True

        except Exception as e:
            self.logger.error(f"Error sending reboot NOTIFY to extension {extension_number}: {e}")
            return False

    def reboot_all_phones(self, sip_server):
        """
        Send SIP NOTIFY to reboot all registered phones

        Args:
            sip_server: SIPServer instance to send NOTIFY

        Returns:
            dict: Results with success count and list of extensions
        """
        results = {
            'success_count': 0,
            'failed_count': 0,
            'rebooted': [],
            'failed': []
        }

        # Get all registered extensions
        extensions = sip_server.pbx_core.extension_registry.get_all()

        for extension in extensions:
            if extension.registered:
                if self.reboot_phone(extension.number, sip_server):
                    results['success_count'] += 1
                    results['rebooted'].append(extension.number)
                else:
                    results['failed_count'] += 1
                    results['failed'].append(extension.number)

        self.logger.info(f"Rebooted {results['success_count']} phones, {results['failed_count']} failed")
        return results
    
    def list_all_templates(self):
        """
        List all available templates (both built-in and custom)
        
        Returns:
            List of dicts with template information
        """
        templates_list = []
        for (vendor, model), template in self.templates.items():
            # Check if template is customized (exists in custom dir)
            is_custom = False
            custom_dir = self.config.get('provisioning.custom_templates_dir', 'provisioning_templates')
            template_filename = f"{vendor}_{model}.template"
            template_path = os.path.join(custom_dir, template_filename)
            
            if os.path.exists(template_path):
                is_custom = True
            
            templates_list.append({
                'vendor': vendor,
                'model': model,
                'is_custom': is_custom,
                'template_path': template_path if is_custom else 'built-in',
                'size': len(template.template_content)
            })
        
        return sorted(templates_list, key=lambda x: (x['vendor'], x['model']))
    
    def get_template_content(self, vendor, model):
        """
        Get the content of a specific template
        
        Args:
            vendor: Phone vendor
            model: Phone model
            
        Returns:
            Template content string or None
        """
        template = self.get_template(vendor, model)
        if template:
            return template.template_content
        return None
    
    def export_template_to_file(self, vendor, model):
        """
        Export a template to the custom templates directory
        
        Args:
            vendor: Phone vendor
            model: Phone model
            
        Returns:
            tuple: (success, message, filepath)
        """
        # Validate vendor and model to prevent path traversal
        import re
        if not re.match(r'^[a-z0-9_-]+$', vendor.lower()) or not re.match(r'^[a-z0-9_-]+$', model.lower()):
            return False, "Invalid vendor or model name. Only alphanumeric, underscore, and hyphen allowed.", None
        
        template = self.get_template(vendor, model)
        if not template:
            return False, f"Template not found for {vendor} {model}", None
        
        # Get custom templates directory
        custom_dir = self.config.get('provisioning.custom_templates_dir', 'provisioning_templates')
        
        # Create directory if it doesn't exist
        if not os.path.exists(custom_dir):
            try:
                os.makedirs(custom_dir)
                self.logger.info(f"Created custom templates directory: {custom_dir}")
            except Exception as e:
                return False, f"Failed to create directory: {e}", None
        
        # Write template to file
        template_filename = f"{vendor.lower()}_{model.lower()}.template"
        template_path = os.path.join(custom_dir, template_filename)
        
        try:
            with open(template_path, 'w') as f:
                f.write(template.template_content)
            
            self.logger.info(f"Exported template to: {template_path}")
            return True, f"Template exported to {template_path}", template_path
        except Exception as e:
            self.logger.error(f"Failed to export template: {e}")
            return False, f"Failed to export template: {e}", None
    
    def update_template(self, vendor, model, content):
        """
        Update a template with new content
        
        Args:
            vendor: Phone vendor
            model: Phone model
            content: New template content
            
        Returns:
            tuple: (success, message)
        """
        # Validate vendor and model to prevent path traversal
        import re
        if not re.match(r'^[a-z0-9_-]+$', vendor.lower()) or not re.match(r'^[a-z0-9_-]+$', model.lower()):
            return False, "Invalid vendor or model name. Only alphanumeric, underscore, and hyphen allowed."
        
        # Get custom templates directory
        custom_dir = self.config.get('provisioning.custom_templates_dir', 'provisioning_templates')
        
        # Create directory if it doesn't exist
        if not os.path.exists(custom_dir):
            try:
                os.makedirs(custom_dir)
            except Exception as e:
                return False, f"Failed to create directory: {e}"
        
        # Write template to file
        template_filename = f"{vendor.lower()}_{model.lower()}.template"
        template_path = os.path.join(custom_dir, template_filename)
        
        try:
            with open(template_path, 'w') as f:
                f.write(content)
            
            # Update in memory
            self.add_template(vendor, model, content)
            
            self.logger.info(f"Updated template: {vendor} {model}")
            return True, f"Template updated successfully"
        except Exception as e:
            self.logger.error(f"Failed to update template: {e}")
            return False, f"Failed to update template: {e}"
    
    def reload_templates(self):
        """
        Reload all templates from disk
        
        Returns:
            tuple: (success, message, stats)
        """
        try:
            # Clear existing templates
            self.templates.clear()
            
            # Reload built-in templates
            self._load_builtin_templates()
            
            # Reload custom templates (these will override built-ins)
            self._load_custom_templates()
            
            stats = {
                'total_templates': len(self.templates),
                'vendors': len(self.get_supported_vendors())
            }
            
            self.logger.info(f"Reloaded {stats['total_templates']} templates")
            return True, "Templates reloaded successfully", stats
        except Exception as e:
            self.logger.error(f"Failed to reload templates: {e}")
            return False, f"Failed to reload templates: {e}", None
