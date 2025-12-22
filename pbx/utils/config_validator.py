"""
Configuration validation for production deployments.

This module provides comprehensive validation of configuration settings
to catch issues before the PBX starts, preventing runtime errors.
"""

import logging
import os
import re
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Validates PBX configuration for production readiness.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize validator with configuration.

        Args:
            config: Configuration dictionary to validate
        """
        self.config = config
        self.errors = []
        self.warnings = []

    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validation checks.

        Returns:
            Tuple of (is_valid, errors_list, warnings_list)
        """
        self.errors = []
        self.warnings = []

        # Run all validation methods
        self._validate_server_config()
        self._validate_database_config()
        self._validate_api_config()
        self._validate_security_config()
        self._validate_extensions_config()
        self._validate_codecs_config()
        self._validate_production_readiness()

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_server_config(self):
        """Validate server configuration."""
        server_config = self.config.get("server", {})

        # Check SIP port
        sip_port = server_config.get("sip_port", 5060)
        if not isinstance(sip_port, int) or sip_port < 1 or sip_port > 65535:
            self.errors.append(f"Invalid SIP port: {sip_port}. Must be 1-65535.")

        # Check RTP port range
        rtp_start = server_config.get("rtp_port_range_start", 10000)
        rtp_end = server_config.get("rtp_port_range_end", 20000)

        if rtp_start >= rtp_end:
            self.errors.append(f"RTP port range invalid: start ({rtp_start}) >= end ({rtp_end})")

        if rtp_end - rtp_start < 100:
            self.warnings.append(
                f"RTP port range is small ({rtp_end - rtp_start} ports). "
                f"Recommend at least 100 ports for production."
            )

        # Check external IP
        external_ip = server_config.get("external_ip")
        if not external_ip:
            self.warnings.append("external_ip not set. This may cause issues with SIP signaling.")
        elif external_ip == "0.0.0.0":  # nosec B104 - Validation check, not binding
            self.warnings.append(
                "external_ip is set to 0.0.0.0. Should be set to actual server IP."
            )

    def _validate_database_config(self):
        """Validate database configuration."""
        db_config = self.config.get("database", {})
        db_type = db_config.get("type", "sqlite")

        if db_type == "postgresql":
            # Check required PostgreSQL settings
            required = ["host", "port", "name", "user", "password"]
            for field in required:
                value = db_config.get(field, "")

                # Check for environment variable placeholders
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]  # Extract var name
                    if not os.environ.get(env_var):
                        self.errors.append(
                            f"Database config '{field}' references undefined "
                            f"environment variable: {env_var}"
                        )
                elif not value:
                    self.errors.append(f"PostgreSQL config missing required field: {field}")

            # Warn about default passwords
            password = db_config.get("password", "")
            if password and not password.startswith("${"):
                # Password is hardcoded, not from env var
                self.warnings.append(
                    "Database password is hardcoded in config. "
                    "Recommend using environment variables."
                )

        elif db_type == "sqlite":
            # Check SQLite path
            db_path = db_config.get("path", "pbx.db")
            if not db_path:
                self.errors.append("SQLite database path is empty")

            # Warn if using SQLite in production
            self.warnings.append("Using SQLite database. PostgreSQL is recommended for production.")

    def _validate_api_config(self):
        """Validate API configuration."""
        api_config = self.config.get("api", {})

        # Check API port
        api_port = api_config.get("port", 8080)
        if not isinstance(api_port, int) or api_port < 1 or api_port > 65535:
            self.errors.append(f"Invalid API port: {api_port}")

        # Check SSL configuration
        ssl_config = api_config.get("ssl", {})
        ssl_enabled = ssl_config.get("enabled", False)

        if ssl_enabled:
            cert_file = ssl_config.get("cert_file")
            key_file = ssl_config.get("key_file")

            if not cert_file or not key_file:
                self.errors.append("SSL enabled but cert_file or key_file not specified")
            elif not cert_file.startswith("${"):  # Not an env var
                if not os.path.exists(cert_file):
                    self.errors.append(f"SSL certificate file not found: {cert_file}")
                if not os.path.exists(key_file):
                    self.errors.append(f"SSL key file not found: {key_file}")
        else:
            self.warnings.append("SSL/TLS is disabled. HTTPS is recommended for production.")

    def _validate_security_config(self):
        """Validate security configuration."""
        security_config = self.config.get("security", {})

        # Check FIPS mode
        fips_mode = security_config.get("fips_mode", False)
        if not fips_mode:
            self.warnings.append("FIPS mode is disabled. Enable for government-grade encryption.")

        # Check rate limiting
        max_failed_attempts = security_config.get("max_failed_attempts", 5)
        if max_failed_attempts > 10:
            self.warnings.append(
                f"max_failed_attempts is high ({max_failed_attempts}). "
                f"Lower values provide better security."
            )

    def _validate_extensions_config(self):
        """Validate extensions configuration."""
        extensions = self.config.get("extensions", [])

        if not extensions:
            self.warnings.append("No extensions configured")
            return

        # Check for duplicate extension numbers
        extension_numbers = [ext.get("number") for ext in extensions]
        duplicates = set([x for x in extension_numbers if extension_numbers.count(x) > 1])
        if duplicates:
            self.errors.append(f"Duplicate extension numbers found: {duplicates}")

        # Check for weak passwords
        weak_patterns = [
            r"^password\d*$",  # password, password1, etc.
            r"^123+$",  # 123, 1234, etc.
            r"^admin\d*$",  # admin, admin1, etc.
            r"^test\d*$",  # test, test1, etc.
        ]

        for ext in extensions:
            number = ext.get("number", "unknown")
            password = ext.get("password", "")

            # Check password strength
            if len(password) < 8:
                self.warnings.append(f"Extension {number}: password is too short (< 8 characters)")

            for pattern in weak_patterns:
                if re.match(pattern, password.lower()):
                    self.warnings.append(f"Extension {number}: weak password detected")
                    break

    def _validate_codecs_config(self):
        """Validate codec configuration."""
        codecs_config = self.config.get("codecs", {})

        # Check if at least one codec is enabled
        enabled_codecs = [
            name
            for name, cfg in codecs_config.items()
            if isinstance(cfg, dict) and cfg.get("enabled", False)
        ]

        if not enabled_codecs:
            self.errors.append("No audio codecs enabled. At least one codec must be enabled.")

        # Check for G.711 (PCMU/PCMA) which should always be available
        if not any(name.startswith("g711") or name in ["pcmu", "pcma"] for name in enabled_codecs):
            self.warnings.append(
                "G.711 (PCMU/PCMA) codec not explicitly enabled. "
                "This is the most compatible codec."
            )

    def _validate_production_readiness(self):
        """Check production-specific requirements."""
        # Check for example/default values that should be changed

        # Server name
        server_config = self.config.get("server", {})
        server_name = server_config.get("server_name", "")
        if "example" in server_name.lower():
            self.warnings.append("Server name contains 'example'. Update for production.")

        # Check voicemail configuration
        voicemail_config = self.config.get("voicemail", {})
        if voicemail_config.get("email_notifications", False):
            smtp_config = voicemail_config.get("smtp", {})

            if not smtp_config.get("host"):
                self.warnings.append(
                    "Voicemail email notifications enabled but SMTP host not configured"
                )

            # Check for default/example email addresses
            from_address = voicemail_config.get("email", {}).get("from_address", "")
            if from_address.endswith("@example.com") or "@example.com" in from_address:
                self.warnings.append(
                    "Voicemail from_address uses example.com. Update for production."
                )

        # Check logging configuration
        logging_config = self.config.get("logging", {})
        log_level = logging_config.get("level", "INFO")

        if log_level == "DEBUG":
            self.warnings.append("Logging level is DEBUG. Use INFO or WARNING for production.")


def validate_config_on_startup(config: Dict[str, Any]) -> bool:
    """
    Validate configuration on startup and log results.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if validation passed (no errors), False otherwise
    """
    validator = ConfigValidator(config)
    is_valid, errors, warnings = validator.validate_all()

    # Log results
    if errors:
        logger.error("=" * 70)
        logger.error("CONFIGURATION VALIDATION ERRORS")
        logger.error("=" * 70)
        for error in errors:
            logger.error(f"  ✗ {error}")
        logger.error("")

    if warnings:
        logger.warning("=" * 70)
        logger.warning("CONFIGURATION WARNINGS")
        logger.warning("=" * 70)
        for warning in warnings:
            logger.warning(f"  ⚠ {warning}")
        logger.warning("")

    if not errors and not warnings:
        logger.info("✓ Configuration validation passed")
    elif not errors:
        logger.info("✓ Configuration validation passed with warnings")

    return is_valid
