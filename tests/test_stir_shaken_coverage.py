"""Comprehensive tests for STIR/SHAKEN caller ID authentication module."""

import base64
import json
import time
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pbx.features.stir_shaken import (
    AttestationLevel,
    STIRSHAKENManager,
    VerificationStatus,
    add_stir_shaken_to_invite,
    verify_stir_shaken_invite,
)


@pytest.mark.unit
class TestAttestationLevel:
    """Tests for the AttestationLevel enum."""

    def test_full_attestation_value(self) -> None:
        assert AttestationLevel.FULL.value == "A"

    def test_partial_attestation_value(self) -> None:
        assert AttestationLevel.PARTIAL.value == "B"

    def test_gateway_attestation_value(self) -> None:
        assert AttestationLevel.GATEWAY.value == "C"


@pytest.mark.unit
class TestVerificationStatus:
    """Tests for the VerificationStatus enum."""

    def test_not_verified(self) -> None:
        assert VerificationStatus.NOT_VERIFIED.value == "not_verified"

    def test_verified_full(self) -> None:
        assert VerificationStatus.VERIFIED_FULL.value == "verified_full"

    def test_verified_partial(self) -> None:
        assert VerificationStatus.VERIFIED_PARTIAL.value == "verified_partial"

    def test_verified_gateway(self) -> None:
        assert VerificationStatus.VERIFIED_GATEWAY.value == "verified_gateway"

    def test_verification_failed(self) -> None:
        assert VerificationStatus.VERIFICATION_FAILED.value == "failed"

    def test_no_signature(self) -> None:
        assert VerificationStatus.NO_SIGNATURE.value == "no_signature"


@pytest.mark.unit
class TestSTIRSHAKENManagerInit:
    """Tests for STIRSHAKENManager initialization."""

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_init_default_config(self) -> None:
        manager = STIRSHAKENManager()
        assert manager.enabled is True
        assert manager.enable_signing is True
        assert manager.enable_verification is True
        assert manager.originating_tn == ""
        assert manager.service_provider_code == ""
        assert manager.private_key is None
        assert manager.certificate is None
        assert manager.ca_bundle is None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_init_with_custom_config(self) -> None:
        config = {
            "enable_signing": False,
            "enable_verification": False,
            "originating_tn": "+12125551234",
            "service_provider_code": "SP001",
        }
        manager = STIRSHAKENManager(config=config)
        assert manager.enable_signing is False
        assert manager.enable_verification is False
        assert manager.originating_tn == "+12125551234"
        assert manager.service_provider_code == "SP001"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", False)
    def test_init_crypto_not_available(self) -> None:
        manager = STIRSHAKENManager()
        assert manager.enabled is False

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_init_loads_private_key(self) -> None:
        config = {"private_key_path": "/fake/key.pem"}
        with patch.object(STIRSHAKENManager, "_load_private_key") as mock_load:
            STIRSHAKENManager(config=config)
            mock_load.assert_called_once_with("/fake/key.pem")

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_init_loads_certificate(self) -> None:
        config = {"certificate_path": "/fake/cert.pem"}
        with patch.object(STIRSHAKENManager, "_load_certificate") as mock_load:
            STIRSHAKENManager(config=config)
            mock_load.assert_called_once_with("/fake/cert.pem")

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_init_loads_ca_bundle(self) -> None:
        config = {"ca_cert_path": "/fake/ca.pem"}
        with patch.object(STIRSHAKENManager, "_load_ca_bundle") as mock_load:
            STIRSHAKENManager(config=config)
            mock_load.assert_called_once_with("/fake/ca.pem")


@pytest.mark.unit
class TestSTIRSHAKENManagerLoadKeys:
    """Tests for loading keys and certificates."""

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    @patch("pbx.features.stir_shaken.serialization")
    @patch("pbx.features.stir_shaken.Path")
    def test_load_private_key_success(self, mock_path_cls, mock_serialization) -> None:
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.return_value = b"fake key data"
        mock_path_cls.return_value.open.return_value = mock_file

        mock_key = MagicMock()
        mock_serialization.load_pem_private_key.return_value = mock_key

        manager = STIRSHAKENManager()
        manager._load_private_key("/fake/key.pem")
        assert manager.private_key == mock_key

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    @patch("pbx.features.stir_shaken.Path")
    def test_load_private_key_file_not_found(self, mock_path_cls) -> None:
        mock_path_cls.return_value.open.side_effect = FileNotFoundError("No file")
        manager = STIRSHAKENManager()
        manager._load_private_key("/nonexistent/key.pem")
        assert manager.enabled is False

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    @patch("pbx.features.stir_shaken.x509")
    @patch("pbx.features.stir_shaken.Path")
    def test_load_certificate_success(self, mock_path_cls, mock_x509) -> None:
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.return_value = b"fake cert data"
        mock_path_cls.return_value.open.return_value = mock_file

        mock_cert = MagicMock()
        mock_x509.load_pem_x509_certificate.return_value = mock_cert

        manager = STIRSHAKENManager()
        manager._load_certificate("/fake/cert.pem")
        assert manager.certificate == mock_cert

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    @patch("pbx.features.stir_shaken.Path")
    def test_load_certificate_file_error(self, mock_path_cls) -> None:
        mock_path_cls.return_value.open.side_effect = OSError("Read error")
        manager = STIRSHAKENManager()
        manager._load_certificate("/bad/cert.pem")
        assert manager.enabled is False

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    @patch("pbx.features.stir_shaken.x509")
    @patch("pbx.features.stir_shaken.Path")
    def test_load_ca_bundle_success(self, mock_path_cls, mock_x509) -> None:
        ca_data = (
            b"-----BEGIN CERTIFICATE-----\nfakecert1\n-----END CERTIFICATE-----\n"
            b"-----BEGIN CERTIFICATE-----\nfakecert2\n-----END CERTIFICATE-----\n"
        )
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.return_value = ca_data
        mock_path_cls.return_value.open.return_value = mock_file

        mock_cert = MagicMock()
        mock_x509.load_pem_x509_certificate.return_value = mock_cert

        manager = STIRSHAKENManager()
        manager._load_ca_bundle("/fake/ca.pem")
        assert manager.ca_bundle is not None
        assert len(manager.ca_bundle) == 2

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    @patch("pbx.features.stir_shaken.Path")
    def test_load_ca_bundle_file_error(self, mock_path_cls) -> None:
        mock_path_cls.return_value.open.side_effect = OSError("No CA file")
        manager = STIRSHAKENManager()
        manager._load_ca_bundle("/bad/ca.pem")
        # Should not crash; ca_bundle stays None


@pytest.mark.unit
class TestSTIRSHAKENManagerCreatePassport:
    """Tests for PASSporT token creation."""

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_passport_disabled(self) -> None:
        manager = STIRSHAKENManager()
        manager.enabled = False
        result = manager.create_passport("+12125551234", "+13105551234")
        assert result is None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_passport_signing_disabled(self) -> None:
        manager = STIRSHAKENManager(config={"enable_signing": False})
        result = manager.create_passport("+12125551234", "+13105551234")
        assert result is None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_passport_no_private_key(self) -> None:
        manager = STIRSHAKENManager()
        manager.private_key = None
        manager.certificate = MagicMock()
        result = manager.create_passport("+12125551234", "+13105551234")
        assert result is None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_passport_no_certificate(self) -> None:
        manager = STIRSHAKENManager()
        manager.private_key = MagicMock()
        manager.certificate = None
        result = manager.create_passport("+12125551234", "+13105551234")
        assert result is None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_passport_rsa_key(self) -> None:
        from cryptography.hazmat.primitives.asymmetric import rsa as real_rsa

        manager = STIRSHAKENManager()
        mock_key = MagicMock(spec=real_rsa.RSAPrivateKey)
        mock_key.sign.return_value = b"fakesignature"
        manager.private_key = mock_key
        manager.certificate = MagicMock()

        result = manager.create_passport("+12125551234", "+13105551234")
        assert result is not None
        parts = result.split(".")
        assert len(parts) == 3

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_passport_with_custom_orig_id(self) -> None:
        from cryptography.hazmat.primitives.asymmetric import rsa as real_rsa

        manager = STIRSHAKENManager()
        mock_key = MagicMock(spec=real_rsa.RSAPrivateKey)
        mock_key.sign.return_value = b"fakesignature"
        manager.private_key = mock_key
        manager.certificate = MagicMock()

        result = manager.create_passport("+12125551234", "+13105551234", orig_id="custom-uuid-123")
        assert result is not None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_passport_sign_exception(self) -> None:
        from cryptography.hazmat.primitives.asymmetric import rsa as real_rsa

        manager = STIRSHAKENManager()
        mock_key = MagicMock(spec=real_rsa.RSAPrivateKey)
        mock_key.sign.side_effect = Exception("Signing failed")
        manager.private_key = mock_key
        manager.certificate = MagicMock()

        result = manager.create_passport("+12125551234", "+13105551234")
        assert result is None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_passport_ec_key(self) -> None:
        """Test creating passport with non-RSA (EC) key."""
        manager = STIRSHAKENManager()
        mock_key = MagicMock()
        mock_key.sign.return_value = b"ec_signature_data"
        manager.private_key = mock_key
        manager.certificate = MagicMock()

        with patch("pbx.features.stir_shaken.rsa") as mock_rsa:
            mock_rsa.RSAPrivateKey = type("FakeRSAKey", (), {})
            result = manager.create_passport("+12125551234", "+13105551234")
            assert result is not None


@pytest.mark.unit
class TestSTIRSHAKENManagerVerifyPassport:
    """Tests for PASSporT token verification."""

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_disabled(self) -> None:
        manager = STIRSHAKENManager()
        manager.enabled = False
        valid, _payload, reason = manager.verify_passport("fake.jwt.token")
        assert valid is False
        assert reason == "Verification disabled"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_verification_disabled(self) -> None:
        manager = STIRSHAKENManager(config={"enable_verification": False})
        valid, _payload, reason = manager.verify_passport("fake.jwt.token")
        assert valid is False
        assert reason == "Verification disabled"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_invalid_jwt_format(self) -> None:
        manager = STIRSHAKENManager()
        valid, _payload, reason = manager.verify_passport("invalid_token")
        assert valid is False
        assert reason == "Invalid JWT format"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_not_shaken(self) -> None:
        manager = STIRSHAKENManager()
        header = (
            base64.urlsafe_b64encode(json.dumps({"ppt": "other"}).encode()).rstrip(b"=").decode()
        )
        payload = (
            base64.urlsafe_b64encode(json.dumps({"iat": int(time.time())}).encode())
            .rstrip(b"=")
            .decode()
        )
        sig = base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode()

        valid, _pay, reason = manager.verify_passport(f"{header}.{payload}.{sig}")
        assert valid is False
        assert reason == "Not a SHAKEN PASSporT"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_expired(self) -> None:
        manager = STIRSHAKENManager()
        header = (
            base64.urlsafe_b64encode(json.dumps({"ppt": "shaken", "alg": "RS256"}).encode())
            .rstrip(b"=")
            .decode()
        )
        payload = (
            base64.urlsafe_b64encode(json.dumps({"iat": int(time.time()) - 120}).encode())
            .rstrip(b"=")
            .decode()
        )
        sig = base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode()

        valid, _pay, reason = manager.verify_passport(f"{header}.{payload}.{sig}")
        assert valid is False
        assert reason == "PASSporT expired"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_missing_cert_url(self) -> None:
        manager = STIRSHAKENManager()
        header = (
            base64.urlsafe_b64encode(json.dumps({"ppt": "shaken", "alg": "RS256"}).encode())
            .rstrip(b"=")
            .decode()
        )
        payload = (
            base64.urlsafe_b64encode(json.dumps({"iat": int(time.time())}).encode())
            .rstrip(b"=")
            .decode()
        )
        sig = base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode()

        valid, _pay, reason = manager.verify_passport(f"{header}.{payload}.{sig}")
        assert valid is False
        assert reason == "Missing certificate URL"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_no_certificate(self) -> None:
        manager = STIRSHAKENManager()
        manager.certificate = None
        header = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"ppt": "shaken", "alg": "RS256", "x5u": "https://cert.example.com/cert.pem"}
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        payload = (
            base64.urlsafe_b64encode(json.dumps({"iat": int(time.time())}).encode())
            .rstrip(b"=")
            .decode()
        )
        sig = base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode()

        valid, _pay, reason = manager.verify_passport(f"{header}.{payload}.{sig}")
        assert valid is False
        assert reason == "No certificate for verification"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_rs256_success(self) -> None:
        manager = STIRSHAKENManager()
        mock_cert = MagicMock()
        mock_pub_key = MagicMock()
        mock_pub_key.verify.return_value = None  # No exception = success
        mock_cert.public_key.return_value = mock_pub_key
        manager.certificate = mock_cert

        header = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"ppt": "shaken", "alg": "RS256", "x5u": "https://cert.example.com"}
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        payload_data = {"iat": int(time.time()), "attest": "A", "orig": {"tn": "+12125551234"}}
        payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(b"validsig").rstrip(b"=").decode()

        valid, _pay, reason = manager.verify_passport(f"{header}.{payload}.{sig}")
        assert valid is True
        assert reason == "Signature valid"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_es256_success(self) -> None:
        manager = STIRSHAKENManager()
        mock_cert = MagicMock()
        mock_pub_key = MagicMock()
        mock_pub_key.verify.return_value = None
        mock_cert.public_key.return_value = mock_pub_key
        manager.certificate = mock_cert

        header = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"ppt": "shaken", "alg": "ES256", "x5u": "https://cert.example.com"}
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        payload_data = {"iat": int(time.time()), "attest": "B"}
        payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(b"ecsig").rstrip(b"=").decode()

        valid, _pay, _reason = manager.verify_passport(f"{header}.{payload}.{sig}")
        assert valid is True

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_signature_verify_fails(self) -> None:
        manager = STIRSHAKENManager()
        mock_cert = MagicMock()
        mock_pub_key = MagicMock()
        mock_pub_key.verify.side_effect = ValueError("Bad signature")
        mock_cert.public_key.return_value = mock_pub_key
        manager.certificate = mock_cert

        header = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"ppt": "shaken", "alg": "RS256", "x5u": "https://cert.example.com"}
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        payload_data = {"iat": int(time.time()), "attest": "A"}
        payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(b"badsig").rstrip(b"=").decode()

        valid, _pay, reason = manager.verify_passport(f"{header}.{payload}.{sig}")
        assert valid is False
        assert "Signature verification failed" in reason

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_passport_json_decode_error(self) -> None:
        manager = STIRSHAKENManager()
        # Create invalid base64 content that won't parse as JSON
        bad_header = base64.urlsafe_b64encode(b"not json").rstrip(b"=").decode()
        bad_payload = base64.urlsafe_b64encode(b"not json").rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode()

        valid, _pay, _reason = manager.verify_passport(f"{bad_header}.{bad_payload}.{sig}")
        assert valid is False


@pytest.mark.unit
class TestSTIRSHAKENManagerIdentityHeader:
    """Tests for SIP Identity header handling."""

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_identity_header_success(self) -> None:
        manager = STIRSHAKENManager()
        with patch.object(manager, "create_passport", return_value="fake.jwt.token"):
            result = manager.create_identity_header("+12125551234", "+13105551234")
            assert result is not None
            assert "fake.jwt.token" in result
            assert "ppt=shaken" in result

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_create_identity_header_passport_fails(self) -> None:
        manager = STIRSHAKENManager()
        with patch.object(manager, "create_passport", return_value=None):
            result = manager.create_identity_header("+12125551234", "+13105551234")
            assert result is None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_parse_identity_header_with_quotes(self) -> None:
        manager = STIRSHAKENManager()
        header = '"a.b.c";info=<https://cert.example.com>;alg=RS256;ppt=shaken'
        result = manager.parse_identity_header(header)
        assert result is not None
        assert result["passport"] == "a.b.c"
        assert result["info"] == "https://cert.example.com"
        assert result["alg"] == "RS256"
        assert result["ppt"] == "shaken"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_parse_identity_header_without_quotes(self) -> None:
        manager = STIRSHAKENManager()
        header = "a.b.c;info=<https://cert.example.com>;alg=RS256;ppt=shaken"
        result = manager.parse_identity_header(header)
        assert result is not None
        assert result["passport"] == "a.b.c"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_parse_identity_header_error(self) -> None:
        manager = STIRSHAKENManager()
        # Force an exception via patching
        with patch.object(manager, "logger"):
            result = manager.parse_identity_header(None)
            assert result is None

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_identity_header_empty(self) -> None:
        manager = STIRSHAKENManager()
        status, _payload = manager.verify_identity_header("")
        assert status == VerificationStatus.NO_SIGNATURE

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_identity_header_parse_fails(self) -> None:
        manager = STIRSHAKENManager()
        with patch.object(manager, "parse_identity_header", return_value=None):
            status, _payload = manager.verify_identity_header("bad header")
            assert status == VerificationStatus.VERIFICATION_FAILED

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_identity_header_verification_fails(self) -> None:
        manager = STIRSHAKENManager()
        parsed = {"passport": "a.b.c", "info": "url", "alg": "RS256", "ppt": "shaken"}
        with (
            patch.object(manager, "parse_identity_header", return_value=parsed),
            patch.object(
                manager, "verify_passport", return_value=(False, None, "Verification failed")
            ),
        ):
            status, _payload = manager.verify_identity_header("some header")
            assert status == VerificationStatus.VERIFICATION_FAILED

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_identity_header_attestation_a(self) -> None:
        manager = STIRSHAKENManager()
        parsed = {"passport": "a.b.c", "info": "url", "alg": "RS256", "ppt": "shaken"}
        pay = {"attest": "A"}
        with (
            patch.object(manager, "parse_identity_header", return_value=parsed),
            patch.object(manager, "verify_passport", return_value=(True, pay, "Signature valid")),
        ):
            status, _payload = manager.verify_identity_header("header")
            assert status == VerificationStatus.VERIFIED_FULL

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_identity_header_attestation_b(self) -> None:
        manager = STIRSHAKENManager()
        parsed = {"passport": "a.b.c", "info": "url", "alg": "RS256", "ppt": "shaken"}
        pay = {"attest": "B"}
        with (
            patch.object(manager, "parse_identity_header", return_value=parsed),
            patch.object(manager, "verify_passport", return_value=(True, pay, "ok")),
        ):
            status, _payload = manager.verify_identity_header("header")
            assert status == VerificationStatus.VERIFIED_PARTIAL

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_identity_header_attestation_c(self) -> None:
        manager = STIRSHAKENManager()
        parsed = {"passport": "a.b.c", "info": "url", "alg": "RS256", "ppt": "shaken"}
        pay = {"attest": "C"}
        with (
            patch.object(manager, "parse_identity_header", return_value=parsed),
            patch.object(manager, "verify_passport", return_value=(True, pay, "ok")),
        ):
            status, _payload = manager.verify_identity_header("header")
            assert status == VerificationStatus.VERIFIED_GATEWAY

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verify_identity_header_unknown_attestation(self) -> None:
        manager = STIRSHAKENManager()
        parsed = {"passport": "a.b.c", "info": "url", "alg": "RS256", "ppt": "shaken"}
        pay = {"attest": "X"}
        with (
            patch.object(manager, "parse_identity_header", return_value=parsed),
            patch.object(manager, "verify_passport", return_value=(True, pay, "ok")),
        ):
            status, _payload = manager.verify_identity_header("header")
            assert status == VerificationStatus.VERIFICATION_FAILED


@pytest.mark.unit
class TestSTIRSHAKENManagerVerificationDisplay:
    """Tests for verification status display."""

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verified_full_display(self) -> None:
        manager = STIRSHAKENManager()
        result = manager.get_verification_status_display(VerificationStatus.VERIFIED_FULL)
        assert result["trust_level"] == "high"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verified_partial_display(self) -> None:
        manager = STIRSHAKENManager()
        result = manager.get_verification_status_display(VerificationStatus.VERIFIED_PARTIAL)
        assert result["trust_level"] == "medium"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verified_gateway_display(self) -> None:
        manager = STIRSHAKENManager()
        result = manager.get_verification_status_display(VerificationStatus.VERIFIED_GATEWAY)
        assert result["trust_level"] == "low"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_no_signature_display(self) -> None:
        manager = STIRSHAKENManager()
        result = manager.get_verification_status_display(VerificationStatus.NO_SIGNATURE)
        assert result["trust_level"] == "unknown"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_verification_failed_display(self) -> None:
        manager = STIRSHAKENManager()
        result = manager.get_verification_status_display(VerificationStatus.VERIFICATION_FAILED)
        assert result["trust_level"] == "none"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_not_verified_display(self) -> None:
        manager = STIRSHAKENManager()
        result = manager.get_verification_status_display(VerificationStatus.NOT_VERIFIED)
        assert result["trust_level"] == "unknown"


@pytest.mark.unit
class TestSTIRSHAKENManagerHelpers:
    """Tests for helper methods."""

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_normalize_tn_already_e164(self) -> None:
        manager = STIRSHAKENManager()
        assert manager._normalize_tn("+12125551234") == "+12125551234"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_normalize_tn_10_digits(self) -> None:
        manager = STIRSHAKENManager()
        assert manager._normalize_tn("2125551234") == "+12125551234"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_normalize_tn_11_digits(self) -> None:
        manager = STIRSHAKENManager()
        assert manager._normalize_tn("12125551234") == "+12125551234"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_normalize_tn_short_number(self) -> None:
        manager = STIRSHAKENManager()
        result = manager._normalize_tn("1234")
        assert result == "1234"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_normalize_tn_with_special_chars(self) -> None:
        manager = STIRSHAKENManager()
        result = manager._normalize_tn("(212) 555-1234")
        assert result == "+12125551234"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_get_certificate_url_default(self) -> None:
        manager = STIRSHAKENManager()
        assert manager._get_certificate_url() == "https://cert.example.com/cert.pem"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_get_certificate_url_from_config(self) -> None:
        manager = STIRSHAKENManager(
            config={"certificate_url": "https://custom.example.com/cert.pem"}
        )
        assert manager._get_certificate_url() == "https://custom.example.com/cert.pem"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_base64url_encode(self) -> None:
        manager = STIRSHAKENManager()
        result = manager._base64url_encode(b"hello")
        assert isinstance(result, str)
        assert "=" not in result

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_base64url_decode(self) -> None:
        manager = STIRSHAKENManager()
        encoded = manager._base64url_encode(b"hello world")
        decoded = manager._base64url_decode(encoded)
        assert decoded == b"hello world"

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    def test_base64url_decode_with_padding(self) -> None:
        manager = STIRSHAKENManager()
        # Encode data that needs padding
        encoded = manager._base64url_encode(b"a")
        decoded = manager._base64url_decode(encoded)
        assert decoded == b"a"


@pytest.mark.unit
class TestSTIRSHAKENManagerGenerateCert:
    """Tests for test certificate generation."""

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", False)
    def test_generate_test_certificate_no_crypto(self) -> None:
        manager = STIRSHAKENManager()
        with pytest.raises(RuntimeError, match="Cryptography library not available"):
            manager.generate_test_certificate()

    @patch("pbx.features.stir_shaken.CRYPTO_AVAILABLE", True)
    @patch("pbx.features.stir_shaken.Path")
    @patch("pbx.features.stir_shaken.x509")
    @patch("pbx.features.stir_shaken.rsa")
    @patch("pbx.features.stir_shaken.hashes")
    @patch("pbx.features.stir_shaken.serialization")
    @patch("pbx.features.stir_shaken.NameOID")
    @patch("pbx.features.stir_shaken.default_backend")
    def test_generate_test_certificate_success(
        self,
        mock_backend,
        mock_nameoid,
        mock_serialization,
        mock_hashes,
        mock_rsa,
        mock_x509,
        mock_path_cls,
    ) -> None:
        mock_key = MagicMock()
        mock_rsa.generate_private_key.return_value = mock_key

        mock_cert_builder = MagicMock()
        mock_x509.CertificateBuilder.return_value = mock_cert_builder
        mock_cert_builder.subject_name.return_value = mock_cert_builder
        mock_cert_builder.issuer_name.return_value = mock_cert_builder
        mock_cert_builder.public_key.return_value = mock_cert_builder
        mock_cert_builder.serial_number.return_value = mock_cert_builder
        mock_cert_builder.not_valid_before.return_value = mock_cert_builder
        mock_cert_builder.not_valid_after.return_value = mock_cert_builder

        mock_signed_cert = MagicMock()
        mock_cert_builder.sign.return_value = mock_signed_cert
        mock_signed_cert.public_bytes.return_value = b"cert_bytes"

        mock_key.private_bytes.return_value = b"key_bytes"

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = MagicMock(return_value=mock_path_instance)
        mock_path_instance.open.return_value = mock_file
        mock_path_cls.return_value = mock_path_instance

        manager = STIRSHAKENManager()
        cert_path, key_path = manager.generate_test_certificate("/tmp/test")
        assert cert_path is not None
        assert key_path is not None


@pytest.mark.unit
class TestUtilityFunctions:
    """Tests for module-level utility functions."""

    def test_add_stir_shaken_to_invite_no_manager(self) -> None:
        sip_msg = MagicMock()
        result = add_stir_shaken_to_invite(sip_msg, None, "+12125551234", "+13105551234")
        assert result == sip_msg

    def test_add_stir_shaken_to_invite_disabled_manager(self) -> None:
        sip_msg = MagicMock()
        manager = MagicMock()
        manager.enabled = False
        result = add_stir_shaken_to_invite(sip_msg, manager, "+12125551234", "+13105551234")
        assert result == sip_msg

    def test_add_stir_shaken_to_invite_identity_created(self) -> None:
        sip_msg = MagicMock()
        manager = MagicMock()
        manager.enabled = True
        manager.create_identity_header.return_value = "fake_identity"
        _result = add_stir_shaken_to_invite(sip_msg, manager, "+12125551234", "+13105551234")
        sip_msg.set_header.assert_called_once_with("Identity", "fake_identity")

    def test_add_stir_shaken_to_invite_identity_none(self) -> None:
        sip_msg = MagicMock()
        manager = MagicMock()
        manager.enabled = True
        manager.create_identity_header.return_value = None
        _result = add_stir_shaken_to_invite(sip_msg, manager, "+12125551234", "+13105551234")
        sip_msg.set_header.assert_not_called()

    def test_verify_stir_shaken_invite_no_manager(self) -> None:
        sip_msg = MagicMock()
        status, _payload = verify_stir_shaken_invite(sip_msg, None)
        assert status == VerificationStatus.NOT_VERIFIED

    def test_verify_stir_shaken_invite_disabled_manager(self) -> None:
        sip_msg = MagicMock()
        manager = MagicMock()
        manager.enabled = False
        status, _payload = verify_stir_shaken_invite(sip_msg, manager)
        assert status == VerificationStatus.NOT_VERIFIED

    def test_verify_stir_shaken_invite_no_identity_header(self) -> None:
        sip_msg = MagicMock()
        sip_msg.get_header.return_value = None
        manager = MagicMock()
        manager.enabled = True
        status, _payload = verify_stir_shaken_invite(sip_msg, manager)
        assert status == VerificationStatus.NO_SIGNATURE

    def test_verify_stir_shaken_invite_with_identity(self) -> None:
        sip_msg = MagicMock()
        sip_msg.get_header.return_value = "identity_header_value"
        manager = MagicMock()
        manager.enabled = True
        manager.verify_identity_header.return_value = (
            VerificationStatus.VERIFIED_FULL,
            {"attest": "A"},
        )
        status, _payload = verify_stir_shaken_invite(sip_msg, manager)
        assert status == VerificationStatus.VERIFIED_FULL
