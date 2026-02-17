"""Comprehensive tests for pbx.utils.config module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import yaml

if TYPE_CHECKING:
    from pbx.utils.config import Config


@pytest.mark.unit
class TestConfigInit:
    """Tests for Config initialization."""

    @patch("pbx.utils.config.load_env_file")
    @patch("pbx.utils.config.get_env_loader")
    def test_init_with_valid_config(
        self, mock_get_env_loader: MagicMock, mock_load_env: MagicMock
    ) -> None:
        """Test Config initialization with a valid YAML file."""
        from pbx.utils.config import Config

        mock_env_loader = MagicMock()
        mock_env_loader.resolve_config.side_effect = lambda x: x
        mock_get_env_loader.return_value = mock_env_loader

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"server": {"host": "0.0.0.0", "port": 5060}}, f)
            f.flush()
            config = Config(config_file=f.name)

        assert config.config["server"]["host"] == "0.0.0.0"
        assert config.config["server"]["port"] == 5060

    @patch("pbx.utils.config.load_env_file")
    @patch("pbx.utils.config.get_env_loader")
    def test_init_file_not_found(
        self, mock_get_env_loader: MagicMock, mock_load_env: MagicMock
    ) -> None:
        """Test Config initialization with nonexistent file."""
        from pbx.utils.config import Config

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            Config(config_file="/tmp/nonexistent_config_xyz.yml")

    @patch("pbx.utils.config.load_env_file")
    @patch("pbx.utils.config.get_env_loader")
    def test_init_no_env_loading(
        self, mock_get_env_loader: MagicMock, mock_load_env: MagicMock
    ) -> None:
        """Test Config initialization with load_env=False."""
        from pbx.utils.config import Config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"test": "value"}, f)
            f.flush()
            config = Config(config_file=f.name, load_env=False)

        assert config.env_enabled is False
        assert config.env_loader is None
        mock_load_env.assert_not_called()

    @patch("pbx.utils.config.load_env_file")
    @patch("pbx.utils.config.get_env_loader")
    def test_init_empty_yaml(
        self, mock_get_env_loader: MagicMock, mock_load_env: MagicMock
    ) -> None:
        """Test Config initialization with empty YAML file."""
        from pbx.utils.config import Config

        mock_env_loader = MagicMock()
        mock_env_loader.resolve_config.side_effect = lambda x: x
        mock_get_env_loader.return_value = mock_env_loader

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("")
            f.flush()
            config = Config(config_file=f.name)

        assert config.config == {}


def _make_config(data: dict) -> Config:
    """Helper to create a Config object with given data."""
    from pbx.utils.config import Config

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(data, f)
        f.flush()
        with (
            patch("pbx.utils.config.load_env_file"),
            patch("pbx.utils.config.get_env_loader") as mock_gel,
        ):
            mock_env = MagicMock()
            mock_env.resolve_config.side_effect = lambda x: x
            mock_gel.return_value = mock_env
            config = Config(config_file=f.name)
    return config


@pytest.mark.unit
class TestValidateEmail:
    """Tests for validate_email static method."""

    def test_valid_email(self) -> None:
        """Test valid email addresses."""
        from pbx.utils.config import Config

        assert Config.validate_email("user@example.com") is True
        assert Config.validate_email("test.user+tag@domain.org") is True
        assert Config.validate_email("a@b.co") is True

    def test_invalid_email(self) -> None:
        """Test invalid email addresses."""
        from pbx.utils.config import Config

        assert Config.validate_email("") is False
        assert Config.validate_email("noemail") is False
        assert Config.validate_email("@domain.com") is False
        assert Config.validate_email("user@") is False
        assert Config.validate_email("user@.com") is False

    def test_empty_string(self) -> None:
        """Test empty string returns False."""
        from pbx.utils.config import Config

        assert Config.validate_email("") is False


@pytest.mark.unit
class TestGet:
    """Tests for get method with dot notation."""

    def test_get_simple_key(self) -> None:
        """Test getting a simple top-level key."""
        config = _make_config({"key": "value"})
        assert config.get("key") == "value"

    def test_get_nested_key(self) -> None:
        """Test getting a nested key with dot notation."""
        config = _make_config({"server": {"host": "0.0.0.0", "port": 5060}})
        assert config.get("server.host") == "0.0.0.0"
        assert config.get("server.port") == 5060

    def test_get_deeply_nested_key(self) -> None:
        """Test getting a deeply nested key."""
        config = _make_config({"a": {"b": {"c": {"d": "deep"}}}})
        assert config.get("a.b.c.d") == "deep"

    def test_get_missing_key_returns_default(self) -> None:
        """Test getting a missing key returns default."""
        config = _make_config({"key": "value"})
        assert config.get("missing") is None
        assert config.get("missing", "fallback") == "fallback"

    def test_get_missing_nested_key(self) -> None:
        """Test getting a missing nested key returns default."""
        config = _make_config({"server": {"host": "0.0.0.0"}})
        assert config.get("server.missing") is None
        assert config.get("nonexistent.key", "default") == "default"

    def test_get_non_dict_intermediate(self) -> None:
        """Test getting key when intermediate value is not a dict."""
        config = _make_config({"key": "string_value"})
        assert config.get("key.sub", "default") == "default"


@pytest.mark.unit
class TestGetExtensions:
    """Tests for get_extensions and get_extension methods."""

    def test_get_extensions(self) -> None:
        """Test getting all extensions."""
        data = {
            "extensions": [
                {"number": "1001", "name": "Alice"},
                {"number": "1002", "name": "Bob"},
            ]
        }
        config = _make_config(data)
        exts = config.get_extensions()
        assert len(exts) == 2

    def test_get_extensions_empty(self) -> None:
        """Test getting extensions when none configured."""
        config = _make_config({})
        assert config.get_extensions() == []

    def test_get_extension_by_number(self) -> None:
        """Test getting a specific extension by number."""
        data = {
            "extensions": [
                {"number": "1001", "name": "Alice"},
                {"number": "1002", "name": "Bob"},
            ]
        }
        config = _make_config(data)
        ext = config.get_extension("1001")
        assert ext is not None
        assert ext["name"] == "Alice"

    def test_get_extension_by_int_number(self) -> None:
        """Test getting a specific extension by integer number."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        ext = config.get_extension(1001)
        assert ext is not None
        assert ext["name"] == "Alice"

    def test_get_extension_not_found(self) -> None:
        """Test getting nonexistent extension returns None."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        assert config.get_extension("9999") is None


@pytest.mark.unit
class TestSave:
    """Tests for save method."""

    def test_save_success(self) -> None:
        """Test successful save."""
        config = _make_config({"key": "value"})
        config.config["new_key"] = "new_value"
        result = config.save()
        assert result is True

        # Verify the file was actually written
        with Path(config.config_file).open() as f:
            saved = yaml.safe_load(f)
        assert saved["new_key"] == "new_value"

    def test_save_permission_error(self) -> None:
        """Test save with permission error."""
        config = _make_config({"key": "value"})
        with patch("pathlib.Path.open", side_effect=PermissionError("denied")):
            result = config.save()
        assert result is False

    def test_save_os_error(self) -> None:
        """Test save with OS error."""
        config = _make_config({"key": "value"})
        with patch("pathlib.Path.open", side_effect=OSError("disk error")):
            result = config.save()
        assert result is False


@pytest.mark.unit
class TestAddExtension:
    """Tests for add_extension method."""

    def test_add_extension_success(self) -> None:
        """Test adding a new extension."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.add_extension("1001", "Alice", "alice@example.com", "pass")
        assert result is True
        assert len(config.config["extensions"]) == 1
        assert config.config["extensions"][0]["number"] == "1001"

    def test_add_extension_duplicate(self) -> None:
        """Test adding a duplicate extension fails."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        result = config.add_extension("1001", "Bob", "bob@example.com", "pass")
        assert result is False

    def test_add_extension_invalid_email(self) -> None:
        """Test adding extension with invalid email fails."""
        config = _make_config({})
        result = config.add_extension("1001", "Alice", "invalid-email", "pass")
        assert result is False

    def test_add_extension_no_email(self) -> None:
        """Test adding extension without email."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.add_extension("1001", "Alice", "", "pass")
        assert result is True
        assert "email" not in config.config["extensions"][0]

    def test_add_extension_allow_external_false(self) -> None:
        """Test adding extension with allow_external=False."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.add_extension(
                "1001", "Alice", "alice@example.com", "pass", allow_external=False
            )
        assert result is True
        assert config.config["extensions"][0]["allow_external"] is False

    def test_add_extension_creates_extensions_key(self) -> None:
        """Test add_extension creates extensions key if not present."""
        config = _make_config({"server": {"host": "0.0.0.0"}})
        with patch.object(config, "save", return_value=True):
            result = config.add_extension("1001", "Alice", "", "pass")
        assert result is True
        assert "extensions" in config.config


@pytest.mark.unit
class TestUpdateExtension:
    """Tests for update_extension method."""

    def test_update_extension_name(self) -> None:
        """Test updating extension name."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        with patch.object(config, "save", return_value=True):
            result = config.update_extension("1001", name="Alice Updated")
        assert result is True
        assert config.config["extensions"][0]["name"] == "Alice Updated"

    def test_update_extension_all_fields(self) -> None:
        """Test updating all fields at once."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        with patch.object(config, "save", return_value=True):
            result = config.update_extension(
                "1001",
                name="New Name",
                email="new@example.com",
                password="newpass",
                allow_external=False,
            )
        assert result is True
        ext = config.config["extensions"][0]
        assert ext["name"] == "New Name"
        assert ext["email"] == "new@example.com"
        assert ext["password"] == "newpass"
        assert ext["allow_external"] is False

    def test_update_extension_not_found(self) -> None:
        """Test updating nonexistent extension."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        result = config.update_extension("9999", name="New")
        assert result is False

    def test_update_extension_no_extensions_key(self) -> None:
        """Test updating when no extensions key exists."""
        config = _make_config({})
        result = config.update_extension("1001", name="Alice")
        assert result is False

    def test_update_extension_invalid_email(self) -> None:
        """Test updating with invalid email."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        result = config.update_extension("1001", email="bad-email")
        assert result is False

    def test_update_extension_empty_email_allowed(self) -> None:
        """Test updating with empty email is valid (disabling email)."""
        data = {"extensions": [{"number": "1001", "name": "Alice", "email": "old@x.com"}]}
        config = _make_config(data)
        with patch.object(config, "save", return_value=True):
            result = config.update_extension("1001", email="")
        assert result is True


@pytest.mark.unit
class TestDeleteExtension:
    """Tests for delete_extension method."""

    def test_delete_extension_success(self) -> None:
        """Test deleting an existing extension."""
        data = {
            "extensions": [
                {"number": "1001", "name": "Alice"},
                {"number": "1002", "name": "Bob"},
            ]
        }
        config = _make_config(data)
        with patch.object(config, "save", return_value=True):
            result = config.delete_extension("1001")
        assert result is True
        assert len(config.config["extensions"]) == 1
        assert config.config["extensions"][0]["number"] == "1002"

    def test_delete_extension_not_found(self) -> None:
        """Test deleting nonexistent extension."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        result = config.delete_extension("9999")
        assert result is False

    def test_delete_extension_no_extensions_key(self) -> None:
        """Test deleting when no extensions key exists."""
        config = _make_config({})
        result = config.delete_extension("1001")
        assert result is False


@pytest.mark.unit
class TestUpdateEmailConfig:
    """Tests for update_email_config method."""

    def test_update_smtp_config(self) -> None:
        """Test updating SMTP configuration."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_email_config(
                {
                    "smtp": {
                        "host": "smtp.example.com",
                        "port": 587,
                        "username": "user",
                        "password": "pass",
                    }
                }
            )
        assert result is True
        assert config.config["voicemail"]["smtp"]["host"] == "smtp.example.com"
        assert config.config["voicemail"]["smtp"]["port"] == 587

    def test_update_email_config_from_address(self) -> None:
        """Test updating email from_address."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_email_config({"email": {"from_address": "pbx@example.com"}})
        assert result is True
        assert config.config["voicemail"]["email"]["from_address"] == "pbx@example.com"

    def test_update_email_notifications_flag(self) -> None:
        """Test updating email notifications flag."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_email_config({"email_notifications": True})
        assert result is True
        assert config.config["voicemail"]["email_notifications"] is True

    def test_update_email_config_preserves_existing(self) -> None:
        """Test updating email config preserves existing voicemail settings."""
        data = {"voicemail": {"smtp": {"host": "old.host"}}}
        config = _make_config(data)
        with patch.object(config, "save", return_value=True):
            result = config.update_email_config({"smtp": {"port": 465}})
        assert result is True
        assert config.config["voicemail"]["smtp"]["host"] == "old.host"
        assert config.config["voicemail"]["smtp"]["port"] == 465


@pytest.mark.unit
class TestUpdateVoicemailPin:
    """Tests for update_voicemail_pin method."""

    def test_update_pin_success(self) -> None:
        """Test updating voicemail PIN successfully."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        with patch.object(config, "save", return_value=True):
            result = config.update_voicemail_pin("1001", "1234")
        assert result is True
        assert config.config["extensions"][0]["voicemail_pin"] == "1234"

    def test_update_pin_invalid_format_too_short(self) -> None:
        """Test updating PIN with too short value."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        result = config.update_voicemail_pin("1001", "12")
        assert result is False

    def test_update_pin_invalid_format_non_digit(self) -> None:
        """Test updating PIN with non-digit value."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        result = config.update_voicemail_pin("1001", "abcd")
        assert result is False

    def test_update_pin_invalid_empty(self) -> None:
        """Test updating PIN with empty value."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        result = config.update_voicemail_pin("1001", "")
        assert result is False

    def test_update_pin_extension_not_found(self) -> None:
        """Test updating PIN for nonexistent extension."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        result = config.update_voicemail_pin("9999", "1234")
        assert result is False

    def test_update_pin_no_extensions(self) -> None:
        """Test updating PIN when no extensions configured."""
        config = _make_config({})
        result = config.update_voicemail_pin("1001", "1234")
        assert result is False

    def test_update_pin_with_integer_pin(self) -> None:
        """Test updating PIN with integer pin value."""
        data = {"extensions": [{"number": "1001", "name": "Alice"}]}
        config = _make_config(data)
        with patch.object(config, "save", return_value=True):
            result = config.update_voicemail_pin("1001", 5678)
        assert result is True
        assert config.config["extensions"][0]["voicemail_pin"] == "5678"


@pytest.mark.unit
class TestGetDtmfConfig:
    """Tests for get_dtmf_config method."""

    def test_get_dtmf_config_defaults(self) -> None:
        """Test getting DTMF config with all defaults."""
        config = _make_config({})
        dtmf = config.get_dtmf_config()
        assert dtmf is not None
        assert dtmf["mode"] == "RFC2833"
        assert dtmf["payload_type"] == 101
        assert dtmf["duration"] == 160

    def test_get_dtmf_config_from_config(self) -> None:
        """Test getting DTMF config from actual config data."""
        data = {
            "features": {
                "webrtc": {
                    "dtmf": {
                        "mode": "SIPInfo",
                        "payload_type": 110,
                        "duration": 200,
                    }
                }
            }
        }
        config = _make_config(data)
        dtmf = config.get_dtmf_config()
        assert dtmf is not None
        assert dtmf["mode"] == "SIPInfo"
        assert dtmf["payload_type"] == 110
        assert dtmf["duration"] == 200


@pytest.mark.unit
class TestEnsureDtmfConfigStructure:
    """Tests for _ensure_dtmf_config_structure method."""

    def test_creates_full_structure(self) -> None:
        """Test creating DTMF config structure from scratch."""
        config = _make_config({})
        dtmf = config._ensure_dtmf_config_structure()
        assert dtmf is not None
        assert isinstance(dtmf, dict)
        assert "features" in config.config
        assert "webrtc" in config.config["features"]
        assert "dtmf" in config.config["features"]["webrtc"]

    def test_preserves_existing_structure(self) -> None:
        """Test preserving existing DTMF config structure."""
        data = {
            "features": {
                "webrtc": {
                    "dtmf": {"mode": "RFC2833"},
                    "other_setting": True,
                }
            }
        }
        config = _make_config(data)
        dtmf = config._ensure_dtmf_config_structure()
        assert dtmf["mode"] == "RFC2833"
        assert config.config["features"]["webrtc"]["other_setting"] is True


@pytest.mark.unit
class TestValidateDtmfFields:
    """Tests for DTMF validation helper methods."""

    def test_validate_payload_type_valid(self) -> None:
        """Test valid payload type."""
        config = _make_config({})
        assert config._validate_dtmf_payload_type(101) == 101
        assert config._validate_dtmf_payload_type(96) == 96
        assert config._validate_dtmf_payload_type(127) == 127

    def test_validate_payload_type_invalid(self) -> None:
        """Test invalid payload type."""
        config = _make_config({})
        assert config._validate_dtmf_payload_type(50) is None
        assert config._validate_dtmf_payload_type(200) is None

    def test_validate_duration_valid(self) -> None:
        """Test valid duration."""
        config = _make_config({})
        assert config._validate_dtmf_duration(160) == 160
        assert config._validate_dtmf_duration(80) == 80
        assert config._validate_dtmf_duration(500) == 500

    def test_validate_duration_invalid(self) -> None:
        """Test invalid duration."""
        config = _make_config({})
        assert config._validate_dtmf_duration(50) is None
        assert config._validate_dtmf_duration(600) is None

    def test_validate_threshold_valid(self) -> None:
        """Test valid threshold."""
        config = _make_config({})
        assert config._validate_dtmf_threshold(0.3) == 0.3
        assert config._validate_dtmf_threshold(0.1) == 0.1
        assert config._validate_dtmf_threshold(0.9) == 0.9

    def test_validate_threshold_invalid(self) -> None:
        """Test invalid threshold."""
        config = _make_config({})
        assert config._validate_dtmf_threshold(0.05) is None
        assert config._validate_dtmf_threshold(0.95) is None


@pytest.mark.unit
class TestUpdateDtmfConfig:
    """Tests for update_dtmf_config method."""

    def test_update_dtmf_mode(self) -> None:
        """Test updating DTMF mode."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_dtmf_config({"mode": "SIPInfo"})
        assert result is True
        assert config.config["features"]["webrtc"]["dtmf"]["mode"] == "SIPInfo"

    def test_update_dtmf_payload_type(self) -> None:
        """Test updating DTMF payload type."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_dtmf_config({"payload_type": 110})
        assert result is True

    def test_update_dtmf_invalid_payload_type(self) -> None:
        """Test updating DTMF with invalid payload type."""
        config = _make_config({})
        result = config.update_dtmf_config({"payload_type": 50})
        assert result is False

    def test_update_dtmf_duration(self) -> None:
        """Test updating DTMF duration."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_dtmf_config({"duration": 200})
        assert result is True

    def test_update_dtmf_invalid_duration(self) -> None:
        """Test updating DTMF with invalid duration."""
        config = _make_config({})
        result = config.update_dtmf_config({"duration": 10})
        assert result is False

    def test_update_dtmf_threshold(self) -> None:
        """Test updating DTMF detection threshold."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_dtmf_config({"detection_threshold": 0.5})
        assert result is True

    def test_update_dtmf_invalid_threshold(self) -> None:
        """Test updating DTMF with invalid threshold."""
        config = _make_config({})
        result = config.update_dtmf_config({"detection_threshold": 0.01})
        assert result is False

    def test_update_dtmf_boolean_fields(self) -> None:
        """Test updating DTMF boolean fields."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_dtmf_config(
                {
                    "sip_info_fallback": False,
                    "inband_fallback": True,
                    "relay_enabled": False,
                }
            )
        assert result is True
        dtmf = config.config["features"]["webrtc"]["dtmf"]
        assert dtmf["sip_info_fallback"] is False
        assert dtmf["inband_fallback"] is True
        assert dtmf["relay_enabled"] is False

    def test_update_dtmf_with_nested_key(self) -> None:
        """Test updating DTMF using nested 'dtmf' key."""
        config = _make_config({})
        with patch.object(config, "save", return_value=True):
            result = config.update_dtmf_config({"dtmf": {"mode": "Inband"}})
        assert result is True
        assert config.config["features"]["webrtc"]["dtmf"]["mode"] == "Inband"
