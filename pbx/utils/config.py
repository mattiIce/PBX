"""Configuration management for PBX system."""

import logging
import re
from pathlib import Path

import yaml

from pbx.utils.env_loader import get_env_loader, load_env_file

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for PBX"""

    # Email validation regex pattern
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __init__(self, config_file: str = "config.yml", load_env: bool = True) -> None:
        """
        Initialize configuration

        Args:
            config_file: Path to configuration file
            load_env: Whether to load .env file and resolve environment variables
        """
        self.config_file = config_file
        self.config = {}
        self.env_loader = None
        self.env_enabled = load_env

        # Load .env file if it exists
        if load_env:
            env_file = str(Path(config_file).parent / ".env")
            load_env_file(env_file)
            self.env_loader = get_env_loader()

        self.load()

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        if not email:
            return False
        return bool(Config.EMAIL_PATTERN.match(email))

    def load(self) -> None:
        """Load configuration from YAML file and resolve environment variables"""
        if Path(self.config_file).exists():
            with Path(self.config_file).open() as f:
                self.config = yaml.safe_load(f) or {}

            # Resolve environment variables in configuration
            if self.env_enabled and self.env_loader:
                self.config = self.env_loader.resolve_config(self.config)
        else:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

    def get(self, key: str, default: object = None) -> object:
        """
        Get configuration value

        Args:
            key: Configuration key (supports dot notation, e.g., 'server.sip_port')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_extensions(self) -> list[dict]:
        """Get all configured extensions"""
        return self.config.get("extensions", [])

    def get_extension(self, number: str | int) -> dict | None:
        """
        Get extension by number

        Args:
            number: Extension number

        Returns:
            Extension configuration or None
        """
        extensions = self.get_extensions()
        for ext in extensions:
            if ext.get("number") == str(number):
                return ext
        return None

    def save(self) -> bool:
        """Save current configuration to YAML file"""
        try:
            with open(self.config_file, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            return True
        except PermissionError as e:
            logger.error("Error saving config: Permission denied - %s", e)
            return False
        except OSError as e:
            logger.error("Error saving config: Disk error - %s", e)
            return False

    def add_extension(self, number: str | int, name: str, email: str, password: str, allow_external: bool = True) -> bool:
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
            if "extensions" not in self.config:
                self.config["extensions"] = []

            # Check if extension already exists
            for ext in self.config["extensions"]:
                if ext.get("number") == str(number):
                    return False

            # Validate email format if provided
            if email and not self.validate_email(email):
                logger.error("Error adding extension: Invalid email format")
                return False

            # Add new extension
            new_ext = {
                "number": str(number),
                "name": name,
                "password": password,
                "allow_external": allow_external,
            }

            if email:
                new_ext["email"] = email

            self.config["extensions"].append(new_ext)
            return self.save()
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Error adding extension: %s", e)
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
            if "extensions" not in self.config:
                return False

            # Validate email format if provided
            if email is not None and email and not self.validate_email(email):
                logger.error("Error updating extension: Invalid email format")
                return False

            # Find and update extension
            for ext in self.config["extensions"]:
                if ext.get("number") == str(number):
                    if name is not None:
                        ext["name"] = name
                    if email is not None:
                        ext["email"] = email
                    if password is not None:
                        ext["password"] = password
                    if allow_external is not None:
                        ext["allow_external"] = allow_external
                    return self.save()

            return False
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Error updating extension: %s", e)
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
            if "extensions" not in self.config:
                return False

            # Find and remove extension
            original_length = len(self.config["extensions"])
            self.config["extensions"] = [
                ext for ext in self.config["extensions"] if ext.get("number") != str(number)
            ]

            if len(self.config["extensions"]) < original_length:
                return self.save()

            return False
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Error deleting extension: %s", e)
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
            if "voicemail" not in self.config:
                self.config["voicemail"] = {}

            # Update SMTP settings
            if "smtp" in config_data:
                if "smtp" not in self.config["voicemail"]:
                    self.config["voicemail"]["smtp"] = {}

                smtp = config_data["smtp"]
                if "host" in smtp:
                    self.config["voicemail"]["smtp"]["host"] = smtp["host"]
                if "port" in smtp:
                    self.config["voicemail"]["smtp"]["port"] = smtp["port"]
                if "username" in smtp:
                    self.config["voicemail"]["smtp"]["username"] = smtp["username"]
                if "password" in smtp:
                    self.config["voicemail"]["smtp"]["password"] = smtp["password"]

            # Update email settings
            if "email" in config_data:
                if "email" not in self.config["voicemail"]:
                    self.config["voicemail"]["email"] = {}

                email = config_data["email"]
                if "from_address" in email:
                    self.config["voicemail"]["email"]["from_address"] = email["from_address"]

            # Update email notifications flag
            if "email_notifications" in config_data:
                self.config["voicemail"]["email_notifications"] = config_data["email_notifications"]

            return self.save()
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Error updating email config: %s", e)
            return False

    def update_voicemail_pin(self, extension_number, pin):
        """
        Update voicemail PIN for an extension

        Args:
            extension_number: Extension number
            pin: Voicemail PIN (4 digits)

        Returns:
            True if successful, False otherwise
        """
        try:
            if "extensions" not in self.config:
                return False

            # Validate PIN format
            if not pin or len(str(pin)) != 4 or not str(pin).isdigit():
                logger.error("Error updating voicemail PIN: Invalid PIN format")
                return False

            # Find and update extension
            for ext in self.config["extensions"]:
                if ext.get("number") == str(extension_number):
                    ext["voicemail_pin"] = str(pin)
                    return self.save()

            return False
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Error updating voicemail PIN: %s", e)
            return False

    def get_dtmf_config(self):
        """
        Get DTMF configuration

        Returns:
            Dictionary with DTMF configuration
        """
        try:
            # Get DTMF config from features.webrtc.dtmf section
            dtmf_config = {
                "mode": self.get("features.webrtc.dtmf.mode", "RFC2833"),
                "payload_type": self.get("features.webrtc.dtmf.payload_type", 101),
                "duration": self.get("features.webrtc.dtmf.duration", 160),
                "sip_info_fallback": self.get("features.webrtc.dtmf.sip_info_fallback", True),
                "inband_fallback": self.get("features.webrtc.dtmf.inband_fallback", True),
                "detection_threshold": self.get("features.webrtc.dtmf.detection_threshold", 0.3),
                "relay_enabled": self.get("features.webrtc.dtmf.relay_enabled", True),
            }
            return dtmf_config
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Error getting DTMF config: %s", e)
            return None

    def _ensure_dtmf_config_structure(self):
        """Ensure DTMF config structure exists"""
        if "features" not in self.config:
            self.config["features"] = {}
        if "webrtc" not in self.config["features"]:
            self.config["features"]["webrtc"] = {}
        if "dtmf" not in self.config["features"]["webrtc"]:
            self.config["features"]["webrtc"]["dtmf"] = {}
        return self.config["features"]["webrtc"]["dtmf"]

    def _update_dtmf_simple_fields(self, dtmf_config, dtmf):
        """Update simple boolean/string DTMF fields"""
        if "mode" in dtmf:
            dtmf_config["mode"] = dtmf["mode"]
        if "sip_info_fallback" in dtmf:
            dtmf_config["sip_info_fallback"] = bool(dtmf["sip_info_fallback"])
        if "inband_fallback" in dtmf:
            dtmf_config["inband_fallback"] = bool(dtmf["inband_fallback"])
        if "relay_enabled" in dtmf:
            dtmf_config["relay_enabled"] = bool(dtmf["relay_enabled"])

    def _validate_dtmf_payload_type(self, payload_type):
        """Validate DTMF payload type"""
        payload_type = int(payload_type)
        if payload_type < 96 or payload_type > 127:
            logger.error(
                "Error updating DTMF config: Invalid payload type %d. Must be between 96 and 127",
                payload_type,
            )
            return None
        return payload_type

    def _validate_dtmf_duration(self, duration):
        """Validate DTMF duration"""
        duration = int(duration)
        if duration < 80 or duration > 500:
            logger.error(
                "Error updating DTMF config: Invalid duration %dms. Must be between 80 and 500ms",
                duration,
            )
            return None
        return duration

    def _validate_dtmf_threshold(self, threshold):
        """Validate DTMF detection threshold"""
        threshold = float(threshold)
        if threshold < 0.1 or threshold > 0.9:
            logger.error(
                "Error updating DTMF config: Invalid detection threshold %s. Must be between 0.1 and 0.9",
                threshold,
            )
            return None
        return threshold

    def update_dtmf_config(self, config_data):
        """
        Update DTMF configuration

        Args:
            config_data: Dictionary with DTMF configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            dtmf_config = self._ensure_dtmf_config_structure()
            dtmf = config_data.get("dtmf", config_data)

            # Update simple fields
            self._update_dtmf_simple_fields(dtmf_config, dtmf)

            # Update and validate complex fields
            if "payload_type" in dtmf:
                validated = self._validate_dtmf_payload_type(dtmf["payload_type"])
                if validated is None:
                    return False
                dtmf_config["payload_type"] = validated

            if "duration" in dtmf:
                validated = self._validate_dtmf_duration(dtmf["duration"])
                if validated is None:
                    return False
                dtmf_config["duration"] = validated

            if "detection_threshold" in dtmf:
                validated = self._validate_dtmf_threshold(dtmf["detection_threshold"])
                if validated is None:
                    return False
                dtmf_config["detection_threshold"] = validated

            return self.save()
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Error updating DTMF config: %s", e)
            return False
