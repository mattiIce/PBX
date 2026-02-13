"""
Test DTMF Configuration API
Tests the DTMF configuration GET and POST endpoints
"""

import os
import tempfile

import yaml


from pbx.utils.config import Config


class TestDTMFConfigMethods:
    """Test DTMF configuration methods in Config class"""

    def setup_method(self) -> None:
        """Set up test configuration file"""
        # Create a temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        config_data = {
            "features": {
                "webrtc": {
                    "dtmf": {
                        "mode": "RFC2833",
                        "payload_type": 101,
                        "duration": 160,
                        "sip_info_fallback": True,
                        "inband_fallback": True,
                        "detection_threshold": 0.3,
                        "relay_enabled": True,
                    }
                }
            }
        }
        yaml.dump(config_data, self.temp_config)
        self.temp_config.close()

        # Create Config instance with test file
        self.config = Config(config_file=self.temp_config.name, load_env=False)

    def teardown_method(self) -> None:
        """Clean up temporary config file"""
        if os.path.exists(self.temp_config.name):
            os.unlink(self.temp_config.name)

    def test_get_dtmf_config_default(self) -> None:
        """Test getting DTMF configuration with default values"""
        dtmf_config = self.config.get_dtmf_config()

        assert dtmf_config is not None
        assert dtmf_config["mode"] == "RFC2833"
        assert dtmf_config["payload_type"] == 101
        assert dtmf_config["duration"] == 160
        assert dtmf_config["sip_info_fallback"]
        assert dtmf_config["inband_fallback"]
        assert dtmf_config["detection_threshold"] == 0.3
        assert dtmf_config["relay_enabled"]
    def test_update_dtmf_config_mode(self) -> None:
        """Test updating DTMF mode"""
        update_data = {"dtmf": {"mode": "SIP_INFO"}}

        result = self.config.update_dtmf_config(update_data)
        assert result
        # Verify the update
        dtmf_config = self.config.get_dtmf_config()
        assert dtmf_config["mode"] == "SIP_INFO"
    def test_update_dtmf_config_payload_type(self) -> None:
        """Test updating DTMF payload type"""
        update_data = {"dtmf": {"payload_type": 100}}

        result = self.config.update_dtmf_config(update_data)
        assert result
        # Verify the update
        dtmf_config = self.config.get_dtmf_config()
        assert dtmf_config["payload_type"] == 100
    def test_update_dtmf_config_duration(self) -> None:
        """Test updating DTMF duration"""
        update_data = {"dtmf": {"duration": 200}}

        result = self.config.update_dtmf_config(update_data)
        assert result
        # Verify the update
        dtmf_config = self.config.get_dtmf_config()
        assert dtmf_config["duration"] == 200
    def test_update_dtmf_config_boolean_fields(self) -> None:
        """Test updating DTMF boolean fields"""
        update_data = {
            "dtmf": {"sip_info_fallback": False, "inband_fallback": False, "relay_enabled": False}
        }

        result = self.config.update_dtmf_config(update_data)
        assert result
        # Verify the update
        dtmf_config = self.config.get_dtmf_config()
        assert not dtmf_config["sip_info_fallback"]
        assert not dtmf_config["inband_fallback"]
        assert not dtmf_config["relay_enabled"]
    def test_update_dtmf_config_threshold(self) -> None:
        """Test updating DTMF detection threshold"""
        update_data = {"dtmf": {"detection_threshold": 0.5}}

        result = self.config.update_dtmf_config(update_data)
        assert result
        # Verify the update
        dtmf_config = self.config.get_dtmf_config()
        assert dtmf_config["detection_threshold"] == 0.5
    def test_update_dtmf_config_all_fields(self) -> None:
        """Test updating all DTMF configuration fields"""
        update_data = {
            "dtmf": {
                "mode": "INBAND",
                "payload_type": 102,
                "duration": 250,
                "sip_info_fallback": False,
                "inband_fallback": False,
                "detection_threshold": 0.7,
                "relay_enabled": False,
            }
        }

        result = self.config.update_dtmf_config(update_data)
        assert result
        # Verify all updates
        dtmf_config = self.config.get_dtmf_config()
        assert dtmf_config["mode"] == "INBAND"
        assert dtmf_config["payload_type"] == 102
        assert dtmf_config["duration"] == 250
        assert not dtmf_config["sip_info_fallback"]
        assert not dtmf_config["inband_fallback"]
        assert dtmf_config["detection_threshold"] == 0.7
        assert not dtmf_config["relay_enabled"]
    def test_update_dtmf_config_invalid_payload_type_low(self) -> None:
        """Test updating DTMF with invalid payload type (too low)"""
        update_data = {"dtmf": {"payload_type": 95}}  # Below valid range (96-127)

        result = self.config.update_dtmf_config(update_data)
        assert not result
    def test_update_dtmf_config_invalid_payload_type_high(self) -> None:
        """Test updating DTMF with invalid payload type (too high)"""
        update_data = {"dtmf": {"payload_type": 128}}  # Above valid range (96-127)

        result = self.config.update_dtmf_config(update_data)
        assert not result
    def test_update_dtmf_config_invalid_duration_low(self) -> None:
        """Test updating DTMF with invalid duration (too low)"""
        update_data = {"dtmf": {"duration": 50}}  # Below valid range (80-500)

        result = self.config.update_dtmf_config(update_data)
        assert not result
    def test_update_dtmf_config_invalid_duration_high(self) -> None:
        """Test updating DTMF with invalid duration (too high)"""
        update_data = {"dtmf": {"duration": 600}}  # Above valid range (80-500)

        result = self.config.update_dtmf_config(update_data)
        assert not result
    def test_update_dtmf_config_invalid_threshold_low(self) -> None:
        """Test updating DTMF with invalid threshold (too low)"""
        update_data = {"dtmf": {"detection_threshold": 0.05}}  # Below valid range (0.1-0.9)

        result = self.config.update_dtmf_config(update_data)
        assert not result
    def test_update_dtmf_config_invalid_threshold_high(self) -> None:
        """Test updating DTMF with invalid threshold (too high)"""
        update_data = {"dtmf": {"detection_threshold": 0.95}}  # Above valid range (0.1-0.9)

        result = self.config.update_dtmf_config(update_data)
        assert not result
    def test_get_dtmf_config_with_missing_structure(self) -> None:
        """Test getting DTMF config when structure doesn't exist"""
        # Create a config without the dtmf structure
        empty_config = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        yaml.dump({}, empty_config)
        empty_config.close()

        config = Config(config_file=empty_config.name, load_env=False)
        dtmf_config = config.get_dtmf_config()

        # Should return defaults
        assert dtmf_config is not None
        assert dtmf_config["mode"] == "RFC2833"
        assert dtmf_config["payload_type"] == 101
        os.unlink(empty_config.name)

    def test_update_dtmf_config_creates_structure(self) -> None:
        """Test that updating DTMF config creates the structure if missing"""
        # Create a config without the dtmf structure
        empty_config = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        yaml.dump({}, empty_config)
        empty_config.close()

        config = Config(config_file=empty_config.name, load_env=False)

        # Update should create the structure
        update_data = {"dtmf": {"mode": "SIP_INFO", "payload_type": 100}}

        result = config.update_dtmf_config(update_data)
        assert result
        # Verify the structure was created and updated
        dtmf_config = config.get_dtmf_config()
        assert dtmf_config["mode"] == "SIP_INFO"
        assert dtmf_config["payload_type"] == 100
        os.unlink(empty_config.name)

    def test_update_dtmf_config_without_dtmf_wrapper(self) -> None:
        """Test updating DTMF config with data not wrapped in 'dtmf' key"""
        update_data = {"mode": "SIP_INFO", "payload_type": 100}

        result = self.config.update_dtmf_config(update_data)
        assert result
        # Verify the update
        dtmf_config = self.config.get_dtmf_config()
        assert dtmf_config["mode"] == "SIP_INFO"
        assert dtmf_config["payload_type"] == 100
