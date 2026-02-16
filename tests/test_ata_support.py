"""
Test ATA (Analog Telephone Adapter) Support

This module tests the provisioning and configuration of ATAs including:
- Grandstream HT801/HT802
- Cisco SPA112/SPA122
- Cisco ATA 191/192
"""

from typing import Any

import pytest

from pbx.features.phone_provisioning import PhoneProvisioning


class MockConfig:
    """Mock configuration object for testing"""

    def __init__(self) -> None:
        self.data = {
            "server": {"sip_host": "192.168.1.10", "sip_port": 5060, "external_ip": "192.168.1.10"},
            "api": {"port": 9000, "ssl": {"enabled": False}},
            "provisioning": {
                "enabled": True,
                "custom_templates_dir": "provisioning_templates",
                "url_format": "http://{{SERVER_IP}}:{{PORT}}/provision/{mac}.cfg",
            },
            "features": {"dtmf": {"payload_type": 101}},
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key"""
        keys = key.split(".")
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value if value is not None else default


@pytest.fixture
def mock_config() -> MockConfig:
    """Fixture providing mock configuration"""
    return MockConfig()


@pytest.fixture
def provisioning(mock_config: MockConfig) -> PhoneProvisioning:
    """Fixture providing PhoneProvisioning instance"""
    return PhoneProvisioning(mock_config)


class TestATATemplates:
    """Test ATA template availability"""

    def test_grandstream_ht801_template_exists(self, provisioning: PhoneProvisioning) -> None:
        """Test that Grandstream HT801 template is available"""
        template = provisioning.get_template("grandstream", "ht801")
        assert template is not None
        assert template.vendor == "grandstream"
        assert template.model == "ht801"

    def test_grandstream_ht802_template_exists(self, provisioning: PhoneProvisioning) -> None:
        """Test that Grandstream HT802 template is available"""
        template = provisioning.get_template("grandstream", "ht802")
        assert template is not None
        assert template.vendor == "grandstream"
        assert template.model == "ht802"

    def test_cisco_spa112_template_exists(self, provisioning: PhoneProvisioning) -> None:
        """Test that Cisco SPA112 template is available"""
        template = provisioning.get_template("cisco", "spa112")
        assert template is not None
        assert template.vendor == "cisco"
        assert template.model == "spa112"

    def test_cisco_spa122_template_exists(self, provisioning: PhoneProvisioning) -> None:
        """Test that Cisco SPA122 template is available"""
        template = provisioning.get_template("cisco", "spa122")
        assert template is not None
        assert template.vendor == "cisco"
        assert template.model == "spa122"

    def test_cisco_ata191_template_exists(self, provisioning: PhoneProvisioning) -> None:
        """Test that Cisco ATA 191 template is available"""
        template = provisioning.get_template("cisco", "ata191")
        assert template is not None
        assert template.vendor == "cisco"
        assert template.model == "ata191"

    def test_cisco_ata192_template_exists(self, provisioning: PhoneProvisioning) -> None:
        """Test that Cisco ATA 192 template is available"""
        template = provisioning.get_template("cisco", "ata192")
        assert template is not None
        assert template.vendor == "cisco"
        assert template.model == "ata192"


class TestATAConfiguration:
    """Test ATA configuration generation"""

    def test_ht801_configuration(self, provisioning: PhoneProvisioning) -> None:
        """Test Grandstream HT801 configuration generation"""
        template = provisioning.get_template("grandstream", "ht801")
        assert template is not None

        extension_config = {
            "number": "1001",
            "name": "Conference Room",
            "password": "secure_password_123",
        }

        server_config = {
            "sip_host": "192.168.1.10",
            "sip_port": "5060",
            "server_name": "TestPBX",
            "dtmf": {"payload_type": "101"},
        }

        config = template.generate_config(extension_config, server_config)

        # Verify key parameters are set
        assert "P270 = 1001" in config  # SIP User ID
        assert "P271 = Conference Room" in config  # Account Name
        assert "P34 = secure_password_123" in config  # Password
        assert "P47 = 192.168.1.10" in config  # SIP Server
        assert "P48 = 5060" in config  # SIP Port

        # Verify ATA-specific settings
        assert "P79 = 2" in config  # DTMF Type (SIP INFO)
        assert "P191 = 1" in config  # Echo Cancellation
        assert "P245 = 1" in config  # T.38 Fax Mode

    def test_ht802_configuration(self, provisioning: PhoneProvisioning) -> None:
        """Test Grandstream HT802 configuration generation (2-port)"""
        template = provisioning.get_template("grandstream", "ht802")
        assert template is not None

        extension_config = {"number": "1002", "name": "Fax Machine", "password": "fax_pass_456"}

        server_config = {
            "sip_host": "10.0.0.5",
            "sip_port": "5060",
            "dtmf": {"payload_type": "101"},
        }

        config = template.generate_config(extension_config, server_config)

        # Verify configuration
        assert "P270 = 1002" in config
        assert "P271 = Fax Machine" in config
        assert "P47 = 10.0.0.5" in config

        # Verify dual-port ATA specific settings
        assert "P2350 = 1" in config  # Send P-Asserted-Identity
        assert "P2351 = 1" in config  # Send Remote-Party-ID

    def test_spa112_configuration(self, provisioning: PhoneProvisioning) -> None:
        """Test Cisco SPA112 configuration generation"""
        template = provisioning.get_template("cisco", "spa112")
        assert template is not None

        extension_config = {"number": "1003", "name": "Analog Phone", "password": "analog_789"}

        server_config = {
            "sip_host": "172.16.0.1",
            "sip_port": "5060",
            "dtmf": {"payload_type": "101"},
        }

        config = template.generate_config(extension_config, server_config)

        # Verify XML structure
        assert "<flat-profile>" in config
        assert "</flat-profile>" in config

        # Verify configuration values
        assert "<Display_Name_1_>Analog Phone</Display_Name_1_>" in config
        assert "<User_ID_1_>1003</User_ID_1_>" in config
        assert "<Password_1_>analog_789</Password_1_>" in config
        assert "<Proxy_1_>172.16.0.1</Proxy_1_>" in config

        # Verify ATA-specific settings
        assert "<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>" in config
        assert "<Echo_Canc_Enable_1_>Yes</Echo_Canc_Enable_1_>" in config

    def test_spa122_configuration(self, provisioning: PhoneProvisioning) -> None:
        """Test Cisco SPA122 configuration generation (with router)"""
        template = provisioning.get_template("cisco", "spa122")
        assert template is not None

        extension_config = {"number": "1004", "name": "Remote Office", "password": "remote_abc"}

        server_config = {
            "sip_host": "192.168.100.1",
            "sip_port": "5060",
            "dtmf": {"payload_type": "101"},
        }

        config = template.generate_config(extension_config, server_config)

        # Verify configuration
        assert "<Display_Name_1_>Remote Office</Display_Name_1_>" in config
        assert "<User_ID_1_>1004</User_ID_1_>" in config

        # Verify router-specific settings (unique to SPA122)
        assert "<Router_Enable>Yes</Router_Enable>" in config
        assert "<DHCP_Server_Enable>Yes</DHCP_Server_Enable>" in config

    def test_ata191_configuration(self, provisioning: PhoneProvisioning) -> None:
        """Test Cisco ATA 191 configuration generation (enterprise with PoE)"""
        template = provisioning.get_template("cisco", "ata191")
        assert template is not None

        extension_config = {
            "number": "1005",
            "name": "Enterprise Phone",
            "password": "ent_pass_123",
        }

        server_config = {
            "sip_host": "10.0.1.1",
            "sip_port": "5060",
            "dtmf": {"payload_type": "101"},
        }

        config = template.generate_config(extension_config, server_config)

        # Verify configuration
        assert "<Display_Name_1_>Enterprise Phone</Display_Name_1_>" in config
        assert "<User_ID_1_>1005</User_ID_1_>" in config

        # Verify PoE support (unique to ATA 191)
        assert "<PoE_Enable>Yes</PoE_Enable>" in config

    def test_ata192_configuration(self, provisioning: PhoneProvisioning) -> None:
        """Test Cisco ATA 192 configuration generation (multiplatform)"""
        template = provisioning.get_template("cisco", "ata192")
        assert template is not None

        extension_config = {"number": "1006", "name": "Multiplatform ATA", "password": "multi_456"}

        server_config = {
            "sip_host": "10.0.2.1",
            "sip_port": "5060",
            "dtmf": {"payload_type": "101"},
        }

        config = template.generate_config(extension_config, server_config)

        # Verify configuration
        assert "<Display_Name_1_>Multiplatform ATA</Display_Name_1_>" in config
        assert "<User_ID_1_>1006</User_ID_1_>" in config

        # Verify multiplatform support (unique to ATA 192)
        assert "<Multiplatform_Enable>Yes</Multiplatform_Enable>" in config


class TestATADeviceRegistration:
    """Test ATA device registration"""

    def test_register_ht801(self, provisioning: PhoneProvisioning) -> None:
        """Test registering a Grandstream HT801"""
        device = provisioning.register_device(
            mac_address="00:0B:82:11:22:33",
            extension_number="1001",
            vendor="grandstream",
            model="ht801",
        )

        assert device is not None
        assert device.mac_address == "000b82112233"  # Normalized
        assert device.extension_number == "1001"
        assert device.vendor == "grandstream"
        assert device.model == "ht801"
        assert device.device_type == "ata"  # Should be detected as ATA
        assert device.is_ata() is True

    def test_register_spa112(self, provisioning: PhoneProvisioning) -> None:
        """Test registering a Cisco SPA112"""
        device = provisioning.register_device(
            mac_address="00-1D-7E-44-55-66", extension_number="1005", vendor="cisco", model="spa112"
        )

        assert device is not None
        assert device.mac_address == "001d7e445566"  # Normalized
        assert device.extension_number == "1005"
        assert device.vendor == "cisco"
        assert device.model == "spa112"
        assert device.device_type == "ata"  # Should be detected as ATA
        assert device.is_ata() is True

    def test_register_cisco_ata191(self, provisioning: PhoneProvisioning) -> None:
        """Test registering a Cisco ATA 191"""
        device = provisioning.register_device(
            mac_address="00-1D-7E-AA-BB-CC",
            extension_number="1006",
            vendor="cisco",
            model="ata191",
        )

        assert device is not None
        assert device.mac_address == "001d7eaabbcc"
        assert device.extension_number == "1006"
        assert device.vendor == "cisco"
        assert device.model == "ata191"
        assert device.device_type == "ata"
        assert device.is_ata() is True

    def test_register_cisco_ata192(self, provisioning: PhoneProvisioning) -> None:
        """Test registering a Cisco ATA 192"""
        device = provisioning.register_device(
            mac_address="00-1D-7E-CC-DD-EE",
            extension_number="1007",
            vendor="cisco",
            model="ata192",
        )

        assert device is not None
        assert device.device_type == "ata"
        assert device.is_ata() is True

    def test_register_regular_phone(self, provisioning: PhoneProvisioning) -> None:
        """Test registering a regular phone (not ATA)"""
        device = provisioning.register_device(
            mac_address="00-15-65-12-34-56",
            extension_number="2001",
            vendor="yealink",
            model="t46s",
        )

        assert device is not None
        assert device.device_type == "phone"  # Should be detected as phone
        assert device.is_ata() is False

    def test_get_ata_device_by_mac(self, provisioning: PhoneProvisioning) -> None:
        """Test retrieving ATA device by MAC address"""
        # Register device
        provisioning.register_device(
            mac_address="00:0B:82:AA:BB:CC",
            extension_number="1010",
            vendor="grandstream",
            model="ht802",
        )

        # Retrieve device
        device = provisioning.get_device("000b82aabbcc")
        assert device is not None
        assert device.extension_number == "1010"
        assert device.model == "ht802"
        assert device.device_type == "ata"

    def test_get_atas_filter(self, provisioning: PhoneProvisioning) -> None:
        """Test filtering ATAs from all devices"""
        # Register mixed devices
        provisioning.register_device(
            mac_address="00:0B:82:11:11:11",
            extension_number="3001",
            vendor="grandstream",
            model="ht801",
        )
        provisioning.register_device(
            mac_address="00:15:65:22:22:22", extension_number="3002", vendor="yealink", model="t46s"
        )
        provisioning.register_device(
            mac_address="00:1D:7E:33:33:33", extension_number="3003", vendor="cisco", model="ata191"
        )

        # Get all ATAs
        atas = provisioning.get_atas()

        # Verify we got ATAs
        assert len(atas) >= 2

        # Verify all returned devices are ATAs and check specific models
        ata_models = [ata.model for ata in atas]
        assert "ht801" in ata_models
        assert "ata191" in ata_models

        # Verify all are actually ATAs
        for ata in atas:
            assert ata.is_ata() is True

    def test_get_phones_filter(self, provisioning: PhoneProvisioning) -> None:
        """Test filtering phones (excluding ATAs) from all devices"""
        # Register mixed devices
        provisioning.register_device(
            mac_address="00:0B:82:44:44:44",
            extension_number="4001",
            vendor="grandstream",
            model="ht802",
        )
        provisioning.register_device(
            mac_address="00:15:65:55:55:55", extension_number="4002", vendor="yealink", model="t28g"
        )
        provisioning.register_device(
            mac_address="00:15:65:66:66:66",
            extension_number="4003",
            vendor="polycom",
            model="vvx450",
        )

        # Get all phones
        phones = provisioning.get_phones()

        # Verify we got phones
        assert len(phones) >= 2

        # Verify all returned devices are phones and check specific models
        phone_models = [phone.model for phone in phones]
        assert "t28g" in phone_models
        assert "vvx450" in phone_models

        # Verify all are actually phones (not ATAs)
        for phone in phones:
            assert phone.is_ata() is False


class TestATACodecConfiguration:
    """Test ATA codec configuration"""

    def test_ht801_codec_priority(self, provisioning: PhoneProvisioning) -> None:
        """Test that HT801 prioritizes G.711 codecs for analog quality"""
        template = provisioning.get_template("grandstream", "ht801")
        config = template.generate_config(
            {"number": "1001", "name": "Test", "password": "pass"},
            {"sip_host": "10.0.0.1", "sip_port": "5060", "dtmf": {"payload_type": "101"}},
        )

        # G.711 codecs should be first priority
        assert "P57 = 0" in config  # PCMU
        assert "P58 = 8" in config  # PCMA

    def test_spa112_codec_priority(self, provisioning: PhoneProvisioning) -> None:
        """Test that SPA112 prioritizes G.711 codecs"""
        template = provisioning.get_template("cisco", "spa112")
        config = template.generate_config(
            {"number": "1002", "name": "Test", "password": "pass"},
            {"sip_host": "10.0.0.1", "sip_port": "5060", "dtmf": {"payload_type": "101"}},
        )

        # G.711 should be preferred
        assert "<Preferred_Codec_1_>G711u</Preferred_Codec_1_>" in config
        assert "<Second_Preferred_Codec_1_>G711a</Second_Preferred_Codec_1_>" in config


class TestATAFaxSupport:
    """Test fax-specific ATA configuration"""

    def test_ht801_t38_enabled(self, provisioning: PhoneProvisioning) -> None:
        """Test that T.38 fax support is enabled on HT801"""
        template = provisioning.get_template("grandstream", "ht801")
        config = template.generate_config(
            {"number": "1099", "name": "Fax", "password": "fax"},
            {"sip_host": "10.0.0.1", "sip_port": "5060", "dtmf": {"payload_type": "101"}},
        )

        # T.38 should be enabled
        assert "P245 = 1" in config  # T.38 Fax Mode

    def test_spa112_t38_enabled(self, provisioning: PhoneProvisioning) -> None:
        """Test that T.38 fax support is enabled on SPA112"""
        template = provisioning.get_template("cisco", "spa112")
        config = template.generate_config(
            {"number": "1099", "name": "Fax", "password": "fax"},
            {"sip_host": "10.0.0.1", "sip_port": "5060", "dtmf": {"payload_type": "101"}},
        )

        # T.38 should be enabled
        assert "<FAX_Enable_T38_1_>Yes</FAX_Enable_T38_1_>" in config


class TestATADTMFConfiguration:
    """Test DTMF configuration for ATAs"""

    def test_ht801_dtmf_sip_info(self, provisioning: PhoneProvisioning) -> None:
        """Test that HT801 uses SIP INFO for DTMF"""
        template = provisioning.get_template("grandstream", "ht801")
        config = template.generate_config(
            {"number": "1001", "name": "Test", "password": "pass"},
            {"sip_host": "10.0.0.1", "sip_port": "5060", "dtmf": {"payload_type": "101"}},
        )

        # SIP INFO method
        assert "P79 = 2" in config  # DTMF Type: 2=SIP INFO

    def test_spa112_dtmf_auto(self, provisioning: PhoneProvisioning) -> None:
        """Test that SPA112 uses Auto DTMF detection"""
        template = provisioning.get_template("cisco", "spa112")
        config = template.generate_config(
            {"number": "1001", "name": "Test", "password": "pass"},
            {"sip_host": "10.0.0.1", "sip_port": "5060", "dtmf": {"payload_type": "101"}},
        )

        # Auto detection
        assert "<DTMF_Tx_Method_1_>Auto</DTMF_Tx_Method_1_>" in config


class TestDeviceTypeUtility:
    """Test the shared device type detection utility"""

    def test_detect_device_type_cisco_ata191(self) -> None:
        """Test detection of Cisco ATA 191"""
        from pbx.utils.device_types import detect_device_type

        result = detect_device_type("cisco", "ata191")
        assert result == "ata"

    def test_detect_device_type_cisco_ata192(self) -> None:
        """Test detection of Cisco ATA 192"""
        from pbx.utils.device_types import detect_device_type

        result = detect_device_type("cisco", "ata192")
        assert result == "ata"

    def test_detect_device_type_cisco_spa112(self) -> None:
        """Test detection of Cisco SPA112"""
        from pbx.utils.device_types import detect_device_type

        result = detect_device_type("cisco", "spa112")
        assert result == "ata"

    def test_detect_device_type_grandstream_ht801(self) -> None:
        """Test detection of Grandstream HT801"""
        from pbx.utils.device_types import detect_device_type

        result = detect_device_type("grandstream", "ht801")
        assert result == "ata"

    def test_detect_device_type_obihai_obi200(self) -> None:
        """Test detection of Obihai OBi200"""
        from pbx.utils.device_types import detect_device_type

        result = detect_device_type("obihai", "obi200")
        assert result == "ata"

    def test_detect_device_type_regular_phone(self) -> None:
        """Test detection of regular IP phone"""
        from pbx.utils.device_types import detect_device_type

        result = detect_device_type("yealink", "t46s")
        assert result == "phone"

    def test_detect_device_type_keyword_match(self) -> None:
        """Test keyword-based ATA detection"""
        from pbx.utils.device_types import detect_device_type

        # Should match via 'ata' keyword
        result = detect_device_type("unknown", "newata500")
        assert result == "ata"

    def test_detect_device_type_obi_keyword(self) -> None:
        """Test obi keyword detection"""
        from pbx.utils.device_types import detect_device_type

        # Should match via 'obi' keyword
        result = detect_device_type("obihai", "obi999")
        assert result == "ata"

    def test_detect_device_type_case_insensitive(self) -> None:
        """Test that detection is case-insensitive"""
        from pbx.utils.device_types import detect_device_type

        result = detect_device_type("CISCO", "ATA191")
        assert result == "ata"


class TestDatabaseLayerMethods:
    """Test database layer methods for device filtering"""

    def test_list_atas_method_exists(self) -> None:
        """Test that list_atas method exists in ProvisionedDevicesDB"""
        from pbx.utils.database import ProvisionedDevicesDB

        assert hasattr(
            ProvisionedDevicesDB, "list_atas"
        ), "ProvisionedDevicesDB should have list_atas method"

    def test_list_phones_method_exists(self) -> None:
        """Test that list_phones method exists in ProvisionedDevicesDB"""
        from pbx.utils.database import ProvisionedDevicesDB

        assert hasattr(
            ProvisionedDevicesDB, "list_phones"
        ), "ProvisionedDevicesDB should have list_phones method"

    def test_list_by_type_method_exists(self) -> None:
        """Test that list_by_type method exists in ProvisionedDevicesDB"""
        from pbx.utils.database import ProvisionedDevicesDB

        assert hasattr(
            ProvisionedDevicesDB, "list_by_type"
        ), "ProvisionedDevicesDB should have list_by_type method"

    def test_detect_device_type_method_uses_utility(self) -> None:
        """Test that _detect_device_type method uses shared utility"""
        import inspect

        from pbx.utils.database import ProvisionedDevicesDB

        source = inspect.getsource(ProvisionedDevicesDB._detect_device_type)
        assert (
            "detect_device_type" in source
        ), "_detect_device_type should call shared utility function"


class TestAPIEndpoints:
    """Test API endpoint structure and security"""

    def test_get_provisioning_atas_endpoint_exists(self) -> None:
        """Test that /api/provisioning/atas endpoint handler exists"""
        from pbx.api.rest_api import PBXAPIHandler

        assert hasattr(
            PBXAPIHandler, "_handle_get_provisioning_atas"
        ), "API should have _handle_get_provisioning_atas method"

    def test_get_provisioning_phones_endpoint_exists(self) -> None:
        """Test that /api/provisioning/phones endpoint handler exists"""
        from pbx.api.rest_api import PBXAPIHandler

        assert hasattr(
            PBXAPIHandler, "_handle_get_provisioning_phones"
        ), "API should have _handle_get_provisioning_phones method"

    def test_get_registered_atas_endpoint_exists(self) -> None:
        """Test that /api/registered-atas endpoint handler exists"""
        from pbx.api.rest_api import PBXAPIHandler

        assert hasattr(
            PBXAPIHandler, "_handle_get_registered_atas"
        ), "API should have _handle_get_registered_atas method"

    def test_get_provisioning_atas_requires_auth(self) -> None:
        """Test that /api/provisioning/atas requires authentication"""
        import inspect

        from pbx.api.rest_api import PBXAPIHandler

        source = inspect.getsource(PBXAPIHandler._handle_get_provisioning_atas)
        assert (
            "_verify_authentication" in source
        ), "_handle_get_provisioning_atas should verify authentication"
        assert (
            "401" in source or "Authentication required" in source
        ), "Should return 401 for unauthenticated requests"

    def test_get_provisioning_phones_requires_auth(self) -> None:
        """Test that /api/provisioning/phones requires authentication"""
        import inspect

        from pbx.api.rest_api import PBXAPIHandler

        source = inspect.getsource(PBXAPIHandler._handle_get_provisioning_phones)
        assert (
            "_verify_authentication" in source
        ), "_handle_get_provisioning_phones should verify authentication"
        assert (
            "401" in source or "Authentication required" in source
        ), "Should return 401 for unauthenticated requests"

    def test_get_registered_atas_requires_auth(self) -> None:
        """Test that /api/registered-atas requires authentication"""
        import inspect

        from pbx.api.rest_api import PBXAPIHandler

        source = inspect.getsource(PBXAPIHandler._handle_get_registered_atas)
        assert (
            "_verify_authentication" in source
        ), "_handle_get_registered_atas should verify authentication"
        assert (
            "401" in source or "Authentication required" in source
        ), "Should return 401 for unauthenticated requests"

    def test_get_registered_atas_requires_admin(self) -> None:
        """Test that /api/registered-atas requires admin privileges"""
        import inspect

        from pbx.api.rest_api import PBXAPIHandler

        source = inspect.getsource(PBXAPIHandler._handle_get_registered_atas)
        assert (
            "admin" in source.lower() and "403" in source
        ), "_handle_get_registered_atas should require admin privileges"
