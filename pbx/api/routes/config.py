"""Flask Blueprint for configuration and SSL management routes."""

import ipaddress
import ssl
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Blueprint, Response

from pbx.api.utils import (
    get_pbx_core,
    get_request_body,
    require_admin,
    send_json,
    verify_authentication,
)
from pbx.utils.logger import get_logger

logger = get_logger()

# Default DTMF configuration to use when config is not available
DEFAULT_DTMF_CONFIG = {
    "mode": "rfc2833",
    "payload_type": 101,
    "duration": 100,
    "volume": -10,
}

# Default config structure to use when not authenticated or PBX not initialized
DEFAULT_CONFIG = {
    "smtp": {"host": "", "port": 587, "username": ""},
    "email": {"from_address": ""},
    "email_notifications": False,
    "integrations": {},
}

# Optional imports for SSL certificate generation
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    SSL_GENERATION_AVAILABLE = True
except ImportError:
    SSL_GENERATION_AVAILABLE = False

config_bp = Blueprint("config", __name__)


@config_bp.route("/api/config", methods=["GET"])
def get_config() -> tuple[Response, int]:
    """Get current configuration.

    Returns configuration including integrations field required by frontend.
    """
    # SECURITY: Check admin authentication but allow graceful degradation
    # Return empty config if not authenticated to prevent UI errors
    is_authenticated, payload = verify_authentication()
    if not is_authenticated or not payload.get("is_admin", False):
        # Return default config structure for non-authenticated users
        # This allows the UI to load gracefully without errors
        return send_json(DEFAULT_CONFIG), 200

    pbx_core = get_pbx_core()
    if pbx_core:
        config_data = {
            "smtp": {
                "host": pbx_core.config.get("voicemail.smtp.host", ""),
                "port": pbx_core.config.get("voicemail.smtp.port", 587),
                "username": pbx_core.config.get("voicemail.smtp.username", ""),
            },
            "email": {"from_address": pbx_core.config.get("voicemail.email.from_address", "")},
            "email_notifications": pbx_core.config.get("voicemail.email_notifications", False),
            # Frontend integration loaders (Jitsi, Matrix, EspoCRM) require this field
            "integrations": pbx_core.config.get("integrations", {}),
        }
        return send_json(config_data), 200
    # Return default config if PBX not initialized
    return send_json(DEFAULT_CONFIG), 200


@config_bp.route("/api/config/full", methods=["GET"])
@require_admin
def get_full_config() -> tuple[Response, int]:
    """Get full system configuration for admin panel."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        # Return comprehensive configuration for the admin panel
        config_data = {
            "server": {
                "sip_port": pbx_core.config.get("server.sip_port", 5060),
                "external_ip": pbx_core.config.get("server.external_ip", ""),
                "server_name": pbx_core.config.get("server.server_name", "Warden Voip"),
            },
            "api": {
                "port": pbx_core.config.get("api.port", 9000),
                "ssl": {
                    "enabled": pbx_core.config.get("api.ssl.enabled", False),
                    "cert_file": pbx_core.config.get("api.ssl.cert_file", "certs/server.crt"),
                    "key_file": pbx_core.config.get("api.ssl.key_file", "certs/server.key"),
                },
            },
            "features": {
                "call_recording": pbx_core.config.get("features.call_recording", True),
                "call_transfer": pbx_core.config.get("features.call_transfer", True),
                "call_hold": pbx_core.config.get("features.call_hold", True),
                "conference": pbx_core.config.get("features.conference", True),
                "voicemail": pbx_core.config.get("features.voicemail", True),
                "call_parking": pbx_core.config.get("features.call_parking", True),
                "call_queues": pbx_core.config.get("features.call_queues", True),
                "presence": pbx_core.config.get("features.presence", True),
                "music_on_hold": pbx_core.config.get("features.music_on_hold", True),
                "auto_attendant": pbx_core.config.get("features.auto_attendant", True),
                "webrtc": {"enabled": pbx_core.config.get("features.webrtc.enabled", True)},
                "webhooks": {"enabled": pbx_core.config.get("features.webhooks.enabled", False)},
                "crm_integration": {
                    "enabled": pbx_core.config.get("features.crm_integration.enabled", True)
                },
                "hot_desking": {
                    "enabled": pbx_core.config.get("features.hot_desking.enabled", True),
                    "require_pin": pbx_core.config.get("features.hot_desking.require_pin", True),
                },
                "voicemail_transcription": {
                    "enabled": pbx_core.config.get("features.voicemail_transcription.enabled", True)
                },
            },
            "voicemail": {
                "max_message_duration": pbx_core.config.get("voicemail.max_message_duration", 180),
                "max_greeting_duration": pbx_core.config.get("voicemail.max_greeting_duration", 30),
                "no_answer_timeout": pbx_core.config.get("voicemail.no_answer_timeout", 30),
                "allow_custom_greetings": pbx_core.config.get(
                    "voicemail.allow_custom_greetings", True
                ),
                "email_notifications": pbx_core.config.get("voicemail.email_notifications", True),
                "smtp": {
                    "host": pbx_core.config.get("voicemail.smtp.host", ""),
                    "port": pbx_core.config.get("voicemail.smtp.port", 587),
                    "use_tls": pbx_core.config.get("voicemail.smtp.use_tls", True),
                    "username": pbx_core.config.get("voicemail.smtp.username", ""),
                },
                "email": {
                    "from_address": pbx_core.config.get("voicemail.email.from_address", ""),
                    "from_name": pbx_core.config.get("voicemail.email.from_name", "PBX Voicemail"),
                },
            },
            "recording": {
                "auto_record": pbx_core.config.get("recording.auto_record", False),
                "format": pbx_core.config.get("recording.format", "wav"),
                "storage_path": pbx_core.config.get("recording.storage_path", "recordings"),
            },
            "security": {
                "password": {
                    "min_length": pbx_core.config.get("security.password.min_length", 12),
                    "require_uppercase": pbx_core.config.get(
                        "security.password.require_uppercase", True
                    ),
                    "require_lowercase": pbx_core.config.get(
                        "security.password.require_lowercase", True
                    ),
                    "require_digit": pbx_core.config.get("security.password.require_digit", True),
                    "require_special": pbx_core.config.get(
                        "security.password.require_special", True
                    ),
                },
                "rate_limit": {
                    "max_attempts": pbx_core.config.get("security.rate_limit.max_attempts", 5),
                    "lockout_duration": pbx_core.config.get(
                        "security.rate_limit.lockout_duration", 900
                    ),
                },
                "fips_mode": pbx_core.config.get("security.fips_mode", True),
            },
            "conference": {
                "max_participants": pbx_core.config.get("conference.max_participants", 50),
                "record_conferences": pbx_core.config.get("conference.record_conferences", False),
            },
        }

        return send_json(config_data), 200
    except (KeyError, OSError, TypeError, ValueError, ssl.SSLError) as e:
        return send_json({"error": str(e)}, 500), 500


@config_bp.route("/api/config/dtmf", methods=["GET"])
def get_dtmf_config() -> tuple[Response, int]:
    """Get DTMF configuration."""
    # SECURITY: Check admin authentication but allow graceful degradation
    # Return default config if not authenticated to prevent UI errors
    is_authenticated, payload = verify_authentication()
    if not is_authenticated or not payload.get("is_admin", False):
        # Return default DTMF configuration for non-authenticated users
        # This allows the UI to load gracefully without errors
        return send_json(DEFAULT_DTMF_CONFIG), 200

    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json(DEFAULT_DTMF_CONFIG), 200

    try:
        dtmf_config = pbx_core.config.get_dtmf_config()
        if dtmf_config is not None:
            return send_json(dtmf_config), 200
        # Return default DTMF configuration instead of error
        return send_json(DEFAULT_DTMF_CONFIG), 200
    except Exception as e:
        logger.error(f"Error getting DTMF config: {e}")
        # Return default configuration on error
        return send_json(DEFAULT_DTMF_CONFIG), 200


@config_bp.route("/api/config", methods=["PUT"])
@require_admin
def update_config() -> tuple[Response, int]:
    """Update system configuration."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        body = get_request_body()

        # Update configuration
        success = pbx_core.config.update_email_config(body)

        if success:
            return send_json(
                {
                    "success": True,
                    "message": "Configuration updated successfully. Restart required.",
                }
            ), 200
        return send_json({"error": "Failed to update configuration"}, 500), 500
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@config_bp.route("/api/config/section", methods=["PUT"])
@require_admin
def update_config_section() -> tuple[Response, int]:
    """Update a specific section of system configuration."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        body = get_request_body()
        section = body.get("section")
        data = body.get("data")

        if section is None or data is None:
            return send_json({"error": "Missing section or data"}, 400), 400

        # Update the configuration section
        # Use config.get() to safely retrieve section with defaults
        current_section = pbx_core.config.config.get(section, {})

        # Deep merge the data into the section
        def deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
            """Deep merge source dict into target dict."""
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
            return target

        # Create merged section and update config
        merged_section = deep_merge(
            current_section.copy() if isinstance(current_section, dict) else {}, data
        )
        pbx_core.config.config[section] = merged_section

        # Save configuration
        success = pbx_core.config.save()

        if success:
            return send_json(
                {
                    "success": True,
                    "message": "Configuration updated successfully. Restart may be required for some changes.",
                }
            ), 200
        return send_json({"error": "Failed to save configuration"}, 500), 500
    except (KeyError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@config_bp.route("/api/config/dtmf", methods=["PUT", "POST"])
@require_admin
def update_dtmf_config() -> tuple[Response, int]:
    """Update DTMF configuration."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        body = get_request_body()

        # Update DTMF configuration
        success = pbx_core.config.update_dtmf_config(body)

        if success:
            return send_json(
                {
                    "success": True,
                    "message": "DTMF configuration updated successfully. PBX restart required for changes to take effect.",
                }
            ), 200
        return send_json({"error": "Failed to update DTMF configuration"}, 500), 500
    except Exception as e:
        return send_json({"error": str(e)}, 500), 500


@config_bp.route("/api/ssl/status", methods=["GET"])
@require_admin
def get_ssl_status() -> tuple[Response, int]:
    """Get SSL/HTTPS configuration status."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        ssl_config = pbx_core.config.get("api.ssl", {})
        cert_file = ssl_config.get("cert_file", "certs/server.crt")
        key_file = ssl_config.get("key_file", "certs/server.key")

        # Check if certificate files exist
        cert_exists = Path(cert_file).exists()
        key_exists = Path(key_file).exists()

        # Get certificate details if it exists
        cert_details = None
        if cert_exists and SSL_GENERATION_AVAILABLE:
            try:
                with Path(cert_file).open("rb") as f:
                    cert_data = f.read()
                    cert = x509.load_pem_x509_certificate(cert_data, default_backend())

                    now = datetime.now(UTC)
                    cert_details = {
                        "subject": cert.subject.rfc4514_string(),
                        "issuer": cert.issuer.rfc4514_string(),
                        "valid_from": cert.not_valid_before.isoformat(),
                        "valid_until": cert.not_valid_after.isoformat(),
                        "is_expired": cert.not_valid_after < now,
                        "days_until_expiry": (cert.not_valid_after - now).days,
                        "serial_number": str(cert.serial_number),
                    }
            except (KeyError, OSError, TypeError, ValueError) as e:
                logger.warning(f"Failed to parse certificate: {e}")

        status_data = {
            "enabled": ssl_config.get("enabled", False),
            "cert_file": cert_file,
            "key_file": key_file,
            "cert_exists": cert_exists,
            "key_exists": key_exists,
            "cert_details": cert_details,
            "ca": {
                "enabled": ssl_config.get("ca", {}).get("enabled", False),
                "server_url": ssl_config.get("ca", {}).get("server_url", ""),
            },
        }

        return send_json(status_data), 200
    except (KeyError, OSError, TypeError, ValueError) as e:
        return send_json({"error": str(e)}, 500), 500


@config_bp.route("/api/ssl/generate-certificate", methods=["POST"])
@require_admin
def generate_ssl_certificate() -> tuple[Response, int]:
    """Generate self-signed SSL certificate."""
    pbx_core = get_pbx_core()
    if not pbx_core:
        return send_json({"error": "PBX not initialized"}, 500), 500

    try:
        body = get_request_body() or {}

        # Get parameters
        hostname = body.get("hostname", pbx_core.config.get("server.external_ip", "localhost"))
        days_valid = body.get("days_valid", 365)
        cert_dir = body.get("cert_dir", "certs")

        # Validate parameters
        if not hostname:
            hostname = "localhost"

        if not isinstance(days_valid, int) or days_valid < 1 or days_valid > 3650:
            days_valid = 365

        logger.info(f"Generating self-signed SSL certificate for {hostname}")

        # Check if SSL generation is available
        if not SSL_GENERATION_AVAILABLE:
            return send_json(
                {
                    "error": "Required cryptography library not available",
                    "details": "Install with: pip install cryptography",
                },
                500,
            ), 500

        # Create cert directory if it doesn't exist
        cert_path = Path(cert_dir)
        cert_path.mkdir(exist_ok=True)

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Generate certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Warden Voip"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ]
        )

        # Build list of Subject Alternative Names
        san_list = [
            x509.DNSName(hostname),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]

        # Try to add the hostname as an IP address if it's a valid IP
        try:
            ip = ipaddress.ip_address(hostname)
            san_list.append(x509.IPAddress(ip))
        except ValueError:
            # Not an IP address, it's a hostname
            pass

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(UTC))
            .not_valid_after(datetime.now(UTC) + timedelta(days=days_valid))
            .add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        # Write private key to file
        key_file = cert_path / "server.key"
        with key_file.open("wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # set restrictive permissions on private key
        key_file.chmod(0o600)

        # Write certificate to file
        cert_file = cert_path / "server.crt"
        with cert_file.open("wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        logger.info(f"SSL certificate generated successfully: {cert_file}")

        # Update configuration to enable SSL
        ssl_config = pbx_core.config.get("api.ssl", {})
        ssl_config["enabled"] = True
        ssl_config["cert_file"] = str(cert_file)
        ssl_config["key_file"] = str(key_file)

        pbx_core.config.config.setdefault("api", {})["ssl"] = ssl_config
        pbx_core.config.save()

        return send_json(
            {
                "success": True,
                "message": "SSL certificate generated successfully. Server restart required to enable HTTPS.",
                "cert_file": str(cert_file),
                "key_file": str(key_file),
                "hostname": hostname,
                "valid_days": days_valid,
            }
        ), 200
    except (KeyError, OSError, TypeError, ValueError) as e:
        logger.error(f"Failed to generate SSL certificate: {e}")
        traceback.print_exc()
        return send_json({"error": str(e)}, 500), 500
