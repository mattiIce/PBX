"""
STIR/SHAKEN Implementation for Caller ID Authentication
RFC 8224 (PASSporT), RFC 8588 (SIP)

Provides cryptographic verification of caller identity to prevent spoofing.
"""

import base64
import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.x509.oid import NameOID

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class AttestationLevel(Enum):
    """
    STIR/SHAKEN Attestation Levels

    A (Full Attestation): Service provider has authenticated the caller and is authorized to use the number
    B (Partial Attestation): Provider authenticated caller but cannot verify authorization to use the number
    C (Gateway Attestation): Provider originated the call but cannot authenticate the caller
    """

    FULL = "A"
    PARTIAL = "B"
    GATEWAY = "C"


class VerificationStatus(Enum):
    """Call verification status"""

    NOT_VERIFIED = "not_verified"
    VERIFIED_FULL = "verified_full"  # Attestation A
    VERIFIED_PARTIAL = "verified_partial"  # Attestation B
    VERIFIED_GATEWAY = "verified_gateway"  # Attestation C
    VERIFICATION_FAILED = "failed"
    NO_SIGNATURE = "no_signature"


class STIRSHAKENManager:
    """
    Manages STIR/SHAKEN caller ID authentication

    Features:
    - PASSporT token creation and validation
    - Certificate management
    - SIP Identity header handling
    - Verification service integration
    """

    def __init__(self, config: dict | None = None) -> None:
        """
        Initialize STIR/SHAKEN manager

        Args:
            config: Configuration dictionary with:
                - certificate_path: Path to signing certificate
                - private_key_path: Path to private key
                - ca_cert_path: Path to CA certificate bundle
                - originating_tn: Service provider telephone number
                - service_provider_code: SP code for origination
                - verification_service_url: Optional external verification service
                - enable_signing: Whether to sign outgoing calls (default: True)
                - enable_verification: Whether to verify incoming calls (default: True)
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}

        if not CRYPTO_AVAILABLE:
            self.logger.error("Cryptography library not available. STIR/SHAKEN disabled.")
            self.enabled = False
            return

        self.enabled = True
        self.private_key = None
        self.certificate = None
        self.ca_bundle = None

        # Load certificates if configured
        if self.config.get("private_key_path"):
            self._load_private_key(self.config["private_key_path"])

        if self.config.get("certificate_path"):
            self._load_certificate(self.config["certificate_path"])

        if self.config.get("ca_cert_path"):
            self._load_ca_bundle(self.config["ca_cert_path"])

        # Configuration options
        self.enable_signing = self.config.get("enable_signing", True)
        self.enable_verification = self.config.get("enable_verification", True)
        self.originating_tn = self.config.get("originating_tn", "")
        self.service_provider_code = self.config.get("service_provider_code", "")

        self.logger.info(
            f"STIR/SHAKEN initialized (signing: {self.enable_signing}, verification: {self.enable_verification})"
        )

    def _load_private_key(self, key_path: str) -> None:
        """Load private key from file"""
        try:
            with open(key_path, "rb") as f:
                key_data = f.read()
                self.private_key = serialization.load_pem_private_key(
                    key_data, password=None, backend=default_backend()
                )
            self.logger.info(f"Loaded private key from {key_path}")
        except OSError as e:
            self.logger.error(f"Failed to load private key: {e}")
            self.enabled = False

    def _load_certificate(self, cert_path: str) -> None:
        """Load certificate from file"""
        try:
            with open(cert_path, "rb") as f:
                cert_data = f.read()
                self.certificate = x509.load_pem_x509_certificate(cert_data, default_backend())
            self.logger.info(f"Loaded certificate from {cert_path}")
        except OSError as e:
            self.logger.error(f"Failed to load certificate: {e}")
            self.enabled = False

    def _load_ca_bundle(self, ca_path: str) -> None:
        """Load CA certificate bundle"""
        try:
            with open(ca_path, "rb") as f:
                ca_data = f.read()
                # Load all certificates from bundle
                self.ca_bundle = []
                for cert_pem in ca_data.split(b"-----END CERTIFICATE-----"):
                    if b"-----BEGIN CERTIFICATE-----" in cert_pem:
                        full_cert_pem = cert_pem + b"-----END CERTIFICATE-----"
                        cert = x509.load_pem_x509_certificate(full_cert_pem.strip(), default_backend())
                        self.ca_bundle.append(cert)
            self.logger.info(f"Loaded CA bundle with {len(self.ca_bundle)} certificates")
        except OSError as e:
            self.logger.error(f"Failed to load CA bundle: {e}")

    def create_passport(
        self,
        originating_tn: str,
        destination_tn: str,
        attestation: AttestationLevel = AttestationLevel.FULL,
        orig_id: str | None = None,
    ) -> str | None:
        """
        Create a PASSporT token (RFC 8225)

        Args:
            originating_tn: Originating telephone number (E.164 format)
            destination_tn: Destination telephone number (E.164 format)
            attestation: Attestation level (A, B, or C)
            orig_id: Optional origination identifier (UUID)

        Returns:
            Signed PASSporT JWT token or None if signing fails
        """
        if not self.enabled or not self.enable_signing:
            self.logger.warning("STIR/SHAKEN signing is disabled")
            return None

        if not self.private_key or not self.certificate:
            self.logger.error("Cannot create PASSporT: missing private key or certificate")
            return None

        # Create PASSporT header
        header = {
            "alg": "ES256",  # ECDSA with SHA-256 (or RS256 for RSA)
            "ppt": "shaken",  # PASSporT type
            "typ": "passport",
            "x5u": self._get_certificate_url(),  # URL to certificate
        }

        # If using RSA (common for testing/development)
        if isinstance(self.private_key, rsa.RSAPrivateKey):
            header["alg"] = "RS256"

        # Create PASSporT payload
        iat = int(time.time())
        payload = {
            "attest": attestation.value,
            "dest": {"tn": [self._normalize_tn(destination_tn)]},
            "iat": iat,
            "orig": {"tn": self._normalize_tn(originating_tn)},
            "origid": orig_id or str(uuid.uuid4()),
        }

        # Encode header and payload
        header_b64 = self._base64url_encode(json.dumps(header).encode())
        payload_b64 = self._base64url_encode(json.dumps(payload).encode())

        # Create signature
        message = f"{header_b64}.{payload_b64}".encode()

        try:
            if isinstance(self.private_key, rsa.RSAPrivateKey):
                signature = self.private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
            else:
                # For ECDSA keys
                from cryptography.hazmat.primitives.asymmetric import ec

                signature = self.private_key.sign(message, ec.ECDSA(hashes.SHA256()))

            signature_b64 = self._base64url_encode(signature)

            # Return complete JWT
            passport = f"{header_b64}.{payload_b64}.{signature_b64}"
            self.logger.debug(
                f"Created PASSporT for {originating_tn} -> {destination_tn} (attest: {attestation.value})"
            )
            return passport

        except Exception as e:
            self.logger.error(f"Failed to sign PASSporT: {e}")
            return None

    def verify_passport(self, passport: str) -> tuple[bool, dict | None, str]:
        """
        Verify a PASSporT token

        Args:
            passport: JWT PASSporT token

        Returns:
            tuple of (valid: bool, payload: dict, reason: str)
        """
        if not self.enabled or not self.enable_verification:
            return False, None, "Verification disabled"

        try:
            # Split JWT into parts
            parts = passport.split(".")
            if len(parts) != 3:
                return False, None, "Invalid JWT format"

            header_b64, payload_b64, signature_b64 = parts

            # Decode header and payload
            header = json.loads(self._base64url_decode(header_b64))
            payload = json.loads(self._base64url_decode(payload_b64))

            # Validate PASSporT type
            if header.get("ppt") != "shaken":
                return False, None, "Not a SHAKEN PASSporT"

            # Check expiration (PASSporT valid for 60 seconds per RFC 8224)
            iat = payload.get("iat", 0)
            now = int(time.time())
            if now - iat > 60:
                return False, payload, "PASSporT expired"

            # Verify signature
            message = f"{header_b64}.{payload_b64}".encode()
            signature = self._base64url_decode(signature_b64)

            # Get certificate from x5u header
            cert_url = header.get("x5u")
            if not cert_url:
                return False, payload, "Missing certificate URL"

            # In production, would fetch and validate certificate from URL
            # For now, use configured certificate
            if not self.certificate:
                return False, payload, "No certificate for verification"

            public_key = self.certificate.public_key()

            try:
                if header.get("alg") == "RS256":
                    public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
                else:  # ES256
                    from cryptography.hazmat.primitives.asymmetric import ec

                    public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))

                self.logger.debug(f"Verified PASSporT: {payload}")
                return True, payload, "Signature valid"

            except (KeyError, TypeError, ValueError) as e:
                return False, payload, f"Signature verification failed: {e}"

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"PASSporT verification error: {e}")
            return False, None, str(e)

    def create_identity_header(
        self,
        originating_tn: str,
        destination_tn: str,
        attestation: AttestationLevel = AttestationLevel.FULL,
        orig_id: str | None = None,
    ) -> str | None:
        """
        Create SIP Identity header with PASSporT (RFC 8588)

        Args:
            originating_tn: Originating telephone number
            destination_tn: Destination telephone number
            attestation: Attestation level
            orig_id: Optional origination ID

        Returns:
            Identity header value or None
        """
        passport = self.create_passport(originating_tn, destination_tn, attestation, orig_id)
        if not passport:
            return None

        # Create Identity header with PASSporT
        # Format: Identity: <passport>;info=<cert-url>;alg=<algorithm>;ppt=shaken
        cert_url = self._get_certificate_url()
        identity = f'"{passport}";info=<{cert_url}>;alg=RS256;ppt=shaken'

        return identity

    def parse_identity_header(self, identity_header: str) -> dict | None:
        """
        Parse SIP Identity header

        Args:
            identity_header: Identity header value

        Returns:
            Dictionary with parsed components or None
        """
        try:
            # Extract PASSporT (between quotes)
            if '"' in identity_header:
                start = identity_header.index('"') + 1
                end = identity_header.index('"', start)
                passport = identity_header[start:end]
            else:
                # No quotes, take first part before semicolon
                passport = identity_header.split(";", maxsplit=1)[0]

            # Parse parameters
            params = {}
            for param in identity_header.split(";")[1:]:
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key.strip()] = value.strip("<>")

            return {
                "passport": passport,
                "info": params.get("info"),
                "alg": params.get("alg"),
                "ppt": params.get("ppt"),
            }

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Failed to parse Identity header: {e}")
            return None

    def verify_identity_header(
        self, identity_header: str
    ) -> tuple[VerificationStatus, dict | None]:
        """
        Verify a SIP Identity header

        Args:
            identity_header: Identity header value

        Returns:
            tuple of (status: VerificationStatus, payload: dict)
        """
        if not identity_header:
            return VerificationStatus.NO_SIGNATURE, None

        # Parse Identity header
        parsed = self.parse_identity_header(identity_header)
        if not parsed:
            return VerificationStatus.VERIFICATION_FAILED, None

        # Verify PASSporT
        valid, payload, reason = self.verify_passport(parsed["passport"])

        if not valid:
            self.logger.warning(f"Identity verification failed: {reason}")
            return VerificationStatus.VERIFICATION_FAILED, payload

        # Map attestation level to verification status
        attestation = payload.get("attest", "C")
        status_map = {
            "A": VerificationStatus.VERIFIED_FULL,
            "B": VerificationStatus.VERIFIED_PARTIAL,
            "C": VerificationStatus.VERIFIED_GATEWAY,
        }

        status = status_map.get(attestation, VerificationStatus.VERIFICATION_FAILED)
        return status, payload

    def get_verification_status_display(self, status: VerificationStatus) -> dict:
        """
        Get human-readable verification status information

        Args:
            status: VerificationStatus enum

        Returns:
            Dictionary with display information
        """
        status_info = {
            VerificationStatus.VERIFIED_FULL: {
                "label": "✓ Verified",
                "description": "Caller ID authenticated and authorized",
                "trust_level": "high",
                "icon": "✓",
            },
            VerificationStatus.VERIFIED_PARTIAL: {
                "label": "✓ Partially Verified",
                "description": "Caller authenticated but not fully authorized",
                "trust_level": "medium",
                "icon": "~",
            },
            VerificationStatus.VERIFIED_GATEWAY: {
                "label": "✓ Gateway",
                "description": "Call originated from gateway",
                "trust_level": "low",
                "icon": "?",
            },
            VerificationStatus.NO_SIGNATURE: {
                "label": "Not Signed",
                "description": "No caller ID signature present",
                "trust_level": "unknown",
                "icon": "—",
            },
            VerificationStatus.VERIFICATION_FAILED: {
                "label": "✗ Failed",
                "description": "Caller ID verification failed",
                "trust_level": "none",
                "icon": "✗",
            },
            VerificationStatus.NOT_VERIFIED: {
                "label": "Not Verified",
                "description": "Verification not performed",
                "trust_level": "unknown",
                "icon": "—",
            },
        }

        return status_info.get(status, status_info[VerificationStatus.NOT_VERIFIED])

    def _normalize_tn(self, tn: str) -> str:
        """
        Normalize telephone number to E.164 format

        Args:
            tn: Telephone number

        Returns:
            Normalized number (e.g., +12125551234)
        """
        # Remove non-digit characters
        digits = "".join(c for c in tn if c.isdigit())

        # Add + prefix if not present
        if not tn.startswith("+"):
            # Assume US/Canada if 10 digits
            if len(digits) == 10:
                return f"+1{digits}"
            # Add + to 11+ digit numbers
            if len(digits) >= 11:
                return f"+{digits}"

        return tn

    def _get_certificate_url(self) -> str:
        """Get certificate URL for Identity header"""
        # In production, this would be a public URL to the certificate
        # For now, return a placeholder
        return self.config.get("certificate_url", "https://cert.example.com/cert.pem")

    def _base64url_encode(self, data: bytes) -> str:
        """Base64 URL-safe encode"""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _base64url_decode(self, data: str) -> bytes:
        """Base64 URL-safe decode"""
        # Add padding if needed
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def generate_test_certificate(self, output_dir: str | None = None) -> tuple[str, str]:
        """
        Generate self-signed certificate for testing

        Args:
            output_dir: Directory to save certificate files

        Returns:
            tuple of (cert_path, key_path)
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")

        output_dir = output_dir or "/tmp"  # nosec B108 - temp directory for certificate generation

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        # Generate certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Test"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Test"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test PBX"),
                x509.NameAttribute(NameOID.COMMON_NAME, "pbx.test.local"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(UTC))
            .not_valid_after(datetime.now(UTC) + timedelta(days=365))
            .sign(private_key, hashes.SHA256(), default_backend())
        )

        # Write certificate
        cert_path = f"{output_dir}/stir_shaken_cert.pem"
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Write private key
        key_path = f"{output_dir}/stir_shaken_key.pem"
        with open(key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        self.logger.info(f"Generated test certificate: {cert_path}, {key_path}")
        return cert_path, key_path


# Utility functions for integration with PBX core


def add_stir_shaken_to_invite(
    sip_message: Any,
    stir_shaken_manager: STIRSHAKENManager,
    from_number: str,
    to_number: str,
    attestation: AttestationLevel = AttestationLevel.FULL,
) -> None:
    """
    Add STIR/SHAKEN Identity header to SIP INVITE message

    Args:
        sip_message: SIPMessage object
        stir_shaken_manager: STIRSHAKENManager instance
        from_number: Originating number
        to_number: Destination number
        attestation: Attestation level

    Returns:
        Modified SIPMessage with Identity header
    """
    if not stir_shaken_manager or not stir_shaken_manager.enabled:
        return sip_message

    identity = stir_shaken_manager.create_identity_header(from_number, to_number, attestation)

    if identity:
        sip_message.set_header("Identity", identity)

    return sip_message


def verify_stir_shaken_invite(
    sip_message: Any, stir_shaken_manager: STIRSHAKENManager
) -> tuple[VerificationStatus, dict | None]:
    """
    Verify STIR/SHAKEN signature on incoming SIP INVITE

    Args:
        sip_message: SIPMessage object
        stir_shaken_manager: STIRSHAKENManager instance

    Returns:
        tuple of (status: VerificationStatus, payload: dict)
    """
    if not stir_shaken_manager or not stir_shaken_manager.enabled:
        return VerificationStatus.NOT_VERIFIED, None

    identity_header = sip_message.get_header("Identity")
    if not identity_header:
        return VerificationStatus.NO_SIGNATURE, None

    return stir_shaken_manager.verify_identity_header(identity_header)
