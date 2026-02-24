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

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pbx.utils.device_types import detect_device_type
from pbx.utils.logger import get_logger


class PhoneTemplate:
    """Represents a phone configuration template"""

    def __init__(self, vendor: str, model: str, template_content: str) -> None:
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

    def generate_config(self, extension_config: str, server_config: dict) -> str:
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

        # Provisioning resource URL (for wallpaper, branding assets, etc.)
        config = config.replace(
            "{{PROVISION_RESOURCE_URL}}",
            str(server_config.get("provision_resource_url", "")),
        )

        return config


def normalize_mac_address(mac: str) -> str:
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
        self,
        mac_address: str,
        extension_number: str,
        vendor: str,
        model: str,
        device_type: str | None = None,
        config_url: str | None = None,
    ) -> None:
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
        self.created_at = datetime.now(UTC)
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

    def mark_provisioned(self) -> None:
        """Mark device as provisioned"""
        self.last_provisioned = datetime.now(UTC)

    def to_dict(self) -> dict:
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

    def __init__(self, config: Any, database: Any | None = None) -> None:
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
        self.logger.info(f"API port: {self.config.get('api.port', 'Not configured')}")

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

    def _load_devices_from_database(self) -> None:
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

            self.logger.info(f"Loaded {len(db_devices)} provisioned devices from database")
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error loading devices from database: {e}")

    def _load_builtin_templates(self) -> None:
        """Load built-in phone templates"""

        # Zultys ZIP 33G template (basic SIP phone, Yealink T28G-based, grayscale LCD)
        # Kept in sync with provisioning_templates/zultys_zip33g.template
        zultys_zip33g_template = """#!version:1.0.0.1
# Zultys ZIP 33G Configuration File
# Generated by Warden VoIP PBX

# SIP Account Configuration
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}

# SIP Server
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600
account.1.sip_server.1.retry_counts = 3
account.1.sip_server.1.transport = 0
account.1.sip_server_host.legacy = {{SIP_SERVER}}
account.1.reregister_enable = 1
account.1.registration_period = 3600

# Codecs — ZIP 33G requires explicit sample_rate/bitrate/ptime for PCMU/PCMA
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

account.1.codec.4.enable = 1
account.1.codec.4.payload_type = 18
account.1.codec.4.priority = 4
account.1.codec.4.name = G729

account.1.codec.5.enable = 1
account.1.codec.5.payload_type = 2
account.1.codec.5.priority = 5
account.1.codec.5.name = G726-32

account.1.codec.6.enable = 1
account.1.codec.6.payload_type = 97
account.1.codec.6.priority = 6
account.1.codec.6.name = iLBC
account.1.codec.6.ptime = 30

account.1.codec.7.enable = 0
account.1.codec.7.priority = 0

# RTP
account.1.rtp.port_min = 10000
account.1.rtp.port_max = 20000
account.1.rtp.packet_time = 20

# DTMF — SIP INFO for reliable voicemail/IVR (avoids ZIP 33G RFC2833 issues)
account.1.dtmf.type = 2
account.1.dtmf.info_type = 0
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}

# Voicemail
voice_mail.number.1 = *{{EXTENSION_NUMBER}}
voice_mail.subscribe.1 = 1
voice_mail.subscribe.1.mwi = 1

# Account features
account.1.missed_calllog = 1
account.1.dialed_calllog = 1
account.1.answered_calllog = 1
account.1.earlymedia = 1
account.1.session_timer = 0
account.1.srtp_mode = 0
account.1.auto_answer = 0

# NAT
account.1.nat.udp_update_time = 30
account.1.nat.rport = 1

# Presence / BLF
account.1.blf.subscribe_period = 3600
account.1.subscribe_mwi = 1

# Call features
account.1.call_waiting = 1
account.1.anonymous_call = 0
account.1.reject_anonymous_call = 0
account.1.dnd.enable = 0

# SIP header identification
account.1.send_line_id = 1
account.1.enable_user_equal_phone = 1

# Network
network.dhcp = 1
network.vlan.internet_port_enable = 0
network.vlan.internet_port_priority = 5
network.lldp.enable = 1
network.lldp.packet_interval = 120
network.qos.enable = 1
network.qos.voice.priority = 6
network.qos.signaling.priority = 5

# Time
local_time.time_zone = -5
local_time.time_zone_name = United States-Eastern Time
local_time.ntp_server1 = pool.ntp.org
local_time.ntp_server2 = time.google.com
local_time.dhcp_time = 1
local_time.summer_time = 1

# Audio
voice.ring_vol = 7
voice.handset.tone_vol = 11
voice.handset.spk_vol = 11
voice.handfree.tone_vol = 15
voice.handfree.spk_vol = 15
voice.headset.tone_vol = 11
voice.headset.spk_vol = 11
voice.vad = 1
voice.comfort_noise = 1
voice.echo_cancellation = 1
voice.noise_reduction = 1

# Phone settings
phone_setting.redial_number = {{EXTENSION_NUMBER}}
phone_setting.redial_server = {{SIP_SERVER}}
phone_setting.call_return_user_name = {{EXTENSION_NUMBER}}
phone_setting.call_return_number = {{EXTENSION_NUMBER}}
phone_setting.call_return_server = {{SIP_SERVER}}
phone_setting.display_name_method = 1
phone_setting.backlight_time = 60
phone_setting.lcd_contrast = 5
phone_setting.language = English

# Auto provisioning
auto_provision.mode = 1
auto_provision.dhcp_option.enable = 1
auto_provision.dhcp_option.option60_value = 66
auto_provision.repeat.enable = 1
auto_provision.repeat.minutes = 1440

# LDAP Phone Book
ldap.enable = {{LDAP_ENABLE}}
ldap.server = {{LDAP_SERVER}}
ldap.port = {{LDAP_PORT}}
ldap.base = {{LDAP_BASE}}
ldap.user = {{LDAP_USER}}
ldap.password = {{LDAP_PASSWORD}}
ldap.version = {{LDAP_VERSION}}
ldap.tls_mode = {{LDAP_TLS_MODE}}
ldap.name_filter = {{LDAP_NAME_FILTER}}
ldap.number_filter = {{LDAP_NUMBER_FILTER}}
ldap.name_attr = {{LDAP_NAME_ATTR}}
ldap.number_attr = {{LDAP_NUMBER_ATTR}}
ldap.display_name = {{LDAP_DISPLAY_NAME}}

# Remote Phone Book (fallback)
remote_phonebook.url = {{REMOTE_PHONEBOOK_URL}}
remote_phonebook.refresh_interval = {{REMOTE_PHONEBOOK_REFRESH}}

# Line Keys
# NOTE: ZIP 33G will only ever use 1 line (account.1), so unused line keys are configured for paging.
# Type 3 = Intercom/Paging. If additional lines are needed in future, change type to 15 and set line = N.
linekey.2.type = 3
linekey.2.label = Paging
linekey.2.value = 700
linekey.2.line = %NULL%

linekey.3.type = 3
linekey.3.label = Paging
linekey.3.value = 700
linekey.3.line = %NULL%
"""
        self.add_template("zultys", "zip33g", zultys_zip33g_template)

        # Zultys ZIP 37G template (advanced SIP phone, Yealink T46G-based, 480x272 color LCD)
        # Kept in sync with provisioning_templates/zultys_zip37g.template
        # NOTE: ZIP 37G does NOT need explicit codec sample_rate/bitrate/ptime (unlike ZIP 33G)
        zultys_zip37g_template = """#!version:1.0.0.1
# Zultys ZIP 37G Configuration File
# Generated by Warden VoIP PBX

# SIP Account Configuration
account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}

# SIP Server
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600
account.1.sip_server.1.retry_counts = 3
account.1.sip_server.1.transport = 0
account.1.sip_server_host.legacy = {{SIP_SERVER}}
account.1.reregister_enable = 1
account.1.registration_period = 3600

# Codecs — ZIP 37G handles codec params internally (no explicit sample_rate needed)
account.1.codec.1.enable = 1
account.1.codec.1.payload_type = 0
account.1.codec.1.priority = 1
account.1.codec.1.name = PCMU

account.1.codec.2.enable = 1
account.1.codec.2.payload_type = 8
account.1.codec.2.priority = 2
account.1.codec.2.name = PCMA

account.1.codec.3.enable = 1
account.1.codec.3.payload_type = 9
account.1.codec.3.priority = 3
account.1.codec.3.name = G722

account.1.codec.4.enable = 1
account.1.codec.4.payload_type = 18
account.1.codec.4.priority = 4
account.1.codec.4.name = G729

account.1.codec.5.enable = 1
account.1.codec.5.payload_type = 2
account.1.codec.5.priority = 5
account.1.codec.5.name = G726-32

account.1.codec.6.enable = 1
account.1.codec.6.payload_type = 97
account.1.codec.6.priority = 6
account.1.codec.6.name = iLBC
account.1.codec.6.ptime = 30

account.1.codec.7.enable = 0
account.1.codec.7.priority = 0

# RTP
account.1.rtp.port_min = 10000
account.1.rtp.port_max = 20000
account.1.rtp.packet_time = 20

# DTMF — SIP INFO to avoid ZIP 37G overly sensitive RFC2833 detection
account.1.dtmf.type = 2
account.1.dtmf.info_type = 0
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}

# Voicemail
voice_mail.number.1 = *{{EXTENSION_NUMBER}}
voice_mail.subscribe.1 = 1
voice_mail.subscribe.1.mwi = 1

# Account features
account.1.missed_calllog = 1
account.1.dialed_calllog = 1
account.1.answered_calllog = 1
account.1.earlymedia = 1
account.1.session_timer = 0
account.1.srtp_mode = 0
account.1.auto_answer = 0

# NAT
account.1.nat.udp_update_time = 30
account.1.nat.rport = 1

# Presence / BLF
account.1.blf.subscribe_period = 3600
account.1.subscribe_mwi = 1

# Call features
account.1.call_waiting = 1
account.1.anonymous_call = 0
account.1.reject_anonymous_call = 0
account.1.dnd.enable = 0

# SIP header identification
account.1.send_line_id = 1
account.1.enable_user_equal_phone = 1

# Network
network.dhcp = 1
network.vlan.internet_port_enable = 0
network.vlan.internet_port_priority = 5
network.lldp.enable = 1
network.lldp.packet_interval = 120
network.qos.enable = 1
network.qos.voice.priority = 6
network.qos.signaling.priority = 5

# Time
local_time.time_zone = -5
local_time.time_zone_name = United States-Eastern Time
local_time.ntp_server1 = pool.ntp.org
local_time.ntp_server2 = time.google.com
local_time.dhcp_time = 1
local_time.summer_time = 1

# Audio
voice.ring_vol = 7
voice.handset.tone_vol = 11
voice.handset.spk_vol = 11
voice.handfree.tone_vol = 15
voice.handfree.spk_vol = 15
voice.headset.tone_vol = 11
voice.headset.spk_vol = 11
voice.vad = 1
voice.comfort_noise = 1
voice.echo_cancellation = 1
voice.noise_reduction = 1

# Phone settings
phone_setting.redial_number = {{EXTENSION_NUMBER}}
phone_setting.redial_server = {{SIP_SERVER}}
phone_setting.call_return_user_name = {{EXTENSION_NUMBER}}
phone_setting.call_return_number = {{EXTENSION_NUMBER}}
phone_setting.call_return_server = {{SIP_SERVER}}
phone_setting.display_name_method = 1
phone_setting.backlight_time = 60
phone_setting.lcd_contrast = 5
phone_setting.language = English

# Auto provisioning
auto_provision.mode = 1
auto_provision.dhcp_option.enable = 1
auto_provision.dhcp_option.option60_value = 66
auto_provision.repeat.enable = 1
auto_provision.repeat.minutes = 1440

# LDAP Phone Book
ldap.enable = {{LDAP_ENABLE}}
ldap.server = {{LDAP_SERVER}}
ldap.port = {{LDAP_PORT}}
ldap.base = {{LDAP_BASE}}
ldap.user = {{LDAP_USER}}
ldap.password = {{LDAP_PASSWORD}}
ldap.version = {{LDAP_VERSION}}
ldap.tls_mode = {{LDAP_TLS_MODE}}
ldap.name_filter = {{LDAP_NAME_FILTER}}
ldap.number_filter = {{LDAP_NUMBER_FILTER}}
ldap.name_attr = {{LDAP_NAME_ATTR}}
ldap.number_attr = {{LDAP_NUMBER_ATTR}}
ldap.display_name = {{LDAP_DISPLAY_NAME}}

# Remote Phone Book (fallback)
remote_phonebook.url = {{REMOTE_PHONEBOOK_URL}}
remote_phonebook.refresh_interval = {{REMOTE_PHONEBOOK_REFRESH}}

# Line Keys
# NOTE: ZIP 37G will only ever use 1 line (account.1), so unused line keys are configured for paging.
# Type 3 = Intercom/Paging. If additional lines are needed in future, change type to 15 and set line = N.
linekey.2.type = 3
linekey.2.label = Paging
linekey.2.value = 700
linekey.2.line = %NULL%

linekey.3.type = 3
linekey.3.label = Paging
linekey.3.value = 700
linekey.3.line = %NULL%
"""
        self.add_template("zultys", "zip37g", zultys_zip37g_template)

        # Yealink T46S template (480x272 color LCD, 16 line keys, Gigabit)
        # Kept in sync with provisioning_templates/yealink_t46s.template
        yealink_t46s_template = """#!version:1.0.0.1
# Yealink T46S Configuration File
# Generated by Warden VoIP PBX

account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600
account.1.sip_server.1.retry_counts = 3
account.1.sip_server.1.failover_timeout = 5
account.1.sip_server.1.transport = 0
account.1.sip_server_host.legacy = {{SIP_SERVER}}
account.1.reregister_enable = 1
account.1.registration_period = 3600

account.1.codec.1.enable = 1
account.1.codec.1.payload_type = 0
account.1.codec.1.priority = 1
account.1.codec.1.name = PCMU
account.1.codec.2.enable = 1
account.1.codec.2.payload_type = 8
account.1.codec.2.priority = 2
account.1.codec.2.name = PCMA
account.1.codec.3.enable = 1
account.1.codec.3.payload_type = 9
account.1.codec.3.priority = 3
account.1.codec.3.name = G722
account.1.codec.4.enable = 1
account.1.codec.4.payload_type = 18
account.1.codec.4.priority = 4
account.1.codec.4.name = G729
account.1.codec.5.enable = 1
account.1.codec.5.payload_type = 2
account.1.codec.5.priority = 5
account.1.codec.5.name = G726-32
account.1.codec.6.enable = 1
account.1.codec.6.payload_type = 97
account.1.codec.6.priority = 6
account.1.codec.6.name = iLBC
account.1.codec.6.ptime = 30
account.1.codec.7.enable = 1
account.1.codec.7.payload_type = 98
account.1.codec.7.priority = 7
account.1.codec.7.name = SPEEX
account.1.codec.8.enable = 0
account.1.codec.8.priority = 0

account.1.rtp.port_min = 10000
account.1.rtp.port_max = 20000
account.1.rtp.packet_time = 20

account.1.dtmf.type = 2
account.1.dtmf.info_type = 0
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}

voice_mail.number.1 = *{{EXTENSION_NUMBER}}
voice_mail.subscribe.1 = 1
voice_mail.subscribe.1.mwi = 1

account.1.missed_calllog = 1
account.1.dialed_calllog = 1
account.1.answered_calllog = 1
account.1.earlymedia = 1
account.1.session_timer = 0
account.1.srtp_mode = 0
account.1.auto_answer = 0
account.1.nat.udp_update_time = 30
account.1.nat.rport = 1
account.1.blf.subscribe_period = 3600
account.1.blf.list_uri =
account.1.subscribe_mwi = 1
account.1.call_waiting = 1
account.1.anonymous_call = 0
account.1.reject_anonymous_call = 0
account.1.dnd.enable = 0
account.1.send_line_id = 1
account.1.enable_user_equal_phone = 1

network.dhcp = 1
network.dhcp_vlan = 0
network.vlan.internet_port_enable = 0
network.vlan.internet_port_priority = 5
network.vlan.internet_port_vid = 1
network.lldp.enable = 1
network.lldp.packet_interval = 120
network.qos.enable = 1
network.qos.voice.priority = 6
network.qos.signaling.priority = 5

local_time.time_zone = -5
local_time.time_zone_name = United States-Eastern Time
local_time.ntp_server1 = pool.ntp.org
local_time.ntp_server2 = time.google.com
local_time.dhcp_time = 1
local_time.summer_time = 1

voice.ring_vol = 7
voice.handset.tone_vol = 11
voice.handset.ring_vol = 7
voice.handset.spk_vol = 11
voice.handfree.tone_vol = 15
voice.handfree.ring_vol = 15
voice.handfree.spk_vol = 15
voice.headset.tone_vol = 11
voice.headset.ring_vol = 7
voice.headset.spk_vol = 11
voice.vad = 1
voice.comfort_noise = 1
voice.echo_cancellation = 1
voice.noise_reduction = 1

phone_setting.redial_number = {{EXTENSION_NUMBER}}
phone_setting.redial_server = {{SIP_SERVER}}
phone_setting.call_return_user_name = {{EXTENSION_NUMBER}}
phone_setting.call_return_number = {{EXTENSION_NUMBER}}
phone_setting.call_return_server = {{SIP_SERVER}}
phone_setting.display_name_method = 1
phone_setting.call_history.dialed_calls = 100
phone_setting.call_history.missed_calls = 100
phone_setting.call_history.received_calls = 100
phone_setting.backlight_time = 60
phone_setting.backlight_timeout = 1
phone_setting.lcd_contrast = 5
phone_setting.language = English

auto_provision.mode = 1
auto_provision.dhcp_option.enable = 1
auto_provision.dhcp_option.list_user_options = %NULL%
auto_provision.dhcp_option.option60_value = 66
auto_provision.dhcp_option.option43_enable = 1
auto_provision.repeat.enable = 1
auto_provision.repeat.minutes = 1440
auto_provision.pnp.enable = 1
auto_provision.server.url =
auto_provision.server.auth_enable = 0

ldap.enable = {{LDAP_ENABLE}}
ldap.server = {{LDAP_SERVER}}
ldap.port = {{LDAP_PORT}}
ldap.base = {{LDAP_BASE}}
ldap.user = {{LDAP_USER}}
ldap.password = {{LDAP_PASSWORD}}
ldap.version = {{LDAP_VERSION}}
ldap.tls_mode = {{LDAP_TLS_MODE}}
ldap.name_filter = {{LDAP_NAME_FILTER}}
ldap.number_filter = {{LDAP_NUMBER_FILTER}}
ldap.name_attr = {{LDAP_NAME_ATTR}}
ldap.number_attr = {{LDAP_NUMBER_ATTR}}
ldap.display_name = {{LDAP_DISPLAY_NAME}}

remote_phonebook.url = {{REMOTE_PHONEBOOK_URL}}
remote_phonebook.refresh_interval = {{REMOTE_PHONEBOOK_REFRESH}}

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
        self.add_template("yealink", "t46s", yealink_t46s_template)

        # Yealink T28G template (grayscale LCD, basic business phone)
        # Kept in sync with provisioning_templates/yealink_t28g.template
        yealink_t28g_template = """#!version:1.0.0.1
# Yealink T28G Configuration File
# Generated by Warden VoIP PBX

account.1.enable = 1
account.1.label = {{EXTENSION_NAME}}
account.1.display_name = {{EXTENSION_NAME}}
account.1.user_name = {{EXTENSION_NUMBER}}
account.1.auth_name = {{EXTENSION_NUMBER}}
account.1.password = {{EXTENSION_PASSWORD}}
account.1.sip_server.1.address = {{SIP_SERVER}}
account.1.sip_server.1.port = {{SIP_PORT}}
account.1.sip_server.1.expires = 3600
account.1.sip_server.1.retry_counts = 3
account.1.sip_server.1.failover_timeout = 5
account.1.sip_server.1.transport = 0
account.1.sip_server_host.legacy = {{SIP_SERVER}}
account.1.reregister_enable = 1
account.1.registration_period = 3600

account.1.codec.1.enable = 1
account.1.codec.1.payload_type = 0
account.1.codec.1.priority = 1
account.1.codec.1.name = PCMU
account.1.codec.2.enable = 1
account.1.codec.2.payload_type = 8
account.1.codec.2.priority = 2
account.1.codec.2.name = PCMA
account.1.codec.3.enable = 1
account.1.codec.3.payload_type = 9
account.1.codec.3.priority = 3
account.1.codec.3.name = G722
account.1.codec.4.enable = 1
account.1.codec.4.payload_type = 18
account.1.codec.4.priority = 4
account.1.codec.4.name = G729
account.1.codec.5.enable = 1
account.1.codec.5.payload_type = 2
account.1.codec.5.priority = 5
account.1.codec.5.name = G726-32
account.1.codec.6.enable = 1
account.1.codec.6.payload_type = 97
account.1.codec.6.priority = 6
account.1.codec.6.name = iLBC
account.1.codec.6.ptime = 30
account.1.codec.7.enable = 1
account.1.codec.7.payload_type = 98
account.1.codec.7.priority = 7
account.1.codec.7.name = SPEEX
account.1.codec.8.enable = 0
account.1.codec.8.priority = 0

account.1.rtp.port_min = 10000
account.1.rtp.port_max = 20000
account.1.rtp.packet_time = 20

account.1.dtmf.type = 2
account.1.dtmf.info_type = 0
account.1.dtmf.dtmf_payload = {{DTMF_PAYLOAD_TYPE}}

voice_mail.number.1 = *{{EXTENSION_NUMBER}}
voice_mail.subscribe.1 = 1
voice_mail.subscribe.1.mwi = 1

account.1.missed_calllog = 1
account.1.dialed_calllog = 1
account.1.answered_calllog = 1
account.1.earlymedia = 1
account.1.session_timer = 0
account.1.srtp_mode = 0
account.1.auto_answer = 0
account.1.nat.udp_update_time = 30
account.1.nat.rport = 1
account.1.blf.subscribe_period = 3600
account.1.blf.list_uri =
account.1.subscribe_mwi = 1
account.1.call_waiting = 1
account.1.anonymous_call = 0
account.1.reject_anonymous_call = 0
account.1.dnd.enable = 0
account.1.send_line_id = 1
account.1.enable_user_equal_phone = 1

network.dhcp = 1
network.dhcp_vlan = 0
network.vlan.internet_port_enable = 0
network.vlan.internet_port_priority = 5
network.lldp.enable = 1
network.lldp.packet_interval = 120
network.qos.enable = 1
network.qos.voice.priority = 6
network.qos.signaling.priority = 5

local_time.time_zone = -5
local_time.time_zone_name = United States-Eastern Time
local_time.ntp_server1 = pool.ntp.org
local_time.ntp_server2 = time.google.com
local_time.dhcp_time = 1
local_time.summer_time = 1

voice.ring_vol = 7
voice.handset.tone_vol = 11
voice.handset.ring_vol = 7
voice.handset.spk_vol = 11
voice.handfree.tone_vol = 15
voice.handfree.ring_vol = 15
voice.handfree.spk_vol = 15
voice.headset.tone_vol = 11
voice.headset.ring_vol = 7
voice.headset.spk_vol = 11
voice.vad = 1
voice.comfort_noise = 1
voice.echo_cancellation = 1
voice.noise_reduction = 1

phone_setting.redial_number = {{EXTENSION_NUMBER}}
phone_setting.redial_server = {{SIP_SERVER}}
phone_setting.call_return_user_name = {{EXTENSION_NUMBER}}
phone_setting.call_return_number = {{EXTENSION_NUMBER}}
phone_setting.call_return_server = {{SIP_SERVER}}
phone_setting.display_name_method = 1
phone_setting.call_history.dialed_calls = 100
phone_setting.call_history.missed_calls = 100
phone_setting.call_history.received_calls = 100
phone_setting.backlight_time = 60
phone_setting.backlight_timeout = 1
phone_setting.lcd_contrast = 5
phone_setting.language = English

auto_provision.mode = 1
auto_provision.dhcp_option.enable = 1
auto_provision.dhcp_option.list_user_options = %NULL%
auto_provision.dhcp_option.option60_value = 66
auto_provision.dhcp_option.option43_enable = 1
auto_provision.repeat.enable = 1
auto_provision.repeat.minutes = 1440
auto_provision.pnp.enable = 1
auto_provision.server.url =
auto_provision.server.auth_enable = 0

ldap.enable = {{LDAP_ENABLE}}
ldap.server = {{LDAP_SERVER}}
ldap.port = {{LDAP_PORT}}
ldap.base = {{LDAP_BASE}}
ldap.user = {{LDAP_USER}}
ldap.password = {{LDAP_PASSWORD}}
ldap.version = {{LDAP_VERSION}}
ldap.tls_mode = {{LDAP_TLS_MODE}}
ldap.name_filter = {{LDAP_NAME_FILTER}}
ldap.number_filter = {{LDAP_NUMBER_FILTER}}
ldap.name_attr = {{LDAP_NAME_ATTR}}
ldap.number_attr = {{LDAP_NUMBER_ATTR}}
ldap.display_name = {{LDAP_DISPLAY_NAME}}

remote_phonebook.url = {{REMOTE_PHONEBOOK_URL}}
remote_phonebook.refresh_interval = {{REMOTE_PHONEBOOK_REFRESH}}

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
        self.add_template("yealink", "t28g", yealink_t28g_template)

        # Polycom VVX 450 template (color LCD, 12 line keys, Gigabit)
        # Kept in sync with provisioning_templates/polycom_vvx450.template
        polycom_vvx450_template = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<polycomConfig>
  <reg reg.1.displayName="{{EXTENSION_NAME}}"
       reg.1.address="{{EXTENSION_NUMBER}}"
       reg.1.label="{{EXTENSION_NAME}}"
       reg.1.auth.userId="{{EXTENSION_NUMBER}}"
       reg.1.auth.password="{{EXTENSION_PASSWORD}}"
       reg.1.server.1.address="{{SIP_SERVER}}"
       reg.1.server.1.port="{{SIP_PORT}}"
       reg.1.server.1.expires="3600"
       reg.1.server.1.retryTimeOut="300"
       reg.1.server.1.retryMaxCount="3"
       reg.1.lineKeys="1"
       reg.1.type="private"
       reg.1.ringType="ringer2"/>

  <voice voice.codecPref.G711_Mu="1"
         voice.codecPref.G711_A="2"
         voice.codecPref.G722="3"
         voice.codecPref.G729_AB="4"
         voice.codecPref.iLBC="5"/>

  <tone tone.dtmf.level="-13"
        tone.dtmf.onTime="100"
        tone.dtmf.offTime="100"
        tone.dtmf.viaRtp="1"
        tone.dtmf.rfc2833Control="1"
        tone.dtmf.rfc2833Payload="{{DTMF_PAYLOAD_TYPE}}"/>

  <msg msg.mwi.1.subscribe="*{{EXTENSION_NUMBER}}"
       msg.mwi.1.callBackMode="contact"
       msg.mwi.1.callBack="*{{EXTENSION_NUMBER}}"/>

  <call call.remotePartyID.1.render="1"
        call.remotePartyID.1.stage="1"
        call.callWaiting.enable="1"
        call.callWaiting.ring="beep"
        call.doNotDisturb.enable="0"
        call.callsPerLineKey="24"
        call.autoAnswer.micMute="0"/>

  <feature feature.callList.enabled="1"
           feature.callListMissed.enabled="1"
           feature.enhancedCallDisplay="1"
           feature.directedCallPickup.enabled="1"/>

  <nat nat.keepalive.interval="30"
       nat.ip="0.0.0.0"/>

  <device device.net.dhcpEnabled="1"
          device.net.lldpEnabled="1"
          device.net.cdpEnabled="1"/>

  <qos qos.ethernet.rtp.user_priority="6"
       qos.ethernet.callControl.user_priority="5"
       qos.ip.rtp.dscp="46"
       qos.ip.callControl.dscp="26"/>

  <tcpIpApp tcpIpApp.sntp.address="pool.ntp.org"
            tcpIpApp.sntp.address.overrideDHCP="0"
            tcpIpApp.sntp.gmtOffset="-18000"
            tcpIpApp.sntp.resyncPeriod="3600"/>

  <voice voice.volume.persist.handset="1"
         voice.volume.persist.handsfree="1"
         voice.volume.persist.headset="1"
         voice.echoSuppressor.enable="1"
         voice.ns.hf.enable="1"
         voice.vadEnable="1"/>

  <up up.backlight.idleIntensity="1"
      up.backlight.onIntensity="3"
      up.backlight.timeout="60"
      up.screenSaver.type="2"
      up.screenSaver.wait="600"/>

  <bg bg.hiRes.color.bm="{{PROVISION_RESOURCE_URL}}/wallpaper_warden.jpg"
      bg.hiRes.color.selection="2"/>

  <dir dir.corp.address="{{LDAP_SERVER}}"
       dir.corp.port="{{LDAP_PORT}}"
       dir.corp.baseDN="{{LDAP_BASE}}"
       dir.corp.user="{{LDAP_USER}}"
       dir.corp.password="{{LDAP_PASSWORD}}"/>

  <prov prov.polling.enabled="1"
        prov.polling.period="86400"
        prov.polling.time="01:00"/>
</polycomConfig>
"""
        self.add_template("polycom", "vvx450", polycom_vvx450_template)

        # Cisco SPA504G template (4-line IP phone)
        # Kept in sync with provisioning_templates/cisco_spa504g.template
        cisco_spa504g_template = """# Cisco SPA504G Configuration

Line_Enable_1_ : Yes
Display_Name_1_ : {{EXTENSION_NAME}}
User_ID_1_ : {{EXTENSION_NUMBER}}
Auth_ID_1_ : {{EXTENSION_NUMBER}}
Password_1_ : {{EXTENSION_PASSWORD}}
Proxy_1_ : {{SIP_SERVER}}
SIP_Port_1_ : {{SIP_PORT}}
Register_1_ : Yes
Register_Expires_1_ : 3600

Preferred_Codec_1_ : G711u
Second_Preferred_Codec_1_ : G711a
Third_Preferred_Codec_1_ : G722
G711u_Enable_1_ : Yes
G711a_Enable_1_ : Yes
G722_Enable_1_ : Yes
G729a_Enable_1_ : Yes

DTMF_Tx_Method_1_ : Auto
RTP_Port_Min_1_ : 16384
RTP_Port_Max_1_ : 16482

Voice_Mail_Server_1_ : *{{EXTENSION_NUMBER}}
Voice_Mail_Subscribe_Enable_1_ : Yes
Call_Waiting_Enable_1_ : Yes
DND_Enable_1_ : No
Send_Caller_ID_In_From_Header_1_ : Yes
Remote_Party_ID_1_ : Yes

NAT_Keep_Alive_Enable_1_ : Yes
Echo_Canc_Enable_1_ : Yes

Internet_Connection_Type : DHCP
DHCP_Option_To_Use : 66
Enable_QOS : Yes
SIP_TOS_DiffServ_Value : 0x68
RTP_TOS_DiffServ_Value : 0xb8

Time_Zone : GMT-05:00
Primary_NTP_Server : pool.ntp.org
Secondary_NTP_Server : time.google.com
Daylight_Saving_Time_Enable : Yes

Station_Name : {{EXTENSION_NAME}}
Back_Light_Timer : 60s
"""
        self.add_template("cisco", "spa504g", cisco_spa504g_template)

        # Grandstream GXP2170 template (6-line, color LCD, 48 BLF keys)
        # Kept in sync with provisioning_templates/grandstream_gxp2170.template
        grandstream_gxp2170_template = """# Grandstream GXP2170 Configuration

P271 = {{EXTENSION_NAME}}
P270 = {{EXTENSION_NUMBER}}
P35 = {{EXTENSION_NUMBER}}
P34 = {{EXTENSION_PASSWORD}}
P47 = {{SIP_SERVER}}
P48 = {{SIP_PORT}}
P2 = 3600
P2312 = 3600
P130 = 0

P57 = 0
P58 = 8
P67 = 9
P46 = 18
P98 = 2
P97 = 97

P79 = 2
P184 = 0
P78 = {{DTMF_PAYLOAD_TYPE}}

P33 = *{{EXTENSION_NUMBER}}
P2355 = 1

P298 = 1
P197 = 0
P2347 = 1
P2348 = 1
P2349 = 1
P2350 = 1
P2351 = 1

P52 = 30
P8 = 0
P1684 = 1
P38 = 48
P3000 = 46

P64 = pool.ntp.org
P65 = time.google.com
P30 = -5
P75 = 2

P200 = 6
P201 = 5
P202 = 5
P191 = 1
P192 = 0
P2336 = 60
P122 = 1
P2916 = {{PROVISION_RESOURCE_URL}}/wallpaper_warden.jpg

P1411 = 0
P194 = 1440
"""
        self.add_template("grandstream", "gxp2170", grandstream_gxp2170_template)

        # Grandstream HT801 (1-Port ATA) template
        # Kept in sync with provisioning_templates/grandstream_ht801.template
        grandstream_ht801_template = """# Grandstream HT801 (1-Port ATA) Configuration

P196 = {{EXTENSION_NAME}}
P8 = 0
P64 = pool.ntp.org
P65 = time.google.com
P30 = -5

P271 = {{EXTENSION_NAME}}
P270 = {{EXTENSION_NUMBER}}
P35 = {{EXTENSION_NUMBER}}
P34 = {{EXTENSION_PASSWORD}}
P47 = {{SIP_SERVER}}
P48 = {{SIP_PORT}}
P2312 = 3600

P57 = 0
P58 = 8
P46 = 18
P67 = 9

P79 = 2
P184 = 0
P78 = {{DTMF_PAYLOAD_TYPE}}

P3 = 1
P4 = 1
P2311 = 2
P240 = 2

P191 = 1
P192 = 0
P245 = 1
P338 = 1
"""
        self.add_template("grandstream", "ht801", grandstream_ht801_template)

        # Grandstream HT802 (2-Port ATA) template
        # Kept in sync with provisioning_templates/grandstream_ht802.template
        grandstream_ht802_template = """# Grandstream HT802 (2-Port ATA) Configuration

P196 = {{EXTENSION_NAME}}
P8 = 0
P64 = pool.ntp.org
P65 = time.google.com
P30 = -5

P271 = {{EXTENSION_NAME}}
P270 = {{EXTENSION_NUMBER}}
P35 = {{EXTENSION_NUMBER}}
P34 = {{EXTENSION_PASSWORD}}
P47 = {{SIP_SERVER}}
P48 = {{SIP_PORT}}
P2312 = 3600

P57 = 0
P58 = 8
P46 = 18
P67 = 9

P79 = 2
P184 = 0
P78 = {{DTMF_PAYLOAD_TYPE}}

P3 = 1
P4 = 1
P2311 = 2
P240 = 2

P191 = 1
P192 = 0
P245 = 1
P338 = 1

P2350 = 1
P2351 = 1
"""
        self.add_template("grandstream", "ht802", grandstream_ht802_template)

        # Cisco SPA112 (2-Port ATA) template
        cisco_spa112_template = """<flat-profile>
<Provision_Enable>No</Provision_Enable>
<Resync_On_Reset>No</Resync_On_Reset>

<!-- Regional Parameters -->
<Time_Zone>GMT-05:00</Time_Zone>
<NTP_Server>pool.ntp.org</NTP_Server>
<Daylight_Saving_Time_Enable>Yes</Daylight_Saving_Time_Enable>
<Daylight_Saving_Time_Rule>start=3/-1/7/2;end=11/-1/7/2;save=1</Daylight_Saving_Time_Rule>

<!-- Line 1 Configuration -->
<Line_Enable_1_>Yes</Line_Enable_1_>
<Display_Name_1_>{{EXTENSION_NAME}}</Display_Name_1_>
<User_ID_1_>{{EXTENSION_NUMBER}}</User_ID_1_>
<Auth_ID_1_>{{EXTENSION_NUMBER}}</Auth_ID_1_>
<Password_1_>{{EXTENSION_PASSWORD}}</Password_1_>
<Proxy_1_>{{SIP_SERVER}}</Proxy_1_>
<Register_1_>Yes</Register_1_>
<Register_Expires_1_>3600</Register_Expires_1_>

<!-- Codecs - Optimized for analog and fax -->
<Preferred_Codec_1_>G711u</Preferred_Codec_1_>
<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>
<Third_Preferred_Codec_1_>G729a</Third_Preferred_Codec_1_>
<G729a_Enable_1_>Yes</G729a_Enable_1_>
<G711u_Enable_1_>Yes</G711u_Enable_1_>
<G711a_Enable_1_>Yes</G711a_Enable_1_>
<G726-16_Enable_1_>No</G726-16_Enable_1_>
<G726-24_Enable_1_>No</G726-24_Enable_1_>
<G726-32_Enable_1_>No</G726-32_Enable_1_>
<G726-40_Enable_1_>No</G726-40_Enable_1_>

<!-- DTMF -->
<DTMF_Tx_Method_1_>Auto</DTMF_Tx_Method_1_>
<DTMF_Tx_Mode_1_>Strict</DTMF_Tx_Mode_1_>
<RTP_Packet_Size_1_>0.020</RTP_Packet_Size_1_>

<!-- Fax - T.38 -->
<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>
<FAX_T38_Redundancy_1_>1</FAX_T38_Redundancy_1_>
<FAX_Passthru_Method_1_>NSE</FAX_Passthru_Method_1_>

<!-- Voice Processing -->
<Silence_Supp_Enable_1_>No</Silence_Supp_Enable_1_>
<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>
<Echo_Canc_Adapt_Enable_1_>Yes</Echo_Canc_Adapt_Enable_1_>
<Echo_Supp_Enable_1_>Yes</Echo_Supp_Enable_1_>

<!-- Caller ID -->
<Caller_ID_Method_1_>Bellcore(N.Amer,China)</Caller_ID_Method_1_>
<Caller_ID_FSK_Standard_1_>bell202</Caller_ID_FSK_Standard_1_>

<!-- Audio -->
<Txgain_1_>0</Txgain_1_>
<Rxgain_1_>0</Rxgain_1_>

<!-- Line 2 Disabled by Default -->
<Line_Enable_2_>No</Line_Enable_2_>

<!-- System Parameters -->
<Primary_NTP_Server>pool.ntp.org</Primary_NTP_Server>
<Secondary_NTP_Server>time.google.com</Secondary_NTP_Server>

<!-- Network -->
<Internet_Connection_Type>DHCP</Internet_Connection_Type>
<Enable_VLAN>No</Enable_VLAN>

<!-- SIP -->
<SIP_Port>{{SIP_PORT}}</SIP_Port>
<RTP_Port_Min>16384</RTP_Port_Min>
<RTP_Port_Max>16482</RTP_Port_Max>
<SIP_TOS_DiffServ_Value>0x68</SIP_TOS_DiffServ_Value>
<RTP_TOS_DiffServ_Value>0xb8</RTP_TOS_DiffServ_Value>

<!-- Regional Settings (FCC/North America) -->
<Ring_Waveform>Sinusoid</Ring_Waveform>
<Ring_Frequency>20</Ring_Frequency>
<Ring_Voltage>75</Ring_Voltage>
<FXS_Port_Impedance>600</FXS_Port_Impedance>
<Hook_Flash_Timer_Min>0.1</Hook_Flash_Timer_Min>
<Hook_Flash_Timer_Max>0.9</Hook_Flash_Timer_Max>
</flat-profile>
"""
        self.add_template("cisco", "spa112", cisco_spa112_template)

        # Cisco SPA122 (2-Port ATA with Router) template
        cisco_spa122_template = """<flat-profile>
<Provision_Enable>No</Provision_Enable>
<Resync_On_Reset>No</Resync_On_Reset>

<!-- Regional Parameters -->
<Time_Zone>GMT-05:00</Time_Zone>
<NTP_Server>pool.ntp.org</NTP_Server>
<Daylight_Saving_Time_Enable>Yes</Daylight_Saving_Time_Enable>
<Daylight_Saving_Time_Rule>start=3/-1/7/2;end=11/-1/7/2;save=1</Daylight_Saving_Time_Rule>

<!-- Line 1 Configuration -->
<Line_Enable_1_>Yes</Line_Enable_1_>
<Display_Name_1_>{{EXTENSION_NAME}}</Display_Name_1_>
<User_ID_1_>{{EXTENSION_NUMBER}}</User_ID_1_>
<Auth_ID_1_>{{EXTENSION_NUMBER}}</Auth_ID_1_>
<Password_1_>{{EXTENSION_PASSWORD}}</Password_1_>
<Proxy_1_>{{SIP_SERVER}}</Proxy_1_>
<Register_1_>Yes</Register_1_>
<Register_Expires_1_>3600</Register_Expires_1_>

<!-- Codecs - Optimized for analog and fax -->
<Preferred_Codec_1_>G711u</Preferred_Codec_1_>
<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>
<Third_Preferred_Codec_1_>G729a</Third_Preferred_Codec_1_>
<G729a_Enable_1_>Yes</G729a_Enable_1_>
<G711u_Enable_1_>Yes</G711u_Enable_1_>
<G711a_Enable_1_>Yes</G711a_Enable_1_>

<!-- DTMF -->
<DTMF_Tx_Method_1_>Auto</DTMF_Tx_Method_1_>
<DTMF_Tx_Mode_1_>Strict</DTMF_Tx_Mode_1_>
<RTP_Packet_Size_1_>0.020</RTP_Packet_Size_1_>

<!-- Fax - T.38 -->
<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>
<FAX_T38_Redundancy_1_>1</FAX_T38_Redundancy_1_>
<FAX_Passthru_Method_1_>NSE</FAX_Passthru_Method_1_>

<!-- Voice Processing -->
<Silence_Supp_Enable_1_>No</Silence_Supp_Enable_1_>
<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>
<Echo_Canc_Adapt_Enable_1_>Yes</Echo_Canc_Adapt_Enable_1_>
<Echo_Supp_Enable_1_>Yes</Echo_Supp_Enable_1_>

<!-- Caller ID -->
<Caller_ID_Method_1_>Bellcore(N.Amer,China)</Caller_ID_Method_1_>
<Caller_ID_FSK_Standard_1_>bell202</Caller_ID_FSK_Standard_1_>

<!-- Audio -->
<Txgain_1_>0</Txgain_1_>
<Rxgain_1_>0</Rxgain_1_>

<!-- Line 2 Disabled by Default -->
<Line_Enable_2_>No</Line_Enable_2_>

<!-- Router Configuration (SPA122 specific) -->
<WAN_Connection_Type>DHCP</WAN_Connection_Type>
<Router_Enable>Yes</Router_Enable>
<LAN_IP_Address>192.168.0.1</LAN_IP_Address>
<LAN_Netmask>255.255.255.0</LAN_Netmask>
<DHCP_Server_Enable>Yes</DHCP_Server_Enable>
<DHCP_Starting_IP>192.168.0.100</DHCP_Starting_IP>
<DHCP_Number_of_Users>50</DHCP_Number_of_Users>
<DHCP_Lease_Time>1440</DHCP_Lease_Time>

<!-- System Parameters -->
<Primary_NTP_Server>pool.ntp.org</Primary_NTP_Server>
<Secondary_NTP_Server>time.google.com</Secondary_NTP_Server>

<!-- SIP -->
<SIP_Port>{{SIP_PORT}}</SIP_Port>
<RTP_Port_Min>16384</RTP_Port_Min>
<RTP_Port_Max>16482</RTP_Port_Max>
<SIP_TOS_DiffServ_Value>0x68</SIP_TOS_DiffServ_Value>
<RTP_TOS_DiffServ_Value>0xb8</RTP_TOS_DiffServ_Value>

<!-- Regional Settings (FCC/North America) -->
<Ring_Waveform>Sinusoid</Ring_Waveform>
<Ring_Frequency>20</Ring_Frequency>
<Ring_Voltage>75</Ring_Voltage>
<FXS_Port_Impedance>600</FXS_Port_Impedance>
<Hook_Flash_Timer_Min>0.1</Hook_Flash_Timer_Min>
<Hook_Flash_Timer_Max>0.9</Hook_Flash_Timer_Max>
<Enable_QOS>Yes</Enable_QOS>
</flat-profile>
"""
        self.add_template("cisco", "spa122", cisco_spa122_template)

        # Cisco ATA 191 (2-Port Enterprise ATA) template
        cisco_ata191_template = """<flat-profile>
<Provision_Enable>No</Provision_Enable>
<Resync_On_Reset>Yes</Resync_On_Reset>
<Resync_Random_Delay>2</Resync_Random_Delay>
<Resync_Periodic>3600</Resync_Periodic>

<!-- Regional Parameters -->
<Time_Zone>GMT-05:00</Time_Zone>
<Primary_NTP_Server>pool.ntp.org</Primary_NTP_Server>
<Secondary_NTP_Server>time.google.com</Secondary_NTP_Server>
<Daylight_Saving_Time_Enable>Yes</Daylight_Saving_Time_Enable>
<Daylight_Saving_Time_Rule>start=3/-1/7/2;end=11/-1/7/2;save=1</Daylight_Saving_Time_Rule>

<!-- Line 1 Configuration -->
<Line_Enable_1_>Yes</Line_Enable_1_>
<Display_Name_1_>{{EXTENSION_NAME}}</Display_Name_1_>
<User_ID_1_>{{EXTENSION_NUMBER}}</User_ID_1_>
<Auth_ID_1_>{{EXTENSION_NUMBER}}</Auth_ID_1_>
<Password_1_>{{EXTENSION_PASSWORD}}</Password_1_>
<Proxy_1_>{{SIP_SERVER}}</Proxy_1_>
<Register_1_>Yes</Register_1_>
<Register_Expires_1_>3600</Register_Expires_1_>

<!-- Codecs - Optimized for analog and fax -->
<Preferred_Codec_1_>G711u</Preferred_Codec_1_>
<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>
<Third_Preferred_Codec_1_>G729a</Third_Preferred_Codec_1_>
<G729a_Enable_1_>Yes</G729a_Enable_1_>
<G711u_Enable_1_>Yes</G711u_Enable_1_>
<G711a_Enable_1_>Yes</G711a_Enable_1_>
<G726-16_Enable_1_>No</G726-16_Enable_1_>
<G726-24_Enable_1_>No</G726-24_Enable_1_>
<G726-32_Enable_1_>No</G726-32_Enable_1_>
<G726-40_Enable_1_>No</G726-40_Enable_1_>
<G722_Enable_1_>No</G722_Enable_1_>
<iLBC_Enable_1_>No</iLBC_Enable_1_>

<!-- DTMF -->
<DTMF_Tx_Method_1_>AVT</DTMF_Tx_Method_1_>
<DTMF_Tx_Mode_1_>Strict</DTMF_Tx_Mode_1_>
<Hook_Flash_Tx_Method_1_>None</Hook_Flash_Tx_Method_1_>
<RTP_Packet_Size_1_>0.020</RTP_Packet_Size_1_>

<!-- Fax - T.38 -->
<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>
<FAX_Codec_Symmetric_1_>Yes</FAX_Codec_Symmetric_1_>
<FAX_T38_Redundancy_1_>1</FAX_T38_Redundancy_1_>
<FAX_Passthru_Method_1_>NSE</FAX_Passthru_Method_1_>
<FAX_Passthru_Codec_1_>G711u</FAX_Passthru_Codec_1_>
<FAX_Disable_ECAN_1_>Yes</FAX_Disable_ECAN_1_>

<!-- Voice Processing -->
<Silence_Supp_Enable_1_>No</Silence_Supp_Enable_1_>
<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>
<Echo_Canc_Adapt_Enable_1_>Yes</Echo_Canc_Adapt_Enable_1_>
<Echo_Supp_Enable_1_>Yes</Echo_Supp_Enable_1_>

<!-- Caller ID -->
<Caller_ID_Method_1_>Bellcore(N.Amer,China)</Caller_ID_Method_1_>
<Caller_ID_FSK_Standard_1_>bell202</Caller_ID_FSK_Standard_1_>

<!-- Audio -->
<Txgain_1_>0</Txgain_1_>
<Rxgain_1_>0</Rxgain_1_>

<!-- Call Features -->
<Call_Waiting_Serv_1_>Yes</Call_Waiting_Serv_1_>
<DND_Serv_1_>No</DND_Serv_1_>

<!-- Line 2 Disabled by Default -->
<Line_Enable_2_>No</Line_Enable_2_>

<!-- Network -->
<Internet_Connection_Type>DHCP</Internet_Connection_Type>
<Enable_VLAN>No</Enable_VLAN>
<PoE_Enable>Yes</PoE_Enable>

<!-- SIP -->
<SIP_Port>{{SIP_PORT}}</SIP_Port>
<RTP_Port_Min>16384</RTP_Port_Min>
<RTP_Port_Max>16482</RTP_Port_Max>
<SIP_Transport_1_>UDP</SIP_Transport_1_>

<!-- QoS -->
<SIP_TOS_DiffServ_Value>0x68</SIP_TOS_DiffServ_Value>
<RTP_TOS_DiffServ_Value>0xb8</RTP_TOS_DiffServ_Value>
<Enable_QOS>Yes</Enable_QOS>

<!-- Regional Settings (FCC/North America) -->
<Ring_Waveform>Sinusoid</Ring_Waveform>
<Ring_Frequency>20</Ring_Frequency>
<Ring_Voltage>75</Ring_Voltage>
<FXS_Port_Impedance>600</FXS_Port_Impedance>
<Hook_Flash_Timer_Min>0.1</Hook_Flash_Timer_Min>
<Hook_Flash_Timer_Max>0.9</Hook_Flash_Timer_Max>

<!-- Dial Plan -->
<Dial_Plan_1_>(xxxxxxxxxxxx|*x|*xx|*xxx|*xxxx|xxxxxxxxxx|xxxxxxxxxxx|1xxxxxxxxxx|1xxxxxxxxxxx|011xx.)</Dial_Plan_1_>
<Interdigit_Long_Timer>10</Interdigit_Long_Timer>
<Interdigit_Short_Timer>3</Interdigit_Short_Timer>
</flat-profile>
"""
        self.add_template("cisco", "ata191", cisco_ata191_template)

        # Cisco ATA 192 (2-Port Enterprise ATA) template
        cisco_ata192_template = """<flat-profile>
<Provision_Enable>No</Provision_Enable>
<Resync_On_Reset>Yes</Resync_On_Reset>
<Resync_Random_Delay>2</Resync_Random_Delay>
<Resync_Periodic>3600</Resync_Periodic>

<!-- Regional Parameters -->
<Time_Zone>GMT-05:00</Time_Zone>
<Primary_NTP_Server>pool.ntp.org</Primary_NTP_Server>
<Secondary_NTP_Server>time.google.com</Secondary_NTP_Server>
<Daylight_Saving_Time_Enable>Yes</Daylight_Saving_Time_Enable>
<Daylight_Saving_Time_Rule>start=3/-1/7/2;end=11/-1/7/2;save=1</Daylight_Saving_Time_Rule>

<!-- Line 1 Configuration -->
<Line_Enable_1_>Yes</Line_Enable_1_>
<Display_Name_1_>{{EXTENSION_NAME}}</Display_Name_1_>
<User_ID_1_>{{EXTENSION_NUMBER}}</User_ID_1_>
<Auth_ID_1_>{{EXTENSION_NUMBER}}</Auth_ID_1_>
<Password_1_>{{EXTENSION_PASSWORD}}</Password_1_>
<Proxy_1_>{{SIP_SERVER}}</Proxy_1_>
<Register_1_>Yes</Register_1_>
<Register_Expires_1_>3600</Register_Expires_1_>

<!-- Codecs - Optimized for analog and fax -->
<Preferred_Codec_1_>G711u</Preferred_Codec_1_>
<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>
<Third_Preferred_Codec_1_>G729a</Third_Preferred_Codec_1_>
<G729a_Enable_1_>Yes</G729a_Enable_1_>
<G711u_Enable_1_>Yes</G711u_Enable_1_>
<G711a_Enable_1_>Yes</G711a_Enable_1_>
<G726-16_Enable_1_>No</G726-16_Enable_1_>
<G726-24_Enable_1_>No</G726-24_Enable_1_>
<G726-32_Enable_1_>No</G726-32_Enable_1_>
<G726-40_Enable_1_>No</G726-40_Enable_1_>
<G722_Enable_1_>No</G722_Enable_1_>
<iLBC_Enable_1_>No</iLBC_Enable_1_>

<!-- DTMF -->
<DTMF_Tx_Method_1_>AVT</DTMF_Tx_Method_1_>
<DTMF_Tx_Mode_1_>Strict</DTMF_Tx_Mode_1_>
<Hook_Flash_Tx_Method_1_>None</Hook_Flash_Tx_Method_1_>
<RTP_Packet_Size_1_>0.020</RTP_Packet_Size_1_>

<!-- Fax - T.38 -->
<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>
<FAX_Codec_Symmetric_1_>Yes</FAX_Codec_Symmetric_1_>
<FAX_T38_Redundancy_1_>1</FAX_T38_Redundancy_1_>
<FAX_Passthru_Method_1_>NSE</FAX_Passthru_Method_1_>
<FAX_Passthru_Codec_1_>G711u</FAX_Passthru_Codec_1_>
<FAX_Disable_ECAN_1_>Yes</FAX_Disable_ECAN_1_>

<!-- Voice Processing -->
<Silence_Supp_Enable_1_>No</Silence_Supp_Enable_1_>
<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>
<Echo_Canc_Adapt_Enable_1_>Yes</Echo_Canc_Adapt_Enable_1_>
<Echo_Supp_Enable_1_>Yes</Echo_Supp_Enable_1_>

<!-- Caller ID -->
<Caller_ID_Method_1_>Bellcore(N.Amer,China)</Caller_ID_Method_1_>
<Caller_ID_FSK_Standard_1_>bell202</Caller_ID_FSK_Standard_1_>

<!-- Audio -->
<Txgain_1_>0</Txgain_1_>
<Rxgain_1_>0</Rxgain_1_>

<!-- Call Features -->
<Call_Waiting_Serv_1_>Yes</Call_Waiting_Serv_1_>
<DND_Serv_1_>No</DND_Serv_1_>

<!-- Line 2 Disabled by Default -->
<Line_Enable_2_>No</Line_Enable_2_>

<!-- Network -->
<Internet_Connection_Type>DHCP</Internet_Connection_Type>
<Enable_VLAN>No</Enable_VLAN>

<!-- SIP -->
<SIP_Port>{{SIP_PORT}}</SIP_Port>
<RTP_Port_Min>16384</RTP_Port_Min>
<RTP_Port_Max>16482</RTP_Port_Max>
<SIP_Transport_1_>UDP</SIP_Transport_1_>

<!-- QoS -->
<SIP_TOS_DiffServ_Value>0x68</SIP_TOS_DiffServ_Value>
<RTP_TOS_DiffServ_Value>0xb8</RTP_TOS_DiffServ_Value>
<Enable_QOS>Yes</Enable_QOS>

<!-- Regional Settings (FCC/North America) -->
<Ring_Waveform>Sinusoid</Ring_Waveform>
<Ring_Frequency>20</Ring_Frequency>
<Ring_Voltage>75</Ring_Voltage>
<FXS_Port_Impedance>600</FXS_Port_Impedance>
<Hook_Flash_Timer_Min>0.1</Hook_Flash_Timer_Min>
<Hook_Flash_Timer_Max>0.9</Hook_Flash_Timer_Max>

<!-- Dial Plan -->
<Dial_Plan_1_>(xxxxxxxxxxxx|*x|*xx|*xxx|*xxxx|xxxxxxxxxx|xxxxxxxxxxx|1xxxxxxxxxx|1xxxxxxxxxxx|011xx.)</Dial_Plan_1_>
<Interdigit_Long_Timer>10</Interdigit_Long_Timer>
<Interdigit_Short_Timer>3</Interdigit_Short_Timer>

<!-- Multiplatform -->
<Multiplatform_Enable>Yes</Multiplatform_Enable>
</flat-profile>
"""
        self.add_template("cisco", "ata192", cisco_ata192_template)

        self.logger.info(f"Loaded {len(self.templates)} built-in phone templates (including ATAs)")

    def _load_custom_templates(self) -> None:
        """Load custom templates from configuration"""
        custom_templates_dir = self.config.get("provisioning.custom_templates_dir", None)

        if custom_templates_dir and Path(custom_templates_dir).exists():
            try:
                for entry in Path(custom_templates_dir).iterdir():
                    filename = entry.name
                    if filename.endswith(".template"):
                        filepath = entry
                        # Parse filename: vendor_model.template
                        parts = filename.replace(".template", "").split("_")
                        if len(parts) >= 2:
                            vendor = parts[0]
                            model = "_".join(parts[1:])

                            with filepath.open() as f:
                                template_content = f.read()

                            self.add_template(vendor, model, template_content)
                            self.logger.info(f"Loaded custom template for {vendor} {model}")
            except OSError as e:
                self.logger.error(f"Error loading custom templates: {e}")

    def add_template(self, vendor: str, model: str, template_content: str) -> None:
        """
        Add a phone template

        Args:
            vendor: Phone vendor
            model: Phone model
            template_content: Template string
        """
        key = (vendor.lower(), model.lower())
        self.templates[key] = PhoneTemplate(vendor, model, template_content)

    def get_template(self, vendor: str, model: str) -> Any | None:
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

    def register_device(
        self, mac_address: str, extension_number: str, vendor: str, model: str
    ) -> Any:
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

    def unregister_device(self, mac_address: str) -> bool:
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

    def get_device(self, mac_address: str) -> Any | None:
        """
        Get device by MAC address

        Args:
            mac_address: Device MAC address

        Returns:
            ProvisioningDevice or None
        """
        normalized_mac = normalize_mac_address(mac_address)
        return self.devices.get(normalized_mac)

    def get_all_devices(self) -> list:
        """
        Get all registered devices

        Returns:
            list of ProvisioningDevice objects
        """
        return list(self.devices.values())

    def get_atas(self) -> list:
        """
        Get all registered ATA devices

        Returns:
            list of ProvisioningDevice objects (ATAs only)
        """
        return [device for device in self.devices.values() if device.is_ata()]

    def get_phones(self) -> list:
        """
        Get all registered phone devices (excluding ATAs)

        Returns:
            list of ProvisioningDevice objects (phones only)
        """
        return [device for device in self.devices.values() if not device.is_ata()]

    def _build_ldap_phonebook_config(self) -> dict:
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

    def generate_config(
        self, mac_address: str, extension_registry: str, request_info: dict | None = None
    ) -> tuple:
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
            "timestamp": datetime.now(UTC).isoformat(),
            "mac_address": mac_address,
            "normalized_mac": normalize_mac_address(mac_address),
            "ip_address": request_info.get("ip") if request_info else None,
            "user_agent": request_info.get("user_agent") if request_info else None,
            "success": False,
            "error": None,
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
            self.logger.warning(f"  Registered devices: {list(self.devices)}")

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
            similar_macs = [m for m in self.devices if m.startswith(mac_prefix)]
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
            self.logger.warning(f"  Available templates: {list(self.templates)}")
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

        self.logger.info(f"  Extension found: {extension.number} ({extension.name})")

        # Build extension config dict
        sip_password = extension.config.get("password", "")

        # If no SIP password is set, use a default based on extension number
        # This ensures phones can register even if sip_password is not explicitly set
        if not sip_password:
            sip_password = f"ext{extension.number}"
            self.logger.warning(
                f"  No SIP password found for extension {extension.number}. "
                f"Using default password format. Recommend setting explicit SIP password in database."
            )

        extension_config = {
            "number": extension.number,
            "name": extension.name,
            "password": sip_password,
        }

        # Build server config dict
        server_ip = self.config.get("server.external_ip", "127.0.0.1")
        api_port = self.config.get("api.port", 9000)
        server_config = {
            "sip_host": server_ip,
            "sip_port": self.config.get("server.sip_port", 5060),
            "server_name": self.config.get("server.server_name", "PBX"),
            "provision_resource_url": f"http://{server_ip}:{api_port}/provision/resources",
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

    def _add_request_log(self, request_log: dict) -> None:
        """Add request to history, keeping only recent requests"""
        self.provision_requests.append(request_log)
        # Keep only the last N requests
        if len(self.provision_requests) > self.max_request_history:
            self.provision_requests = self.provision_requests[-self.max_request_history :]

    def get_request_history(self, limit: int | None = None) -> list:
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

    def _generate_config_url(self, mac_address: str) -> str:
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

    def get_supported_vendors(self) -> list:
        """
        Get list of supported vendors

        Returns:
            list of vendor names
        """
        vendors = set()
        for vendor, _model in self.templates:
            vendors.add(vendor)
        return sorted(vendors)

    def get_supported_models(self, vendor: str | None = None) -> list:
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
            for v, m in self.templates:
                if v == vendor:
                    models.append(m)
            return sorted(models)
        # Return dict of vendor -> models
        result = {}
        for v, m in self.templates:
            if v not in result:
                result[v] = []
            result[v].append(m)
        # Sort each vendor's models
        for v, models in result.items():
            result[v] = sorted(models)
        return result

    def reboot_phone(self, extension_number: str, sip_server: Any) -> bool:
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
                call_id=f"notify-reboot-{extension_number}-{datetime.now(UTC).timestamp()}",
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

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error sending reboot NOTIFY to extension {extension_number}: {e}")
            return False

    def reboot_all_phones(self, sip_server: Any) -> dict:
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

    def list_all_templates(self) -> list:
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
            template_path = Path(custom_dir) / template_filename

            if Path(template_path).exists():
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

    def get_template_content(self, vendor: str, model: str) -> Any | None:
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

    def export_template_to_file(self, vendor: str, model: str) -> tuple:
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
        if not Path(custom_dir).exists():
            try:
                Path(custom_dir).mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created custom templates directory: {custom_dir}")
            except OSError as e:
                return False, f"Failed to create directory: {e}", None

        # Write template to file
        template_filename = f"{vendor.lower()}_{model.lower()}.template"
        template_path = Path(custom_dir) / template_filename

        try:
            with template_path.open("w") as f:
                f.write(template.template_content)

            self.logger.info(f"Exported template to: {template_path}")
            return True, f"Template exported to {template_path}", template_path
        except OSError as e:
            self.logger.error(f"Failed to export template: {e}")
            return False, f"Failed to export template: {e}", None

    def update_template(self, vendor: str, model: str, content: str) -> tuple:
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
        if not Path(custom_dir).exists():
            try:
                Path(custom_dir).mkdir(parents=True, exist_ok=True)
            except OSError as e:
                return False, f"Failed to create directory: {e}"

        # Write template to file
        template_filename = f"{vendor.lower()}_{model.lower()}.template"
        template_path = Path(custom_dir) / template_filename

        try:
            with template_path.open("w") as f:
                f.write(content)

            # Update in memory
            self.add_template(vendor, model, content)

            self.logger.info(f"Updated template: {vendor} {model}")
            return True, "Template updated successfully"
        except OSError as e:
            self.logger.error(f"Failed to update template: {e}")
            return False, f"Failed to update template: {e}"

    def set_static_ip(self, mac_address: str, static_ip: str) -> tuple:
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
                return False, "Failed to update static IP in database"
            except Exception as e:
                self.logger.error(f"Failed to set static IP: {e}")
                return False, f"Failed to set static IP: {e}"
        else:
            return False, "Database not available - static IP mapping requires database"

    def get_static_ip(self, mac_address: str) -> Any | None:
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
            except (KeyError, TypeError, ValueError) as e:
                self.logger.error(f"Failed to get static IP: {e}")

        return None

    def reload_templates(self) -> tuple:
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
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to reload templates: {e}")
            return False, f"Failed to reload templates: {e}", None
