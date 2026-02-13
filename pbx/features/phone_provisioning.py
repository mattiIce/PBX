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
from datetime import datetime, timezone

from pbx.utils.device_types import detect_device_type
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
        config = config.replace("{{EXTENSION_NUMBER}}", str(extension_config.get("number", "")))
        config = config.replace("{{EXTENSION_NAME}}", str(extension_config.get("name", "")))
        config = config.replace("{{EXTENSION_PASSWORD}}", str(extension_config.get("password", "")))

        # Server information
        config = config.replace("{{SIP_SERVER}}", str(server_config.get("sip_host", "")))
        config = config.replace("{{SIP_PORT}}", str(server_config.get("sip_port", "5060")))
        config = config.replace("{{SERVER_NAME}}", str(server_config.get("server_name", "PBX")))

        # LDAP/LDAPS Phone Book Configuration
        ldap_config = server_config.get("ldap_phonebook", {})
        config = config.replace("{{LDAP_ENABLE}}", str(ldap_config.get("enable", "0")))
        config = config.replace("{{LDAP_SERVER}}", str(ldap_config.get("server", "")))
        config = config.replace("{{LDAP_PORT}}", str(ldap_config.get("port", "636")))
        config = config.replace("{{LDAP_BASE}}", str(ldap_config.get("base", "")))
        config = config.replace("{{LDAP_USER}}", str(ldap_config.get("user", "")))
        config = config.replace("{{LDAP_PASSWORD}}", str(ldap_config.get("password", "")))
        config = config.replace("{{LDAP_VERSION}}", str(ldap_config.get("version", "3")))
        config = config.replace("{{LDAP_TLS_MODE}}", str(ldap_config.get("tls_mode", "1")))
        config = config.replace(
            "{{LDAP_NAME_FILTER}}", str(ldap_config.get("name_filter", "(|(cn=%)(sn=%))"))
        )
        config = config.replace(
            "{{LDAP_NUMBER_FILTER}}",
            str(ldap_config.get("number_filter", "(|(telephoneNumber=%)(mobile=%))")),
        )
        config = config.replace("{{LDAP_NAME_ATTR}}", str(ldap_config.get("name_attr", "cn")))
        config = config.replace(
            "{{LDAP_NUMBER_ATTR}}", str(ldap_config.get("number_attr", "telephoneNumber"))
        )
        config = config.replace(
            "{{LDAP_DISPLAY_NAME}}", str(ldap_config.get("display_name", "Company Directory"))
        )

        # Remote Phone Book URL (fallback method)
        remote_phonebook = server_config.get("remote_phonebook", {})
        config = config.replace("{{REMOTE_PHONEBOOK_URL}}", str(remote_phonebook.get("url", "")))
        config = config.replace(
            "{{REMOTE_PHONEBOOK_REFRESH}}", str(remote_phonebook.get("refresh_interval", "60"))
        )

        # DTMF Configuration
        dtmf_config = server_config.get("dtmf", {})
        config = config.replace(
            "{{DTMF_PAYLOAD_TYPE}}", str(dtmf_config.get("payload_type", "101"))
        )

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
    normalized = mac.lower().replace(":", "").replace("-", "").replace(".", "")
    return normalized


class ProvisioningDevice:
    """Represents a provisioned phone device"""

    def __init__(
        self, mac_address, extension_number, vendor, model, device_type=None, config_url=None
    ):
        """
        Initialize provisioning device

        Args:
            mac_address: Device MAC address (normalized format)
            extension_number: Associated extension number
            vendor: Phone vendor
            model: Phone model
            device_type: Device type ('phone' or 'ata', auto-detected if None)
            config_url: URL where config can be fetched
        """
        self.mac_address = normalize_mac_address(mac_address)
        self.extension_number = extension_number
        self.vendor = vendor.lower()
        self.model = model.lower()
        # Auto-detect device type if not provided
        if device_type is None:
            self.device_type = self._detect_device_type(vendor, model)
        else:
            self.device_type = device_type
        self.config_url = config_url
        self.created_at = datetime.now(timezone.utc)
        self.last_provisioned = None

    def _detect_device_type(self, vendor: str, model: str) -> str:
        """
        Detect device type based on vendor and model

        Args:
            vendor: Device vendor
            model: Device model

        Returns:
            str: 'ata' or 'phone'
        """
        return detect_device_type(vendor, model)

    def is_ata(self) -> bool:
        """Check if device is an ATA"""
        return self.device_type == "ata"

    def mark_provisioned(self):
        """Mark device as provisioned"""
        self.last_provisioned = datetime.now(timezone.utc)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "mac_address": self.mac_address,
            "extension_number": self.extension_number,
            "vendor": self.vendor,
            "model": self.model,
            "device_type": self.device_type,
            "config_url": self.config_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_provisioned": (
                self.last_provisioned.isoformat() if self.last_provisioned else None
            ),
        }


class PhoneProvisioning:
    """Phone provisioning management"""

    def __init__(self, config, database=None):
        """
        Initialize phone provisioning

        Args:
            config: Config object
            database: Optional DatabaseBackend instance for persistent storage
        """
        self.config = config
        self.logger = get_logger()
        # MAC address -> ProvisioningDevice (in-memory cache)
        self.devices = {}
        self.templates = {}  # (vendor, model) -> PhoneTemplate
        self.provision_requests = []  # Track provisioning requests for troubleshooting
        self.max_request_history = 100  # Keep last 100 requests
        self.database = database
        self.devices_db = None

        # Initialize database access if available
        if database and database.enabled:
            from pbx.utils.database import ProvisionedDevicesDB

            self.devices_db = ProvisionedDevicesDB(database)
            self.logger.info("Phone provisioning will use database for persistent storage")
            # Load devices from database into memory
            self._load_devices_from_database()
        else:
            self.logger.info("Phone provisioning will use in-memory storage only")

        # Initialize built-in templates
        self._load_builtin_templates()

        # Load custom templates if configured
        self._load_custom_templates()

        self.logger.info("Phone provisioning initialized")
        self.logger.info(
            f"Provisioning URL format: {self.config.get('provisioning.url_format', 'Not configured')}"
        )
        self.logger.info(
            f"Server external IP: {self.config.get('server.external_ip', 'Not configured')}"
        )
        self.logger.info(
            f"API port: {self.config.get('api.port', 'Not configured')}"
        )

        # Check SSL status for provisioning URL generation
        ssl_enabled = self.config.get("api.ssl.enabled", False)
        if ssl_enabled:
            self.logger.warning(
                "SSL is enabled - phones may not be able to provision with self-signed certificates"
            )
            self.logger.warning(
                "Consider using HTTP for provisioning or obtaining trusted certificates"
            )
            self.logger.warning(
                "To use HTTP for provisioning: set provisioning.url_format to http://... in config.yml"
            )

    def _load_devices_from_database(self):
        """Load provisioned devices from database into memory"""
        if not self.devices_db:
            return

        try:
            db_devices = self.devices_db.list_all()
            for db_device in db_devices:
                device = ProvisioningDevice(
                    mac_address=db_device["mac_address"],
                    extension_number=db_device["extension_number"],
                    vendor=db_device["vendor"],
                    model=db_device["model"],
                    device_type=db_device.get("device_type"),  # Load device_type from DB
                )
                
                # Regenerate config_url to reflect current configuration
                # This ensures the URL uses the current api.port and server.external_ip
                # even if they changed since the device was originally registered
                device.config_url = self._generate_config_url(device.mac_address)
                
                # Restore timestamps if available
                if db_device.get("created_at"):
                    device.created_at = db_device["created_at"]
                if db_device.get("last_provisioned"):
                    device.last_provisioned = db_device["last_provisioned"]

                self.devices[device.mac_address] = device

            self.logger.info(
                f"Loaded {len(db_devices)} provisioned devices from database"
            )
        except Exception as e:
            self.logger.error(f"Error loading devices from database: {e}")

    def _load_builtin_templates(self):
        """Load built-in phone templates"""

        # Zultys ZIP 33G template (basic SIP phone)
        # Configuration based on working Yealink T28G settings
        zultys_zip33g_template = """#!version:1.0.0.1
# Zultys ZIP 33G Configuration File
# Generated by Warden Voip System
# Format: Flat config file (key = value)
# Based on working Yealink T28G configuration

# SIP Account Configuration
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}  # Use extension number for SIP authentication (matches T28G)
account.1.password = {{EXTENSION_PASSWORD}}

# SIP Server Configuration (Modern Format - firmware 47.80.132.4+)
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600

# Legacy SIP Server (for backward compatibility)
account.1.sip_server_host.legacy = {{SIP_SERVER}}

# Codecs - Priority: PCMU > PCMA > G722 (G.711 preferred for reliability)
# ZIP33G requires explicit codec parameters for proper audio
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = 0
account.1.codec.1.priority = 1
account.1.codec.1.name = PCMU
account.1.codec.1.sample_rate = 8000
account.1.codec.1.bitrate = 64
account.1.codec.1.ptime = 20

account.1.codec.2.enable = 1
account.1.codec.2.payload_type = 8
account.1.codec.2.priority = 2
account.1.codec.2.name = PCMA
account.1.codec.2.sample_rate = 8000
account.1.codec.2.bitrate = 64
account.1.codec.2.ptime = 20

account.1.codec.3.enable = 1
account.1.codec.3.payload_type = 9
account.1.codec.3.priority = 3
account.1.codec.3.name = G722
# Note: G722 is a wideband codec (16kHz). ZIP33G handles G722 parameters internally.

account.1.codec.4.enable = 0

# DTMF Settings - Using SIP INFO for reliable voicemail IVR (from T28G)
account.1.dtmf.type = 2          # 0=Inband, 1=RFC2833, 2=SIP INFO
account.1.dtmf.info_type = 0     # 0=DTMF, 1=DTMF-Relay
account.1.dtmf.dtmf_payload = 101  # Payload type for RFC2833

# Voicemail Configuration
# Note: Using *EXTENSION for direct voicemail access (e.g., *1501)
voice_mail.number.1 = *{{EXTENSION_NUMBER}}

# Account Features
account.1.missed_calllog = 1  # Enable missed call logging for better user experience
account.1.earlymedia = 1
account.1.nat.udp_update_time = 30
account.1.blf.subscribe_period = 3600

# Codec Configuration - disable unused codec slots
account.1.codec.5.enable = 0
account.1.codec.6.enable = 0
account.1.codec.6.priority = 0

# Network Settings
network.dhcp = 1
network.vlan.internet_port_priority = 5
network.lldp.enable = 0
network.lldp.packet_interval = 120

# Time Zone
local_time.time_zone = -5
local_time.time_zone_name = United States-Eastern Time
local_time.ntp_server1 = pool.ntp.org

# Voice/Ring Volume Settings
voice.ring_vol = 7
voice.handset.tone_vol = 11
voice.handfree.tone_vol = 15
voice.handfree.spk_vol = 15

# Phone Settings (redial/call return configuration)
phone_setting.redial_number = {{EXTENSION_NUMBER}}
phone_setting.redial_server = {{SIP_SERVER}}
phone_setting.call_return_user_name = {{EXTENSION_NUMBER}}
phone_setting.call_return_number = {{EXTENSION_NUMBER}}
phone_setting.call_return_server = {{SIP_SERVER}}

# Auto Provision Settings (Note: URL typically set via phone UI, not config file)
auto_provision.dhcp_option.list_user_options = %NULL%
auto_provision.dhcp_option.option60_value = 66

# ============================================================================
# Phone Book Configuration
# ============================================================================
# Two methods are supported for phone book access:
# 1. LDAPS - Direct LDAP/LDAPS server connection (Primary method)
# 2. Remote Phone Book URL - HTTP/HTTPS XML feed (Fallback method)

# LDAP/LDAPS Phone Book Configuration
# Enable LDAP directory lookup (0=disabled, 1=enabled)
ldap.enable = {{LDAP_ENABLE}}

# LDAP server address (hostname or IP)
ldap.server = {{LDAP_SERVER}}

# LDAP port (389 for LDAP, 636 for LDAPS)
ldap.port = {{LDAP_PORT}}

# Base DN for directory searches (e.g., dc=company,dc=com)
ldap.base = {{LDAP_BASE}}

# LDAP bind username (DN format, e.g., cn=phonebook,dc=company,dc=com)
ldap.user = {{LDAP_USER}}

# LDAP bind password
ldap.password = {{LDAP_PASSWORD}}

# LDAP version (typically 3)
ldap.version = {{LDAP_VERSION}}

# Enable SSL/TLS for secure LDAP (0=plain LDAP, 1=LDAPS/TLS)
ldap.tls_mode = {{LDAP_TLS_MODE}}

# LDAP search filters
# Name filter: Search by name (% is replaced with user input)
ldap.name_filter = {{LDAP_NAME_FILTER}}

# Number filter: Search by phone number
ldap.number_filter = {{LDAP_NUMBER_FILTER}}

# LDAP attribute mapping
ldap.name_attr = {{LDAP_NAME_ATTR}}
ldap.number_attr = {{LDAP_NUMBER_ATTR}}
ldap.display_name = {{LDAP_DISPLAY_NAME}}

# Remote Phone Book URL (Fallback method)
# URL to fetch XML phone book (leave empty if using LDAP only)
remote_phonebook.url = {{REMOTE_PHONEBOOK_URL}}

# Remote phone book refresh interval in minutes
remote_phonebook.refresh_interval = {{REMOTE_PHONEBOOK_REFRESH}}

# Line Key Configuration (extensible - customize as needed)
linekey.2.type = 15
linekey.2.line = 1
linekey.2.value = %NULL%
linekey.2.label = %NULL%
linekey.2.extension = %NULL%
linekey.2.xml_phonebook = 0
linekey.2.pickup_value = %NULL%

linekey.3.type = 15
linekey.3.line = 1
linekey.3.value = %NULL%
linekey.3.label = %NULL%
linekey.3.extension = %NULL%
linekey.3.xml_phonebook = 0
linekey.3.pickup_value = %NULL%
"""
        self.add_template("zultys", "zip33g", zultys_zip33g_template)

        # Zultys ZIP 37G template (advanced SIP phone)
        # NOTE: ZIP 37G can use the same flat .cfg format as ZIP 33G
        # Full ZIP 37G support with config.bin TAR archive is a future
        # enhancement
        zultys_zip37g_template = """#!version:1.0.0.1
# Zultys ZIP 37G Configuration File
# Generated by Warden Voip System
# Format: Flat config file (key = value)
# Note: ZIP 37G can accept flat .cfg format similar to ZIP 33G

# SIP Account Configuration
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NAME}}
account.1.password = {{EXTENSION_PASSWORD}}

# SIP Server Configuration (Modern Format - firmware 47.80.132.4+)
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.expires = 600

# Legacy SIP Server (for backward compatibility)
account.1.sip_server_host.legacy = {{SIP_SERVER}}

# Voicemail Configuration
# Note: Using *EXTENSION for direct voicemail access (e.g., *1501)
voice_mail.number.1 = *{{EXTENSION_NUMBER}}

# Account Features
account.1.missed_calllog = 0
account.1.earlymedia = 1
account.1.nat.udp_update_time = 21
account.1.blf.subscribe_period = 3600

# Codec Configuration - disable unused codec slot 6
account.1.codec.6.enable = 0
account.1.codec.6.priority = 0

# Network Settings
network.dhcp = 1
network.vlan.internet_port_priority = 5
network.lldp.enable = 0
network.lldp.packet_interval = 120

# Time Zone
local_time.time_zone = -5
local_time.time_zone_name = United States-Eastern Time
local_time.ntp_server1 = pool.ntp.org

# Voice/Ring Volume Settings
voice.ring_vol = 7
voice.handset.tone_vol = 11
voice.handfree.tone_vol = 15
voice.handfree.spk_vol = 15

# Phone Settings (redial/call return configuration)
phone_setting.redial_number = {{EXTENSION_NUMBER}}
phone_setting.redial_server = {{SIP_SERVER}}
phone_setting.call_return_user_name = {{EXTENSION_NUMBER}}
phone_setting.call_return_number = {{EXTENSION_NUMBER}}
phone_setting.call_return_server = {{SIP_SERVER}}

# Auto Provision Settings (Note: URL typically set via phone UI, not config file)
auto_provision.dhcp_option.list_user_options = %NULL%
auto_provision.dhcp_option.option60_value = 66

# ============================================================================
# Phone Book Configuration
# ============================================================================
# Two methods are supported for phone book access:
# 1. LDAPS - Direct LDAP/LDAPS server connection (Primary method)
# 2. Remote Phone Book URL - HTTP/HTTPS XML feed (Fallback method)

# LDAP/LDAPS Phone Book Configuration
# Enable LDAP directory lookup (0=disabled, 1=enabled)
ldap.enable = {{LDAP_ENABLE}}

# LDAP server address (hostname or IP)
ldap.server = {{LDAP_SERVER}}

# LDAP port (389 for LDAP, 636 for LDAPS)
ldap.port = {{LDAP_PORT}}

# Base DN for directory searches (e.g., dc=company,dc=com)
ldap.base = {{LDAP_BASE}}

# LDAP bind username (DN format, e.g., cn=phonebook,dc=company,dc=com)
ldap.user = {{LDAP_USER}}

# LDAP bind password
ldap.password = {{LDAP_PASSWORD}}

# LDAP version (typically 3)
ldap.version = {{LDAP_VERSION}}

# Enable SSL/TLS for secure LDAP (0=plain LDAP, 1=LDAPS/TLS)
ldap.tls_mode = {{LDAP_TLS_MODE}}

# LDAP search filters
# Name filter: Search by name (% is replaced with user input)
ldap.name_filter = {{LDAP_NAME_FILTER}}

# Number filter: Search by phone number
ldap.number_filter = {{LDAP_NUMBER_FILTER}}

# LDAP attribute mapping
ldap.name_attr = {{LDAP_NAME_ATTR}}
ldap.number_attr = {{LDAP_NUMBER_ATTR}}
ldap.display_name = {{LDAP_DISPLAY_NAME}}

# Remote Phone Book URL (Fallback method)
# URL to fetch XML phone book (leave empty if using LDAP only)
remote_phonebook.url = {{REMOTE_PHONEBOOK_URL}}

# Remote phone book refresh interval in minutes
remote_phonebook.refresh_interval = {{REMOTE_PHONEBOOK_REFRESH}}

# Line Key Configuration (extensible - customize as needed)
linekey.2.type = 15
linekey.2.line = 1
linekey.2.value = %NULL%
linekey.2.label = %NULL%
linekey.2.extension = %NULL%
linekey.2.xml_phonebook = 0
linekey.2.pickup_value = %NULL%

linekey.3.type = 15
linekey.3.line = 1
linekey.3.value = %NULL%
linekey.3.label = %NULL%
linekey.3.extension = %NULL%
linekey.3.xml_phonebook = 0
linekey.3.pickup_value = %NULL%
"""
        self.add_template("zultys", "zip37g", zultys_zip37g_template)

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
        self.add_template("yealink", "t46s", yealink_t46s_template)

        # Yealink T28G template (basic business phone)
        yealink_t28g_template = """#!version:1.0.0.1

# Yealink T28G Configuration File

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

# Codecs - Priority: PCMU > PCMA > G722 (G.711 preferred for reliability)
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = PCMU
account.1.codec.2.enable = 1
account.1.codec.2.payload_type = PCMA
account.1.codec.3.enable = 1
account.1.codec.3.payload_type = G722
account.1.codec.4.enable = 0

# DTMF Settings - Using SIP INFO for reliable voicemail IVR
account.1.dtmf.type = 2          # 0=Inband, 1=RFC2833, 2=SIP INFO
account.1.dtmf.info_type = 0     # 0=DTMF, 1=DTMF-Relay
account.1.dtmf.dtmf_payload = 101  # Payload type for RFC2833

# Network
network.internet_port.type = 0
network.internet_port.dhcp = 1

# Time
local_time.time_zone = -8
local_time.ntp_server1 = pool.ntp.org
"""
        self.add_template("yealink", "t28g", yealink_t28g_template)

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
        self.add_template("polycom", "vvx450", polycom_vvx450_template)

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
        self.add_template("cisco", "spa504g", cisco_spa504g_template)

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
        self.add_template("grandstream", "gxp2170", grandstream_gxp2170_template)

        # Grandstream HT801 (1-Port ATA) template
        grandstream_ht801_template = """# Grandstream HT801 (1-Port ATA) Configuration
# Single FXS port for connecting one analog phone or fax machine

# Basic Settings
P2 = admin
P196 = {{EXTENSION_NAME}}

# Network Settings
P8 = 0
P64 = pool.ntp.org
P30 = 13

# SIP Account 1 (FXS Port 1)
P271 = {{EXTENSION_NAME}}
P270 = {{EXTENSION_NUMBER}}
P35 = {{EXTENSION_NUMBER}}
P34 = {{EXTENSION_PASSWORD}}
P47 = {{SIP_SERVER}}
P48 = {{SIP_PORT}}
P2312 = 3600

# Codecs - Optimized for analog and fax
P57 = 0    # PCMU
P58 = 8    # PCMA
P46 = 18   # G729
P67 = 9    # G722

# DTMF Settings
P79 = 2
P184 = 0
P78 = {{DTMF_PAYLOAD_TYPE}}

# Analog-Specific / Caller ID Settings
P3 = 1      # Caller ID Scheme
P4 = 1      # Enable Caller ID display
P2311 = 2   # Offhook Auto-Dial
P240 = 2

# Echo Cancellation
P191 = 1
P192 = 0

# Fax Support - T.38
P245 = 1
P338 = 1
"""
        self.add_template("grandstream", "ht801", grandstream_ht801_template)

        # Grandstream HT802 (2-Port ATA) template
        grandstream_ht802_template = """# Grandstream HT802 (2-Port ATA) Configuration
# Two FXS ports for connecting two analog phones or fax machines

# Basic Settings
P2 = admin
P196 = {{EXTENSION_NAME}}

# Network Settings
P8 = 0
P64 = pool.ntp.org
P30 = 13

# SIP Account 1 (FXS Port 1)
P271 = {{EXTENSION_NAME}}
P270 = {{EXTENSION_NUMBER}}
P35 = {{EXTENSION_NUMBER}}
P34 = {{EXTENSION_PASSWORD}}
P47 = {{SIP_SERVER}}
P48 = {{SIP_PORT}}
P2312 = 3600

# Port 1 Codecs
P57 = 0    # PCMU
P58 = 8    # PCMA
P46 = 18   # G729
P67 = 9    # G722

# Port 1 DTMF Settings
P79 = 2
P184 = 0
P78 = {{DTMF_PAYLOAD_TYPE}}

# Port 1 Analog Settings
P3 = 1
P4 = 1
P2311 = 2   # Offhook Auto-Dial
P240 = 2

# Echo Cancellation
P191 = 1
P192 = 0

# Fax Support - T.38
P245 = 1
P338 = 1

# SIP Send Line and MAC Address Support
P2350 = 1
P2351 = 1
"""
        self.add_template("grandstream", "ht802", grandstream_ht802_template)

        # Cisco SPA112 (2-Port ATA) template
        cisco_spa112_template = """<flat-profile>
<Provision_Enable>No</Provision_Enable>
<Time_Zone>GMT-08:00</Time_Zone>
<NTP_Server>pool.ntp.org</NTP_Server>

<!-- Line 1 Configuration -->
<Line_Enable_1_>Yes</Line_Enable_1_>
<Display_Name_1_>{{EXTENSION_NAME}}</Display_Name_1_>
<User_ID_1_>{{EXTENSION_NUMBER}}</User_ID_1_>
<Auth_ID_1_>{{EXTENSION_NUMBER}}</Auth_ID_1_>
<Password_1_>{{EXTENSION_PASSWORD}}</Password_1_>
<Proxy_1_>{{SIP_SERVER}}</Proxy_1_>
<Register_1_>Yes</Register_1_>
<Register_Expires_1_>3600</Register_Expires_1_>

<!-- Codecs -->
<Preferred_Codec_1_>G711u</Preferred_Codec_1_>
<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>
<G711u_Enable_1_>Yes</G711u_Enable_1_>
<G711a_Enable_1_>Yes</G711a_Enable_1_>

<!-- DTMF -->
<DTMF_Tx_Method_1_>Auto</DTMF_Tx_Method_1_>

<!-- Fax - T.38 -->
<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>

<!-- Echo Cancellation -->
<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>

<!-- Line 2 Disabled by Default -->
<Line_Enable_2_>No</Line_Enable_2_>

<!-- Network -->
<Internet_Connection_Type>DHCP</Internet_Connection_Type>

<!-- SIP -->
<SIP_Port>{{SIP_PORT}}</SIP_Port>
<RTP_Port_Min>16384</RTP_Port_Min>
<RTP_Port_Max>16482</RTP_Port_Max>

<!-- Regional Settings -->
<FXS_Port_Impedance>600</FXS_Port_Impedance>
</flat-profile>
"""
        self.add_template("cisco", "spa112", cisco_spa112_template)

        # Cisco SPA122 (2-Port ATA with Router) template
        cisco_spa122_template = """<flat-profile>
<Provision_Enable>No</Provision_Enable>
<Time_Zone>GMT-08:00</Time_Zone>
<NTP_Server>pool.ntp.org</NTP_Server>

<!-- Line 1 Configuration -->
<Line_Enable_1_>Yes</Line_Enable_1_>
<Display_Name_1_>{{EXTENSION_NAME}}</Display_Name_1_>
<User_ID_1_>{{EXTENSION_NUMBER}}</User_ID_1_>
<Auth_ID_1_>{{EXTENSION_NUMBER}}</Auth_ID_1_>
<Password_1_>{{EXTENSION_PASSWORD}}</Password_1_>
<Proxy_1_>{{SIP_SERVER}}</Proxy_1_>
<Register_1_>Yes</Register_1_>
<Register_Expires_1_>3600</Register_Expires_1_>

<!-- Codecs -->
<Preferred_Codec_1_>G711u</Preferred_Codec_1_>
<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>
<G711u_Enable_1_>Yes</G711u_Enable_1_>
<G711a_Enable_1_>Yes</G711a_Enable_1_>

<!-- DTMF -->
<DTMF_Tx_Method_1_>Auto</DTMF_Tx_Method_1_>

<!-- Fax - T.38 -->
<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>

<!-- Echo Cancellation -->
<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>

<!-- Line 2 Disabled by Default -->
<Line_Enable_2_>No</Line_Enable_2_>

<!-- Router Settings -->
<WAN_Connection_Type>DHCP</WAN_Connection_Type>
<Router_Enable>Yes</Router_Enable>
<LAN_IP_Address>192.168.0.1</LAN_IP_Address>
<DHCP_Server_Enable>Yes</DHCP_Server_Enable>

<!-- SIP -->
<SIP_Port>{{SIP_PORT}}</SIP_Port>
<RTP_Port_Min>16384</RTP_Port_Min>
<RTP_Port_Max>16482</RTP_Port_Max>

<!-- Regional Settings -->
<FXS_Port_Impedance>600</FXS_Port_Impedance>
</flat-profile>
"""
        self.add_template("cisco", "spa122", cisco_spa122_template)

        # Cisco ATA 191 (2-Port Enterprise ATA) template
        cisco_ata191_template = """<flat-profile>
<Provision_Enable>No</Provision_Enable>
<Time_Zone>GMT-08:00</Time_Zone>
<Primary_NTP_Server>pool.ntp.org</Primary_NTP_Server>

<!-- Line 1 Configuration -->
<Line_Enable_1_>Yes</Line_Enable_1_>
<Display_Name_1_>{{EXTENSION_NAME}}</Display_Name_1_>
<User_ID_1_>{{EXTENSION_NUMBER}}</User_ID_1_>
<Auth_ID_1_>{{EXTENSION_NUMBER}}</Auth_ID_1_>
<Password_1_>{{EXTENSION_PASSWORD}}</Password_1_>
<Proxy_1_>{{SIP_SERVER}}</Proxy_1_>
<Register_1_>Yes</Register_1_>
<Register_Expires_1_>3600</Register_Expires_1_>

<!-- Codecs -->
<Preferred_Codec_1_>G711u</Preferred_Codec_1_>
<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>
<G711u_Enable_1_>Yes</G711u_Enable_1_>
<G711a_Enable_1_>Yes</G711a_Enable_1_>

<!-- DTMF -->
<DTMF_Tx_Method_1_>Auto</DTMF_Tx_Method_1_>

<!-- Fax - T.38 -->
<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>

<!-- Echo Cancellation -->
<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>

<!-- Line 2 Disabled by Default -->
<Line_Enable_2_>No</Line_Enable_2_>

<!-- Network -->
<Internet_Connection_Type>DHCP</Internet_Connection_Type>

<!-- PoE Support -->
<PoE_Enable>Yes</PoE_Enable>

<!-- SIP -->
<SIP_Port>{{SIP_PORT}}</SIP_Port>
<RTP_Port_Min>16384</RTP_Port_Min>
<RTP_Port_Max>16482</RTP_Port_Max>

<!-- Regional Settings -->
<FXS_Port_Impedance>600</FXS_Port_Impedance>
</flat-profile>
"""
        self.add_template("cisco", "ata191", cisco_ata191_template)

        # Cisco ATA 192 (2-Port Enterprise ATA) template
        cisco_ata192_template = """<flat-profile>
<Provision_Enable>No</Provision_Enable>
<Time_Zone>GMT-08:00</Time_Zone>
<Primary_NTP_Server>pool.ntp.org</Primary_NTP_Server>

<!-- Line 1 Configuration -->
<Line_Enable_1_>Yes</Line_Enable_1_>
<Display_Name_1_>{{EXTENSION_NAME}}</Display_Name_1_>
<User_ID_1_>{{EXTENSION_NUMBER}}</User_ID_1_>
<Auth_ID_1_>{{EXTENSION_NUMBER}}</Auth_ID_1_>
<Password_1_>{{EXTENSION_PASSWORD}}</Password_1_>
<Proxy_1_>{{SIP_SERVER}}</Proxy_1_>
<Register_1_>Yes</Register_1_>
<Register_Expires_1_>3600</Register_Expires_1_>

<!-- Codecs -->
<Preferred_Codec_1_>G711u</Preferred_Codec_1_>
<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>
<G711u_Enable_1_>Yes</G711u_Enable_1_>
<G711a_Enable_1_>Yes</G711a_Enable_1_>

<!-- DTMF -->
<DTMF_Tx_Method_1_>Auto</DTMF_Tx_Method_1_>

<!-- Fax - T.38 -->
<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>

<!-- Echo Cancellation -->
<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>

<!-- Line 2 Disabled by Default -->
<Line_Enable_2_>No</Line_Enable_2_>

<!-- Network -->
<Internet_Connection_Type>DHCP</Internet_Connection_Type>

<!-- SIP -->
<SIP_Port>{{SIP_PORT}}</SIP_Port>
<RTP_Port_Min>16384</RTP_Port_Min>
<RTP_Port_Max>16482</RTP_Port_Max>

<!-- Regional Settings -->
<FXS_Port_Impedance>600</FXS_Port_Impedance>

<!-- Multiplatform -->
<Multiplatform_Enable>Yes</Multiplatform_Enable>
</flat-profile>
"""
        self.add_template("cisco", "ata192", cisco_ata192_template)

        self.logger.info(f"Loaded {len(self.templates)} built-in phone templates (including ATAs)")

    def _load_custom_templates(self):
        """Load custom templates from configuration"""
        custom_templates_dir = self.config.get("provisioning.custom_templates_dir", None)

        if custom_templates_dir and os.path.exists(custom_templates_dir):
            try:
                for filename in os.listdir(custom_templates_dir):
                    if filename.endswith(".template"):
                        filepath = os.path.join(custom_templates_dir, filename)
                        # Parse filename: vendor_model.template
                        parts = filename.replace(".template", "").split("_")
                        if len(parts) >= 2:
                            vendor = parts[0]
                            model = "_".join(parts[1:])

                            with open(filepath, "r") as f:
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

        # Generate config URL for this device
        config_url = self._generate_config_url(device.mac_address)
        device.config_url = config_url
        self.devices[device.mac_address] = device

        # Save to database if available
        if self.devices_db:
            try:
                self.devices_db.add_device(
                    mac_address=device.mac_address,
                    extension_number=extension_number,
                    vendor=vendor,
                    model=model,
                    device_type=device.device_type,
                    config_url=config_url,
                )
                device_type_label = "ATA" if device.is_ata() else "phone"
                self.logger.info(
                    f"Registered {device_type_label} {mac_address} for extension {extension_number} (saved to database)"
                )
            except Exception as e:
                self.logger.error(f"Failed to save device to database: {e}")
                self.logger.info(
                    f"Registered device {mac_address} for extension {extension_number} (in-memory only)"
                )
        else:
            self.logger.info(
                f"Registered device {mac_address} for extension {extension_number} (in-memory only)"
            )

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

        found = normalized_mac in self.devices
        if found:
            del self.devices[normalized_mac]

            # Remove from database if available
            if self.devices_db:
                try:
                    self.devices_db.remove_device(normalized_mac)
                    self.logger.info(f"Unregistered device {mac_address} (removed from database)")
                except Exception as e:
                    self.logger.error(f"Failed to remove device from database: {e}")
                    self.logger.info(
                        f"Unregistered device {mac_address} (removed from memory only)"
                    )
            else:
                self.logger.info(f"Unregistered device {mac_address} (removed from memory)")

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
            list of ProvisioningDevice objects
        """
        return list(self.devices.values())

    def get_atas(self):
        """
        Get all registered ATA devices

        Returns:
            list of ProvisioningDevice objects (ATAs only)
        """
        return [device for device in self.devices.values() if device.is_ata()]

    def get_phones(self):
        """
        Get all registered phone devices (excluding ATAs)

        Returns:
            list of ProvisioningDevice objects (phones only)
        """
        return [device for device in self.devices.values() if not device.is_ata()]

    def _build_ldap_phonebook_config(self):
        """
        Build LDAP phonebook configuration from AD credentials or explicit config

        This method prioritizes using Active Directory credentials from .env file
        (AD_SERVER, AD_BIND_DN, AD_BIND_PASSWORD) if AD integration is enabled.
        Falls back to explicit ldap_phonebook config if AD is disabled.

        Returns:
            dict: LDAP phonebook configuration
        """
        from urllib.parse import urlparse

        # Check if explicit ldap_phonebook config exists
        explicit_config = self.config.get("provisioning.ldap_phonebook", {})

        # Check if AD integration is enabled
        ad_enabled = self.config.get("integrations.active_directory.enabled", False)

        if ad_enabled:
            # Use AD credentials from .env (via config)
            ad_server = self.config.get("integrations.active_directory.server", "")
            ad_bind_dn = self.config.get("integrations.active_directory.bind_dn", "")
            ad_bind_password = self.config.get("integrations.active_directory.bind_password", "")
            ad_base_dn = self.config.get("integrations.active_directory.base_dn", "")

            # Validate AD credentials
            if ad_server and ad_bind_dn and ad_bind_password:
                # Validate LDAP DN format (basic check)
                if not ad_bind_dn.upper().startswith(("CN=", "OU=", "DC=")):
                    self.logger.warning(f"AD bind DN may be invalid: {ad_bind_dn}")

                self.logger.info("Using AD credentials from .env for LDAP phonebook")

                # Parse server URL properly using urllib
                try:
                    parsed = urlparse(ad_server)

                    # Extract hostname and port
                    server_url = (
                        parsed.hostname or parsed.netloc.split(":")[0]
                        if parsed.netloc
                        else ad_server
                    )
                    port = parsed.port
                    scheme = parsed.scheme.lower()

                    # Determine TLS mode and default port based on scheme
                    if scheme == "ldaps":
                        tls_mode = 1
                        port = port or 636  # Default LDAPS port
                    elif scheme == "ldap":
                        tls_mode = 0
                        port = port or 389  # Default LDAP port
                    else:
                        # No scheme provided, assume LDAPS
                        self.logger.warning(
                            f"No scheme in AD server URL, assuming LDAPS: {ad_server}"
                        )
                        tls_mode = 1
                        port = port or 636

                except Exception as e:
                    self.logger.error(f"Error parsing AD server URL '{ad_server}': {e}")
                    # Fall back to simple parsing
                    server_url = (
                        ad_server.replace("ldaps://", "").replace("ldap://", "").split(":")[0]
                    )
                    port = 636
                    tls_mode = 1

                # Build config from AD credentials with sensible defaults
                # Override with explicit config if provided
                ldap_config = {
                    # Enable by default
                    "enable": explicit_config.get("enable", 1),
                    "server": server_url,
                    "port": explicit_config.get("port", port),
                    "base": explicit_config.get("base", ad_base_dn),
                    "user": ad_bind_dn,
                    "password": ad_bind_password,
                    "version": explicit_config.get("version", 3),
                    "tls_mode": explicit_config.get("tls_mode", tls_mode),
                    # Filter to only show users with telephoneNumber - ensures
                    # phone book shows entries with phone numbers
                    "name_filter": explicit_config.get(
                        "name_filter", "(&(|(cn=%)(sn=%))(telephoneNumber=*))"
                    ),
                    "number_filter": explicit_config.get(
                        "number_filter", "(|(telephoneNumber=%)(mobile=%))"
                    ),
                    "name_attr": explicit_config.get("name_attr", "cn"),
                    "number_attr": explicit_config.get("number_attr", "telephoneNumber"),
                    "display_name": explicit_config.get("display_name", "Company Directory"),
                }

                return ldap_config

        # Fall back to explicit ldap_phonebook config
        if explicit_config:
            self.logger.info("Using explicit ldap_phonebook configuration")
            return explicit_config

        # Return empty config if neither AD nor explicit config is available
        self.logger.debug("No LDAP phonebook configuration available")
        return {
            "enable": 0,
            "server": "",
            "port": 636,
            "base": "",
            "user": "",
            "password": "",
            "version": 3,
            "tls_mode": 1,
            # Filter to only show users with telephoneNumber - ensures phone
            # book shows entries with phone numbers
            "name_filter": "(&(|(cn=%)(sn=%))(telephoneNumber=*))",
            "number_filter": "(|(telephoneNumber=%)(mobile=%))",
            "name_attr": "cn",
            "number_attr": "telephoneNumber",
            "display_name": "Directory",
        }

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mac_address": mac_address,
            "normalized_mac": normalize_mac_address(mac_address),
            "ip_address": request_info.get("ip") if request_info else None,
            "user_agent": request_info.get("user_agent") if request_info else None,
            "success": False,
            "error": None,
        }

        self.logger.info(f"Provisioning request received for MAC: {mac_address}")
        if request_info:
            self.logger.info(
                f"  Request from IP: {request_info.get('ip', 'Unknown')}"
            )
            self.logger.info(f"  User-Agent: {request_info.get('user_agent', 'Unknown')}")

        device = self.get_device(mac_address)
        if not device:
            normalized = normalize_mac_address(mac_address)
            error_msg = f"Device {mac_address} not registered in provisioning system"
            self.logger.warning(error_msg)
            self.logger.warning(f"  Normalized MAC: {normalized}")
            self.logger.warning(
                f"  Registered devices: {list(self.devices.keys())}"
            )

            # Provide helpful guidance
            # Determine protocol based on actual API configuration
            # Note: Provisioning typically uses HTTP even when API uses HTTPS
            # because phones often cannot validate self-signed certificates
            ssl_enabled = self.config.get("api.ssl.enabled", False)
            api_protocol = "https" if ssl_enabled else "http"
            api_port = self.config.get("api.port", 9000)
            server_ip = self.config.get("server.external_ip", "192.168.1.14")

            self.logger.warning("  → Device needs to be registered first")
            self.logger.warning("  → Register via API: POST /api/provisioning/devices")
            self.logger.warning("  → Example:")
            self.logger.warning(
                f"     curl -X POST {api_protocol}://{server_ip}:{api_port}/api/provisioning/devices \\"
            )
            self.logger.warning("       -H 'Content-type: application/json' \\")
            self.logger.warning(
                '       -d \'{{"mac_address":"{mac_address}","extension_number":"XXXX","vendor":"VENDOR","model":"MODEL"}}\''
            )
            self.logger.warning(
                "  → Available vendors: yealink, polycom, cisco, grandstream, zultys"
            )

            # Check if there are similar MACs (might be a format issue)
            mac_prefix = normalized[:6]  # First 6 chars (OUI)
            similar_macs = [m for m in self.devices.keys() if m.startswith(mac_prefix)]
            if similar_macs:
                self.logger.warning(f"  → Similar MACs found (same vendor): {similar_macs}")
                self.logger.warning("     This might be a typo in the MAC address")

            request_log["error"] = error_msg
            self._add_request_log(request_log)
            return None, None

        self.logger.info(
            f"  Found device: vendor={device.vendor}, model={device.model}, extension={device.extension_number}"
        )

        # Get template
        template = self.get_template(device.vendor, device.model)
        if not template:
            error_msg = f"Template not found for {device.vendor} {device.model}"
            self.logger.warning(error_msg)
            self.logger.warning(
                f"  Available templates: {list(self.templates.keys())}"
            )
            request_log["error"] = error_msg
            self._add_request_log(request_log)
            return None, None

        # Get extension configuration
        extension = extension_registry.get(device.extension_number)
        if not extension:
            error_msg = f"Extension {device.extension_number} not found"
            self.logger.warning(error_msg)
            self.logger.warning(
                f"  Available extensions: {[e.number for e in extension_registry.get_all()]}"
            )
            request_log["error"] = error_msg
            self._add_request_log(request_log)
            return None, None

        self.logger.info(
            f"  Extension found: {extension.number} ({extension.name})"
        )

        # Build extension config dict
        extension_config = {
            "number": extension.number,
            "name": extension.name,
            "password": extension.config.get("password", ""),
        }

        # Build server config dict
        server_config = {
            "sip_host": self.config.get("server.external_ip", "127.0.0.1"),
            "sip_port": self.config.get("server.sip_port", 5060),
            "server_name": self.config.get("server.server_name", "PBX"),
        }

        # Add LDAP phonebook configuration
        server_config["ldap_phonebook"] = self._build_ldap_phonebook_config()
        server_config["remote_phonebook"] = self.config.get("provisioning.remote_phonebook", {})

        self.logger.info(
            f"  Server config: SIP={server_config['sip_host']}:{server_config['sip_port']}"
        )

        # Generate configuration
        config_content = template.generate_config(extension_config, server_config)

        # Determine content type based on vendor
        # Mapping of vendors to their content types
        vendor_content_types = {
            "polycom": "application/xml",
        }
        content_type = vendor_content_types.get(device.vendor, "text/plain")

        # Mark device as provisioned
        device.mark_provisioned()

        # Update last_provisioned timestamp in database
        if self.devices_db:
            try:
                self.devices_db.mark_provisioned(device.mac_address)
            except Exception as e:
                self.logger.debug(f"Failed to update last_provisioned in database: {e}")

        self.logger.info(f"✓ Successfully generated config for device {mac_address}")
        self.logger.info(
            f"  Config size: {len(config_content)} bytes, Content-type: {content_type}"
        )

        request_log["success"] = True
        request_log["vendor"] = device.vendor
        request_log["model"] = device.model
        request_log["extension"] = device.extension_number
        request_log["config_size"] = len(config_content)
        self._add_request_log(request_log)

        return config_content, content_type

    def _add_request_log(self, request_log):
        """Add request to history, keeping only recent requests"""
        self.provision_requests.append(request_log)
        # Keep only the last N requests
        if len(self.provision_requests) > self.max_request_history:
            self.provision_requests = self.provision_requests[-self.max_request_history :]

    def get_request_history(self, limit=None):
        """
        Get provisioning request history

        Args:
            limit: Optional limit on number of requests to return

        Returns:
            list of request log dicts
        """
        if limit:
            return self.provision_requests[-limit:]
        return self.provision_requests

    def _generate_config_url(self, mac_address):
        """
        Generate provisioning config URL for a device

        Args:
            mac_address: Normalized MAC address

        Returns:
            Generated config URL string
        """
        provisioning_url_format = self.config.get("provisioning.url_format")

        if not provisioning_url_format:
            # Auto-generate URL format based on SSL status
            # Default to HTTP for phone provisioning (phones often can't handle
            # self-signed certs)
            ssl_enabled = self.config.get("api.ssl.enabled", False)
            protocol = "http"  # Always use HTTP for provisioning by default
            provisioning_url_format = (
                f"{protocol}://{{{{SERVER_IP}}}}:{{{{PORT}}}}/provision/{{mac}}.cfg"
            )
            if ssl_enabled:
                self.logger.debug("Using HTTP for provisioning even though SSL is enabled")

        config_url = provisioning_url_format.replace("{mac}", mac_address)
        config_url = config_url.replace(
            "{{SERVER_IP}}", self.config.get("server.external_ip", "127.0.0.1")
        )
        config_url = config_url.replace("{{PORT}}", str(self.config.get("api.port", 9000)))

        return config_url

    def get_supported_vendors(self):
        """
        Get list of supported vendors

        Returns:
            list of vendor names
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
            list of models or dict of vendor -> models
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
            # Build SIP NOTIFY for check-sync event (triggers phone
            # reboot/config reload)
            server_ip = sip_server.pbx_core.config.get("server.external_ip", "127.0.0.1")
            sip_port = sip_server.pbx_core.config.get("server.sip_port", 5060)

            notify_msg = SIPMessageBuilder.build_request(
                method="NOTIFY",
                uri=f"sip:{extension_number}@{extension.address[0]}:{extension.address[1]}",
                from_addr=f"<sip:{server_ip}:{sip_port}>",
                to_addr=f"<sip:{extension_number}@{server_ip}>",
                call_id=f"notify-reboot-{extension_number}-{datetime.now(timezone.utc).timestamp()}",
                cseq=1,
            )

            # Add NOTIFY-specific headers
            notify_msg.set_header("Event", "check-sync")
            notify_msg.set_header("Subscription-State", "terminated")
            notify_msg.set_header("Content-Length", "0")

            # Send the NOTIFY message
            sip_server._send_message(notify_msg.build(), extension.address)

            self.logger.info(
                f"Sent reboot NOTIFY to extension {extension_number} at {extension.address}"
            )
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
        results = {"success_count": 0, "failed_count": 0, "rebooted": [], "failed": []}

        # Get all registered extensions
        extensions = sip_server.pbx_core.extension_registry.get_all()

        for extension in extensions:
            if extension.registered:
                if self.reboot_phone(extension.number, sip_server):
                    results["success_count"] += 1
                    results["rebooted"].append(extension.number)
                else:
                    results["failed_count"] += 1
                    results["failed"].append(extension.number)

        self.logger.info(
            f"Rebooted {results['success_count']} phones, {results['failed_count']} failed"
        )
        return results

    def list_all_templates(self):
        """
        list all available templates (both built-in and custom)

        Returns:
            list of dicts with template information
        """
        templates_list = []
        for (vendor, model), template in self.templates.items():
            # Check if template is customized (exists in custom dir)
            is_custom = False
            custom_dir = self.config.get(
                "provisioning.custom_templates_dir", "provisioning_templates"
            )
            template_filename = f"{vendor}_{model}.template"
            template_path = os.path.join(custom_dir, template_filename)

            if os.path.exists(template_path):
                is_custom = True

            templates_list.append(
                {
                    "vendor": vendor,
                    "model": model,
                    "is_custom": is_custom,
                    "template_path": template_path if is_custom else "built-in",
                    "size": len(template.template_content),
                }
            )

        return sorted(templates_list, key=lambda x: (x["vendor"], x["model"]))

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

        if not re.match(r"^[a-z0-9_-]+$", vendor.lower()) or not re.match(
            r"^[a-z0-9_-]+$", model.lower()
        ):
            return (
                False,
                "Invalid vendor or model name. Only alphanumeric, underscore, and hyphen allowed.",
                None,
            )

        template = self.get_template(vendor, model)
        if not template:
            return False, f"Template not found for {vendor} {model}", None

        # Get custom templates directory
        custom_dir = self.config.get("provisioning.custom_templates_dir", "provisioning_templates")

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
            with open(template_path, "w") as f:
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

        if not re.match(r"^[a-z0-9_-]+$", vendor.lower()) or not re.match(
            r"^[a-z0-9_-]+$", model.lower()
        ):
            return (
                False,
                "Invalid vendor or model name. Only alphanumeric, underscore, and hyphen allowed.",
            )

        # Get custom templates directory
        custom_dir = self.config.get("provisioning.custom_templates_dir", "provisioning_templates")

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
            with open(template_path, "w") as f:
                f.write(content)

            # Update in memory
            self.add_template(vendor, model, content)

            self.logger.info(f"Updated template: {vendor} {model}")
            return True, "Template updated successfully"
        except Exception as e:
            self.logger.error(f"Failed to update template: {e}")
            return False, f"Failed to update template: {e}"

    def set_static_ip(self, mac_address, static_ip):
        """
        set static IP address for a device

        Args:
            mac_address: Device MAC address
            static_ip: Static IP address

        Returns:
            tuple: (success, message)
        """
        normalized_mac = normalize_mac_address(mac_address)

        # Check if device exists
        device = self.get_device(mac_address)
        if not device:
            return False, f"Device {mac_address} not found"

        # Save to database if available
        if self.devices_db:
            try:
                success = self.devices_db.set_static_ip(normalized_mac, static_ip)
                if success:
                    self.logger.info(f"set static IP {static_ip} for device {mac_address}")
                    return True, f"Static IP {static_ip} set for device {mac_address}"
                else:
                    return False, "Failed to update static IP in database"
            except Exception as e:
                self.logger.error(f"Failed to set static IP: {e}")
                return False, f"Failed to set static IP: {e}"
        else:
            return False, "Database not available - static IP mapping requires database"

    def get_static_ip(self, mac_address):
        """
        Get static IP address for a device

        Args:
            mac_address: Device MAC address

        Returns:
            Static IP address or None
        """
        normalized_mac = normalize_mac_address(mac_address)

        if self.devices_db:
            try:
                device = self.devices_db.get_device(normalized_mac)
                if device:
                    return device.get("static_ip")
            except Exception as e:
                self.logger.error(f"Failed to get static IP: {e}")

        return None

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
                "total_templates": len(self.templates),
                "vendors": len(self.get_supported_vendors()),
            }

            self.logger.info(f"Reloaded {stats['total_templates']} templates")
            return True, "Templates reloaded successfully", stats
        except Exception as e:
            self.logger.error(f"Failed to reload templates: {e}")
            return False, f"Failed to reload templates: {e}", None
