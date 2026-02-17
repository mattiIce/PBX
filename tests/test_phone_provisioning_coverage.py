"""
Comprehensive tests for pbx/features/phone_provisioning.py

Covers all public classes and methods:
- normalize_mac_address()
- PhoneTemplate
- ProvisioningDevice
- PhoneProvisioning (all public + key private methods)
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(overrides: dict | None = None) -> MagicMock:
    """Build a mock Config whose .get() navigates a nested dict."""
    base = {
        "server": {
            "external_ip": "10.0.0.1",
            "sip_port": 5060,
            "server_name": "TestPBX",
        },
        "api": {
            "port": 9000,
            "ssl": {"enabled": False},
        },
        "provisioning": {},
        "integrations": {
            "active_directory": {"enabled": False},
        },
    }
    if overrides:
        _deep_merge(base, overrides)

    config = MagicMock()

    def _get(key: str, default=None):
        keys = key.split(".")
        value = base
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    config.get.side_effect = _get
    return config


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _make_provisioning(config_overrides: dict | None = None, database=None):
    """Instantiate PhoneProvisioning with mocked logger and config."""
    cfg = _make_config(config_overrides)
    with patch("pbx.features.phone_provisioning.get_logger") as mock_gl:
        mock_gl.return_value = MagicMock()
        prov = _lazy_import().PhoneProvisioning(cfg, database=database)
    return prov


def _lazy_import():
    """Import the module under test (deferred so patches can be applied)."""
    import pbx.features.phone_provisioning as mod

    return mod


# ---------------------------------------------------------------------------
# Tests for normalize_mac_address
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeMacAddress:
    """Tests for the module-level normalize_mac_address() helper."""

    def test_colon_separated(self) -> None:
        mod = _lazy_import()
        assert mod.normalize_mac_address("AA:BB:CC:DD:EE:FF") == "aabbccddeeff"

    def test_dash_separated(self) -> None:
        mod = _lazy_import()
        assert mod.normalize_mac_address("AA-BB-CC-DD-EE-FF") == "aabbccddeeff"

    def test_dot_separated(self) -> None:
        mod = _lazy_import()
        assert mod.normalize_mac_address("AABB.CCDD.EEFF") == "aabbccddeeff"

    def test_already_normalized(self) -> None:
        mod = _lazy_import()
        assert mod.normalize_mac_address("aabbccddeeff") == "aabbccddeeff"

    def test_mixed_case(self) -> None:
        mod = _lazy_import()
        assert mod.normalize_mac_address("aA:Bb:cC:dD:eE:fF") == "aabbccddeeff"

    def test_empty_string(self) -> None:
        mod = _lazy_import()
        assert mod.normalize_mac_address("") == ""


# ---------------------------------------------------------------------------
# Tests for PhoneTemplate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPhoneTemplate:
    """Tests for the PhoneTemplate class."""

    def test_init_stores_lower(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate("Yealink", "T46S", "content")
        assert tpl.vendor == "yealink"
        assert tpl.model == "t46s"
        assert tpl.template_content == "content"

    def test_generate_config_replaces_extension_fields(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate(
            "v", "m", "N={{EXTENSION_NUMBER}} P={{EXTENSION_PASSWORD}} NM={{EXTENSION_NAME}}"
        )
        result = tpl.generate_config(
            {"number": "2001", "name": "Alice", "password": "s3cr3t"},
            {"sip_host": "1.2.3.4"},
        )
        assert "N=2001" in result
        assert "P=s3cr3t" in result
        assert "NM=Alice" in result

    def test_generate_config_replaces_server_fields(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate("v", "m", "H={{SIP_SERVER}} P={{SIP_PORT}} S={{SERVER_NAME}}")
        result = tpl.generate_config(
            {"number": "1"},
            {"sip_host": "10.0.0.5", "sip_port": "5061", "server_name": "MyPBX"},
        )
        assert "H=10.0.0.5" in result
        assert "P=5061" in result
        assert "S=MyPBX" in result

    def test_generate_config_replaces_ldap_fields(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate("v", "m", "LE={{LDAP_ENABLE}} LS={{LDAP_SERVER}} LP={{LDAP_PORT}}")
        result = tpl.generate_config(
            {"number": "1"},
            {"ldap_phonebook": {"enable": "1", "server": "ldap.local", "port": "389"}},
        )
        assert "LE=1" in result
        assert "LS=ldap.local" in result
        assert "LP=389" in result

    def test_generate_config_ldap_defaults(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate(
            "v", "m", "V={{LDAP_VERSION}} T={{LDAP_TLS_MODE}} DN={{LDAP_DISPLAY_NAME}}"
        )
        result = tpl.generate_config({"number": "1"}, {})
        assert "V=3" in result
        assert "T=1" in result
        assert "DN=Company Directory" in result

    def test_generate_config_remote_phonebook(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate(
            "v", "m", "U={{REMOTE_PHONEBOOK_URL}} R={{REMOTE_PHONEBOOK_REFRESH}}"
        )
        result = tpl.generate_config(
            {"number": "1"},
            {"remote_phonebook": {"url": "http://pb.local/dir.xml", "refresh_interval": "30"}},
        )
        assert "U=http://pb.local/dir.xml" in result
        assert "R=30" in result

    def test_generate_config_dtmf(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate("v", "m", "D={{DTMF_PAYLOAD_TYPE}}")
        result = tpl.generate_config({"number": "1"}, {"dtmf": {"payload_type": "96"}})
        assert "D=96" in result

    def test_generate_config_dtmf_default(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate("v", "m", "D={{DTMF_PAYLOAD_TYPE}}")
        result = tpl.generate_config({"number": "1"}, {})
        assert "D=101" in result

    def test_generate_config_missing_keys_use_empty_string(self) -> None:
        mod = _lazy_import()
        tpl = mod.PhoneTemplate("v", "m", "N={{EXTENSION_NUMBER}}")
        result = tpl.generate_config({}, {})
        assert "N=" in result


# ---------------------------------------------------------------------------
# Tests for ProvisioningDevice
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProvisioningDevice:
    """Tests for the ProvisioningDevice class."""

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_init_normalizes_mac(self, _mock_detect) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("AA:BB:CC:DD:EE:FF", "1001", "Yealink", "T46S")
        assert dev.mac_address == "aabbccddeeff"

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_init_lowercases_vendor_model(self, _mock_detect) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "YEALINK", "T46S")
        assert dev.vendor == "yealink"
        assert dev.model == "t46s"

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_auto_detect_device_type(self, mock_detect) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "yealink", "t46s")
        mock_detect.assert_called_once_with("yealink", "t46s")
        assert dev.device_type == "phone"

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_explicit_device_type_skips_detection(self, mock_detect) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "cisco", "spa112", device_type="ata")
        assert dev.device_type == "ata"
        # detect_device_type should not be called when device_type is explicitly provided
        mock_detect.assert_not_called()

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="ata")
    def test_is_ata_true(self, _mock) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "cisco", "spa112")
        assert dev.is_ata() is True

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_is_ata_false(self, _mock) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "yealink", "t46s")
        assert dev.is_ata() is False

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_mark_provisioned(self, _mock) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "yealink", "t46s")
        assert dev.last_provisioned is None
        dev.mark_provisioned()
        assert dev.last_provisioned is not None
        assert isinstance(dev.last_provisioned, datetime)

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_to_dict(self, _mock) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "yealink", "t46s", config_url="http://x")
        d = dev.to_dict()
        assert d["mac_address"] == "aabb"
        assert d["extension_number"] == "1001"
        assert d["vendor"] == "yealink"
        assert d["model"] == "t46s"
        assert d["device_type"] == "phone"
        assert d["config_url"] == "http://x"
        assert d["created_at"] is not None
        assert d["last_provisioned"] is None

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_to_dict_after_provisioned(self, _mock) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "yealink", "t46s")
        dev.mark_provisioned()
        d = dev.to_dict()
        assert d["last_provisioned"] is not None

    @patch("pbx.features.phone_provisioning.detect_device_type", return_value="phone")
    def test_created_at_is_utc(self, _mock) -> None:
        mod = _lazy_import()
        dev = mod.ProvisioningDevice("aabb", "1001", "yealink", "t46s")
        assert dev.created_at.tzinfo is not None


# ---------------------------------------------------------------------------
# Tests for PhoneProvisioning.__init__
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPhoneProvisioningInit:
    """Tests for PhoneProvisioning initialization."""

    def test_init_without_database(self) -> None:
        prov = _make_provisioning()
        assert prov.devices == {}
        assert prov.devices_db is None
        assert len(prov.templates) > 0

    def test_init_with_database_disabled(self) -> None:
        db = MagicMock()
        db.enabled = False
        prov = _make_provisioning(database=db)
        assert prov.devices_db is None

    @patch("pbx.features.phone_provisioning.get_logger")
    def test_init_with_database_enabled(self, mock_gl) -> None:
        mock_gl.return_value = MagicMock()
        db = MagicMock()
        db.enabled = True

        mock_devices_db = MagicMock()
        mock_devices_db.list_all.return_value = []

        cfg = _make_config()
        with patch("pbx.utils.database.ProvisionedDevicesDB", return_value=mock_devices_db):
            mod = _lazy_import()
            prov = mod.PhoneProvisioning(cfg, database=db)

        assert prov.devices_db is not None

    @patch("pbx.features.phone_provisioning.get_logger")
    def test_init_ssl_enabled_logs_warnings(self, mock_gl) -> None:
        mock_logger = MagicMock()
        mock_gl.return_value = mock_logger
        cfg = _make_config({"api": {"ssl": {"enabled": True}}})
        mod = _lazy_import()
        mod.PhoneProvisioning(cfg)
        # Should have logged SSL warnings
        assert mock_logger.warning.called


# ---------------------------------------------------------------------------
# Tests for PhoneProvisioning._load_devices_from_database
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadDevicesFromDatabase:
    """Tests for _load_devices_from_database."""

    @patch("pbx.features.phone_provisioning.get_logger")
    def test_load_devices_populates_cache(self, mock_gl) -> None:
        mock_gl.return_value = MagicMock()
        db = MagicMock()
        db.enabled = True

        mock_devices_db = MagicMock()
        mock_devices_db.list_all.return_value = [
            {
                "mac_address": "aabbccddeeff",
                "extension_number": "1001",
                "vendor": "yealink",
                "model": "t46s",
                "device_type": "phone",
                "created_at": datetime(2025, 1, 1, tzinfo=UTC),
                "last_provisioned": datetime(2025, 1, 2, tzinfo=UTC),
            }
        ]

        cfg = _make_config()
        with patch("pbx.utils.database.ProvisionedDevicesDB", return_value=mock_devices_db):
            mod = _lazy_import()
            prov = mod.PhoneProvisioning(cfg, database=db)

        assert "aabbccddeeff" in prov.devices
        dev = prov.devices["aabbccddeeff"]
        assert dev.extension_number == "1001"
        assert dev.created_at == datetime(2025, 1, 1, tzinfo=UTC)
        assert dev.last_provisioned == datetime(2025, 1, 2, tzinfo=UTC)

    @patch("pbx.features.phone_provisioning.get_logger")
    def test_load_devices_handles_error(self, mock_gl) -> None:
        mock_logger = MagicMock()
        mock_gl.return_value = mock_logger
        db = MagicMock()
        db.enabled = True

        mock_devices_db = MagicMock()
        mock_devices_db.list_all.side_effect = KeyError("bad key")

        cfg = _make_config()
        with patch("pbx.utils.database.ProvisionedDevicesDB", return_value=mock_devices_db):
            mod = _lazy_import()
            prov = mod.PhoneProvisioning(cfg, database=db)

        mock_logger.error.assert_called()
        assert len(prov.devices) == 0

    def test_no_db_does_nothing(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = None
        prov._load_devices_from_database()
        assert len(prov.devices) == 0


# ---------------------------------------------------------------------------
# Tests for _load_builtin_templates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadBuiltinTemplates:
    """Tests for built-in template loading."""

    def test_builtin_templates_loaded(self) -> None:
        prov = _make_provisioning()
        # All expected vendor/model combos
        expected = [
            ("zultys", "zip33g"),
            ("zultys", "zip37g"),
            ("yealink", "t46s"),
            ("yealink", "t28g"),
            ("polycom", "vvx450"),
            ("cisco", "spa504g"),
            ("cisco", "spa112"),
            ("cisco", "spa122"),
            ("cisco", "ata191"),
            ("cisco", "ata192"),
            ("grandstream", "gxp2170"),
            ("grandstream", "ht801"),
            ("grandstream", "ht802"),
        ]
        for vendor, model in expected:
            assert (vendor, model) in prov.templates, f"Missing template: {vendor} {model}"

    def test_builtin_template_count(self) -> None:
        prov = _make_provisioning()
        assert len(prov.templates) == 13


# ---------------------------------------------------------------------------
# Tests for _load_custom_templates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadCustomTemplates:
    """Tests for custom template loading."""

    def test_no_custom_dir_configured(self) -> None:
        prov = _make_provisioning()
        # No custom dir → no error, only built-ins
        assert len(prov.templates) == 13

    @patch("pbx.features.phone_provisioning.get_logger")
    def test_custom_dir_with_template_files(self, mock_gl) -> None:
        mock_gl.return_value = MagicMock()

        # Create a mock file entry
        mock_entry = MagicMock()
        mock_entry.name = "acme_phone100.template"
        mock_entry.open = mock_open(read_data="custom template content")

        cfg = _make_config({"provisioning": {"custom_templates_dir": "/tmp/tpls"}})

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[mock_entry]),
        ):
            mod = _lazy_import()
            prov = mod.PhoneProvisioning(cfg)

        assert ("acme", "phone100") in prov.templates

    @patch("pbx.features.phone_provisioning.get_logger")
    def test_custom_dir_skips_non_template_files(self, mock_gl) -> None:
        mock_gl.return_value = MagicMock()

        mock_entry = MagicMock()
        mock_entry.name = "readme.txt"

        cfg = _make_config({"provisioning": {"custom_templates_dir": "/tmp/tpls"}})

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[mock_entry]),
        ):
            mod = _lazy_import()
            prov = mod.PhoneProvisioning(cfg)

        # Only built-in templates should exist
        assert ("readme", "txt") not in prov.templates

    @patch("pbx.features.phone_provisioning.get_logger")
    def test_custom_dir_os_error(self, mock_gl) -> None:
        mock_logger = MagicMock()
        mock_gl.return_value = mock_logger

        cfg = _make_config({"provisioning": {"custom_templates_dir": "/tmp/tpls"}})

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.iterdir", side_effect=OSError("permission denied")),
        ):
            mod = _lazy_import()
            _prov = mod.PhoneProvisioning(cfg)

        mock_logger.error.assert_called()


# ---------------------------------------------------------------------------
# Tests for add_template / get_template
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAddGetTemplate:
    """Tests for add_template and get_template."""

    def test_add_and_get_template(self) -> None:
        prov = _make_provisioning()
        prov.add_template("NewVendor", "NewModel", "template_data")
        tpl = prov.get_template("newvendor", "newmodel")
        assert tpl is not None
        assert tpl.template_content == "template_data"

    def test_get_template_case_insensitive(self) -> None:
        prov = _make_provisioning()
        prov.add_template("ACME", "PHONE", "data")
        assert prov.get_template("acme", "phone") is not None
        assert prov.get_template("ACME", "PHONE") is not None

    def test_get_template_not_found(self) -> None:
        prov = _make_provisioning()
        assert prov.get_template("nonexistent", "model") is None


# ---------------------------------------------------------------------------
# Tests for register_device / unregister_device / get_device
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeviceRegistration:
    """Tests for device registration lifecycle."""

    def test_register_device_in_memory(self) -> None:
        prov = _make_provisioning()
        dev = prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        assert dev.mac_address == "aabbccddeeff"
        assert dev.extension_number == "1001"
        assert dev.config_url is not None
        assert "aabbccddeeff" in prov.devices

    def test_register_device_with_database(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        dev = prov.register_device("11:22:33:44:55:66", "2001", "cisco", "spa504g")
        prov.devices_db.add_device.assert_called_once()
        assert dev.mac_address == "112233445566"

    def test_register_device_db_save_fails(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.add_device.side_effect = RuntimeError("db error")
        # Should not raise; device still saved in memory
        _dev = prov.register_device("11:22:33:44:55:66", "2001", "cisco", "spa504g")
        assert "112233445566" in prov.devices

    def test_unregister_device_found(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        assert prov.unregister_device("AA:BB:CC:DD:EE:FF") is True
        assert prov.get_device("AA:BB:CC:DD:EE:FF") is None

    def test_unregister_device_not_found(self) -> None:
        prov = _make_provisioning()
        assert prov.unregister_device("00:00:00:00:00:00") is False

    def test_unregister_device_with_database(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        prov.unregister_device("AA:BB:CC:DD:EE:FF")
        prov.devices_db.remove_device.assert_called_once_with("aabbccddeeff")

    def test_unregister_device_db_remove_fails(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        prov.devices_db.remove_device.side_effect = RuntimeError("db fail")
        # Should still return True (removed from memory)
        assert prov.unregister_device("AA:BB:CC:DD:EE:FF") is True
        assert "aabbccddeeff" not in prov.devices

    def test_get_device_normalizes_mac(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        assert prov.get_device("aa-bb-cc-dd-ee-ff") is not None
        assert prov.get_device("AABB.CCDD.EEFF") is not None

    def test_get_device_not_found(self) -> None:
        prov = _make_provisioning()
        assert prov.get_device("00:00:00:00:00:00") is None


# ---------------------------------------------------------------------------
# Tests for get_all_devices / get_atas / get_phones
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeviceLists:
    """Tests for device listing methods."""

    def test_get_all_devices_empty(self) -> None:
        prov = _make_provisioning()
        assert prov.get_all_devices() == []

    def test_get_all_devices(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:01", "1001", "yealink", "t46s")
        prov.register_device("AA:BB:CC:DD:EE:02", "1002", "cisco", "spa504g")
        assert len(prov.get_all_devices()) == 2

    def test_get_atas(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:01", "1001", "yealink", "t46s")
        prov.register_device("AA:BB:CC:DD:EE:02", "1002", "grandstream", "ht801")
        atas = prov.get_atas()
        assert len(atas) == 1
        assert atas[0].model == "ht801"

    def test_get_phones(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:01", "1001", "yealink", "t46s")
        prov.register_device("AA:BB:CC:DD:EE:02", "1002", "grandstream", "ht801")
        phones = prov.get_phones()
        assert len(phones) == 1
        assert phones[0].model == "t46s"

    def test_get_atas_empty(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:01", "1001", "yealink", "t46s")
        assert prov.get_atas() == []

    def test_get_phones_empty(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:01", "1001", "grandstream", "ht801")
        assert prov.get_phones() == []


# ---------------------------------------------------------------------------
# Tests for _build_ldap_phonebook_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildLdapPhonebookConfig:
    """Tests for _build_ldap_phonebook_config."""

    def test_no_ad_no_explicit_returns_defaults(self) -> None:
        prov = _make_provisioning()
        cfg = prov._build_ldap_phonebook_config()
        assert cfg["enable"] == 0
        assert cfg["server"] == ""
        assert cfg["port"] == 636
        assert cfg["display_name"] == "Directory"

    def test_explicit_config_returned(self) -> None:
        prov = _make_provisioning(
            {
                "provisioning": {
                    "ldap_phonebook": {
                        "enable": 1,
                        "server": "ldap.company.com",
                        "port": 389,
                    }
                }
            }
        )
        cfg = prov._build_ldap_phonebook_config()
        assert cfg["enable"] == 1
        assert cfg["server"] == "ldap.company.com"
        assert cfg["port"] == 389

    def test_ad_enabled_ldaps_url(self) -> None:
        prov = _make_provisioning(
            {
                "integrations": {
                    "active_directory": {
                        "enabled": True,
                        "server": "ldaps://ad.company.com",
                        "bind_dn": "CN=admin,DC=company,DC=com",
                        "bind_password": "adpass",
                        "base_dn": "DC=company,DC=com",
                    }
                }
            }
        )
        cfg = prov._build_ldap_phonebook_config()
        assert cfg["enable"] == 1
        assert cfg["server"] == "ad.company.com"
        assert cfg["port"] == 636
        assert cfg["tls_mode"] == 1
        assert cfg["user"] == "CN=admin,DC=company,DC=com"
        assert cfg["password"] == "adpass"
        assert cfg["base"] == "DC=company,DC=com"

    def test_ad_enabled_ldap_url(self) -> None:
        prov = _make_provisioning(
            {
                "integrations": {
                    "active_directory": {
                        "enabled": True,
                        "server": "ldap://ad.company.com",
                        "bind_dn": "CN=admin,DC=company,DC=com",
                        "bind_password": "adpass",
                        "base_dn": "DC=company,DC=com",
                    }
                }
            }
        )
        cfg = prov._build_ldap_phonebook_config()
        assert cfg["port"] == 389
        assert cfg["tls_mode"] == 0

    def test_ad_enabled_ldaps_with_custom_port(self) -> None:
        prov = _make_provisioning(
            {
                "integrations": {
                    "active_directory": {
                        "enabled": True,
                        "server": "ldaps://ad.company.com:3269",
                        "bind_dn": "CN=admin,DC=company,DC=com",
                        "bind_password": "adpass",
                        "base_dn": "DC=company,DC=com",
                    }
                }
            }
        )
        cfg = prov._build_ldap_phonebook_config()
        assert cfg["port"] == 3269
        assert cfg["tls_mode"] == 1

    def test_ad_enabled_no_scheme_defaults_ldaps(self) -> None:
        prov = _make_provisioning(
            {
                "integrations": {
                    "active_directory": {
                        "enabled": True,
                        "server": "ad.company.com",
                        "bind_dn": "CN=admin,DC=company,DC=com",
                        "bind_password": "adpass",
                        "base_dn": "DC=company,DC=com",
                    }
                }
            }
        )
        cfg = prov._build_ldap_phonebook_config()
        assert cfg["tls_mode"] == 1
        assert cfg["port"] == 636

    def test_ad_enabled_invalid_bind_dn_logs_warning(self) -> None:
        prov = _make_provisioning(
            {
                "integrations": {
                    "active_directory": {
                        "enabled": True,
                        "server": "ldaps://ad.company.com",
                        "bind_dn": "admin@company.com",
                        "bind_password": "adpass",
                        "base_dn": "DC=company,DC=com",
                    }
                }
            }
        )
        cfg = prov._build_ldap_phonebook_config()
        # Should still produce config, just with a warning logged
        assert cfg["user"] == "admin@company.com"

    def test_ad_enabled_missing_credentials_falls_through(self) -> None:
        prov = _make_provisioning(
            {
                "integrations": {
                    "active_directory": {
                        "enabled": True,
                        "server": "",
                        "bind_dn": "",
                        "bind_password": "",
                        "base_dn": "",
                    }
                }
            }
        )
        cfg = prov._build_ldap_phonebook_config()
        # Falls through to empty defaults since credentials are missing
        assert cfg["enable"] == 0

    def test_ad_explicit_config_overrides_defaults(self) -> None:
        prov = _make_provisioning(
            {
                "integrations": {
                    "active_directory": {
                        "enabled": True,
                        "server": "ldaps://ad.company.com",
                        "bind_dn": "CN=admin,DC=company,DC=com",
                        "bind_password": "adpass",
                        "base_dn": "DC=company,DC=com",
                    }
                },
                "provisioning": {
                    "ldap_phonebook": {
                        "port": 3269,
                        "display_name": "Corp Directory",
                    }
                },
            }
        )
        cfg = prov._build_ldap_phonebook_config()
        assert cfg["port"] == 3269
        assert cfg["display_name"] == "Corp Directory"


# ---------------------------------------------------------------------------
# Tests for generate_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateConfig:
    """Tests for generate_config."""

    def _setup_for_generate(self, prov):
        """Register a device and create a mock extension registry."""
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")

        ext = MagicMock()
        ext.number = "1001"
        ext.name = "Test User"
        ext.config = {"password": "pass123"}

        registry = MagicMock()
        registry.get.return_value = ext
        registry.get_all.return_value = [ext]
        return registry

    def test_success(self) -> None:
        prov = _make_provisioning()
        registry = self._setup_for_generate(prov)

        config_content, content_type = prov.generate_config("AA:BB:CC:DD:EE:FF", registry)
        assert config_content is not None
        assert content_type == "text/plain"
        assert "1001" in config_content
        assert "Test User" in config_content
        assert "pass123" in config_content

    def test_polycom_returns_xml_content_type(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "polycom", "vvx450")

        ext = MagicMock()
        ext.number = "1001"
        ext.name = "Test"
        ext.config = {"password": "pw"}

        registry = MagicMock()
        registry.get.return_value = ext
        registry.get_all.return_value = [ext]

        _, content_type = prov.generate_config("AA:BB:CC:DD:EE:FF", registry)
        assert content_type == "application/xml"

    def test_device_not_found_returns_none(self) -> None:
        prov = _make_provisioning()
        registry = MagicMock()
        result = prov.generate_config("00:00:00:00:00:00", registry)
        assert result == (None, None)

    def test_template_not_found_returns_none(self) -> None:
        prov = _make_provisioning()
        # Register device with unknown model
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "unknown_vendor", "unknown_model")
        registry = MagicMock()
        result = prov.generate_config("AA:BB:CC:DD:EE:FF", registry)
        assert result == (None, None)

    def test_extension_not_found_returns_none(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")

        registry = MagicMock()
        registry.get.return_value = None
        registry.get_all.return_value = []

        result = prov.generate_config("AA:BB:CC:DD:EE:FF", registry)
        assert result == (None, None)

    def test_marks_device_as_provisioned(self) -> None:
        prov = _make_provisioning()
        registry = self._setup_for_generate(prov)
        prov.generate_config("AA:BB:CC:DD:EE:FF", registry)
        dev = prov.get_device("AA:BB:CC:DD:EE:FF")
        assert dev.last_provisioned is not None

    def test_updates_db_on_success(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        registry = self._setup_for_generate(prov)
        prov.generate_config("AA:BB:CC:DD:EE:FF", registry)
        prov.devices_db.mark_provisioned.assert_called_once_with("aabbccddeeff")

    def test_db_update_failure_does_not_raise(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.mark_provisioned.side_effect = RuntimeError("db fail")
        registry = self._setup_for_generate(prov)
        # Should not raise
        config_content, _ = prov.generate_config("AA:BB:CC:DD:EE:FF", registry)
        assert config_content is not None

    def test_request_info_logged(self) -> None:
        prov = _make_provisioning()
        registry = self._setup_for_generate(prov)
        request_info = {"ip": "192.168.1.50", "user_agent": "Yealink SIP-T46S"}
        prov.generate_config("AA:BB:CC:DD:EE:FF", registry, request_info=request_info)
        assert len(prov.provision_requests) == 1
        assert prov.provision_requests[0]["success"] is True
        assert prov.provision_requests[0]["ip_address"] == "192.168.1.50"

    def test_failed_request_logged(self) -> None:
        prov = _make_provisioning()
        registry = MagicMock()
        prov.generate_config("00:00:00:00:00:00", registry)
        assert len(prov.provision_requests) == 1
        assert prov.provision_requests[0]["success"] is False
        assert prov.provision_requests[0]["error"] is not None

    def test_similar_macs_hint(self) -> None:
        """When an unknown MAC shares the OUI prefix with a registered device."""
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        registry = MagicMock()
        # Same OUI prefix (aabbcc) but different device bytes
        result = prov.generate_config("AA:BB:CC:00:00:00", registry)
        assert result == (None, None)


# ---------------------------------------------------------------------------
# Tests for _add_request_log / get_request_history
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestHistory:
    """Tests for provision request history tracking."""

    def test_add_and_get_history(self) -> None:
        prov = _make_provisioning()
        prov._add_request_log({"ts": 1, "mac": "aa"})
        prov._add_request_log({"ts": 2, "mac": "bb"})
        history = prov.get_request_history()
        assert len(history) == 2

    def test_get_history_with_limit(self) -> None:
        prov = _make_provisioning()
        for i in range(10):
            prov._add_request_log({"ts": i})
        history = prov.get_request_history(limit=3)
        assert len(history) == 3
        assert history[0]["ts"] == 7

    def test_history_trimmed_to_max(self) -> None:
        prov = _make_provisioning()
        prov.max_request_history = 5
        for i in range(10):
            prov._add_request_log({"ts": i})
        assert len(prov.provision_requests) == 5
        assert prov.provision_requests[0]["ts"] == 5

    def test_get_history_no_limit_returns_all(self) -> None:
        prov = _make_provisioning()
        for i in range(5):
            prov._add_request_log({"ts": i})
        assert len(prov.get_request_history()) == 5

    def test_get_history_limit_none(self) -> None:
        prov = _make_provisioning()
        prov._add_request_log({"ts": 1})
        assert len(prov.get_request_history(limit=None)) == 1


# ---------------------------------------------------------------------------
# Tests for _generate_config_url
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateConfigUrl:
    """Tests for _generate_config_url."""

    def test_default_url_format(self) -> None:
        prov = _make_provisioning()
        url = prov._generate_config_url("aabbccddeeff")
        assert "aabbccddeeff" in url
        assert "http://" in url
        assert "10.0.0.1" in url
        assert "9000" in url

    def test_custom_url_format(self) -> None:
        prov = _make_provisioning(
            {
                "provisioning": {
                    "url_format": "tftp://{{SERVER_IP}}/configs/{mac}.cfg",
                }
            }
        )
        url = prov._generate_config_url("aabbccddeeff")
        assert url == "tftp://10.0.0.1/configs/aabbccddeeff.cfg"

    def test_ssl_enabled_still_uses_http(self) -> None:
        prov = _make_provisioning({"api": {"ssl": {"enabled": True}}})
        url = prov._generate_config_url("aabbccddeeff")
        assert "http://" in url


# ---------------------------------------------------------------------------
# Tests for get_supported_vendors / get_supported_models
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSupportedVendorsModels:
    """Tests for vendor/model discovery methods."""

    def test_get_supported_vendors(self) -> None:
        prov = _make_provisioning()
        vendors = prov.get_supported_vendors()
        assert isinstance(vendors, list)
        assert "cisco" in vendors
        assert "yealink" in vendors
        assert "polycom" in vendors
        assert "grandstream" in vendors
        assert "zultys" in vendors
        # Sorted
        assert vendors == sorted(vendors)

    def test_get_supported_models_for_vendor(self) -> None:
        prov = _make_provisioning()
        models = prov.get_supported_models("zultys")
        assert "zip33g" in models
        assert "zip37g" in models
        assert models == sorted(models)

    def test_get_supported_models_for_unknown_vendor(self) -> None:
        prov = _make_provisioning()
        models = prov.get_supported_models("unknown_vendor")
        assert models == []

    def test_get_supported_models_no_vendor(self) -> None:
        prov = _make_provisioning()
        all_models = prov.get_supported_models()
        assert isinstance(all_models, dict)
        assert "cisco" in all_models
        for models in all_models.values():
            assert models == sorted(models)

    def test_get_supported_models_case_insensitive(self) -> None:
        prov = _make_provisioning()
        models = prov.get_supported_models("CISCO")
        assert len(models) > 0


# ---------------------------------------------------------------------------
# Tests for reboot_phone
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRebootPhone:
    """Tests for reboot_phone."""

    def test_reboot_unregistered_extension_returns_false(self) -> None:
        prov = _make_provisioning()
        sip_server = MagicMock()
        ext = MagicMock()
        ext.registered = False
        sip_server.pbx_core.extension_registry.get.return_value = ext
        assert prov.reboot_phone("1001", sip_server) is False

    def test_reboot_no_extension_returns_false(self) -> None:
        prov = _make_provisioning()
        sip_server = MagicMock()
        sip_server.pbx_core.extension_registry.get.return_value = None
        assert prov.reboot_phone("9999", sip_server) is False

    def test_reboot_no_address_returns_false(self) -> None:
        prov = _make_provisioning()
        sip_server = MagicMock()
        ext = MagicMock()
        ext.registered = True
        ext.address = None
        sip_server.pbx_core.extension_registry.get.return_value = ext
        assert prov.reboot_phone("1001", sip_server) is False

    @patch("pbx.features.phone_provisioning.SIPMessageBuilder", create=True)
    def test_reboot_success(self, _mock_builder_import) -> None:
        prov = _make_provisioning()
        sip_server = MagicMock()
        ext = MagicMock()
        ext.registered = True
        ext.address = ("192.168.1.50", 5060)
        ext.number = "1001"
        sip_server.pbx_core.extension_registry.get.return_value = ext
        sip_server.pbx_core.config.get.return_value = "10.0.0.1"

        # Mock the SIPMessageBuilder import
        with patch("pbx.sip.message.SIPMessageBuilder") as mock_builder:
            mock_msg = MagicMock()
            mock_builder.build_request.return_value = mock_msg
            result = prov.reboot_phone("1001", sip_server)

        assert result is True
        sip_server._send_message.assert_called_once()

    def test_reboot_exception_returns_false(self) -> None:
        prov = _make_provisioning()
        sip_server = MagicMock()
        ext = MagicMock()
        ext.registered = True
        ext.address = ("192.168.1.50", 5060)
        ext.number = "1001"
        sip_server.pbx_core.extension_registry.get.return_value = ext
        sip_server.pbx_core.config.get.side_effect = KeyError("bad")
        assert prov.reboot_phone("1001", sip_server) is False


# ---------------------------------------------------------------------------
# Tests for reboot_all_phones
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRebootAllPhones:
    """Tests for reboot_all_phones."""

    def test_reboot_all_empty(self) -> None:
        prov = _make_provisioning()
        sip_server = MagicMock()
        sip_server.pbx_core.extension_registry.get_all.return_value = []
        results = prov.reboot_all_phones(sip_server)
        assert results["success_count"] == 0
        assert results["failed_count"] == 0

    def test_reboot_all_skips_unregistered(self) -> None:
        prov = _make_provisioning()
        sip_server = MagicMock()
        ext = MagicMock()
        ext.registered = False
        sip_server.pbx_core.extension_registry.get_all.return_value = [ext]
        results = prov.reboot_all_phones(sip_server)
        assert results["success_count"] == 0
        assert results["failed_count"] == 0

    def test_reboot_all_mixed_results(self) -> None:
        prov = _make_provisioning()
        sip_server = MagicMock()

        ext1 = MagicMock()
        ext1.registered = True
        ext1.number = "1001"

        ext2 = MagicMock()
        ext2.registered = True
        ext2.number = "1002"

        sip_server.pbx_core.extension_registry.get_all.return_value = [ext1, ext2]

        with patch.object(prov, "reboot_phone", side_effect=[True, False]):
            results = prov.reboot_all_phones(sip_server)

        assert results["success_count"] == 1
        assert results["failed_count"] == 1
        assert "1001" in results["rebooted"]
        assert "1002" in results["failed"]


# ---------------------------------------------------------------------------
# Tests for list_all_templates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListAllTemplates:
    """Tests for list_all_templates."""

    def test_list_all_templates(self) -> None:
        prov = _make_provisioning()
        templates = prov.list_all_templates()
        assert len(templates) == 13
        # Should be sorted by vendor, model
        vendors_models = [(t["vendor"], t["model"]) for t in templates]
        assert vendors_models == sorted(vendors_models)

    def test_template_list_contains_required_fields(self) -> None:
        prov = _make_provisioning()
        templates = prov.list_all_templates()
        for t in templates:
            assert "vendor" in t
            assert "model" in t
            assert "is_custom" in t
            assert "template_path" in t
            assert "size" in t
            assert isinstance(t["size"], int)

    def test_builtin_templates_not_custom(self) -> None:
        prov = _make_provisioning()
        templates = prov.list_all_templates()
        for t in templates:
            # All built-in templates should not appear as custom unless the file exists
            if t["template_path"] == "built-in":
                assert t["is_custom"] is False


# ---------------------------------------------------------------------------
# Tests for get_template_content
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetTemplateContent:
    """Tests for get_template_content."""

    def test_existing_template(self) -> None:
        prov = _make_provisioning()
        content = prov.get_template_content("yealink", "t46s")
        assert content is not None
        assert "Yealink T46S" in content

    def test_nonexistent_template(self) -> None:
        prov = _make_provisioning()
        content = prov.get_template_content("unknown", "model")
        assert content is None


# ---------------------------------------------------------------------------
# Tests for export_template_to_file
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportTemplateToFile:
    """Tests for export_template_to_file."""

    def test_invalid_vendor_name(self) -> None:
        prov = _make_provisioning()
        success, msg, path = prov.export_template_to_file("bad/vendor", "model")
        assert success is False
        assert "Invalid" in msg
        assert path is None

    def test_invalid_model_name(self) -> None:
        prov = _make_provisioning()
        success, msg, _path = prov.export_template_to_file("vendor", "bad..model")
        assert success is False
        assert "Invalid" in msg

    def test_template_not_found(self) -> None:
        prov = _make_provisioning()
        success, msg, _path = prov.export_template_to_file("unknown", "model")
        assert success is False
        assert "not found" in msg

    def test_success(self) -> None:
        prov = _make_provisioning()
        m = mock_open()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.open", m),
        ):
            success, msg, _path = prov.export_template_to_file("yealink", "t46s")
        assert success is True
        assert "exported" in msg.lower()
        m.assert_called_once_with("w")

    def test_creates_dir_if_missing(self) -> None:
        prov = _make_provisioning()
        m = mock_open()
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("pathlib.Path.open", m),
        ):
            success, _msg, _path = prov.export_template_to_file("yealink", "t46s")
        assert success is True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_mkdir_failure(self) -> None:
        prov = _make_provisioning()
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir", side_effect=OSError("no permission")),
        ):
            success, msg, _path = prov.export_template_to_file("yealink", "t46s")
        assert success is False
        assert "Failed" in msg

    def test_write_failure(self) -> None:
        prov = _make_provisioning()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.open", side_effect=OSError("disk full")),
        ):
            success, msg, _path = prov.export_template_to_file("yealink", "t46s")
        assert success is False
        assert "Failed" in msg


# ---------------------------------------------------------------------------
# Tests for update_template
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateTemplate:
    """Tests for update_template."""

    def test_invalid_vendor_name(self) -> None:
        prov = _make_provisioning()
        success, msg = prov.update_template("bad/vendor", "model", "content")
        assert success is False
        assert "Invalid" in msg

    def test_invalid_model_name(self) -> None:
        prov = _make_provisioning()
        success, msg = prov.update_template("vendor", "bad..model", "content")
        assert success is False
        assert "Invalid" in msg

    def test_success_updates_memory_and_disk(self) -> None:
        prov = _make_provisioning()
        m = mock_open()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.open", m),
        ):
            success, msg = prov.update_template("acme", "phone1", "new content")
        assert success is True
        assert "successfully" in msg.lower()
        assert prov.get_template("acme", "phone1") is not None
        assert prov.get_template("acme", "phone1").template_content == "new content"

    def test_creates_dir_if_missing(self) -> None:
        prov = _make_provisioning()
        m = mock_open()
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("pathlib.Path.open", m),
        ):
            success, _msg = prov.update_template("acme", "phone1", "data")
        assert success is True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_mkdir_failure(self) -> None:
        prov = _make_provisioning()
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir", side_effect=OSError("no permission")),
        ):
            success, _msg = prov.update_template("acme", "phone1", "data")
        assert success is False

    def test_write_failure(self) -> None:
        prov = _make_provisioning()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.open", side_effect=OSError("disk full")),
        ):
            success, _msg = prov.update_template("acme", "phone1", "data")
        assert success is False


# ---------------------------------------------------------------------------
# Tests for set_static_ip / get_static_ip
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStaticIp:
    """Tests for set_static_ip and get_static_ip."""

    def test_set_static_ip_device_not_found(self) -> None:
        prov = _make_provisioning()
        success, msg = prov.set_static_ip("00:00:00:00:00:00", "10.0.0.50")
        assert success is False
        assert "not found" in msg

    def test_set_static_ip_no_database(self) -> None:
        prov = _make_provisioning()
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        success, msg = prov.set_static_ip("AA:BB:CC:DD:EE:FF", "10.0.0.50")
        assert success is False
        assert "Database not available" in msg

    def test_set_static_ip_success(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.set_static_ip.return_value = True
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        success, _msg = prov.set_static_ip("AA:BB:CC:DD:EE:FF", "10.0.0.50")
        assert success is True
        prov.devices_db.set_static_ip.assert_called_once_with("aabbccddeeff", "10.0.0.50")

    def test_set_static_ip_db_returns_false(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.set_static_ip.return_value = False
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        success, _msg = prov.set_static_ip("AA:BB:CC:DD:EE:FF", "10.0.0.50")
        assert success is False

    def test_set_static_ip_db_exception(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.set_static_ip.side_effect = RuntimeError("db error")
        prov.register_device("AA:BB:CC:DD:EE:FF", "1001", "yealink", "t46s")
        success, msg = prov.set_static_ip("AA:BB:CC:DD:EE:FF", "10.0.0.50")
        assert success is False
        assert "Failed" in msg

    def test_get_static_ip_no_database(self) -> None:
        prov = _make_provisioning()
        assert prov.get_static_ip("AA:BB:CC:DD:EE:FF") is None

    def test_get_static_ip_found(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.get_device.return_value = {"static_ip": "10.0.0.50"}
        result = prov.get_static_ip("AA:BB:CC:DD:EE:FF")
        assert result == "10.0.0.50"

    def test_get_static_ip_device_not_in_db(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.get_device.return_value = None
        assert prov.get_static_ip("AA:BB:CC:DD:EE:FF") is None

    def test_get_static_ip_no_static_ip_field(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.get_device.return_value = {"mac": "aabb"}
        result = prov.get_static_ip("AA:BB:CC:DD:EE:FF")
        assert result is None

    def test_get_static_ip_db_exception(self) -> None:
        prov = _make_provisioning()
        prov.devices_db = MagicMock()
        prov.devices_db.get_device.side_effect = KeyError("bad")
        assert prov.get_static_ip("AA:BB:CC:DD:EE:FF") is None


# ---------------------------------------------------------------------------
# Tests for reload_templates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReloadTemplates:
    """Tests for reload_templates."""

    def test_reload_success(self) -> None:
        prov = _make_provisioning()
        prov.add_template("custom", "phone", "data")
        assert len(prov.templates) == 14
        success, msg, stats = prov.reload_templates()
        assert success is True
        assert "successfully" in msg.lower()
        # custom template should be gone after reload (only built-ins reload)
        assert len(prov.templates) == 13
        assert stats["total_templates"] == 13
        assert stats["vendors"] > 0

    def test_reload_restores_templates(self) -> None:
        prov = _make_provisioning()
        prov.templates.clear()
        assert len(prov.templates) == 0
        success, _, _ = prov.reload_templates()
        assert success is True
        assert len(prov.templates) == 13
