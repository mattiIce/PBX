#!/usr/bin/env python3
"""Comprehensive tests for the config_validator module."""

from unittest.mock import patch

import pytest

from pbx.utils.config_validator import ConfigValidator, validate_config_on_startup


@pytest.mark.unit
class TestConfigValidatorInit:
    """Tests for ConfigValidator initialization."""

    def test_init_with_config(self) -> None:
        config = {"server": {"sip_port": 5060}}
        validator = ConfigValidator(config)
        assert validator.config is config
        assert validator.errors == []
        assert validator.warnings == []

    def test_init_with_empty_config(self) -> None:
        validator = ConfigValidator({})
        assert validator.config == {}
        assert validator.errors == []
        assert validator.warnings == []


@pytest.mark.unit
class TestValidateAll:
    """Tests for validate_all method."""

    def test_validate_all_returns_tuple(self) -> None:
        validator = ConfigValidator({})
        result = validator.validate_all()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_validate_all_resets_errors(self) -> None:
        validator = ConfigValidator({})
        validator.errors = ["old error"]
        validator.warnings = ["old warning"]
        validator.validate_all()
        # Errors/warnings should have been reset (then re-populated from validation)
        assert "old error" not in validator.errors
        assert "old warning" not in validator.warnings

    def test_validate_all_valid_config(self) -> None:
        config = {
            "server": {
                "sip_port": 5060,
                "rtp_port_range_start": 10000,
                "rtp_port_range_end": 20000,
                "external_ip": "192.168.1.1",
            },
            "database": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "name": "pbx",
                "user": "admin",
                "password": "${DB_PASSWORD}",
            },
            "api": {
                "port": 9000,
                "ssl": {"enabled": True, "cert_file": "${SSL_CERT}", "key_file": "${SSL_KEY}"},
            },
            "security": {"fips_mode": True, "max_failed_attempts": 5},
            "extensions": [
                {"number": "1001", "password": "SecurePass123!"},
                {"number": "1002", "password": "AnotherGood9!"},
            ],
            "codecs": {
                "g711_pcmu": {"enabled": True},
                "opus": {"enabled": True},
            },
            "logging": {"level": "INFO"},
        }
        with patch("pbx.utils.config_validator.environ") as mock_env:
            mock_env.get.return_value = "some_value"
            validator = ConfigValidator(config)
            is_valid, errors, _warnings = validator.validate_all()
            assert is_valid is True
            assert len(errors) == 0


@pytest.mark.unit
class TestValidateServerConfig:
    """Tests for _validate_server_config method."""

    def test_valid_sip_port(self) -> None:
        config = {"server": {"sip_port": 5060}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        port_errors = [e for e in validator.errors if "SIP port" in e]
        assert len(port_errors) == 0

    def test_invalid_sip_port_too_low(self) -> None:
        config = {"server": {"sip_port": 0}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        assert any("SIP port" in e for e in validator.errors)

    def test_invalid_sip_port_too_high(self) -> None:
        config = {"server": {"sip_port": 70000}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        assert any("SIP port" in e for e in validator.errors)

    def test_invalid_sip_port_not_int(self) -> None:
        config = {"server": {"sip_port": "abc"}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        assert any("SIP port" in e for e in validator.errors)

    def test_rtp_range_start_greater_than_end(self) -> None:
        config = {"server": {"rtp_port_range_start": 20000, "rtp_port_range_end": 10000}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        assert any("RTP port range invalid" in e for e in validator.errors)

    def test_rtp_range_equal(self) -> None:
        config = {"server": {"rtp_port_range_start": 10000, "rtp_port_range_end": 10000}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        assert any("RTP port range invalid" in e for e in validator.errors)

    def test_rtp_range_too_small(self) -> None:
        config = {"server": {"rtp_port_range_start": 10000, "rtp_port_range_end": 10050}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        assert any("RTP port range is small" in w for w in validator.warnings)

    def test_rtp_range_adequate(self) -> None:
        config = {"server": {"rtp_port_range_start": 10000, "rtp_port_range_end": 20000}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        rtp_warnings = [w for w in validator.warnings if "RTP port range is small" in w]
        assert len(rtp_warnings) == 0

    def test_no_external_ip(self) -> None:
        config = {"server": {}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        assert any("external_ip not set" in w for w in validator.warnings)

    def test_external_ip_zero(self) -> None:
        config = {"server": {"external_ip": "0.0.0.0"}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        assert any("0.0.0.0" in w for w in validator.warnings)

    def test_valid_external_ip(self) -> None:
        config = {"server": {"external_ip": "192.168.1.1"}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        ip_warnings = [w for w in validator.warnings if "external_ip" in w]
        assert len(ip_warnings) == 0

    def test_default_sip_port_used(self) -> None:
        config = {"server": {}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        # Default 5060 should not cause an error
        port_errors = [e for e in validator.errors if "SIP port" in e]
        assert len(port_errors) == 0

    def test_sip_port_boundary_1(self) -> None:
        config = {"server": {"sip_port": 1}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        port_errors = [e for e in validator.errors if "SIP port" in e]
        assert len(port_errors) == 0

    def test_sip_port_boundary_65535(self) -> None:
        config = {"server": {"sip_port": 65535}}
        validator = ConfigValidator(config)
        validator._validate_server_config()
        port_errors = [e for e in validator.errors if "SIP port" in e]
        assert len(port_errors) == 0


@pytest.mark.unit
class TestValidateDatabaseConfig:
    """Tests for _validate_database_config method."""

    def test_postgresql_all_fields_present(self) -> None:
        config = {
            "database": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "name": "pbx",
                "user": "admin",
                "password": "${DB_PASSWORD}",
            }
        }
        with patch("pbx.utils.config_validator.environ") as mock_env:
            mock_env.get.return_value = "secret"
            validator = ConfigValidator(config)
            validator._validate_database_config()
            # No errors for missing fields
            missing_errors = [e for e in validator.errors if "missing required" in e.lower()]
            assert len(missing_errors) == 0

    def test_postgresql_missing_host(self) -> None:
        config = {
            "database": {
                "type": "postgresql",
                "port": 5432,
                "name": "pbx",
                "user": "admin",
                "password": "secret",
            }
        }
        validator = ConfigValidator(config)
        validator._validate_database_config()
        assert any("host" in e for e in validator.errors)

    def test_postgresql_missing_multiple_fields(self) -> None:
        config = {"database": {"type": "postgresql"}}
        validator = ConfigValidator(config)
        validator._validate_database_config()
        assert len(validator.errors) >= 5  # All required fields missing

    def test_postgresql_env_var_placeholder_undefined(self) -> None:
        config = {
            "database": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "name": "pbx",
                "user": "admin",
                "password": "${DB_PASSWORD}",
            }
        }
        with patch("pbx.utils.config_validator.environ") as mock_env:
            mock_env.get.return_value = ""  # Env var not set
            validator = ConfigValidator(config)
            validator._validate_database_config()
            assert any("DB_PASSWORD" in e for e in validator.errors)

    def test_postgresql_env_var_placeholder_defined(self) -> None:
        config = {
            "database": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "name": "pbx",
                "user": "admin",
                "password": "${DB_PASSWORD}",
            }
        }
        with patch("pbx.utils.config_validator.environ") as mock_env:
            mock_env.get.return_value = "actual_secret"
            validator = ConfigValidator(config)
            validator._validate_database_config()
            env_errors = [e for e in validator.errors if "DB_PASSWORD" in e]
            assert len(env_errors) == 0

    def test_postgresql_hardcoded_password_warning(self) -> None:
        config = {
            "database": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "name": "pbx",
                "user": "admin",
                "password": "my_hardcoded_secret",
            }
        }
        validator = ConfigValidator(config)
        validator._validate_database_config()
        assert any("hardcoded" in w.lower() for w in validator.warnings)

    def test_non_postgresql_type_rejected(self) -> None:
        """Non-postgresql database types should produce an error."""
        config = {"database": {"type": "sqlite", "path": "pbx.db"}}
        validator = ConfigValidator(config)
        validator._validate_database_config()
        assert any("Unsupported database type" in e for e in validator.errors)
        assert any("PostgreSQL is required" in e for e in validator.errors)

    def test_invalid_db_type_rejected(self) -> None:
        """Arbitrary invalid database types should produce an error."""
        config = {"database": {"type": "mysql"}}
        validator = ConfigValidator(config)
        validator._validate_database_config()
        assert any("Unsupported database type" in e for e in validator.errors)

    def test_default_db_type_postgresql(self) -> None:
        """Default database type should be postgresql, requiring connection fields."""
        config = {"database": {}}
        validator = ConfigValidator(config)
        validator._validate_database_config()
        # Default is postgresql, so missing required fields should cause errors
        assert any("missing required" in e.lower() or "host" in e for e in validator.errors)

    def test_no_database_config(self) -> None:
        """Missing database config should default to postgresql and require fields."""
        config = {}
        validator = ConfigValidator(config)
        validator._validate_database_config()
        # Should default to postgresql and error on missing required fields
        assert any("missing required" in e.lower() or "host" in e for e in validator.errors)


@pytest.mark.unit
class TestValidateApiConfig:
    """Tests for _validate_api_config method."""

    def test_valid_api_port(self) -> None:
        config = {"api": {"port": 9000}}
        validator = ConfigValidator(config)
        validator._validate_api_config()
        port_errors = [e for e in validator.errors if "API port" in e]
        assert len(port_errors) == 0

    def test_invalid_api_port(self) -> None:
        config = {"api": {"port": 99999}}
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any("API port" in e for e in validator.errors)

    def test_invalid_api_port_string(self) -> None:
        config = {"api": {"port": "not_a_port"}}
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any("API port" in e for e in validator.errors)

    def test_invalid_api_port_zero(self) -> None:
        config = {"api": {"port": 0}}
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any("API port" in e for e in validator.errors)

    def test_ssl_enabled_no_certs(self) -> None:
        config = {"api": {"ssl": {"enabled": True}}}
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any("cert_file or key_file" in e for e in validator.errors)

    def test_ssl_enabled_with_env_var_certs(self) -> None:
        config = {
            "api": {
                "ssl": {
                    "enabled": True,
                    "cert_file": "${SSL_CERT}",
                    "key_file": "${SSL_KEY}",
                }
            }
        }
        validator = ConfigValidator(config)
        validator._validate_api_config()
        # Should not check file existence for env var paths
        file_errors = [e for e in validator.errors if "not found" in e]
        assert len(file_errors) == 0

    def test_ssl_enabled_cert_files_not_found(self) -> None:
        config = {
            "api": {
                "ssl": {
                    "enabled": True,
                    "cert_file": "/nonexistent/cert.pem",
                    "key_file": "/nonexistent/key.pem",
                }
            }
        }
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any(
            "certificate file not found" in e.lower() or "cert" in e.lower()
            for e in validator.errors
        )

    def test_ssl_disabled_warning(self) -> None:
        config = {"api": {"ssl": {"enabled": False}}}
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any("SSL/TLS is disabled" in w for w in validator.warnings)

    def test_ssl_not_configured_warning(self) -> None:
        config = {"api": {}}
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any("SSL/TLS is disabled" in w for w in validator.warnings)

    def test_ssl_enabled_missing_cert_file_only(self) -> None:
        config = {
            "api": {
                "ssl": {
                    "enabled": True,
                    "key_file": "/some/key.pem",
                }
            }
        }
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any("cert_file or key_file" in e for e in validator.errors)

    def test_ssl_enabled_missing_key_file_only(self) -> None:
        config = {
            "api": {
                "ssl": {
                    "enabled": True,
                    "cert_file": "/some/cert.pem",
                }
            }
        }
        validator = ConfigValidator(config)
        validator._validate_api_config()
        assert any("cert_file or key_file" in e for e in validator.errors)


@pytest.mark.unit
class TestValidateSecurityConfig:
    """Tests for _validate_security_config method."""

    def test_fips_disabled_warning(self) -> None:
        config = {"security": {"fips_mode": False}}
        validator = ConfigValidator(config)
        validator._validate_security_config()
        assert any("FIPS" in w for w in validator.warnings)

    def test_fips_enabled_no_warning(self) -> None:
        config = {"security": {"fips_mode": True}}
        validator = ConfigValidator(config)
        validator._validate_security_config()
        fips_warnings = [w for w in validator.warnings if "FIPS" in w]
        assert len(fips_warnings) == 0

    def test_high_max_failed_attempts(self) -> None:
        config = {"security": {"max_failed_attempts": 15}}
        validator = ConfigValidator(config)
        validator._validate_security_config()
        assert any("max_failed_attempts" in w for w in validator.warnings)

    def test_reasonable_max_failed_attempts(self) -> None:
        config = {"security": {"max_failed_attempts": 5}}
        validator = ConfigValidator(config)
        validator._validate_security_config()
        attempt_warnings = [w for w in validator.warnings if "max_failed_attempts" in w]
        assert len(attempt_warnings) == 0

    def test_boundary_max_failed_attempts_10(self) -> None:
        config = {"security": {"max_failed_attempts": 10}}
        validator = ConfigValidator(config)
        validator._validate_security_config()
        attempt_warnings = [w for w in validator.warnings if "max_failed_attempts" in w]
        assert len(attempt_warnings) == 0

    def test_boundary_max_failed_attempts_11(self) -> None:
        config = {"security": {"max_failed_attempts": 11}}
        validator = ConfigValidator(config)
        validator._validate_security_config()
        assert any("max_failed_attempts" in w for w in validator.warnings)

    def test_no_security_config(self) -> None:
        config = {}
        validator = ConfigValidator(config)
        validator._validate_security_config()
        # Defaults: fips_mode=False (warning), max_failed_attempts=5 (no warning)
        assert any("FIPS" in w for w in validator.warnings)


@pytest.mark.unit
class TestValidateExtensionsConfig:
    """Tests for _validate_extensions_config method."""

    def test_no_extensions(self) -> None:
        config = {}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("No extensions configured" in w for w in validator.warnings)

    def test_empty_extensions_list(self) -> None:
        config = {"extensions": []}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("No extensions configured" in w for w in validator.warnings)

    def test_duplicate_extensions(self) -> None:
        config = {
            "extensions": [
                {"number": "1001", "password": "SecurePass1!"},
                {"number": "1001", "password": "SecurePass2!"},
            ]
        }
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("Duplicate extension numbers" in e for e in validator.errors)

    def test_no_duplicate_extensions(self) -> None:
        config = {
            "extensions": [
                {"number": "1001", "password": "SecurePass1!"},
                {"number": "1002", "password": "SecurePass2!"},
            ]
        }
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        dup_errors = [e for e in validator.errors if "Duplicate" in e]
        assert len(dup_errors) == 0

    def test_weak_password_password(self) -> None:
        config = {"extensions": [{"number": "1001", "password": "password"}]}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("weak password" in w.lower() for w in validator.warnings)

    def test_weak_password_password1(self) -> None:
        config = {"extensions": [{"number": "1001", "password": "password1"}]}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("weak password" in w.lower() for w in validator.warnings)

    def test_weak_password_123(self) -> None:
        # Pattern ^123+$ matches: 123, 1233, 12333, 123333, etc.
        config = {"extensions": [{"number": "1001", "password": "123"}]}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("weak password" in w.lower() for w in validator.warnings)

    def test_weak_password_admin(self) -> None:
        config = {"extensions": [{"number": "1001", "password": "admin123"}]}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("weak password" in w.lower() for w in validator.warnings)

    def test_weak_password_test(self) -> None:
        config = {"extensions": [{"number": "1001", "password": "test1234"}]}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("weak password" in w.lower() for w in validator.warnings)

    def test_short_password_warning(self) -> None:
        config = {"extensions": [{"number": "1001", "password": "Ab1!"}]}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("too short" in w.lower() for w in validator.warnings)

    def test_strong_password_no_warning(self) -> None:
        config = {"extensions": [{"number": "1001", "password": "V3ryStr0ngP@ss!"}]}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        weak_warnings = [w for w in validator.warnings if "weak" in w.lower()]
        short_warnings = [w for w in validator.warnings if "too short" in w.lower()]
        assert len(weak_warnings) == 0
        assert len(short_warnings) == 0

    def test_missing_number_field(self) -> None:
        config = {"extensions": [{"password": "SecurePass1!"}]}
        validator = ConfigValidator(config)
        # Should not crash
        validator._validate_extensions_config()

    def test_missing_password_field(self) -> None:
        config = {"extensions": [{"number": "1001"}]}
        validator = ConfigValidator(config)
        validator._validate_extensions_config()
        assert any("too short" in w.lower() for w in validator.warnings)


@pytest.mark.unit
class TestValidateCodecsConfig:
    """Tests for _validate_codecs_config method."""

    def test_no_codecs_enabled(self) -> None:
        config = {"codecs": {"opus": {"enabled": False}}}
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        assert any("No audio codecs enabled" in e for e in validator.errors)

    def test_empty_codecs_config(self) -> None:
        config = {"codecs": {}}
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        assert any("No audio codecs enabled" in e for e in validator.errors)

    def test_no_codecs_section(self) -> None:
        config = {}
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        assert any("No audio codecs enabled" in e for e in validator.errors)

    def test_g711_enabled(self) -> None:
        config = {"codecs": {"g711_pcmu": {"enabled": True}}}
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        codec_errors = [e for e in validator.errors if "codec" in e.lower()]
        g711_warnings = [w for w in validator.warnings if "G.711" in w]
        assert len(codec_errors) == 0
        assert len(g711_warnings) == 0

    def test_pcmu_enabled(self) -> None:
        config = {"codecs": {"pcmu": {"enabled": True}}}
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        g711_warnings = [w for w in validator.warnings if "G.711" in w]
        assert len(g711_warnings) == 0

    def test_pcma_enabled(self) -> None:
        config = {"codecs": {"pcma": {"enabled": True}}}
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        g711_warnings = [w for w in validator.warnings if "G.711" in w]
        assert len(g711_warnings) == 0

    def test_no_g711_warning(self) -> None:
        config = {"codecs": {"opus": {"enabled": True}}}
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        assert any("G.711" in w for w in validator.warnings)

    def test_codec_config_non_dict_value(self) -> None:
        config = {"codecs": {"opus": "enabled"}}
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        # Non-dict codec config should not count as enabled
        assert any("No audio codecs enabled" in e for e in validator.errors)

    def test_multiple_codecs_one_g711(self) -> None:
        config = {
            "codecs": {
                "g711_pcmu": {"enabled": True},
                "opus": {"enabled": True},
                "g722": {"enabled": False},
            }
        }
        validator = ConfigValidator(config)
        validator._validate_codecs_config()
        codec_errors = [e for e in validator.errors if "codec" in e.lower()]
        assert len(codec_errors) == 0


@pytest.mark.unit
class TestValidateProductionReadiness:
    """Tests for _validate_production_readiness method."""

    def test_example_in_server_name(self) -> None:
        config = {"server": {"server_name": "example-pbx.local"}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        assert any("example" in w.lower() for w in validator.warnings)

    def test_no_example_in_server_name(self) -> None:
        config = {"server": {"server_name": "production-pbx.acme.com"}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        example_warnings = [
            w for w in validator.warnings if "Server name" in w and "example" in w.lower()
        ]
        assert len(example_warnings) == 0

    def test_voicemail_email_no_smtp_host(self) -> None:
        config = {"voicemail": {"email_notifications": True, "smtp": {}}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        assert any("SMTP host" in w for w in validator.warnings)

    def test_voicemail_email_with_smtp_host(self) -> None:
        config = {"voicemail": {"email_notifications": True, "smtp": {"host": "smtp.acme.com"}}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        smtp_warnings = [w for w in validator.warnings if "SMTP host" in w]
        assert len(smtp_warnings) == 0

    def test_voicemail_example_from_address(self) -> None:
        config = {
            "voicemail": {
                "email_notifications": True,
                "smtp": {"host": "smtp.acme.com"},
                "email": {"from_address": "pbx@example.com"},
            }
        }
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        assert any("example.com" in w for w in validator.warnings)

    def test_voicemail_valid_from_address(self) -> None:
        config = {
            "voicemail": {
                "email_notifications": True,
                "smtp": {"host": "smtp.acme.com"},
                "email": {"from_address": "pbx@acme.com"},
            }
        }
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        example_warnings = [w for w in validator.warnings if "example.com" in w]
        assert len(example_warnings) == 0

    def test_voicemail_disabled(self) -> None:
        config = {"voicemail": {"email_notifications": False}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        smtp_warnings = [w for w in validator.warnings if "SMTP" in w]
        assert len(smtp_warnings) == 0

    def test_debug_logging_warning(self) -> None:
        config = {"logging": {"level": "DEBUG"}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        assert any("DEBUG" in w for w in validator.warnings)

    def test_info_logging_no_warning(self) -> None:
        config = {"logging": {"level": "INFO"}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        log_warnings = [w for w in validator.warnings if "DEBUG" in w]
        assert len(log_warnings) == 0

    def test_warning_logging_no_warning(self) -> None:
        config = {"logging": {"level": "WARNING"}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        log_warnings = [w for w in validator.warnings if "DEBUG" in w]
        assert len(log_warnings) == 0

    def test_no_logging_config(self) -> None:
        config = {}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        # Default level "INFO" should not trigger warning
        log_warnings = [w for w in validator.warnings if "DEBUG" in w]
        assert len(log_warnings) == 0

    def test_empty_server_name(self) -> None:
        config = {"server": {"server_name": ""}}
        validator = ConfigValidator(config)
        validator._validate_production_readiness()
        # Empty string should not trigger "example" warning
        example_warnings = [
            w for w in validator.warnings if "example" in w.lower() and "Server" in w
        ]
        assert len(example_warnings) == 0


@pytest.mark.unit
class TestValidateConfigOnStartup:
    """Tests for validate_config_on_startup function."""

    def test_valid_config_returns_true(self) -> None:
        config = {
            "server": {
                "sip_port": 5060,
                "rtp_port_range_start": 10000,
                "rtp_port_range_end": 20000,
                "external_ip": "10.0.0.1",
            },
            "database": {
                "type": "postgresql",
                "host": "db",
                "port": 5432,
                "name": "pbx",
                "user": "u",
                "password": "${P}",
            },
            "api": {
                "port": 9000,
                "ssl": {"enabled": True, "cert_file": "${C}", "key_file": "${K}"},
            },
            "security": {"fips_mode": True, "max_failed_attempts": 5},
            "extensions": [{"number": "1001", "password": "G00dPa$$word!"}],
            "codecs": {"g711_pcmu": {"enabled": True}},
            "logging": {"level": "INFO"},
        }
        with patch("pbx.utils.config_validator.environ") as mock_env:
            mock_env.get.return_value = "value"
            result = validate_config_on_startup(config)
            assert result is True

    def test_invalid_config_returns_false(self) -> None:
        config = {"server": {"sip_port": -1}}
        result = validate_config_on_startup(config)
        assert result is False

    def test_warnings_only_returns_true(self) -> None:
        # Config that produces warnings but no errors
        config = {
            "server": {
                "sip_port": 5060,
                "rtp_port_range_start": 10000,
                "rtp_port_range_end": 20000,
                "external_ip": "10.0.0.1",
            },
            "database": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "name": "pbx",
                "user": "admin",
                "password": "hardcoded_pw",
            },
            "api": {"port": 9000},
            "security": {"fips_mode": False},
            "codecs": {"g711_pcmu": {"enabled": True}},
        }
        result = validate_config_on_startup(config)
        # Should return True (warnings are ok)
        assert result is True

    def test_no_errors_no_warnings(self) -> None:
        """Config that passes all checks cleanly."""
        config = {
            "server": {
                "sip_port": 5060,
                "rtp_port_range_start": 10000,
                "rtp_port_range_end": 20000,
                "external_ip": "10.0.0.1",
                "server_name": "production-pbx",
            },
            "database": {
                "type": "postgresql",
                "host": "db",
                "port": 5432,
                "name": "pbx",
                "user": "u",
                "password": "${P}",
            },
            "api": {
                "port": 9000,
                "ssl": {"enabled": True, "cert_file": "${C}", "key_file": "${K}"},
            },
            "security": {"fips_mode": True, "max_failed_attempts": 5},
            "extensions": [{"number": "1001", "password": "G00dPa$$word!"}],
            "codecs": {"g711_pcmu": {"enabled": True}},
            "logging": {"level": "INFO"},
        }
        with patch("pbx.utils.config_validator.environ") as mock_env:
            mock_env.get.return_value = "value"
            result = validate_config_on_startup(config)
            assert result is True
